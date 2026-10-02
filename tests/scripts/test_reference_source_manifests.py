import hashlib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "reference,prefix,chromosomes,row_count,annotation",
    [
        (
            "GRCh37",
            "Homo_sapiens.GRCh37.dna.chromosome",
            range(1, 23),
            26,
            None,
        ),
        (
            "mm9",
            "Mus_musculus.NCBIM37.67.dna.chromosome",
            range(1, 20),
            23,
            None,
        ),
        (
            "mm10",
            "Mus_musculus.GRCm38.dna.chromosome",
            range(1, 20),
            23,
            "Mus_musculus.GRCm38.94.chr.gtf.gz",
        ),
    ],
)
def test_source_manifest_is_complete_and_uses_sha256(
    reference, prefix, chromosomes, row_count, annotation
):
    manifest = ROOT / "reference_data" / reference / "source_manifest.tsv"
    rows = [
        line.split("\t")
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]

    assert len(rows) == row_count
    assert len({row[0] for row in rows}) == len(rows)
    assert all(len(row) == 4 for row in rows)
    assert all(len(row[1]) == hashlib.sha256().digest_size * 2 for row in rows)
    assert all(set(row[1]) <= set("0123456789abcdef") for row in rows)
    assert {row[0] for row in rows if row[0].endswith(".fa.gz")} == {
        *(f"{prefix}.{chrom}.fa.gz" for chrom in chromosomes),
        f"{prefix}.X.fa.gz",
        f"{prefix}.Y.fa.gz",
        f"{prefix}.MT.fa.gz",
    }
    if annotation:
        assert annotation in {row[0] for row in rows}


@pytest.mark.parametrize(
    "reference,count,prefix",
    [("GRCh37", 54, "ENST"), ("mm9", 21, "ENSMUST"), ("mm10", 58, "ENSMUST")],
)
def test_annotation_exclusions_are_explicit(reference, count, prefix):
    path = ROOT / "reference_data" / reference / "excluded_transcript_ids.txt"
    transcript_ids = {
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }

    assert len(transcript_ids) == count
    assert all(transcript_id.startswith(prefix) for transcript_id in transcript_ids)
