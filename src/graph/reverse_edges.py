"""Fail-closed reverse projection for ``cbe-reverse-edges/3``.

The Python adapter is the sole call resolver.  This module projects its typed
``Relation`` values and the independent ``CallSiteInventory`` carrier; it does
not inspect source, use names as a fallback, or infer a denominator from the
edge rows.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)
from pydantic import ValidationError

from src.ir import (
    CallOutcome,
    CallSiteInventory,
    EntityKind,
    ExternalEcosystem,
    ReceiverGapReason,
    ReceiverShape,
    Relation,
    Symbol,
)


MODULE_SCOPE_SUFFIX = "<module>"
_ENTITY_ID_RE = re.compile(r"^ir_[0-9a-f]{64}$")
_REVISION_ID_RE = re.compile(r"^rev_[0-9a-f]{64}$")
_EXTERNAL_ID_RE = re.compile(r"^ext_[0-9a-f]{64}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class ReverseEdgeError(ValueError):
    """Raised when reverse input or a v3 payload is unusable."""


class ReverseResolution(StrEnum):
    RUNTIME_EXACT = "runtime_exact"
    LEXICAL_BASE = "lexical_base"
    OVERRIDE_CANDIDATE = "override_candidate"


class _V3Model(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_default=True,
        validate_assignment=True,
    )


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value


def _canonical_tuple(value: Sequence[str], field_name: str) -> tuple[str, ...]:
    result = tuple(value)
    if any(not isinstance(item, str) or not item for item in result):
        raise ValueError(f"{field_name} must contain non-empty strings")
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must be unique")
    if result != tuple(sorted(result)):
        raise ValueError(f"{field_name} must be sorted")
    return result


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_id(value: str, field_name: str = "id") -> str:
    normalized = _non_empty(value, field_name)
    if not _ENTITY_ID_RE.fullmatch(normalized):
        raise ValueError(f"{field_name} must be an IR id")
    return normalized


def _canonical_revision(value: str) -> str:
    normalized = _non_empty(value, "source_revision_id")
    if not _REVISION_ID_RE.fullmatch(normalized):
        raise ValueError("source_revision_id must be a rev_ SHA-256 id")
    return normalized


def _canonical_path(value: str, field_name: str = "path") -> str:
    normalized = _non_empty(value, field_name)
    if normalized.startswith("/") or "\\" in normalized or "\x00" in normalized:
        raise ValueError(f"{field_name} must be a normalized relative POSIX path")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise ValueError(f"{field_name} must be a normalized relative POSIX path")
    return normalized


def _lexical_name(path: str, qualified_name: str) -> str:
    stem = path[:-3] if path.endswith(".py") else path
    module = stem.replace("/", ".")
    if module.endswith(".__init__"):
        module = module[:-9]
    prefix = f"{module}." if module else ""
    return qualified_name[len(prefix) :] if prefix and qualified_name.startswith(prefix) else qualified_name


def _canonical_symbol_id(path: str, qualified_name: str) -> str:
    lexical = _lexical_name(path, qualified_name)
    if not lexical:
        raise ValueError("symbol lexical name must be non-empty")
    return f"{path}::{lexical}"


def _canonical_callee_id(value: str, field_name: str = "callee_id") -> str:
    normalized = _non_empty(value, field_name)
    if "::" not in normalized:
        raise ValueError(f"{field_name} must use canonical path::lexical namespace")
    _caller_path(normalized)
    return normalized


def _caller_path(caller_id: str) -> str:
    if "::" not in caller_id:
        raise ValueError("caller_id must use path::lexical namespace")
    path, lexical = caller_id.rsplit("::", 1)
    _canonical_path(path, "caller path")
    if not lexical:
        raise ValueError("caller lexical name must be non-empty")
    return path


class ReverseEdgeV3(_V3Model):
    callee_id: str
    caller_id: str
    call_site_id: str
    kind: Literal["call"]
    resolution: ReverseResolution
    line: StrictInt = Field(ge=1)
    via: str
    candidate_target_ids: tuple[str, ...] = ()

    @field_validator("callee_id")
    @classmethod
    def _callee(cls, value: str) -> str:
        return _canonical_callee_id(value)

    @field_validator("call_site_id")
    @classmethod
    def _ids(cls, value: str, info: Any) -> str:
        return _canonical_id(value, info.field_name)

    @field_validator("caller_id")
    @classmethod
    def _caller(cls, value: str) -> str:
        _caller_path(value)
        return value

    @field_validator("via")
    @classmethod
    def _via(cls, value: str) -> str:
        return _non_empty(value, "via")

    @field_validator("candidate_target_ids")
    @classmethod
    def _candidates(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = _canonical_tuple(value, "candidate_target_ids")
        for item in result:
            _canonical_callee_id(item, "candidate target id")
        return result

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.resolution is ReverseResolution.RUNTIME_EXACT and self.candidate_target_ids:
            raise ValueError("runtime_exact rows cannot carry candidate targets")
        if self.resolution in {
            ReverseResolution.LEXICAL_BASE,
            ReverseResolution.OVERRIDE_CANDIDATE,
        } and not self.candidate_target_ids:
            raise ValueError("virtual rows require the complete candidate target set")
        if self.resolution is ReverseResolution.OVERRIDE_CANDIDATE and self.callee_id not in self.candidate_target_ids:
            raise ValueError("override row callee must be in its candidate target set")
        if self.resolution is ReverseResolution.LEXICAL_BASE and self.callee_id not in self.candidate_target_ids:
            raise ValueError("lexical row callee must be in its candidate target set")
        return self


class UnresolvedSiteV3(_V3Model):
    call_site_id: str
    caller_id: str
    line: StrictInt = Field(ge=1)
    receiver_shape: ReceiverShape
    receiver_text: str
    reason: ReceiverGapReason

    @field_validator("call_site_id")
    @classmethod
    def _site_id(cls, value: str) -> str:
        return _canonical_id(value, "call_site_id")

    @field_validator("caller_id")
    @classmethod
    def _caller(cls, value: str) -> str:
        _caller_path(value)
        return value

    @field_validator("receiver_text")
    @classmethod
    def _text(cls, value: str) -> str:
        return _non_empty(value, "receiver_text")


class ExternalSiteV3(_V3Model):
    call_site_id: str
    caller_id: str
    line: StrictInt = Field(ge=1)
    receiver_shape: ReceiverShape
    external_id: str
    ecosystem: ExternalEcosystem
    qualified_name: str
    distribution: str | None = None

    @field_validator("call_site_id")
    @classmethod
    def _site_id(cls, value: str) -> str:
        return _canonical_id(value, "call_site_id")

    @field_validator("caller_id")
    @classmethod
    def _caller(cls, value: str) -> str:
        _caller_path(value)
        return value

    @field_validator("external_id")
    @classmethod
    def _external_id(cls, value: str) -> str:
        normalized = _non_empty(value, "external_id")
        if not _EXTERNAL_ID_RE.fullmatch(normalized):
            raise ValueError("external_id must be an ext_ SHA-256 id")
        return normalized

    @field_validator("qualified_name")
    @classmethod
    def _qualified_name(cls, value: str) -> str:
        return _non_empty(value, "qualified_name")


class ReverseSymbolV3(_V3Model):
    path: str
    qualified_name: str
    local_name: str
    kind: str
    owner_class: str | None = None
    decorators: tuple[str, ...] = ()
    span: tuple[StrictInt, StrictInt]
    ir_symbol_ids: tuple[str, ...]

    @field_validator("path")
    @classmethod
    def _path(cls, value: str) -> str:
        return _canonical_path(value)

    @field_validator("qualified_name", "local_name", "kind")
    @classmethod
    def _text(cls, value: str, info: Any) -> str:
        return _non_empty(value, info.field_name)

    @field_validator("owner_class")
    @classmethod
    def _owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        _caller_path(value)
        return value

    @field_validator("decorators")
    @classmethod
    def _decorators(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_tuple(value, "decorators")

    @field_validator("span")
    @classmethod
    def _span(cls, value: tuple[int, int]) -> tuple[int, int]:
        if len(value) != 2 or any(type(item) is not int or item < 1 for item in value):
            raise ValueError("span must contain positive line numbers")
        if value[1] < value[0]:
            raise ValueError("span end must not precede start")
        return value

    @field_validator("ir_symbol_ids")
    @classmethod
    def _ir_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        result = _canonical_tuple(value, "ir_symbol_ids")
        if not result:
            raise ValueError("ir_symbol_ids must contain at least one id")
        for item in result:
            _canonical_id(item, "ir_symbol_id")
        return result


class ReverseIndexReadingsV3(_V3Model):
    n_all_ast_calls: StrictInt = Field(ge=0)
    n_call_relations: StrictInt = Field(ge=0)
    n_runtime_exact: StrictInt = Field(ge=0)
    n_virtual_dispatch: StrictInt = Field(ge=0)
    n_external: StrictInt = Field(ge=0)
    n_unresolved_or_deep: StrictInt = Field(ge=0)
    reconciled: StrictBool
    edges_runtime_exact: StrictInt = Field(ge=0)
    edges_lexical_base: StrictInt = Field(ge=0)
    edges_override_candidate: StrictInt = Field(ge=0)
    receiver_shape_histogram: dict[str, StrictInt]
    gap_reason_histogram: dict[str, StrictInt]

    @model_validator(mode="after")
    def _counts(self) -> Self:
        if not self.reconciled:
            raise ValueError("unreconciled readings cannot enter a v3 payload")
        if self.n_all_ast_calls != self.n_call_relations:
            raise ValueError("inventory and typed Relation denominators disagree")
        if self.n_all_ast_calls != (
            self.n_runtime_exact
            + self.n_virtual_dispatch
            + self.n_external
            + self.n_unresolved_or_deep
        ):
            raise ValueError("call outcome counts do not reconcile")
        expected_shapes = {item.value for item in ReceiverShape}
        expected_gaps = {item.value for item in ReceiverGapReason}
        if set(self.receiver_shape_histogram) != expected_shapes:
            raise ValueError("receiver_shape_histogram must contain every enum value")
        if set(self.gap_reason_histogram) != expected_gaps:
            raise ValueError("gap_reason_histogram must contain every enum value")
        if any(type(value) is not int or value < 0 for value in self.receiver_shape_histogram.values()):
            raise ValueError("receiver shape histogram values must be non-negative integers")
        if any(type(value) is not int or value < 0 for value in self.gap_reason_histogram.values()):
            raise ValueError("gap reason histogram values must be non-negative integers")
        return self


class CoverageBoundaryV3(_V3Model):
    mode: Literal["static_typed_ir_only"]
    empty_runtime_exact_means: Literal["no_proven_runtime_exact_static_caller"]
    excluded_mechanisms: tuple[str, ...]
    legacy_non_python_excluded: Literal[True]
    source_revision_id: str

    @field_validator("source_revision_id")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _canonical_revision(value)

    @model_validator(mode="after")
    def _mechanisms(self) -> Self:
        expected = (
            "dynamic_attribute",
            "framework_callback",
            "runtime_dispatch",
            "string_registry",
        )
        if self.excluded_mechanisms != expected:
            raise ValueError("coverage boundary mechanisms are not canonical")
        return self


def _via_sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
    return (
        str(row.get("basis", "")),
        str(row.get("source_revision_id", "")),
        str(row.get("source_entity_id") or ""),
        _canonical_json(row.get("evidence", [])),
    )


def _validate_via(value: str, resolution: ReverseResolution, revision: str) -> None:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("via must be canonical cbe-via/1 JSON") from exc
    if not isinstance(parsed, dict) or set(parsed) != {"provenance", "schema", "target_role"}:
        raise ValueError("via has invalid cbe-via/1 keys")
    if parsed["schema"] != "cbe-via/1" or parsed["target_role"] != resolution.value:
        raise ValueError("via schema or target role is invalid")
    if not isinstance(parsed["provenance"], list) or not parsed["provenance"]:
        raise ValueError("via requires provenance")
    rows = parsed["provenance"]
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "basis", "evidence", "source_entity_id", "source_revision_id"
        }:
            raise ValueError("via provenance row has invalid keys")
        if row["source_revision_id"] != revision:
            raise ValueError("via provenance revision differs from payload revision")
        source_id = row["source_entity_id"]
        if source_id is not None:
            _canonical_id(source_id, "via source_entity_id")
        evidence = row["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("via provenance requires evidence")
        for span in evidence:
            if not isinstance(span, dict) or set(span) != {
                "end_column", "end_line", "path", "source_unit_id", "start_column", "start_line"
            }:
                raise ValueError("via evidence row has invalid keys")
            _canonical_path(str(span["path"]), "via evidence path")
            _canonical_id(str(span["source_unit_id"]), "via source_unit_id")
            if type(span["start_line"]) is not int or span["start_line"] < 1:
                raise ValueError("via evidence start_line is invalid")
            if type(span["end_line"]) is not int or span["end_line"] < 1:
                raise ValueError("via evidence end_line is invalid")
            if type(span["start_column"]) is not int or span["start_column"] < 0:
                raise ValueError("via evidence start_column is invalid")
            if type(span["end_column"]) is not int or span["end_column"] < 0:
                raise ValueError("via evidence end_column is invalid")
    if rows != sorted(rows, key=_via_sort_key):
        raise ValueError("via provenance is not canonically ordered")
    if _canonical_json(parsed) != value:
        raise ValueError("via is not canonical JSON")


def _edge_sort_key(edge: ReverseEdgeV3) -> tuple[object, ...]:
    return (
        edge.callee_id,
        edge.caller_id,
        edge.call_site_id,
        edge.kind,
        edge.resolution.value,
        edge.line,
        edge.via,
        edge.candidate_target_ids,
    )


def _unresolved_sort_key(row: UnresolvedSiteV3) -> tuple[object, ...]:
    return (
        row.call_site_id,
        row.caller_id,
        row.line,
        row.receiver_shape.value,
        row.receiver_text,
        row.reason.value,
    )


def _external_sort_key(row: ExternalSiteV3) -> tuple[object, ...]:
    return (
        row.call_site_id,
        row.caller_id,
        row.line,
        row.receiver_shape.value,
        row.external_id,
        row.ecosystem.value,
        row.qualified_name,
        (0,) if row.distribution is None else (1, row.distribution),
    )


class ReversePayloadV3(_V3Model):
    schema: Literal["cbe-reverse-edges/3"]
    source: Literal["cbe-ir/3 Relation(kind=call)+CallSiteInventory"]
    source_revision_id: str
    repo: str
    coverage_boundary: CoverageBoundaryV3
    readings: ReverseIndexReadingsV3
    symbols: dict[str, ReverseSymbolV3]
    by_callee_symbol: dict[str, tuple[ReverseEdgeV3, ...]]
    by_callee_path: dict[str, tuple[str, ...]]
    unresolved_sites: tuple[UnresolvedSiteV3, ...]
    external_sites: tuple[ExternalSiteV3, ...]

    @field_validator("source_revision_id")
    @classmethod
    def _revision(cls, value: str) -> str:
        return _canonical_revision(value)

    @field_validator("repo")
    @classmethod
    def _repo(cls, value: str) -> str:
        normalized = _non_empty(value, "repo")
        if not _REPO_RE.fullmatch(normalized):
            raise ValueError("repo contains characters outside the v3 label grammar")
        return normalized

    @model_validator(mode="after")
    def _payload(self) -> Self:
        if self.coverage_boundary.source_revision_id != self.source_revision_id:
            raise ValueError("coverage boundary revision differs from payload revision")
        if not self.symbols:
            raise ValueError("v3 reverse payload requires symbols")
        if tuple(self.symbols) != tuple(sorted(self.symbols)):
            raise ValueError("symbols map keys must be sorted")
        for symbol_id, symbol in self.symbols.items():
            expected = _canonical_symbol_id(symbol.path, symbol.qualified_name)
            if symbol_id != expected:
                raise ValueError("symbol map key is not the canonical path::lexical id")
            if symbol.kind == "method" and symbol.owner_class is None:
                raise ValueError("method ReverseSymbolV3 requires owner_class")
            if symbol.kind != "method" and symbol.owner_class is not None:
                raise ValueError("only method ReverseSymbolV3 may carry owner_class")
            if symbol.owner_class is not None and symbol.owner_class not in self.symbols:
                raise ValueError("method owner_class is not present in symbols")

        if tuple(self.by_callee_symbol) != tuple(sorted(self.by_callee_symbol)):
            raise ValueError("by_callee_symbol map keys must be sorted")
        all_edges: list[ReverseEdgeV3] = []
        for callee_id, rows in self.by_callee_symbol.items():
            if callee_id not in self.symbols or not rows:
                raise ValueError("by_callee_symbol key must name a non-empty symbol row set")
            if tuple(rows) != tuple(sorted(rows, key=_edge_sort_key)):
                raise ValueError("by_callee_symbol rows must be sorted")
            if len(set(_edge_sort_key(row) for row in rows)) != len(rows):
                raise ValueError("by_callee_symbol rows must be duplicate-free")
            for row in rows:
                if row.callee_id != callee_id:
                    raise ValueError("edge callee_id does not match its map key")
                if any(target not in self.symbols for target in row.candidate_target_ids):
                    raise ValueError("edge candidate target is not a known symbol")
                _validate_via(row.via, row.resolution, self.source_revision_id)
                all_edges.append(row)

        if tuple(self.by_callee_path) != tuple(sorted(self.by_callee_path)):
            raise ValueError("by_callee_path map keys must be sorted")
        expected_paths: dict[str, set[str]] = defaultdict(set)
        for row in all_edges:
            expected_paths[row.callee_id.split("::", 1)[0]].add(_caller_path(row.caller_id))
        if set(self.by_callee_path) != set(expected_paths):
            raise ValueError("by_callee_path keys do not match edge-bearing callee paths")
        for path, callers in self.by_callee_path.items():
            _canonical_path(path, "by_callee_path key")
            if tuple(callers) != tuple(sorted(callers)) or len(set(callers)) != len(callers):
                raise ValueError("by_callee_path callers must be sorted and unique")
            if set(callers) != expected_paths[path]:
                raise ValueError("by_callee_path callers do not match edge rows")

        if tuple(self.unresolved_sites) != tuple(sorted(self.unresolved_sites, key=_unresolved_sort_key)):
            raise ValueError("unresolved_sites must be sorted")
        if len(set(_unresolved_sort_key(row) for row in self.unresolved_sites)) != len(self.unresolved_sites):
            raise ValueError("unresolved_sites must be duplicate-free")
        if tuple(self.external_sites) != tuple(sorted(self.external_sites, key=_external_sort_key)):
            raise ValueError("external_sites must be sorted")
        if len(set(_external_sort_key(row) for row in self.external_sites)) != len(self.external_sites):
            raise ValueError("external_sites must be duplicate-free")

        edge_site_groups: dict[str, list[ReverseEdgeV3]] = defaultdict(list)
        for row in all_edges:
            edge_site_groups[row.call_site_id].append(row)
        unresolved_ids = {row.call_site_id for row in self.unresolved_sites}
        external_ids = {row.call_site_id for row in self.external_sites}
        if set(edge_site_groups) & (unresolved_ids | external_ids) or unresolved_ids & external_ids:
            raise ValueError("call sites occur in multiple outcome groups")
        if len(edge_site_groups) + len(unresolved_ids) + len(external_ids) != self.readings.n_all_ast_calls:
            raise ValueError("payload call-site groups do not match readings denominator")
        runtime_ids = {
            site_id for site_id, rows in edge_site_groups.items()
            if any(row.resolution is ReverseResolution.RUNTIME_EXACT for row in rows)
        }
        virtual_ids = set(edge_site_groups) - runtime_ids
        if any(
            sum(row.resolution is ReverseResolution.RUNTIME_EXACT for row in rows) != 1
            for rows in edge_site_groups.values()
            if any(row.resolution is ReverseResolution.RUNTIME_EXACT for row in rows)
        ):
            raise ValueError("each runtime-exact call site must have one runtime row")
        for site_id in virtual_ids:
            rows = edge_site_groups[site_id]
            if not any(row.resolution is ReverseResolution.LEXICAL_BASE for row in rows):
                raise ValueError("each virtual call site requires one lexical row")
            candidate_sets = {row.candidate_target_ids for row in rows}
            if len(candidate_sets) != 1:
                raise ValueError("virtual call-site rows must share candidate target set")
            if len(rows) != len(next(iter(candidate_sets))):
                raise ValueError("virtual call-site row count must equal complete candidate set")

        if len(runtime_ids) != self.readings.n_runtime_exact:
            raise ValueError("runtime-exact readings disagree with edge groups")
        if len(virtual_ids) != self.readings.n_virtual_dispatch:
            raise ValueError("virtual readings disagree with edge groups")
        if len(external_ids) != self.readings.n_external:
            raise ValueError("external readings disagree with site rows")
        if len(unresolved_ids) != self.readings.n_unresolved_or_deep:
            raise ValueError("unresolved readings disagree with site rows")
        if sum(row.resolution is ReverseResolution.RUNTIME_EXACT for row in all_edges) != self.readings.edges_runtime_exact:
            raise ValueError("runtime edge reading disagrees with rows")
        if sum(row.resolution is ReverseResolution.LEXICAL_BASE for row in all_edges) != self.readings.edges_lexical_base:
            raise ValueError("lexical edge reading disagrees with rows")
        if sum(row.resolution is ReverseResolution.OVERRIDE_CANDIDATE for row in all_edges) != self.readings.edges_override_candidate:
            raise ValueError("override edge reading disagrees with rows")
        return self


def validate_reverse_payload(payload: Mapping[str, object] | ReversePayloadV3) -> ReversePayloadV3:
    """Validate the one canonical object used by builders, sidecars and renderers."""

    try:
        return ReversePayloadV3.model_validate(payload)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ReverseEdgeError(f"invalid cbe-reverse-edges/3 payload: {exc}") from exc


@dataclass(frozen=True)
class CallerAnswer:
    """Separate runtime-exact, lexical-base and non-answer override rows."""

    callee_id: str
    runtime_exact: tuple[ReverseEdgeV3, ...]
    lexical_base: tuple[ReverseEdgeV3, ...]
    override_candidates: tuple[ReverseEdgeV3, ...]
    coverage_note: str


@dataclass(frozen=True)
class ReverseIndex:
    """Immutable in-memory v3 projection."""

    repo: str
    source_revision_id: str
    symbols: Mapping[str, ReverseSymbolV3]
    by_callee_symbol: Mapping[str, tuple[ReverseEdgeV3, ...]]
    by_callee_path: Mapping[str, tuple[str, ...]]
    unresolved_sites: tuple[UnresolvedSiteV3, ...]
    external_sites: tuple[ExternalSiteV3, ...]
    readings: ReverseIndexReadingsV3
    coverage_boundary: CoverageBoundaryV3
    _payload: ReversePayloadV3 = field(repr=False)

    def callers_of(self, callee_id: str) -> CallerAnswer:
        rows = self.by_callee_symbol.get(callee_id, ())
        return CallerAnswer(
            callee_id=callee_id,
            runtime_exact=tuple(row for row in rows if row.resolution is ReverseResolution.RUNTIME_EXACT),
            lexical_base=tuple(row for row in rows if row.resolution is ReverseResolution.LEXICAL_BASE),
            override_candidates=tuple(row for row in rows if row.resolution is ReverseResolution.OVERRIDE_CANDIDATE),
            coverage_note=self.coverage_boundary.empty_runtime_exact_means,
        )

    def caller_paths_of(self, path: str) -> tuple[str, ...]:
        return self.by_callee_path.get(path, ())

    def to_payload(self) -> dict[str, object]:
        validated = validate_reverse_payload(self._payload)
        return validated.model_dump(mode="json")


def _source_revision_from_inputs(
    symbols: Sequence[Symbol],
    relations: Sequence[Relation],
    inventories: Sequence[CallSiteInventory],
) -> str:
    revisions = {item.source_revision_id for item in (*symbols, *relations, *inventories)}
    if len(revisions) != 1:
        raise ReverseEdgeError("reverse input mixes source revisions")
    return next(iter(revisions))


def _owner_class(symbol: Symbol, canonical_ids: set[str]) -> str | None:
    if symbol.kind != "method":
        return None
    lexical = _lexical_name(symbol.path, symbol.qualified_name)
    if "." not in lexical:
        raise ReverseEdgeError(f"method has no canonical owner class: {symbol.path}::{lexical}")
    owner = f"{symbol.path}::{lexical.rsplit('.', 1)[0]}"
    if owner not in canonical_ids:
        raise ReverseEdgeError(f"method owner class is absent from reverse symbols: {owner}")
    return owner


def _reverse_symbols(
    symbols: Sequence[Symbol],
) -> tuple[dict[str, ReverseSymbolV3], dict[str, str], dict[str, Symbol]]:
    if not symbols:
        raise ReverseEdgeError("reverse index requires at least one Symbol")
    by_canonical: dict[str, list[Symbol]] = defaultdict(list)
    by_ir: dict[str, Symbol] = {}
    for symbol in symbols:
        prior = by_ir.get(symbol.id)
        if prior is not None and prior != symbol:
            raise ReverseEdgeError(f"IR Symbol id is bound to multiple values: {symbol.id}")
        by_ir[symbol.id] = symbol
        by_canonical[_canonical_symbol_id(symbol.path, symbol.qualified_name)].append(symbol)
    canonical_ids = set(by_canonical)
    output: dict[str, ReverseSymbolV3] = {}
    ir_to_canonical: dict[str, str] = {}
    for canonical, group in sorted(by_canonical.items()):
        chosen = min(group, key=lambda item: item.id)
        for candidate in group:
            if (
                candidate.path != chosen.path
                or candidate.qualified_name != chosen.qualified_name
                or candidate.local_name != chosen.local_name
                or candidate.kind != chosen.kind
                or candidate.decorators != chosen.decorators
            ):
                raise ReverseEdgeError(f"canonical Symbol projection is ambiguous: {canonical}")
            ir_to_canonical[candidate.id] = canonical
        owner = _owner_class(chosen, canonical_ids)
        output[canonical] = ReverseSymbolV3(
            path=chosen.path,
            qualified_name=chosen.qualified_name,
            local_name=chosen.local_name,
            kind=chosen.kind,
            owner_class=owner,
            decorators=chosen.decorators,
            span=(chosen.definition.start_line, chosen.definition.end_line),
            ir_symbol_ids=tuple(sorted(item.id for item in group)),
        )
    return output, ir_to_canonical, by_ir


def _target_id(
    target_evidence: Any,
    *,
    source_revision_id: str,
    ir_to_canonical: Mapping[str, str],
    ir_symbols: Mapping[str, Symbol],
) -> str:
    target = target_evidence.target
    if target.source_revision_id != source_revision_id:
        raise ReverseEdgeError("target identity uses a foreign source revision")
    symbol = ir_symbols.get(target.ref.id)
    if symbol is None or target.ref.kind is not EntityKind.SYMBOL:
        raise ReverseEdgeError(f"target ref is not an accepted Symbol: {target.ref.id}")
    if (
        symbol.source_revision_id != target.source_revision_id
        or symbol.path != target.path
        or symbol.definition_locator != target.definition_locator
    ):
        raise ReverseEdgeError("target ref identity does not match its accepted Symbol")
    canonical = ir_to_canonical.get(target.ref.id)
    if canonical is None:
        raise ReverseEdgeError(f"target ref is outside the accepted Symbol universe: {target.ref.id}")
    return canonical


def _via(target_evidence: Any, role: ReverseResolution) -> str:
    provenance = []
    for item in target_evidence.provenance:
        provenance.append(
            {
                "basis": item.basis.value,
                "evidence": [
                    {
                        "end_column": span.end_column,
                        "end_line": span.end_line,
                        "path": span.path,
                        "source_unit_id": span.source_unit_id,
                        "start_column": span.start_column,
                        "start_line": span.start_line,
                    }
                    for span in item.evidence
                ],
                "source_entity_id": (
                    item.source_entity.ref.id if item.source_entity is not None else None
                ),
                "source_revision_id": item.source_revision_id,
            }
        )
    provenance.sort(key=_via_sort_key)
    return _canonical_json(
        {
            "provenance": provenance,
            "schema": "cbe-via/1",
            "target_role": role.value,
        }
    )


def _caller_from_inventory(relation: Relation, anchors: Mapping[str, Any]) -> str:
    anchor = anchors.get(relation.id)
    if anchor is None:
        raise ReverseEdgeError(f"typed call relation is absent from CallSiteInventory: {relation.id}")
    span = relation.evidence[0]
    if anchor.span != span:
        raise ReverseEdgeError(f"Relation and inventory span disagree for {relation.id}")
    fields = relation.locator.split(":", 6)
    if len(fields) != 7 or fields[:2] != ["python", "call"]:
        raise ReverseEdgeError(f"typed call locator has invalid v3 shape: {relation.locator}")
    caller = fields[6]
    if caller != anchor.caller_canonical_id:
        raise ReverseEdgeError(f"Relation and inventory caller disagree for {relation.id}")
    return caller


def _call_line(relation: Relation) -> int:
    if not relation.evidence:
        raise ReverseEdgeError(f"call relation has no evidence: {relation.id}")
    return relation.evidence[0].start_line


def build_reverse_index_from_ir(
    symbols: Iterable[Symbol],
    relations: Iterable[Relation],
    inventories: Iterable[CallSiteInventory],
    *,
    repo: str,
) -> ReverseIndex:
    """Project typed IR plus its independent inventory into reverse v3."""

    if not isinstance(repo, str) or not _REPO_RE.fullmatch(repo):
        raise ReverseEdgeError("reverse index requires a valid non-empty repo label")
    ir_symbols = tuple(sorted(symbols, key=lambda item: item.id))
    ir_relations = tuple(sorted(relations, key=lambda item: item.id))
    call_inventories = tuple(sorted(inventories, key=lambda item: item.path))
    if not call_inventories:
        raise ReverseEdgeError("reverse index requires independent CallSiteInventory values")
    source_revision_id = _source_revision_from_inputs(ir_symbols, ir_relations, call_inventories)
    reverse_symbols, ir_to_canonical, ir_symbol_map = _reverse_symbols(ir_symbols)

    inventory_by_id: dict[str, Any] = {}
    for inventory in call_inventories:
        if inventory.source_revision_id != source_revision_id:
            raise ReverseEdgeError("CallSiteInventory uses a foreign source revision")
        for anchor in inventory.call_sites:
            if anchor.call_site_id in inventory_by_id:
                raise ReverseEdgeError("duplicate call_site_id across inventories")
            inventory_by_id[anchor.call_site_id] = anchor

    typed_relations = [
        relation
        for relation in ir_relations
        if relation.kind == "call"
        and relation.path.rsplit(".", 1)[-1].lower() in {"py", "pyi"}
    ]
    if any(relation.call_resolution is None for relation in typed_relations):
        raise ReverseEdgeError("Python call relation is missing typed call_resolution")
    typed_ids = {relation.id for relation in typed_relations}
    inventory_ids = set(inventory_by_id)
    if typed_ids != inventory_ids:
        raise ReverseEdgeError(
            "CallSiteInventory/Relation ID set mismatch: "
            f"missing_relations={sorted(inventory_ids - typed_ids)}, "
            f"missing_inventory={sorted(typed_ids - inventory_ids)}"
        )

    edges: list[ReverseEdgeV3] = []
    unresolved: list[UnresolvedSiteV3] = []
    external: list[ExternalSiteV3] = []
    shape_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    for relation in typed_relations:
        resolution = relation.call_resolution
        assert resolution is not None
        caller = _caller_from_inventory(relation, inventory_by_id)
        line = _call_line(relation)
        shape_counts[resolution.receiver_shape.value] += 1
        outcome_counts[resolution.outcome.value] += 1
        if resolution.outcome is CallOutcome.RUNTIME_EXACT:
            target = resolution.runtime_exact_target
            if target is None:
                raise ReverseEdgeError("runtime_exact relation lacks target evidence")
            callee = _target_id(
                target,
                source_revision_id=source_revision_id,
                ir_to_canonical=ir_to_canonical,
                ir_symbols=ir_symbol_map,
            )
            edges.append(
                ReverseEdgeV3(
                    callee_id=callee,
                    caller_id=caller,
                    call_site_id=relation.id,
                    kind="call",
                    resolution=ReverseResolution.RUNTIME_EXACT,
                    line=line,
                    via=_via(target, ReverseResolution.RUNTIME_EXACT),
                )
            )
        elif resolution.outcome is CallOutcome.VIRTUAL_DISPATCH:
            lexical = resolution.lexical_base_target
            if lexical is None:
                raise ReverseEdgeError("virtual relation lacks lexical base evidence")
            lexical_id = _target_id(
                lexical,
                source_revision_id=source_revision_id,
                ir_to_canonical=ir_to_canonical,
                ir_symbols=ir_symbol_map,
            )
            override_ids = [
                _target_id(
                    item,
                    source_revision_id=source_revision_id,
                    ir_to_canonical=ir_to_canonical,
                    ir_symbols=ir_symbol_map,
                )
                for item in resolution.override_candidates
            ]
            candidates = tuple(sorted((lexical_id, *override_ids)))
            edges.append(
                ReverseEdgeV3(
                    callee_id=lexical_id,
                    caller_id=caller,
                    call_site_id=relation.id,
                    kind="call",
                    resolution=ReverseResolution.LEXICAL_BASE,
                    line=line,
                    via=_via(lexical, ReverseResolution.LEXICAL_BASE),
                    candidate_target_ids=candidates,
                )
            )
            for item, target_id in zip(resolution.override_candidates, override_ids):
                edges.append(
                    ReverseEdgeV3(
                        callee_id=target_id,
                        caller_id=caller,
                        call_site_id=relation.id,
                        kind="call",
                        resolution=ReverseResolution.OVERRIDE_CANDIDATE,
                        line=line,
                        via=_via(item, ReverseResolution.OVERRIDE_CANDIDATE),
                        candidate_target_ids=candidates,
                    )
                )
        elif resolution.outcome is CallOutcome.EXTERNAL:
            target = resolution.external_target
            if target is None:
                raise ReverseEdgeError("external relation lacks external evidence")
            external.append(
                ExternalSiteV3(
                    call_site_id=relation.id,
                    caller_id=caller,
                    line=line,
                    receiver_shape=resolution.receiver_shape,
                    external_id=target.external_id,
                    ecosystem=target.ecosystem,
                    qualified_name=target.qualified_name,
                    distribution=target.distribution,
                )
            )
        elif resolution.outcome is CallOutcome.UNRESOLVED_OR_DEEP:
            gap = resolution.unresolved_or_deep_receiver
            if gap is None:
                raise ReverseEdgeError("unresolved relation lacks receiver gap")
            gap_counts[gap.reason.value] += 1
            unresolved.append(
                UnresolvedSiteV3(
                    call_site_id=relation.id,
                    caller_id=caller,
                    line=line,
                    receiver_shape=resolution.receiver_shape,
                    receiver_text=gap.receiver_text,
                    reason=gap.reason,
                )
            )
        else:  # pragma: no cover - CallOutcome is exhaustive
            raise ReverseEdgeError(f"unsupported call outcome: {resolution.outcome}")

    edges = sorted(edges, key=_edge_sort_key)
    unresolved = sorted(unresolved, key=_unresolved_sort_key)
    external = sorted(external, key=_external_sort_key)
    by_callee: dict[str, list[ReverseEdgeV3]] = defaultdict(list)
    by_path: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        by_callee[edge.callee_id].append(edge)
        by_path[edge.callee_id.split("::", 1)[0]].add(_caller_path(edge.caller_id))
    by_callee_symbol = {
        key: tuple(sorted(value, key=_edge_sort_key)) for key, value in sorted(by_callee.items())
    }
    by_callee_path = {
        key: tuple(sorted(value)) for key, value in sorted(by_path.items())
    }

    shape_histogram = {key: shape_counts.get(key, 0) for key in sorted(item.value for item in ReceiverShape)}
    gap_histogram = {key: gap_counts.get(key, 0) for key in sorted(item.value for item in ReceiverGapReason)}
    readings = ReverseIndexReadingsV3(
        n_all_ast_calls=len(inventory_ids),
        n_call_relations=len(typed_relations),
        n_runtime_exact=outcome_counts[CallOutcome.RUNTIME_EXACT.value],
        n_virtual_dispatch=outcome_counts[CallOutcome.VIRTUAL_DISPATCH.value],
        n_external=outcome_counts[CallOutcome.EXTERNAL.value],
        n_unresolved_or_deep=outcome_counts[CallOutcome.UNRESOLVED_OR_DEEP.value],
        reconciled=True,
        edges_runtime_exact=sum(row.resolution is ReverseResolution.RUNTIME_EXACT for row in edges),
        edges_lexical_base=sum(row.resolution is ReverseResolution.LEXICAL_BASE for row in edges),
        edges_override_candidate=sum(row.resolution is ReverseResolution.OVERRIDE_CANDIDATE for row in edges),
        receiver_shape_histogram=shape_histogram,
        gap_reason_histogram=gap_histogram,
    )
    boundary = CoverageBoundaryV3(
        mode="static_typed_ir_only",
        empty_runtime_exact_means="no_proven_runtime_exact_static_caller",
        excluded_mechanisms=(
            "dynamic_attribute",
            "framework_callback",
            "runtime_dispatch",
            "string_registry",
        ),
        legacy_non_python_excluded=True,
        source_revision_id=source_revision_id,
    )
    payload = ReversePayloadV3(
        schema="cbe-reverse-edges/3",
        source="cbe-ir/3 Relation(kind=call)+CallSiteInventory",
        source_revision_id=source_revision_id,
        repo=repo,
        coverage_boundary=boundary,
        readings=readings,
        symbols=dict(sorted(reverse_symbols.items())),
        by_callee_symbol=by_callee_symbol,
        by_callee_path=by_callee_path,
        unresolved_sites=tuple(unresolved),
        external_sites=tuple(external),
    )
    validate_reverse_payload(payload)
    return ReverseIndex(
        repo=repo,
        source_revision_id=source_revision_id,
        symbols=payload.symbols,
        by_callee_symbol=payload.by_callee_symbol,
        by_callee_path=payload.by_callee_path,
        unresolved_sites=payload.unresolved_sites,
        external_sites=payload.external_sites,
        readings=payload.readings,
        coverage_boundary=payload.coverage_boundary,
        _payload=payload,
    )


def build_reverse_index(
    root_path: str,
    universe: Iterable[str] = (),
    *,
    repo: str,
    package_name: str | None = None,
    ledger_symbol_ids: Iterable[str] | None = None,
) -> ReverseIndex:
    """Build v3 from the server's canonical IR bridge.

    ``universe``, ``package_name`` and ``ledger_symbol_ids`` remain accepted at
    this outer compatibility boundary for callers that still pass them, but
    none can provide reverse outcomes or denominator rows.
    """

    del universe, package_name, ledger_symbol_ids
    root = Path(root_path)
    if not root.is_dir():
        raise ReverseEdgeError(f"package root is not a directory: {root_path}")
    try:
        from src.semantic.inventory import enumerate_semantic_inventory
        from src.server import _python_semantic_ir_cached

        inventory = enumerate_semantic_inventory(root)
        symbols, relations, inventories = _python_semantic_ir_cached(
            root.as_posix(), inventory.source_revision
        )
    except Exception as exc:  # pragma: no cover - boundary error wording
        raise ReverseEdgeError(f"cannot load canonical Python IR: {exc}") from exc
    return build_reverse_index_from_ir(symbols, relations, inventories, repo=repo)


def write_sidecar(index: ReverseIndex, destination: Path) -> Path:
    """Write canonical v3 JSON without a compatibility marker."""

    payload = validate_reverse_payload(index.to_payload()).model_dump(mode="json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_canonical_json(payload) + "\n", encoding="utf-8")
    return destination


def load_sidecar(source: Path) -> dict[str, object]:
    """Read and validate one v3 sidecar; v2 requires replay/rebuild."""

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReverseEdgeError(f"invalid reverse sidecar {source}: {exc}") from exc
    if isinstance(payload, Mapping) and payload.get("schema") == "cbe-reverse-edges/2":
        raise ReverseEdgeError("cbe-reverse-edges/2 sidecars require replay/rebuild from cbe-ir/3")
    return validate_reverse_payload(payload).model_dump(mode="json")
