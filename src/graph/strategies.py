"""Pluggable grouping strategy interface (V5).

All codebase file grouping algorithms implement the GroupingStrategy protocol.
The active strategy is selected via the CODEBASE_EXPLORER_STRATEGY env var.

Available strategies:
  - "feature_cone" (default): Louvain community detection + directory post-processing
  - "directory_first": Directory-based grouping with Louvain fallback (future)
  - "fusion": DIS-enhanced graph + Louvain (future)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import networkx as nx

from src.parser.codebase import CodebaseSnapshot


@dataclass(frozen=True)
class FunctionalModule:
    """A functional module: files grouped by purpose, not just directory."""

    module_id: str
    name: str
    files: tuple[str, ...]
    layer: int
    depends_on: tuple[str, ...]
    token_count: int
    directory_hint: str


@dataclass(frozen=True)
class StrategyResult:
    """Unified output from any grouping strategy."""

    modules: dict[str, FunctionalModule]
    infrastructure: tuple[str, ...]
    strategy_used: str
    metadata: dict


class GroupingStrategy(Protocol):
    """All grouping algorithms must implement this protocol."""

    @property
    def name(self) -> str:
        """Algorithm name for logging and metadata."""
        ...

    def group(
        self,
        graph: nx.DiGraph,
        snapshot: CodebaseSnapshot,
    ) -> StrategyResult:
        """Execute grouping, return unified result.

        Args:
            graph: Weighted dependency graph (nodes=files, edges=deps+weights).
            snapshot: Parsed codebase snapshot.

        Returns:
            StrategyResult with functional modules and infrastructure files.
        """
        ...


class FeatureConeStrategy:
    """Default strategy: Louvain community detection on weighted graph.

    Stage 1: Louvain communities on undirected weighted graph.
    Stage 2: Infrastructure identification, test separation, semantic naming.
    """

    name = "feature_cone"

    def group(
        self,
        graph: nx.DiGraph,
        snapshot: CodebaseSnapshot,
    ) -> StrategyResult:
        from src.graph.feature_cone import extract_feature_cones

        cones, infrastructure = extract_feature_cones(graph, snapshot)

        modules: dict[str, FunctionalModule] = {}
        for cid, cone in cones.items():
            modules[cid] = FunctionalModule(
                module_id=cone.cone_id,
                name=cid,
                files=cone.exclusive_files,
                layer=cone.layer,
                depends_on=cone.shared_deps,
                token_count=cone.token_count,
                directory_hint="",
            )

        return StrategyResult(
            modules=modules,
            infrastructure=tuple(infrastructure),
            strategy_used=self.name,
            metadata={},
        )


_STRATEGIES: dict[str, GroupingStrategy] = {
    "feature_cone": FeatureConeStrategy(),
}


def get_strategy(name: str | None = None) -> GroupingStrategy:
    """Get a grouping strategy by name.

    Falls back to CODEBASE_EXPLORER_STRATEGY env var, then default.
    """
    if name is None:
        name = os.environ.get("CODEBASE_EXPLORER_STRATEGY", "feature_cone")
    return _STRATEGIES.get(name, FeatureConeStrategy())


def list_strategies() -> list[str]:
    """Return names of all registered strategies."""
    return list(_STRATEGIES.keys())
