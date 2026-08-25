#!/usr/bin/env python3

# Author: Erik Bergstrom
# Contact: ebergstr@eng.ucsd.edu

import time
from collections import defaultdict
from pathlib import Path


_ENCODING_TABLES = {
    "N": bytes.maketrans(b"ACGTN", bytes([0, 1, 2, 3, 16])),
    "T": bytes.maketrans(b"ACGTN", bytes([4, 5, 6, 7, 17])),
    "U": bytes.maketrans(b"ACGTN", bytes([8, 9, 10, 11, 18])),
    "B": bytes.maketrans(b"ACGTN", bytes([12, 13, 14, 15, 19])),
}
_VALID_BASES = frozenset("ACGTN")
_CHUNK_SIZE = 1024 * 1024


def _chromosome_aliases(chromosome):
    aliases = [chromosome]
    if chromosome.startswith("chr"):
        aliases.append(chromosome[3:])
    else:
        aliases.append(f"chr{chromosome}")

    if chromosome in {"M", "MT", "chrM", "chrMT"}:
        aliases.extend(["M", "MT", "chrM", "chrMT"])

    return dict.fromkeys(aliases)


def _resolve_chromosome_name(chromosome, chromosome_string_path):
    for alias in _chromosome_aliases(chromosome):
        if (chromosome_string_path / f"{alias}.txt").exists():
            return alias

    raise ValueError(
        f"Transcript chromosome {chromosome!r} has no matching chromosome "
        f"sequence file in {chromosome_string_path}."
    )


def _split_transcript_line(line):
    tab_fields = line.rstrip("\n").split("\t")
    return tab_fields if len(tab_fields) >= 6 else line.split()


def _load_transcripts(transcript_path, chromosome_string_path):
    transcripts = defaultdict(list)

    for transcript_file in sorted(transcript_path.iterdir()):
        if transcript_file.name.startswith(".") or not transcript_file.is_file():
            continue

        with transcript_file.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue

                fields = _split_transcript_line(line)
                if len(fields) < 6:
                    raise ValueError(
                        f"{transcript_file}:{line_number} has fewer than six columns."
                    )

                try:
                    start = int(fields[4])
                    end = int(fields[5])
                except ValueError:
                    is_header = (
                        "start" in fields[4].lower() and "end" in fields[5].lower()
                    )
                    if is_header:
                        continue
                    raise ValueError(
                        f"{transcript_file}:{line_number} has invalid coordinates."
                    ) from None

                strand = fields[3]
                if strand not in {"1", "-1"}:
                    raise ValueError(
                        f"{transcript_file}:{line_number} has unsupported strand "
                        f"{strand!r}; expected '1' or '-1'."
                    )
                if start < 1 or end < start:
                    raise ValueError(
                        f"{transcript_file}:{line_number} has invalid interval "
                        f"{start}-{end}."
                    )

                chromosome = _resolve_chromosome_name(
                    fields[2], chromosome_string_path
                )
                # Transcript coordinates are one-based and inclusive. Converting
                # to a zero-based half-open interval preserves the final base.
                transcripts[chromosome].append((start - 1, end, strand))

    return transcripts


def _transcription_state(plus_strand_count, minus_strand_count):
    if plus_strand_count and minus_strand_count:
        return "B"
    if plus_strand_count:
        return "U"
    if minus_strand_count:
        return "T"
    return "N"


def _write_encoded_segment(handle, sequence, start, end, state):
    encoding_table = _ENCODING_TABLES[state]
    for chunk_start in range(start, end, _CHUNK_SIZE):
        chunk_end = min(chunk_start + _CHUNK_SIZE, end)
        chunk = sequence[chunk_start:chunk_end]
        handle.write(chunk.encode("ascii").translate(encoding_table))


def _write_chromosome_tsb(sequence, intervals, output_file):
    invalid_bases = set(sequence) - _VALID_BASES
    if invalid_bases:
        raise ValueError(
            f"{output_file.name} contains unsupported bases: "
            f"{', '.join(sorted(invalid_bases))}."
        )

    events = defaultdict(lambda: [0, 0])
    for start, end, strand in intervals:
        if end > len(sequence):
            raise ValueError(
                f"Transcript interval {start + 1}-{end} exceeds chromosome length "
                f"{len(sequence)} for {output_file.stem}."
            )
        strand_index = 0 if strand == "1" else 1
        events[start][strand_index] += 1
        events[end][strand_index] -= 1

    temporary_output = output_file.with_suffix(output_file.suffix + ".tmp")
    plus_strand_count = 0
    minus_strand_count = 0
    previous_position = 0

    try:
        with temporary_output.open("wb") as handle:
            for position in sorted(events):
                state = _transcription_state(
                    plus_strand_count, minus_strand_count
                )
                _write_encoded_segment(
                    handle, sequence, previous_position, position, state
                )

                plus_delta, minus_delta = events[position]
                plus_strand_count += plus_delta
                minus_strand_count += minus_delta
                if plus_strand_count < 0 or minus_strand_count < 0:
                    raise ValueError(
                        f"Invalid transcript event counts for {output_file.stem} "
                        f"at zero-based position {position}."
                    )
                previous_position = position

            state = _transcription_state(plus_strand_count, minus_strand_count)
            _write_encoded_segment(
                handle, sequence, previous_position, len(sequence), state
            )

        if plus_strand_count or minus_strand_count:
            raise ValueError(
                f"Unbalanced transcript intervals for {output_file.stem}."
            )
        temporary_output.replace(output_file)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        raise


def save_tsb(chromosome_string_path, transcript_path, output_path):
    """Create one binary transcriptional-strand-bias file per chromosome.

    Chromosome sequence files must be named ``<chromosome>.txt`` and contain an
    A/C/G/T/N sequence. Transcript files may be combined or split by chromosome.
    Their first six whitespace-delimited columns must be gene ID, transcript ID,
    chromosome, strand (1 or -1), one-based inclusive start, and one-based
    inclusive end.
    """

    start_time = time.time()
    chromosome_string_path = Path(chromosome_string_path)
    transcript_path = Path(transcript_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    chromosome_files = sorted(
        path
        for path in chromosome_string_path.glob("*.txt")
        if not path.name.startswith(".")
    )
    if not chromosome_files:
        raise ValueError(
            f"No chromosome sequence files were found in {chromosome_string_path}."
        )

    transcripts = _load_transcripts(transcript_path, chromosome_string_path)

    print("Creating the transcriptional reference files now. This may take awhile...")
    chromosome_total = len(chromosome_files)
    for index, chromosome_file in enumerate(chromosome_files, start=1):
        chromosome = chromosome_file.stem
        sequence = "".join(chromosome_file.read_text().split()).upper()
        output_file = output_path / f"{chromosome}.txt"
        _write_chromosome_tsb(
            sequence, transcripts.get(chromosome, []), output_file
        )
        print(
            "The transcript reference file has been created for Chromosome: "
            f"{chromosome} ({index}/{chromosome_total})"
        )

    print(f"Transcript files created.\n Job took: {time.time() - start_time} seconds")
