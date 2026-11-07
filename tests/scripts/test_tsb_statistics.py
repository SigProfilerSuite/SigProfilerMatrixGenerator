"""Exercise optional strand-bias statistics without an installed genome."""

import hashlib
import itertools

import numpy as np
import pandas as pd
import pytest
from scipy.stats import binomtest

from SigProfilerMatrixGenerator.scripts import MutationMatrixGenerator as mmg
from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as api
from SigProfilerMatrixGenerator.scripts import ref_install, reference_genome_manager


REPORT_COLUMNS = ["Sample", "MutationType", "Enrichment", "PValue", "QValue"]
SBS_CONTEXTS = ("6144", "384", "1536", "96", "6", "24", "4608", "288", "18")


def synthetic_catalogue():
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
    catalogue = pd.DataFrame(
        0, index=channels, columns=["second", "first", "empty"], dtype="int64"
    )
    # The two pentamers collapse to the same SBS384 and SBS24 channel.
    for label, counts in {
        "T:AA[C>A]AA": (10, 80),
        "U:AA[C>A]AA": (50, 40),
        "T:CA[C>A]AC": (20, 120),
        "U:CA[C>A]AC": (10, 10),
        "U:AA[C>G]AA": (30, 60),
        "T:AA[T>A]AA": (60, 100),
        "T:AA[T>C]AA": (10, 10),
        "U:AA[T>C]AA": (30, 30),
        "B:AA[C>A]AA": (7, 9),
        "N:AA[C>A]AA": (11, 13),
    }.items():
        catalogue.loc[label, ["second", "first"]] = counts
    return catalogue.iloc[::-1]


def generate(catalogue, destination, tsb_stat):
    destination.mkdir()
    return mmg.matrix_generator(
        "6144",
        str(destination) + "/",
        "fixture",
        list(catalogue.columns),
        {"T": 0, "U": 1, "B": 2, "N": 3},
        {"6144": catalogue.copy()},
        False,
        list(catalogue.index),
        False,
        functionFlag=True,
        plot=False,
        tsb_stat=tsb_stat,
    )


def expected_report(catalogue, context):
    counts = {}
    for channel, row in catalogue.iterrows():
        if channel[0] not in "TU":
            continue
        mutation = (
            channel[2:]
            if context == "6144"
            else (
                channel[3:10]
                if context == "384"
                else channel.split("[", 1)[1].split("]", 1)[0]
            )
        )
        counts.setdefault(mutation, {"T": {}, "U": {}})
        for sample in catalogue.columns:
            strand = counts[mutation][channel[0]]
            strand[sample] = strand.get(sample, 0) + int(row[sample])
    rows = []
    for sample in catalogue.columns:
        sample_rows = []
        for mutation in sorted(counts):
            transcribed = counts[mutation]["T"][sample]
            untranscribed = counts[mutation]["U"][sample]
            ratio = (
                transcribed / untranscribed
                if untranscribed
                else np.inf if transcribed else np.nan
            )
            total = transcribed + untranscribed
            pvalue = binomtest(transcribed, total).pvalue if total else 1.0
            sample_rows.append((sample, mutation, ratio, pvalue))
        pvalues = np.array([row[3] for row in sample_rows])
        order = np.argsort(pvalues)
        adjusted = pvalues[order] * len(pvalues) / np.arange(1, len(pvalues) + 1)
        adjusted = np.minimum(np.minimum.accumulate(adjusted[::-1])[::-1], 1.0)
        qvalues = np.empty_like(adjusted)
        qvalues[order] = adjusted
        rows.extend((*row, qvalue) for row, qvalue in zip(sample_rows, qvalues))
    return pd.DataFrame(rows, columns=REPORT_COLUMNS)


def read_report(path, header=False):
    return pd.read_csv(
        path, sep="\t", header=0 if header else None, names=REPORT_COLUMNS
    )


def assert_statistics_equal(actual, expected):
    index = ["Sample", "MutationType"]
    actual = actual.set_index(index).sort_index()
    expected = expected.set_index(index).sort_index()
    pd.testing.assert_index_equal(actual.index, expected.index)
    for column in ("Enrichment", "PValue", "QValue"):
        np.testing.assert_allclose(
            actual[column], expected[column], rtol=1e-12, atol=0, equal_nan=True
        )


@pytest.fixture
def statistics_run(tmp_path):
    catalogue = synthetic_catalogue()
    destination = tmp_path / "statistics"
    matrices = generate(catalogue, destination, tsb_stat=True)
    return catalogue, destination, matrices


@pytest.mark.parametrize("context", ["6144", "384", "24"])
def test_tsb_reports_match_each_context_counts(statistics_run, context):
    catalogue, destination, _ = statistics_run
    report = read_report(
        destination / "TSB" / f"strandBiasTest_{context}.txt", header=context == "6144"
    )
    assert_statistics_equal(report, expected_report(catalogue, context))
    empty = report.loc[report.Sample == "empty"]
    assert empty.Enrichment.isna().all()
    assert (empty.PValue == 1).all()
    assert (empty.QValue == 1).all()
    if context != "6144":
        mutation = "C>A" if context == "24" else "A[C>A]A"
        ratios = (
            report.loc[report.MutationType == mutation].set_index("Sample").Enrichment
        )
        assert ratios["first"] == 4.0
        assert ratios["second"] == 0.5


def test_significant_tsb_results_match_context_specific_statistics(statistics_run):
    catalogue, destination, _ = statistics_run
    expected = pd.concat(
        [expected_report(catalogue, context) for context in ("6144", "384", "24")]
    )
    expected = expected.loc[expected.QValue < 0.01]
    actual = read_report(destination / "TSB" / "significantResults_strandBiasTest.txt")
    assert not expected.empty
    assert {"C>A", "A[C>A]A"}.issubset(set(expected.MutationType))
    assert_statistics_equal(actual, expected)


def test_tsb_statistics_preserve_all_sbs_matrices(statistics_run, tmp_path):
    catalogue, destination, with_statistics = statistics_run
    baseline = tmp_path / "baseline"
    without_statistics = generate(catalogue, baseline, tsb_stat=False)
    for context in SBS_CONTEXTS:
        pd.testing.assert_frame_equal(
            with_statistics[context], without_statistics[context]
        )
        filename = f"fixture.SBS{context}.all"
        assert (destination / "SBS" / filename).read_bytes() == (
            baseline / "SBS" / filename
        ).read_bytes()
    assert not (baseline / "TSB").exists()


@pytest.mark.parametrize("genome", ["GRCh37", "CHM13-T2T"])
def test_public_api_tsb_statistics_preserve_sbs_and_indel_outputs(
    tmp_path, monkeypatch, genome
):
    encoded = bytearray()
    events = []
    for sequence, state, count in (
        ("AAAACAAAA", "T", 8),
        ("AAAACAAAA", "U", 4),
        ("TTCACACTT", "T", 12),
        ("TTCACACTT", "U", 1),
    ):
        for _ in range(count):
            block = bytearray("ACGT".index(base) for base in sequence)
            block[4] += 4 if state == "T" else 8
            events.append((len(encoded) + 5, "C", "A"))
            encoded.extend(block)
    events.extend(((5, "CA", "C"), (5, "C", "CT")))
    volume = tmp_path / "volume"
    chromosome = volume / "tsb" / genome / "1.txt"
    chromosome.parent.mkdir(parents=True)
    chromosome.write_bytes(encoded)
    monkeypatch.setitem(
        reference_genome_manager.CHECKSUMS,
        genome,
        {"1": hashlib.md5(encoded).hexdigest()},
    )
    monkeypatch.setattr(
        ref_install.ReferenceDir,
        "_get_package_installation_folder",
        lambda self: tmp_path / "package",
    )
    monkeypatch.delenv("SIGPROFILERMATRIXGENERATOR_VOLUME", raising=False)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "sample.vcf").write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        + "".join(
            f"1\t{position}\t.\t{ref}\t{alt}\t.\tPASS\t.\n"
            for position, ref, alt in sorted(events)
        )
    )
    results = []
    for enabled in (False, True):
        results.append(
            api.SigProfilerMatrixGeneratorFunc(
                "fixture",
                genome,
                str(inputs),
                volume=str(volume),
                output_directory=str(tmp_path / str(enabled)),
                plot=False,
                seqInfo=False,
                tsb_stat=enabled,
                indel_contexts=("89", "476"),
            )
        )
    baseline, statistics = results
    for context, expected in baseline.items():
        if isinstance(expected, pd.DataFrame):
            pd.testing.assert_frame_equal(statistics[context], expected)
        else:
            assert statistics[context] is expected
    assert statistics["96"].to_numpy().sum() == 25
    assert statistics["ID89"].to_numpy().sum() == 2
    assert statistics["ID476"].to_numpy().sum() == 2
    for context, mutation in (("24", "C>A"), ("384", "A[C>A]A")):
        report = read_report(
            tmp_path / "True" / "TSB" / f"strandBiasTest_{context}.txt"
        )
        assert report.loc[report.MutationType == mutation, "Enrichment"].item() == 4.0
    for directory in ("SBS", "DBS", "ID"):
        for path in (tmp_path / "False" / directory).glob("*"):
            assert (
                path.read_bytes()
                == (tmp_path / "True" / directory / path.name).read_bytes()
            )
