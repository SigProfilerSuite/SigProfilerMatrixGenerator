from pathlib import Path

import pytest

from SigProfilerMatrixGenerator.web import inputs

BRCA_EXAMPLE = (
    Path(inputs.__file__).resolve().parents[1]
    / "references" / "vcf_files" / "BRCA_example" / "SNV"
)


def _maf(rows):
    header = "\t".join(["c"] * 20)
    lines = [header]
    for sample in rows:
        row = ["."] * 20
        row[15] = sample
        lines.append("\t".join(row))
    return "\n".join(lines) + "\n"


def test_browse_lists_visible_entries_only(tmp_path):
    (tmp_path / "visible.txt").write_text("x")
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "subdir").mkdir()

    result = inputs.browse(str(tmp_path))

    by_name = {entry["name"]: entry["is_dir"] for entry in result["entries"]}
    assert by_name == {"visible.txt": False, "subdir": True}


def test_browse_rejects_a_file_path(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x")
    with pytest.raises(inputs.InputError):
        inputs.browse(str(target))


def test_vcf_is_one_sample_per_file_and_counts_records(tmp_path):
    (tmp_path / "PD1.vcf").write_text("##fileformat=VCFv4.2\n#CHROM\n1\t10\t.\tA\tG\n1\t20\t.\tC\tT\n")
    (tmp_path / "PD2.vcf").write_text("##fileformat=VCFv4.2\n#CHROM\n2\t10\t.\tA\tG\n")

    result = inputs.inspect(str(tmp_path))

    assert result["format"] == "VCF"
    assert result["file_count"] == 2
    assert result["sample_count"] == 2
    assert result["records"] == 3
    assert result["samples_preview"] == ["PD1", "PD2"]


def test_txt_samples_come_from_the_second_column(tmp_path):
    # convertTxt() reads the sample from field 2 of every line; one file can
    # hold many samples, so counting files would be wrong.
    lines = [
        "BRCA\tS1\tCGP\tGRCh37\tSNP\t1\t100\t100\tA\tG",
        "BRCA\tS1\tCGP\tGRCh37\tSNP\t1\t200\t200\tC\tT",
        "BRCA\tS2\tCGP\tGRCh37\tSNP\t2\t300\t300\tG\tA",
    ]
    (tmp_path / "cohort.txt").write_text("\n".join(lines) + "\n")

    result = inputs.inspect(str(tmp_path))

    assert result["format"] == "Txt"
    assert result["file_count"] == 1
    assert result["sample_count"] == 2
    assert result["records"] == 3


def test_maf_samples_come_from_tumor_sample_barcode(tmp_path):
    (tmp_path / "cohort.maf").write_text(_maf(["SAMPLE_A", "SAMPLE_A", "SAMPLE_B"]))

    result = inputs.inspect(str(tmp_path))

    assert result["format"] == "MAF"
    assert result["sample_count"] == 2
    assert result["records"] == 3


def test_files_the_generator_skips_are_ignored(tmp_path):
    # SigProfilerMatrixGeneratorFunc skips names starting with "__" or ".DS".
    (tmp_path / "PD1.vcf").write_text("##fileformat=VCFv4.2\n")
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / ".DS_Store").write_text("")

    result = inputs.inspect(str(tmp_path))

    assert result["file_count"] == 1
    assert result["other_count"] == 0


def test_other_files_are_reported(tmp_path):
    (tmp_path / "PD1.vcf").write_text("##fileformat=VCFv4.2\n")
    (tmp_path / "README.md").write_text("notes")

    result = inputs.inspect(str(tmp_path))

    assert result["other_count"] == 1
    assert result["other_files"] == ["README.md"]


def test_legacy_input_subfolder_is_used_when_the_folder_has_no_files(tmp_path):
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "PD1.vcf").write_text("##fileformat=VCFv4.2\n")

    result = inputs.inspect(str(tmp_path))

    assert result["format"] == "VCF"
    assert result["source"] == str(tmp_path / "input")


def test_inspect_rejects_mixed_formats(tmp_path):
    (tmp_path / "a.vcf").write_text("##fileformat=VCFv4.2\n")
    (tmp_path / "b.maf").write_text(_maf(["S1"]))

    with pytest.raises(inputs.InputError, match="mixes formats"):
        inputs.inspect(str(tmp_path))


def test_inspect_rejects_a_folder_with_no_mutation_files(tmp_path):
    (tmp_path / "notes.tsv").write_text("x")

    with pytest.raises(inputs.InputError, match="no .vcf, .maf or .txt files"):
        inputs.inspect(str(tmp_path))


def test_inspect_rejects_missing_path(tmp_path):
    with pytest.raises(inputs.InputError, match="does not exist"):
        inputs.inspect(str(tmp_path / "nope"))


def test_inspect_rejects_a_single_file_and_names_its_folder(tmp_path):
    # path_to_input_files is a folder: SigProfilerMatrixGeneratorFunc lists it.
    target = tmp_path / "sample1.vcf"
    target.write_text("##fileformat=VCFv4.2\n")

    with pytest.raises(inputs.InputError, match="choose the folder") as excinfo:
        inputs.inspect(str(target))
    assert str(tmp_path) in str(excinfo.value)


def test_bundled_brca_example_is_recognised():
    result = inputs.inspect(str(BRCA_EXAMPLE))

    assert result["format"] == "Txt"
    assert result["sample_count"] == 4
    assert result["records"] == 32455


def test_bundled_examples_declare_their_assemblies():
    # The BRCA example names GRCh37 in its genome column; the GRCh38 test set
    # VCF has no ##reference header, so its assembly is unknown, not guessed.
    assert inputs.inspect(str(BRCA_EXAMPLE))["assembly"] == "GRCh37"
    assert inputs.inspect(str(BRCA_EXAMPLE.parents[1] / "GRCh38_bench"))["assembly"] is None


@pytest.mark.parametrize("header, assembly", [
    ("##reference=GRCh38", "GRCh38"),
    ("##reference=file:///refs/hs37d5.fa", "GRCh37"),
    ("##reference=/data/Homo_sapiens_assembly38.fasta", None),
    ("##reference=/refs/chm13v2.0.fa", "CHM13-T2T"),
    ("##assembly=hg19", "GRCh37"),
    ("##source=caller", None),
])
def test_vcf_assembly_comes_from_its_header(tmp_path, header, assembly):
    (tmp_path / "S1.vcf").write_text(f"##fileformat=VCFv4.2\n{header}\n#CHROM\n1\t10\t.\tA\tG\n")
    assert inputs.inspect(str(tmp_path))["assembly"] == assembly


def test_maf_assembly_comes_from_ncbi_build(tmp_path):
    rows = _maf(["S1", "S2"]).splitlines()
    body = []
    for line in rows[1:]:
        fields = line.split("\t")
        fields[3] = "37"
        body.append("\t".join(fields))
    (tmp_path / "cohort.maf").write_text("\n".join([rows[0], *body]) + "\n")
    assert inputs.inspect(str(tmp_path))["assembly"] == "GRCh37"


def test_disagreeing_files_declare_no_assembly(tmp_path):
    (tmp_path / "a.txt").write_text("P\tS1\tCGP\tGRCh37\tSNP\t1\t100\t100\tA\tG\n")
    (tmp_path / "b.txt").write_text("P\tS2\tCGP\tGRCh38\tSNP\t1\t100\t100\tA\tG\n")
    result = inputs.inspect(str(tmp_path))
    assert result["assembly"] is None
    assert result["declared_assembly"] == ["GRCh37", "GRCh38"]
