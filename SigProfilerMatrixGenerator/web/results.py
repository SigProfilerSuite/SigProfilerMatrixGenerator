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
import shutil
from pathlib import Path

CONTEXT_SUBDIRS = ("SBS", "DBS", "ID", "SV", "CNV")

# <project>.<CONTEXT><digits>.<suffix...>, e.g. "MySamples.SBS96.all" or
# "MySamples.ID83.exome.chr1" -- see MutationMatrixGenerator.py's
# file_prefix/output_file_matrix construction.
_MATRIX_NAME = re.compile(r"^(?P<project>.+)\.(?P<context>[A-Z]+\d+)(?:\..+)?$")


class ResultsError(ValueError):
    pass


# What SigProfilerMatrixGenerator writes into an output folder, by subfolder,
# matched by the names it gives them. Replacing earlier results removes only
# these, so a folder that happens to share a name ("input", "logs", "plots")
# keeps anything else it holds.
_UUID_TAIL = re.compile(r"^.+_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_GENERATED_FILES = {
    "SBS": re.compile(r"^.+\.SBS\d+(\..+)?$"),
    "DBS": re.compile(r"^.+\.DBS\d+(\..+)?$"),
    "ID": re.compile(r"^.+\.ID\d+(_ID\d+)?(\..+)?$"),
    "TSB": re.compile(r"^(significantResults_strandBiasTest|strandBiasTest_\d+)\.txt$"),
    "plots": re.compile(r"^[A-Z]+_\d+_plots_.+\.pdf$"),
    "logs": re.compile(r"^SigProfilerMatrixGenerator_.+\.(out|err)$"),
    "vcf_files/SNV": re.compile(r"^.+_seqinfo\.txt$"),
    "vcf_files/DBS": re.compile(r"^.+_seqinfo\.txt$"),
    "vcf_files/MNS": re.compile(r"^.+_seqinfo\.txt$"),
    "vcf_files/ID": re.compile(r"^.+_seqinfo\.txt$"),
}
# Its copy of each run's input calls, and its scratch space: one folder per
# run, named <project>_<uuid4>.
_GENERATED_DIRS = ("input", "temp")
# What counts as results, as opposed to logs and scratch.
RESULT_FOLDERS = ("SBS", "DBS", "ID", "TSB", "plots")


def _real_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def _generated_in(root: Path) -> list[Path]:
    found = []
    for sub, pattern in _GENERATED_FILES.items():
        folder = root / sub
        if _real_dir(folder):
            found += [p for p in sorted(folder.iterdir())
                      if not p.is_dir() and pattern.match(p.name)]
    for sub in _GENERATED_DIRS:
        folder = root / sub
        if _real_dir(folder):
            found += [p for p in sorted(folder.iterdir())
                      if _real_dir(p) and _UUID_TAIL.match(p.name)]
    return found


def earlier_results(output_dir: str) -> dict:
    """Which result folders an earlier run left in ``output_dir``, if any."""
    root = Path(output_dir).expanduser()
    if not _real_dir(root):
        return {"found": False, "folders": []}
    folders = {p.parent.name for p in _generated_in(root) if p.parent.parent == root}
    shown = [name for name in RESULT_FOLDERS if name in folders]
    return {"found": bool(shown), "folders": shown}


def next_free_folder(output_dir: str) -> str:
    """A sibling of ``output_dir`` holding no results: name_2, name_3, ..."""
    root = Path(output_dir).expanduser()
    numbered = re.fullmatch(r"(.+)_(\d+)", root.name)
    base, n = (numbered.group(1), int(numbered.group(2)) + 1) if numbered else (root.name, 2)
    while earlier_results(str(root.with_name(f"{base}_{n}")))["found"]:
        n += 1
    return str(root.with_name(f"{base}_{n}"))


def replace_problem(output_dir: str, input_dir: str) -> str | None:
    """Why earlier results in ``output_dir`` must not be removed, or None."""
    root = Path(output_dir).expanduser().resolve()
    calls = Path(input_dir).expanduser().resolve()
    if calls == root or root in calls.parents:
        return ("The input calls are inside this output folder, so its earlier results "
                "are not removed automatically. Choose a different output folder.")
    return None


def clear_earlier_results(output_dir: str, input_dir: str) -> list[str]:
    """Remove what SigProfilerMatrixGenerator wrote into ``output_dir`` before.

    Only files and folders it names its own way are removed (see
    _GENERATED_FILES); everything else in the folder stays. Returns the
    removed paths, relative to ``output_dir``.
    """
    problem = replace_problem(output_dir, input_dir)
    if problem:
        raise ResultsError(problem)
    root = Path(output_dir).expanduser()
    if not _real_dir(root):
        return []
    removed = []
    for path in _generated_in(root):
        if _real_dir(path):
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(str(path.relative_to(root)))
    # Folders left empty by that, deepest first; a folder holding anything
    # else is kept.
    for sub in sorted({*_GENERATED_FILES, *_GENERATED_DIRS, "vcf_files"}, key=len, reverse=True):
        folder = root / sub
        if _real_dir(folder):
            try:
                folder.rmdir()
            except OSError:
                pass
    return removed


def generated_size(output_dir: str) -> dict:
    """How many files, and bytes, clear_earlier_results() would remove."""
    root = Path(output_dir).expanduser()
    files = size = 0
    if _real_dir(root):
        for path in _generated_in(root):
            walk = [p for p in path.rglob("*") if p.is_file()] if _real_dir(path) else [path]
            for f in walk:
                files += 1
                try:
                    size += f.lstat().st_size
                except OSError:
                    pass
    return {"files": files, "bytes": size}


def delete_output(output_dir: str, input_dir: str) -> list[str]:
    """Delete a run's results: what clear_earlier_results() removes, and the
    output folder itself if nothing else is left in it."""
    removed = clear_earlier_results(output_dir, input_dir)
    root = Path(output_dir).expanduser()
    if _real_dir(root):
        try:
            root.rmdir()
        except OSError:
            pass  # it holds other files: they stay
    return removed


def _has_counts(path: Path) -> bool:
    """Whether a matrix file holds any non-zero count (stops at the first)."""
    with open(path, "r", errors="replace") as handle:
        next(handle, None)  # header: MutationType, then the samples
        for line in handle:
            for value in line.rstrip("\n").split("\t")[1:]:
                try:
                    if float(value) != 0:
                        return True
                except ValueError:
                    continue
    return False


# SigProfilerPlotting names its PDFs <TYPE>_<channels>_plots_<project>.pdf.
_PLOT_NAME = re.compile(r"^(?P<family>[A-Z]+)_(?P<channels>\d+)_plots_(?P<project>.+)\.pdf$")
# A plot is drawn after its matrix is written, in the same run; allow for
# coarse file-system timestamps.
_CLOCK_SLACK = 2.0


def plotting_available() -> bool:
    try:
        import sigProfilerPlotting.web.matrix  # noqa: F401
    except ImportError:
        return False
    return True


def scan(output_dir: str) -> dict:
    """List matrix files and PDF plots under ``output_dir``.

    Matrices are grouped by context and say whether they hold any counts.
    Plots say which matrix they show and whether they are older than it,
    which means an earlier run drew them.
    """
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
                    "project": match.group("project"),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "empty": not _has_counts(file),
                }
            )
    # PDF figures SigProfilerPlotting wrote when the run asked for plots.
    plots_dir = root / "plots"
    plots = []
    for file in (sorted(plots_dir.iterdir()) if plots_dir.is_dir() else []):
        if not (file.is_file() and file.suffix.lower() == ".pdf"):
            continue
        stat = file.stat()
        plot = {"path": str(file), "name": file.name, "size": stat.st_size, "modified": stat.st_mtime}
        named = _PLOT_NAME.match(file.name)
        if named:
            plot["context"] = named.group("family") + named.group("channels")
            matrices = [m for m in contexts.get(plot["context"], [])
                        if m["project"] == named.group("project")]
            plot["older_than_matrix"] = bool(matrices) and (
                stat.st_mtime + _CLOCK_SLACK < max(m["modified"] for m in matrices))
        plots.append(plot)
    return {
        "output_dir": str(root),
        "contexts": contexts,
        "plots": plots,
        "plotting_available": plotting_available(),
    }


def newest_file_time(scanned: dict) -> float | None:
    times = [f["modified"] for files in scanned["contexts"].values() for f in files]
    times += [p["modified"] for p in scanned["plots"]]
    return max(times) if times else None


def mark_earlier(scanned: dict, since: float) -> dict:
    """Flag matrices and plots written before ``since``: an earlier run's."""
    for files in scanned["contexts"].values():
        for f in files:
            f["earlier"] = f["modified"] + _CLOCK_SLACK < since
    for p in scanned["plots"]:
        p["earlier"] = p["modified"] + _CLOCK_SLACK < since
    return scanned


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
        response = renderers.render_sample(data, sample, unit=unit, compare_cosmic=compare_cosmic)
    except plotting_matrix.MatrixError as exc:
        raise ResultsError(str(exc)) from exc
    if data.context == "DBS1248" and response.get("kind") == "standard":
        response["figure"] = regroup_flanked_dbs(response["figure"], getattr(renderers, "PALETTE", None))
    return response


# DBS1248 is DBS78 with a flanking base on each side: A[AC>CA]T.
_FLANKED_DBS = re.compile(r"^([ACGT])\[(([ACGT]{2})>[ACGT]{2})\]([ACGT])$")


def regroup_flanked_dbs(figure: dict, palette: list[str] | None = None) -> dict:
    """Group a DBS1248 chart by reference dinucleotide, as the DBS78 chart is.

    SigProfilerPlotting 1.5.0 has no DBS1248 renderer; its generic one groups
    A[AC>CA]T by "A[AC" (5' flank plus reference), which gives 40 legend
    entries and colors that mean nothing. Here the bars are regrouped into the
    10 reference dinucleotides, colored as DBS78 colors them, and ordered DBS78
    channel by channel, each followed by its 16 flanking contexts. It steps
    aside on its own for a SigProfilerPlotting that draws DBS1248 itself, and
    can be deleted once the minimum required version does.
    """
    traces = figure.get("traces") or []
    if traces and all(re.fullmatch(r"[ACGT]{2}", str(trace.get("name", ""))) for trace in traces):
        # Already grouped by reference dinucleotide: a SigProfilerPlotting
        # with its own DBS1248 renderer. Its colors and order stand.
        return figure
    bars = [(x, y) for trace in traces for x, y in zip(trace.get("x", []), trace.get("y", []))]
    parsed = [(_FLANKED_DBS.match(str(x)), x, y) for x, y in bars]
    if not parsed or not all(match for match, _, _ in parsed):
        return figure  # not the labels this was written for: leave it alone
    channel_order: dict[str, int] = {}
    reference_order: dict[str, int] = {}
    for match, _, _ in parsed:
        channel_order.setdefault(match.group(2), len(channel_order))
        reference_order.setdefault(match.group(3), len(reference_order))
    parsed.sort(key=lambda item: (channel_order[item[0].group(2)], item[0].group(1), item[0].group(4)))

    palette = palette or [trace.get("marker", {}).get("color", "#4C78A8") for trace in traces]
    template = traces[0].get("hovertemplate", "%{x}: %{y}")
    grouped: dict[str, tuple[list, list]] = {}
    for match, x, y in parsed:
        xs, ys = grouped.setdefault(match.group(3), ([], []))
        xs.append(x)
        ys.append(y)
    figure["traces"] = [
        {
            "type": "bar", "name": reference, "x": xs, "y": ys,
            "marker": {"color": palette[index % len(palette)]},
            "hovertemplate": re.sub(r"<extra>.*</extra>", f"<extra>{reference}</extra>", template),
        }
        for index, (reference, (xs, ys)) in enumerate(
            sorted(grouped.items(), key=lambda item: reference_order[item[0]]))
    ]
    # 1,248 bars: no gap between them, or they thin to hairlines.
    figure.setdefault("layout", {})["bargap"] = 0
    return figure
