"""Public adapter contracts and backend registry."""

from src.parser.adapters.base import (
    FileIR,
    LanguageAdapter,
    ResolutionDelta,
    ResolverAdapter,
    SymbolIndex,
)
from src.parser.adapters.registry import BackendRegistry, default_backend_registry

__all__ = [
    "BackendRegistry",
    "FileIR",
    "LanguageAdapter",
    "ResolutionDelta",
    "ResolverAdapter",
    "SymbolIndex",
    "default_backend_registry",
]

