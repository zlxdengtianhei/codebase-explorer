"""Rendering with a page budget: page size, unit coverage and single-unit lookup.

The generated tree and its unit explanations are frozen here; only the page
boundary moves. These tests pin what the reader gets: no page past its budget
unless the tree offers no split, every unit printed exactly once, a group's units
never split across pages, and ``catalog_query`` still returning one unit.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from cbe import catalog_query, docs, page_budget
from cbe.token_budget import count_text_tokens


LONG = ("It reads the incoming value, checks the boundary, and returns the result "
        "to the caller. ")


STRUCTURE = ([("root", None, 1)]
             + [(group, "root", 2) for group in ("g1", "g2", "g3")]
             + [(f"{group}{leaf}", group, 6)
                for group in ("g1", "g2", "g3") for leaf in ("a", "b", "c")])


def _fixture(structure=STRUCTURE) -> tuple[dict, dict]:
    """A tree and its unit explanations from ``(node, parent, explain repeat)`` rows."""
    units: dict[str, dict] = {}
    nodes = []
    for nid, parent, repeat in structure:
        ids = [f"grp:{nid}-{index}" for index in range(2)]
        for uid in ids:
            units[uid] = {"id": uid, "kind": "group", "summary": "", "explain": LONG * repeat}
        nodes.append({"id": nid, "parent": parent, "title": nid.upper(), "summary": "",
                      "capability": f"{nid} is responsible for one thing.", "unit_ids": ids})
    return units, {"nodes": nodes, "depends_on": []}


def _render(tmp_path: Path, *, structure=STRUCTURE, **kwargs) -> tuple[Path, dict, dict, dict]:
    units, tree = _fixture(structure)
    run = tmp_path / "run"
    run.mkdir()
    meta = docs.render(run_dir=run, source_root=tmp_path, inventory={}, units=units,
                       dispositions={}, tree=tree, languages={}, **kwargs)
    return run, meta, tree, units


def _page_tokens(run: Path) -> dict[str, int]:
    return {path.name: count_text_tokens(path.read_text(encoding="utf-8"))
            for path in sorted((run / "docs" / "nodes").glob("*.md"))}


def _unit_headings(run: Path) -> dict[str, list[str]]:
    import re
    found: dict[str, list[str]] = {}
    for path in sorted((run / "docs" / "nodes").glob("*.md")):
        for name in re.findall(r"^### `(.+?)`$", path.read_text(encoding="utf-8"), re.M):
            found.setdefault(name, []).append(path.name)
    return found


def test_the_default_page_boundary_is_the_budget() -> None:
    assert page_budget.DEFAULT_PAGE_MODE == "budget"
    parameters = inspect.signature(docs.render).parameters
    assert parameters["pages"].default == "budget"
    assert parameters["page_budget_tokens"].default == page_budget.DEFAULT_PAGE_BUDGET


def test_pages_stay_within_the_budget_and_print_every_unit_once(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=700)
    plan = json.loads((run / "catalog.json").read_text())["pages"]
    assert plan["mode"] == "budget" and plan["page_count"] < len(tree["nodes"])
    tokens = _page_tokens(run)
    assert set(tokens) == {f"{row['root']}.md" for row in plan["pages"]}
    assert all(row["tokens"] <= 700 for row in plan["pages"])
    found = _unit_headings(run)
    assert sum(len(pages) for pages in found.values()) == len(units)
    assert [name for name, pages in found.items() if len(pages) > 1] == []


def test_a_group_units_never_split_across_pages(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=500)
    catalog = json.loads((run / "catalog.json").read_text())
    for node in tree["nodes"]:
        pages = {catalog["units"][uid]["page"] for uid in node["unit_ids"]}
        assert len(pages) == 1, f"{node['id']} is split across {pages}"
        assert all(catalog["units"][uid]["node"] == node["id"] for uid in node["unit_ids"])


def test_every_node_is_printed_on_the_page_the_catalog_names(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=500)
    catalog = json.loads((run / "catalog.json").read_text())
    pages = {f"nodes/{row['root']}.md" for row in catalog["pages"]["pages"]}
    assert pages == {f"nodes/{path.name}" for path in (run / "docs").glob("nodes/*.md")}
    for node in tree["nodes"]:
        page = catalog["pages"]["root_of"][node["id"]]
        text = (run / "docs" / "nodes" / f"{page}.md").read_text(encoding="utf-8")
        assert f"# {node['title']}" in text or f"## {node['title']}" in text


def test_query_still_returns_one_unit_and_points_at_the_page_that_prints_it(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=500)
    for uid, unit in units.items():
        record = catalog_query.query(run, uid)
        assert record["explain"] == unit["explain"]
        page = run / "docs" / record["page"]
        assert page.is_file()
        assert unit["explain"].splitlines()[0][:40] in page.read_text(encoding="utf-8")


def test_group_mode_renders_one_page_per_node_at_any_budget(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, pages="group", page_budget_tokens=100000)
    catalog = json.loads((run / "catalog.json").read_text())
    assert catalog["pages"]["mode"] == "group"
    assert catalog["pages"]["page_count"] == len(tree["nodes"])
    assert len(list((run / "docs" / "nodes").glob("*.md"))) == len(tree["nodes"])
    assert catalog["pages"]["root_of"] == {node["id"]: node["id"] for node in tree["nodes"]}


def test_verify_reports_the_page_plan_and_the_budget(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=500)
    checks = {check["check"]: check for check in
              docs.verify(run, {}, units, {}, tree)}
    assert checks["catalog_pages_match_plan"]["ok"]
    assert checks["pages_respect_budget"]["ok"]
    assert checks["pages_respect_budget"]["detail"]["budget"] == 500


def test_a_node_too_large_for_any_page_is_flagged_and_still_printed(tmp_path: Path) -> None:
    run, meta, tree, units = _render(
        tmp_path, structure=[("root", None, 1), ("big", "root", 40)], page_budget_tokens=200)
    catalog = json.loads((run / "catalog.json").read_text())
    flagged = {row["root"]: row["over_budget"] for row in catalog["pages"]["pages"]
               if row.get("over_budget")}
    assert flagged == {"big": page_budget.UNSPLITTABLE_LEAF}
    text = (run / "docs" / "nodes" / "big.md").read_text(encoding="utf-8")
    assert text.count("### `big-") == 2
    checks = {check["check"]: check for check in docs.verify(run, {}, units, {}, tree)}
    assert checks["pages_respect_budget"]["ok"]
    assert checks["pages_respect_budget"]["detail"]["pages_over_budget_with_reason"] == ["big"]


def test_query_units_prints_a_node_and_its_subtree_like_the_page(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=100000)
    page = (run / "docs" / "nodes" / "root.md").read_text(encoding="utf-8")
    assert catalog_query.node_units_text(run, "root") == page
    printed = catalog_query.node_units_text(run, "g1")
    assert printed.count("### `") == 2 + 3 * 2 and "# G1" in printed and "G2" not in printed


def test_query_units_depth_limits_how_far_below_the_node_it_prints(tmp_path: Path) -> None:
    run, meta, tree, units = _render(tmp_path, page_budget_tokens=100000)
    alone = catalog_query.node_units_text(run, "g1", depth=0)
    assert alone.count("### `") == 2 and "G1A" not in alone.split("**Children.**")[0]
    assert "**Children.**" in alone and "(g1a.md)" in alone
    one = catalog_query.node_units_text(run, "g1", depth=1)
    assert one.count("### `") == 2 + 3 * 2 and "## G1A" in one
    assert catalog_query.node_units_text(run, "root", depth=1).count("### `") == 2 + 3 * 2


def test_query_units_refuses_a_unit_and_the_options_it_does_not_take(tmp_path: Path, capsys) -> None:
    from cbe import cli
    from cbe.symbols import SemanticError

    run, meta, tree, units = _render(tmp_path)
    with pytest.raises(SemanticError, match="not a tree node"):
        catalog_query.node_units_text(run, "grp:g1-0")
    assert cli.main(["query", "--run-dir", str(run), "--id", "g1", "--units", "--depth", "0"]) == 0
    assert capsys.readouterr().out.count("### `") == 2
    assert cli.main(["query", "--run-dir", str(run), "--id", "g1", "--units", "--json"]) == 2
    assert cli.main(["query", "--run-dir", str(run), "--id", "g1", "--depth", "1"]) == 2
