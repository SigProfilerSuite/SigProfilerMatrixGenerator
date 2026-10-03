"""Opt-in regression tests requiring the full corrected CHM13 reference."""

import os
from pathlib import Path
import shutil

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
