"""Two advisory readings of the finished tree: cohesion (P2) and granularity (P3).

They never trigger rewrites. They measure structural proxies, not whether a
capability is semantically true. ``summary.json`` keeps the raw readings;
``RUN.md`` shows the two summary lines of ``run_lines``.
"""
from __future__ import annotations

from cbe.skeleton import GRAIN


def _cohesion(nodes: list[dict], edges: list[dict]) -> dict:
    owner = {uid: n["id"] for n in nodes for uid in n.get("unit_ids") or []}
    rows = {n["id"]: {"internal": 0, "external": 0} for n in nodes}
    for e in edges:
        a, b = owner.get(e["from"]), owner.get(e["to"])
        if a == b and a in rows:
            rows[a]["internal"] += e["count"]
        elif a and b:
            rows[a]["external"] += e["count"]
            rows[b]["external"] += e["count"]
    for r in rows.values():
        r["internal_external_ratio"] = r["internal"] / r["external"] if r["external"] else None
    return {"principle": "P2", "ok": all(r["internal"] >= r["external"] for r in rows.values()), "modules": rows,
            "scope": "direct primary ownership; incident cross-module edges counted at each endpoint"}


def _granularity(nodes: list[dict]) -> dict:
    low, high = GRAIN
    sizes = {n["id"]: len(n.get("unit_ids") or []) for n in nodes if n.get("unit_ids")}
    bad = {nid: size for nid, size in sizes.items() if not low <= size <= high}
    return {"principle": "P3", "ok": not bad, "bounds": [low, high], "out_of_bounds": bad,
            "scope": "nodes with directly owned units; structural ancestors excluded"}


def report(tree: dict, edges: list[dict]) -> dict:
    nodes = tree.get("nodes") or []
    return {"advisory": True, "checks": [_cohesion(nodes, edges), _granularity(nodes)]}


def run_lines(result: dict, tree: dict) -> str:
    """The two numbers RUN.md shows; the full readings stay in summary.json."""
    rows = next(c for c in result["checks"] if c["principle"] == "P2")["modules"]
    linked = [r for r in rows.values() if r["internal"] or r["external"]]
    low, high = GRAIN
    sizes = [len(n["unit_ids"]) for n in tree.get("nodes") or [] if n.get("unit_ids")]
    return ("\n## Checks\n\n"
            f"- Cohesion: {sum(r['internal'] >= r['external'] for r in linked)} of {len(linked)} modules with edges "
            "have at least as many resolved edges inside as outside.\n"
            f"- Granularity: {sum(low <= n <= high for n in sizes)} of {len(sizes)} modules hold {low} to {high} units.\n"
            "- Program diagnostics only; they do not prove semantic correctness. All readings: `summary.json`.\n")
