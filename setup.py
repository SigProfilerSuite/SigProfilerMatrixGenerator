from pathlib import Path

from setuptools import find_namespace_packages, setup


LONG_DESCRIPTION = Path("README.md").read_text(encoding="utf-8")

INSTALL_REQUIRES = [
    "matplotlib>=2.2.2",
    "sigProfilerPlotting>=1.4.1",
    "statsmodels>=0.9.0",
    "numpy>=2.0.0",
    "pandas>=2.0.0",
    "scipy>=1.12.0",
]

VERSION_TEMPLATE = "version = '{version}'\n"


setup(
    name="SigProfilerMatrixGenerator",
    use_scm_version={
        "write_to": "SigProfilerMatrixGenerator/_version.py",
        "write_to_template": VERSION_TEMPLATE,
        "fallback_version": "0+unknown",
    },
    description="SigProfiler matrix generator tool",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/SigProfilerSuite/SigProfilerMatrixGenerator.git",
    author="Erik Bergstrom",
    author_email="ebergstr@eng.ucsd.edu",
    license="UCSD",
    packages=find_namespace_packages(include=["SigProfilerMatrixGenerator*"]),
    python_requires=">=3.9",
    install_requires=INSTALL_REQUIRES,
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
