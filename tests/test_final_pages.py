"""The final page shape: a leaf page names its files, and the entry page shows two levels."""
from pathlib import Path

from cbe import docs


def _nodes(pairs: dict[str, str | None]) -> dict:
    return {nid: {"id": nid, "parent": parent, "title": nid.replace("-", " ").title(),
                  "capability": f"{nid} is responsible for a thing.", "summary": "", "unit_ids": []}
            for nid, parent in pairs.items()}


def _children(nodes: dict) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {nid: [] for nid in nodes}
    for nid, node in nodes.items():
        if node["parent"] in nodes:
            children[node["parent"]].append(nid)
    return children


def _entry(nodes: dict) -> tuple[str, dict]:
    return docs._entry_page(repo="repo", nodes=nodes, children=_children(nodes),
                            roots=[nid for nid, node in nodes.items() if node["parent"] is None],
                            overview="What the repository is for.", owner={}, name_of=str)


def test_a_leaf_page_names_its_members_files_most_members_first():
    counts = docs.member_files(["src/a.ts::function::one::1", "src/a.ts::function::two::2",
                                "src/b.ts::function::three::3"], {})
    assert counts == [("src/a.ts", 2), ("src/b.ts", 1)]
    assert docs.files_line(counts) == "Files: `src/a.ts`, `src/b.ts`."


def test_more_than_five_files_are_counted_not_listed():
    counts = [(f"src/f{index}.ts", index) for index in range(7)]
    line = docs.files_line(counts)
    assert line.startswith("Files: `src/f0.ts`")
    assert "`src/f4.ts`" in line and "`src/f5.ts`" not in line
    assert line.endswith("and 2 more (7 files).")


def test_a_member_without_a_recorded_file_falls_back_to_its_id_path():
    counts = docs.member_files(["src/a.ts::module_residual::::0", "grp:no-path"], {})
    assert counts == [("src/a.ts", 1)]


def test_the_entry_page_shows_two_levels_without_repeating_the_commands():
    nodes = _nodes({"root": None, "top-a": "root", "top-b": "root",
                    "kid-a": "top-a", "kid-b": "top-b"})
    text, meta = _entry(nodes)
    assert meta["levels"] == 2 and meta["levels_shown"] == 2
    assert "  - [**Kid A**](nodes/kid-a.md)" in text
    assert text.count("cbe find --run-dir") == 1
    assert "top level is listed here" not in text


def test_a_two_level_page_over_budget_keeps_the_top_level_and_says_why():
    long_line = "It coordinates several responsibilities at once and is written out at length. "
    nodes = _nodes({"root": None,
                    **{f"top-{index}": "root" for index in range(40)},
                    **{f"kid-{index}": f"top-{index}" for index in range(40)}})
    for node in nodes.values():
        node["capability"] = long_line * 4
    text, meta = _entry(nodes)
    assert meta["levels"] == 2 and meta["levels_shown"] == 1
    assert "Two levels would take about" in text and f"{docs.INDEX_BUDGET:,}-token budget" in text
    assert "Each module page lists its own children." in text
    assert "kid-0.md" not in text
    assert text.count("cbe find --run-dir") == 1


def test_a_one_level_tree_has_nothing_to_fold(tmp_path: Path):
    nodes = _nodes({"only": None})
    text, meta = _entry(nodes)
    assert meta["levels"] == 1 and meta["levels_shown"] == 1
    assert "Two levels would take about" not in text


def test_a_rendered_leaf_page_carries_the_files_line(tmp_path: Path):
    from test_layers_o4 import _run

    run, _, _, _, _ = _run(tmp_path)
    page = (run / "docs/nodes/root.md").read_text()
    assert page.startswith("# Root\n\nFiles: `pkg/jobs.py`.\n")
    index = (run / "docs/INDEX.md").read_text()
    assert "cbe find --run-dir" in index
