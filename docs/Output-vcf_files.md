<h1> vcf_files </h1>

@[toc](Quick Links)
- [Using the Tool - **Output**][1]
---

This output folder structure provides text-based files containing the original mutations paired with the SigProfilerMatrixGenerator classification for each chromosome. The files are separated into dinucleotides (DBS),  multinucleotide substitutions (MNS), smaller insertions/deletions (ID), and single nucleotide variants (SNV) folders containing the appropriate files. These files are only generated when seqInfo is set to true. Similarly, if exome=True, an additional file will appear that contains all of the original mutations that occurred within the exome.

## Overview ##
![overview](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cb74bfe353c58001b9f01fc?mode=render =50%x)

The individual output folder structure for each of the 3 folders is the same. Each mutation gets resaved in the appropriate MNS, DBS, ID, or SNV folder in the correct chromosome based file.

![DBS, SNV, MNS](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca3bcdd7dc3f0016700a47?mode=render =50%x)

The output for each file are identical. For example, the sample table below represents the output of the *1_seqInfo.txt* file in the DBS folder. The headers for each file are the same with the exception of the MNS files which don't contain a matrix classification or a strand classification {1, 0, -1}. The MNS file simply contains the mutation present in the original vcf file. 

| Sample | Chromosome | Position | SBS6144 classification | Strand |
| ------ | ------- | ------- | ------- | ------- |
| MELA_006 | 1 | 18915081 | N:T[CC>TT]C | -1 |
| **MELA_006** | **1** | **57243769** | **U:T[CC>TT]T** | **-1** |
The second line refers to a dinucleotide mutation found in the MELA_006 sample on chromosome 1 at position 57243769 classified as N:T[CC>TT]C (Untranscribed T[CC>TT]T) on the non-reference strand.

### DBS ###
Dinucleotide substitution refers to two adjacent nucleotides that have both mutated to another dinucleotide combination.

Below is a screenshot of what the generated file should look like.

![DBS](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca3f7e42c4b70018b62843?mode=render =50%x)
### MNS ###
Multinucleotide substitution are classified as a series of mutations occurring within 5 base pairs of each other. DBSs are not included in this classification. 

Below is a screenshot of what the generated file should look like.
![MNS](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca3fb642c4b70017b9aa64?mode=render =50%x)

### SBS ###
Single nucleotide variant is a single base pair mutated to another base pair.

Below is a screenshot of what the generated file should look like.
![SNV](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca3fd100a81000175f1181?mode=render =50%x)

[1]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
