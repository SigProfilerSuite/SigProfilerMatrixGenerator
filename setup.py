import os
import shutil

from setuptools import setup

VERSION = "1.3.6"

# remove the dist folder first if exists
if os.path.exists("dist"):
    shutil.rmtree("dist")


def readme():
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, "README.md"), encoding="latin-1") as f:
        long_description = f.read()
        return long_description


def write_version_py(filename="SigProfilerMatrixGenerator/version.py"):
    # Copied from numpy setup.py
    cnt = """
# THIS FILE IS GENERATED FROM SIGPROFILEMATRIXGENERATOR SETUP.PY
short_version = '%(version)s'
version = '%(version)s'
Update = 'v1.3.6: Add automated Docker build and publish pipeline'

	"""
    fh = open(filename, "w")
    fh.write(
        cnt
        % {
            "version": VERSION,
        }
    )
    fh.close()


write_version_py()

setup(
    name="SigProfilerMatrixGenerator",
    version=VERSION,
    description="SigProfiler matrix generator tool",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/SigProfilerSuite/SigProfilerMatrixGenerator.git",
    author="Erik Bergstrom",
    author_email="ebergstr@eng.ucsd.edu",
    license="UCSD",
    packages=["SigProfilerMatrixGenerator"],
    python_requires=">=3.9",
    install_requires=[
        "matplotlib>=2.2.2",
        "sigProfilerPlotting>=1.4.1",
        "statsmodels>=0.9.0",
        "numpy>=2.0.0",
        "pandas>=2.0.0",
        "scipy>=1.12.0",
    ],
    entry_points={
        "console_scripts": [
            "SigProfilerMatrixGenerator=SigProfilerMatrixGenerator.scripts.SigProfilerMatrixGenerator_CLI:main_function",
        ],
    },
    extras_require={
        "tests": [
            "pytest",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
