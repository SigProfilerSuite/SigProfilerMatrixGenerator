"""Browser-driven interaction tests for the dashboard frontend.

Skips cleanly (module-level importorskip) when Playwright is not installed,
same as SigProfilerPlotting's dashboard test suite: these run in a dedicated
venv with `playwright install chromium`, not in the shared dev environment.

The page's CSP refuses eval, so waits poll from Python instead of using
wait_for_function.
"""

import threading
import time

import pytest

playwright_sync_api = pytest.importorskip("playwright.sync_api")

from SigProfilerMatrixGenerator.web import jobs, server


@pytest.fixture
def dashboard_url(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNJOB_MODULE", "tests.web.fixtures.fake_runjob")
    srv = server.make_server("127.0.0.1", 0, tmp_path / "jobs")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}/"
    finally:
        srv.shutdown()
        thread.join(timeout=5)
        srv.server_close()


@pytest.fixture
def page(dashboard_url):
    with playwright_sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        browser_page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        browser_page.on("pageerror", lambda e: errors.append(str(e)))
        browser_page.goto(dashboard_url)
        browser_page.wait_for_selector("#genomeSel option", state="attached")
        yield browser_page
        browser.close()
        assert errors == [], f"uncaught page errors: {errors}"


def _wait_text(locator, needle, timeout=10.0):
    deadline = time.monotonic() + timeout
    text = ""
    while time.monotonic() < deadline:
        text = locator.text_content() or ""
        if needle in text:
            return text
        time.sleep(0.15)
    raise AssertionError(f"{needle!r} never appeared (last text: {text!r})")


def _vcf_folder(tmp_path, name="cohort", samples=("PD1", "PD2")):
    folder = tmp_path / name
    folder.mkdir()
    for sample in samples:
        (folder / f"{sample}.vcf").write_text("##fileformat=VCFv4.2\n#CHROM\n1\t10\t.\tA\tG\n")
    return folder


def _paste_input(page, path):
    page.fill("#inputPath", str(path))
    page.press("#inputPath", "Enter")


# ------------------------------------------------------------------ shell


def test_page_loads_on_new_run(page):
    assert page.title() == "SigProfilerMatrixGenerator Workbench"
    assert page.get_attribute("#tab-run", "aria-selected") == "true"
    assert page.is_visible("#view-run")


def test_tabs_switch_views(page):
    page.click("#tab-monitor")
    assert page.get_attribute("#tab-monitor", "aria-selected") == "true"
    assert page.is_visible("#view-monitor")
    assert not page.is_visible("#view-run")
    page.click("#tab-help")
    assert page.is_visible("#view-help")


def test_theme_choice_applies_and_survives_a_reload(page):
    page.select_option("#themeSel", "night")
    assert page.get_attribute("html", "data-theme") == "night"
    page.reload()
    page.wait_for_selector("#genomeSel option", state="attached")
    assert page.get_attribute("html", "data-theme") == "night"
    assert page.input_value("#themeSel") == "night"


def test_about_button_toggles_its_panel(page):
    button = page.locator("#optionsCard .about-btn")
    button.click()
    assert page.is_visible("#about-options")
    assert button.get_attribute("aria-expanded") == "true"
    button.click()
    assert not page.is_visible("#about-options")


def test_quit_dialog_can_be_cancelled(page):
    page.click("#quitBtn")
    assert page.is_visible("#quitDialog")
    page.click("#quitCancel")
    assert not page.is_visible("#quitDialog")


# ------------------------------------------------------------------ input


def test_pasted_folder_is_recognised(page, tmp_path):
    folder = _vcf_folder(tmp_path)
    _paste_input(page, folder)

    page.wait_for_selector("#inputInfo .tile")
    tiles = page.locator("#inputInfo .tile .v").all_text_contents()
    assert tiles[:2] == ["VCF", "2"]
    assert "cohort" in page.text_content("#inputChosen")
    assert page.input_value("#inputPath") == ""
    assert page.input_value("#projectName") == "cohort"
    assert str(folder) in page.text_content("#outPreview")


def test_a_single_file_is_refused_with_its_folder_named(page, tmp_path):
    folder = _vcf_folder(tmp_path)
    _paste_input(page, folder / "PD1.vcf")

    box = page.locator("#inputInfo .note-box.crit")
    _wait_text(box, "choose the folder")


@pytest.mark.parametrize("example, recognised, project, genome", [
    ("brca", ["Txt", "4", "32,455"], "BRCA_example", "GRCh37"),
    ("grch38_test", ["VCF", "1", "9,631"], "GRCh38_test", "GRCh38"),
])
def test_examples_fill_in_a_safe_setup(page, example, recognised, project, genome):
    button = page.locator(f'#examples button[data-example="{example}"]')
    if not button.count():
        pytest.skip(f"this install does not ship the {example} example")
    button.click()
    page.wait_for_selector("#inputInfo .tile")
    tiles = page.locator("#inputInfo .tile .v").all_text_contents()
    assert tiles[:3] == recognised
    assert page.input_value("#projectName") == project
    assert page.input_value("#genomeSel") == genome
    assert page.input_value("#outputPath").endswith(f"SigProfilerMatrixGenerator_example/{project}")


# -------------------------------------------------------------------- run


def test_start_refuses_without_an_input(page):
    page.click("#startBtn")
    _wait_text(page.locator("#startError"), "Not ready yet")


def test_a_run_reaches_done_and_offers_its_results(page, tmp_path):
    _paste_input(page, _vcf_folder(tmp_path))
    page.wait_for_selector("#inputInfo .tile")
    page.click("#startBtn")

    page.wait_for_selector("#view-monitor:not(.hidden)")
    _wait_text(page.locator("#jobPill"), "done")
    assert page.is_visible("#jobResult button:has-text('Open results')")
    assert "cohort" in page.text_content("#jobList")
    assert page.locator("#jobSteps .s.done").count() == 3


# ---------------------------------------------------------------- results


@pytest.fixture
def output_folder(tmp_path):
    matrix = pytest.importorskip("sigProfilerPlotting.web.matrix")
    root = tmp_path / "output"
    for sub, ctx in (("SBS", "SBS96"), ("ID", "ID83")):
        (root / sub).mkdir(parents=True)
        labels = matrix.REFERENCE_CONTEXTS[ctx]
        rows = ["MutationType\tS1\tS2"] + [f"{label}\t{i % 9 + 1}\t{i % 5 + 2}" for i, label in enumerate(labels)]
        (root / sub / f"MyProject.{ctx}.all").write_text("\n".join(rows) + "\n")
    return root


def test_results_list_contexts_and_draw_a_real_chart(page, output_folder):
    page.fill("#openPath", str(output_folder))
    page.press("#openPath", "Enter")

    page.wait_for_selector("#view-results:not(.hidden)")
    assert page.get_attribute('.chip[data-ctx="SBS96"]', "aria-pressed") == "true"
    # A trace node, not just Plotly's wrapper: an empty chart has the wrapper too.
    page.wait_for_selector("#chart svg .trace")
    assert page.locator("#sampleSel option").all_text_contents() == ["S1", "S2"]
    assert "MyProject.SBS96.all" in page.get_attribute("#downloadBtn", "href")
    assert page.locator("#fileList .f").count() == 2


def test_results_switch_context_and_units(page, output_folder):
    page.fill("#openPath", str(output_folder))
    page.press("#openPath", "Enter")
    page.wait_for_selector("#chart svg .trace")

    page.click('.chip[data-ctx="ID83"]')
    _wait_text(page.locator("#chartTitle"), "ID83")
    page.wait_for_selector("#chart svg .trace")
    page.click('.seg label:has-text("Percent")')
    page.wait_for_selector("#chart svg .trace")
    assert page.is_checked('input[name="unit"][value="percent"]')


# ------------------------------------------------- review fixes, 2026-11-11


def test_choose_button_opens_the_picker_through_the_protected_post(page, tmp_path, monkeypatch):
    # The real page must reach the native picker with its token and exact
    # Origin; the picker itself is replaced so no OS dialog opens.
    folder = _vcf_folder(tmp_path)
    opened = []
    monkeypatch.setattr(server.native_dialog, "choose",
                        lambda kind, title: opened.append((kind, title)) or str(folder))

    page.click("#inputChoose")

    page.wait_for_selector("#inputInfo .tile")
    assert opened == [server.PICKERS["input"]]
    assert "cohort" in page.text_content("#inputChosen")


@pytest.fixture
def custom_volume(tmp_path, monkeypatch):
    from SigProfilerMatrixGenerator.scripts import reference_genome_manager

    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    monkeypatch.setitem(reference_genome_manager.CHECKSUMS, "fixtureG", {"1": "x"})
    volume = tmp_path / "genomes"
    (volume / "tsb" / "fixtureG").mkdir(parents=True)
    (volume / "tsb" / "fixtureG" / "1.txt").write_text("data")
    return volume


def test_genome_status_follows_the_advanced_install_folder(tmp_path, custom_volume, page):
    # custom_volume comes before page so the test genome is registered when
    # the page loads; it is installed only in the custom folder.
    page.select_option("#genomeSel", "fixtureG")
    page.wait_for_selector("#genomeStatus .pill.warn")

    page.click("#optionsCard details.adv summary")
    page.fill("#volumePath", str(custom_volume))
    page.press("#volumePath", "Enter")

    page.wait_for_selector("#genomeStatus .pill.good")
    assert "not installed" not in page.text_content("#genomeStatus")
    assert "fixtureG" in page.text_content("#genomeList")


def test_run_with_auto_install_off_uses_the_advanced_install_folder(page, tmp_path, custom_volume):
    # The 2026-11-11 review: Start refused this run, claiming the genome was
    # missing, because status was read from the startup folder instead.
    _paste_input(page, _vcf_folder(tmp_path))
    page.wait_for_selector("#inputInfo .tile")
    page.click("#optionsCard details.adv summary")
    page.fill("#volumePath", str(custom_volume))
    page.press("#volumePath", "Enter")
    page.select_option("#genomeSel", "fixtureG")
    page.wait_for_selector("#genomeStatus .pill.good")
    page.uncheck("#autoInstall")

    page.click("#startBtn")

    page.wait_for_selector("#view-monitor:not(.hidden)")
    _wait_text(page.locator("#jobPill"), "done")


def test_phone_width_has_no_horizontal_overflow_and_keeps_the_sidebar(dashboard_url):
    with playwright_sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        phone = browser.new_page(viewport={"width": 390, "height": 844})
        try:
            phone.goto(dashboard_url)
            phone.wait_for_selector("#genomeSel option", state="attached")
            for tab in ("run", "monitor", "results", "help"):
                phone.click(f"#tab-{tab}")
                width = phone.evaluate("document.documentElement.scrollWidth")
                assert width <= 390, f"{tab} view is {width}px wide at a 390px viewport"
                if tab == "results":
                    # Opening results does not depend on the sidebar.
                    assert phone.is_visible("#resultsChoose")
            # Work area first, the sidebar's actions below it, still reachable.
            main_top = phone.locator(".main").bounding_box()["y"]
            sidebar_top = phone.locator(".sidebar").bounding_box()["y"]
            assert main_top < sidebar_top
            assert phone.is_visible("#openResultsBtn")
        finally:
            browser.close()


def test_wide_screen_offers_one_open_a_results_folder_button(page):
    # The page fixture is 1280 px wide: the sidebar holds the only button,
    # and the empty Results tab points at it instead of repeating it.
    page.click("#tab-results")
    assert page.is_visible("#openResultsBtn")
    assert not page.is_visible("#resultsChoose")
    assert page.is_visible("#resultsEmpty .wide-only")
    visible = [b for b in page.locator("button:has-text('Open a results folder')").all() if b.is_visible()]
    assert len(visible) == 1


def test_results_list_pdf_plots_with_open_and_download(page, output_folder):
    (output_folder / "plots").mkdir()
    (output_folder / "plots" / "SBS_96_plots_MyProject.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    page.fill("#openPath", str(output_folder))
    page.press("#openPath", "Enter")

    row = page.locator("#plotList .f")
    row.wait_for()
    assert row.locator(".badge").text_content() == "SBS96"
    assert "/api/results/view?" in row.locator("a:has-text('Open')").get_attribute("href")
    assert row.locator("a:has-text('Open')").get_attribute("target") == "_blank"
    assert "/api/results/download?" in row.locator("a:has-text('Download')").get_attribute("href")


def test_results_without_plots_explain_how_to_get_them(page, output_folder):
    page.fill("#openPath", str(output_folder))
    page.press("#openPath", "Enter")
    _wait_text(page.locator("#plotList"), "Tick PDF plots")


def test_pdf_plots_option_reaches_the_run(page, tmp_path, dashboard_url):
    import json

    _paste_input(page, _vcf_folder(tmp_path))
    page.wait_for_selector("#inputInfo .tile")
    page.check("#optPlot")
    page.click("#startBtn")
    _wait_text(page.locator("#jobPill"), "done")
    configs = list((tmp_path / "jobs").glob("*/config.json"))
    assert [json.loads(c.read_text())["plot"] for c in configs] == [True]


def test_pdf_plots_are_listed_by_channel_count(page, output_folder):
    (output_folder / "plots").mkdir()
    for name in ("SBS_1536_plots_P.pdf", "ID_83_plots_P.pdf", "SBS_96_plots_P.pdf"):
        (output_folder / "plots" / name).write_bytes(b"%PDF-1.4\n%%EOF\n")
    page.fill("#openPath", str(output_folder))
    page.press("#openPath", "Enter")
    page.locator("#plotList .f").first.wait_for()
    assert page.locator("#plotList .badge").all_text_contents() == ["SBS96", "SBS1536", "ID83"]


@pytest.fixture(params=[("GRCh38", "Try the GRCh38 test set"), ("GRCh37", "Try the BRCA example")])
def installed_only(request, monkeypatch):
    genome, first = request.param
    monkeypatch.setattr(server.genomes, "installed_genomes", lambda volume=None: [genome])
    return first


def test_an_example_that_can_run_now_is_listed_first(installed_only, page):
    labels = page.locator("#examples button").all_text_contents()
    assert labels[0] == installed_only
    assert set(labels) == {"Try the BRCA example", "Try the GRCh38 test set"}


# ------------------------------------------------- genome / calls mismatch

def test_a_genome_other_than_the_calls_declare_is_flagged_before_the_run(page):
    button = page.locator('#examples button[data-example="brca"]')
    if not button.count():
        pytest.skip("this install does not ship the BRCA example")
    button.click()
    page.wait_for_selector("#inputInfo .tile")
    assert page.locator("#genomeMatch .note-box").count() == 0

    page.select_option("#genomeSel", "GRCh38")
    _wait_text(page.locator("#genomeMatch"), "made against GRCh37, but GRCh38 is chosen")
    page.click("#genomeMatch button:has-text('Use GRCh37')")
    assert page.input_value("#genomeSel") == "GRCh37"
    assert page.locator("#genomeMatch .note-box").count() == 0


def test_a_failed_run_says_how_many_mutations_were_skipped_and_why(page, tmp_path, monkeypatch):
    import json

    log = tmp_path / "output" / "logs" / "SigProfilerMatrixGenerator_cohort_GRCh38.out"
    monkeypatch.setenv("FAKE_RUNJOB_RESULT", json.dumps({
        "status": "failed",
        "error": "ValueError: Error: More than 30% of mutations were skipped.",
        "skipped": {"The reference base does not match the reference genome": 950,
                    "The position is out of range": 50},
        "skipped_total": 1000,
        "generator_log": str(log),
    }))
    _paste_input(page, _vcf_folder(tmp_path))
    page.wait_for_selector("#inputInfo .tile")
    page.select_option("#genomeSel", "GRCh38")
    page.click("#startBtn")

    note = page.locator("#jobResult .note-box.skips")
    note.wait_for()
    text = note.text_content()
    assert "1,000 mutations were skipped." in text
    assert "The reference base does not match the reference genome: 950" in text
    assert "Most of the calls do not match GRCh38" in text
    assert str(log) in text
    assert "The log below has the details" not in page.locator("#jobResult").text_content()
