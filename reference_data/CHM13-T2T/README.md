# CHM13-T2T Reference Profile

Assembly: T2T-CHM13v2.0. Annotation: NCBI RefSeq
`GCF_009914755.1-RS_2025_08`. Sources and SHA-256 fingerprints are recorded
in `source_manifest.tsv` and `docs/Currently-Supported-Genomes.md`.

The payload includes chromosomes 1-22, X, and Y, but not MT. The pinned
annotation produces 184,134 transcripts, including predicted models. The exome
list is a union of CDS features, not a capture-kit definition: 213,010
one-based inclusive intervals covering 36,402,445 bases.

Independent validation compares all 3,117,275,501 nuclear DNA bases and strand
labels against the FASTA and raw GTF with zero mismatches. A separate raw-GFF
comparison verifies every CDS-covered position. Existing v1.4.0 reference
registrations and opportunity tables are unchanged.

The archive is `CHM13-T2T.tar.gz`, with one `CHM13-T2T` root and 24 files.
Size: 849,740,149 bytes. SHA-256:
`e8d0309879486beefb83d730c00b8cf8733aa7cd1716f694855817e69943f6a3`.
Use `tools/build_reference_archive.py --genome CHM13-T2T --compression-level 6`
with the input payload directory and output archive path to reproduce it.
Compression metadata can change the archive hash without changing payload MD5s.

Network installation requires publication to the configured AlexandrovLab FTP.
CHM13-specific opportunity tables and downstream signature catalogues are not
part of this change.
