"""Developer-only oracle utility. Pass an external output directory."""

import sys
import csv
import itertools
from pathlib import Path
import random

root = Path(sys.argv[1]).resolve()
repository = Path(__file__).resolve().parents[2]
if root == repository or repository in root.parents:
    raise ValueError("Write oracle outputs outside the repository")
root.mkdir(parents=True, exist_ok=True)
events = []


def event(sequence, position, reference, alternate):
    if reference != alternate:
        events.append((sequence, position, reference, alternate))


def change(word, right, operation, left="GCGC"):
    sequence = left + (word if operation == "Del" else "") + right + "CGTACGTCAG"
    ref = left[-1] + (word if operation == "Del" else "")
    alt = left[-1] + (word if operation == "Ins" else "")
    event(sequence, len(left), ref, alt)


for base in "ACGT":
    flanks = [b for b in "ACGT" if b != base]
    for left, right in itertools.product(flanks, repeat=2):
        for repeats in range(14):
            change(base, base * repeats + right, "Ins", "GCG" + left)
            change(base, base * repeats + right, "Del", "GCG" + left)

rng = random.Random(25547689)
units = {
    "A",
    "C",
    "G",
    "T",
    "AT",
    "AC",
    "GC",
    "AG",
    "ACT",
    "AGT",
    "CGTA",
    "GATCA",
    "ACGTTC",
    "ACTGACG",
    "AGCTACGA",
}
for unit in sorted(units):
    for internal in (1, 2, 3, 4, 5, 6, 7):
        for repeat in (0, 1, 2, 3, 4, 5, 8, 10):
            for spacer in ("", "G", "TC", "CACT"):
                word = unit * internal + spacer
                for operation in ("Del", "Ins"):
                    change(word, unit * repeat + "TCGACTG", operation)

for i in range(8000):
    word = "".join(rng.choices("ACGT", k=rng.randrange(2, 31)))
    if i % 3 == 0:
        right = word[: rng.randrange(1, len(word))] + "".join(rng.choices("ACGT", k=40))
    else:
        right = "".join(rng.choices("ACGT", k=60))
    change(word, right, rng.choice(("Del", "Ins")), "".join(rng.choices("ACGT", k=12)))

for delta in (0, 1, 3, 7, 15, 25, -1, -3, -7, -15, -25):
    ref = "AT" + "C" * max(delta, 0)
    alt = "TG" + "A" * max(-delta, 0)
    event("CGC" + ref + "CGTGAC", 4, ref, alt)

with (root / "oracle_inputs.tsv").open("w") as out:
    writer = csv.writer(out, delimiter="\t", lineterminator="\n")
    writer.writerow(("sequence", "position", "reference", "alternate"))
    writer.writerows(dict.fromkeys(events))
print("Wrote", len(dict.fromkeys(events)), "independent inputs")
