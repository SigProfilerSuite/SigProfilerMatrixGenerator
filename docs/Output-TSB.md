<h1> Transcriptional Strand Bias (TSB) </h1>

@[toc](Quick Links)
- [Using the Tool - **Output**][1]
---
## TSB Categorization ##

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5ce472572a50c400177d0b55?mode=render =50%x)

RNA polymerase uses the template strand to transcribe DNA into RNA. The strand upon which the gene is located is referred to as the coding strand. All regions outside of the coding sequence of a gene are referred to as non-transcribed regions. Single point substitutions are oriented based on their pyrimidine base and the strand of the reference genome. When a gene is found on the reference strand an A:T>T:A substitution in the footprint of the gene is classified as transcribed T>A (example indicated by circle) while a C:G>G:C substitution in the footprint of the gene is classified as un-transcribed C>G (example indicated by star). Mutations outside of the footprints of genes are classified as non-transcribed (example indicated by square). Classification of single base substitutions is shown both in regard to SBS-24 and SBS-384. 

## Transcriptional Strand Bias Categories ##
These are the 4 transcriptional strand bias categories.
*   T: Transcribed <br> The variant is on the transcribed strand.
*   U: Untranscribed <br> The variant is on the untranscribed strand.
*   B: Bidirectional <br> The variant is on both strands and is transcribed either way.
*   N: Nontranscribed <br> The variant is in a non-coding region and is untranslated. <br> 

There is one additional transcriptional strand bias category, **Q: Questionable**. This category is used to classify any mutations that are a mix of purines and pyrimidines and thus can't be classified into one of the above 4 categories.

The TSB files and classification only considers the first 4 categories.

## Output Folder ##
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5c743a4462c82a0017dec3a0?mode=render =50%x)

This output folder contains the results of the transcriptional strand bias test. The test compares the number of translated and untranslated mutations for each mutational context and outputs the enrichment value, a p-value, and a corrected p-value for multiple-hypothesis testing for each comparison. The significant results from the tests are returned in a separate file *significantResults_strandBiasTest.txt*. The file will be empty if there are no significant enrichment values. <br>

The ouput files contain the following information:
* the mutation type
* the enrichment value (translated/untranslated)
* p-value
* false discovery rate (FDR) q-value.

### Overview ###
| File | # of sequences |
| ------ | ----------- |
| *strandBiasTes_24.txt*  | Stats of the pyrimidine nucleotide variants (**6**) x TBS categories (**4**) = **24** |
| *strandBiasTes_384.txt* | Stats of the possible ending nucleotides (**4**)  x *strandBiasTes_24.txt* (**24**) x possible ending nucleotides (**4**) = **312** |
| *strandBiasTes_6144.txt* | Stats of the possible ending nucleotides (**4**) x *strandBiasTes_384.txt* (**1248**) x possible ending nucleotides (**4**) = **6144** |

### TSB-24 ###
The *strandBiasTes_24.txt* file summarizes the information discussed above (*the mutation type, the enrichment value, p-value, and FDR q-value*) of each of the 6 pyrimidine single nucleotide variants, C > {A, G, or T} and T > {A, G, or C} detected in each input sample. <br> 

6 x 4 = 24 total combinations
    
Output of *strandBiasTes_24.txt* for a single analyzed sample is shown in the table below.

| Sample | MutationType | Enrichment<br>[Trans/UnTrans] | p.value | FDR_q.value |
| ------ | ------- | ------- | ------- | ------- |
| PD10010a | C>A | 2.1429 | 0.1338 | 0.8028 |
| **PD10010a** | **C>G** | **2.0** | **0.0407** | **1.0** |
| PD10010a | C>T | 1.0 | 1.0 | 1.0 |
| PD10010a | T>A | 0.6667 | 1.0 | 1.0 |
| PD10010a | T>C | 1.5 | 0.7539 | 1.0 |
| PD10010a | T>G | 0 | 0.5 | 1.0 |

In this example table, the **second row** has a significant p value (<.05) and this result would be returned in the *significantResults_strandBiasTest.txt* file. 

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79e74bbbd370019a1b591?mode=render =25%x)
The above image is a screenshot of the generated file. Here line **4** corresponds to a T>A mutation with an enrichment rate of 6.0, p value equal to 0.9007479747784868, and false discovery rate (FDR) q-value of 1.0 in the MELA_0004 sample.

### TSB-384 ###
The *strandBiasTes_384.txt* file summarizes the information discussed above (*the mutation type, the enrichment value, p-value, and FDR q-value*) for the following pyrimidine single nucleotide variants, N[{C > A, G, or T} or {T > A, G, or C}]N.

4 starting nucleotides x 24 combinations x 4 ending nucleotides = 384 total combinations
   
|Sample | MutationType | Enrichment[Trans/UnTrans] | p.value | FDR_q.value |
| ------ | ------- | ------- | ------- | ------- |
| PD10010a | A[C>A]A | 0 | 1.0 | 1.0 |

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79e7a42c4b70017b6e98e?mode=render =25%x)
The above image is a screenshot of the generated file. Here line **6** corresponds to a ACC to AGC mutation with an enrichment rate of 6.0, p value equal to 0.15158963203430173, and false discovery rate (FDR) q-value of 1.0 in the MELA_0004 sample.

### TSB-6144 ###
The *strandBiasTes_6144.txt* file summarizes the information discussed above (*the mutation type, the enrichment value, p-value, and FDR q-value*) for the following pyrimidine single nucleotide variants, NN[{C > A, G, or T} or {T > A, G, or C}]NN.

6 (4x4) possible starting dinucleotides x 24 combinations x 16 (4x4) possible ending dinucleotides = 6144 total combinations. 

|Sample | MutationType | Enrichment[Trans/UnTrans] | p.value | FDR_q.value |
| ------ | ------- | ------- | ------- | ------- |
| PD10010a | AA[C>A]AA | 0 | 1.0 | 1.0 |

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79f6700a81000175c59ed?mode=render =25%x)
The above image is a screenshot of the generated file. Here line **8** corresponds to a AACCG to AAACG mutation with an enrichment rate of 6.0, p value equal to 0.125, and false discovery rate (FDR) q-value of 1.0 in the MELA_0004 sample.


  [1]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
