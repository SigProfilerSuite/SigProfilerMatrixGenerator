# Dog Reference Correction

The default `dog` reference for CanFam3.1 (INSDC `GCA_000002285.2`) has
corrected transcription-strand boundaries and overlaps. The previously
distributed archive is retained byte-for-byte as `dog_Legacy.tar.gz`; its
SHA-256 is
`e945bb4317295cfe81ad7fc190e5156e947b27178fcf772fcfbc6abd222a440d`.
The original archive contains an internal `dog/` directory; the installer
maps it to `dog_Legacy/` without modifying the archive bytes.

## Sources

- DNA: the 39 registered chromosomes (1-38 and X) from Ensembl release 100
  CanFam3.1 FASTA files in
  `https://ftp.ensembl.org/pub/release-100/fasta/canis_lupus_familiaris/dna/`.
- Annotation validation: Ensembl release 93
  `Canis_familiaris.CanFam3.1.93.chr.gtf.gz` from
  `https://ftp.ensembl.org/pub/release-93/gtf/canis_familiaris/`.
- Published BSD checksums and SHA-256 values for every source file are in
  [source_manifest.tsv](source_manifest.tsv).

Ensembl release 100 is an authoritative source for the historical DNA, but
its transcript model does not match the bundled dog transcript files. Release
93 matches 24,766 of the 24,767 bundled records in gene ID, chromosome,
strand, and inclusive coordinates. This does not establish the exact release
from which the historical transcript bundle was made. The remaining bundled
record, `ENSCAFT00000018875`, is excluded from the corrected strand map: the
bundle marks it protein coding and starts it at chromosome 24 position
41,492,796, while release 93 calls it a pseudogene starting at 41,492,787.
See [excluded_transcript_ids.txt](excluded_transcript_ids.txt). Another 72
protein-coding transcripts in that GTF are outside the historical bundle and
were not added; see
[excluded_gtf_transcript_ids.txt](excluded_gtf_transcript_ids.txt). Gene-name
differences do not affect strand-state encoding.

The 39 corrected chromosome files retain the historical DNA exactly. All
2,327,633,984 registered positions were independently checked against the
source FASTA and the expected strand state from the 24,766 validated
transcripts: zero base mismatches, invalid codes, or corrected strand-state
mismatches. The corrected `dog.tar.gz` SHA-256 is
`1d1bd4e27aeaf0e698cd4e4f253b7a38d2b02e8d0a45a7f3233717b154132649`.
Build scripts, manifests, and test evidence are outside the repository in
`test_results/dog_tsb_correction_2026-09-25/`.

The package does not ship dog context-count or distribution tables, so this
correction does not add or alter any. Sequence-only mutation counts retain
the same DNA; strand-aware counts can change.

## Release

Upload both archive files from the external evidence directory to the
reference FTP before merging or releasing the code. The corrected archive
keeps `dog.tar.gz`; the historical bytes use `dog_Legacy.tar.gz`. Existing
local `dog` installations must be reinstalled for new analyses. Use
`dog_Legacy` only to reproduce historical analyses.
