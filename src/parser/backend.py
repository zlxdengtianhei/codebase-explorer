"""Typed parser backend boundary and built-in backend implementations."""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import platform
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

from src.ir import SourceUnit


class BackendStatus(StrEnum):
    """Runtime state of a backend probe."""

    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    ERROR = "error"


class FailureCode(StrEnum):
    """Stable categories for failures crossing the parser boundary."""

    BACKEND_UNAVAILABLE = "backend_unavailable"
    INCOMPATIBLE_API = "incompatible_api"
    UNSUPPORTED_LANGUAGE = "unsupported_language"
    INVALID_INPUT = "invalid_input"
    SOURCE_UNAVAILABLE = "source_unavailable"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    PARSE_ERROR = "parse_error"
    BACKEND_ERROR = "backend_error"


@dataclass(frozen=True)
class BackendHealth:
    """Truthful result of probing one installed backend."""

    backend_id: str
    backend_version: str
    status: BackendStatus
    supported_languages: tuple[str, ...]
    semantic_tier: str
    toolchain_conditions: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def available(self) -> bool:
        return self.status is BackendStatus.HEALTHY


@dataclass(frozen=True)
class TypedFailure:
    """Actionable non-success returned by backend operations."""

    code: FailureCode
    message: str
    backend_id: str
    language: str
    retryable: bool = False
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class SyntaxArtifact:
    """Opaque syntax result awaiting a language adapter."""

    source_unit: SourceUnit
    backend_id: str
    backend_version: str
    language: str
    syntax_tree: object
    diagnostics: tuple[str, ...] = ()


class ParserBackend(ABC):
    """Narrow backend contract consumed by the registry and adapters."""

    @abstractmethod
    def health(self, *, refresh: bool = False) -> BackendHealth:
        """Probe the backend; ``refresh`` invalidates any cached observation."""

    @abstractmethod
    def parse(self, source_unit: SourceUnit) -> SyntaxArtifact | TypedFailure:
        """Parse one canonical source unit or return a typed failure."""


Importer = Callable[[str], object]


class GraphSitterBackend(ParserBackend):
    """Boundary for the installed ``graph_sitter`` package."""

    backend_id = "graph_sitter"

    def __init__(
        self,
        *,
        root: str | Path | None = None,
        importer: Importer = importlib.import_module,
    ) -> None:
        self._root = None if root is None else Path(root).resolve()
        self._importer = importer
        self._health: BackendHealth | None = None

    def health(self, *, refresh: bool = False) -> BackendHealth:
        if refresh:
            self._health = None
        if self._health is not None:
            return self._health
        try:
            # Third-party import-time deprecations are not a backend health
            # failure.  Keep them at this boundary so warning-strict callers
            # can still receive a typed probe result.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                warnings.simplefilter("ignore", FutureWarning)
                module = self._importer("graph_sitter")
        except (ImportError, ModuleNotFoundError) as exc:
            self._health = BackendHealth(
                backend_id=self.backend_id,
                backend_version="not-installed",
                status=BackendStatus.UNAVAILABLE,
                supported_languages=(),
                semantic_tier="syntax_only",
                toolchain_conditions=(f"python={platform.python_version()}",),
                limitations=(f"graph_sitter is not importable: {exc}",),
            )
            return self._health
        except Exception as exc:  # third-party import boundary
            return self._remember_incompatible(
                "unknown", f"graph_sitter import self-test failed: {exc}"
            )

        version = str(getattr(module, "version", getattr(module, "__version__", "unknown")))
        codebase = getattr(module, "Codebase", None)
        if codebase is None:
            return self._remember_incompatible(version, "graph_sitter.Codebase is missing")
        try:
            parameters = inspect.signature(codebase).parameters
        except Exception as exc:  # third-party signature boundary
            return self._remember_incompatible(version, f"Codebase signature unavailable: {exc}")
        if "repo_path" not in parameters or "language" not in parameters:
            return self._remember_incompatible(
                version, "Codebase API lacks repo_path/language parameters"
            )

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                warnings.simplefilter("ignore", FutureWarning)
                parser_module = self._importer("graph_sitter.tree_sitter_parser")
                if not callable(getattr(parser_module, "parse_file", None)):
                    raise AttributeError("parse_file is missing")
                # Codebase imports this dependency on initialization. Importing
                # it catches installed-but-incompatible py_mini_racer pairs.
                self._importer("graph_sitter.typescript.external.ts_analyzer_engine")
        except Exception as exc:  # third-party self-test boundary
            return self._remember_incompatible(version, f"runtime API self-test failed: {exc}")

        self._health = BackendHealth(
            backend_id=self.backend_id,
            backend_version=version,
            status=BackendStatus.HEALTHY,
            supported_languages=("python", "typescript", "javascript"),
            semantic_tier="syntax_only",
            toolchain_conditions=(
                f"python={platform.python_version()}",
                "graph_sitter Codebase and tree_sitter_parser APIs import cleanly",
            ),
            limitations=(
                "P2 verifies syntax backend reachability only; language semantics require adapters",
                "JavaScript uses graph_sitter's TSX syntax parser and has no resolver claim",
            ),
        )
        return self._health

    def _remember_incompatible(self, version: str, limitation: str) -> BackendHealth:
        self._health = BackendHealth(
            backend_id=self.backend_id,
            backend_version=version,
            status=BackendStatus.INCOMPATIBLE,
            supported_languages=(),
            semantic_tier="syntax_only",
            toolchain_conditions=(f"python={platform.python_version()}",),
            limitations=(limitation,),
        )
        return self._health

    def parse(self, source_unit: SourceUnit) -> SyntaxArtifact | TypedFailure:
        health = self.health()
        if not health.available:
            code = (
                FailureCode.INCOMPATIBLE_API
                if health.status is BackendStatus.INCOMPATIBLE
                else FailureCode.BACKEND_UNAVAILABLE
            )
            return TypedFailure(
                code=code,
                message=health.limitations[0],
                backend_id=self.backend_id,
                language=source_unit.language,
                details=health.limitations,
            )
        source = _read_verified_source(self._root, source_unit, self.backend_id)
        if isinstance(source, TypedFailure):
            return source
        try:
            parser_module = self._importer("graph_sitter.tree_sitter_parser")
            tree = parser_module.parse_file(source_unit.path, source)  # type: ignore[attr-defined]
        except Exception as exc:  # boundary converts third-party failures
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"graph_sitter failed to parse {source_unit.path}: {exc}",
                backend_id=self.backend_id,
                language=source_unit.language,
            )
        return SyntaxArtifact(
            source_unit=source_unit,
            backend_id=self.backend_id,
            backend_version=health.backend_version,
            language=source_unit.language,
            syntax_tree=tree,
            diagnostics=("syntax-only graph_sitter artifact; normalization pending",),
        )


class PythonAstBackend(ParserBackend):
    """Explicitly heuristic Python fallback backed by the standard library AST."""

    backend_id = "python_ast"
    backend_version = platform.python_version()

    def __init__(self, *, root: str | Path | None = None) -> None:
        self._root = None if root is None else Path(root).resolve()

    def health(self, *, refresh: bool = False) -> BackendHealth:
        return BackendHealth(
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            status=BackendStatus.HEALTHY,
            supported_languages=("python",),
            semantic_tier="heuristic",
            toolchain_conditions=(
                f"python={platform.python_version()}",
                "stdlib ast; no external parser toolchain",
            ),
            limitations=(
                "Python only",
                "imports, calls and types are best-effort heuristics",
                "no compiler, framework or incremental semantics",
            ),
        )

    def parse(self, source_unit: SourceUnit) -> SyntaxArtifact | TypedFailure:
        if source_unit.language.lower() != "python":
            return TypedFailure(
                code=FailureCode.UNSUPPORTED_LANGUAGE,
                message="python_ast supports Python only",
                backend_id=self.backend_id,
                language=source_unit.language,
            )
        source = _read_verified_source(self._root, source_unit, self.backend_id)
        if isinstance(source, TypedFailure):
            return source
        try:
            tree = ast.parse(source, filename=source_unit.path)
        except (SyntaxError, ValueError) as exc:
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"Python AST parse failed for {source_unit.path}: {exc}",
                backend_id=self.backend_id,
                language="python",
            )
        return SyntaxArtifact(
            source_unit=source_unit,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            language="python",
            syntax_tree=tree,
            diagnostics=("heuristic Python AST fallback",),
        )


def _read_verified_source(
    root: Path | None, source_unit: SourceUnit, backend_id: str
) -> str | TypedFailure:
    if root is None:
        return TypedFailure(
            code=FailureCode.INVALID_INPUT,
            message="backend parse requires a repository root",
            backend_id=backend_id,
            language=source_unit.language,
        )
    path = (root / source_unit.path).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return TypedFailure(
            code=FailureCode.INVALID_INPUT,
            message=f"source unit escapes repository root: {source_unit.path}",
            backend_id=backend_id,
            language=source_unit.language,
        )
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return TypedFailure(
            code=FailureCode.SOURCE_UNAVAILABLE,
            message=f"cannot read {source_unit.path}: {exc}",
            backend_id=backend_id,
            language=source_unit.language,
        )
    actual = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if actual != source_unit.content_hash:
        return TypedFailure(
            code=FailureCode.CONTENT_HASH_MISMATCH,
            message=f"content hash mismatch for {source_unit.path}",
            backend_id=backend_id,
            language=source_unit.language,
            details=(f"expected={source_unit.content_hash}", f"actual={actual}"),
        )
    return source
