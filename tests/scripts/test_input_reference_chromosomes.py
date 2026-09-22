import pytest

from SigProfilerMatrixGenerator.scripts import convert_input_to_simple_files as convert
from SigProfilerMatrixGenerator.scripts import reference_genome_manager


@pytest.mark.parametrize("format_name", ["VCF", "Txt", "MAF"])
def test_input_conversion_uses_registered_chromosomes(
    monkeypatch, tmp_path, format_name
):
    # No per-chromosome transcript files are present. Chromosome 2 can be
    # unannotated and still has an installed nucleotide/TSB reference.
    monkeypatch.setitem(
        reference_genome_manager.CHECKSUMS, "fixture", {"1": "unused", "2": "unused"}
    )
    source, output = tmp_path / "input", tmp_path / "output"
    source.mkdir()
    output.mkdir()
    variants = [("1", "3", "C", "A"), ("2", "10", "C", "CA")]
    if format_name == "MAF":
        variants[1] = ("2", "10", "-", "A")
    if format_name == "VCF":
        contents = (
            "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        )
        contents += "".join(
            f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t.\tPASS\t.\n"
            for chrom, pos, ref, alt in variants
        )
    else:
        rows = []
        for chrom, pos, ref, alt in variants:
            row = ["."] * (10 if format_name == "Txt" else 16)
            fields = (
                {1: "S1", 5: chrom, 6: pos, 7: pos, 8: ref, 9: alt}
                if format_name == "Txt"
                else {
                    4: chrom,
                    5: pos,
                    6: pos,
                    10: ref,
                    12: alt,
                    15: "S1",
                }
            )
            for index, value in fields.items():
                row[index] = value
            rows.append("\t".join(row))
        contents = "header\n" + "\n".join(rows) + "\n"
    (source / "S1.input").write_text(contents)
    result = getattr(convert, "convert" + format_name)(
        "fixture",
        str(source) + "/",
        "fixture",
        str(output) + "/",
        {},
        str(tmp_path / "convert.log"),
    )
    assert result == (True, True, 0, ["S1"])
    assert (output / "SNV" / "1_fixture.genome").read_text() == "S1\t1\t3\tC\tA\n"
    # Keep the existing MAF insertion anchor conversion separate from routing.
    expected_indel = (
        "S1\t2\t9\t-\tA\n" if format_name == "MAF" else "S1\t2\t10\tC\tCA\n"
    )
    assert (output / "INDEL" / "2_fixture.genome").read_text() == expected_indel


def test_unregistered_genome_has_clear_error():
    with pytest.raises(ValueError, match="No chromosome manifest is registered"):
        convert._get_output_chromosomes("not_a_registered_genome")
