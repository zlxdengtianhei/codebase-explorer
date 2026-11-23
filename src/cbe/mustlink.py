"""Units that must be grouped together, merged into one candidate before the leaf layer is cut.

The model groups units; it can only put in one group what one task sees. A leaf task
sees one chunk of units (design 2.3: at most ``MAX_CHUNK_MEMBERS``), and the chunks are
cut after the candidate grouping, so two units that belong to one module but land in
different chunks can never be grouped, however good the answer. The program therefore
merges, before the chunking, the unit sets that must end up in one candidate:

* **declaration / implementation** - a type declared in a type-only file (``.d.ts``) or
  by an ``interface`` / ``type_alias`` unit, and the class, function or method of the
  same name in the code file that implements it;
* **test / subject** - a unit in a test file and the unit of the same name in the file
  the test file is named after, or the unit a run's graph shows the test calling. A test
  file whose stem names no subject (``__init__``, ``index``, ``main``: see
  ``GENERIC_STEMS``) is paired by the graph only, and two region units are not paired on
  a shared name: ``app = Flask(__name__)`` in two unrelated ``__init__.py`` files is not
  a test and its subject;
* **header / source** - a unit declared in ``x.h`` and the unit of the same name
  defined in ``x.c`` (also ``.hpp`` / ``.cpp`` and the C++ spellings).

The signals are name and path rules read off the unit id alone. They need no model
call, no graph and no git history, and the same input gives the same pairs. Merging is
transitive (union-find): a declaration linked to two implementation units puts three
units in one candidate.

A merged set whose members fit one group (``max_group``) is marked in the chunk and
checked in the answer: an answer that splits it is asked again once. A larger set does
not fit one page at all; its units still reach the same task, so the author can divide
them by function with the declaration in view, and that answer is not checked.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

#: Files that carry types only; a unit there is a declaration, never an implementation.
TYPE_ONLY_SUFFIXES = (".d.ts", ".d.mts", ".d.cts")
#: A type unit's kind, whatever file it sits in.
DECLARATION_KINDS = frozenset({"interface", "type_alias"})
#: Units that implement something. ``module_region`` / ``module_residual`` name a file
#: region, not a symbol, so their name alone never matches a declaration.
IMPLEMENTATION_KINDS = frozenset({"class", "function", "method"})
HEADER_SUFFIXES = (".h", ".hpp", ".hh", ".hxx")
SOURCE_SUFFIXES = (".c", ".cc", ".cpp", ".cxx", ".m", ".mm")
HEADER_SIDE = frozenset({"header"})
_TEST_DIRS = frozenset({"test", "tests", "spec", "specs", "__tests__", "testing", "testdata"})
_TEST_FILE = re.compile(r"(^test_)|(_test\.)|(\.test\.)|(\.spec\.)|(\.tests\.)|(_spec\.)|"
                        r"(Tests?\.(java|kt|rb|py|ts|js)$)", re.IGNORECASE)
_TEST_MARKERS = ("tests.", "test.", "spec.", "test_", "_test", "_spec")
#: A name found in more code files than this is a word, not a module: linking it would
#: put unrelated work in one candidate (``Options``, ``Config``, ``init``).
MAX_NAME_FILES = 4
#: Stems that name the file's place, not a subject: every ``__init__.py`` in a repository
#: shares the stem ``__init__``, so a test file named after one would be paired with
#: whichever ``__init__.py`` came last. A test with such a stem is still linked by a
#: resolved edge, never by the file name.
GENERIC_STEMS = frozenset({"__init__", "__main__", "index", "mod", "main", "conftest", "setup"})
#: Kinds that name a region of a file rather than a symbol. Their name is a local
#: variable (``app = Flask(__name__)``) or the file name, so it must not decide that two
#: files are about each other.
REGION_KINDS = frozenset({"module_region", "module_residual"})


def _parts(uid: str) -> tuple[str, str, str]:
    """``(path, kind, name)`` from ``path::kind::Name::offset``; empty strings otherwise."""
    pieces = uid.split("::")
    if len(pieces) < 3:
        return "", "", ""
    return pieces[0], pieces[1], pieces[2]


def _base(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _stem(path: str) -> str:
    """``src/plugins/plugin.tooltip.js`` -> ``plugin.tooltip``; ``tests/test_basic.py`` -> ``basic``."""
    name = _base(path)
    for marker in _TEST_MARKERS:
        index = name.find(marker)
        if index == 0:
            name = name[len(marker):]
            break
        if index > 0:
            name = name[:index]
            break
    for suffix in TYPE_ONLY_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    dot = name.rfind(".")
    return name[:dot] if dot > 0 else name


def is_test_path(path: str) -> bool:
    """A path under a test directory, or a file named like a test."""
    pieces = path.split("/")
    return (any(piece.lower() in _TEST_DIRS for piece in pieces[:-1])
            or bool(_TEST_FILE.search(pieces[-1])))


def _is_type_only(path: str) -> bool:
    return path.endswith(TYPE_ONLY_SUFFIXES)


def _side(path: str) -> str:
    """``header``, ``source`` or ``""`` for a C/C++ file, by suffix."""
    for suffix in HEADER_SUFFIXES:
        if path.endswith(suffix):
            return "header"
    for suffix in SOURCE_SUFFIXES:
        if path.endswith(suffix):
            return "source"
    return ""


class _Sets:
    """Union-find over hashable keys."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, uid: str) -> str:
        self.parent.setdefault(uid, uid)
        root = uid
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[uid] != root:
            self.parent[uid], uid = root, self.parent[uid]
        return root

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[max(ra, rb)] = min(ra, rb)
        return True


def links(units: dict, edges: list[dict] | None = None) -> dict:
    """The unit pairs the program links, and how many came from each rule.

    The three name rules read the unit id alone; the test rule also adds the edges a run
    resolved from a test unit into a subject unit, because that is the strongest signal
    for "this test is about that code" when the names do not say so."""
    pairs: list[tuple[str, str]] = []
    families: Counter = Counter()
    skipped: Counter = Counter()
    by_name: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    by_file: dict[str, list[str]] = defaultdict(list)
    kind_of: dict[str, str] = {}
    for uid in units:
        path, kind, name = _parts(uid)
        if not path:
            continue
        kind_of[uid] = kind
        by_file[path].append(uid)
        key = name.strip().lower()
        if key and name != "<region>":
            by_name[key][path].append(uid)
    # A declaration names a type or a symbol; a method inside an interface does not (its
    # name is a field), so method units are never the declaration side of a link.
    declared = {uid for uid in units
                if kind_of.get(uid) in DECLARATION_KINDS
                or (_is_type_only(_parts(uid)[0]) and kind_of.get(uid) in IMPLEMENTATION_KINDS - {"method"})}
    implemented = {uid for uid in units
                   if kind_of.get(uid) in IMPLEMENTATION_KINDS - {"method"}
                   and not _is_type_only(_parts(uid)[0])}
    seen: set[tuple[str, str]] = set()

    def add(a: str, b: str, family: str) -> None:
        key = (a, b) if a < b else (b, a)
        if a == b or key in seen:
            return
        seen.add(key)
        pairs.append(key)
        families[family] += 1

    # A declaration and the same name implemented in code. A name that several files use
    # is a word, not a module: linking it would put unrelated work in one candidate.
    for name, files in by_name.items():
        code_files = sorted(path for path in files if not _is_type_only(path))
        if not code_files:
            continue
        if len(files) > MAX_NAME_FILES:
            skipped["a name used by too many files"] += 1
            continue
        heads = [uid for path in files for uid in files[path] if uid in declared]
        tails = [uid for path in code_files for uid in files[path] if uid in implemented]
        for head in heads:
            for tail in tails:
                if _parts(head)[0] != _parts(tail)[0]:
                    add(head, tail, "declaration/implementation")

    # A test unit and the unit it exercises: the same name in the file the test file is
    # named after, or an edge a run resolved from the test into the subject.
    subjects: dict[str, list[str]] = defaultdict(list)
    for path in by_file:
        if is_test_path(path) or _stem(path) in GENERIC_STEMS:
            continue
        subjects[_stem(path)].append(path)
    for path in sorted(by_file):
        if not is_test_path(path):
            continue
        if _stem(path) in GENERIC_STEMS:
            skipped["test file named after a generic stem"] += 1
            continue
        before = families["test/subject"]
        for subject in subjects.get(_stem(path), []):
            if subject == path:
                continue
            # A region is named after a local variable or the file, not a symbol. Two regions
            # that share a name (flask's ``app = Flask(__name__)`` in two ``__init__.py``
            # files) are two variables that happen to be called the same, not a test and its
            # subject. A region named after a function or class the other file defines is a
            # link (Chart.js: a ``describe('_filterBetween', ...)`` block against the
            # function of that name).
            names = {_parts(other)[2].strip().lower() for other in by_file[subject]} - {"", "<region>"}
            for uid in by_file[path]:
                name = _parts(uid)[2].strip().lower()
                if not name or name not in names:
                    continue
                for other in by_file[subject]:
                    if _parts(other)[2].strip().lower() != name:
                        continue
                    if kind_of.get(uid) in REGION_KINDS and kind_of.get(other) in REGION_KINDS:
                        continue
                    add(uid, other, "test/subject")
        if families["test/subject"] == before:
            skipped["test file whose units match no subject unit"] += 1
    test_files = {path for path in by_file if is_test_path(path)}
    for edge in edges or []:
        source, target = edge.get("from"), edge.get("to")
        if source not in units or target not in units:
            continue
        if _parts(source)[0] in test_files and _parts(target)[0] not in test_files:
            add(source, target, "test/subject")

    # A header and a source file of the same stem: the declaration and its definition.
    stems: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path in by_file:
        side = _side(path)
        if not side:
            continue
        suffix = next(s for s in HEADER_SUFFIXES + SOURCE_SUFFIXES if path.endswith(s))
        stems[_base(path)[: -len(suffix)]][side].append(path)
    for sides in stems.values():
        for header in sides["header"]:
            for source in sides["source"]:
                names = {_parts(other)[2].strip().lower() for other in by_file[source]} - {"", "<region>"}
                for uid in by_file[header]:
                    name = _parts(uid)[2].strip().lower()
                    if name and name in names:
                        for other in by_file[source]:
                            if _parts(other)[2].strip().lower() == name:
                                add(uid, other, "header/source")
    return {"pairs": pairs, "families": dict(sorted(families.items())),
            "skipped": dict(sorted(skipped.items()))}


def merge(candidates: list[list[str]], pairs: list[tuple[str, str]], *,
          max_group: int) -> dict:
    """Candidate groups that each hold whole linked sets; the linked sets themselves.

    A set's units move into one candidate: the candidate that already holds most of the
    set (the lowest index on a tie), because that is the one whose other units the set
    sat near anyway. The other candidates lose those units; one that loses all of them
    drops out. Moving units - not merging candidates - keeps the hint narrow: two
    unrelated sets that happen to touch the same candidate stay apart.

    ``linked`` holds the sets that fit one group (``max_group`` members): those a chunk
    marks and an answer is checked against. ``oversized`` holds the sets above that: they
    sit in one candidate, but no page can hold them, so they are divided by function and
    not checked."""
    sets = _Sets()
    for group in candidates:
        for uid in group:
            sets.find(uid)
    outside = 0
    for a, b in pairs:
        if a not in sets.parent or b not in sets.parent:
            outside += 1
            continue
        sets.union(a, b)
    members_of: dict[str, list[str]] = defaultdict(list)
    for uid in sets.parent:
        members_of[sets.find(uid)].append(uid)
    home_of_candidate: dict[str, int] = {}
    owner: dict[str, int] = {}
    for index, group in enumerate(candidates):
        for uid in group:
            owner.setdefault(uid, index)
    for root, members in members_of.items():
        if len(members) < 2:
            continue
        counts: Counter = Counter(owner.get(uid, -1) for uid in members)
        home_of_candidate[root] = min(counts, key=lambda index: (-counts[index], index))
    moved: dict[int, list[str]] = defaultdict(list)
    for root, home in home_of_candidate.items():
        if home < 0:
            continue
        for uid in members_of[root]:
            moved[home].append(uid)
    staying: dict[str, int] = {}
    for root, home in home_of_candidate.items():
        if home >= 0:
            for uid in members_of[root]:
                staying[uid] = home
    merged: list[list[str]] = []
    for index, group in enumerate(candidates):
        kept = [uid for uid in group if staying.get(uid, index) == index]
        kept.extend(sorted(moved.get(index, [])))
        if kept:
            merged.append(sorted(set(kept)))
    linked, oversized = [], []
    for root, members in sorted(members_of.items(), key=lambda row: sorted(row[1])[0]):
        if len(members) < 2:
            continue
        (linked if len(members) <= max_group else oversized).append(sorted(members))
    return {"candidates": merged, "linked": linked, "oversized": oversized,
            "outside": outside, "sets_moved": sum(len(group) for group in moved.values())}
