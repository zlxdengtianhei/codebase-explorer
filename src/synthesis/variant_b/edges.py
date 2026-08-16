"""Call / alias edges and PageRank. Deterministic, zero LLM."""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from pathlib import Path

import networkx as nx

from src.semantic.models import SemanticLedger
from src.synthesis.variant_b.surface import PublicSurface


def probe_call_edges(repo_root: Path, ledger: SemanticLedger) -> set[tuple[str, str]]:
    """Same-file AST calls, keyed with ledger symbol ids (path::qual)."""

    known = set(ledger.symbols)
    edges: set[tuple[str, str]] = set()
    files = {record.path for record in ledger.symbols.values()}
    for relative in sorted(files):
        path = repo_root / relative
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        local_to_id: dict[str, str] = {}
        stack: list[str] = []

        def index(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    local_to_id.setdefault(child.name, f"{relative}::{'.'.join(stack)}")
                    index(child)
                    stack.pop()
                else:
                    index(child)

        index(tree)

        def collect(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    stack.append(child.name)
                    caller = f"{relative}::{'.'.join(stack)}"
                    for descendant in ast.walk(child):
                        if not isinstance(descendant, ast.Call):
                            continue
                        function = descendant.func
                        name = getattr(function, "id", None) or getattr(function, "attr", None)
                        callee = local_to_id.get(name) if name else None
                        if callee and callee != caller and caller in known and callee in known:
                            edges.add((caller, callee))
                    collect(child)
                    stack.pop()
                else:
                    collect(child)

        collect(tree)
    return edges


def citation_edges(ledger: SemanticLedger) -> set[tuple[str, str]]:
    known = set(ledger.symbols)
    edges: set[tuple[str, str]] = set()
    for symbol_id, record in ledger.symbols.items():
        if record.explanation is None:
            continue
        for cited in record.explanation.cited_symbol_ids:
            if cited in known and cited != symbol_id:
                edges.add((symbol_id, cited))
    return edges


def overlay_alias_edges(surface: PublicSurface, ledger: SemanticLedger) -> set[tuple[str, str]]:
    known = set(ledger.symbols)
    edges: set[tuple[str, str]] = set()
    for binding in surface.bindings:
        local_id = f"{binding.path}::{binding.name}"
        if local_id not in known:
            continue
        for target in binding.resolved_symbol_ids:
            if target in known and target != local_id:
                edges.add((local_id, target))
    return edges


def ir_file_edges(ir_path: Path | None, ledger: SemanticLedger) -> set[tuple[str, str]]:
    if ir_path is None or not ir_path.is_file():
        return set()
    try:
        payload = json.loads(ir_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    known = set(ledger.symbols)
    edges: set[tuple[str, str]] = set()
    for row in payload.get("relations", []):
        src, dst = str(row.get("src", "")), str(row.get("dst", ""))
        if src in known and dst in known and src != dst:
            edges.add((src, dst))
    return edges


def call_edges(
    repo_root: Path,
    ledger: SemanticLedger,
    surface: PublicSurface,
    *,
    ir_path: Path | None = None,
) -> set[tuple[str, str]]:
    return (
        probe_call_edges(repo_root, ledger)
        | ir_file_edges(ir_path, ledger)
        | overlay_alias_edges(surface, ledger)
        | citation_edges(ledger)
    )


def pagerank_scores(
    nodes: tuple[str, ...],
    edges: set[tuple[str, str]],
) -> dict[str, float]:
    """Power iteration. Avoid networkx.pagerank (it imports scipy, not in .venv)."""

    ordered = tuple(sorted(nodes))
    if not ordered:
        return {}
    index = {node: i for i, node in enumerate(ordered)}
    n = len(ordered)
    out: list[list[int]] = [[] for _ in range(n)]
    for src, dst in edges:
        if src in index and dst in index and src != dst:
            out[index[src]].append(index[dst])
    # dangling + uniform teleport, alpha=0.85, 40 iters — enough for ranking ties
    alpha = 0.85
    rank = [1.0 / n] * n
    for _ in range(40):
        nxt = [(1.0 - alpha) / n] * n
        dangling = 0.0
        for i, dests in enumerate(out):
            if not dests:
                dangling += rank[i]
                continue
            share = alpha * rank[i] / len(dests)
            for j in dests:
                nxt[j] += share
        extra = alpha * dangling / n
        rank = [value + extra for value in nxt]
    return {ordered[i]: rank[i] for i in range(n)}


def file_dag_layers(
    files: tuple[str, ...],
    symbol_path: Mapping[str, str],
    edges: set[tuple[str, str]],
) -> tuple[tuple[str, ...], ...]:
    """Topo layers of files. Layer 0 = sources (entries), last = sinks."""

    file_set = set(files)
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(files))
    for src, dst in edges:
        src_file = symbol_path.get(src)
        dst_file = symbol_path.get(dst)
        if (
            src_file in file_set
            and dst_file in file_set
            and src_file != dst_file
        ):
            graph.add_edge(src_file, dst_file)
    if graph.number_of_edges() == 0:
        return (tuple(sorted(files)),)

    condensed = nx.condensation(graph)
    mapping: dict[int, tuple[str, ...]] = {}
    for scc_id, data in condensed.nodes(data=True):
        members = tuple(sorted(data.get("members", ())))
        mapping[int(scc_id)] = members

    layers: list[tuple[str, ...]] = []
    for generation in nx.topological_generations(condensed):
        bucket: list[str] = []
        for scc_id in sorted(generation):
            bucket.extend(mapping[int(scc_id)])
        layers.append(tuple(sorted(bucket)))
    return tuple(layers)


def emit_ir_json(
    ledger: SemanticLedger,
    edges: set[tuple[str, str]],
) -> dict[str, object]:
    return {
        "symbols": [
            {"id": symbol_id, "name": record.qualified_name}
            for symbol_id, record in sorted(ledger.symbols.items())
        ],
        "relations": [
            {"src": src, "dst": dst, "kind": "call"}
            for src, dst in sorted(edges)
        ],
    }
