#!/usr/bin/env python3
"""Derive the shipped CHM13-T2T reference files from an NCBI RefSeq annotation.

This is the utility that produced

* ``references/chromosomes/exome/CHM13-T2T/CHM13-T2T_exome.interval_list``
  (``exome-list`` subcommand, from the GFF), and
* ``references/chromosomes/transcripts/CHM13-T2T/*_transcripts.txt``
  (``transcripts`` subcommand, from the GTF).

It is a developer tool, not part of the matrix generation path; it is kept in
the repository so both sets of shipped files can be regenerated and audited
rather than merely described. Both subcommands read the same NCBI assembly
report to map RefSeq accessions onto chromosome names, which is why they live
in one module.

The two subcommands deliberately read different files from the same annotation
release. The transcript format is built on NCBI's GTF-only ``gene_id`` /
``transcript_id`` conventions -- the ``SYMBOL_1`` suffixes that disambiguate
duplicated gene symbols, and the ``unassigned_transcript_N`` placeholders for
features with no accession. Neither appears in the GFF.

Example, for the shipped CHM13-T2T files::

    python build_refseq_references.py exome-list \\
        --gff GCF_009914755.1_T2T-CHM13v2.0_genomic.gff.gz \\
        --assembly-report GCF_009914755.1_T2T-CHM13v2.0_assembly_report.txt \\
        --feature CDS \\
        --description "NCBI RefSeq GCF_009914755.1-RS_2025_08 CDS features on T2T-CHM13v2.0, merged" \\
        --output CHM13-T2T_exome.interval_list

    python build_refseq_references.py transcripts \\
        --gtf GCF_009914755.1_T2T-CHM13v2.0_genomic.gtf.gz \\
        --assembly-report GCF_009914755.1_T2T-CHM13v2.0_assembly_report.txt \\
        --outdir references/chromosomes/transcripts/CHM13-T2T
"""

import argparse
import gzip
import io
import os
import re


def open_maybe_gzip(path):
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8")
    return open(path, encoding="utf-8")


def read_accession_map(assembly_report, bare=False):
    """RefSeq accession -> chromosome name, nuclear chromosomes only.

    NCBI assembly reports are CRLF-terminated, hence the explicit strip. With
    ``bare`` the ``chr`` prefix is dropped: the interval list uses UCSC-style
    ``chrX`` like every other shipped exome file, whereas the transcript files
    use bare ``X`` because ``gene_range()`` keys its dictionaries on that column.
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
            stripped = ucsc_name[3:] if ucsc_name.startswith("chr") else ucsc_name
            if stripped == "X" or stripped == "Y" or stripped.isdigit():
                accession_to_chrom[refseq_accession] = (
                    stripped if bare else ucsc_name
                )
    return accession_to_chrom


def assert_annotation_release(path, expected):
    """Guard against silently mixing annotation releases across subcommands."""
    with open_maybe_gzip(path) as handle:
        for line in handle:
            if not line.startswith("#"):
                break
            if line.startswith("#!annotation-source"):
                found = line.strip().split(None, 1)[1]
                if expected is not None and found != expected:
                    raise SystemExit(
                        f"{path} is {found!r}, expected {expected!r}"
                    )
                return found
    raise SystemExit(f"{path} has no #!annotation-source header")


# ---------------------------------------------------------------- exome-list


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


def build_exome_list(args):
    accession_to_chrom = read_accession_map(args.assembly_report)
    if not accession_to_chrom:
        raise SystemExit(f"no nuclear chromosomes found in {args.assembly_report}")
    print(f"mapped {len(accession_to_chrom)} chromosome accessions")
    assert_annotation_release(args.gff, args.expect_release)

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


# ---------------------------------------------------------------- transcripts

# GTF attributes are `key "value";` pairs. NCBI quotes every value, including
# the empty transcript_id it emits on gene features.
ATTRIBUTE_RE = re.compile(r'(\S+) "([^"]*)"')

# Column order is fixed by save_tsb_192.save_tsb() and gene_range(), which read
# fields 2-6 (chromosome, strand, start, end, gene) positionally. The flanking
# identifier and biotype columns are carried only to match the format of the
# other shipped genomes.
TRANSCRIPT_COLUMNS = (
    "gene_id",
    "transcript_id",
    "chrom",
    "strand",
    "start",
    "end",
    "gene",
    "transcript_biotype",
)


def read_transcripts(gtf, accession_to_chrom, exclude_sources=(), exclude_biotypes=()):
    """`transcript` features per chromosome, as pre-joined output rows.

    ``exclude_sources`` and ``exclude_biotypes`` drop features by GTF column 2
    (e.g. ``Gnomon`` for predicted models) and by ``transcript_biotype``. Both
    are empty by default: every other shipped genome is unfiltered, so the
    faithful rendering of the annotation release is the default here too.
    """
    rows = {chrom: [] for chrom in accession_to_chrom.values()}
    dropped = 0
    with open_maybe_gzip(gtf) as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9 or fields[2] != "transcript":
                continue
            chrom = accession_to_chrom.get(fields[0])
            if chrom is None:
                continue
            if fields[1] in exclude_sources:
                dropped += 1
                continue
            attributes = dict(ATTRIBUTE_RE.findall(fields[8]))
            if attributes.get("transcript_biotype", "") in exclude_biotypes:
                dropped += 1
                continue
            rows[chrom].append(
                (
                    int(fields[3]),
                    (
                        attributes.get("gene_id", ""),
                        attributes.get("transcript_id", ""),
                        chrom,
                        "1" if fields[6] == "+" else "-1",
                        fields[3],
                        fields[4],
                        attributes.get("gene", attributes.get("gene_id", "")),
                        attributes.get("transcript_biotype", ""),
                    ),
                )
            )
    if dropped:
        print(f"dropped {dropped} transcripts by --exclude-source/--exclude-biotype")
    return rows


def build_transcripts(args):
    accession_to_chrom = read_accession_map(args.assembly_report, bare=True)
    if not accession_to_chrom:
        raise SystemExit(f"no nuclear chromosomes found in {args.assembly_report}")
    print(f"mapped {len(accession_to_chrom)} chromosome accessions")
    assert_annotation_release(args.gtf, args.expect_release)

    rows = read_transcripts(
        args.gtf,
        accession_to_chrom,
        exclude_sources=set(args.exclude_source),
        exclude_biotypes=set(args.exclude_biotype),
    )

    os.makedirs(args.outdir, exist_ok=True)
    total = 0
    for chrom in sorted(rows, key=chrom_sort_key):
        path = os.path.join(args.outdir, f"{chrom}_transcripts.txt")
        # Sort by integer start. save_tsb() rewrites each file into exactly this
        # order in place before reading it, so anything else would leave the
        # committed files silently modified after a build.
        with open(path, "w", encoding="utf-8") as out:
            for _, row in sorted(rows[chrom], key=lambda item: item[0]):
                out.write("\t".join(row) + "\n")
        print(f"wrote {len(rows[chrom])} transcripts to {path}")
        total += len(rows[chrom])

    print(f"wrote {total} transcripts across {len(rows)} chromosomes")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--expect-release",
        default="NCBI RefSeq GCF_009914755.1-RS_2025_08",
        help="required #!annotation-source value; pass an empty string to skip",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    exome = subparsers.add_parser(
        "exome-list", help="build an exome interval list from a RefSeq GFF"
    )
    exome.add_argument("--gff", required=True, help="RefSeq GFF, optionally gzipped")
    exome.add_argument(
        "--assembly-report", required=True, help="matching NCBI assembly report"
    )
    exome.add_argument(
        "--feature",
        default="CDS",
        help="GFF feature type to collect (default: CDS)",
    )
    exome.add_argument(
        "--description",
        required=True,
        help="provenance string for the single @ header line",
    )
    exome.add_argument("--output", required=True)
    exome.set_defaults(func=build_exome_list)

    transcripts = subparsers.add_parser(
        "transcripts", help="build per-chromosome transcript files from a RefSeq GTF"
    )
    transcripts.add_argument(
        "--gtf", required=True, help="RefSeq GTF, optionally gzipped"
    )
    transcripts.add_argument(
        "--assembly-report", required=True, help="matching NCBI assembly report"
    )
    transcripts.add_argument("--outdir", required=True)
    transcripts.add_argument(
        "--exclude-source",
        action="append",
        default=[],
        metavar="SOURCE",
        help="drop features with this GTF source, repeatable "
        "(e.g. --exclude-source Gnomon to keep only curated models)",
    )
    transcripts.add_argument(
        "--exclude-biotype",
        action="append",
        default=[],
        metavar="BIOTYPE",
        help="drop features with this transcript_biotype, repeatable "
        "(e.g. --exclude-biotype lnc_RNA)",
    )
    transcripts.set_defaults(func=build_transcripts)

    args = parser.parse_args()
    if not args.expect_release:
        args.expect_release = None
    args.func(args)


if __name__ == "__main__":
    main()
