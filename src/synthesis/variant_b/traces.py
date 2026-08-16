"""One named trace per function cluster.

Selection is fully deterministic. Do not hand-pick seeds.

Rule (also written into flow_traces.json `selection_rule`):

1. Candidate seeds = overlay-resolved symbols in the cluster, plus methods
   of those overlay-resolved classes (same cluster). If empty: in-degree-0
   cluster nodes. If still empty: every cluster symbol.
2. Walk graph = probe AST calls ∪ IR relations ∪ overlay aliases.
   Citation edges are NOT used for walking (they are not call edges).
3. For each candidate seed, compute the longest SCC-DAG path in the cluster
   subgraph (one hop outside only if that seed has no intra-cluster successor).
4. Chosen seed = argmax (path length, seed PageRank, seed out-degree, -id).
   That is "the public-surface entry whose call path is longest", not a
   hand-picked tail list.
5. Realize the winning SCC path as a node sequence (highest-PageRank unused
   adjacent node inside each SCC). Cap 12 nodes.
6. Zero-symbol clusters emit a residual placeholder.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

import networkx as nx

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.edges import pagerank_scores
from src.synthesis.variant_b.surface import PublicSurface
from src.synthesis.variant_b.text import tail
from src.synthesis.variant_b.types import Cluster, FlowTraceSet, MAX_TRACE_NODES, NamedTrace


SELECTION_RULE = (
    "Per-cluster main trace. Candidate seeds = overlay-resolved symbols in "
    "the cluster plus methods of overlay-resolved classes. Walk graph = "
    "probe AST calls ∪ IR ∪ overlay aliases (not citation edges). For each "
    "seed compute the longest SCC-DAG path (one hop outside only if the seed "
    "has no intra-cluster successor). Keep the seed with max (path length, "
    "PageRank, out-degree, -id). Realize the SCC path by highest-PageRank "
    "unused adjacent node (cap 12). Zero-symbol clusters emit a residual "
    "placeholder. No hand-picked tails."
)


def _overlay_resolved(surface: PublicSurface) -> set[str]:
    return {symbol_id for item in surface.bindings for symbol_id in item.resolved_symbol_ids}


def _out_degree(edges: set[tuple[str, str]]) -> dict[str, int]:
    degree: dict[str, int] = defaultdict(int)
    for src, _dst in edges:
        degree[src] += 1
    return dict(degree)


def _in_degree(edges: set[tuple[str, str]], nodes: set[str]) -> dict[str, int]:
    degree = {node: 0 for node in nodes}
    for src, dst in edges:
        if src in nodes and dst in nodes:
            degree[dst] = degree.get(dst, 0) + 1
    return degree


def _candidate_seeds(
    cluster: Cluster,
    ledger: SemanticLedger,
    preferred: set[str],
    edges: set[tuple[str, str]],
) -> list[str]:
    cluster_set = set(cluster.symbol_ids)
    if not cluster_set:
        return []
    seeds = {symbol_id for symbol_id in cluster.symbol_ids if symbol_id in preferred}
    class_ids = {
        symbol_id
        for symbol_id in seeds
        if ledger.symbols[symbol_id].kind.value == "class"
    }
    for symbol_id in cluster.symbol_ids:
        record = ledger.symbols[symbol_id]
        if record.kind.value != "method" or "." not in record.qualified_name:
            continue
        owner = f"{record.path}::{record.qualified_name.rsplit('.', 1)[0]}"
        if owner in class_ids:
            seeds.add(symbol_id)
    if not seeds:
        inbound = _in_degree(edges, cluster_set)
        seeds = {symbol_id for symbol_id in cluster.symbol_ids if inbound.get(symbol_id, 0) == 0}
    if not seeds:
        seeds = set(cluster.symbol_ids)
    return sorted(seeds)


def _allowed_nodes(cluster: Cluster, seed: str, edges: set[tuple[str, str]]) -> set[str]:
    cluster_set = set(cluster.symbol_ids)
    has_internal = any(src == seed and dst in cluster_set and dst != seed for src, dst in edges)
    allowed = set(cluster_set)
    if not has_internal:
        for src, dst in edges:
            if src == seed:
                allowed.add(dst)
    return allowed


def _realize_scc_path(
    graph: nx.DiGraph,
    scc_path: list[int],
    members: Mapping[int, tuple[str, ...]],
    seed: str,
    ranks: Mapping[str, float],
    out_degree: Mapping[str, int],
) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    current: str | None = seed
    for scc_id in scc_path:
        candidates = [node for node in members[scc_id] if node not in seen]
        if not candidates:
            continue
        if current is not None and current in candidates:
            chosen = current
        else:
            adjacent = [
                node
                for node in candidates
                if current is not None and graph.has_edge(current, node)
            ]
            pool = adjacent or candidates
            chosen = max(
                pool,
                key=lambda node: (
                    ranks.get(node, 0.0),
                    out_degree.get(node, 0),
                    -len(node),
                    node,
                ),
            )
        ordered.append(chosen)
        seen.add(chosen)
        current = chosen
        if len(ordered) >= MAX_TRACE_NODES:
            break
        # Consume a second high-rank adjacent node inside a large SCC so
        # a 40-method class does not collapse to a single hop.
        extras = [
            node
            for node in members[scc_id]
            if node not in seen and graph.has_edge(chosen, node)
        ]
        extras.sort(
            key=lambda node: (
                -ranks.get(node, 0.0),
                -out_degree.get(node, 0),
                node,
            )
        )
        for extra in extras:
            if len(ordered) >= MAX_TRACE_NODES:
                break
            ordered.append(extra)
            seen.add(extra)
            current = extra
    return tuple(ordered)


def _longest_path(
    seed: str,
    allowed: set[str],
    edges: set[tuple[str, str]],
    ranks: Mapping[str, float],
    out_degree: Mapping[str, int],
) -> tuple[str, ...]:
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(allowed))
    graph.add_edges_from(
        sorted((src, dst) for src, dst in edges if src in allowed and dst in allowed and src != dst)
    )
    if seed not in graph:
        return (seed,)
    condensed = nx.condensation(graph)
    members: dict[int, tuple[str, ...]] = {}
    node_scc: dict[str, int] = {}
    for scc_id, data in condensed.nodes(data=True):
        group = tuple(sorted(data.get("members", ())))
        members[int(scc_id)] = group
        for node in group:
            node_scc[node] = int(scc_id)
    start = node_scc[seed]

    # Longest path on the SCC DAG from `start`. Score = (n_sccs, n_nodes, lexical).
    topo = list(nx.topological_sort(condensed))
    reachable = nx.descendants(condensed, start) | {start}
    best_from: dict[int, tuple[int, int, str, list[int]]] = {}
    for scc_id in reversed(topo):
        scc_id = int(scc_id)
        if scc_id not in reachable:
            continue
        succs = [int(dst) for dst in condensed.successors(scc_id) if int(dst) in reachable]
        node_count = len(members[scc_id])
        if not succs:
            best_from[scc_id] = (1, node_count, f"{scc_id:08d}", [scc_id])
            continue
        best_succ = max(
            succs,
            key=lambda dst: (
                best_from[dst][0],
                best_from[dst][1],
                best_from[dst][2],
            ),
        )
        length, nodes, lex, path = best_from[best_succ]
        best_from[scc_id] = (
            length + 1,
            nodes + node_count,
            f"{scc_id:08d}-" + lex,
            [scc_id, *path],
        )
    scc_path = best_from[start][3]
    return _realize_scc_path(graph, scc_path, members, seed, ranks, out_degree)


def _entry_name(surface: PublicSurface, seed: str) -> str | None:
    for binding in surface.bindings:
        if seed in binding.resolved_symbol_ids:
            return binding.name
    seed_tail = tail(seed)
    for binding in surface.bindings:
        if binding.name == seed_tail:
            return binding.name
    return None


def extract_cluster_traces(
    repo_root: str,
    ledger: SemanticLedger,
    surface: PublicSurface,
    clusters: tuple[Cluster, ...],
    edges: set[tuple[str, str]],
) -> FlowTraceSet:
    ranks = pagerank_scores(tuple(ledger.symbols), edges)
    out_degree = _out_degree(edges)
    preferred = _overlay_resolved(surface)
    traces: list[NamedTrace] = []

    for cluster in clusters:
        if not cluster.symbol_ids:
            traces.append(
                NamedTrace(
                    trace_id=f"cluster-{cluster.slug}",
                    title=cluster.display,
                    cluster_id=cluster.cluster_id,
                    entry_surface_id=None,
                    seed_symbol_id=None,
                    ordered_symbol_ids=(),
                    edges=(),
                    stale_nodes=(),
                    residual=cluster.unassigned_reason or "cluster has no ledger symbols",
                    selection={"rule": "placeholder", "cluster": cluster.cluster_id},
                )
            )
            continue
        candidates = _candidate_seeds(cluster, ledger, preferred, edges)
        scored: list[tuple[tuple[object, ...], str, tuple[str, ...], set[str]]] = []
        for seed in candidates:
            allowed = _allowed_nodes(cluster, seed, edges)
            ordered = _longest_path(seed, allowed, edges, ranks, out_degree)
            if ordered and ordered[0] != seed:
                ordered = (seed, *[node for node in ordered if node != seed])[:MAX_TRACE_NODES]
            score = (
                len(ordered),
                ranks.get(seed, 0.0),
                out_degree.get(seed, 0),
                -len(seed),
                seed,
            )
            scored.append((score, seed, ordered, allowed))
        scored.sort(key=lambda item: item[0], reverse=True)
        _score, seed, ordered, allowed = scored[0]
        stale = tuple(
            symbol_id for symbol_id in ordered if not ledger.symbols[symbol_id].is_fresh
        )
        residual = None
        if len(ordered) < 3:
            residual = "static call graph yielded fewer than 3 nodes"
        traces.append(
            NamedTrace(
                trace_id=f"cluster-{cluster.slug}",
                title=cluster.display,
                cluster_id=cluster.cluster_id,
                entry_surface_id=_entry_name(surface, seed),
                seed_symbol_id=seed,
                ordered_symbol_ids=ordered,
                edges=tuple(zip(ordered, ordered[1:])),
                stale_nodes=stale,
                residual=residual,
                selection={
                    "seed": seed,
                    "seed_pagerank": ranks.get(seed, 0.0),
                    "seed_out_degree": out_degree.get(seed, 0),
                    "allowed_nodes": len(allowed),
                    "n_nodes": len(ordered),
                    "n_candidate_seeds": len(candidates),
                },
            )
        )

    return FlowTraceSet(
        repo_root=repo_root,
        source_revision=ledger.source_revision,
        selection_rule=SELECTION_RULE,
        traces=tuple(traces),
    )
