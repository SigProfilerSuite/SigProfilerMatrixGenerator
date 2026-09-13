import hashlib

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import (
    ref_install,
    reference_genome_manager,
    save_tsb_192,
)


@pytest.mark.parametrize("mode", ["WGS", "WES", "BED", "WES_ZERO_LOWER_BOUND"])
@pytest.mark.parametrize(
    "genome",
    ["GRCh37", "GRCh37_havana", "GRCh38_havana", "mm10_havana", "GRCh38_TSBv2"],
)
@pytest.mark.parametrize("input_format", ["vcf", "txt", "maf", "genome"])
def test_tiny_reference_through_public_matrix_api(
    monkeypatch, tmp_path, mode, genome, input_format
):
    # Use a supported name only to exercise dispatch. This is a synthetic
    # 20-base fixture, not validation of the real distributed GRCh37 reference.
    # The proposed edition is registered only inside this synthetic test.
    monkeypatch.setitem(
        reference_genome_manager.REFERENCE_ASSEMBLIES, "GRCh38_TSBv2", "GRCh38"
    )
    assembly = reference_genome_manager.get_reference_assembly(genome)
    if genome != assembly:
        monkeypatch.setitem(
            reference_genome_manager.CHECKSUMS, assembly, {"2": "unused"}
        )
    volume = tmp_path / "volume"
    package = tmp_path / "package"
    sequence_dir = tmp_path / "sequence"
    transcript_dir = tmp_path / "transcripts"
    sequence_dir.mkdir()
    transcript_dir.mkdir()
    (sequence_dir / "1.txt").write_text("C" * 20)
    (transcript_dir / "combined.txt").write_text("g1 t1 1 1 4 10\n")
    save_tsb_192.save_tsb(sequence_dir, transcript_dir, volume / "tsb" / genome)
    encoded = (volume / "tsb" / genome / "1.txt").read_bytes()
    monkeypatch.setitem(
        reference_genome_manager.CHECKSUMS,
        genome,
        {
            "1": hashlib.md5(encoded).hexdigest(),
        },
    )
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    monkeypatch.setattr(
        ref_install.ReferenceDir,
        "_get_package_installation_folder",
        lambda self: package,
    )

    input_dir = tmp_path / "input_vcfs"
    input_dir.mkdir()
    vcf = (
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "1\t3\t.\tC\tA\t.\tPASS\t.\n"
        "1\t10\t.\tC\tA\t.\tPASS\t.\n"
    )
    if input_format == "vcf":
        (input_dir / "sample.vcf").write_text(vcf)
    else:
        rows = []
        for position in ("3", "10"):
            fields = ["."] * (16 if input_format == "maf" else 10)
            values = (
                {4: "1", 5: position, 6: position, 10: "C", 12: "A", 15: "sample"}
                if input_format == "maf"
                else {1: "sample", 5: "1", 6: position, 7: position, 8: "C", 9: "A"}
            )
            for index, value in values.items():
                fields[index] = value
            rows.append("\t".join(fields))
        (input_dir / f"sample.{input_format}").write_text(
            "header\n" + "\n".join(rows) + "\n"
        )
    bed = tmp_path / "panel.bed"
    bed.write_text("#chrom\tstart\tend\n1\t0\t5\n")
    exome_dir = package / "references" / "chromosomes" / "exome" / assembly
    exome_dir.mkdir(parents=True)
    zero_lower_bound = mode == "WES_ZERO_LOWER_BOUND"
    interval = "1\t1\t4\t+\tfixture\n" if zero_lower_bound else "1\t8\t12\t+\tfixture\n"
    (exome_dir / f"{assembly}_exome.interval_list").write_text(
        "@HD\tVN:1.0\tSO:coordinate\n" "@SQ\tSN:1\tLN:20\n" + interval
    )

    output = tmp_path / "output"
    matrices = api.SigProfilerMatrixGeneratorFunc(
        "fixture",
        genome,
        str(input_dir),
        plot=False,
        exome=mode.startswith("WES"),
        bed_file=str(bed) if mode == "BED" else None,
        chrom_based=False,
        tsb_stat=False,
        seqInfo=False,
        cushion=1 if zero_lower_bound else 0,
        volume=str(volume),
        output_directory=str(output),
    )
    expected_n = 0 if mode == "WES" else 1
    expected_u = 0 if mode == "BED" or zero_lower_bound else 1
    assert matrices["6144"].at["N:CC[C>A]CC", "sample"] == expected_n
    assert matrices["6144"].at["U:CC[C>A]CC", "sample"] == expected_u
    assert matrices["96"].at["C[C>A]C", "sample"] == expected_n + expected_u
    suffix = "exome" if mode.startswith("WES") else "all" if mode == "WGS" else "region"
    for context in ("96", "6144", "4608"):
        assert len(matrices[context]) == int(context)
        assert matrices[context].to_numpy().sum() == expected_n + expected_u
        saved = pd.read_csv(
            output / "SBS" / f"fixture.SBS{context}.{suffix}", sep="\t", index_col=0
        )
        pd.testing.assert_frame_equal(saved, matrices[context])
    log = next((output / "logs").glob("*.out")).read_text()
    assert f"Reference data ID: {genome}" in log
    assert f"Reference assembly: {assembly}" in log
    assert str(volume / "tsb" / genome) in log


def test_bed_filtering_keeps_first_record_and_roman_chromosomes(tmp_path):
    from SigProfilerMatrixGenerator.scripts import MutationMatrixGenerator as mmg

    bed = tmp_path / "regions.bed"
    bed.write_text("#chrom\tstart\tend\nchrI\t10\t11\n\nIII\t20\t21\n")
    assert mmg.BED_filtering(bed) == {"I": {10, 11}, "III": {20, 21}}
