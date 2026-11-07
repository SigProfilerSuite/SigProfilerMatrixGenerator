import hashlib

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import ref_install, reference_genome_manager, save_tsb_192


@pytest.fixture
def matrix_run(tmp_path, monkeypatch):
    volume = tmp_path / "volume"
    sequence = tmp_path / "sequence"
    transcripts = tmp_path / "transcripts"
    sequence.mkdir()
    transcripts.mkdir()
    (sequence / "1.txt").write_text("C" * 20)
    (transcripts / "combined.txt").write_text("g1 t1 1 1 4 10\n")
    save_tsb_192.save_tsb(sequence, transcripts, volume / "tsb" / "GRCh38")
    digest = hashlib.md5((volume / "tsb" / "GRCh38" / "1.txt").read_bytes()).hexdigest()
    monkeypatch.setitem(reference_genome_manager.CHECKSUMS, "GRCh38", {"1": digest})
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    monkeypatch.setattr(ref_install.ReferenceDir, "_get_package_installation_folder", lambda self: tmp_path / "package")

    def run(source, output=None):
        return api.SigProfilerMatrixGeneratorFunc(
            "fixture", "GRCh38", str(source), plot=False, seqInfo=False,
            cushion=0, volume=str(volume),
            output_directory=str(output) if output is not None else None,
        )
    return run


def write_vcf(path, alternate="A", position=3):
    path.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        f"1\t{position}\t.\tC\t{alternate}\t.\tPASS\t.\n"
    )


def test_reused_output_reads_new_cohort(matrix_run, tmp_path):
    first = tmp_path / "cohort_a"
    second = tmp_path / "cohort_b"
    first.mkdir()
    second.mkdir()
    write_vcf(first / "old.vcf")
    write_vcf(second / "new.vcf", "G")
    output = tmp_path / "output"
    old = matrix_run(first, output)
    new = matrix_run(second, output)
    assert list(old["96"].columns) == ["old"]
    assert list(new["96"].columns) == ["new"]
    assert new["96"].at["C[C>G]C", "new"] == 1
    saved = pd.read_csv(output / "SBS" / "fixture.SBS96.all", sep="\t", index_col=0)
    pd.testing.assert_frame_equal(saved, new["96"])
    assert len(list((output / "input").glob("*/old.vcf"))) == 1
    assert len(list((output / "input").glob("*/new.vcf"))) == 1


@pytest.mark.parametrize("explicit_output", [False, True])
def test_modified_and_removed_inputs_are_not_reused(matrix_run, tmp_path, explicit_output):
    source = tmp_path / "source"
    source.mkdir()
    write_vcf(source / "sample.vcf")
    write_vcf(source / "removed.vcf", position=10)
    output = tmp_path / "output" if explicit_output else None
    first = matrix_run(source, output)
    assert set(first["96"].columns) == {"sample", "removed"}
    (source / "removed.vcf").unlink()
    write_vcf(source / "sample.vcf", "G")
    second = matrix_run(source, output)
    assert list(second["96"].columns) == ["sample"]
    assert second["96"].at["C[C>A]C", "sample"] == 0
    assert second["96"].at["C[C>G]C", "sample"] == 1


def test_legacy_project_input_directory_remains_supported(matrix_run, tmp_path):
    project = tmp_path / "project"
    source = project / "input"
    source.mkdir(parents=True)
    write_vcf(source / "sample.vcf")
    matrices = matrix_run(project)
    assert matrices["96"].at["C[C>A]C", "sample"] == 1
    assert (source / "sample.vcf").exists()


def test_empty_source_does_not_fall_back_to_output_inputs(matrix_run, tmp_path):
    source = tmp_path / "empty"
    source.mkdir()
    output = tmp_path / "output"
    stale = output / "input"
    stale.mkdir(parents=True)
    write_vcf(stale / "old.vcf")
    with pytest.raises(ValueError, match="No input files found"):
        matrix_run(source, output)
    assert (stale / "old.vcf").exists()
