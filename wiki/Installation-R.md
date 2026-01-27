# Installation - R (R-wrapper)

This section will help you set up the necessary software and packages required to run SigProfilerMatrixGeneratorR.

**Important:** You must first install the Python package for SigProfilerMatrixGenerator before installing the R wrapper.

## Prerequisites

- **Internet Connection**
- **Python** - v3.4+
- **pandas** - any version (automatically downloaded with SigProfilerMatrixGenerator)
- **Wget** - v1.9
- **SigProfilerPlotting** - latest version (automatically downloaded with SigProfilerMatrixGenerator)
- **Reference genomes** - At least one reference genome must be downloaded and installed prior to use

## Step 1: Install Python Package

First, follow the [Python Installation](Installation-Python) instructions to install the base SigProfilerMatrixGenerator package:

```bash
pip install SigProfilerMatrixGenerator
```

## Step 2: Install R Dependencies

You must first install the `devtools` and `reticulate` libraries in R:

```r
R
> install.packages("devtools")
> install.packages("reticulate")
```

## Step 3: Install SigProfilerMatrixGeneratorR

Once the dependencies are installed, you can install SigProfilerMatrixGeneratorR:

```r
R
> library("reticulate")
> use_python("path_to_your_python3")
> py_config()
> library("devtools")
> install_github("SigProfilerSuite/SigProfilerMatrixGeneratorR")
```

Replace `"path_to_your_python3"` with the actual path to your Python 3 installation (e.g., `/usr/local/bin/python3` or the path from your conda environment).

## Step 4: Install Reference Genome

Prior to use of SigProfilerMatrixGeneratorR, the reference genome files need to be installed:

```r
R
> library("SigProfilerMatrixGeneratorR")
> install('GRCh37', rsync=FALSE, bash=TRUE)
```

This example installs the human GRCh37 assembly reference files. You can install any of the [available genome assemblies](Currently-Supported-Genomes).

**Note:** The installation process saves custom reference files for all chromosomes in the genome assembly, requiring ~3 GB of storage per genome.

## Setting up R Environment with Conda (Recommended)

For a streamlined setup, you can use conda to create an environment with all dependencies:

```bash
conda create --name spmg_r -y
conda activate spmg_r
conda install python=3.10 r-base r-devtools r-reticulate -c conda-forge -y
pip install SigProfilerMatrixGenerator
echo 'devtools::install_github("SigProfilerSuite/SigProfilerMatrixGeneratorR")' | Rscript -
```

## Upgrades

To upgrade SigProfilerMatrixGenerator:

```bash
pip install SigProfilerMatrixGenerator --upgrade
```

Then reinstall the R package:

```r
R
> library("devtools")
> install_github("SigProfilerSuite/SigProfilerMatrixGeneratorR")
```
