import csv
from pathlib import Path

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import koh_indels as koh


DATA = Path(__file__).parents[1] / "data"
with (DATA / "koh_indels_oracle.tsv").open() as handle:
    ORACLE = list(csv.DictReader(handle, delimiter="\t"))


@pytest.mark.parametrize("event", ORACLE, ids=[row["id476"] for row in ORACLE])
def test_matches_independent_r_classifier(event):
    result = koh.classify_indel(
        event["sequence"],
        int(event["position"]),
        event["reference"],
        event["alternate"],
    )
    assert result.id89 == event["id89"]
    assert result.id476 == event["id476"]


def test_canonical_rows_and_all_channel_coverage():
    assert len(koh.ID476_CHANNELS) == len(set(koh.ID476_CHANNELS)) == 476
    assert len(koh.ID89_CHANNELS) == len(set(koh.ID89_CHANNELS)) == 89
    assert (
        list(koh.ID89_CHANNELS)
        == (DATA / "koh_id89_channels.txt").read_text().splitlines()
    )
    assert (
        list(koh.ID476_CHANNELS)
        == (DATA / "koh_id476_channels.txt").read_text().splitlines()
    )
    assert {row["id476"] for row in ORACLE} == set(koh.ID476_CHANNELS)
    assert {row["id89"] for row in ORACLE} == set(koh.ID89_CHANNELS)


def test_id476_is_not_always_a_lossless_parent_of_id89():
    low = koh.classify_indel("GATATATATC", 1, "GATATAT", "G")
    high = koh.classify_indel("GATATATATATC", 1, "GATATAT", "G")
    assert low.id476 == high.id476 == "Del(6,):U2:R(4,)"
    assert low.id89 == "Del(2,8):U(1,2):R(2,4)"
    assert high.id89 == "Del(2,):U(1,2):R(5,)"


def test_equivalent_indel_positions_have_identical_labels():
    first = koh.classify_indel("GATATATC", 1, "GAT", "G")
    shifted = koh.classify_indel("GATATATC", 3, "TAT", "T")
    assert first == shifted


@pytest.mark.parametrize("event", [row for row in ORACLE if "[" in row["id476"]])
def test_purine_and_pyrimidine_reverse_complements(event):
    sequence = event["sequence"]
    complement = str.maketrans("ACGT", "TGCA")
    reverse = lambda value: value.translate(complement)[::-1]
    original = koh.classify_indel(
        sequence, int(event["position"]), event["reference"], event["alternate"]
    )
    position = len(sequence) - int(event["position"]) - len(event["reference"]) + 2
    reflected = koh.classify_indel(
        reverse(sequence),
        position,
        reverse(event["reference"]),
        reverse(event["alternate"]),
    )
    assert (original.id89, original.id476) == (reflected.id89, reflected.id476)


@pytest.mark.parametrize(
    "sequence,pos,ref,alt,reason",
    [
        ("GACT", 1, "T", "TA", "reference_allele_mismatch"),
        ("GACT", 1, "GAT", "G", "reference_allele_mismatch"),
        ("GACT", 0, "G", "GA", "reference_out_of_bounds"),
        ("GACT", 5, "T", "TA", "reference_out_of_bounds"),
        ("GACT", 1, "G", "<INS>", "non_literal"),
        ("GACT", 1, "G", "GA,GT", "non_literal"),
        ("GACT", 1, "G", "GN", "non_literal"),
        ("GACT", 1, "-", "A", "non_literal"),
        ("GACT", 1, "G", "G", "unchanged"),
        ("GAAA", 1, "GA", "G", "missing_sequence_context"),
        ("AAAAC", 1, "AA", "A", "missing_sequence_context"),
        ("NAAAC", 2, "AA", "A", "ambiguous_sequence_context"),
    ],
)
def test_rejects_invalid_alleles_and_missing_context(sequence, pos, ref, alt, reason):
    with pytest.raises(koh.IndelClassificationError, match=reason):
        koh.classify_indel(sequence, pos, ref, alt)


def test_binary_reference_does_not_strip_valid_terminal_bytes(tmp_path):
    path = tmp_path / "chromosome.txt"
    encoded = bytes([9, 10, 13, 16, 17, 18, 19, 9])
    path.write_bytes(encoded)
    with koh.EncodedReference(path) as reference:
        assert len(reference) == 8
        assert reference[:] == "CGCNNNNC"
        assert reference[0] == reference[-1] == "C"


@pytest.mark.parametrize(
    "contexts,expected",
    [(None, ()), ([], ()), ("89", ("89",)), (("ID89", "476", "89"), ("89", "476"))],
)
def test_context_selection(contexts, expected):
    assert koh.validate_contexts(contexts) == expected


def test_rejects_unsupported_context():
    with pytest.raises(ValueError, match="indel_contexts"):
        koh.validate_contexts(["83"])


def test_intervals_merge_and_select_original_anchor(tmp_path):
    path = tmp_path / "regions.bed"
    path.write_text("#chrom start end\nchr1\t10\t15\nchr1\t12\t20\nchr1\t30\t31\n")
    selection = koh.IntervalSelection(path, 1, lambda chrom: chrom.removeprefix("chr"))
    assert selection.contains("1", 9)
    assert selection.contains("1", 21)
    assert not selection.contains("1", 22)
    assert not selection.contains("2", 10)


def test_duplicate_calls_are_sample_specific_and_reports_exclusions(tmp_path):
    encoded = tmp_path / "chromosomes"
    encoded.mkdir()
    sequence = "GATATATC"
    (encoded / "1.txt").write_bytes(bytes("ACGT".index(base) for base in sequence))
    catalog = koh.KohIndelCatalog(("89", "476"), ["a", "b"], tmp_path, "test", encoded)
    catalog.count_chromosome(
        "1",
        [
            ["a", "1", "1", "GAT", "G"],
            ["a", "1", "3", "TAT", "T"],
            ["b", "1", "1", "GAT", "G"],
            ["a", "1", "1", "TAT", "T"],
        ],
    )
    matrices = catalog.save(tmp_path / "log")
    assert matrices["ID89"].to_numpy().sum() == 2
    assert matrices["ID476"].to_numpy().sum() == 2
    assert catalog.summary == {
        "counted": 2,
        "duplicate": 1,
        "reference_allele_mismatch": 1,
    }
    report = pd.read_csv(catalog.report, sep="\t")
    assert len(report) == 4
    assert report.Status.tolist()[-1] == "reference_allele_mismatch"


@pytest.mark.parametrize("contexts", [("89",), ("476",)])
def test_single_context_multichromosome_and_empty_catalog(tmp_path, contexts):
    encoded = tmp_path / "chromosomes"
    encoded.mkdir()
    for chrom in ("1", "2"):
        (encoded / f"{chrom}.txt").write_bytes(
            bytes("ACGT".index(base) for base in "GATATATC")
        )
    empty = koh.KohIndelCatalog(contexts, ["sample"], tmp_path, "empty", encoded)
    for matrix in empty.save(tmp_path / "log").values():
        assert matrix.to_numpy().sum() == 0
    catalog = koh.KohIndelCatalog(
        contexts, ["sample"], tmp_path, "test", encoded, chrom_based=True
    )
    for chrom in ("1", "2"):
        catalog.count_chromosome(chrom, [["sample", chrom, "1", "GAT", "G"]])
    matrices = catalog.save(tmp_path / "log")
    assert list(matrices) == [f"ID{contexts[0]}"]
    assert next(iter(matrices.values())).to_numpy().sum() == 2
    for chrom in ("1", "2"):
        saved = pd.read_csv(
            tmp_path / "ID" / f"test.ID{contexts[0]}.all.chr{chrom}",
            sep="\t",
            index_col=0,
        )
        assert saved.to_numpy().sum() == 1


def test_normalization_does_not_change_region_membership(tmp_path):
    encoded = tmp_path / "chromosomes"
    encoded.mkdir()
    (encoded / "1.txt").write_bytes(bytes("ACGT".index(base) for base in "GATATATC"))
    intervals = tmp_path / "intervals"
    intervals.write_text("1\t3\t3\n")
    selection = koh.IntervalSelection(intervals, 0, lambda chrom: chrom)
    catalog = koh.KohIndelCatalog(
        ("89", "476"), ["sample"], tmp_path, "test", encoded, selection=selection
    )
    catalog.count_chromosome(
        "1", [["sample", "1", "1", "GAT", "G"], ["sample", "1", "3", "TAT", "T"]]
    )
    assert catalog.summary == {"counted": 1, "outside_region": 1}
    assert catalog.matrices["ID89"].to_numpy().sum() == 1
    report = pd.read_csv(catalog.report, sep="\t")
    assert report.iloc[1].InputPosition == 3
    assert report.iloc[1].NormalizedPosition == 2


def test_unknown_base_after_a_long_repeat_is_not_a_known_mismatch():
    with pytest.raises(
        koh.IndelClassificationError, match="ambiguous_sequence_context"
    ):
        koh.classify_indel("GATATATATATATNTC", 1, "GAT", "G")
