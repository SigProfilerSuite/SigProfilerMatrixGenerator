# Output - TSB (Transcriptional Strand Bias)

This page provides detailed information about Transcriptional Strand Bias (TSB) output files.

## Overview

TSB analysis examines whether mutations show preferential occurrence on the transcribed or untranscribed strand of genes, which can indicate specific mutational processes.

## Output Files

| File | # of Sequences | Calculation |
|------|----------------|-------------|
| strandBiasTest_24.txt | 24 | 6 × 4 |
| strandBiasTest_384.txt | 384 | 4 × 24 × 4 |
| strandBiasTest_6144.txt | 6144 | 4 × 384 × 4 |

---

## Strand Bias Categories

| Category | Code | Description |
|----------|------|-------------|
| Transcribed | T | Mutation on the transcribed (template) strand |
| Untranscribed | U | Mutation on the untranscribed (coding) strand |
| Non-transcribed | N | Mutation in intergenic region (no transcription) |
| Bidirectional | B | Mutation in region with overlapping transcription |
| Questionable | Q | Ambiguous strand assignment |

---

## Statistical Output

The TSB analysis produces statistical metrics for each mutation type:

### Enrichment Values

- **Transcribed strand enrichment:** Ratio of mutations on transcribed vs untranscribed strand
- **Untranscribed strand enrichment:** Ratio of mutations on untranscribed vs transcribed strand

### Statistical Tests

| Metric | Description |
|--------|-------------|
| **p-value** | Statistical significance of strand bias |
| **q-value (FDR)** | False discovery rate corrected p-value |
| **Fold enrichment** | Magnitude of strand bias |

---

## strandBiasTest_24.txt

Contains strand bias analysis for the 6 basic mutation types across 4 TSB categories.

**Format:**
- Rows: 6 mutation types (C>A, C>G, C>T, T>A, T>C, T>G)
- Categories: T, U, N, B

---

## strandBiasTest_384.txt

Extends the analysis to include sequence context (SBS-96 format) with strand bias.

**Calculation:** 4 (5' context) × 24 × 4 (3' context) = 384 sequences

---

## strandBiasTest_6144.txt

Full extended context analysis with strand bias.

**Calculation:** 4 × 384 × 4 = 6144 sequences

---

## Interpretation

### Transcriptional Strand Bias Patterns

| Pattern | Possible Cause |
|---------|----------------|
| More C>T on transcribed strand | Transcription-coupled repair of UV damage |
| More T>A on untranscribed strand | Adenine damage by certain carcinogens |
| No strand bias | Random/replication-associated mutations |

### Biological Significance

Transcriptional strand bias can indicate:

1. **Transcription-coupled nucleotide excision repair (TC-NER):** Preferential repair of bulky lesions on the transcribed strand
2. **Transcription-associated mutagenesis:** Increased mutation rates during transcription
3. **DNA damage patterns:** Certain mutagens preferentially damage specific strands

---

## Usage Notes

- TSB analysis requires `tsb_stat=True` parameter
- Results are most meaningful for samples with sufficient mutation counts
- Consider multiple testing correction when interpreting p-values
