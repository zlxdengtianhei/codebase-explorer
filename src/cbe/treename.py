"""Read view of a finished tree: parents, members, titles, slugs, dependencies.

The structure comes from ``layers`` (the model groups detail, level by level).
This module holds the parts every later stage shares: a read view of the node
list, the readable slug for a node id, the program-made record used when a group
never got a usable answer, and the cross-node dependency counts.
"""
from __future__ import annotations

import hashlib
import math
import posixpath
import re
import unicodedata
from collections import Counter, defaultdict

from cbe import skeleton

TITLE_WORDS = 9
_STOP_PATH = {"lib", "src", "main", "java", "com", "test", "tests", "include", "rb", "py", "js", "ts", "org"}


class Tree:
    """Read view of a frozen skeleton (``skeleton.build()["nodes"]``)."""

    def __init__(self, nodes: list[dict]):
        self.nodes = {n["id"]: n for n in nodes}
        self.order = [n["id"] for n in nodes]
        self.kids: dict[str, list[str]] = defaultdict(list)
        for n in nodes:
            if n["parent"]:
                self.kids[n["parent"]].append(n["id"])
        self.root = next(i for i in self.order if self.nodes[i]["parent"] is None)
        self._members: dict[str, list[str]] = {}
        self.leaf_of = {u: n["id"] for n in nodes for u in n["unit_ids"]}

    def leaves(self) -> list[str]:
        return [i for i in self.order if not self.kids[i]]

    def internals(self) -> list[str]:
        return [i for i in self.order if self.kids[i]]

    def members(self, node: str) -> list[str]:
        if node not in self._members:
            out = list(self.nodes[node]["unit_ids"])
            for kid in self.kids[node]:
                out += self.members(kid)
            self._members[node] = out
        return self._members[node]


def empty_tree() -> dict:
    """The tree of a run with no units: one root node."""
    return {"nodes": [{"id": "root", "parent": None, "title": "Codebase", "unit_ids": [], "evidence_units": [],
                       "capability": "This run has no explainable code units.",
                       "summary": "Every file read was empty, so there is nothing to map."}],
            "depends_on": []}


def normalize_title(text: str) -> str:
    return re.sub(r"\W+", " ", str(text or "").lower()).strip()


# ------------------------------------------------- program-made titles ----

def _words(units: dict[str, dict], members: list[str]) -> Counter:
    count = Counter()
    for u in members:
        for w in set(skeleton.word_tokens(skeleton.symbol_words(u) + " " + (units[u].get("summary") or ""))):
            count[w] += 1
    return count


def program_record(units: dict[str, dict], members: list[str], *, avoid: set[str] = frozenset(),
                   siblings: list[list[str]] = ()) -> dict:
    """A title and a capability made from the members: telling words plus the main directory.

    Never numbered; ``avoid`` holds normalized titles the result must not equal."""
    words = _words(units, members)
    others = Counter()
    for other in siblings:
        others.update(_words(units, other))
    score = {w: c * (1 + math.log(len(members) / (1 + others.get(w, 0)) + 1)) for w, c in words.items()}
    ranked = [w for w, _ in sorted(score.items(), key=lambda t: (-t[1], t[0]))]
    dirs = Counter(posixpath.dirname((skeleton.unit_paths(units[u]) or [""])[0]).split("/")[-1] for u in members)
    main_dir = next((d for d, _ in dirs.most_common() if d and d.lower() not in _STOP_PATH), "")

    def prefixed(text: str) -> str:
        return f"{main_dir}: {text}" if main_dir else text

    options = [prefixed(" ".join(w.capitalize() for w in ranked[:k])) for k in range(2, len(ranked) + 1)]
    files = Counter((skeleton.unit_paths(units[u]) or [""])[0] for u in members)
    stem = posixpath.splitext(posixpath.basename(files.most_common(1)[0][0]))[0] if files else ""
    base = prefixed(" ".join(w.capitalize() for w in ranked[:3])) if ranked else (main_dir or "Miscellaneous")
    first = skeleton.symbol_words(sorted(members)[0]) if members else ""
    options += [f"{base} ({stem})" if stem else base, f"{base} ({stem}: {first})" if stem else f"{base} ({first})"]
    title = next((t for t in options if normalize_title(t) not in avoid), options[-1])
    capability = f"Units around {', '.join(ranked[:4])}" + (f" in {main_dir}" if main_dir else "") + " (program-made description)."
    return {"title": title, "capability": capability, "summary": capability, "evidence_units": [],
            "program_made": True}


# ------------------------------------------------------------- assemble ----

def dependencies(tree: Tree, edges: list[dict]) -> list[dict]:
    """``depends_on`` between sibling nodes, from the unit edges that cross between their subtrees."""
    path_of: dict[str, list[str]] = {}
    for leaf in tree.leaves():
        chain, node = [], leaf
        while node:
            chain.append(node)
            node = tree.nodes[node]["parent"]
        for unit in tree.nodes[leaf]["unit_ids"]:
            path_of[unit] = chain[::-1]
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for edge in edges:
        pa, pb = path_of.get(edge["from"]), path_of.get(edge["to"])
        if not pa or not pb or edge["from"] == edge["to"]:
            continue
        if edge.get("kind") not in ("call", "import"):
            continue
        depth = next((i for i, (x, y) in enumerate(zip(pa, pb)) if x != y), None)
        if depth is not None:
            counts[pa[depth], pb[depth]] += edge["count"]
    return [{"from": a, "to": b, "basis": f"{n} resolved call/import edge(s)"}
            for (a, b), n in sorted(counts.items())]


def slugs(tree: Tree, titles: dict[str, str]) -> dict[str, str]:
    """Node ids people can read and type: the title as lower-case ASCII words joined by hyphens.

    The first node to use a slug keeps it; a later node, or one whose title has no ASCII letter, gets a
    short hash of its node id (the same input always gives the same ids)."""
    out: dict[str, str] = {}
    taken: set[str] = set()
    for node in tree.order:
        ascii_title = unicodedata.normalize("NFKD", titles[node]).encode("ascii", "ignore").decode()
        base = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:48].strip("-")
        slug, extra = base, 0
        while not slug or slug in taken:
            digest = hashlib.sha1(f"{node}{extra}".encode()).hexdigest()[:5]
            slug, extra = f"{base}-{digest}" if base else f"node-{digest}", extra + 1
        taken.add(slug)
        out[node] = slug
    return out
