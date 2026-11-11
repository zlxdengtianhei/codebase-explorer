"""Scales A (self-consistency), B1 (static cohesion), B2 (co-change agreement)."""
from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

from common import Repo, Tree, file_membership


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def scale_a(repo: Repo, tree: Tree) -> dict:
    """Empty nodes; sibling title repeats; title and capability repeats anywhere; unit coverage faults."""
    nodes = tree.nodes
    empty = [n for n in nodes if not nodes[n].get("unit_ids") and not tree.children[n]]
    sib = 0
    for kids in tree.children.values():
        c = Counter(_norm(nodes[k].get("title")) for k in kids)
        sib += sum(v - 1 for v in c.values() if v > 1)
    titles = Counter(_norm(n.get("title")) for n in nodes.values())
    caps = Counter(_norm(n.get("capability")) for n in nodes.values() if _norm(n.get("capability")))
    # near duplicate capability: word-set Jaccard >= 0.7 between two different nodes
    ws = {i: set(_norm(n.get("capability")).split()) for i, n in nodes.items() if _norm(n.get("capability"))}
    ids = sorted(ws)
    near = 0
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            x, y = ws[ids[a]], ws[ids[b]]
            if len(x & y) / len(x | y) >= 0.7:
                near += 1
    cover = sum(1 for u in repo.units if len(tree.owners.get(u, [])) != 1)
    unc = repo.uncovered
    return dict(nodes=len(nodes), empty=len(empty), sibling_dup_title=sib,
                dup_title_anywhere=sum(v - 1 for v in titles.values() if v > 1),
                dup_capability=sum(v - 1 for v in caps.values() if v > 1),
                near_dup_capability_pairs=near, unit_cover_faults=cover,
                uncovered_source_files=len(unc), uncovered_source_lines=sum(n for _, n in unc),
                nontest_lines=repo.all_nontest_lines)


# ------------------------------------------------------------ modularity

def soft_modularity(pairs: dict, member: dict[str, dict[str, float]]) -> float:
    """Newman-style modularity with belonging coefficients; one-hot rows give the usual Q.

    Q = sum_{i<j} w_ij s_ij / m  -  sum_g (K_g / 2m)^2,  s_ij = <m_i, m_j>, K_g = sum_i k_i m_ig.
    Items without a row (no unit lines) never share a module."""
    m = sum(pairs.values())
    if m <= 0:
        return float("nan")
    k = defaultdict(float)
    inside = 0.0
    for (a, b), w in pairs.items():
        k[a] += w
        k[b] += w
        ma, mb = member.get(a), member.get(b)
        if ma and mb:
            if len(ma) > len(mb):
                ma, mb = mb, ma
            inside += w * sum(x * mb.get(g, 0.0) for g, x in ma.items())
    K = defaultdict(float)
    for i, ki in k.items():
        for g, x in (member.get(i) or {}).items():
            K[g] += ki * x
    return inside / m - sum((x / (2 * m)) ** 2 for x in K.values())


def _hard(label: dict[str, str]) -> dict[str, dict[str, float]]:
    return {i: {g: 1.0} for i, g in label.items()}


def b1(repo: Repo, label: dict[str, str], kinds: str = "call", shuffles: int = 30, seed: int = 1) -> dict:
    pairs: dict = defaultdict(float)
    for e in repo.edges(kinds):
        a, b = sorted((e["from"], e["to"]))
        pairs[a, b] += e["count"]
    q = soft_modularity(pairs, _hard(label))
    units = sorted(label)
    vals = [label[u] for u in units]
    rng = random.Random(seed)
    rs = []
    for _ in range(shuffles):
        rng.shuffle(vals)
        rs.append(soft_modularity(pairs, _hard(dict(zip(units, vals)))))
    return dict(q=q, rand=sum(rs) / len(rs), groups=len(set(label.values())), edge_weight=sum(pairs.values()))


def b2(repo: Repo, label: dict[str, str], shuffles: int = 30, seed: int = 1) -> dict:
    pairs = repo.cochange()
    q = soft_modularity(pairs, file_membership(repo, label))
    rng = random.Random(seed)
    units = sorted(label)
    vals = [label[u] for u in units]
    r_unit, r_file = [], []
    mem = file_membership(repo, label)
    hard = {f: max(sorted(c), key=lambda g: c[g]) for f, c in mem.items()}
    files = sorted(hard)
    fvals = [hard[f] for f in files]
    for _ in range(shuffles):
        rng.shuffle(vals)
        r_unit.append(soft_modularity(pairs, file_membership(repo, dict(zip(units, vals)))))
        rng.shuffle(fvals)
        r_file.append(soft_modularity(pairs, _hard(dict(zip(files, fvals)))))
    return dict(q=q, rand_unit=sum(r_unit) / len(r_unit), rand_file=sum(r_file) / len(r_file),
                groups=len(set(label.values())), pair_weight=sum(pairs.values()),
                files_in_graph=len({f for p in pairs for f in p}))
