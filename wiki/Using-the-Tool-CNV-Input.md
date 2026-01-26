# Using the Tool - CNV Input

This section describes how to generate Copy Number Variation (CNV) matrices using SigProfilerMatrixGenerator.

## CNV Quick Start Example

To generate a copy number matrix, provide an absolute path to a multi-sample segmentation file obtained from one of the supported copy number calling tools.

**Note:** If you have individual sample files, combine them into one file with the first column corresponding to the sample name.

## Supported CNV Callers

- ASCAT
- ASCAT_NGS
- SEQUENZA
- ABSOLUTE
- BATTENBERG
- FACETS
- PURPLE
- TCGA

## Example Input File (Battenberg)

| sample | chrom | startpos | endpos | nMaj1_A | nMin1_A | frac_1A | nMaj2_A | nMin1_A | frac_2A |
|--------|-------|----------|--------|---------|---------|---------|---------|---------|---------|
| NSLC-1060-T01 | 19 | 90407080 | 91002641 | 1 | 0 | 0.67 | 2 | 0 | 0.33 |

**Note:** For Battenberg input, information for both the clone and subclone is considered and counted as separate events if multiple subclones are present.

---

## Python Usage

```python
python3
>>> from SigProfilerMatrixGenerator.scripts import CNVMatrixGenerator as scna
>>> file_type = "BATTENBERG"
>>> input_file = "./SigProfilerMatrixGenerator/references/CNV/example_input/Battenberg_test.tsv"
>>> output_path = "/Users/user/CNVMatrixGenerator/example_output/"
>>> project = "Battenberg_test"
>>> scna.generateCNVMatrix(file_type, input_file, project, output_path)
```

### Command Line Usage

```bash
python ./SigProfilerMatrixGenerator/scripts/CNVMatrixGenerator.py BATTENBERG ./SigProfilerMatrixGenerator/references/CNV/example_input/Battenberg_test.tsv BATTENBERG-TEST ./SigProfilerMatrixGenerator/references/CNV/example_output/
```

---

## R Usage

### Setting up R Environment with Conda (Recommended)

```bash
conda create --name spmg_r -y
conda activate spmg_r
conda install python=3.10 r-base r-devtools r-reticulate -c conda-forge -y
pip install SigProfilerMatrixGenerator
echo 'devtools::install_github("AlexandrovLab/SigProfilerMatrixGeneratorR")' | Rscript -
```

### R Example

```r
R
> library("reticulate")
> use_python("path_to_your_python3")
> py_config()
> library("SigProfilerMatrixGeneratorR")
> cnv <- CNVMatrixGenerator("BATTENBERG", "[your_repo]/test_data/CNV/Battenberg_test.tsv", "test_CNV", "[your_repo]/test_data/CNV")
```

---

## Function Arguments

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `file_type` | string | Segmentation/caller type | `"BATTENBERG"` |
| `input_file` | string | Path to the segmentation file | `"./path/to/file.tsv"` |
| `project` | string | Project name for this instance | `"my_project"` |
| `output_path` | string | Path to directory for output files | `"./output/"` |

### Supported File Types

```
["ASCAT", "ASCAT_NGS", "SEQUENZA", "ABSOLUTE", "BATTENBERG", "FACETS", "PURPLE", "TCGA"]
```

---

## CNV Classification Schema

The copy number classification schema consists of 48 mutually exclusive channels, divided by:

1. **Heterozygosity status** (Het vs LOH vs Homozygous Deletion)
2. **Segment size** (0-100kb, 100kb-1Mb, 1Mb-10Mb, 10Mb-40Mb, >40Mb)
3. **Total Copy Number (TCN)**

### Heterozygous State
Both alleles are retained and either one or both can be amplified.
- TCN categories: 1, 2, 3-4, 5-8, ≥9

### Loss of Heterozygosity (LOH)
One allele is lost; the remaining allele can be duplicated.
- TCN categories: 0, 1, 2, 3-4, 5-8, ≥9

### Homozygous Deletions
Both alleles are lost.
- Size categories: 0-100kb, 100kb-1Mb, >1Mb
