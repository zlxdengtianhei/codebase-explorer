"""Immutable data contracts for Variant C.

The contracts deliberately separate model output (``PageDraft``) from
rendered Markdown.  A producer can select only target ids; it cannot supply a
URL or an anchor string.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


SECTION_TITLES = ("初始化", "请求流程", "响应阶段", "异常处理")
MAX_DETAIL_SYMBOLS = 40
MAX_DETAIL_LINES = 400


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()


def _unique_strings(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    result = tuple(_required(value, field_name) for value in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


def stable_digest(parts: Sequence[str]) -> str:
    framed = "\n".join(parts).encode("utf-8")
    return "sha256:" + hashlib.sha256(framed).hexdigest()


@dataclass(frozen=True, slots=True)
class FileCard:
    """Non-source facts supplied to a cluster-level producer."""

    path: str
    purpose: str
    symbol_ids: tuple[str, ...]
    revision: str
    line_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required(self.path, "path"))
        object.__setattr__(self, "purpose", _required(self.purpose, "purpose"))
        object.__setattr__(self, "symbol_ids", _unique_strings(self.symbol_ids, "symbol_ids"))
        object.__setattr__(self, "revision", _required(self.revision, "revision"))
        if type(self.line_count) is not int or self.line_count < 0:
            raise ValueError("line_count must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class SymbolCard:
    """One-liner and source location; source bytes are intentionally absent."""

    symbol_id: str
    path: str
    qualified_name: str
    one_liner: str
    span: tuple[int, int]
    content_hash: str
    fresh: bool = True

    def __post_init__(self) -> None:
        for name in ("symbol_id", "path", "qualified_name", "one_liner", "content_hash"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if len(self.span) != 2 or any(type(item) is not int for item in self.span):
            raise ValueError("span must contain two integers")
        if self.span[0] < 1 or self.span[1] < self.span[0]:
            raise ValueError("span must be an inclusive positive line range")
        if type(self.fresh) is not bool:
            raise ValueError("fresh must be boolean")


@dataclass(frozen=True, slots=True)
class ClusterRecord:
    """A functional cluster and its optional internal DAG layers."""

    cluster_id: str
    name: str
    purpose: str
    files: tuple[FileCard, ...]
    symbols: tuple[SymbolCard, ...]
    edges: tuple[tuple[str, str], ...] = ()
    dag_layers: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        for name in ("cluster_id", "name", "purpose"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        file_paths = tuple(file_card.path for file_card in self.files)
        if len(set(file_paths)) != len(file_paths):
            raise ValueError("cluster files must be unique")
        symbol_ids = tuple(symbol.symbol_id for symbol in self.symbols)
        if len(set(symbol_ids)) != len(symbol_ids):
            raise ValueError("cluster symbols must be unique")
        known = set(symbol_ids)
        normalized_edges = tuple((str(source), str(target)) for source, target in self.edges)
        if any(source not in known or target not in known for source, target in normalized_edges):
            raise ValueError("cluster edge endpoint is outside the cluster symbol set")
        object.__setattr__(self, "edges", tuple(sorted(set(normalized_edges))))
        layers: list[tuple[str, ...]] = []
        seen: set[str] = set()
        for layer in self.dag_layers:
            normalized = tuple(item for item in layer if item in known and item not in seen)
            if normalized:
                layers.append(normalized)
                seen.update(normalized)
        missing = tuple(item for item in symbol_ids if item not in seen)
        if missing:
            layers.append(missing)
        object.__setattr__(self, "dag_layers", tuple(layers))

    @property
    def symbol_ids(self) -> tuple[str, ...]:
        return tuple(symbol.symbol_id for symbol in self.symbols)

    @property
    def file_paths(self) -> tuple[str, ...]:
        return tuple(file_card.path for file_card in self.files)

    @property
    def layer_count(self) -> int:
        return len(self.dag_layers)


@dataclass(frozen=True, slots=True)
class BatchPlan:
    """One planned LLM call; parts are deterministic render pages, not calls."""

    batch_id: str
    cluster_id: str
    cluster_name: str
    layer: str
    symbol_ids: tuple[str, ...]
    file_paths: tuple[str, ...]
    output_path: str
    part_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("batch_id", "cluster_id", "cluster_name", "layer", "output_path"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "symbol_ids", _unique_strings(self.symbol_ids, "symbol_ids"))
        object.__setattr__(self, "file_paths", _unique_strings(self.file_paths, "file_paths"))
        parts = _unique_strings(self.part_paths, "part_paths")
        if not parts:
            raise ValueError("part_paths must contain at least one render page")
        object.__setattr__(self, "part_paths", parts)


@dataclass(frozen=True, slots=True)
class CandidateTarget:
    """A real, ledger-derived target. It has no model-supplied URL field."""

    target_id: str
    kind: str
    label: str
    target_path: str
    line_start: int
    line_end: int
    anchor: str
    source_symbol_id: str | None = None
    source_path: str | None = None

    def __post_init__(self) -> None:
        for name in ("target_id", "kind", "label", "target_path", "anchor"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if type(self.line_start) is not int or type(self.line_end) is not int:
            raise ValueError("candidate line range must contain integers")
        if self.line_start < 1 or self.line_end < self.line_start:
            raise ValueError("candidate line range must be positive and ordered")
        if self.kind not in {"symbol", "page"}:
            raise ValueError("candidate kind must be symbol or page")
        if self.kind == "symbol" and not self.source_symbol_id:
            raise ValueError("symbol candidate requires source_symbol_id")
        if self.source_path is None:
            object.__setattr__(self, "source_path", self.target_path)


@dataclass(frozen=True, slots=True)
class CandidateSet:
    """Closed candidate universe for one page."""

    page_id: str
    targets: tuple[CandidateTarget, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "page_id", _required(self.page_id, "page_id"))
        target_ids = tuple(target.target_id for target in self.targets)
        if len(set(target_ids)) != len(target_ids):
            raise ValueError("candidate target ids must be unique")

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(target.target_id for target in self.targets)

    def get(self, target_id: str) -> CandidateTarget | None:
        return next((target for target in self.targets if target.target_id == target_id), None)


@dataclass(frozen=True, slots=True)
class PageDraft:
    """Structured model output: prose plus selected ids, never Markdown links."""

    body: str
    selected_target_ids: tuple[str, ...]
    covered_symbol_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", _required(self.body, "body"))
        object.__setattr__(
            self,
            "selected_target_ids",
            _unique_strings(self.selected_target_ids, "selected_target_ids"),
        )
        object.__setattr__(
            self,
            "covered_symbol_ids",
            _unique_strings(self.covered_symbol_ids, "covered_symbol_ids"),
        )


@dataclass(frozen=True, slots=True)
class BatchReceipt:
    batch_id: str
    status: str
    attempts: int
    provider: str
    fallback_used: bool = False
    is_substitute: bool = False
    requested_primary: str | None = None
    resolved_tier: str | None = None
    fallback_chain_requested: tuple[str, ...] = ()
    route_attempts: tuple[tuple[str, str, str], ...] = ()
    source_receipt_id: str | None = None
    rejection_reason: str | None = None
    residual_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "batch_id", _required(self.batch_id, "batch_id"))
        object.__setattr__(self, "status", _required(self.status, "status"))
        object.__setattr__(self, "provider", _required(self.provider, "provider"))
        object.__setattr__(
            self,
            "fallback_chain_requested",
            _unique_strings(self.fallback_chain_requested, "fallback_chain_requested"),
        )
        object.__setattr__(
            self,
            "route_attempts",
            tuple((str(tier), str(kind), str(detail)) for tier, kind, detail in self.route_attempts),
        )
        if type(self.attempts) is not int or self.attempts < 1:
            raise ValueError("attempts must be a positive integer")


@dataclass(frozen=True, slots=True)
class PageArtifact:
    page_id: str
    output_path: str
    cluster_id: str
    cluster_name: str
    draft: PageDraft
    candidates: CandidateSet
    receipt: BatchReceipt
    part_number: int = 1
    part_count: int = 1

    def __post_init__(self) -> None:
        for name in ("page_id", "output_path", "cluster_id", "cluster_name"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.part_number < 1 or self.part_count < self.part_number:
            raise ValueError("invalid page part numbering")


@dataclass(frozen=True, slots=True)
class PageState:
    """Persisted dependency closure for one rendered page."""

    page_id: str
    output_path: str
    cited_symbol_ids: tuple[str, ...]
    cited_target_ids: tuple[str, ...]
    symbol_hashes: tuple[tuple[str, str], ...]
    file_revisions: tuple[tuple[str, str], ...]
    page_hash: str
    status: str = "fresh"
    stale_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("page_id", "output_path", "page_hash", "status"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "cited_symbol_ids", _unique_strings(self.cited_symbol_ids, "cited_symbol_ids"))
        object.__setattr__(self, "cited_target_ids", _unique_strings(self.cited_target_ids, "cited_target_ids"))
        object.__setattr__(self, "symbol_hashes", tuple(sorted(self.symbol_hashes)))
        object.__setattr__(self, "file_revisions", tuple(sorted(self.file_revisions)))


def first_sentence(text: str, limit: int = 260) -> str:
    normalized = " ".join(text.strip().split())
    for index, char in enumerate(normalized):
        if char in "。！？":
            return normalized[: index + 1]
        if char in ".!?" and (index + 1 == len(normalized) or normalized[index + 1] == " "):
            return normalized[: index + 1]
    return normalized[:limit].rstrip() + ("…" if len(normalized) > limit else "")


def as_mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("expected a mapping")
    return value
