from pathlib import Path


CONTEXT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "SigProfilerMatrixGenerator"
    / "references"
    / "chromosomes"
    / "context_distributions"
)


def _manifest_entries():
    manifest = CONTEXT_DIRECTORY / "context_table_manifest.txt"
    return {
        line.strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_context_table_manifest_matches_packaged_source_files():
    expected = _manifest_entries()
    observed = {path.name for path in CONTEXT_DIRECTORY.glob("*.csv")}

    assert expected == observed
    assert not any(
        "_TSBv2" in filename or "_pending" in filename for filename in expected
    )


def test_context_table_manifest_records_known_irregular_footprints():
    entries = _manifest_entries()

    assert "context_distribution_GRCh37_DBS186_female_BED.csv" in entries
    # The historically missing whole-genome male "6" table has been rebuilt
    # and is now packaged for both the corrected and Legacy mm10 identities.
    assert "context_distribution_mm10_6_male.csv" in entries
    assert "context_distribution_mm10_Legacy_6_male.csv" in entries
    assert not any(
        filename.startswith("context_distribution_rn6_DBS") for filename in entries
    )
