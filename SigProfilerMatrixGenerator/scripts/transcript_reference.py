"""Shared reader for one-based, inclusive transcript reference records."""

from pathlib import Path
from typing import NamedTuple


class Transcript(NamedTuple):
    gene_id: str
    transcript_id: str
    chromosome: str
    strand: str
    start: int
    end: int
    gene_name: str


def iter_transcripts(transcript_path):
    """Read combined or per-chromosome files, with or without a header.

    The six required columns are gene ID, transcript ID, chromosome, strand
    (1 or -1), start, and end. An optional seventh column supplies the gene
    name; otherwise the stable gene ID is used.
    """
    for transcript_file in sorted(Path(transcript_path).iterdir()):
        if transcript_file.name.startswith(".") or not transcript_file.is_file():
            continue
        with transcript_file.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                tab_fields = line.rstrip("\r\n").split("\t")
                fields = tab_fields if len(tab_fields) >= 6 else line.split()
                location = f"{transcript_file}:{line_number}"
                if len(fields) < 6:
                    raise ValueError(f"{location} has fewer than six columns.")
                try:
                    start, end = int(fields[4]), int(fields[5])
                except ValueError:
                    if "start" in fields[4].lower() and "end" in fields[5].lower():
                        continue
                    raise ValueError(f"{location} has invalid coordinates.") from None
                strand = fields[3]
                if strand not in {"1", "-1"}:
                    raise ValueError(
                        f"{location} has unsupported strand {strand!r}; "
                        "expected '1' or '-1'."
                    )
                if start < 1 or end < start:
                    raise ValueError(f"{location} has invalid interval {start}-{end}.")
                gene_name = fields[6].strip() if len(fields) > 6 else ""
                yield Transcript(
                    fields[0],
                    fields[1],
                    fields[2],
                    strand,
                    start,
                    end,
                    gene_name or fields[0],
                )
