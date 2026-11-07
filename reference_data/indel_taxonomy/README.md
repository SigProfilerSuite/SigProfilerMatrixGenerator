# Koh ID89 and ID476 taxonomy provenance

The optional classifiers implement the small-indel taxonomy in Koh et al.,
*A redefined InDel taxonomy provides insights into mutational signatures*,
Nature Genetics 57, 1132-1141 (2025), DOI
[10.1038/s41588-025-02152-y](https://doi.org/10.1038/s41588-025-02152-y).

The segmentation priorities and category definitions derive from the original
MIT-licensed [indelsig.tools.lib](https://github.com/Nik-Zainal-Group/indelsig.tools.lib)
at commit `d0bdb9b554dd3b63bcfecd75f58486bd54b3142d`:

- `src/code.cpp`: maximize 3-prime repeat coverage, then internal coverage,
  minimize the residual spacer, then minimize unit length.
- `R/indel_classification.R` and `R/indel_classification_full.R`: channel rules.
- `data/indel_template_type_4*.rda`: fixed category definitions.

The copyright and permission notice ships alongside `scripts/koh_indels.py` in
`scripts/LICENSE.indelsig.tools.lib`. No R runtime is required by MatrixGenerator.

## Interoperable Channel Names

Rows use the open upper-interval spelling used by the IndelSig browser and
`mSigSpectra`: e.g. single-base `R(9,)` includes all repeat counts >=9, rather
than discarding high-repeat events. ID89 similarly uses `R(8,)`, `R(7,)`, etc.
This is a naming/binning policy, not a claim that the event repeat count is 9.
The event report retains the actual repeat count.

The older reference scripts use some closed labels such as `R(5,9)` and offer
separate high-specificity filtering. The new feature does not apply that
filter automatically. Compare classifiers under the same input/filter policy.

## Independent Validation

The small deterministic fixture `tests/data/koh_indels_oracle.tsv` contains one
reference-matching case for every ID476 channel, also covering all 89 ID89
channels. Expected labels come from external R/C++ classification in
[`mSigSpectra`](https://github.com/steverozen/mSigSpectra) at
`1848df872cd6455a554ca737a608bc11f233d8a7`, not from the production Python
classifier. That GPL-3 package is an external validation oracle, not bundled
production code or an installed dependency.

The initial comparison used 15,641 deterministic synthetic cases, including
all nucleotide orientations, repeat boundaries, internal repeats, spaced
microhomology, and complex length bins. Every pair of channel labels matched.
The oracle harness substitutes a base-R reverse-complement helper for the
unavailable `fastrc` package and normalizes its one historical `Del(C):R(6,9)`
label to the oracle's own row-order spelling `Del(C):R(6,)`. Other classifier
and Rcpp segmentation code runs unchanged. Complex-bin expectations use the
explicit absolute net length-change convention below because the original
scripts incompletely handle net insertions and balanced delins.

Channel-order fixtures record the independent oracle's order. All inputs and
expected outputs are small synthetic test data, not patient data or extracted
signature profiles. Large generated results stay outside the repository.
The optional `tests/oracles/` utilities reproduce the complete comparison
without making R a package dependency.

## Classification Contracts

Literal REF alleles must match the complete selected reference sequence.
Trim common allele prefixes/suffixes, then left-align simple indels while
retaining a left anchor. Report unsupported alleles or missing/ambiguous context
instead of guessing. Complex delins use absolute net length-change bins
`(0,1)`, `(2,5)`, `(6,10)`, `(11,20)`, `(21,)` and collapse to ID89 `Complex`.
This is a documented implementation convention; confirmation of the original
authors' intent for balanced and net-insertion complex events remains pending.
Tests of this convention do not establish unchanged upstream agreement for
those cases.

Derive both labels from each event. Do not blindly collapse ID476 matrices:
`Del(6,):U2:R(4,)` combines events with four and five AT repeats that ID89
separates. An ID83 matrix alone likewise cannot supply the missing information.

Filtering uses the original input anchor and the existing API's inclusive
anchor bounds with its cushion. Normalization must not change panel membership.
This addition does not settle or change historical BED/exome conventions.

No corrected/default/Legacy reference archive changes for this feature. It
uses the DNA retained in the installed encoded chromosome files. Counts are not
genome-opportunity-normalized signatures or a clinical classifier.
