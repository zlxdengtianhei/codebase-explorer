"""Unit-level graph evidence for detail authors, shared by both drivers.

The inventory defines identity; chunks define call-site ownership. Rendering and
budget selection live here so host files and all detail/review/repair prompts
cannot acquire different projection rules.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from cbe.token_budget import count_text_tokens

DEFAULT_GRAPH_MAX_TOKENS = 3000


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


@dataclass(frozen=True)
class EvidenceRow:
    category: str
    text: str
    count: int = 1


@dataclass(frozen=True)
class UnitGraph:
    """Unbounded rows in priority order, plus non-optional mapping accounting."""
    rows: tuple[EvidenceRow, ...]
    internal_calls: int
    unmapped_calls: int


def unit_graph(graph: dict, paths: list[str], inventory: dict[str, dict],
               chunks: list[dict]) -> UnitGraph:
    """Map call sites only through chunks whose ids occur in the inventory.

    Source endpoints use edge.path/line, never the enclosing Joern method.
    Targets use the callee definition line. Split chunks retain their own ids.
    An unmappable resolved call is counted explicitly, never silently dropped.
    """
    wanted = set(paths)
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    ids = {s["id"] for entry in inventory.values() for s in entry["symbols"]}
    blocks: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        if chunk["id"] in ids:
            blocks[chunk["path"]].append(chunk)
    for rows in blocks.values():
        rows.sort(key=lambda c: (c["end_line"] - c["start_line"], c["start_line"], c["id"]))

    def at(path: str | None, line: int | None) -> str | None:
        if path and line is not None:
            for chunk in blocks[path]:
                if chunk["start_line"] <= line <= chunk["end_line"]:
                    return chunk["id"]
        return None

    def endpoint(node: dict) -> str | None:
        return at(node.get("path"), node.get("start_line"))

    outgoing, incoming, ambiguous = [], [], []
    dependencies: dict[str, set[str]] = defaultdict(set)
    unresolved: dict[str, list[str]] = defaultdict(list)
    skeleton: Counter = Counter()
    internal = unmapped = 0
    for edge in sorted(graph.get("edges", []), key=lambda e: str(e.get("id", ""))):
        source = nodes.get(edge.get("source"), {})
        target = nodes.get(edge.get("target"), {})
        path = edge.get("path") or source.get("path")
        target_path = target.get("path")
        local_source, local_target = path in wanted, target_path in wanted
        if edge.get("kind") == "import":
            if edge.get("status") == "external" and local_source:
                dependencies[path].add(str(target.get("name") or edge.get("target_expression")
                                           or edge.get("expression") or "unknown"))
            if edge.get("status") == "resolved" and path and target_path:
                left = path.rpartition("/")[0] or "."
                right = target_path.rpartition("/")[0] or "."
                skeleton[left, right] += 1
            continue
        if edge.get("kind") != "call" or not (local_source or local_target):
            continue
        caller = at(path, edge.get("line"))
        callee = endpoint(target)
        status = edge.get("status")
        if status == "resolved":
            if not caller or not callee:
                unmapped += 1
                continue
            if local_source and local_target:
                internal += 1
            elif local_source:
                outgoing.append((caller, callee, target_path, target.get("start_line")))
            else:
                incoming.append((callee, caller, path, edge.get("line")))
        elif status == "ambiguous":
            candidates = []
            for candidate in (edge.get("candidates") or [])[:3]:
                node = nodes.get(candidate, {}) if isinstance(candidate, str) else candidate
                candidates.append(endpoint(node) or str(node.get("name") or candidate))
            ambiguous.append(EvidenceRow("ambiguous", f"? {caller or path}: "
                f"{edge.get('expression') or edge.get('target_expression') or '?'} => "
                + "; ".join(candidates) + f" ({len(edge.get('candidates') or [])} candidates)"))
        elif status == "unresolved" and local_source:
            expression = str(edge.get("target_expression") or edge.get("expression") or "?")
            unresolved[path].append(expression.split("(", 1)[0].strip()[:80])

    rows: list[EvidenceRow] = []
    # Group by caller/callee without duplicating an inventory id for every site.
    # Repeated sites remain counted even if their endpoint pair is the same.
    for category, arrow, relations in (("out", "→", outgoing), ("in", "←", incoming)):
        grouped: dict[tuple, Counter] = defaultdict(Counter)
        for local, remote, remote_path, line in relations:
            grouped[local][remote, remote_path, line] += 1
        for local, destinations in sorted(grouped.items()):
            for (remote, remote_path, line), count in sorted(destinations.items()):
                # Each row is independently truncatable; repeated local ids are
                # compressed by render_rows below, keeping omission counts exact.
                rows.append(EvidenceRow(category, f"{local} {arrow} {remote} ({remote_path}:{line})"
                                         + (f" ×{count}" if count > 1 else ""), count))
    rows += sorted(ambiguous, key=lambda r: r.text)
    for path in sorted(wanted):
        rows.append(EvidenceRow("dependencies", f"External imports {path}: "
                    + ", ".join(sorted(dependencies[path])) if dependencies[path]
                    else f"External imports {path}: none"))
        if unresolved[path]:
            names = list(dict.fromkeys(unresolved[path]))[:5]
            rows.append(EvidenceRow("unresolved", f"Unresolved calls {path}: {len(unresolved[path])}; "
                                    + "; ".join(names), len(unresolved[path])))

    symbol_kinds = {s["id"]: s.get("kind") for entry in inventory.values() for s in entry["symbols"]}
    cfg_nodes: dict[str, list[dict]] = defaultdict(list)
    for node in nodes.values():
        if node.get("kind") == "cfg_node" and node.get("path") in wanted:
            uid = endpoint(nodes.get(node.get("owner"), {}))
            if uid and symbol_kinds.get(uid) in {"function", "method"}:
                cfg_nodes[uid].append(node)
    for uid, members in sorted(cfg_nodes.items()):
        controls = sum(n.get("label") == "CONTROL_STRUCTURE" for n in members)
        returns = sum(n.get("label") == "RETURN" for n in members)
        throws = sum(n.get("label") == "THROW" for n in members)
        last = max((n.get("start_line") or 0 for n in members
                    if n.get("label") not in {"METHOD", "METHOD_RETURN"}), default=0)
        early = sum(n.get("label") == "RETURN" and (n.get("start_line") or last) < last
                    for n in members)
        if controls or returns or throws:
            rows.append(EvidenceRow("cfg", f"CFG {uid}: control_structures={controls}, "
                        f"returns={returns}, early_returns_by_line={early}, explicit_throw_exits={throws}; "
                        "other exception exits unknown"))
    # A package skeleton is deliberately small; preserve its omitted pair count.
    for (left, right), count in sorted(skeleton.items())[:12]:
        rows.append(EvidenceRow("packages", f"Package imports {left} → {right}: {count}"))
    if len(skeleton) > 12:
        rows.append(EvidenceRow("packages", f"Package imports: {len(skeleton) - 12} other package pairs"))
    if not skeleton:
        rows.append(EvidenceRow("packages", "Package imports: no resolved package links"))
    return UnitGraph(tuple(rows), internal, unmapped)


def render_rows(rows: list[EvidenceRow]) -> list[str]:
    """Group adjacent relations by local inventory id, without new identities."""
    lines: list[str] = []
    previous = None
    for row in rows:
        if row.category in {"out", "in"}:
            arrow = " → " if row.category == "out" else " ← "
            local, remote = row.text.split(arrow, 1)
            key = row.category, local
            if previous == key:
                lines.append("  " + arrow.strip() + " " + remote)
            else:
                lines.append(row.text)
            previous = key
        else:
            lines.append(row.text)
            previous = None
    return lines


def graph_text(evidence: UnitGraph, *, budget: int | None = None) -> str:
    """Drop a suffix in reverse priority, accounting for every omitted relation.

    The notice itself participates in token accounting. Full host files use
    budget=None and the exact same rows. No dataflow nodes are ever rendered.
    """
    rows = list(evidence.rows)
    omitted: Counter = Counter()
    while True:
        lines = ["LOCAL GRAPH EVIDENCE (unit ids; graph evidence is not proof of behavior).",
                 f"Batch-internal resolved calls: {evidence.internal_calls} (source visible); "
                 f"unmapped resolved calls: {evidence.unmapped_calls}."]
        lines += render_rows(rows)
        lines.append("Omitted: " + (", ".join(f"{k}={v}" for k, v in sorted(omitted.items())) or "none")
                     + ". Omitted evidence is unavailable in this excerpt.")
        text = "\n".join(lines)
        if budget is None or count_text_tokens(text) <= budget:
            return text
        if not rows:
            # Very small/empty sources cannot carry the normal explanatory
            # header. Keep numeric accounting before prose, still within budget.
            text = (f"Graph: internal={evidence.internal_calls}, unmapped={evidence.unmapped_calls}; "
                    "omitted " + ",".join(f"{k}={v}" for k, v in sorted(omitted.items())))
            if count_text_tokens(text) <= budget:
                return text
            return ""  # zero/tiny source budget: no graph payload can fit
        row = rows.pop()
        omitted[row.category] += row.count


def graph_prompt_lines(graph: Any, paths: list[str], *, embed: bool,
                       inventory: dict[str, dict] | None = None,
                       chunks: list[dict] | None = None,
                       source_tokens: int = DEFAULT_GRAPH_MAX_TOKENS,
                       max_tokens: int = DEFAULT_GRAPH_MAX_TOKENS) -> list[str]:
    """Status notices retain their original meanings; provided evidence is bounded."""
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
    if not any(n.get("path") in set(paths) for n in graph.get("nodes", [])):
        return [f"GRAPH: provided for this run ({detail}) but no graph node anchors the listed file(s). This is "
                "not an empty graph and not a missing graph: the analyzer produced no symbol node for these "
                "paths. Do not infer either the presence or the absence of relations from it; keep unproven "
                "boundaries in 'uncertainties'.", ""]
    evidence = unit_graph(graph, paths, inventory or {}, chunks or [])
    text = graph_text(evidence, budget=max(0, min(max_tokens, source_tokens)))
    return [text, ""] if text else []
