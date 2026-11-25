"""Unit records and edges for the tree, and the relationship view of a finished tree.

The tree itself comes from ``skeleton`` (structure) and ``treename`` (names).
"""
from __future__ import annotations

from collections import Counter, defaultdict

from cbe.records import build_records, frozen_sources
from cbe.docs import unit_ranges


def inputs(units: dict, dispositions: dict, inventory: dict, context: dict) -> tuple[dict, list[dict]]:
    """Use the same source-coordinate ownership as the published catalog."""
    ranges = {uid: unit_ranges(uid, unit, inventory) for uid, unit in units.items()}
    edge_table = {}
    records, _ = build_records(
        units, dispositions, inventory, ranges, frozen_sources(context, list(inventory)),
        {f["path"]: f.get("language", "unknown") for f in context.get("files", [])},
        context, context.get("graph"), edge_table)
    return records, unit_edges(records, edge_table)


def unit_edges(records: dict, edge_table: dict) -> list[dict]:
    """Roll resolved raw edges through the catalog's folded-symbol ownership."""
    owners = {sid: uid for uid, row in records.items() if not row.get("pieces")
              for sid in [uid] + row.get("folded_members", [])}
    # A call reaches a unit cut for length as a whole; a call made inside it comes from its piece.
    callee = {**owners, **{sid: uid for uid, row in records.items() for sid in row.get("pieces") or []}}
    counts = Counter()
    for edge in edge_table.values():
        source, target = owners.get(edge.get("source_symbol")), callee.get(edge.get("target_symbol"))
        if target and records.get(source, {}).get("piece_of") == target:
            continue  # a piece calling its own unit is not a relation between units
        if edge.get("status") == "resolved" and source and target and source != target:
            counts[source, target, edge["kind"]] += 1
    # File-level imports without two source-coordinate unit owners are not
    # unit edges: they are never attributed to an arbitrary function in the imported file.
    return [{"from": a, "to": b, "kind": kind, "count": n}
            for (a, b, kind), n in sorted(counts.items())]


def roll_up_edges(edges: list[dict], membership: dict[str, str]) -> list[dict]:
    counts = Counter()
    for e in edges:
        a, b = membership.get(e["from"]), membership.get(e["to"])
        if a and b and a != b:
            counts[a, b, e["kind"]] += e["count"]
    return [{"from": a, "to": b, "kind": k, "count": n}
            for (a, b, k), n in sorted(counts.items())]


def relationship_view(tree: dict, edges: list[dict], graph: dict | None, *, graph_only_limit: int = 40,
                      within_containment_limit: int = 40) -> dict:
    """Compare disjoint subtrees; expose calls inside structural containment.

    Tree containment pairs count ancestor direct units versus descendant subtree.
    Graph-only pairs use direct primary ownership to avoid repeating edges at
    every ancestor level. Only resolved call/import inputs are graph evidence.
    """
    from cbe.graph import graph_state

    state, reason = graph_state(graph)
    membership = {uid: n["id"] for n in tree.get("nodes", []) for uid in n.get("unit_ids", [])}
    resolved = [e for e in edges if e["kind"] in {"call", "import"}] if state == "provided" else []
    nodes = {n["id"]: n for n in tree.get("nodes", [])}
    ancestors = {}
    for nid in nodes:
        lineage, parent = set(), nodes[nid].get("parent")
        while parent in nodes and parent not in lineage:
            lineage.add(parent)
            parent = nodes[parent].get("parent")
        ancestors[nid] = lineage
    def contains(a, b):
        return a in ancestors[b] or b in ancestors[a]
    subtree_units = {nid: {uid for uid, owner in membership.items()
                           if owner == nid or nid in ancestors[owner]} for nid in nodes}
    counts = Counter()
    kinds = defaultdict(Counter)
    for edge in roll_up_edges(resolved, membership):
        pair = edge["from"], edge["to"]
        counts[pair] += edge["count"]
        kinds[pair][edge["kind"]] += edge["count"]
    node_ids = set(nodes)
    model = {(e["from"], e["to"]): e.get("basis", "") for e in tree.get("depends_on", [])
             if e.get("from") in node_ids and e.get("to") in node_ids and e["from"] != e["to"]}
    unmentioned = counts.keys() - model.keys()
    graph_only = sorted((p for p in unmentioned if not contains(*p)), key=lambda p: (-counts[p], p))
    within_containment = sorted((p for p in unmentioned if contains(*p)), key=lambda p: (-counts[p], p))
    reverse_counts = {}
    for a, b in model:
        if contains(a, b):
            ancestor, descendant = (a, b) if a in ancestors[b] else (b, a)
            pair_membership = {uid: ancestor for uid in nodes[ancestor].get("unit_ids", [])}
            pair_membership.update({uid: descendant for uid in subtree_units[descendant]})
        else:
            pair_membership = {uid: nid for nid in (a, b) for uid in subtree_units[nid]}
        rolled = roll_up_edges(resolved, pair_membership)
        pair_kinds = Counter()
        reverse_counts[a, b] = sum(edge["count"] for edge in rolled
                                   if (edge["from"], edge["to"]) == (b, a))
        for edge in rolled:
            if (edge["from"], edge["to"]) == (a, b):
                pair_kinds[edge["kind"]] += edge["count"]
        counts[a, b] = sum(pair_kinds.values())
        kinds[a, b] = pair_kinds
    pairs = sorted(model) + graph_only[:graph_only_limit] + within_containment[:within_containment_limit]
    dependencies = [{"from": a, "to": b,
                     "source": "containment" if contains(a, b) and (a, b) in model else
                               "graph_confirmed" if counts[a, b] and (a, b) in model else
                               "within_containment" if contains(a, b) else "graph_only",
                     "count": counts[a, b],
                     **({"reverse_count": reverse_counts[a, b]} if contains(a, b) and (a, b) in model else {}),
                     "containment": contains(a, b), "kinds": dict(sorted(kinds[a, b].items())),
                     "basis": model.get((a, b), ""), "description": ""} for a, b in pairs]
    totals = {source: sum(e["source"] == source for e in dependencies)
              for source in ("graph_confirmed", "graph_only")}
    totals["graph_only"] = len(graph_only)
    return {"dependencies": dependencies, "counts": totals,
            "within_containment_count": len(within_containment),
            "within_containment_omitted": max(0, len(within_containment) - within_containment_limit),
            "graph_only_omitted": max(0, len(graph_only) - graph_only_limit),
            "graph_state": state, "graph_reason": reason}
