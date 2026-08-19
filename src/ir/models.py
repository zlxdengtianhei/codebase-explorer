"""Immutable canonical values for the ``cbe-ir/3`` protocol."""

from __future__ import annotations

import hashlib
import json
import keyword
import math
import re
from collections.abc import Iterable, Iterator
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


class CallOutcome(StrEnum):
    """Mutually exclusive outcomes for one Python AST call site."""

    RUNTIME_EXACT = "runtime_exact"
    VIRTUAL_DISPATCH = "virtual_dispatch"
    EXTERNAL = "external"
    UNRESOLVED_OR_DEEP = "unresolved_or_deep"


# The longer name is useful to callers that do not know the historical
# ``ResolutionStatus`` vocabulary.  Keep both names as the same enum object so
# a protocol consumer cannot accidentally create two incompatible vocabularies.
ResolutionOutcome = CallOutcome


class ReceiverShape(StrEnum):
    BARE_NAME = "bare_name"
    MODULE_ATTRIBUTE = "module_attribute"
    SELF = "self"
    CLS = "cls"
    ANNOTATED_NAME = "annotated_name"
    ATTRIBUTE_CHAIN = "attribute_chain"
    CALL_RESULT = "call_result"
    SUBSCRIPT = "subscript"
    DYNAMIC_ATTRIBUTE = "dynamic_attribute"
    OTHER = "other"


class ProvenanceBasis(StrEnum):
    DIRECT_LOCAL_BINDING = "direct_local_binding"
    IMPORT_BINDING = "import_binding"
    MODULE_BINDING = "module_binding"
    ENCLOSING_CLASS = "enclosing_class"
    RECEIVER_ANNOTATION = "receiver_annotation"
    CLASS_HIERARCHY = "class_hierarchy"
    FINAL_CLASS_OR_METHOD = "final_class_or_method"


class ReceiverGapReason(StrEnum):
    UNKNOWN_NAME = "unknown_name"
    UNTYPED_RECEIVER = "untyped_receiver"
    MISSING_LEXICAL_MEMBER = "missing_lexical_member"
    UNSUPPORTED_UNION_RECEIVER = "unsupported_union_receiver"
    ATTRIBUTE_CHAIN = "attribute_chain"
    FACTORY_RESULT = "factory_result"
    SUBSCRIPT_RECEIVER = "subscript_receiver"
    DYNAMIC_ATTRIBUTE = "dynamic_attribute"
    DYNAMIC_IMPORT = "dynamic_import"
    EXEC = "exec"
    DECORATED_CALLABLE = "decorated_callable"
    AMBIGUOUS_MRO = "ambiguous_mro"
    UNSUPPORTED_SYNTAX = "unsupported_syntax"


class ExternalEcosystem(StrEnum):
    PYTHON_BUILTIN = "python_builtin"
    PYTHON_MODULE = "python_module"
    PYTHON_DISTRIBUTION = "python_distribution"
    UNKNOWN_EXTERNAL = "unknown_external"


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
    decorators: tuple[str, ...]
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

    @field_validator("decorators")
    @classmethod
    def _decorators(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not isinstance(item, str) for item in value):
            raise ValueError("decorator names must be strings")
        if any(
            not component.isidentifier() or keyword.iskeyword(component)
            for item in value
            for component in item.split(".")
        ):
            raise ValueError(
                "decorator names must be dotted Python identifiers without keywords"
            )
        if any(item != item.strip() for item in value):
            raise ValueError("decorator names must be normalized")
        if len(value) != len(set(value)):
            raise ValueError("decorator names must be unique")
        if value != tuple(sorted(value)):
            raise ValueError("decorator names must be lexically sorted")
        return value

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


def _evidence_key(span: EvidenceSpan) -> tuple[Any, ...]:
    return (
        span.path,
        span.start_line,
        span.start_column,
        span.end_line,
        span.end_column,
        span.source_unit_id,
    )


def _source_entity_key(entity: "RepositoryEntityIdentity | None") -> tuple[Any, ...]:
    if entity is None:
        return (0,)
    return (
        1,
        entity.ref.kind.value,
        entity.ref.id,
        entity.source_revision_id,
        entity.path,
        entity.definition_locator,
    )


def _provenance_key(provenance: "Provenance") -> tuple[Any, ...]:
    return (
        provenance.basis.value,
        provenance.source_revision_id,
        _source_entity_key(provenance.source_entity),
        tuple(_evidence_key(span) for span in provenance.evidence),
    )


def _target_key(target: "TargetEvidence") -> tuple[Any, ...]:
    return (
        target.target.ref.id,
        target.target.source_revision_id,
        target.target.path,
        target.target.definition_locator,
        tuple(_provenance_key(item) for item in target.provenance),
    )


def _external_key(target: "ExternalTargetEvidence") -> tuple[Any, ...]:
    return (
        target.external_id,
        target.ecosystem.value,
        target.qualified_name,
        (0,) if target.distribution is None else (1, target.distribution),
        tuple(_provenance_key(item) for item in target.provenance),
    )


def _canonical_evidence(value: tuple[EvidenceSpan, ...], field_name: str) -> tuple[EvidenceSpan, ...]:
    if not value:
        raise ValueError(f"{field_name} requires at least one evidence span")
    deduped = { _evidence_key(item): item for item in value }
    return tuple(deduped[key] for key in sorted(deduped))


class RepositoryEntityIdentity(IRModel):
    """Recomputable identity for a repository Symbol target."""

    ref: EntityRef
    source_revision_id: str
    path: str
    definition_locator: str

    @field_validator("source_revision_id")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator("definition_locator")
    @classmethod
    def _locator(cls, value: str) -> str:
        return _non_empty(value, "definition_locator")

    @model_validator(mode="after")
    def _identity(self) -> Self:
        if self.ref.kind is not EntityKind.SYMBOL:
            raise ValueError("repository target identity must reference a Symbol")
        expected = deterministic_entity_id(
            self.source_revision_id,
            self.path,
            EntityKind.SYMBOL,
            self.definition_locator,
        )
        if self.ref.id != expected:
            raise ValueError("repository target ref does not match its identity")
        return self


class Provenance(IRModel):
    basis: ProvenanceBasis
    evidence: tuple[EvidenceSpan, ...]
    source_revision_id: str
    source_entity: RepositoryEntityIdentity | None = None

    @field_validator("source_revision_id")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @model_validator(mode="after")
    def _canonical(self) -> Self:
        object.__setattr__(
            self,
            "evidence",
            _canonical_evidence(self.evidence, "provenance evidence"),
        )
        if self.source_entity is not None and self.source_entity.source_revision_id != self.source_revision_id:
            raise ValueError("provenance source entity must use the provenance revision")
        return self


class TargetEvidence(IRModel):
    target: RepositoryEntityIdentity
    provenance: tuple[Provenance, ...]

    @model_validator(mode="after")
    def _canonical(self) -> Self:
        if not self.provenance:
            raise ValueError("target evidence requires provenance")
        if any(item.source_revision_id != self.target.source_revision_id for item in self.provenance):
            raise ValueError("target evidence provenance must use the target revision")
        deduped = {_provenance_key(item): item for item in self.provenance}
        ordered = tuple(deduped[key] for key in sorted(deduped))
        object.__setattr__(self, "provenance", ordered)
        return self


def _normalize_external_distribution(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"[-_.]+", "-", value.strip().lower())
    return _non_empty(normalized, "distribution")


def _external_identity(
    ecosystem: ExternalEcosystem,
    qualified_name: str,
    distribution: str | None,
) -> str:
    payload = json.dumps(
        [ecosystem.value, qualified_name, distribution],
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return "ext_" + hashlib.sha256(payload).hexdigest()


class ExternalTargetEvidence(IRModel):
    external_id: str
    ecosystem: ExternalEcosystem
    qualified_name: str
    distribution: str | None = None
    provenance: tuple[Provenance, ...]

    @field_validator("external_id")
    @classmethod
    def _external_id(cls, value: str) -> str:
        normalized = _non_empty(value, "external_id")
        if not re.fullmatch(r"ext_[0-9a-f]{64}", normalized):
            raise ValueError("external_id must be an ext_ SHA-256 identity")
        return normalized

    @field_validator("qualified_name")
    @classmethod
    def _qualified_name(cls, value: str) -> str:
        normalized = ".".join(part.strip() for part in value.strip().split("."))
        if not normalized or any(not part for part in normalized.split(".")):
            raise ValueError("qualified_name must be a normalized dotted name")
        return normalized

    @field_validator("distribution")
    @classmethod
    def _distribution(cls, value: str | None) -> str | None:
        return _normalize_external_distribution(value)

    @model_validator(mode="after")
    def _identity_and_provenance(self) -> Self:
        if self.ecosystem is ExternalEcosystem.PYTHON_DISTRIBUTION and self.distribution is None:
            raise ValueError("python_distribution requires distribution")
        if self.ecosystem is not ExternalEcosystem.PYTHON_DISTRIBUTION and self.distribution is not None:
            raise ValueError("only python_distribution may carry distribution")
        if self.external_id != _external_identity(self.ecosystem, self.qualified_name, self.distribution):
            raise ValueError("external_id does not match canonical external identity")
        if not self.provenance:
            raise ValueError("external target evidence requires provenance")
        revisions = {item.source_revision_id for item in self.provenance}
        if len(revisions) != 1:
            raise ValueError("external target provenance must use one source revision")
        deduped = {_provenance_key(item): item for item in self.provenance}
        object.__setattr__(self, "provenance", tuple(deduped[key] for key in sorted(deduped)))
        return self


class ReceiverGap(IRModel):
    reason: ReceiverGapReason
    receiver_text: str
    evidence: tuple[EvidenceSpan, ...]

    @field_validator("receiver_text")
    @classmethod
    def _receiver_text(cls, value: str) -> str:
        return _non_empty(value, "receiver_text")

    @model_validator(mode="after")
    def _canonical(self) -> Self:
        object.__setattr__(
            self,
            "evidence",
            _canonical_evidence(self.evidence, "receiver gap evidence"),
        )
        return self


class CallResolution(IRModel):
    outcome: CallOutcome
    receiver_shape: ReceiverShape
    runtime_exact_target: TargetEvidence | None = None
    lexical_base_target: TargetEvidence | None = None
    override_candidates: tuple[TargetEvidence, ...] = ()
    external_target: ExternalTargetEvidence | None = None
    unresolved_or_deep_receiver: ReceiverGap | None = None

    @model_validator(mode="after")
    def _cardinality_and_order(self) -> Self:
        has_runtime = self.runtime_exact_target is not None
        has_lexical = self.lexical_base_target is not None
        has_external = self.external_target is not None
        has_gap = self.unresolved_or_deep_receiver is not None
        if self.outcome is CallOutcome.RUNTIME_EXACT:
            if not has_runtime or has_lexical or self.override_candidates or has_external or has_gap:
                raise ValueError("runtime_exact requires exactly one runtime target and no other evidence")
        elif self.outcome is CallOutcome.VIRTUAL_DISPATCH:
            if not has_lexical or has_runtime or has_external or has_gap:
                raise ValueError("virtual_dispatch requires one lexical base and no runtime target")
            if any(item.target.ref.id == self.lexical_base_target.target.ref.id for item in self.override_candidates):
                raise ValueError("virtual override candidates must exclude the lexical base")
            ids = [item.target.ref.id for item in self.override_candidates]
            if len(ids) != len(set(ids)):
                raise ValueError("virtual override candidates must have unique target ids")
            if tuple(_target_key(item) for item in self.override_candidates) != tuple(
                sorted(_target_key(item) for item in self.override_candidates)
            ):
                raise ValueError("virtual override candidates must be canonically ordered")
        elif self.outcome is CallOutcome.EXTERNAL:
            if not has_external or has_runtime or has_lexical or self.override_candidates or has_gap:
                raise ValueError("external requires exactly one external target")
        elif self.outcome is CallOutcome.UNRESOLVED_OR_DEEP:
            if not has_gap or has_runtime or has_lexical or self.override_candidates or has_external:
                raise ValueError("unresolved_or_deep requires exactly one receiver gap")
        else:  # pragma: no cover - StrEnum validation normally handles this.
            raise ValueError("unknown call outcome")
        return self


def _call_locator_from_anchor(
    path: str,
    span: EvidenceSpan,
    caller_canonical_id: str,
) -> str:
    return (
        f"python:call:{span.start_line}:{span.start_column}:"
        f"{span.end_line}:{span.end_column}:{caller_canonical_id}"
    )


class CallSiteAnchor(IRModel):
    call_site_id: str
    caller_canonical_id: str
    span: EvidenceSpan

    @field_validator("call_site_id")
    @classmethod
    def _call_site_id(cls, value: str) -> str:
        return _entity_id(value, "call_site_id")

    @field_validator("caller_canonical_id")
    @classmethod
    def _caller_id(cls, value: str) -> str:
        return _non_empty(value, "caller_canonical_id")

    @model_validator(mode="after")
    def _locator_shape(self) -> Self:
        if "::" not in self.caller_canonical_id:
            raise ValueError("caller_canonical_id must use path::lexical namespace")
        path, lexical = self.caller_canonical_id.rsplit("::", 1)
        if normalize_relative_path(path) != self.span.path or not lexical:
            raise ValueError("caller_canonical_id path must match call span path")
        return self


class CallSiteInventory(IRModel):
    source_revision_id: str
    source_unit_id: str
    path: str
    language: str
    ast_backend_id: str
    ast_backend_version: str
    call_sites: tuple[CallSiteAnchor, ...] = ()

    @field_validator("source_revision_id")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _revision_id(value, "source_revision_id")

    @field_validator("source_unit_id")
    @classmethod
    def _source_unit_id(cls, value: str) -> str:
        return _entity_id(value, "source_unit_id")

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return normalize_relative_path(value)

    @field_validator("language", "ast_backend_id", "ast_backend_version")
    @classmethod
    def _text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @model_validator(mode="after")
    def _anchors(self) -> Self:
        if self.language != "python":
            raise ValueError("CallSiteInventory is defined only for Python")
        expected_unit = deterministic_entity_id(
            self.source_revision_id,
            self.path,
            EntityKind.SOURCE_UNIT,
            self.path,
        )
        if self.source_unit_id != expected_unit:
            raise ValueError("call inventory source_unit_id does not match its identity")
        previous: tuple[Any, ...] | None = None
        seen_ids: set[str] = set()
        seen_spans: set[tuple[Any, ...]] = set()
        for anchor in self.call_sites:
            if anchor.span.path != self.path or anchor.span.source_unit_id != self.source_unit_id:
                raise ValueError("call inventory anchor is bound to another source unit")
            if anchor.call_site_id in seen_ids:
                raise ValueError("call inventory contains duplicate call_site_id")
            seen_ids.add(anchor.call_site_id)
            span_key = _evidence_key(anchor.span)
            if span_key in seen_spans:
                raise ValueError("call inventory contains duplicate call span")
            seen_spans.add(span_key)
            locator = _call_locator_from_anchor(self.path, anchor.span, anchor.caller_canonical_id)
            expected_id = deterministic_entity_id(
                self.source_revision_id,
                self.path,
                EntityKind.RELATION,
                locator,
            )
            if anchor.call_site_id != expected_id:
                raise ValueError("call inventory anchor id does not match its canonical locator")
            key = (*span_key, anchor.call_site_id)
            if previous is not None and key < previous:
                raise ValueError("call inventory anchors must be canonically ordered")
            previous = key
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
    call_resolution: CallResolution | None = None

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
        if self.kind == "call":
            # Call-expression witnesses are part of the v3 canonical form;
            # normalize/dedupe them before any typed outcome checks.  A normal
            # parser emits one span, while this also makes replayed models
            # deterministic under input permutation.
            object.__setattr__(
                self,
                "evidence",
                _canonical_evidence(self.evidence, "call relation evidence"),
            )
        if self.kind == "call":
            extension = self.path.rsplit(".", 1)[-1].lower() if "." in self.path else ""
            if extension in {"py", "pyi"} and self.call_resolution is None:
                raise ValueError("Python call relations require typed call_resolution")
            if extension in {"js", "jsx", "ts", "tsx"} and self.call_resolution is not None:
                raise ValueError("non-Python legacy call relations must leave call_resolution null")
            if extension not in {"py", "pyi", "js", "jsx", "ts", "tsx"}:
                raise ValueError("call relations require a supported source extension")
            if self.call_resolution is not None:
                if self.target is not None or self.candidates:
                    raise ValueError("typed call relations cannot carry legacy target/candidates")
                for span in self.evidence:
                    expected_unit = deterministic_entity_id(
                        self.source_revision_id,
                        span.path,
                        EntityKind.SOURCE_UNIT,
                        span.path,
                    )
                    if span.source_unit_id != expected_unit:
                        raise ValueError("typed call evidence source unit is not revision-bound")
                nested_revisions: set[str] = set()
                for target in (
                    self.call_resolution.runtime_exact_target,
                    self.call_resolution.lexical_base_target,
                    *self.call_resolution.override_candidates,
                ):
                    if target is not None:
                        nested_revisions.add(target.target.source_revision_id)
                        for provenance in target.provenance:
                            nested_revisions.add(provenance.source_revision_id)
                            for span in provenance.evidence:
                                expected_unit = deterministic_entity_id(
                                    self.source_revision_id,
                                    span.path,
                                    EntityKind.SOURCE_UNIT,
                                    span.path,
                                )
                                if span.source_unit_id != expected_unit:
                                    raise ValueError("typed provenance evidence source unit is not revision-bound")
                if self.call_resolution.external_target is not None:
                    for provenance in self.call_resolution.external_target.provenance:
                        nested_revisions.add(provenance.source_revision_id)
                        for span in provenance.evidence:
                            expected_unit = deterministic_entity_id(
                                self.source_revision_id,
                                span.path,
                                EntityKind.SOURCE_UNIT,
                                span.path,
                            )
                            if span.source_unit_id != expected_unit:
                                raise ValueError("typed external evidence source unit is not revision-bound")
                if nested_revisions and nested_revisions != {self.source_revision_id}:
                    raise ValueError("typed call evidence must use the relation source revision")
                gap = self.call_resolution.unresolved_or_deep_receiver
                if gap is not None:
                    # EvidenceSpan has no revision field; its source-unit id is
                    # nevertheless recomputable against this relation revision.
                    for span in gap.evidence:
                        expected_unit = deterministic_entity_id(
                            self.source_revision_id, span.path, EntityKind.SOURCE_UNIT, span.path
                        )
                        if span.source_unit_id != expected_unit:
                            raise ValueError("typed gap evidence source unit is not revision-bound")
                expected_statuses = {
                    CallOutcome.RUNTIME_EXACT: ResolutionStatus.RESOLVED,
                    CallOutcome.VIRTUAL_DISPATCH: ResolutionStatus.AMBIGUOUS,
                    CallOutcome.EXTERNAL: ResolutionStatus.EXTERNAL,
                    CallOutcome.UNRESOLVED_OR_DEEP: {
                        ResolutionStatus.UNRESOLVED,
                        ResolutionStatus.UNSUPPORTED,
                    },
                }[self.call_resolution.outcome]
                accepted_statuses = (
                    expected_statuses
                    if isinstance(expected_statuses, set)
                    else {expected_statuses}
                )
                if self.resolution_status not in accepted_statuses:
                    raise ValueError("resolution_status is not the typed call outcome compatibility label")
                if not self.locator.startswith("python:call:"):
                    raise ValueError("typed call locator must use the v3 Python call locator")
                # Relation evidence and locator must encode the same target-free
                # six-tuple.  Recompute from the suffix after the fixed prefix.
                fields = self.locator.split(":", 6)
                if len(fields) != 7 or fields[:2] != ["python", "call"]:
                    raise ValueError("typed call locator has invalid v3 shape")
                expected = f"python:call:{self.evidence[0].start_line}:{self.evidence[0].start_column}:{self.evidence[0].end_line}:{self.evidence[0].end_column}:{fields[6]}"
                if self.locator != expected:
                    raise ValueError("typed call locator does not match relation evidence")
                caller_path, lexical = fields[6].rsplit("::", 1) if "::" in fields[6] else (None, None)
                if caller_path != self.path or not lexical:
                    raise ValueError("typed call locator caller namespace is invalid")
        elif self.call_resolution is not None:
            raise ValueError("only call relations may carry typed call_resolution")
        typed_call = self.kind == "call" and self.call_resolution is not None
        target_required = {ResolutionStatus.RESOLVED, ResolutionStatus.EXTERNAL}
        if not typed_call and self.resolution_status in target_required and self.target is None:
            raise ValueError(
                f"{self.resolution_status.value} relation requires a non-null target"
            )
        if self.resolution_status is ResolutionStatus.RESOLVED and not typed_call:
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


def reconcile_call_site_ids(
    inventories: Iterable[CallSiteInventory],
    relations: Iterable[Relation],
    expected_source_unit_ids: Iterable[str | SourceUnit] | None = None,
) -> tuple[str, ...]:
    """Fail closed unless independent inventory and typed-call IDs reconcile.

    ``expected_source_unit_ids`` is the independent Python SourceUnit
    denominator.  It is deliberately required by the caller (``None`` is a
    fail-closed error): inventory rows alone cannot prove that a zero-call
    Python file was not silently dropped.  SourceUnit objects are accepted as
    a convenience for aggregate consumers that already own the indexed
    source-unit carrier; strings are the corresponding identity-only form.
    Non-Python calls stay on the explicit legacy-null lane and are excluded.
    """

    if expected_source_unit_ids is None:
        raise ValueError("expected Python SourceUnit IDs are required for call-site reconciliation")
    expected_values = tuple(expected_source_unit_ids)
    expected_ids: set[str] = set()
    expected_revisions: set[str] = set()
    expected_paths: set[str] = set()
    for value in expected_values:
        if isinstance(value, SourceUnit):
            if value.language.lower() != "python":
                raise ValueError("call-site denominator may contain only Python SourceUnits")
            expected_id = value.id
            expected_revisions.add(value.source_revision_id)
            expected_paths.add(value.path)
        elif isinstance(value, str):
            expected_id = value
        else:
            raise TypeError("expected_source_unit_ids must contain SourceUnit objects or IDs")
        if expected_id in expected_ids:
            raise ValueError("expected Python SourceUnit denominator contains duplicate IDs")
        expected_ids.add(expected_id)

    inventory_values = tuple(inventories)
    relation_values = tuple(relations)
    inventory_ids: set[str] = set()
    inventory_units: set[str] = set()
    inventory_paths: set[str] = set()
    inventory_revisions: set[str] = set()
    for inventory in inventory_values:
        if inventory.source_unit_id in inventory_units:
            raise ValueError("duplicate call-site inventory source unit")
        if inventory.path in inventory_paths:
            raise ValueError("duplicate call-site inventory path")
        if expected_ids and inventory.source_unit_id not in expected_ids:
            raise ValueError("call-site inventory belongs to a foreign Python SourceUnit")
        inventory_units.add(inventory.source_unit_id)
        inventory_paths.add(inventory.path)
        inventory_revisions.add(inventory.source_revision_id)
        for anchor in inventory.call_sites:
            if anchor.call_site_id in inventory_ids:
                raise ValueError("duplicate call-site inventory id across source units")
            inventory_ids.add(anchor.call_site_id)

    if inventory_units != expected_ids:
        missing_inventories = sorted(expected_ids - inventory_units)
        foreign_inventories = sorted(inventory_units - expected_ids)
        raise ValueError(
            "Python SourceUnit/inventory cardinality mismatch: "
            f"missing_inventories={missing_inventories}, "
            f"foreign_inventories={foreign_inventories}"
        )
    if expected_paths and len(expected_paths) != len(expected_ids):
        raise ValueError("expected Python SourceUnit denominator contains duplicate paths")

    relation_ids: set[str] = set()
    relation_revisions: set[str] = set()
    for relation in relation_values:
        extension = relation.path.rsplit(".", 1)[-1].lower() if "." in relation.path else ""
        if relation.kind != "call" or extension not in {"py", "pyi"}:
            continue
        if relation.call_resolution is None:
            raise ValueError("Python call relation is missing typed call_resolution")
        relation_revisions.add(relation.source_revision_id)
        if relation.id in relation_ids:
            raise ValueError("duplicate typed Python call relation id")
        relation_ids.add(relation.id)

    revisions = inventory_revisions | relation_revisions | expected_revisions
    if len(revisions) > 1:
        raise ValueError("call-site inventory and relations mix source revisions")
    if inventory_ids != relation_ids:
        missing_relations = sorted(inventory_ids - relation_ids)
        missing_inventory = sorted(relation_ids - inventory_ids)
        raise ValueError(
            "call-site inventory/Relation ID set mismatch: "
            f"missing_relations={missing_relations}, missing_inventory={missing_inventory}"
        )
    return tuple(sorted(inventory_ids))


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
    CallSiteInventory,
    Relation,
    CapabilityCell,
    SemanticModule,
    ReadReceipt,
    RunManifest,
    VerificationReceipt,
    ConsumerReceipt,
)
