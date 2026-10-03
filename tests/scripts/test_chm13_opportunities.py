import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import save_context_distribution as reference
from tools.build_chm13_opportunities import (
    CONTEXTS, collapse_counts, primitive_counts, read_intervals, write_tables,
)


TSB_REF = {value: ["NTUB"[value // 4], "ACGT"[value % 4]] for value in range(16)}
TSB_REF.update({16 + state: ["NTUB"[state], "N"] for state in range(4)})


@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("exome", [False, True])
def test_chunked_opportunities_match_existing_scalar_generator(tmp_path, context, exome):
    rng = np.random.default_rng(250)
    encoded = rng.integers(0, 20, size=1000, dtype=np.uint8)
    chromosome = tmp_path / "1.txt"
    chromosome.write_bytes(encoded.tobytes())
    intervals = [(0, 311), (330, 1000)]
    expected = collapse_counts(primitive_counts(encoded, intervals if exome else None, chunk_size=7))[context]
    output = tmp_path / "distribution.csv"
    if exome:
        exome_path = tmp_path / "exome.interval_list"
        exome_path.write_text("@header\nchr1\t1\t311\nchr1\t331\t1000\n")
        reference.context_distribution_BED(
            context, str(output), str(tmp_path) + "/", ["1"], False, None,
            True, str(exome_path), "CHM13-T2T", str(tmp_path), TSB_REF, "male",
        )
    else:
        reference.context_distribution(context, str(output), str(tmp_path) + "/", ["1"], TSB_REF, "CHM13-T2T")
    suffix = "_exome" if exome else ""
    observed = pd.read_csv(tmp_path / f"context_counts_CHM13-T2T_{context}{suffix}.csv", index_col=0)
    assert list(observed.columns) == ["1"]
    observed_counts = observed["1"].to_dict()
    assert observed_counts == {label: expected[label] for label in observed_counts}
    assert sum(observed_counts.values()) == sum(expected.values())


def test_one_based_exome_boundaries_and_ambiguous_windows(tmp_path):
    path = tmp_path / "intervals.txt"
    path.write_text("@header\nchr1\t1\t5\n")
    assert read_intervals(path) == {"1": [(0, 5)]}
    counts = collapse_counts(primitive_counts(np.array([1, 1, 4, 1, 1], dtype=np.uint8), [(0, 5)], chunk_size=1))
    assert counts["24"]["U:T"] == 1
    assert sum(counts["6"].values()) == 1
    assert sum(primitive_counts(np.array([1, 1, 16, 1, 1]))["6144"].values()) == 0
    with pytest.raises(ValueError, match="Invalid TSB"):
        primitive_counts(np.array([255], dtype=np.uint8))


def test_distributions_exclude_y_for_female_and_handle_zero_rows(tmp_path):
    primitive = collapse_counts(primitive_counts(np.array([1, 1, 4, 1, 1], dtype=np.uint8)))
    counts = {mode: {chrom: primitive for chrom in ["X", "Y", "1"]}
              for mode in ["whole_genome", "exome"]}
    write_tables(tmp_path, counts, chromosomes=["X", "Y", "1"])
    assert len(list(tmp_path.glob("*.csv"))) == 48
    female = pd.read_csv(tmp_path / "context_distribution_CHM13-T2T_24_female.csv", index_col=0)
    assert list(female.columns) == ["X", "1"]
    assert female.loc["U:T"].tolist() == [0.5, 0.5]
    assert female.loc["N:C"].sum() == 0


ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "SigProfilerMatrixGenerator/references/chromosomes/context_distributions"


def test_chm13_table_fingerprints_and_exact_footprint():
    manifest = pd.read_csv(ROOT / "reference_data/CHM13-T2T/opportunity_manifest.tsv", sep="\t")
    observed = {path.name for path in TABLES.glob("*CHM13-T2T*.csv")}
    assert len(manifest) == 48
    assert set(manifest["filename"]) == observed
    for row in manifest.itertuples(index=False):
        assert hashlib.sha256((TABLES / row.filename).read_bytes()).hexdigest() == row.sha256


@pytest.mark.parametrize("context,rows", [("6", 2), ("24", 8), ("96", 32), ("384", 128), ("1536", 512), ("6144", 2048), ("DBS", 10), ("DBS186", 22)])
@pytest.mark.parametrize("exome", [False, True])
def test_packaged_counts_and_chromosome_probabilities(context, rows, exome):
    suffix = "_exome" if exome else ""
    counts = pd.read_csv(TABLES / f"context_counts_CHM13-T2T_{context}{suffix}.csv", index_col=0)
    assert len(counts) == rows and counts.index.is_unique
    assert list(counts.columns) == ["X", "Y", *map(str, range(1, 23))]
    assert all(dtype.kind in "iu" for dtype in counts.dtypes)
    assert (counts.to_numpy() >= 0).all()
    for sex in ["male", "female"]:
        distribution = pd.read_csv(TABLES / f"context_distribution_CHM13-T2T_{context}_{sex}{suffix}.csv", index_col=0)
        selected = counts if sex == "male" else counts.drop(columns="Y")
        expected = selected.div(selected.sum(axis=1).replace(0, 1), axis=0)
        pd.testing.assert_frame_equal(distribution, expected, check_dtype=False, atol=1e-14, rtol=1e-14)
