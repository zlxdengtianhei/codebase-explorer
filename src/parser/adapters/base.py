"""Language and resolver adapter contracts over canonical parser artifacts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.ir import CallSiteInventory, Relation, SourceUnit, Symbol
from src.parser.backend import SyntaxArtifact, TypedFailure


@dataclass(frozen=True)
class FileIR:
    """Normalized per-file IR produced by a language adapter."""

    source_unit: SourceUnit
    symbols: tuple[Symbol, ...] = ()
    relations: tuple[Relation, ...] = ()
    call_site_inventory: CallSiteInventory | None = None


@dataclass(frozen=True)
class SymbolIndex:
    """Read-only symbol index input for resolution adapters."""

    symbols: tuple[Symbol, ...]


@dataclass(frozen=True)
class ResolutionDelta:
    """Relations added or replaced by one resolution pass."""

    relations: tuple[Relation, ...]


class LanguageAdapter(ABC):
    """Normalize backend-specific syntax into canonical file IR."""

    @abstractmethod
    def normalize(self, artifact: SyntaxArtifact) -> FileIR | TypedFailure:
        """Return normalized IR without silently discarding unsupported syntax."""


class ResolverAdapter(ABC):
    """Resolve normalized references against a separate symbol index."""

    @abstractmethod
    def resolve(
        self, file_ir: FileIR, symbol_index: SymbolIndex
    ) -> ResolutionDelta | TypedFailure:
        """Return a typed resolution delta or a typed failure."""
