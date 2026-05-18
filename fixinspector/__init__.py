"""FIX Inspector package."""

from importlib.metadata import version, PackageNotFoundError

try:
    # package name defined in [project.name] of pyproject.toml
    __version__ = version("fixinspector")
except PackageNotFoundError:
    # fallback for when the package is not installed (e.g. during local dev)
    __version__ = "0.0.0"


__all__ = ["__version__"]
