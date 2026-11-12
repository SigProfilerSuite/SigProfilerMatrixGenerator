#!/usr/bin/env bash
# Remove what the SigProfilerMatrixGenerator Workbench installed on this Mac (or Linux computer):
#   - its private Python environment, .venv-dashboard, next to this script
#   - its run records, in ~/.cache/sigprofilermatrixgenerator
#   - only if you say so as well: the reference genomes installed in this folder, in
#     SigProfilerMatrixGenerator/references/chromosomes/tsb (runs from Python or the
#     command line in this folder use them too)
# Your matrices (wherever runs wrote them) and the rest of this folder are kept; delete them
# yourself if you no longer need them. Run it by double-clicking uninstall_web.command, or
# from Terminal: ./uninstall_web.sh [--yes] [--genomes]
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv-dashboard"
TSB="$HERE/SigProfilerMatrixGenerator/references/chromosomes/tsb"
STATE="${XDG_CACHE_HOME:-$HOME/.cache}/sigprofilermatrixgenerator"
YES=0
GENOMES_TOO=0
for arg in "$@"; do
  case "$arg" in
    -y|--yes) YES=1 ;;
    --genomes) GENOMES_TOO=1 ;;
    -h|--help)
      echo "Usage: ./uninstall_web.sh [--yes] [--genomes]"
      echo "Removes the Workbench's Python environment ($VENV) and run records ($STATE)."
      echo "Matrices and this folder are kept, and so are the reference genomes installed"
      echo "in it unless you agree to remove them too."
      echo "  --yes      remove without asking (the genomes are kept)"
      echo "  --genomes  remove the reference genomes too, without asking"
      exit 0 ;;
  esac
done

in_use() {
  # The Workbench, or one of its runs, still running?
  local pidfile="$STATE/dashboard.pid"
  if [ -f "$pidfile" ]; then
    local pid
    pid="$(cut -d: -f1 "$pidfile" 2>/dev/null)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then return 0; fi
  fi
  ps -axo command= 2>/dev/null | grep -F -- "$VENV/" | grep -F -- "SigProfilerMatrixGenerator.web" \
    | grep -v grep >/dev/null
}

echo
echo "  SigProfilerMatrixGenerator Workbench uninstaller"
echo "  ------------------------------------------------"

if in_use; then
  echo "  The Workbench is still running. Click Quit in it (or run ./launch_web.sh --stop),"
  echo "  then run this again."
  exit 1
fi

HAS_VENV=0
[ -f "$VENV/pyvenv.cfg" ] && HAS_VENV=1
RUNS=0
[ -d "$STATE/jobs" ] && RUNS="$(find "$STATE/jobs" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
HAS_STATE=0
{ [ -d "$STATE/jobs" ] || [ -f "$STATE/dashboard.pid" ] || [ -f "$STATE/dashboard.lock" ]; } && HAS_STATE=1

# Installed genomes: one folder each under tsb/, which the package ships empty (but for
# __init__.py). Unfinished downloads (spmg-reference-*) are not genomes.
GENOMES=()
if [ -d "$TSB" ]; then
  for dir in "$TSB"/*/; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    case "$name" in __*|spmg-reference-*) continue ;; esac
    GENOMES+=("$name")
  done
fi
HAS_GENOMES=0
[ "${#GENOMES[@]}" -gt 0 ] && HAS_GENOMES=1

if [ "$HAS_VENV" = 0 ] && [ "$HAS_STATE" = 0 ] && [ "$HAS_GENOMES" = 0 ]; then
  echo "  Nothing to remove: the Workbench's Python environment and run records are not here."
  exit 0
fi

GENOME_LIST=""
GENOME_SIZE=""
if [ "$HAS_GENOMES" = 1 ]; then
  GENOME_LIST="${GENOMES[*]}"
  GENOME_SIZE="$(cd "$TSB" && du -shc "${GENOMES[@]}" 2>/dev/null | tail -1 | cut -f1)"
fi

REMOVE=0
if [ "$HAS_VENV" = 1 ] || [ "$HAS_STATE" = 1 ]; then
  echo "  This removes:"
  if [ "$HAS_VENV" = 1 ]; then
    SIZE="$(du -sh "$VENV" 2>/dev/null | cut -f1)"
    echo "    - the Python environment $VENV (${SIZE:-?})"
  fi
  [ "$HAS_STATE" = 1 ] && echo "    - the records of $RUNS run(s) in $STATE (settings and logs, not matrices)"
  echo
  echo "  It keeps your matrices (each run's output folder) and this folder ($HERE)."
  echo

  if [ "$YES" = 1 ]; then
    REMOVE=1
  else
    read -r -p "  Remove them? Type y and press Enter: " ans
    case "$ans" in
      y|Y|yes|YES|Yes) REMOVE=1 ;;
      *) echo "  Nothing was removed."; exit 0 ;;
    esac
    echo
  fi
else
  echo "  The Workbench's Python environment and run records are not here."
  echo
fi

REMOVE_GENOMES=0
if [ "$HAS_GENOMES" = 1 ]; then
  echo "  Reference genomes installed in this folder: $GENOME_LIST (${GENOME_SIZE:-?})"
  echo "    in $TSB"
  echo "  Runs from Python or the command line in this folder use them too, and each one"
  echo "  takes a while to download again."
  if [ "$GENOMES_TOO" = 1 ]; then
    REMOVE_GENOMES=1
  elif [ "$YES" = 1 ]; then
    echo "  They are kept (--genomes removes them too)."
  else
    read -r -p "  Remove these genomes too? Type y and press Enter, or just Enter to keep them: " ans
    case "$ans" in
      y|Y|yes|YES|Yes) REMOVE_GENOMES=1 ;;
      *) echo "  The genomes are kept." ;;
    esac
  fi
  echo
fi

status=0
if [ "$REMOVE" = 1 ] && [ "$HAS_VENV" = 1 ]; then
  if rm -rf -- "$VENV"; then
    echo "  Removed $VENV."
  else
    echo "  Could not remove $VENV; delete that folder yourself."
    status=1
  fi
fi
if [ "$REMOVE" = 1 ] && [ "$HAS_STATE" = 1 ]; then
  # Only the Workbench's own files; the folder goes only if that empties it.
  rm -rf -- "$STATE/jobs"
  rm -f -- "$STATE/dashboard.pid" "$STATE/dashboard.lock"
  rmdir "$STATE" 2>/dev/null || true
  if [ -d "$STATE/jobs" ]; then
    echo "  Could not remove the run records in $STATE; delete them yourself."
    status=1
  else
    echo "  Removed the run records."
  fi
fi
if [ "$REMOVE_GENOMES" = 1 ]; then
  for name in "${GENOMES[@]}"; do
    if rm -rf -- "${TSB:?}/$name"; then
      echo "  Removed the reference genome $name."
    else
      echo "  Could not remove $TSB/$name; delete that folder yourself."
      status=1
    fi
  done
fi

if [ "$REMOVE" = 0 ] && [ "$REMOVE_GENOMES" = 0 ]; then
  echo "  Nothing was removed."
  exit 0
fi

echo
echo "  Done. To start again later, double-click launch_web.command: it sets everything up anew."
echo "  To remove the rest, delete this folder and, if you no longer need them, your matrices."
exit $status
