import time

import pytest

from SigProfilerMatrixGenerator.scripts import reference_genome_manager
from SigProfilerMatrixGenerator.web import genomes


@pytest.fixture
def volume(tmp_path, monkeypatch):
    # The env var outranks the volume argument in ref_install.reference_dir().
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    monkeypatch.setitem(reference_genome_manager.CHECKSUMS, "fixtureA", {"1": "x", "2": "y"})
    monkeypatch.setitem(reference_genome_manager.CHECKSUMS, "fixtureB", {"1": "x"})
    return tmp_path


def _install_files(volume, genome, chroms):
    folder = volume / "tsb" / genome
    folder.mkdir(parents=True, exist_ok=True)
    for chrom in chroms:
        (folder / f"{chrom}.txt").write_text("data")


def test_available_genomes_matches_checksums_registry():
    assert genomes.available_genomes() == sorted(reference_genome_manager.CHECKSUMS)


def test_a_genome_with_every_chromosome_file_is_installed(volume):
    _install_files(volume, "fixtureA", ["1", "2"])

    assert "fixtureA" in genomes.installed_genomes(str(volume))


def test_a_genome_missing_a_chromosome_file_is_not_installed(volume):
    _install_files(volume, "fixtureA", ["1"])

    assert "fixtureA" not in genomes.installed_genomes(str(volume))


def test_status_reports_available_and_installed(volume):
    _install_files(volume, "fixtureB", ["1"])

    result = genomes.status(str(volume))

    assert "fixtureB" in result["available"]
    assert "fixtureA" in result["available"]
    assert result["installed"] == ["fixtureB"]


def test_status_does_not_hash_files(volume, monkeypatch):
    # Hashing every chromosome on each page load took ~7 s for one genome.
    _install_files(volume, "fixtureA", ["1", "2"])
    monkeypatch.setattr(
        reference_genome_manager.ReferenceGenomeManager, "_verify_checksum",
        lambda *a, **k: pytest.fail("status() must not checksum files"),
    )
    started = time.monotonic()
    genomes.status(str(volume))
    assert time.monotonic() - started < 1.0


def test_install_calls_download_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reference_genome_manager.ReferenceGenomeManager,
        "download_genome",
        lambda self, name: calls.append(("download", name)),
    )

    genomes.install("GRCh37")

    assert calls == [("download", "GRCh37")]


def test_install_uses_local_genome_when_given(monkeypatch):
    calls = []
    monkeypatch.setattr(
        reference_genome_manager.ReferenceGenomeManager,
        "install_local_genome",
        lambda self, name, directory: calls.append(("local", name, directory)),
    )

    genomes.install("GRCh37", local_genome_dir="/tmp/my_genome")

    assert calls == [("local", "GRCh37", "/tmp/my_genome")]
