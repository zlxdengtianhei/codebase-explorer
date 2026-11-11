"""One registry for aggregation guidance and its advisory program checks.

These diagnostics never trigger rewrites. They measure structural proxies, not
whether a capability is semantically true. P7 needs a prior run of the same detail
input; absent comparison is explicitly 'not_checked', never a stability pass.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json

from cbe.skeleton import GRAIN

SHARED_MIN_EDGES = 3   # P5: edges a dependent module needs before a unit counts as shared


def _p1(c):
    texts = [n.get("capability", "").strip() for n in c["nodes"]]
    counts = Counter(t.casefold() for t in texts)
    bad = [n["id"] for n, text in zip(c["nodes"], texts) if not text or counts[text.casefold()] > 1]
    return {"ok": not bad, "empty_or_duplicate_capabilities": bad}


def _p2(c):
    rows = {n["id"]: {"internal": 0, "external": 0} for n in c["nodes"]}
    for e in c["edges"]:
        a, b = c["owner"].get(e["from"]), c["owner"].get(e["to"])
        if a == b and a in rows:
            rows[a]["internal"] += e["count"]
        elif a and b:
            rows[a]["external"] += e["count"]
            rows[b]["external"] += e["count"]
    for r in rows.values():
        r["internal_external_ratio"] = r["internal"] / r["external"] if r["external"] else None
    return {"ok": all(r["internal"] >= r["external"] for r in rows.values()), "modules": rows,
            "scope": "direct primary ownership; incident cross-module edges counted at each endpoint"}


def _p3(c):
    low, high = GRAIN
    sizes = {n["id"]: len(n.get("unit_ids") or []) for n in c["nodes"] if n.get("unit_ids")}
    bad = {nid: size for nid, size in sizes.items() if not low <= size <= high}
    return {"ok": not bad, "bounds": [low, high], "out_of_bounds": bad,
            "scope": "nodes with directly owned units; structural ancestors excluded"}


def _p4(c):
    counts = Counter(uid for n in c["nodes"] for uid in n.get("unit_ids") or [])
    bad = {uid: counts[uid] for uid in sorted(set(c["units"]) | set(counts))
           if counts[uid] != 1 or uid not in c["units"]}
    return {"ok": not bad, "ownership_violations": bad}


def _p5(c):
    users = defaultdict(Counter)
    for e in c["edges"]:
        source, target = c["owner"].get(e["from"]), c["owner"].get(e["to"])
        if source and target and source != target:
            users[e["to"]][source] += e["count"]
    minimum = SHARED_MIN_EDGES
    shared = {uid: dict(counts) for uid, counts in sorted(users.items())
              if sum(n >= minimum for n in counts.values()) >= 2}
    return {"ok": not shared, "min_edges_per_dependent_module": minimum,
            "min_dependent_modules": 2, "shared_units": shared,
            "note": "dependency signal only, including utilities already separated; no automatic reassignment"}


def _p6(c):
    rows = {}
    for n in c["nodes"]:
        counts = Counter()
        for uid in n.get("unit_ids") or []:
            langs = {c["languages"].get(r["path"], "unknown")
                     for r in c["units"].get(uid, {}).get("ranges", [])}
            counts.update(langs or {"unknown"})
        rows[n["id"]] = dict(sorted(counts.items()))
    return {"ok": not any("unknown" in r for r in rows.values()), "modules": rows,
            "scope": "unit counts by language; a multi-language unit contributes once per language"}


def _p7(c):
    previous = c["previous"]
    if not previous or previous.get("input_digest") != c["input_digest"]:
        return {"ok": None, "status": "not_checked", "reason": "no prior tree for the same detail input"}
    before = previous["identity"]
    after = c["identity"]
    if c["comparison_scope"] == "same_run_rerender":
        return {"ok": None, "status": "re-render identical" if before == after else "re-render changed",
                "identical": before == after,
                "scope": "same run, same detail answers; cross-run stability requires replay scripts"}
    return {"ok": before == after, "status": "compared", "previous": before, "current": after}


@dataclass(frozen=True)
class Principle:
    id: str
    check: object


PRINCIPLES = (
    Principle("P1", _p1),   # one distinct capability sentence per module
    Principle("P2", _p2),   # cohesion: resolved edges stay inside the module
    Principle("P3", _p3),   # granularity: units per module
    Principle("P4", _p4),   # one primary home per unit
    Principle("P5", _p5),   # shared utilities apart from their consumers
    Principle("P6", _p6),   # language identity kept
    Principle("P7", _p7),   # stable identity for identical inputs
)


def report(tree: dict, units: dict, edges: list[dict], languages: dict, previous: dict | None = None,
           *, comparison_scope: str = "replay") -> dict:
    nodes = tree.get("nodes") or []
    identity = sorted([[n["id"], n["title"]] for n in nodes])
    digest = hashlib.sha256(json.dumps({"units": units, "edges": edges, "languages": languages},
                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    c = {"nodes": nodes, "units": units, "edges": edges, "languages": languages,
         "owner": {uid: n["id"] for n in nodes for uid in n.get("unit_ids") or []},
         "comparison_scope": comparison_scope,
         "input_digest": digest, "identity": identity, "previous": previous}
    # R-20 and R-21 remain visible alongside principles, without inducing rewrites.
    children = defaultdict(list)
    for n in nodes:
        children[n.get("parent")].append(n["id"])
    descendants = {}
    def owned(nid, active):
        if nid in active:
            return set()
        n = next(n for n in nodes if n["id"] == nid)
        return set(n.get("unit_ids") or []) | set().union(
            *(owned(kid, active | {nid}) for kid in children[nid]))
    long = {}
    for n in nodes:
        descendants[n["id"]] = owned(n["id"], set())
        intro = len(n.get("capability", "")) + len(n.get("summary", ""))
        detail = sum(len(units.get(uid, {}).get("explain", "")) for uid in descendants[n["id"]])
        if intro > detail:
            long[n["id"]] = {"introduction_chars": intro, "detail_chars": detail}
    return {"advisory": True, "input_digest": digest, "identity": identity,
            "edge_counts_by_kind": {kind: sum(e["count"] for e in edges if e["kind"] == kind)
                                    for kind in sorted({e["kind"] for e in edges})},
            "checks": [{"principle": p.id, **p.check(c)} for p in PRINCIPLES],
            "hierarchy": {"ok": len(units) <= GRAIN[1] or any(n.get("parent") and children[n["id"]] for n in nodes),
                          "requires_intermediate_above_units": GRAIN[1]},
            "introduction_length": {"ok": not long, "overlong": long,
                                    "scope": "capability+summary characters versus descendant explain characters"}}


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
