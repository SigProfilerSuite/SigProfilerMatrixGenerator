"""Local HTTP server for the SigProfilerMatrixGenerator dashboard.

A single-user, local-only tool: this server binds to the loopback
interface and never asks for credentials, so two checks guard every
request instead -- the Host header must name this machine (stops DNS
rebinding, where a public page resolves its own name to 127.0.0.1 and then
drives this server) and a cross-site Origin is refused (stops an ordinary
cross-site POST). Do not bind this to a public interface.
"""

from __future__ import annotations

import json
import mimetypes
import os
import secrets
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import genomes, inputs, jobs, native_dialog, results

STATIC = Path(__file__).resolve().parent / "static"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1"}

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; connect-src 'self'"
)

CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

_CLIENT_ERRORS = (
    inputs.InputError,
    results.ResultsError,
    native_dialog.DialogError,
    jobs.JobError,
)


class Handler(BaseHTTPRequestHandler):
    server_version = "SigProfilerMatrixGeneratorWeb"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------ plumbing

    def log_message(self, fmt, *args):
        if self.server.verbose:
            sys.stderr.write("  %s\n" % (fmt % args))

    def _local_only(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if host.lower() not in ALLOWED_HOSTS:
            return False
        origin = self.headers.get("Origin")
        if origin:
            if (urlparse(origin).hostname or "").lower() not in ALLOWED_HOSTS:
                return False
        return True

    def _origin_required(self) -> bool:
        # State-changing requests (POSTs) must carry a matching Origin, full
        # stop -- unlike GET (a top-level page load legitimately has no
        # Origin at all), a same-origin fetch() POST from this page always
        # sets one, so a POST with none is not something this dashboard's
        # own frontend would ever send.
        origin = self.headers.get("Origin")
        if not origin:
            return False
        return (urlparse(origin).hostname or "").lower() in ALLOWED_HOSTS

    def _send(self, status, body=b"", ctype="application/json", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj), "application/json")

    def _fail(self, message, status=400):
        self._json({"ok": False, "error": str(message)}, status)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    def _file(self, path: Path, download: bool = False, filename: str | None = None):
        if not path.is_file():
            return self._fail(f"not found: {path.name}", 404)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store, must-revalidate")
        if download:
            self.send_header(
                "Content-Disposition", f'attachment; filename="{filename or path.name}"'
            )
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(path, "rb") as handle:
            while chunk := handle.read(1 << 16):
                self.wfile.write(chunk)

    # -------------------------------------------------------------- routes

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self._local_only():
            return self._fail("requests must come from this machine", 403)
        url = urlparse(self.path)
        path, query = unquote(url.path), parse_qs(url.query)
        try:
            return self._get(path, query)
        except BrokenPipeError:
            return
        except _CLIENT_ERRORS as exc:
            sys.stderr.write(f"  [400] GET {path}: {type(exc).__name__}: {exc}\n")
            return self._fail(str(exc), 400)
        except Exception as exc:  # noqa: BLE001 - request boundary
            sys.stderr.write(f"  [500] GET {path}:\n")
            traceback.print_exc()
            return self._fail(f"{type(exc).__name__}: {exc}", 500)

    def _get(self, path: str, query: dict):
        srv = self.server
        if path in ("/", "/index.html"):
            return self._file(STATIC / "index.html")
        if path.startswith("/static/"):
            target = (STATIC / path[len("/static/") :]).resolve()
            static_root = STATIC.resolve()
            if static_root != target and static_root not in target.parents:
                return self._fail("forbidden", 403)
            return self._file(target)
        if path == "/vendor/plotly.min.js":
            return self._plotly_bundle()

        if path == "/api/identity":
            return self._json({"pid": os.getpid(), "token": srv.instance_token})
        if path == "/api/env":
            return self._json(
                {
                    "ok": True,
                    "version": _package_version(),
                    "genomes": genomes.status(srv.volume),
                    "plotting_available": results.plotting_available(),
                    "example": _example_input(),
                }
            )
        if path == "/api/browse":
            return self._json({"ok": True, **inputs.browse(_one(query, "path"))})
        if path == "/api/inspect":
            return self._json({"ok": True, **inputs.inspect(_one(query, "path"))})
        if path == "/api/dialog":
            kind = _one(query, "kind", "folder")
            title = _one(query, "title", "Choose a location")
            return self._json({"ok": True, "path": native_dialog.choose(kind, title)})

        if path == "/api/jobs":
            return self._json({"ok": True, "jobs": srv.manager.listing()})
        if path.startswith("/api/jobs/") and path.endswith("/log"):
            job_id = path.split("/")[3]
            try:
                offset = int(_one(query, "offset", "0"))
            except ValueError:
                return self._fail("offset must be an integer", 400)
            return self._json({"ok": True, **srv.manager.log(job_id, offset)})
        if path.startswith("/api/jobs/"):
            job_id = path.split("/")[3]
            job = srv.manager.get(job_id)
            return self._json({"ok": bool(job), "job": job})

        if path == "/api/results":
            return self._json({"ok": True, **results.scan(_one(query, "path"))})
        if path == "/api/results/samples":
            return self._json({"ok": True, **results.load(_one(query, "path"))})
        if path == "/api/results/render":
            return self._json(
                {
                    "ok": True,
                    **results.render(
                        _one(query, "path"),
                        _one(query, "sample"),
                        unit=_one(query, "unit", "counts"),
                        compare_cosmic=query.get("cosmic", [None])[0] or None,
                    ),
                }
            )
        if path == "/api/results/download":
            return self._file(Path(_one(query, "path")), download=True)

        return self._fail("not found", 404)

    def _plotly_bundle(self):
        try:
            import plotly.offline

            bundle = plotly.offline.get_plotlyjs()
        except ImportError:
            self.send_response(302)
            self.send_header("Location", CDN_PLOTLY)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send(200, bundle, "application/javascript")

    def do_POST(self):
        if not self._local_only():
            return self._fail("requests must come from this machine", 403)
        if not self._origin_required():
            return self._fail("a matching Origin header is required", 403)
        path = unquote(urlparse(self.path).path)
        try:
            return self._post(path)
        except BrokenPipeError:
            return
        except _CLIENT_ERRORS as exc:
            sys.stderr.write(f"  [400] POST {path}: {type(exc).__name__}: {exc}\n")
            return self._fail(str(exc), 400)
        except Exception as exc:  # noqa: BLE001 - request boundary
            sys.stderr.write(f"  [500] POST {path}:\n")
            traceback.print_exc()
            return self._fail(f"{type(exc).__name__}: {exc}", 500)

    def _post(self, path: str):
        srv = self.server
        body = self._body()

        if path == "/api/run":
            config = dict(body.get("config") or {})
            missing = [
                label
                for key, label in (
                    ("project", "a project name"),
                    ("reference_genome", "a reference genome"),
                    ("path_to_input_files", "an input folder"),
                )
                if not config.get(key)
            ]
            if missing:
                return self._fail("A run needs " + ", ".join(missing) + ".", 400)
            config["volume"] = config.get("volume") or srv.volume
            extra = {
                "kind": "run",
                "project": config["project"],
                "reference_genome": config["reference_genome"],
                "input": config["path_to_input_files"],
                "output_dir": _output_dir(config),
            }
            name = body.get("name") or config["project"]
            return self._json({"ok": True, "job": srv.manager.start(config, name, extra=extra)})
        if path == "/api/genomes/install":
            genome_name = body.get("genome")
            if not genome_name:
                return self._fail("genome is required", 400)
            config = {
                "install_only": True,
                "reference_genome": genome_name,
                "volume": body.get("volume") or srv.volume,
                "local_genome_dir": body.get("local_genome_dir"),
            }
            extra = {"kind": "install", "reference_genome": genome_name}
            meta = srv.manager.start(config, f"Install {genome_name}", extra=extra)
            return self._json({"ok": True, "job": meta})
        if path.startswith("/api/jobs/") and path.endswith("/stop"):
            job_id = path.split("/")[3]
            return self._json({"ok": srv.manager.stop(job_id)})
        if path == "/api/shutdown":
            if self.headers.get("X-Dashboard-Token") != srv.instance_token:
                return self._fail("forbidden", 403)
            self._json({"ok": True})
            threading.Thread(target=srv.shutdown, daemon=True).start()
            return
        if path == "/api/quit":
            srv.manager.stop_all()
            self._json({"ok": True})
            threading.Thread(target=srv.shutdown, daemon=True).start()
            return

        return self._fail("not found", 404)


def _one(query: dict, key: str, default: str = "") -> str:
    values = query.get(key)
    return values[0] if values else default


def _output_dir(config: dict) -> str:
    # Mirrors SigProfilerMatrixGeneratorFunc: matrices go straight into
    # output_directory when one is given, otherwise into <input>/output/.
    if config.get("output_directory"):
        return str(Path(config["output_directory"]))
    return str(Path(config["path_to_input_files"]) / "output")


def _package_version() -> str:
    from SigProfilerMatrixGenerator.version import __version__

    return __version__


def _example_input() -> dict | None:
    # The BRCA example that ships inside the package: simple-text calls for
    # four breast cancer genomes, against GRCh37. Its output is pointed outside
    # the package, since the default (<input>/output/) would write into the
    # installed package itself.
    import SigProfilerMatrixGenerator

    folder = (
        Path(SigProfilerMatrixGenerator.__file__).resolve().parent
        / "references" / "vcf_files" / "BRCA_example" / "SNV"
    )
    if not (folder / "BRCA_example_subs_simple.txt").is_file():
        return None
    return {
        "path": str(folder),
        "project": "BRCA_example",
        "reference_genome": "GRCh37",
        "output_directory": str(Path.home() / "SigProfilerMatrixGenerator_example"),
    }


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        host: str,
        port: int,
        jobs_dir: str | Path,
        volume: str | None = None,
        verbose: bool = False,
    ):
        super().__init__((host, port), Handler)
        self.verbose = verbose
        self.volume = volume
        self.manager = jobs.JobManager(jobs_dir)
        self.instance_token = secrets.token_hex(16)


def make_server(
    host: str,
    port: int,
    jobs_dir: str | Path,
    volume: str | None = None,
    verbose: bool = False,
) -> Server:
    return Server(host, port, jobs_dir, volume=volume, verbose=verbose)
