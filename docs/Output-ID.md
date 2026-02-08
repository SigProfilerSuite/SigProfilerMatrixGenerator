<h1> Insertions and Deletions, Indels (ID) </h1>

@[toc](Quick Links)
- [Using the Tool - **Output**][1]
---

## Overview ##
![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca315fbbbd370018a60ecc?mode=render =50%x)

This output folder returns files containing all the insertions and deletions found within the samples. If no files are returned, this means no insertions or deletions were found.

<h3> Indel Sample Plot </h3>

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca319cbbbd37001aa27f97?mode=render =75%x)
<br>
### ID-28 ###
The *test.ID28.all* file identifies all 1 bp (C and T only) insertions and deletions from homopolymer length 1 to 6+, the >1bp deletions and insertions as repeats, and all other indels in the microhomology category and categorizes each by length. 

The generated plot above gives a visual for how each indel is categorized and returned. 

| Mutation Type | Sample 1 (PD10001a) | Sample 2 (PD10011a) | ..... |
| ------- |  ------- |  ------- |  ------- |
| 6 rows for 1:Del:C:0 to 1:Del:C:5 | frequency of each deletion of C in sample 1 | frequency of each deletion of C in sample 2 | .... |
| 6 rows for 1:Del:T:0 to 1:Del:T:5 | frequency of each deletion of T in sample 1 | frequency of each deletion of T in sample 2 | .... |
| 6 rows for 1:Ins:C:0 to 1:Ins:C:5 | frequency of each insertion of C in sample 1 | frequency of each insertion of C in sample 2 | .... |
| 6 rows for 1:Ins:C:0 to 1:Ins:C:5 |frequency of each insertion of T in sample 1 | frequency of each insertion of T in sample 2 | .... |
| long_Del (repeat units) | frequency of each long deletion in sample 1 | frequency of each long deletion in sample 2 | .... |
| long_Ins (repeat units) | frequency of each long insertion in sample 1 | frequency of each long insertion in sample 2 | .... |
| MH (microhomology) | 0 | 0 | | |
| complex | 0 | 0 | | |

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca31ce00a81000175f07a3?mode=render =100%x)
The above image is a screenshot of the generated file. Here, on line **5**, 1:Del:C:3 corresponds to a deletion of C in a sequence N[C]CCCN where N is represents any nucleotide A, T, or G to give NCCCN. 

### ID-83 ###
The *test.ID83.all* file further categorizes each unique repeat and microhomology indel found. 

| *test.ID28.all* | *test.ID83.all* |
| ------------------ | ----------------- |
| long_Del | 2:Del:R:0 - 2:Del:R:5<br> 3:Del:R:0 - 3:Del:R:5<br> 4:Del:R:0 - 4:Del:R:5 <br> 5:Del:R:0 - 5:Del:R:5|
| long_Ins | 2:Ins:R:0 - 2:Ins:R:5<br> 3:Ins:R:0 - 3:Ins:R:5<br> 4:Ins:R:0 - 4:Ins:R:5 <br> 5:Ins:R:0 - 5:Ins:R:5|
| MH | 2:Del:M:1 - 5:Del:M:5 <br> 2:Ins:M:1 - 5:Ins:M:5 |


![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca31d542c4b70016b5bae7?mode=render =100%x)
Here, on line **3**, 1:Del:C:1 corresponds to a deletion of C in a sequence N[C]CN where N is represents any nucleotide A, C, or G to give NCN.

### ID-415 ###
The *test.ID415.all* file categorizes each identified indel from *test.ID83.all* into the 5 transcriptional strand bias categories {T, U, N, B, Q}.

83 x 5 = 415 combinations
    
For example, a category in *test.ID83.all* would be further categorized into the following in *test.ID415.all*.

| *test.ID83.all* | *test.ID415.all* |
| ------------------ | ----------------- |
| 4:Del:R:4 | T:4:Del:R:4 <br> U:4:Del:R:4 <br> N:4:Del:R:4 <br> B:4:Del:R:4 <br> Q:4:Del:R:4|

![enter image description here](https://files.osf.io/v1/resources/s93d5/providers/osfstorage/5cca31db42c4b70018b62345?mode=render =100%x)
The above image is a screenshot of the generated file. Here, on line **7**, T:1:Del:C:5 corresponds to a deletion of C in a sequence N[C]CCCCCN where N is represents any nucleotide A, C, or G to give NCCCCCN. 
on the transcribed strand.

### ID-8268 ###
The test.ID8268.all file extends the categorization from the ID-83 matrix by providing complete information about the indel sequence for indels at repetitive regions with length less than 6bp. 

| *test.ID8268.all* |  |
| ------------------ | ----------------- |
| 2:Del:TA:5 | Deletion of length 2 with sequence TC or GA (reverse complement)|
| 5:Ins:CCATC:2 | Insertion of length 5 with sequence CCATC or GATGG (reverse complement)|


  [1]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
