# GRCh37 corrected TSB provenance

The corrected `GRCh37` reference uses GRCh37.p13 (`GCA_000001405.14`)
chromosome FASTA files from the frozen Ensembl GRCh37 release 93 directory.
The annotation source is `Homo_sapiens.GRCh37.87.chr.gtf.gz`; Ensembl's frozen
GRCh37 service exposes release 87 gene annotation through the release 93
directory. `source_manifest.tsv` records the SHA-256 and Ensembl `sum` values
verified before generation.

The historical package contains 81,691 protein-coding transcript rows. Every
one maps exactly to a `transcript` feature in the pinned GTF. The GTF has 54
additional protein-coding transcripts that were absent from the historical
BioMart export. They are listed in `excluded_transcript_ids.txt` and remain
excluded so this correction changes only TSB interval semantics, not annotation
scope. Concatenating the historical transcript files in lexical filename order
has SHA-256 `2729a17eb2c98ca3ca58d524a491602a161ba145fa0e0adbde4b81b4482fed67`.

Generation used the repository's `save_tsb_192.save_tsb` implementation with
one-based, inclusive transcript coordinates. Validation independently rebuilt
the interval states from all transcript start/end events and checked all
3,095,693,981 encoded positions. DNA bases matched the pinned FASTA at every
position. Relative to the historical archive, 1,717,352 strand labels changed:
8,345 N-to-T, 8,546 N-to-U, 670,933 T-to-B, and 1,029,528 U-to-B.

The normalized inputs and TSB files can be reproduced from the repository root
with the following commands after downloading every file listed in
`source_manifest.tsv` to `$SOURCE`:

```bash
shasum -a 256 "$SOURCE"/*.gz
mkdir -p "$BUILD/chrom_string" "$BUILD/tsb/GRCh37"
for fasta in "$SOURCE"/Homo_sapiens.GRCh37.dna.chromosome.*.fa.gz; do
    chromosome="${fasta##*.chromosome.}"
    chromosome="${chromosome%.fa.gz}"
    gzip -dc "$fasta" | tail -n +2 | tr -d '\n\r' \
        > "$BUILD/chrom_string/$chromosome.txt"
done
PYTHONPATH=. python -c \
  'from SigProfilerMatrixGenerator.scripts.save_tsb_192 import save_tsb; save_tsb("'$BUILD'/chrom_string", "SigProfilerMatrixGenerator/references/chromosomes/transcripts/GRCh37", "'$BUILD'/tsb/GRCh37")'
```

The strand-dependent 24, 384, 6144, and DBS186 opportunity tables were rebuilt
from the corrected bytes. Collapsing strand labels reproduces source-sequence
counts, with one deliberate correction to the historical whole-genome tables:
the old generator omitted chromosome 17's final valid window. The corrected
tables include its terminal `GTGGT` five-base context (canonical `ACCAC`) and
terminal `GT` dinucleotide (canonical `AC`), increasing the corresponding
whole-genome total by one. Exome totals are unchanged.

The unmatched historical `context_distribution_GRCh37_DBS186_female_BED.csv`
artifact has no runtime consumer and no corresponding male or other-context
table. It is retained under the `GRCh37_Legacy` identity only and is not part of
the corrected default table footprint.

The corrected logical reference `GRCh37` resolves to `GRCh37.tar.gz`.
`GRCh37_Legacy` resolves to a copy of the untouched historical archive named
`GRCh37_Legacy.tar.gz`; the installer safely remaps its internal `GRCh37/`
directory to `GRCh37_Legacy/`. Existing installations of the former `GRCh37`
must be reinstalled after upgrading.
