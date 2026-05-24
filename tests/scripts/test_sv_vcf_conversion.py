import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VCF_TO_BEDPE_PATH = (
    REPO_ROOT / "SigProfilerMatrixGenerator" / "scripts" / "vcfToBedpe.py"
)
SPEC = importlib.util.spec_from_file_location("vcfToBedpe", VCF_TO_BEDPE_PATH)
vcf_to_bedpe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vcf_to_bedpe)


def test_purple_gridss_bnd_vcf_classifies_events(tmp_path):
    vcf_path = (
        REPO_ROOT
        / "SigProfilerMatrixGenerator"
        / "references"
        / "SV"
        / "example_input"
        / "VCF"
        / "COLO829v003T.purple.sv.vcf"
    )

    bedpe, unclassified = vcf_to_bedpe.vcfToBedpe(str(vcf_path), str(tmp_path))

    assert len(bedpe) == 109
    assert len(unclassified) == 38
    assert set(bedpe["svclass"]).issubset(
        {"deletion", "translocation", "tandem-duplication", "inversion"}
    )
    assert bedpe["sample"].unique().tolist() == ["COLO829v003T"]
    assert bedpe["svclass"].value_counts().to_dict() == {
        "tandem-duplication": 53,
        "inversion": 28,
        "translocation": 22,
        "deletion": 6,
    }
