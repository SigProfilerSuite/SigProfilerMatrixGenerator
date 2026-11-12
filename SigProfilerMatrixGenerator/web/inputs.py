"""Recognize a folder of mutation input files before a run starts.

Recognition follows SigProfilerMatrixGeneratorFunc's own rules rather than
sniffing contents: it reads every regular file in one folder (falling back to
an input/ subfolder, the historical project layout), skips names starting
with "__" or ".DS", and picks a converter by file extension.
"""

from __future__ import annotations

import re
from pathlib import Path

RECOGNIZED_EXTENSIONS = {".vcf": "VCF", ".maf": "MAF", ".txt": "Txt", ".genome": "Txt"}
PREVIEW_SAMPLES = 6


class InputError(ValueError):
    pass


def browse(path: str) -> dict:
    """List a directory's entries, for a folder picker's own listing view."""
    target = Path(path)
    if not target.is_dir():
        raise InputError(f"not a directory: {path}")
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        if child.name.startswith("."):
            continue
        entries.append({"name": child.name, "is_dir": child.is_dir()})
    return {"path": str(target), "entries": entries}


def _skipped_by_generator(name: str) -> bool:
    # The same filter SigProfilerMatrixGeneratorFunc applies to its input files.
    return name.startswith("__") or name.startswith(".DS")


def _input_files(folder: Path) -> tuple[Path, list[Path]]:
    files = sorted(p for p in folder.iterdir() if p.is_file() and not _skipped_by_generator(p.name))
    legacy = folder / "input"
    if not files and legacy.is_dir():
        return legacy, _input_files(legacy)[1]
    return folder, files


# How inputs commonly name an assembly, mapped to this package's genome names.
_ASSEMBLY_ALIASES = {
    "grch37": "GRCh37", "37": "GRCh37", "hg19": "GRCh37", "b37": "GRCh37", "hs37d5": "GRCh37",
    "grch38": "GRCh38", "38": "GRCh38", "hg38": "GRCh38",
    "chm13": "CHM13-T2T", "chm13-t2t": "CHM13-T2T", "t2t-chm13": "CHM13-T2T",
    "chm13v2": "CHM13-T2T", "t2t": "CHM13-T2T", "hs1": "CHM13-T2T",
    "mm9": "mm9", "mm10": "mm10", "grcm38": "mm10", "mm39": "mm39", "grcm39": "mm39",
    "rn6": "rn6", "rn7": "rn7",
}


def assembly_of(raw: str) -> str | None:
    """The assembly a declared name refers to, or None if it is not clear."""
    token = raw.strip().lower()
    if token in _ASSEMBLY_ALIASES:
        return _ASSEMBLY_ALIASES[token]
    # A VCF ##reference value is usually a path or URL: look for a known name
    # inside it as a whole word. Bare numbers ("37") are too easy to hit by
    # accident there, so only longer names count.
    hits = {
        assembly for alias, assembly in _ASSEMBLY_ALIASES.items()
        if len(alias) > 2 and re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", token)
    }
    return hits.pop() if len(hits) == 1 else None


def _is_indel(ref: str, alt: str) -> bool:
    # VCF indels carry an anchor base (A>AT); MAF and simple text use "-".
    alt = alt.split(",")[0]
    return ref in ("-", "") or alt in ("-", "") or len(ref) != len(alt)


def _scan_vcf(path: Path, samples: set, preview: list, declared: set, counts: dict) -> None:
    name = path.name.split(".")[0]
    if name not in samples and len(preview) < PREVIEW_SAMPLES:
        preview.append(name)
    samples.add(name)
    with open(path, "r", errors="replace") as handle:
        for line in handle:
            if line.startswith("##reference=") or line.startswith("##assembly="):
                declared.add(line.split("=", 1)[1].strip())
            elif line.strip() and not line.startswith("#"):
                counts["records"] += 1
                fields = line.split("\t")
                if len(fields) > 4 and _is_indel(fields[3].strip(), fields[4].strip()):
                    counts["indels"] += 1


# Where convertMAF() and convertTxt() read each field (0-based).
_LAYOUTS = {
    # MAF: header row; Tumor_Sample_Barcode is column 16, NCBI_Build 4,
    # Reference_Allele 11 and Tumor_Seq_Allele2 13.
    "MAF": {"sep": "\t", "header": True, "sample": 15, "assembly": 3, "ref": 10, "alt": 12},
    # Simple text, whitespace separated: project, sample, ID, genome, type,
    # chromosome, start, end, ref, alt.
    "Txt": {"sep": None, "header": False, "sample": 1, "assembly": 3, "ref": 8, "alt": 9},
}


def _scan_columns(path: Path, layout: dict, samples: set, preview: list,
                  declared: set, counts: dict) -> None:
    sep, column = layout["sep"], layout["sample"]
    header_pending = layout["header"]
    ref_col, alt_col = layout["ref"], layout["alt"]
    with open(path, "r", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            if header_pending:
                header_pending = False
                continue
            fields = line.rstrip("\n").split(sep)
            if len(fields) <= column:
                continue
            counts["records"] += 1
            sample = fields[column]
            if sample not in samples:
                samples.add(sample)
                if len(preview) < PREVIEW_SAMPLES:
                    preview.append(sample)
            if len(fields) > layout["assembly"] and len(declared) < 10:
                declared.add(fields[layout["assembly"]])
            if len(fields) > max(ref_col, alt_col) and _is_indel(fields[ref_col], fields[alt_col]):
                counts["indels"] += 1


def inspect(path: str) -> dict:
    """Recognize the mutation input at ``path``: format, files, samples, records."""
    target = Path(path)
    if target.is_file():
        raise InputError(
            "SigProfilerMatrixGenerator reads every file in a folder, so choose "
            f"the folder that holds this file instead: {target.parent}"
        )
    if not target.is_dir():
        raise InputError(f"this folder does not exist: {path}")

    source, files = _input_files(target)
    by_format: dict[str, list[Path]] = {}
    other: list[str] = []
    for file in files:
        file_format = RECOGNIZED_EXTENSIONS.get(file.suffix.lower())
        if file_format:
            by_format.setdefault(file_format, []).append(file)
        elif not file.name.startswith("."):
            other.append(file.name)

    if not by_format:
        raise InputError(
            f"no .vcf, .maf or .txt files in {source}. (The ICGC .tsv format "
            "is no longer supported; convert it to VCF, MAF or Txt first.)"
        )
    if len(by_format) > 1:
        found = ", ".join(sorted(by_format))
        raise InputError(
            f"this folder mixes formats ({found}). SigProfilerMatrixGenerator "
            "reads one format per run, so put each format in its own folder."
        )

    (file_format, matched), = by_format.items()
    samples: set = set()
    preview: list = []
    declared: set = set()
    counts = {"records": 0, "indels": 0}
    for file in matched:
        if file_format == "VCF":
            # One sample per VCF, named after the file, as convertVCF() does.
            # The assembly, if any, is in a ##reference or ##assembly header.
            _scan_vcf(file, samples, preview, declared, counts)
        else:
            _scan_columns(file, _LAYOUTS[file_format], samples, preview, declared, counts)

    # The assembly the calls say they were made against, when they all agree.
    assemblies = {assembly_of(value) for value in declared}
    assembly = assemblies.pop() if len(assemblies) == 1 else None

    return {
        "assembly": assembly,
        "declared_assembly": sorted(declared)[:3],
        "path": str(target),
        "source": str(source),
        "format": file_format,
        "file_count": len(matched),
        "sample_count": len(samples),
        "samples_preview": preview[:PREVIEW_SAMPLES],
        "records": counts["records"],
        # Insertions and deletions among them: without any, a run makes no ID
        # matrices (and ID89/ID476, when asked for, are all zeros).
        "indels": counts["indels"],
        "other_files": other[:5],
        "other_count": len(other),
    }
