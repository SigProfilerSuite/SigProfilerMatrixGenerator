#!/usr/bin/env bash
# Double-click to remove the SigProfilerMatrixGenerator Workbench's Python environment and run
# records from this Mac. Your matrices and this folder are kept, and the reference genomes too
# unless you agree to remove them. It asks before removing anything.
# The first time, macOS may say it cannot verify the file: right-click it and choose Open.
cd "$(dirname "$0")" || exit 1
bash ./uninstall_web.sh "$@"
echo
read -r -p "  Press Enter to close this window. " _
