### **CNV Quick Start Example:** ###

In order to generate a copy number matrix, provide the an absolute path to a multi-sample segmentation file obtained from one of the following copy number calling tools (if you have individual sample files, please combine them into one file with the first column corresponding to the sample name):

1. ASCAT
2. ASCAT_NGS
3. SEQUENZA
4. ABSOLUTE
5. BATTENBERG
6. FACETS
7. PURPLE
8. TCGA

### **Example of CNV input file (Battenberg)**:


| sample | chrom | startpos | endpos | nMaj1_A | nMin1_A | frac_1A | nMaj2_A | nMin1_A | frac_2A
| :-----: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| NSLC-1060-T01 | 19 | 90407080 | 91002641 | 1 | 0 | 0.67 | 2 | 0 | 0.33

*NOTE: In the case of Battenberg input, information for both the clone and subclone is considered and counted as separate events if multiple subclones are present*

In addition, provide the name of the project and the output directory for the resulting matrix. The final matrix will be placed in the directory specified by the output path.

**An example to generate the CNV matrix is as follows:**

$ python3
```
>>from SigProfilerMatrixGenerator.scripts import CNVMatrixGenerator as scna
>>file_type = "BATTENBERG"
>>input_file = "./SigProfilerMatrixGenerator/references/CNV/example_input/Battenberg_test.tsv" #example input file for testing
>>output_path = "/Users/azhark/iCloud/dev/CNVMatrixGenerator/example_output/"
>>project = "Battenberg_test"
>>scna.generateCNVMatrix(file_type, input_file, project, output_path)

```

*Alternatively, you can run directly from the command line:*

```
python ./SigProfilerMatrixGenerator/scripts/CNVMatrixGenerator.py BATTENBERG ./SigProfilerMatrixGenerator/references/CNV/example_input/Battenberg_test.tsv BATTENBERG-TEST ./SigProfilerMatrixGenerator/references/CNV/example_output/

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
>> cnv <- CNVMatrixGenerator("BATTENBERG", "[your_repo]/test_data/CNV/Battenberg_test.tsv", "test_CNV", "[your_repo]/test_data/CNV")

```
### Function Arguments ###

These are the acceptable parameters that can be passed into the function call.<br>

**Required:**<br>
 - **file_type:** Segmentation/caller type. Currently supported callers are ["ASCAT", "ASCAT_NGS", "SEQUENZA", "ABSOLUTE", "BATTENBERG", "FACETS", "PURPLE", "TCGA"]. <br> *Type:* string <br> *Example:* "BATTENBERG"


 - **input_file:** Path to directory containing SV bedpe files, one per sample. <br> *Type:* string <br> *Example:* "./SigProfilerMatrixGenerator/references/SV/example_input/560-Breast/"

 - **output_path:** Path to directory for output files. If this directory doesn't exist, a new one will created. <br> *Type:* string <br> *Example:* "./SigProfilerMatrixGenerator/references/SV/example_output/"

 - **project:** Project name for this instance of matrix generation. <br> *Type:* string <br> *Example:* "560-Breast"
