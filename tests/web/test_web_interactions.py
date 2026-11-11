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


def test_example_fills_in_a_safe_setup(page):
    if not page.is_visible("#exampleBtn"):
        pytest.skip("this install does not ship the BRCA example")
    page.click("#exampleBtn")
    page.wait_for_selector("#inputInfo .tile")
    tiles = page.locator("#inputInfo .tile .v").all_text_contents()
    assert tiles[:2] == ["Txt", "4"]
    assert page.input_value("#projectName") == "BRCA_example"
    assert page.input_value("#genomeSel") == "GRCh37"
    assert "SigProfilerMatrixGenerator_example" in page.input_value("#outputPath")


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
