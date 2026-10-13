"""The structured-detail / ownership-tree / render engine.

These tests pin the contract the generation stage relies on: hard validation
covers identity, coverage and ownership; length and count measures stay
diagnostics and never trigger a repair; and the program, not the model, derives
published source ranges.
"""

from __future__ import annotations

import json

import pytest

from cbe import semantic


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
    return semantic.build_inventory({"pkg/jobs.py": {"source": SRC, "digest": "d", "tokens": 40}})


def test_python_inventory_ids_are_unique_for_overloads_and_cover_the_module() -> None:
    inventory = _inventory()
    ids = [row["id"] for row in inventory["pkg/jobs.py"]["symbols"]]
    assert len(ids) == len(set(ids)), ids
    assert "pkg/jobs.py::reserve" in ids
    assert sum(1 for uid in ids if uid.startswith("pkg/jobs.py::reserve")) == 2
    assert "pkg/jobs.py::Pool" in ids and "pkg/jobs.py::Pool.submit" in ids
    assert "pkg/jobs.py::<module top-level>" in ids


def _good_payload(inventory: dict) -> dict:
    units, dispositions = [], {}
    for row in inventory["pkg/jobs.py"]["symbols"]:
        units.append({"id": row["id"], "kind": row["kind"],
                      "explain": f"{row['name']} does its job.",
                      "extras": [], "relations": [], "uncertainties": []})
        dispositions[row["id"]] = {"how": "unit", "unit": row["id"], "reason": "behavior"}
    return {"units": units, "dispositions": dispositions, "batch_notes": "ok"}


def test_validate_details_accepts_a_complete_payload() -> None:
    inventory = _inventory()
    assert semantic.validate_details(_good_payload(inventory), ["pkg/jobs.py"], inventory, set()) == []


def test_validate_details_flags_missing_disposition_unknown_kind_and_bad_relation() -> None:
    inventory = _inventory()
    payload = _good_payload(inventory)
    dropped = "pkg/jobs.py::<module top-level>"
    payload["dispositions"].pop(dropped)
    payload["units"][0]["kind"] = "macro"
    payload["units"][0]["relations"] = [{"target": "pkg/jobs.py::reserve", "kind": "likes"}]
    problems = semantic.validate_details(payload, ["pkg/jobs.py"], inventory, set())
    joined = "\n".join(problems)
    assert dropped in joined
    assert "kind must be one of" in joined and "got 'macro'" in joined
    assert "relation kind" in joined and "got 'likes'" in joined


def test_length_is_a_diagnostic_not_a_hard_failure() -> None:
    inventory = _inventory()
    payload = _good_payload(inventory)
    payload["units"][0]["explain"] = "This is a very long explanation. " * 100
    # The overage is recorded for a reader, but the payload is still valid.
    diagnostics = semantic.length_diagnostics(payload)
    assert any(row["kind"] == "explain_length" for row in diagnostics)
    assert semantic.validate_details(payload, ["pkg/jobs.py"], inventory, set()) == []


def test_normalize_details_keeps_facts_and_repairs_shape() -> None:
    inventory = _inventory()
    payload = _good_payload(inventory)
    payload["units"][0]["kind"] = "not-a-kind"
    original_explain = payload["units"][1]["explain"]
    payload["dispositions"].pop("pkg/jobs.py::Pool.submit")
    flags = semantic.normalize_details(payload, ["pkg/jobs.py"], inventory, set())
    assert any("module_region" in flag for flag in flags)
    assert payload["units"][1]["explain"] == original_explain  # facts are never dropped
    assert payload["dispositions"]["pkg/jobs.py::Pool.submit"]["how"] == "index_only"


def test_unit_ranges_come_from_the_inventory_not_the_model() -> None:
    inventory = _inventory()
    unit = {"id": "pkg/jobs.py::Pool", "kind": "class",
            "members": ["pkg/jobs.py::Pool.submit", "pkg/jobs.py::does-not-exist"]}
    ranges = semantic.unit_ranges("pkg/jobs.py::Pool", unit, inventory)
    assert [entry["path"] for entry in ranges] == ["pkg/jobs.py"]
    covered = [pair for entry in ranges for pair in entry["lines"]]
    assert any(pair[0] == 10 for pair in covered)  # class line
    assert any(pair[0] == 11 for pair in covered)  # folded member line
    assert semantic.unit_ranges("grp:pool-helpers", {"id": "grp:pool-helpers"}, inventory) == []


def _tree(unit_ids: list[str], **overrides) -> dict:
    node = {"id": "root", "parent": None, "title": "Root",
            "capability": "Every source unit under one responsibility root.",
            "summary": "Start here.", "unit_ids": unit_ids}
    node.update(overrides)
    return {"nodes": [node], "depends_on": []}


def test_validate_tree_requires_single_root_and_unique_primary_ownership() -> None:
    inventory = _inventory()
    ids = [row["id"] for row in inventory["pkg/jobs.py"]["symbols"]]
    assert semantic.validate_tree(_tree(ids), set(ids)) == []

    duplicated = _tree(ids + ids[:1])
    assert any("assigned to both" in problem for problem in semantic.validate_tree(duplicated, set(ids)))

    missing = _tree(ids[:-1])
    assert any("no primary owner" in problem for problem in semantic.validate_tree(missing, set(ids)))

    cyclic = {"nodes": [
        {"id": "a", "parent": "b", "title": "A", "capability": "A real capability text here.", "summary": "s", "unit_ids": []},
        {"id": "b", "parent": "a", "title": "B", "capability": "Another real capability text.", "summary": "s", "unit_ids": ids},
    ], "depends_on": []}
    assert any("cycle" in problem or "exactly one root" in problem
               for problem in semantic.validate_tree(cyclic, set(ids)))


def test_validate_tree_requires_a_dependency_basis() -> None:
    inventory = _inventory()
    ids = [row["id"] for row in inventory["pkg/jobs.py"]["symbols"]]
    payload = _tree(ids)
    payload["depends_on"] = [{"from": "root", "to": "root", "basis": ""}]
    assert any("basis" in problem for problem in semantic.validate_tree(payload, set(ids)))


def test_normalize_tree_assigns_unowned_units_to_the_root() -> None:
    inventory = _inventory()
    ids = [row["id"] for row in inventory["pkg/jobs.py"]["symbols"]]
    payload = _tree(ids[:-1])
    flags = semantic.normalize_tree(payload, set(ids))
    assert any("no owner" in flag for flag in flags)
    owned = {uid for node in payload["nodes"] for uid in node["unit_ids"]}
    assert owned == set(ids)


def test_mechanical_tree_covers_every_unit_and_is_labelled_a_fallback() -> None:
    inventory = _inventory()
    units = {row["id"]: {"id": row["id"], "kind": row["kind"], "explain": "x"}
             for row in inventory["pkg/jobs.py"]["symbols"]}
    tree = semantic.mechanical_tree([{"number": 0, "title": "Jobs", "files": ["pkg/jobs.py"]}], units)
    assert tree["fallback"]
    owned = {uid for node in tree["nodes"] for uid in node["unit_ids"]}
    assert owned == set(units)
    assert semantic.validate_tree(tree, set(units)) == []


def test_merge_replacement_stays_inline_below_the_measured_threshold(tmp_path) -> None:
    units = {"a.py::f": {"id": "a.py::f", "explain": "same fact", "extras": []},
             "b.py::g": {"id": "b.py::g", "explain": "same fact", "extras": []}}
    owner = {"a.py::f": "node-a", "b.py::g": "node-b"}
    replacements = [{"merge_id": "m1", "fragment_words": "same fact",
                     "primary_unit": "a.py::f",
                     "targets": [{"unit": "b.py::g", "field": "explain"}]}]
    working, applied, skipped = semantic.apply_merge_replacements(
        units, replacements, lambda uid: uid, owner, min_saving=24)
    assert not applied and skipped and working["b.py::g"]["explain"] == "same fact"


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
    meta = semantic.render(run_dir=run_dir, source_root=repo, inventory=inventory,
                           units=units, dispositions=dispositions, tree=tree)
    assert meta["nodes"] == 1
    index = (run_dir / "docs" / "INDEX.md").read_text(encoding="utf-8")
    assert "](nodes/root.md)" in index
    page = (run_dir / "docs" / "nodes" / "root.md").read_text(encoding="utf-8")
    assert "pkg/jobs.py" in page and "L1-L" in page  # program-derived source link
    catalog = json.loads((run_dir / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["units"] and catalog["symbols"]["pkg/jobs.py::Pool"]["file"] == "pkg/jobs.py"
    checks = {row["check"]: row["ok"] for row in
              semantic.verify(run_dir, inventory, units, dispositions, tree)}
    assert checks["unique_primary_ownership"] and checks["relative_links_resolve"]


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
    semantic.render(run_dir=run, source_root=repo, inventory=inventory,
                    units=units, dispositions=dispositions, tree=tree)
    return run, inventory, units, dispositions, tree, members, group, index_only


@pytest.mark.parametrize("old_catalog", [False, True])
def test_find_and_query_resolve_grouped_symbols_units_and_index_only(tmp_path, old_catalog) -> None:
    from cbe import generate

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
        record = generate.query(run, sid)
        assert record["unit"] == group and record["node"] == "root"
        assert record["page"] == "nodes/root.md"
        assert record["anchor"] == f"#{semantic.anchor(group)}"
        found = next(row for row in generate.find(run, sid) if row["id"] == sid)
        assert found == record
    record = generate.query(run, index_only)
    assert record["how"] == "index_only" and record["reason"] == "import metadata"
    assert record["page"] is None and record["anchor"] is None
    checks = {row["check"]: row for row in semantic.verify(run, inventory, units, dispositions, tree)}
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
        page.write_text(page.read_text().replace(f'<a id="{semantic.anchor(group)}"></a>', ""))
    catalog_path.write_text(json.dumps(catalog))
    checks = {row["check"]: row for row in semantic.verify(run, inventory, units, dispositions, tree)}
    assert not checks["catalog_navigation_resolves"]["ok"], checks


def test_inventory_from_context_uses_chunk_ids_and_rejects_a_missing_path() -> None:
    context = {"schema": "cbe-context/1",
               "files": [{"path": "a.py", "language": "python", "sha256": "x"}],
               "chunks": [{"id": "chunk-1", "path": "a.py", "language": "python",
                           "kind": "function", "name": "f", "start_line": 1, "end_line": 2,
                           "text": "def f():\n    return 1\n", "sha256": "y"}],
               "graph": None, "diagnostics": []}
    inventory = semantic.inventory_from_context(context, ["a.py"])
    assert inventory["a.py"]["symbols"][0]["id"] == "chunk-1"
    with pytest.raises(semantic.SemanticError):
        semantic.inventory_from_context(context, ["missing.py"])


def test_ensure_chunk_coverage_marks_empty_and_keeps_comment_only(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "empty.py").write_text("", encoding="utf-8")
    (repo / "doc.py").write_text('"""Only a docstring, no declaration."""\n', encoding="utf-8")
    ast_inventory = semantic.build_inventory({
        "empty.py": {"source": "", "digest": "e", "tokens": 0},
        "doc.py": {"source": '"""Only a docstring, no declaration."""\n', "digest": "d", "tokens": 8},
    })
    context = {"schema": "cbe-context/1",
               "files": [{"path": "empty.py", "language": "python", "sha256": "e"},
                         {"path": "doc.py", "language": "python", "sha256": "d"}],
               "chunks": [], "graph": None, "diagnostics": []}
    semantic.ensure_chunk_coverage(context, repo, ast_inventory, ["empty.py", "doc.py"])
    codes = {(row["path"], row["code"]) for row in context["diagnostics"]}
    assert ("empty.py", "known_empty") in codes
    assert not any(chunk["path"] == "empty.py" for chunk in context["chunks"])
    # A comment/docstring-only file is not empty; it keeps a real reading chunk.
    assert any(chunk["path"] == "doc.py" for chunk in context["chunks"])
    inventory = semantic.inventory_from_context(context, ["empty.py", "doc.py"])
    assert inventory["empty.py"]["symbols"] == [] and inventory["empty.py"]["known_empty"] is True
    assert inventory["doc.py"]["symbols"] and inventory["doc.py"]["known_empty"] is False


def test_validate_details_allows_empty_units_only_when_no_inventory_ids() -> None:
    empty_inventory = {"a.py": {"tokens": 0, "sha256": "x", "nlines": 1, "symbols": [],
                                "known_empty": True}}
    payload = {"units": [], "dispositions": {}, "batch_notes": "known-empty batch"}
    assert semantic.validate_details(payload, ["a.py"], empty_inventory, set()) == []
    assert semantic.normalize_details(dict(payload), ["a.py"], empty_inventory, set()) == []

    full = semantic.build_inventory({"a.py": {"source": "def f():\n    return 1\n",
                                              "digest": "d", "tokens": 5}})
    problems = semantic.validate_details({"units": [], "dispositions": {}, "batch_notes": "x"},
                                         ["a.py"], full, set())
    assert any("nonempty" in problem for problem in problems)


def test_validate_details_reports_a_list_relation_kind_instead_of_crashing() -> None:
    """The real Flask module_6 counterexample: relations[].kind == ["use"]."""
    inventory = _inventory()
    payload = _good_payload(inventory)
    target = payload["units"][0]["id"]
    payload["units"][0]["relations"] = [{"target": target, "kind": ["use"]}]
    problems = semantic.validate_details(payload, ["pkg/jobs.py"], inventory, set())
    assert any("relation kind must be one of" in problem and "['use']" in problem for problem in problems)
    flags = semantic.normalize_details(payload, ["pkg/jobs.py"], inventory, set())
    assert payload["units"][0]["relations"][0]["kind"] == "use"
    assert any("use" in flag for flag in flags)


def test_validate_details_reports_list_unit_kind_and_extra_topic_instead_of_crashing() -> None:
    inventory = _inventory()
    payload = _good_payload(inventory)
    payload["units"][0]["kind"] = ["function"]
    payload["units"][0]["extras"] = [{"topic": ["failure"], "note": "a real note"}]
    joined = "\n".join(semantic.validate_details(payload, ["pkg/jobs.py"], inventory, set()))
    assert "kind must be one of" in joined and "extra topic must be one of" in joined
    semantic.normalize_details(payload, ["pkg/jobs.py"], inventory, set())
    assert payload["units"][0]["kind"] == "function"
    assert payload["units"][0]["extras"][0]["topic"] == "failure"


def test_validate_details_reports_list_disposition_how_instead_of_crashing() -> None:
    inventory = _inventory()
    payload = _good_payload(inventory)
    key = next(iter(payload["dispositions"]))
    payload["dispositions"][key] = {"how": ["unit"], "unit": key, "reason": "x"}
    joined = "\n".join(semantic.validate_details(payload, ["pkg/jobs.py"], inventory, set()))
    assert "how must be one of" in joined
    semantic.normalize_details(payload, ["pkg/jobs.py"], inventory, set())
    assert payload["dispositions"][key]["how"] == "index_only"


def test_validate_tree_survives_list_valued_fields() -> None:
    payload = {"nodes": [{"id": "root", "parent": None, "title": "Root",
                          "capability": ["a capability " * 5], "summary": "s",
                          "unit_ids": [["u1"]]}], "depends_on": []}
    problems = semantic.validate_tree(payload, {"u1"})  # must not raise
    joined = "\n".join(problems)
    assert "unit_ids must be a list of strings" in joined
    assert "capability must be a nonempty string" in joined
    parent_payload = {"nodes": [
        {"id": "root", "parent": None, "title": "Root", "capability": "c" * 50, "summary": "s", "unit_ids": []},
        {"id": "kid", "parent": ["root"], "title": "Kid", "capability": "c" * 50, "summary": "s", "unit_ids": []},
    ], "depends_on": []}
    assert any("parent" in problem for problem in semantic.validate_tree(parent_payload, set()))
