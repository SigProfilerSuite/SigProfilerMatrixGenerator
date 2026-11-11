import http.client
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from SigProfilerMatrixGenerator.web import jobs, server

# The fake job only reads "outcome"; the rest is what /api/run requires.
RUN_CONFIG = {
    "outcome": "done",
    "project": "P",
    "reference_genome": "GRCh37",
    "path_to_input_files": "/data/cohort",
}


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNJOB_MODULE", "tests.web.fixtures.fake_runjob")
    srv = server.make_server("127.0.0.1", 0, tmp_path / "jobs")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        thread.join(timeout=5)
        srv.server_close()


def _url(srv, path):
    return f"http://127.0.0.1:{srv.server_address[1]}{path}"


def _get(srv, path, headers=None):
    request = urllib.request.Request(_url(srv, path), headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _post(srv, path, payload=None, headers=None, token=True):
    """POST as the app's own page does: exact Origin plus the launch token."""
    data = json.dumps(payload or {}).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Origin": _url(srv, "")}
    if token:
        hdrs["X-Dashboard-Token"] = srv.instance_token
    hdrs.update(headers or {})
    request = urllib.request.Request(_url(srv, path), data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _raw(srv, request_bytes):
    import socket

    with socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=5) as sock:
        sock.sendall(request_bytes)
        return sock.recv(65536)


# ------------------------------------------------------------- security


def test_wrong_host_header_is_refused(running_server):
    request = urllib.request.Request(_url(running_server, "/api/env"))
    request.headers["Host"] = "evil.example.com"
    # urllib won't let us override Host easily via headers dict (it's set
    # from the URL), so hit the socket directly for this one check.
    import socket

    with socket.create_connection(("127.0.0.1", running_server.server_address[1]), timeout=5) as sock:
        sock.sendall(
            b"GET /api/env HTTP/1.1\r\nHost: evil.example.com\r\nConnection: close\r\n\r\n"
        )
        response = sock.recv(4096)
    assert b"403" in response.split(b"\r\n", 1)[0]


def test_cross_site_origin_is_refused(running_server):
    status, body = _post(
        running_server, "/api/quit", headers={"Origin": "http://evil.example.com"}
    )
    assert status == 403
    assert body["ok"] is False


def test_post_without_origin_header_is_refused(running_server):
    # Unlike GET (a top-level page load legitimately has no Origin), a POST
    # with no Origin at all is not something this dashboard's own frontend
    # would ever send, so it's refused outright rather than let through.
    request = urllib.request.Request(
        _url(running_server, "/api/run"),
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status, body = response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        status, body = exc.code, json.loads(exc.read())
    assert status == 403
    assert body["ok"] is False


def test_post_without_the_token_is_refused(running_server):
    status, _ = _post(running_server, "/api/quit", token=False)
    assert status == 403
    time.sleep(0.2)
    assert _get(running_server, "/api/identity")[0] == 200  # did not quit


def test_post_with_a_wrong_token_is_refused(running_server):
    status, _ = _post(running_server, "/api/quit", headers={"X-Dashboard-Token": "guess"})
    assert status == 403


@pytest.mark.parametrize("origin", [
    "http://127.0.0.1:1",                  # another local server (wrong port)
    "http://localhost",                     # no port at all
    "https://127.0.0.1:{port}",             # wrong scheme
    "http://evil.example.com:{port}",       # another site
    "null",                                 # sandboxed or file:// page
])
def test_post_from_any_other_origin_is_refused_even_with_the_token(running_server, origin):
    origin = origin.format(port=running_server.server_address[1])
    status, _ = _post(running_server, "/api/quit", headers={"Origin": origin})
    assert status == 403


def test_get_with_a_foreign_origin_is_refused(running_server):
    status, _ = _get(running_server, "/api/env", headers={"Origin": "http://127.0.0.1:1"})
    assert status == 403


def test_the_page_carries_this_launch_token(running_server):
    with urllib.request.urlopen(_url(running_server, "/"), timeout=5) as response:
        page = response.read().decode("utf-8")
    assert running_server.instance_token in page
    assert server.TOKEN_PLACEHOLDER not in page


@pytest.fixture
def no_dialogs(monkeypatch):
    opened = []
    monkeypatch.setattr(server.native_dialog, "choose",
                        lambda kind, title: opened.append((kind, title)) or "/picked")
    return opened


@pytest.mark.parametrize("method", [b"GET", b"HEAD"])
def test_a_link_or_image_cannot_open_a_native_picker(running_server, no_dialogs, method):
    # What a cross-site link, image or navigation sends: GET/HEAD, no Origin.
    response = _raw(
        running_server,
        method + b" /api/dialog?purpose=input&title=x HTTP/1.1\r\nHost: 127.0.0.1\r\n"
        b"Connection: close\r\n\r\n",
    )
    assert b" 200 " not in response.split(b"\r\n", 1)[0]
    assert no_dialogs == []


def test_picker_title_comes_from_the_server_not_the_request(running_server, no_dialogs):
    status, body = _post(running_server, "/api/dialog",
                         {"purpose": "input", "title": 'x") & (do shell script "id")'})
    assert status == 200
    assert body["path"] == "/picked"
    assert no_dialogs == [server.PICKERS["input"]]


def test_unknown_picker_purpose_is_a_client_error(running_server, no_dialogs):
    status, body = _post(running_server, "/api/dialog", {"purpose": "anything"})
    assert status == 400
    assert no_dialogs == []


def test_picker_without_the_token_does_not_open(running_server, no_dialogs):
    status, _ = _post(running_server, "/api/dialog", {"purpose": "input"}, token=False)
    assert status == 403
    assert no_dialogs == []


def test_genome_status_follows_the_requested_install_folder(running_server, tmp_path, monkeypatch):
    from SigProfilerMatrixGenerator.scripts import reference_genome_manager

    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    monkeypatch.setitem(reference_genome_manager.CHECKSUMS, "fixtureG", {"1": "x"})
    volume = tmp_path / "genomes"
    (volume / "tsb" / "fixtureG").mkdir(parents=True)
    (volume / "tsb" / "fixtureG" / "1.txt").write_text("data")

    _, elsewhere = _get(running_server, "/api/genomes")
    _, here = _get(running_server, f"/api/genomes?volume={volume}")

    assert "fixtureG" not in elsewhere["installed"]
    assert "fixtureG" in here["installed"]


def test_every_response_has_a_csp_header(running_server):
    request = urllib.request.Request(_url(running_server, "/api/env"))
    with urllib.request.urlopen(request, timeout=5) as response:
        assert "default-src" in response.headers.get("Content-Security-Policy", "")


def test_static_path_cannot_escape_static_root(running_server):
    status, body = _get(running_server, "/static/../../../etc/passwd")
    assert status in (403, 404)


# ------------------------------------------------------------------ pages


def test_root_serves_index_html(running_server):
    request = urllib.request.Request(_url(running_server, "/"))
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200
        assert b"SigProfilerMatrixGenerator" in response.read()


def test_unknown_route_is_404(running_server):
    status, body = _get(running_server, "/api/nonexistent")
    assert status == 404


# -------------------------------------------------------------------- env


def test_env_reports_genomes_and_plotting_availability(running_server):
    status, body = _get(running_server, "/api/env")
    assert status == 200
    assert body["ok"] is True
    assert "available" in body["genomes"]
    assert "installed" in body["genomes"]
    assert isinstance(body["plotting_available"], bool)
    assert body["version"]


def test_env_offers_both_examples_writing_outside_the_package(running_server):
    _, body = _get(running_server, "/api/env")
    examples = {ex["id"]: ex for ex in body["examples"]}
    assert examples["brca"]["reference_genome"] == "GRCh37"
    assert examples["brca"]["path"].endswith("BRCA_example/SNV")
    assert examples["grch38_test"]["reference_genome"] == "GRCh38"
    assert examples["grch38_test"]["path"].endswith("GRCh38_bench")
    package_dir = str(Path(server.__file__).resolve().parents[1])
    outputs = [ex["output_directory"] for ex in examples.values()]
    assert not any(out.startswith(package_dir) for out in outputs)
    assert len(set(outputs)) == len(outputs)  # examples never share a folder


def test_pdf_plots_open_inline(running_server, tmp_path):
    pdf = tmp_path / "SBS_96_plots_P.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    url = _url(running_server, "/api/results/view?" + urllib.parse.urlencode({"path": str(pdf)}))
    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.headers["Content-Type"] == "application/pdf"
        assert "attachment" not in (response.headers.get("Content-Disposition") or "")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.read().startswith(b"%PDF")


def test_only_pdfs_can_be_viewed_inline(running_server, tmp_path):
    # Anything else served inline from this origin (HTML, say) would run as
    # part of the app; it can still be downloaded as an attachment.
    page = tmp_path / "evil.html"
    page.write_text("<script>alert(1)</script>")
    status, _ = _get(running_server, "/api/results/view?" + urllib.parse.urlencode({"path": str(page)}))
    assert status == 400


def test_run_without_required_fields_is_a_client_error(running_server):
    status, body = _post(running_server, "/api/run", {"config": {"project": "P"}})
    assert status == 400
    assert "reference genome" in body["error"]
    assert "input folder" in body["error"]


def test_run_records_where_its_matrices_go(running_server):
    _, body = _post(running_server, "/api/run", {"config": dict(RUN_CONFIG)})
    job = body["job"]
    assert job["kind"] == "run"
    assert job["project"] == "P"
    assert job["reference_genome"] == "GRCh37"
    assert job["output_dir"] == str(Path("/data/cohort") / "output")


def test_run_with_output_directory_writes_there_directly(running_server):
    config = dict(RUN_CONFIG, output_directory="/results/here")
    _, body = _post(running_server, "/api/run", {"config": config})
    assert body["job"]["output_dir"] == str(Path("/results/here"))


def test_identity_reports_pid_and_token(running_server):
    status, body = _get(running_server, "/api/identity")
    assert status == 200
    assert body["pid"] > 0
    assert body["token"] == running_server.instance_token


# ----------------------------------------------------------------- inputs


def test_browse_lists_a_directory(running_server, tmp_path):
    (tmp_path / "sample1.vcf").write_text("x")
    status, body = _get(running_server, f"/api/browse?path={tmp_path}")
    assert status == 200
    assert body["ok"] is True
    assert any(e["name"] == "sample1.vcf" for e in body["entries"])


def test_browse_missing_path_is_a_client_error(running_server, tmp_path):
    status, body = _get(running_server, f"/api/browse?path={tmp_path / 'nope'}")
    assert status == 400
    assert body["ok"] is False


def test_inspect_recognizes_vcf_input(running_server, tmp_path):
    (tmp_path / "sample1.vcf").write_text("##fileformat=VCFv4.2\n")
    status, body = _get(running_server, f"/api/inspect?path={tmp_path}")
    assert status == 200
    assert body["format"] == "VCF"


# ------------------------------------------------------------------- jobs


def test_run_starts_a_job_and_it_reaches_done(running_server):
    status, body = _post(
        running_server, "/api/run", {"config": dict(RUN_CONFIG), "name": "my run"}
    )
    assert status == 200
    job_id = body["job"]["id"]

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status, body = _get(running_server, f"/api/jobs/{job_id}")
        if body["job"]["status"] == "done":
            break
        time.sleep(0.05)
    assert body["job"]["status"] == "done"


def test_job_log_is_readable_while_running(running_server):
    _, body = _post(running_server, "/api/run", {"config": dict(RUN_CONFIG)})
    job_id = body["job"]["id"]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status, log_body = _get(running_server, f"/api/jobs/{job_id}/log")
        if "step 1/1" in log_body["text"]:
            break
        time.sleep(0.05)
    assert "step 1/1" in log_body["text"]


def test_job_log_with_non_integer_offset_is_a_client_error(running_server):
    _, body = _post(running_server, "/api/run", {"config": dict(RUN_CONFIG)})
    job_id = body["job"]["id"]
    status, body = _get(running_server, f"/api/jobs/{job_id}/log?offset=not-a-number")
    assert status == 400
    assert body["ok"] is False


def test_stop_unknown_job_is_a_client_error(running_server):
    status, body = _post(running_server, "/api/jobs/doesnotexist/stop")
    assert status == 400
    assert body["ok"] is False


def test_jobs_listing_includes_started_jobs(running_server):
    _, body = _post(running_server, "/api/run", {"config": dict(RUN_CONFIG)})
    job_id = body["job"]["id"]
    status, listing = _get(running_server, "/api/jobs")
    assert status == 200
    assert any(job["id"] == job_id for job in listing["jobs"])


def test_get_unknown_job_returns_ok_false(running_server):
    status, body = _get(running_server, "/api/jobs/doesnotexist")
    assert status == 200
    assert body["ok"] is False
    assert body["job"] is None


# ---------------------------------------------------------------- results


def test_results_scan_of_empty_directory(running_server, tmp_path):
    status, body = _get(running_server, f"/api/results?path={tmp_path}")
    assert status == 200
    assert body["contexts"] == {}


def test_results_scan_missing_directory_is_a_client_error(running_server, tmp_path):
    status, body = _get(running_server, f"/api/results?path={tmp_path / 'nope'}")
    assert status == 400


# -------------------------------------------------------------------- misc


def test_quit_stops_the_server(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "RUNJOB_MODULE", "tests.web.fixtures.fake_runjob")
    srv = server.make_server("127.0.0.1", 0, tmp_path / "jobs")
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _post(srv, "/api/quit")
        assert status == 200
        thread.join(timeout=5)
        assert not thread.is_alive()
    finally:
        srv.server_close()


def test_genome_status_names_the_assembly_behind_each_genome(running_server):
    status, body = _get(running_server, "/api/genomes")
    assert status == 200
    assert body["assemblies"]["GRCh37_havana"] == "GRCh37"
    assert body["assemblies"]["GRCh38"] == "GRCh38"


def test_a_browser_that_disconnects_mid_request_is_not_a_server_error(running_server, monkeypatch, capsys):
    # A page closed or reloaded while a request is in flight resets the
    # connection; that is the browser leaving, not a failure to report.
    def reset(path):
        raise ConnectionResetError(54, "Connection reset by peer")

    monkeypatch.setattr(server.inputs, "browse", reset)
    with pytest.raises((urllib.error.URLError, http.client.HTTPException, ConnectionError)):
        _get(running_server, "/api/browse?path=/tmp")
    assert "[500]" not in capsys.readouterr().err


# ------------------------------------------- output folders with earlier results

def _earlier_results(folder, project="P"):
    (folder / "SBS").mkdir(parents=True)
    (folder / "SBS" / f"{project}.SBS96.all").write_text("MutationType\tS1\na\t1\n")
    (folder / "plots").mkdir()
    (folder / "plots" / f"SBS_96_plots_{project}.pdf").write_bytes(b"%PDF-1.4\n")


def _calls(tmp_path):
    calls = tmp_path / "calls"
    calls.mkdir(exist_ok=True)
    (calls / "S1.vcf").write_text("##fileformat=VCFv4.2\n#CHROM\n1\t10\t.\tA\tG\n")
    return calls


def _run_config(calls, out, **extra):
    return {"config": {"project": "P", "reference_genome": "GRCh38",
                       "path_to_input_files": str(calls), "output_directory": str(out), **extra}}


def test_output_check_reports_earlier_results_and_a_free_folder(running_server, tmp_path):
    out = tmp_path / "BRCA"
    _earlier_results(out)
    calls = _calls(tmp_path)

    status, body = _get(running_server, "/api/output?" + urllib.parse.urlencode(
        {"path": str(out), "input": str(calls)}))

    assert status == 200
    assert body["found"] is True and body["folders"] == ["SBS", "plots"]
    assert body["suggested"] == str(tmp_path / "BRCA_2")
    assert body["replace_problem"] is None

    status, body = _get(running_server, "/api/output?" + urllib.parse.urlencode(
        {"path": str(tmp_path / "fresh"), "input": str(calls)}))
    assert body["found"] is False and body["suggested"] is None


def test_a_run_never_lands_silently_on_earlier_results(running_server, tmp_path):
    out = tmp_path / "out"
    _earlier_results(out)
    calls = _calls(tmp_path)

    status, body = _post(running_server, "/api/run", _run_config(calls, out))
    assert status == 409
    assert "already holds results" in body["error"]

    status, body = _post(running_server, "/api/run", _run_config(calls, out, replace_existing=True))
    assert status == 200 and body["job"]["status"] == "running"

    status, body = _post(running_server, "/api/run",
                         _run_config(out / "SBS", out, replace_existing=True))
    assert status == 400
    assert "inside this output folder" in body["error"]


def _finished_run(srv, calls, out):
    status, body = _post(srv, "/api/run", _run_config(calls, out, replace_existing=True))
    assert status == 200, body
    job_id = body["job"]["id"]
    deadline = time.monotonic() + 10
    while srv.manager.get(job_id)["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
    return job_id


def test_results_mark_files_older_than_the_run_that_wrote_the_folder(running_server, tmp_path):
    import os

    out = tmp_path / "out"
    _earlier_results(out)
    hour_ago = time.time() - 3600
    for f in (out / "SBS" / "P.SBS96.all", out / "plots" / "SBS_96_plots_P.pdf"):
        os.utime(f, (hour_ago, hour_ago))
    _finished_run(running_server, _calls(tmp_path), out)
    # What the run itself wrote (the stand-in runner writes nothing).
    (out / "SBS" / "P.SBS6.all").write_text("MutationType\tS1\na\t1\n")

    status, body = _get(running_server, "/api/results?" + urllib.parse.urlencode({"path": str(out)}))

    assert status == 200
    assert body["run"]["name"] == "P"
    assert body["contexts"]["SBS96"][0]["earlier"] is True
    assert body["contexts"]["SBS6"][0]["earlier"] is False
    assert body["plots"][0]["earlier"] is True


def test_a_run_can_leave_the_list_and_come_back(running_server, tmp_path):
    job_id = _finished_run(running_server, _calls(tmp_path), tmp_path / "out")

    assert _post(running_server, f"/api/jobs/{job_id}/hide")[0] == 200
    assert job_id not in [j["id"] for j in _get(running_server, "/api/jobs")[1]["jobs"]]
    assert _post(running_server, f"/api/jobs/{job_id}/unhide")[0] == 200
    assert job_id in [j["id"] for j in _get(running_server, "/api/jobs")[1]["jobs"]]


def test_deleting_a_run_removes_its_record_and_what_it_wrote(running_server, tmp_path):
    out = tmp_path / "out"
    job_id = _finished_run(running_server, _calls(tmp_path), out)
    _earlier_results(out)   # stands in for what the run wrote
    (out / "notes.txt").write_text("mine")

    status, plan = _get(running_server, f"/api/jobs/{job_id}/delete-preview")
    assert status == 200
    assert plan["deletes_files"] is True and plan["files"] == 2

    status, body = _post(running_server, f"/api/jobs/{job_id}/delete")

    assert status == 200 and body["removed"] == 2
    assert running_server.manager.get(job_id) is None
    assert not (out / "SBS").exists() and not (out / "plots").exists()
    assert (out / "notes.txt").is_file()


def test_deleting_an_older_run_leaves_a_later_runs_files_alone(running_server, tmp_path):
    out = tmp_path / "out"
    calls = _calls(tmp_path)
    older = _finished_run(running_server, calls, out)
    _finished_run(running_server, calls, out)
    _earlier_results(out)

    plan = _get(running_server, f"/api/jobs/{older}/delete-preview")[1]
    assert plan["deletes_files"] is False and "later run" in plan["kept_because"]

    assert _post(running_server, f"/api/jobs/{older}/delete")[0] == 200
    assert (out / "SBS" / "P.SBS96.all").is_file()


def test_removing_or_deleting_runs_needs_the_pages_token(running_server, tmp_path):
    job_id = _finished_run(running_server, _calls(tmp_path), tmp_path / "out")
    for action in ("hide", "unhide", "delete"):
        assert _post(running_server, f"/api/jobs/{job_id}/{action}", token=False)[0] == 403
    assert running_server.manager.get(job_id) is not None


def test_a_running_job_cannot_be_deleted(running_server, tmp_path):
    srv = running_server
    meta = srv.manager.start({"outcome": "hang"}, name="hang", cwd=str(Path(__file__).resolve().parents[2]),
                             extra={"kind": "run"})
    try:
        status, body = _post(srv, f"/api/jobs/{meta['id']}/delete")
        assert status == 409
    finally:
        srv.manager.stop(meta["id"])
