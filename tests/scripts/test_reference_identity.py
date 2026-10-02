import hashlib
from pathlib import Path

import pytest

from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import reference_genome_manager as refs


@pytest.mark.parametrize(
    "name,assembly",
    [
        ("GRCh37", "GRCh37"),
        ("GRCh37_Legacy", "GRCh37"),
        ("GRCh38", "GRCh38"),
        ("GRCh37_havana", "GRCh37"),
        ("GRCh38_havana", "GRCh38"),
        ("GRCh38_Legacy", "GRCh38"),
        ("mm9_Legacy", "mm9"),
        ("mm10_havana", "mm10"),
        ("mm10_Legacy", "mm10"),
        ("mm39_Legacy", "mm39"),
        ("rn6_Legacy", "rn6"),
        ("rn7_Legacy", "rn7"),
        ("dog_Legacy", "dog"),
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


@pytest.mark.parametrize("reference", ["mm9", "mm10"])
def test_corrected_and_legacy_mouse_registrations_have_all_primary_chromosomes(reference):
    expected = {
        *(str(chromosome) for chromosome in range(1, 20)),
        "X",
        "Y",
        "MT",
    }
    assert set(refs.CHECKSUMS[reference]) == expected
    assert set(refs.CHECKSUMS[f"{reference}_Legacy"]) == expected
    assert refs.CHECKSUMS[reference] != refs.CHECKSUMS[f"{reference}_Legacy"]


def test_corrected_and_legacy_grch37_registrations_have_all_primary_chromosomes():
    expected = {
        *(str(chromosome) for chromosome in range(1, 23)),
        "X",
        "Y",
        "MT",
    }
    assert set(refs.CHECKSUMS["GRCh37"]) == expected
    assert set(refs.CHECKSUMS["GRCh37_Legacy"]) == expected
    assert refs.CHECKSUMS["GRCh37"] != refs.CHECKSUMS["GRCh37_Legacy"]


def test_corrected_and_legacy_mm39_registrations_have_all_primary_chromosomes():
    expected = {*(str(chromosome) for chromosome in range(1, 20)), "X", "Y"}
    assert set(refs.CHECKSUMS["mm39"]) == expected
    assert set(refs.CHECKSUMS["mm39_Legacy"]) == expected
    assert refs.CHECKSUMS["mm39"] != refs.CHECKSUMS["mm39_Legacy"]


def test_corrected_and_legacy_rn6_retain_historical_table_footprint():
    expected = {*(str(chromosome) for chromosome in range(1, 21)), "X", "Y", "MT"}
    assert set(refs.CHECKSUMS["rn6"]) == expected
    assert set(refs.CHECKSUMS["rn6_Legacy"]) == expected
    assert refs.CHECKSUMS["rn6"] != refs.CHECKSUMS["rn6_Legacy"]
    assert refs.get_archive_filename("rn6") == "rn6.tar.gz"
    assert refs.get_archive_filename("rn6_Legacy") == "rn6_Legacy.tar.gz"

    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator/references/chromosomes/context_distributions"
    )
    for reference in ("rn6", "rn6_Legacy"):
        files = [
            path for path in context_dir.glob(f"context_*_{reference}_*.csv")
            if reference != "rn6" or "_rn6_Legacy_" not in path.name
        ]
        assert len(files) == 38
        assert not list(context_dir.glob(f"context_distribution_{reference}_DBS*.csv"))
        assert (context_dir / f"context_counts_{reference}_DBS.csv").is_file()


def test_corrected_and_legacy_rn7_retain_historical_table_footprint():
    expected = {*(str(chromosome) for chromosome in range(1, 21)), "X", "Y", "MT"}
    assert set(refs.CHECKSUMS["rn7"]) == expected
    assert set(refs.CHECKSUMS["rn7_Legacy"]) == expected
    assert refs.CHECKSUMS["rn7"] != refs.CHECKSUMS["rn7_Legacy"]
    assert refs.get_archive_filename("rn7") == "rn7.tar.gz"
    assert refs.get_archive_filename("rn7_Legacy") == "rn7_Legacy.tar.gz"

    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator/references/chromosomes/context_distributions"
    )
    for reference in ("rn7", "rn7_Legacy"):
        files = [
            path for path in context_dir.glob(f"context_*_{reference}_*.csv")
            if reference != "rn7" or "_rn7_Legacy_" not in path.name
        ]
        assert len(files) == 48
        assert (context_dir / f"context_counts_{reference}_DBS186_exome.csv").is_file()
        assert (context_dir / f"context_distribution_{reference}_6144_male.csv").is_file()


def test_corrected_and_legacy_dog_registrations_have_historical_chromosomes():
    expected = {*(str(chromosome) for chromosome in range(1, 39)), "X"}
    assert set(refs.CHECKSUMS["dog"]) == expected
    assert set(refs.CHECKSUMS["dog_Legacy"]) == expected
    assert refs.CHECKSUMS["dog"] != refs.CHECKSUMS["dog_Legacy"]
    assert refs.get_archive_filename("dog") == "dog.tar.gz"
    assert refs.get_archive_filename("dog_Legacy") == "dog_Legacy.tar.gz"

    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator/references/chromosomes/context_distributions"
    )
    assert not list(context_dir.glob("context_*_dog_*.csv"))
    assert not list(context_dir.glob("context_*_dog_Legacy_*.csv"))


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
    assert (context_dir / "context_counts_GRCh38_6144.csv").read_bytes() != (
        context_dir / "context_counts_GRCh38_Legacy_6144.csv"
    ).read_bytes()


def test_corrected_and_legacy_mm10_context_tables_are_packaged():
    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator"
        / "references"
        / "chromosomes"
        / "context_distributions"
    )
    for reference in ("mm10", "mm10_Legacy"):
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
        for context in ("6", "96", "1536"):
            for gender in ("female", "male"):
                assert (
                    context_dir
                    / f"context_distribution_{reference}_{context}_{gender}_exome.csv"
                ).is_file()

    # Every context size ships both WGS genders for the corrected identity,
    # including the historically missing whole-genome male "6" table.
    for context in ("6", "96", "1536"):
        for gender in ("female", "male"):
            assert (
                context_dir / f"context_distribution_mm10_{context}_{gender}.csv"
            ).is_file()
    # mm10_Legacy preserves the exact historical 47-file footprint: it never
    # shipped a whole-genome male "6" distribution, and does not gain one now.
    assert not (
        context_dir / "context_distribution_mm10_Legacy_6_male.csv"
    ).is_file()
    for context in ("96", "1536"):
        assert (
            context_dir / f"context_distribution_mm10_Legacy_{context}_male.csv"
        ).is_file()

    assert (context_dir / "context_counts_mm10_6144.csv").read_bytes() != (
        context_dir / "context_counts_mm10_Legacy_6144.csv"
    ).read_bytes()


@pytest.mark.parametrize("reference_name", ["GRCh37", "mm9", "mm39"])
def test_corrected_and_legacy_context_tables_are_packaged(reference_name):
    context_dir = (
        Path(__file__).resolve().parents[2]
        / "SigProfilerMatrixGenerator"
        / "references"
        / "chromosomes"
        / "context_distributions"
    )
    for reference in (reference_name, f"{reference_name}_Legacy"):
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

    assert (context_dir / f"context_counts_{reference_name}_6144.csv").read_bytes() != (
        context_dir / f"context_counts_{reference_name}_Legacy_6144.csv"
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


def test_old_grch38_installation_error_explains_legacy_migration(monkeypatch, tmp_path):
    monkeypatch.setitem(refs.CHECKSUMS, "GRCh38", {"1": "not-the-old-checksum"})
    directory = tmp_path / "tsb" / "GRCh38"
    directory.mkdir(parents=True)
    (directory / "1.txt").write_bytes(b"former GRCh38 reference")
    manager = refs.ReferenceGenomeManager(str(tmp_path))

    message = manager.installation_error_message("GRCh38")

    assert "Reinstall 'GRCh38' for new analyses" in message
    assert "'GRCh38_Legacy'" in message


def test_old_mm10_installation_error_explains_legacy_migration(monkeypatch, tmp_path):
    monkeypatch.setitem(refs.CHECKSUMS, "mm10", {"1": "not-the-old-checksum"})
    directory = tmp_path / "tsb" / "mm10"
    directory.mkdir(parents=True)
    (directory / "1.txt").write_bytes(b"former mm10 reference")
    manager = refs.ReferenceGenomeManager(str(tmp_path))

    message = manager.installation_error_message("mm10")

    assert "Reinstall 'mm10' for new analyses" in message
    assert "'mm10_Legacy'" in message


def test_grch38_uses_existing_published_archive_filenames():
    assert refs.get_archive_filename("GRCh38") == "GRCh38.tar.gz"
    assert refs.get_archive_filename("GRCh38_Legacy") == "GRCh38_Legacy.tar.gz"
    assert "GRCh38" not in refs.ARCHIVE_FILENAMES


def test_mm10_uses_default_and_legacy_archive_names():
    assert refs.get_archive_filename("mm10") == "mm10.tar.gz"
    assert refs.get_archive_filename("mm10_Legacy") == "mm10_Legacy.tar.gz"
    assert refs.get_archive_root("mm10_Legacy") == "mm10"
    assert "mm10" not in refs.ARCHIVE_FILENAMES


def test_grch37_uses_default_and_legacy_archive_names():
    assert refs.get_archive_filename("GRCh37") == "GRCh37.tar.gz"
    assert refs.get_archive_filename("GRCh37_Legacy") == "GRCh37_Legacy.tar.gz"
    assert refs.get_archive_root("GRCh37_Legacy") == "GRCh37"


def test_mm9_uses_default_and_legacy_archive_names():
    assert refs.get_archive_filename("mm9") == "mm9.tar.gz"
    assert refs.get_archive_filename("mm9_Legacy") == "mm9_Legacy.tar.gz"
    assert refs.get_archive_root("mm9_Legacy") == "mm9"


def test_mm39_default_and_legacy_archive_names():
    assert refs.get_archive_filename("mm39") == "mm39.tar.gz"
    assert refs.get_archive_filename("mm39_Legacy") == "mm39_Legacy.tar.gz"
    assert refs.get_archive_root("mm39_Legacy") == "mm39"


@pytest.mark.parametrize("reference_name", sorted(refs.KNOWN_AFFECTED_UNCORRECTED))
def test_matrix_api_warns_for_known_affected_reference(
    monkeypatch, tmp_path, reference_name
):
    monkeypatch.setattr(
        refs.ReferenceGenomeManager, "is_genome_installed", lambda self, name: False
    )
    monkeypatch.setattr(
        refs.ReferenceGenomeManager,
        "print_genome_checksum_verification_report",
        lambda self, name: None,
    )

    with pytest.warns(
        refs.KnownAffectedReferenceWarning,
        match="Transcription-strand-aware results may be affected",
    ):
        with pytest.raises(refs.ReferenceInstallationError):
            api.SigProfilerMatrixGeneratorFunc(
                "fixture",
                reference_name,
                str(tmp_path),
                volume=str(tmp_path),
                plot=False,
            )
