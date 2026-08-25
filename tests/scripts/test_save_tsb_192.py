import pytest

from SigProfilerMatrixGenerator.scripts import save_tsb_192


def decode_states(tsb_bytes):
    states = ("N", "T", "U", "B")
    return "".join(
        states[value - 16 if value >= 16 else value // 4] for value in tsb_bytes
    )


def decode_bases(tsb_bytes):
    bases = "ACGT"
    return "".join(bases[value % 4] if value < 16 else "N" for value in tsb_bytes)


def make_reference(tmp_path, sequence="ACGTACGTACGT", chromosome="I"):
    chromosome_dir = tmp_path / "chromosomes"
    transcript_dir = tmp_path / "transcripts"
    output_dir = tmp_path / "tsb"
    chromosome_dir.mkdir()
    transcript_dir.mkdir()
    (chromosome_dir / f"{chromosome}.txt").write_text(sequence)
    return chromosome_dir, transcript_dir, output_dir


def test_save_tsb_handles_nested_opposite_strand_transcripts(tmp_path):
    chromosome_dir, transcript_dir, output_dir = make_reference(tmp_path)
    transcript_file = transcript_dir / "combined.txt"
    transcript_contents = (
        "gene2\ttx2\tI\t-1\t5\t10\n"
        "gene1\ttx1\tI\t1\t2\t8\n"
        "gene3\ttx3\tI\t1\t6\t7\n"
    )
    transcript_file.write_text(transcript_contents)

    save_tsb_192.save_tsb(
        f"{chromosome_dir}/", f"{transcript_dir}/", f"{output_dir}/"
    )

    observed = (output_dir / "I.txt").read_bytes()
    assert decode_bases(observed) == "ACGTACGTACGT"
    assert decode_states(observed) == "NUUUBBBBTTNN"
    assert transcript_file.read_text() == transcript_contents


def test_save_tsb_preserves_inclusive_one_base_transcript(tmp_path):
    chromosome_dir, transcript_dir, output_dir = make_reference(
        tmp_path, sequence="ACGTN"
    )
    (transcript_dir / "I_transcripts.txt").write_text(
        "gene1\ttx1\tI\t-1\t3\t3\n"
    )

    save_tsb_192.save_tsb(chromosome_dir, transcript_dir, output_dir)

    observed = (output_dir / "I.txt").read_bytes()
    assert decode_bases(observed) == "ACGTN"
    assert decode_states(observed) == "NNTNN"


def test_save_tsb_counts_overlapping_transcripts_on_the_same_strand(tmp_path):
    chromosome_dir, transcript_dir, output_dir = make_reference(tmp_path)
    (transcript_dir / "I_transcripts.txt").write_text(
        "gene1\ttx1\tI\t1\t2\t10\n"
        "gene2\ttx2\tI\t1\t4\t6\n"
        "gene3\ttx3\tI\t-1\t5\t8\n"
    )

    save_tsb_192.save_tsb(chromosome_dir, transcript_dir, output_dir)

    observed = (output_dir / "I.txt").read_bytes()
    assert decode_states(observed) == "NUUUBBBBUUNN"


def test_save_tsb_supports_headers_chr_aliases_and_unannotated_chromosomes(tmp_path):
    chromosome_dir, transcript_dir, output_dir = make_reference(
        tmp_path, sequence="ACGTN", chromosome="M"
    )
    (chromosome_dir / "II.txt").write_text("NACGT")
    (transcript_dir / "combined.txt").write_text(
        "Gene stable ID\tTranscript stable ID\tChromosome\tStrand\t"
        "Transcript start (bp)\tTranscript end (bp)\n"
        "gene1\ttx1\tchrM\t1\t1\t5\n"
    )

    save_tsb_192.save_tsb(chromosome_dir, transcript_dir, output_dir)

    assert decode_states((output_dir / "M.txt").read_bytes()) == "UUUUU"
    assert decode_states((output_dir / "II.txt").read_bytes()) == "NNNNN"
    assert decode_bases((output_dir / "M.txt").read_bytes()) == "ACGTN"


@pytest.mark.parametrize(
    ("transcript", "message"),
    [
        ("gene1\ttx1\tI\t0\t1\t2\n", "unsupported strand"),
        ("gene1\ttx1\tI\t1\t0\t2\n", "invalid interval"),
        ("gene1\ttx1\tI\t1\t2\t20\n", "exceeds chromosome length"),
        ("gene1\ttx1\tunknown\t1\t1\t2\n", "no matching chromosome"),
    ],
)
def test_save_tsb_rejects_invalid_transcripts(tmp_path, transcript, message):
    chromosome_dir, transcript_dir, output_dir = make_reference(tmp_path)
    (transcript_dir / "combined.txt").write_text(transcript)

    with pytest.raises(ValueError, match=message):
        save_tsb_192.save_tsb(chromosome_dir, transcript_dir, output_dir)


def test_save_tsb_does_not_replace_existing_output_after_failure(tmp_path):
    chromosome_dir, transcript_dir, output_dir = make_reference(tmp_path)
    output_dir.mkdir()
    existing_output = output_dir / "I.txt"
    existing_output.write_bytes(b"existing")
    (transcript_dir / "I_transcripts.txt").write_text(
        "gene1\ttx1\tI\t1\t2\t20\n"
    )

    with pytest.raises(ValueError, match="exceeds chromosome length"):
        save_tsb_192.save_tsb(chromosome_dir, transcript_dir, output_dir)

    assert existing_output.read_bytes() == b"existing"
    assert not (output_dir / "I.txt.tmp").exists()
