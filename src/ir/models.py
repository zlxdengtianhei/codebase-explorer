"""Immutable canonical values for the ``cbe-ir/2`` protocol."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterator
from enum import Enum, StrEnum
from typing import Any, Mapping, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_ENTITY_ID_RE = re.compile(r"^ir_[0-9a-f]{64}$")
_REVISION_ID_RE = re.compile(r"^rev_[0-9a-f]{64}$")
# V2 changes target presence, not the four identity inputs, so the identity
# framing domain intentionally remains stable across the transport migration.
_ENTITY_ID_DOMAIN = b"cbe-ir/1:entity-id\x00"

class FrozenDict(Mapping[Any, Any]):
    """A structurally immutable mapping with no mutable base-class storage."""

    __slots__ = ("_items",)

    def __init__(self, value: Mapping[Any, Any]) -> None:
        object.__setattr__(self, "_items", tuple(value.items()))

    def __getitem__(self, key: Any) -> Any:
        for candidate, value in self._items:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[Any]:
        return (key for key, _value in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise TypeError("canonical IR mappings are immutable")

    def __setitem__(self, _key: Any, _value: Any) -> None:
        raise TypeError("canonical IR mappings are immutable")

    def __delitem__(self, _key: Any) -> None:
        raise TypeError("canonical IR mappings are immutable")


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"


class SemanticTier(StrEnum):
    SYNTAX_ONLY = "syntax_only"
    HEURISTIC = "heuristic"
    RESOLVED = "resolved"
    SPECIALIZED = "specialized"


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    FAILED = "failed"
    CANNOT_JUDGE = "cannot_judge"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    EXTERNAL = "external"
    UNSUPPORTED = "unsupported"


class ResolutionMethod(StrEnum):
    EXACT = "exact"
    HEURISTIC = "heuristic"
    COMPILER = "compiler"
    DATAFLOW = "dataflow"
    SEARCH_FALLBACK = "search_fallback"


class SourceUnitState(StrEnum):
    DISCOVERED = "discovered"
    EXCLUDED = "excluded"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    PARSE_ERROR = "parse_error"
    INDEXED = "indexed"


class SemanticTaskState(StrEnum):
    PENDING = "pending"
    LEASED = "leased"
    ARTIFACT_STAGED = "artifact_staged"
    VERIFICATION_PENDING = "verification_pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    RESIDUAL = "residual"
    STALE = "stale"


class RunTerminalState(StrEnum):
    VERIFIED_FULL = "verified_full"
    VERIFIED_WITH_RESIDUALS = "verified_with_residuals"
    FAILED = "failed"


class VerifierVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CANNOT_JUDGE = "cannot_judge"


class EntityKind(StrEnum):
    SOURCE_UNIT = "source_unit"
    SYMBOL = "symbol"
    RELATION = "relation"
    SEMANTIC_MODULE = "semantic_module"


def _non_empty(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    return value


def _sha256(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 hex digest")
    return normalized


def _git_commit(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not _GIT_COMMIT_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a full 40- or 64-hex Git commit id")
    return normalized


def _entity_id(value: str, field_name: str) -> str:
    normalized = _non_empty(value, field_name)
    if not _ENTITY_ID_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a canonical IR id")
    return normalized


def _revision_id(value: str, field_name: str) -> str:
    normalized = _non_empty(value, field_name)
    if not _REVISION_ID_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be a canonical source revision id")
    return normalized


def _normalize_posix_path(value: str, field_name: str, *, absolute: bool) -> str:
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if "\x00" in value:
        raise ValueError(f"{field_name} must not contain NUL")
    raw = value
    if raw.startswith("/") != absolute:
        expected = "absolute" if absolute else "relative"
        raise ValueError(f"{field_name} must be a {expected} POSIX path")

    parts: list[str] = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                raise ValueError(f"{field_name} must not escape its root")
            parts.pop()
            continue
        parts.append(part)

    if not absolute and not parts:
        raise ValueError(f"{field_name} must identify a source unit")
    return ("/" if absolute else "") + "/".join(parts)


def normalize_repo_root(value: str) -> str:
    """Return an absolute normalized POSIX repository root without trimming names."""

    return _normalize_posix_path(value, "repo_root", absolute=True)


def normalize_relative_path(value: str) -> str:
    """Normalize filesystem aliases while preserving significant name bytes."""

    return _normalize_posix_path(value, "path", absolute=False)


def canonical_json_value(value: Any, path: str = "$") -> Any:
    """Return the single strict JSON-native representation used by IR boundaries."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", round_trip=True, warnings="error")
    elif isinstance(value, Enum):
        value = value.value

    if value is None or type(value) is bool or type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError(f"non-finite number at {path}")
        return value
    if type(value) is str:
        value.encode("utf-8")
        return value
    if type(value) is list:
        return [
            canonical_json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(
                    f"canonical JSON object key at {path} must be a string, "
                    f"got {type(key).__name__}"
                )
            key.encode("utf-8")
            normalized[key] = canonical_json_value(item, f"{path}.{key}")
        return normalized
    raise TypeError(f"unsupported canonical JSON type at {path}: {type(value).__name__}")


def deterministic_entity_id(
    source_revision: str,
    relative_path: str,
    entity_kind: EntityKind | str,
    language_stable_locator: str,
) -> str:
    """Derive the sole canonical entity id from the frozen four-part identity."""

    revision = _non_empty(source_revision, "source_revision")
    path = normalize_relative_path(relative_path)
    kind = EntityKind(entity_kind).value
    if not language_stable_locator:
        raise ValueError("language_stable_locator must not be empty")
    locator = language_stable_locator
    framed = _ENTITY_ID_DOMAIN + b"".join(
        len(encoded).to_bytes(8, "big") + encoded
        for value in (revision, path, kind, locator)
        for encoded in (value.encode("utf-8"),)
    )
    return f"ir_{hashlib.sha256(framed).hexdigest()}"


class IRModel(BaseModel):
    """Common fail-closed and immutable policy for all protocol values."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
    )

    @model_validator(mode="after")
    def _canonical_json_parity(self) -> Self:
        try:
            canonical_json_value(self)
        except (TypeError, ValueError, UnicodeError) as exc:
            raise ValueError(f"model state is not canonical JSON: {exc}") from exc
        return self


class SourceRevision(IRModel):
    id: str = ""
    repo_root: str
    git_commit: str | None = None
    dirty_content_digest: str | None = None
    exclusion_config_hash: str
    source_manifest_hash: str

    @field_validator("repo_root")
    @classmethod
    def _repo_root(cls, value: str) -> str:
        return normalize_repo_root(value)

    @field_validator("git_commit")
    @classmethod
    def _commit(cls, value: str | None) -> str | None:
        return None if value is None else _git_commit(value, "git_commit")

    @field_validator(
        "dirty_content_digest", "exclusion_config_hash", "source_manifest_hash"
    )
    @classmethod
    def _digest(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _sha256(value, info.field_name)

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if (self.git_commit is None) == (self.dirty_content_digest is None):
            raise ValueError(
                "exactly one of git_commit or dirty_content_digest is required"
            )
        identity = self.git_commit or self.dirty_content_digest
        framed = "\x1f".join(
            (
                self.repo_root,
                identity or "",
                self.exclusion_config_hash,
                self.source_manifest_hash,
            )
        ).encode("utf-8")
        expected = f"rev_{hashlib.sha256(framed).hexdigest()}"
        if self.id and self.id != expected:
            raise ValueError("source revision id conflicts with canonical inputs")
        if not self.id:
            object.__setattr__(self, "id", expected)
        return self


class SourceUnit(IRModel):
    id: str
    source_revision_id: str
    path: str
    language: str
    content_hash: str
    state: SourceUnitState
    backend_id: str
    backend_version: str
    diagnostics: tuple[str, ...] = ()

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator("content_hash")
    @classmethod
    def _content_hash(cls, value: str) -> str:
        return _sha256(value, "content_hash")

    @field_validator("source_revision_id")
    @classmethod
    def _revision_id(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("language", "backend_id", "backend_version")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _canonical_id(self) -> Self:
        expected = deterministic_entity_id(
            self.source_revision_id, self.path, EntityKind.SOURCE_UNIT, self.path
        )
        if self.id != expected:
            raise ValueError("source unit deterministic id does not match its identity")
        return self


class EvidenceSpan(IRModel):
    source_unit_id: str
    path: str
    start_line: int = Field(ge=1)
    start_column: int = Field(ge=0)
    end_line: int = Field(ge=1)
    end_column: int = Field(ge=0)

    @field_validator("source_unit_id")
    @classmethod
    def _source_unit_id(cls, value: str) -> str:
        return _entity_id(value, "source_unit_id")

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        start = (self.start_line, self.start_column)
        end = (self.end_line, self.end_column)
        if end < start:
            raise ValueError("evidence span end must not precede start")
        return self


class EntityRef(IRModel):
    kind: EntityKind
    id: str

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        normalized = _non_empty(value, "id")
        if not _ENTITY_ID_RE.fullmatch(normalized):
            raise ValueError("entity reference id must be a canonical IR id")
        return normalized


class Symbol(IRModel):
    id: str
    source_revision_id: str
    source_unit_id: str
    path: str
    kind: str
    qualified_name: str
    local_name: str
    definition_locator: str
    definition: EvidenceSpan
    language: str
    language_attributes: Mapping[str, str | int | float | bool | None] = Field(
        default_factory=dict
    )

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator(
        "kind",
        "qualified_name",
        "local_name",
        "definition_locator",
        "language",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("source_revision_id")
    @classmethod
    def _revision_id(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("source_unit_id")
    @classmethod
    def _source_unit_id(cls, value: str) -> str:
        return _entity_id(value, "source_unit_id")

    @field_validator("language_attributes", mode="after")
    @classmethod
    def _frozen_attributes(
        cls, value: Mapping[str, str | int | float | bool | None]
    ) -> Mapping[str, str | int | float | bool | None]:
        return FrozenDict(value)

    @field_serializer("language_attributes")
    def _serialize_attributes(
        self, value: Mapping[str, str | int | float | bool | None]
    ) -> dict[str, str | int | float | bool | None]:
        return dict(value.items())

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if self.definition.source_unit_id != self.source_unit_id:
            raise ValueError("symbol definition must belong to its source unit")
        if self.definition.path != self.path:
            raise ValueError("symbol definition path must match symbol path")
        expected = deterministic_entity_id(
            self.source_revision_id,
            self.path,
            EntityKind.SYMBOL,
            self.definition_locator,
        )
        if self.id != expected:
            raise ValueError(
                "symbol deterministic id does not match its definition locator"
            )
        return self


class Relation(IRModel):
    id: str
    source_revision_id: str
    path: str
    kind: str
    locator: str
    source: EntityRef
    target: EntityRef | None
    evidence: tuple[EvidenceSpan, ...]
    resolution_status: ResolutionStatus
    resolution_method: ResolutionMethod
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    candidates: tuple[EntityRef, ...]

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator("source_revision_id")
    @classmethod
    def _revision_id(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("kind", "locator", "reason")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _identity_and_resolution(self) -> Self:
        expected = deterministic_entity_id(
            self.source_revision_id, self.path, EntityKind.RELATION, self.locator
        )
        if self.id != expected:
            raise ValueError("relation deterministic id does not match its identity")
        if not self.evidence:
            raise ValueError("relation requires at least one evidence span")
        if any(span.path != self.path for span in self.evidence):
            raise ValueError("relation evidence must use the relation path")
        target_required = {ResolutionStatus.RESOLVED, ResolutionStatus.EXTERNAL}
        if self.resolution_status in target_required and self.target is None:
            raise ValueError(
                f"{self.resolution_status.value} relation requires a non-null target"
            )
        if self.resolution_status is ResolutionStatus.RESOLVED:
            if self.resolution_method is ResolutionMethod.SEARCH_FALLBACK:
                raise ValueError("resolved relation cannot rely on search fallback")
            if self.target not in self.candidates:
                raise ValueError("resolved relation target must be among candidates")
        if self.resolution_status is ResolutionStatus.UNRESOLVED:
            if self.target is not None:
                raise ValueError("unresolved relation requires a null target")
            if self.candidates:
                raise ValueError("unresolved relation requires empty candidates")
        return self


class CapabilityCell(IRModel):
    language: str
    capability: str
    availability: Availability
    semantic_tier: SemanticTier
    verification_status: VerificationStatus
    backend_id: str
    backend_version: str
    toolchain_conditions: tuple[str, ...]
    evidence_receipt_id: str
    limitations: tuple[str, ...]

    @field_validator(
        "language",
        "capability",
        "backend_id",
        "backend_version",
        "evidence_receipt_id",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _consistent_axes(self) -> Self:
        if (
            self.availability is not Availability.AVAILABLE
            and self.verification_status is VerificationStatus.VERIFIED
        ):
            raise ValueError("an unavailable capability cannot be verified")
        if (
            self.availability is Availability.UNSUPPORTED
            and self.verification_status
            not in {VerificationStatus.UNVERIFIED, VerificationStatus.CANNOT_JUDGE}
        ):
            raise ValueError("unsupported capability has no executable verification")
        return self


class SemanticModule(IRModel):
    id: str
    source_revision_id: str
    path: str
    locator: str
    member_ir_ids: tuple[str, ...]
    rationale: str
    producer: str
    index_revision: str

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator("source_revision_id")
    @classmethod
    def _revision_id(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("locator", "rationale", "producer", "index_revision")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("id")
    @classmethod
    def _canonical_id(cls, value: str) -> str:
        return _entity_id(value, "semantic module id")

    @model_validator(mode="after")
    def _members(self) -> Self:
        if not self.member_ir_ids or len(set(self.member_ir_ids)) != len(
            self.member_ir_ids
        ):
            raise ValueError("semantic module members must be non-empty and unique")
        if any(not _ENTITY_ID_RE.fullmatch(member) for member in self.member_ir_ids):
            raise ValueError("semantic module members must be canonical IR ids")
        expected = deterministic_entity_id(
            self.source_revision_id,
            self.path,
            EntityKind.SEMANTIC_MODULE,
            self.locator,
        )
        if self.id != expected:
            raise ValueError(
                "semantic module deterministic id does not match its locator"
            )
        return self


class ReadReceipt(IRModel):
    task_id: str
    assigned_scopes: tuple[str, ...]
    read_scopes: tuple[str, ...]
    opened_cursors: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    producer: str
    revision: str

    @field_validator("task_id", "producer", "revision")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _bounded_reads(self) -> Self:
        if not set(self.read_scopes).issubset(self.assigned_scopes):
            raise ValueError("read scopes must be a subset of assigned scopes")
        return self


class RunManifest(IRModel):
    run_id: str
    source_revision: str
    index_revision: str
    document_revision: str
    verification_revision: str
    terminal_state: RunTerminalState
    universe_partition: Mapping[SourceUnitState, tuple[str, ...]]
    schema_hashes: Mapping[str, str]
    residuals: tuple[str, ...] = ()

    @field_validator(
        "run_id",
        "source_revision",
        "index_revision",
        "document_revision",
        "verification_revision",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("schema_hashes")
    @classmethod
    def _schema_hashes(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        return FrozenDict(
            {key: _sha256(digest, f"schema_hashes[{key}]") for key, digest in value.items()}
        )

    @field_validator("universe_partition", mode="after")
    @classmethod
    def _partition_frozen(
        cls, value: Mapping[SourceUnitState, tuple[str, ...]]
    ) -> Mapping[SourceUnitState, tuple[str, ...]]:
        return FrozenDict(
            {
                state: tuple(normalize_relative_path(path) for path in paths)
                for state, paths in value.items()
            }
        )

    @field_serializer("schema_hashes")
    def _serialize_schema_hashes(
        self, value: Mapping[str, str]
    ) -> dict[str, str]:
        return dict(value.items())

    @field_serializer("universe_partition")
    def _serialize_partition(
        self, value: Mapping[SourceUnitState, tuple[str, ...]]
    ) -> dict[SourceUnitState, tuple[str, ...]]:
        return dict(value.items())

    @model_validator(mode="after")
    def _manifest_consistency(self) -> Self:
        expected_states = {
            SourceUnitState.EXCLUDED,
            SourceUnitState.UNSUPPORTED,
            SourceUnitState.UNAVAILABLE,
            SourceUnitState.PARSE_ERROR,
            SourceUnitState.INDEXED,
        }
        if set(self.universe_partition) != expected_states:
            raise ValueError("universe partition must contain every terminal state")
        members = [
            path
            for state_paths in self.universe_partition.values()
            for path in state_paths
        ]
        if len(members) != len(set(members)):
            raise ValueError("universe partition states must be mutually exclusive")
        if self.terminal_state is RunTerminalState.VERIFIED_FULL and self.residuals:
            raise ValueError("verified_full manifest cannot contain residuals")
        if (
            self.terminal_state is RunTerminalState.VERIFIED_WITH_RESIDUALS
            and not self.residuals
        ):
            raise ValueError("verified_with_residuals requires explicit residuals")
        return self


class VerificationReceipt(IRModel):
    canonical_content_hash: str
    producer_identity: str
    verifier_revision: str
    oracle_package: str
    verdict: VerifierVerdict
    counterexamples: tuple[str, ...] = ()

    @field_validator("canonical_content_hash")
    @classmethod
    def _content_hash(cls, value: str) -> str:
        return _sha256(value, "canonical_content_hash")

    @field_validator("producer_identity", "verifier_revision", "oracle_package")
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _verdict_evidence(self) -> Self:
        if self.verdict is VerifierVerdict.PASS and self.counterexamples:
            raise ValueError("passing verification cannot contain counterexamples")
        return self


class ConsumerReceipt(IRModel):
    host: str
    host_version: str
    product_commit: str
    source_revision: str
    queries: tuple[str, ...]
    cursors: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    changed_decision: str
    oracle_result: VerifierVerdict

    @field_validator(
        "host",
        "host_version",
        "source_revision",
        "changed_decision",
    )
    @classmethod
    def _required_text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("product_commit")
    @classmethod
    def _product_commit(cls, value: str) -> str:
        return _git_commit(value, "product_commit")


IR_ENTITY_MODELS: tuple[type[IRModel], ...] = (
    SourceRevision,
    SourceUnit,
    EvidenceSpan,
    EntityRef,
    Symbol,
    Relation,
    CapabilityCell,
    SemanticModule,
    ReadReceipt,
    RunManifest,
    VerificationReceipt,
    ConsumerReceipt,
)
