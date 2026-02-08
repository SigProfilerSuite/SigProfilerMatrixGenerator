import argparse
import json
import mimetypes
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple, Dict, Set


_OSF_API = "https://api.osf.io/v2"
_OSF_FILES_RE = re.compile(r"https://files\.osf\.io/[^\s)\"']+")
_OSF_SHORT_RE = re.compile(r"https://osf\.io/[^\s)\"']+")
_OSF_IMAGE_SIZE_SUFFIX_RE = re.compile(
    r"(https://files\.osf\.io/[^\s)\"']+)\s+=\d+(?:%x|x)$"
)
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)


def _headers(*, accept: str, token: Optional[str], extra: Optional[dict] = None) -> dict:
    headers = {
        "User-Agent": _BROWSER_UA,
        "Accept": accept,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra:
        headers.update(extra)
    return headers


def _fetch(url: str, accept: str, token: Optional[str]) -> Tuple[int, Optional[str], bytes]:
    req = urllib.request.Request(
        url,
        headers=_headers(accept=accept, token=token),
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = r.read()
        return r.status, r.headers.get("content-type"), payload


def _fetch_json(url: str, token: Optional[str]) -> dict:
    status, content_type, payload = _fetch(url, "application/json", token)
    if not payload or not payload.strip():
        raise RuntimeError(
            f"Expected JSON but got empty response (status={status}, content-type={content_type}) from {url}"
        )

    try:
        return json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        snippet = payload[:200].decode("utf-8", "replace")
        raise RuntimeError(
            f"Expected JSON but got non-JSON response (status={status}, content-type={content_type}) from {url}: {snippet!r}"
        )


def _iter_osf_collection(first_url: str, token: Optional[str]):
    url = first_url
    while url:
        # OSF node wiki listing is usually public, but allow auth for private projects.
        data = _fetch_json(url, token=token)
        for item in data.get("data", []):
            yield item
        url = (data.get("links") or {}).get("next")


def _safe_filename(name: str) -> str:
    # OSF wiki names typically don't contain path separators, but guard anyway.
    return name.replace("/", "-").replace("\\", "-")


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
    if data.startswith(b"PK\x03\x04"):
        return ".zip"
    if data.startswith(b"\x1f\x8b"):
        return ".gz"
    head = data[:512].lstrip()
    if head.startswith(b"<!DOCTYPE html") or head.startswith(b"<html") or head.startswith(
        b"<!doctype html"
    ):
        return ".html"
    if b"<svg" in head[:512]:
        return ".svg"
    return ""


def _parse_files_osf_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse files.osf.io v1 URLs:
      /v1/resources/<node>/providers/<provider>/<file_id>?...
    Returns (node_id, provider, file_id) or (None, None, None) if not recognized.
    """
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


def _download(url: str, out_path: Path, token: Optional[str]) -> Path:
    download_url = url
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "osf.io":
        # osf.io shortlinks often require /download to yield the file bytes.
        if not parsed.path.rstrip("/").endswith("/download"):
            download_url = urllib.parse.urljoin(
                url if url.endswith("/") else url + "/", "download"
            )

    candidate_urls = [download_url]

    # Some OSF file URLs are easier to fetch as downloads than as "render".
    if parsed.netloc == "files.osf.io":
        # Prefer an API-resolved download URL when authenticated. This often yields a
        # signed URL and avoids 403s from direct files.osf.io access.
        if token:
            node_id, provider, file_id = _parse_files_osf_url(url)
            if provider and file_id:
                api_download = _resolve_osf_file_download_url(
                    provider=provider, file_id=file_id, token=token, node_id=node_id
                )
                if api_download:
                    candidate_urls.insert(0, api_download)

        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if q.get("mode") == ["render"]:
            q.pop("mode", None)
            q["action"] = ["download"]
            new_query = urllib.parse.urlencode(q, doseq=True)
            candidate_urls.append(parsed._replace(query=new_query).geturl())

    last_err = None
    for candidate in candidate_urls:
        req = urllib.request.Request(
            candidate,
            headers=_headers(
                accept="*/*",
                token=token,
                extra={
                    "Referer": "https://osf.io/",
                },
            ),
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                content_type = r.headers.get("content-type")
                data = r.read()
            last_err = None
            break
        except urllib.error.HTTPError as e:
            # Capture a small snippet for debugging; continue to next candidate.
            try:
                snippet = e.read(200).decode("utf-8", "replace")
            except Exception:
                snippet = ""
            # If this looks like an OSF Storage file id, try to resolve a signed/alternate
            # download URL via the OSF API (often works better than files.osf.io URLs).
            # If we didn't already add an API URL (or it failed), attempt it on-demand.
            if e.code in (401, 403) and parsed.netloc == "files.osf.io" and token:
                node_id, provider, file_id = _parse_files_osf_url(url)
                if provider and file_id:
                    api_download = _resolve_osf_file_download_url(
                        provider=provider,
                        file_id=file_id,
                        token=token,
                        node_id=node_id,
                    )
                    if api_download and api_download not in candidate_urls:
                        candidate_urls.append(api_download)
                        continue

            last_err = RuntimeError(
                f"HTTP {e.code} fetching {candidate} (from {url})"
                + (f": {snippet!r}" if snippet else "")
            )
            continue
        except Exception as e:
            last_err = e
            continue

    if last_err is not None:
        raise last_err

    ext = _guess_ext(content_type) or _sniff_ext(data)
    final_path = out_path.with_suffix(ext) if ext else out_path
    final_path.parent.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(data)
    return final_path


def _resolve_osf_file_download_url(
    *, provider: str, file_id: str, token: str, node_id: Optional[str]
) -> Optional[str]:
    """
    Best-effort: ask OSF API for a download link for a file.
    Some OSF instances return an authenticated/signed URL here.
    """
    endpoints = [
        f"{_OSF_API}/files/{provider}/{file_id}/",
        f"{_OSF_API}/files/{file_id}/",  # older/alternate shape on some deployments
    ]
    if node_id:
        endpoints.append(f"{_OSF_API}/nodes/{node_id}/files/{provider}/{file_id}/")

    payload = None
    for ep in endpoints:
        try:
            payload = _fetch_json(ep, token=token)
            break
        except Exception:
            continue
    if not payload:
        return None

    data = payload.get("data") or {}
    links = data.get("links") or {}
    for key in ("download", "render"):
        val = links.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
    return None


def _extract_osf_file_urls(markdown: str) -> list[str]:
    urls = []
    for raw in _OSF_FILES_RE.findall(markdown) + _OSF_SHORT_RE.findall(markdown):
        url = raw.rstrip(").,")
        url = _OSF_IMAGE_SIZE_SUFFIX_RE.sub(r"\1", url)
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc == "osf.io":
            parts = parsed.path.strip("/").split("/")
            # Do not treat OSF wiki navigation links as downloadable "assets".
            if len(parts) >= 2 and parts[1] == "wiki":
                continue
        urls.append(url)
    return sorted(set(urls))


def _write_text_exact(path: Path, content: str) -> None:
    # Preserve content as provided by OSF. Add a trailing newline only when non-empty.
    if content and not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _fetch_wiki_markdown(wiki_id: str, token: Optional[str]) -> str:
    # OSF has historically returned either JSON or raw markdown from this endpoint.
    url = f"{_OSF_API}/wikis/{wiki_id}/content/"
    status, content_type, payload = _fetch(
        url, "application/json, text/plain, */*", token=token
    )
    if not payload or not payload.strip():
        raise RuntimeError(
            f"Empty wiki content response (status={status}, content-type={content_type}) from {url}"
        )

    # Try JSON first when it looks like JSON.
    looks_like_json = payload[:1] in (b"{", b"[")
    if looks_like_json or (content_type and "json" in content_type.lower()):
        try:
            content_payload = json.loads(payload.decode("utf-8"))
            data = content_payload.get("data") or {}
            attrs = data.get("attributes") or {}
            # Common OSF field.
            if isinstance(attrs.get("content"), str):
                return attrs["content"]
        except Exception:
            # Fall back to treating it as text.
            pass

    return payload.decode("utf-8", "replace")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mirror OSF wiki pages and referenced OSF-hosted assets into docs/ for local MkDocs rendering.",
    )
    parser.add_argument(
        "--node",
        default="s93d5",
        help="OSF node GUID (default: s93d5).",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs",
        help="MkDocs docs_dir (default: docs).",
    )
    parser.add_argument(
        "--wiki-out",
        default="docs/osf_wiki",
        help="Output directory for mirrored wiki pages (default: docs/osf_wiki).",
    )
    parser.add_argument(
        "--assets-out",
        default="docs/assets/osf",
        help="Output directory for downloaded assets (default: docs/assets/osf).",
    )
    parser.add_argument(
        "--page-size",
        default=100,
        type=int,
        help="OSF API page size (default: 100).",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("OSF_TOKEN"),
        help="OSF personal access token (or set env var OSF_TOKEN). Needed for private assets/projects.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previously-mirrored wiki pages and downloaded assets (keeps placeholder SVG if present).",
    )
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="Mirror wiki pages but skip downloading referenced assets.",
    )
    parser.add_argument(
        "--continue-on-asset-error",
        action="store_true",
        help="Continue mirroring even if some assets fail to download.",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    wiki_out = Path(args.wiki_out)
    assets_out = Path(args.assets_out)

    if args.clean:
        # Remove old mirrored pages.
        if wiki_out.exists():
            for p in wiki_out.rglob("*.md"):
                try:
                    p.unlink()
                except Exception:
                    pass
        # Remove old downloaded assets (but keep the committed placeholder if present).
        if assets_out.exists():
            for p in assets_out.rglob("*"):
                if p.is_dir():
                    continue
                if p.name in {"osf_asset_unavailable.svg"}:
                    continue
                try:
                    p.unlink()
                except Exception:
                    pass

    wikis_url = f"{_OSF_API}/nodes/{args.node}/wikis/?page[size]={args.page_size}"
    wiki_items = list(_iter_osf_collection(wikis_url, token=args.token))

    pages = []
    all_asset_urls: set[str] = set()
    asset_sources: Dict[str, Set[str]] = {}
    asset_failures: Dict[str, dict] = {}
    for item in wiki_items:
        wiki_id = item.get("id")
        attrs = item.get("attributes") or {}
        name = attrs.get("name") or wiki_id

        markdown = _fetch_wiki_markdown(wiki_id, token=args.token)

        filename = _safe_filename(name) + ".md"
        out_path = wiki_out / filename
        _write_text_exact(out_path, markdown)

        # Paths in index.md are relative to docs/osf_wiki/index.md.
        pages.append((name, filename))
        urls = _extract_osf_file_urls(markdown)
        all_asset_urls.update(urls)
        for u in urls:
            asset_sources.setdefault(u, set()).add(f"osf_wiki/{filename}")

    # Download assets and write manifest for mkdocs_hooks.py rewrite.
    manifest: dict[str, str] = {}
    if not args.skip_assets:
        for url in sorted(all_asset_urls):
            parsed = urllib.parse.urlparse(url)
            file_id = parsed.path.rstrip("/").split("/")[-1] or "osf_file"
            base_out = assets_out / file_id
            try:
                final_path = _download(url, base_out, token=args.token)
            except Exception as e:
                if args.continue_on_asset_error:
                    refs = sorted(asset_sources.get(url, set()))
                    ref_msg = f" (referenced by: {', '.join(refs)})" if refs else ""
                    print(f"[warn] Failed to download asset {url}{ref_msg}: {e}")
                    asset_failures[url] = {
                        "error": str(e),
                        "referenced_by": refs,
                    }
                    continue
                raise
            rel = os.path.relpath(final_path, docs_dir)
            manifest[url] = rel.replace(os.sep, "/")

    assets_out.mkdir(parents=True, exist_ok=True)
    (assets_out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (assets_out / "missing_assets.json").write_text(
        json.dumps(asset_failures, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Generate a browsable index for MkDocs (without editing mirrored pages).
    pages_md_lines = [
        "# OSF Wiki (Mirrored)\n",
        "\n",
        "These pages are mirrored from the OSF wiki and stored in-repo for local viewing.\n",
        "\n",
        "To regenerate the mirror:\n",
        "\n",
        "```bash\n",
        f"python3 tools/mirror_osf_wiki.py --node {args.node} --continue-on-asset-error\n",
        "```\n",
        "\n",
    ]
    if asset_failures:
        pages_md_lines.append(
            f"Some OSF-hosted assets could not be downloaded (e.g. HTTP 403). "
            f"See [Missing Assets](missing-assets.md).\n"
        )
        pages_md_lines.append("\n")
    pages_md_lines.append("## Pages\n\n")
    for name, rel in sorted(pages, key=lambda x: x[0].lower()):
        pages_md_lines.append(f"- [{name}]({rel})\n")
    _write_text_exact(wiki_out / "index.md", "".join(pages_md_lines))

    # Missing assets report (human-readable).
    missing_lines = ["# Missing Assets\n\n"]
    if not asset_failures:
        missing_lines.append("All referenced OSF assets were downloaded successfully.\n")
    else:
        missing_lines.append(
            "Some OSF-hosted assets referenced by the wiki could not be downloaded.\n\n"
        )
        missing_lines.append(
            "Common causes:\n\n- The asset belongs to a different OSF project you cannot access\n"
            "- The asset is private or restricted\n\n"
        )
        missing_lines.append("## Details\n\n")
        for url, info in sorted(asset_failures.items(), key=lambda x: x[0]):
            missing_lines.append(f"- `{url}`\n")
            missing_lines.append(f"  - Error: `{info.get('error','')}`\n")
            refs = info.get("referenced_by") or []
            if refs:
                missing_lines.append(f"  - Referenced by: {', '.join(f'`{r}`' for r in refs)}\n")
    _write_text_exact(wiki_out / "missing-assets.md", "".join(missing_lines))

    print(f"Mirrored {len(pages)} wiki pages to: {wiki_out}")
    print(f"Downloaded {len(manifest)} assets to: {assets_out}")
    print(f"Wrote manifest: {assets_out / 'manifest.json'}")
    if asset_failures:
        print(f"Wrote missing assets: {assets_out / 'missing_assets.json'}")
        print(f"Wrote missing report: {wiki_out / 'missing-assets.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
