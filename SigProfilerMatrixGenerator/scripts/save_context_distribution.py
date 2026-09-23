#!/usr/bin/env python3

# This source code file is a part of SigProfilerSimulator

# Author: Erik Bergstrom

# Contact: ebergstr@eng.ucsd.edu

from __future__ import print_function

import argparse
import os
import re
import sys
import filecmp
import uuid

from SigProfilerMatrixGenerator.scripts import ref_install

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
            "Q": "Q",
        }[B]
        for B in x
    ][::-1]
)


# This function was introduced because this section of code caused file access errors when run in parallel.
# The exome file was sorted (male/female sort) and overwritten in parallel. Introducing, temporary
# files resolved this issue.
def safe_sort_and_compare(file_to_open, chromosomes_sort):
    # Generate a unique temp file using UUID
    temp_output_file = f"{file_to_open}.tmp.{uuid.uuid4()}"

    try:
        # Perform sorting and write to temporary file
        with open(file_to_open, "r") as f, open(temp_output_file, "w") as output:
            lines = [line.strip().split() for line in f]
            print("\t".join(lines[0]), file=output)

            if len(lines) > 1:
                if len(lines[1][0]) > 2:
                    sorted_lines = sorted(
                        lines[1:],
                        key=lambda x: (
                            chromosomes_sort.index(x[0][3:]),
                            int(x[1]),
                            int(x[2]),
                        ),
                    )
                else:
                    sorted_lines = sorted(
                        lines[1:],
                        key=lambda x: (
                            chromosomes_sort.index(x[0]),
                            int(x[1]),
                            int(x[2]),
                        ),
                    )

                for line in sorted_lines:
                    print("\t".join(line), file=output)

        # Check if the sorted output differs from the original
        if filecmp.cmp(file_to_open, temp_output_file, shallow=False):
            print(f"No changes detected in {file_to_open}. Discarding temporary file.")
            os.remove(temp_output_file)
            return file_to_open  # Return original file since no changes detected
        else:
            print(f"Changes detected. Using sorted file instead of {file_to_open}.")
            return temp_output_file  # Return the temp file path for further use

    except Exception as e:
        print(f"Error during sorting and comparison: {e}")
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        print("Temporary file removed. Original file remains intact.")
        return file_to_open  # Return original if something goes wrong


def context_distribution(
    context_input, output_file, chromosome_path, chromosomes, tsb_ref, genome
):
    """
    Creates a csv file for the distribution of nucleotides given a specific context.
    This csv file needs to be created before simulating mutationalsigantures for the
    given context.

    Requires:
            Chromosomes saved in individual text files ('X.txt','Y.txt', '1.txt', etc)
            Transcriptional data saved in binary files for each chromosome.
            These files can be created using the function:
            "save_tsb_192.save_tsb"

    Parameters:
                      context_input  -> simulation context of interest (ex: 96, 192, 1536, 3072, DINUC, INDEL)
                            output_file  -> file where the distribution for the given nucleotide context is saved (csv file)
                    chromosome_path  -> path to the reference chromosomes
                            chromosomes  -> list of chromosomes for the species of interest

    Returns:
            None

    Outputs:
            CSV file with each chromosome represented as a column and reach row
            represented as a nucleotide. Under each chromosome for a given nucleotide
            is the proportion of the total length of that chromosome associated with that
            nucleotide.
    """

    dinuc_types = ["AA", "AC", "AG", "AT", "CA", "CC", "CG", "GA", "GC", "TA"]
    dinuc_tsb = [
        "AA",
        "AG",
        "CC",
        "GA",
    ]
    dinuc_non_tsb = ["Q:AC", "Q:AT", "Q:CA", "Q:CG", "Q:GC", "Q:TA"]
    tsb_bias = ["T", "U", "B", "N"]

    # Set the context parameter based upon the user input
    if context_input == "96" or context_input == "192" or context_input == "384":
        context = 5
        output_context = 3
    elif context_input == "1536" or context_input == "3072" or context_input == "6144":
        context = 5
        output_context = 5
    elif (
        context_input == "DINUC" or context_input == "DBS186" or context_input == "DBS"
    ):
        context = 2
        output_context = 2
    elif context_input == "6" or context_input == "24":
        context = 5
        output_context = 1
    else:
        print("Not a valid context")
        sys.exit()

    count = 0
    probs = {}
    chromosome_lengths = []

    # Populate the dictionary if desired context is DINUC
    if context_input == "DBS" or context_input == "DINUC":
        for dinuc in dinuc_types:
            probs[dinuc] = {}

    if context_input == "DBS186":
        for dinuc in dinuc_tsb:
            for bias in tsb_bias:
                dinuc_t = bias + ":" + dinuc
                probs[dinuc_t] = {}
        for dinuc in dinuc_non_tsb:
            probs[dinuc] = {}

    # Iterate through each chromosome and open the associated file
    for chrom in chromosomes:
        with open(chromosome_path + chrom + ".txt", "rb") as f:
            chromosome = f.read()
            chromosome_lengths.append(len(chromosome))
            print(chrom, len(chromosome))

            # Iterate through the chromosome base by base
            for i in range(0, len(chromosome) - context + 1):
                nuc = ""
                for l in range(i, i + context, 1):
                    nuc += tsb_ref[chromosome[l]][1]
                base = nuc[int(context / 2)]
                count += 1
                if count == 1000000:
                    print(i)
                    count = 0
                # Skip the base if unknown
                if "N" in nuc:
                    pass

                else:
                    if (
                        context_input != "DINUC"
                        and context_input != "DBS186"
                        and context_input != "DBS"
                    ):
                        # Only save the pyrimidine context (canonical)
                        reverse_strand = base == "A" or base == "G"
                        if reverse_strand:
                            nuc = revcompl(nuc)
                        trim = (context - output_context) // 2
                        if trim:
                            nuc = nuc[trim:-trim]

                        # Adjust the nucleotide representaiton if TSB is desired
                        if (
                            context_input == "192"
                            or context_input == "3072"
                            or context_input == "384"
                            or context_input == "6144"
                            or context_input == "24"
                        ):
                            bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                            if reverse_strand:
                                bias = revbias(bias)
                            nuc = bias + ":" + nuc

                        # Update the dictionary for the current nucleotide
                        if nuc not in probs:
                            probs[nuc] = {chrom: 1}
                        else:
                            if chrom not in probs[nuc]:
                                probs[nuc][chrom] = 1
                            else:
                                probs[nuc][chrom] += 1

                    else:
                        if context_input == "DBS186":
                            bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                            if nuc not in dinuc_types:
                                nuc = revcompl(nuc)
                                bias = revbias(bias)
                            if nuc not in dinuc_tsb:
                                bias = "Q"
                            nuc = bias + ":" + nuc

                        else:
                            if nuc not in dinuc_types:
                                nuc = revcompl(nuc)
                        # Update the dictionary for the current nucleotide
                        if chrom not in probs[nuc]:
                            probs[nuc][chrom] = 1
                        else:
                            probs[nuc][chrom] += 1

        print("chrom ", chrom, "done")
    print(probs, chromosome_lengths)
    # Write the resulting dictionary to the csv file
    with open(output_file, "w") as out:
        print(" ,", end="", file=out)
        for chrom in chromosomes[:-1]:
            print(chrom + ",", end="", file=out)
        print(chromosomes[-1], file=out)
        for nuc in probs.keys():
            nuc_sum = sum(probs[nuc].values())
            print(nuc + ",", end="", file=out)
            for i in range(0, len(chromosomes[:-1]), 1):
                try:
                    print(
                        str(probs[nuc][chromosomes[i]] / nuc_sum) + ",",
                        end="",
                        file=out,
                    )
                    out.flush()
                except:
                    print(str(0) + ",", end="", file=out)
            try:
                print(probs[nuc][chromosomes[-1]] / nuc_sum, file=out)
            except:
                print(str(0), file=out)

    counts_file = os.path.dirname(output_file)
    with open(
        counts_file + "/context_counts_" + genome + "_" + context_input + ".csv", "w"
    ) as out:
        print(" ,", end="", file=out)
        for chrom in chromosomes[:-1]:
            print(chrom + ",", end="", file=out)
        print(chromosomes[-1], file=out)
        for nuc in probs.keys():
            nuc_sum = sum(probs[nuc].values())
            print(nuc + ",", end="", file=out)
            for chroms in chromosomes[:-1]:
                try:
                    print(str(probs[nuc][chroms]) + ",", end="", file=out)
                    out.flush()
                except:
                    print(str(0) + ",", end="", file=out)
            try:
                print(str(probs[nuc][chromosomes[-1]]), file=out)
            except:
                print(str(0), file=out)

    # Sort the file so that the nucleotides are in alphabetical order
    sort_command_1 = "sort -t ',' -k 1,1 "
    sort_command_2 = " -o "
    os.system(sort_command_1 + output_file + sort_command_2 + output_file)


def context_distribution_BED(
    context_input,
    output_file,
    chromosome_path,
    chromosomes,
    bed,
    bed_file,
    exome,
    exome_file,
    genome,
    ref_dir,
    tsb_ref,
    gender,
):
    """
    Creates a csv file for the distribution of nucleotides given a specific context and BED file.
    This csv file needs to be created before simulating mutationalsigantures for the given
    context.

    Requires:
            Chromosomes saved in individual text files ('X.txt','Y.txt', '1.txt', etc)
            Transcriptional data saved in binary files for each chromosome.
            These files can be created using the function:
            "save_tsb_192.save_tsb"

    Parameters:
                      context_input  -> simulation context of interest (ex: 96, 192, 1536, 3072, DINUC, INDEL)
                            output_file  -> file where the distribution for the given nucleotide context is saved (csv file)
                    chromosome_path  -> path to the reference chromosomes
                            chromosomes  -> list of chromosomes for the species of interest
                                            bed  -> flag that determines if the user has provided a BED file with specific ranges to simulate
                               bed_file  -> BED file that contains the ranges of interest

    Returns:
            None

    Outputs:
            CSV file with each chromosome represented as a column and reach row
            represented as a nucleotide. Under each chromosome for a given nucleotide
            is the proportion of the total length of that chromosome associated with that
            nucleotide.
    """

    dinuc_types = ["AA", "AC", "AG", "AT", "CA", "CC", "CG", "GA", "GC", "TA"]
    dinuc_tsb = [
        "AA",
        "AG",
        "CC",
        "GA",
    ]
    dinuc_non_tsb = ["Q:AC", "Q:AT", "Q:CA", "Q:CG", "Q:GC", "Q:TA"]
    tsb_bias = ["T", "U", "B", "N"]

    # Set the context parameter based upon the user input
    if context_input == "96" or context_input == "192" or context_input == "384":
        context = 5
        output_context = 3
    elif context_input == "1536" or context_input == "3072" or context_input == "6144":
        context = 5
        output_context = 5
    elif (
        context_input == "DINUC" or context_input == "DBS" or context_input == "DBS186"
    ):
        context = 2
        output_context = 2
    elif context_input == "6" or context_input == "24":
        context = 5
        output_context = 1
    else:
        print("Not a valid context")
        sys.exit()
    count = 0
    probs = {}
    chromosome_lengths = {}
    first_line = True
    chrom_length = 0
    if exome:
        file_to_open = exome_file
    else:
        file_to_open = bed_file

    chromosomes_sort = chromosomes
    if "Y" not in chromosomes:
        chromosomes_sort.append("Y")
    if "MT" not in chromosomes:
        chromosomes_sort.append("MT")
    if "M" not in chromosomes:
        chromosomes_sort.append("M")

    # Populate the dictionary if desired context is DINUC
    if context_input == "DBS" or context_input == "DINUC":
        for dinuc in dinuc_types:
            probs[dinuc] = {}

    if context_input == "DBS186":
        for dinuc in dinuc_tsb:
            for bias in tsb_bias:
                dinuc_t = bias + ":" + dinuc
                probs[dinuc_t] = {}
        for dinuc in dinuc_non_tsb:
            probs[dinuc] = {}

    processed_file = safe_sort_and_compare(file_to_open, chromosomes_sort)

    with open(processed_file) as b_file:
        next(b_file)
        for lines in b_file:
            line = lines.strip().split()
            chrom = line[0]
            if len(chrom) > 1 and chrom[0:3].upper() == "CHR":
                chrom = chrom[3:]
            if gender == "female" and chrom == "Y":
                continue

            try:
                start = int(line[1])
                end = int(line[2])
            except Exception as e:
                print(
                    f"There was an issue processing the start and end position from the line: {line}"
                )
                continue

            if first_line:
                chrom_initial = chrom
                first_line = False
                f = open(chromosome_path + chrom + ".txt", "rb")
                chromosome = f.read()

            if chrom == chrom_initial:
                chrom_length += end - start
                for i in range(
                    start, min(end + 1 - context, len(chromosome) + 1 - context)
                ):
                    nuc = ""
                    for l in range(i, min(i + context, len(chromosome))):
                        nuc += tsb_ref[chromosome[l]][1]

                    # Skip incomplete windows
                    if len(nuc) != context:
                        overlap = context - len(nuc)
                        print(
                            f"Skipping window at index {i} for chromosome {chromosome}: expected context length {context}, but got {len(nuc)}. "
                            f"Missing {overlap} base(s) due to boundary at the end of the chromosome."
                        )
                        continue

                    # Skip the base if unknown
                    if "N" in nuc:
                        pass
                    else:
                        # Assign `base` to the middle nucleotide of the context
                        if len(nuc) >= int(context / 2) + 1:  # Prevent IndexError
                            base = nuc[int(context / 2)]
                        else:
                            continue  # Skip if `nuc` is too short
                        if (
                            context_input != "DINUC"
                            and context_input != "DBS186"
                            and context_input != "DBS"
                        ):
                            # Only save the pyrimidine context (canonical)
                            reverse_strand = base == "A" or base == "G"
                            if reverse_strand:
                                nuc = revcompl(nuc)
                            trim = (context - output_context) // 2
                            if trim:
                                nuc = nuc[trim:-trim]

                            # Adjust the nucleotide representaiton if TSB is desired
                            if (
                                context_input == "192"
                                or context_input == "3072"
                                or context_input == "384"
                                or context_input == "6144"
                                or context_input == "24"
                            ):
                                bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                                if reverse_strand:
                                    bias = revbias(bias)
                                nuc = bias + ":" + nuc

                            # Update the dictionary for the current nucleotide
                            if nuc not in probs:
                                probs[nuc] = {chrom: 1}
                            else:
                                if chrom not in probs[nuc]:
                                    probs[nuc][chrom] = 1
                                else:
                                    probs[nuc][chrom] += 1

                        else:
                            if context_input == "DBS186":
                                bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                                if nuc not in dinuc_types:
                                    nuc = revcompl(nuc)
                                    bias = revbias(bias)
                                if nuc not in dinuc_tsb:
                                    bias = "Q"
                                nuc = bias + ":" + nuc

                            else:
                                if nuc not in dinuc_types:
                                    nuc = revcompl(nuc)
                            # Update the dictionary for the current nucleotide
                            if chrom not in probs[nuc]:
                                probs[nuc][chrom] = 1
                            else:
                                probs[nuc][chrom] += 1
            else:
                f.close()
                print("          Chromosome ", chrom_initial, "done")
                chromosome_lengths[chrom_initial] = chrom_length
                chrom_length = end - start
                chrom_initial = chrom
                try:
                    f = open(chromosome_path + chrom + ".txt", "rb")
                    chromosome = f.read()
                except:
                    continue

                for i in range(
                    start, min(end + 1 - context, len(chromosome) + 1 - context)
                ):
                    nuc = ""
                    for l in range(i, i + context, 1):
                        nuc += tsb_ref[chromosome[l]][1]

                    # Skip incomplete windows
                    if len(nuc) != context:
                        overlap = context - len(nuc)
                        print(
                            f"Skipping window at index {i} for chromosome {chromosome}: expected context length {context}, but got {len(nuc)}. "
                            f"Missing {overlap} base(s) due to boundary at the end of the chromosome."
                        )
                        continue

                    base = nuc[int(context / 2)]

                    # Skip the base if unknown
                    if "N" in nuc:
                        pass

                    else:
                        if (
                            context_input != "DINUC"
                            and context_input != "DBS186"
                            and context_input != "DBS"
                        ):
                            # Only save the pyrimidine context (canonical)
                            reverse_strand = base == "A" or base == "G"
                            if reverse_strand:
                                nuc = revcompl(nuc)
                            trim = (context - output_context) // 2
                            if trim:
                                nuc = nuc[trim:-trim]

                            # Adjust the nucleotide representaiton if TSB is desired
                            if (
                                context_input == "192"
                                or context_input == "3072"
                                or context_input == "384"
                                or context_input == "6144"
                                or context_input == "24"
                            ):
                                bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                                if reverse_strand:
                                    bias = revbias(bias)
                                nuc = bias + ":" + nuc

                            # Update the dictionary for the current nucleotide
                            if nuc not in probs:
                                probs[nuc] = {chrom: 1}
                            else:
                                if chrom not in probs[nuc]:
                                    probs[nuc][chrom] = 1
                                else:
                                    probs[nuc][chrom] += 1
                        else:
                            if context_input == "DBS186":
                                bias = tsb_ref[chromosome[i + int(context / 2)]][0]
                                if nuc not in dinuc_types:
                                    nuc = revcompl(nuc)
                                    bias = revbias(bias)
                                if nuc not in dinuc_tsb:
                                    bias = "Q"
                                nuc = bias + ":" + nuc

                            else:
                                if nuc not in dinuc_types:
                                    nuc = revcompl(nuc)
                            # Update the dictionary for the current nucleotide
                            if chrom not in probs[nuc]:
                                probs[nuc][chrom] = 1
                            else:
                                probs[nuc][chrom] += 1
        chromosome_lengths[chrom_initial] = chrom_length

    # Write the resulting dictionary to the csv file
    with open(output_file, "w") as out:
        print(" ,", end="", file=out)
        for chrom in chromosomes[:-1]:
            print(chrom + ",", end="", file=out)
        print(chromosomes[-1], file=out)
        for nuc in probs.keys():
            nuc_sum = sum(probs[nuc].values())
            print(nuc + ",", end="", file=out)
            for chroms in chromosomes[:-1]:
                try:
                    print(str(probs[nuc][chroms] / nuc_sum) + ",", end="", file=out)
                    out.flush()
                except:
                    print(str(0) + ",", end="", file=out)
            try:
                print(probs[nuc][chromosomes[-1]] / nuc_sum, file=out)
            except:
                print(str(0), file=out)

    counts_file = os.path.dirname(output_file)
    with open(
        counts_file + "/context_counts_" + genome + "_" + context_input + "_exome.csv",
        "w",
    ) as out:
        print(" ,", end="", file=out)
        for chrom in chromosomes[:-1]:
            print(chrom + ",", end="", file=out)
        print(chromosomes[-1], file=out)
        for nuc in probs.keys():
            nuc_sum = sum(probs[nuc].values())
            print(nuc + ",", end="", file=out)
            for chroms in chromosomes[:-1]:
                try:
                    print(str(probs[nuc][chroms]) + ",", end="", file=out)
                    out.flush()
                except:
                    print(str(0) + ",", end="", file=out)
            try:
                print(str(probs[nuc][chromosomes[-1]]), file=out)
            except:
                print(str(0), file=out)

    # Sort the file so that the nucleotides are in alphabetical order
    sort_command_1 = "sort -t ',' -k 1,1 "
    sort_command_2 = " -o "
    os.system(sort_command_1 + output_file + sort_command_2 + output_file)


def main():
    bed = False
    bed_file = None
    exome = False
    exome_file = None
    gender = "male"

    parser = argparse.ArgumentParser(
        description="Provide the necessary arguments to save the nucleotide distributions for each chromosome."
    )
    parser.add_argument(
        "--genome", "-g", help="Provide a reference genome. (ex: GRCh37, GRCh38, mm10)"
    )
    parser.add_argument("--context", "-c", help="Whole genome context by default")
    parser.add_argument(
        "-b",
        "--bed",
        nargs="?",
        help="Optional parameter instructs script to simulate on a given set of ranges (ex: exome). Whole genome context by default",
    )
    parser.add_argument(
        "-e",
        "--exome",
        nargs="?",
        help="Optional parameter instructs script to simulate only on exome). Whole genome context by default",
    )
    parser.add_argument(
        "-gD",
        "--gender",
        help="Optional parameter instructs script to create the context files based on female (two x chromosomes.",
        action="store_true",
    )

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

    args = parser.parse_args()
    genome = args.genome
    context = args.context
    if args.bed:
        bed = True
        bed_file = args.bed

    if args.exome:
        exome = True
        exome_file = args.exome

    chromosomes = [
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
    ]

    if args.gender:
        gender = "female"
        chromosomes.remove("Y")
        y_removed = True
    else:
        y_removed = False

    # Calculate offset for slicing
    offset = 1 if y_removed else 0

    # Handle genome-specific chromosome slicing
    if genome.upper() in ["MM10", "MM9", "MM39"]:
        chromosomes = chromosomes[: 21 - offset]
    elif genome.upper() in ["RN6", "RN7"]:
        chromosomes = chromosomes[: 22 - offset]

    script_dir = os.getcwd()
    reference_dir = ref_install.reference_dir()
    ref_dir = reference_dir.path
    chromosome_path = str(reference_dir.get_tsb_dir() / genome) + "/"

    output_path = os.path.join(ref_dir, "references/chromosomes/context_distributions/")
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    if bed:
        output_file = os.path.join(
            ref_dir,
            "references",
            "chromosomes",
            "context_distributions",
            f"context_distribution_{genome}_{context}_{gender}_BED.csv",
        )

    else:
        if exome:
            output_file = os.path.join(
                ref_dir,
                "references",
                "chromosomes",
                "context_distributions",
                f"context_distribution_{genome}_{context}_{gender}_exome.csv",
            )
        else:
            output_file = os.path.join(
                ref_dir,
                "references",
                "chromosomes",
                "context_distributions",
                f"context_distribution_{genome}_{context}_{gender}.csv",
            )

    if bed or exome:
        context_distribution_BED(
            context,
            output_file,
            chromosome_path,
            chromosomes,
            bed,
            bed_file,
            exome,
            exome_file,
            genome,
            ref_dir,
            tsb_ref,
            gender,
        )
    else:
        context_distribution(
            context, output_file, chromosome_path, chromosomes, tsb_ref, genome
        )


if __name__ == "__main__":
    main()
