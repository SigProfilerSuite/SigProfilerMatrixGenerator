import hashlib
import tarfile

import pytest

from tools.build_reference_archive import build_archive


@pytest.mark.parametrize("compression_level", [1, 6, 9])
def test_reference_archive_is_deterministic_and_has_expected_layout(tmp_path, compression_level):
    reference = tmp_path / "fixture"
    reference.mkdir()
    (reference / "2.txt").write_bytes(b"second")
    (reference / "1.txt").write_bytes(b"first")
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"

    build_archive(reference, first, compression_level=compression_level)
    build_archive(reference, second, compression_level=compression_level)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()
    with tarfile.open(first, "r:gz") as archive:
        assert archive.getnames() == ["fixture", "fixture/1.txt", "fixture/2.txt"]
        assert archive.extractfile("fixture/1.txt").read() == b"first"
        for member in archive.getmembers():
            assert member.mtime == 0
            assert member.uid == member.gid == 0


def test_reference_archive_validation_rejects_partial_or_changed_payload(tmp_path):
    reference = tmp_path / "fixture"
    reference.mkdir()
    (reference / "1.txt").write_bytes(b"first")
    expected = {
        "1": hashlib.md5(b"first").hexdigest(),
        "2": hashlib.md5(b"second").hexdigest(),
    }

    with pytest.raises(ValueError, match="missing=.*2.txt"):
        build_archive(reference, tmp_path / "partial.tar.gz", expected)

    (reference / "2.txt").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_archive(reference, tmp_path / "changed.tar.gz", expected)
    assert not (tmp_path / "partial.tar.gz").exists()
    assert not (tmp_path / "changed.tar.gz").exists()


def test_registered_archive_requires_installable_names_and_no_extra_files(tmp_path):
    reference = tmp_path / "wrong-name"
    reference.mkdir()
    (reference / "1.txt").write_bytes(b"first")
    expected = {"1": hashlib.md5(b"first").hexdigest()}

    with pytest.raises(ValueError, match="directory must be named"):
        build_archive(
            reference,
            tmp_path / "fixture.tar.gz",
            expected,
            expected_genome="fixture",
        )

    reference = reference.rename(tmp_path / "fixture")
    with pytest.raises(ValueError, match="archive must be named"):
        build_archive(
            reference,
            tmp_path / "wrong.tar.gz",
            expected,
            expected_genome="fixture",
        )

    (reference / "notes.txt").write_text("not part of the reference")
    with pytest.raises(ValueError, match="unexpected=.*notes.txt"):
        build_archive(
            reference,
            tmp_path / "fixture.tar.gz",
            expected,
            expected_genome="fixture",
        )
