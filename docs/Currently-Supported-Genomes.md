<h1> Currently Supported Genomes </h1>

### Quick Links ###
- [**Home**][1]
- [**Installing** SigProfilerMatrixGenerator][2]
- [**Using** SigProfilerMatrixGenerator - **Input**][3]
- [**Using** SigProfilerMatrixGenerator - **Output**][4]
- [**Quick Start Example** for SigProfilerMatrixGenerator][5]

----------

These are the currently supported genomes:

- [GRCh38.p12 [GRCh38]][6] <br>
*GRCh38.p12 [GRCh38] (Genome Reference Consortium Human Reference 38), INSDC Assembly GCA_000001405.27, Dec 2013. Released July 2014. Last updated January 2018. <br>This genome was downloaded from ENSEMBL database version 93.38.*

- [T2T-CHM13v2.0 [CHM13-T2T]][16] <br>
*T2T-CHM13v2.0 [CHM13-T2T] (Telomere-to-Telomere consortium complete human reference), INSDC Assembly GCA_009914755.4, Jan 2022. Nuclear chromosomes only (1-22, X, Y). The reference FASTA does carry a `chrM`, but it is not covered here: the two CHM13v2.0 distributions in common use disagree on it, iGenomes shipping the CHM13 mitochondrial assembly (CP068254.1) and `chm13v2.0_maskedY_rCRS.fa` substituting rCRS, and NCBI RefSeq annotation release `GCF_009914755.1-RS_2025_08` does not annotate the mitochondrion at all (its assembly report gives no RefSeq accession for it), so no transcript file can be derived from the same pinned release. Mutations on `MT`/`chrM` are skipped rather than classified.*
<br>*Exome regions: unlike the capture-kit definitions used for GRCh37/GRCh38, the CHM13-T2T exome interval list is annotation-derived. It is the union of all CDS features in NCBI RefSeq annotation release `GCF_009914755.1-RS_2025_08` (annotation date 2025-08-01), mapped from RefSeq accessions to chromosome names via `GCF_009914755.1_T2T-CHM13v2.0_assembly_report.txt`, restricted to chromosomes 1-22/X/Y, then merged. Result: 213,010 non-overlapping intervals covering 36.4 Mb (mean 171 bp), against 215,152 intervals / 49.7 Mb for the GRCh38 Agilent SureSelect list. CDS was chosen over the wider exon-based sets (mRNA exons 102.4 Mb, all exons 153.7 Mb) because it stays closest to the interval granularity of the other human genomes; CDS features from predicted (XM_) models are included as well as curated (NM_) ones, so genes annotated only in regions newly resolved by T2T are not dropped. Exome matrices for CHM13-T2T are therefore not directly comparable to GRCh38 exome matrices. The list can be regenerated exactly with `SigProfilerMatrixGenerator/scripts/build_refseq_references.py exome-list --feature CDS`.*
<br>*Transcript files: the per-chromosome `*_transcripts.txt` files are derived from the `transcript` features of the same annotation release, `GCF_009914755.1-RS_2025_08` (GTF flavour, whose `gene_id`/`transcript_id` conventions the format depends on), restricted to chromosomes 1-22/X/Y: 184,134 transcripts. They can be regenerated exactly with `SigProfilerMatrixGenerator/scripts/build_refseq_references.py transcripts`. Note that RS_2025_08 annotates 4,993 transcripts on chrY, of which 4,376 are Gnomon-predicted lncRNA models in the Yq12 satellite region that T2T resolved for the first time; transcriptional strand assignments on chrY therefore differ substantially from GRCh38.*

- [GRCh37.p13 [GRCh37]][7] <br>
*GRCh37.p13 [GRCh37] (Genome Reference Consortium Human Reference 37), INSDC Assembly GCA_000001405.14, Feb 2009. Released April 2011. Last updated September 2013. <br>This genome was downloaded from ENSEMBL database version 93.37.*

- [GRCm39 \[mm39\]][8] <br> 
*GRCm39 \[mm39\] (Genome Reference Consortium Mouse Reference 39), INSDC Assembly GCA_000001635.9, Jun 2020. Last updated August 2020. <br>This genome was downloaded from ENSEMBL database version 103.*

- [GRCm38.p6 [mm10]][9] <br>
*GRCm38.p6 [mm10] (Genome Reference Consortium Mouse Reference 38), INDSDC Assembly GCA_000001635.8, Jan 2012. Released July 2012. Last updated March 2018. <br>This genome was downloaded from ENSEMBL database version 93.38.*

- [GRCm37 [mm9]][10] <br>
*GRCm37 [mm9] (Release 67, NCBIM37), INDSDC Assembly GCA_000001635.18. Released Jan 2011. Last updated March 2012. <br>This genome was downloaded from ENSEMBL database version release 67.*

- [rn6 [Rnor_6.0]][11] <br>
*Rnor_6.0, INSDC Assembly GCA_000001895.4, Jul 2014. Released Jun 2015. Last updated Jan 2017. <br>This genome was downloaded from ENSEMBL database version 96.6.* 

- [yeast [Saccharomyces cerevisiae S288C; assembly R64-2-1]][12] <br> 
*yeast [Saccharomyces cerevisiae S288C; assembly R64-2-1]. Released Nov 2014.*

- [EBV [Epstein-Barr Virus]][13] <br>
*ebv  [EBV] NC_007605.1, Nov 2005. Last updated Aug 2018. This genome was downloaded from the NCBI database: https://www.ncbi.nlm.nih.gov/nuccore/82503188/.*

- [dog [CanFam3.1]][14] <br>
*dog [CanFam3.1] GCA_000002285.2, Sep 2011. Last updated Jun 2019. This genome was downloaded from ENSEMBL database version 100.*

- [c_elegans [WBcel235]][15] <br>
*WBcel235 [c_elegans] GCA_000002985.3, Oct 2014. Last updated Jan 2019. This genome was downloaded from ENSEMBL database version 100.*


  [1]: https://osf.io/s93d5/wiki/home/
  [2]: https://osf.io/s93d5/wiki/1.%20Installation%20-%20Python/
  [3]: https://osf.io/s93d5/wiki/3.%20Using%20the%20Tool%20-%20Input/
  [4]: https://osf.io/s93d5/wiki/4.%20Using%20the%20Tool%20-%20Output/
  [5]: https://osf.io/s93d5/wiki/6.%20Quick%20Start%20Example/
  [6]: http://uswest.ensembl.org/Homo_sapiens/Info/Index
  [7]: https://grch37.ensembl.org/Homo_sapiens/Info/Index
  [8]: https://uswest.ensembl.org/Mus_musculus/Info/Index
  [9]: https://nov2020.archive.ensembl.org/Mus_musculus/Info/Index
  [10]: http://may2012.archive.ensembl.org/Mus_musculus/Info/Index
  [11]: http://uswest.ensembl.org/Rattus_norvegicus/Location/Genome?r=5:62797383-63627669
  [12]: https://www.ncbi.nlm.nih.gov/genome/15?genome_assembly_id=22535
  [13]: https://www.ncbi.nlm.nih.gov/nuccore/82503188/
  [14]: http://uswest.ensembl.org/Canis_lupus_familiaris/Location/Genome?r=1
  [15]: http://uswest.ensembl.org/Caenorhabditis_elegans/Location/Genome?db=core;g=WBGene00001663;r=V:11174567-11177559
  [16]: https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_009914755.1/
