# mm39 Reference Correction

The default `mm39` reference is rebuilt from GRCm39 (INSDC
`GCA_000001635.9`) with corrected transcription-strand boundaries and
overlaps. The previously distributed archive is retained byte-for-byte as
`mm39_Legacy.tar.gz`. Its SHA-256 is
`c9d8113d2484e6e9a97daf0733d6e5968ed771e85f3e13fa7b82c0f998442ce5`.
The old archive contains an internal `mm39/` directory; the reference manager
maps it to the installed `mm39_Legacy/` directory. Do not repackage it.

## Sources

- DNA: Ensembl release 103 GRCm39 chromosome FASTAs for 1-19, X, and Y,
  downloaded from `https://ftp.ensembl.org/pub/release-103/fasta/mus_musculus/dna/`.
  The release's MT FASTA was checked but is not in the historical mm39 reference.
- Annotation: `Mus_musculus.GRCm39.103.chr.gtf.gz` from
  `https://ftp.ensembl.org/pub/release-103/gtf/mus_musculus/`.
- Exact file SHA-256 values and Ensembl BSD checksums are recorded in
  [source_manifest.tsv](source_manifest.tsv).
- The repository's 59,063 bundled mm39 transcripts all match the GTF in gene
  ID, chromosome, strand, and inclusive start/end positions. There are 17
  gene-name-only differences, listed in
  [gene_name_differences.tsv](gene_name_differences.tsv). Another 76
  protein-coding GTF transcripts are excluded to keep the historical annotation
  scope; their IDs are in
  [excluded_transcript_ids.txt](excluded_transcript_ids.txt).

The corrected chromosome files retain the historical DNA sequence exactly.
All 2,723,414,844 registered bases were independently compared with the source
FASTA and with the expected strand state from the bundled transcripts. There
were zero sequence or corrected strand-state mismatches. The full build,
archive manifests, context-table validation, and matrix smoke-test evidence
are kept outside the repository in
`test_results/mm39_tsb_correction_2026-09-24/`.

The opportunity tables were rebuilt from a consistent five-base SBS window.
The old `6` and `96` tables do not always collapse to the old `1536` table;
the corrected tables do. Thus, raw sequence-only mutation counts stay the
same, but analyses using opportunity counts or distributions can change even
for a sequence-only context. All 48 historical opportunity tables are retained
byte-for-byte under the `mm39_Legacy` identity.

## Release

Upload both archive files from that evidence directory to the reference FTP
before merging or releasing code that registers the new checksums. The
corrected archive keeps the standard `mm39.tar.gz` name; the historical bytes
are available as `mm39_Legacy.tar.gz`. Existing local `mm39` installations
must be reinstalled for new analyses. Use `mm39_Legacy` only to reproduce
historical analyses.
