# Optional independent oracle comparison

These developer utilities are not runtime dependencies and do not run in CI.
The committed golden fixtures let ordinary Python tests run offline.

Use a separate results directory outside the repository. From the repo root:

```bash
RESULTS=/absolute/path/outside/repository/koh_validation
python tests/oracles/generate_inputs.py "$RESULTS"
git clone https://github.com/steverozen/mSigSpectra.git "$RESULTS/upstream_mSigSpectra"
git -C "$RESULTS/upstream_mSigSpectra" checkout 1848df872cd6455a554ca737a608bc11f233d8a7
Rscript tests/oracles/reference.R \
  "$RESULTS/oracle_inputs.tsv" "$RESULTS/oracle_results.tsv" \
  "$RESULTS/upstream_mSigSpectra"
PYTHONPATH=. python tests/oracles/compare_outputs.py "$RESULTS"
```

The R environment needs `Rcpp`, `stringi` and a C++ compiler. The scripts do
not install packages. The classifier remains external to this repository.
The R utility verifies its exact Git revision before executing its functions.
It replaces the optional `fastrc` dependency with a base-R reverse complement,
and uses the explicit complex-length convention described in
`reference_data/indel_taxonomy/README.md`. The Python classifier is not involved
in generating reference labels. Check both mismatches and skipped/oracle-error
counts in the JSON report, not just channel coverage. Generated test data is
synthetic; these are not clinical accuracy measurements.

`golden_examples.tsv` selects matching examples for all channels. Updating a
committed fixture requires reviewing the full comparison and its pinned source,
not merely replacing expected labels to make tests pass.
