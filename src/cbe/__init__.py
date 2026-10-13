"""Codebase Explorer semantic documentation product."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("codebase-explorer")
except PackageNotFoundError:
    # Source checkout without installed distribution metadata.
    __version__ = "2.1.1"
