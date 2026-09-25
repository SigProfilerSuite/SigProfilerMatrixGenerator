# rn6 Reference Correction

The default `rn6` reference is rebuilt from Rnor_6.0 (INSDC
`GCA_000001895.4`) with corrected transcription-strand boundaries and
overlaps. The previously distributed archive is retained byte-for-byte as
`rn6_Legacy.tar.gz`. Its SHA-256 is
`2ffd42025d3a6d9364597a5bb3bf334ecfd73b65b5c0c3a956e69917cf0a0379`.
The old archive contains an internal `rn6/` directory; the reference manager
maps it to the installed `rn6_Legacy/` directory. Do not repackage it.

## Sources

- DNA: Ensembl release 96 Rnor_6.0 chromosome FASTAs for 1-20, X, Y, and MT,
  downloaded from
  `https://ftp.ensembl.org/pub/release-96/fasta/rattus_norvegicus/dna/`.
- Annotation: `Rattus_norvegicus.Rnor_6.0.96.chr.gtf.gz` from
  `https://ftp.ensembl.org/pub/release-96/gtf/rattus_norvegicus/`.
- Exact file SHA-256 values and Ensembl BSD checksums are recorded in
  [source_manifest.tsv](source_manifest.tsv).
- All 28,705 bundled rn6 transcripts match the GTF in gene ID, chromosome,
  strand, inclusive start/end positions, gene name, and biotype. Another 22
  protein-coding GTF transcripts are excluded to retain the historical
  annotation scope; their IDs are in
  [excluded_transcript_ids.txt](excluded_transcript_ids.txt).

The corrected chromosome files retain the historical DNA sequence exactly.
All 2,782,028,915 registered bases were independently compared with the
source FASTA and the expected strand state from bundled transcripts. There
were zero sequence or corrected strand-state mismatches. The corrected archive
is `rn6.tar.gz`, SHA-256
`3d460a7bcbffc31f803a4cfbc73b0471b701b02243f13fcc5d96f1b8bddf54ba`.
Build scripts, full validation reports, archive manifests, and matrix smoke
tests are kept outside the repository in
`test_results/rn6_tsb_correction_2026-09-24/`.

Only rn6's 38 historically shipped opportunity files are rebuilt and
preserved for the legacy identity. The historical rn6 reference has no DBS
distribution files or DBS exome counts. This correction does not add those
missing file types. Its exome files also omit the all-zero `MT` and `M`
columns found in some other genomes' tables; that column layout is retained.
The original whole-genome SBS opportunity tables total 2,737,353,805, while
an independent count of valid five-base windows in the source FASTA gives
2,651,203,463, exactly matching the rebuilt tables. Raw sequence-only
mutation counts remain the same; strand-aware counts and opportunity-based
normalization can change.

## Release

Upload both archive files from that evidence directory to the reference FTP
before merging or releasing code that registers the new checksums. The
corrected archive keeps the standard `rn6.tar.gz` name; the historical bytes
are available as `rn6_Legacy.tar.gz`. Existing local `rn6` installations
must be reinstalled for new analyses. Use `rn6_Legacy` only to reproduce
historical analyses.
