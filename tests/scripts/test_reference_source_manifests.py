import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_grch37_source_manifest_is_complete_and_uses_sha256():
    manifest = ROOT / "reference_data" / "GRCh37" / "source_manifest.tsv"
    rows = [
        line.split("\t")
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]

    assert len(rows) == 26
    assert len({row[0] for row in rows}) == len(rows)
    assert all(len(row) == 4 for row in rows)
    assert all(len(row[1]) == hashlib.sha256().digest_size * 2 for row in rows)
    assert all(set(row[1]) <= set("0123456789abcdef") for row in rows)
    assert {row[0] for row in rows if row[0].endswith(".fa.gz")} == {
        *(
            f"Homo_sapiens.GRCh37.dna.chromosome.{chrom}.fa.gz"
            for chrom in range(1, 23)
        ),
        "Homo_sapiens.GRCh37.dna.chromosome.X.fa.gz",
        "Homo_sapiens.GRCh37.dna.chromosome.Y.fa.gz",
        "Homo_sapiens.GRCh37.dna.chromosome.MT.fa.gz",
    }


def test_grch37_annotation_exclusions_are_explicit():
    path = ROOT / "reference_data" / "GRCh37" / "excluded_transcript_ids.txt"
    transcript_ids = {
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }

    assert len(transcript_ids) == 54
    assert all(transcript_id.startswith("ENST") for transcript_id in transcript_ids)
