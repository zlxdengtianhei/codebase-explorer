"""The graph evidence one detail author sees: a bounded, deterministic projection.

The complete graph stays in the frozen ``context.json``. A projection keeps
both endpoints of every included relation, reports what it omitted, and is
never a second graph or scheduler.
"""

from __future__ import annotations

import json
import shlex
import sys
from typing import Any


#: The prompt-facing schema. It is a bounded projection of ``cbe-graph/1``, not a new graph.
GRAPH_PROJECTION_SCHEMA = "cbe-graph-projection/1"
#: Default prompt budget. The complete graph stays in the frozen ``context.json``;
#: these caps only bound what one completion sees, with explicit omission counts.
DEFAULT_GRAPH_MAX_NODES = 200
DEFAULT_GRAPH_MAX_EDGES = 320
#: Semantic relations are included before structural ones, and resolved before
#: unresolved, so a budget cut never silently drops the import/call evidence.
_GRAPH_KIND_PRIORITY = {"import": 0, "call": 1, "cfg": 2, "dataflow": 3}
_GRAPH_STATUS_PRIORITY = {"resolved": 0, "ambiguous": 1, "unresolved": 2, "external": 3,
                          "unsupported": 4}
_SEMANTIC_GRAPH_KINDS = ("import", "call")
_STRUCTURAL_GRAPH_KINDS = ("cfg", "dataflow")


def graph_state(graph: Any) -> tuple[str, str]:
    """Classify a graph as one of ``absent|unsupported|failed|empty|provided``.

    An empty graph is a verified result, not a missing graph, and is never
    reported as "not provided". """
    if graph is None:
        return "absent", "no graph was provided for this run"
    if not isinstance(graph, dict) or graph.get("schema") != "cbe-graph/1":
        found = graph.get("schema") if isinstance(graph, dict) else type(graph).__name__
        return "unsupported", f"graph schema is {found!r}, expected 'cbe-graph/1'"
    nodes = [node for node in graph.get("nodes") or [] if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]
    if nodes or edges:
        return "provided", f"{len(nodes)} nodes, {len(edges)} edges"
    statuses = {str(cap.get("status")) for cap in graph.get("capabilities") or []
                if isinstance(cap, dict) and cap.get("status")}
    if statuses & {"failed", "unavailable"}:
        return "failed", "backend failed or was unavailable"
    if "unsupported" in statuses and not (statuses & {"resolved", "partial", "empty"}):
        return "unsupported", "no requested language/graph type is supported"
    diagnostics = {row.get("code") for row in graph.get("diagnostics") or []
                   if isinstance(row, dict)}
    if "no_language_requested" in diagnostics or (
            "analyzed_languages" in graph and not graph["analyzed_languages"]):
        return "unsupported", "no language was selected for analysis"
    if "no_backend_completed" in diagnostics:
        return "failed", "no backend completed; the empty graph is not authoritative"
    return "empty", "the analyzer ran and found no relation"


def _compact_graph_node(node: dict) -> dict:
    out: dict[str, Any] = {"id": node.get("id"), "kind": node.get("kind"),
                           "name": node.get("name")}
    if node.get("path"):
        out["path"] = node["path"]
        out["lines"] = [node.get("start_line"), node.get("end_line")]
    else:
        out["boundary"] = True
    for key in ("owner", "label"):
        if node.get(key) and node.get(key) != node.get("name"):
            out[key] = node[key]
    return out


def _compact_graph_edge(edge: dict) -> dict:
    out: dict[str, Any] = {"id": edge.get("id"), "source": edge.get("source"),
                           "target": edge.get("target"), "kind": edge.get("kind"),
                           "status": edge.get("status")}
    for key in ("path", "line", "expression", "target_expression", "method_full_name", "owner"):
        if edge.get(key) is not None:
            out[key] = edge[key]
    candidates = edge.get("candidates")
    if isinstance(candidates, list) and candidates:
        out["candidates"] = candidates[:8]
        out["candidate_count"] = len(candidates)
    return out


def project_graph(graph: Any, paths: list[str], *, max_nodes: int = DEFAULT_GRAPH_MAX_NODES,
                  max_edges: int = DEFAULT_GRAPH_MAX_EDGES) -> dict[str, Any]:
    """Bounded, deterministic, referentially closed projection for one prompt.

    Every included relation keeps both endpoints, even a boundary node outside
    the requested paths, so no selected edge dangles. Import/call edges are
    taken first; cfg/dataflow edges are sampled deterministically by edge id and
    labeled as such. Counts of total/selected/omitted are always reported. This
    is a projection, never a second graph or scheduler."""
    state, detail = graph_state(graph)
    result: dict[str, Any] = {
        "schema": GRAPH_PROJECTION_SCHEMA, "state": state, "state_detail": detail,
        "scope": {"paths": sorted(set(paths)), "direction": "both",
                  "relation_scope": "incident_to_paths",
                  "boundary_endpoints_retained": True},
    }
    if state in {"absent", "unsupported", "failed"}:
        return result
    nodes = [node for node in graph.get("nodes") or [] if isinstance(node, dict) and node.get("id")]
    edges = [edge for edge in graph.get("edges") or [] if isinstance(edge, dict)]
    by_id = {node["id"]: node for node in nodes}
    result["backend"] = graph.get("backend")
    result["capabilities"] = list(graph.get("capabilities") or [])
    result["diagnostics"] = list(graph.get("diagnostics") or [])[:20]
    provenance = graph.get("provenance")
    if isinstance(provenance, dict):
        result["provenance"] = {key: provenance[key] for key in
                                ("source_stable", "config_stable", "analyzed_languages", "fingerprint")
                                if key in provenance}
    selected_paths = set(paths)
    path_node_ids = {node["id"] for node in nodes if node.get("path") in selected_paths}
    if not path_node_ids:
        result["state"] = "no_local_nodes"
        result["counts"] = {"nodes_total": len(nodes), "edges_total": len(edges),
                            "nodes_selected": 0, "edges_selected": 0,
                            "edges_in_scope": 0}
        return result

    incident = [edge for edge in edges
                if edge.get("source") in path_node_ids or edge.get("target") in path_node_ids]

    def edge_rank(edge: dict) -> tuple:
        return (_GRAPH_KIND_PRIORITY.get(edge.get("kind"), 9),
                _GRAPH_STATUS_PRIORITY.get(edge.get("status"), 9), str(edge.get("id")))

    ranked = sorted(incident, key=edge_rank)
    selected_nodes: dict[str, dict] = {}
    selected_edges: list[dict] = []
    omitted_by_kind: dict[str, int] = {}
    omitted_missing_endpoint = 0
    # Relations first, in priority order: a semantic edge and both its endpoints
    # are taken before any structural node, so a budget cut can never drop
    # import/call evidence in favour of CFG blocks.
    for edge in ranked:
        if len(selected_edges) >= max_edges:
            omitted_by_kind[edge.get("kind")] = omitted_by_kind.get(edge.get("kind"), 0) + 1
            continue
        endpoints = [edge.get("source"), edge.get("target")]
        if any(endpoint and endpoint not in by_id for endpoint in endpoints):
            omitted_missing_endpoint += 1  # never emit a dangling edge
            continue
        missing = [endpoint for endpoint in endpoints if endpoint and endpoint not in selected_nodes]
        if len(selected_nodes) + len(set(missing)) > max_nodes:
            omitted_by_kind[edge.get("kind")] = omitted_by_kind.get(edge.get("kind"), 0) + 1
            continue
        for endpoint in missing:
            selected_nodes[endpoint] = _compact_graph_node(by_id[endpoint])
        selected_edges.append(_compact_graph_edge(edge))
    # Then any remaining reading-scope node, so a file/function with no edge is
    # still visible, without ever displacing a relation.
    for node_id in sorted(path_node_ids, key=lambda item: (by_id[item].get("path") or "",
                                                           by_id[item].get("start_line") or 0, item)):
        if len(selected_nodes) >= max_nodes:
            break
        selected_nodes.setdefault(node_id, _compact_graph_node(by_id[node_id]))

    by_kind: dict[str, dict[str, int]] = {}
    for kind in ("import", "call", "cfg", "dataflow"):
        scope = [edge for edge in incident if edge.get("kind") == kind]
        chosen = sum(1 for edge in selected_edges if edge.get("kind") == kind)
        if scope or chosen:
            by_kind[kind] = {"in_scope": len(scope), "selected": chosen,
                             "omitted": len(scope) - chosen}
    semantic_omitted = sum(omitted_by_kind.get(kind, 0) for kind in _SEMANTIC_GRAPH_KINDS)
    aggregation: dict[str, dict[str, dict[str, int]]] = {}
    for kind in _STRUCTURAL_GRAPH_KINDS:
        scope = [edge for edge in incident if edge.get("kind") == kind]
        if not scope:
            continue
        owners: dict[str, dict[str, int]] = {}
        chosen_ids = {edge.get("id") for edge in selected_edges}
        for edge in scope:
            owner = edge.get("owner")
            if not owner:
                source_node = by_id.get(edge.get("source")) or {}
                owner = source_node.get("owner") or edge.get("path") or source_node.get("path") or "<unknown>"
            row = owners.setdefault(owner, {"in_scope": 0, "selected": 0})
            row["in_scope"] += 1
            if edge.get("id") in chosen_ids:
                row["selected"] += 1
        aggregation[kind] = dict(sorted(owners.items())[:50])

    result["nodes"] = sorted(selected_nodes.values(),
                             key=lambda node: (node.get("path") or "", node.get("kind") or "",
                                               node.get("lines") or [0, 0], node.get("id") or ""))
    result["edges"] = selected_edges
    result["counts"] = {
        "nodes_total": len(nodes), "nodes_selected": len(selected_nodes),
        "nodes_omitted": len(nodes) - len(selected_nodes),
        "edges_total": len(edges), "edges_in_scope": len(incident),
        "edges_selected": len(selected_edges),
        "edges_omitted": len(incident) - len(selected_edges),
        "edges_omitted_by_kind": {kind: count for kind, count in omitted_by_kind.items() if count},
        "edges_omitted_missing_endpoint": omitted_missing_endpoint,
        "by_kind": by_kind,
    }
    result["sampling"] = {
        "priority": "import/call before cfg/dataflow; resolved before unresolved; then edge id",
        "import_call": ("all included" if semantic_omitted == 0 else
                        f"{semantic_omitted} import/call edge(s) omitted after the budget"),
        "cfg_dataflow": "deterministically sampled by edge id; not a representative subset",
        "aggregation": "cfg/dataflow in_scope/selected counts per owner" if aggregation else None,
    }
    if aggregation:
        result["cfg_dataflow_by_owner"] = aggregation
    return result


def graph_prompt_lines(graph: Any, paths: list[str], *, embed: bool,
                       expand_context_path: str | None = None,
                       max_nodes: int = DEFAULT_GRAPH_MAX_NODES,
                       max_edges: int = DEFAULT_GRAPH_MAX_EDGES) -> list[str]:
    """Prompt body lines that state the graph state and, when present, a bounded
    deterministic projection with explicit omissions and a host expansion path."""
    state, detail = graph_state(graph)
    if state == "absent":
        return ["GRAPH: not provided for this run. Do not infer imports, calls or data flow; state the "
                "boundary in 'uncertainties' when a relation would matter.", ""]
    if state == "unsupported":
        return [f"GRAPH: unsupported for this run ({detail}). Do not infer relations from the graph; "
                "state unproven boundaries in 'uncertainties'.", ""]
    if state == "failed":
        return [f"GRAPH: analysis failed or was unavailable ({detail}). Treat relations as unknown, not "
                "absent, and do not invent them.", ""]
    if state == "empty":
        return ["GRAPH: provided and successfully empty (the analyzer ran and found no node or relation). "
                "An empty graph is a verified result, not a missing graph; still state any unproven boundary.", ""]
    projection = project_graph(graph, paths, max_nodes=max_nodes, max_edges=max_edges)
    if projection.get("state") == "no_local_nodes":
        return [f"GRAPH: provided for this run ({detail}) but no graph node anchors the listed file(s). This is "
                "not an empty graph and not a missing graph: the analyzer produced no symbol node for these "
                "paths. Do not infer either the presence or the absence of relations from it; keep unproven "
                "boundaries in 'uncertainties'.", ""]
    counts = projection["counts"]
    omitted = counts["edges_omitted_by_kind"] or "none"
    lines = [
        "LOCAL GRAPH EVIDENCE (a deterministic projection of the frozen full graph; an edge is evidence, "
        "not proof of behavior). Boundary nodes outside the listed files are kept so every included relation "
        "stays resolvable.",
        f"Scope: relations incident to {sorted(set(paths))}. Totals {counts['nodes_total']} nodes / "
        f"{counts['edges_total']} edges; included {counts['nodes_selected']} nodes / {counts['edges_selected']} "
        f"edges; omitted {counts['edges_omitted']} incident edge(s) by kind: {omitted}. "
        "Import/call relations are prioritized; CFG/dataflow edges are deterministically sampled by edge id and "
        "are not a representative subset; the omitted edges are not shown and their absence is not evidence.",
    ]
    if embed:
        lines.append("This completion is tool-free: you cannot query the frozen graph, so the projection "
                     "below is the only relation evidence available. Do not claim to have inspected an "
                     "omitted edge.")
    elif expand_context_path:
        command = shlex.join([
            sys.executable, "-m", "cbe", "graph", "query", "--graph", expand_context_path,
            "--path", sorted(set(paths))[0], "--kind", "call", "--direction", "both",
        ])
        lines.append("To expand an omitted relation, run: " + command)
        lines.append("You may replace --path with another listed path and --kind with import, cfg, or "
                     "dataflow. Read only the returned slice; the query does not execute repository code.")
    lines += [json.dumps(projection, ensure_ascii=False), ""]
    return lines
