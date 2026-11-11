"""Scan a SigProfilerMatrixGenerator output folder and render its matrices.

Rendering is delegated to sigProfilerPlotting.web (matrix.load_matrix /
renderers.render_sample) rather than reimplemented here, per the context-
specific plotting logic (SBS4608 multi-panel layout, ID89/ID476 grouping,
COSMIC comparison, ...) that already lives there. sigProfilerPlotting is an
optional dependency (the "web" extra): when it is not installed, results can
still be listed and downloaded, just not rendered inline.
"""

from __future__ import annotations

import re
from pathlib import Path

CONTEXT_SUBDIRS = ("SBS", "DBS", "ID", "SV", "CNV")

# <project>.<CONTEXT><digits>.<suffix...>, e.g. "MySamples.SBS96.all" or
# "MySamples.ID83.exome.chr1" -- see MutationMatrixGenerator.py's
# file_prefix/output_file_matrix construction.
_MATRIX_NAME = re.compile(r"^(?P<project>.+)\.(?P<context>[A-Z]+\d+)(?:\..+)?$")


class ResultsError(ValueError):
    pass


def plotting_available() -> bool:
    try:
        import sigProfilerPlotting.web.matrix  # noqa: F401
    except ImportError:
        return False
    return True


def scan(output_dir: str) -> dict:
    """List matrix files under ``output_dir``, grouped by context."""
    root = Path(output_dir)
    if not root.is_dir():
        raise ResultsError(f"not a directory: {output_dir}")

    contexts: dict[str, list[dict]] = {}
    for subdir in CONTEXT_SUBDIRS:
        folder = root / subdir
        if not folder.is_dir():
            continue
        for file in sorted(folder.iterdir()):
            if not file.is_file():
                continue
            match = _MATRIX_NAME.match(file.name)
            if not match:
                continue
            context = match.group("context")
            stat = file.stat()
            contexts.setdefault(context, []).append(
                {
                    "path": str(file),
                    "name": file.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    # PDF figures SigProfilerPlotting wrote when the run asked for plots.
    plots_dir = root / "plots"
    plots = [
        {"path": str(file), "name": file.name, "size": file.stat().st_size}
        for file in (sorted(plots_dir.iterdir()) if plots_dir.is_dir() else [])
        if file.is_file() and file.suffix.lower() == ".pdf"
    ]
    return {
        "output_dir": str(root),
        "contexts": contexts,
        "plots": plots,
        "plotting_available": plotting_available(),
    }


def load(matrix_path: str) -> dict:
    """Load a matrix file's samples and context, without rendering it."""
    from sigProfilerPlotting.web import matrix as plotting_matrix

    try:
        data = plotting_matrix.load_matrix(matrix_path)
    except plotting_matrix.MatrixError as exc:
        # Re-raised as our own domain error so callers (server.py's route
        # dispatch) only ever need to know about this module's exception
        # types, not sigProfilerPlotting's.
        raise ResultsError(str(exc)) from exc
    return {"context": data.context, "samples": list(data.columns)}


def render(matrix_path: str, sample: str, unit: str = "counts", compare_cosmic: str | None = None) -> dict:
    """Render one sample from a matrix file as Plotly JSON."""
    from sigProfilerPlotting.web import matrix as plotting_matrix, renderers

    try:
        data = plotting_matrix.load_matrix(matrix_path)
        return renderers.render_sample(data, sample, unit=unit, compare_cosmic=compare_cosmic)
    except plotting_matrix.MatrixError as exc:
        raise ResultsError(str(exc)) from exc
