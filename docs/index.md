<h1> SigProfilerMatrixGenerator </h1>

SigProfilerMatrixGenerator is a [python][1] framework that creates mutational matrices for somatic mutations. This tool works to identify and categorize the mutations based on possible single nucleotide variants (SNVs), double base substitutions (DBS), and insertions/deletions and provides further transcriptional strand bias categorization. It downsizes the generated mutations to parts of the genome like the [exome][2] or a custom [BED file][3] to help identify true mutational signatures within a genome. SigProfilerMatrixGenerator seamlessly integrates with [other SigProfiler tools][4].

The SigProfilerMatrixGenerator library can be found on github [here][11]. For users that prefer working in an R environment, we provide an R wrapper (SigProfilerMatrixGeneratorR) that can be found on github [here][10].

----------

### Citation ###
Bergstrom EN, Huang MN, Mahto U, Barnes M, Stratton MR, Rozen SG, and Alexandrov LB (2019) SigProfilerMatrixGenerator: a tool for visualizing and exploring patterns of small mutational events. **BMC Genomics** 20, Article number: 685.
https://bmcgenomics.biomedcentral.com/articles/10.1186/s12864-019-6041-2
<br>
### License ###
Copyright (c) 2019, Erik Bergstrom [Alexandrov Lab]
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
<br>
### Contact ###
All SigProfilerMatrixGenerator related queries or bug reports should be directed to Erik Bergstrom at ebergstr@eng.ucsd.edu.

  [1]: https://www.python.org/
  [2]: https://www.broadinstitute.org/blog/what-exome-sequencing
  [3]: https://genome.ucsc.edu/FAQ/FAQformat.html#format1
  [4]: https://osf.io/mc45g/
  [5]: https://osf.io/s93d5/wiki/1.%20Installation/
  [6]: https://osf.io/s93d5/wiki/2.%20Using%20the%20Tool%20-%20Input/
  [7]: https://osf.io/s93d5/wiki/3.%20Using%20the%20Tool%20-%20Output/
  [8]: https://osf.io/s93d5/wiki/5.%20Quick%20Start%20Example/
  [9]: https://osf.io/s93d5/wiki/6.%20Currently%20Supported%20Genomes/
  [10]: https://github.com/AlexandrovLab/SigProfilerMatrixGeneratorR
  [11]: https://github.com/AlexandrovLab/SigProfilerMatrixGenerator
