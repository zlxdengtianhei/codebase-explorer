"""Shared loading code for the module-tree measuring scripts (p2a).

Everything here is read-only on the catalogs. A "tree" is the same shape the
catalog uses: nodes with id, parent (None for the root), title, capability,
summary, unit_ids. A "cut" flattens a tree into groups of units.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # the worktree root
CLONES = Path(os.environ.get("CBE_EVAL_CLONES", ROOT / ".eval" / "clones"))   # full-history clones of the five repos
LAB = Path(os.environ.get("CBE_EVAL_LAB", ROOT / ".eval" / "lab"))   # raw model answers, caches (not in git)

REPOS = {
    "ruby_llm": dict(catalog="examples/ruby_llm/catalog.json.gz",
                     sha="1e315ab4b3f3a150c443dc9a17f504756c2aad6f"),
    "gson": dict(catalog="examples/gson/catalog.json.gz",
                 sha="e2292f9c9f2e07a4791827e8eea34aa7d80545d6"),
    "tsdown": dict(catalog="examples/tsdown/catalog.json.gz",
                   sha="2b1be7e0accdb1d6e903cd42642666431fc5e93d"),
    "fmt": dict(catalog="examples/fmt/catalog.json.gz",
                sha="b4ffa39b9994c961418406f47358791d89a5aa48"),
    "flask": dict(catalog="evaluation/e2-flask/cbe-docs/catalog.json.gz",
                  sha="85c5d93cbd049c4bd0679c36fd1ddcae8c37b642"),
}

_TEST_DIRS = {"test", "tests", "spec", "specs", "__tests__", "testing", "test_apps", "testdata", "fixtures"}
_TEST_FILE = re.compile(r"(^test_)|(_test\.)|(\.test\.)|(\.spec\.)|(Tests?\.(java|kt|rb|py|ts|js)$)")


def is_test(path: str) -> bool:
    parts = path.split("/")
    return any(p.lower() in _TEST_DIRS for p in parts[:-1]) or bool(_TEST_FILE.search(parts[-1]))


# ---------------------------------------------------------------- catalog

class Repo:
    def __init__(self, name: str):
        self.name = name
        cfg = REPOS[name]
        self.sha = cfg["sha"]
        self.clone = CLONES / name
        self.cat = json.load(gzip.open(ROOT / cfg["catalog"]))
        self.units: dict = self.cat["units"]
        # unit -> {path: lines}; lines counted from the unit's ranges
        self.unit_lines: dict[str, dict[str, int]] = {}
        for uid, u in self.units.items():
            d: dict[str, int] = defaultdict(int)
            for r in u.get("ranges") or []:
                d[r["path"]] += sum(b - a + 1 for a, b in r["lines"])
            self.unit_lines[uid] = dict(d)
        self.unit_file = {}      # the file holding most of the unit (for directory trees)
        for uid, d in self.unit_lines.items():
            if d:
                self.unit_file[uid] = max(sorted(d), key=lambda p: d[p])
            else:
                pr = (self.units[uid].get("primary_range") or {}).get("path")
                self.unit_file[uid] = pr or next(iter(self.units[uid].get("members") or [""]), "").split("::")[0]
        self.files = sorted(self.cat["files"])
        covered = Counter()
        for d in self.unit_lines.values():
            for p, l in d.items():
                covered[p] += l
        # source files = non-test files that some unit covers; the rest cannot be given to any module
        self.src_files = [f for f in self.files if not is_test(f) and covered[f] > 0]
        inv = self.cat.get("inventory") or {}
        self.uncovered = [(f, (inv.get(f) or {}).get("nlines", 0)) for f in self.files if not is_test(f) and covered[f] == 0]
        self.all_nontest_lines = sum((inv.get(f) or {}).get("nlines", 0) for f in self.files if not is_test(f))
        self.src_set = set(self.src_files)
        self.total_src_lines = sum(l for d in self.unit_lines.values() for p, l in d.items() if p in self.src_set)
        self._edges = None

    def edges(self, kinds: str = "call") -> list[dict]:
        """Unit-to-unit edges. kinds='call': resolved call edges only; 'all': plus model-inferred relations."""
        if self._edges is None:
            from cbe.aggregation import unit_edges
            self._edges = unit_edges(self.units, self.cat["edges"])
        return [e for e in self._edges if kinds == "all" or e["kind"] != "relation"]

    def tree0(self) -> "Tree":
        nodes = []
        for nid, n in self.cat["nodes"].items():
            nodes.append(dict(id=nid, parent=n.get("parent") or None, title=n.get("title", ""),
                              capability=n.get("capability", ""), summary=n.get("summary", ""),
                              unit_ids=list(n.get("unit_ids") or [])))
        return Tree("T0-" + self.name, nodes)

    def tree1(self, files: bool = False) -> "Tree":
        """Directory tree: one node per directory prefix; a unit sits in the directory of its main file.
        With files=True every file is a node under its directory and the units sit in their file's node (T1f)."""
        nodes = {".": dict(id=".", parent=None, title=".", capability="", summary="", unit_ids=[])}
        for uid in sorted(self.units):
            d = os.path.dirname(self.unit_file[uid]) or "."
            parts = [] if d == "." else d.split("/")
            for i in range(len(parts)):
                pid = "/".join(parts[:i + 1])
                if pid not in nodes:
                    par = "/".join(parts[:i]) or "."
                    nodes[pid] = dict(id=pid, parent=par, title=pid, capability="", summary="", unit_ids=[])
            if files:
                fid = self.unit_file[uid]
                if fid not in nodes:
                    nodes[fid] = dict(id=fid, parent=d, title=fid, capability="", summary="", unit_ids=[])
                nodes[fid]["unit_ids"].append(uid)
            else:
                nodes[d]["unit_ids"].append(uid)
        return Tree(("T1f-" if files else "T1-") + self.name, list(nodes.values()))

    def cochange(self) -> dict:
        """Pair weights of snapshot non-test source files changed together (history up to the snapshot)."""
        cache = LAB / "cochange" / f"{self.name}.json"
        if cache.exists():
            raw = json.load(open(cache))
            return {tuple(k.split("\t")): v for k, v in raw["pairs"].items()}
        import itertools
        log = subprocess.run(["git", "-C", str(self.clone), "log", "--no-merges", "--name-only", "--format=@@%H", self.sha],
                             capture_output=True, text=True, check=True).stdout
        w = Counter()
        used = 0
        for block in log.split("@@")[1:]:
            fs = sorted({l for l in block.splitlines()[1:] if l in self.src_set})
            if 2 <= len(fs) <= 15:
                used += 1
                for a, b in itertools.combinations(fs, 2):
                    w[a, b] += 1.0 / (len(fs) - 1)
        cache.parent.mkdir(parents=True, exist_ok=True)
        json.dump(dict(commits_used=used, pairs={f"{a}\t{b}": x for (a, b), x in w.items()}), open(cache, "w"))
        return dict(w)


# ------------------------------------------------------------------- tree

def load_tree(path: str | Path) -> "Tree":
    d = json.load(open(path))
    return Tree(d["name"], d["nodes"])


class Tree:
    def __init__(self, name: str, nodes: list[dict]):
        self.name = name
        self.nodes = {n["id"]: n for n in nodes}
        self.children: dict[str, list[str]] = defaultdict(list)
        for n in nodes:
            if n.get("parent") in self.nodes:
                self.children[n["parent"]].append(n["id"])
        self.roots = [n["id"] for n in nodes if n.get("parent") not in self.nodes]
        self.owners: dict[str, list[str]] = defaultdict(list)
        for n in nodes:
            for u in n.get("unit_ids") or []:
                self.owners[u].append(n["id"])

    def chain(self, nid: str) -> list[str]:
        """Root ... nid."""
        out = [nid]
        while self.nodes[out[-1]].get("parent") in self.nodes:
            out.append(self.nodes[out[-1]]["parent"])
        return out[::-1]

    def depth(self, nid: str) -> int:
        return len(self.chain(nid)) - 1

    def owner(self, uid: str) -> str | None:
        o = self.owners.get(uid)
        return o[0] if o else None

    # ---- cuts: unit -> group node id
    def cut(self, kind: str, units) -> dict[str, str]:
        """kind: 'leaf' (the owning node), 'up1' (leaf nodes folded into their parent, unless the parent is the root), 'top'
        (children of the first branching node), or 'depth:K' (ancestor at depth <= K)."""
        out = {}
        branch = None
        if kind == "top":
            # one virtual root over several roots counts as branching
            if len(self.roots) != 1:
                branch = None
            else:
                b = self.roots[0]
                while len(self.children[b]) == 1 and not self.nodes[b].get("unit_ids"):
                    b = self.children[b][0]
                branch = b
        for u in units:
            o = self.owner(u)
            if o is None:
                continue
            ch = self.chain(o)
            if kind == "leaf":
                g = o
            elif kind == "up1":
                g = o if self.children[o] or len(ch) <= 2 else ch[-2]   # never fold into the root
            elif kind == "top":
                if branch is None:
                    g = ch[0]
                elif branch in ch:
                    i = ch.index(branch)
                    g = branch if o == branch else ch[i + 1]
                else:
                    g = ch[0]
            elif kind.startswith("depth:"):
                g = ch[min(int(kind[6:]), len(ch) - 1)]
            else:
                raise ValueError(kind)
            out[u] = g
        return out


# ------------------------------------------------------------------ views

def file_membership(repo: Repo, label: dict[str, str]) -> dict[str, dict[str, float]]:
    """Soft membership of each non-test source file: share of its unit lines that sit in each group."""
    cnt: dict[str, Counter] = defaultdict(Counter)
    for uid, d in repo.unit_lines.items():
        g = label.get(uid)
        if g is None:
            continue
        for p, l in d.items():
            if p in repo.src_set:
                cnt[p][g] += l
    out = {}
    for p, c in cnt.items():
        t = sum(c.values())
        if t:
            out[p] = {g: x / t for g, x in c.items()}
    return out


def group_lines(repo: Repo, label: dict[str, str]) -> Counter:
    c = Counter()
    for uid, d in repo.unit_lines.items():
        g = label.get(uid)
        if g is not None:
            c[g] += sum(l for p, l in d.items() if p in repo.src_set)
    return c


def view_groups(repo: Repo, tree: Tree, label: dict[str, str]) -> list[dict]:
    """One entry per module that holds source lines: id, title, capability, lines, top-3 files."""
    files: dict[str, Counter] = defaultdict(Counter)
    for uid, d in repo.unit_lines.items():
        g = label.get(uid)
        if g is None:
            continue
        for p, l in d.items():
            if p in repo.src_set:
                files[g][p] += l
    out = []
    for g, c in files.items():
        n = tree.nodes[g]
        top = sorted(c, key=lambda p: (-c[p], p))[:3]
        out.append(dict(id=g, title=n.get("title") or g, capability=n.get("capability") or "",
                        lines=sum(c.values()), files=top))
    out.sort(key=lambda x: x["id"])
    return out
