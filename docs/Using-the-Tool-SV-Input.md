## **STRUCTURAL VARIANT MATRIX GENERATION**

### **INPUT FORMAT**:

***First six columns are required, and either the column "svclass" (deletion, translocation, tandem-duplication, or inversion) or the columns "strand1" & "strand2" (BRASS convention) must also be present***


### **Example with SV class present (tsv or csv file):**


| chrom1 | start1 | end1 | chrom2 | start2 | end2 | svclass |
| :-----: | :-: | :-: | :-: | :-: | :-: | :-: |
| 19 | 21268384 | 21268385 | 19 | 21327858 | 21327859 | deletion

### **Example without SV class present (tsv or csv file):**

| chrom1 | start1 | end1 | chrom2 | start2 | end2 | strand1 | strand2
| :-----: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| 19 | 21268384 | 21268385 | 19 | 21327858 | 21327859 | + | +


### **SV Quick Start Example:** ###

```
#navigate to SVMatrixGenerator directory and start python3 interpreter

from SigProfilerMatrixGenerator.scripts import SVMatrixGenerator as sv
input_dir = "./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast" #directory which contains collection of bedpe files (one per sample)
output_dir = "./SigProfilerMatrixGenerator/references/SV/"
project = "560-Breast"
sv.generateSVMatrix(input_dir, project, output_dir)
```
*Alternatively, you can run directly from the command line:*
```
python3 ./SigProfilerMatrixGenerator/scripts/SVMatrixGenerator.py ./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast 560-Breast ./SigProfilerMatrixGenerator/references/SV/example_output/ #provide input_dir, project, output_dir as command-line arguments
```

**Setting up R environment with conda (optional but recommended if using R):**

```
conda create --name spmg_r_1.2.13 -y
conda activate spmg_r_1.2.13
conda install python=3.10 r-base r-devtools r-reticulate -c conda-forge -y
pip install SigProfilerMatrixGenerator
echo 'devtools::install_github("AlexandrovLab/SigProfilerMatrixGeneratorR")' | Rscript -

```

**From within a R session, you can now generate the matrices as follows:**
```
$ R
>> library("reticulate")
>> use_python("path_to_your_python3")
>> py_config()
>> library("SigProfilerMatrixGeneratorR")

>> sv <- SVMatrixGenerator("[your_repo]/test_data/SV", "test_CNV",  "[your_repo]/test_data/")

```

### **Function Arguments** ###

These are the acceptable parameters that can be passed into the function call.<br>

**Required:**<br>
 - **project:** Project name for this instance of matrix generation. <br> *Type:* string <br> *Example:* "560-Breast"

 - **input_dir:** Path to directory containing SV bedpe files, one per sample. <br> *Type:* string <br> *Example:* "./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast/"

 - **output_dir:** Path to directory for output files. If this directory doesn't exist, a new one will created. <br> *Type:* string <br> *Example:* "./SigProfilerMatrixGenerator/references/SV/example_output/"
