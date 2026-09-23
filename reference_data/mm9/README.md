# mm9 corrected TSB provenance

The corrected `mm9` reference uses GRCm37 / NCBIM37
(`GCA_000001635.18`) chromosome FASTA files and annotation from Ensembl
release 67. `source_manifest.tsv` records SHA-256 and BSD `sum` values verified
before generation. The FASTA `sum` values match Ensembl's published CHECKSUMS;
the GTF directory does not publish a CHECKSUMS file.

The historical package contains 79,644 protein-coding transcript rows. Every
row exactly matches the coordinates, strand, gene, and biotype derived from
the pinned GTF. The GTF has 21 additional protein-coding transcripts that
were absent from the historical BioMart export. They are listed in
`excluded_transcript_ids.txt` and remain excluded so the correction changes
only TSB interval semantics, not annotation scope. Concatenating the
historical transcript files in byte-sorted filename order has SHA-256
`38c4b5eaba548de3051799635b5d73dd6043b34dba7923e986b6e839e77c57d1`.

Generation used the repository's `save_tsb_192.save_tsb` implementation with
one-based, inclusive transcript coordinates. Independent event-sweep
validation checked all 2,654,911,517 positions and found no state errors. DNA
bases matched the pinned FASTA at every position. Relative to the historical
archive, 1,235,491 strand labels changed: 10,029 N-to-T, 9,769 N-to-U,
563,225 T-to-B, and 652,468 U-to-B.

The normalized inputs and TSB files can be reproduced from the repository root
after downloading every file in `source_manifest.tsv` to `$SOURCE`:

```bash
shasum -a 256 "$SOURCE"/*.gz
mkdir -p "$BUILD/chrom_string" "$BUILD/tsb/mm9"
for fasta in "$SOURCE"/Mus_musculus.NCBIM37.67.dna.chromosome.*.fa.gz; do
    chromosome="${fasta##*.chromosome.}"
    chromosome="${chromosome%.fa.gz}"
    gzip -dc "$fasta" | tail -n +2 | tr -d '\n\r' \
        > "$BUILD/chrom_string/$chromosome.txt"
done
PYTHONPATH=. python -c \
  'from SigProfilerMatrixGenerator.scripts.save_tsb_192 import save_tsb; save_tsb("'$BUILD'/chrom_string", "SigProfilerMatrixGenerator/references/chromosomes/transcripts/mm9", "'$BUILD'/tsb/mm9")'
```

The strand-dependent 24, 384, 6144, and DBS186 opportunity tables were
rebuilt from the corrected bytes. Strand-collapsed exome totals reproduce the
historical unstranded tables exactly. The old whole-genome generator omitted
the final valid window on each of 20 chromosomes; corrected tables include
those 20 terminal contexts.

The corrected logical reference `mm9` resolves to the immutable physical
archive `mm9.tsb-v2.tar.gz`. `mm9_Legacy` resolves to the untouched historical
`mm9.tar.gz`; the installer safely remaps its internal `mm9/` directory to
`mm9_Legacy/`.
