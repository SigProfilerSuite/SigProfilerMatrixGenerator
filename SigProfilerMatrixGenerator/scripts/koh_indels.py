"""Koh et al. (2025) ID89/ID476 counts, independent of the legacy ID83 path.

Taxonomy: doi:10.1038/s41588-025-02152-y. Segmentation and channel rules
adapted from the MIT-licensed Nik-Zainal-Group/indelsig.tools.lib at d0bdb9b.
See reference_data/indel_taxonomy/README.md and LICENSE.indelsig.tools.lib.
"""

from dataclasses import dataclass
from bisect import bisect_right
from collections import Counter
import csv
import mmap
from pathlib import Path

import pandas as pd


def _channels_476():
    rows = []
    for operation, repeats in (
        ("Del", tuple(range(1, 9)) + ("(9,)",)),
        ("Ins", tuple(range(9)) + ("(9,)",)),
    ):
        for base, flanks in (("C", "AGT"), ("T", "ACG")):
            for left in flanks:
                for repeat in repeats:
                    for right in flanks:
                        rows.append(f"{left}[{operation}({base}):R{repeat}]{right}")
    for unit in ("1", "(2,)"):
        rows.extend(f"Del{length}:U{unit}:R1" for length in (*range(2, 10), "(10,)"))
    rows.extend(
        (
            "Del2:U1:R3",
            "Del2:U1:R4",
            "Del2:U1:R(5,)",
            "Del2:U2:R2",
            "Del2:U2:R3",
            "Del2:U2:R4",
            "Del2:U2:R(5,)",
            "Del3:U1:R4",
            "Del3:U1:R(5,)",
            "Del3:U3:R2",
            "Del3:U3:R3",
            "Del3:U3:R4",
            "Del3:U3:R(5,)",
            "Del4:U1:R(5,)",
            "Del4:U2:R3",
            "Del4:U2:R4",
            "Del4:U2:R(5,)",
            "Del4:U4:R2",
            "Del4:U4:R3",
            "Del4:U4:R4",
            "Del4:U4:R(5,)",
            "Del5:U1:R(5,)",
            "Del5:U5:R2",
            "Del5:U5:R3",
            "Del5:U5:R4",
            "Del5:U5:R(5,)",
            "Del(6,):U1:R(7,)",
            "Del(6,):U2:R(4,)",
            "Del(6,):U3:R(3,)",
            "Del(6,):U(4,):R(2,)",
            "Ins(2,4):M",
            "Ins(5,):M",
            "Ins2:U1:R0",
            "Ins3:U1:R0",
            "Ins4:U1:R0",
            "Ins2:U2:R0",
            "Ins3:U3:R0",
            "Ins4:U2:R0",
            "Ins4:U4:R0",
            "Ins(5,):R0",
        )
    )
    for length, units in (
        (2, (1, 2)),
        (3, (1, 3)),
        (4, (1, 2, 4)),
        ("(5,)", (1, 2, "(3,)")),
    ):
        for unit in units:
            rows.extend(
                f"Ins{length}:U{unit}:R{repeat}" for repeat in (1, 2, 3, 4, "(5,)")
            )
    for length in range(2, 7):
        rows.extend(f"Del{length}:M{mh}" for mh in range(1, length))
    rows.extend(f"Del(7,):M{mh}" for mh in (1, 2, 3, 4, 5, "(6,)"))
    rows.extend(
        f"Complex{interval}"
        for interval in ("(0,1)", "(2,5)", "(6,10)", "(11,20)", "(21,)")
    )
    return tuple(rows)


def _channels_89():
    rows = [
        f"[Del(C):R{repeat}]{right}" for repeat in (1, 2, 3, "(4,5)") for right in "AT"
    ]
    rows.extend(("[Del(C):R(1,5)]G", "Del(C):R(6,)"))
    rows.extend(
        f"{left}[Del(T):R{repeat}]{right}"
        for repeat in ("(1,4)", "(5,7)", "(8,)")
        for left in "ACG"
        for right in "ACG"
    )
    rows.extend(
        (
            "A[Ins(C):R0]A",
            "A[Ins(C):R0]T",
            "Ins(C):R(0,3)",
            "Ins(C):R(4,6)",
            "Ins(C):R(7,)",
        )
    )
    rows.extend(
        f"{left}[Ins(T):R{repeat}]{right}"
        for repeat in ("(0,4)", "(5,7)", "(8,)")
        for left in "ACG"
        for right in "ACG"
    )
    rows.extend(
        (
            "Del(2,4):R1",
            "Del(5,):R1",
            "Del(2,8):U(1,2):R(2,4)",
            "Del(2,):U(1,2):R(5,)",
            "Del(3,):U(3,):R2",
            "Del(3,):U(3,):R(3,)",
            "Ins(2,4):R0",
            "Ins(5,):R0",
            "Ins(2,4):R1",
            "Ins(5,):R1",
            "Ins(2,):R(2,4)",
            "Ins(2,):R(5,)",
            "Del(2,5):M1",
            "Del(3,5):M2",
            "Del(4,5):M(3,4)",
            "Del(6,):M1",
            "Del(6,):M2",
            "Del(6,):M3",
            "Del(6,):M(4,)",
            "Complex",
        )
    )
    return tuple(rows)


ID476_CHANNELS = _channels_476()
ID89_CHANNELS = _channels_89()
_ID476_SET = frozenset(ID476_CHANNELS)
_ID89_SET = frozenset(ID89_CHANNELS)
_COMPLEMENT = str.maketrans("ACGT", "TGCA")
_DECODE = bytes.maketrans(bytes(range(20)), b"ACGTACGTACGTACGTNNNN")


class IndelClassificationError(ValueError):
    """An event cannot be assigned without guessing its sequence or context."""


@dataclass(frozen=True)
class Classification:
    id89: str
    id476: str
    position: int
    reference: str
    alternate: str
    repeats: int
    unit_length: int
    microhomology: int


class EncodedReference:
    """Decode only requested slices of the registered binary chromosome."""

    def __init__(self, path):
        self._file = open(path, "rb")
        try:
            self._data = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        except BaseException:
            self._file.close()
            raise

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        value = self._data[key]
        if isinstance(key, slice):
            return value.translate(_DECODE).decode("ascii")
        return chr(_DECODE[value])

    def close(self):
        self._data.close()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _repeat_bases(sequence, position, unit):
    start = position
    size = len(unit)
    while position + size <= len(sequence):
        observed = sequence[position : position + size]
        if observed == unit:
            position += size
            continue
        for base, expected in zip(observed, unit):
            if base not in "ACGT":
                raise IndelClassificationError("ambiguous_sequence_context")
            if base != expected:
                break
        break
    return position - start


def _segment(word, sequence, position):
    # Match the published priority: flanking coverage, internal coverage,
    # smaller spacer, then smaller unit. Scores measure bases, not repeat counts.
    best = None
    for size in range(1, len(word) + 1):
        unit = word[:size]
        internal = _repeat_bases(word, size, unit)
        spacer = len(word) - size - internal
        external = _repeat_bases(sequence, position, unit)
        score = (external, internal, -spacer, -size)
        if best is None or score > best[0]:
            best = (score, size, internal // size, spacer, external // size)
    return best[1:]


def _mono89(operation, base, repeat, left, right):
    if base == "C":
        if operation == "Ins":
            if repeat == 0 and left == "A" and right in "AT":
                return f"A[Ins(C):R0]{right}"
            interval = "(0,3)" if repeat <= 3 else "(4,6)" if repeat <= 6 else "(7,)"
            return f"Ins(C):R{interval}"
        if repeat >= 6:
            return "Del(C):R(6,)"
        if right == "G":
            return "[Del(C):R(1,5)]G"
        interval = repeat if repeat <= 3 else "(4,5)"
        return f"[Del(C):R{interval}]{right}"
    interval = (
        ("(0,4)" if operation == "Ins" else "(1,4)")
        if repeat <= 4
        else "(5,7)" if repeat <= 7 else "(8,)"
    )
    return f"{left}[{operation}(T):R{interval}]{right}"


def _multi_labels(operation, length, unit, internal, spacer, external):
    repeat = external if operation == "Ins" or spacer else internal + 1 + external
    if spacer and external:
        mh = min(length - spacer, unit * external)
        if operation == "Ins":
            size = "(2,4)" if length <= 4 else "(5,)"
            return f"Ins{size}:R0", f"Ins{size}:M", repeat, mh
        size = length if length <= 6 else "(7,)"
        micro = mh if mh <= 5 else "(6,)"
        label476 = f"Del{size}:M{micro}"
        if length <= 5:
            label89 = f"Del({min(mh + 1, 4)},5):M{mh if mh <= 2 else '(3,4)'}"
        else:
            label89 = f"Del(6,):M{mh if mh <= 3 else '(4,)'}"
        return label89, label476, repeat, mh

    if operation == "Ins":
        if spacer:
            # No repeated prefix in the flank: the entire inserted word is the unit.
            unit = length
        size = length if length <= 4 else "(5,)"
        rep = repeat if repeat <= 4 else "(5,)"
        if repeat == 0 and length >= 5:
            label476 = "Ins(5,):R0"
        else:
            u = unit if length <= 4 or unit <= 2 else "(3,)"
            label476 = f"Ins{size}:U{u}:R{rep}"
        if repeat <= 1:
            size89 = "(2,4)" if length <= 4 else "(5,)"
            label89 = f"Ins{size89}:R{repeat}"
        else:
            label89 = f"Ins(2,):R{'(2,4)' if repeat <= 4 else '(5,)'}"
        return label89, label476, repeat, 0

    if not external:
        size = length if length <= 9 else "(10,)"
        u = 1 if unit == 1 else "(2,)"
        return (
            f"Del{'(2,4)' if length <= 4 else '(5,)'}:R1",
            f"Del{size}:U{u}:R1",
            repeat,
            0,
        )
    if length <= 5:
        label476 = f"Del{length}:U{unit}:R{repeat if repeat <= 4 else '(5,)'}"
    else:
        suffix = {1: "U1:R(7,)", 2: "U2:R(4,)", 3: "U3:R(3,)"}.get(unit, "U(4,):R(2,)")
        label476 = f"Del(6,):{suffix}"
    if unit <= 2:
        label89 = f"Del{'(2,8):U(1,2):R(2,4)' if repeat <= 4 else '(2,):U(1,2):R(5,)'}"
    else:
        label89 = f"Del(3,):U(3,):R{'2' if repeat == 2 else '(3,)'}"
    return label89, label476, repeat, 0


def classify_indel(sequence, position, reference, alternate):
    """Classify a literal VCF allele using 1-based coordinates and forward DNA.

    Prefix/suffix trimming and left alignment affect classification only.
    Region selection must use the original input coordinates separately.
    Ambiguous/symbolic/gapped alleles raise IndelClassificationError.
    """
    reference, alternate = reference.upper(), alternate.upper()
    if not reference or not alternate or set(reference + alternate) - set("ACGT"):
        raise IndelClassificationError("non_literal_or_ambiguous_allele")
    start = int(position) - 1
    if start < 0 or start + len(reference) > len(sequence):
        raise IndelClassificationError("reference_out_of_bounds")
    if sequence[start : start + len(reference)] != reference:
        raise IndelClassificationError("reference_allele_mismatch")
    if reference == alternate:
        raise IndelClassificationError("unchanged_allele")
    while reference and alternate and reference[0] == alternate[0]:
        reference, alternate, start = reference[1:], alternate[1:], start + 1
    while reference and alternate and reference[-1] == alternate[-1]:
        reference, alternate = reference[:-1], alternate[:-1]
    if reference and alternate:
        delta = abs(len(reference) - len(alternate))
        interval = next(
            label
            for limit, label in (
                (1, "(0,1)"),
                (5, "(2,5)"),
                (10, "(6,10)"),
                (20, "(11,20)"),
                (float("inf"), "(21,)"),
            )
            if delta <= limit
        )
        return Classification(
            "Complex", f"Complex{interval}", start + 1, reference, alternate, 0, 0, 0
        )
    operation = "Del" if reference else "Ins"
    word = reference or alternate
    # Rotate the changed word when shifting through an equivalent tandem repeat.
    while start > 1 and sequence[start - 1] == word[-1]:
        start -= 1
        word = word[-1] + word[:-1]
    right_position = start + len(word) if operation == "Del" else start
    if start == 0 or right_position >= len(sequence):
        raise IndelClassificationError("missing_sequence_context")
    unit, internal, spacer, external = _segment(word, sequence, right_position)
    if len(word) == 1:
        repeat = external + (operation == "Del")
        left = sequence[start - 1]
        if left == word:
            raise IndelClassificationError("missing_sequence_context")
        after = right_position + external
        if after >= len(sequence):
            raise IndelClassificationError("missing_sequence_context")
        right = sequence[after]
        if left not in "ACGT" or right not in "ACGT":
            raise IndelClassificationError("ambiguous_sequence_context")
        base = word
        if base in "AG":
            left, right, base = (
                right.translate(_COMPLEMENT),
                left.translate(_COMPLEMENT),
                base.translate(_COMPLEMENT),
            )
        label476 = (
            f"{left}[{operation}({base}):R{repeat if repeat < 9 else '(9,)'}]{right}"
        )
        label89 = _mono89(operation, base, repeat, left, right)
        mh = 0
    else:
        # Unknown flank bases must not terminate a potential repeat/MH as if
        # they were known mismatches. Inspect enough context to prove the result.
        context = sequence[
            right_position : min(len(sequence), right_position + len(word))
        ]
        if set(context) - set("ACGT"):
            raise IndelClassificationError("ambiguous_sequence_context")
        label89, label476, repeat, mh = _multi_labels(
            operation, len(word), unit, internal, spacer, external
        )
    if label476 not in _ID476_SET or label89 not in _ID89_SET:
        raise RuntimeError(f"Unregistered Koh channel: {label89}, {label476}")
    return Classification(
        label89,
        label476,
        start + 1,
        word if operation == "Del" else "",
        word if operation == "Ins" else "",
        int(repeat),
        unit,
        mh,
    )


def validate_contexts(contexts):
    if contexts is None:
        return ()
    if isinstance(contexts, str):
        contexts = (contexts,)
    result = []
    for value in contexts:
        value = str(value).upper().removeprefix("ID")
        if value not in ("89", "476"):
            raise ValueError(
                "indel_contexts must contain only '89' and/or '476'; ID83 is always retained"
            )
        if value not in result:
            result.append(value)
    return tuple(result)


class IntervalSelection:
    """Use the matrix API's original-coordinate, inclusive-anchor region rule.

    This deliberately does not change the historical API's BED convention.
    Left alignment for the new taxonomy never moves a call into/out of a panel.
    """

    def __init__(self, path, cushion, normalize_chromosome):
        self._intervals = {}
        self._starts = {}
        with open(path) as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip() or line.lstrip().startswith(
                    ("#", "@", "track", "browser")
                ):
                    continue
                fields = line.split()
                try:
                    chrom = normalize_chromosome(fields[0])
                    start, end = int(fields[1]), int(fields[2])
                except (IndexError, ValueError) as error:
                    raise ValueError(f"Invalid interval at {path}:{number}") from error
                if start < 0 or end < start:
                    raise ValueError(f"Invalid interval at {path}:{number}")
                self._intervals.setdefault(chrom, []).append(
                    (max(0, start - cushion), end + cushion)
                )
        for chrom, intervals in self._intervals.items():
            merged = []
            for start, end in sorted(intervals):
                if merged and start <= merged[-1][1] + 1:
                    merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                else:
                    merged.append((start, end))
            self._intervals[chrom] = merged
            self._starts[chrom] = [interval[0] for interval in merged]

    def contains(self, chrom, position):
        index = bisect_right(self._starts.get(chrom, ()), position) - 1
        return index >= 0 and position <= self._intervals[chrom][index][1]


class KohIndelCatalog:
    """Accumulate the two taxonomies without changing ID83 event accounting."""

    def __init__(
        self,
        contexts,
        samples,
        output,
        project,
        chromosome_directory,
        suffix="all",
        selection=None,
        chrom_based=False,
    ):
        self.contexts = contexts
        self.project = project
        self.output = Path(output) / "ID"
        self.output.mkdir(parents=True, exist_ok=True)
        self.chromosomes = Path(chromosome_directory)
        self.suffix = suffix
        self.selection = selection
        self.chrom_based = chrom_based
        self.summary = Counter()
        self.matrices = {
            f"ID{context}": pd.DataFrame(
                0,
                index=ID89_CHANNELS if context == "89" else ID476_CHANNELS,
                columns=samples,
                dtype="int64",
            ).rename_axis("MutationType")
            for context in contexts
        }
        self.report = self.output / f"{project}.ID89_ID476.classification.{suffix}.tsv"
        with self.report.open("w", newline="") as handle:
            csv.writer(handle, delimiter="\t").writerow(
                (
                    "Sample",
                    "Chromosome",
                    "InputPosition",
                    "REF",
                    "ALT",
                    "Status",
                    "NormalizedPosition",
                    "ID89",
                    "ID476",
                    "Repeats",
                    "UnitLength",
                    "Microhomology",
                )
            )

    def count_chromosome(self, chrom, lines):
        if not lines:
            return
        local = {key: frame * 0 for key, frame in self.matrices.items()}
        seen = set()
        with EncodedReference(
            self.chromosomes / f"{chrom}.txt"
        ) as sequence, self.report.open("a", newline="") as report:
            writer = csv.writer(report, delimiter="\t")
            for fields in lines:
                sample, _, position, reference, alternate = fields[:5]
                position = int(position)
                prefix = [sample, chrom, position, reference, alternate]
                if self.selection is not None and not self.selection.contains(
                    chrom, position
                ):
                    self.summary["outside_region"] += 1
                    writer.writerow(prefix + ["outside_region"] + [""] * 6)
                    continue
                try:
                    result = classify_indel(sequence, position, reference, alternate)
                except IndelClassificationError as error:
                    self.summary[str(error)] += 1
                    writer.writerow(prefix + [str(error)] + [""] * 6)
                    continue
                key = (sample, result.position, result.reference, result.alternate)
                status = "duplicate" if key in seen else "counted"
                self.summary[status] += 1
                writer.writerow(
                    prefix
                    + [
                        status,
                        result.position,
                        result.id89,
                        result.id476,
                        result.repeats,
                        result.unit_length,
                        result.microhomology,
                    ]
                )
                if status == "duplicate":
                    continue
                seen.add(key)
                for context, label in (("ID89", result.id89), ("ID476", result.id476)):
                    if context in local:
                        local[context].at[label, sample] += 1
        for key, frame in local.items():
            self.matrices[key] += frame
            if self.chrom_based:
                frame.to_csv(
                    self.output / f"{self.project}.{key}.{self.suffix}.chr{chrom}",
                    sep="\t",
                )

    def save(self, log_file):
        for key, frame in self.matrices.items():
            frame.to_csv(self.output / f"{self.project}.{key}.{self.suffix}", sep="\t")
        with open(log_file, "a") as handle:
            print(
                "Koh ID89/ID476 classification (independent of ID83):",
                dict(self.summary),
                file=handle,
            )
            print("Koh classification report:", self.report, file=handle)
        return self.matrices
