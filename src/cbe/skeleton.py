"""Program-computed module skeleton: units + edges in, a tree of modules out.

Pure function. It calls no model, reads and writes no file, and knows nothing
about the task state machine. A model later only names the modules (``treename``).

How the tree is computed
------------------------
1. One undirected weighted graph.  Nodes are units plus "anchors" (one per file,
   one per directory) that only pull units of the same file or directory
   together; anchors are dropped from the result.
   * dependency edges: ``1 + ln(count)``; model-inferred relations use
     ``Weights.relation``; an edge into a unit is divided by
     ``ln(e + in_degree(unit))`` so a helper that everybody calls does not glue
     everybody together;
   * position: unit - file ``w_file``, file - directory ``w_dir``,
     directory - parent directory ``w_dir / 2``;
   * wording: TF-IDF cosine over summary words and identifier words; each unit
     keeps its 5 best neighbours whose cosine is at least ``text_floor``;
     weight ``w_text * cosine``.
2. Leaf modules: Louvain with a fixed seed; a community above ``grain[1]`` units
   is split again inside its own subgraph; a leaf below ``MIN_LEAF`` units joins
   the neighbour it is tied to most strongly.  Leaves that still miss the grain
   carry a ``flag`` that says why.
3. Upper levels: modules become points, anchors stay, Louvain runs again, repeat
   until at most ``TOP_MAX`` nodes are left.  A group of one module is not a node.

Same input and seed give byte-identical output.  Node ids are a hash of the
sorted member unit ids of the node's subtree.
"""
from __future__ import annotations

import hashlib
import math
import posixpath
import re
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx
from networkx.algorithms.community import louvain_communities

GRAIN = (5, 30)       # units per leaf module
MIN_LEAF = 3          # a leaf with fewer units always tries to join a neighbour
TOP_MAX = 9           # stop stacking levels at this many top nodes
TEXT_NEIGHBORS = 5
RESOLUTIONS_UP = (1.0, 2.0, 4.0, 8.0, 16.0)   # tried in order to split an oversized community
COARSEN_SHRINK = 0.6    # each level above the leaves keeps at most this share of the nodes
COARSEN_LADDER = (3.0, 2.0, 1.5, 1.0, 0.7, 0.5, 0.35, 0.25, 0.15, 0.08)
POOL_CHUNK = 10       # units per leaf when unrelated units are packed in path order
_ANCHOR_FILE = "\x00file:"
_ANCHOR_DIR = "\x00dir:"


@dataclass(frozen=True)
class Weights:
    """Defaults picked on ruby_llm and gson; not user configuration."""
    w_file: float = 1.0
    w_dir: float = 0.5
    w_text: float = 0.5
    text_floor: float = 0.25
    relation: float = 0.5


# ---------------------------------------------------------------- graph ----

_STOP = frozenset(
    "a an and are as at be but by for from has have if in into is it its of on or that the their then "
    "this to was when which while with within without not can via per each also than so such these "
    "those they them used use uses using returns return only any all one two both other over under "
    "after before inside outside".split())


def word_tokens(text: str) -> list[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    out = []
    for token in re.findall(r"[A-Za-z]+", text):
        token = token.lower()
        if len(token) < 3 or token in _STOP:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        out.append(token)
    return out


def symbol_words(ident: str) -> str:
    """Name part of ``path::kind::Name::offset`` ids; the slug of ``grp:`` ids."""
    parts = ident.split("::")
    if len(parts) >= 3:
        return parts[2]
    return re.sub(r"^[a-z]+:", "", ident).replace("-", " ").replace("_", " ")


def unit_paths(unit: dict) -> list[str]:
    seen: list[str] = []
    for rng in unit.get("ranges") or []:
        path = rng.get("path")
        if path and path not in seen:
            seen.append(path)
    if not seen and (unit.get("primary_range") or {}).get("path"):
        seen.append(unit["primary_range"]["path"])
    return seen


def _unit_doc(uid: str, unit: dict) -> list[str]:
    words = word_tokens(unit.get("summary") or "")
    words += word_tokens(symbol_words(uid))
    for member in unit.get("folded_members") or []:
        if isinstance(member, str):
            words += word_tokens(symbol_words(member))
    for path in unit_paths(unit):
        words += word_tokens(path.replace("/", " ").replace(".", " ").replace("_", " "))
    return words


def _text_edges(units: dict, uids: list[str], floor: float) -> dict[tuple[str, str], float]:
    """Cosine of TF-IDF vectors; each unit keeps its best TEXT_NEIGHBORS at or above floor."""
    docs = {uid: _unit_doc(uid, units[uid]) for uid in uids}
    df: dict[str, int] = defaultdict(int)
    for words in docs.values():
        for word in set(words):
            df[word] += 1
    n = len(uids)
    vectors: dict[str, dict[str, float]] = {}
    for uid, words in docs.items():
        tf: dict[str, int] = defaultdict(int)
        for word in words:
            tf[word] += 1
        vec = {w: (1 + math.log(c)) * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in tf.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors[uid] = {w: v / norm for w, v in vec.items()}
    postings: dict[str, list[str]] = defaultdict(list)
    for uid in uids:
        for word in vectors[uid]:
            postings[word].append(uid)
    out: dict[tuple[str, str], float] = {}
    for uid in uids:
        dots: dict[str, float] = defaultdict(float)
        vec = vectors[uid]
        for word, value in vec.items():
            if len(postings[word]) > 0.5 * n and n > 20:   # words found nearly everywhere carry no signal
                continue
            for other in postings[word]:
                if other != uid:
                    dots[other] += value * vectors[other][word]
        best = sorted(((c, o) for o, c in dots.items() if c >= floor), key=lambda t: (-t[0], t[1]))
        for cos, other in best[:TEXT_NEIGHBORS]:
            key = (uid, other) if uid < other else (other, uid)
            out[key] = max(out.get(key, 0.0), cos)
    return out


def _anchor_chain(path: str) -> list[str]:
    """Directory anchors from the file's directory up to (not including) the root."""
    chain, d = [], posixpath.dirname(path)
    while d and d != ".":
        chain.append(d)
        d = posixpath.dirname(d)
    return chain


def _build_graph(units: dict, edges: list[dict], w: Weights):
    uids = sorted(units)
    G = nx.Graph()
    G.add_nodes_from(uids)
    indeg: dict[str, set] = defaultdict(set)
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a in units and b in units and a != b:
            indeg[b].add(a)
    acc: dict[tuple[str, str], float] = defaultdict(float)
    for e in sorted(edges, key=lambda e: (str(e.get("from")), str(e.get("to")), str(e.get("kind")))):
        a, b = e.get("from"), e.get("to")
        if a not in units or b not in units or a == b:
            continue
        base = w.relation if e.get("kind") == "relation" else 1.0
        weight = base * (1 + math.log(max(int(e.get("count") or 1), 1))) / math.log(math.e + len(indeg[b]))
        if weight > 0:
            acc[(a, b) if a < b else (b, a)] += weight
    dep = dict(acc)
    for (a, b), weight in dep.items():
        G.add_edge(a, b, weight=weight)
    text = {}
    if w.w_text > 0 and len(uids) > 1:
        text = {k: w.w_text * c for k, c in _text_edges(units, uids, w.text_floor).items()}
        for (a, b), weight in text.items():
            G.add_edge(a, b, weight=G[a][b]["weight"] + weight if G.has_edge(a, b) else weight)
    anchors_of: dict[str, list[str]] = {}
    profile: dict[str, dict[str, float]] = {}
    for uid in uids:
        files = unit_paths(units[uid])
        anchors: list[str] = []
        prof: dict[str, float] = defaultdict(float)
        for path in files:
            share = 1.0 / len(files)
            if w.w_file > 0:
                fa = _ANCHOR_FILE + path
                G.add_edge(uid, fa, weight=G[uid][fa]["weight"] + w.w_file * share if G.has_edge(uid, fa) else w.w_file * share)
                anchors.append(fa)
                prof[fa] += w.w_file * share
                if w.w_dir > 0:
                    chain = _anchor_chain(path)
                    prev = fa
                    for k, d in enumerate(chain):
                        da = _ANCHOR_DIR + d
                        weight = w.w_dir if k == 0 else w.w_dir / 2
                        if not G.has_edge(prev, da):
                            G.add_edge(prev, da, weight=weight)
                        anchors.append(da)
                        prof[da] += w.w_dir / (2 ** k) * share
                        prev = da
        anchors_of[uid] = anchors
        profile[uid] = dict(prof)
    return G, uids, dep, text, anchors_of, profile


# ------------------------------------------------------------ community ----

def _louvain(G: nx.Graph, resolution: float, seed: int) -> list[list[str]]:
    comms = louvain_communities(G, weight="weight", resolution=resolution, seed=seed)
    return sorted((sorted(c) for c in comms), key=lambda c: c[0])


def _is_anchor(name: str) -> bool:
    return name.startswith("\x00")


def _subgraph(G: nx.Graph, members: list[str], anchors_of: dict) -> nx.Graph:
    names = set(members)
    for uid in members:
        names.update(anchors_of.get(uid, ()))
    # Not G.subgraph(names): a view of a small node set iterates that set, in hash order, and
    # Louvain's result depends on node order.
    H = nx.Graph()
    H.add_nodes_from(n for n in G if n in names)
    for u in H:
        for v, data in G[u].items():
            if v in names and not H.has_edge(u, v):
                H.add_edge(u, v, weight=data["weight"])
    return H


def _split(G, members: list[str], anchors_of, grain, seed) -> list[tuple[list[str], str | None]]:
    """Split ``members`` until every part has at most grain[1] units."""
    if len(members) <= grain[1]:
        return [(members, None)]
    sub = _subgraph(G, members, anchors_of)
    parts: list[list[str]] = []
    for r in RESOLUTIONS_UP:
        parts = [[n for n in c if not _is_anchor(n)] for c in _louvain(sub, r, seed)]
        parts = [p for p in parts if p]
        if len(parts) >= 2:
            break
    if len(parts) < 2:
        return [(members, f"Louvain does not split these units at resolution up to {RESOLUTIONS_UP[-1]:g}")]
    out: list[tuple[list[str], str | None]] = []
    for part in parts:
        out.extend(_split(G, part, anchors_of, grain, seed))
    return out


def _leaf_ties(members: set[str], owner: dict, dep_text: nx.Graph) -> dict[int, float]:
    """Tie strength from a module to every other module (unit edges + shared files and directories)."""
    ties: dict[int, float] = defaultdict(float)
    for u in sorted(members):
        if u in dep_text:
            for v, data in dep_text[u].items():
                o = owner.get(v)
                if o is not None and v not in members:
                    ties[o] += data["weight"]
    return ties


def _profile_of(members, profile) -> dict[str, float]:
    total: dict[str, float] = defaultdict(float)
    for u in sorted(members):
        for a, v in profile.get(u, {}).items():
            total[a] += v
    return total


def _shape_leaves(parts, dep_text, profile, units, grain):
    """Merge small leaves into their tightest neighbour; pack unrelated stragglers in path order."""
    leaves: dict[int, dict] = {}
    for i, (members, flag) in enumerate(parts):
        leaves[i] = {"m": set(members), "flag": None, "why": flag}
    next_id = len(leaves)

    def owner_map():
        return {u: k for k, leaf in leaves.items() for u in leaf["m"]}

    def ties_for(k, owner, profs):
        t = _leaf_ties(leaves[k]["m"], owner, dep_text)
        mine = profs[k]
        if mine:
            for j in leaves:
                if j != k:
                    shared = sum(min(v, profs[j].get(a, 0.0)) for a, v in mine.items() if a in profs[j])
                    if shared > 0:
                        t[j] += shared
        return t

    isolated: list[int] = []
    changed = True
    while changed:
        changed = False
        owner = owner_map()
        profs = {k: _profile_of(leaf["m"], profile) for k, leaf in leaves.items()}
        for k in sorted(leaves, key=lambda k: (len(leaves[k]["m"]), min(leaves[k]["m"]))):
            size = len(leaves[k]["m"])
            if size >= grain[0] or k in isolated:
                continue
            ties = ties_for(k, owner, profs)
            total = sum(ties.values())
            fits = {j: v for j, v in ties.items() if size + len(leaves[j]["m"]) <= grain[1]}
            pool = fits if (fits or size >= MIN_LEAF) else ties
            if not pool or max(pool.values()) <= 0:
                if size < MIN_LEAF:
                    isolated.append(k)
                else:
                    leaves[k]["why"] = "no tie to any other module"
                continue
            best = max(sorted(pool), key=lambda j: pool[j])
            if size >= MIN_LEAF and pool[best] < 0.3 * total:
                leaves[k]["why"] = f"the strongest neighbour holds {pool[best] / total:.0%} of their outside ties (below 30%)"
                continue
            leaves[best]["m"] |= leaves[k]["m"]
            if len(leaves[best]["m"]) > grain[1]:
                leaves[best]["why"] = f"grew past the limit when a {size}-unit leaf with no better home joined"
            del leaves[k]
            changed = True
            break
    # straggler pool: no tie to anything, so only the path order is left
    pool_units = sorted((u for k in isolated if k in leaves for u in leaves[k]["m"]),
                        key=lambda u: ((unit_paths(units[u]) or [""])[0], u))
    for k in isolated:
        leaves.pop(k, None)
    chunks = [pool_units[i:i + POOL_CHUNK] for i in range(0, len(pool_units), POOL_CHUNK)]
    if len(chunks) > 1 and len(chunks[-1]) < MIN_LEAF:
        chunks[-2] += chunks.pop()
    if len(chunks) == 1 and len(chunks[0]) < MIN_LEAF and leaves:
        # too few stragglers for a leaf of their own: each joins the leaf that shares the longest path prefix
        for u in chunks.pop():
            mine = (unit_paths(units[u]) or [""])[0]
            def common(k):
                return max(len(posixpath.commonpath([mine, p]) if mine and p else "")
                           for v in leaves[k]["m"] for p in [(unit_paths(units[v]) or [""])[0]])
            fits = [k for k in leaves if len(leaves[k]["m"]) < grain[1]] or list(leaves)
            home = max(sorted(fits), key=lambda k: (common(k), -len(leaves[k]["m"])))
            leaves[home]["m"].add(u)
    for chunk in chunks:
        flag = "packed_by_path: units with no edge, shared file or similar wording, grouped in path order"
        leaves[next_id] = {"m": set(chunk), "flag": flag, "why": None}
        next_id += 1
    for leaf in leaves.values():
        size = len(leaf["m"])
        if str(leaf["flag"]).startswith("packed"):
            continue
        if size > grain[1]:
            leaf["flag"] = f"oversize: {size} units; {leaf['why'] or 'no better split'}"
        elif size < grain[0]:
            leaf["flag"] = f"under_min: {size} units; {leaf['why'] or 'no neighbour to join'}"
        else:
            leaf["flag"] = None            # inside the grain (a later merge may have fixed it)
    return [(sorted(leaf["m"]), leaf["flag"]) for _, leaf in sorted(leaves.items(), key=lambda kv: min(kv[1]["m"]))]


def _contract(G: nx.Graph, owner: dict[str, str]) -> nx.Graph:
    acc: dict[tuple[str, str], float] = defaultdict(float)
    for a, b, data in G.edges(data=True):
        ma, mb = owner.get(a, a), owner.get(b, b)
        acc[(ma, mb) if ma <= mb else (mb, ma)] += data["weight"]
    C = nx.Graph()
    C.add_nodes_from(sorted({owner.get(n, n) for n in G.nodes}))
    for (a, b), weight in sorted(acc.items()):
        C.add_edge(a, b, weight=weight)
    return C


def _coarsen(C: nx.Graph, mods: list[str], seed: int) -> list[list[str]]:
    """Group modules so that the count falls to about 60% or less (never to one group)."""
    limit = max(2, math.ceil(COARSEN_SHRINK * len(mods)))
    best = None
    for r in COARSEN_LADDER:
        gs = [[n for n in c if not _is_anchor(n)] for c in _louvain(C, r, seed)]
        gs = [g for g in gs if g]
        if 2 <= len(gs) <= limit:
            return gs
        if 2 <= len(gs) < len(mods) and (best is None or len(gs) < len(best)):
            best = gs
    return best or [[m] for m in mods]


def _node_id(unit_ids) -> str:
    return "m" + hashlib.sha1("\n".join(sorted(unit_ids)).encode()).hexdigest()[:10]


# ----------------------------------------------------------------- build ---

def build(units: dict[str, dict], edges: list[dict], *, seed: int = 20261111,
          grain: tuple[int, int] = GRAIN, weights: Weights = Weights()) -> dict:
    """Return ``{"nodes": [{"id", "parent", "unit_ids", "level"[, "flag"]}]}``.

    ``level`` is the depth below the root (root 0).  Only leaves hold units.  A leaf outside
    ``grain`` carries ``flag``: why it is outside.
    """
    if not units:
        return {"nodes": []}
    G, uids, dep, text, anchors_of, profile = _build_graph(units, edges, weights)
    dep_text = nx.Graph()
    dep_text.add_nodes_from(uids)
    for (a, b), x in list(dep.items()) + list(text.items()):
        dep_text.add_edge(a, b, weight=dep_text[a][b]["weight"] + x if dep_text.has_edge(a, b) else x)

    parts = _split(G, uids, anchors_of, grain, seed)
    leaves = _shape_leaves(parts, dep_text, profile, units, grain)

    # tree under construction: temp name -> {"units", "children", "flag"}
    tree: dict[str, dict] = {}
    for i, (members, flag) in enumerate(leaves):
        tree[f"L{i}"] = {"units": members, "children": [], "flag": flag}
    top = list(tree)
    n_level = 0
    while len(top) > TOP_MAX:
        owner: dict[str, str] = {}
        for name in top:
            for u in _subtree_units(tree, name):
                owner[u] = name
        C = _contract(G, owner)
        groups = _coarsen(C, sorted(top), seed)
        if len(groups) >= len(top):
            break
        n_level += 1
        new_top = []
        for gi, group in enumerate(sorted(groups, key=lambda g: g[0])):
            if len(group) == 1:
                new_top.append(group[0])
            else:
                name = f"U{n_level}_{gi}"
                tree[name] = {"units": [], "children": sorted(group), "flag": None}
                new_top.append(name)
        top = new_top
    if len(top) == 1:
        root = top[0]
    else:
        root = "ROOT"
        tree[root] = {"units": [], "children": sorted(top), "flag": None}

    ids = {name: _node_id(_subtree_units(tree, name)) for name in tree}
    nodes: list[dict] = []

    def emit(name: str, parent: str | None, level: int):
        entry = tree[name]
        node = {"id": ids[name], "parent": parent, "unit_ids": sorted(entry["units"]), "level": level}
        if entry["flag"]:
            node["flag"] = entry["flag"]
        nodes.append(node)
        kids = sorted(entry["children"], key=lambda c: (-len(_subtree_units(tree, c)), ids[c]))
        for kid in kids:
            emit(kid, ids[name], level + 1)

    emit(root, None, 0)

    return {"nodes": nodes}


def _subtree_units(tree: dict, name: str) -> list[str]:
    entry = tree[name]
    out = list(entry["units"])
    for kid in entry["children"]:
        out.extend(_subtree_units(tree, kid))
    return out

