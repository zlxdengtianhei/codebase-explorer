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
    unmapped_cfg: int = 0
    exception_exits_exported: bool = False


def unit_graph(graph: dict, paths: list[str], inventory: dict[str, dict],
               chunks: list[dict]) -> UnitGraph:
    """Map call coordinates into inventory chunks' half-open byte ranges.

    Frozen chunk text reconstructs source coordinates, including UTF-8 columns.
    Missing coordinates or source bytes are counted rather than guessed by line.
    """
    wanted = set(paths)
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    ids = {s["id"] for entry in inventory.values() for s in entry["symbols"]}
    blocks: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        if chunk["id"] in ids:
            blocks[chunk["path"]].append(chunk)
    source_parts: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        source_parts[chunk["path"]].append(chunk)
    source_lines = {}
    for path, parts in source_parts.items():
        raw = b"".join(c.get("text", "").encode("utf-8")
                       for c in sorted(parts, key=lambda c: c.get("start_byte", 0)))
        starts = [0] + [i + 1 for i, byte in enumerate(raw) if byte == 10]
        source_lines[path] = (raw, starts)

    def at(path: str | None, line: int | None, column: int | None = None) -> str | None:
        if path not in source_lines or line is None or line < 1:
            return None
        raw, starts = source_lines[path]
        if line > len(starts):
            return None
        base = starts[line - 1]
        if column is None:
            point = base
            while point < len(raw) and raw[point] in b" \t":
                point += 1
        else:
            if column < 1:
                return None
            end = starts[line] if line < len(starts) else len(raw)
            text = raw[base:end].decode("utf-8")
            if column > len(text) + 1:
                return None
            point = base + len(text[:column - 1].encode("utf-8"))
        for chunk in blocks[path]:
            if chunk.get("start_byte", -1) <= point < chunk.get("end_byte", -1):
                assert chunk["start_byte"] <= point < chunk["end_byte"]
                return chunk["id"]
        return None

    def endpoint(node: dict) -> str | None:
        return at(node.get("path"), node.get("start_line"))

    outgoing, incoming, ambiguous = [], [], []
    dependencies: dict[str, set[str]] = defaultdict(set)
    external_calls: Counter = Counter()
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
        caller = at(path, edge.get("line"), edge.get("column"))
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
        elif status == "external" and local_source:
            external_calls[path] += 1
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
        names = ", ".join(sorted(dependencies[path])) or "none"
        rows.append(EvidenceRow("dependencies", f"External imports {path}: {names}; "
                    f"external calls={external_calls[path]}",
                    len(dependencies[path]) + external_calls[path]))
        if unresolved[path]:
            names = list(dict.fromkeys(unresolved[path]))[:5]
            rows.append(EvidenceRow("unresolved", f"Unresolved calls {path}: {len(unresolved[path])}; "
                                    + "; ".join(names), len(unresolved[path])))

    symbol_kinds = {s["id"]: s.get("kind") for entry in inventory.values() for s in entry["symbols"]}
    cfg_nodes: dict[str, list[dict]] = defaultdict(list)
    unmapped_owners = set()
    for node in nodes.values():
        if node.get("kind") == "cfg_node" and node.get("path") in wanted:
            owner = nodes.get(node.get("owner"), {})
            # All angle-bracket methods are analyzer-generated, including lambdas.
            if "<" in str(owner.get("name", "")) and ">" in str(owner.get("name", "")):
                continue
            uid = endpoint(owner)
            if uid and symbol_kinds.get(uid) in {"function", "method"}:
                cfg_nodes[uid].append(node)
            else:
                unmapped_owners.add(node.get("owner"))
    for uid, members in sorted(cfg_nodes.items()):
        controls = sum(n.get("label") == "CONTROL_STRUCTURE" for n in members)
        returns = sum(n.get("label") == "RETURN" for n in members)
        if controls or returns:
            rows.append(EvidenceRow("cfg", f"CFG {uid}: control_structures={controls}, "
                                    f"returns={returns}"))
    # A package skeleton is deliberately small; preserve its omitted pair count.
    for (left, right), count in sorted(skeleton.items())[:12]:
        rows.append(EvidenceRow("packages", f"Package imports {left} → {right}: {count}"))
    if len(skeleton) > 12:
        rows.append(EvidenceRow("packages", f"Package imports: {len(skeleton) - 12} other package pairs",
                                len(skeleton) - 12))
    if not skeleton:
        rows.append(EvidenceRow("packages", "Package imports: no resolved package links", 0))
    # Package context survives before lower-priority per-function cfg hints.
    rows.sort(key=lambda row: {"out": 0, "in": 1, "ambiguous": 2,
                              "dependencies": 3, "unresolved": 3,
                              "packages": 4, "cfg": 5}[row.category])
    return UnitGraph(tuple(rows), internal, unmapped, len(unmapped_owners),
                     any(n.get("label") == "THROW" for n in nodes.values()))


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
    suffix: list[Counter] = [Counter() for _ in range(len(rows) + 1)]
    for index in range(len(rows) - 1, -1, -1):
        suffix[index] = suffix[index + 1].copy()
        if rows[index].count:
            suffix[index][rows[index].category] += rows[index].count

    def render(keep: int) -> str:
        omitted = suffix[keep]
        lines = ["LOCAL GRAPH EVIDENCE (unit ids; dependencies count import names + external call sites; graph evidence is not proof of behavior).",
                 f"Batch-internal resolved calls: {evidence.internal_calls} (source visible); "
                 f"unmapped resolved calls: {evidence.unmapped_calls}; "
                 f"unmapped cfg owners: {evidence.unmapped_cfg}."
                 + ("" if evidence.exception_exits_exported else
                    " exception exits are not exported by this graph.")]
        lines += render_rows(rows[:keep])
        lines.append("Omitted: " + (", ".join(f"{k}={v}" for k, v in sorted(omitted.items())) or "none")
                     + ". Omitted evidence is unavailable in this excerpt.")
        return "\n".join(lines)

    text = render(len(rows))
    if budget is None or count_text_tokens(text) <= budget:
        return text
    low, high = 0, len(rows) - 1
    best = ""
    while low <= high:
        middle = (low + high) // 2
        candidate = render(middle)
        if count_text_tokens(candidate) <= budget:
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    if best:
        return best
    text = (f"Graph: internal={evidence.internal_calls}, unmapped={evidence.unmapped_calls}, "
            f"unmapped_cfg={evidence.unmapped_cfg}; omitted "
            + ",".join(f"{k}={v}" for k, v in sorted(suffix[0].items()))
            + "; dependencies unit=import names + external call sites"
            + ("" if evidence.exception_exits_exported else
               "; exception exits are not exported by this graph"))
    return text if count_text_tokens(text) <= budget else ""


def graph_prompt_lines(graph: Any, paths: list[str], *, embed: bool,
                       inventory: dict[str, dict] | None = None,
                       chunks: list[dict] | None = None,
                       source_tokens: int | None = DEFAULT_GRAPH_MAX_TOKENS,
                       max_tokens: int | None = DEFAULT_GRAPH_MAX_TOKENS,
                       graph_file: str | None = None) -> list[str]:
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
    limits = [limit for limit in (max_tokens, source_tokens) if limit is not None]
    budget = max(0, min(limits)) if limits else None
    text = graph_text(evidence, budget=budget)
    if text:
        access = []
        if budget is not None:
            if embed:
                access = ["Graph access: this completion is tool-free; omitted evidence cannot be inspected.", ""]
            elif graph_file:
                access = [f"Graph access: Read the complete evidence for this batch at {graph_file}", ""]
        return access + [text, ""]
    # Like absent/failed graph notices, this is status, not relation payload.
    # A hard zero/tiny payload cap must never imply there were no relations.
    omitted = Counter()
    for row in evidence.rows:
        if row.count:
            omitted[row.category] += row.count
    notice = (f"GRAPH STATUS (outside payload cap): budget={budget} tokens; omitted "
              + ",".join(f"{kind}={count}" for kind, count in sorted(omitted.items()))
              + f"; internal={evidence.internal_calls}; unmapped={evidence.unmapped_calls}; "
              + f"unmapped_cfg={evidence.unmapped_cfg}; dependencies unit=import names + external call sites."
              + ("" if evidence.exception_exits_exported else
                 " exception exits are not exported by this graph."))
    if not embed and graph_file:
        notice += f" Read full evidence: {graph_file}"
    return [notice, ""]
