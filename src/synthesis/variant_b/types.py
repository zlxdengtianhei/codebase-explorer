"""Immutable records for the variant-B evidence map."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


INDEX_LINE_LIMIT = 150
DETAIL_LINE_LIMIT = 400
MAX_TRACE_NODES = 12
DEEP_FILE_COUNT = 12
DEEP_SYMBOL_COUNT = 60
DEEP_DAG_LAYERS = 3
ROOT_INDEX = "INDEX.md"
GENERATED_HEADER = "<!-- generated:codebase-explorer-variant-b -->"
HREF_TOKEN = "@@REF:{kind}:{key}@@"
TARGET_OPEN = "<!-- tgt:{kind}:{key} -->"
TARGET_CLOSE = "<!-- /tgt:{kind}:{key} -->"
FILE_LEVEL_NOTE = "模块级绑定，非枚举符号"
OVERLAY_DIR = "_overlay"
OVERLAY_PER_PAGE = 35


@dataclass(frozen=True)
class Cluster:
    cluster_id: str
    slug: str
    display: str
    files: tuple[str, ...]
    symbol_ids: tuple[str, ...]
    dag_layers: tuple[tuple[str, ...], ...]
    unassigned_reason: str | None = None
    purpose: str = ""
    name_source: str = "cluster_id"

    @property
    def n_files(self) -> int:
        return len(self.files)

    @property
    def n_symbols(self) -> int:
        return len(self.symbol_ids)

    @property
    def n_layers(self) -> int:
        return len(self.dag_layers)


@dataclass(frozen=True)
class NamedTrace:
    trace_id: str
    title: str
    cluster_id: str
    entry_surface_id: str | None
    seed_symbol_id: str | None
    ordered_symbol_ids: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    stale_nodes: tuple[str, ...]
    residual: str | None
    selection: Mapping[str, object]

    def to_json(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "title": self.title,
            "cluster_id": self.cluster_id,
            "entry_surface_id": self.entry_surface_id,
            "seed_symbol_id": self.seed_symbol_id,
            "ordered_symbol_ids": list(self.ordered_symbol_ids),
            "edges": [list(edge) for edge in self.edges],
            "stale_nodes": list(self.stale_nodes),
            "residual": self.residual,
            "selection": dict(self.selection),
        }


@dataclass(frozen=True)
class FlowTraceSet:
    repo_root: str
    source_revision: str | None
    selection_rule: str
    traces: tuple[NamedTrace, ...]

    def to_json(self) -> dict[str, object]:
        return {
            "schema": "cbe-flow-traces-b-2",
            "repo_root": self.repo_root,
            "source_revision": self.source_revision,
            "selection_rule": self.selection_rule,
            "traces": [item.to_json() for item in self.traces],
        }


@dataclass(frozen=True)
class LayerBucket:
    name: str
    files: tuple[str, ...]
    symbol_ids: tuple[str, ...]


@dataclass(frozen=True)
class ClusterLayout:
    cluster: Cluster
    deep: bool
    reason: str
    index_relpath: str | None
    buckets: tuple[LayerBucket, ...]


@dataclass(frozen=True)
class TargetRef:
    kind: str
    key: str
    page: str
    start: int
    end: int


def href_token(kind: str, key: str) -> str:
    return HREF_TOKEN.format(kind=kind, key=key)


def target_open(kind: str, key: str) -> str:
    return TARGET_OPEN.format(kind=kind, key=key)


def target_close(kind: str, key: str) -> str:
    return TARGET_CLOSE.format(kind=kind, key=key)
