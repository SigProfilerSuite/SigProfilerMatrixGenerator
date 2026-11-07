"""Developer-only oracle utility. Pass an external output directory."""

import sys
import csv
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

from SigProfilerMatrixGenerator.scripts.koh_indels import (
    classify_indel,
    ID89_CHANNELS,
    ID476_CHANNELS,
)

root = Path(sys.argv[1]).resolve()
repository = Path(__file__).resolve().parents[2]
if root == repository or repository in root.parents:
    raise ValueError("Write oracle outputs outside the repository")
root.mkdir(parents=True, exist_ok=True)
counts = Counter()
issues = []
examples = {}
with (root / "oracle_results.tsv").open() as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        counts["total"] += 1
        if row["id89"] == "ERROR":
            counts["oracle_error"] += 1
            continue
        try:
            result = classify_indel(
                row["sequence"],
                int(row["position"]),
                row["reference"],
                row["alternate"],
            )
            if (result.id89, result.id476) != (row["id89"], row["id476"]):
                issues.append({"event": row, "observed": asdict(result)})
            else:
                counts["matched"] += 1
                examples.setdefault(result.id476, row)
        except Exception as error:
            issues.append(
                {"event": row, "exception": f"{type(error).__name__}: {error}"}
            )
counts["mismatches"] = len(issues)
orders = {}
for context, expected in (("89", ID89_CHANNELS), ("476", ID476_CHANNELS)):
    external = (root / f"oracle_ID{context}_channels.txt").read_text().splitlines()
    orders[context] = list(expected) == external
result = {
    "counts": dict(counts),
    "channel_order_matches": orders,
    "channels_476_covered": len(examples),
    "missing_channels": sorted(set(ID476_CHANNELS) - examples.keys()),
    "first_mismatches": issues[:40],
}
(root / "oracle_comparison.json").write_text(json.dumps(result, indent=2) + "\n")
with (root / "golden_examples.tsv").open("w") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=("sequence", "position", "reference", "alternate", "id89", "id476"),
        delimiter="\t",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(examples.values())
print(json.dumps(result, indent=2))
if (
    issues
    or counts.get("oracle_error", 0)
    or not all(orders.values())
    or result["missing_channels"]
):
    raise SystemExit(1)
