import pytest

from SigProfilerMatrixGenerator.scripts import MutationMatrixGenerator as mmg
from SigProfilerMatrixGenerator.scripts.transcript_reference import iter_transcripts


HEADER = "gene\ttranscript\tchromosome\tstrand\tstart\tend\tname\n"


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("header", [False, True])
@pytest.mark.parametrize("named", [False, True])
def test_gene_ranges_accept_supported_transcript_layouts(
    tmp_path, combined, header, named
):
    records = [
        ["g1", "t1", "1", "1", "10", "12", "G1"],
        ["g2", "t2", "1", "-1", "4", "6", "G2"],
        ["g1", "t3", "1", "1", "2", "3", "G1"],
        ["g3", "t4", "2", "-1", "1", "1", "G3"],
    ]
    files = {}
    for row in records:
        filename = "combined.txt" if combined else f"{row[2]}_transcripts.txt"
        files.setdefault(filename, HEADER if header else "")
        files[filename] += "\t".join(row if named else row[:6]) + "\n"
    for name, contents in files.items():
        (tmp_path / name).write_text(contents)
    (tmp_path / ".ignored").write_text("not a transcript")
    (tmp_path / "ignored_directory").mkdir()

    ranges, counts, names, per_sample, per_type = mmg.gene_range(tmp_path)
    labels = ["G1", "G2", "G3"] if named else ["g1", "g2", "g3"]
    assert ranges == {"1": [(2, 12, "1"), (4, 6, "-1")], "2": [(1, 1, "-1")]}
    assert names == {"1": labels[:2], "2": labels[2:]}
    assert counts[labels[0]]["T:C>A"] == 0
    assert counts[labels[0]]["samples"] == []
    assert per_sample == per_type == {name: {} for name in labels}
    for name, contents in files.items():
        assert (tmp_path / name).read_text() == contents


def test_headerless_single_transcript_and_blank_gene_name(tmp_path):
    (tmp_path / "combined.txt").write_text("g1\tt1\t1\t1\t4\t6\t\n")
    ranges, counts, names, *_ = mmg.gene_range(tmp_path, indel=True)
    assert ranges == {"1": [(4, 6, "1")]}
    assert names == {"1": ["g1"]}
    assert counts == {"g1": {"T": 0, "U": 0, "samples": []}}


def test_transcript_reader_accepts_whitespace_comments_and_crlf(tmp_path):
    (tmp_path / "combined.txt").write_text(
        "#comment\n\n" + HEADER + "g1 t1 1 -1 2 4\r\n"
    )
    (record,) = iter_transcripts(tmp_path)
    assert (record.chromosome, record.strand, record.start, record.end) == (
        "1",
        "-1",
        2,
        4,
    )


@pytest.mark.parametrize(
    "line,message",
    [
        ("g1 t1 1\n", "fewer than six"),
        ("g1 t1 1 1 not_a_number 5\n", "invalid coordinates"),
        ("g1 t1 1 0 1 5\n", "unsupported strand"),
        ("g1 t1 1 1 0 5\n", "invalid interval"),
        ("g1 t1 1 1 6 5\n", "invalid interval"),
    ],
)
def test_transcript_reader_reports_bad_records(tmp_path, line, message):
    (tmp_path / "combined.txt").write_text(line)
    with pytest.raises(ValueError, match=message):
        list(iter_transcripts(tmp_path))


def test_gene_ranges_reject_conflicting_strands(tmp_path):
    (tmp_path / "combined.txt").write_text("g1 t1 1 1 2 5\ng1 t2 1 -1 3 6\n")
    with pytest.raises(ValueError, match="conflicting strands"):
        mmg.gene_range(tmp_path)
