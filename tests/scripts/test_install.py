from unittest import mock

from SigProfilerMatrixGenerator import install
from SigProfilerMatrixGenerator.scripts import reference_genome_manager


def test_python_offline_install_delegates_to_verified_local_installer(
    monkeypatch, tmp_path
):
    manager = mock.create_autospec(
        reference_genome_manager.ReferenceGenomeManager, instance=True
    )
    monkeypatch.setattr(
        reference_genome_manager,
        "ReferenceGenomeManager",
        lambda volume: manager,
    )
    archive_directory = tmp_path / "archives"
    volume = tmp_path / "volume"

    install.install(
        "CHM13-T2T",
        offline_files_path=str(archive_directory),
        volume=str(volume),
    )

    manager.install_local_genome.assert_called_once_with(
        "CHM13-T2T", str(archive_directory)
    )
