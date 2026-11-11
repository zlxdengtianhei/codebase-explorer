"""The structured-detail / ownership-tree / render engine.

These tests pin the contract the generation stage relies on: hard validation
covers identity, coverage and ownership; length and count measures stay
diagnostics and never trigger a repair; and the program, not the model, derives
published source ranges.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from cbe import checks, docs, symbols, catalog_query


SRC = (
    "import typing\n"
    "\n"
    "@typing.overload\n"
    "def reserve(value: int) -> int: ...\n"
    "def reserve(value):\n"
    "    if value < 0:\n"
    "        raise ValueError('negative')\n"
    "    return value\n"
    "\n"
    "class Pool:\n"
    "    def submit(self, value):\n"
    "        return reserve(value)\n"
)


def _inventory() -> dict:
    """Inventory of ``SRC`` from a hand-written chunk set with readable ids.

    Ids are opaque strings to every consumer; a real run supplies grammar ids."""
    lines = SRC.splitlines(keepends=True)
    spans = [("pkg/jobs.py::reserve", "reserve", "function", 3, 4),
             ("pkg/jobs.py::reserve@5", "reserve", "function", 5, 8),
             ("pkg/jobs.py::Pool", "Pool", "class", 10, 12),
             ("pkg/jobs.py::Pool.submit", "Pool.submit", "method", 11, 12),
             ("pkg/jobs.py::<module top-level>", "<module top-level>", "module_region", 1, 3)]
    context = {"schema": "cbe-context/1", "graph": None, "diagnostics": [],
               "files": [{"path": "pkg/jobs.py", "language": "python", "sha256": "d"}],
               "chunks": [{"id": uid, "path": "pkg/jobs.py", "kind": kind, "name": name,
                           "start_line": start, "end_line": end, "text": "".join(lines[start - 1:end])}
                          for uid, name, kind, start, end in spans]}
    return symbols.inventory_from_context(context)


def _good_payload(inventory: dict) -> dict:
    units, dispositions = [], {}
    for row in inventory["pkg/jobs.py"]["symbols"]:
        units.append({"id": row["id"], "kind": row["kind"],
                      "explain": f"{row['name']} does its job.",
                      "extras": [], "relations": [], "uncertainties": []})
        dispositions[row["id"]] = {"how": "unit", "unit": row["id"], "reason": "behavior"}
    return {"units": units, "dispositions": dispositions, "batch_notes": "ok"}


def test_unit_ranges_come_from_the_inventory_not_the_model() -> None:
    inventory = _inventory()
    unit = {"id": "pkg/jobs.py::Pool", "kind": "class",
            "members": ["pkg/jobs.py::Pool.submit", "pkg/jobs.py::does-not-exist"]}
    ranges = docs.unit_ranges("pkg/jobs.py::Pool", unit, inventory)
    assert [entry["path"] for entry in ranges] == ["pkg/jobs.py"]
    covered = [pair for entry in ranges for pair in entry["lines"]]
    assert any(pair[0] == 10 for pair in covered)  # class line
    assert any(pair[0] == 11 for pair in covered)  # folded member line
    assert docs.unit_ranges("grp:pool-helpers", {"id": "grp:pool-helpers"}, inventory) == []


def _tree(unit_ids: list[str], **overrides) -> dict:
    node = {"id": "root", "parent": None, "title": "Root",
            "capability": "Every source unit under one responsibility root.",
            "summary": "Start here.", "unit_ids": unit_ids}
    node.update(overrides)
    return {"nodes": [node], "depends_on": []}


def test_render_publishes_node_pages_source_links_and_a_compatible_catalog(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "jobs.py").write_text(SRC, encoding="utf-8")
    inventory = _inventory()
    units = {row["id"]: {"id": row["id"], "kind": row["kind"],
                         "explain": f"{row['name']} does its job.",
                         "extras": [], "relations": [], "uncertainties": []}
             for row in inventory["pkg/jobs.py"]["symbols"]}
    dispositions = {uid: {"how": "unit", "unit": uid, "reason": "behavior"} for uid in units}
    tree = _tree(sorted(units))
    run_dir = tmp_path / "run"
    meta = docs.render(run_dir=run_dir, source_root=repo, inventory=inventory,
                           units=units, dispositions=dispositions, tree=tree,
                           languages={"pkg/jobs.py": "python"})
    assert meta["nodes"] == 1
    index = (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "](nodes/root.md)" in index
    page = (run_dir / "docs" / "nodes" / "root.md").read_text(encoding="utf-8")
    assert "pkg/jobs.py" in page and "L1-L" in page  # program-derived source link
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["units"] and catalog["symbols"]["pkg/jobs.py::Pool"]["file"] == "pkg/jobs.py"
    checks = {row["check"]: row["ok"] for row in
              docs.verify(run_dir, inventory, units, dispositions, tree)}
    assert checks["unique_primary_ownership"] and checks["relative_links_resolve"]


def test_verify_flags_an_empty_node_and_sibling_nodes_with_the_same_title(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "jobs.py").write_text(SRC, encoding="utf-8")
    inventory = _inventory()
    ids = [row["id"] for row in inventory["pkg/jobs.py"]["symbols"]]
    units = {uid: {"id": uid, "kind": "function", "explain": "Does its job.", "extras": [], "relations": [],
                   "uncertainties": []} for uid in ids}
    dispositions = {uid: {"how": "unit", "unit": uid} for uid in ids}

    def node(nid, parent, title, unit_ids):
        return {"id": nid, "parent": parent, "title": title, "capability": "c" * 50, "summary": "s",
                "unit_ids": unit_ids}

    good = {"nodes": [node("root", None, "Root", []), node("a", "root", "Alpha", ids[:1]),
                      node("b", "root", "Beta", ids[1:])], "depends_on": []}
    run = tmp_path / "run"
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units, dispositions=dispositions,
                tree=good, languages={"pkg/jobs.py": "python"})

    def failed(tree):
        return {row["check"] for row in docs.verify(run, inventory, units, dispositions, tree) if not row["ok"]}

    assert not failed(good) & {"no_empty_nodes", "sibling_titles_distinct"}
    hollow = {"nodes": good["nodes"] + [node("c", "root", "Gamma", [])], "depends_on": []}
    assert "no_empty_nodes" in failed(hollow)
    twin = {"nodes": [good["nodes"][0], good["nodes"][1], {**good["nodes"][2], "title": " alpha! "}],
            "depends_on": []}
    assert "sibling_titles_distinct" in failed(twin)


def test_catalog_language_is_the_frozen_context_language(tmp_path) -> None:
    repo = tmp_path / "repo"
    (repo / "ui").mkdir(parents=True)
    (repo / "ui" / "view.tsx").write_text("export const View = () => <div/>;\n", encoding="utf-8")
    (repo / "ui" / "shape.h").write_text("struct Shape { int w; };\n", encoding="utf-8")
    context = {"schema": "cbe-context/1", "graph": None, "diagnostics": [],
               "files": [{"path": "ui/view.tsx", "language": "tsx", "sha256": "a"},
                         # Planned with --header-language cpp: the frozen row wins.
                         {"path": "ui/shape.h", "language": "cpp", "sha256": "b"}],
               "chunks": [{"id": "ui/view.tsx::View", "path": "ui/view.tsx", "kind": "function",
                           "name": "View", "start_line": 1, "end_line": 1,
                           "text": "export const View = () => <div/>;\n"},
                          {"id": "ui/shape.h::Shape", "path": "ui/shape.h", "kind": "class",
                           "name": "Shape", "start_line": 1, "end_line": 1,
                           "text": "struct Shape { int w; };\n"}]}
    inventory = symbols.inventory_from_context(context)
    units = {uid: {"id": uid, "kind": "function", "explain": "x", "extras": [], "relations": [],
                   "uncertainties": []} for uid in symbols.inventory_ids(inventory)}
    dispositions = {uid: {"how": "unit", "unit": uid, "reason": "behavior"} for uid in units}
    run_dir = tmp_path / "run"
    docs.render(run_dir=run_dir, source_root=repo, inventory=inventory, units=units,
                dispositions=dispositions, tree=_tree(sorted(units)),
                languages={row["path"]: row["language"] for row in context["files"]})
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    assert {path: row["language"] for path, row in catalog["files"].items()} == {
        "ui/view.tsx": "tsx", "ui/shape.h": "cpp"}


def _grouped_run(tmp_path):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC, encoding="utf-8")
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {row["id"]: row for row in payload["units"]}
    dispositions = payload["dispositions"]
    members = ["pkg/jobs.py::reserve", "pkg/jobs.py::Pool.submit"]
    group = "grp:job-dispatch"
    for sid in members:
        units.pop(sid)
        dispositions[sid] = {"how": "grouped", "unit": group, "reason": "shared operation"}
    index_only = "pkg/jobs.py::<module top-level>"
    units.pop(index_only)
    dispositions[index_only] = {"how": "index_only", "reason": "import metadata"}
    units[group] = {"id": group, "kind": "group", "members": members,
                    "explain": "Reserve and submit a job.", "extras": [],
                    "relations": [], "uncertainties": []}
    tree = _tree(sorted(units))
    run = tmp_path / "run"
    docs.render(run_dir=run, source_root=repo, inventory=inventory,
                    units=units, dispositions=dispositions, tree=tree,
                    languages={"pkg/jobs.py": "python"})
    return run, inventory, units, dispositions, tree, members, group, index_only


@pytest.mark.parametrize("old_catalog", [False, True])
def test_find_and_query_resolve_grouped_symbols_units_and_index_only(tmp_path, old_catalog) -> None:
    run, inventory, units, dispositions, tree, members, group, index_only = _grouped_run(tmp_path)
    catalog_path = run / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    # Existing real runs have this stale compatibility view. Queries must work
    # without regenerating the model output or rewriting its catalog.
    if old_catalog:
        for sid in members:
            catalog["symbols"][sid] = {"file": "pkg/jobs.py", "name": sid,
                                       "node": None, "page": None}
        catalog_path.write_text(json.dumps(catalog))
    else:
        assert catalog["symbols"][members[0]]["page"] == "nodes/root.md"
        assert catalog["symbols"][members[0]]["how"] == "grouped"
    before = catalog_path.read_bytes()
    for sid in [*members, group]:
        record = catalog_query.query(run, sid)
        assert record["unit"] == group and record["node"] == "root"
        assert record["page"] == "nodes/root.md"
        assert record["anchor"] == f"#{docs.anchor(group)}"
        found = next(row for row in catalog_query.find(run, sid) if row["id"] == sid)
        assert found["id"] == sid and found["location"] and found["name"]
        assert not {"explain", "incoming", "outgoing", "signatures"} & found.keys()
    record = catalog_query.query(run, index_only)
    assert record["how"] == "index_only" and record["reason"] == "import metadata"
    assert record["page"] is None and record["anchor"] is None
    checks = {row["check"]: row for row in docs.verify(run, inventory, units, dispositions, tree)}
    assert checks["catalog_navigation_resolves"]["ok"], checks
    assert catalog_path.read_bytes() == before


@pytest.mark.parametrize("damage", ["wrong_target", "missing_group", "missing_anchor"])
def test_verification_rejects_broken_published_navigation(tmp_path, damage) -> None:
    run, inventory, units, dispositions, tree, members, group, _ = _grouped_run(tmp_path)
    catalog_path = run / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    if damage == "wrong_target":
        catalog["symbol_index"][members[0]]["anchor"] = "#u-wrong-target"
    elif damage == "missing_group":
        catalog["units"].pop(group)
        catalog["symbol_index"].pop(group)
    else:
        page = run / "docs/nodes/root.md"
        page.write_text(page.read_text().replace(f'<a id="{docs.anchor(group)}"></a>', ""))
    catalog_path.write_text(json.dumps(catalog))
    checks = {row["check"]: row for row in docs.verify(run, inventory, units, dispositions, tree)}
    assert not checks["catalog_navigation_resolves"]["ok"], checks


def test_inventory_from_context_uses_chunk_ids_and_rejects_a_missing_path() -> None:
    context = {"schema": "cbe-context/1",
               "files": [{"path": "a.py", "language": "python", "sha256": "x"}],
               "chunks": [{"id": "chunk-1", "path": "a.py", "language": "python",
                           "kind": "function", "name": "f", "start_line": 1, "end_line": 2,
                           "text": "def f():\n    return 1\n", "sha256": "y"}],
               "graph": None, "diagnostics": []}
    inventory = symbols.inventory_from_context(context, ["a.py"])
    assert inventory["a.py"]["symbols"][0]["id"] == "chunk-1"
    with pytest.raises(symbols.SemanticError):
        symbols.inventory_from_context(context, ["missing.py"])


def test_ensure_chunk_coverage_marks_empty_and_keeps_comment_only(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "empty.py").write_text("", encoding="utf-8")
    (repo / "doc.py").write_text('"""Only a docstring, no declaration."""\n', encoding="utf-8")
    context = {"schema": "cbe-context/1",
               "files": [{"path": "empty.py", "language": "python", "sha256": "e"},
                         {"path": "doc.py", "language": "python", "sha256": "d"}],
               "chunks": [], "graph": None, "diagnostics": []}
    symbols.ensure_chunk_coverage(context, repo, ["empty.py", "doc.py"])
    codes = {(row["path"], row["code"]) for row in context["diagnostics"]}
    assert ("empty.py", "known_empty") in codes
    assert not any(chunk["path"] == "empty.py" for chunk in context["chunks"])
    # A comment/docstring-only file is not empty; it keeps a real reading chunk.
    assert any(chunk["path"] == "doc.py" for chunk in context["chunks"])
    inventory = symbols.inventory_from_context(context, ["empty.py", "doc.py"])
    assert inventory["empty.py"]["symbols"] == [] and inventory["empty.py"]["known_empty"] is True
    assert inventory["doc.py"]["symbols"] and inventory["doc.py"]["known_empty"] is False


def test_ensure_chunk_coverage_digests_the_file_bytes_of_a_crlf_file(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    raw = b"def f():\r\n    return 1\r\n"
    (repo / "crlf.py").write_bytes(raw)
    context = {"schema": "cbe-context/1", "files": [], "chunks": [], "graph": None, "diagnostics": []}
    symbols.ensure_chunk_coverage(context, repo, ["crlf.py"])
    assert context["files"] == [{"path": "crlf.py", "language": "python",
                                 "sha256": hashlib.sha256(raw).hexdigest(),
                                 "source": raw.decode("utf-8")}]
