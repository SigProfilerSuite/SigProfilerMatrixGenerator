# Reference Correctness

## What Is Being Corrected?

MatrixGenerator prepares reference files and then reads them when classifying
mutations. Both steps must use the same position and strand rules. Correcting
the program does not automatically rebuild reference files already installed
on a user's computer.

## Transcript Rules

The transcript reader accepts combined or per-chromosome files. The six required
columns are:

| Column | Meaning |
| --- | --- |
| 1 | Stable gene ID |
| 2 | Transcript ID |
| 3 | Chromosome name |
| 4 | Strand: `1` or `-1` |
| 5 | Start position, starting at 1 |
| 6 | End position, included in the interval |

An optional seventh column contains the gene name. When it is absent or empty,
the internal gene-range reader uses the stable gene ID. Headers naming the
start/end columns, blank lines, and comment lines beginning with `#` are ignored.
An input without a header must retain its first transcript. Reading annotations
does not sort, split, delete, or otherwise rewrite the source files.

For example, a transcript from position 4 through position 6 covers positions
4, 5, and 6. It contains three bases, not two. Ensembl documents its use of
[one-based inclusive coordinates](https://mart.ensembl.org/info/docs/api/general_instructions.html).
Other source formats must be converted explicitly before use; these transcript
rules are not a general definition of BED coordinates.

For a base on the stored forward reference sequence:

- `N`: no transcript covers the position.
- `U`: one or more plus-strand transcripts cover it, and no minus-strand transcript does.
- `T`: one or more minus-strand transcripts cover it, and no plus-strand transcript does.
- `B`: transcripts on both strands cover it.

Overlapping transcripts on the same strand must not cancel one another. Nested
opposite-strand intervals must not truncate other intervals. These labels are
derived from annotations; they do not measure expression in a particular sample.

## Reading a Mutation

A mutation reported at position `p` reads its base and strand label from array
index `p - 1`, because Python arrays begin at zero. If an A/G-reference mutation
is reverse-complemented into C/T orientation, its T/U label is also reversed.
The five-base SBS context needs two bases on each side; positions without those
flanks must not wrap around to the opposite end of the chromosome.

The chromosome list used by VCF, text, and MAF readers comes from the registered
reference checksums. It does not depend on how the transcript files are named
or whether a chromosome has any annotated transcripts.

The internal gene-range reader accepts these annotation formats, but the
public API still disables `gs=True` with its existing unsupported-feature
warning. This patch does not enable that experimental analysis.

## Reference Identity and Installation Errors

A reference-data ID identifies the exact registered set of TSB files. The base
assembly identifies shared resources such as exome intervals. These are not
interchangeable: chromosome checksums, input conversion, and TSB lookup retain
the full reference-data ID. Run logs record both names and the TSB directory.

`REFERENCE_ASSEMBLIES` explicitly maps the existing `GRCh37_Legacy`,
`GRCh37_havana`, `GRCh38_havana`, `GRCh38_Legacy`, `mm9_Legacy`,
`mm10_havana`, `mm10_Legacy`, `mm39_Legacy`, `rn6_Legacy`,
`rn7_Legacy`, `dog_Legacy`, and `c_elegans_Legacy`
references to their base assemblies. Unknown names are not shortened by
guessing from underscores or the word `havana`.

The three Havana references remain available for historical compatibility but
are known to contain the pre-correction transcript-boundary and overlap defect.
Their exact source annotations are not available in the repository, so they
cannot yet be rebuilt authoritatively. Installing or using one emits a runtime
warning; transcription-strand-aware results may be affected.

`GRCh38` identifies the corrected transcription-strand reference and is the
default for new analyses. The previously distributed data is registered as
`GRCh38_Legacy` for reproducing historical results. Both identities share the
GRCh38 DNA assembly, exome intervals, and transcript resources, but have their
own chromosome checksums and strand-dependent context tables. Network
installation continues to use the already-published corrected `GRCh38.tar.gz`.
The immutable filename mapping applies prospectively and does not rename this
working archive.

`mm10` identifies the corrected mouse transcription-strand reference and
resolves to `mm10.tar.gz`. A copy of the previously distributed archive is
available as `mm10_Legacy.tar.gz` and registered as `mm10_Legacy`. Both
identities use the same GRCm38 DNA sequence, exome intervals, and transcript
scope, but have separate chromosome checksums and strand-aware context tables.
Older software will reject the corrected archive because its chromosome
checksums differ; use a version that registers `mm10_Legacy` to reproduce
earlier results.

The same registration applies to GRCh37. `GRCh37` resolves to the corrected
`GRCh37.tar.gz` archive. `GRCh37_Legacy` resolves to a copy of the untouched
historical archive named `GRCh37_Legacy.tar.gz`, whose internal `GRCh37/`
directory is staged and installed as `GRCh37_Legacy/`. Older software will
reject the corrected archive because its chromosome checksums differ; use a
version that registers `GRCh37_Legacy` to reproduce earlier results.

`mm9` identifies the corrected mouse transcription-strand reference and
resolves to `mm9.tar.gz`. A copy of the previously distributed archive is
available as `mm9_Legacy.tar.gz` and registered as `mm9_Legacy`. Both
identities use the same GRCm37 DNA sequence, exome intervals, and transcript
scope, but have separate chromosome checksums and strand-aware context tables.
Older software will reject the corrected archive because its chromosome
checksums differ; use a version that registers `mm9_Legacy` to reproduce
earlier results.

The same corrected-default and historical-Legacy naming applies to `mm39`,
`rn6`, `rn7`, `dog`, and `c_elegans`. Their corrected archives retain the
standard `<genome>.tar.gz` names, while the previous bytes are available as
`<genome>_Legacy.tar.gz`. The corrected archives must be used with software
that registers their new chromosome checksums. Each genome's source and
validation details are recorded under `reference_data/<genome>/`.

The matrix API raises `ReferenceInstallationError` when verification fails.
Its message distinguishes an unknown name, missing files, an incomplete install,
and files whose checksums do not match. A mismatch may mean a different reference
revision or damaged files; it does not necessarily mean the genome is absent.
Verification does not delete or replace files. An installation created by an
earlier release under a corrected default name will fail verification after
upgrading; reinstall the corrected identity, or install the corresponding
`*_Legacy` identity to reproduce an earlier analysis.

## Tests and Release Limits

Tests include direct boundary classifications, reverse-complement controls,
nested intervals, decoded-base checks, and small generated references passed
through the public WGS, WES, and BED matrix workflows. Full corrected GRCh38
validation separately checks all encoded bases and TSB positions and compares
legacy and corrected matrices for the public TCGA-BRCA cohort. CHM13 remains a
separate reference-validation task.

Before releasing regenerated references:

1. Preserve the old compressed archive and its SHA-256 fingerprint.
2. Pin the source FASTA, annotations, conversion commands, and software revision.
3. Compare decoded reference bases directly with the verified source FASTA.
4. Check strand labels with an independently implemented interval calculation.
5. Validate expected matrices, including boundary and overlapping-transcript cases.
6. Record both software and reference-data versions so earlier analyses remain reproducible.

For SBS opportunity tables, `24` and `384` must be collapsed from the same
valid five-base opportunities used by `6144`; calculating them independently
from one-base or three-base windows admits positions that matrix generation
cannot classify. When an A/G-centered context is reverse-complemented into the
standard C/T orientation, its T/U label must also be reversed. Whole-genome and
exome counts must be conserved when N/T/U/B labels are collapsed.

When changing which data the default identity resolves to, preserve the former
archive under an explicit legacy identity, document the migration, and validate
both archives. Do not update expected matrices solely to make tests pass. The
reference archives are separately published data artifacts and are not bundled
in the Python wheel.
