import json
import threading
import time
import urllib.error
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


def _post(srv, path, payload=None, headers=None):
    data = json.dumps(payload or {}).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "Origin": _url(srv, "")[:-1]}
    hdrs.update(headers or {})
    request = urllib.request.Request(_url(srv, path), data=data, method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


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


def test_env_example_points_its_output_outside_the_package(running_server):
    status, body = _get(running_server, "/api/env")
    example = body["example"]
    assert example["reference_genome"] == "GRCh37"
    assert example["path"].endswith("BRCA_example/SNV")
    package_dir = str(Path(server.__file__).resolve().parents[1])
    assert not example["output_directory"].startswith(package_dir)


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
