"""Name the program-made module tree and put the finished tree together.

``skeleton.build`` decides the structure. The model only names it, in two kinds
of task: ``tree_name_<k>`` names a batch of leaf modules and ``tree_top`` names
every internal node. This module holds what those tasks need and nothing about
the task state machine (see ``host_run``): batches, the facts shown to the
model, answer decoding with short numbers, program-made titles for nodes the
model could not name, and the final ``nodes`` list.

A model answer never changes the structure. Answers are decoded node by node: a
good node is kept and only the bad ones are asked again. A node that stays
unnamed gets a title made from its members (frequent words plus the main
directory), so the run always ends with a valid tree.
"""
from __future__ import annotations

import hashlib
import math
import posixpath
import re
import unicodedata
from collections import Counter, defaultdict

from cbe import skeleton
from cbe.records import summary_sentence
from cbe.token_budget import count_text_tokens

BATCH_TOKENS = 12_000     # about this many prompt tokens of member lines per tree_name task
SUMMARY_CHARS = 200
TITLE_WORDS = 9
CAPABILITY_WORDS = 45     # the prompt asks for about 25; an answer above this is sent back
MIN_GROUP_CAPABILITY = 40 # a node with children needs a real sentence, not a fragment
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


def freeze(units: dict[str, dict], edges: list[dict]) -> dict:
    """The skeleton and its leaf batches, as stored in the run state."""
    nodes = skeleton.build(units, edges)["nodes"]
    if not nodes:
        return {"nodes": [], "batches": []}
    return {"nodes": nodes, "batches": plan_batches(Tree(nodes), units)}


def _short(text: str) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= SUMMARY_CHARS else text[:SUMMARY_CHARS - 1].rstrip() + "…"


def plan_batches(tree: Tree, units: dict[str, dict]) -> list[list[str]]:
    """Cut the leaves, in tree order, into batches of about ``BATCH_TOKENS`` tokens."""
    batches: list[list[str]] = []
    current: list[str] = []
    used = 0
    for leaf in tree.leaves():
        size = sum(count_text_tokens(_short(summary_sentence(units[u]))) + 8
                   for u in tree.nodes[leaf]["unit_ids"]) + 60
        if current and used + size > BATCH_TOKENS:
            batches.append(current)
            current, used = [], 0
        current.append(leaf)
        used += size
    if current:
        batches.append(current)
    return batches


# ------------------------------------------------------------ tree_name ----

def name_context(batch: list[str], tree: Tree) -> tuple[dict[str, str], dict[str, str]]:
    """``({label: leaf}, {unit: code})``: the short numbers of one batch, the same on every ask."""
    labels = {f"M{i + 1}": leaf for i, leaf in enumerate(batch)}
    codes: dict[str, str] = {}
    for leaf in batch:
        for unit in sorted(tree.nodes[leaf]["unit_ids"]):
            codes[unit] = f"u{len(codes) + 1}"
    return labels, codes


def _ties(pairs, owner_of):
    out = defaultdict(lambda: defaultdict(int))
    for edge in pairs:
        a, b = owner_of(edge["from"]), owner_of(edge["to"])
        if a and b and a != b:
            out[a][b] += edge["count"]
    return out


def _tie_line(prefix: str, table: dict, name_of) -> str:
    items = sorted(((name_of(o), c) for o, c in table.items() if name_of(o)), key=lambda t: (-t[1], t[0]))
    return f"{prefix}: " + ", ".join(f"{n} x{c}" for n, c in items) if items else ""


def name_blocks(batch: list[str], tree: Tree, units: dict[str, dict], edges: list[dict]) -> list[str]:
    """One text block per leaf module: members by file, calls in and out within the batch."""
    labels, codes = name_context(batch, tree)
    label_of = {leaf: label for label, leaf in labels.items()}
    out_ties = _ties(edges, lambda u: tree.leaf_of.get(u) if tree.leaf_of.get(u) in label_of else None)
    in_ties = defaultdict(lambda: defaultdict(int))
    for a, row in out_ties.items():
        for b, count in row.items():
            in_ties[b][a] += count
    blocks = []
    for leaf in batch:
        members = tree.nodes[leaf]["unit_ids"]
        by_file = defaultdict(list)
        for unit in members:
            by_file[(skeleton.unit_paths(units[unit]) or ["?"])[0]].append(unit)
        lines = [f"## {label_of[leaf]}  ({len(members)} units in {len(by_file)} files)"]
        for path in sorted(by_file):
            lines.append(f"file {path}")
            lines += [f"  {codes[u]}: {_short(summary_sentence(units[u]))}" for u in sorted(by_file[path], key=lambda u: int(codes[u][1:]))]
        for prefix, table in (("calls into", out_ties.get(leaf, {})), ("called from", in_ties.get(leaf, {}))):
            if line := _tie_line(prefix, table, label_of.get):
                lines.append(line)
        blocks.append("\n".join(lines))
    return blocks


def normalize_title(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _text_problem(record: dict, label: str) -> list[str]:
    problems = []
    for key in ("title", "capability", "summary"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            problems.append(f"{label}: {key} is empty")
    if problems:
        return problems
    title = record["title"].strip()
    if len(title) > 90 or len(title.split()) > TITLE_WORDS:
        problems.append(f"{label}: title is too long (2 to 6 words)")
    if len(record["capability"].split()) > CAPABILITY_WORDS:
        problems.append(f"{label}: capability must be one sentence of about 25 words")
    return problems


def decode_names(answer: object, batch: list[str], tree: Tree, pending: set[str], taken: set[str]) -> tuple[dict, dict]:
    """Decode one ``tree_name`` answer for the leaves in ``pending``.

    Returns ``(good, errors)``: ``good`` maps a leaf to its record, ``errors`` maps a leaf to what
    is wrong. ``taken`` holds the normalized titles accepted from earlier answers of this batch."""
    labels, codes = name_context(batch, tree)
    by_code = {code: unit for unit, code in codes.items()}
    rows = answer.get("modules") if isinstance(answer, dict) else None
    if not isinstance(rows, list):
        raise ValueError('answer needs {"modules": [...]}')
    seen: dict[str, dict] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("id") in labels and row["id"] not in seen:
            seen[row["id"]] = row
    used = set(taken)       # titles kept so far: the first of two equal titles stays, the later one is asked again
    good: dict[str, dict] = {}
    errors: dict[str, list[str]] = {}
    for label, leaf in labels.items():
        if leaf not in pending:
            continue
        row = seen.get(label)
        if row is None:
            errors[leaf] = [f"module {label} is missing from the answer"]
            continue
        problems = _text_problem(row, label)
        title = str(row.get("title", "")).strip()
        if title and normalize_title(title) in used:
            problems.append(f"{label}: title {title!r} is used by another module of this batch")
        members = set(tree.nodes[leaf]["unit_ids"])
        evidence = row.get("evidence_units")
        want = min(2, len(members))
        if (not isinstance(evidence, list) or any(not isinstance(e, str) or by_code.get(e) not in members for e in evidence)
                or len(set(evidence)) < want):
            problems.append(f"{label}: evidence_units needs {want} to 4 unit numbers that belong to {label}")
        if problems:
            errors[leaf] = problems
            continue
        used.add(normalize_title(title))
        good[leaf] = {"title": title, "capability": row["capability"].strip(), "summary": row["summary"].strip(),
                      "evidence_units": [by_code[e] for e in dict.fromkeys(evidence)][:4]}
    return good, errors


# ------------------------------------------------------------- tree_top ----

def top_context(tree: Tree) -> dict[str, str]:
    """``{label: internal node}`` in tree order (the root is G1)."""
    return {f"G{i + 1}": node for i, node in enumerate(tree.internals())}


def top_blocks(tree: Tree, names: dict[str, dict], units: dict[str, dict], edges: list[dict]) -> list[str]:
    """One block per internal node: its children (named leaves, or the group that names them) and their ties."""
    label_of = {node: label for label, node in top_context(tree).items()}

    def child_name(node: str) -> str:
        return names[node]["title"] if node in names else f"group {label_of[node]}"

    blocks = []
    for node, label in label_of.items():
        kids = tree.kids[node]
        home = {u: kid for kid in kids for u in tree.members(kid)}
        ties = _ties([e for e in edges if e["from"] in home and e["to"] in home], home.get)
        lines = [f"## {label}  ({len(tree.members(node))} units)", "children:"]
        for kid in kids:
            what = f": {names[kid]['capability']}" if kid in names else ""
            lines.append(f"- {child_name(kid)} ({len(tree.members(kid))} units){what}")
        flows = [f"{child_name(a)} -> {child_name(b)} x{c}"
                 for a in kids for b, c in sorted(ties[a].items(), key=lambda t: -t[1])[:3]]
        if flows:
            lines.append("edges between children: " + "; ".join(flows))
        blocks.append("\n".join(lines))
    return blocks


def decode_top(answer: object, tree: Tree, names: dict[str, dict], pending: set[str], taken: set[str]) -> tuple[dict, dict]:
    """Decode one ``tree_top`` answer for the internal nodes in ``pending`` (same return as ``decode_names``)."""
    groups = top_context(tree)
    rows = answer.get("groups") if isinstance(answer, dict) else None
    if not isinstance(rows, list):
        raise ValueError('answer needs {"groups": [...]}')
    seen: dict[str, dict] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("id") in groups and row["id"] not in seen:
            seen[row["id"]] = row
    used = set(taken)
    good: dict[str, dict] = {}
    errors: dict[str, list[str]] = {}
    for label, node in groups.items():
        if node not in pending:
            continue
        row = seen.get(label)
        if row is None:
            errors[node] = [f"group {label} is missing from the answer"]
            continue
        problems = _text_problem(row, label)
        title = str(row.get("title", "")).strip()
        kid_titles = {normalize_title(names[k]["title"]) for k in tree.kids[node] if k in names}
        if title and (normalize_title(title) in used or normalize_title(title) in kid_titles):
            problems.append(f"{label}: title {title!r} repeats the title of another group or of one of its children")
        if not problems and len(row["capability"].strip()) < MIN_GROUP_CAPABILITY:
            problems.append(f"{label}: capability must be a full sentence")
        if problems:
            errors[node] = problems
            continue
        used.add(normalize_title(title))
        good[node] = {"title": title, "capability": row["capability"].strip(), "summary": row["summary"].strip(),
                      "evidence_units": []}
    return good, errors


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
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for edge in edges:
        pa, pb = path_of.get(edge["from"]), path_of.get(edge["to"])
        if not pa or not pb or edge["from"] == edge["to"]:
            continue
        depth = next((i for i, (x, y) in enumerate(zip(pa, pb)) if x != y), None)
        if depth is None:
            continue
        if edge["kind"] in ("call", "import") and edge.get("provenance") != "model_inferred":
            counts[pa[depth], pb[depth]][0] += edge["count"]
        elif edge["kind"] == "relation":
            counts[pa[depth], pb[depth]][1] += edge["count"]
    return [{"from": a, "to": b, "basis": f"{r} resolved call/import edge(s)" if r else f"{m} model-inferred relation(s)"}
            for (a, b), (r, m) in sorted(counts.items()) if r or m]


def slugs(tree: Tree, titles: dict[str, str]) -> dict[str, str]:
    """Node ids people can read and type: the title as lower-case ASCII words joined by hyphens.

    The first node to use a slug keeps it; a later node, or one whose title has no ASCII letter, gets a
    short hash of its skeleton id (the same input always gives the same ids)."""
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


def assemble(tree: Tree, records: dict[str, dict], units: dict[str, dict], edges: list[dict], repo: str) -> dict:
    """The tree in the published shape. A node without a record gets a program-made one, and so does a
    node whose title a sibling already uses; both carry a ``note``."""
    made: dict[str, dict] = {}
    for node in tree.order:
        record = records.get(node)
        if record is None:
            made[node] = program_record(units, tree.members(node))
            if node == tree.root:
                made[node]["title"] = repo
        else:
            made[node] = dict(record)
    for parent in tree.internals():
        used: set[str] = set()
        for kid in tree.kids[parent]:
            if normalize_title(made[kid]["title"]) in used:
                others = [tree.members(o) for o in tree.kids[parent] if o != kid]
                made[kid] = program_record(units, tree.members(kid), avoid=used | {normalize_title(made[o]["title"]) for o in tree.kids[parent] if o != kid},
                                           siblings=others)
                made[kid]["note"] = "program-made title (a sibling had the same title)"
            used.add(normalize_title(made[kid]["title"]))
    ids = slugs(tree, {node: made[node]["title"] for node in tree.order})
    nodes = []
    for node in tree.order:
        record = made[node]
        inside = set(tree.members(node))
        parent = tree.nodes[node]["parent"]
        row = {"id": ids[node], "parent": ids[parent] if parent else None, "title": record["title"],
               "capability": record["capability"], "summary": record["summary"],
               "unit_ids": sorted(tree.nodes[node]["unit_ids"]),
               "evidence_units": [u for u in record.get("evidence_units") or [] if u in inside]}
        note = record.get("note") or ("program-made title" if record.get("program_made") else None)
        if note:
            row["note"] = note
        nodes.append(row)
    return {"nodes": nodes, "depends_on": [{**dep, "from": ids[dep["from"]], "to": ids[dep["to"]]}
                                           for dep in dependencies(tree, edges)]}
