"""Bounded responsibility aggregation: summaries, resolved graph and candidate regions.

Regions are scheduling boundaries, not semantic modules. Only the model chooses
responsibilities; composition preserves each accepted subtree verbatim apart from
namespacing ids and attaching its root to the chosen upper-level owner.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
from pathlib import PurePosixPath

from cbe.records import build_records, frozen_sources, summary_sentence
from cbe.docs import unit_ranges
from cbe.token_budget import count_text_tokens


@dataclass(frozen=True)
class Limits:
    max_units: int = 300
    max_tokens: int = 32000

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
    records, symbols = build_records(
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
    # Import file nodes have no symbol coordinate. Attribute an import once to
    # the module residual (or first source unit) of each file, never every pair.
    files = defaultdict(list)
    for uid, row in records.items():
        for r in row["ranges"]:
            files[r["path"]].append(uid)
    representative = {path: min(ids, key=lambda uid: ("::module_residual::" not in uid, uid))
                      for path, ids in files.items()}
    graph = context.get("graph") or {}
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    for edge in graph.get("edges", []):
        if edge.get("kind") != "import" or edge.get("status") != "resolved":
            continue
        source = representative.get(nodes.get(edge.get("source"), {}).get("path"))
        target = representative.get(nodes.get(edge.get("target"), {}).get("path"))
        # Coordinate-resolved imports already entered the counter above.
        existing = edge_table.get(edge.get("id"), {})
        if owners.get(existing.get("source_symbol")) and owners.get(existing.get("target_symbol")):
            continue
        if source and target and source != target:
            counts[source, target, "import"] += 1
    return records, [{"from": a, "to": b, "kind": kind, "count": n}
                     for (a, b, kind), n in sorted(counts.items())]


def region_edges(edges: list[dict], membership: dict[str, str]) -> list[dict]:
    counts = Counter()
    for e in edges:
        a, b = membership.get(e["from"]), membership.get(e["to"])
        if a and b and a != b:
            counts[a, b, e["kind"]] += e["count"]
    return [{"from": a, "to": b, "kind": k, "count": n}
            for (a, b, k), n in sorted(counts.items())]


def partition(units: dict, edges: list[dict], limits: Limits, prompt) -> list[dict]:
    """Deterministic directory/package seeds, import affinity packing, exact budget.

    ``prompt`` renders a candidate region with its internal edges. Its actual
    token count (including rules/principles) decides whether it fits. No model
    is called. A single over-budget digest is an explicit planning error.
    """
    def subset(ids):
        wanted = set(ids)
        return {uid: units[uid] for uid in sorted(ids)}, [e for e in edges
                if e["from"] in wanted and e["to"] in wanted]

    def tokens(ids):
        rows, graph = subset(ids)
        return count_text_tokens(prompt(rows, graph))

    if len(units) <= limits.max_units and tokens(units) <= limits.max_tokens:
        return []
    buckets = defaultdict(list)
    for uid in sorted(units):
        ranges = units[uid].get("ranges") or []
        path = ranges[0]["path"] if ranges else uid.split("::", 1)[0].removeprefix("grp:")
        buckets[str(PurePosixPath(path).parent)].append(uid)
    affinity = Counter()
    for e in edges:
        if e["kind"] == "import":
            affinity[e["from"], e["to"]] += e["count"]
            affinity[e["to"], e["from"]] += e["count"]
    pending = [uid for directory in sorted(buckets) for uid in buckets[directory]]
    groups = []
    while pending:
        selected = [pending.pop(0)]
        if tokens(selected) > limits.max_tokens:
            raise ValueError(f"single tree summary exceeds token budget: {selected[0]}")
        while pending and len(selected) < limits.max_units:
            # Preserve directory locality, prefer an imported neighbour within it.
            directory = next(key for key, ids in buckets.items() if pending[0] in ids)
            candidates = [uid for uid in pending if uid in buckets[directory]]
            candidate = min(candidates, key=lambda uid: (-sum(affinity[a, uid] for a in selected), uid))
            if tokens(selected + [candidate]) > limits.max_tokens:
                break
            selected.append(candidate)
            pending.remove(candidate)
        groups.append({"id": f"region-{len(groups) + 1:04d}", "unit_ids": sorted(selected),
                       "input_tokens": tokens(selected)})
    return groups


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
            rename = {n["id"]: f"{rid}-{n['id']}" for n in subtree["nodes"]}
            nodes.extend({**n, "id": rename[n["id"]],
                          "parent": rename.get(n.get("parent"), node["id"])} for n in subtree["nodes"])
            edges.extend({**e, "from": rename[e["from"]], "to": rename[e["to"]]}
                         for e in subtree.get("depends_on") or [])
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        raise ValueError("upper-level node id collides with an accepted subtree id")
    return {"nodes": nodes, "depends_on": edges}
