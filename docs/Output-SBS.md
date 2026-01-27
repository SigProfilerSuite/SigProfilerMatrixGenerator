# Output - SBS (Single Base Substitution)

This page provides detailed information about Single Base Substitution (SBS) output files.

## Overview

SBS matrices classify single nucleotide variants using pyrimidine notation (C>X or T>X mutations only, as purine mutations are represented by their complementary pyrimidine).

## Output Files

| File | # of Sequences | Calculation |
|------|----------------|-------------|
| test.SBS6.all | 6 | 6 mutation types |
| test.SBS24.all | 24 | 6 × 4 TSB categories |
| test.SBS96.all | 96 | 4 × 6 × 4 |
| test.SBS384.all | 384 | 96 × 4 TSB categories |
| test.SBS1536.all | 1536 | 4 × 4 × 6 × 4 × 4 |
| test.SBS6144.all | 6144 | 1536 × 4 TSB categories |

---

## SBS-6

The 6 basic mutation types (using pyrimidine notation):

1. **C>A** - Cytosine to Adenine
2. **C>G** - Cytosine to Guanine
3. **C>T** - Cytosine to Thymine
4. **T>A** - Thymine to Adenine
5. **T>C** - Thymine to Cytosine
6. **T>G** - Thymine to Guanine

---

## SBS-24

SBS-24 extends SBS-6 by incorporating 4 transcriptional strand bias categories:

| Category | Description |
|----------|-------------|
| **T** | Transcribed strand |
| **U** | Untranscribed strand |
| **B** | Bidirectional transcription |
| **N** | Non-transcribed (intergenic) |

**Calculation:** 6 mutation types × 4 TSB categories = 24 sequences

---

## SBS-96

SBS-96 is the standard mutational signature format, incorporating the immediate 5' and 3' sequence context.

**Format:** `5'[X>Y]3'`

Where:
- 5' = One of 4 possible nucleotides (A, C, G, T)
- X>Y = One of 6 mutation types
- 3' = One of 4 possible nucleotides (A, C, G, T)

**Calculation:** 4 (5' context) × 6 (mutations) × 4 (3' context) = 96 sequences

**Example:** `A[C>T]G` represents a C>T mutation with A at the 5' position and G at the 3' position.

---

## SBS-384

SBS-384 extends SBS-96 by incorporating transcriptional strand bias.

**Calculation:** 96 × 4 TSB categories = 384 sequences

**Example:** `T:A[C>T]G` represents a C>T mutation in A_G context on the transcribed strand.

---

## SBS-1536

SBS-1536 extends the sequence context to include two nucleotides on each side.

**Format:** `5'5'[X>Y]3'3'`

**Calculation:** 4 × 4 × 6 × 4 × 4 = 1536 sequences

**Example:** `AA[C>T]GG` represents a C>T mutation with AA at 5' and GG at 3'.

---

## SBS-6144

SBS-6144 combines SBS-1536 with transcriptional strand bias categories.

**Calculation:** 1536 × 4 TSB categories = 6144 sequences

---

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.all` | All mutations (default) |
| `.exome` | Mutations mapped to exome regions |
| `.region` | Mutations mapped to custom BED file regions |
| `.chrX` | Chromosome-specific mutations |
