# Quick Start Example

This section provides a quick start guide for using SigProfilerMatrixGenerator.

## Step 1: Start Python

Start a Python terminal session and verify you're running Python 3:

```bash
python3
```

You should see output like:
```
Python 3.5.2 (v3.5.2:4def2a2901a5, Jun 26 2016, 10:47:25)
[GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

## Step 2: Verify Installation

Check if SigProfilerMatrixGenerator is installed:

```python
>>> help("modules")
```

Look for `SigProfilerMatrixGenerator` in the list of available modules.

If not installed, follow the instructions on the [Installation - Python](Installation-Python.md) page.

## Step 3: Install Reference Genome

Install your desired reference genome:

```python
>>> from SigProfilerMatrixGenerator import install as genInstall
>>> genInstall.install('GRCh37')
```

This example installs the human GRCh37 assembly. You can install any of the [available genome assemblies](Currently-Supported-Genomes.md).

**Note:**
- ~3 GB of storage is required per genome
- This step may take some time due to large file sizes

## Step 4: Prepare Input Files

Place your VCF files in your desired project folder. We recommend naming it based on your project's name.

Supported input formats:
- VCF (Variant Call Format) - one file per sample
- MAF (Mutation Annotation Format)
- ICGC format
- Simple text files (tab-delimited)

## Step 5: Generate Matrices

From within a Python session, generate the matrices:

```python
>>> from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
>>> matrices = matGen.SigProfilerMatrixGeneratorFunc("test", "GRCh37", "/Users/user/Desktop/test", plot=True)
```

### Parameter Layout

```python
SigProfilerMatrixGeneratorFunc(project, reference_genome, path_to_input_files, plot)
```

| Parameter | Description |
|-----------|-------------|
| `project` | Your project name (string) |
| `reference_genome` | Reference genome to use (e.g., "GRCh37", "GRCh38") |
| `path_to_input_files` | Full path to directory containing your input VCF files |
| `plot` | Set to `True` to generate visualization plots |

## Expected Output

After successful execution, you will find the following in your output directory:

```
project_name/
├── input/          # Copies of input files
├── logs/           # Log and error files
└── output/
    ├── SBS/        # Single base substitution matrices
    ├── DBS/        # Double base substitution matrices
    ├── ID/         # Insertion/deletion matrices
    ├── TSB/        # Transcriptional strand bias results
    ├── plots/      # Visualization plots (if plot=True)
    └── vcf_files/  # Processed VCF files
```

## Complete Example

```python
# Start Python
python3

# Import the module
>>> from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen

# Generate matrices with plotting enabled
>>> matrices = matGen.SigProfilerMatrixGeneratorFunc(
...     "my_cancer_project",      # project name
...     "GRCh37",                  # reference genome
...     "/path/to/my/vcf/files",  # input directory
...     plot=True                  # generate plots
... )
```

For all function arguments and their types, see the [Using the Tool - SBS, ID, DBS Input](Using-the-Tool-SBS-ID-DBS-Input.md) section.
