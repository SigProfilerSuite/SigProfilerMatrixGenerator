"""Generate and check a tiny CHM13 whole-genome example."""
import argparse
from pathlib import Path

import pandas as pd
from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matgen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", required=True, help="Installed reference directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = root / "my_project_output"
    matrices = matgen.SigProfilerMatrixGeneratorFunc(
        "my_project", "CHM13-T2T", str(root / "mixed_variant_inputs"),
        volume=str(Path(args.volume).resolve()), output_directory=str(output),
        plot=False, seqInfo=False, cushion=0,
    )
    assert matrices is not None, "No matrices generated"
    assert matrices["96"].at["A[C>A]G", "sbs"] == 1
    assert matrices["96"]["sbs"].sum() == 1
    assert matrices["6144"].at["T:GA[C>A]GT", "sbs"] == 1
    dbs = pd.read_csv(output / "DBS/my_project.DBS78.all", sep="\t", index_col=0)
    indels = pd.read_csv(output / "ID/my_project.ID83.all", sep="\t", index_col=0)
    assert dbs.at["CC>TT", "dbs"] == 1 and dbs["dbs"].sum() == 1
    assert indels.at["1:Del:C:0", "indel"] == 1
    assert indels.at["1:Ins:T:0", "indel"] == 1
    assert indels["indel"].sum() == 2
    print("PASS: SBS sample = 1 substitution; DBS sample = 1 double substitution;")
    print("      indel sample = 1 deletion + 1 insertion; strand channel matches.")
    print(f"Matrices: {output}")


if __name__ == "__main__":
    main()
