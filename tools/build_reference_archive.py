#!/usr/bin/env python3
"""Build a deterministic ``.tar.gz`` reference-genome archive."""

import argparse
import gzip
import hashlib
from pathlib import Path
import tarfile


def _metadata(name, *, directory=False, size=0):
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    info.mode = 0o755 if directory else 0o644
    info.size = size
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    return info


def _md5(path):
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_reference_directory(
    source_directory, expected_checksums, expected_genome=None
):
    """Require the exact registered chromosome set and payload checksums."""
    source_directory = Path(source_directory)
    if expected_genome and source_directory.name != expected_genome:
        raise ValueError(
            f"Reference directory must be named {expected_genome!r}, "
            f"not {source_directory.name!r}"
        )
    observed = {path.name: path for path in source_directory.iterdir() if path.is_file()}
    expected = {f"{chromosome}.txt" for chromosome in expected_checksums}
    if set(observed) != expected:
        raise ValueError(
            "Reference chromosome files do not match the registered manifest: "
            f"missing={sorted(expected - set(observed))}, "
            f"unexpected={sorted(set(observed) - expected)}"
        )
    mismatches = {}
    for chromosome, checksum in expected_checksums.items():
        observed_checksum = _md5(observed[f"{chromosome}.txt"])
        if observed_checksum != checksum:
            mismatches[chromosome] = (observed_checksum, checksum)
    if mismatches:
        raise ValueError(f"Reference checksum mismatch: {mismatches}")


def build_archive(
    source_directory, output_path, expected_checksums=None, expected_genome=None
):
    source_directory = Path(source_directory)
    output_path = Path(output_path)
    if not source_directory.is_dir():
        raise ValueError(f"Reference directory does not exist: {source_directory}")
    if expected_genome and output_path.name != f"{expected_genome}.tar.gz":
        raise ValueError(
            f"Reference archive must be named {expected_genome}.tar.gz, "
            f"not {output_path.name}"
        )
    if expected_checksums is not None:
        validate_reference_directory(
            source_directory, expected_checksums, expected_genome
        )
    files = sorted(path for path in source_directory.iterdir() if path.is_file())
    if not files:
        raise ValueError(f"Reference directory contains no files: {source_directory}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        with temporary_path.open("wb") as raw, gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0
        ) as compressed, tarfile.open(
            fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT
        ) as archive:
            root = source_directory.name
            archive.addfile(_metadata(f"{root}/", directory=True))
            for path in files:
                archive_name = f"{root}/{path.name}"
                with path.open("rb") as contents:
                    archive.addfile(
                        _metadata(archive_name, size=path.stat().st_size), contents
                    )
        temporary_path.replace(output_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_directory")
    parser.add_argument("output_path")
    parser.add_argument(
        "--genome",
        help="validate the payload against this registered reference before archiving",
    )
    args = parser.parse_args()
    expected_checksums = None
    if args.genome:
        from SigProfilerMatrixGenerator.scripts.reference_genome_manager import (
            CHECKSUMS,
        )

        try:
            expected_checksums = CHECKSUMS[args.genome]
        except KeyError:
            parser.error(f"unknown registered genome: {args.genome}")
    build_archive(
        args.source_directory,
        args.output_path,
        expected_checksums,
        expected_genome=args.genome,
    )


if __name__ == "__main__":
    main()
