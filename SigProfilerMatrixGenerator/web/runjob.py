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


def run(config: dict, result_path: Path) -> None:
    if config.get("install_only"):
        return _run_install_only(config, result_path)

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
        tsb_stat=config.get("tsb_stat", False),
        volume=volume,
        output_directory=config.get("output_directory"),
        indel_contexts=config.get("indel_contexts"),
    )

    _step(3, "writing result summary")
    contexts = sorted(name for name, value in (matrices or {}).items() if value)
    _write_result_atomic(
        result_path,
        {
            "status": "done",
            "contexts": contexts,
            "elapsed_seconds": round(time.monotonic() - started, 2),
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
    try:
        run(config, result_path)
    except Exception as exc:  # noqa: BLE001 -- job boundary, must always report back
        traceback.print_exc()
        _write_result_atomic(
            result_path,
            {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
