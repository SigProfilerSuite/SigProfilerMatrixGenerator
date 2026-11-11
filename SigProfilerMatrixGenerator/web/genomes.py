"""Report which reference genomes are installed, and install one."""

from __future__ import annotations

from SigProfilerMatrixGenerator.scripts import reference_genome_manager


def available_genomes() -> list[str]:
    """All genome names SigProfilerMatrixGenerator knows how to install."""
    return sorted(reference_genome_manager.CHECKSUMS.keys())


def installed_genomes(volume: str | None = None) -> list[str]:
    """Genomes whose chromosome files are all present under ``volume``.

    Presence only, not ReferenceGenomeManager.is_genome_installed(): that
    MD5-hashes every chromosome file, which takes seconds per genome and would
    stall every page load. A run still verifies the checksums before it
    starts (runjob.py), and reports a damaged install there.
    """
    manager = reference_genome_manager.ReferenceGenomeManager(volume)
    tsb_dir = manager.reference_dir.get_tsb_dir()
    return sorted(
        name
        for name, files in reference_genome_manager.CHECKSUMS.items()
        if all((tsb_dir / name / f"{chrom}.txt").is_file() for chrom in files)
    )


def status(volume: str | None = None) -> dict:
    return {"available": available_genomes(), "installed": installed_genomes(volume)}


def install(genome_name: str, volume: str | None = None, local_genome_dir: str | None = None) -> None:
    """Install ``genome_name``, raising reference_genome_manager.GenomeDownloadError on failure."""
    manager = reference_genome_manager.ReferenceGenomeManager(volume)
    if local_genome_dir:
        manager.install_local_genome(genome_name, local_genome_dir)
    else:
        manager.download_genome(genome_name)
