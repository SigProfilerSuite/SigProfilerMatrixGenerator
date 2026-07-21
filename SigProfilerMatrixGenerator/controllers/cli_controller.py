import argparse
from typing import List
from SigProfilerMatrixGenerator import test_helpers
from SigProfilerMatrixGenerator.scripts import (
    SigProfilerMatrixGeneratorFunc as mg,
    SVMatrixGenerator as sv_mg,
    CNVMatrixGenerator as cnv_mg,
    reference_genome_manager,
)


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_arguments_test(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run tests for SigProfilerMatrixGenerator."
    )
    parser.add_argument(
        "-t",
        "--test_genome",
        help="Genomes to test (GRCh37, any test genome, or all)",
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--download_genomes",
        help="Download genomes for the test (GRCh37, any test genome, or all)",
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--volume",
        help="Specify a destination for the downloaded genomes (default: None, used for Docker)",
        default=None,
    )

    result = parser.parse_args(args)
    return result


def parse_arguments_install(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install reference genome files.")
    parser.add_argument(
        "genome",
        help="The reference genome to install. Supported genomes include {c_elegans, dog, ebv, GRCh37, GRCh38, mm9, mm10, mm39, rn6, rn7, yeast}.",
    )
    parser.add_argument(
        "-l",
        "--local_genome",
        help="""
            Install an offline reference genome downloaded from the Alexandrov Lab's FTP server.
            Provide the absolute path to the directory containing the locally-stored
            <genome>.tar.gz file.
            For downloads, visit AlexandrovLab's ftp server:
            ftp://alexandrovlab-ftp.ucsd.edu/pub/tools/SigProfilerMatrixGenerator/
            """,
        default=None,
    )
    parser.add_argument(
        "-v",
        "--volume",
        help="Specify a destination for the downloaded genomes (default: None, used for Docker)",
        default=None,
    )
    result = parser.parse_args(args)
    return result


def parse_arguments_matrix_generator(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create mutational matrices for all types of somatic mutations"
    )

    # Mandatory arguments
    parser.add_argument("project", help="The name of the project.")
    parser.add_argument(
        "reference_genome",
        help="The name of the reference genome. Supported values {c_elegans, dog, ebv, GRCh37, GRCh38, mm9, mm10, mm39, rn6, rn7, yeast}.",
    )
    parser.add_argument("path_to_input_files", help="The path to the input files.")

    # Optional arguments
    parser.add_argument(
        "--exome",
        action="store_true",
        help="Downsamples mutational matrices to the exome regions of the genome. Default is False.",
    )
    parser.add_argument(
        "--bed_file",
        default=None,
        help="Downsamples mutational matrices to custom regions of the genome. Provide full path to BED file. Note: BED file header is required. Default is None.",
    )
    parser.add_argument(
        "--chrom_based",
        action="store_true",
        help="Outputs chromosome-based matrices. Default is False.",
    )
    parser.add_argument(
        "--plot",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Integrates with SigProfilerPlotting to output visualizations for each matrix. Default is False.",
    )
    parser.add_argument(
        "--tsb_stat",
        type=str2bool,
        nargs="?",
        const=True,
        default=False,
        help="Outputs the results of a transcriptional strand bias test for the respective matrices. Default is False.",
    )
    parser.add_argument(
        "--seqInfo",
        type=str2bool,
        nargs="?",
        const=True,
        default=True,
        help="Outputs original mutations into a text file with the SigProfilerMatrixGenerator classification for each mutation. Default is True.",
    )
    parser.add_argument(
        "--cushion",
        type=int,
        default=100,
        help="Adds an Xbp cushion to the exome/bed_file ranges for downsampling mutations. Default is 100.",
    )

    parser.add_argument(
        "-v",
        "--volume",
        help="Specify a destination for the downloaded genomes (default: None, used for Docker)",
        default=None,
    )

    parser.add_argument(
        "--output_directory",
        help="Specify a custom output directory (default: None).",
        default=None,
    )

    result = parser.parse_args(args)
    return result


def parse_arguments_sv_matrix_generator(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a structural variant (SV) matrix from input data."
    )

    # Mandatory arguments
    parser.add_argument("input_dir", help="The directory containing the input files.")
    parser.add_argument("project", help="The name of the project.")
    parser.add_argument(
        "output_dir", help="The directory where the output matrix will be stored."
    )

    result = parser.parse_args(args)
    return result


def parse_arguments_cnv_matrix_generator(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Copy Number Variation (CNV) matrix."
    )

    # Mandatory arguments
    parser.add_argument(
        "file_type",
        choices=[
            "ASCAT",
            "ASCAT_NGS",
            "SEQUENZA",
            "ABSOLUTE",
            "BATTENBERG",
            "FACETS",
            "PURPLE",
            "TCGA",
        ],
        help="The type of the input file based on the CNV calling tool used (e.g., 'ASCAT').",
    )
    parser.add_argument(
        "input_file", help="The absolute path to the multi-sample segmentation file."
    )
    parser.add_argument("project", help="The name of the project.")
    parser.add_argument(
        "output_path", help="The path where the output CNV matrix will be stored."
    )

    result = parser.parse_args(args)
    return result


class CliController:
    def dispatch_install(self, user_args: List[str]) -> None:
        parsed_args = parse_arguments_install(user_args)
        rgm = reference_genome_manager.ReferenceGenomeManager(parsed_args.volume)
        # ftp genome installation (default)
        if parsed_args.local_genome is None:
            rgm.download_genome(parsed_args.genome)
        # local genome installation
        else:
            rgm.install_local_genome(parsed_args.genome, parsed_args.local_genome)

    def dispatch_test(self, user_args: List[str]) -> None:
        parsed_args = parse_arguments_test(user_args)

        if parsed_args.download_genomes:
            test_helpers.install_genomes(parsed_args.download_genomes)
        if parsed_args.test_genome:
            test_helpers.test_genomes(parsed_args.test_genome, parsed_args.volume)


    def dispatch_matrix_generator(self, user_args: List[str]) -> None:
        parsed_args = parse_arguments_matrix_generator(user_args)

        mg.SigProfilerMatrixGeneratorFunc(
            project=parsed_args.project,
            reference_genome=parsed_args.reference_genome,
            path_to_input_files=parsed_args.path_to_input_files,
            exome=parsed_args.exome,
            bed_file=parsed_args.bed_file,
            chrom_based=parsed_args.chrom_based,
            plot=parsed_args.plot,
            tsb_stat=parsed_args.tsb_stat,
            seqInfo=parsed_args.seqInfo,
            cushion=parsed_args.cushion,
            volume=parsed_args.volume,
            output_directory=parsed_args.output_directory,
        )

    def dispatch_sv_matrix_generator(self, user_args: List[str]) -> None:
        parsed_args = parse_arguments_sv_matrix_generator(user_args)
        sv_mg.generateSVMatrix(
            input_dir=parsed_args.input_dir,
            project=parsed_args.project,
            output_dir=parsed_args.output_dir,
        )

    def dispatch_cnv_matrix_generator(self, user_args: List[str]) -> None:
        parsed_args = parse_arguments_cnv_matrix_generator(user_args)
        cnv_mg.generateCNVMatrix(
            file_type=parsed_args.file_type,
            input_file=parsed_args.input_file,
            project=parsed_args.project,
            output_path=parsed_args.output_path,
        )
