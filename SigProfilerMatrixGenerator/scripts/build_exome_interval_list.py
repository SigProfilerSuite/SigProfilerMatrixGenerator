#!/usr/bin/env python3
"""Build an exome interval list from an NCBI RefSeq GFF annotation.

This is the utility that produced
``references/chromosomes/exome/CHM13-T2T/CHM13-T2T_exome.interval_list``. It is a
developer tool, not part of the matrix generation path; it is kept in the
repository so the shipped interval list can be regenerated and audited.

The output format is dictated by ``exome_check()`` in ``MutationMatrixGenerator``,
which is a single-pass merge join against a mutation stream sorted to
``chrom_order`` (X, Y, 1..N). The chromosome blocks must therefore appear in that
order with ascending, non-overlapping intervals inside each block: an unsorted
file silently drops mutations instead of raising.

Example, for the shipped CHM13-T2T list::

    python build_exome_interval_list.py \\
        --gff GCF_009914755.1_T2T-CHM13v2.0_genomic.gff.gz \\
        --assembly-report GCF_009914755.1_T2T-CHM13v2.0_assembly_report.txt \\
        --feature CDS \\
        --description "NCBI RefSeq GCF_009914755.1-RS_2025_08 CDS features on T2T-CHM13v2.0, merged" \\
        --output CHM13-T2T_exome.interval_list
"""

import argparse
import gzip
import io
import os


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, encoding="utf-8")


def read_accession_map(assembly_report):
    """RefSeq accession -> UCSC-style chromosome name, nuclear chromosomes only.

    NCBI assembly reports are CRLF-terminated, hence the explicit strip.
    """
    accession_to_chrom = {}
    with open(assembly_report, encoding="utf-8") as handle:
        for line in handle:
            line = line.replace("\r", "")
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue
            refseq_accession, unit, ucsc_name = fields[6], fields[7], fields[9]
            if unit != "Primary Assembly":
                continue
            bare = ucsc_name[3:] if ucsc_name.startswith("chr") else ucsc_name
            if bare == "X" or bare == "Y" or bare.isdigit():
                accession_to_chrom[refseq_accession] = ucsc_name
    return accession_to_chrom


def read_intervals(gff, accession_to_chrom, feature):
    """Half-open [start, end) intervals for `feature`, keyed by chromosome."""
    intervals = {chrom: [] for chrom in accession_to_chrom.values()}
    with open_maybe_gzip(gff) as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 9 or fields[2] != feature:
                continue
            chrom = accession_to_chrom.get(fields[0])
            if chrom is None:
                continue
            intervals[chrom].append((int(fields[3]) - 1, int(fields[4])))
    return intervals


def merge(intervals):
    """Sort and collapse overlapping/abutting intervals."""
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def chrom_sort_key(chrom):
    """The X, Y, 1..N ordering that exome_check's merge join requires."""
    bare = chrom[3:] if chrom.startswith("chr") else chrom
    if bare == "X":
        return -1
    if bare == "Y":
        return 0
    return int(bare)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gff", required=True, help="RefSeq GFF, optionally gzipped")
    parser.add_argument(
        "--assembly-report", required=True, help="matching NCBI assembly report"
    )
    parser.add_argument(
        "--feature",
        default="CDS",
        help="GFF feature type to collect (default: CDS)",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="provenance string for the single @ header line",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    accession_to_chrom = read_accession_map(args.assembly_report)
    if not accession_to_chrom:
        raise SystemExit(f"no nuclear chromosomes found in {args.assembly_report}")
    print(f"mapped {len(accession_to_chrom)} chromosome accessions")

    intervals = read_intervals(args.gff, accession_to_chrom, args.feature)

    total_intervals = 0
    total_span = 0
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out:
        out.write(f'@track name="Covered" description="{args.description}"\n')
        for chrom in sorted(intervals, key=chrom_sort_key):
            for start, end in merge(intervals[chrom]):
                out.write(f"{chrom}\t{start}\t{end}\n")
                total_intervals += 1
                total_span += end - start

    print(
        f"wrote {total_intervals} intervals covering "
        f"{total_span / 1e6:.1f} Mb to {args.output}"
    )


if __name__ == "__main__":
    main()
