import argparse
from pathlib import Path


def _write_text_exact(path: Path, content: str) -> None:
    if content and not content.endswith("\n"):
        content += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy mirrored OSF wiki pages from docs/osf_wiki into the main docs/*.md files used by mkdocs.yml nav.",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs",
        help="Docs directory (default: docs).",
    )
    parser.add_argument(
        "--osf-wiki-dir",
        default="docs/osf_wiki",
        help="Mirrored OSF wiki directory (default: docs/osf_wiki).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing files.",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir)
    osf_dir = Path(args.osf_wiki_dir)
    if not docs_dir.exists():
        raise SystemExit(f"docs dir not found: {docs_dir}")
    if not osf_dir.exists():
        raise SystemExit(
            f"OSF wiki dir not found: {osf_dir}. Run tools/mirror_osf_wiki.py first."
        )

    mapping = {
        # Home
        "home.md": "index.md",
        # Getting started
        "6. Quick Start Example.md": "Quick-Start-Example.md",
        # Installation
        "1. Installation - Python.md": "Installation-Python.md",
        "2. Installation - R.md": "Installation-R.md",
        "7. Currently Supported Genomes.md": "Currently-Supported-Genomes.md",
        # Usage
        "3. Using the Tool - SBS, ID, DBS Input.md": "Using-the-Tool-SBS-ID-DBS-Input.md",
        "3. Using the Tool - CNV Input.md": "Using-the-Tool-CNV-Input.md",
        "3. Using the Tool - SV Input.md": "Using-the-Tool-SV-Input.md",
        "4. Using the Tool - Output.md": "Using-the-Tool-Output.md",
        # Output reference
        "5. Output - SBS.md": "Output-SBS.md",
        "5. Output - DBS.md": "Output-DBS.md",
        "5. Output - ID.md": "Output-ID.md",
        "5. Output - TSB.md": "Output-TSB.md",
        "5. Output - vcf_files.md": "Output-vcf_files.md",
        "5. Output - Plots.md": "Output-Plots.md",
        # Additional outputs available in OSF
        "5. Output - CNV.md": "Output-CNV.md",
        "5. Output - SV.md": "Output-SV.md",
    }

    missing_sources = []
    for src_name in mapping:
        src_path = osf_dir / src_name
        if not src_path.exists():
            missing_sources.append(src_name)
    if missing_sources:
        raise SystemExit(
            "Missing expected OSF wiki pages:\n"
            + "\n".join(f"- {name}" for name in missing_sources)
        )

    changed = 0
    for src_name, dst_name in mapping.items():
        src_path = osf_dir / src_name
        dst_path = docs_dir / dst_name
        content = src_path.read_text(encoding="utf-8")

        if args.dry_run:
            print(f"{src_path} -> {dst_path}")
            continue

        _write_text_exact(dst_path, content)
        changed += 1

    if not args.dry_run:
        print(f"Updated {changed} docs pages from {osf_dir}")
        print("Preview with: python3 -m mkdocs serve")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

