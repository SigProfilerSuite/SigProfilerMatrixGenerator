import warnings

import numpy as np
import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import SVMatrixGenerator as sv


def deletion(chrom, left, sample):
    return dict(
        chrom1=chrom, start1=left, end1=left + 1,
        chrom2=chrom, start2=left + 100000, end2=left + 100001,
        sample=sample, svclass="deletion",
    )


@pytest.mark.parametrize("copy_on_write", [False, True])
def test_sv32_clustered_and_nonclustered_counts(tmp_path, monkeypatch, copy_on_write):
    source = tmp_path / "bedpe"
    source.mkdir()
    dense = pd.DataFrame([deletion("1", 100000 + i * 1000, "dense") for i in range(12)])
    sparse = pd.DataFrame([deletion(str(i + 2), 100000, "sparse") for i in range(3)])
    dense.to_csv(source / "dense.bedpe", sep="\t", index=False)
    sparse.to_csv(source / "sparse.bedpe", sep="\t", index=False)
    monkeypatch.setattr(sv.sigPlt, "plotSV", lambda *args, **kwargs: None)
    with pd.option_context("mode.copy_on_write", copy_on_write), warnings.catch_warnings():
        warnings.simplefilter("error", pd.errors.ChainedAssignmentError)
        matrix = sv.generateSVMatrix(str(source), "fixture", str(tmp_path / "output"))
    expected = pd.DataFrame(0, index=matrix.index, columns=matrix.columns)
    expected.at["clustered_del_10-100Kb", "dense"] = 11
    expected.at["non-clustered_del_10-100Kb", "dense"] = 1
    expected.at["non-clustered_del_10-100Kb", "sparse"] = 3
    pd.testing.assert_frame_equal(matrix, expected)
    saved = pd.read_csv(tmp_path / "output" / "fixture.SV32.matrix.tsv", sep="\t", index_col=0)
    pd.testing.assert_frame_equal(saved, expected)


@pytest.mark.parametrize("copy_on_write", [False, True])
def test_hotspot_info_updates_parent_and_length(copy_on_write):
    regions = pd.DataFrame({
        "firstBp": [0], "lastBp": [2], "start_bp": [np.nan],
        "end_bp": [np.nan], "length_bp": [np.nan], "avgDist_bp": [np.nan],
    })
    subs = pd.DataFrame({"pos": [100, 200, 300], "sample": ["one"] * 3})
    with pd.option_context("mode.copy_on_write", copy_on_write):
        result = sv.hotspotInfo2(regions, subs, np.array([10.0, 20.0, 30.0]))
    assert result.at[0, "start_bp"] == 100
    assert result.at[0, "end_bp"] == 300
    assert result.at[0, "length_bp"] == 200
    assert result.at[0, "number_bps"] == 3
    assert result.at[0, "no_samples"] == 1
    assert result.at[0, "avgDist_bp"] == 20


@pytest.mark.parametrize("copy_on_write", [False, True])
def test_adjacent_hotspots_merge(copy_on_write):
    subs = pd.DataFrame({
        "chr": ["1"] * 20, "pos": np.arange(20) * 1000,
        "sample": ["one"] * 20,
    })
    with pd.option_context("mode.copy_on_write", copy_on_write):
        result = sv.extract_kat_regions(
            {"yhat": np.array([10.0] * 10 + [20.0] * 10)},
            100, subs, 1, 1, 0, True, 10, np.nan,
        )
    assert len(result) == 1
    assert result.iloc[0]["firstBp"] == 0
    assert result.iloc[0]["lastBp"] == 19
    assert result.iloc[0]["length_bp"] == 19000
    assert result.iloc[0]["number_bps"] == 20
