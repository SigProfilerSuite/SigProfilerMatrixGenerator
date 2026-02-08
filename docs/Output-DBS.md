<h1> Double Base Substitution (DBS) </h1>

@[toc](Quick Links)
- [Using the Tool - **Output**][1]
---

### Overview ###
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca386e42c4b70019b58c7b?mode=render =50%x)
<br>

| File | # of sequences |
| ------ | ----------- |
| *test.DBS78.all*  | **78** pyrimidine double nucleotide variants |
| *test.DBS186.all* | **36** dinucleotide combinations that have only all purines or all pyrimidines x **4** transcriptional bias categories = 144 + 42 classified in the **Q** transcriptional bias category = **186** |
| *test.DBS1248.all* | Possible starting nucleotides (**4**) x *78* x possible ending nucleotides (**4**)= **1,248** total combinations |
| *test.DBS2976.all* | Possible starting nucleotides (**4**) x *186* x possible ending nucleotides (**4**) = **2,976** |


### DBS-78 ###
The *test.DBS78.all* file contains the frequency of each pyrimidine double nucleotide variants, {AC, AT, CC, CG, CT, GC, TA, TC, TG, or TT} > {NN} detected in each input sample. As explained above, the *test.DBS78.exome* file contains the frequency of each variant mapped out to the exome and similarly for any other file extension.

There are 16 possible dinucleotide combinations however only the top 10 with the highest pyrimidine content (in alphabetical order) are returned. There are a total of 9 dinucleotide combinations each pair of nucleotides can mutate to but only 6 possible mutations are considered for 4 combinations {CG, GC, AT, and AT}. Thus 6 x 4 (24) + 9 x 6 (54) equals the final total of 78 combinations.
     
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79c0042c4b70017b6e72b?mode=render =25%x)
The above image is a screenshot of the generated file. Here, line **3** lists the frequency of AC to CG mutations in each of the samples (column headers).

### DBS-186 ###     
There are 4 dinucleotide combinations consisting only of pyrimidines {CT, TC, CC, and TT}. Each combination can mutate to 9 other possibilities giving us a total of 36 dinucleotide combinations as discussed in the DBS-78 section. Here the *test.DBS186.all* further categorizes each of those 36 dinucleotide combinations from the *test.DBS78.all* file into the 4 transcriptional strand bias categories {T, U, N, and B}. The other 44 combinations in the DBS-78 file are categorized as having questionable bias (Q). This includes the 6 possible mutations considered for 4 combinations {CG, GC, AT, and AT} plus the 9 mutations considered for the AC and TG dincucleotide combinations.

36 sequences x 4 categories (144) + 9 + 9 + 24 = 186 total combinations.

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79c0700a81000175c5772?mode=render =25%x)
The above image is a screenshot of the generated file. Here, line **5** lists the frequency of T:AC>GA mutations, AC sequences on the transcribed strand mutating to AG.

### DBS-1248 ###
The *test.DBS1248.all* file contains all of the following pyrimidine double nucleotide variants, {N[dinucleotide variant from *test.**DBS78**.all*]N} > {N[NN]N}. For example, {N[AC]N} > {N[TT]N}. 

4 possible starting nucleotides x 78 combinations from DBS78 x 4 ending nucleotides = 1,248 total combinations.
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79ba9d7dc3f00176b0285?mode=render =25%x)
The above image is a screenshot of the generated file. Here, line **7** A[AC>CG]C corresponds to AACC sequences mutating to ACGC.
        
### DBS-2976 ###
The *test.DBS2976.all* file takes each nucleotide combination from the *test.DBS186.all* file and adds a starting and ending nucleotides. 

4 possible starting nucleotides x 186 combinations from DBS186 x 4 ending nucleotides = 2976 total combinations.
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79c1942c4b70019b42617?mode=render =25%x)
The above image is a screenshot of the generated file. Here, line **9** T:A[AC>CG]T corresponds to a AACT on the transcribed strand mutating to ACGT.
<br><br>


  [1]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
