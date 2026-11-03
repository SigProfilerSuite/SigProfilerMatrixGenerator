"""Opt-in regression tests requiring the full corrected CHM13 reference."""

import os
from pathlib import Path
import shutil

import pandas as pd
import pytest

from SigProfilerMatrixGenerator import test_helpers
from SigProfilerMatrixGenerator.scripts.SigProfilerMatrixGeneratorFunc import (
    SigProfilerMatrixGeneratorFunc,
)


REFERENCE_VOLUME = os.environ.get("SPMG_CHM13_REFERENCE_VOLUME")


@pytest.mark.parametrize(
    "exome,bed_file",
    [(False, False), (True, False), (False, True)],
    ids=["WGS", "WES", "BED"],
)
def test_corrected_chm13_reference_matches_regression_matrices(
    tmp_path, exome, bed_file
):
    if not REFERENCE_VOLUME:
        pytest.skip("set SPMG_CHM13_REFERENCE_VOLUME to a corrected CHM13 install")

    mode = "WES" if exome else "bed_file" if bed_file else "WGS"
    source = Path(test_helpers.TEST_INPUT_DIR) / mode / "CHM13-T2T"
    solution = Path(test_helpers.TEST_INPUT_DIR) / mode / "solutions" / "CHM13-T2T"
    interval_list = None
    if bed_file:
        interval_list = tmp_path / "CHM13-T2T_exome.interval_list"
        shutil.copyfile(
            Path(test_helpers.BED_FILE_DIR)
            / "CHM13-T2T"
            / "CHM13-T2T_exome.interval_list",
            interval_list,
        )

    matrices = SigProfilerMatrixGeneratorFunc(
        test_helpers.FILE_PREF,
        "CHM13-T2T",
        str(source),
        volume=REFERENCE_VOLUME,
        exome=exome,
        bed_file=str(interval_list) if interval_list else None,
        output_directory=str(tmp_path / mode),
        plot=False,
        chrom_based=False,
        tsb_stat=False,
        seqInfo=False,
        cushion=100,
    )
    test_helpers.load_and_compare(
        matrices,
        str(solution),
        exome=exome,
        bed_file=bed_file,
    )


def test_corrected_chm13_demo_with_tsb_statistics(tmp_path, monkeypatch):
    if not REFERENCE_VOLUME:
        pytest.skip("set SPMG_CHM13_REFERENCE_VOLUME to a corrected CHM13 install")

    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    source = (
        Path(__file__).resolve().parents[1]
        / "docs/assets/examples/chm13/mixed_variant_inputs"
    )
    inputs = tmp_path / "inputs"
    shutil.copytree(source, inputs)
    results = []
    for enabled in (False, True):
        results.append(
            SigProfilerMatrixGeneratorFunc(
                "chm13_tsb_demo",
                "CHM13-T2T",
                str(inputs),
                volume=REFERENCE_VOLUME,
                output_directory=str(tmp_path / str(enabled)),
                plot=False,
                seqInfo=False,
                tsb_stat=enabled,
                indel_contexts=("89", "476"),
            )
        )
    baseline, statistics = results
    for context, expected in baseline.items():
        if isinstance(expected, pd.DataFrame):
            pd.testing.assert_frame_equal(statistics[context], expected)
        else:
            assert statistics[context] is expected
    assert statistics["96"]["sbs"].sum() == 1
    assert statistics["DINUC"]["dbs"].sum() == 1
    assert statistics["ID"]["indel"].sum() == 2
    for directory in ("SBS", "DBS", "ID"):
        for path in (tmp_path / "False" / directory).glob("*"):
            assert (
                path.read_bytes()
                == (tmp_path / "True" / directory / path.name).read_bytes()
            )
    for context in ("6144", "384", "24"):
        report = tmp_path / "True" / "TSB" / f"strandBiasTest_{context}.txt"
        assert report.is_file() and report.stat().st_size > 0
