# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added support for the T2T-CHM13v2.0 human reference genome (CHM13-T2T), nuclear chromosomes only (1–22, X, Y), distributed via the AlexandrovLab FTP.
- Added `scripts/build_refseq_references.py`, the developer tool that derives both the CHM13-T2T exome interval list and its per-chromosome transcript files from a pinned NCBI RefSeq annotation release, so the shipped files can be regenerated and audited rather than only described. Replaces `scripts/build_exome_interval_list.py`, whose behaviour is now the `exome-list` subcommand.
- Added an exome interval list for CHM13-T2T, so `exome=True` is supported alongside WGS. It is annotation-derived (union of all CDS features in NCBI RefSeq annotation release `GCF_009914755.1-RS_2025_08`, merged; 213,010 intervals over 36.4 Mb) rather than a capture-kit definition, so CHM13-T2T exome matrices are not directly comparable to GRCh38 exome matrices. See `docs/Currently-Supported-Genomes.md` for the full derivation.

### Fixed
- `test_one_genome()` now forwards `exome`/`bed_file` to `load_and_compare()`. Without them those parameters kept their defaults (`exome=False`, `bed_file=True`), so the WGS and exome paths looked for `.region` solution files in the `WGS/solutions` and `WES/solutions` directories, where the files are named `.all` and `.exome`. Nothing matched, and for every genome only the bed_file path was ever actually asserted.

### Changed
- Regenerated the CHM13-T2T transcript files, and with them the whole TSB reference payload, against NCBI RefSeq annotation release `GCF_009914755.1-RS_2025_08`. The previous files came from an earlier release that was never recorded, so neither they nor the TSB files derived from them could be reproduced from any pinned source. All 24 per-chromosome checksums in `CHECKSUMS` change as a result. Note that RS_2025_08 annotates 4,993 transcripts on chrY against 882 before, almost all Gnomon-predicted lncRNA models in the Yq12 satellite region newly resolved by T2T, so transcriptional strand assignments on chrY shift substantially.
- `exome=True` now fails immediately with an actionable message naming the missing interval list and the genomes that do support exome downsampling, instead of raising a bare `FileNotFoundError` after every chromosome has already been parsed.
- Exome interval list paths are resolved through `ReferenceDir.get_exome_dir()` / `get_exome_interval_list()` rather than being assembled by hand in several places.

## [1.3.6] - 2025-10-28

### Added
- Implemented a CI/CD pipeline with Travis CI to automate the building and publishing of Docker images to GHCR.

## [1.3.5] - 2025-08-05

### Changed
- Updated README to clarify usage and examples.
- Added custom output directory option.

## [1.3.4] - 2025-06-06

### Fixed
- Update file counts for rn7 and mm39 genomes after issue resolving issue with save_context_distribution script where final chromosome was not being processed correctly and counts were being carried over from the previous chromosome.

### Added
- Added pyproject.toml file to the repository to support Python packaging and distribution.

## [1.3.3] - 2025-04-16

### Fixed
- Resolved an issue where ID plots were not generated due to the use of an unrecognized plot type (`96ID`). The correct plot type `IDSB` is now used.

### Deprecated
- Removed support for **ICGC input format**. The [ICGC Data Portal officially closed](https://www.icgc-argo.org/) in June 2024, and associated example files are no longer accessible. Since the format is no longer actively maintained or distributed, and unresolved issues remained (see [#158](https://github.com/SigProfilerSuite/SigProfilerMatrixGenerator/issues/158), [#159](https://github.com/SigProfilerSuite/SigProfilerMatrixGenerator/issues/159)), support has been deprecated to reduce maintenance burden and avoid user confusion.

## [1.3.2] - 2025-03-13

### Fixed
- The save_context_distribution script had an error on the edges of chromosomes where the window would extend beyond the chromosome length. This was fixed by limiting the window to the chromosome length.
- The save_context_distribution script had an error when running multiple jobs in paralell because the exome file was being sorted differently for male and female genomes and concurrent jobs would overwrite each other. This was fixed by creating unique temporary files for each run.

### Added
- Context distribution files for mm39 and rn7 genomes.
- Exome file for rn7 genome.


## [1.3.1] - 2025-03-13

### Fixed
- SV Matrix generation compatibility: Updated remnant Pandas and NumPy < 2.0.0 syntax to ensure compatibility with newer versions.
- Indexing error in reference genome handling: Edge cases where BED file indices extended beyond the reference genome range caused crashes. Index accesses are now restricted to valid ranges, and cases where the genomic context extends beyond valid positions are skipped.
- Uninitialized variable: The dinuc_mat variable was accessed before being initialized, causing a runtime error. It is now explicitly initialized to None before use.

## [1.3.0] - 2025-02-11

### Changed
- Updated dependencies: Now requires **Pandas >= 2.0.0**, **NumPy >= 2.0.0**, and **Python >= 3.9**.
- Dropped support for **Python 3.8**

## [1.2.31] - 2024-11-6

### Fixed
- Resolved a bug where DBS and ID matrices were not being returned due to an indentation issue when the parameter 'chrom_based' was set as True.

### Notice
- Python 3.8 support will be phased out in future updates as we align with Python's ongoing release cycle. Users on Python 3.8 are encouraged to consider upgrading to Python 3.9 or newer.

## [1.2.30] - 2024-10-10

### Fixed
- Resolved a bug that caused the code to crash when running with `exome=True` during INDEL processing. The issue was due to incorrect indentation.

## [1.2.29] - 2024-09-24

### Added
- Added sort function to handle non-sorted input and BED files. This posed as an issue for when the BED file was not sorted by chromosome and start position in cases when certain reference genomes were used because of roman numerals and decimal (ie ChrX vs chr10).

### Changed
- Transcript files were modified to adopt the new sorting standard.


## [1.2.28] - 2024-08-06

### Added
- Added support for processing SV input for VCF versions 4.1, 4.2, and 4.3. The tool now supports both the previous input format (requiring the first six columns and either the "svclass" column or the "strand1" & "strand2" columns) and VCF files.

### Changed
- Updated the README command line examples to use CLI instead of calling the script directly.

## [1.2.27] - 2024-07-18

### Added
- Added environmental variable `SIGPROFILERMATRIXGENERATOR_VOLUME` to enhance configurability.
- Updated CLI to handle boolean arguments more effectively.

### Changed
- Fixed `binomtest` to use the parameter `k` instead of `x` for improved accuracy and clarity.
- Updated Dockerfile to require SigProfilerMatrixGenerator version 1.2.27 (previously 1.2.25).
- Updated `numpy` dependency to require `numpy>=1.18.5,<2.0.0` to prevent compatibility issues with `numpy` 2.0.0.
- Removed incorrect print statement for the SV plot file path.
