import sys
from pathlib import Path

# tests/scripts/test_build_reference_archive.py and test_chm13_opportunities.py
# import the dev-only tools/ package (not shipped with the installed
# distribution, see setup.py's find_namespace_packages include list). Make it
# importable when running the test suite from a checkout, regardless of
# whether pytest was invoked as `pytest` or `python -m pytest`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
