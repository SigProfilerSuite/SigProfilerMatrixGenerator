import itertools

import pandas as pd
import pytest

from SigProfilerMatrixGenerator.scripts import MutationMatrixGenerator as mmg
from SigProfilerMatrixGenerator.scripts import save_tsb_192


ENCODE = {
    state: dict(zip("ACGTN", codes))
    for state, codes in {
        "N": [0, 1, 2, 3, 16],
        "T": [4, 5, 6, 7, 17],
        "U": [8, 9, 10, 11, 18],
        "B": [12, 13, 14, 15, 19],
    }.items()
}
DECODE = {
    code: (state, base)
    for state, bases in ENCODE.items()
    for base, code in bases.items()
}
COMPLEMENT = str.maketrans("ACGT", "TGCA")
REVERSE_BIAS = {"N": "N", "T": "U", "U": "T", "B": "B"}


def empty_catalogue():
    channels = [
        f"{state}:{a}{b}[{mutation}]{c}{d}"
        for state, a, b, mutation, c, d in itertools.product(
            "NTUB",
            "ACGT",
            "ACGT",
            ("C>A", "C>G", "C>T", "T>A", "T>C", "T>G"),
            "ACGT",
            "ACGT",
        )
    ]
    return pd.DataFrame(0, index=channels, columns=["sample"], dtype="int64")


def catalogue_variant(tmp_path, position, ref, alt, matrix, skipped=False):
    result = mmg.catalogue_generator_single(
        lines=[["sample", "1", str(position), ref, alt]],
        chrom="1",
        mutation_dict={"6144": matrix},
        mutation_dinuc_pd_all=pd.DataFrame(),
        mutation_types_tsb_context=[],
        vcf_path=str(tmp_path) + "/",
        vcf_path_original=str(tmp_path) + "/",
        vcf_files=[],
        bed_file_path=None,
        chrom_path=str(tmp_path / "tsb") + "/",
        project="fixture",
        output_matrix=str(tmp_path) + "/",
        context="6144",
        exome=False,
        genome="fixture",
        ncbi_chrom={},
        functionFlag=True,
        bed=False,
        bed_ranges={},
        chrom_based=False,
        plot=False,
        tsb_ref=DECODE,
        transcript_path=str(tmp_path / "transcripts") + "/",
        tsb_stat=False,
        seqInfo=False,
        gs=False,
        log_file=str(tmp_path / "catalogue.log"),
    )
    assert result[1:4] == ((1, 0, 0) if skipped else (0, 1, 0))


@pytest.mark.parametrize("position", [0, 1, 2, 8, 9, 10])
def test_sbs_does_not_wrap_at_chromosome_edges(tmp_path, position):
    (tmp_path / "tsb").mkdir()
    (tmp_path / "tsb" / "1.txt").write_bytes(bytes([ENCODE["N"]["C"]]) * 9)
    matrix = empty_catalogue()
    catalogue_variant(tmp_path, position, "C", "A", matrix, skipped=True)
    assert matrix.to_numpy().sum() == 0


@pytest.mark.parametrize("state,neighbor", itertools.product("NTUB", repeat=2))
@pytest.mark.parametrize("reverse", [False, True])
def test_sbs_reads_mutated_base_state_not_neighbor(tmp_path, state, neighbor, reverse):
    sequence = "TTTTGTTTT" if reverse else "AAAACAAAA"
    encoded = bytearray(ENCODE["N"][base] for base in sequence)
    encoded[4] = ENCODE[state][sequence[4]]
    encoded[5] = ENCODE[neighbor][sequence[5]]
    (tmp_path / "tsb").mkdir()
    (tmp_path / "tsb" / "1.txt").write_bytes(encoded)
    matrix = empty_catalogue()
    catalogue_variant(tmp_path, 5, sequence[4], "T" if reverse else "A", matrix)
    bias = REVERSE_BIAS[state] if reverse else state
    assert matrix.at[f"{bias}:AA[C>A]AA", "sample"] == 1
    assert matrix["sample"].sum() == 1


def test_reference_build_to_sbs_matrices_at_all_fixture_positions(tmp_path):
    sequence = "AACGTCGATGCTACGTTGCAACGTACGTA"
    intervals = [(4, 20, "1"), (8, 10, "-1"), (9, 16, "-1"), (24, 24, "-1")]
    sequences = tmp_path / "sequences"
    transcripts = tmp_path / "transcripts"
    sequences.mkdir()
    transcripts.mkdir()
    (sequences / "1.txt").write_text(sequence)
    (transcripts / "combined.txt").write_text(
        "".join(
            f"g{i}\tt{i}\t1\t{strand}\t{start}\t{end}\n"
            for i, (start, end, strand) in enumerate(intervals)
        )
    )
    save_tsb_192.save_tsb(sequences, transcripts, tmp_path / "tsb")
    encoded = (tmp_path / "tsb" / "1.txt").read_bytes()
    assert "".join(DECODE[code][1] for code in encoded) == sequence

    observed, expected = empty_catalogue(), empty_catalogue()
    for position in range(3, len(sequence) - 1):
        strands = {
            strand for start, end, strand in intervals if start <= position <= end
        }
        state = (
            "B"
            if len(strands) == 2
            else "U" if "1" in strands else "T" if "-1" in strands else "N"
        )
        assert DECODE[encoded[position - 1]][0] == state
        ref = sequence[position - 1]
        alt = {"C": "A", "T": "G", "G": "T", "A": "C"}[ref]
        catalogue_variant(tmp_path, position, ref, alt, observed)
        context = sequence[position - 3 : position + 2]
        if ref in "AG":
            state = REVERSE_BIAS[state]
            ref, alt = ref.translate(COMPLEMENT), alt.translate(COMPLEMENT)
            context = context.translate(COMPLEMENT)[::-1]
        expected.at[f"{state}:{context[:2]}[{ref}>{alt}]{context[3:]}", "sample"] += 1
    pd.testing.assert_frame_equal(observed, expected)

    (tmp_path / "output").mkdir()
    matrices = mmg.matrix_generator(
        "6144",
        str(tmp_path / "output") + "/",
        "fixture",
        ["sample"],
        {"T": 0, "U": 1, "B": 2, "N": 3},
        {"6144": observed},
        False,
        list(observed.index),
        False,
        functionFlag=True,
        plot=False,
        tsb_stat=False,
    )
    expected96 = expected.groupby(expected.index.str[3:10]).sum()
    pd.testing.assert_frame_equal(
        matrices["96"].sort_index(),
        expected96.sort_index(),
        check_names=False,
    )
    for context in ("96", "6144", "4608"):
        assert len(matrices[context]) == int(context)
        assert matrices[context]["sample"].sum() == len(sequence) - 4
    # The existing SBS4608 convention splits B counts, giving the odd remainder to T.
    for channel in expected.index:
        state, mutation = channel.split(":", 1)
        if state == "B":
            continue
        count = expected.at[channel, "sample"]
        both = expected.at["B:" + mutation, "sample"]
        count += (both + 1) // 2 if state == "T" else both // 2 if state == "U" else 0
        assert matrices["4608"].at[channel, "sample"] == count
