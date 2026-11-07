import hashlib

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import ref_install, reference_genome_manager


def fixture_events():
    sequence = "CGTACGTCAG"
    rows = []
    for word, right, alternate, label89, label476 in [
        ("ATATAT", "ATGCTAC", "", "Del(2,8):U(1,2):R(2,4)", "Del(6,):U2:R(4,)"),
        ("ATATAT", "ATATGCTAC", "", "Del(2,):U(1,2):R(5,)", "Del(6,):U2:R(4,)"),
        ("", "TAGCG", "C", "A[Ins(C):R0]T", "A[Ins(C):R0]T"),
        ("T", "TTTTTTTTTAGC", "", "A[Del(T):R(8,)]A", "A[Del(T):R(9,)]A"),
        ("", "ATCAG", "ATG", "Ins(2,4):R0", "Ins(2,4):M"),
        ("ATCA", "CGTAC", "G", "Complex", "Complex(2,5)"),
    ]:
        sequence += "CGTACGTA"
        anchor = sequence[-1]
        rows.append(
            (len(sequence), anchor + word, anchor + alternate, label89, label476)
        )
        sequence += word + right + "CGTACGTGC"
    return sequence, rows


@pytest.mark.parametrize("genome", ["GRCh37", "GRCh38", "GRCh38_Legacy", "CHM13-T2T"])
@pytest.mark.parametrize("mode", ["WGS", "WES", "BED"])
@pytest.mark.parametrize("chrom_based", [False, True])
def test_public_api_matches_koh_expectations_and_preserves_legacy_outputs(
    tmp_path, monkeypatch, genome, mode, chrom_based
):
    sequence, rows = fixture_events()
    package = tmp_path / "package"
    volume = tmp_path / "volume"
    chromosome = volume / "tsb" / genome / "1.txt"
    chromosome.parent.mkdir(parents=True)
    data = bytes("ACGT".index(base) for base in sequence)
    chromosome.write_bytes(data)
    monkeypatch.setitem(
        reference_genome_manager.CHECKSUMS, genome, {"1": hashlib.md5(data).hexdigest()}
    )
    monkeypatch.setattr(
        ref_install.ReferenceDir,
        "_get_package_installation_folder",
        lambda self: package,
    )
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    source = tmp_path / "vcfs"
    source.mkdir()
    (source / "sample.vcf").write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        + "".join(
            f"1\t{position}\t.\t{ref}\t{alt}\t.\tPASS\t.\n"
            for position, ref, alt, _, _ in rows
        )
    )
    selected = list(range(len(rows))) if mode == "WGS" else [0, 2, 4]
    intervals = "".join(f"1\t{rows[i][0]}\t{rows[i][0]}\n" for i in selected)
    assembly = reference_genome_manager.get_reference_assembly(genome)
    exome_dir = package / "references" / "chromosomes" / "exome" / assembly
    exome_dir.mkdir(parents=True)
    (exome_dir / f"{assembly}_exome.interval_list").write_text(
        "@HD\tVN:1.0\n" + intervals
    )
    bed = tmp_path / "regions.bed"
    bed.write_text("#chrom\tstart\tend\n" + intervals)
    baseline, extended = tmp_path / "baseline", tmp_path / "extended"
    kwargs = dict(
        plot=False,
        seqInfo=False,
        cushion=0,
        volume=str(volume),
        exome=mode == "WES",
        bed_file=str(bed) if mode == "BED" else None,
        chrom_based=chrom_based,
    )
    old = api.SigProfilerMatrixGeneratorFunc(
        "fixture", genome, str(source), output_directory=str(baseline), **kwargs
    )
    new = api.SigProfilerMatrixGeneratorFunc(
        "fixture",
        genome,
        str(source),
        output_directory=str(extended),
        indel_contexts=("89", "476"),
        **kwargs,
    )
    for key in old:
        if isinstance(old[key], pd.DataFrame):
            pd.testing.assert_frame_equal(old[key], new[key])
        else:
            assert old[key] is new[key]
    for context, column in (("89", 3), ("476", 4)):
        matrix = new[f"ID{context}"]
        expected = matrix * 0
        for index in selected:
            expected.at[rows[index][column], "sample"] += 1
        pd.testing.assert_frame_equal(matrix, expected)
        assert len(matrix) == int(context)
        suffix = "all" if mode == "WGS" else "exome" if mode == "WES" else "region"
        saved = pd.read_csv(
            extended / "ID" / f"fixture.ID{context}.{suffix}", sep="\t", index_col=0
        )
        pd.testing.assert_frame_equal(saved, expected)
        if chrom_based:
            saved = pd.read_csv(
                extended / "ID" / f"fixture.ID{context}.{suffix}.chr1",
                sep="\t",
                index_col=0,
            )
            pd.testing.assert_frame_equal(saved, expected)
    for old_file in (baseline / "ID").iterdir():
        assert old_file.read_bytes() == (extended / "ID" / old_file.name).read_bytes()


def test_cli_forwards_context_selection(monkeypatch):
    from SigProfilerMatrixGenerator.controllers import cli_controller

    calls = []
    monkeypatch.setattr(
        cli_controller.mg,
        "SigProfilerMatrixGeneratorFunc",
        lambda **kwargs: calls.append(kwargs),
    )
    cli_controller.CliController().dispatch_matrix_generator(
        ["test", "CHM13-T2T", "/inputs", "--indel_contexts", "89", "476"]
    )
    assert calls[0]["indel_contexts"] == ["89", "476"]
