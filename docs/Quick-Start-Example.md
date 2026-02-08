<h1> Quick Start Example </h1>


This section provides an example for users to quickly get started with using SigProfilerMatrixGenerator tool.

@[toc](Quick Links)
- [**Home**][1]
- [**Installing** SigProfilerMatrixGenerator][2]
- [**Using** SigProfilerMatrixGenerator - **Input**][3]
- [**Using** SigProfilerMatrixGenerator - **Output**][4]
- [**Currently** Supported Genomes][5]

----------

### Step 1. Run python ###
To run SigProfilerMatrixGenerator, start a Python terminal session, and run programs from the terminal using SigProfilerMatrixGenerator. Check that the running version is **python3**.
<br>
```
$python
Python 3.5.2 (v3.5.2:4def2a2901a5, Jun 26 2016, 10:47:25) 
[GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>> 
```

### Step 2. SigProfilerMatrixGenerator installation ###
Check if SigProfilerMatrixGenerator is installed.
```
$python
Python 3.5.2 (v3.5.2:4def2a2901a5, Jun 26 2016, 10:47:25) 
[GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>> help("modules")
Please wait a moment while I gather a list of all available modules...
IN
argparse
setuptools
SigProfilerMatrixGenerator
...
```

If not, follow the instructions on the [Installation][3] page.

### Step 3. Reference genome installation ###
Install your desired reference genome from the command line/terminal as follows:
```
$ python3
>> from SigProfilerMatrixGenerator import install as genInstall
>> genInstall.install('GRCh37')
```
<br>
This example installs the custom human 37 assembly reference files but you can install any of the available [genome assemblies][2]. 

The installation process saves the custom reference files for all chromosomes in the genome assembly so **~3 Gb** of storage must be available for the downloads for each genome. You can find all the downloaded reference files in the main SigProfilerMatrixGenerator folder. Because the custom files are so large, this step could take some time. <br>

![file structure](https://files.osf.io/v1/resources/mc45g/providers/osfstorage/5c6dc7fe62c82a0017d85230?mode=render =25%x)

### Step 4. Output folder ###
Place your vcf files in your desired project folder. We recommend naming it based on your project's name.


### Step 5. Matrix generation ###
From within a python session, you can now generate the matrices as follows:
```
$ python3
>>from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
>>matrices = matGen.SigProfilerMatrixGeneratorFunc("test", "GRCh37", "/Users/ebergstr/Desktop/test",plot=True)
```
In the above example, the layout of the parameters are as follows: *SigProfilerMatrixGeneratorFunc(project, reference_genome, path_to_input_files, plot)*. All of the function arguments and their types are explained in detail in the [Using the Tool][4] section.


  [1]: https://osf.io/s93d5/wiki/home/
  [2]: https://osf.io/s93d5/wiki/1.%20Installation%20-%20Python/
  [3]: https://osf.io/s93d5/wiki/3.%20Using%20the%20Tool%20-%20Input/
  [4]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
  [5]: https://osf.io/s93d5/wiki/7.%20Currently%20Supported%20Genomes/
