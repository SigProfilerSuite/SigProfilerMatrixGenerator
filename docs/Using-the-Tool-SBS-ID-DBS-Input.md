<h1> Using SigProfilerMatrixGenerator </h1>

SigProfilerMatrixGenerator works in conjunction with [other SigProfiler tools][1] but can also be run alone on input datasets. This section goes over the function arguments, input files, and all the output folders and files in detail.

@[toc](Quick Links)
- [**Home**][2]
- [**Installing** SigProfilerMatrixGenerator][3]
- [**Using** SigProfilerMatrixGenerator - **Output**][4]
- [**Quick Start Example** for SigProfilerMatrixGenerator][5]
- [**Currently** Supported Genomes][6]
----------

From within a python session, you can now generate the matrices as follows:
```
$ python3
>>from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
>>matrices = matGen.SigProfilerMatrixGeneratorFunc(project, genome, vcfFiles, exome=False, bed_file=None, chrom_based=False, plot=False, tsb_stat=False, seqInfo=False)
```

From within a R session, you can now generate the matrices as follows:
```
$ R
>> library("reticulate")
>> use_python("path_to_your_python3")
>> py_config()
>> library("SigProfilerMatrixGeneratorR")
>> matrices <- SigProfilerMatrixGeneratorR("BRCA", "GRCh37", "/Users/ebergstr/Desktop/BRCA/", plot=T, exome=F, bed_file=NULL, chrom_based=F, tsb_stat=F, seqInfo=F, cushion=100)
```

### Function Arguments ### 

These are the acceptable parameters that can be passed into the function call.<br>

**Required:**<br>
 - **project:** Project name for this instance of matrix generation. <br> *Type:* string <br> *Example:* "alexandrov_lab_test_1"

- **genome:** Reference genome to use for the matrix generation. <br> *Type:* string <br> *Example:* "GRCh37"
 
 - **vcfFiles:** Full path of the saved input files in the desired output folder. <br> *Type:* string <br> *Example:* "/Users/test/Desktop/alexandrov_lab_test_1"

**Optional:**<br>
 - **exome:** Downsamples mutational matrices to the exome regions of the genome. <br> *Type:* boolean <br> *Default:* False <br> *Example:* exome=True

 - **bed_file:** Downsamples mutational matrices to custom regions of the genome. Requires the full path to the [BED file][7]. <br> *Type:* string <br> *Default:* None <br> *Example:* bed_file="/Users/test/Desktop/bed_files/sample_1.bed"
 
- **chrom_based:** Outputs chromosome-based matrices. <br> *Type:* boolean <br> *Default:* False <br> *Example:* chrom_based=True

 - **plot:** Integrates with SigProfilerPlotting to output all available visualizations for each matrix. <br> Type: boolean <br> *Default:* False <br> *Example:* plot=True

 - **tsb_stat:** Outputs the results of a transcriptional strand bias test for the respective matrices. <br> Type: boolean <br> *Default:* False <br> *Example:* tsb_stat=True
 
 - **seqInfo:** Ouputs original mutations into a text file that contains the SigProfilerMatrixGenerator classificaiton for each mutation. <br> Type: boolean <br> *Default:* False <br> *Example:* seqInfo=True

 - **cushion:** Adds an Xbp cushion to the exome/bed_file ranges for downsampling the mutations. <br> Type: integer <br> *Default:* 100 <br> *Example:* cushion=250
 

All **string** arguments must be surrounded by quotation marks ex. *"test"* and all **boolean** arguments must be *True* or *False*.
<br><br>

### Input File ###
This tool currently supports the following formats:
* [MAF][8] <br> Mutation Annotation Format [[example.maf][9]]
* [VCF][10] <br> Variant Call Format [[example.vcf][11]] <br>
If files are in .vcf format, each sample must be saved as a separate file.
* [ICGC][12] <br>
* Simple text file [[example.txt][13]] <br>

The user must provide variant data adhering to one of these four formats. 
<br><br>

### Folder Structure ### 
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5c74312f82a3950017d11ff5?mode=render =50%x)
<br>
The final output is divided into three folders:
* **Input:** Contains copies of the user-provided input files.![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5c74320162c82a0019db475f?mode=render =50%x)

* **Logs:** Contains the error and log files for the submitted job.
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5c74320f8d5d98001a39c827?mode=render =50%x) <br>
All errors are saved in the *sigProfilerMatrixGenerator_[project]_[genome].err* file and all progress checkpoints are saved in the *sigProfilerMatrixGenerator_[project]_[genome].out* file within the specified output folder. 
* **Output:** Contains the DBS, SBS, INDEL, TSB, plots, and vcf_files folders. All matrices are saved in the appropriate folders.
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc6a29c00a81000175b5de5?mode=render =50%x)
<br><br>

### File Extensions ###
All output files will have a file extension indicative of which arguments were passed in as **True**. By default, the files will have *.all* file extension. The rest of the file extensions are explained below.
* *.exome* <br>exome argument was passed in as **True** and contains all the mutations mapped out to the exome. 

* *.region* <br> bed_file argument was passed in as **string** and contains all the mutations mapped out to the input bed_file regions.

* *.chrx where x denotes which chromosome i.e. chr1, chrA, etc.* <br> chrom_based argument was passed in as **True** and contains all the mutations mapped out to each chromosome.
<br><br>


  [1]: https://osf.io/mc45g/
  [2]: https://osf.io/s93d5/wiki/home
  [3]: https://osf.io/s93d5/wiki/2.%20Installation/
  [4]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
  [5]: https://osf.io/s93d5/wiki/6.%20Quick%20Start%20Example/
  [6]: https://osf.io/s93d5/wiki/7.%20Currently%20Supported%20Genomes/
  [7]: https://samtools.github.io/hts-specs/VCFv4.2.pdf
  [8]: https://docs.gdc.cancer.gov/Data/File_Formats/MAF_Format/
  [9]: https://osf.io/dkjwr/
  [10]: https://samtools.github.io/hts-specs/VCFv4.2.pdf
  [11]: https://osf.io/8vm4p/
  [12]: https://docs.icgc.org/submission/guide/overview/submission-file-format/
  [13]: https://osf.io/xfphr/
