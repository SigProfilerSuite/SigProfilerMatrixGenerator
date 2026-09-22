import csv

import pytest

from SigProfilerMatrixGenerator.scripts import save_context_distribution as contexts


TSB_REF = {value: ["NTUB"[value // 4], "ACGT"[value % 4]] for value in range(16)}
TSB_REF.update({16: ["N", "N"], 17: ["T", "N"], 18: ["U", "N"], 19: ["B", "N"]})


def read_counts(path):
    with path.open() as handle:
        rows = csv.reader(handle)
        header = next(rows)[1:]
        return {row[0]: dict(zip(header, map(int, row[1:]))) for row in rows}


@pytest.mark.parametrize(
    "context,first_channel,second_channel",
    [
        ("24", "U:T", "T:C"),
        ("384", "U:GTG", "T:GCG"),
        ("6144", "U:GGTGG", "T:GGCGG"),
    ],
)
def test_whole_genome_distribution_uses_five_base_opportunities_and_reverses_bias(
    tmp_path, context, first_channel, second_channel
):
    chromosome_dir = tmp_path / "chromosomes"
    output_dir = tmp_path / "output"
    chromosome_dir.mkdir()
    output_dir.mkdir()
    # T:A and U:G must switch strand after canonicalization. U:G is encoded as
    # byte 10, so this also checks that binary data is not stripped.
    (chromosome_dir / "1.txt").write_bytes(bytes([1, 1, 4, 1, 1]))
    (chromosome_dir / "2.txt").write_bytes(bytes([1, 1, 10, 1, 1]))
    output = output_dir / f"context_distribution_fixture_{context}_male.csv"

    contexts.context_distribution(
        context,
        str(output),
        f"{chromosome_dir}/",
        ["1", "2"],
        TSB_REF,
        "fixture",
    )

    counts = read_counts(output_dir / f"context_counts_fixture_{context}.csv")
    assert counts[first_channel]["1"] == 1
    assert counts[second_channel]["2"] == 1


def test_exome_distribution_uses_same_opportunities_and_bias(tmp_path):
    chromosome_dir = tmp_path / "chromosomes"
    output_dir = tmp_path / "output"
    chromosome_dir.mkdir()
    output_dir.mkdir()
    (chromosome_dir / "1.txt").write_bytes(bytes([1, 1, 4, 1, 1]))
    (chromosome_dir / "2.txt").write_bytes(bytes([1, 1, 10, 1, 1]))
    intervals = tmp_path / "exome.interval_list"
    intervals.write_text("@header\n1\t0\t5\n2\t0\t5\n")
    output = output_dir / "context_distribution_fixture_24_male_exome.csv"

    contexts.context_distribution_BED(
        "24",
        str(output),
        f"{chromosome_dir}/",
        ["1", "2"],
        False,
        None,
        True,
        str(intervals),
        "fixture",
        str(tmp_path),
        TSB_REF,
        "male",
    )

    counts = read_counts(output_dir / "context_counts_fixture_24_exome.csv")
    assert counts["U:T"]["1"] == 1
    assert counts["T:C"]["2"] == 1


def test_binary_whitespace_bytes_at_file_boundaries_are_not_removed(tmp_path):
    chromosome_dir = tmp_path / "chromosomes"
    output_dir = tmp_path / "output"
    chromosome_dir.mkdir()
    output_dir.mkdir()
    # Bytes 10 and 9 are valid TSB/base encodings. Placing them at the file
    # boundaries catches regressions that call strip() on binary chromosome data.
    (chromosome_dir / "1.txt").write_bytes(bytes([10, 1, 5, 1, 1, 9]))
    output = output_dir / "context_distribution_fixture_24_male.csv"

    contexts.context_distribution(
        "24",
        str(output),
        f"{chromosome_dir}/",
        ["1"],
        TSB_REF,
        "fixture",
    )

    counts = read_counts(output_dir / "context_counts_fixture_24.csv")
    assert sum(channel_counts["1"] for channel_counts in counts.values()) == 2
