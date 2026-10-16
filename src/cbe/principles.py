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
import os


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
    low, high = int(os.environ.get("CBE_TREE_MIN_GRAIN", 5)), int(os.environ.get("CBE_TREE_MAX_GRAIN", 30))
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
    minimum = int(os.environ.get("CBE_TREE_SHARED_MIN_EDGES", 3))
    shared = {uid: dict(counts) for uid, counts in sorted(users.items())
              if sum(n >= minimum for n in counts.values()) >= 2}
    return {"ok": not shared, "min_edges_per_dependent_module": minimum,
            "min_dependent_modules": 2, "shared_units": shared,
            "note": "candidates for a shared responsibility; no automatic reassignment"}


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
    return {"ok": before == after, "status": "compared", "previous": before, "current": after}


@dataclass(frozen=True)
class Principle:
    id: str
    prompt: str
    check: object


PRINCIPLES = (
    Principle("P1", "Give each module one distinct capability sentence.", _p1),
    Principle("P2", "Prefer cohesive responsibilities; use resolved internal and external edges as evidence.", _p2),
    Principle("P3", "Aim for 5–30 units per module; grow genuine intermediate capabilities when needed.", _p3),
    Principle("P4", "Give every unit exactly one primary home; reference it elsewhere.", _p4),
    Principle("P5", "Keep shared utilities and infrastructure separate from their consumers.", _p5),
    Principle("P6", "Group by responsibility across languages and retain language identity.", _p6),
    Principle("P7", "Use stable responsibility-based ids and titles for identical inputs.", _p7),
)


def report(tree: dict, units: dict, edges: list[dict], languages: dict, previous: dict | None = None) -> dict:
    nodes = tree.get("nodes") or []
    identity = sorted([[n["id"], n["title"]] for n in nodes])
    digest = hashlib.sha256(json.dumps({"units": units, "edges": edges, "languages": languages},
                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    c = {"nodes": nodes, "units": units, "edges": edges, "languages": languages,
         "owner": {uid: n["id"] for n in nodes for uid in n.get("unit_ids") or []},
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
            "checks": [{"principle": p.id, **p.check(c)} for p in PRINCIPLES],
            "hierarchy": {"ok": len(units) < 31 or any(n.get("parent") and children[n["id"]] for n in nodes),
                          "requires_intermediate_above_units": 30},
            "introduction_length": {"ok": not long, "overlong": long,
                                    "scope": "capability+summary characters versus descendant explain characters"}}


def markdown(result: dict) -> str:
    lines = ["", "## Aggregation principle checks", "",
             "Program diagnostics only; they do not prove semantic correctness or trigger rewrites.", ""]
    for row in result["checks"]:
        state = "not checked" if row["ok"] is None else ("pass" if row["ok"] else "observe")
        lines += [f"### {row['principle']} · {state}", "", "```json",
                  json.dumps(row, ensure_ascii=False, sort_keys=True), "```", ""]
    lines += ["Hierarchy and introduction length:", "", "```json",
              json.dumps({k: result[k] for k in ("hierarchy", "introduction_length")}, ensure_ascii=False),
              "```", ""]
    return "\n".join(lines)
