"""Build CHM13 context opportunities from registered TSB files and CDS intervals."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from SigProfilerMatrixGenerator.scripts.reference_genome_manager import CHECKSUMS
from tools.build_reference_archive import validate_reference_directory


CONTEXTS = ("6", "24", "96", "384", "1536", "6144", "DBS", "DBS186")
CHROMOSOMES = ["X", "Y", *map(str, range(1, 23))]
BASES = "ACGT"
STATES = "NTUB"
DINUC = ("AA", "AC", "AG", "AT", "CA", "CC", "CG", "GA", "GC", "TA")


def reverse_complement(sequence):
    return sequence.translate(str.maketrans("ACGT", "TGCA"))[::-1]


def labels(width):
    rows = []
    for code in range(4 ** width):
        sequence = "".join(BASES[(code >> (2 * offset)) & 3]
                           for offset in reversed(range(width)))
        for state in STATES:
            if width == 5:
                if sequence[2] in "AG":
                    canonical = reverse_complement(sequence)
                    bias = {"N": "N", "T": "U", "U": "T", "B": "B"}[state]
                else:
                    canonical, bias = sequence, state
            else:
                canonical = sequence if sequence in DINUC else reverse_complement(sequence)
                bias = state if sequence in DINUC else {"N": "N", "T": "U", "U": "T", "B": "B"}[state]
                if canonical not in ("AA", "AG", "CC", "GA"):
                    bias = "Q"
            rows.append(f"{bias}:{canonical}")
    return rows


def read_intervals(path):
    intervals = defaultdict(list)
    with Path(path).open() as handle:
        for line in handle:
            if not line.strip() or line.startswith(("@", "#")):
                continue
            row = line.split()
            chrom = row[0].removeprefix("chr")
            start, end = int(row[1]) - 1, int(row[2])
            if chrom not in CHROMOSOMES or not 0 <= start < end:
                raise ValueError(f"Invalid CHM13 interval: {line.strip()}")
            if intervals[chrom] and start < intervals[chrom][-1][1]:
                raise ValueError(f"Overlapping or unsorted intervals: {line.strip()}")
            intervals[chrom].append((start, end))
    return intervals


def primitive_counts(encoded, intervals=None, chunk_size=1_000_000):
    """Count five-base SBS and two-base DBS windows with bounded memory."""
    encoded = np.asarray(encoded, dtype=np.uint8)
    if np.any(encoded >= 20):
        raise ValueError("Invalid TSB encoding")
    coverage = None
    if intervals is not None:
        coverage = np.zeros(len(encoded), dtype=bool)
        for start, end in intervals:
            if not 0 <= start < end <= len(encoded):
                raise ValueError("Interval outside chromosome")
            coverage[start:end] = True
    result = {}
    for width in (5, 2):
        raw = np.zeros(4 ** width * 4, dtype=np.int64)
        for start in range(0, max(0, len(encoded) - width + 1), chunk_size):
            end = min(start + chunk_size, len(encoded) - width + 1)
            valid = np.ones(end - start, dtype=bool)
            key = np.zeros(end - start, dtype=np.int64)
            for offset in range(width):
                values = encoded[start + offset:end + offset]
                valid &= values < 16
                if coverage is not None:
                    valid &= coverage[start + offset:end + offset]
                key = key * 4 + values % 4
            state = encoded[start + width // 2:end + width // 2] // 4
            key = key * 4 + state
            raw += np.bincount(key[valid], minlength=len(raw))
        canonical = defaultdict(int)
        for label, count in zip(labels(width), raw):
            canonical[label] += int(count)
        result["6144" if width == 5 else "DBS186"] = dict(sorted(canonical.items()))
    return result


def collapse_counts(primitive):
    result = {"6144": primitive["6144"], "DBS186": primitive["DBS186"]}
    for context in CONTEXTS:
        if context in result:
            continue
        counts = defaultdict(int)
        source = primitive["DBS186"] if context == "DBS" else primitive["6144"]
        for label, count in source.items():
            bias, sequence = label.split(":")
            if context in ("6", "24"):
                sequence = sequence[2]
            elif context in ("96", "384"):
                sequence = sequence[1:4]
            key = f"{bias}:{sequence}" if context in ("24", "384") else sequence
            counts[key] += count
        result[context] = dict(sorted(counts.items()))
    return result


def write_tables(output, counts, chromosomes=CHROMOSOMES):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for mode in ("whole_genome", "exome"):
        suffix = "_exome" if mode == "exome" else ""
        for context in CONTEXTS:
            rows = counts[mode][chromosomes[0]][context]
            count_path = output / f"context_counts_CHM13-T2T_{context}{suffix}.csv"
            with count_path.open("w", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow([" ", *chromosomes])
                for label in rows:
                    writer.writerow([label, *[counts[mode][chrom][context][label] for chrom in chromosomes]])
            for gender in ("male", "female"):
                selected = [chrom for chrom in chromosomes if gender == "male" or chrom != "Y"]
                path = output / f"context_distribution_CHM13-T2T_{context}_{gender}{suffix}.csv"
                with path.open("w", newline="") as handle:
                    writer = csv.writer(handle, lineterminator="\n")
                    writer.writerow([" ", *selected])
                    for label in rows:
                        values = [counts[mode][chrom][context][label] for chrom in selected]
                        total = sum(values)
                        writer.writerow([label, *[value / total if total else 0 for value in values]])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True, help="Installed CHM13-T2T payload directory")
    parser.add_argument("--exome", type=Path, required=True, help="One-based inclusive CHM13 CDS interval list")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    validate_reference_directory(args.reference, CHECKSUMS["CHM13-T2T"], "CHM13-T2T")
    intervals = read_intervals(args.exome)
    counts = {"whole_genome": {}, "exome": {}}
    for chrom in CHROMOSOMES:
        encoded = np.memmap(args.reference / f"{chrom}.txt", dtype=np.uint8, mode="r")
        counts["whole_genome"][chrom] = collapse_counts(primitive_counts(encoded))
        counts["exome"][chrom] = collapse_counts(primitive_counts(encoded, intervals.get(chrom, [])))
        print(f"Validated reference opportunities counted: {chrom}", flush=True)
    write_tables(args.output, counts)


if __name__ == "__main__":
    main()
