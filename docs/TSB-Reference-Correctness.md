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

`REFERENCE_ASSEMBLIES` explicitly maps the existing `GRCh37_havana`,
`GRCh38_havana`, and `mm10_havana` references to their base assemblies. Unknown
names are not shortened by guessing from underscores or the word `havana`.

`GRCh38_TSBv2` is a proposed name for a corrected reference edition, not a
currently registered or downloadable reference. Tests temporarily register a
tiny synthetic fixture with this name; they do not add production checksums.
Before registering a real edition, verify that any shared exome intervals match
the assembly. Rebuild and validate strand-dependent context distributions rather
than automatically reusing those from an older TSB edition.

The matrix API raises `ReferenceInstallationError` when verification fails.
Its message distinguishes an unknown name, missing files, an incomplete install,
and files whose checksums do not match. A mismatch may mean a different reference
revision or damaged files; it does not necessarily mean the genome is absent.
Verification does not delete or replace files. Preserve old references before
reinstallation, and retain matching software and reference versions when
reproducing an earlier analysis.

## Tests and Release Limits

Tests include direct boundary classifications, reverse-complement controls,
nested intervals, decoded-base checks, and small generated references passed
through the public WGS, WES, and BED matrix workflows. These use explicitly
synthetic sequences. They do not establish the correctness of all distributed
GRCh38/CHM13 files or quantify effects on real sample results.

Before releasing regenerated references:

1. Preserve the old compressed archive and its SHA-256 fingerprint.
2. Pin the source FASTA, annotations, conversion commands, and software revision.
3. Compare decoded reference bases directly with the verified source FASTA.
4. Check strand labels with an independently implemented interval calculation.
5. Validate expected matrices, including boundary and overlapping-transcript cases.
6. Record both software and reference-data versions so earlier analyses remain reproducible.

Do not silently overwrite published archives or update expected matrices solely
to make tests pass. Reference publication and naming require a separate release
decision. No corrected archive is bundled by this code change.
