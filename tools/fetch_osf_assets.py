import argparse
import json
import mimetypes
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


_OSF_URL_RE = re.compile(r"https://files\.osf\.io/[^\s)\"']+")
_OSF_SHORT_RE = re.compile(r"https://osf\.io/[^\s)\"']+")
_OSF_IMAGE_SIZE_SUFFIX_RE = re.compile(r"(https://files\.osf\.io/[^\s)\"']+)\s+=\d+(?:%x|x)$")
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def _guess_ext(content_type: Optional[str]) -> str:
    if not content_type:
        return ""
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime == "image/jpeg":
        return ".jpg"
    if mime == "image/svg+xml":
        return ".svg"
    return mimetypes.guess_extension(mime) or ""


def _sniff_ext(data: bytes) -> str:
    if not data:
        return ""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"%PDF-"):
        return ".pdf"
    head = data[:512].lstrip()
    if head.startswith(b"<!DOCTYPE html") or head.startswith(b"<html") or head.startswith(
        b"<!doctype html"
    ):
        return ".html"
    if b"<svg" in head[:512]:
        return ".svg"
    return ""


def _parse_files_osf_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "files.osf.io":
        return None, None, None
    parts = parsed.path.strip("/").split("/")
    node_id = None
    provider = None
    file_id = None
    try:
        r = parts.index("resources")
        node_id = parts[r + 1]
    except Exception:
        node_id = None
    try:
        p = parts.index("providers")
        provider = parts[p + 1]
        file_id = parts[p + 2]
    except Exception:
        provider = None
        file_id = None
    return node_id, provider, file_id


def _download(url: str, out_path: Path, token: Optional[str]) -> str:
    download_url = url
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "osf.io" and not parsed.path.rstrip("/").endswith("/download"):
        download_url = urllib.parse.urljoin(
            url if url.endswith("/") else url + "/", "download"
        )

    req = urllib.request.Request(
        download_url,
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "*/*",
            **({"Authorization": f"Bearer {token}"} if token else {}),
            "Referer": "https://osf.io/",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        content_type = r.headers.get("content-type")
        data = r.read()

    ext = _guess_ext(content_type) or _sniff_ext(data)
    final_path = out_path.with_suffix(ext) if ext else out_path
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(data)
    return final_path.name


def _extract_urls(markdown: str) -> list[str]:
    urls = []
    for raw in _OSF_URL_RE.findall(markdown) + _OSF_SHORT_RE.findall(markdown):
        url = raw.rstrip(").,")
        url = _OSF_IMAGE_SIZE_SUFFIX_RE.sub(r"\1", url)
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc == "osf.io":
            parts = parsed.path.strip("/").split("/")
            # Skip OSF wiki links; those should be rewritten to local docs, not downloaded as HTML.
            if len(parts) >= 2 and parts[1] == "wiki":
                continue
        urls.append(url)
    return sorted(set(urls))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download OSF-hosted assets referenced in docs Markdown (files.osf.io) into docs/assets/osf/.",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs",
        help="MkDocs docs_dir (default: docs).",
    )
    parser.add_argument(
        "--out-dir",
        default="docs/assets/osf",
        help="Output directory for downloaded assets (default: docs/assets/osf).",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("OSF_TOKEN"),
        help="OSF personal access token (or set env var OSF_TOKEN). Needed for private assets/projects.",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    out_dir = Path(args.out_dir)
    if not docs_dir.exists():
        raise SystemExit(f"docs dir not found: {docs_dir}")

    md_files = sorted(docs_dir.rglob("*.md"))
    all_urls: set[str] = set()
    for md in md_files:
        all_urls.update(_extract_urls(md.read_text(encoding="utf-8")))

    manifest: dict[str, str] = {}
    for url in sorted(all_urls):
        parsed = urllib.parse.urlparse(url)
        file_id = parsed.path.rstrip("/").split("/")[-1] or "osf_file"
        base_out = out_dir / file_id
        downloaded_name = _download(url, base_out, token=args.token)
        rel = os.path.relpath(out_dir / downloaded_name, docs_dir)
        manifest[url] = rel.replace(os.sep, "/")

    manifest_path = out_dir / "manifest.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"Downloaded {len(manifest)} assets")
    print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
