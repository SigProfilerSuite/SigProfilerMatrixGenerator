import re
from pathlib import Path
import json
import os
import urllib.parse


_TOC_MARKER_LINE_RE = re.compile(r"^\s*@\[toc\]\([^)]+\)\s*$", re.IGNORECASE)
_OSF_IMAGE_SIZE_SUFFIX_RE = re.compile(r"(!\[[^\]]*\]\([^\s)]+)\s+=\d+(?:%x|x)(\))")
_OSF_URL_IN_MD_IMAGE_RE = re.compile(r"(!\[[^\]]*\]\()([^) \t\r\n]+)(\))")
_OSF_URL_IN_HTML_IMG_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")', re.IGNORECASE)
_OSF_EMBED_RE = re.compile(r"@\[(osf)\]\(([^)]+)\)", re.IGNORECASE)
_OSF_WIKI_URL_RE = re.compile(r"https://osf\.io/([^/]+)/wiki/([^\s)\"]+)", re.IGNORECASE)
_OSF_MANIFEST_CACHE = None
_OSF_MANIFEST_LOADED = False
_OSF_MISSING_CACHE = None
_OSF_MISSING_LOADED = False
_OSF_PLACEHOLDER = "assets/osf/osf_asset_unavailable.svg"

# Map OSF wiki page names (decoded from URL) to local docs filenames.
_OSF_WIKI_PAGE_TO_DOC = {
    "home": "index.md",
    "1. installation - python": "Installation-Python.md",
    "2. installation - r": "Installation-R.md",
    # Historical/renumbered OSF page names we still see linked in the wiki:
    "1. installation": "Installation-Python.md",
    "2. installation": "Installation-Python.md",
    "2. using the tool - input": "Using-the-Tool-SBS-ID-DBS-Input.md",
    "3. using the tool - input": "Using-the-Tool-SBS-ID-DBS-Input.md",
    "3. using the tool - sbs, id, dbs input": "Using-the-Tool-SBS-ID-DBS-Input.md",
    "3. using the tool - cnv input": "Using-the-Tool-CNV-Input.md",
    "3. using the tool - sv input": "Using-the-Tool-SV-Input.md",
    "3. using the tool - output": "Using-the-Tool-Output.md",
    "4. using the tool - output": "Using-the-Tool-Output.md",
    "5. quick start example": "Quick-Start-Example.md",
    "6. quick start example": "Quick-Start-Example.md",
    "6. currently supported genomes": "Currently-Supported-Genomes.md",
    "7. currently supported genomes": "Currently-Supported-Genomes.md",
    "5. output - sbs": "Output-SBS.md",
    "5. output - dbs": "Output-DBS.md",
    "5. output - id": "Output-ID.md",
    "5. output - tsb": "Output-TSB.md",
    "5. output - vcf_files": "Output-vcf_files.md",
    "5. output - plots": "Output-Plots.md",
    "5. output - cnv": "Output-CNV.md",
    "5. output - sv": "Output-SV.md",
}


def on_page_markdown(markdown: str, page, config, files):
    if not markdown:
        return markdown

    lines = markdown.splitlines(keepends=True)
    filtered_lines = [
        line for line in lines if not _TOC_MARKER_LINE_RE.match(line.strip("\n"))
    ]
    cleaned = "".join(filtered_lines)

    # OSF Wiki sometimes appends non-standard size hints like " =50%x" inside
    # Markdown image links, which breaks rendering in MkDocs/Markdown.
    cleaned = _OSF_IMAGE_SIZE_SUFFIX_RE.sub(r"\1\2", cleaned)

    # Convert OSF embed markers (e.g. "@[osf](abcde)") into plain links.
    cleaned = _OSF_EMBED_RE.sub(r"[OSF](https://osf.io/\2/)", cleaned)

    prefix = _page_relative_prefix(page)

    # Rewrite OSF wiki links to local pages (prevents navigation to downloaded HTML stubs).
    cleaned = _rewrite_osf_wiki_links(cleaned, prefix=prefix)

    manifest = _load_osf_manifest(config)
    if manifest:
        for url, rel_path in manifest.items():
            if _is_osf_wiki_url(url):
                continue
            cleaned = cleaned.replace(url, prefix + rel_path)

    missing = _load_osf_missing(config)
    if missing:
        cleaned = _replace_blocked_osf_images(cleaned, missing, prefix=prefix)

    return cleaned


def _load_osf_manifest(config):
    global _OSF_MANIFEST_CACHE
    global _OSF_MANIFEST_LOADED

    if _OSF_MANIFEST_LOADED:
        return _OSF_MANIFEST_CACHE

    _OSF_MANIFEST_LOADED = True
    docs_dir = config.get("docs_dir") or "docs"
    manifest_path = (
        Path(os.path.abspath(docs_dir)) / "assets" / "osf" / "manifest.json"
    )
    if not manifest_path.exists():
        _OSF_MANIFEST_CACHE = None
        return None

    try:
        _OSF_MANIFEST_CACHE = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        _OSF_MANIFEST_CACHE = None
    return _OSF_MANIFEST_CACHE


def _is_osf_url(url: str) -> bool:
    return url.startswith("https://files.osf.io/") or url.startswith("https://osf.io/")


def _is_osf_wiki_url(url: str) -> bool:
    return url.startswith("https://osf.io/") and "/wiki/" in url


def _page_relative_prefix(page) -> str:
    try:
        src_path = getattr(page.file, "src_path", "") or ""
    except Exception:
        src_path = ""
    page_dir = os.path.dirname(src_path).strip("/\\")
    if not page_dir:
        return ""
    depth = len([p for p in re.split(r"[\\/]+", page_dir) if p and p != "."])
    return "../" * depth


def _load_osf_missing(config):
    global _OSF_MISSING_CACHE
    global _OSF_MISSING_LOADED

    if _OSF_MISSING_LOADED:
        return _OSF_MISSING_CACHE

    _OSF_MISSING_LOADED = True
    docs_dir = config.get("docs_dir") or "docs"
    missing_path = (
        Path(os.path.abspath(docs_dir)) / "assets" / "osf" / "missing_assets.json"
    )
    if not missing_path.exists():
        _OSF_MISSING_CACHE = None
        return None

    try:
        payload = json.loads(missing_path.read_text(encoding="utf-8"))
        # File is a dict keyed by URL.
        if isinstance(payload, dict):
            _OSF_MISSING_CACHE = set(payload.keys())
        else:
            _OSF_MISSING_CACHE = None
    except Exception:
        _OSF_MISSING_CACHE = None
    return _OSF_MISSING_CACHE


def _replace_blocked_osf_images(markdown: str, blocked_urls: set, *, prefix: str) -> str:
    dir_prefix = prefix

    def md_repl(m):
        img_prefix, url, suffix = m.group(1), m.group(2), m.group(3)
        if url in blocked_urls:
            return f"{img_prefix}{dir_prefix + _OSF_PLACEHOLDER}{suffix}"
        return m.group(0)

    def html_repl(m):
        img_prefix, url, suffix = m.group(1), m.group(2), m.group(3)
        if url in blocked_urls:
            return f"{img_prefix}{dir_prefix + _OSF_PLACEHOLDER}{suffix}"
        return m.group(0)

    out = _OSF_URL_IN_MD_IMAGE_RE.sub(md_repl, markdown)
    out = _OSF_URL_IN_HTML_IMG_RE.sub(html_repl, out)
    return out


def _rewrite_osf_wiki_links(markdown: str, *, prefix: str) -> str:
    """
    Rewrite links like:
      https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
    to local MkDocs pages.
    """

    def repl(m):
        tail = m.group(2)  # e.g. "4.%20Using%20the%20Tool%20-%20Output/"
        decoded = urllib.parse.unquote(tail).rstrip("/")
        key = decoded.lower()
        doc = _OSF_WIKI_PAGE_TO_DOC.get(key)
        if not doc:
            return m.group(0)
        return prefix + doc

    return _OSF_WIKI_URL_RE.sub(repl, markdown)
