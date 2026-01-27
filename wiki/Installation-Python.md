# Installation - Python

This section will help you set up the necessary software and packages required to run SigProfilerMatrixGenerator.

## Prerequisites

- **Internet Connection**
- **Python** - v3.4+
- **pandas** - any version (automatically downloaded when you install SigProfilerMatrixGenerator)
- **Wget** - v1.9
- **SigProfilerPlotting** - latest version (automatically downloaded when you install SigProfilerMatrixGenerator)
- **Reference genomes** - latest version (must be downloaded separately after installation)

## Upgrades

If there is an updated version of the tool that has been released, use the following command within Terminal or the Command Line:

```bash
pip install SigProfilerMatrixGenerator --upgrade
```

This will upgrade the tool to its latest version.

---

## Mac/Unix Installation

For Mac/OSX systems, the use of a package manager like Conda is recommended to simplify environment setup.

### Check Python Version

Check that you have the required python version by opening Terminal (Cmd + Space, type terminal, and hit return) and entering:

```bash
python --version
```

By default, OSX systems come with a version of Python installed at `/usr/bin/python`. This system version of Python is currently Python 2.

If you have multiple versions of Python installed, try:

```bash
python3 --version
```

You should see output like:
```
Python 3.7.3
```

Follow [Python Installation](https://www.python.org/downloads/) instructions to download the most recent version if you do not have v3.4 or higher.

Installation instructions for Conda through the Anaconda distribution can be found at [Anaconda Installation](https://docs.anaconda.com/anaconda/install/).

### Check pip

Check if you have pip installed:

```bash
pip --version
```

You should see output similar to:
```
pip 19.0.1 from /Library/Frameworks/SomeFilePath/
```

This tells you which version of pip is currently installed, and which version of Python it is set up to install packages for.

### Install SigProfilerMatrixGenerator

Now that you've successfully downloaded all the required software, install SigProfilerMatrixGenerator using pip:

```bash
pip install SigProfilerMatrixGenerator
```

---

## Windows Installation

### Check Python Version

By default, Windows systems do not come with Python installed. Check if you have Python by opening Command Prompt (Win + R, type `cmd`, and press Enter) and entering:

```bash
python --version
```

If you have multiple versions of Python installed, try:

```bash
python3 --version
```

If you know you have Python 3.4+ installed but get an error like:
```
'python' is not recognized as an internal or external command
```

Then Python has not been added to the PATH environmental variable. Add it with:

```bash
setx PATH "%PATH%;[path_to_python where .exe file is]"
```

Follow [Python Installation](https://www.python.org/downloads/) to download Python for your operating system. **Make sure to check the "Add Python to PATH" box during installation.**

### Check pip

Check if you have pip installed:

```bash
pip --version
```

If pip is not recognized, add it to PATH:

```bash
setx PATH "%PATH%;[path_to_python]\Scripts\"
```

### Install SigProfilerMatrixGenerator

```bash
pip install SigProfilerMatrixGenerator
```

---

## Reference Genome Installation

Prior to use of SigProfilerMatrixGenerator, reference genome files need to be installed.

Install your desired reference genome from the command line as follows:

```python
python3
>>> from SigProfilerMatrixGenerator import install as genInstall
>>> genInstall.install('GRCh37', bash=True)
```

This example installs the human GRCh37 assembly reference files. You can install any of the [available genome assemblies](Currently-Supported-Genomes).

If the server has a firewall that blocks wget, use the rsync parameter:

```python
>>> genInstall.install('GRCh37', rsync=False)
```

**Note:** The installation process saves custom reference files for all chromosomes in the genome assembly, requiring ~3 GB of storage per genome. This step could take some time due to the large file sizes.
