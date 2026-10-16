"""Bounded responsibility aggregation: summaries, resolved graph and candidate regions.

Regions are scheduling boundaries, not semantic modules. Only the model chooses
responsibilities; composition preserves each accepted subtree verbatim apart from
namespacing ids and attaching its root to the chosen upper-level owner.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
import os
from pathlib import PurePosixPath

from cbe.records import build_records, frozen_sources, summary_sentence
from cbe.docs import unit_ranges
from cbe.token_budget import count_text_tokens


@dataclass(frozen=True)
class Limits:
    max_units: int = 300
    max_tokens: int = 64000

    @classmethod
    def configured(cls):
        defaults = cls()
        values = {key: int(os.environ.get(env, getattr(defaults, key))) for key, env in
                  (("max_units", "CBE_TREE_MAX_UNITS"), ("max_tokens", "CBE_TREE_MAX_TOKENS"))}
        if min(values.values()) < 1:
            raise ValueError("tree aggregation limits must be positive")
        return cls(**values)


def digest(unit: dict) -> dict:
    return {"id": unit.get("id"), "kind": unit.get("kind"),
            "summary": summary_sentence(unit),
            "ranges": unit.get("ranges") or unit.get("primary_range") or []}


def inputs(units: dict, dispositions: dict, inventory: dict, context: dict) -> tuple[dict, list[dict]]:
    """Use the same source-coordinate ownership as the published catalog."""
    ranges = {uid: unit_ranges(uid, unit, inventory) for uid, unit in units.items()}
    edge_table = {}
    records, _ = build_records(
        units, dispositions, inventory, ranges, frozen_sources(context, list(inventory)),
        {f["path"]: f.get("language", "unknown") for f in context.get("files", [])},
        context, context.get("graph"), edge_table)
    owners = {sid: uid for uid, row in records.items()
              for sid in [uid] + row.get("folded_members", [])}
    counts = Counter()
    for edge in edge_table.values():
        source, target = owners.get(edge.get("source_symbol")), owners.get(edge.get("target_symbol"))
        if edge.get("status") == "resolved" and source and target and source != target:
            counts[source, target, edge["kind"]] += 1
    # File-level imports without two source-coordinate unit owners are not
    # unit edges. They are consumed separately by partition(), never attributed
    # to an arbitrary function in the imported file.
    for uid, unit in units.items():
        for relation in unit.get("relations") or []:
            target = owners.get(relation.get("target"))
            if target and target != uid:
                counts[uid, target, "relation"] += 1
    return records, [{"from": a, "to": b, "kind": kind, "count": n,
                      **({"provenance": "model_inferred"} if kind == "relation" else {})}
                     for (a, b, kind), n in sorted(counts.items())]


def region_edges(edges: list[dict], membership: dict[str, str]) -> list[dict]:
    counts = Counter()
    for e in edges:
        a, b = membership.get(e["from"]), membership.get(e["to"])
        if a and b and a != b:
            counts[a, b, e["kind"]] += e["count"]
    return [{"from": a, "to": b, "kind": k, "count": n,
             **({"provenance": "model_inferred"} if k == "relation" else {})}
            for (a, b, k), n in sorted(counts.items())]


def relationship_view(tree: dict, edges: list[dict], graph: dict | None, *, graph_only_limit: int = 40) -> dict:
    """Compare exact node pairs; containment does not imply a dependency.

    Direct primary ownership is shared with region rollup. Ancestor/descendant
    pairs remain literal pairs, never expand to all descendants. Only resolved
    call/import inputs are graph evidence; model relations are excluded.
    """
    from cbe.graph import graph_state

    state, reason = graph_state(graph)
    membership = {uid: n["id"] for n in tree.get("nodes", []) for uid in n.get("unit_ids", [])}
    resolved = [e for e in edges if e["kind"] in {"call", "import"}
                and e.get("provenance") != "model_inferred"] if state == "provided" else []
    counts = Counter()
    kinds = defaultdict(Counter)
    for edge in region_edges(resolved, membership):
        pair = edge["from"], edge["to"]
        counts[pair] += edge["count"]
        kinds[pair][edge["kind"]] += edge["count"]
    node_ids = {n["id"] for n in tree.get("nodes", [])}
    model = {(e["from"], e["to"]): e.get("basis", "") for e in tree.get("depends_on", [])
             if e.get("from") in node_ids and e.get("to") in node_ids and e["from"] != e["to"]}
    graph_only = sorted(counts.keys() - model.keys(), key=lambda p: (-counts[p], p))
    pairs = sorted(model) + graph_only[:graph_only_limit]
    dependencies = [{"from": a, "to": b,
                     "source": "graph_confirmed" if (a, b) in counts and (a, b) in model else
                               "model_inferred" if (a, b) in model else "graph_only",
                     "count": counts[a, b], "kinds": dict(sorted(kinds[a, b].items())),
                     "basis": model.get((a, b), ""), "description": ""} for a, b in pairs]
    totals = {source: sum(e["source"] == source for e in dependencies)
              for source in ("graph_confirmed", "model_inferred", "graph_only")}
    totals["graph_only"] = len(graph_only)
    return {"dependencies": dependencies, "counts": totals,
            "graph_only_omitted": max(0, len(graph_only) - graph_only_limit),
            "graph_state": state, "graph_reason": reason,
            "candidate_flows": candidate_flows(resolved)}


def candidate_flows(edges: list[dict], *, max_entries: int = 12, max_depth: int = 6,
                    max_flows: int = 24) -> list[list[str]]:
    """Stable bounded DFS from zero-incoming units, ranked by outgoing count.

    Depth counts units (six steps). Cycles end at the last unique unit. Pure
    cyclic components have no entry and intentionally yield no candidates.
    """
    adjacency = defaultdict(Counter)
    incoming = set()
    for e in edges:
        if e["kind"] == "call" and e.get("provenance") != "model_inferred" and e["from"] != e["to"]:
            adjacency[e["from"]][e["to"]] += e["count"]
            incoming.add(e["to"])
    entries = sorted(adjacency.keys() - incoming,
                     key=lambda uid: (-sum(adjacency[uid].values()), uid))[:max_entries]
    result = []
    def visit(path):
        if len(result) >= max_flows:
            return
        targets = sorted((uid for uid in adjacency[path[-1]] if uid not in path),
                         key=lambda uid: (-adjacency[path[-1]][uid], uid))
        if len(path) >= max_depth or not targets:
            if len(path) > 1:
                result.append(path)
            return
        for uid in targets:
            if len(result) >= max_flows:
                break
            visit(path + [uid])
    for uid in entries:
        visit([uid])
    return result


def annotate_relationships(view: dict, system: dict, edges: list[dict]) -> dict:
    """Publish model prose separately from the program's evidence labels."""
    descriptions = {(e["from"], e["to"]): e["description"]
                    for e in system.get("dependency_descriptions", [])}
    calls = {(e["from"], e["to"]) for e in edges if e["kind"] == "call"
             and e.get("provenance") != "model_inferred"} if view["graph_state"] == "provided" else set()
    flows = []
    for flow in system.get("key_flows", []):
        steps = flow["steps"]
        flows.append({**flow, "inferred_steps": [i for i in range(1, len(steps))
                                                if (steps[i-1], steps[i]) not in calls]})
    return {**view, "dependencies": [{**e, "description": descriptions.get((e["from"], e["to"]), "")}
                                      for e in view["dependencies"]], "key_flows": flows}


def partition(units: dict, edges: list[dict], limits: Limits, prompt, *, context: dict | None = None) -> list[dict]:
    """Pack indivisible files into balanced regions, then measure exact prompts.

    Incremental weights guide packing; only complete candidate prompts are
    rendered. Unit count is a soft ceiling for an indivisible file; tokens are
    a hard ceiling. A file that cannot fit fails with a configurable remedy.
    """
    if len(units) <= limits.max_units and count_text_tokens(prompt(units, edges)) <= limits.max_tokens:
        return []
    files = defaultdict(list)
    for uid, unit in sorted(units.items()):
        ranges = unit.get("ranges") or []
        paths = sorted({r["path"] for r in ranges}) or [uid.split("::", 1)[0].removeprefix("grp:")]
        files[paths[0]].append(uid)
    # Multi-file units join their files into one atomic component.
    parent = {path: path for path in files}
    def find(path):
        parent.setdefault(path, path)
        while parent[path] != path:
            parent[path] = parent[parent[path]]
            path = parent[path]
        return path
    for uid, unit in units.items():
        paths = sorted({r["path"] for r in unit.get("ranges", [])})
        for path in paths[1:]:
            parent[find(path)] = find(paths[0])
    blocks = defaultdict(list)
    for path, ids in files.items():
        blocks[find(path)].extend(ids)
    directory_index = defaultdict(set)
    for path in blocks:
        directory_index[str(PurePosixPath(path).parent)].add(path)
    paths = [path for directory in sorted(directory_index) for path in sorted(directory_index[directory])]
    overhead = count_text_tokens(prompt({}, []))
    weights = {path: sum(count_text_tokens(json.dumps(digest(units[uid]), ensure_ascii=False)) + 2
                         for uid in blocks[path]) for path in paths}
    # Account for edges once at their endpoints, avoiding repeated full renders.
    owner = {uid: path for path in paths for uid in blocks[path]}
    adjacency = defaultdict(Counter)
    for edge in edges:
        a, b = owner.get(edge["from"]), owner.get(edge["to"])
        if a and b:
            cost = count_text_tokens(json.dumps(edge, ensure_ascii=False)) + 2
            weights[a] += cost
            adjacency[a][b] += edge["count"]
            adjacency[b][a] += edge["count"]
    graph = (context or {}).get("graph") or {}
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    for edge in graph.get("edges", []):
        if edge.get("kind") == "import" and edge.get("status") == "resolved":
            a = nodes.get(edge.get("source"), {}).get("path")
            b = nodes.get(edge.get("target"), {}).get("path")
            if a in parent and b in parent:
                a, b = find(a), find(b)
                adjacency[a][b] += 1
                adjacency[b][a] += 1
    def measured(selected):
        ids = {uid for path in selected for uid in blocks[path]}
        return sorted(ids), count_text_tokens(prompt({uid: units[uid] for uid in sorted(ids)},
            [e for e in edges if e["from"] in ids and e["to"] in ids]))
    if overhead >= limits.max_tokens:
        raise ValueError("tree prompt rules exceed token budget; increase CBE_TREE_MAX_TOKENS")
    for path in paths:
        if overhead + weights[path] > limits.max_tokens:
            _, size = measured([path])
            if size > limits.max_tokens:
                raise ValueError(f"single tree summary file block exceeds token budget: {path} ({size}); "
                                 "increase CBE_TREE_MAX_TOKENS; files cannot be split")
    count = max(2, math.ceil(len(units) / limits.max_units),
                math.ceil(sum(weights.values()) / (limits.max_tokens - overhead)))
    count = min(count, len(paths))
    while True:
        groups = [[] for _ in range(count)]
        loads, sizes = [0] * count, [0] * count
        directory_counts = [Counter() for _ in range(count)]
        assigned = {}
        for path in paths:
            directory = str(PurePosixPath(path).parent)
            eligible = [i for i in range(count) if not groups[i] or
                        sizes[i] + len(blocks[path]) <= limits.max_units]
            eligible = eligible or list(range(count))
            # Load dominates; directory/import affinity breaks nearby choices.
            low = min(loads[i] for i in eligible)
            candidates = [i for i in eligible if loads[i] <= low + weights[path] * .25]
            scores = Counter()
            for neighbour, weight in adjacency[path].items():
                if neighbour in assigned:
                    scores[assigned[neighbour]] += weight
            chosen = min(candidates, key=lambda i: (-scores[i], -directory_counts[i][directory], loads[i], i))
            groups[chosen].append(path)
            assigned[path] = chosen
            directory_counts[chosen][directory] += 1
            loads[chosen] += weights[path]
            sizes[chosen] += len(blocks[path])
        results = [measured(group) for group in groups if group]
        if all(size <= limits.max_tokens for _, size in results):
            return [{"id": f"region-{i:04d}", "unit_ids": ids, "input_tokens": size}
                    for i, (ids, size) in enumerate(results, 1)]
        if count == len(paths):
            raise ValueError("file blocks cannot fit tree budget; increase CBE_TREE_MAX_TOKENS")
        count += 1


def region_prefix(region_id: str) -> str:
    return f"r{int(region_id.removeprefix('region-'))}-"


def region_unit_ids(regions: list[dict], region_id: str) -> set[str]:
    return set(next(r["unit_ids"] for r in regions if r["id"] == region_id))


def validate_region_ids(tree: dict, region_id: str) -> None:
    prefix = region_prefix(region_id)
    for node in tree["nodes"]:
        if len(prefix + node["id"]) > 64:
            raise ValueError(f"region node id exceeds 64 characters with prefix {prefix!r}; "
                             f"shorten id to at most {64 - len(prefix)} characters")


def merge_inputs(regions: list[dict], subtrees: dict, edges: list[dict]) -> tuple[dict, list[dict]]:
    rows = {}
    membership = {}
    for region in regions:
        rid = region["id"]
        tree = subtrees[rid]
        root = next(n for n in tree["nodes"] if n.get("parent") is None)
        rows[rid] = {"id": rid, "kind": "region", "summary": root["capability"] + " " + root["summary"],
                     "title": root["title"], "top_nodes": [
                         {k: n[k] for k in ("id", "title", "capability", "summary")}
                         for n in tree["nodes"] if n.get("parent") == root["id"]]}
        membership.update({uid: rid for uid in region["unit_ids"]})
    return rows, region_edges(edges, membership)


def compose(upper: dict, subtrees: dict) -> dict:
    """Replace region pseudo-units with intact accepted subtrees."""
    nodes, edges = [], list(upper.get("depends_on") or [])
    for node in upper["nodes"]:
        nodes.append({**node, "unit_ids": []})
        for rid in node.get("unit_ids") or []:
            subtree = subtrees[rid]
            rename = {n["id"]: f"{region_prefix(rid)}{n['id']}" for n in subtree["nodes"]}
            nodes.extend({**n, "id": rename[n["id"]],
                          "parent": rename.get(n.get("parent"), node["id"])} for n in subtree["nodes"])
            edges.extend({**e, "from": rename[e["from"]], "to": rename[e["to"]]}
                         for e in subtree.get("depends_on") or [])
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise ValueError("upper-level node id collides with an accepted subtree id")
    return {"nodes": nodes, "depends_on": edges}
