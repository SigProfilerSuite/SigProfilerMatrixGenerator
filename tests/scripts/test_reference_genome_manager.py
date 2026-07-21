import ftplib
import io
import subprocess
import tarfile

import pytest

from SigProfilerMatrixGenerator.scripts import reference_genome_manager


def write_test_archive(archive_path, genome_name="test_genome"):
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    contents = b"test chromosome contents"
    member = tarfile.TarInfo(f"{genome_name}/1.txt")
    member.size = len(contents)
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(member, io.BytesIO(contents))


def test_download_genome_installs_archive_from_ftp(monkeypatch, tmp_path):
    manager = reference_genome_manager.ReferenceGenomeManager(reference_dir=tmp_path)
    archive_path = tmp_path.resolve() / "tsb" / "test_genome.tar.gz"
    installed_file = tmp_path.resolve() / "tsb" / "test_genome" / "1.txt"

    monkeypatch.setattr(manager, "is_genome_installed", lambda genome: False)
    monkeypatch.setattr(
        manager,
        "_download_via_ftplib",
        lambda *args: write_test_archive(args[-1]),
    )

    def unexpected_curl(*args):
        raise AssertionError("curl should not run after a successful FTP download")

    monkeypatch.setattr(manager, "_download_via_curl", unexpected_curl)

    manager.download_genome("test_genome")

    assert installed_file.read_bytes() == b"test chromosome contents"
    assert not archive_path.exists()


def test_download_genome_falls_back_to_curl_on_same_mirror(monkeypatch, tmp_path):
    manager = reference_genome_manager.ReferenceGenomeManager(reference_dir=tmp_path)
    calls = []

    monkeypatch.setattr(manager, "is_genome_installed", lambda genome: False)
    monkeypatch.setattr(reference_genome_manager.shutil, "which", lambda name: "curl")

    def fail_ftp(server, path, filename, local_filepath):
        calls.append(("ftp", server))
        raise ftplib.error_temp("Connection reset by peer")

    def successful_curl(server, path, filename, local_filepath):
        calls.append(("curl", server))
        write_test_archive(local_filepath)

    monkeypatch.setattr(manager, "_download_via_ftplib", fail_ftp)
    monkeypatch.setattr(manager, "_download_via_curl", successful_curl)

    manager.download_genome("test_genome")

    assert calls == [
        ("ftp", "alexandrovlab-ftp.ucsd.edu"),
        ("curl", "alexandrovlab-ftp.ucsd.edu"),
    ]
    assert (tmp_path.resolve() / "tsb" / "test_genome" / "1.txt").exists()


def test_download_via_curl_uses_retrying_ftp_command(monkeypatch, tmp_path):
    manager = reference_genome_manager.ReferenceGenomeManager(reference_dir=tmp_path)
    archive_path = tmp_path / "downloads" / "ebv.tar.gz"
    observed = {}

    def capture_run(command, check):
        observed["command"] = command
        observed["check"] = check

    monkeypatch.setattr(reference_genome_manager.subprocess, "run", capture_run)

    manager._download_via_curl(
        "alexandrovlab-ftp.ucsd.edu",
        "pub/tools/SigProfilerMatrixGenerator/",
        "ebv.tar.gz",
        archive_path,
    )

    assert observed == {
        "command": [
            "curl",
            "--fail",
            "--location",
            "--retry",
            "3",
            "--connect-timeout",
            "30",
            "-o",
            str(archive_path),
            "ftp://alexandrovlab-ftp.ucsd.edu/pub/tools/"
            "SigProfilerMatrixGenerator/ebv.tar.gz",
        ],
        "check": True,
    }


def test_download_genome_raises_clear_error_when_all_downloads_fail(
    monkeypatch, tmp_path
):
    manager = reference_genome_manager.ReferenceGenomeManager(reference_dir=tmp_path)
    archive_path = tmp_path.resolve() / "tsb" / "mm10.tar.gz"

    monkeypatch.setattr(manager, "is_genome_installed", lambda genome: False)
    monkeypatch.setattr(reference_genome_manager.shutil, "which", lambda name: "curl")

    def fail_ftp(*args):
        raise ftplib.error_temp("Connection reset by peer")

    def fail_curl(*args):
        local_filepath = args[-1]
        local_filepath.write_bytes(b"partial archive")
        raise subprocess.CalledProcessError(56, ["curl"])

    monkeypatch.setattr(manager, "_download_via_ftplib", fail_ftp)
    monkeypatch.setattr(manager, "_download_via_curl", fail_curl)

    with pytest.raises(reference_genome_manager.GenomeDownloadError) as error:
        manager.download_genome("mm10")

    message = str(error.value)
    assert "Unable to download mm10.tar.gz" in message
    assert "alexandrovlab FTP" in message
    assert "sanger curl" in message
    assert "--local_genome" in message
    assert "offline_files_path" in message
    assert "directory containing the archive" in message
    assert not archive_path.exists()


def test_download_genome_removes_bad_archive_when_extract_fails(monkeypatch, tmp_path):
    manager = reference_genome_manager.ReferenceGenomeManager(reference_dir=tmp_path)
    archive_path = tmp_path.resolve() / "tsb" / "mm10.tar.gz"

    monkeypatch.setattr(manager, "is_genome_installed", lambda genome: False)

    def write_bad_archive(*args):
        local_filepath = args[-1]
        local_filepath.write_bytes(b"not a tar.gz archive")

    monkeypatch.setattr(manager, "_download_via_ftplib", write_bad_archive)

    with pytest.raises(reference_genome_manager.GenomeDownloadError) as error:
        manager.download_genome("mm10")

    assert "could not be extracted" in str(error.value)
    assert "offline_files_path" in str(error.value)
    assert not archive_path.exists()
