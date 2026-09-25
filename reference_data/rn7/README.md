# rn7 Reference Correction

The default `rn7` reference is rebuilt from mRatBN7.2 (INSDC
`GCA_015227675.2`) with corrected transcription-strand boundaries and
overlaps. The previously distributed archive is retained byte-for-byte as
`rn7_Legacy.tar.gz`. Its SHA-256 is
`792e185c23413a29ab5d870bbae72a11e9931a854cd5658bd05f2d80442b051c`.
The old archive contains an internal `rn7/` directory; the reference manager
maps it to the installed `rn7_Legacy/` directory. Do not repackage it.

## Sources

- DNA: UCSC `rn7.fa.gz` from
  `https://hgdownload.soe.ucsc.edu/goldenPath/rn7/bigZips/`; the 23 historical
  chromosomes are `chr1`-`chr20`, `chrX`, `chrY`, and `chrM` (installed as `MT`).
- Annotation: Ensembl release 105
  `Rattus_norvegicus.mRatBN7.2.105.chr.gtf.gz` from
  `https://ftp.ensembl.org/pub/release-105/gtf/rattus_norvegicus/`.
- Published checksums and exact SHA-256 values are recorded in
  [source_manifest.tsv](source_manifest.tsv).
- Of 54,830 bundled transcripts, 54,827 match the GTF in gene ID,
  chromosome, strand, and inclusive coordinates. Three anomalous chromosome 4
  records are omitted from the corrected strand map; see
  [excluded_transcript_ids.txt](excluded_transcript_ids.txt). The GTF has 22
  additional transcripts outside the historical bundled set. Many gene names
  differ between the historical bundle and Ensembl 105, and some names are
  absent from the GTF. Gene names are not used for strand-state encoding.

The corrected chromosome files retain the historical DNA sequence exactly.
All 2,633,489,728 registered bases were independently compared with the UCSC
FASTA and with the expected strand state from the 54,827 validated transcript
intervals. There were zero sequence or corrected strand-state mismatches. The
full build, archive manifests, context-table validation, and matrix smoke-test
evidence are kept outside the repository in
`test_results/rn7_tsb_correction_2026-09-25/`.

The opportunity tables are rebuilt from a consistent five-base SBS window.
Raw sequence-only mutation counts retain the same DNA, but opportunity counts
and distributions can change. All 48 historical opportunity tables are retained
byte-for-byte under the `rn7_Legacy` identity.

## Release

Upload both archive files from that evidence directory to the reference FTP
before merging or releasing code that registers the new checksums. The
corrected archive keeps the standard `rn7.tar.gz` name; the historical bytes
are available as `rn7_Legacy.tar.gz`. Existing local `rn7` installations must
be reinstalled for new analyses. Use `rn7_Legacy` only to reproduce historical
analyses.
