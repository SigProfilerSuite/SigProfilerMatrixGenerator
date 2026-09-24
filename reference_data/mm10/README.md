# mm10 corrected TSB provenance

The corrected `mm10` reference uses GRCm38.p6 (`GCA_000001635.8`) chromosome
FASTA files. The historical package documented "ENSEMBL database version
93.38" as its source. Verifying the bundled transcript set against candidate
Ensembl releases found an exact, zero-diff match only at **release 94**: 0 of
the 57,718 bundled transcripts are retired or reclassified in release 94, and
release 94 has exactly 58 additional protein-coding transcripts (by
`gene_biotype`) absent from the bundle, listed in `excluded_transcript_ids.txt`.
Release 93 gave 414 retired IDs and 26 reclassified IDs against the bundle,
so release 94 is used as the actual annotation source; the historical "93.38"
note appears to be an approximation. `source_manifest.tsv` records SHA-256 and
BSD `sum` values for the release-94 FASTA/GTF files, verified against
Ensembl's own published `CHECKSUMS`. FASTA sequence content is confirmed
byte-identical between release 93 and release 94 for all 22 chromosomes
(only the gzip container differs), so this does not represent any change to
the DNA sequence itself, only to which annotation release matches the bundle.

All 57,718 bundled transcript rows match the pinned GTF's coordinates,
strand, and gene exactly (checked programmatically, not just by ID). The 58
additional GTF protein-coding transcripts remain excluded so the correction
changes only TSB interval semantics, not annotation scope. Concatenating the
historical transcript files in byte-sorted filename order has SHA-256
`a43115660315a953ccad23023339b6f7ae2ba448f3dcf849c977e99152b5583c`.

Independent event-sweep validation (a from-scratch reimplementation, not a
reuse of `save_tsb_192.py`'s logic) checked all 2,725,537,669 positions across
all 22 chromosomes and found no DNA base mismatches and no strand-state
mismatches. Relative to the historical archive, 770,227 strand labels
changed: 9,926 N-to-T, 9,615 N-to-U, 337,339 T-to-B, and 413,347 U-to-B - the
same four transition classes established for GRCh38, GRCh37, and mm9, with no
other transition type occurring.

The corrected logical reference `mm10` resolves to `mm10.tar.gz`. `mm10_Legacy`
resolves to a copy of the untouched historical archive named
`mm10_Legacy.tar.gz`; the installer safely remaps its internal `mm10/`
directory to `mm10_Legacy/`.

## Context tables: a pre-existing data/archive inconsistency, unrelated to this fix

Before rebuilding anything, the currently-shipped mm10 context-distribution
tables were checked for internal consistency against the currently-registered
`CHECKSUMS["mm10"]` archive (the same archive this correction starts from).
They are **not** consistent:

- The four strand-aware tables (`24`, `384`, `6144`, `DBS186`) do not match
  what the documented generation pipeline (`save_context_distribution.py`)
  actually produces from the currently-shipped `mm10` TSB archive. For
  example, the existing `context_counts_mm10_24.csv` records `T:C=6402185`
  for chromosome 19; independently re-running the real generator against the
  real, checksum-verified archive gives `T:C=6127048` for the same
  chromosome - confirmed two ways: with a from-scratch vectorized
  reimplementation, and by running the repository's own unmodified,
  unvectorized `context_distribution()` function directly. This is a
  pre-existing provenance drift (the shipped tables were built from some
  other TSB revision than what is registered today), not something
  introduced by or related to the TSB strand-labeling defect being fixed
  here.
- The strand-independent ("sequence-only") tables (`6`, `96`, `1536`, `DBS`)
  do not depend on TSB state, so their whole-genome **counts** files are
  byte-identical between the corrected and Legacy identities in every case
  checked - confirming the underlying per-chromosome tallies genuinely
  haven't changed. Their whole-genome **distribution** (proportion) files are
  a different story: recomputing proportions directly from that shared,
  identical counts file reproduces the corrected distribution file exactly,
  but does **not** reproduce the shipped Legacy distribution file for three
  of the four context types. Concretely (max relative difference, WGS only):

  | context | female | male | note |
  |---|---|---|---|
  | `6` | 2.2e-06 | (no historical file; see below) | float-noise only |
  | `96` | 2.5e-02 | 2.5e-02 | concentrated at chr19, rare trinucleotide contexts (e.g. `ACG`/`GCG`) |
  | `1536` | 2.5e-02 | 2.5e-02 | concentrated at chr19, rare pentanucleotide contexts |
  | `DBS` | 2.5e-02 | 2.5e-02 | concentrated at chr19, the `CG` dinucleotide |

  In other words, the shipped historical distribution files for `96`,
  `1536`, and `DBS` are internally inconsistent with the shipped historical
  counts file they should have been derived from - a real ~2.5% discrepancy
  concentrated on one chromosome, not a rounding artifact. This is the same
  symptom as the strand-aware drift above (a historical file that doesn't
  reconcile with other historical files it should match), just affecting
  sequence-only tables too. Separately, the shipped
  `context_distribution_mm10_6_female_exome.csv` includes a stray `Y` column
  despite being labeled "female" (female gender excludes Y by construction) -
  noted here, not investigated further; it does not affect any value used by
  this correction.
- This same investigation also explained a header artifact present in every
  currently-shipped `*_exome.csv` file across every genome (GRCh37, mm9,
  mm10 alike): `context_distribution_BED`'s `chromosomes_sort = chromosomes`
  aliases the same list object used for the CSV header, so appending `"MT"`
  and `"M"` for interval-file sorting purposes leaks two permanent,
  always-zero columns into the header. This is harmless (the columns are
  always zero) and is reproduced here only for consistency with every other
  genome's existing exome tables, not because it is desirable.

Per Mishu/agentA's existing precedent, `mm10_Legacy` preserves the **currently
shipped** context tables byte-for-byte, drift included, since Legacy's purpose
is exact historical reproducibility. The corrected `mm10` identity's context
tables were regenerated directly from the corrected, checksum-verified TSB
archive using the repository's own generation logic (cross-validated against
the real `context_distribution`/`context_distribution_BED` functions on real
data before use - see "Validation of the regeneration method" below), so they
are internally consistent with the corrected archive by construction. This
drift is flagged here as a separate, out-of-scope finding for later review; it
was not chased further or "fixed" globally across other genomes.

## The missing `context_distribution_mm10_6_male.csv`

Every context size/gender/exome combination mm10 ships has both a `_male` and
a `_female` variant except context `6`, which was missing
`context_distribution_mm10_6_male.csv` (only `_female`, `_female_exome`, and
`_male_exome` existed). `context_counts_mm10_6.csv`'s header already includes
`Y` (the male chromosome set), showing the counts file was always generated
under male gender; only the corresponding whole-genome male distribution file
was never produced or was lost. Context `6` does not use transcription-strand
data at all (only nucleotide identity), so it is unaffected by the TSB
correction and could safely be derived from either archive. It was
regenerated from the corrected archive using the unmodified generation logic
and is included for the corrected `mm10` identity only, where it fills a real
gap. `mm10_Legacy` preserves the exact historical 47-file footprint and does
not gain this file, since it never shipped historically; "safe to derive"
is not the same claim as "was previously shipped," and Legacy's purpose is
the latter.

## Validation of the regeneration method

`save_context_distribution.py`'s real `context_distribution()` and
`context_distribution_BED()` functions are a pure-Python per-base loop; a
full run across all context sizes/genders/exome combinations for a 2.7-billion
base genome is impractically slow. A vectorized (numpy) reimplementation was
written and cross-validated against the real, unmodified functions before
being trusted for the full rebuild:

- Whole-genome, strand-aware context (`24`): matched the real
  `context_distribution()` exactly on chromosome MT (tiny, fast to run
  directly) and on the full chromosome 19 (61,431,566 bases, run to
  completion with the real function as an independent ground truth) - every
  count identical.
- Dinucleotide contexts (`DBS`, `DBS186`): matched the real
  `context_distribution()` exactly on chromosome MT, including the `Q:`
  bias-suppressed dinucleotide classes.
- Exome/BED-restricted counting: matched the real, currently-shipped
  `context_counts_mm10_1536_exome.csv` and
  `context_distribution_mm10_1536_male_exome.csv` (a strand-independent,
  therefore trustworthy, existing table) exactly once the reimplementation
  was corrected to replicate the reference algorithm's per-BED-line
  processing, including counting a position once for every exome probe
  interval that covers it when intervals overlap (confirmed present in the
  real mm10 interval list, e.g. `chr7:9754728-9755448` and
  `chr7:9754729-9755449`), rather than deduplicating overlapping intervals.

## Reproducing the corrected archive

```bash
shasum -a 256 "$SOURCE"/*.gz
mkdir -p "$BUILD/chrom_string" "$BUILD/tsb/mm10"
for fasta in "$SOURCE"/Mus_musculus.GRCm38.dna.chromosome.*.fa.gz; do
    chromosome="${fasta##*.chromosome.}"
    chromosome="${chromosome%.fa.gz}"
    gzip -dc "$fasta" | tail -n +2 | tr -d '\n\r' \
        > "$BUILD/chrom_string/$chromosome.txt"
done
PYTHONPATH=. python -c \
  'from SigProfilerMatrixGenerator.scripts.save_tsb_192 import save_tsb; save_tsb("'$BUILD'/chrom_string", "SigProfilerMatrixGenerator/references/chromosomes/transcripts/mm10", "'$BUILD'/tsb/mm10")'
```

The strand-dependent 24, 384, 6144, and DBS186 opportunity tables were
rebuilt from the corrected bytes. Strand-collapsed exome totals reproduce the
corrected archive's own whole-genome/exome conservation exactly.
