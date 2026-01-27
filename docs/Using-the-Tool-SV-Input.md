# Using the Tool - SV Input

This section describes how to generate Structural Variant (SV) matrices using SigProfilerMatrixGenerator.

## Input Format

The first six columns are required, and either the column `svclass` OR the columns `strand1` & `strand2` must be present.

### Example with SV Class (TSV or CSV file)

| chrom1 | start1 | end1 | chrom2 | start2 | end2 | svclass |
|--------|--------|------|--------|--------|------|---------|
| 19 | 21268384 | 21268385 | 19 | 21327858 | 21327859 | deletion |

### Example with Strand Information (TSV or CSV file)

| chrom1 | start1 | end1 | chrom2 | start2 | end2 | strand1 | strand2 |
|--------|--------|------|--------|--------|------|---------|---------|
| 19 | 21268384 | 21268385 | 19 | 21327858 | 21327859 | + | + |

### SV Classes

- `deletion`
- `translocation`
- `tandem-duplication`
- `inversion`

---

## Python Usage

```python
# Navigate to SVMatrixGenerator directory and start python3 interpreter
from SigProfilerMatrixGenerator.scripts import SVMatrixGenerator as sv

input_dir = "./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast"
output_dir = "./SigProfilerMatrixGenerator/references/SV/"
project = "560-Breast"

sv.generateSVMatrix(input_dir, project, output_dir)
```

### Command Line Usage

```bash
python3 ./SigProfilerMatrixGenerator/scripts/SVMatrixGenerator.py \
    ./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast \
    560-Breast \
    ./SigProfilerMatrixGenerator/references/SV/example_output/
```

Arguments: `input_dir`, `project`, `output_dir`

---

## R Usage

### Setting up R Environment with Conda (Recommended)

```bash
conda create --name spmg_r -y
conda activate spmg_r
conda install python=3.10 r-base r-devtools r-reticulate -c conda-forge -y
pip install SigProfilerMatrixGenerator
echo 'devtools::install_github("SigProfilerSuite/SigProfilerMatrixGeneratorR")' | Rscript -
```

### R Example

```r
R
> library("reticulate")
> use_python("path_to_your_python3")
> py_config()
> library("SigProfilerMatrixGeneratorR")
> sv <- SVMatrixGenerator("[your_repo]/test_data/SV", "test_SV", "[your_repo]/test_data/")
```

---

## Function Arguments

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `input_dir` | string | Path to directory containing SV bedpe files (one per sample) | `"./references/SV/example_input/560-Breast/"` |
| `project` | string | Project name for this instance | `"560-Breast"` |
| `output_dir` | string | Path to directory for output files | `"./references/SV/example_output/"` |

**Note:** If the output directory doesn't exist, a new one will be created.

---

## SV Classification Schema (SV32)

The SV32 classification schema bins structural variants by:

1. **Size categories:**
   - 0-10kb
   - 10kb-100kb
   - 100kb-1Mb
   - 1Mb-10Mb
   - >10Mb

2. **Clustering status:**
   - Clustered
   - Non-clustered

3. **SV type:**
   - Deletion
   - Tandem duplication
   - Inversion
   - Translocation (size-independent)

This creates a 32-channel classification matrix for comprehensive structural variant analysis.
