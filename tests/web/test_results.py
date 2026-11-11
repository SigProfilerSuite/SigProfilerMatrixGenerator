import pytest

from SigProfilerMatrixGenerator.web import results


def _sbs96_labels():
    from sigProfilerPlotting.web.matrix import REFERENCE_CONTEXTS

    return list(REFERENCE_CONTEXTS["SBS96"])


@pytest.fixture
def plotting_web():
    # sigProfilerPlotting.web first shipped in SigProfilerPlotting 1.5.0.
    pytest.importorskip("sigProfilerPlotting.web.renderers")


def _write_sbs96_matrix(path, samples, labels=None):
    labels = labels if labels is not None else [f"row{i}" for i in range(96)]
    lines = ["MutationType\t" + "\t".join(samples)]
    for i, label in enumerate(labels):
        lines.append(label + "\t" + "\t".join(str(i + 1) for _ in samples))
    path.write_text("\n".join(lines) + "\n")


def test_scan_finds_matrix_files_grouped_by_context(tmp_path):
    (tmp_path / "SBS").mkdir()
    (tmp_path / "ID").mkdir()
    _write_sbs96_matrix(tmp_path / "SBS" / "MyProject.SBS96.all", ["S1", "S2"])
    (tmp_path / "ID" / "MyProject.ID83.all").write_text("MutationType\tS1\n1:Del:C:0\t1\n")
    (tmp_path / "SBS" / "notes.txt").write_text("not a matrix")

    result = results.scan(str(tmp_path))

    assert set(result["contexts"]) == {"SBS96", "ID83"}
    assert result["contexts"]["SBS96"][0]["name"] == "MyProject.SBS96.all"


def test_scan_rejects_missing_directory(tmp_path):
    with pytest.raises(results.ResultsError):
        results.scan(str(tmp_path / "nope"))


def test_scan_ignores_contexts_with_no_matrix_files(tmp_path):
    (tmp_path / "SBS").mkdir()
    result = results.scan(str(tmp_path))
    assert result["contexts"] == {}


def test_load_reports_context_and_samples(tmp_path, plotting_web):
    matrix_path = tmp_path / "MyProject.SBS96.all"
    _write_sbs96_matrix(matrix_path, ["S1", "S2"], labels=_sbs96_labels())

    loaded = results.load(str(matrix_path))

    assert loaded["context"] == "SBS96"
    assert loaded["samples"] == ["S1", "S2"]


def test_render_returns_a_plotly_figure(tmp_path, plotting_web):
    # A contract test against sigProfilerPlotting.web.renderers' return
    # shape: app.js calls Plotly.react(node, figure.traces, figure.layout,
    # figure.config), so a change to those keys on SigProfilerPlotting's side
    # should fail here, not only in the browser.
    matrix_path = tmp_path / "MyProject.SBS96.all"
    _write_sbs96_matrix(matrix_path, ["S1"], labels=_sbs96_labels())

    response = results.render(str(matrix_path), "S1")

    assert response["kind"] == "standard"
    assert response["figure"]["traces"]
    assert "layout" in response["figure"]
    assert "config" in response["figure"]


def test_render_with_invalid_unit_raises_results_error_not_matrix_error(tmp_path, plotting_web):
    # render_sample() raises sigProfilerPlotting.web.matrix.MatrixError for
    # this, a third-party exception type the server's route dispatch
    # shouldn't need to know about -- it must surface here as our own
    # ResultsError instead.
    matrix_path = tmp_path / "MyProject.SBS96.all"
    _write_sbs96_matrix(matrix_path, ["S1"], labels=_sbs96_labels())

    with pytest.raises(results.ResultsError):
        results.render(str(matrix_path), "S1", unit="not-a-real-unit")


def test_load_with_malformed_matrix_raises_results_error(tmp_path, plotting_web):
    matrix_path = tmp_path / "MyProject.broken.all"
    matrix_path.write_text("MutationType\tS1\nnot-a-real-context\t1\n")

    with pytest.raises(results.ResultsError):
        results.load(str(matrix_path))


def test_scan_lists_pdf_plots(tmp_path):
    (tmp_path / "SBS").mkdir()
    (tmp_path / "plots").mkdir()
    (tmp_path / "plots" / "SBS_96_plots_P.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "plots" / "notes.txt").write_text("not a plot")

    result = results.scan(str(tmp_path))

    assert [p["name"] for p in result["plots"]] == ["SBS_96_plots_P.pdf"]


def test_scan_without_plots_folder_lists_none(tmp_path):
    assert results.scan(str(tmp_path))["plots"] == []
