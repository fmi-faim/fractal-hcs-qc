"""Package description."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fractal_hcs_qc")
except PackageNotFoundError:
    __version__ = "uninstalled"
