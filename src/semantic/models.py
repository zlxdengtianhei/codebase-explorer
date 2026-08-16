"""Strongly validated values for the probe-compatible semantic ledger."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.ir import normalize_relative_path


LEDGER_SCHEMA = "cbe-semantic-ledger-2"
MIN_EXPLANATION_CHARS = 25
PENDING_EXPLANATION_REASON = "pending semantic explanation"

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class FileStatus(StrEnum):
    COVERED = "covered"
    NO_SYMBOLS = "no_symbols"
    RESIDUAL = "residual"


class SemanticSymbolKind(StrEnum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _content_hash(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name).strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a sha256:-prefixed lowercase digest")
    return normalized


def _relative_posix_path(value: str) -> str:
    raw = _required_text(value, "path")
    if "\\" in raw or raw.startswith("/"):
        raise ValueError("path must be a relative POSIX path")
    normalized = normalize_relative_path(raw)
    if normalized != raw:
        raise ValueError("path must already be canonical")
    return normalized


class SemanticModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        validate_default=True,
    )


class SemanticExplanation(SemanticModel):
    text: str
    explained_content_hash: str
    cited_symbol_ids: tuple[str, ...] = ()
    producer: str
    created_at: datetime

    @field_validator("text")
    @classmethod
    def _informative_text(cls, value: str) -> str:
        if len(_required_text(value, "text").strip()) < MIN_EXPLANATION_CHARS:
            raise ValueError(
                f"text must contain at least {MIN_EXPLANATION_CHARS} non-padding characters"
            )
        return value

    @field_validator("explained_content_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return _content_hash(value, "explained_content_hash")

    @field_validator("cited_symbol_ids")
    @classmethod
    def _unique_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("cited_symbol_ids must contain non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("cited_symbol_ids must be unique")
        return value

    @field_validator("producer")
    @classmethod
    def _producer(cls, value: str) -> str:
        return _required_text(value, "producer")

    @field_validator("created_at")
    @classmethod
    def _utc_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must use UTC")
        return value.astimezone(UTC)


class SemanticFileRecord(SemanticModel):
    status: FileStatus
    reason: str = ""

    @model_validator(mode="after")
    def _residual_reason(self) -> Self:
        if self.status is FileStatus.RESIDUAL and not self.reason.strip():
            raise ValueError("residual file status requires a reason")
        return self


class SemanticSymbolRecord(SemanticModel):
    path: str
    qualified_name: str
    kind: SemanticSymbolKind
    span: tuple[int, int]
    content_hash: str
    explanation: SemanticExplanation | None = None
    ir_symbol_id: str | None = None
    module_id: str | None = None
    scc_id: str | None = None
    cycle_peer_ids: tuple[str, ...] = ()
    invalidation_reason: str | None = None
    runtime_covered_lines: int | None = Field(default=None, ge=0)

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return _relative_posix_path(value)

    @field_validator("qualified_name")
    @classmethod
    def _qualified_name(cls, value: str) -> str:
        name = _required_text(value, "qualified_name")
        if "::" in name or any(not part for part in name.split(".")):
            raise ValueError("qualified_name must be a dot-separated lexical name")
        return name

    @field_validator("span", mode="before")
    @classmethod
    def _span_shape(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("span must contain exactly start and end lines")
        if any(type(item) is not int for item in value):
            raise ValueError("span lines must be integers")
        return value

    @field_validator("span")
    @classmethod
    def _ordered_span(cls, value: tuple[int, int]) -> tuple[int, int]:
        if value[0] < 1 or value[1] < value[0]:
            raise ValueError("span must be a positive inclusive line range")
        return value

    @field_validator("content_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        return _content_hash(value, "content_hash")

    @field_validator("ir_symbol_id", "module_id", "scc_id", "invalidation_reason")
    @classmethod
    def _optional_text(cls, value: str | None, info: object) -> str | None:
        if value is None:
            return None
        field_name = getattr(info, "field_name", "value")
        return _required_text(value, field_name)

    @field_validator("cycle_peer_ids")
    @classmethod
    def _unique_cycle_peers(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("cycle_peer_ids must be unique")
        return value

    @property
    def symbol_id(self) -> str:
        return semantic_symbol_id(self.path, self.qualified_name)

    @property
    def is_explained(self) -> bool:
        return self.explanation is not None and bool(self.explanation.text.strip())

    @property
    def is_fresh(self) -> bool:
        return (
            self.is_explained
            and self.explanation is not None
            and self.explanation.explained_content_hash == self.content_hash
            and self.invalidation_reason is None
        )


class SemanticResidual(SemanticModel):
    symbol_id: str
    reason: str

    @field_validator("symbol_id", "reason")
    @classmethod
    def _required(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))


class SemanticTotals(SemanticModel):
    symbols: int = Field(ge=0)
    explained: int = Field(ge=0)
    stale: int = Field(ge=0)
    uncovered: int = Field(ge=0)
    residual: int = Field(ge=0)


class SemanticLedger(SemanticModel):
    schema_id: Literal["cbe-semantic-ledger-2"] = Field(
        default=LEDGER_SCHEMA,
        alias="schema",
        serialization_alias="schema",
    )
    repo_root: str
    source_revision: str
    #: per-file 指纹：`path -> sha256:<全文摘要>`。增量的前置条件 P0（F1 §2.3）。
    #: `source_revision` 自此降级为**派生的展示字段**，不再作为图投影保留与否的判据——
    #: 它是仓库级的，改任意一个文件就全变，于是全仓投影被清零、全图 condensation 与
    #: 全仓 PageRank 重算。默认空 dict 是为了让本字段出现之前写下的台账仍能加载；
    #: 空即回退到旧的仓库级判据，非空则按文件逐个判（`inventory.reconcile_semantic_ledger`）。
    file_revisions: dict[str, str] = Field(default_factory=dict)
    excluded_globs: tuple[str, ...] = ()
    files: dict[str, SemanticFileRecord]
    symbols: dict[str, SemanticSymbolRecord]
    order: tuple[str, ...] = ()
    residuals: tuple[SemanticResidual, ...] = ()
    totals: SemanticTotals
    coverage_percent: float = Field(ge=0.0, le=100.0)
    uncovered_symbols: tuple[str, ...] = ()

    @property
    def schema(self) -> str:
        """Expose the probe field name without shadowing BaseModel at definition time."""

        return self.schema_id

    @field_validator("repo_root")
    @classmethod
    def _absolute_root(cls, value: str) -> str:
        root = Path(_required_text(value, "repo_root"))
        if not root.is_absolute():
            raise ValueError("repo_root must be absolute")
        return root.resolve().as_posix()

    @field_validator("source_revision")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _content_hash(value, "source_revision")

    @field_validator("file_revisions")
    @classmethod
    def _file_revisions(cls, value: dict[str, str]) -> dict[str, str]:
        for path, digest in value.items():
            if _relative_posix_path(path) != path:
                raise ValueError("file_revisions keys must be canonical relative POSIX paths")
            _content_hash(digest, f"file_revisions[{path}]")
        return dict(sorted(value.items()))

    @field_validator("excluded_globs")
    @classmethod
    def _unique_exclusions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("excluded_globs must contain non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("excluded_globs must be unique")
        return value

    @model_validator(mode="after")
    def _derived_projection_is_exact(self) -> Self:
        if any(_relative_posix_path(path) != path for path in self.files):
            raise ValueError("files keys must be canonical relative POSIX paths")
        if self.file_revisions and set(self.file_revisions) != set(self.files):
            raise ValueError("file_revisions must cover exactly the enumerated files")
        if any(symbol.path not in self.files for symbol in self.symbols.values()):
            raise ValueError("every symbol path must exist in files")
        for symbol_id, symbol in self.symbols.items():
            if symbol_id != symbol.symbol_id:
                raise ValueError(f"symbol key does not match path and qualified name: {symbol_id}")
            if any(cited not in self.symbols for cited in (symbol.explanation.cited_symbol_ids if symbol.explanation else ())):
                raise ValueError(f"symbol {symbol_id} has a dangling cited_symbol_id")
            if any(peer not in self.symbols for peer in symbol.cycle_peer_ids):
                raise ValueError(f"symbol {symbol_id} has a dangling cycle peer")

        fresh = {symbol_id for symbol_id, symbol in self.symbols.items() if symbol.is_fresh}
        explained = {symbol_id for symbol_id, symbol in self.symbols.items() if symbol.is_explained}
        stale = explained - fresh
        uncovered = set(self.symbols) - fresh
        expected_uncovered = tuple(sorted(uncovered))
        if self.uncovered_symbols != expected_uncovered:
            raise ValueError("uncovered_symbols must be the sorted derived uncovered set")

        residual_ids = [item.symbol_id for item in self.residuals]
        if len(set(residual_ids)) != len(residual_ids):
            raise ValueError("residual symbol ids must be unique")
        if set(residual_ids) != uncovered:
            raise ValueError("residuals must account for every and only uncovered symbol")

        if len(set(self.order)) != len(self.order):
            raise ValueError("order must not contain duplicate symbol ids")
        if any(symbol_id not in fresh for symbol_id in self.order):
            raise ValueError("order may contain only current fresh symbols")

        by_path: dict[str, list[SemanticSymbolRecord]] = {path: [] for path in self.files}
        for symbol in self.symbols.values():
            by_path[symbol.path].append(symbol)
        for path, record in self.files.items():
            path_symbols = by_path[path]
            if record.status is FileStatus.NO_SYMBOLS and path_symbols:
                raise ValueError(f"no_symbols file contains symbols: {path}")
            if record.status is FileStatus.COVERED and (
                not path_symbols or any(not symbol.is_fresh for symbol in path_symbols)
            ):
                raise ValueError(f"covered file is not fully fresh: {path}")

        expected_totals = SemanticTotals(
            symbols=len(self.symbols),
            explained=len(fresh),
            stale=len(stale),
            uncovered=len(uncovered),
            residual=len(self.residuals),
        )
        if self.totals != expected_totals:
            raise ValueError("totals must equal the ledger-derived projection")
        expected_coverage = (
            round(100.0 * len(fresh) / len(self.symbols), 4) if self.symbols else 0.0
        )
        if abs(self.coverage_percent - expected_coverage) >= 0.00005:
            raise ValueError("coverage_percent must equal the ledger-derived projection")
        return self


def semantic_symbol_id(path: str, qualified_name: str) -> str:
    """Return the immutable probe identity for one lexical Python symbol."""

    canonical_path = _relative_posix_path(path)
    name = _required_text(qualified_name, "qualified_name")
    if "::" in name or any(not part for part in name.split(".")):
        raise ValueError("qualified_name must be a dot-separated lexical name")
    return f"{canonical_path}::{name}"


def derived_totals(symbols: dict[str, SemanticSymbolRecord], residual_count: int) -> SemanticTotals:
    """Recompute the five probe totals from canonical symbol records."""

    fresh = sum(symbol.is_fresh for symbol in symbols.values())
    stale = sum(symbol.is_explained and not symbol.is_fresh for symbol in symbols.values())
    return SemanticTotals(
        symbols=len(symbols),
        explained=fresh,
        stale=stale,
        uncovered=len(symbols) - fresh,
        residual=residual_count,
    )


def revalidate_semantic_ledger(ledger: SemanticLedger) -> SemanticLedger:
    """Rebuild from JSON-native values so copied model updates are validated."""

    return SemanticLedger.model_validate(
        ledger.model_dump(mode="json", round_trip=True, warnings="error")
    )
