try:
    from ._version import version as __version__
except Exception:
    try:
        from importlib.metadata import PackageNotFoundError
        from importlib.metadata import version as _metadata_version
    except Exception:  # pragma: no cover
        PackageNotFoundError = Exception  # type: ignore

        def _metadata_version(_name: str) -> str:  # type: ignore
            raise PackageNotFoundError()

    try:
        __version__ = _metadata_version("SigProfilerMatrixGenerator")
    except PackageNotFoundError:
        __version__ = "0+unknown"


short_version = __version__
version = __version__
Update = ""
