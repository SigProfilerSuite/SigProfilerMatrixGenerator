# Using the Tool - SBS, ID, DBS Input

SigProfilerMatrixGenerator generates mutational matrices for Single Base Substitutions (SBS), Insertions/Deletions (ID), and Doublet Base Substitutions (DBS) from input variant files.

## Python Usage

From within a Python session, generate matrices as follows:

```python
python3
>>> from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
>>> matrices = matGen.SigProfilerMatrixGeneratorFunc("test", "GRCh37", "/Users/test/Desktop/test/")
```

## R Usage

From within an R session:

```r
R
> library("reticulate")
> use_python("path_to_your_python3")
> py_config()
> library("SigProfilerMatrixGeneratorR")
> matrices <- SigProfilerMatrixGeneratorR("test", "GRCh37", "/Users/test/Desktop/test/")
```

---

## Function Arguments

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `project` | string | Project name for this instance of matrix generation | `"alexandrov_lab_test_1"` |
| `genome` | string | Reference genome to use | `"GRCh37"` |
| `vcfFiles` | string | Full path to the input files folder | `"/Users/test/Desktop/test/"` |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `exome` | boolean | `False` | Downsamples mutational matrices to exome regions |
| `bed_file` | string | `None` | Path to BED file for custom region downsampling |
| `chrom_based` | boolean | `False` | Outputs chromosome-based matrices |
| `plot` | boolean | `False` | Integrates with SigProfilerPlotting for visualizations |
| `tsb_stat` | boolean | `False` | Outputs transcriptional strand bias test results |
| `seqInfo` | boolean | `False` | Outputs original mutations with SigProfilerMatrixGenerator classification |
| `cushion` | integer | `100` | Adds Xbp cushion to exome/bed_file ranges |

**Note:** All `string` arguments must be surrounded by quotation marks (e.g., `"test"`), and all `boolean` arguments must be `True` or `False`.

---

## Input File Formats

This tool supports the following input formats:

| Format | Description | Example |
|--------|-------------|---------|
| **MAF** | Mutation Annotation Format | [example.maf](https://docs.gdc.cancer.gov/Data/File_Formats/MAF_Format/) |
| **VCF** | Variant Call Format (each sample as separate file) | [example.vcf](https://samtools.github.io/hts-specs/VCFv4.2.pdf) |
| **ICGC** | ICGC submission format | [ICGC docs](https://docs.icgc.org/submission/guide/overview/submission-file-format/) |
| **Simple text** | Tab-delimited text file | See example below |

### Simple Text File Format

The simple text format requires the following columns:
- Sample name
- Chromosome
- Position
- Reference allele
- Alternate allele

---

## Output Folder Structure

The final output is divided into three folders:

### Input
Contains copies of the user-provided input files.

### Logs
Contains error and log files for the submitted job:
- `sigProfilerMatrixGenerator_[project]_[genome].err`
- `sigProfilerMatrixGenerator_[project]_[genome].out`

### Output
Contains the following subfolders:
- **DBS/** - Doublet base substitution matrices
- **SBS/** - Single base substitution matrices
- **ID/** - Insertion/deletion matrices
- **TSB/** - Transcriptional strand bias results
- **plots/** - Generated visualizations
- **vcf_files/** - Processed VCF files

---

## File Extensions

Output files have extensions indicating which arguments were passed:

| Extension | Description |
|-----------|-------------|
| `.all` | Default - all mutations |
| `.exome` | Mutations mapped to exome regions (`exome=True`) |
| `.region` | Mutations mapped to custom BED file regions |
| `.chrX` | Chromosome-specific mutations (`chrom_based=True`) |
