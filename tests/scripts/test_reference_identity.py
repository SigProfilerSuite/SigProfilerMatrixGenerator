import hashlib

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
        ("mm10_havana", "mm10"),
        ("custom_genome_name", "custom_genome_name"),
        ("contains_havana_but_not_registered", "contains_havana_but_not_registered"),
    ],
)
def test_reference_assembly_mapping_is_explicit(name, assembly):
    assert refs.get_reference_assembly(name) == assembly


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
