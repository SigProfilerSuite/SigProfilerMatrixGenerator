import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts.CNVMatrixGenerator import generateCNVMatrix


@pytest.mark.parametrize("minor", [0, 1, None, "NA"])
def test_facets_single_copy_uses_existing_loh_channels(tmp_path, minor):
    ends = [50_000, 500_000, 5_000_000, 20_000_000, 50_000_000]
    sizes = ["0-100kb", "100kb-1Mb", "1Mb-10Mb", "10Mb-40Mb", ">40Mb"]
    rows = [["S1", 1, minor, 0, end] for end in ends]
    rows += [
        ["S1", 2, 1, 0, 50_000_000],
        ["S1", 0, 0, 0, 2_000_000],
        ["S1", 2, 0, 0, 5_000_000],
    ]
    source = tmp_path / "facets.tsv"
    pd.DataFrame(rows, columns=["sample", "tcn.em", "lcn.em", "start", "end"]).to_csv(
        source, sep="\t", index=False
    )
    output = tmp_path / "output"
    matrix = generateCNVMatrix("FACETS", str(source), "fixture", str(output))
    counts = matrix.set_index("MutationType")["S1"]
    assert len(counts) == 48
    assert counts.sum() == len(rows)
    assert [counts[f"1:LOH:{size}"] for size in sizes] == [1] * 5
    assert counts["2:het:>40Mb"] == 1
    assert counts["0:homdel:>1Mb"] == 1
    assert counts["2:LOH:1Mb-10Mb"] == 1
    assert not counts.index.str.startswith("1:het").any()
    saved = pd.read_csv(output / "fixture.CNV48.matrix.tsv", sep="\t")
    pd.testing.assert_frame_equal(matrix, saved)
