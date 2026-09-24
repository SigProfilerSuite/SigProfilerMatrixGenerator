import pandas as pd
import pytest

from SigProfilerMatrixGenerator import test_helpers as helpers


@pytest.mark.parametrize(
    "exome,bed,mode,suffix",
    [
        (False, False, "WGS", "all"),
        (True, False, "WES", "exome"),
        (False, True, "bed_file", "region"),
    ],
)
@pytest.mark.parametrize("correct", [True, False])
def test_genome_comparison_checks_the_selected_mode(
    monkeypatch, tmp_path, exome, bed, mode, suffix, correct
):
    solution = tmp_path / mode / "solutions" / "fixture"
    solution.mkdir(parents=True)
    expected = pd.DataFrame({"sample": [1]}, index=["A[C>A]A"])
    expected.to_csv(solution / f"test_example.SBS96.{suffix}", sep="\t")
    observed = expected if correct else expected * 99
    monkeypatch.setattr(helpers, "TEST_INPUT_DIR", str(tmp_path) + "/")
    monkeypatch.setattr(
        helpers.matGen,
        "SigProfilerMatrixGeneratorFunc",
        lambda *args, **kwargs: {"96": observed},
    )
    if correct:
        helpers.test_one_genome("fixture", None, exome=exome, bed_file=bed)
    else:
        with pytest.raises(AssertionError):
            helpers.test_one_genome("fixture", None, exome=exome, bed_file=bed)


def test_missing_required_solution_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Required solution file"):
        helpers.load_and_compare({"96": pd.DataFrame()}, tmp_path, bed_file=False)


def test_empty_generated_matrices_are_an_error(tmp_path):
    with pytest.raises(AssertionError, match="No matrices were generated"):
        helpers.load_and_compare({}, tmp_path)
