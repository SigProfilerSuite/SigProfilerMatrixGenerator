import json

import pytest

from SigProfilerMatrixGenerator.web import runjob


@pytest.fixture
def stub_generator(monkeypatch):
    """Replace the real genome manager and matrix generator with stubs."""
    calls = {"installed": [], "generated": []}

    class StubManager:
        def __init__(self, volume):
            self.volume = volume

        def is_genome_installed(self, name):
            return name == "AlreadyInstalled"

        def installation_error_message(self, name):
            return f"{name} is not installed"

    def stub_generator_func(**kwargs):
        calls["generated"].append(kwargs)
        return {"96": {"S1": {}}, "ID": None}

    def stub_install(genome_name, volume=None, local_genome_dir=None):
        calls["installed"].append(genome_name)

    import SigProfilerMatrixGenerator.scripts.reference_genome_manager as real_rgm

    monkeypatch.setattr(real_rgm, "ReferenceGenomeManager", StubManager)

    import SigProfilerMatrixGenerator.scripts.SigProfilerMatrixGeneratorFunc as real_mg

    monkeypatch.setattr(real_mg, "SigProfilerMatrixGeneratorFunc", stub_generator_func)

    from SigProfilerMatrixGenerator.web import genomes

    monkeypatch.setattr(genomes, "install", stub_install)

    return calls


def test_run_skips_install_when_genome_already_installed(tmp_path, stub_generator):
    result_path = tmp_path / "result.json"
    config = {
        "project": "MyProject",
        "reference_genome": "AlreadyInstalled",
        "path_to_input_files": str(tmp_path),
        "install_genome_if_missing": True,
    }

    runjob.run(config, result_path)

    assert stub_generator["installed"] == []
    result = json.loads(result_path.read_text())
    assert result["status"] == "done"
    assert result["contexts"] == ["96"]


def test_run_installs_missing_genome_when_allowed(tmp_path, stub_generator):
    result_path = tmp_path / "result.json"
    config = {
        "project": "MyProject",
        "reference_genome": "NotInstalledYet",
        "path_to_input_files": str(tmp_path),
        "install_genome_if_missing": True,
    }

    runjob.run(config, result_path)

    assert stub_generator["installed"] == ["NotInstalledYet"]
    result = json.loads(result_path.read_text())
    assert result["status"] == "done"


def test_run_raises_when_genome_missing_and_install_not_allowed(tmp_path, stub_generator):
    import SigProfilerMatrixGenerator.scripts.reference_genome_manager as real_rgm

    config = {
        "project": "MyProject",
        "reference_genome": "NotInstalledYet",
        "path_to_input_files": str(tmp_path),
        "install_genome_if_missing": False,
    }

    with pytest.raises(real_rgm.ReferenceInstallationError):
        runjob.run(config, tmp_path / "result.json")
    assert stub_generator["installed"] == []


def test_main_writes_failed_result_on_exception(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"reference_genome": "X", "project": "P", "path_to_input_files": "/nope"}))

    def boom(config, result_path):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(runjob, "run", boom)

    exit_code = runjob.main([str(config_path)])

    assert exit_code == 1
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == "failed"
    assert "kaboom" in result["error"]


def test_run_install_only_skips_matrix_generation(tmp_path, stub_generator):
    result_path = tmp_path / "result.json"
    config = {"reference_genome": "NotInstalledYet", "install_only": True}

    runjob.run(config, result_path)

    assert stub_generator["installed"] == ["NotInstalledYet"]
    assert stub_generator["generated"] == []
    result = json.loads(result_path.read_text())
    assert result["status"] == "done"
    assert result["installed"] == "NotInstalledYet"


def test_main_requires_exactly_one_argument():
    assert runjob.main([]) == 2
    assert runjob.main(["a", "b"]) == 2
