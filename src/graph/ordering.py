"""DAG topological ordering and PageRank analysis.

Provides functions to compute the optimal module analysis order using
SCC condensation, topological sorting, and PageRank-based prioritisation
within each topological layer.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from src.graph.grouper import ModuleMetrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisPlan:
    """Immutable plan describing the module analysis order."""

    project_name: str
    total_modules: int
    analysis_layers: tuple[tuple[str, ...], ...]  # layered analysis order
    module_metrics: dict[str, ModuleMetrics]
    has_cycles: bool
    cycle_info: tuple[tuple[str, ...], ...] | None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def topological_order(
    graph: nx.DiGraph,
    modules: dict[str, tuple[str, ...] | list[str]],
) -> list[list[str]]:
    """Compute layered topological order for inter-module dependencies.

    Strategy:
    1. Build a module-level DAG where an edge from module A to module B
       means at least one file in A depends on a file in B.
    2. Condense strongly connected components into super-nodes so that
       cycles do not prevent topological sorting.
    3. Produce layers: ``[[leaf modules], [next layer], ...]`` where
       each layer only depends on modules in previous layers.
    4. Within each layer, sort by PageRank descending (more important
       modules first).

    Args:
        graph: File-level dependency DiGraph.
        modules: Module name to file paths mapping.

    Returns:
        List of layers.  Each layer is a list of module names that can
        be analysed in parallel (they only depend on earlier layers).
    """
    module_graph = _build_module_graph(graph, modules)

    if module_graph.number_of_nodes() == 0:
        return []

    # Condense SCCs into super-nodes to handle cycles
    condensed = nx.condensation(module_graph)

    # Compute PageRank on the module graph for intra-layer ordering
    pr_scores = _safe_pagerank(module_graph)

    # Build layers via Kahn-style topological level assignment
    layers = _layered_topological_sort(condensed, pr_scores)

    logger.info(
        "Computed %d analysis layers for %d modules",
        len(layers),
        module_graph.number_of_nodes(),
    )

    return layers


def compute_pagerank(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    max_iter: int = 100,
) -> dict[str, float]:
    """Compute PageRank scores for all nodes in a dependency graph.

    Args:
        graph: Dependency DiGraph (file-level or module-level).
        alpha: Damping factor.
        max_iter: Maximum iterations.

    Returns:
        Dict mapping node identifiers to PageRank scores.
    """
    return _safe_pagerank(graph, alpha=alpha, max_iter=max_iter)


def create_analysis_plan(
    modules: dict[str, tuple[str, ...] | list[str]],
    order: list[list[str]],
    metrics: dict[str, ModuleMetrics],
    project_name: str = "project",
    graph: nx.DiGraph | None = None,
) -> AnalysisPlan:
    """Create an immutable analysis plan from modules, order, and metrics.

    Args:
        modules: Module name to file paths mapping.
        order: Layered analysis order from ``topological_order``.
        metrics: Module metrics from ``get_module_metrics``.
        project_name: Human-readable project name.
        graph: Optional file-level graph for cycle detection.

    Returns:
        ``AnalysisPlan`` dataclass.
    """
    has_cycles = False
    cycle_info: tuple[tuple[str, ...], ...] | None = None

    if graph is not None:
        module_graph = _build_module_graph(graph, modules)
        cycles = _detect_module_cycles(module_graph)
        has_cycles = len(cycles) > 0
        cycle_info = cycles if has_cycles else None

    analysis_layers = tuple(tuple(layer) for layer in order)

    plan = AnalysisPlan(
        project_name=project_name,
        total_modules=len(modules),
        analysis_layers=analysis_layers,
        module_metrics=metrics,
        has_cycles=has_cycles,
        cycle_info=cycle_info,
    )

    logger.info(
        "Created analysis plan: project=%s, modules=%d, layers=%d, cycles=%s",
        project_name,
        plan.total_modules,
        len(analysis_layers),
        has_cycles,
    )

    return plan


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_module_graph(
    file_graph: nx.DiGraph,
    modules: dict[str, tuple[str, ...] | list[str]],
) -> nx.DiGraph:
    """Build a module-level DiGraph from the file-level graph.

    An edge from module A to module B exists when at least one file
    in A has a dependency on a file in B.  Edge weight equals the
    number of such cross-module file-level edges.
    """
    # Reverse lookup: file_path -> module_name
    file_to_module: dict[str, str] = {}
    for mod_name, files in modules.items():
        for f in files:
            file_to_module[f] = mod_name

    module_graph = nx.DiGraph()
    for mod_name in modules:
        module_graph.add_node(mod_name)

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for src, tgt in file_graph.edges():
        src_mod = file_to_module.get(src)
        tgt_mod = file_to_module.get(tgt)
        if src_mod and tgt_mod and src_mod != tgt_mod:
            edge_weights[(src_mod, tgt_mod)] += 1

    for (src_mod, tgt_mod), weight in edge_weights.items():
        module_graph.add_edge(src_mod, tgt_mod, weight=weight)

    return module_graph


def _layered_topological_sort(
    condensed: nx.DiGraph,
    pr_scores: dict[str, float],
) -> list[list[str]]:
    """Produce layers from a condensed (DAG) graph.

    Each layer contains modules whose predecessors all appear in
    earlier layers.  Within a layer, modules are sorted by PageRank
    descending.

    The ``condensed`` graph is produced by ``nx.condensation()`` and
    stores the original node names in ``condensed.nodes[n]["members"]``.
    """
    layers: list[list[str]] = []
    remaining = set(condensed.nodes())

    while remaining:
        # Nodes with no incoming edges from remaining nodes
        current_layer_nodes: set[int] = set()
        for node in remaining:
            predecessors_in_remaining = [
                p for p in condensed.predecessors(node) if p in remaining
            ]
            if not predecessors_in_remaining:
                current_layer_nodes.add(node)

        if not current_layer_nodes:
            # Safety valve: shouldn't happen on a true DAG, but break
            # infinite loops by taking all remaining nodes.
            logger.warning(
                "Unexpected cycle in condensed DAG; draining %d remaining nodes",
                len(remaining),
            )
            current_layer_nodes = remaining.copy()

        # Expand SCC super-nodes back to original module names
        layer_modules: list[str] = []
        for scc_node in current_layer_nodes:
            members = condensed.nodes[scc_node].get("members", set())
            layer_modules.extend(members)

        # Sort within layer: higher PageRank first, then alphabetically
        layer_modules.sort(key=lambda m: (-pr_scores.get(m, 0.0), m))

        layers.append(layer_modules)
        remaining -= current_layer_nodes

    return layers


def _detect_module_cycles(
    module_graph: nx.DiGraph,
) -> tuple[tuple[str, ...], ...]:
    """Detect circular dependencies among modules.

    Returns tuple of SCC groups where each group has > 1 member.
    """
    cycles = tuple(
        tuple(sorted(scc))
        for scc in nx.strongly_connected_components(module_graph)
        if len(scc) > 1
    )
    if cycles:
        logger.warning(
            "Detected %d circular dependency group(s) among modules: %s",
            len(cycles),
            cycles,
        )
    return cycles


def _safe_pagerank(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    max_iter: int = 100,
) -> dict[str, float]:
    """Compute PageRank with graceful fallback on failure.

    Tries the default NetworkX implementation first (which may require
    scipy).  Falls back to a simple iterative power-method when scipy
    is unavailable, and finally to uniform scores if all else fails.
    """
    if graph.number_of_nodes() == 0:
        return {}

    # Attempt 1: default nx.pagerank (scipy-backed in 3.6+)
    try:
        return dict(nx.pagerank(graph, alpha=alpha, max_iter=max_iter))
    except (ImportError, ModuleNotFoundError):
        pass  # scipy missing, try fallback
    except nx.PowerIterationFailedConvergence:
        logger.warning("PageRank did not converge; using uniform scores")
        n = graph.number_of_nodes()
        return {node: 1.0 / n for node in graph.nodes()}
    except Exception:  # noqa: BLE001
        pass  # try fallback

    # Attempt 2: pure-Python iterative PageRank (no scipy needed)
    try:
        return _iterative_pagerank(graph, alpha=alpha, max_iter=max_iter)
    except Exception:  # noqa: BLE001
        logger.warning("PageRank fallback also failed", exc_info=True)

    # Attempt 3: uniform scores
    n = graph.number_of_nodes()
    return {node: 1.0 / n for node in graph.nodes()}


def _iterative_pagerank(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    max_iter: int = 100,
    tol: float = 1.0e-6,
) -> dict[str, float]:
    """Simple iterative PageRank without scipy dependency.

    Implements the standard power-iteration algorithm directly.
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    if n == 0:
        return {}

    node_idx = {node: i for i, node in enumerate(nodes)}
    rank = {node: 1.0 / n for node in nodes}

    # Precompute out-degree and successors
    out_degree: dict[str, int] = {}
    for node in nodes:
        out_degree[node] = graph.out_degree(node)

    for _ in range(max_iter):
        new_rank: dict[str, float] = {}
        dangling_sum = sum(
            rank[node] for node in nodes if out_degree[node] == 0
        )

        for node in nodes:
            incoming = sum(
                rank[pred] / out_degree[pred]
                for pred in graph.predecessors(node)
                if out_degree[pred] > 0
            )
            new_rank[node] = (
                (1.0 - alpha) / n
                + alpha * (incoming + dangling_sum / n)
            )

        # Check convergence
        delta = sum(abs(new_rank[node] - rank[node]) for node in nodes)
        rank = new_rank
        if delta < tol:
            break

    return rank
