# CHM13 Opportunities and Downstream Compatibility

## What Is Included

MatrixGenerator supplies raw CHM13 SBS, DBS, and indel matrices, plus 48
opportunity files covering whole genome and annotation-derived CDS exome regions.
The opportunity contexts are 6, 24, 96, 384, 1536, 6144, DBS, and DBS186.

Counts record the number of eligible reference windows per context/chromosome.
Distribution rows divide each chromosome count by the total for that context
across the selected chromosomes. These are chromosome-selection probabilities,
not a mutation-signature catalogue and not a frequency distribution over contexts.
Male tables include X/Y and female tables omit Y, following the existing resource
convention; they do not model copy number or double the number of X copies.
All CHM13 tables are nuclear-only.

SBS contexts use eligible five-base windows, even when reporting one- or
three-base contexts. Unknown DNA bases invalidate a window. DBS uses two-base
windows. Exome windows must fit within the CDS union, without padding or windows
crossing excluded bases. Zero-opportunity rows have zero probabilities.
Different capture kits or custom BED regions require their own opportunity counts;
the shipped exome tables must not be substituted for arbitrary target regions.

See [sources and build command](Currently-Supported-Genomes.md) and
[the runnable matrix example](CHM13-Test-Example.md).

## Extractor and Assignment Are Not Automatically Enabled

The reviewed local Extractor code accepts CHM13 matrices for de novo extraction,
but its catalogue-selection code in `SigProfilerExtractor/sigpro.py` permits
only GRCh37, GRCh38, mm9, mm10, mm39, rn6, and rn7. Other opportunity genome
names, including CHM13, are reset to GRCh37 with a console and metadata message
before the optional assignment/decomposition stage. Adding MatrixGenerator
resources does not change that list or supply CHM13 reference signatures.

**Do not interpret a GRCh37 fallback as CHM13-adjusted catalogue matching.**
No downstream compatibility changes are included in this MatrixGenerator branch.
Package versions may differ; inspect the installed downstream version and its
metadata before interpreting results. Matrix counts themselves require no
opportunity normalization and remain usable independently of catalogue matching.

## Required Downstream Follow-Up

1. Add an explicit CHM13 policy in Extractor/Assignment: permit de novo extraction
   while rejecting unsupported catalogue matching rather than falling back to
   GRCh37 without the user's explicit agreement. Test matrix and VCF entry points,
   including `stop_after_extraction=True`, and record both genome identities.
2. Define and validate how a chosen reference signature catalogue is adjusted
   from its original assembly to CHM13 opportunities. Specify the source assembly,
   whole-genome versus target-region opportunities, channel order, zero-count
   behavior, and normalization. Strand-aware/HD categories also need matching
   transcript/strand definitions; sequence ratios alone do not establish that.
3. Register CHM13 only after the adjusted catalogue and regression expectations
   exist. Test decomposition, refitting, reported metadata, and plots. A new
   catalogue must not be presented as an official COSMIC CHM13 release.
4. Audit Simulator's supported-genome lists and resource loading, then test real
   CHM13 WGS/exome simulations and female Y exclusion. File availability alone
   is not evidence that a downstream consumer supports the assembly.

These are separate downstream changes and review gates, not features already
implemented by this branch. The packaged opportunity tables are a prerequisite.
