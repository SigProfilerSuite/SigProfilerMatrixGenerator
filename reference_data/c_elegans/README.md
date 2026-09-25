# c_elegans Reference Correction

The default `c_elegans` reference for WBcel235 (INSDC `GCA_000002985.3`) has
corrected transcription-strand boundaries and overlaps. The previously
distributed archive is retained byte-for-byte as `c_elegans_Legacy.tar.gz`;
its SHA-256 is
`807ee073c1a33c203e2c3afef36e201166e50b681da3a97ee0bd01a8e8d90445`.
The original archive contains an internal `c_elegans/` directory; the
installer maps it to `c_elegans_Legacy/` without modifying the archive bytes.

## Sources

- DNA: the 7 registered chromosomes (I, II, III, IV, V, X, MtDNA) from
  Ensembl release 100 WBcel235 FASTA files in
  `https://ftp.ensembl.org/pub/release-100/fasta/caenorhabditis_elegans/dna/`.
- Annotation: `Caenorhabditis_elegans.WBcel235.100.gtf.gz` from
  `https://ftp.ensembl.org/pub/release-100/gtf/caenorhabditis_elegans/`.
- Published BSD checksums and SHA-256 values for every source file are in
  [source_manifest.tsv](source_manifest.tsv).

All 33,541 bundled transcripts match release 100 exactly in gene ID,
chromosome, strand, inclusive coordinates, and biotype - no coordinate or
biotype anomalies were found, so no transcripts needed to be excluded from
the corrected strand map. Another 11 protein-coding transcripts in that GTF
(including several mitochondrial genes not present in the historical
bundle) are outside the historical bundled set and were not added; see
[excluded_gtf_transcript_ids.txt](excluded_gtf_transcript_ids.txt). Gene-name
differences do not affect strand-state encoding.

The 7 corrected chromosome files retain the historical DNA exactly. All
100,286,401 registered positions were independently checked against the
source FASTA and the expected strand state from the bundled transcripts:
zero base mismatches, invalid codes, or corrected strand-state mismatches.
73,962 positions changed strand state relative to the historical archive
(N->T 9,432; N->U 8,523; T->B 15,144; U->B 40,863). The corrected
`c_elegans.tar.gz` SHA-256 is
`1414377196896649ccbf8419ab6c2eb75365f50a0d10e3bac358649c27e79f60`.
Build scripts, manifests, and test evidence are outside the repository in
`test_results/c_elegans_tsb_correction_2026-09-25/`.

The package does not ship c_elegans context-count or distribution tables,
so this correction does not add or alter any. Sequence-only mutation counts
retain the same DNA; strand-aware counts can change.

## Release

Upload both archive files from the external evidence directory to the
reference FTP before merging or releasing the code. The corrected archive
keeps `c_elegans.tar.gz`; the historical bytes use `c_elegans_Legacy.tar.gz`.
Existing local `c_elegans` installations must be reinstalled for new
analyses. Use `c_elegans_Legacy` only to reproduce historical analyses.
