# Output - DBS (Double Base Substitution)

This page provides detailed information about Double Base Substitution (DBS) output files.

## Overview

DBS matrices classify dinucleotide variants where two adjacent bases are mutated simultaneously.

## Output Files

| File | # of Sequences | Description |
|------|----------------|-------------|
| test.DBS78.all | 78 | Pyrimidine dinucleotide variants |
| test.DBS186.all | 186 | 78 + TSB categories |
| test.DBS1248.all | 1248 | With flanking nucleotide context |
| test.DBS2976.all | 2976 | Extended context + TSB |

---

## DBS-78

The DBS78 file contains the frequency of pyrimidine double nucleotide variants.

### Dinucleotide Combinations

Only the 10 dinucleotide combinations with the highest pyrimidine content are considered:
- AC, AT, CC, CG, CT, GC, TA, TC, TG, TT

### Mutation Possibilities

- 4 combinations (CG, GC, AT, TA) have 6 possible mutations each
- 6 combinations have 9 possible mutations each

**Calculation:** (6 × 4) + (9 × 6) = 24 + 54 = 78 combinations

**Example:** Line listing `AC>CG` shows the frequency of AC to CG mutations across all samples.

---

## DBS-186

DBS-186 extends DBS-78 by incorporating transcriptional strand bias categories.

### Pyrimidine-only Dinucleotides

The 4 dinucleotide combinations consisting only of pyrimidines (CT, TC, CC, TT) are categorized into:

| Category | Description |
|----------|-------------|
| **T** | Transcribed strand |
| **U** | Untranscribed strand |
| **N** | Non-transcribed |
| **B** | Bidirectional |
| **Q** | Questionable (for other combinations) |

**Calculation:**
- 36 sequences × 4 categories = 144
- Plus questionable categories = 186 total

**Example:** `T:AC>GA` indicates an AC sequence on the transcribed strand mutating to GA.

---

## DBS-1248

DBS-1248 adds flanking nucleotide context to DBS-78.

**Format:** `N[XY>ZW]N`

Where N represents any nucleotide at the 5' or 3' position.

**Calculation:** 4 (5' nucleotide) × 78 × 4 (3' nucleotide) = 1248 combinations

**Example:** `A[AC>CG]C` corresponds to AACC sequences mutating to ACGC.

---

## DBS-2976

DBS-2976 extends DBS-186 with flanking nucleotide context.

**Calculation:** 4 × 186 × 4 = 2976 combinations

**Example:** `T:A[AC>CG]T` corresponds to AACT on the transcribed strand mutating to ACGT.

---

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.all` | All mutations (default) |
| `.exome` | Mutations mapped to exome regions |
| `.region` | Mutations mapped to custom BED file regions |
| `.chrX` | Chromosome-specific mutations |
