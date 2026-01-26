# Output - ID (Insertions and Deletions)

This page provides detailed information about Insertion and Deletion (ID/Indel) output files.

## Overview

ID matrices classify small insertions and deletions based on size, sequence context, and repeat/microhomology status.

## Output Files

| File | # of Sequences | Description |
|------|----------------|-------------|
| test.ID28.all | 28 | Basic indel classification |
| test.ID83.all | 83 | Extended classification |
| test.ID415.all | 415 | With TSB categories |
| test.ID8628.all | 8628 | Complete sequence information |

---

## ID-28

The ID28 file provides basic classification of insertions and deletions.

### Categories

| Category | Description | Rows |
|----------|-------------|------|
| 1:Del:C:0-5 | 1bp deletion of C in homopolymer length 0-5+ | 6 |
| 1:Del:T:0-5 | 1bp deletion of T in homopolymer length 0-5+ | 6 |
| 1:Ins:C:0-5 | 1bp insertion of C in homopolymer length 0-5+ | 6 |
| 1:Ins:T:0-5 | 1bp insertion of T in homopolymer length 0-5+ | 6 |
| long_Del | >1bp deletions at repeat regions | 1 |
| long_Ins | >1bp insertions at repeat regions | 1 |
| MH | Microhomology-mediated deletions | 1 |
| complex | Complex indels | 1 |

**Example:** `1:Del:C:3` corresponds to a deletion of C in a sequence N[C]CCCN (homopolymer of 4 C's).

---

## ID-83

ID-83 extends ID-28 by further categorizing repeat and microhomology indels.

### Long Deletions/Insertions at Repeats

| ID-28 Category | ID-83 Categories |
|----------------|------------------|
| long_Del | 2:Del:R:0-5, 3:Del:R:0-5, 4:Del:R:0-5, 5:Del:R:0-5 |
| long_Ins | 2:Ins:R:0-5, 3:Ins:R:0-5, 4:Ins:R:0-5, 5:Ins:R:0-5 |

### Microhomology

| ID-28 Category | ID-83 Categories |
|----------------|------------------|
| MH | 2:Del:M:1-5, 3:Del:M:1-5, 4:Del:M:1-5, 5:Del:M:1-5 |

**Notation:**
- `X:Del:R:Y` = Deletion of length X at repeat with Y repeat units
- `X:Del:M:Y` = Deletion of length X with Y bp microhomology

**Example:** `1:Del:C:1` corresponds to a deletion of C in sequence N[C]CN.

---

## ID-415

ID-415 categorizes each ID-83 category into 5 transcriptional strand bias categories.

**Calculation:** 83 × 5 = 415 combinations

### TSB Categories

| Category | Description |
|----------|-------------|
| **T** | Transcribed strand |
| **U** | Untranscribed strand |
| **N** | Non-transcribed |
| **B** | Bidirectional |
| **Q** | Questionable |

**Example:** `T:1:Del:C:5` corresponds to a deletion of C in homopolymer CCCCCC on the transcribed strand.

---

## ID-8628

ID-8628 provides complete information about the indel sequence for indels at repetitive regions with length less than 6bp.

### Format

| Pattern | Description |
|---------|-------------|
| 2:Del:TA:5 | Deletion of length 2 with sequence TC or GA (reverse complement) |
| 5:Ins:CCATC:2 | Insertion of length 5 with sequence CCATC at 2 repeat units |

This extended classification allows for more precise analysis of indel patterns.

---

## File Extensions

| Extension | Description |
|-----------|-------------|
| `.all` | All mutations (default) |
| `.exome` | Mutations mapped to exome regions |
| `.region` | Mutations mapped to custom BED file regions |
| `.chrX` | Chromosome-specific mutations |
