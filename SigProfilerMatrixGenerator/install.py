#!/usr/bin/env python3

# Author: Erik Bergstrom

# Contact: ebergstr@eng.ucsd.edu

from __future__ import print_function

import glob
import hashlib
import os
import shutil
import sys

from SigProfilerMatrixGenerator.scripts import (
    ref_install,
    save_chrom_strings,
    save_chrom_tsb_separate,
    save_tsb_192,
    reference_genome_manager,
)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def install_chromosomes(
    genomes, reference_dir: ref_install.ReferenceDir, custom, rsync, bash
):
    ref_dir = str(reference_dir.path)
    absolute_fasta_root_dir = str(reference_dir.get_fasta_dir())
    if custom:
        for genome in genomes:
            os.system("gzip -d " + absolute_fasta_root_dir + "/" + genome + "/*.gz")
            save_chrom_strings.save_chrom_strings(genome, custom)
            print(
                "Chromosome string files for "
                + genome
                + " have been created. Continuing with installation."
            )
    else:
        for genome in genomes:
            species = None
            chrom_number = None
            if genome == "GRCh37" or genome == "GRCh38":
                species = "homo_sapiens"
                chrom_number = 24
            elif genome == "mm10" or genome == "mm9":
                species = "mus_musculus"
                chrom_number = 21
            elif genome == "rn6":
                species = "rattus_norvegicus"
                chrom_number = 22
            else:
                print(
                    genome
                    + " is not supported. The following genomes are supported:\nGRCh37, GRCh38, mm10"
                )
                sys.exit()

            chromosome_string_path = (
                "references/chromosomes/chrom_string/" + genome + "/"
            )
            absolute_fasta_path = absolute_fasta_root_dir + "/" + genome + "/"

            # this `if` statement is strange. Usually the "chromosomes" folder is in
            # ref_dir + "references", not directly in ref_dir, so I would expect
            # the first clause to always be False, and so the if statement
            if (
                os.path.exists(ref_dir + "chromosomes/tsb/" + genome)
                and len(os.listdir(ref_dir + "chromosomes/tsb/" + genome))
                >= chrom_number
            ):
                break
            wget_flag = True
            if (
                os.path.exists(chromosome_string_path) == False
                or len(os.listdir(chromosome_string_path)) <= chrom_number
            ):
                print(
                    "[DEBUG] Chromosome string files found at: "
                    + ref_dir
                    + chromosome_string_path
                )
                if (
                    os.path.exists(absolute_fasta_path) == False
                    or len(os.listdir(absolute_fasta_path)) <= chrom_number
                ):
                    print(
                        "[DEBUG] Chromosome fasta files found at: "
                        + absolute_fasta_path
                    )
                    print(
                        "Chromosomes are not currently saved as individual text files for "
                        + genome
                        + ". Downloading the files now..."
                    )
                    if not rsync:
                        if wget_flag:
                            try:
                                if genome == "GRCh37":
                                    if bash:
                                        os.system(
                                            "bash -c '"
                                            + 'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/ 2>> install.log"
                                            + "'"
                                        )
                                    else:
                                        os.system(
                                            'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/ 2>> install.log"
                                        )
                                elif genome == "mm9":
                                    if bash:
                                        os.system(
                                            "bash -c '"
                                            + 'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-67/fasta/mus_musculus/dna/ 2>> install.log"
                                            + "'"
                                        )
                                    else:
                                        os.system(
                                            'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-67/fasta/mus_musculus/dna/ 2>> install.log"
                                        )

                                elif genome == "rn6":
                                    if bash:
                                        os.system(
                                            "bash -c '"
                                            + 'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-96/fasta/rattus_norvegicus/dna/ 2>> install.log"
                                            + "'"
                                        )
                                    else:
                                        os.system(
                                            'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-96/fasta/rattus_norvegicus/dna/ 2>> install.log"
                                        )
                                else:
                                    if bash:
                                        os.system(
                                            "bash -c '"
                                            + 'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-93/fasta/"
                                            + species
                                            + "/dna/ 2>> install.log"
                                            + "'"
                                        )
                                    else:
                                        os.system(
                                            'wget -r -l1 -c -nc --no-parent -A "*.dna.chromosome.*" -nd -P '
                                            + absolute_fasta_path
                                            + " ftp://ftp.ensembl.org/pub/release-93/fasta/"
                                            + species
                                            + "/dna/ 2>> install.log"
                                        )

                                os.system(
                                    "gzip -d references/chromosomes/fasta/"
                                    + genome
                                    + "/*.gz"
                                )

                            except:
                                print(
                                    "The ensembl ftp site is not currently responding."
                                )
                                sys.exit()
                    else:
                        try:
                            if genome == "GRCh37":
                                if bash:
                                    os.system(
                                        "bash -c '"
                                        + "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/grch37/current/fasta/homo_sapiens/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                        + "'"
                                    )
                                else:
                                    os.system(
                                        "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/grch37/current/fasta/homo_sapiens/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                    )
                            elif genome == "mm9":
                                if bash:
                                    os.system(
                                        "bash -c '"
                                        + "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-67/fasta/mus_musculus/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                        + "'"
                                    )
                                else:
                                    os.system(
                                        "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-67/fasta/mus_musculus/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                    )
                            elif genome == "rn6":
                                if bash:
                                    os.system(
                                        "bash -c '"
                                        + "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-96/fasta/rattus_norvegicus/dna/ "
                                        + absolute_fasta_path
                                        + " 2>> install.log"
                                        + "'"
                                    )
                                else:
                                    os.system(
                                        "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-96/fasta/rattus_norvegicus/dna/ "
                                        + absolute_fasta_path
                                        + " 2>> install.log"
                                    )
                            else:
                                if bash:
                                    os.system(
                                        "bash -c '"
                                        + "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-93/fasta/"
                                        + species
                                        + "/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                        + "'"
                                    )
                                else:
                                    os.system(
                                        "rsync -av -m --include='*/' --include='*.dna.chromosome.*' --exclude='*' rsync://ftp.ensembl.org/ensembl/pub/release-93/fasta/"
                                        + species
                                        + "/dna/ "
                                        + absolute_fasta_path
                                        + " 2>&1>> install.log"
                                    )

                            # os.system("gunzip references/chromosomes/fasta/" + genome + "/*.gz")
                            os.system(
                                "gzip -d references/chromosomes/fasta/"
                                + genome
                                + "/*.gz"
                            )

                        except:
                            print("The ensembl ftp site is not currently responding.")
                            sys.exit()

                print(
                    "Chromosome fasta files for "
                    + genome
                    + " have been installed. Creating the chromosome string files now..."
                )
                save_chrom_strings.save_chrom_strings(genome, custom)
                print(
                    "Chromosome string files for "
                    + genome
                    + " have been created. Continuing with installation."
                )
                shutil.rmtree(absolute_fasta_path)

            else:
                print(
                    "Chromosome reference files exist for "
                    + genome
                    + ". Continuing with installation."
                )


def install_chromosomes_tsb(genomes, reference_dir: ref_install.ReferenceDir, custom):
    ref_dir = str(reference_dir.path)
    for genome in genomes:
        chrom_number = None
        if genome == "GRCh37" or genome == "GRCh38":
            chrom_number = 24
        elif genome == "mm10" or genome == "mm9":
            chrom_number = 21
        elif genome == "rn6":
            chrom_number = 22

        if custom:
            chrom_string_path = os.path.join(
                ref_dir, "references", "chromosomes", "chrom_string", genome, ""
            )
            chrom_number = len(
                [x for x in os.listdir(chrom_string_path) if x != ".DS_Store"]
            )
        chromosome_TSB_pathlib = reference_dir.get_tsb_dir() / genome / ""
        chromosome_TSB_path = f"{chromosome_TSB_pathlib}{os.sep}"
        transcript_files = os.path.join(
            ref_dir, "references", "chromosomes", "transcripts", genome, ""
        )
        print("[DEBUG] Chromosome tsb files found at: " + chromosome_TSB_path)

        if (
            os.path.exists(transcript_files) == False
            or len(os.listdir(transcript_files)) < 1
        ):
            print(
                "Please download the transcript files before proceeding. You can download the files from 'http://www.ensembl.org/biomart/martview'."
            )
            print(
                "Follow the format presented in the README file:\n\n\tGene stable ID  Transcript stable ID    Chromosome/scaffold name    Strand  Transcript start (bp)   Transcript end (bp)\n\n\n"
            )
            sys.exit()
        if (
            os.path.exists(chromosome_TSB_path) == False
            or len(os.listdir(chromosome_TSB_path)) < chrom_number
        ):
            print(
                "The transcriptional reference data for "
                + genome
                + " has not been saved. Creating these files now"
            )

            chromosome_string_path = (
                os.path.join(
                    ref_dir, "references", "chromosomes", "chrom_string", genome
                )
                + os.sep
            )
            transcript_path = (
                os.path.join(
                    ref_dir, "references", "chromosomes", "transcripts", genome
                )
                + os.sep
            )

            output_pathlib = reference_dir.get_tsb_dir() / genome / ""
            output_path = f"{output_pathlib}{os.sep}"
            if os.path.exists(output_path) == False:
                os.makedirs(output_path)

            save_tsb_192.save_tsb(chromosome_string_path, transcript_path, output_path)

        if not custom:
            corrupt = False
            for files in os.listdir(chromosome_TSB_path):
                if "proportions" in files:
                    continue
                if ".DS_Store" in files:
                    continue
                chrom = files.split(".")
                chrom = chrom[0]
                check = md5(chromosome_TSB_path + files)
                if reference_genome_manager.CHECKSUMS[genome][chrom] != check:
                    corrupt = True
                    os.remove(chromosome_TSB_path + files)
                    print(
                        "[DEBUG] Chromosome "
                        + chrom
                        + " md5sum did not match => reference md5sum: "
                        + str(reference_genome_manager.CHECKSUMS[genome][chrom])
                        + "    new file md5sum: "
                        + str(check)
                    )
            if corrupt:
                print(
                    "The transcriptional reference data appears to be corrupted. Please reinstall the "
                    + genome
                    + " genome."
                )
                sys.exit()

        print("The transcriptional reference data for " + genome + " has been saved.")


def install_chromosomes_tsb_BED(
    genomes, reference_dir: ref_install.ReferenceDir, custom
):
    for genome in genomes:
        ref_dir = str(reference_dir.path)
        tsb_bed_genome_dir = os.path.join(ref_dir, "chromosomes", "tsb_BED", genome, "")
        # this `if` statement is strange. Usually the "chromosomes" folder is in
        # ref_dir + "references", not directly in ref_dir, so I would expect
        # the first clause to always be True
        if (
            not os.path.exists(tsb_bed_genome_dir)
            or len(os.listdir(tsb_bed_genome_dir)) < 19
        ):
            is_custom = False
            if custom:
                is_custom = True
            save_chrom_tsb_separate.save_chrom_tsb_separate(
                genome, reference_dir, is_custom
            )
            print("The TSB BED files for " + genome + " have been saved.")


# Helper function for install()
# This function resets (removes and recreates) the specified directory.
# Optionally, it can also copy a file to the newly created directory.
def reset_directory(path, file_to_copy=None):
    if os.path.exists(path):
        # Prompt the user for confirmation
        proceed = input(f"Are you sure you want to delete {path}? (yes/no): ")
        if proceed.lower() == "yes":
            shutil.rmtree(path)
        else:
            print(f"Directory {path} was not deleted.")
            return  # Exit the function if user says "no"

    os.makedirs(path)

    if file_to_copy:
        shutil.copy(file_to_copy, path)


def print_available_tools():
    """
    Checks for the presence of required tools (curl, wget, rsync) and
    prints the status of each tool in a table format.
    """
    # Update the list of required tools
    required_tools = ["curl", "wget", "rsync"]

    # Print the table header
    print("{:<10} | {:<10}".format("Tool", "Installed"))
    print("-" * 23)

    # Check each tool and print its status
    for tool in required_tools:
        if shutil.which(tool):
            print("{:<10} | {:<10}".format(tool, "True"))
        else:
            print("{:<10} | {:<10}".format(tool, "False"))


def install(
    genome,
    custom=False,
    rsync=False,
    bash=True,
    ftp=True,
    fastaPath=None,
    transcriptPath=None,
    exomePath=None,
    offline_files_path=None,
    volume=None,
):
    # Genome installation is using locally provided files
    if custom or offline_files_path is not None:
        ftp = False
    reference_dir = ref_install.reference_dir(secondary_chromosome_install_dir=volume)
    ref_dir = str(reference_dir.path)

    if not custom and offline_files_path is None:
        # 1. Check for required tools
        print_available_tools()

    if os.path.exists("install.log"):
        os.remove("install.log")

    chrom_string_dir = os.path.join(
        ref_dir, "references", "chromosomes", "chrom_string"
    )
    chrom_fasta_dir = os.path.join(ref_dir, "references", "chromosomes", "fasta")
    chrom_tsb_dir = str(reference_dir.get_tsb_dir())
    matrix_dir = os.path.join(ref_dir, "references", "matrix")
    vcf_dir = os.path.join(ref_dir, "references", "vcf_files")
    bed_dir = os.path.join(vcf_dir, "BED")
    log_dir = "logs"
    new_dirs = [
        ref_dir,
        chrom_string_dir,
        chrom_fasta_dir,
        chrom_tsb_dir,
        matrix_dir,
        vcf_dir,
        bed_dir,
        log_dir,
    ]

    # 2. Make necessary directories for installation
    for dirs in new_dirs:
        if not os.path.exists(dirs):
            os.makedirs(dirs)

    # 3. Install a custom genome with user provided files (FASTA, transcripts, exome interval list)
    if custom:
        chrom_fasta_genome_dir = os.path.join(chrom_fasta_dir, genome, "")
        if os.path.exists(chrom_fasta_genome_dir):
            shutil.rmtree(chrom_fasta_genome_dir)
        os.makedirs(chrom_fasta_genome_dir)
        fastaFiles = glob.iglob(os.path.join(fastaPath, "*.gz"))
        for file in fastaFiles:
            if os.path.isfile(file):
                shutil.copy(file, chrom_fasta_genome_dir)

        transcript_dir = os.path.join(
            ref_dir, "references", "chromosomes", "transcripts", genome
        )
        exome_dir = os.path.join(ref_dir, "references", "chromosomes", "exome", genome)

        reset_directory(transcript_dir, transcriptPath)
        reset_directory(exome_dir, exomePath)

    # 4. Install a genome using from ftp server using ftlib or curl
    if ftp:
        genome_manager = reference_genome_manager.ReferenceGenomeManager(volume)
        genome_manager.download_genome(genome)

    # 5. Install a genome using locally provided files
    elif offline_files_path is not None:
        print("Beginning installation using locally provided files.")
        genome_manager = reference_genome_manager.ReferenceGenomeManager(volume)
        genome_manager.install_local_genome(genome, offline_files_path)
        print("The transcriptional reference data for " + genome + " has been saved.")

    # 6. Install a genome using rsync or wget
    #   linux legacy installer supports just GRCh37, GRCh38, mm9, mm10, rn6
    else:
        print("Beginning installation. This may take up to 20 minutes to complete.")
        print(
            "[DEBUG] Path to SigProfilerMatrixGenerator used for the install: ", ref_dir
        )

        genomes = [genome]

        if os.path.exists("install.log"):
            os.remove("install.log")

        install_chromosomes(genomes, reference_dir, custom, rsync, bash)
        install_chromosomes_tsb(genomes, reference_dir, custom)

        if custom:
            install_chromosomes_tsb_BED(genomes, reference_dir, custom)

    if os.path.exists("context_distributions/"):
        shutil.copy("context_distributions/", "references/chromosomes/")

    print("All reference files have been created.")
    if "havana" in genome:
        genome = genome.split("_")[0]

    print(
        "To proceed with matrix_generation, please provide the path to your vcf files and an appropriate output path."
    )
    shutil.rmtree(chrom_string_dir)
    print("Installation complete.")
