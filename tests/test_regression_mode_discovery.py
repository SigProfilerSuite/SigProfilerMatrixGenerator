import runpy
from pathlib import Path
from unittest import mock

import pytest

from SigProfilerMatrixGenerator import test_helpers


def test_missing_fixtures_do_not_raise_during_discovery(tmp_path, monkeypatch):
    monkeypatch.setattr(test_helpers, "TEST_INPUT_DIR", str(tmp_path))
    assert test_helpers.available_test_modes("new_genome") == []


def test_missing_fixtures_fail_explicit_test_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(test_helpers, "TEST_INPUT_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="new_genome"):
        test_helpers.run_all_modes_for_genome("new_genome")


def test_partial_fixture_discovery_requires_inputs_and_solutions(tmp_path, monkeypatch):
    monkeypatch.setattr(test_helpers, "TEST_INPUT_DIR", str(tmp_path))
    (tmp_path / "WGS/new_genome").mkdir(parents=True)
    assert test_helpers.available_test_modes("new_genome") == []
    (tmp_path / "WGS/solutions/new_genome").mkdir(parents=True)
    assert test_helpers.available_test_modes("new_genome") == [(False, False)]


def test_controller_module_loads_without_any_regression_fixtures():
    path = Path(__file__).parent / "controllers/test_cli_controller.py"
    with mock.patch.object(test_helpers.os.path, "isdir", return_value=False):
        module = runpy.run_path(str(path))
    assert len(module["TestController"].genome_calls) == 4


def test_available_modes_are_forwarded_with_volume(tmp_path, monkeypatch):
    monkeypatch.setattr(test_helpers, "TEST_INPUT_DIR", str(tmp_path))
    for directory in ("WGS", "WES", "bed_file"):
        (tmp_path / directory / "new_genome").mkdir(parents=True)
        (tmp_path / directory / "solutions/new_genome").mkdir(parents=True)
    run = mock.Mock()
    monkeypatch.setattr(test_helpers, "test_one_genome", run)
    test_helpers.run_all_modes_for_genome("new_genome", volume="my-volume")
    assert run.call_args_list == [
        mock.call("new_genome", volume="my-volume", exome=False, bed_file=False),
        mock.call("new_genome", volume="my-volume", exome=True, bed_file=False),
        mock.call("new_genome", volume="my-volume", exome=False, bed_file=True),
    ]
