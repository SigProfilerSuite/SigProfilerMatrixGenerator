import hashlib
from pathlib import Path

import pytest

from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import reference_genome_manager as refs


@pytest.mark.parametrize(
    "name,assembly",
    [
        ("GRCh37", "GRCh37"),
        ("GRCh38", "GRCh38"),
        ("GRCh37_havana", "GRCh37"),
        ("GRCh38_havana", "GRCh38"),
        ("GRCh38_Legacy", "GRCh38"),
        ("mm10_havana", "mm10"),
        ("custom_genome_name", "custom_genome_name"),
        ("contains_havana_but_not_registered", "contains_havana_but_not_registered"),
    ],
)
def test_reference_assembly_mapping_is_explicit(name, assembly):
    assert refs.get_reference_assembly(name) == assembly


def test_corrected_and_legacy_grch38_registrations_have_all_primary_chromosomes():
    expected = {
        *(str(chromosome) for chromosome in range(1, 23)),
        "X",
        "Y",
        "MT",
    }
    assert set(refs.CHECKSUMS["GRCh38"]) == expected
    assert set(refs.CHECKSUMS["GRCh38_Legacy"]) == expected
    assert refs.CHECKSUMS["GRCh38"] != refs.CHECKSUMS["GRCh38_Legacy"]


def test_corrected_and_legacy_grch38_context_tables_are_packaged():
    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator"
        / "references"
        / "chromosomes"
        / "context_distributions"
    )
    for reference in ("GRCh38", "GRCh38_Legacy"):
        for context in ("24", "384", "6144", "DBS186"):
            assert (context_dir / f"context_counts_{reference}_{context}.csv").is_file()
            assert (
                context_dir / f"context_counts_{reference}_{context}_exome.csv"
            ).is_file()
            for gender in ("female", "male"):
                assert (
                    context_dir
                    / f"context_distribution_{reference}_{context}_{gender}.csv"
                ).is_file()
                assert (
                    context_dir
                    / f"context_distribution_{reference}_{context}_{gender}_exome.csv"
                ).is_file()

    assert not any(context_dir.glob("*GRCh38_TSBv2*"))
    assert (
        context_dir / "context_counts_GRCh38_6144.csv"
    ).read_bytes() != (
        context_dir / "context_counts_GRCh38_Legacy_6144.csv"
    ).read_bytes()


@pytest.mark.parametrize(
    "status,message",
    [
        ("unregistered", "not registered"),
        ("missing", "has not been installed"),
        ("partial", "incomplete"),
        ("directory_instead_of_file", "incomplete"),
        ("mismatch", "files do not match the checksums"),
    ],
)
def test_public_api_explains_reference_verification_failure(
    monkeypatch, tmp_path, status, message
):
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    name = "review_fixture"
    contents = b"expected reference"
    checksum = hashlib.md5(contents).hexdigest()
    if status != "unregistered":
        monkeypatch.setitem(refs.CHECKSUMS, name, {"1": checksum, "2": checksum})
    directory = tmp_path / "tsb" / name
    directory.mkdir(parents=True)
    if status in {"partial", "directory_instead_of_file", "mismatch"}:
        (directory / "1.txt").write_bytes(contents)
    if status == "mismatch":
        (directory / "2.txt").write_bytes(b"old or damaged reference")
    elif status == "directory_instead_of_file":
        (directory / "2.txt").mkdir()
    before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}

    with pytest.raises(refs.ReferenceInstallationError, match=message) as error:
        api.SigProfilerMatrixGeneratorFunc(
            "fixture",
            name,
            str(tmp_path),
            volume=str(tmp_path),
            plot=False,
        )
    if status == "mismatch":
        assert "has not been installed" not in str(error.value)
        assert "different revision" in str(error.value)
    after = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    assert before == after


def test_old_grch38_installation_error_explains_legacy_migration(
    monkeypatch, tmp_path
):
    monkeypatch.setitem(refs.CHECKSUMS, "GRCh38", {"1": "not-the-old-checksum"})
    directory = tmp_path / "tsb" / "GRCh38"
    directory.mkdir(parents=True)
    (directory / "1.txt").write_bytes(b"former GRCh38 reference")
    manager = refs.ReferenceGenomeManager(str(tmp_path))

    message = manager.installation_error_message("GRCh38")

    assert "Reinstall 'GRCh38' for new analyses" in message
    assert "'GRCh38_Legacy'" in message
