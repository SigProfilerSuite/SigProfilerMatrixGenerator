import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.web import genomes, jobs, runjob

REPO_ROOT = Path(__file__).resolve().parents[2]


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
        # The real return shape: a DataFrame per context written, None for
        # contexts with no mutations of that type.
        calls["generated"].append(kwargs)
        return {"96": pd.DataFrame({"S1": [1, 0]}), "DINUC": None,
                "INDEL": pd.DataFrame({"S1": [2]})}

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
        "plot": True,
    }

    runjob.run(config, result_path)

    assert stub_generator["installed"] == []
    assert stub_generator["generated"][0]["plot"] is True
    result = json.loads(result_path.read_text())
    assert result["status"] == "done"
    assert result["contexts"] == ["96", "INDEL"]


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

    def boom(config, result_path, since):
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


# Synthetic calls from the 2026-11-11 review: one substitution, one deletion
# and one insertion at chr1:1,000,001 of GRCh38. No patient data.
REVIEW_VCF = (
    "##fileformat=VCFv4.2\n"
    "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    "1\t1000001\t.\tG\tT\t.\tPASS\t.\n"
    "1\t1000001\t.\tGT\tG\t.\tPASS\t.\n"
    "1\t1000001\t.\tG\tGAC\t.\tPASS\t.\n"
)


def _matrix_total(path):
    return int(pd.read_csv(path, sep="\t", index_col=0).to_numpy().sum())


@pytest.mark.skipif(
    "GRCh38" not in genomes.installed_genomes(), reason="needs an installed GRCh38 reference"
)
def test_real_generation_through_the_job_runner_is_reported_done(tmp_path):
    # The path a browser run takes (JobManager, then runjob in its own
    # process, then the real generator), so the generator's real return
    # value reaches the summary step. A stubbed generator cannot catch that.
    calls = tmp_path / "calls"
    calls.mkdir()
    (calls / "review.vcf").write_text(REVIEW_VCF)
    output = tmp_path / "output"
    manager = jobs.JobManager(tmp_path / "jobs")
    meta = manager.start(
        {
            "project": "review",
            "reference_genome": "GRCh38",
            "path_to_input_files": str(calls),
            "output_directory": str(output),
            "indel_contexts": ["89", "476"],
            "install_genome_if_missing": False,
        },
        name="review",
        cwd=REPO_ROOT,
    )
    deadline = time.monotonic() + 600
    while manager.get(meta["id"])["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.5)

    job = manager.get(meta["id"])
    assert job["status"] == "done", manager.log(meta["id"])["text"][-3000:]
    assert _matrix_total(output / "SBS" / "review.SBS96.all") == 1
    assert _matrix_total(output / "ID" / "review.ID83.all") == 2
    assert _matrix_total(output / "ID" / "review.ID89.all") == 2
    assert _matrix_total(output / "ID" / "review.ID476.all") == 2


def _run_through_job_runner(tmp_path, config, timeout=600):
    manager = jobs.JobManager(tmp_path / "jobs")
    meta = manager.start(config, name=config["project"], cwd=REPO_ROOT)
    deadline = time.monotonic() + timeout
    while manager.get(meta["id"])["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.5)
    return manager, manager.get(meta["id"])


@pytest.mark.skipif(
    "GRCh38" not in genomes.installed_genomes(), reason="needs an installed GRCh38 reference"
)
def test_grch38_test_set_matches_its_expected_sbs96_and_draws_plots(tmp_path):
    # The web app's "GRCh38 test set" example: the bundled benchmark input,
    # checked against the expected SBS96 that ships beside it, with PDF plots.
    package = REPO_ROOT / "SigProfilerMatrixGenerator"
    output = tmp_path / "output"
    manager, job = _run_through_job_runner(tmp_path, {
        "project": "GRCh38_test",
        "reference_genome": "GRCh38",
        "path_to_input_files": str(package / "references" / "vcf_files" / "GRCh38_bench"),
        "output_directory": str(output),
        "plot": True,
        "install_genome_if_missing": False,
    })

    assert job["status"] == "done", manager.log(job["id"])["text"][-3000:]
    got = pd.read_csv(output / "SBS" / "GRCh38_test.SBS96.all", sep="\t", index_col=0)
    want = pd.read_csv(package / "scripts" / "Benchmark" / "GRCh38_bench_orig_96.txt",
                       sep="\t", index_col=0)
    pd.testing.assert_series_equal(got.iloc[:, 0].reindex(want.index), want.iloc[:, 0],
                                   check_names=False, check_dtype=False)
    assert (output / "plots" / "SBS_96_plots_GRCh38_test.pdf").is_file()
    # A run's own plots are drawn after its matrices: none may look stale.
    from SigProfilerMatrixGenerator.web import results

    plots = results.scan(str(output))["plots"]
    assert plots and not [p["name"] for p in plots if p.get("older_than_matrix")]


@pytest.mark.skipif(
    "GRCh38" not in genomes.installed_genomes(), reason="needs an installed GRCh38 reference"
)
def test_calls_on_the_wrong_genome_fail_with_the_skips_counted_by_reason(tmp_path):
    # The BRCA example's calls are GRCh37. Run against GRCh38, most reference
    # bases do not match and SigProfilerMatrixGenerator stops; the result must
    # say why, from its own log, which the run's output never shows.
    import shutil

    source = REPO_ROOT / "SigProfilerMatrixGenerator" / "references" / "vcf_files" / "BRCA_example" / "SNV"
    shutil.copytree(source, tmp_path / "calls")
    manager, job = _run_through_job_runner(tmp_path, {
        "project": "wrong_genome",
        "reference_genome": "GRCh38",
        "path_to_input_files": str(tmp_path / "calls"),
        "output_directory": str(tmp_path / "output"),
        "install_genome_if_missing": False,
    })

    assert job["status"] == "failed"
    assert "More than 30% of mutations were skipped" in job["error"]
    log_text = manager.log(job["id"])["text"]
    reported = int(re.search(r"with (\d+) errors", log_text).group(1))
    assert job["skipped_total"] == reported
    top = max(job["skipped"], key=job["skipped"].get)
    assert top == "The reference base does not match the reference genome"
    assert Path(job["generator_log"]).parent == tmp_path / "output" / "logs"


def _generator_log(folder, project, genome, lines, day="2026-11-11"):
    logs = folder / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    path = logs / f"SigProfilerMatrixGenerator_{project}_{genome}{day}.out"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_generator_log_summary_counts_skips_by_reason(tmp_path):
    path = _generator_log(tmp_path, "P", "GRCh38", [
        "Chromosome 1 done",
        "The reference base does not match the reference genome. Skipping this mutation: 1 10 A G",
        "The reference base does not match the reference genome. Skipping this mutation: 1 11 C T",
        "The position is out of range. Skipping this mutation: 1 999999999 C T",
    ])
    config = {"project": "P", "reference_genome": "GRCh38", "output_directory": str(tmp_path)}

    summary = runjob.generator_log_summary(config, since=0)

    assert summary == {
        "generator_log": str(path),
        "skipped": {
            "The reference base does not match the reference genome": 2,
            "The position is out of range": 1,
        },
        "skipped_total": 3,
    }


def test_generator_log_summary_ignores_logs_from_earlier_runs(tmp_path):
    path = _generator_log(tmp_path, "P", "GRCh38", ["x. Skipping this mutation: 1"])
    old = time.time() - 3600
    os.utime(path, (old, old))
    config = {"project": "P", "reference_genome": "GRCh38", "output_directory": str(tmp_path)}

    assert runjob.generator_log_summary(config, since=time.time() - 60) == {}


def test_generator_log_summary_ignores_other_projects_and_genomes(tmp_path):
    _generator_log(tmp_path, "P_other", "GRCh38", ["x. Skipping this mutation: 1"])
    _generator_log(tmp_path, "P", "GRCh37", ["x. Skipping this mutation: 1"])
    config = {"project": "P", "reference_genome": "GRCh38", "output_directory": str(tmp_path)}

    assert runjob.generator_log_summary(config, since=0) == {}


def test_failed_result_carries_the_skip_summary(tmp_path, monkeypatch):
    out = tmp_path / "out"
    _generator_log(out, "P", "GRCh38", ["Bad. Skipping this mutation: 1"])
    config = {"project": "P", "reference_genome": "GRCh38", "output_directory": str(out)}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))

    def boom(config, result_path, since):
        raise ValueError("Error: More than 30% of mutations were skipped.")

    monkeypatch.setattr(runjob, "run", boom)
    assert runjob.main([str(config_path)]) == 1
    result = json.loads((tmp_path / "result.json").read_text())
    assert result["status"] == "failed"
    assert result["skipped"] == {"Bad": 1}


def test_replacing_clears_earlier_results_before_generating(tmp_path, stub_generator):
    out = tmp_path / "out"
    (out / "plots").mkdir(parents=True)
    (out / "plots" / "SBS_6_plots_P.pdf").write_bytes(b"%PDF-1.4\n")
    (out / "plots" / "mine.pdf").write_bytes(b"%PDF-1.4\n")
    calls = tmp_path / "calls"
    calls.mkdir()
    config = {"project": "P", "reference_genome": "AlreadyInstalled",
              "path_to_input_files": str(calls), "output_directory": str(out),
              "replace_existing": True}

    runjob.run(config, tmp_path / "result.json")

    assert not (out / "plots" / "SBS_6_plots_P.pdf").exists()
    assert (out / "plots" / "mine.pdf").exists()
    assert stub_generator["generated"], "generation still ran"


def test_without_replacing_earlier_results_are_left_alone(tmp_path, stub_generator):
    out = tmp_path / "out"
    (out / "plots").mkdir(parents=True)
    (out / "plots" / "SBS_6_plots_P.pdf").write_bytes(b"%PDF-1.4\n")
    config = {"project": "P", "reference_genome": "AlreadyInstalled",
              "path_to_input_files": str(tmp_path), "output_directory": str(out)}

    runjob.run(config, tmp_path / "result.json")

    assert (out / "plots" / "SBS_6_plots_P.pdf").exists()
