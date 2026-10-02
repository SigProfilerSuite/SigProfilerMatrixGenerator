# Legacy Reference Archives

Corrected transcription-strand references are distributed under the standard
genome names. The archives distributed before those corrections are retained
under `_Legacy` names so earlier analyses can be reproduced. Use the corrected
name for new analyses; select a Legacy name only when comparing with results
generated using the former reference.

| Genome | Corrected reference/archive | Historical reference/archive |
| --- | --- | --- |
| GRCh38 | `GRCh38` / `GRCh38.tar.gz` | `GRCh38_Legacy` / `GRCh38_Legacy.tar.gz` |
| GRCh37 | `GRCh37` / `GRCh37.tar.gz` | `GRCh37_Legacy` / `GRCh37_Legacy.tar.gz` |
| mm9 | `mm9` / `mm9.tar.gz` | `mm9_Legacy` / `mm9_Legacy.tar.gz` |
| mm10 | `mm10` / `mm10.tar.gz` | `mm10_Legacy` / `mm10_Legacy.tar.gz` |
| mm39 | `mm39` / `mm39.tar.gz` | `mm39_Legacy` / `mm39_Legacy.tar.gz` |
| rn6 | `rn6` / `rn6.tar.gz` | `rn6_Legacy` / `rn6_Legacy.tar.gz` |
| rn7 | `rn7` / `rn7.tar.gz` | `rn7_Legacy` / `rn7_Legacy.tar.gz` |
| dog | `dog` / `dog.tar.gz` | `dog_Legacy` / `dog_Legacy.tar.gz` |
| c_elegans | `c_elegans` / `c_elegans.tar.gz` | `c_elegans_Legacy` / `c_elegans_Legacy.tar.gz` |

## Reproduce a Previous Analysis

Use a SigProfilerMatrixGenerator release that recognizes the `_Legacy` genome
names. Install the Legacy reference, then select that same name when generating
matrices. For example, if the previous analysis used the former GRCh38 archive:

```bash
SigProfilerMatrixGenerator install GRCh38_Legacy
SigProfilerMatrixGenerator matrix_generator previous_project GRCh38_Legacy /path/to/original_inputs
```

The equivalent Python calls are:

```python
from SigProfilerMatrixGenerator import install as genInstall
from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen

genInstall.install("GRCh38_Legacy")
matGen.SigProfilerMatrixGeneratorFunc(
    "previous_project", "GRCh38_Legacy", "/path/to/original_inputs"
)
```

Substitute the appropriate genome name from the table. An older reference
installed under the standard name is **not** automatically renamed to its
`_Legacy` identity after a software upgrade. Install and select the Legacy
identity explicitly. If you also need the corrected reference for new analyses,
install it under the standard name; the two identities can coexist.

## Install from a Downloaded Archive

The archives are available at
`ftp://alexandrovlab-ftp.ucsd.edu/pub/tools/SigProfilerMatrixGenerator/`.
If automatic downloading is unavailable, download the exact archive filename
from the table into a local directory, then pass **the directory**, not the
archive path, to the CLI:

```bash
SigProfilerMatrixGenerator install GRCh38_Legacy --local_genome /path/to/archive-directory
```

For this example, the directory must contain `GRCh38_Legacy.tar.gz`. The CLI
checks the installed chromosome files against the registered reference
checksums. Do not rename a corrected archive to a Legacy filename or vice versa.

## Reproducibility Limits

The Legacy archive preserves the previously distributed reference data, but
does not restore an older version of the tool. For the closest possible
reproduction, keep the original input files, SigProfilerMatrixGenerator and
dependency versions, command arguments, and any BED/exome files. Differences
caused by code or settings may remain even when the Legacy archive is used.
Record the reference identity (`GRCh38` versus `GRCh38_Legacy`) with each run.

The separate `GRCh37_havana`, `GRCh38_havana`, and `mm10_havana` references
are not substitutes for these Legacy archives. See
[Reference Correctness](TSB-Reference-Correctness.md) for the scope of the
corrections and [Supported Genomes](Currently-Supported-Genomes.md) for genome
descriptions.
