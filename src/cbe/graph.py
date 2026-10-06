"""Symbol graph for evidence and candidate boundaries. Not an architecture decision.

Canonical snapshot keeps complete lists. Display/packet paging must carry totals
so a truncated view cannot silently drop the rest of the tree.
"""

from __future__ import annotations

from dataclasses import dataclass

from cbe.inventory import Inventory


@dataclass
class GraphSnapshot:
    nodes: list[str]
    edges: list[dict]
    sccs: list[list[str]]
    entries: list[str]
    shared_callees: list[dict]
    unknown_edges: list[dict]
    structural_hints: list[dict]

    def to_dict(self) -> dict:
        return {
            "nodes": list(self.nodes),
            "edges": list(self.edges),
            "sccs": [list(item) for item in self.sccs],
            "entries": list(self.entries),
            "shared_callees": list(self.shared_callees),
            "unknown_edges": list(self.unknown_edges),
            "structural_hints": list(self.structural_hints),
            "nodes_total": len(self.nodes),
            "edges_total": len(self.edges),
            "sccs_total": len(self.sccs),
            "entries_total": len(self.entries),
            "shared_callees_total": len(self.shared_callees),
            "unknown_edges_total": len(self.unknown_edges),
            "structural_hints_total": len(self.structural_hints),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> GraphSnapshot:
        return cls(
            nodes=list(payload.get("nodes") or []),
            edges=list(payload.get("edges") or []),
            sccs=[list(item) for item in payload.get("sccs") or []],
            entries=list(payload.get("entries") or []),
            shared_callees=list(payload.get("shared_callees") or []),
            unknown_edges=list(payload.get("unknown_edges") or []),
            structural_hints=list(payload.get("structural_hints") or []),
        )


def callers_of(edges: list[dict], targets: set[str]) -> set[str]:
    """Subjects of resolved call edges whose target is in `targets`.

    Used by refresh so a deleted callee still stale-marks callers recorded
    on the *old* graph, not only edges that survive in the new snapshot.
    """

    found: set[str] = set()
    if not targets:
        return found
    for edge in edges or []:
        if edge.get("kind") != "call":
            continue
        target = edge.get("target_id")
        subject = edge.get("subject_id")
        if target in targets and subject:
            found.add(str(subject))
    return found


def page_list(items: list, *, page: int = 0, page_size: int | None = None) -> dict:
    """Page a sequence without dropping the total from the payload."""

    total = len(items)
    if page_size is None or page_size <= 0:
        return {
            "items": list(items),
            "total": total,
            "page": 0,
            "page_size": total,
            "offset": 0,
            "truncated": False,
        }
    offset = max(0, page) * page_size
    sliced = list(items[offset:offset + page_size])
    return {
        "items": sliced,
        "total": total,
        "page": max(0, page),
        "page_size": page_size,
        "offset": offset,
        "truncated": offset + len(sliced) < total,
    }


def build_graph(inventory: Inventory) -> GraphSnapshot:
    # Reading a frozen graph or recording native handoffs needs no graph
    # algorithms. Load NetworkX only when constructing a new source graph.
    import networkx as nx

    graph = nx.DiGraph()
    for symbol_id, symbol in inventory.symbols.items():
        graph.add_node(
            symbol_id,
            path=symbol.path,
            kind=symbol.kind,
            name=symbol.name,
        )
    edges: list[dict] = []
    unknown: list[dict] = []
    for raw in inventory.relations:
        kind = raw.get("kind")
        subject = raw.get("subject_id")
        target = raw.get("target_id")
        if subject not in graph:
            continue
        record = {
            "kind": kind,
            "subject_id": subject,
            "target_id": target,
            "status": raw.get("status"),
            "confidence": raw.get("confidence"),
            "reason": raw.get("reason"),
        }
        if target and target in graph:
            graph.add_edge(subject, target, **record)
            edges.append(record)
        else:
            unknown.append(record)
    sccs = [
        sorted(component)
        for component in nx.strongly_connected_components(graph)
        if len(component) > 1
    ]
    sccs.sort(key=lambda item: item[0] if item else "")
    entries = sorted(
        node
        for node, degree in graph.in_degree()
        if degree == 0 and graph.nodes[node].get("kind") in {"function", "method", "module_residual"}
    )
    shared = []
    for node, degree in graph.in_degree():
        if degree >= 3:
            shared.append({"symbol_id": node, "in_degree": int(degree)})
    shared.sort(key=lambda item: (-item["in_degree"], item["symbol_id"]))
    hints = []
    undirected = graph.to_undirected()
    for index, component in enumerate(nx.connected_components(undirected)):
        if len(component) < 2:
            continue
        members = sorted(component)
        hints.append(
            {
                "kind": "connected_component",
                "note": "structural hint only; not a semantic architecture group",
                "member_ids": members,
                "size": len(members),
                "members_total": len(members),
                "hint_id": f"hint-cc-{index}",
            }
        )
    return GraphSnapshot(
        nodes=sorted(graph.nodes),
        edges=edges,
        sccs=sccs,
        entries=entries,
        shared_callees=shared,
        unknown_edges=unknown,
        structural_hints=hints,
    )
