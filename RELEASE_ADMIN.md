# SigProfilerMatrixGenerator Release Administration

This repository publishes Python distributions through GitHub Actions and PyPI
Trusted Publishing. The release process intentionally has two publish steps:

1. Push a version tag such as `v1.3.7` to publish to TestPyPI.
2. Publish a GitHub Release for that same tag to publish to PyPI.

Merging into `master` does not publish a Python package by itself.

## Required GitHub Setup

Create these GitHub environments:

```text
testpypi
pypi
```

The environment names must exactly match `.github/workflows/release.yml`.
The `pypi` environment should require reviewer approval before deployment.

## Required TestPyPI Trusted Publisher

Configure this from TestPyPI:

```text
PyPI Project Name: SigProfilerMatrixGenerator
Owner: SigProfilerSuite
Repository name: SigProfilerMatrixGenerator
Workflow name: release.yml
Environment name: testpypi
```

If the project does not exist on TestPyPI yet, use the pending trusted
publisher flow to create it on first publish.

## Required PyPI Trusted Publisher

Configure this from the existing PyPI project:

```text
PyPI Project Name: SigProfilerMatrixGenerator
Owner: SigProfilerSuite
Repository name: SigProfilerMatrixGenerator
Workflow name: release.yml
Environment name: pypi
```

For an existing PyPI project, configure this from:

```text
PyPI -> Your projects -> SigProfilerMatrixGenerator -> Manage -> Publishing
```

If `Manage` is disabled, ask a current project owner to add your PyPI account
as an owner or maintainer with publishing permissions.

## Versioning

Package versions are derived from Git tags by `setuptools_scm`.

Release tags must start with `v`, for example:

```text
v1.3.7
```

The package version for that tag becomes:

```text
1.3.7
```

Untagged commits produce development versions, for example:

```text
1.3.7.dev2+gabcdef0.d20260524
```

The generated file `SigProfilerMatrixGenerator/_version.py` is ignored and
must not be committed.

## Release Flow

First merge the release-ready branch into `master` through the repository's
normal review process.

Then create and push the tag:

```bash
git checkout master
git pull origin master
git tag -a v1.3.7 -m "v1.3.7"
git push origin v1.3.7
```

The pushed tag triggers `.github/workflows/release.yml` and publishes to
TestPyPI.

After TestPyPI is verified, publish a GitHub Release for the same tag. That
release event triggers the PyPI publish job.

## Verification

After the tag push, verify the GitHub Actions run:

- build job passed
- `twine check` passed
- package version printed correctly
- TestPyPI publish job passed

Optional TestPyPI install check:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple SigProfilerMatrixGenerator==1.3.7
python -c "import SigProfilerMatrixGenerator; print(SigProfilerMatrixGenerator.__version__)"
```

After publishing the GitHub Release, verify the PyPI job and package page:

```text
https://pypi.org/project/SigProfilerMatrixGenerator/
```

Optional PyPI install check:

```bash
python -m pip install SigProfilerMatrixGenerator==1.3.7
python -c "import SigProfilerMatrixGenerator; print(SigProfilerMatrixGenerator.__version__)"
```

## Troubleshooting

If the package version is `0+unknown`, check that:

- the release workflow checkout uses `fetch-depth: 0`
- the tag exists locally and remotely
- the tag starts with `v`

If Trusted Publishing fails, check that:

- the TestPyPI/PyPI trusted publisher values exactly match this repository
- the GitHub environment name is `testpypi` or `pypi`
- the publish job has `id-token: write`
