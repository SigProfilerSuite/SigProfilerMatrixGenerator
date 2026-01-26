# Output - vcf_files

This page describes the vcf_files output folder structure.

## Overview

The vcf_files folder contains text-based files with original mutations paired with their SigProfilerMatrixGenerator classifications.

## Folder Structure

```
vcf_files/
├── DBS/     # Dinucleotide substitutions
├── MNS/     # Multinucleotide substitutions
├── SNV/     # Single nucleotide variants
└── ID/      # Small insertions and deletions
```

---

## Subfolders

### DBS (Dinucleotide Substitutions)

Contains files with double base substitution mutations and their DBS classifications.

**Output includes:**
- Original mutation coordinates
- Reference dinucleotide
- Alternate dinucleotide
- DBS classification category

### MNS (Multinucleotide Substitutions)

Contains mutations involving 3 or more consecutive nucleotides.

**Output includes:**
- Mutation coordinates
- Reference sequence
- Alternate sequence
- MNS classification

### SNV (Single Nucleotide Variants)

Contains single base substitutions with their SBS classifications.

**Output includes:**
- Chromosome and position
- Reference nucleotide
- Alternate nucleotide
- Sequence context
- SBS96 classification
- Transcriptional strand information

### ID (Insertions and Deletions)

Contains small insertions and deletions with their ID classifications.

**Output includes:**
- Mutation coordinates
- Indel sequence
- Repeat/microhomology context
- ID classification category

---

## File Format

Each file is tab-delimited with the following general columns:

| Column | Description |
|--------|-------------|
| Sample | Sample name |
| Chromosome | Chromosome identifier |
| Position | Genomic position |
| Ref | Reference allele |
| Alt | Alternate allele |
| Context | Sequence context |
| Classification | SigProfilerMatrixGenerator category |
| Strand | Transcriptional strand (if applicable) |

---

## Usage

These files are useful for:

1. **Quality control:** Verify mutation classifications
2. **Custom analysis:** Export mutations with classifications for downstream analysis
3. **Visualization:** Create custom plots with mutation-level data
4. **Integration:** Combine with other genomic annotations

---

## Enabling vcf_files Output

To generate vcf_files output, set `seqInfo=True`:

```python
matrices = matGen.SigProfilerMatrixGeneratorFunc(
    "project",
    "GRCh37",
    "/path/to/input",
    seqInfo=True
)
```
