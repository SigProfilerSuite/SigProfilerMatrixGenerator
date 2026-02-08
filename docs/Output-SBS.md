<h1> Single Base Substitution (SBS) </h1>

@[toc](Quick Links)
- [Using the Tool - **Output**][1]
---

## Overview ##
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca3896d7dc3f00196c1a98?mode=render =50%x)
<br>

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5c86002a245c0a0018d22838?mode=render =75%x)
<br>

Classification of single base substitutions (SBSs). The complete classification of an SBS includes both bases in the Watson-Crick base-pairing. To simplify this notation, one can use either the purine or the pyrimidine base. SigProfilerMatrixGenerator uses as a standard the pyrimidine classification

| File | # of sequences |
| ------ | ----------- |
| *test.SBS6.all*  | Pyrimidine single nucleotide variants, C > {A, G, or T} and T > {A, G, or C} = **6** |
| *test.SBS24.all* | *test.SBS6.all* (**6**) x **4** transcriptional bias categories = **24** |
| *test.SBS96.all* | Possible starting nucleotides (**4**) x *test.SBS6.all* (**6**) x possible ending nucleotides (**4**)= **96** total combinations |
| *test.SBS384.all* | *test.SBS96.all* (**96**) x **4** transcriptional bias categories = **384** |
| *test.SBS1536.all* | Possible starting dinucleotides (**16**) x *test.SBS6.all* (**6**) x possible ending dinucleotides (**16**) = **1536** total combinations |
| *test.SBS6124.all* | *test.SBS1536.all* (**1536**) x **4** transcriptional bias categories = **6144** |

### SBS-6 ###
The *test.SBS6.all* file contains the frequency of each of the 6 pyrimidine single nucleotide variants, C > {A, G, or T} and T > {A, G, or C} detected in each input sample. 

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc798b800a81000175c54a3?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **3**, C>G corresponds to a C to G mutation and each column is the frequency of that mutation in a specific sample (corresponding column header). 

### SBS-24 ###
The *test.SBS24.all* file separates each of the 6 pyrimidine single nucleotide variants, C > {A, G, or T} and T > {A, G, or C} detected into the 4 transcriptional strand bias categories.
6 x 4 = 24 total combinations
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc798c3d7dc3f00166d44c2?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **4**, T:C>T corresponds to a C to T mutation on the transcribed strand. 
  
### SBS-96 ###    
The *test.SBS96.all* file contains all of the following the pyrimidine single nucleotide variants, N[{C > A, G, or T} or {T > A, G, or C}]N.  

4 possible starting nucleotides x 6 pyrimidine variants x 4 ending nucleotides = 96 total combinations.
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc798dad7dc3f00176b012a?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **6**, A[C>G]A corresponds to a ACA mutating to AGA. 
    
### SBS-384 ###
The *test.SBS384.all* file separates each nucleotide combination in the *test.SBS96.all* file into the 4 transcriptional strand bias categories. 

96 sequences x 4 categories = 384 total combinations.
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc7992f00a81000175c550a?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **7**, T:A[C>G]C corresponds to a ACC mutating to AGC on the transcribed strand. 
    
### SBS-1536 ###
The *test.SBS1536.all* file contains all of the following the pyrimidine single nucleotide variants, NN[{C > A, G, or T} or {T > A, G, or C}]NN. 

16 (4x4) possible starting dinucleotides x 6 pyrimidine variants x 16 (4x4) possible ending dinucleotides = 1536 total combinations.
    
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79937bbbd37001aa12d51?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **8**, AA[C>A]CG corresponds to a AACCG mutating to AAACG. 
  
### SBS-6144 ###
The *test.SBS6144.all* file separates each nucleotide combination in the *test.SB1536.all* file into the 4 transcriptional strand bias categories. 

1536 sequences x 4 categories = 6144 total combinations.

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cc79942bbbd37001aa12d5a?mode=render =50%x)
The above image is a screenshot of the generated file. Here, on line **9**, T:AA[C>A]CT corresponds to a AACCT mutating to AAACT on the transcribed strand.


  [1]:  https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
