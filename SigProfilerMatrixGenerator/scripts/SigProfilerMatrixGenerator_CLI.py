#!/usr/bin/env python3

import sys
from SigProfilerMatrixGenerator.controllers import cli_controller


def main_function():
    commands = {
        "install": "Install reference genome files (required to generate matrices).",
        "matrix_generator": "Create mutational matrices for SBSs, DBSs, and INDELs.",
        "sv_matrix_generator": "Create mutational matrices for SVs.",
        "cnv_matrix_generator": "Create mutational matrices for CNVs.",
        "web": "Launch the local SigProfilerMatrixGenerator dashboard.",
    }

    if len(sys.argv) < 2 or sys.argv[1].lower() not in commands:
        print_usage(commands)
        sys.exit(1)

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    controller = cli_controller.CliController()

    """
    The test cli is not included here because tests
    are not distributed with the package and are only
    to be run from the source code.
    """
    if command == "install":
        controller.dispatch_install(args)
    elif command == "matrix_generator":
        controller.dispatch_matrix_generator(args)
    elif command == "sv_matrix_generator":
        controller.dispatch_sv_matrix_generator(args)
    elif command == "cnv_matrix_generator":
        controller.dispatch_cnv_matrix_generator(args)
    elif command == "web":
        controller.dispatch_web(args)


def print_usage(commands):
    """Prints the usage message."""
    print("Usage: SigProfilerMatrixGenerator <command> [<args>]\n")
    print("Commands:")
    for cmd, desc in commands.items():
        print(f"  {cmd}: {desc}")


if __name__ == "__main__":
    main_function()
