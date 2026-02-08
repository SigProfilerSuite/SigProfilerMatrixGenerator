<h1> Using SigProfilerMatrixGenerator - Output</h1>

This section goes over all the output folders and files in detail.

@[toc](Quick Links)
- [**Home**][1]
- [**Installing** SigProfilerMatrixGenerator][2]
- [**Using** SigProfilerMatrixGenerator - **Input**][3]
- [**Quick Start Example** for SigProfilerMatrixGenerator][4]
- [**Currently** Supported Genomes][5]


----------
### SBS: Single Base Substitution ###

The calculations for the number of returned sequences in the SBS output folder are summarized below. 

| File | # of sequences |
| ------ | ----------- |
| *test.SBS6.all*  | 6 |
| *test.SBS24.all* | 6 x 4 = 24 |
| *test.SBS96.all* | 4 x 6 x 4 = 96 |
| *test.SBS384.all* | 96 x 4 = 384 |
| *test.SBS1536.all* | 4 x 4 x 6 x 4 x 4 = 1536|
| *test.SBS6124.all* | 1536 x 4 = 6124 |

For a more detailed explanation, refer to the [Output - SBS][6] page.

### DBS: Double Base Substitution ###

The calculations for the number of returned sequences in the DBS output folder are summarized below. 

| File | # of sequences |
| ------ | ----------- |
| *test.DBS78.all*  | 78 |
| *test.DBS312.all* | 186 |
| *test.DBS1248.all* | 4 x 78 x 4 = 1248 |
| *test.DBS4992.all* | 4 x 186 x 4 = 2976 |

For a more detailed explanation, refer to the [Output - DBS][7] page.

### ID: Insertion Deletion ###

The calculations for the number of returned sequences in the DBS output folder are summarized below. 

| File | # of sequences |
| ------ | ----------- |
| *test.ID28.all*  | 28 |
| *test.ID83.all* | 83 |
| *test.ID415.all* | 83 x 5 = 415 |
| *test.ID8268.all* | 8268 |

For more details, refer to the [Output - ID][8] page.


### TSB: Transcriptional Strand Bias ###

The calculations for the number of returned sequences in the TSB output folder are summarized below. 

| File | # of sequences |
| ------ | ----------- |
| *strandBiasTes_24.txt*  | 6 x 4 = 24 |
| *strandBiasTes_384.txt* | 4 x 24 x 4 = 384|
| *strandBiasTes_6144.txt* | 4 x 384 x 4 = 6144 |

For a more detailed explanation, refer to the [Output - TSB][9] page.

### vcf_files ###
The vcf_files folder contains the following additional folders depending on the input parameters.
- DBS: Dinucleotide substitution.
- MNS: Multinucleotide substitution.
- SNV: Single nucleotide variant.
- ID: Small insertions and deletions.

For more details, refer to the [Output - vcf_files][10] page.

### Plots ###

This output folder contains the generated plots from the results of the SBS, DBS, and ID matrix generation.

For more details, refer to the [Output - Plots][11] page.


  [1]:  https://osf.io/s93d5/wiki/home/
  [2]: https://osf.io/s93d5/wiki/1.%20Installation%20-%20Python/
  [3]: https://osf.io/s93d5/wiki/3.%20Using%20the%20Tool%20-%20Input/
  [4]: https://osf.io/s93d5/wiki/6.%20Quick%20Start%20Example/
  [5]: https://osf.io/s93d5/wiki/7.%20Currently%20Supported%20Genomes/
  [6]: https://osf.io/s93d5/wiki/5.%20Output%20-%20SBS/
  [7]: https://osf.io/s93d5/wiki/5.%20Output%20-%20DBS/
  [8]: https://osf.io/s93d5/wiki/5.%20Output%20-%20ID/
  [9]: https://osf.io/s93d5/wiki/5.%20Output%20-%20TSB/
  [10]: https://osf.io/s93d5/wiki/5.%20Output%20-%20vcf_files/
  [11]:https://osf.io/s93d5/wiki/5.%20Output%20-%20Plots/
