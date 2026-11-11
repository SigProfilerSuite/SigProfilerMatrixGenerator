"""Subprocess entry point for one matrix-generation run.

Invoked as ``python -m SigProfilerMatrixGenerator.web.runjob <config.json>``
by jobs.py, in its own process so a long run never blocks the dashboard
server and a crash in it never takes the server down. Progress is the
"== step N/M: ..." lines this module prints to its own stdout (redirected by
the caller to the job's log file) -- not instrumentation added to the
matrix-generation code itself, which stays untouched.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

TOTAL_STEPS = 3


def _step(n: int, message: str) -> None:
    print(f"== step {n}/{TOTAL_STEPS}: {message}", flush=True)


def _write_result_atomic(result_path: Path, result: dict) -> None:
    tmp = result_path.with_name(result_path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.replace(tmp, result_path)


def output_dir_for(config: dict) -> Path:
    # Mirrors SigProfilerMatrixGeneratorFunc: matrices go straight into
    # output_directory when one is given, otherwise into <input>/output/.
    if config.get("output_directory"):
        return Path(config["output_directory"])
    return Path(config["path_to_input_files"]) / "output"


_SKIP_MARKER = " Skipping this mutation"


def generator_log_summary(config: dict, since: float) -> dict:
    """Where SigProfilerMatrixGenerator's own log is, and what it skipped and why.

    Per-mutation reasons go only to that log (logs/*.out), not to stdout.
    Only a log written during this run counts, so a failure before the
    generator started never reports an older run's log.
    """
    try:
        logs = output_dir_for(config) / "logs"
        name = re.compile(
            rf"SigProfilerMatrixGenerator_{re.escape(config['project'])}_"
            rf"{re.escape(config['reference_genome'])}\d{{4}}-\d{{2}}-\d{{2}}\.out"
        )
        candidates = [
            p for p in logs.iterdir()
            if name.fullmatch(p.name) and p.stat().st_mtime >= since
        ]
    except (KeyError, OSError):
        return {}
    if not candidates:
        return {}
    log_file = max(candidates, key=lambda p: p.stat().st_mtime)
    reasons: dict[str, int] = {}
    with open(log_file, "r", errors="replace") as handle:
        for line in handle:
            cut = line.find(_SKIP_MARKER)
            if cut > 0:
                reason = line[:cut].strip().rstrip(".")
                reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "generator_log": str(log_file),
        "skipped": reasons,
        "skipped_total": sum(reasons.values()),
    }


def _run_install_only(config: dict, result_path: Path) -> None:
    from SigProfilerMatrixGenerator.web import genomes

    started = time.monotonic()
    reference_genome = config["reference_genome"]
    print(f"Installing genome {reference_genome}...", flush=True)
    genomes.install(
        reference_genome,
        volume=config.get("volume"),
        local_genome_dir=config.get("local_genome_dir"),
    )
    _write_result_atomic(
        result_path,
        {
            "status": "done",
            "installed": reference_genome,
            "elapsed_seconds": round(time.monotonic() - started, 2),
        },
    )
    print("Done.", flush=True)


def run(config: dict, result_path: Path, since: float | None = None) -> None:
    if config.get("install_only"):
        return _run_install_only(config, result_path)
    # Wall-clock start (a second early, for coarse file timestamps), to tell
    # this run's generator log from an older one.
    since = time.time() - 1 if since is None else since

    from SigProfilerMatrixGenerator.scripts import reference_genome_manager
    from SigProfilerMatrixGenerator.scripts.SigProfilerMatrixGeneratorFunc import (
        SigProfilerMatrixGeneratorFunc,
    )
    from SigProfilerMatrixGenerator.web import genomes

    started = time.monotonic()
    reference_genome = config["reference_genome"]
    volume = config.get("volume")

    _step(1, f"checking reference genome {reference_genome}")
    manager = reference_genome_manager.ReferenceGenomeManager(volume)
    if not manager.is_genome_installed(reference_genome):
        if not config.get("install_genome_if_missing"):
            raise reference_genome_manager.ReferenceInstallationError(
                manager.installation_error_message(reference_genome)
            )
        print(f"Installing genome {reference_genome}...", flush=True)
        genomes.install(reference_genome, volume=volume)

    _step(2, "generating matrices")
    matrices = SigProfilerMatrixGeneratorFunc(
        project=config["project"],
        reference_genome=reference_genome,
        path_to_input_files=config["path_to_input_files"],
        exome=config.get("exome", False),
        bed_file=config.get("bed_file"),
        plot=config.get("plot", False),
        tsb_stat=config.get("tsb_stat", False),
        volume=volume,
        output_directory=config.get("output_directory"),
        indel_contexts=config.get("indel_contexts"),
    )

    _step(3, "writing result summary")
    # The values are pandas DataFrames (None for contexts with no mutations);
    # a DataFrame has no truth value, so test for None explicitly.
    contexts = sorted(name for name, value in (matrices or {}).items() if value is not None)
    _write_result_atomic(
        result_path,
        {
            "status": "done",
            "contexts": contexts,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            **generator_log_summary(config, since),
        },
    )
    print(
        f"Done. Elapsed time: {round(time.monotonic() - started, 2)} seconds.",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: runjob.py <config.json>", file=sys.stderr)
        return 2
    config_path = Path(argv[0])
    config = json.loads(config_path.read_text(encoding="utf-8"))
    result_path = config_path.with_name("result.json")
    since = time.time() - 1
    try:
        run(config, result_path, since)
    except Exception as exc:  # noqa: BLE001 -- job boundary, must always report back
        traceback.print_exc()
        _write_result_atomic(
            result_path,
            {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                **generator_log_summary(config, since),
            },
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
