"""Strongly validated values for the probe-compatible semantic ledger."""

from __future__ import annotations

import re
import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.ir import normalize_relative_path


LEDGER_SCHEMA = "cbe-semantic-ledger/3"
LEGACY_LEDGER_SCHEMA = "cbe-semantic-ledger-2"
EDGE_PROTOCOL_IDS = {
    "inbound": "cbe-inbound-call/1",
    "ir": "cbe-ir/3",
    "reverse": "cbe-reverse-edges/3",
}
EDGE_PROTOCOL_SHA256 = (
    "sha256:4402da6860671678a4cf23efb05249236e265cd85427e78e90c4c638e65e7a42"
)
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
    cited_relation_ids: tuple[str, ...] = ()
    producer_session_id: str
    provenance: Literal["canonical_producer", "legacy_revalidated"] = "canonical_producer"
    legacy_fact_sha256: str | None = None
    created_at: datetime

    def __init__(self, **data: Any) -> None:
        # ``producer`` was the pre-v3 public spelling.  Accept it only at the
        # compatibility boundary and persist the single v3 identity field.
        if "producer" in data:
            if "producer_session_id" not in data:
                data["producer_session_id"] = data["producer"]
            data.pop("producer")
        super().__init__(**data)

    @property
    def producer(self) -> str:
        """Compatibility alias; the durable model has one producer identity."""

        return self.producer_session_id

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

    @field_validator("cited_symbol_ids", "cited_relation_ids")
    @classmethod
    def _unique_citations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError("cited_symbol_ids must contain non-empty strings")
        if len(set(value)) != len(value):
            raise ValueError("cited_symbol_ids must be unique")
        return value

    @field_validator("producer_session_id")
    @classmethod
    def _producer_session(cls, value: str) -> str:
        return _required_text(value, "producer_session_id")

    @field_validator("legacy_fact_sha256")
    @classmethod
    def _legacy_hash(cls, value: str | None) -> str | None:
        return None if value is None else _content_hash(value, "legacy_fact_sha256")

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


# ---------------------------------------------------------------------------
# v3 lifecycle envelopes.  These are declared after the legacy probe models
# so existing structural callers keep their symbol record types while the
# durable ledger itself has one strict schema.


def canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", round_trip=True, warnings="error")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def hash_json(value: object) -> str:
    return hash_bytes(canonical_json_bytes(value))


def _v3_source_revision(value: str) -> str:
    raw = _required_text(value, "source_revision")
    if raw.startswith("rev_"):
        if not re.fullmatch(r"rev_[0-9a-f]{64}", raw):
            raise ValueError("source_revision must be rev_ plus 64 lowercase hex chars")
        return raw
    if _SHA256_RE.fullmatch(raw):
        return "rev_" + raw.removeprefix("sha256:")
    return "rev_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SemanticBindingsV3(SemanticModel):
    source_revision_id: str
    source_revision_digest_sha256: str
    file_revisions: dict[str, str]
    symbol_inventory_sha256: str
    semantic_schema_sha256: str
    edge_protocol_ids: dict[str, str]
    edge_protocol_sha256: str
    edge_snapshot_sha256: str
    edge_relation_count: int = Field(ge=0)

    @field_validator("source_revision_id")
    @classmethod
    def _source(cls, value: str) -> str:
        return _v3_source_revision(value)

    @field_validator(
        "source_revision_digest_sha256",
        "symbol_inventory_sha256",
        "semantic_schema_sha256",
        "edge_protocol_sha256",
        "edge_snapshot_sha256",
    )
    @classmethod
    def _hash(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))

    @field_validator("file_revisions")
    @classmethod
    def _file_revisions(cls, value: dict[str, str]) -> dict[str, str]:
        for path, digest in value.items():
            if _relative_posix_path(path) != path:
                raise ValueError("file_revisions keys must be canonical relative POSIX paths")
            _content_hash(digest, f"file_revisions[{path}]")
        return dict(sorted(value.items()))

    @field_validator("edge_protocol_ids")
    @classmethod
    def _edge_ids(cls, value: dict[str, str]) -> dict[str, str]:
        if value != EDGE_PROTOCOL_IDS:
            raise ValueError("edge_protocol_ids do not match the frozen T2 protocols")
        return dict(value)

    @field_validator("edge_protocol_sha256")
    @classmethod
    def _edge_protocol_hash(cls, value: str) -> str:
        if value != EDGE_PROTOCOL_SHA256:
            raise ValueError("edge_protocol_sha256 does not match the frozen T2 design")
        return value


class SubmissionCommitV3(SemanticModel):
    batch_id: str
    claim_generation_id: str
    claim_revision: int = Field(ge=0)
    committed_revision: int = Field(gt=0)
    source_revision_id: str
    edge_snapshot_sha256: str
    packet_sha256: str
    producer_session_id: str
    explanation_symbol_ids: tuple[str, ...] = ()
    residual_symbol_ids: tuple[str, ...] = ()
    producer_runner_kind: Literal["codex", "claude", "generic"] = "generic"
    producer_events_path: str
    producer_events_sha256: str
    committed_at: datetime

    @field_validator("claim_generation_id")
    @classmethod
    def _generation(cls, value: str) -> str:
        if not re.fullmatch(r"claimgen_[0-9a-f]{64}", value):
            raise ValueError("claim_generation_id is malformed")
        return value

    @field_validator("source_revision_id")
    @classmethod
    def _source(cls, value: str) -> str:
        return _v3_source_revision(value)

    @field_validator("edge_snapshot_sha256", "packet_sha256", "producer_events_sha256")
    @classmethod
    def _hashes(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))

    @field_validator("batch_id", "producer_session_id", "producer_events_path")
    @classmethod
    def _text(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))


class ReviewStateV3(SemanticModel):
    status: Literal["none", "pending", "accepted", "revision_required"] = "none"
    review_batch_id: str | None = None
    bound_ledger_revision: int | None = None
    bound_subject_sha256: str | None = None
    packet_sha256: str | None = None
    hidden_map_sha256: str | None = None
    reviewer_session_id: str | None = None
    producer_session_ids_sha256: str | None = None
    verdict_sha256: str | None = None
    reviewer_runner_kind: Literal["codex", "claude", "generic"] | None = None
    reviewer_events_path: str | None = None
    reviewer_events_sha256: str | None = None
    docs_fingerprint: str | None = None
    revision_symbol_ids: tuple[str, ...] = ()
    committed_at: datetime | None = None

    @field_validator(
        "bound_subject_sha256",
        "packet_sha256",
        "hidden_map_sha256",
        "producer_session_ids_sha256",
        "verdict_sha256",
        "reviewer_events_sha256",
        "docs_fingerprint",
    )
    @classmethod
    def _hashes(cls, value: str | None, info: object) -> str | None:
        return None if value is None else _content_hash(value, getattr(info, "field_name", "hash"))

    @model_validator(mode="after")
    def _none_shape(self) -> Self:
        if self.status == "none" and (
            self.review_batch_id is not None
            or self.bound_ledger_revision is not None
            or self.bound_subject_sha256 is not None
            or self.packet_sha256 is not None
            or self.hidden_map_sha256 is not None
            or self.reviewer_session_id is not None
            or self.producer_session_ids_sha256 is not None
            or self.verdict_sha256 is not None
            or self.reviewer_runner_kind is not None
            or self.reviewer_events_path is not None
            or self.reviewer_events_sha256 is not None
            or self.docs_fingerprint is not None
            or self.revision_symbol_ids
            or self.committed_at is not None
        ):
            raise ValueError("review status none must not carry terminal fields")
        return self


class LegacyFileResultV3(SemanticModel):
    path: str
    sha256: str
    parse_status: Literal["valid", "invalid_json", "invalid_schema"]
    row_count: int = Field(ge=0)
    imported_symbol_ids: tuple[str, ...] = ()
    duplicate_symbol_ids: tuple[str, ...] = ()
    rejected_symbol_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    @field_validator("sha256")
    @classmethod
    def _hash(cls, value: str) -> str:
        return _content_hash(value, "sha256")


class LegacyImportStateV3(SemanticModel):
    status: Literal["open", "closed"] = "open"
    scan_root: str
    scanned_at: datetime | None = None
    source_paths: tuple[str, ...] = ()
    source_sha256: dict[str, str] = Field(default_factory=dict)
    file_results: dict[str, LegacyFileResultV3] = Field(default_factory=dict)
    imported_symbol_ids: tuple[str, ...] = ()
    duplicate_symbol_ids: tuple[str, ...] = ()
    rejected_symbol_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    imported_count: int = Field(default=0, ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)
    invalid_file_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    migration_receipt_sha256: str | None = None

    @field_validator("scan_root")
    @classmethod
    def _root(cls, value: str) -> str:
        root = Path(_required_text(value, "scan_root"))
        if not root.is_absolute():
            raise ValueError("scan_root must be absolute")
        return root.resolve().as_posix()

    @field_validator("source_sha256")
    @classmethod
    def _source_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        for path, digest in value.items():
            _relative_posix_path(path)
            _content_hash(digest, f"source_sha256[{path}]")
        return dict(sorted(value.items()))

    @field_validator("migration_receipt_sha256")
    @classmethod
    def _receipt_hash(cls, value: str | None) -> str | None:
        return None if value is None else _content_hash(value, "migration_receipt_sha256")


class ArtifactStateV1(SemanticModel):
    path: str
    kind: Literal["missing", "file", "directory_tree"]
    sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return _relative_posix_path(value)

    @field_validator("sha256")
    @classmethod
    def _hash(cls, value: str | None) -> str | None:
        return None if value is None else _content_hash(value, "sha256")

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.kind == "missing" and (self.sha256 is not None or self.size_bytes is not None):
            raise ValueError("missing artifact must have null hash and size")
        if self.kind != "missing" and (self.sha256 is None or self.size_bytes is None):
            raise ValueError("present artifact must have hash and size")
        return self


class ArtifactManifestV1(SemanticModel):
    schema_id: Literal["cbe-semantic-artifact-manifest/1"] = Field(
        default="cbe-semantic-artifact-manifest/1", alias="schema", serialization_alias="schema"
    )
    entries: tuple[ArtifactStateV1, ...] = ()

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        paths = tuple(item.path for item in self.entries)
        if paths != tuple(sorted(set(paths))):
            raise ValueError("artifact manifest entries must be sorted and unique")
        return self


class CommitReceiptV1(SemanticModel):
    schema_id: Literal["cbe-semantic-commit-receipt/1"] = Field(
        default="cbe-semantic-commit-receipt/1", alias="schema", serialization_alias="schema"
    )
    transaction_id: str
    ledger_revision: int = Field(ge=0)
    ledger_sha256: str
    source_revision_id: str
    semantic_schema: Literal["cbe-semantic-ledger/3"] = LEDGER_SCHEMA
    semantic_schema_sha256: str
    edge_snapshot_sha256: str
    artifact_manifest: ArtifactManifestV1
    artifact_manifest_sha256: str
    prior_commit_receipt_sha256: str | None = None
    committed_at: datetime

    @field_validator("ledger_sha256", "semantic_schema_sha256", "edge_snapshot_sha256", "artifact_manifest_sha256")
    @classmethod
    def _hash(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))

    @field_validator("source_revision_id")
    @classmethod
    def _source(cls, value: str) -> str:
        return _v3_source_revision(value)


class TransactionJournalV2(SemanticModel):
    schema_id: Literal["cbe-semantic-transaction-journal/2"] = Field(
        default="cbe-semantic-transaction-journal/2", alias="schema", serialization_alias="schema"
    )
    state: Literal["prepared"] = "prepared"
    transaction_id: str
    expected_ledger_revision: int | None = Field(default=None, ge=0)
    candidate_ledger_revision: int = Field(ge=0)
    before_manifest: ArtifactManifestV1
    before_manifest_sha256: str
    after_manifest: ArtifactManifestV1
    after_manifest_sha256: str
    before_commit_receipt_sha256: str | None = None
    after_commit_receipt_sha256: str
    backup_dir: Literal[".codebase-analysis/semantic_transaction_backup"] = ".codebase-analysis/semantic_transaction_backup"
    created_at: datetime

    @field_validator("before_manifest_sha256", "after_manifest_sha256", "after_commit_receipt_sha256")
    @classmethod
    def _hash(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))


class SubmissionDispatchReservationV1(SemanticModel):
    schema_id: Literal["cbe-semantic-submission-dispatch/1"] = Field(
        default="cbe-semantic-submission-dispatch/1", alias="schema", serialization_alias="schema"
    )
    dispatch_kind: Literal["submission"] = "submission"
    dispatch_id: str
    dispatch_id_sha256: str
    claim_generation_id: str
    lease_owner: str
    bound_ledger_revision: int = Field(ge=0)
    source_revision_id: str
    edge_snapshot_sha256: str
    reservation_token: str
    dispatch_generation_id: str
    owner_pid: int = Field(ge=1)
    liveness_lock_path: str
    liveness_lock_payload_sha256: str
    reserved_at: datetime
    reservation_payload_sha256: str

    @field_validator("dispatch_id", "lease_owner", "liveness_lock_path")
    @classmethod
    def _text(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))

    @field_validator("dispatch_id_sha256", "edge_snapshot_sha256", "liveness_lock_payload_sha256", "reservation_payload_sha256")
    @classmethod
    def _hash(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))

    @field_validator("source_revision_id")
    @classmethod
    def _source(cls, value: str) -> str:
        return _v3_source_revision(value)

    @field_validator("claim_generation_id")
    @classmethod
    def _claim_generation(cls, value: str) -> str:
        if not re.fullmatch(r"claimgen_[0-9a-f]{64}", value):
            raise ValueError("claim_generation_id is malformed")
        return value

    @field_validator("reservation_token")
    @classmethod
    def _token(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("reservation_token is malformed")
        return value

    @field_validator("dispatch_generation_id")
    @classmethod
    def _dispatch_generation(cls, value: str) -> str:
        if not re.fullmatch(r"dispatchgen_[0-9a-f]{64}", value):
            raise ValueError("dispatch_generation_id is malformed")
        return value


class ReviewDispatchReservationV1(SemanticModel):
    schema_id: Literal["cbe-semantic-review-dispatch/1"] = Field(
        default="cbe-semantic-review-dispatch/1", alias="schema", serialization_alias="schema"
    )
    dispatch_kind: Literal["review"] = "review"
    dispatch_id: str
    dispatch_id_sha256: str
    bound_ledger_revision: int = Field(ge=0)
    bound_subject_sha256: str
    reservation_token: str
    dispatch_generation_id: str
    owner_pid: int = Field(ge=1)
    liveness_lock_path: str
    liveness_lock_payload_sha256: str
    reserved_at: datetime
    reservation_payload_sha256: str

    @field_validator("dispatch_id", "liveness_lock_path")
    @classmethod
    def _text(cls, value: str, info: object) -> str:
        return _required_text(value, getattr(info, "field_name", "value"))

    @field_validator("dispatch_id_sha256", "bound_subject_sha256", "liveness_lock_payload_sha256", "reservation_payload_sha256")
    @classmethod
    def _hash(cls, value: str, info: object) -> str:
        return _content_hash(value, getattr(info, "field_name", "hash"))

    @field_validator("reservation_token")
    @classmethod
    def _token(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("reservation_token is malformed")
        return value

    @field_validator("dispatch_generation_id")
    @classmethod
    def _dispatch_generation(cls, value: str) -> str:
        if not re.fullmatch(r"dispatchgen_[0-9a-f]{64}", value):
            raise ValueError("dispatch_generation_id is malformed")
        return value


class DispatchLivenessLockV1(SemanticModel):
    schema_id: Literal["cbe-semantic-dispatch-liveness/1"] = Field(
        default="cbe-semantic-dispatch-liveness/1", alias="schema", serialization_alias="schema"
    )
    dispatch_id: str
    reservation_token: str
    dispatch_generation_id: str

    @field_validator("dispatch_id")
    @classmethod
    def _dispatch(cls, value: str) -> str:
        return _required_text(value, "dispatch_id")

    @field_validator("reservation_token")
    @classmethod
    def _token(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("reservation_token is malformed")
        return value

    @field_validator("dispatch_generation_id")
    @classmethod
    def _dispatch_generation(cls, value: str) -> str:
        if not re.fullmatch(r"dispatchgen_[0-9a-f]{64}", value):
            raise ValueError("dispatch_generation_id is malformed")
        return value


class DispatchReservationHandleV1(SemanticModel):
    dispatch_kind: Literal["submission", "review"]
    path: str
    dispatch_id: str
    reservation_token: str
    dispatch_generation_id: str
    reservation_payload_sha256: str

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return _relative_posix_path(value)

    @field_validator("dispatch_id")
    @classmethod
    def _dispatch(cls, value: str) -> str:
        return _required_text(value, "dispatch_id")

    @field_validator("reservation_token")
    @classmethod
    def _token(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("reservation_token is malformed")
        return value

    @field_validator("dispatch_generation_id")
    @classmethod
    def _dispatch_generation(cls, value: str) -> str:
        if not re.fullmatch(r"dispatchgen_[0-9a-f]{64}", value):
            raise ValueError("dispatch_generation_id is malformed")
        return value

    @field_validator("reservation_payload_sha256")
    @classmethod
    def _payload_hash(cls, value: str) -> str:
        return _content_hash(value, "reservation_payload_sha256")


def _default_bindings(source_revision: str, file_revisions: dict[str, str], symbols: dict[str, Any]) -> SemanticBindingsV3:
    source = _v3_source_revision(source_revision)
    normalized_files = {
        path: digest if isinstance(digest, str) and _SHA256_RE.fullmatch(digest)
        else hash_bytes(str(digest).encode("utf-8"))
        for path, digest in sorted(file_revisions.items())
    }
    symbol_rows = []
    for symbol_id, symbol in sorted(symbols.items()):
        content_hash = symbol.content_hash if hasattr(symbol, "content_hash") else symbol.get("content_hash", "")
        symbol_rows.append([symbol_id, content_hash])
    return SemanticBindingsV3(
        source_revision_id=source,
        source_revision_digest_sha256="sha256:" + source.removeprefix("rev_"),
        file_revisions=normalized_files,
        symbol_inventory_sha256=hash_json(symbol_rows),
        semantic_schema_sha256=hash_json({"schema": LEDGER_SCHEMA}),
        edge_protocol_ids=dict(EDGE_PROTOCOL_IDS),
        edge_protocol_sha256=EDGE_PROTOCOL_SHA256,
        edge_snapshot_sha256=hash_json([]),
        edge_relation_count=0,
    )


class SemanticLedgerV3(SemanticModel):
    schema_id: Literal["cbe-semantic-ledger/3"] = Field(
        default=LEDGER_SCHEMA, alias="schema", serialization_alias="schema"
    )
    ledger_revision: int = Field(default=0, ge=0)
    repo_root: str
    bindings: SemanticBindingsV3
    excluded_globs: tuple[str, ...] = ()
    files: dict[str, SemanticFileRecord]
    symbols: dict[str, SemanticSymbolRecord]
    order: tuple[str, ...] = ()
    residuals: tuple[SemanticResidual, ...] = ()
    accepted_submissions: dict[str, SubmissionCommitV3] = Field(default_factory=dict)
    review: ReviewStateV3 = Field(default_factory=ReviewStateV3)
    legacy_import: LegacyImportStateV3
    totals: SemanticTotals
    coverage_percent: float = Field(ge=0.0, le=100.0)
    uncovered_symbols: tuple[str, ...] = ()

    def __init__(self, **data: Any) -> None:
        if "bindings" not in data and "source_revision" in data:
            source = data.pop("source_revision")
            files = data.get("files", {})
            symbols = data.get("symbols", {})
            file_revisions = data.pop("file_revisions", None) or {
                path: hash_bytes(b"") for path in files
            }
            data["bindings"] = _default_bindings(source, file_revisions, symbols)
        if "legacy_import" not in data:
            root = data.get("repo_root", "/")
            data["legacy_import"] = {
                "status": "open",
                "scan_root": (Path(root) / ".codebase-analysis/legacy-l1").as_posix(),
            }
        super().__init__(**data)

    @property
    def schema(self) -> str:
        return self.schema_id

    @property
    def source_revision(self) -> str:
        return self.bindings.source_revision_id

    @property
    def file_revisions(self) -> dict[str, str]:
        return self.bindings.file_revisions

    @property
    def product_complete(self) -> bool:
        return bool(
            self.totals.symbols == self.totals.explained
            and self.totals.uncovered == 0
            and self.totals.stale == 0
            and not self.uncovered_symbols
            and not self.residuals
            and self.review.status == "accepted"
            and self.review.bound_ledger_revision == self.ledger_revision - 1
            and self.legacy_import.status == "closed"
        )

    @property
    def complete(self) -> bool:
        return self.product_complete

    @field_validator("repo_root")
    @classmethod
    def _root(cls, value: str) -> str:
        root = Path(_required_text(value, "repo_root"))
        if not root.is_absolute():
            raise ValueError("repo_root must be absolute")
        return root.resolve().as_posix()

    @model_validator(mode="after")
    def _derived(self) -> Self:
        if set(self.bindings.file_revisions) != set(self.files):
            raise ValueError("bindings.file_revisions must cover exactly the enumerated files")
        if any(_relative_posix_path(path) != path for path in self.files):
            raise ValueError("files keys must be canonical relative POSIX paths")
        if any(symbol.path not in self.files for symbol in self.symbols.values()):
            raise ValueError("every symbol path must exist in files")
        for symbol_id, symbol in self.symbols.items():
            if symbol_id != symbol.symbol_id:
                raise ValueError(f"symbol key does not match path and qualified name: {symbol_id}")
            explanation = symbol.explanation
            if explanation is not None and any(
                cited not in self.symbols for cited in explanation.cited_symbol_ids
            ):
                raise ValueError(f"symbol {symbol_id} has a dangling cited_symbol_id")
            if any(peer not in self.symbols for peer in symbol.cycle_peer_ids):
                raise ValueError(f"symbol {symbol_id} has a dangling cycle peer")
        fresh = {symbol_id for symbol_id, symbol in self.symbols.items() if symbol.is_fresh}
        explained = {symbol_id for symbol_id, symbol in self.symbols.items() if symbol.is_explained}
        stale = explained - fresh
        uncovered = set(self.symbols) - fresh
        if self.uncovered_symbols != tuple(sorted(uncovered)):
            raise ValueError("uncovered_symbols must be the sorted derived uncovered set")
        residual_ids = [item.symbol_id for item in self.residuals]
        if len(set(residual_ids)) != len(residual_ids) or set(residual_ids) != uncovered:
            raise ValueError("residuals must account for every and only uncovered symbol")
        if len(set(self.order)) != len(self.order) or any(item not in fresh for item in self.order):
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
        expected_coverage = round(100.0 * len(fresh) / len(self.symbols), 4) if self.symbols else 0.0
        if abs(self.coverage_percent - expected_coverage) >= 0.00005:
            raise ValueError("coverage_percent must equal the ledger-derived projection")
        return self


# Public names consumed by the existing semantic modules now point to v3.
SemanticBindings = SemanticBindingsV3
SubmissionCommit = SubmissionCommitV3
ReviewState = ReviewStateV3
LegacyFileResult = LegacyFileResultV3
LegacyImportState = LegacyImportStateV3
SemanticLedger = SemanticLedgerV3


def legacy_schema_payload(raw: object) -> bool:
    return isinstance(raw, dict) and raw.get("schema") == LEGACY_LEDGER_SCHEMA
