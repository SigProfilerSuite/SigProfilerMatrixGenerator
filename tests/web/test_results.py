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


# ------------------------------------------- earlier results: find, replace, delete

UUID = "6ca8bd09-0498-4c48-87da-20e790c8c4d6"


def _spmg_output(root, project="P"):
    """A folder as SigProfilerMatrixGenerator leaves it, plus files of the user's own."""
    files = {
        f"SBS/{project}.SBS96.all": "MutationType\tS1\nA[C>A]A\t3\n",
        f"ID/{project}.ID89_ID476.classification.all.tsv": "Sample\n",
        f"plots/SBS_96_plots_{project}.pdf": "%PDF-1.4\n",
        f"logs/SigProfilerMatrixGenerator_{project}_GRCh382026-11-11.out": "log\n",
        f"input/{project}_{UUID}/S1.vcf": "#CHROM\n",
        f"temp/{project}_{UUID}/x.txt": "scratch\n",
        "vcf_files/SNV/1_seqinfo.txt": "seq\n",
        "TSB/strandBiasTest_24.txt": "tsb\n",
    }
    mine = {
        "README.txt": "mine",
        "SBS/notes.txt": "mine",
        "plots/figure_for_paper.pdf": "%PDF-1.4\n",
        "logs/my_pipeline.log": "mine",
        "input/my_calls/S9.vcf": "#CHROM\n",
    }
    for rel, text in {**files, **mine}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return sorted(files), sorted(mine)


def test_earlier_results_are_found_by_spmg_names_only(tmp_path):
    _spmg_output(tmp_path / "out")
    assert results.earlier_results(str(tmp_path / "out")) == {
        "found": True, "folders": ["SBS", "ID", "TSB", "plots"]}

    # Same folder names, nothing SigProfilerMatrixGenerator wrote.
    mine = tmp_path / "mine"
    (mine / "plots").mkdir(parents=True)
    (mine / "plots" / "figure.pdf").write_text("x")
    (mine / "logs").mkdir()
    (mine / "logs" / "run.log").write_text("x")
    assert results.earlier_results(str(mine))["found"] is False
    assert results.earlier_results(str(tmp_path / "missing"))["found"] is False


def test_next_free_folder_skips_folders_that_hold_results(tmp_path):
    _spmg_output(tmp_path / "BRCA")
    _spmg_output(tmp_path / "BRCA_2")
    assert results.next_free_folder(str(tmp_path / "BRCA")) == str(tmp_path / "BRCA_3")
    assert results.next_free_folder(str(tmp_path / "BRCA_2")) == str(tmp_path / "BRCA_3")


def test_replacing_removes_only_what_spmg_wrote(tmp_path):
    root = tmp_path / "out"
    generated, mine = _spmg_output(root)

    removed = results.clear_earlier_results(str(root), str(tmp_path / "calls"))

    for rel in mine:
        assert (root / rel).is_file(), f"{rel} was the user's and must stay"
    assert not (root / "SBS" / "P.SBS96.all").exists()
    assert not (root / "plots" / "SBS_96_plots_P.pdf").exists()
    assert not (root / "input" / f"P_{UUID}").exists()
    # Folders left empty go; ones holding the user's files stay.
    assert not (root / "TSB").exists() and not (root / "temp").exists() and not (root / "vcf_files").exists()
    assert (root / "SBS").is_dir() and (root / "input" / "my_calls").is_dir()
    assert f"input/P_{UUID}" in removed
    assert results.earlier_results(str(root))["found"] is False


def test_replacing_refuses_when_the_calls_are_inside_the_output_folder(tmp_path):
    root = tmp_path / "out"
    _spmg_output(root)
    for calls in (root, root / "input" / "my_calls"):
        assert results.replace_problem(str(root), str(calls))
        with pytest.raises(results.ResultsError):
            results.clear_earlier_results(str(root), str(calls))
    assert (root / "SBS" / "P.SBS96.all").is_file()


def test_deleting_output_removes_the_folder_only_when_nothing_else_is_left(tmp_path):
    lone = tmp_path / "lone"
    lone.mkdir()
    (lone / "SBS").mkdir()
    (lone / "SBS" / "P.SBS96.all").write_text("MutationType\tS1\n")
    assert results.generated_size(str(lone))["files"] == 1
    results.delete_output(str(lone), str(tmp_path / "calls"))
    assert not lone.exists()

    shared = tmp_path / "shared"
    _spmg_output(shared)
    results.delete_output(str(shared), str(tmp_path / "calls"))
    assert (shared / "README.txt").is_file()


def test_scan_marks_matrices_with_no_counts_as_empty(tmp_path):
    (tmp_path / "ID").mkdir()
    (tmp_path / "ID" / "P.ID89.all").write_text("MutationType\tS1\tS2\na\t0\t0\nb\t0\t0\n")
    (tmp_path / "ID" / "P.ID83.all").write_text("MutationType\tS1\tS2\na\t0\t0\nb\t0\t1\n")

    found = results.scan(str(tmp_path))["contexts"]

    assert found["ID89"][0]["empty"] is True
    assert found["ID83"][0]["empty"] is False


def test_scan_flags_a_plot_older_than_its_matrix(tmp_path):
    import os
    import time

    (tmp_path / "SBS").mkdir()
    (tmp_path / "plots").mkdir()
    matrix = tmp_path / "SBS" / "P.SBS96.all"
    matrix.write_text("MutationType\tS1\na\t1\n")
    old_plot = tmp_path / "plots" / "SBS_96_plots_P.pdf"
    new_plot = tmp_path / "plots" / "SBS_6_plots_P.pdf"
    old_plot.write_bytes(b"%PDF-1.4\n")
    new_plot.write_bytes(b"%PDF-1.4\n")
    (tmp_path / "SBS" / "P.SBS6.all").write_text("MutationType\tS1\na\t1\n")
    hour_ago = time.time() - 3600
    os.utime(old_plot, (hour_ago, hour_ago))
    os.utime(tmp_path / "SBS" / "P.SBS6.all", (hour_ago, hour_ago))

    plots = {p["name"]: p for p in results.scan(str(tmp_path))["plots"]}

    assert plots["SBS_96_plots_P.pdf"]["older_than_matrix"] is True
    assert plots["SBS_6_plots_P.pdf"]["older_than_matrix"] is False
    assert plots["SBS_96_plots_P.pdf"]["context"] == "SBS96"


def test_mark_earlier_flags_files_written_before_a_run_started(tmp_path):
    import os
    import time

    (tmp_path / "SBS").mkdir()
    old = tmp_path / "SBS" / "P.SBS6.all"
    new = tmp_path / "SBS" / "P.SBS96.all"
    for f in (old, new):
        f.write_text("MutationType\tS1\na\t1\n")
    hour_ago = time.time() - 3600
    os.utime(old, (hour_ago, hour_ago))

    scanned = results.mark_earlier(results.scan(str(tmp_path)), since=time.time() - 60)

    assert scanned["contexts"]["SBS6"][0]["earlier"] is True
    assert scanned["contexts"]["SBS96"][0]["earlier"] is False


def test_dbs1248_is_grouped_by_reference_dinucleotide_like_dbs78(tmp_path, plotting_web):
    from sigProfilerPlotting.web.matrix import REFERENCE_CONTEXTS

    labels = list(REFERENCE_CONTEXTS["DBS1248"])
    path = tmp_path / "P.DBS1248.all"
    path.write_text("MutationType\tS1\n" + "".join(f"{label}\t{i % 7}\n" for i, label in enumerate(labels)))
    dbs78 = tmp_path / "P.DBS78.all"
    dbs78.write_text("MutationType\tS1\n" + "".join(f"{label}\t1\n" for label in REFERENCE_CONTEXTS["DBS78"]))

    traces = results.render(str(path), "S1")["figure"]["traces"]
    reference = results.render(str(dbs78), "S1")["figure"]["traces"]

    assert [t["name"] for t in traces] == [t["name"] for t in reference]          # the 10 dinucleotides
    assert [t["marker"]["color"] for t in traces] == [t["marker"]["color"] for t in reference]
    xs = [x for t in traces for x in t["x"]]
    assert sorted(xs) == sorted(labels)                                             # every bar, once
    assert sum(y for t in traces for y in t["y"]) == sum(i % 7 for i in range(len(labels)))
    # DBS78 channel by channel, each with its 16 flanking contexts together.
    assert xs[:16] == [f"{a}[AC>CA]{b}" for a in "ACGT" for b in "ACGT"]
    assert all(t["hovertemplate"].endswith(f"<extra>{t['name']}</extra>") for t in traces)


def test_regrouping_leaves_unexpected_labels_alone():
    figure = {"traces": [{"name": "x", "x": ["odd"], "y": [1]}], "layout": {}}
    assert results.regroup_flanked_dbs(figure) == {"traces": [{"name": "x", "x": ["odd"], "y": [1]}], "layout": {}}


def test_a_dbs1248_chart_already_grouped_upstream_is_left_as_drawn():
    # A SigProfilerPlotting with its own DBS1248 renderer: its colors stand.
    figure = {"traces": [{"name": "AC", "x": ["A[AC>CA]A"], "y": [1], "marker": {"color": "#03BCEE"}},
                         {"name": "AT", "x": ["A[AT>CA]A"], "y": [2], "marker": {"color": "#0366CB"}}],
              "layout": {}}
    before = repr(figure)
    assert repr(results.regroup_flanked_dbs(figure, ["#000000"])) == before
