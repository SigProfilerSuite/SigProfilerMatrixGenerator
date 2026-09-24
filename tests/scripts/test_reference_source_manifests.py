from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mm39_source_manifest_records_all_chromosomes_and_annotation():
    path = ROOT / "reference_data/mm39/source_manifest.tsv"
    rows = [line.split("\t") for line in path.read_text().splitlines()
            if line and not line.startswith("#")]
    assert len(rows) == 23
    assert len({row[0] for row in rows}) == 23
    assert all(len(row) == 4 and len(row[1]) == 64 for row in rows)
    assert "Mus_musculus.GRCm39.103.chr.gtf.gz" in {row[0] for row in rows}
    assert {row[0] for row in rows if row[0].endswith(".fa.gz")} == {
        *(f"Mus_musculus.GRCm39.dna.chromosome.{chrom}.fa.gz"
          for chrom in range(1, 20)),
        "Mus_musculus.GRCm39.dna.chromosome.X.fa.gz",
        "Mus_musculus.GRCm39.dna.chromosome.Y.fa.gz",
        "Mus_musculus.GRCm39.dna.chromosome.MT.fa.gz",
    }


def test_mm39_historical_transcript_exclusions_are_explicit():
    path = ROOT / "reference_data/mm39/excluded_transcript_ids.txt"
    ids = [line for line in path.read_text().splitlines()
           if line and not line.startswith("#")]
    assert len(ids) == 76
    assert len(set(ids)) == len(ids)
    assert all(transcript.startswith("ENSMUST") for transcript in ids)
