import pathlib

import pytest

import SigProfilerMatrixGenerator
from SigProfilerMatrixGenerator.scripts import ref_install


class TestReferenceDir:
    @pytest.fixture
    def package_reference_dir(self):
        return pathlib.Path(SigProfilerMatrixGenerator.__file__).parent.resolve()

    @pytest.fixture
    def default_fasta_dir(self, package_reference_dir):
        result = package_reference_dir / "references" / "chromosomes" / "fasta"
        return result

    @pytest.fixture
    def default_tsb_dir(self, package_reference_dir):
        result = package_reference_dir / "references" / "chromosomes" / "tsb"
        return result

    def test_path_no_secondary_chromosome_install_dir(self, package_reference_dir):
        refdir = ref_install.reference_dir()
        observed = refdir.path
        assert package_reference_dir == observed
        # check path is absolute
        assert observed == observed.resolve()

    def test_path_not_affected_by_secondary_chromosome_install_dir(
        self, package_reference_dir
    ):
        refdir = ref_install.reference_dir(
            secondary_chromosome_install_dir="/somewhere"
        )
        observed = refdir.path
        assert observed == package_reference_dir

    def test_get_fasta_dir_default(self, default_fasta_dir):
        refdir = ref_install.reference_dir()
        observed = refdir.get_fasta_dir()
        assert observed == default_fasta_dir

    get_fasta_dir_data = [
        pytest.param(
            "/somewhere", pathlib.Path("/somewhere/fasta"), id="absolute,string"
        ),
        pytest.param(
            "relative/to/here",
            pathlib.Path.cwd() / "relative/to/here/fasta",
            id="relative,string",
        ),
        pytest.param(
            pathlib.Path("relative/to/here"),
            pathlib.Path.cwd() / "relative/to/here/fasta",
            id="relative,path",
        ),
    ]

    @pytest.mark.parametrize("provided,expected", get_fasta_dir_data)
    def test_get_fasta_dir(self, provided, expected):
        refdir = ref_install.reference_dir(secondary_chromosome_install_dir=provided)
        observed = refdir.get_fasta_dir()
        assert observed == expected

    def test_get_tsb_dir_default(self, default_tsb_dir):
        refdir = ref_install.reference_dir()
        observed = refdir.get_tsb_dir()
        assert observed == default_tsb_dir

    def test_tsb_dir_with_env_variable(self, monkeypatch):
        test_dir = "/somewhere/else"
        monkeypatch.setenv("SIGPROFILERMATRIXGENERATOR_VOLUME", test_dir)

        refdir = ref_install.reference_dir()
        observed_tsb_dir = refdir.get_tsb_dir()
        assert observed_tsb_dir == pathlib.Path(test_dir, "tsb").resolve()
