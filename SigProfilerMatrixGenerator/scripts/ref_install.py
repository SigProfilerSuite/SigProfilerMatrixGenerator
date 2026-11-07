import os
import pathlib
from importlib import resources
from typing import Optional, Union

import SigProfilerMatrixGenerator


def reference_dir(
    secondary_chromosome_install_dir: Optional[Union[str, pathlib.Path]] = None
) -> "ReferenceDir":
    """Small constructor for ReferenceDir"""
    # Check the environmental variable first
    env_var_name = "SIGPROFILERMATRIXGENERATOR_VOLUME"
    env_directory = os.getenv(env_var_name)

    if env_directory:
        install_dir = pathlib.Path(env_directory)
    elif secondary_chromosome_install_dir is not None:
        install_dir = pathlib.Path(secondary_chromosome_install_dir)
    else:
        install_dir = None

    result = ReferenceDir(secondary_chromosome_install_dir=install_dir)
    return result


class ReferenceDir:
    """The directory where the reference genomes are installed"""

    _default_chromosome_dir = pathlib.Path("references", "chromosomes")

    def __init__(self, secondary_chromosome_install_dir: Optional[pathlib.Path] = None):
        self._secondary_chromosome_install_dir = secondary_chromosome_install_dir

    @property
    def path(self) -> pathlib.Path:
        """Where references that cannot be installed are"""
        root_path = self._get_package_installation_folder()
        return root_path.resolve()

    def get_fasta_dir(self) -> pathlib.Path:
        result = self.get_chromosomes_dir() / "fasta"
        return result

    def get_tsb_dir(self) -> pathlib.Path:
        result = self.get_chromosomes_dir() / "tsb"
        return result

    def get_exome_dir(self) -> pathlib.Path:
        """Exome interval lists ship inside the package, so they are anchored on
        ``path`` rather than on the (possibly relocated) chromosomes directory."""
        result = self.path / self._default_chromosome_dir / "exome"
        return result

    def get_exome_interval_list(self, genome: str) -> pathlib.Path:
        result = self.get_exome_dir() / genome / f"{genome}_exome.interval_list"
        return result

    def get_chromosomes_dir(self) -> pathlib.Path:
        if self._secondary_chromosome_install_dir is None:
            root_dir = self.path / self._default_chromosome_dir
        else:
            root_dir = self._secondary_chromosome_install_dir.resolve()
        result = root_dir
        return result

    def _get_package_installation_folder(self):
        return resources.files(SigProfilerMatrixGenerator)
