#!/usr/bin/env python3

# Author: Erik Bergstrom

# Contact: ebergstr@eng.ucsd.edu

from __future__ import print_function

import os

from SigProfilerMatrixGenerator.scripts import reference_genome_manager


def _get_output_chromosomes(genome):
    # Transcript inputs may be combined or omit unannotated chromosomes.
    # Use the same chromosome manifest as reference installation verification.
    try:
        return list(reference_genome_manager.CHECKSUMS[genome])
    except KeyError:
        raise ValueError(f"No chromosome manifest is registered for {genome}.") from None


def convertVCF(project, vcf_path, genome, output_path, ncbi_chrom, log_file):
    """
    Converts input vcf files into a single simple text format.

    Parameters:
             project  -> unique name given to the current samples
            vcf_path  -> path to the input vcf files
              genome  -> reference genome
     output_path  -> path to the temporary folder

    Returns:
                     snv  -> Boolean that informs whether there are SNVs present in the
                                     input files
               indel  -> Boolean that informs whether there are INDELs present
                                     in the input files

    Ouput:
            Saves a single text file to the temporary file folder

    """
    # Collect all input file names and instantiate flags
    out_chroms = _get_output_chromosomes(genome)
    files = os.listdir(vcf_path)
    first_indel = True
    first_SNV = True
    snv = False
    indel = False
    out = open(log_file, "a")
    prev_line = None
    skipped_count = 0
    samples = []

    # Iterates through each file
    for file in files:
        # Skip hidden files
        if file[0] == ".":
            continue
        file_name = file.split(".")
        sample = file_name[0]
        if sample not in samples:
            samples.append(sample)
        with open(vcf_path + file) as f:
            for lines in f:
                # Skips any header lines
                if lines[0] == "#":
                    continue
                else:
                    try:
                        line = lines.strip().split()
                        if len(line) == 0:
                            continue
                        chrom = line[0]
                        if len(chrom) > 2 and genome.lower() != "ebv":
                            chrom = chrom[3:]
                        if chrom in ncbi_chrom:
                            chrom = ncbi_chrom[chrom]
                        if chrom.upper() == "M" or chrom == "mt":
                            chrom = "MT"
                        start = line[1]
                        ref = line[3]
                        mut = line[4]
                        int(start)

                    except:
                        print(
                            "The given input files do not appear to be in the correct vcf format. Skipping this file: ",
                            file,
                        )
                        break

                    # Saves SNV mutations into an SNV simple text file
                    if len(ref) == 1 and len(mut) == 1 and ref != "-" and mut != "-":
                        snv = True

                        if ref not in "ACGT-":
                            print(
                                "The ref base is not recognized. Skipping this mutation: "
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

                        if mut not in "ACGT-":
                            print(
                                "The mutation base is not recognized. Skipping this mutation: "
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
                            out.flush()
                            skipped_count += 1
                            continue

                        if line == prev_line:
                            print(
                                "There appears to be a duplicate single base substitution. Skipping this mutation: "
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
                        # Open all SNV files to be written to
                        if first_SNV:
                            if not os.path.exists(output_path + "SNV/"):
                                os.mkdir(output_path + "SNV/")
                            chrom_names = [
                                str(output_path)
                                + "SNV/"
                                + out_chroms[i]
                                + "_"
                                + project
                                + ".genome"
                                for i in range(0, len(out_chroms))
                            ]
                            chrom_files = [
                                open(file_name, "w", 10000000)
                                for file_name in chrom_names
                            ]
                            outFiles = dict(zip(out_chroms, chrom_files))
                            first_SNV = False

                        if chrom in outFiles:
                            print(
                                "\t".join([sample, chrom, start, ref, mut]),
                                file=outFiles[chrom],
                            )
                        else:
                            print(
                                chrom
                                + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                                file=out,
                            )
                            out.flush()

                    elif (
                        len(ref) == 2
                        and len(mut) == 2
                        and "-" not in ref
                        and "-" not in mut
                    ):
                        ref_1 = ref[0]
                        ref_2 = ref[1]
                        mut_1 = mut[0]
                        mut_2 = mut[1]
                        snv = True
                        # Check first base combination
                        if ref_1 not in "ACGT-":
                            print(
                                "The ref base is not recognized. Skipping this mutation: "
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

                        if mut_1 not in "ACGT-":
                            print(
                                "The mutation base is not recognized. Skipping this mutation: "
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

                        if ref_1 == mut_1:
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
                            out.flush()
                            skipped_count += 1
                            continue

                        if line == prev_line:
                            print(
                                "There appears to be a duplicate single base substitution. Skipping this mutation: "
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
                        # Check second base combination
                        if ref_2 not in "ACGT-":
                            print(
                                "The ref base is not recognized. Skipping this mutation: "
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

                        if mut_2 not in "ACGT-":
                            print(
                                "The mutation base is not recognized. Skipping this mutation: "
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

                        if ref_2 == mut_2:
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
                            out.flush()
                            skipped_count += 1
                            continue

                        if line == prev_line:
                            print(
                                "There appears to be a duplicate single base substitution. Skipping this mutation: "
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

                        if first_SNV:
                            if not os.path.exists(output_path + "SNV/"):
                                os.mkdir(output_path + "SNV/")
                            chrom_names = [
                                str(output_path)
                                + "SNV/"
                                + out_chroms[i]
                                + "_"
                                + project
                                + ".genome"
                                for i in range(0, len(out_chroms))
                            ]
                            chrom_files = [
                                open(file_name, "w", 10000000)
                                for file_name in chrom_names
                            ]
                            outFiles = dict(zip(out_chroms, chrom_files))
                            first_SNV = False

                        if chrom in outFiles:
                            print(
                                "\t".join([sample, chrom, start, ref_1, mut_1]),
                                file=outFiles[chrom],
                            )
                            print(
                                "\t".join(
                                    [sample, chrom, str(int(start) + 1), ref_2, mut_2]
                                ),
                                file=outFiles[chrom],
                            )
                        else:
                            print(
                                chrom
                                + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                                file=out,
                            )
                            out.flush()

                    # Saves INDEL mutations into an INDEL simple text file
                    else:
                        indel = True
                        if first_indel:
                            if not os.path.exists(output_path + "INDEL/"):
                                os.mkdir(output_path + "INDEL/")

                            chrom_namesI = [
                                str(output_path)
                                + "INDEL/"
                                + out_chroms[i]
                                + "_"
                                + project
                                + ".genome"
                                for i in range(0, len(out_chroms))
                            ]
                            chrom_filesI = [
                                open(file_name, "w", 10000000)
                                for file_name in chrom_namesI
                            ]
                            outFilesI = dict(zip(out_chroms, chrom_filesI))
                            first_indel = False

                        if chrom in outFilesI:
                            print(
                                "\t".join([sample, chrom, start, ref, mut]),
                                file=outFilesI[chrom],
                            )
                        else:
                            print(
                                chrom
                                + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                                file=out,
                            )
                            out.flush()

                    prev_line = line

    # Closes the output files and returns the boolean flags
    if snv:
        for files in outFiles.values():
            files.close()
    if indel:
        for files in outFilesI.values():
            files.close()
    out.close()
    return (snv, indel, skipped_count, samples)


def convertTxt(project, vcf_path, genome, output_path, ncbi_chrom, log_file):
    """
    Converts input text files into a single simple text format.

    Parameters:
             project  -> unique name given to the current samples
            vcf_path  -> path to the input text files
              genome  -> reference genome
     output_path  -> path to the temporary folder

    Returns:
                     snv  -> Boolean that informs whether there are SNVs present in the
                                     input files
               indel  -> Boolean that informs whether there are INDELs present
                                     in the input files

    Ouput:
            Saves a single text file to the temporary file folder

    """

    # Collect all input file names and instantiate flags
    out_chroms = _get_output_chromosomes(genome)
    out = open(log_file, "a")
    files = os.listdir(vcf_path)
    first_indel = True
    first_SNV = True
    snv = False
    indel = False
    prev_line = None
    skipped_count = 0
    samples = []

    # Iterates through each file
    for file in files:
        if file[0] == ".":
            continue
        with open(vcf_path + file) as f:
            next(f)
            for lines in f:
                try:
                    line = lines.strip().split()
                    if len(line) == 0:
                        continue
                    sample = line[1]
                    if sample not in samples:
                        samples.append(sample)
                    chrom = line[5]
                    if len(chrom) > 2:
                        chrom = chrom[3:]
                    if chrom in ncbi_chrom:
                        chrom = ncbi_chrom[chrom]
                    if chrom.upper() == "M" or chrom == "mt":
                        chrom = "MT"
                    start = line[6]
                    end = line[7]
                    ref = line[8]
                    mut = line[9]
                    int(start)
                    int(end)

                except:
                    print(
                        "The given input files do not appear to be in the correct simple text format. Skipping this file: ",
                        file,
                    )
                    break

                # Saves SNV mutations into an SNV simple text file
                if len(ref) == 1 and len(mut) == 1 and ref != "-" and mut != "-":
                    snv = True
                    if ref not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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

                    if first_SNV:
                        if not os.path.exists(output_path + "SNV/"):
                            os.mkdir(output_path + "SNV/")
                        chrom_names = [
                            str(output_path)
                            + "SNV/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_files = [
                            open(file_name, "w", 10000000) for file_name in chrom_names
                        ]
                        outFiles = dict(zip(out_chroms, chrom_files))
                        first_SNV = False

                    if chrom in outFiles:
                        print(
                            "\t".join([sample, chrom, start, ref, mut]),
                            file=outFiles[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()
                elif (
                    len(ref) == 2
                    and len(mut) == 2
                    and "-" not in ref
                    and "-" not in mut
                ):
                    ref_1 = ref[0]
                    ref_2 = ref[1]
                    mut_1 = mut[0]
                    mut_2 = mut[1]
                    snv = True
                    # Check first base combination
                    if ref_1 not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut_1 not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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

                    if ref_1 == mut_1:
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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
                    # Check second base combination
                    if ref_2 not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut_2 not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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

                    if ref_2 == mut_2:
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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

                    if first_SNV:
                        if not os.path.exists(output_path + "SNV/"):
                            os.mkdir(output_path + "SNV/")
                        chrom_names = [
                            str(output_path)
                            + "SNV/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_files = [
                            open(file_name, "w", 10000000) for file_name in chrom_names
                        ]
                        outFiles = dict(zip(out_chroms, chrom_files))
                        first_SNV = False

                    if chrom in outFiles:
                        print(
                            "\t".join([sample, chrom, start, ref_1, mut_1]),
                            file=outFiles[chrom],
                        )
                        print(
                            "\t".join(
                                [sample, chrom, str(int(start) + 1), ref_2, mut_2]
                            ),
                            file=outFiles[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()

                # Saves INDEL mutations into an INDEL simple text file
                else:
                    indel = True
                    if first_indel:
                        if not os.path.exists(output_path + "INDEL/"):
                            os.mkdir(output_path + "INDEL/")
                        chrom_namesI = [
                            str(output_path)
                            + "INDEL/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_filesI = [
                            open(file_name, "w", 10000000) for file_name in chrom_namesI
                        ]
                        outFilesI = dict(zip(out_chroms, chrom_filesI))
                        first_indel = False

                    if chrom in outFilesI:
                        print(
                            "\t".join([sample, chrom, start, ref, mut]),
                            file=outFilesI[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()
                prev_line = line

    # Closes the output files and returns the boolean flags
    if snv:
        for files in outFiles.values():
            files.close()
        # out_snv.close()
    if indel:
        for files in outFilesI.values():
            files.close()
        # out_indel.close()
    out.close()
    return (snv, indel, skipped_count, samples)


def convertMAF(project, vcf_path, genome, output_path, ncbi_chrom, log_file):
    """
    Converts input MAF files into a single simple text format.

    Parameters:
             project  -> unique name given to the current samples
            vcf_path  -> path to the input MAF files
            genome  -> reference genome
     output_path  -> path to the temporary folder

    Returns:
                     snv  -> Boolean that informs whether there are SNVs present in the
                                     input files
               indel  -> Boolean that informs whether there are INDELs present
                                     in the input files

    Ouput:
            Saves a single text file to the temporary file folder

    """

    # Collect all input file names and instantiate flags
    out = open(log_file, "a")
    files = os.listdir(vcf_path)
    first_indel = True
    first_SNV = True
    snv = False
    indel = False
    prev_line = None
    skipped_count = 0
    samples = []

    # Iterates through each file
    out_chroms = _get_output_chromosomes(genome)
    for file in files:
        header = True
        if file[0] == ".":
            continue
        name = file.split(".")
        with open(vcf_path + file) as f:
            for lines in f:
                if lines[0] == "#":
                    continue
                elif header:
                    header = False
                    continue
                try:
                    line = lines.strip().split("\t")
                    if len(line) == 0:
                        continue
                    chrom = line[4]
                    if len(chrom) > 2:
                        chrom = chrom[3:]
                    if chrom in ncbi_chrom:
                        chrom = ncbi_chrom[chrom]
                    if chrom.upper() == "M" or chrom == "mt":
                        chrom = "MT"
                    start = line[5]
                    end = line[6]
                    ref = line[10]
                    mut = line[12]
                    sample = line[15]
                    if sample not in samples:
                        samples.append(sample)
                    int(start)
                    int(end)

                except:
                    print(
                        "The given input files do not appear to be in the correct MAF format. Skipping this file: ",
                        file,
                    )
                    break

                # Saves SNV mutations into an SNV simple text file
                if len(ref) == 1 and len(mut) == 1 and ref != "-" and mut != "-":
                    snv = True
                    if ref not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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

                    if first_SNV:
                        if not os.path.exists(output_path + "SNV/"):
                            os.mkdir(output_path + "SNV/")
                        chrom_names = [
                            str(output_path)
                            + "SNV/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_files = [
                            open(file_name, "w", 10000000) for file_name in chrom_names
                        ]
                        outFiles = dict(zip(out_chroms, chrom_files))
                        first_SNV = False

                    if chrom in outFiles:
                        print(
                            "\t".join([sample, chrom, start, ref, mut]),
                            file=outFiles[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()

                elif (
                    len(ref) == 2
                    and len(mut) == 2
                    and "-" not in ref
                    and "-" not in mut
                ):
                    ref_1 = ref[0]
                    ref_2 = ref[1]
                    mut_1 = mut[0]
                    mut_2 = mut[1]
                    snv = True
                    # Check first base combination
                    if ref_1 not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut_1 not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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

                    if ref_1 == mut_1:
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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
                    # Check second base combination
                    if ref_2 not in "ACGT-":
                        print(
                            "The ref base is not recognized. Skipping this mutation: "
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

                    if mut_2 not in "ACGT-":
                        print(
                            "The mutation base is not recognized. Skipping this mutation: "
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

                    if ref_2 == mut_2:
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
                        out.flush()
                        skipped_count += 1
                        continue

                    if line == prev_line:
                        print(
                            "There appears to be a duplicate single base substitution. Skipping this mutation: "
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

                    if first_SNV:
                        if not os.path.exists(output_path + "SNV/"):
                            os.mkdir(output_path + "SNV/")
                        chrom_names = [
                            str(output_path)
                            + "SNV/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_files = [
                            open(file_name, "w", 10000000) for file_name in chrom_names
                        ]
                        outFiles = dict(zip(out_chroms, chrom_files))
                        first_SNV = False

                    if chrom in outFiles:
                        print(
                            "\t".join([sample, chrom, start, ref_1, mut_1]),
                            file=outFiles[chrom],
                        )
                        print(
                            "\t".join(
                                [sample, chrom, str(int(start) + 1), ref_2, mut_2]
                            ),
                            file=outFiles[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()

                # Saves INDEL mutations into an INDEL simple text file
                else:
                    start = str(int(line[5]) - 1)
                    indel = True
                    if first_indel:
                        if not os.path.exists(output_path + "INDEL/"):
                            os.mkdir(output_path + "INDEL/")
                        chrom_namesI = [
                            str(output_path)
                            + "INDEL/"
                            + out_chroms[i]
                            + "_"
                            + project
                            + ".genome"
                            for i in range(0, len(out_chroms))
                        ]
                        chrom_filesI = [
                            open(file_name, "w", 10000000) for file_name in chrom_namesI
                        ]
                        outFilesI = dict(zip(out_chroms, chrom_filesI))
                        first_indel = False

                    if chrom in outFilesI:
                        print(
                            "\t".join([sample, chrom, start, ref, mut]),
                            file=outFilesI[chrom],
                        )
                    else:
                        print(
                            chrom
                            + " is not supported. You will need to download that chromosome and create the required files. Continuing with the matrix generation...",
                            file=out,
                        )
                        out.flush()

                prev_line = line

    # Closes the output files and returns the boolean flags
    if snv:
        for files in outFiles.values():
            files.close()
        # out_snv.close()
    if indel:
        for files in outFilesI.values():
            files.close()
        # out_indel.close()
    out.close()
    return (snv, indel, skipped_count, samples)
