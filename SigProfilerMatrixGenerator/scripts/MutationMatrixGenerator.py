#!/usr/bin/env python3

# Author: Erik Bergstrom

# Contact: ebergstr@eng.ucsd.edu

from __future__ import print_function

import argparse
import datetime
import gc
import itertools
import os
import re
import sys
import time
import uuid
from collections import OrderedDict, defaultdict
from itertools import chain

import numpy as np
import pandas as pd
import sigProfilerPlotting as sigPlt
import statsmodels.stats.multitest as sm
from scipy import stats

from SigProfilerMatrixGenerator.scripts import ref_install


################# Functions and references ###############################################
def df2csv(df, fname, formats=[], sep="\t"):
    """
    # function is faster than to_csv
    # 7 times faster for numbers if formats are specified,
    # 2 times faster for strings.
    # Note - be careful. It doesn't add quotes and doesn't check
    # for quotes or separators inside elements
    # We've seen output time going down from 45 min to 6 min
    # on a simple numeric 4-col dataframe with 45 million rows.
    """
    if len(df.columns) <= 0:
        return
    Nd = len(df.columns)
    Nd_1 = Nd
    # formats = myformats[:] # take a copy to modify it
    Nf = 0
    formats.append("%s")
    # make sure we have formats for all columns
    if Nf < Nd:
        for ii in range(Nf, Nd, 1):
            coltype = df[df.columns[ii]].dtype
            ff = "%s"
            if coltype == np.int64:
                ff = "%d"
            elif coltype == np.float64:
                ff = "%f"
            formats.append(ff)
    fh = open(fname, "w", buffering=200000)
    header = ["MutationType"] + list(df.columns)
    fh.write("\t".join(header) + "\n")
    for row in df.itertuples(index=True):
        ss = ""
        for ii in range(0, Nd + 1, 1):
            ss += formats[ii] % row[ii]
            if ii < Nd_1:
                ss += sep
        fh.write(ss + "\n")
    fh.close()


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


def reference_paths(genome, volume=None):
    """
    Returns the path to the reference genomes installed with SigProfilerMatrixGenerator

    Parameters:
            genome  -> reference genome

    Returns:
            chrom_path  -> path to the reference genome's chromosome files
    """
    reference_dir = ref_install.reference_dir(secondary_chromosome_install_dir=volume)
    ref_dir = str(reference_dir.path)
    chrom_path = str(reference_dir.get_tsb_dir() / genome) + "/"

    return (chrom_path, ref_dir)


def BED_filtering(bed_file_path):
    """
    Creates ranges from a bed file for generating the matrix.

    Parameters:
             bed_file_path  -> path to the desired bed file

    Returns:
              ranges_final  -> dictionary of all ranges for each chromosome.
    """
    ranges = {}
    ranges_final = {}
    with open(bed_file_path) as f:
        # next(f)
        for lines in f:
            if lines[0] == "#" or lines[0] == "@":
                next(f)
            else:
                line = lines.strip().split()
                chrom = line[0]
                if len(chrom) > 2:
                    chrom = chrom[3:]
                start = int(line[1])
                end = int(line[2])
                if chrom not in ranges.keys():
                    ranges[chrom] = []
                ranges[chrom].append((start, end))

    for chroms in ranges.keys():
        ranges_final[chroms] = set(
            chain(*(range(start, end + 1) for start, end in ranges[chroms]))
        )

    return ranges_final


def BED_sorting(bed_file_path, genome):
    """
    Sorts a BED file and writes the sorted content to a new file with a different name.

    Parameters:
        bed_file_path (str): Path to the input BED file.
        genome (str): Name of the genome for sorting.

    Returns:
        str: Path to the new sorted BED file.
    """
    # Define the common chromosome lists and chrom_orders dictionary
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
        "c_elegans": ["X", "I", "II", "III", "IV", "V", "M", "MT", "MtDNA"],
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
            "MT",
            "MtDNA",
        ],
        **{
            g: common_chrom_list
            for g in ["GRCh37", "GRCh38", "CHM13-T2T", "dog", "ebv", "mm10", "mm9", "mm39", "rn6"]
        },
    }

    # Select the chromosome order based on the genome
    chrom_order = chrom_orders[genome]

    def remove_chr_prefix(line):
        parts = line.split()
        if parts[0].startswith("chr"):
            parts[0] = parts[0][3:]  # Remove 'chr' prefix
        return parts

    # Read the lines from the input file
    with open(bed_file_path, "r") as infile:
        lines = infile.readlines()

    # Determine if the first line is a header
    header = None
    if (
        lines[0].startswith("@")
        or lines[0].startswith("#")
        or "chrom" in lines[0].lower()
    ):
        header = lines[0]
        lines = lines[1:]

    # Split the lines into columns for sorting and remove 'chr' prefix
    lines_split = [remove_chr_prefix(line) for line in lines]

    # Sort the lines based on the selected chromosome order and position
    sorted_lines = sorted(
        lines_split,
        key=lambda x: (
            (
                chrom_order.index(x[0]) if x[0] in chrom_order else len(chrom_order)
            ),  # Sort by chromosome order
            int(x[1]),  # Then sort by position
        ),
    )

    # Create new file name with hardcoded suffix
    base, ext = os.path.splitext(bed_file_path)
    new_file_name = f"{base}_sorted{ext}"

    # Write the sorted output to the new file
    with open(new_file_name, "w") as outfile:
        if header:
            outfile.write(header)
        for line in sorted_lines:
            outfile.write("\t".join(line) + "\n")

    # print(f"Sorted BED file saved to: {new_file_name}")

    return new_file_name


def gene_range(files_path, indel=False):
    """
    Creates a dictionary of gene ranges and gene names across the
    given reference genome.

    Parameters:
                                                    files_path  -> path to the transcript files
                                                             indel  -> flag that will construct the data structures for indels

    Returns:
                                               gene_ranges  -> dictionary that contains the gene ranges on a chromosome basis.
                                               gene_counts  -> dictionary that contains the number of mutations found for a given gene.
                                                                               This value broken into a list of two integers ([transcribed, untranscribed])
                                                    gene_names  -> dictionary that contains all of the gene names on a chromosome basis
                    sample_mut_counts_per_gene  -> dictionary that contains all of the genes. It will store the number
                                                                               of mutations associated with each gene per sample.
            sample_mut_counts_per_mut_type  -> dictionary that contains the total mutation count for each gene per mutation type
    """
    gene_ranges = {}
    gene_counts = {}
    gene_names = {}
    sample_mut_counts_per_gene = {}
    sample_mut_counts_per_mut_type = {}

    for file in os.listdir(files_path):
        name = file.split("_")
        chrom = name[0]
        gene_ranges[chrom] = []
        gene_names[chrom] = []
        if file == ".DS_Store":
            continue
        else:
            with open(files_path + file) as f:
                next(f)
                for lines in f:
                    line = lines.strip().split("\t")
                    gene, start, end, strand, chrom = (
                        line[6],
                        line[4],
                        line[5],
                        line[3],
                        line[2],
                    )
                    start, end = int(start), int(end)
                    if gene not in gene_names[chrom]:
                        gene_counts[gene] = OrderedDict()
                        gene_ranges[chrom].append((start, end, strand))
                        gene_names[chrom].append(gene)
                        if indel:
                            gene_counts[gene] = {"T": 0, "U": 0, "samples": []}
                        else:
                            gene_counts[gene] = {
                                "T:C>A": 0,
                                "T:C>G": 0,
                                "T:C>T": 0,
                                "T:T>A": 0,
                                "T:T>C": 0,
                                "T:T>G": 0,
                                "U:C>A": 0,
                                "U:C>G": 0,
                                "U:C>T": 0,
                                "U:T>A": 0,
                                "U:T>C": 0,
                                "U:T>G": 0,
                                "samples": [],
                            }
                        sample_mut_counts_per_gene[gene] = {}
                        sample_mut_counts_per_mut_type[gene] = {}
                    else:
                        lst = list(gene_ranges[chrom][-1])
                        if start < lst[0]:
                            lst[0] = start
                        if end > lst[1]:
                            lst[1] = end
                        gene_ranges[chrom][-1] = tuple(lst)

    return (
        gene_ranges,
        gene_counts,
        gene_names,
        sample_mut_counts_per_gene,
        sample_mut_counts_per_mut_type,
    )


def catalogue_generator_single(
    lines,
    chrom,
    mutation_dict,
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
    genome,
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
    volume=None,
):
    """
    Generates the mutational matrix for 96, 1536, 384, and 6144 context using a single vcf file with all samples of interest.

    Parameters:
                                    vcf_path  -> path to vcf file of interest
               vcf_path_original  -> path to the original vcf files
                               vcf_files  -> actual vcf file
                       bed_file_path  -> path to the user-provided bed files
                              chrom_path  -> path to chromosome reference files. The chromosomes are saved as strings witht the following
                                                            file name: '1.txt', '2.txt', etc.
                                     project  -> unique name given to the set of samples (ex. 'BRCA')
                       output_matrix  -> path where the final mutational matrix is stored
                                     context  -> desired context (ex. 96, 1536, 384, 6144)
                                       exome  -> flag that generates the matrix in only the exome
                                      genome  -> the desired reference genome
                              ncbi_chrom  -> dictionary that allows for the converstion of ncbi chromosome names to standard format
                                                            for the mm10 assembly.
                            functionFlag  -> flag that is used when calling this function from an alternate script
                                             bed  -> parameter used to filter the mutations on a user-provided BED file
                              bed_ranges  -> dictionary that contains all of the ranges for each chromosome dictated by the user's input BED file
                             chrom_based  -> flag that generates the matrices on a chromosome basis
                                            plot  -> flag that plots the matrices after they are generated
                                    tsb_stat  -> performs a transcriptional strand bias test for the 24, 384, and 6144 contexts. The output is
                                                             saved into the output/TSB directory

                                     tsb_ref  -> dictionary that allows for switching between binary and biologically relevant strings
                     transcript_path  -> path to the transcript files
                                              gs  -> flag that generates a file for the strand bias on a gene basis.
                                    log_file  -> path to the output log file

    Returns:
            If called as a function, returns a nested dictionary of panda data frames for each matrix

    Outputs:
            Outputs a mutational matrix for the desired context within [user-provided input path]/output/[mut_type]/

    """
    out = open(log_file, "a")
    mnv = 5
    # Small functions to provide reverse complements of TSB and sequence info:
    revcompl = lambda x: "".join(
        [
            {
                "A": "T",
                "C": "G",
                "G": "C",
                "T": "A",
                "N": "N",
                "[": "[",
                "]": "]",
                ">": ">",
            }[B]
            for B in x
        ][::-1]
    )
    revbias = lambda x: "".join(
        [
            {
                "0": "0",
                "3": "3",
                "1": "2",
                "2": "1",
                "U": "T",
                "T": "U",
                "B": "B",
                "N": "N",
            }[B]
            for B in x
        ][::-1]
    )

    # Provides the sorting order for the TSB matrices
    bias_sort = {"T": 0, "U": 1, "N": 3, "B": 2}
    tsb = ["T", "U", "N", "B"]
    bases = ["A", "C", "G", "T"]

    # Instantiates all relevant variables
    types = []
    flag = True
    i = 0
    sample_start = None
    gene_counts = {}
    skipped_count = 0
    total_analyzed = 0
    total_analyzed_DINUC = 0
    sequence = ""

    # Instantiates the necessary variables/data structures for DINUCs
    if exome:
        exome_temp_file = "exome_temp.txt"
        exome_file = open(vcf_path + exome_temp_file, "a")
        exome_temp_file_context_tsb_DINUC = "exome_temp_context_tsb_DINUC.txt"
        exome_file_context_tsb_DINUC = open(
            vcf_path + exome_temp_file_context_tsb_DINUC, "a"
        )

    if bed:
        bed_temp_file = "bed_temp.txt"
        bed_file = open(vcf_path + bed_temp_file, "a")
        bed_temp_file_context_tsb_DINUC = "bed_temp_context_tsb_DINUC.txt"
        bed_file_context_tsb_DINUC = open(
            vcf_path + bed_temp_file_context_tsb_DINUC, "a"
        )

    dinuc_tsb_ref = ["CC", "CT", "TC", "TT", "AA", "AG", "GA", "GG"]
    chrom_start = chrom

    # Opens the input vcf file
    with open(chrom_path + chrom_start + ".txt", "rb") as f2:
        chrom_string = f2.read()

        dinuc_sub = [int(y[2]) - int(x[2]) for x, y in zip(lines, lines[1:])]
        dinuc_index_temp = [i for i, x in enumerate(dinuc_sub) if x == 1]
        mnv_index_temp = [i for i, x in enumerate(dinuc_sub) if x <= mnv and x > 0]

        if seqInfo:
            seqOut_path = output_matrix + "vcf_files/SNV/"
            seqOut_path_dinuc = output_matrix + "vcf_files/DBS/"
            seqOut_path_mns = output_matrix + "vcf_files/MNS/"
            if not os.path.exists(seqOut_path):
                os.makedirs(seqOut_path)
            if not os.path.exists(seqOut_path_dinuc):
                os.makedirs(seqOut_path_dinuc)
            if not os.path.exists(seqOut_path_mns):
                os.makedirs(seqOut_path_mns)
            seqOut = open(seqOut_path + chrom_start + "_seqinfo.txt", "w")
            seqOut_dinuc = open(seqOut_path_dinuc + chrom_start + "_seqinfo.txt", "w")
            seqOut_mns = open(seqOut_path_mns + chrom_start + "_seqinfo.txt", "w")

            mnv_index = []
            if len(mnv_index_temp) > 1:
                if mnv_index_temp[0] + 1 == mnv_index_temp[1]:
                    if lines[mnv_index_temp[0]][0] == lines[mnv_index_temp[1]][0]:
                        mnv_index.append(mnv_index_temp[0])
                elif mnv_index_temp[0] not in dinuc_index_temp:
                    mnv_index.append(mnv_index_temp[0])
                else:
                    pass
                for i in range(1, len(mnv_index_temp) - 1, 1):
                    if mnv_index_temp[i] + 1 == mnv_index_temp[i + 1]:
                        if (
                            lines[mnv_index_temp[i]][0]
                            == lines[mnv_index_temp[i + 1]][0]
                        ):
                            mnv_index.append(mnv_index_temp[i])
                    elif mnv_index_temp[i] - 1 == mnv_index_temp[i - 1]:
                        if (
                            lines[mnv_index_temp[i]][0]
                            == lines[mnv_index_temp[i - 1]][0]
                        ):
                            mnv_index.append(mnv_index_temp[i])
                    elif mnv_index_temp[i] not in dinuc_index_temp:
                        mnv_index.append(mnv_index_temp[i])
                if mnv_index_temp[-1] - 1 == mnv_index_temp[-2]:
                    if lines[mnv_index_temp[-1]][0] == lines[mnv_index_temp[-2]][0]:
                        mnv_index.append(mnv_index_temp[-1])
                elif mnv_index_temp[-1] not in dinuc_index_temp:
                    mnv_index.append(mnv_index_temp[-1])

                dinuc_index = [x for x in dinuc_index_temp if x not in mnv_index]

            else:
                dinuc_index = dinuc_index_temp
                mnv_index = [x for x in mnv_index_temp if x not in dinuc_index]

            if mnv_index:
                i = 0
                mnv_seq = ""
                mut_seq = ""
                save_start = None
                change_start = True
                while i < len(mnv_index):
                    line1 = lines[mnv_index[i]]
                    line2 = lines[mnv_index[i] + 1]
                    start1 = int(line1[2])
                    start2 = int(line2[2])
                    previous_ref = line1[3]
                    ref = line2[3]
                    previous_mut = line1[4]
                    mut = line2[4]
                    sample = line1[0]
                    sample2 = line2[0]

                    if sample != sample2:
                        mnv_seq = ""
                        mut_seq = ""

                    else:
                        if change_start:
                            save_start = start1
                            change_start = False
                        mnv_seq += previous_ref
                        mut_seq += previous_mut

                        for l in range(start1 + 1, start2, 1):
                            mnv_seq += tsb_ref[chrom_string[l - 1]][1]
                            mut_seq += tsb_ref[chrom_string[l - 1]][1]

                        if i < len(mnv_index) - 1:
                            if mnv_index[i] + 1 != mnv_index[i + 1]:
                                mnv_seq += tsb_ref[chrom_string[start2 - 1]][1]
                                mut_seq += mut
                                print(
                                    "\t".join(
                                        [
                                            sample,
                                            chrom,
                                            str(save_start),
                                            mnv_seq + ">" + mut_seq,
                                        ]
                                    ),
                                    file=seqOut_mns,
                                )
                                mnv_seq = ""
                                mut_seq = ""
                                change_start = True
                        elif i == len(mnv_index) - 1:
                            mnv_seq += tsb_ref[chrom_string[start2 - 1]][1]
                            mut_seq += mut
                            print(
                                "\t".join(
                                    [
                                        sample,
                                        chrom,
                                        str(save_start),
                                        mnv_seq + ">" + mut_seq,
                                    ]
                                ),
                                file=seqOut_mns,
                            )
                    i += 1

        else:
            dinuc_index = dinuc_index_temp

        for x in dinuc_index:
            strand = "1"
            line1 = lines[x]
            line2 = lines[x + 1]
            previous_ref = line1[3]
            ref = line2[3]
            previous_mut = line1[4]
            mut = line2[4]
            dinuc = "".join([previous_ref, ref, ">", previous_mut, mut])
            sample = line1[0]
            sample2 = line2[0]
            start = int(line1[2])

            if sample != sample2:
                continue

            try:
                dinuc_seq = "".join(
                    [
                        tsb_ref[chrom_string[start - 2]][1],
                        "[",
                        dinuc,
                        "]",
                        tsb_ref[chrom_string[start + 1]][1],
                    ]
                )
                bias = tsb_ref[chrom_string[start - 1]][0]
                if "N" in dinuc_seq:
                    print(
                        "The position is out of range. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    skipped_count += 1
                    continue

            except:
                print(
                    "The position is out of range. Skipping this mutation: "
                    + chrom
                    + " "
                    + str(start)
                    + " "
                    + ref
                    + " "
                    + mut,
                    file=out,
                )
                skipped_count += 1
                continue

            dinuc_seq_tsb = bias + ":" + dinuc_seq
            if dinuc[:2] not in dinuc_tsb_ref:
                dinuc_seq_tsb = "Q" + dinuc_seq_tsb[1:]
                strand = "0"

                if dinuc_seq_tsb in mutation_types_tsb_context:
                    mutation_dinuc_pd_all.at[dinuc_seq_tsb, sample] += 1

                else:
                    dinuc_seq_tsb = "".join(
                        [
                            "Q:",
                            revcompl(dinuc_seq_tsb[-1]),
                            "[",
                            revcompl(dinuc_seq_tsb[4:6]),
                            ">",
                            revcompl(dinuc_seq_tsb[7:9]),
                            "]",
                            revcompl(dinuc_seq_tsb[2]),
                        ]
                    )
                    mutation_dinuc_pd_all.at[dinuc_seq_tsb, sample] += 1

            else:
                if dinuc_seq_tsb in mutation_types_tsb_context:
                    mutation_dinuc_pd_all.at[dinuc_seq_tsb, sample] += 1

                else:
                    strand = "-1"
                    dinuc_seq_tsb = "".join(
                        [
                            revbias(dinuc_seq_tsb[0]),
                            ":",
                            revcompl(dinuc_seq_tsb[-1]),
                            "[",
                            revcompl(dinuc_seq_tsb[4:6]),
                            ">",
                            revcompl(dinuc_seq_tsb[7:9]),
                            "]",
                            revcompl(dinuc_seq_tsb[2]),
                        ]
                    )
                    mutation_dinuc_pd_all.at[dinuc_seq_tsb, sample] += 1

            if seqInfo:
                print(
                    "\t".join([sample, chrom, str(start), dinuc_seq_tsb, strand]),
                    file=seqOut_dinuc,
                )

            # Saves the DINUC into temporary files for exome sorting
            if exome:
                exome_file_context_tsb_DINUC.write(
                    sample
                    + "\t"
                    + chrom
                    + "\t"
                    + str(start)
                    + "\t"
                    + dinuc_seq_tsb
                    + "\t"
                    + ref
                    + "\t"
                    + mut
                    + "\n"
                )

            # Saves the DINUC into temporary files for region sorting
            if bed:
                bed_file_context_tsb_DINUC.write(
                    sample
                    + "\t"
                    + chrom
                    + "\t"
                    + str(start)
                    + "\t"
                    + dinuc_seq_tsb
                    + "\t"
                    + ref
                    + "\t"
                    + mut
                    + "\n"
                )

            total_analyzed_DINUC += 1

        for line in lines:
            range_index = 0
            if gs:
                out = open(output_matrix + "gene_strand_bias_counts_SNV.txt", "w")
                out_hot = open(
                    output_matrix + "gene_strand_bias_counts_hotspots_SNV.txt", "w"
                )
                (
                    gene_ranges,
                    gene_counts,
                    gene_names,
                    sample_mut_counts_per_gene,
                    sample_mut_counts_per_mut_type,
                ) = gene_range(transcript_path)

            try:
                sample = line[0]
                start = int(line[2])
                ref = line[3][0].upper()
                mut = line[4][0].upper()

                # Pulls out the relevant sequence depending on the context
                try:
                    sequence = "".join(
                        [
                            tsb_ref[chrom_string[start - 3]][1],
                            tsb_ref[chrom_string[start - 2]][1],
                            tsb_ref[chrom_string[start - 1]][1],
                            tsb_ref[chrom_string[start]][1],
                            tsb_ref[chrom_string[start + 1]][1],
                        ]
                    )
                except:
                    print(
                        "The position is out of range. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    out.flush()
                    skipped_count += 1
                    continue

                bias = tsb_ref[chrom_string[start]][0]
                char = sequence[int(len(sequence) / 2)]

                # Prints the sequence and position if the pulled sequence doesn't match
                # the variant from the file
                if char != ref:  # and revcompl(char) != ref:
                    print(
                        "The reference base does not match the reference genome. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    out.flush()
                    skipped_count += 1
                    continue

                # Saves the sequence/mutation type if it matched the reference/reverse strand
                else:
                    strand = "1"
                    if ref == "A" or ref == "G":
                        strand = "-1"
                        bias = revbias(bias)
                        ref = revcompl(ref)
                        mut = revcompl(mut)
                        sequence = revcompl(sequence)

                    # Performs the gene strand bias test if desired
                    if gs:
                        for ranges in gene_ranges[chrom_start][range_index:]:
                            dict_key = ref + ">" + mut
                            if start < ranges[0]:
                                break
                            if ranges[0] <= start <= ranges[1]:
                                gene_index = gene_ranges[chrom_start].index(ranges)
                                gene = gene_names[chrom_start][gene_index]
                                if int(strand) + int(ranges[2]) == 0:
                                    dict_key = "T:" + dict_key
                                    gene_counts[gene][dict_key] += 1
                                    if sample not in gene_counts[gene]["samples"]:
                                        gene_counts[gene]["samples"].append(sample)
                                        sample_mut_counts_per_gene[gene][sample] = 1
                                        sample_mut_counts_per_mut_type[gene][sample] = {
                                            "T:C>A": 0,
                                            "T:C>G": 0,
                                            "T:C>T": 0,
                                            "T:T>A": 0,
                                            "T:T>C": 0,
                                            "T:T>G": 0,
                                            "U:C>A": 0,
                                            "U:C>G": 0,
                                            "U:C>T": 0,
                                            "U:T>A": 0,
                                            "U:T>C": 0,
                                            "U:T>G": 0,
                                        }
                                        sample_mut_counts_per_mut_type[gene][sample][
                                            dict_key
                                        ] += 1

                                    else:
                                        sample_mut_counts_per_gene[gene][sample] += 1
                                        sample_mut_counts_per_mut_type[gene][sample][
                                            dict_key
                                        ] += 1
                                elif strand == ranges[2]:
                                    dict_key = "U:" + dict_key
                                    gene_counts[gene][dict_key] += 1
                                    if sample not in gene_counts[gene]["samples"]:
                                        gene_counts[gene]["samples"].append(sample)
                                        sample_mut_counts_per_gene[gene][sample] = 1
                                        sample_mut_counts_per_mut_type[gene][sample] = {
                                            "T:C>A": 0,
                                            "T:C>G": 0,
                                            "T:C>T": 0,
                                            "T:T>A": 0,
                                            "T:T>C": 0,
                                            "T:T>G": 0,
                                            "U:C>A": 0,
                                            "U:C>G": 0,
                                            "U:C>T": 0,
                                            "U:T>A": 0,
                                            "U:T>C": 0,
                                            "U:T>G": 0,
                                        }
                                        sample_mut_counts_per_mut_type[gene][sample][
                                            dict_key
                                        ] += 1
                                    else:
                                        sample_mut_counts_per_gene[gene][sample] += 1
                                        sample_mut_counts_per_mut_type[gene][sample][
                                            dict_key
                                        ] += 1

                    # Saves the mutation key for the current variant
                    mut_key = "".join(
                        [
                            bias,
                            ":",
                            sequence[0 : int(len(sequence) / 2)],
                            "[",
                            ref,
                            ">",
                            mut,
                            "]",
                            sequence[int(len(sequence) / 2 + 1) :],
                        ]
                    )
                    mutation_dict["6144"].at[mut_key, sample] += 1
                    total_analyzed += 1

                    # If exome is specified, it will write the variant to a temporary exome file.
                    if exome:
                        exome_file.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + mut_key
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                    if bed:
                        bed_file.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + mut_key
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                    if seqInfo:
                        print(
                            "\t".join([sample, chrom, str(start), mut_key, strand]),
                            file=seqOut,
                        )

            except:
                print(
                    "There appears to be an error in this line. Skipping this mutation: "
                    + chrom
                    + " "
                    + str(start)
                    + " "
                    + ref
                    + " "
                    + mut,
                    file=out,
                )
                out.flush()
                skipped_count += 1

            # Once all variants are accounted for, complete the gene strand bias test/output to the final file.
            if gs:
                pvals = []
                qvals = []
                pvals_hot = []
                qvals_hot = []
                hotspots = {}
                gene_bias = []
                gene_bias_hotspots = []
                for gene in gene_counts:
                    if gene not in gene_bias:
                        gene_bias.append(gene)
                    total_count = sum(sample_mut_counts_per_gene[gene].values())
                    for sample in sample_mut_counts_per_gene[gene]:
                        mut_count = sample_mut_counts_per_gene[gene][sample]
                        if mut_count > 3:  # and mut_count/total_count > 0.5:
                            if gene not in gene_bias_hotspots:
                                gene_bias_hotspots.append(gene)
                            if gene not in hotspots:
                                hotspots[gene] = {}
                                for mut, count in sample_mut_counts_per_mut_type[gene][
                                    sample
                                ].items():
                                    hotspots[gene][mut] = count
                                hotspots[gene]["samples"] = [sample]
                                for mut, count in sample_mut_counts_per_mut_type[gene][
                                    sample
                                ].items():
                                    gene_counts[gene][mut] -= count
                                gene_counts[gene]["samples"].remove(sample)
                            else:
                                for mut, count in sample_mut_counts_per_mut_type[gene][
                                    sample
                                ].items():
                                    hotspots[gene][mut] += count
                                    gene_counts[gene][mut] -= count
                                gene_counts[gene]["samples"].remove(sample)
                                hotspots[gene]["samples"].append(sample)

                    sum_tran = 0
                    sum_untran = 0
                    for mut, counts in gene_counts[gene].items():
                        if mut[0] == "T":
                            sum_tran += counts
                        elif mut[0] == "U":
                            sum_untran += counts
                    n = sum_tran + sum_untran
                    if n > 0:
                        pval = stats.binomtest(k=sum_tran, n=n).pvalue
                    else:
                        pval = 1
                    pvals.append(pval)

                    sum_tran_hot = 0
                    sum_untran_hot = 0
                    if gene in hotspots:
                        for mut, counts in hotspots[gene].items():
                            if mut[0] == "T":
                                sum_tran_hot += counts
                            elif mut[0] == "U":
                                sum_untran_hot += counts
                    n_hot = sum_tran_hot + sum_untran_hot
                    if n_hot > 0:
                        pval_hot = stats.binomtest(k=sum_tran_hot, n=n_hot).pvalue
                    else:
                        pval_hot = 1
                    pvals_hot.append(pval_hot)

                qvals = sm.fdrcorrection(pvals)[1]
                qvals_hot = sm.fdrcorrection(pvals_hot)[1]
                ind = pvals.index("BMP7")
                ind2 = pvals_hot.index("BMP7")

                gene_ind = 0
                for gene in gene_bias:
                    gene_counts[gene]["samples"] = len(gene_counts[gene]["samples"])
                    print(gene, end="", file=out, flush=False)
                    sum_tran = 0
                    sum_untran = 0
                    for mut, counts in gene_counts[gene].items():
                        if mut[0] == "T":
                            sum_tran += counts
                        elif mut[0] == "U":
                            sum_untran += counts
                        print("\t" + str(counts), end="", file=out, flush=False)
                    print(
                        "\t"
                        + str(sum_tran)
                        + "\t"
                        + str(sum_untran)
                        + "\t"
                        + str(qvals[gene_ind]),
                        flush=False,
                        file=out,
                    )
                    gene_ind += 1
                out.close()
                with open(output_matrix + "gene_strand_bias_counts_SNV.txt") as f2:
                    lines = [line.strip().split() for line in f2]
                output = open(output_matrix + "gene_strand_bias_counts_SNV.txt", "w")
                print(
                    "GENE\tT:C>A\tT:C>G\tT:C>T\tT:T>A\tT:T>C\tT:T>G\tU:C>A\tU:C>G\tU:C>T\tU:T>A\tU:T>C\tU:T>G\tSampleCount\tTranscribed_total\tUntranscribedTotal\tq_value",
                    file=output,
                )
                for line in sorted(lines, key=lambda x: (float(x[-1])), reverse=False):
                    print("\t".join(line), file=output)
                output.close()

                # Gene strand bias test for hot spot samples.
                gene_ind = 0
                for gene in gene_bias_hotspots:
                    hotspots[gene]["samples"] = len(hotspots[gene]["samples"])
                    print(gene, end="", file=out_hot, flush=False)
                    sum_tran_hot = 0
                    sum_untran_hot = 0
                    for mut, counts in hotspots[gene].items():
                        if mut[0] == "T":
                            sum_tran_hot += counts
                        elif mut[0] == "U":
                            sum_untran_hot += counts
                        print("\t" + str(counts), end="", file=out_hot, flush=False)
                    print(
                        "\t"
                        + str(sum_tran_hot)
                        + "\t"
                        + str(sum_untran_hot)
                        + "\t"
                        + str(qvals_hot[gene_ind]),
                        flush=False,
                        file=out_hot,
                    )
                    gene_ind += 1
                out_hot.close()
                with open(
                    output_matrix + "gene_strand_bias_counts_hotspots_SNV.txt"
                ) as f2:
                    lines = [line.strip().split() for line in f2]
                output = open(
                    output_matrix + "gene_strand_bias_counts_hotspots_SNV.txt", "w"
                )
                print(
                    "GENE\tT:C>A\tT:C>G\tT:C>T\tT:T>A\tT:T>C\tT:T>G\tU:C>A\tU:C>G\tU:C>T\tU:T>A\tU:T>C\tU:T>G\tSampleCount\tTranscribed_total\tUntranscribedTotal\tq_value",
                    file=output,
                )
                for line in sorted(lines, key=lambda x: (float(x[-1])), reverse=False):
                    print("\t".join(line), file=output)
                output.close()

    # Organizes the required dictionaries for the final matrix generation.
    print("Chromosome " + chrom_start + " done", file=out)
    out.flush()

    if seqInfo:
        seqOut.close()
        seqOut_dinuc.close()

    if exome:
        exome_file.close()
    if bed:
        bed_file.close()
    # Calls the function to generate the final matrix
    if functionFlag:
        chrom_start = None
        chrom_start = None
        out.close()

        return (
            mutation_dict,
            skipped_count,
            total_analyzed,
            total_analyzed_DINUC,
            mutation_dinuc_pd_all,
        )
    else:
        if not chrom_based:
            chrom_start = None
            matrix_generator(
                context,
                output_matrix,
                project,
                samples,
                bias_sort,
                mutation_dict,
                exome,
                mut_types,
                bed,
                chrom_start,
                functionFlag,
                plot,
                tsb_stat,
            )
    out.close()


def catalogue_generator_INDEL_single(
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
    genome,
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
):
    """
    Generates the mutational matrix for the INDEL context.

    Parameters:
                                    vcf_path  -> path to vcf file of interest
               vcf_path_original  -> path to the original vcf files
                               vcf_files  -> actual vcf file
                       bed_file_path  -> path to the user-provided bed files
                              chrom_path  -> path to chromosome reference files. The chromosomes are saved as strings witht the following
                                                            file name: '1.txt', '2.txt', etc.
                                     project  -> unique name given to the set of samples (ex. 'BRCA')
                       output_matrix  -> path where the final mutational matrix is stored
                                       exome  -> flag that generates the matrix in only the exome
                                      genome  -> the desired reference genome
                              ncbi_chrom  -> dictionary that allows for the converstion of ncbi chromosome names to standard format
                                                            for the mm10 assembly.
                       limited_indel  -> flag that creates the matrix based on limited indels
                            functionFlag  -> flag that is used when calling this function from an alternate script
                                             bed  -> parameter used to filter the mutations on a user-provided BED file
                              bed_ranges  -> dictionary that contains all of the ranges for each chromosome dictated by the user's input BED file
                             chrom_based  -> flag that generates the matrices on a chromosome basis
                                            plot  -> flag that plots the matrices after they are generated
                                     tsb_ref  -> dictionary that allows for switching between binary and biologically relevant strings
                     transcript_path  -> path to the transcript files
                                              gs  -> flag that generates a file for the strand bias on a gene basis.
                                    log_file  -> path to the output log file

    Returns:
            If called as a function, returns a nested dictionary of panda data frames for each matrix

    Outputs:
            Outputs a mutational matrix for the desired context within [user-provided input path]/output/[mut_type]/

    """

    out = open(log_file, "a")
    range_index = 0
    tsb_abrev = ["T", "U", "B", "N"]
    revcompl = lambda x: "".join(
        [{"A": "T", "C": "G", "G": "C", "T": "A", "N": "N"}[B] for B in x][::-1]
    )
    revbias = lambda x: "".join(
        [
            {
                "0": "0",
                "3": "3",
                "1": "2",
                "2": "1",
                "U": "T",
                "T": "U",
                "B": "B",
                "N": "N",
            }[B]
            for B in x
        ][::-1]
    )
    # Instantiates the remaining varibales/data structures
    i = 0
    chrom_string = None
    count = 0
    non_matching = 0
    complex_muts = 0
    skipped_count = 0
    total_analyzed = 0

    # Creates files for exome and region sorting
    if exome:
        exome_temp_file = "exome_temp.txt"
        exome_temp_file_simple = "exome_temp_simple.txt"
        exome_temp_file_tsb = "exome_temp_tsb.txt"
        exome_file = open(vcf_path + exome_temp_file, "a")
        exome_file_simple = open(vcf_path + exome_temp_file_simple, "a")
        exome_file_tsb = open(vcf_path + exome_temp_file_tsb, "a")

    if bed:
        bed_temp_file = "bed_temp.txt"
        bed_temp_file_simple = "bed_temp_simple.txt"
        bed_temp_file_tsb = "bed_temp_tsb.txt"
        bed_file = open(vcf_path + bed_temp_file, "a")
        bed_file_simple = open(vcf_path + bed_temp_file_simple, "a")
        bed_file_tsb = open(vcf_path + bed_temp_file_tsb, "a")

    # Opens the input vcf files
    with open(chrom_path + chrom + ".txt", "rb") as f:
        chrom_string = f.read().strip()
        prev_line = None

        if seqInfo:
            seqOut_path = output_matrix + "vcf_files/ID/"
            if not os.path.exists(seqOut_path):
                os.makedirs(seqOut_path)
            seqOut = open(seqOut_path + chrom + "_seqinfo.txt", "w")

        # Creates files for the genes strand bias test
        if gs:
            out = open(output_matrix + "gene_strand_bias_counts_indel.txt", "w")
            out_hot = open(
                output_matrix + "gene_strand_bias_counts_hotspots_indel.txt", "w"
            )
            (
                gene_ranges,
                gene_counts,
                gene_names,
                sample_mut_counts_per_gene,
                sample_mut_counts_per_mut_type,
            ) = gene_range(transcript_path, True)

        first_flag = True

        # Saves the relevant data from each line
        for line in lines:
            try:
                sample = line[0]
                chrom = line[1]
                start = int(line[2])
                ref = line[3].upper()
                mut = line[4].upper()
                if ref == "-":
                    mut = "-" + mut
                if mut == "-":
                    ref = "-" + ref
                sub_type_length = 0

                mut_type = None

                # Exception handling for incorrect input formats
                skip = False
                for r in ref:
                    if r not in "ACGT-":
                        print(
                            "The ref contains bases that are not recognized. Skipping this mutation: "
                            + chrom
                            + " "
                            + str(start)
                            + " "
                            + ref
                            + " "
                            + mut,
                            file=out,
                        )
                        skipped_count += 1
                        skip = True
                        break
                if skip:
                    continue

                skip = False
                for m in mut:
                    if m not in "ACGT-":
                        print(
                            "The mutation contains bases that are not recognized. Skipping this mutation: "
                            + chrom
                            + " "
                            + str(start)
                            + " "
                            + ref
                            + " "
                            + mut,
                            file=out,
                        )
                        skipped_count += 1
                        skip = True
                        break
                if skip:
                    continue

                if ref == mut:
                    print(
                        "The ref base appears to match the mutated base. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    skipped_count += 1
                    continue

                if line == prev_line:
                    print(
                        "There appears to be a duplicate single base substitution. Skipping this mutation: "
                        + chrom
                        + str(start)
                        + ref
                        + mut,
                        file=out,
                    )
                    skipped_count += 1
                    continue

                prev_line = line

                # Saves the relevant chromosome information from the reference file
                try:
                    base = tsb_ref[chrom_string[start - 1]][1]
                except:
                    print(
                        "The start position is out of range. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    skipped_count += 1
                    continue

                if ref[0] != base and ref[0] != "-":
                    print(
                        "The reference base does not match the reference chromosome position. Skipping this mutation: "
                        + chrom
                        + " "
                        + str(start)
                        + " "
                        + ref
                        + " "
                        + mut,
                        file=out,
                    )
                    skipped_count += 1
                    continue

                if ref[0] == base or ref[0] == "-":
                    bias = tsb_ref[chrom_string[start - 1]][0]

                    # Saves the mutation type for the given variant
                    if len(ref) - len(mut) == len(ref) - 1:
                        strand = "1"
                        mut_type = "Del"
                        ref_base = ref[1]
                        if ref_base == "G" or ref_base == "A":
                            ref_base = revcompl(ref_base)
                            strand = "-1"
                            bias = revbias(bias)

                    elif len(mut) - len(ref) == len(mut) - 1:
                        strand = "1"
                        mut_type = "Ins"
                        mut_base = mut[1]
                        if mut_base == "G" or mut_base == "A":
                            mut_base = revcompl(mut_base)
                            strand = "-1"
                            bias = revbias(bias)

                    else:
                        mutation_ID["ID"].at["complex", sample] += 1
                        mutation_ID["simple"].at["complex", sample] += 1
                        total_analyzed += 1
                        continue

                    type_sequence = ""

                    # Pulls out the mutation subtype for deletions
                    if mut_type == "Del":
                        type_sequence = ref[1:]

                        type_length = len(type_sequence)
                        sequence = type_sequence
                        pos = start + type_length
                        pos_rev = start
                        actual_seq = ""
                        for i in range(pos_rev - type_length, pos_rev, 1):
                            actual_seq += tsb_ref[chrom_string[i]][1]
                        while pos_rev - type_length > 0 and actual_seq == type_sequence:
                            sequence = actual_seq + sequence
                            pos_rev -= type_length
                            actual_seq = ""
                            for i in range(pos_rev - type_length, pos_rev, 1):
                                actual_seq += tsb_ref[chrom_string[i]][1]

                        new_seq = ""
                        for i in range(pos, pos + type_length, 1):
                            new_seq += tsb_ref[chrom_string[i]][1]
                        while (
                            pos + type_length < len(chrom_string)
                            and new_seq == type_sequence
                        ):
                            sequence += new_seq
                            pos += type_length
                            new_seq = ""
                            for i in range(pos, pos + type_length, 1):
                                new_seq += tsb_ref[chrom_string[i]][1]

                        # Pulls out possible microhomology deletions
                        if type_length > 1 and len(sequence) == type_length:
                            forward_homology = ref[1:-1]
                            reverse_homology = ref[2:]

                            # for_hom = False
                            # pos = start + type_length
                            # for i in range (len(forward_homology), 0, -1):
                            # 	seq = ''
                            # 	for l in range (pos, pos + i, 1):
                            # 		seq += tsb_ref[chrom_string[l]][1]
                            # 	if seq == forward_homology[:i]:
                            # 		sequence += forward_homology[:i]
                            # 		mut_type += '_Micro_for'
                            # 		for_hom = True
                            # 		break

                            # if for_hom != True:
                            # 	pos = start
                            # 	for i in range (len(reverse_homology), 0, -1):
                            # 		seq = ''
                            # 		for l in range (pos-i, pos, 1):
                            # 			seq += tsb_ref[chrom_string[l]][1]
                            # 		if seq == reverse_homology[-i:]:
                            # 			sequence = reverse_homology[-i:] + sequence
                            # 			mut_type += '_Micro_rev'
                            # 			break

                            for_hom = 0
                            pos = start + type_length
                            for i in range(len(forward_homology), 0, -1):
                                seq = ""
                                for l in range(pos, pos + i, 1):
                                    seq += tsb_ref[chrom_string[l]][1]
                                if seq == forward_homology[:i]:
                                    for_seq = forward_homology[:i]
                                    for_hom = len(for_seq)
                                    break

                            rev_hom = 0
                            pos = start
                            for i in range(len(reverse_homology), 0, -1):
                                seq = ""
                                for l in range(pos - i, pos, 1):
                                    seq += tsb_ref[chrom_string[l]][1]
                                if seq == reverse_homology[-i:]:
                                    rev_seq = reverse_homology[-i:]
                                    rev_hom = len(rev_seq)
                                    break

                            if for_hom > 0 or rev_hom > 0:
                                if for_hom > rev_hom or for_hom == rev_hom:
                                    sequence += for_seq
                                    mut_type += "_Micro_for"
                                else:
                                    sequence = rev_seq + sequence
                                    mut_type += "_Micro_rev"

                    # Pulls out the mutation subtype for insertions
                    elif mut_type == "Ins":
                        type_sequence = mut[1:]
                        type_length = len(type_sequence)
                        sequence = type_sequence

                        pos = start
                        pos_rev = start
                        seq = ""
                        for i in range(pos_rev - type_length, pos_rev, 1):
                            seq += tsb_ref[chrom_string[i]][1]
                        while pos_rev - type_length > 0 and seq == type_sequence:
                            sequence = seq + sequence
                            pos_rev -= type_length
                            seq = ""
                            for i in range(pos_rev - type_length, pos_rev, 1):
                                seq += tsb_ref[chrom_string[i]][1]

                        seq = ""
                        for i in range(pos, pos + type_length, 1):
                            seq += tsb_ref[chrom_string[i]][1]
                        while (
                            pos + type_length < len(chrom_string)
                            and seq == type_sequence
                        ):
                            sequence += seq
                            pos += type_length
                            seq = ""
                            for i in range(pos, pos + type_length, 1):
                                seq += tsb_ref[chrom_string[i]][1]

                        # Pulls possible microhomology for insertions
                        if type_length > 1 and len(sequence) == type_length:
                            forward_homology = mut[1:-1]
                            reverse_homology = mut[2:]

                            # for_hom = False
                            # pos = start
                            # for i in range (len(forward_homology), 0, -1):
                            # 	seq = ''
                            # 	for i in range (pos, pos + i, 1):
                            # 		seq += tsb_ref[chrom_string[i]][1]
                            # 	if seq == forward_homology[:i]:
                            # 		sequence += forward_homology[:i]
                            # 		mut_type += '_Micro_for'
                            # 		for_hom = True
                            # 		break

                            # if for_hom != True:
                            # 	pos = start
                            # 	for i in range (len(reverse_homology), 0, -1):
                            # 		seq = ''
                            # 		for i in range (pos-i, pos, 1):
                            # 			seq += tsb_ref[chrom_string[i]][1]
                            # 		if seq == reverse_homology[-i:]:
                            # 			sequence = reverse_homology[-i:] + sequence
                            # 			mut_type += '_Micro_rev'
                            # 			break

                            for_hom = 0
                            pos = start
                            for i in range(len(forward_homology), 0, -1):
                                seq = ""
                                for l in range(pos, pos + i, 1):
                                    seq += tsb_ref[chrom_string[l]][1]
                                if seq == forward_homology[:i]:
                                    for_seq = forward_homology[:i]
                                    for_hom = len(for_seq)
                                    break

                            rev_hom = 0
                            pos = start
                            for i in range(len(reverse_homology), 0, -1):
                                seq = ""
                                for l in range(pos - i, pos, 1):
                                    seq += tsb_ref[chrom_string[l]][1]
                                if seq == reverse_homology[-i:]:
                                    rev_seq = reverse_homology[-i:]
                                    rev_hom = len(rev_seq)
                                    break

                            if for_hom > 0 or rev_hom > 0:
                                if for_hom > rev_hom or for_hom == rev_hom:
                                    sequence += for_seq
                                    mut_type += "_Micro_for"
                                else:
                                    sequence = rev_seq + sequence
                                    mut_type += "_Micro_rev"

                    # Instantiates variables used to create the unique INDEL keys
                    indel_key_1 = None
                    indel_key_2 = None
                    indel_key_3 = None
                    indel_key_4 = None
                    indel_key = "blah"

                    output_sequence = None

                    # Creates the INDEL key for all deletions
                    if mut_type[0:3] == "Del":
                        indel_key_2 = "Del"

                        # Includes deletions of >1 bp
                        if len(ref) - 1 > 1:
                            key_1 = len(ref) - 1
                            if key_1 < 5:
                                indel_key_1 = key_1
                            else:
                                indel_key_1 = 5

                            # Only regular deleletions
                            if mut_type == "Del":
                                indel_key_3 = "R"
                                key_4 = int(len(sequence) / key_1 - 1)
                                if key_4 < 5:
                                    indel_key_4 = key_4
                                else:
                                    indel_key_4 = 5

                            # Only for microhomologies
                            else:
                                indel_key_3 = "M"
                                key_4 = len(sequence) - (len(ref) - 1)
                                if key_4 > 5:
                                    indel_key_4 = 5
                                elif key_4 < 0:
                                    print(lines)
                                else:
                                    indel_key_4 = key_4

                        # For deletions of 1bp
                        else:
                            indel_key_1 = 1
                            key_4 = len(sequence) - 1
                            if key_4 > 5:
                                indel_key_4 = 5
                            else:
                                indel_key_4 = key_4

                            if ref[1] == "C" or ref[1] == "G":
                                indel_key_3 = "C"

                            else:
                                indel_key_3 = "T"

                    # Creates the INDEL key for all insertions
                    elif mut_type[0:3] == "Ins":
                        indel_key_2 = "Ins"

                        # Includes insertions of >1bp
                        if len(mut) - 1 > 1:
                            key_1 = len(mut) - 1
                            if key_1 < 5:
                                indel_key_1 = key_1
                            else:
                                indel_key_1 = 5

                            # Only regular insertions
                            if mut_type == "Ins":
                                indel_key_3 = "R"
                                key_4 = int(len(sequence) / key_1 - 1)
                                if key_4 < 5:
                                    indel_key_4 = key_4
                                else:
                                    indel_key_4 = 5
                            # Only for microhomologies
                            else:
                                indel_key_3 = "M"
                                key_4 = len(sequence) - (len(mut) - 1)
                                if key_4 >= 5:
                                    indel_key_4 = 5
                                elif key_4 < 0:
                                    print(lines)
                                else:
                                    indel_key_4 = key_4

                        # Includes insertions of 1bp
                        else:
                            indel_key_1 = 1
                            key_4 = len(sequence) - 1
                            if key_4 >= 5:
                                indel_key_4 = 5
                            else:
                                indel_key_4 = key_4

                            if mut[1] == "C" or mut[1] == "G":
                                indel_key_3 = "C"
                            else:
                                indel_key_3 = "T"

                    # Counts the number of "complex" mutations
                    else:
                        non_matching += 1

                    # Creates the final INDEl key and saves it into the data structure
                    indel_key_simple = ""
                    if len(type_sequence) < 6:
                        indel_key_complete = (
                            str(indel_key_1)
                            + ":"
                            + indel_key_2
                            + ":"
                            + type_sequence
                            + ":"
                            + str(indel_key_4)
                        )
                        indel_key_complete_rev = (
                            str(indel_key_1)
                            + ":"
                            + indel_key_2
                            + ":"
                            + revcompl(type_sequence)
                            + ":"
                            + str(indel_key_4)
                        )
                    else:
                        indel_key_complete = (
                            str(indel_key_1)
                            + ":"
                            + indel_key_2
                            + ":5:"
                            + str(indel_key_4)
                        )

                    if limited_indel and indel_key_2 == "Ins" and indel_key_3 == "M":
                        indel_key = (
                            str(indel_key_1) + ":" + indel_key_2 + ":" + "R" + ":" + "0"
                        )
                    else:
                        indel_key = (
                            str(indel_key_1)
                            + ":"
                            + indel_key_2
                            + ":"
                            + indel_key_3
                            + ":"
                            + str(indel_key_4)
                        )

                    if int(indel_key_1) > 1:
                        if indel_key_3 == "M":
                            indel_key_simple = "MH"
                        else:
                            indel_key_simple = "long_" + indel_key_2
                    else:
                        indel_key_simple = indel_key

                    if (
                        bool(re.match("^[CT]*$", sequence))
                        or bool(re.match("^[GA]*$", sequence))
                        or bias == "N"
                    ):
                        indel_key_tsb = bias + ":" + indel_key
                        mutation_ID["tsb"].at[indel_key_tsb, sample] += 1
                    else:
                        indel_key_tsb = "Q:" + indel_key
                        mutation_ID["tsb"].at[indel_key_tsb, sample] += 1
                        strand = 0

                    # Performs the gene strand bias test if desired
                    if gs:
                        if indel_key[0] == "1":
                            continue_flag = False
                            for ranges in gene_ranges[initial_chrom][range_index:]:
                                if start < ranges[0]:
                                    break
                                if ranges[0] <= start <= ranges[1]:
                                    continue_flag = True
                                    gene_index = gene_ranges[initial_chrom].index(
                                        ranges
                                    )
                                    gene = gene_names[initial_chrom][gene_index]
                                    if strand == ranges[2]:
                                        dict_key = "T"
                                        gene_counts[gene][dict_key] += 1
                                        if sample not in gene_counts[gene]["samples"]:
                                            gene_counts[gene]["samples"].append(sample)
                                            sample_mut_counts_per_gene[gene][sample] = 1
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ] = {"T": 0, "U": 0}
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ][dict_key] += 1

                                        else:
                                            sample_mut_counts_per_gene[gene][
                                                sample
                                            ] += 1
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ][dict_key] += 1
                                    elif int(strand) + int(ranges[2]) == 0:
                                        dict_key = "U"
                                        gene_counts[gene][dict_key] += 1
                                        if sample not in gene_counts[gene]["samples"]:
                                            gene_counts[gene]["samples"].append(sample)
                                            sample_mut_counts_per_gene[gene][sample] = 1
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ] = {"T": 0, "U": 0}
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ][dict_key] += 1
                                        else:
                                            sample_mut_counts_per_gene[gene][
                                                sample
                                            ] += 1
                                            sample_mut_counts_per_mut_type[gene][
                                                sample
                                            ][dict_key] += 1

                    mutation_ID["ID"].at[indel_key, sample] += 1
                    try:
                        mutation_ID["complete"].at[indel_key_complete, sample] += 1
                    except:
                        mutation_ID["complete"].at[indel_key_complete_rev, sample] += 1

                    mutation_ID["simple"].at[indel_key_simple, sample] += 1
                    total_analyzed += 1

                    # Writes the INDEL to a temporary file for exome/region sorting
                    if exome:
                        exome_file.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                        exome_file_simple.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key_simple
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                        exome_file_tsb.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key_tsb
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                    if bed:
                        bed_file.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                        bed_file_simple.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key_simple
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )
                        bed_file_tsb.write(
                            sample
                            + "\t"
                            + chrom
                            + "\t"
                            + str(start)
                            + "\t"
                            + indel_key_tsb
                            + "\t"
                            + ref
                            + "\t"
                            + mut
                            + "\n"
                        )

                    if seqInfo:
                        print(
                            "\t".join(
                                [
                                    sample,
                                    chrom,
                                    str(start),
                                    indel_key_tsb,
                                    ref,
                                    mut,
                                    str(strand),
                                ]
                            ),
                            file=seqOut,
                        )

                else:
                    if not functionFlag:
                        mutation_ID["ID"].at["non_matching", sample] += 1

            except:
                print(
                    "There appears to be an error in this line. Skipping this mutation: "
                    + chrom
                    + " "
                    + str(start)
                    + " "
                    + ref
                    + " "
                    + mut,
                    file=out,
                )
                skipped_count += 1

        # Once all of the variants have been account for, complete the gene strand bias test
        if gs:
            pvals = []
            qvals = []
            pvals_hot = []
            qvals_hot = []
            hotspots = {}
            for gene in gene_counts:
                total_count = sum(sample_mut_counts_per_gene[gene].values())
                for sample in sample_mut_counts_per_gene[gene]:
                    mut_count = sample_mut_counts_per_gene[gene][sample]
                    if mut_count > 10 and mut_count / total_count > 0.5:
                        if gene not in hotspots:
                            hotspots[gene] = {}
                            for mut, count in sample_mut_counts_per_mut_type[gene][
                                sample
                            ].items():
                                hotspots[gene][mut] = count
                            hotspots[gene]["samples"] = [sample]
                            for mut, count in sample_mut_counts_per_mut_type[gene][
                                sample
                            ].items():
                                gene_counts[gene][mut] -= count
                            gene_counts[gene]["samples"].remove(sample)
                        else:
                            for mut, count in sample_mut_counts_per_mut_type[gene][
                                sample
                            ].items():
                                hotspots[gene][mut] += count
                                gene_counts[gene][mut] -= count
                            gene_counts[gene]["samples"].remove(sample)
                            hotspots[gene]["samples"].append(sample)

                sum_tran = 0
                sum_untran = 0
                for mut, counts in gene_counts[gene].items():
                    if mut[0] == "T":
                        sum_tran += counts
                    elif mut[0] == "U":
                        sum_untran += counts
                n = sum_tran + sum_untran
                if n > 0:
                    pval = stats.binomtest(k=sum_tran, n=n).pvalue
                else:
                    pval = 1
                pvals.append(pval)

                sum_tran_hot = 0
                sum_untran_hot = 0
                if gene in hotspots:
                    for mut, counts in hotspots[gene].items():
                        if mut[0] == "T":
                            sum_tran_hot += counts
                        elif mut[0] == "U":
                            sum_untran_hot += counts
                n_hot = sum_tran_hot + sum_untran_hot
                if n_hot > 0:
                    pval_hot = stats.binomtest(k=sum_tran_hot, n=n_hot).pvalue
                else:
                    pval_hot = 1
                pvals_hot.append(pval_hot)

            qvals = sm.fdrcorrection(pvals)[1]
            qvals_hot = sm.fdrcorrection(pvals_hot)[1]
            gene_ind = 0
            for gene in gene_counts:
                gene_counts[gene]["samples"] = len(gene_counts[gene]["samples"])
                print(gene, end="", file=out, flush=False)
                sum_tran = 0
                sum_untran = 0
                for mut, counts in gene_counts[gene].items():
                    if mut[0] == "T":
                        sum_tran += counts
                    elif mut[0] == "U":
                        sum_untran += counts
                    print("\t" + str(counts), end="", file=out, flush=False)
                print("\t" + str(qvals[gene_ind]), flush=False, file=out)
                gene_ind += 1
            out.close()
            with open(output_matrix + "gene_strand_bias_counts_indel.txt") as f2:
                lines = [line.strip().split() for line in f2]
            output = open(output_matrix + "gene_strand_bias_counts_indel.txt", "w")
            print("GENE\tTranscribed\tUntranscribed\tSampleCount\tq_value", file=output)
            for line in sorted(lines, key=lambda x: (float(x[-1])), reverse=False):
                print("\t".join(line), file=output)
            output.close()

            # Performs gene strand bias test hot spot samples
            gene_ind = 0
            for gene in hotspots:
                hotspots[gene]["samples"] = len(hotspots[gene]["samples"])
                print(gene, end="", file=out_hot, flush=False)
                sum_tran_hot = 0
                sum_untran_hot = 0
                for mut, counts in hotspots[gene].items():
                    if mut[0] == "T":
                        sum_tran_hot += counts
                    elif mut[0] == "U":
                        sum_untran_hot += counts
                    print("\t" + str(counts), end="", file=out_hot, flush=False)
                print("\t" + str(qvals_hot[gene_ind]), flush=False, file=out_hot)
                gene_ind += 1
            out_hot.close()
            with open(
                output_matrix + "gene_strand_bias_counts_hotspots_indel.txt"
            ) as f2:
                lines = [line.strip().split() for line in f2]
            output = open(
                output_matrix + "gene_strand_bias_counts_hotspots_indel.txt", "w"
            )
            print(
                "GENE\tTranscribed\tUntranscribed\ttSampleCount\tq_value", file=output
            )
            for line in sorted(lines, key=lambda x: (float(x[-1])), reverse=False):
                print("\t".join(line), file=output)
            output.close()

    # Prints the total number of complex mutations
    # if chrom_based:
    # 	matrix_generator_INDEL(output_matrix, samples, indel_types, indel_types_tsb, indel_dict, indel_tsb_dict, indel_simple_dict, project, exome, limited_indel, bed, initial_chrom, plot)

    if seqInfo:
        seqOut.close()

    if exome:
        exome_file.close()
        exome_file_simple.close()
        exome_file_tsb.close()

    if bed:
        bed_file.close()
        bed_file_simple.close()
        bed_file_tsb.close()

    # Calls the function to generate the final mutational matrix
    if not chrom_based:
        initial_chrom = None
    if functionFlag:
        return (mutation_ID, skipped_count, total_analyzed)


# def exome_check (mutation_pd, genome, exome_temp_file, output_matrix, project, context, cushion, subcontext=None):
def exome_check(
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
    mutation_pd,
    genome,
    exome_temp_file,
    output_matrix,
    project,
    context,
    cushion,
    subcontext=None,
    volume=None,
):
    """
    Filters the variants for those present within the exome.

    Parameters:
                             genome  -> name of the genome of interest (ex: GRCh37)
            exome_temp_file  -> The temporary file that contains all of the variants used for filtering
              output_matrix  -> path to the final output matrix folder
                            project  -> name of the unique project

    Returns:
              mutation_dict  -> updated mutation dictionary for each sample for each mutation type post filtering
                            samples  -> updated list of samples that still contain mutations post filtering

    """

    # Instantiates the relevant variables/data structures
    base_cushion = cushion
    mutation_dict = {}
    # samples = []

    romanNumeralConversion = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
    }

    initial = True
    udpate_chrom = False
    reference_dir = ref_install.reference_dir()

    exome_file = str(reference_dir.get_exome_interval_list(genome))

    exome_output_path = output_matrix + "vcf_files/" + context + "/"
    if context == "ID":
        context = subcontext
    exome_output = exome_output_path + project + "_" + context + "_exome.vcf"
    if not os.path.exists(exome_output_path):
        os.makedirs(exome_output_path)

    save_chrom = None

    with open(exome_temp_file) as f, open(exome_file) as exome, open(
        exome_output, "w"
    ) as out:
        previous_chrom_ref = None
        previous_chrom_start = None
        previous_chrom_end = None

        save_mat = True
        chrom_ref = None
        start_ref = None
        end_ref = None

        read = True

        for lines in f:
            # Saves the relevant data for the current variant for later reference
            line = lines.strip().split()
            sample = line[0]
            chrom = line[1]
            start = int(line[2])
            mut_type = line[3]
            ref = line[4]
            mut = line[5]

            # Saves a value for the x and y chromosomes as a numeric reference
            if chrom == "X":
                chrom_value = -1
            elif chrom == "Y":
                chrom_value = 0
            elif chrom == "MT" or chrom == "M":
                chrom_value = 100
            elif chrom == "gi_82503188_ref_NC_007605":
                chrom_value = -1
            else:
                try:
                    chrom_value = int(chrom)
                except:
                    chrom_value = romanNumeralConversion[chrom]

            if initial:
                chrom_start = chrom
                save_chrom = chrom
                initial = False

            if chrom != save_chrom:
                if chrom_based:
                    if save_mat:
                        mut_count_all = {}
                        mut_count_all["6144"] = mutation_pd
                        if context == "83":
                            mut_count_all["ID"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                mut_types,
                                None,
                                None,
                                mut_count_all["ID"],
                                None,
                                None,
                                None,
                                project,
                                exome,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "simple":
                            mut_count_all["simple"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                None,
                                None,
                                mut_types,
                                None,
                                None,
                                mut_count_all["simple"],
                                None,
                                project,
                                exome,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "tsb":
                            mut_count_all["tsb"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                None,
                                mut_types,
                                None,
                                None,
                                mut_count_all["tsb"],
                                None,
                                None,
                                project,
                                exome,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "SNV":
                            mut_count_all["6144"] = mutation_pd
                            matrices = matrix_generator(
                                "6144",
                                output_matrix,
                                project,
                                samples,
                                bias_sort,
                                mut_count_all,
                                exome,
                                mut_types,
                                bed,
                                save_chrom,
                                functionFlag,
                                plot,
                                tsb_stat,
                                volume=volume,
                            )
                        elif context == "DBS":
                            dinuc_mat = matrix_generator_DINUC(
                                output_matrix,
                                samples,
                                bias_sort,
                                mutation_pd,
                                mut_types,
                                project,
                                exome,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )

                        mutation_pd = {}
                        mutation_pd = pd.DataFrame(0, index=mut_types, columns=samples)
                save_chrom = chrom

            stop = False
            while not stop:
                if chrom == previous_chrom_ref:
                    if (
                        start >= previous_chrom_start - base_cushion
                        and start <= previous_chrom_end + base_cushion
                    ):
                        mutation_pd.at[mut_type, sample] += 1
                        read = True
                        print("\t".join([chrom, str(start), ".", ref, mut]), file=out)
                        break

                if read:
                    lines2 = exome.readline()
                try:
                    if lines2[0] == "@":
                        continue
                except:
                    break
                else:
                    line2 = lines2.strip().split()
                    chrom_ref = line2[0]
                    if len(chrom_ref) > 2:
                        chrom_ref = chrom_ref[3:]
                    start_ref = int(line2[1])
                    end_ref = int(line2[2])

                    if chrom_ref == "X":
                        ref_chrom_value = -1
                    elif chrom_ref == "Y":
                        ref_chrom_value = 0
                    elif chrom_ref == "MT" or chrom_ref == "M":
                        ref_chrom_value = 100
                    elif chrom_ref == "gi_82503188_ref_NC_007605":
                        ref_chrom_value = -1
                    else:
                        try:
                            ref_chrom_value = int(chrom_ref)
                        except:
                            ref_chrom_value = romanNumeralConversion[chrom_ref]

                    if chrom == chrom_ref:
                        save_mat = True
                        if start > (
                            start_ref - base_cushion and end_ref + base_cushion
                        ):
                            read = True
                            continue
                        elif (
                            start >= start_ref - base_cushion
                            and start <= end_ref + base_cushion
                        ):
                            mutation_pd.at[mut_type, sample] += 1
                            read = True
                            print(
                                "\t".join([chrom, str(start), ".", ref, mut]), file=out
                            )
                            break
                        elif start < (start_ref - base_cushion):
                            read = False
                            break

                    else:
                        if chrom_value < ref_chrom_value:
                            read = False
                            break
                        elif chrom_value > ref_chrom_value:
                            read = True
                            continue

            chrom_start = chrom
            previous_chrom_ref = chrom_ref
            previous_chrom_start = start_ref
            previous_chrom_end = end_ref

    if chrom_based:
        mut_count_all = {}
        if context == "83":  # or context == 'simple' or context == 'tsb':
            mut_count_all["ID"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                mut_types,
                None,
                None,
                mut_count_all["ID"],
                None,
                None,
                None,
                project,
                exome,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "simple":
            mut_count_all["simple"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                None,
                None,
                mut_types,
                None,
                None,
                mut_count_all["simple"],
                None,
                project,
                exome,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "tsb":
            mut_count_all["tsb"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                None,
                mut_types,
                None,
                None,
                mut_count_all["tsb"],
                None,
                None,
                project,
                exome,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "SNV":
            mut_count_all["6144"] = mutation_pd
            matrices = matrix_generator(
                "6144",
                output_matrix,
                project,
                samples,
                bias_sort,
                mut_count_all,
                exome,
                mut_types,
                bed,
                save_chrom,
                functionFlag,
                plot,
                tsb_stat,
                volume=volume,
            )
        elif context == "DBS":
            dinuc_mat = matrix_generator_DINUC(
                output_matrix,
                samples,
                bias_sort,
                mutation_pd,
                mut_types,
                project,
                exome,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )

    return (mutation_pd, samples)


def panel_check(
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
    mutation_pd,
    genome,
    bed_temp_file,
    output_matrix,
    bed_file_path,
    project,
    context,
    cushion,
    subcontext=None,
    volume=None,
):
    """
    Filters the variants for those present within the exome.

    Parameters:
                             genome  -> name of the genome of interest (ex: GRCh37)
            exome_temp_file  -> The temporary file that contains all of the variants used for filtering
              output_matrix  -> path to the final output matrix folder
              bed_file_path  -> path to the bed file
                            project  -> unique project name


    Returns:
              mutation_dict  -> updated mutation dictionary for each sample for each mutation type post filtering
                            samples  -> updated list of samples that still contain mutations post filtering

    """

    # Instantiates the relevant variables/data structures
    base_cushion = cushion
    # samples = []
    reference_dir = ref_install.reference_dir()
    ref_dir = str(reference_dir.path)

    romanNumeralConversion = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10,
        "XI": 11,
        "XII": 12,
        "XIII": 13,
        "XIV": 14,
        "XV": 15,
        "XVI": 16,
    }

    initial = True
    udpate_chrom = False
    panel_file = BED_sorting(bed_file_path, genome=genome)
    panel_output_path = output_matrix + "vcf_files/" + context + "/"

    if context == "ID":
        context = subcontext
    panel_output = panel_output_path + project + "_" + context + "_panel.vcf"

    if not os.path.exists(panel_output_path):
        os.makedirs(panel_output_path)

    with open(bed_temp_file) as f, open(panel_file) as exome, open(
        panel_output, "w"
    ) as out:
        previous_chrom_ref = None
        previous_chrom_start = None
        previous_chrom_end = None
        save_mat = True

        chrom_ref = None
        start_ref = None
        end_ref = None

        read = True

        for lines in f:
            # Saves the relevant data for the current variant for later reference
            line = lines.strip().split()
            sample = line[0]
            chrom = line[1]
            start = int(line[2])
            mut_type = line[3]
            ref = line[4]
            mut = line[5]

            # Saves a value for the x and y chromosomes as a numeric reference
            if genome == "yeast":
                if chrom == "X":
                    chrom_value = 10  # Keep "X" as value 10
                elif chrom == "MT" or chrom == "M" or chrom == "MtDNA":
                    chrom_value = 100
                else:
                    chrom_value = romanNumeralConversion[chrom]
            else:
                if chrom == "X":
                    chrom_value = -1
                elif chrom == "Y":
                    chrom_value = 0
                elif chrom == "MT" or chrom == "M" or chrom == "MtDNA":
                    chrom_value = 100
                elif chrom == "gi_82503188_ref_NC_007605":
                    chrom_value = -1
                else:
                    try:
                        chrom_value = int(chrom)
                    except:
                        chrom_value = romanNumeralConversion[chrom]

            if initial:
                chrom_start = chrom
                save_chrom = chrom
                initial = False
            if chrom != save_chrom:
                if chrom_based:
                    if save_mat:
                        mut_count_all = {}
                        if context == "83":
                            mut_count_all["ID"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                mut_types,
                                None,
                                None,
                                mut_count_all["ID"],
                                None,
                                None,
                                None,
                                project,
                                None,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "simple":
                            mut_count_all["simple"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                None,
                                None,
                                mut_types,
                                None,
                                None,
                                mut_count_all["simple"],
                                None,
                                project,
                                None,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "tsb":
                            mut_count_all["tsb"] = mutation_pd
                            matrix_generator_INDEL(
                                output_matrix,
                                samples,
                                None,
                                mut_types,
                                None,
                                None,
                                mut_count_all["tsb"],
                                None,
                                None,
                                project,
                                None,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        elif context == "SNV":
                            mut_count_all["6144"] = mutation_pd
                            matrices = matrix_generator(
                                "6144",
                                output_matrix,
                                project,
                                samples,
                                bias_sort,
                                mut_count_all,
                                None,
                                mut_types,
                                bed,
                                save_chrom,
                                functionFlag,
                                plot,
                                tsb_stat,
                                volume=volume,
                            )
                        elif context == "DBS":
                            dinuc_mat = matrix_generator_DINUC(
                                output_matrix,
                                samples,
                                bias_sort,
                                mutation_pd,
                                mut_types,
                                project,
                                None,
                                bed,
                                save_chrom,
                                plot,
                                volume=volume,
                            )
                        mutation_pd = {}
                        mutation_pd = pd.DataFrame(0, index=mut_types, columns=samples)
                        save_mat = False
                save_chrom = chrom

            stop = False
            while not stop:
                if chrom == previous_chrom_ref:
                    if (
                        start >= previous_chrom_start - base_cushion
                        and start <= previous_chrom_end + base_cushion
                    ):
                        mutation_pd.at[mut_type, sample] += 1
                        # read = True
                        print("\t".join([chrom, str(start), ".", ref, mut]), file=out)
                        break

                if read:
                    lines2 = exome.readline()
                try:
                    if lines2[0] == "@" or lines2[0] == "#":
                        continue
                except:
                    break
                else:
                    line2 = lines2.strip().split("\t")
                    chrom_ref = line2[0]
                    # if len(chrom_ref) > 2:
                    #     chrom_ref = chrom_ref[3:]
                    start_ref = int(line2[1])
                    end_ref = int(line2[2])
                    if genome == "yeast":
                        if chrom_ref == "X":
                            ref_chrom_value = 10  # Keep "X" as value 10
                        elif (
                            chrom_ref == "MT"
                            or chrom_ref == "M"
                            or chrom_ref == "MtDNA"
                        ):
                            ref_chrom_value = 100
                        else:
                            ref_chrom_value = romanNumeralConversion[chrom_ref]
                    else:
                        if chrom_ref == "X":
                            ref_chrom_value = -1
                        elif chrom_ref == "Y":
                            ref_chrom_value = 0
                        elif (
                            chrom_ref == "MT"
                            or chrom_ref == "M"
                            or chrom_ref == "MtDNA"
                        ):
                            ref_chrom_value = 100
                        elif chrom_ref == "gi_82503188_ref_NC_007605":
                            ref_chrom_value = -1
                        else:
                            try:
                                ref_chrom_value = int(chrom_ref)
                            except:
                                ref_chrom_value = romanNumeralConversion[chrom_ref]

                    if chrom == chrom_ref:
                        save_mat = True
                        if start > (
                            start_ref - base_cushion and end_ref + base_cushion
                        ):
                            read = True
                            continue
                        elif (
                            start >= start_ref - base_cushion
                            and start <= end_ref + base_cushion
                        ):
                            mutation_pd.at[mut_type, sample] += 1
                            # read = True
                            print(
                                "\t".join([chrom, str(start), ".", ref, mut]), file=out
                            )
                            break
                        elif start < (start_ref - base_cushion):
                            read = False
                            break

                    else:
                        if chrom_value < ref_chrom_value:
                            read = False
                            break
                        elif chrom_value > ref_chrom_value:
                            read = True
                            continue

            chrom_start = chrom
            previous_chrom_ref = chrom_ref
            previous_chrom_start = start_ref
            previous_chrom_end = end_ref

    if chrom_based:
        mut_count_all = {}
        if context == "83":
            mut_count_all["ID"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                mut_types,
                None,
                None,
                mut_count_all["ID"],
                None,
                None,
                None,
                project,
                None,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "simple":
            mut_count_all["simple"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                None,
                None,
                mut_types,
                None,
                None,
                mut_count_all["simple"],
                None,
                project,
                None,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "tsb":
            mut_count_all["tsb"] = mutation_pd
            matrix_generator_INDEL(
                output_matrix,
                samples,
                None,
                mut_types,
                None,
                None,
                mut_count_all["tsb"],
                None,
                None,
                project,
                None,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )
        elif context == "SNV":
            mut_count_all["6144"] = mutation_pd
            matrices = matrix_generator(
                "6144",
                output_matrix,
                project,
                samples,
                bias_sort,
                mut_count_all,
                None,
                mut_types,
                bed,
                save_chrom,
                functionFlag,
                plot,
                tsb_stat,
                volume=volume,
            )
        elif context == "DBS":
            dinuc_mat = matrix_generator_DINUC(
                output_matrix,
                samples,
                bias_sort,
                mutation_pd,
                mut_types,
                project,
                None,
                bed,
                save_chrom,
                plot,
                volume=volume,
            )

    return (mutation_pd, samples)


def matrix_generator(
    context,
    output_matrix,
    project,
    samples,
    bias_sort,
    mut_count_all,
    exome,
    mut_types,
    bed,
    chrom_start=None,
    functionFlag=False,
    plot=False,
    tsb_stat=False,
    volume=None,
):
    """
    Writes the final mutational matrix given a dictionary of samples, mutation types, and counts

    Parameters:
                                    context  -> desired context (ex. 96, 1536, 384, 6144)
                      output_matrix  -> path where the final mutational matrix is stored
                                    project  -> unique name given to the set of samples (ex. 'BRCA')
                                     samples -> a list of all sample names
                               bias_sort -> dictionary that provides the sorting order for the TSB matrices
                     muatation_dict  -> dictionary with the counts for each mutation type for each sample
                                      exome  -> Boolean for whether the catalogue should be generated across the whole
                                                            genome or just the exome
                              mut_types  -> list with all possible mutation types for the given context
                                            bed  -> parameter used to filter the mutations on a user-provided BED file
                            chrom_start  -> current chromosome when generating the matrix on a chromosome basis
                       functionFlag  -> flag that will return the matrix in memory.
                                       plot  -> flag that will generate the plots for each context
                               tsb_stat  -> performs a transcriptional strand bias test for the 24, 384, and 6144 contexts. The output is
                                                            saved into the output/TSB directory


    Returns:
            None

    Output:
            Write the final mutational matrix for 96, 384, 1536, 6144 contexts

    """

    # Prepares all of the required data structures and files
    reference_dir = ref_install.reference_dir()
    ref_dir = str(reference_dir.path)

    contexts = ["96", "384", "1536", "6", "24", "288", "4608", "18"]
    mut_count_all["6144"].index.name = "MutationType"

    mut_count_all["6144"] = mut_count_all["6144"].astype(int)
    mut_count_all["384"] = (
        mut_count_all["6144"]
        .groupby(
            mut_count_all["6144"].index.str[0:2] + mut_count_all["6144"].index.str[3:10]
        )
        .sum()
    )
    mut_count_all["1536"] = (
        mut_count_all["6144"].groupby(mut_count_all["6144"].index.str[2:]).sum()
    )
    mut_count_all["96"] = (
        mut_count_all["1536"].groupby(mut_count_all["1536"].index.str[1:8]).sum()
    )
    mut_count_all["6"] = (
        mut_count_all["96"].groupby(mut_count_all["96"].index.str[2:5]).sum()
    )
    mut_count_all["24"] = (
        mut_count_all["384"]
        .groupby(
            mut_count_all["384"].index.str[0:2] + mut_count_all["384"].index.str[4:7]
        )
        .sum()
    )

    # Collapse the Bi-directionally transcribed type to transcribed and untranscribed
    # 6144 to 4608
    # trans = mut_count_all['6144'][mut_count_all['6144'].index.str.contains('T:')]
    # untrans = mut_count_all['6144'][mut_count_all['6144'].index.str.contains('U:')]
    # bitrans = mut_count_all['6144'][mut_count_all['6144'].index.str.contains('B:')]
    # nontrans = mut_count_all['6144'][mut_count_all['6144'].index.str.contains('N:')]
    # a = bitrans//2
    # b = bitrans%2
    # trans = trans.append(a)
    # trans  = trans.groupby(trans.index.str[2:]).sum()
    # trans = trans.rename(index=lambda s: "T:"+s)
    # untrans = untrans.append(a)
    # untrans = untrans.groupby(untrans.index.str[2:]).sum()
    # untrans = untrans.rename(index=lambda s:"U:"+s)
    # mut_count_all['4608'] = pd.concat([trans, untrans, nontrans])
    # for x in list(b.index):
    # 	mutAbrrev = x.split(":")[1]
    # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
    # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
    # 		mut_count_all['4608'].loc[z,y] += b.loc[x,y]
    # mut_count_all['288'] = mut_count_all['4608'].groupby(mut_count_all['4608'].index.str[0:2] + mut_count_all['4608'].index.str[3:10]).sum()
    # mut_count_all['18'] = mut_count_all['288'].groupby(mut_count_all['288'].index.str[0:2] + mut_count_all['288'].index.str[4:7]).sum()

    # # 384 to 288
    # trans = mut_count_all['384'][mut_count_all['384'].index.str.contains('T:')]
    # untrans = mut_count_all['384'][mut_count_all['384'].index.str.contains('U:')]
    # bitrans = mut_count_all['384'][mut_count_all['384'].index.str.contains('B:')]
    # nontrans = mut_count_all['384'][mut_count_all['384'].index.str.contains('N:')]
    # a = bitrans//2
    # b = bitrans%2
    # trans = trans.append(a)
    # trans  = trans.groupby(trans.index.str[2:]).sum()
    # trans = trans.rename(index=lambda s: "T:"+s)
    # untrans = untrans.append(a)
    # untrans = untrans.groupby(untrans.index.str[2:]).sum()
    # untrans = untrans.rename(index=lambda s:"U:"+s)
    # mut_count_all['288'] = pd.concat([trans, untrans, nontrans])
    # for x in list(b.index):
    # 	mutAbrrev = x.split(":")[1]
    # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
    # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
    # 		mut_count_all['288'].loc[z,y] += b.loc[x,y]

    # # 24 to 18
    # trans = mut_count_all['24'][mut_count_all['24'].index.str.contains('T:')]
    # untrans = mut_count_all['24'][mut_count_all['24'].index.str.contains('U:')]
    # bitrans = mut_count_all['24'][mut_count_all['24'].index.str.contains('B:')]
    # nontrans = mut_count_all['24'][mut_count_all['24'].index.str.contains('N:')]
    # a = bitrans//2
    # b = bitrans%2
    # trans = trans.append(a)
    # trans  = trans.groupby(trans.index.str[2:]).sum()
    # trans = trans.rename(index=lambda s: "T:"+s)
    # untrans = untrans.append(a)
    # untrans = untrans.groupby(untrans.index.str[2:]).sum()
    # untrans = untrans.rename(index=lambda s:"U:"+s)
    # mut_count_all['18'] = pd.concat([trans, untrans, nontrans])
    # for x in list(b.index):
    # 	mutAbrrev = x.split(":")[1]
    # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
    # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
    # 		mut_count_all['18'].loc[z,y] += b.loc[x,y]
    # mut_count_all['288'] = mut_count_all['4608'].groupby(mut_count_all['4608'].index.str[0:2] + mut_count_all['4608'].index.str[3:10]).sum()
    # mut_count_all['18'] = mut_count_all['288'].groupby(mut_count_all['288'].index.str[0:2] + mut_count_all['288'].index.str[4:7]).sum()

    # Collapses the Bi-directionally transcribed regions
    # 6144 to 4608
    trans = mut_count_all["6144"][mut_count_all["6144"].index.str.contains("T:")]
    untrans = mut_count_all["6144"][mut_count_all["6144"].index.str.contains("U:")]
    bitrans = mut_count_all["6144"][mut_count_all["6144"].index.str.contains("B:")]
    nontrans = mut_count_all["6144"][mut_count_all["6144"].index.str.contains("N:")]
    a = bitrans // 2
    b = bitrans % 2
    trans = pd.concat([trans, a, b])
    trans = trans.groupby(trans.index.str[2:]).sum()
    trans = trans.rename(index=lambda s: "T:" + s)
    untrans = pd.concat([untrans, a])
    untrans = untrans.groupby(untrans.index.str[2:]).sum()
    untrans = untrans.rename(index=lambda s: "U:" + s)
    mut_count_all["4608"] = pd.concat([trans, untrans, nontrans])

    # mut_count_all['288'] = mut_count_all['4608'].groupby(mut_count_all['4608'].index.str[0:2] + mut_count_all['4608'].index.str[3:10]).sum()
    # mut_count_all['18'] = mut_count_all['288'].groupby(mut_count_all['288'].index.str[0:2] + mut_count_all['288'].index.str[4:7]).sum()

    # 384 to 288
    trans = mut_count_all["384"][mut_count_all["384"].index.str.contains("T:")]
    untrans = mut_count_all["384"][mut_count_all["384"].index.str.contains("U:")]
    bitrans = mut_count_all["384"][mut_count_all["384"].index.str.contains("B:")]
    nontrans = mut_count_all["384"][mut_count_all["384"].index.str.contains("N:")]
    a = bitrans // 2
    b = bitrans % 2
    trans = pd.concat([trans, a, b])
    trans = trans.groupby(trans.index.str[2:]).sum()
    trans = trans.rename(index=lambda s: "T:" + s)
    untrans = pd.concat([untrans, a])
    untrans = untrans.groupby(untrans.index.str[2:]).sum()
    untrans = untrans.rename(index=lambda s: "U:" + s)
    mut_count_all["288"] = pd.concat([trans, untrans, nontrans])

    # 24 to 18
    trans = mut_count_all["24"][mut_count_all["24"].index.str.contains("T:")]
    untrans = mut_count_all["24"][mut_count_all["24"].index.str.contains("U:")]
    bitrans = mut_count_all["24"][mut_count_all["24"].index.str.contains("B:")]
    nontrans = mut_count_all["24"][mut_count_all["24"].index.str.contains("N:")]
    a = bitrans // 2
    b = bitrans % 2
    trans = pd.concat([trans, a, b])
    trans = trans.groupby(trans.index.str[2:]).sum()
    trans = trans.rename(index=lambda s: "T:" + s)
    untrans = pd.concat([untrans, a])
    untrans = untrans.groupby(untrans.index.str[2:]).sum()
    untrans = untrans.rename(index=lambda s: "U:" + s)
    mut_count_all["18"] = pd.concat([trans, untrans, nontrans])

    mut_count_all["1536"].index.name = "MutationType"
    mut_count_all["96"].index.name = "MutationType"
    mut_count_all["6"].index.name = "MutationType"
    mut_count_all["384"].index.name = "MutationType"
    mut_count_all["24"].index.name = "MutationType"

    mut_count_all["4608"].index.name = "MutationType"
    mut_count_all["288"].index.name = "MutationType"
    mut_count_all["18"].index.name = "MutationType"

    strandBiasOut = output_matrix + "TSB/"
    output_matrix_SBS = output_matrix + "SBS/"

    if not os.path.exists(output_matrix_SBS):
        os.mkdir(output_matrix_SBS)

    file_prefix = project + ".SBS" + context
    if exome:
        output_file_matrix = output_matrix_SBS + file_prefix + ".exome"
    else:
        if bed:
            output_file_matrix = output_matrix_SBS + file_prefix + ".region"
        else:
            output_file_matrix = output_matrix_SBS + file_prefix + ".all"

    if chrom_start != None:
        output_file_matrix += ".chr" + chrom_start

    types = list(mut_count_all["6144"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["6144"] = mut_count_all["6144"].reindex(types)

    types = list(mut_count_all["4608"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["4608"] = mut_count_all["4608"].reindex(types)

    types = list(mut_count_all["384"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["384"] = mut_count_all["384"].reindex(types)

    types = list(mut_count_all["288"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["288"] = mut_count_all["288"].reindex(types)

    types = list(mut_count_all["24"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["24"] = mut_count_all["24"].reindex(types)

    types = list(mut_count_all["18"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["18"] = mut_count_all["18"].reindex(types)

    df2csv(mut_count_all["6144"], output_file_matrix)

    # TSB test:
    if tsb_stat:
        types_7pN = list(mut_count_all["24"].index)
        types.append("T:T>CpN")
        types.append("U:T>CpN")
        types_7pN = list(mut_count_all["384"].index)

        mut_count_all["6_pvalue_temp"] = mut_count_all["24"]
        mut_count_all["7_pvalue_temp"] = mut_count_all["384"]
        mut_count_all["6_pvalue"] = mut_count_all["6"]
        mut_count_all["7_pvalue"] = mut_count_all["6"]

        mut_count_all["6_pvalue"] = mut_count_all["6"].to_dict("dict")
        mut_count_all["7_pvalue"] = mut_count_all["6"].to_dict("dict")

        drop_muts = [
            "T:A[T>C]A",
            "T:A[T>C]C",
            "T:A[T>C]G",
            "T:A[T>C]T",
            "U:A[T>C]A",
            "U:A[T>C]C",
            "U:A[T>C]G",
            "U:A[T>C]T",
            "B:A[T>C]A",
            "B:A[T>C]C",
            "B:A[T>C]G",
            "B:A[T>C]T",
            "N:A[T>C]A",
            "N:A[T>C]C",
            "N:A[T>C]G",
            "N:A[T>C]T",
        ]
        add_counts_T = []
        add_counts_U = []
        add_counts_B = []
        add_counts_N = []

        for mut in drop_muts:
            mut_count_all["7_pvalue_temp"] = mut_count_all["7_pvalue_temp"].drop(mut)
            if mut[0] == "T":
                add_counts_T.append(mut_count_all["384"].loc[mut])
            elif mut[0] == "U":
                add_counts_U.append(mut_count_all["384"].loc[mut])
            elif mut[0] == "B":
                add_counts_B.append(mut_count_all["384"].loc[mut])
            elif mut[0] == "N":
                add_counts_N.append(mut_count_all["384"].loc[mut])

        # don't combine the categories like that. Need to keep TSB categories
        mut_count_all["7_pvalue_temp"] = (
            mut_count_all["7_pvalue_temp"]
            .groupby(
                mut_count_all["7_pvalue_temp"].index.str[0:2]
                + mut_count_all["7_pvalue_temp"].index.str[4:7]
            )
            .sum()
        )

        mut_count_all["7_pvalue_temp"].loc["T:T>CpN"] = sum(add_counts_T)
        mut_count_all["7_pvalue_temp"].loc["U:T>CpN"] = sum(add_counts_U)
        mut_count_all["7_pvalue_temp"].loc["B:T>CpN"] = sum(add_counts_B)
        mut_count_all["7_pvalue_temp"].loc["N:T>CpN"] = sum(add_counts_N)

        function_tsb_test = ["6_pvalue_temp", "7_pvalue_temp"]
        for cont in function_tsb_test:
            cont_save = cont[:8]
            if cont == "6_pvalue_temp":
                types = list(mut_count_all["24"].index)
            else:
                types = list(mut_count_all["24"].index)
                types.append("T:T>CpN")
                types.append("U:T>CpN")
            types = list(set(types))
            current_tsb = mut_count_all[cont]
            for sample in samples:
                pvals = []
                for mut_type in types:
                    if mut_type[0] == "T":
                        successes = current_tsb.loc[mut_type][sample]
                        total_trials = (
                            successes + current_tsb.loc["U:" + mut_type[2:]][sample]
                        )

                        if total_trials > 0:
                            pval = stats.binomtest(k=successes, n=total_trials).pvalue
                        else:
                            pval = 1

                        if (
                            current_tsb.loc[mut_type][sample]
                            >= current_tsb.loc["U:" + mut_type[2:]][sample]
                        ):
                            strand_test = 1
                        else:
                            strand_test = -1
                        mut_count_all[cont_save][sample][mut_type[2:]] = [
                            pval,
                            strand_test,
                        ]

        mut_count_all["6_pvalue"] = pd.DataFrame.from_dict(mut_count_all["6_pvalue"])
        mut_count_all["7_pvalue"] = pd.DataFrame.from_dict(mut_count_all["7_pvalue"])

        if not os.path.exists(strandBiasOut):
            os.mkdir(strandBiasOut)
        significant_tsb = open(
            strandBiasOut + "significantResults_strandBiasTest.txt", "w"
        )
        with open(strandBiasOut + "strandBiasTest_6144.txt", "w") as out2, open(
            strandBiasOut + "strandBiasTest_384.txt", "w"
        ) as out384, open(strandBiasOut + "strandBiasTest_24.txt", "w") as out24:
            print(
                "Sample\tMutationType\tEnrichment[Trans/UnTrans]\tp.value\tFDR_q.value",
                file=out2,
            )
            tsb_6144 = mut_count_all["6144"][mut_count_all["6144"].index.str[0] == "T"]
            tsb_6144_U = mut_count_all["6144"][
                mut_count_all["6144"].index.str[0] == "U"
            ]
            tsb_index = [x[2:] for x in list(tsb_6144.index)]
            tsb_6144.index = tsb_index
            tsb_6144_U.index = tsb_index

            tsb_384 = mut_count_all["384"][mut_count_all["384"].index.str[0] == "T"]
            tsb_384_U = mut_count_all["384"][mut_count_all["384"].index.str[0] == "U"]
            tsb_index384 = [x[2:] for x in list(tsb_384.index)]
            tsb_384.index = tsb_index384
            tsb_384_U.index = tsb_index384

            tsb_24 = mut_count_all["24"][mut_count_all["24"].index.str[0] == "T"]
            tsb_24_U = mut_count_all["24"][mut_count_all["24"].index.str[0] == "U"]
            tsb_index24 = [x[2:] for x in list(tsb_24.index)]
            tsb_24.index = tsb_index24
            tsb_24_U.index = tsb_index24

            enr = tsb_6144 / tsb_6144_U
            enr_384 = tsb_384 / tsb_384_U
            enr_24 = tsb_24 / tsb_24_U

            for sample in samples:
                pvals = []
                pvals_384 = []
                pvals_24 = []
                enrichment = list(enr[sample])
                enrichment_384 = list(enr[sample])
                enrichment_24 = list(enr[sample])

                for i in range(len(tsb_6144)):
                    successes = tsb_6144[sample][i]
                    total_trials = successes + tsb_6144_U[sample][i]
                    if total_trials > 0:
                        pval = stats.binomtest(k=successes, n=total_trials).pvalue
                    else:
                        pval = 1
                    pvals.append(pval)

                for i in range(len(tsb_384)):
                    successes = tsb_384[sample][i]
                    total_trials = successes + tsb_384_U[sample][i]
                    if total_trials > 0:
                        pval = stats.binomtest(k=successes, n=total_trials).pvalue
                    else:
                        pval = 1
                    pvals_384.append(pval)

                for i in range(len(tsb_24)):
                    successes = tsb_24[sample][i]
                    total_trials = successes + tsb_24_U[sample][i]
                    if total_trials > 0:
                        pval = stats.binomtest(k=successes, n=total_trials).pvalue
                    else:
                        pval = 1
                    pvals_24.append(pval)

                qvals = sm.fdrcorrection(pvals)[1]
                qvals_384 = sm.fdrcorrection(pvals_384)[1]
                qvals_24 = sm.fdrcorrection(pvals_24)[1]
                p_index = 0
                for mut in tsb_index:
                    print(
                        sample
                        + "\t"
                        + mut
                        + "\t"
                        + str(enrichment[p_index])
                        + "\t"
                        + str(pvals[p_index])
                        + "\t"
                        + str(qvals[p_index]),
                        file=out2,
                    )
                    if qvals[p_index] < 0.01:
                        print(
                            sample
                            + "\t"
                            + mut
                            + "\t"
                            + str(enrichment[p_index])
                            + "\t"
                            + str(pvals[p_index])
                            + "\t"
                            + str(qvals[p_index]),
                            file=significant_tsb,
                        )
                    p_index += 1

                p_index = 0
                for mut in tsb_index384:
                    print(
                        sample
                        + "\t"
                        + mut
                        + "\t"
                        + str(enrichment_384[p_index])
                        + "\t"
                        + str(pvals_384[p_index])
                        + "\t"
                        + str(qvals_384[p_index]),
                        file=out384,
                    )
                    if qvals_384[p_index] < 0.01:
                        print(
                            sample
                            + "\t"
                            + mut
                            + "\t"
                            + str(enrichment_384[p_index])
                            + "\t"
                            + str(pvals_384[p_index])
                            + "\t"
                            + str(qvals_384[p_index]),
                            file=significant_tsb,
                        )
                    p_index += 1

                p_index = 0
                for mut in tsb_index24:
                    print(
                        sample
                        + "\t"
                        + mut
                        + "\t"
                        + str(enrichment_24[p_index])
                        + "\t"
                        + str(pvals_24[p_index])
                        + "\t"
                        + str(qvals_24[p_index]),
                        file=out24,
                    )
                    if qvals_24[p_index] < 0.01:
                        print(
                            sample
                            + "\t"
                            + mut
                            + "\t"
                            + str(enrichment_24[p_index])
                            + "\t"
                            + str(pvals_24[p_index])
                            + "\t"
                            + str(qvals_24[p_index]),
                            file=significant_tsb,
                        )
                    p_index += 1
        significant_tsb.close()

    # Generates the matrices for the remaining matrices (1536, 384, 96, 24, 6) by
    # summing the counts from the 6144 matrix
    for cont in contexts:
        file_prefix = project + ".SBS" + cont
        if exome:
            output_file_matrix = output_matrix_SBS + file_prefix + ".exome"
        else:
            if bed:
                output_file_matrix = output_matrix_SBS + file_prefix + ".region"
            else:
                output_file_matrix = output_matrix_SBS + file_prefix + ".all"

        if chrom_start != None:
            output_file_matrix += ".chr" + chrom_start
        df2csv(mut_count_all[cont], output_file_matrix)

        if plot:
            output_path = output_matrix + "plots/"
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            file_name = project
            if exome:
                file_name += "_exome"
            if bed:
                file_name += "_region"
            if chrom_start != None:
                file_name += "_chr" + chrom_start
            if cont == "96":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "96",
                        False,
                        volume=volume,
                    )
                except:
                    pass
            elif cont == "384":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "384",
                        False,
                        volume=volume,
                    )
                except:
                    pass
            elif cont == "6":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "6",
                        False,
                        volume=volume,
                    )
                except:
                    pass
            elif cont == "24":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "24",
                        False,
                        volume=volume,
                    )
                except:
                    pass
            elif cont == "1536":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "1536",
                        False,
                        volume=volume,
                    )
                except:
                    pass
            elif cont == "288":
                try:
                    sigPlt.plotSBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        "288",
                        False,
                        volume=volume,
                    )
                except:
                    pass

    # If this code is run as an imported function, delete the physcial matrix.
    if functionFlag:
        return mut_count_all


def matrix_generator_INDEL(
    output_matrix,
    samples,
    indel_types,
    indel_types_tsb,
    indel_types_simple,
    indel_dict,
    indel_tsb_dict,
    indel_simple_dict,
    indel_dict_complete,
    project,
    exome,
    limited_indel,
    bed,
    initial_chrom=None,
    plot=False,
    volume=None,
):
    """
    Writes the final mutational matrix for INDELS given a dictionary of samples, INDEL types, and counts

    Parameters:
                      output_matrix  -> path where the final mutational matrix is stored
                                    samples  -> a list of all sample names
                            indel_types  -> list of the INDEL types
                    indel_types_tsb  -> list of the INDEL types for the TSB matrix
             indel_types_simple  -> list of the INDEL types for the simple categories matrix
                             indel_dict  -> dictionary with the counts for each INDEL type for each sample
                     indel_tsb_dict  -> dictionary with the TSB counts for each INDEL type (only 1bp INDELs)
              indel_simple_dict  -> dictionary with the counts for each simple INDEL type
                                    project  -> unique name given to the set of samples (ex. 'BRCA')
                                      exome  -> Boolean for whether the catalogue should be generated across the whole
                                                            genome or just the exome
                      limited_indel  -> flag that instructs the function to create the a limited indel matrix
                                            bed  -> parameter used to filter the mutations on a user-provided BED file
                      initial_chrom  -> the current chromosome to generate the matrix for.
                                       plot  -> flag that will generate the INDEL plots for the provided samples.

    Returns:
            None

    Output:
            Write the final mutational matrix for INDELS

    """

    # Instantiates all of the required data structures and output files
    reference_dir = ref_install.reference_dir()
    ref_dir = str(reference_dir.path)

    bias_sort = {"T": 0, "U": 1, "N": 3, "B": 2, "Q": 4}
    col_sort = {"C": 0, "T": 1, "R": 2, "M": 3}

    output_matrix_INDEL = output_matrix + "ID/"
    if not os.path.exists(output_matrix_INDEL):
        os.mkdir(output_matrix_INDEL)

    if limited_indel:
        file_prefix = project + ".ID83"
        file_prefix_tsb = project + ".ID415"
        file_prefix_tsb_abbrev = project + ".ID332"
        file_prefix_simple = project + ".ID28"
        file_prefix_complete = project + ".ID96"
        file_prefix_complete_seq = project + ".ID8628"
    else:
        file_prefix = project + ".ID94"
        file_prefix_tsb = project + ".ID415"
        file_prefix_tsb_abbrev = project + ".ID332"
        file_prefix_simple = project + ".ID28"
        file_prefix_complete = project + ".ID96"
        file_prefix_complete_seq = project + ".ID8628"

    if exome:
        output_file_matrix = output_matrix_INDEL + file_prefix + ".exome"
        output_file_matrix_tsb = output_matrix_INDEL + file_prefix_tsb + ".exome"
        output_file_matrix_tsb_abbrev = (
            output_matrix_INDEL + file_prefix_tsb_abbrev + ".exome"
        )
        output_file_matrix_simple = output_matrix_INDEL + file_prefix_simple + ".exome"
        output_file_matrix_complete = (
            output_matrix_INDEL + file_prefix_complete + ".exome"
        )
        output_file_matrix_complete_seq = (
            output_matrix_INDEL + file_prefix_complete_seq + ".exome"
        )

    else:
        if bed:
            output_file_matrix = output_matrix_INDEL + file_prefix + ".region"
            output_file_matrix_tsb = output_matrix_INDEL + file_prefix_tsb + ".region"
            output_file_matrix_tsb_abbrev = (
                output_matrix_INDEL + file_prefix_tsb_abbrev + ".region"
            )
            output_file_matrix_simple = (
                output_matrix_INDEL + file_prefix_simple + ".region"
            )
            output_file_matrix_complete = (
                output_matrix_INDEL + file_prefix_complete + ".region"
            )
            output_file_matrix_complete_seq = (
                output_matrix_INDEL + file_prefix_complete_seq + ".region"
            )

        else:
            output_file_matrix = output_matrix_INDEL + file_prefix + ".all"
            output_file_matrix_tsb = output_matrix_INDEL + file_prefix_tsb + ".all"
            output_file_matrix_tsb_abbrev = (
                output_matrix_INDEL + file_prefix_tsb_abbrev + ".all"
            )
            output_file_matrix_simple = (
                output_matrix_INDEL + file_prefix_simple + ".all"
            )
            output_file_matrix_complete = (
                output_matrix_INDEL + file_prefix_complete + ".all"
            )
            output_file_matrix_complete_seq = (
                output_matrix_INDEL + file_prefix_complete_seq + ".all"
            )

    if initial_chrom != None:
        output_file_matrix += ".chr" + initial_chrom
        output_file_matrix_tsb += ".chr" + initial_chrom
        output_file_matrix_tsb_abbrev += ".chr" + initial_chrom
        output_file_matrix_simple += ".chr" + initial_chrom
        output_file_matrix_complete += ".chr" + initial_chrom
        output_file_matrix_complete_seq += ".chr" + initial_chrom

    # Sort the TSB types (T,U,B,N)
    try:
        types = list(indel_tsb_dict.index)
        types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
        indel_tsb_dict = indel_tsb_dict.reindex(types)

        # Collapse the Bi-directionally transcribed type to transcribed and untranscribed
        # trans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'T:']
        # untrans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'U:']
        # bitrans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'B:']
        # nontrans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'N:']
        # questionable = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'Q:']
        # a = bitrans//2
        # b = bitrans%2
        # trans = trans.append(a)
        # trans  = trans.groupby(trans.index.str[2:]).sum()
        # trans = trans.rename(index=lambda s: "T:"+s)
        # untrans = untrans.append(a)
        # untrans = untrans.groupby(untrans.index.str[2:]).sum()
        # untrans = untrans.rename(index=lambda s:"U:"+s)
        # indel_tsb_dict_abbrev = pd.concat([trans, untrans, nontrans, questionable])
        # for x in list(b.index):
        # 	mutAbrrev = x[2:]
        # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
        # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
        # 		indel_tsb_dict_abbrev.loc[z,y] += b.loc[x,y]

        # Collapse the Bi-directionally transcribed type to non-transcribed
        trans = indel_tsb_dict[indel_tsb_dict.index.str.contains("T:")]
        untrans = indel_tsb_dict[indel_tsb_dict.index.str.contains("U:")]
        bitrans = indel_tsb_dict[indel_tsb_dict.index.str.contains("B:")]
        nontrans = indel_tsb_dict[indel_tsb_dict.index.str.contains("N:")]
        questionable = indel_tsb_dict[indel_tsb_dict.index.str.contains("Q:")]
        a = bitrans // 2
        b = bitrans % 2
        trans = pd.concat([trans, a, b])
        trans = trans.groupby(trans.index.str[2:]).sum()
        trans = trans.rename(index=lambda s: "T:" + s)
        untrans = pd.concat([untrans, a])
        untrans = untrans.groupby(untrans.index.str[2:]).sum()
        untrans = untrans.rename(index=lambda s: "U:" + s)
        indel_tsb_dict_abbrev = pd.concat([trans, untrans, nontrans, questionable])
    except:
        pass

    # trans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'T:']
    # untrans = indel_tsb_dict[indel_tsb_dict.index.str[0:2] == 'U:']
    # biTransNonTrans =  indel_tsb_dict[indel_tsb_dict.index.str.contains('B:') | indel_tsb_dict.index.str.contains('N:')]
    # questionableTrans = indel_tsb_dict[indel_tsb_dict.index.str.contains('Q:')]
    # biTransNonTrans = biTransNonTrans.groupby(biTransNonTrans.index.str[2:]).sum()
    # biTransNonTrans = biTransNonTrans.rename(index=lambda s: "N:"+s)
    # indel_tsb_dict_abbrev = pd.concat([trans, untrans, biTransNonTrans, questionableTrans])

    try:
        short_id = pd.DataFrame(indel_dict).iloc[:83, :]
    except:
        pass

    if initial_chrom != None and (exome or bed):
        if indel_tsb_dict is None and indel_simple_dict is None:
            df2csv(indel_dict, output_file_matrix_complete)
        elif indel_dict is None and indel_simple_dict is None:
            df2csv(indel_tsb_dict, output_file_matrix_tsb)
            df2csv(indel_tsb_dict_abbrev, output_file_matrix_tsb_abbrev)
        elif indel_dict is None and indel_tsb_dict is None:
            df2csv(indel_simple_dict, output_file_matrix_simple)
    else:
        df2csv(short_id, output_file_matrix)
        df2csv(indel_dict, output_file_matrix_complete)
        df2csv(indel_tsb_dict, output_file_matrix_tsb)
        df2csv(indel_tsb_dict_abbrev, output_file_matrix_tsb_abbrev)
        df2csv(indel_simple_dict, output_file_matrix_simple)
        df2csv(indel_dict_complete, output_file_matrix_complete_seq)

    if plot:
        output_path = output_matrix + "plots/"
        if not os.path.exists(output_path):
            os.mkdir(output_path)
        file_name = project
        if exome:
            file_name += "_exome"
        if bed:
            file_name += "_region"
        if initial_chrom != None:
            file_name += "_chr" + initial_chrom

        try:
            sigPlt.plotID(
                output_file_matrix, output_path, file_name, "94", False, volume=volume
            )
        except:
            pass
        try:
            sigPlt.plotID(
                output_file_matrix_tsb,
                output_path,
                file_name,
                "IDSB",
                False,
                volume=volume,
            )
        except:
            pass
        try:
            sigPlt.plotID(
                output_file_matrix_simple,
                output_path,
                file_name,
                "ID_simple",
                False,
                volume=volume,
            )
        except:
            pass


def matrix_generator_DINUC(
    output_matrix,
    samples,
    bias_sort,
    all_dinucs,
    all_mut_types,
    project,
    exome,
    bed,
    chrom_start=None,
    plot=False,
    volume=None,
):
    """
    Writes the final mutational matrix for INDELS given a dictionary of samples, INDEL types, and counts

    Parameters:
                    output_matrix  -> path where the final mutational matrix is stored
                              samples  -> a list of all sample names
                            bias_sort  -> dictionary that provides the sorting order for the TSB matrices
                       all_dinucs  -> dictionary that contains all of the  mutation counts for each DINUC context
                    all_mut_types  -> dictionary that contains all of the mutation types for each DINUC context
                              project  -> unique name given to the set of samples (ex. 'BRCA')
                                    exome  -> Boolean for whether the catalogue should be generated across the whole
                                                      genome or just the exome
                                      bed  -> parameter used to filter the mutations on a user-provided BED file
                      chrom_start  -> current chromosome to generate the matrix for
                                     plot  -> flag that generates the DINUC plots for the provided samples

    Returns:
            None

    Output:
            Write the final mutational matrix for DINUCs

    """

    mut_4992 = all_dinucs
    revcompl = lambda x: "".join(
        [{"A": "T", "C": "G", "G": "C", "T": "A", "N": "N"}[B] for B in x][::-1]
    )
    revbias = lambda x: "".join(
        [
            {
                "0": "0",
                "3": "3",
                "1": "2",
                "2": "1",
                "U": "T",
                "T": "U",
                "B": "B",
                "N": "N",
            }[B]
            for B in x
        ][::-1]
    )

    contexts = ["78", "186", "1248", "150", "2400"]
    mut_count_all = {"78": {}, "186": {}, "1248": {}, "150": {}, "2400": {}}

    if not any(mut_4992):
        return ()

    mut_4992 = pd.DataFrame.from_dict(mut_4992)
    mut_4992.index.name = "MutationType"

    zeros_data = np.zeros(len(mut_4992.columns.values))
    available_types = set(mut_4992.index)
    for mut in all_mut_types:
        if mut not in available_types:
            mut_4992.loc[mut] = zeros_data

    mut_4992 = mut_4992.fillna(0)
    mut_4992 = mut_4992.astype(int)

    mut_count_all["78"] = mut_4992.groupby(mut_4992.index.str[4:9]).sum()
    mut_count_all["186"] = mut_4992.groupby(
        mut_4992.index.str[0:2] + mut_4992.index.str[4:9]
    ).sum()
    mut_count_all["1248"] = mut_4992.groupby(mut_4992.index.str[2:]).sum()

    # Collapse the Bi-directionally transcribed type to transcribed and untranscribed
    # 2976 to 2400
    # trans = mut_4992[mut_4992.index.str.contains('T:')]
    # untrans = mut_4992[mut_4992.index.str.contains('U:')]
    # bitrans = mut_4992[mut_4992.index.str.contains('B:')]
    # nontrans = mut_4992[mut_4992.index.str.contains('N:')]
    # questionable = mut_4992[mut_4992.index.str.contains('Q:')]
    # a = bitrans//2
    # b = bitrans%2
    # trans = trans.append(a)
    # trans  = trans.groupby(trans.index.str[2:]).sum()
    # trans = trans.rename(index=lambda s: "T:"+s)
    # untrans = untrans.append(a)
    # untrans = untrans.groupby(untrans.index.str[2:]).sum()
    # untrans = untrans.rename(index=lambda s:"U:"+s)
    # mut_count_all['2400'] = pd.concat([trans, untrans, nontrans, questionable])
    # for x in list(b.index):
    # 	mutAbrrev = x.split(":")[1]
    # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
    # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
    # 		mut_count_all['2400'].loc[z,y] += b.loc[x,y]

    # # 186 to 150
    # trans = mut_count_all['186'][mut_count_all['186'].index.str.contains('T:')]
    # untrans = mut_count_all['186'][mut_count_all['186'].index.str.contains('U:')]
    # bitrans = mut_count_all['186'][mut_count_all['186'].index.str.contains('B:')]
    # nontrans = mut_count_all['186'][mut_count_all['186'].index.str.contains('N:')]
    # questionable = mut_count_all['186'][mut_count_all['186'].index.str.contains('Q:')]
    # a = bitrans//2
    # b = bitrans%2
    # trans = trans.append(a)
    # trans  = trans.groupby(trans.index.str[2:]).sum()
    # trans = trans.rename(index=lambda s: "T:"+s)
    # untrans = untrans.append(a)
    # untrans = untrans.groupby(untrans.index.str[2:]).sum()
    # untrans = untrans.rename(index=lambda s:"U:"+s)
    # mut_count_all['150'] = pd.concat([trans, untrans, nontrans, questionable])
    # for x in list(b.index):
    # 	mutAbrrev = x.split(":")[1]
    # 	tempMat = pd.concat([trans.loc["T:"+mutAbrrev],untrans.loc["U:"+mutAbrrev]], axis=1)
    # 	for z,y in zip(tempMat.idxmax(axis=1), list(tempMat.index)):
    # 		mut_count_all['150'].loc[z,y] += b.loc[x,y]

    # Collapse the Bi-directionally transcribed type to non-transcribed
    # 186 to 150
    trans = mut_count_all["186"][mut_count_all["186"].index.str.contains("T:")]
    untrans = mut_count_all["186"][mut_count_all["186"].index.str.contains("U:")]
    bitrans = mut_count_all["186"][mut_count_all["186"].index.str.contains("B:")]
    nontrans = mut_count_all["186"][mut_count_all["186"].index.str.contains("N:")]
    questionable = mut_count_all["186"][mut_count_all["186"].index.str.contains("Q:")]
    a = bitrans // 2
    b = bitrans % 2
    trans = pd.concat([trans, a, b])
    trans = trans.groupby(trans.index.str[2:]).sum()
    trans = trans.rename(index=lambda s: "T:" + s)
    untrans = pd.concat([untrans, a])
    untrans = untrans.groupby(untrans.index.str[2:]).sum()
    untrans = untrans.rename(index=lambda s: "U:" + s)
    mut_count_all["150"] = pd.concat([trans, untrans, nontrans, questionable])

    # 2976 to 2400
    trans = mut_4992[mut_4992.index.str.contains("T:")]
    untrans = mut_4992[mut_4992.index.str.contains("U:")]
    bitrans = mut_4992[mut_4992.index.str.contains("B:")]
    nontrans = mut_4992[mut_4992.index.str.contains("N:")]
    questionable = mut_4992[mut_4992.index.str.contains("Q:")]
    a = bitrans // 2
    b = bitrans % 2
    trans = pd.concat([trans, a, b])
    trans = trans.groupby(trans.index.str[2:]).sum()
    trans = trans.rename(index=lambda s: "T:" + s)
    untrans = pd.concat([untrans, a])
    untrans = untrans.groupby(untrans.index.str[2:]).sum()
    untrans = untrans.rename(index=lambda s: "U:" + s)
    mut_count_all["2400"] = pd.concat([trans, untrans, nontrans, questionable])

    # # Collapse the Bi-directionally transcribed type to non-transcribed
    # # 186 to 150
    # trans = mut_count_all['186'][mut_count_all['186'].index.str[0:2] == 'T:']
    # untrans = mut_count_all['186'][mut_count_all['186'].index.str[0:2] == 'U:']
    # biTransNonTrans =  mut_count_all['186'][mut_count_all['186'].index.str.contains('B:') | mut_count_all['186'].index.str.contains('N:')]
    # questionableTrans = mut_count_all['186'][mut_count_all['186'].index.str.contains('Q:')]
    # biTransNonTrans = biTransNonTrans.groupby(biTransNonTrans.index.str[2:]).sum()
    # biTransNonTrans = biTransNonTrans.rename(index=lambda s: "N:"+s)
    # mut_count_all['150'] = pd.concat([trans, untrans, biTransNonTrans, questionableTrans])

    # # 2976 to 2400
    # trans = mut_4992[mut_4992.index.str[0:2] == 'T:']
    # untrans = mut_4992[mut_4992.index.str[0:2] == 'U:']
    # biTransNonTrans =  mut_4992[mut_4992.index.str.contains('B:') | mut_4992.index.str.contains('N:')]
    # questionableTrans = mut_4992[mut_4992.index.str.contains('Q:')]
    # biTransNonTrans = biTransNonTrans.groupby(biTransNonTrans.index.str[2:]).sum()
    # biTransNonTrans = biTransNonTrans.rename(index=lambda s: "N:"+s)
    # mut_count_all['2400'] = pd.concat([trans, untrans, biTransNonTrans, questionableTrans])

    mut_count_all["78"].index.name = "MutationType"
    mut_count_all["186"].index.name = "MutationType"
    mut_count_all["1248"].index.name = "MutationType"
    mut_count_all["150"].index.name = "MutationType"
    mut_count_all["2400"].index.name = "MutationType"

    output_matrix_DINUC = output_matrix + "DBS/"
    if not os.path.exists(output_matrix_DINUC):
        os.mkdir(output_matrix_DINUC)

    reference_dir = ref_install.reference_dir()
    ref_dir = str(reference_dir.path)

    file_prefix = project + ".DBS2976"
    if exome:
        output_file_matrix = output_matrix_DINUC + file_prefix + ".exome"
    else:
        if bed:
            output_file_matrix = output_matrix_DINUC + file_prefix + ".region"
        else:
            output_file_matrix = output_matrix_DINUC + file_prefix + ".all"

    if chrom_start != None:
        output_file_matrix += ".chr" + chrom_start

    types = list(mut_4992.index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_4992 = mut_4992.reindex(types)

    types = list(mut_count_all["186"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["186"] = mut_count_all["186"].reindex(types)

    types = list(mut_count_all["150"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["150"] = mut_count_all["150"].reindex(types)

    types = list(mut_count_all["2400"].index)
    types = sorted(types, key=lambda val: (bias_sort[val[0]], val[2:]))
    mut_count_all["2400"] = mut_count_all["2400"].reindex(types)

    mut_4992.to_csv(output_file_matrix, header=True, sep="\t")

    for cont in contexts:
        mutation_dict = mut_count_all[cont]
        file_prefix = project + ".DBS" + cont
        if exome:
            output_file_matrix = output_matrix_DINUC + file_prefix + ".exome"
        else:
            if bed:
                output_file_matrix = output_matrix_DINUC + file_prefix + ".region"
            else:
                output_file_matrix = output_matrix_DINUC + file_prefix + ".all"
        if chrom_start != None:
            output_file_matrix += ".chr" + chrom_start
        mutation_dict.to_csv(output_file_matrix, header=True, sep="\t")

        if plot:
            file_name = project
            if exome:
                file_name += "_exome"
            if bed:
                file_name += "_region"
            if chrom_start != None:
                file_name += "_chr" + chrom_start
            output_path = output_matrix + "plots/"
            if not os.path.exists(output_path):
                os.mkdir(output_path)
            try:
                if cont == "78" or cont == "186":
                    sigPlt.plotDBS(
                        output_file_matrix,
                        output_path,
                        file_name,
                        cont,
                        False,
                        volume=volume,
                    )
            except:
                pass

    return mut_count_all["78"]
