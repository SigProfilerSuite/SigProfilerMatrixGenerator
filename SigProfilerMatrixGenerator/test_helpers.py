import os
import warnings

import pandas as pd
from pandas.testing import assert_frame_equal

from SigProfilerMatrixGenerator import install as genInstall
from SigProfilerMatrixGenerator.scripts import (
    SigProfilerMatrixGeneratorFunc as matGen,
    ref_install,
)

reference_dir = ref_install.reference_dir()
TEST_INPUT_DIR = str(reference_dir.path / "references/tests/") + "/"
BED_FILE_DIR = str(reference_dir.get_exome_dir()) + "/"
FILE_PREF = "test_example"
TEST_GENOMES = [
    "c_elegans",
    "CHM13-T2T",
    "dog",
    "GRCh37",
    "GRCh38",
    "mm9",
    "mm10",
    "mm39",
    "rn6",
    "yeast",
]


def load_and_compare(matrices, solution_dir, exome=False, bed_file=True):
    for key in matrices:
        # Determine the solution file path based on the exome flag
        if exome:
            solution_file = os.path.join(
                solution_dir, FILE_PREF + ".SBS" + key + ".exome"
            )
        elif bed_file:
            solution_file = os.path.join(
                solution_dir, FILE_PREF + ".SBS" + key + ".region"
            )
        else:
            solution_file = os.path.join(
                solution_dir, FILE_PREF + ".SBS" + key + ".all"
            )

        # Load the solution file and compare with the generated matrix
        if os.path.exists(solution_file):
            solution_df = pd.read_csv(solution_file, sep="\t", index_col=0)
            assert_frame_equal(matrices[key], solution_df)
        else:
            # Nothing to compare against: warn so that a genome without solution
            # files is not mistaken for a passing test
            warnings.warn(
                "No solution file found, skipping comparison: " + solution_file
            )


def test_one_genome(genome, volume, exome=False, bed_file=True):
    if exome:
        matrices = matGen.SigProfilerMatrixGeneratorFunc(
            FILE_PREF,
            genome,
            os.path.join(TEST_INPUT_DIR + "WES", genome),
            plot=False,
            exome=True,
            bed_file=None,
            chrom_based=False,
            tsb_stat=False,
            seqInfo=False,
            cushion=100,
            volume=volume,
        )
    elif bed_file:
        matrices = matGen.SigProfilerMatrixGeneratorFunc(
            FILE_PREF,
            genome,
            os.path.join(TEST_INPUT_DIR + "bed_file", genome),
            plot=False,
            exome=False,
            bed_file=str(reference_dir.get_exome_interval_list(genome)),
            chrom_based=False,
            tsb_stat=False,
            seqInfo=False,
            cushion=100,
            volume=volume,
        )

    else:
        matrices = matGen.SigProfilerMatrixGeneratorFunc(
            FILE_PREF,
            genome,
            os.path.join(TEST_INPUT_DIR + "WGS", genome),
            plot=False,
            exome=False,
            bed_file=None,
            chrom_based=False,
            tsb_stat=False,
            seqInfo=False,
            cushion=100,
            volume=volume,
        )

    # load the results from the solution directory and compare them to the dataframes in matrices
    if exome:
        solution_dir = os.path.join(TEST_INPUT_DIR, f"WES/solutions/{genome}/")
    elif bed_file:
        solution_dir = os.path.join(TEST_INPUT_DIR, f"bed_file/solutions/{genome}/")
    else:
        solution_dir = os.path.join(TEST_INPUT_DIR, f"WGS/solutions/{genome}/")
    load_and_compare(matrices, solution_dir)


def install_genomes(genome_install_list):
    if genome_install_list is None:
        return
    # download all the genomes specified by user
    for tmp_genome in genome_install_list:
        if tmp_genome == "all":
            for genome in TEST_GENOMES:
                genInstall.install(genome)
        elif tmp_genome not in TEST_GENOMES:
            print(
                "Warning: Download for",
                tmp_genome,
                "is skipped because it is not a valid test genome.",
            )
        else:
            genInstall.install(tmp_genome)


def test_genomes(test_genome, volume=None):
    # Check for all test, otherwise test specific genomes
    if test_genome is None:
        print("No genomes specified for testing. Please specify a genome or all.")
    elif test_genome[0] == "all":
        for genome in TEST_GENOMES:
            test_one_genome(genome, volume=volume)
    else:
        for genome in test_genome:
            if genome not in TEST_GENOMES:
                print(
                    genome
                    + " is not a valid test genome. Please choose from: "
                    + str(TEST_GENOMES)
                )
                continue
            try:
                test_one_genome(genome, volume=volume)
                print("Completed test for " + genome)
            except Exception as e:
                assert False, "Test failed for " + genome + ":\n" + str(e)


def test_all_genomes(volume=None):
    for genome in TEST_GENOMES:
        try:
            test_one_genome(genome, volume)
            print(f"Completed test for {genome}\n")
        except Exception as e:
            print(f"Test failed for {genome}:\n{str(e)}\n")
