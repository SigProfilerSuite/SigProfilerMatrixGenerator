# Currently Supported Genomes

This page lists all reference genomes currently supported by SigProfilerMatrixGenerator.

## Summary Table

| Organism | Genome Build | Alias | Source |
|----------|--------------|-------|--------|
| Human | GRCh38.p12 | GRCh38 | ENSEMBL v93.38 |
| Human | GRCh37.p13 | GRCh37 | ENSEMBL v93.37 |
| Mouse | GRCm39 | mm39 | ENSEMBL v103 |
| Mouse | GRCm38.p6 | mm10 | ENSEMBL v93.38 |
| Mouse | GRCm37 | mm9 | ENSEMBL v67 |
| Rat | Rnor_6.0 | rn6 | ENSEMBL v96.6 |
| Yeast | S288C R64-2-1 | yeast | - |
| Epstein-Barr Virus | NC_007605.1 | ebv | NCBI |
| Dog | CanFam3.1 | dog | ENSEMBL v100 |
| C. elegans | WBcel235 | c_elegans | ENSEMBL v100 |

---

## Detailed Genome Information

### Human Genomes

#### GRCh38 (GRCh38.p12)
- **Full Name:** Genome Reference Consortium Human Reference 38
- **INSDC Assembly:** GCA_000001405.27
- **Release Date:** December 2013 (Released July 2014, Last updated January 2018)
- **Source:** ENSEMBL database version 93.38

```python
genInstall.install('GRCh38')
```

#### GRCh37 (GRCh37.p13)
- **Full Name:** Genome Reference Consortium Human Reference 37
- **INSDC Assembly:** GCA_000001405.14
- **Release Date:** February 2009 (Released April 2011, Last updated September 2013)
- **Source:** ENSEMBL database version 93.37

```python
genInstall.install('GRCh37')
```

---

### Mouse Genomes

#### mm39 (GRCm39)
- **Full Name:** Genome Reference Consortium Mouse Reference 39
- **INSDC Assembly:** GCA_000001635.9
- **Release Date:** June 2020 (Last updated August 2020)
- **Source:** ENSEMBL database version 103

```python
genInstall.install('mm39')
```

#### mm10 (GRCm38.p6)
- **Full Name:** Genome Reference Consortium Mouse Reference 38
- **INSDC Assembly:** GCA_000001635.8
- **Release Date:** January 2012 (Released July 2012, Last updated March 2018)
- **Source:** ENSEMBL database version 93.38

```python
genInstall.install('mm10')
```

#### mm9 (GRCm37)
- **Full Name:** Release 67, NCBIM37
- **INSDC Assembly:** GCA_000001635.18
- **Release Date:** January 2011 (Last updated March 2012)
- **Source:** ENSEMBL database version release 67

```python
genInstall.install('mm9')
```

---

### Rat Genome

#### rn6 (Rnor_6.0)
- **INSDC Assembly:** GCA_000001895.4
- **Release Date:** July 2014 (Released June 2015, Last updated January 2017)
- **Source:** ENSEMBL database version 96.6

```python
genInstall.install('rn6')
```

---

### Other Organisms

#### Yeast (Saccharomyces cerevisiae S288C)
- **Assembly:** R64-2-1
- **Release Date:** November 2014

```python
genInstall.install('yeast')
```

#### Epstein-Barr Virus (EBV)
- **Accession:** NC_007605.1
- **Release Date:** November 2005 (Last updated August 2018)
- **Source:** NCBI database

```python
genInstall.install('ebv')
```

#### Dog (CanFam3.1)
- **INSDC Assembly:** GCA_000002285.2
- **Release Date:** September 2011 (Last updated June 2019)
- **Source:** ENSEMBL database version 100

```python
genInstall.install('dog')
```

#### C. elegans (WBcel235)
- **INSDC Assembly:** GCA_000002985.3
- **Release Date:** October 2014 (Last updated January 2019)
- **Source:** ENSEMBL database version 100

```python
genInstall.install('c_elegans')
```

---

## Installation Example

To install a reference genome:

```python
from SigProfilerMatrixGenerator import install as genInstall
genInstall.install('GRCh37')  # Replace with your desired genome
```

**Note:** Each genome requires approximately 3 GB of storage space. The installation process may take some time due to the large file sizes.
