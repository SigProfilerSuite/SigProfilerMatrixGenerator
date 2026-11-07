from unittest import mock

import pytest

from SigProfilerMatrixGenerator import test_helpers
from SigProfilerMatrixGenerator import install
from SigProfilerMatrixGenerator.controllers import cli_controller
from SigProfilerMatrixGenerator.scripts import reference_genome_manager


class TestController:
    @pytest.fixture
    def mock_ref_gen_manager(self, monkeypatch):
        """Mock ReferenceGenomeManager for testing."""
        mock_manager = mock.create_autospec(
            reference_genome_manager.ReferenceGenomeManager, instance=True
        )
        monkeypatch.setattr(
            reference_genome_manager,
            "ReferenceGenomeManager",
            lambda volume: mock_manager,
        )
        return mock_manager

    @pytest.fixture
    def mock_install(self, monkeypatch):
        """Temporarily change install.install with a mock object for testing"""
        mock_install = mock.Mock()
        monkeypatch.setattr(install, "install", mock_install)
        return mock_install

    @pytest.fixture
    def mock_test(self, monkeypatch):
        """Temporarily change test_helpers.test_one_genome with a mock object for testing"""
        mock_test = mock.Mock()
        monkeypatch.setattr(test_helpers, "test_one_genome", mock_test)
        return mock_test

    def test_dispatch_download_ftp_genome(self, mock_ref_gen_manager):
        controller = cli_controller.CliController()
        controller.dispatch_install(["GRCh37"])
        mock_ref_gen_manager.download_genome.assert_called_with("GRCh37")

    def test_dispatch_install_local_genome(self, mock_ref_gen_manager):
        controller = cli_controller.CliController()
        controller.dispatch_install(["yeast", "--local_genome", "/somewhere"])
        mock_ref_gen_manager.install_local_genome.assert_called_with(
            "yeast", "/somewhere"
        )

    genome_calls = [
        pytest.param(
            ["--test_genome", "GRCh37", "dog"],
            [
                mock.call(genome, volume=None, exome=exome, bed_file=bed_file)
                for genome in ("GRCh37", "dog")
                for exome, bed_file in test_helpers.available_test_modes(genome)
            ],
            id="two genomes",
        ),
        pytest.param(
            ["--test_genome", "GRCh37"],
            [
                mock.call("GRCh37", volume=None, exome=exome, bed_file=bed_file)
                for exome, bed_file in test_helpers.available_test_modes("GRCh37")
            ],
            id="one genome",
        ),
        pytest.param(["--test_genome", "unknown_genome"], [], id="no known genomes"),
        pytest.param(
            ["--test_genome", "all"],
            [
                mock.call(genome, volume=None, exome=exome, bed_file=bed_file)
                for genome in test_helpers.TEST_GENOMES
                for exome, bed_file in test_helpers.available_test_modes(genome)
            ],
            id="all genomes",
        ),
    ]

    @pytest.mark.parametrize("provided, expected", genome_calls)
    def test_dispatch_test_genome(self, mock_test, provided, expected):
        controller = cli_controller.CliController()
        controller.dispatch_test(provided)
        mock_test.assert_has_calls(expected)

    download_calls = [
        pytest.param(
            ["--download", "GRCh37", "dog"],
            [mock.call("GRCh37"), mock.call("dog")],
            id="two genomes",
        ),
        pytest.param(
            ["--download", "all"],
            [mock.call(genome) for genome in test_helpers.TEST_GENOMES],
            id="all genomes",
        ),
    ]

    @pytest.mark.parametrize("provided, expected", download_calls)
    def test_dispatch_test_download(self, mock_install, provided, expected):
        controller = cli_controller.CliController()
        controller.dispatch_test(provided)
        mock_install.assert_has_calls(expected)

    def test_dispatch_test_download_and_genome(self, mock_install, mock_test):
        provided = ["--download", "GRCh37", "--test_genome", "GRCh37"]
        controller = cli_controller.CliController()
        controller.dispatch_test(provided)
        mock_install.assert_has_calls([mock.call("GRCh37")])
        mock_test.assert_has_calls(
            [
                mock.call("GRCh37", volume=None, exome=exome, bed_file=bed_file)
                for exome, bed_file in test_helpers.available_test_modes("GRCh37")
            ]
        )
