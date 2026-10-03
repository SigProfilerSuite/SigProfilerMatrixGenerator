# CHM13 Test Example

This small synthetic example tests matrix generation using the corrected
`CHM13-T2T` reference. It contains three samples: one single-base substitution,
one double-base substitution, and two indels. All positions use CHM13 coordinates.
It is a smoke test, not a biological dataset or full-genome validation.

## Install the Development Branch

Use a separate Python environment for testing:

```bash
python -m venv chm13-test-env
source chm13-test-env/bin/activate
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/SigProfilerSuite/SigProfilerMatrixGenerator.git@prepare/chm13-support-v1.4.0"
```

On Windows, activate with `chm13-test-env\Scripts\activate` instead.
For reproducible testing, record the installed Git commit with
`python -m pip freeze`.

## Install the Reference Locally

Obtain the validated `CHM13-T2T.tar.gz` archive from the maintainer's shared
download link. It is not included in the example ZIP. Keep the exact filename
and do not extract it manually. The expected SHA-256 is:

```text
e8d0309879486beefb83d730c00b8cf8733aa7cd1716f694855817e69943f6a3
```

Verify on Linux with `sha256sum CHM13-T2T.tar.gz`, on macOS with
`shasum -a 256 CHM13-T2T.tar.gz`, or in Windows PowerShell with
`Get-FileHash CHM13-T2T.tar.gz -Algorithm SHA256`.

```bash
SigProfilerMatrixGenerator install CHM13-T2T \
  --local_genome /absolute/path/to/archive-folder \
  --volume /absolute/path/to/reference-folder
```

Replace the example paths. `--local_genome` is the folder containing the
archive. `--volume` is the folder where the reference is installed; use that
same folder when running the example. Local installation does not need FTP.
Allow approximately 4 GB of space for the archive and installed reference.
If `SIGPROFILERMATRIXGENERATOR_VOLUME` is set, it takes precedence over
`--volume`; unset it or make it match the intended reference folder.

## Download and Run

Download and extract [the example ZIP](assets/examples/chm13/chm13_my_project_example.zip).
It includes the script and a `mixed_variant_inputs` folder. Keep them together.
From the extracted folder, run:

```bash
python test_my_project.py --volume /absolute/path/to/reference-folder
```

`my_project` is the output project name, not an input folder. Results are saved
under `my_project_output` beside the script. Each VCF filename identifies a sample.

| Sample | Expected Result |
| --- | --- |
| `sbs` | One SBS96 `A[C>A]G`; SBS6144 strand channel `T:GA[C>A]GT` |
| `dbs` | One DBS78 `CC>TT` |
| `indel` | One ID83 `1:Del:C:0` and one `1:Ins:T:0` |

The script prints `PASS` if all assertions succeed. DBS events can also
contribute component substitutions to SBS matrices; the SBS assertion applies
only to the separate `sbs` sample. Share the installed commit, Python version,
complete console output, and generated matrices when reporting a failure.

## Demo Code

[Download the Python script](assets/examples/chm13/test_my_project.py).

```python
--8<-- "docs/assets/examples/chm13/test_my_project.py"
```

Individual inputs: [SBS VCF](assets/examples/chm13/mixed_variant_inputs/sbs.vcf),
[DBS VCF](assets/examples/chm13/mixed_variant_inputs/dbs.vcf), and
[indel VCF](assets/examples/chm13/mixed_variant_inputs/indel.vcf).

The reference covers nuclear chromosomes 1-22, X, and Y, not MT. CHM13-specific
opportunity tables and downstream signature catalogues are outside this example.
See [supported genomes and provenance](Currently-Supported-Genomes.md).
