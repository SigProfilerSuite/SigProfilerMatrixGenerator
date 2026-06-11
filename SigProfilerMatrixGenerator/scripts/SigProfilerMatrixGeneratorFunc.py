#!/usr/bin/env python3

# Author: Erik Bergstrom

# Contact: ebergstr@eng.ucsd.edu

from __future__ import print_function

import datetime
import itertools
import os
import platform
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

import matplotlib as plt
import numpy as np
import pandas as pd
import scipy
import sigProfilerPlotting as sigPlt
import statsmodels

import SigProfilerMatrixGenerator as sig
from SigProfilerMatrixGenerator import install
from SigProfilerMatrixGenerator.scripts import (
    convert_input_to_simple_files as convertIn,
    MutationMatrixGenerator as matGen,
    ref_install,
    reference_genome_manager,
)


def perm(n, seq):
    """
    Generates a list of all available permutations of n-mers.

    Parameters:
                       n  -> length of the desired permutation string
                     seq  -> list of all possible string values

    Returns:
              permus  -> list of all available permutations
    """
    permus = []
    for p in itertools.product(seq, repeat=n):
        permus.append("".join(p))
    return permus


def SigProfilerMatrixGeneratorFunc(
    project,
    reference_genome,
    path_to_input_files,
    exome=False,
    bed_file=None,
    chrom_based=False,
    plot=False,
    tsb_stat=False,
    seqInfo=True,
    cushion=100,
    gs=False,
    volume=None,
    output_directory=None,
):
    """
    Allows for the import of the sigProfilerMatrixGenerator.py function. Returns a dictionary
    with each context serving as the first level of keys.

    Parameters:
                              project  -> unique name given to the current samples
             reference_genome  -> reference genome
      path_to_input_files  -> path where the input vcf files are located.
                                    exome  -> flag to use only the exome or not
                             bed_file  -> BED file that contains a list of ranges to be used in generating the matrices
                      chrom_based  -> flag to create the matrices on a per chromosome basis
                                     plot  -> flag to generate the plots for each context
                             tsb_stat  -> performs a transcriptional strand bias test for the 24, 384, and 6144 contexts. The output is
                                                      saved into the output/TSB directory
                                       gs  -> flag that performs a gene strand bias test

    Returns:
                             matrices  -> dictionary (nested) of the matrices for each context

            example:
                    matrices = {'96': {'PD1001a':{'A[A>C]A':23,
                                                                             'A[A>G]A':10,...},
                                                      'PD1202a':{'A[A>C]A':23,
                                                                             'A[A>G]A':10,...},...},
                                            '192':{'PD1001a':{'T:A[A>C]A':23,
                                                                             'T:A[A>G]A':10,...},
                                                      'PD1202a':{'T:A[A>C]A':23,
                                                                             'T:A[A>G]A':10,...},...},...}
    """

    # verify chromosome file installation for supported genomes
    # 1. get list of all files that were downloaded
    # Terminates the code if the genome reference files have not been created/installed

    reference_dir = ref_install.reference_dir(secondary_chromosome_install_dir=volume)
    ref_dir = str(reference_dir.path)

    # 2. Check if genome is installed (if not print checksum report)
    genome_manager = reference_genome_manager.ReferenceGenomeManager(volume)
    if not genome_manager.is_genome_installed(reference_genome):
        genome_manager.print_genome_checksum_verification_report(reference_genome)
        raise Exception(
            "The specified genome "
            + reference_genome
            + " has not been installed\nPlease refer to the SigProfilerMatrixGenerator README for installation instructions:\n\thttps://github.com/SigProfilerSuite/SigProfilerMatrixGenerator"
        )

    # Instantiates all of the required variables and references
    if not os.path.exists(path_to_input_files):
        print(
            "The given project path does not appear to exist. Please check that the specified path exists before proceeding...\n\t"
            + path_to_input_files
        )
        return
    if gs:
        print(
            "The Gene Strand Bias is not yet supported! Continuing with the matrix generation."
        )
        gs = False
    functionFlag = True
    bed = False
    bed_ranges = None
    limited_indel = True
    exome = exome
    plot = plot

    # Instantiates the final output matrix
    matrices = {
        "96": None,
        "1536": None,
        "384": None,
        "6144": None,
        "DINUC": None,
        "6": None,
        "24": None,
        "INDEL": None,
    }

    # Provides a chromosome conversion from NCBI notation
    ncbi_chrom = {
        "NC_000067.6": "1",
        "NC_000068.7": "2",
        "NC_000069.6": "3",
        "NC_000070.6": "4",
        "NC_000071.6": "5",
        "NC_000072.6": "6",
        "NC_000073.6": "7",
        "NC_000074.6": "8",
        "NC_000075.6": "9",
        "NC_000076.6": "10",
        "NC_000077.6": "11",
        "NC_000078.6": "12",
        "NC_000079.6": "13",
        "NC_000080.6": "14",
        "NC_000081.6": "15",
        "NC_000082.6": "16",
        "NC_000083.6": "17",
        "NC_000084.6": "18",
        "NC_000085.6": "19",
        "NC_000086.7": "X",
        "NC_000087.7": "Y",
        "82503188|ref|NC_007605.1|": "gi_82503188_ref_NC_007605",
    }

    # Provides the reference file conversion from binary to base information
    tsb_ref = {
        0: ["N", "A"],
        1: ["N", "C"],
        2: ["N", "G"],
        3: ["N", "T"],
        4: ["T", "A"],
        5: ["T", "C"],
        6: ["T", "G"],
        7: ["T", "T"],
        8: ["U", "A"],
        9: ["U", "C"],
        10: ["U", "G"],
        11: ["U", "T"],
        12: ["B", "A"],
        13: ["B", "C"],
        14: ["B", "G"],
        15: ["B", "T"],
        16: ["N", "N"],
        17: ["T", "N"],
        18: ["U", "N"],
        19: ["B", "N"],
    }

    bias_sort = {"T": 0, "U": 1, "N": 3, "B": 2, "Q": 4}
    tsb = ["T", "U", "N", "B"]
    tsb_I = ["T", "U", "N", "B", "Q"]
    bases = ["A", "C", "G", "T"]
    mutation_types = [
        "CC>AA",
        "CC>AG",
        "CC>AT",
        "CC>GA",
        "CC>GG",
        "CC>GT",
        "CC>TA",
        "CC>TG",
        "CC>TT",
        "CT>AA",
        "CT>AC",
        "CT>AG",
        "CT>GA",
        "CT>GC",
        "CT>GG",
        "CT>TA",
        "CT>TC",
        "CT>TG",
        "TC>AA",
        "TC>AG",
        "TC>AT",
        "TC>CA",
        "TC>CG",
        "TC>CT",
        "TC>GA",
        "TC>GG",
        "TC>GT",
        "TT>AA",
        "TT>AC",
        "TT>AG",
        "TT>CA",
        "TT>CC",
        "TT>CG",
        "TT>GA",
        "TT>GC",
        "TT>GG",
    ]

    mutation_types_non_tsb = [
        "AC>CA",
        "AC>CG",
        "AC>CT",
        "AC>GA",
        "AC>GG",
        "AC>GT",
        "AC>TA",
        "AC>TG",
        "AC>TT",
        "AT>CA",
        "AT>CC",
        "AT>CG",
        "AT>GA",
        "AT>GC",
        "AT>TA",
        "CG>AT",
        "CG>GC",
        "CG>GT",
        "CG>TA",
        "CG>TC",
        "CG>TT",
        "GC>AA",
        "GC>AG",
        "GC>AT",
        "GC>CA",
        "GC>CG",
        "GC>TA",
        "TA>AT",
        "TA>CG",
        "TA>CT",
        "TA>GC",
        "TA>GG",
        "TA>GT",
        "TG>AA",
        "TG>AC",
        "TG>AT",
        "TG>CA",
        "TG>CC",
        "TG>CT",
        "TG>GA",
        "TG>GC",
        "TG>GT",
    ]

    indels_seq_types = [  # Single-sequences
        "C",
        "T",
        # Di-sequences
        "AC",
        "AT",
        "CA",
        "CC",
        "CG",
        "CT",
        "GC",
        "TA",
        "TC",
        "TT",
        # Tri-sequences
        "ACC",
        "ACT",
        "ATC",
        "ATT",
        "CAC",
        "CAT",
        "CCA",
        "CCC",
        "CCG",
        "CCT",
        "CGC",
        "CGT",
        "CTA",
        "CTC",
        "CTG",
        "CTT",
        "GCC",
        "GCT",
        "GTC",
        "GTT",
        "TAC",
        "TAT",
        "TCA",
        "TCC",
        "TCG",
        "TCT",
        "TGC",
        "TGT",
        "TTA",
        "TTC",
        "TTG",
        "TTT",
        # Tetra-sequences
        "AACC",
        "AACT",
        "AATC",
        "AATT",
        "ACAC",
        "ACAT",
        "ACCA",
        "ACCC",
        "ACCG",
        "ACCT",
        "ACGC",
        "ACGT",
        "ACTA",
        "ACTC",
        "ACTG",
        "ACTT",
        "AGCC",
        "AGCT",
        "AGTC",
        "AGTT",
        "ATAC",
        "ATAT",
        "ATCA",
        "ATCC",
        "ATCG",
        "ATCT",
        "ATGC",
        "ATGT",
        "ATTA",
        "ATTC",
        "ATTG",
        "ATTT",
        "CAAC",
        "CAAT",
        "CACA",
        "CACC",
        "CACG",
        "CACT",
        "CAGC",
        "CAGT",
        "CATA",
        "CATC",
        "CATG",
        "CATT",
        "CCAA",
        "CCAC",
        "CCAG",
        "CCAT",
        "CCCA",
        "CCCC",
        "CCCG",
        "CCCT",
        "CCGA",
        "CCGC",
        "CCGG",
        "CCGT",
        "CCTA",
        "CCTC",
        "CCTG",
        "CCTT",
        "CGAC",
        "CGAT",
        "CGCA",
        "CGCC",
        "CGCG",
        "CGCT",
        "CGGC",
        "CGTA",
        "CGTC",
        "CGTG",
        "CGTT",
        "CTAA",
        "CTAC",
        "CTAG",
        "CTAT",
        "CTCA",
        "CTCC",
        "CTCG",
        "CTCT",
        "CTGA",
        "CTGC",
        "CTGG",
        "CTGT",
        "CTTA",
        "CTTC",
        "CTTG",
        "CTTT",
        "GACC",
        "GATC",
        "GCAC",
        "GCCA",
        "GCCC",
        "GCCG",
        "GCCT",
        "GCGC",
        "GCTA",
        "GCTC",
        "GCTG",
        "GCTT",
        "GGCC",
        "GGTC",
        "GTAC",
        "GTCA",
        "GTCC",
        "GTCG",
        "GTCT",
        "GTGC",
        "GTTA",
        "GTTC",
        "GTTG",
        "GTTT",
        "TAAC",
        "TACA",
        "TACC",
        "TACG",
        "TACT",
        "TAGC",
        "TATA",
        "TATC",
        "TATG",
        "TATT",
        "TCAA",
        "TCAC",
        "TCAG",
        "TCAT",
        "TCCA",
        "TCCC",
        "TCCG",
        "TCCT",
        "TCGA",
        "TCGC",
        "TCGG",
        "TCGT",
        "TCTA",
        "TCTC",
        "TCTG",
        "TCTT",
        "TGAC",
        "TGCA",
        "TGCC",
        "TGCG",
        "TGCT",
        "TGTA",
        "TGTC",
        "TGTG",
        "TGTT",
        "TTAA",
        "TTAC",
        "TTAG",
        "TTAT",
        "TTCA",
        "TTCC",
        "TTCG",
        "TTCT",
        "TTGA",
        "TTGC",
        "TTGG",
        "TTGT",
        "TTTA",
        "TTTC",
        "TTTG",
        "TTTT",
        # Penta-sequences
        "AACCC",
        "AACCT",
        "AACTC",
        "AACTT",
        "AATCC",
        "AATCT",
        "AATTC",
        "AATTT",
        "ACACC",
        "ACACT",
        "ACATC",
        "ACATT",
        "ACCAC",
        "ACCAT",
        "ACCCA",
        "ACCCC",
        "ACCCG",
        "ACCCT",
        "ACCGC",
        "ACCGT",
        "ACCTA",
        "ACCTC",
        "ACCTG",
        "ACCTT",
        "ACGCC",
        "ACGCT",
        "ACGTC",
        "ACGTT",
        "ACTAC",
        "ACTAT",
        "ACTCA",
        "ACTCC",
        "ACTCG",
        "ACTCT",
        "ACTGC",
        "ACTGT",
        "ACTTA",
        "ACTTC",
        "ACTTG",
        "ACTTT",
        "AGCCC",
        "AGCCT",
        "AGCTC",
        "AGCTT",
        "AGTCC",
        "AGTCT",
        "AGTTC",
        "AGTTT",
        "ATACC",
        "ATACT",
        "ATATC",
        "ATATT",
        "ATCAC",
        "ATCAT",
        "ATCCA",
        "ATCCC",
        "ATCCG",
        "ATCCT",
        "ATCGC",
        "ATCGT",
        "ATCTA",
        "ATCTC",
        "ATCTG",
        "ATCTT",
        "ATGCC",
        "ATGCT",
        "ATGTC",
        "ATGTT",
        "ATTAC",
        "ATTAT",
        "ATTCA",
        "ATTCC",
        "ATTCG",
        "ATTCT",
        "ATTGC",
        "ATTGT",
        "ATTTA",
        "ATTTC",
        "ATTTG",
        "ATTTT",
        "CAACC",
        "CAACT",
        "CAATC",
        "CAATT",
        "CACAC",
        "CACAT",
        "CACCA",
        "CACCC",
        "CACCG",
        "CACCT",
        "CACGC",
        "CACGT",
        "CACTA",
        "CACTC",
        "CACTG",
        "CACTT",
        "CAGCC",
        "CAGCT",
        "CAGTC",
        "CAGTT",
        "CATAC",
        "CATAT",
        "CATCA",
        "CATCC",
        "CATCG",
        "CATCT",
        "CATGC",
        "CATGT",
        "CATTA",
        "CATTC",
        "CATTG",
        "CATTT",
        "CCAAC",
        "CCAAT",
        "CCACA",
        "CCACC",
        "CCACG",
        "CCACT",
        "CCAGC",
        "CCAGT",
        "CCATA",
        "CCATC",
        "CCATG",
        "CCATT",
        "CCCAA",
        "CCCAC",
        "CCCAG",
        "CCCAT",
        "CCCCA",
        "CCCCC",
        "CCCCG",
        "CCCCT",
        "CCCGA",
        "CCCGC",
        "CCCGG",
        "CCCGT",
        "CCCTA",
        "CCCTC",
        "CCCTG",
        "CCCTT",
        "CCGAC",
        "CCGAT",
        "CCGCA",
        "CCGCC",
        "CCGCG",
        "CCGCT",
        "CCGGC",
        "CCGGT",
        "CCGTA",
        "CCGTC",
        "CCGTG",
        "CCGTT",
        "CCTAA",
        "CCTAC",
        "CCTAG",
        "CCTAT",
        "CCTCA",
        "CCTCC",
        "CCTCG",
        "CCTCT",
        "CCTGA",
        "CCTGC",
        "CCTGG",
        "CCTGT",
        "CCTTA",
        "CCTTC",
        "CCTTG",
        "CCTTT",
        "CGACC",
        "CGACT",
        "CGATC",
        "CGATT",
        "CGCAC",
        "CGCAT",
        "CGCCA",
        "CGCCC",
        "CGCCG",
        "CGCCT",
        "CGCGC",
        "CGCGT",
        "CGCTA",
        "CGCTC",
        "CGCTG",
        "CGCTT",
        "CGGCC",
        "CGGCT",
        "CGGTC",
        "CGGTT",
        "CGTAC",
        "CGTAT",
        "CGTCA",
        "CGTCC",
        "CGTCG",
        "CGTCT",
        "CGTGC",
        "CGTGT",
        "CGTTA",
        "CGTTC",
        "CGTTG",
        "CGTTT",
        "CTAAC",
        "CTAAT",
        "CTACA",
        "CTACC",
        "CTACG",
        "CTACT",
        "CTAGC",
        "CTAGT",
        "CTATA",
        "CTATC",
        "CTATG",
        "CTATT",
        "CTCAA",
        "CTCAC",
        "CTCAG",
        "CTCAT",
        "CTCCA",
        "CTCCC",
        "CTCCG",
        "CTCCT",
        "CTCGA",
        "CTCGC",
        "CTCGG",
        "CTCGT",
        "CTCTA",
        "CTCTC",
        "CTCTG",
        "CTCTT",
        "CTGAC",
        "CTGAT",
        "CTGCA",
        "CTGCC",
        "CTGCG",
        "CTGCT",
        "CTGGC",
        "CTGGT",
        "CTGTA",
        "CTGTC",
        "CTGTG",
        "CTGTT",
        "CTTAA",
        "CTTAC",
        "CTTAG",
        "CTTAT",
        "CTTCA",
        "CTTCC",
        "CTTCG",
        "CTTCT",
        "CTTGA",
        "CTTGC",
        "CTTGG",
        "CTTGT",
        "CTTTA",
        "CTTTC",
        "CTTTG",
        "CTTTT",
        "GACCC",
        "GACCT",
        "GACTC",
        "GACTT",
        "GATCC",
        "GATCT",
        "GATTC",
        "GATTT",
        "GCACC",
        "GCACT",
        "GCATC",
        "GCATT",
        "GCCAC",
        "GCCAT",
        "GCCCA",
        "GCCCC",
        "GCCCG",
        "GCCCT",
        "GCCGC",
        "GCCGT",
        "GCCTA",
        "GCCTC",
        "GCCTG",
        "GCCTT",
        "GCGCC",
        "GCGCT",
        "GCGTC",
        "GCGTT",
        "GCTAC",
        "GCTAT",
        "GCTCA",
        "GCTCC",
        "GCTCG",
        "GCTCT",
        "GCTGC",
        "GCTGT",
        "GCTTA",
        "GCTTC",
        "GCTTG",
        "GCTTT",
        "GGCCC",
        "GGCCT",
        "GGCTC",
        "GGCTT",
        "GGTCC",
        "GGTCT",
        "GGTTC",
        "GGTTT",
        "GTACC",
        "GTACT",
        "GTATC",
        "GTATT",
        "GTCAC",
        "GTCAT",
        "GTCCA",
        "GTCCC",
        "GTCCG",
        "GTCCT",
        "GTCGC",
        "GTCGT",
        "GTCTA",
        "GTCTC",
        "GTCTG",
        "GTCTT",
        "GTGCC",
        "GTGCT",
        "GTGTC",
        "GTGTT",
        "GTTAC",
        "GTTAT",
        "GTTCA",
        "GTTCC",
        "GTTCG",
        "GTTCT",
        "GTTGC",
        "GTTGT",
        "GTTTA",
        "GTTTC",
        "GTTTG",
        "GTTTT",
        "TAACC",
        "TAACT",
        "TAATC",
        "TAATT",
        "TACAC",
        "TACAT",
        "TACCA",
        "TACCC",
        "TACCG",
        "TACCT",
        "TACGC",
        "TACGT",
        "TACTA",
        "TACTC",
        "TACTG",
        "TACTT",
        "TAGCC",
        "TAGCT",
        "TAGTC",
        "TAGTT",
        "TATAC",
        "TATAT",
        "TATCA",
        "TATCC",
        "TATCG",
        "TATCT",
        "TATGC",
        "TATGT",
        "TATTA",
        "TATTC",
        "TATTG",
        "TATTT",
        "TCAAC",
        "TCAAT",
        "TCACA",
        "TCACC",
        "TCACG",
        "TCACT",
        "TCAGC",
        "TCAGT",
        "TCATA",
        "TCATC",
        "TCATG",
        "TCATT",
        "TCCAA",
        "TCCAC",
        "TCCAG",
        "TCCAT",
        "TCCCA",
        "TCCCC",
        "TCCCG",
        "TCCCT",
        "TCCGA",
        "TCCGC",
        "TCCGG",
        "TCCGT",
        "TCCTA",
        "TCCTC",
        "TCCTG",
        "TCCTT",
        "TCGAC",
        "TCGAT",
        "TCGCA",
        "TCGCC",
        "TCGCG",
        "TCGCT",
        "TCGGC",
        "TCGGT",
        "TCGTA",
        "TCGTC",
        "TCGTG",
        "TCGTT",
        "TCTAA",
        "TCTAC",
        "TCTAG",
        "TCTAT",
        "TCTCA",
        "TCTCC",
        "TCTCG",
        "TCTCT",
        "TCTGA",
        "TCTGC",
        "TCTGG",
        "TCTGT",
        "TCTTA",
        "TCTTC",
        "TCTTG",
        "TCTTT",
        "TGACC",
        "TGACT",
        "TGATC",
        "TGATT",
        "TGCAC",
        "TGCAT",
        "TGCCA",
        "TGCCC",
        "TGCCG",
        "TGCCT",
        "TGCGC",
        "TGCGT",
        "TGCTA",
        "TGCTC",
        "TGCTG",
        "TGCTT",
        "TGGCC",
        "TGGCT",
        "TGGTC",
        "TGGTT",
        "TGTAC",
        "TGTAT",
        "TGTCA",
        "TGTCC",
        "TGTCG",
        "TGTCT",
        "TGTGC",
        "TGTGT",
        "TGTTA",
        "TGTTC",
        "TGTTG",
        "TGTTT",
        "TTAAC",
        "TTAAT",
        "TTACA",
        "TTACC",
        "TTACG",
        "TTACT",
        "TTAGC",
        "TTAGT",
        "TTATA",
        "TTATC",
        "TTATG",
        "TTATT",
        "TTCAA",
        "TTCAC",
        "TTCAG",
        "TTCAT",
        "TTCCA",
        "TTCCC",
        "TTCCG",
        "TTCCT",
        "TTCGA",
        "TTCGC",
        "TTCGG",
        "TTCGT",
        "TTCTA",
        "TTCTC",
        "TTCTG",
        "TTCTT",
        "TTGAC",
        "TTGAT",
        "TTGCA",
        "TTGCC",
        "TTGCG",
        "TTGCT",
        "TTGGC",
        "TTGGT",
        "TTGTA",
        "TTGTC",
        "TTGTG",
        "TTGTT",
        "TTTAA",
        "TTTAC",
        "TTTAG",
        "TTTAT",
        "TTTCA",
        "TTTCC",
        "TTTCG",
        "TTTCT",
        "TTTGA",
        "TTTGC",
        "TTTGG",
        "TTTGT",
        "TTTTA",
        "TTTTC",
        "TTTTG",
        "TTTTT",
    ]

    # Pre-fills the mutation types variable
    size = 5
    mut_types_initial = perm(size, "ACGT")
    mut_types = []
    for tsbs in tsb:
        for mut in mut_types_initial:
            current_base = mut[int(size / 2)]
            if current_base == "C" or current_base == "T":
                for base in bases:
                    if base != current_base:
                        mut_types.append(
                            tsbs
                            + ":"
                            + mut[0 : int(size / 2)]
                            + "["
                            + current_base
                            + ">"
                            + base
                            + "]"
                            + mut[int(size / 2) + 1 :]
                        )

    # Organizes all of the mutation types for DINUCs
    mutation_types_tsb_context = []
    for base in bases:
        for mut in mutation_types:
            for base2 in bases:
                for base3 in tsb:
                    mutation_types_tsb_context.append(
                        "".join([base3, ":", base, "[", mut, "]", base2])
                    )

    for base in bases:
        for mut in mutation_types_non_tsb:
            for base2 in bases:
                mutation_types_tsb_context.append(
                    "".join(["Q:", base, "[", mut, "]", base2])
                )

    indel_types_tsb = []
    indel_types_simple = []
    indel_complete = []

    indel_cat = ["Del", "Ins"]

    indel_types = [
        "1:Del:C:0",
        "1:Del:C:1",
        "1:Del:C:2",
        "1:Del:C:3",
        "1:Del:C:4",
        "1:Del:C:5",
        "1:Del:T:0",
        "1:Del:T:1",
        "1:Del:T:2",
        "1:Del:T:3",
        "1:Del:T:4",
        "1:Del:T:5",
        "1:Ins:C:0",
        "1:Ins:C:1",
        "1:Ins:C:2",
        "1:Ins:C:3",
        "1:Ins:C:4",
        "1:Ins:C:5",
        "1:Ins:T:0",
        "1:Ins:T:1",
        "1:Ins:T:2",
        "1:Ins:T:3",
        "1:Ins:T:4",
        "1:Ins:T:5",
        # >1bp INDELS
        "2:Del:R:0",
        "2:Del:R:1",
        "2:Del:R:2",
        "2:Del:R:3",
        "2:Del:R:4",
        "2:Del:R:5",
        "3:Del:R:0",
        "3:Del:R:1",
        "3:Del:R:2",
        "3:Del:R:3",
        "3:Del:R:4",
        "3:Del:R:5",
        "4:Del:R:0",
        "4:Del:R:1",
        "4:Del:R:2",
        "4:Del:R:3",
        "4:Del:R:4",
        "4:Del:R:5",
        "5:Del:R:0",
        "5:Del:R:1",
        "5:Del:R:2",
        "5:Del:R:3",
        "5:Del:R:4",
        "5:Del:R:5",
        "2:Ins:R:0",
        "2:Ins:R:1",
        "2:Ins:R:2",
        "2:Ins:R:3",
        "2:Ins:R:4",
        "2:Ins:R:5",
        "3:Ins:R:0",
        "3:Ins:R:1",
        "3:Ins:R:2",
        "3:Ins:R:3",
        "3:Ins:R:4",
        "3:Ins:R:5",
        "4:Ins:R:0",
        "4:Ins:R:1",
        "4:Ins:R:2",
        "4:Ins:R:3",
        "4:Ins:R:4",
        "4:Ins:R:5",
        "5:Ins:R:0",
        "5:Ins:R:1",
        "5:Ins:R:2",
        "5:Ins:R:3",
        "5:Ins:R:4",
        "5:Ins:R:5",
        # MicroHomology INDELS
        "2:Del:M:1",
        "3:Del:M:1",
        "3:Del:M:2",
        "4:Del:M:1",
        "4:Del:M:2",
        "4:Del:M:3",
        "5:Del:M:1",
        "5:Del:M:2",
        "5:Del:M:3",
        "5:Del:M:4",
        "5:Del:M:5",
        "2:Ins:M:1",
        "3:Ins:M:1",
        "3:Ins:M:2",
        "4:Ins:M:1",
        "4:Ins:M:2",
        "4:Ins:M:3",
        "5:Ins:M:1",
        "5:Ins:M:2",
        "5:Ins:M:3",
        "5:Ins:M:4",
        "5:Ins:M:5",
        "complex",
        "non_matching",
    ]

    for indels in indel_types[:-13]:
        for tsbs in tsb_I:
            indel_types_tsb.append(tsbs + ":" + indels)

    for indels in indels_seq_types:
        repeat = str(len(indels))
        for id_cat in indel_cat:
            for l in range(0, 6, 1):
                indel_complete.append(":".join([repeat, id_cat, indels, str(l)]))
    for id_cat in indel_cat:
        for i in range(0, 6, 1):
            indel_complete.append(":".join(["5", id_cat, "5", str(i)]))

    indel_types_simple = indel_types[:24]
    indel_types_simple.append("long_Del")
    indel_types_simple.append("long_Ins")
    indel_types_simple.append("MH")
    indel_types_simple.append("complex")
    # Instantiates the initial contexts to generate matrices for
    contexts = ["6144"]

    chrom_path = str(reference_dir.get_tsb_dir() / reference_genome) + "/"
    if "havana" in reference_genome:
        reference_genome = reference_genome.split("_")[0]
    transcript_path = (
        ref_dir + "/references/chromosomes/transcripts/" + reference_genome + "/"
    )

    # Terminates the code if the genome reference files have not been created/installed
    if not os.path.exists(chrom_path):
        raise Exception(
            "The specified genome "
            + reference_genome
            + " has not been installed\nPlease refer to the SigProfilerMatrixGenerator README for installation instructions:\n\thttps://github.com/SigProfilerSuite/SigProfilerMatrixGenerator"
        )

    # Set base directory (for input/ and output/) based on user-provided output_directory if given
    base_path = output_directory if output_directory else path_to_input_files
    if not base_path.endswith("/"):
        base_path += "/"

    # Ensure input path and create if needed
    vcf_path = os.path.join(base_path, "input/")
    vcf_path_original = vcf_path

    # Copy all regular files from input source into vcf_path if vcf_path is missing or empty
    if not os.path.exists(vcf_path) or len(os.listdir(vcf_path)) < 1:
        os.makedirs(vcf_path, exist_ok=True)
        if not path_to_input_files.endswith("/"):
            path_to_input_files += "/"
        for filename in os.listdir(path_to_input_files):
            src = os.path.join(path_to_input_files, filename)
            dst = os.path.join(vcf_path, filename)
            if os.path.isfile(src):
                shutil.copy(src, dst)

    # Define the output matrix path, allowing override via `output_directory`
    if output_directory:
        if output_directory[-1] != "/":
            output_directory += "/"
        output_matrix = output_directory
    else:
        output_matrix = base_path + "output/"

    os.makedirs(output_matrix, exist_ok=True)


    # Organizes the error and log files
    time_stamp = datetime.date.today()
    output_log_path = output_matrix + "logs/"
    if not os.path.exists(output_log_path):
        os.makedirs(output_log_path)
    error_file = (
        output_log_path
        + "SigProfilerMatrixGenerator_"
        + project
        + "_"
        + reference_genome
        + str(time_stamp)
        + ".err"
    )
    log_file = (
        output_log_path
        + "SigProfilerMatrixGenerator_"
        + project
        + "_"
        + reference_genome
        + str(time_stamp)
        + ".out"
    )

    if os.path.exists(error_file):
        os.remove(error_file)
    if os.path.exists(log_file):
        os.remove(log_file)
    tempErr = sys.stderr
    sys.stderr = open(error_file, "w")
    log_out = open(log_file, "w")
    log_out.write("THIS FILE CONTAINS THE METADATA ABOUT SYSTEM AND RUNTIME\n\n\n")
    log_out.write("-------System Info-------\n")
    log_out.write(
        "Operating System Name: "
        + platform.uname()[0]
        + "\n"
        + "Nodename: "
        + platform.uname()[1]
        + "\n"
        + "Release: "
        + platform.uname()[2]
        + "\n"
        + "Version: "
        + platform.uname()[3]
        + "\n"
    )
    log_out.write("\n-------Python and Package Versions------- \n")
    log_out.write(
        "Python Version: "
        + str(platform.sys.version_info.major)
        + "."
        + str(platform.sys.version_info.minor)
        + "."
        + str(platform.sys.version_info.micro)
        + "\n"
    )
    log_out.write("SigProfilerMatrixGenerator Version: " + sig.__version__ + "\n")
    log_out.write("SigProfilerPlotting version: " + sigPlt.__version__ + "\n")
    log_out.write("matplotlib version: " + plt.__version__ + "\n")
    log_out.write("statsmodels version: " + statsmodels.__version__ + "\n")
    log_out.write("scipy version: " + scipy.__version__ + "\n")
    log_out.write("pandas version: " + pd.__version__ + "\n")
    log_out.write("numpy version: " + np.__version__ + "\n")

    log_out.write("\n-------Vital Parameters Used for the execution -------\n")
    log_out.write(
        "Project: {}\nGenome: {}\nInput File Path: {}\nexome: {}\nbed_file: {}\nchrom_based: {}\nplot: {}\ntsb_stat: {}\nseqInfo: {}\n".format(
            project,
            reference_genome,
            path_to_input_files,
            str(exome),
            str(bed_file),
            str(chrom_based),
            str(plot),
            str(tsb_stat),
            str(seqInfo),
        )
    )
    log_out.write("\n-------Date and Time Data------- \n")
    tic = datetime.datetime.now()
    log_out.write(
        "Date and Clock time when the execution started: " + str(tic) + "\n\n\n"
    )
    log_out.write("-------Runtime Checkpoints------- \n")
    log_out.close()

    # Gathers all of the vcf files:
    vcf_files_temp = os.listdir(vcf_path)
    vcf_files = []
    first_extenstion = True
    for file in vcf_files_temp:
        # Skips hidden files
        if file[0:3] == ".DS" or file[0:2] == "__":
            pass
        else:
            vcf_files.append(file)

    # Creates a temporary folder for sorting and generating the matrices
    file_name = vcf_files[0].split(".")
    file_extension = file_name[-1]
    unique_folder = project + "_" + str(uuid.uuid4())
    output_path = output_matrix + "temp/" + unique_folder + "/"
    if os.path.exists(output_path):
        shutil.rmtree(output_path)
    os.makedirs(output_path)

    skipped_muts = 0
    # Converts the input files to standard text in the temporary folder
    if file_extension == "genome":
        snv, indel, skipped, samples = convertIn.convertTxt(
            project, vcf_path, reference_genome, output_path
        )
    else:
        if file_extension == "txt":
            snv, indel, skipped, samples = convertIn.convertTxt(
                project, vcf_path, reference_genome, output_path, ncbi_chrom, log_file
            )
        elif file_extension == "vcf":
            snv, indel, skipped, samples = convertIn.convertVCF(
                project, vcf_path, reference_genome, output_path, ncbi_chrom, log_file
            )
        elif file_extension == "maf":
            snv, indel, skipped, samples = convertIn.convertMAF(
                project, vcf_path, reference_genome, output_path, ncbi_chrom, log_file
            )
        elif file_extension == "tsv":
            print("ICGC format (.tsv) is no longer supported. Please convert your file to .vcf, .maf, or .txt.")
            raise ValueError(
                "ICGC format (.tsv) is no longer supported. Please convert your file to .vcf, .maf, or .txt."
            )
        else:
            print("File format not supported")

    samples = sorted(samples)
    skipped_muts += skipped

    # Instantiates variables for final output statistics
    analyzed_muts = [0, 0, 0]

    sample_count_high = 0

    # Begins matrix generation for all possible contexts
    for i in range(0, 2, 1):
        if i == 0 and snv:
            mutation_pd = {}
            mutation_pd["6144"] = pd.DataFrame(0, index=mut_types, columns=samples)
            mutation_dinuc_pd_all = pd.DataFrame(
                0, index=mutation_types_tsb_context, columns=samples
            )

            output_path_snv = output_path + "SNV/"
            vcf_files = os.listdir(output_path_snv)
            vcf_path = output_path_snv
            print(
                "Starting matrix generation for SNVs and DINUCs...", end="", flush=True
            )
            start = time.time()

        # Skips SNVs if none are present
        elif i == 0 and not snv:
            continue
        elif i == 1 and indel:
            mutation_ID = {}
            mutation_ID["ID"] = pd.DataFrame(0, index=indel_types, columns=samples)
            mutation_ID["simple"] = pd.DataFrame(
                0, index=indel_types_simple, columns=samples
            )
            mutation_ID["tsb"] = pd.DataFrame(0, index=indel_types_tsb, columns=samples)
            mutation_ID["complete"] = pd.DataFrame(
                0, index=indel_complete, columns=samples
            )

            contexts = ["INDEL"]
            output_path_indel = output_path + "INDEL/"
            vcf_files = os.listdir(output_path_indel)
            vcf_path = output_path_indel
            print("Starting matrix generation for INDELs...", end="", flush=True)
            start = time.time()

        # Skips INDELs if none are present and deletes the temp folder
        elif i == 1 and not indel:
            shutil.rmtree(output_matrix + "temp/")
            continue

        # Removes hidden files generated in macos
        if ".DS_Store" in vcf_files:
            vcf_files.remove(".DS_Store")

        # Generates the bed regions if a bed file was provided
        if bed_file != None:
            bed = True
            bed_file_path = bed_file
            bed_ranges = matGen.BED_filtering(bed_file_path)
        else:
            bed_file_path = None

        # Sorts files based on chromosome, sample, and start position
        if not chrom_based:
            chrom_start = None

        # initialize dinuc_mat to None
        dinuc_mat = None
        if i != 1:
            for file in vcf_files:
                if reference_genome.lower() != "ebv":
                    chrom = file.split("_")[0]
                else:
                    chrom = "gi_82503188_ref_NC_007605"
                if not os.path.exists(chrom_path + chrom + ".txt"):
                    continue
                with open(vcf_path + file) as f:
                    lines = [line.strip().split() for line in f]
                lines = sorted(lines, key=lambda x: (x[0], int(x[2])))

                context = "6144"
                (
                    mutation_pd,
                    skipped_mut,
                    total,
                    total_DINUC,
                    mutation_dinuc_pd_all,
                ) = matGen.catalogue_generator_single(
                    lines,
                    chrom,
                    mutation_pd,
                    mutation_dinuc_pd_all,
                    mutation_types_tsb_context,
                    vcf_path,
                    vcf_path_original,
                    vcf_files,
                    bed_file_path,
                    chrom_path,
                    project,
                    output_matrix,
                    context,
                    exome,
                    reference_genome,
                    ncbi_chrom,
                    functionFlag,
                    bed,
                    bed_ranges,
                    chrom_based,
                    plot,
                    tsb_ref,
                    transcript_path,
                    tsb_stat,
                    seqInfo,
                    gs,
                    log_file,
                    volume=volume,
                )

                if chrom_based and not exome and not bed:
                    matrices = matGen.matrix_generator(
                        context,
                        output_matrix,
                        project,
                        samples,
                        bias_sort,
                        mutation_pd,
                        exome,
                        mut_types,
                        bed,
                        chrom,
                        functionFlag,
                        plot,
                        tsb_stat,
                        volume=volume,
                    )
                    mutation_pd = {}
                    mutation_pd["6144"] = pd.DataFrame(
                        0, index=mut_types, columns=samples
                    )
                    dinuc_mat = matGen.matrix_generator_DINUC(
                        output_matrix,
                        samples,
                        bias_sort,
                        mutation_dinuc_pd_all,
                        mutation_types_tsb_context,
                        project,
                        exome,
                        bed,
                        chrom,
                        plot,
                        volume=volume,
                    )
                    mutation_dinuc_pd_all = pd.DataFrame(
                        0, index=mutation_types_tsb_context, columns=samples
                    )

                skipped_muts += skipped_mut
                analyzed_muts[0] += total
                analyzed_muts[1] += total_DINUC

            sample_count_high = len(samples)

            if exome:
                with open(vcf_path + "exome_temp.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]

                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "exome_temp.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                # Initialize the DataFrame for storing mutation data
                mutation_pd = {}
                mutation_pd["6144"] = pd.DataFrame(0, index=mut_types, columns=samples)
                # mutation_pd['6144'], samples2 = matGen.exome_check(mutation_pd['6144'], genome, vcf_path + "exome_temp.txt", output_matrix, project, "SNV", cushion)
                mutation_pd["6144"], samples2 = matGen.exome_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    mut_types,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_pd["6144"],
                    reference_genome,
                    vcf_path + "exome_temp.txt",
                    output_matrix,
                    project,
                    "SNV",
                    cushion,
                    volume=volume,
                )

            if bed:
                with open(vcf_path + "bed_temp.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "bed_temp.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_pd = {}
                mutation_pd["6144"] = pd.DataFrame(0, index=mut_types, columns=samples)
                mutation_pd["6144"], samples2 = matGen.panel_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    mut_types,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_pd["6144"],
                    reference_genome,
                    vcf_path + "bed_temp.txt",
                    output_matrix,
                    bed_file_path,
                    project,
                    "SNV",
                    cushion,
                    volume=volume,
                )

            if not chrom_based:
                if not mutation_pd["6144"].empty:
                    matrices = matGen.matrix_generator(
                        context,
                        output_matrix,
                        project,
                        samples,
                        bias_sort,
                        mutation_pd,
                        exome,
                        mut_types,
                        bed,
                        chrom_start,
                        functionFlag,
                        plot,
                        tsb_stat,
                        volume=volume,
                    )

            if analyzed_muts[1] > 0:
                if exome:
                    with open(vcf_path + "exome_temp_context_tsb_DINUC.txt") as f:
                        lines = [line.strip().split() for line in f]
                    common_chrom_list = [
                        "gi_82503188_ref_NC_007605",
                        "X",
                        "Y",
                        "1",
                        "2",
                        "3",
                        "4",
                        "5",
                        "6",
                        "7",
                        "8",
                        "9",
                        "10",
                        "11",
                        "12",
                        "13",
                        "14",
                        "15",
                        "16",
                        "17",
                        "18",
                        "19",
                        "20",
                        "21",
                        "22",
                        "23",
                        "24",
                        "25",
                        "26",
                        "27",
                        "28",
                        "29",
                        "30",
                        "31",
                        "32",
                        "33",
                        "34",
                        "35",
                        "36",
                        "37",
                        "38",
                        "39",
                        "MT",
                        "M",
                        "MtDNA",
                        "chrM",
                    ]
                    chrom_orders = {
                        "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                        "yeast": [
                            "I",
                            "II",
                            "III",
                            "IV",
                            "V",
                            "VI",
                            "VII",
                            "VIII",
                            "IX",
                            "X",
                            "XI",
                            "XII",
                            "XIII",
                            "XIV",
                            "XV",
                            "XVI",
                            "M",
                        ],
                        # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                        # Add other genomes here if needed
                        **{
                            genome: common_chrom_list
                            for genome in [
                                "GRCh37",
                                "GRCh38",
                                "CHM13-T2T",
                                "dog",
                                "ebv",
                                "mm10",
                                "mm9",
                                "mm39",
                                "rn6",
                            ]
                        },
                    }

                    # # # Select the chromosome order based on the genome
                    chrom_order = chrom_orders[reference_genome]

                    # Open the same file to write the sorted data
                    with open(
                        vcf_path + "exome_temp_context_tsb_DINUC.txt", "w"
                    ) as output:
                        # Sort the lines based on the selected chromosome order and position
                        sorted_lines = sorted(
                            lines,
                            key=lambda x: (
                                chrom_order.index(x[1]),  # Sort by chromosome order
                                int(x[2]),  # Then sort by position
                            ),
                        )

                        # Write the sorted lines back to the file
                        for line in sorted_lines:
                            print("\t".join(line), file=output)

                    mutation_dinuc_pd_all = pd.DataFrame(
                        0, index=mutation_types_tsb_context, columns=samples
                    )
                    mutation_dinuc_pd_all, samples2 = matGen.exome_check(
                        chrom_based,
                        samples,
                        bias_sort,
                        exome,
                        mutation_types_tsb_context,
                        bed,
                        chrom,
                        functionFlag,
                        plot,
                        tsb_stat,
                        mutation_dinuc_pd_all,
                        reference_genome,
                        vcf_path + "exome_temp_context_tsb_DINUC.txt",
                        output_matrix,
                        project,
                        "DBS",
                        cushion,
                        volume=volume,
                    )

                if bed:
                    with open(vcf_path + "bed_temp_context_tsb_DINUC.txt") as f:
                        lines = [line.strip().split() for line in f]
                    common_chrom_list = [
                        "gi_82503188_ref_NC_007605",
                        "X",
                        "Y",
                        "1",
                        "2",
                        "3",
                        "4",
                        "5",
                        "6",
                        "7",
                        "8",
                        "9",
                        "10",
                        "11",
                        "12",
                        "13",
                        "14",
                        "15",
                        "16",
                        "17",
                        "18",
                        "19",
                        "20",
                        "21",
                        "22",
                        "23",
                        "24",
                        "25",
                        "26",
                        "27",
                        "28",
                        "29",
                        "30",
                        "31",
                        "32",
                        "33",
                        "34",
                        "35",
                        "36",
                        "37",
                        "38",
                        "39",
                        "MT",
                        "M",
                        "MtDNA",
                        "chrM",
                    ]
                    chrom_orders = {
                        "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                        "yeast": [
                            "I",
                            "II",
                            "III",
                            "IV",
                            "V",
                            "VI",
                            "VII",
                            "VIII",
                            "IX",
                            "X",
                            "XI",
                            "XII",
                            "XIII",
                            "XIV",
                            "XV",
                            "XVI",
                            "M",
                        ],
                        # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                        # Add other genomes here if needed
                        **{
                            genome: common_chrom_list
                            for genome in [
                                "GRCh37",
                                "GRCh38",
                                "CHM13-T2T",
                                "dog",
                                "ebv",
                                "mm10",
                                "mm9",
                                "mm39",
                                "rn6",
                            ]
                        },
                    }

                    # # # Select the chromosome order based on the genome
                    chrom_order = chrom_orders[reference_genome]

                    # Open the same file to write the sorted data
                    with open(
                        vcf_path + "bed_temp_context_tsb_DINUC.txt", "w"
                    ) as output:
                        # Sort the lines based on the selected chromosome order and position
                        sorted_lines = sorted(
                            lines,
                            key=lambda x: (
                                chrom_order.index(x[1]),  # Sort by chromosome order
                                int(x[2]),  # Then sort by position
                            ),
                        )

                        # Write the sorted lines back to the file
                        for line in sorted_lines:
                            print("\t".join(line), file=output)

                    mutation_dinuc_pd_all = pd.DataFrame(
                        0, index=mutation_types_tsb_context, columns=samples
                    )
                    mutation_dinuc_pd_all, samples2 = matGen.panel_check(
                        chrom_based,
                        samples,
                        bias_sort,
                        exome,
                        mutation_types_tsb_context,
                        bed,
                        chrom,
                        functionFlag,
                        plot,
                        tsb_stat,
                        mutation_dinuc_pd_all,
                        reference_genome,
                        vcf_path + "bed_temp_context_tsb_DINUC.txt",
                        output_matrix,
                        bed_file_path,
                        project,
                        "DBS",
                        cushion,
                        volume=volume,
                    )

                if not chrom_based:
                    if not mutation_dinuc_pd_all.empty:
                        dinuc_mat = matGen.matrix_generator_DINUC(
                            output_matrix,
                            samples,
                            bias_sort,
                            mutation_dinuc_pd_all,
                            mutation_types_tsb_context,
                            project,
                            exome,
                            bed,
                            chrom_start,
                            plot,
                            volume=volume,
                        )
                matrices["DINUC"] = dinuc_mat

        else:
            for file in vcf_files:
                chrom = file.split("_")[0]
                if reference_genome == "ebv":
                    chrom = "gi_82503188_ref_NC_007605"
                with open(vcf_path + file) as f:
                    lines = [line.strip().split() for line in f]
                lines = sorted(lines, key=lambda x: (x[0], int(x[2])))
                (
                    mutation_ID,
                    skipped_mut,
                    total,
                ) = matGen.catalogue_generator_INDEL_single(
                    mutation_ID,
                    lines,
                    chrom,
                    vcf_path,
                    vcf_path_original,
                    vcf_files,
                    bed_file_path,
                    chrom_path,
                    project,
                    output_matrix,
                    exome,
                    reference_genome,
                    ncbi_chrom,
                    limited_indel,
                    functionFlag,
                    bed,
                    bed_ranges,
                    chrom_based,
                    plot,
                    tsb_ref,
                    transcript_path,
                    seqInfo,
                    gs,
                    log_file,
                )

                if chrom_based and not exome and not bed:
                    matGen.matrix_generator_INDEL(
                        output_matrix,
                        samples,
                        indel_types,
                        indel_types_tsb,
                        indel_types_simple,
                        mutation_ID["ID"],
                        mutation_ID["tsb"],
                        mutation_ID["simple"],
                        mutation_ID["complete"],
                        project,
                        exome,
                        limited_indel,
                        bed,
                        chrom,
                        plot,
                        volume=volume,
                    )
                    mutation_ID["ID"] = pd.DataFrame(
                        0, index=indel_types, columns=samples
                    )
                    mutation_ID["simple"] = pd.DataFrame(
                        0, index=indel_types_simple, columns=samples
                    )
                    mutation_ID["tsb"] = pd.DataFrame(
                        0, index=indel_types_tsb, columns=samples
                    )
                    mutation_ID["complete"] = pd.DataFrame(
                        0, index=indel_complete, columns=samples
                    )

                sample_count_high = len(samples)
                skipped_muts += skipped_mut
                analyzed_muts[2] += total

            # Performs the final filter on the variants base upon the exome if desired
            if exome:
                with open(vcf_path + "exome_temp.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "exome_temp.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_ID = {}
                mutation_ID["ID"] = pd.DataFrame(0, index=indel_types, columns=samples)
                mutation_ID["ID"], samples2 = matGen.exome_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    indel_types,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_ID["ID"],
                    reference_genome,
                    vcf_path + "exome_temp.txt",
                    output_matrix,
                    project,
                    "ID",
                    cushion,
                    "83",
                    volume=volume,
                )

                with open(vcf_path + "exome_temp_simple.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "exome_temp_simple.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_ID["simple"] = pd.DataFrame(
                    0, index=indel_types_simple, columns=samples
                )

                mutation_ID["simple"], samples2 = matGen.exome_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    indel_types_simple,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_ID["simple"],
                    reference_genome,
                    vcf_path + "exome_temp_simple.txt",
                    output_matrix,
                    project,
                    "ID",
                    cushion,
                    "simple",
                    volume=volume,
                )

                with open(vcf_path + "exome_temp_tsb.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "exome_temp_tsb.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_ID["tsb"] = pd.DataFrame(
                    0, index=indel_types_tsb, columns=samples
                )
                mutation_ID["tsb"], samples2 = matGen.exome_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    indel_types_tsb,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_ID["tsb"],
                    reference_genome,
                    vcf_path + "exome_temp_tsb.txt",
                    output_matrix,
                    project,
                    "ID",
                    cushion,
                    "tsb",
                    volume=volume,
                )
                mutation_ID["complete"] = pd.DataFrame(
                    0, index=indel_complete, columns=samples
                )

            if bed:
                with open(vcf_path + "bed_temp.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "bed_temp.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_ID = {}
                mutation_ID["ID"] = pd.DataFrame(0, index=indel_types, columns=samples)
                mutation_ID["ID"], samples2 = matGen.panel_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    indel_types,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_ID["ID"],
                    reference_genome,
                    vcf_path + "bed_temp.txt",
                    output_matrix,
                    bed_file_path,
                    project,
                    "ID",
                    cushion,
                    "83",
                    volume=volume,
                )

                with open(vcf_path + "bed_temp_simple.txt") as f:
                    lines = [line.strip().split() for line in f]
                common_chrom_list = [
                    "gi_82503188_ref_NC_007605",
                    "X",
                    "Y",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                    "17",
                    "18",
                    "19",
                    "20",
                    "21",
                    "22",
                    "23",
                    "24",
                    "25",
                    "26",
                    "27",
                    "28",
                    "29",
                    "30",
                    "31",
                    "32",
                    "33",
                    "34",
                    "35",
                    "36",
                    "37",
                    "38",
                    "39",
                    "MT",
                    "M",
                    "MtDNA",
                    "chrM",
                ]
                chrom_orders = {
                    "c_elegans": ["X", "I", "II", "III", "IV", "V", "MT", "MtDNA"],
                    "yeast": [
                        "I",
                        "II",
                        "III",
                        "IV",
                        "V",
                        "VI",
                        "VII",
                        "VIII",
                        "IX",
                        "X",
                        "XI",
                        "XII",
                        "XIII",
                        "XIV",
                        "XV",
                        "XVI",
                        "M",
                    ],
                    # This approach uses dictionary unpacking (**) and a dictionary comprehension to add multiple keys with the same value in a single line.
                    # Add other genomes here if needed
                    **{
                        genome: common_chrom_list
                        for genome in [
                            "GRCh37",
                            "GRCh38",
                            "CHM13-T2T",
                            "dog",
                            "ebv",
                            "mm10",
                            "mm9",
                            "mm39",
                            "rn6",
                        ]
                    },
                }

                # # # Select the chromosome order based on the genome
                chrom_order = chrom_orders[reference_genome]

                # Open the same file to write the sorted data
                with open(vcf_path + "bed_temp_simple.txt", "w") as output:
                    # Sort the lines based on the selected chromosome order and position
                    sorted_lines = sorted(
                        lines,
                        key=lambda x: (
                            chrom_order.index(x[1]),  # Sort by chromosome order
                            int(x[2]),  # Then sort by position
                        ),
                    )

                    # Write the sorted lines back to the file
                    for line in sorted_lines:
                        print("\t".join(line), file=output)

                mutation_ID["tsb"] = pd.DataFrame(
                    0, index=indel_types_tsb, columns=samples
                )
                mutation_ID["tsb"], samples2 = matGen.panel_check(
                    chrom_based,
                    samples,
                    bias_sort,
                    exome,
                    indel_types_tsb,
                    bed,
                    chrom,
                    functionFlag,
                    plot,
                    tsb_stat,
                    mutation_ID["tsb"],
                    reference_genome,
                    vcf_path + "bed_temp_tsb.txt",
                    output_matrix,
                    bed_file_path,
                    project,
                    "ID",
                    cushion,
                    "tsb",
                )
                mutation_ID["complete"] = pd.DataFrame(
                    0, index=indel_complete, columns=samples
                )

            if not chrom_based:
                # Ensure all required keys exist
                for key, indel_set in [
                    ("ID", indel_types),
                    ("simple", indel_types_simple),
                    ("tsb", indel_types),
                    ("complete", indel_types)
                ]:
                    if key not in mutation_ID or not isinstance(mutation_ID[key], pd.DataFrame) or mutation_ID[key].empty:
                        mutation_ID[key] = pd.DataFrame(0, index=indel_set, columns=samples)

                matGen.matrix_generator_INDEL(
                    output_matrix,
                    samples,
                    indel_types,
                    indel_types_tsb,
                    indel_types_simple,
                    mutation_ID["ID"],
                    mutation_ID["tsb"],
                    mutation_ID["simple"],
                    mutation_ID["complete"],
                    project,
                    exome,
                    limited_indel,
                    bed,
                    chrom_start,
                    plot,
                    volume=volume,
                )
            matrices["ID"] = mutation_ID["ID"].iloc[0:83, :]

        if i == 1:
            shutil.rmtree(output_matrix + "temp/")
        end = time.time() - start
        print("Completed! Elapsed time: " + str(round(end, 2)) + " seconds.")

    sys.stderr.close()
    sys.stderr = tempErr
    # Prints a summary for the given run (total samples, skipped mutations, etc.)
    if not chrom_based:
        print(
            "Matrices generated for "
            + str(sample_count_high)
            + " samples with "
            + str(skipped_muts)
            + " errors. Total of "
            + str(analyzed_muts[0])
            + " SNVs, "
            + str(analyzed_muts[1])
            + " DINUCs, and "
            + str(analyzed_muts[2])
            + " INDELs were successfully analyzed."
        )
        # Raise an error when more than 30% of mutations are skipped
        if (
            skipped_muts
            > (analyzed_muts[0] + analyzed_muts[1] + analyzed_muts[2]) * 0.3
        ):
            raise ValueError(
                "Error: More than 30% of mutations were skipped. Please check the log file for more information."
            )
    return matrices
