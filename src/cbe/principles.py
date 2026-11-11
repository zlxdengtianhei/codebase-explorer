"""Advisory readings of the finished tree: cohesion (P2), granularity (P3) and the
length of each module's introduction against the explanations it introduces.

They never trigger rewrites. They measure structural proxies, not whether a
capability is semantically true. ``summary.json`` keeps the raw readings;
``RUN.md`` shows the summary lines of ``run_lines``.
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


def _introduction_length(nodes: list[dict], units: dict) -> dict:
    """A module's capability and summary should not be longer than the unit explanations under it."""
    children: dict = {}
    for n in nodes:
        children.setdefault(n.get("parent"), []).append(n)

    def detail(node: dict) -> int:
        own = sum(len((units.get(uid) or {}).get("explain") or "") for uid in node.get("unit_ids") or [])
        return own + sum(detail(kid) for kid in children.get(node["id"], []))

    overlong, worst = {}, 0.0
    for n in nodes:
        intro, below = len(n.get("capability") or "") + len(n.get("summary") or ""), detail(n)
        if below:
            worst = max(worst, intro / below)
        if intro > below:
            overlong[n["id"]] = {"introduction_chars": intro, "detail_chars": below}
    return {"ok": not overlong, "overlong": overlong, "max_ratio": round(worst, 3),
            "scope": "capability+summary characters versus the explain characters of the units under the node"}


def report(tree: dict, edges: list[dict], units: dict | None = None) -> dict:
    nodes = tree.get("nodes") or []
    result = {"advisory": True, "checks": [_cohesion(nodes, edges), _granularity(nodes)]}
    if units is not None:
        result["introduction_length"] = _introduction_length(nodes, units)
    return result


def run_lines(result: dict, tree: dict) -> str:
    """The summary lines RUN.md shows; the full readings stay in summary.json."""
    rows = next(c for c in result["checks"] if c["principle"] == "P2")["modules"]
    linked = [r for r in rows.values() if r["internal"] or r["external"]]
    low, high = GRAIN
    sizes = [len(n["unit_ids"]) for n in tree.get("nodes") or [] if n.get("unit_ids")]
    length = result.get("introduction_length")
    return ("\n## Checks\n\n"
            f"- Cohesion: {sum(r['internal'] >= r['external'] for r in linked)} of {len(linked)} modules with edges "
            "have at least as many resolved edges inside as outside.\n"
            f"- Granularity: {sum(low <= n <= high for n in sizes)} of {len(sizes)} modules hold {low} to {high} units.\n"
            + (f"- Introduction length: the longest module introduction is {length['max_ratio']:.2f} times "
               f"the explanations under it; {len(length['overlong'])} module(s) above 1.\n" if length else "") +
            "- Program diagnostics only; they do not prove semantic correctness. All readings: `summary.json`.\n")
