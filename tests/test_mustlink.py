"""Must-link merging: units that must stay together before the leaf chunks are cut."""
from __future__ import annotations

import json
from pathlib import Path

from cbe import host_run, layers, mustlink, skeleton


def _unit(path: str, kind: str, name: str, offset: int = 0) -> str:
    return f"{path}::{kind}::{name}::{offset}"


def _units(*rows: tuple[str, str, str]) -> dict:
    out = {}
    for index, (path, kind, name) in enumerate(rows):
        uid = _unit(path, kind, name, index)
        out[uid] = {"id": uid, "kind": kind, "summary": f"`{name}` does its work. ",
                    "ranges": [{"path": path, "lines": [[index + 1, index + 1]]}]}
    return out


def test_links_a_declaration_and_its_implementation():
    # Chart.js shape: the type sits in a .d.ts file, the class in a .js file, and a big
    # class is several class units. A method inside an interface is a field, not a
    # declaration of the module's subject.
    units = _units(
        ("src/types/index.d.ts", "interface", "Tooltip"),
        ("src/types/index.d.ts", "method", "update"),
        ("src/plugins/plugin.tooltip.js", "class", "Tooltip"),
        ("src/plugins/plugin.tooltip.js", "class", "Tooltip"),
        ("src/plugins/plugin.tooltip.js", "method", "update"),
    )
    counted = mustlink.links(units, [])
    paths = {frozenset([a.split("::")[0], b.split("::")[0]]) for a, b in counted["pairs"]}
    assert paths == {frozenset(["src/types/index.d.ts", "src/plugins/plugin.tooltip.js"])}
    assert len(counted["pairs"]) == 2  # the interface against both class units
    assert counted["families"] == {"declaration/implementation": 2}


def test_links_a_test_to_what_it_tests_by_name_and_by_edge():
    units = _units(
        ("test/specs/format.tests.js", "function", "format"),
        ("src/format.js", "function", "format"),
        ("tests/test_views.py", "function", "check"),
        ("src/views.py", "function", "render"),
    )
    counted = mustlink.links(units, [])
    assert len(counted["pairs"]) == 1 and "function::format" in counted["pairs"][0][0]
    # The graph a run resolved says it better than the names: a call from the test.
    edge = {"from": _unit("tests/test_views.py", "function", "check", 2),
            "to": _unit("src/views.py", "function", "render", 3), "kind": "call", "count": 1}
    counted = mustlink.links(units, [edge])
    assert counted["families"] == {"test/subject": 2}
    assert sorted([edge["from"], edge["to"]]) in [sorted(pair) for pair in counted["pairs"]]


def test_links_a_header_and_its_source_file():
    units = _units(("src/a.h", "function", "init"), ("src/a.c", "function", "init"),
                   ("src/b.h", "function", "init"), ("src/b.c", "function", "close"))
    counted = mustlink.links(units, [])
    assert len(counted["pairs"]) == 1
    assert counted["pairs"][0] == (_unit("src/a.c", "function", "init", 1),
                                   _unit("src/a.h", "function", "init", 0)) or \
        counted["pairs"][0] == (_unit("src/a.h", "function", "init", 0),
                                _unit("src/a.c", "function", "init", 1))
    assert counted["families"] == {"header/source": 1}


def test_a_name_shared_by_many_files_is_a_word_not_a_module():
    units = _units(("src/types/index.d.ts", "interface", "Options"),
                   *[(f"src/mod{i}.js", "class", "Options") for i in range(mustlink.MAX_NAME_FILES + 1)])
    counted = mustlink.links(units, [])
    assert counted["pairs"] == []
    assert counted["skipped"] == {"a name used by too many files": 1}


def test_merge_moves_units_and_leaves_other_candidates_alone():
    a, b, c, d, e = ("a", "b", "c", "d", "e")
    candidates = [[a, b], [c, d], [e]]
    merged = mustlink.merge(candidates, [(b, c)], max_group=12)
    assert merged["candidates"] == [[a, b, c], [d], [e]]
    assert merged["linked"] == [sorted([b, c])]
    assert merged["oversized"] == []


def test_a_linked_set_above_the_group_ceiling_is_not_checked_but_stays_in_one_candidate():
    units = _units(*[("a.py", "function", f"fn{i}") for i in range(13)])
    members = list(units)
    chain = [(members[i], members[i + 1]) for i in range(len(members) - 1)]
    merged = mustlink.merge([[member] for member in members], chain, max_group=12)
    home = next(group for group in merged["candidates"] if members[0] in group)
    assert sorted(home) == sorted(members)
    assert merged["linked"] == [] and merged["oversized"] == [sorted(members)]


def _fixture_units(filler: int = 200) -> dict:
    """A type file and an implementation file, each big enough to become its own leaf
    module, plus enough unrelated units to need more than one chunk."""
    rows = [("src/types/index.d.ts", "interface", "Tooltip")]
    rows += [("src/types/index.d.ts", "interface", f"TypeX{index}") for index in range(8)]
    rows.append(("src/plugins/plugin.tooltip.js", "class", "Tooltip"))
    rows += [("src/plugins/plugin.tooltip.js", "function", f"helper{index}") for index in range(8)]
    modules = ("src/core/core.scale.js", "src/core/core.element.js", "src/scales/scale.time.js",
               "src/controllers/controller.bar.js")
    for index in range(filler):
        rows.append((modules[index % len(modules)], "method", f"work{index}"))
    return _units(*rows)


def _place(units: dict, uid: str, groups: list[list[str]]) -> int | None:
    for index, group in enumerate(groups):
        if uid in group:
            return index
    return None


def test_the_acceptance_case_a_declaration_and_its_implementation_in_two_groups():
    """Red before the change, green after: the program's candidate grouping puts a type
    file and its implementation file in two groups; the merge puts them in one."""
    units = _fixture_units()
    declared = next(uid for uid in units if uid.startswith("src/types/index.d.ts::interface"))
    implemented = next(uid for uid in units if uid.startswith("src/plugins/plugin.tooltip.js::class"))

    before = [sorted(node["unit_ids"]) for node in skeleton.build(units, [])["nodes"]
              if node.get("unit_ids")]
    assert len(before) > 1
    assert _place(units, declared, before) != _place(units, implemented, before)

    planned = layers.leaf_plan(units, [])
    after = planned["candidates"]
    assert _place(units, declared, after) == _place(units, implemented, after)
    assert planned["linked"] and planned["linked"][0] == sorted([declared, implemented])


def test_chunking_cannot_split_a_linked_pair_after_the_merge():
    """A candidate and its neighbour land in different chunks (each chunk starts anew when
    the last one is full); after the merge the pair is one candidate and one chunk."""
    declared = ("src/types/index.d.ts::interface::Tooltip::0", "interface", "Tooltip")
    implemented = ("src/plugins/plugin.tooltip.js::class::Tooltip::1", "class", "Tooltip")
    big = "`does its work` " * 6000  # about 18k tokens: one candidate fills a chunk
    units = {}
    for uid, kind, name in (declared, implemented):
        units[uid] = {"id": uid, "kind": kind, "summary": big,
                      "ranges": [{"path": uid.split("::")[0], "lines": [[1, 1]]}]}
    extra = {}
    for index in range(4):
        uid = f"src/core/core.scale.js::method::work{index}::{2 + index}"
        extra[uid] = {"id": uid, "kind": "method", "summary": "`work` does its work. ",
                      "ranges": [{"path": "src/core/core.scale.js", "lines": [[index + 1, index + 1]]}]}
    units.update(extra)
    first, second = declared[0], implemented[0]
    candidates = [[first], [second]] + [[uid] for uid in extra]
    chunks_before = layers.leaf_chunks(units, candidates)
    homes = [{index for index, chunk in enumerate(chunks_before) if uid in chunk["members"]}
             for uid in (first, second)]
    assert len(chunks_before) > 1 and homes[0] != homes[1]

    merged = mustlink.merge(candidates, [(first, second)], max_group=12)
    chunks_after = layers.leaf_chunks(units, merged["candidates"], merged["linked"])
    homes = [{index for index, chunk in enumerate(chunks_after) if uid in chunk["members"]}
             for uid in (first, second)]
    assert homes[0] == homes[1]
    assert chunks_after[homes[0].pop()]["linked"] == [sorted([first, second])]


def test_an_answer_that_splits_a_linked_set_is_asked_again_once():
    units = _units(("a.py", "function", "load"), ("a.py", "function", "save"),
                   ("a.py", "function", "other"), ("a.py", "function", "last"))
    members = list(units)
    labels = layers.labels_for(members, unit_layer=True)
    chunk = {"members": members, "candidates": [members], "linked": [[members[0], members[1]]]}
    split = {"groups": [{"title": "Load", "capability": "Loads.", "summary": "Loads a file.",
                         "members": [labels[members[0]], labels[members[2]]]},
                        {"title": "Save", "capability": "Saves.", "summary": "Saves a file.",
                         "members": [labels[members[1]], labels[members[3]]]}]}
    try:
        layers.decode(split, chunk, labels, 1, {})
    except layers.LayerShapeError as exc:
        assert "linked these units" in str(exc)
    else:
        raise AssertionError("a split linked set must go back to the author")
    groups, flags = layers.decode(split, chunk, labels, 1, {}, allow_split=True)
    assert len(groups) == 2 and any("linked" in flag for flag in flags)


def test_a_candidate_block_says_which_sets_must_stay_together():
    units = _units(("src/types/index.d.ts", "interface", "Tooltip"),
                   ("src/plugins/plugin.tooltip.js", "class", "Tooltip"))
    members = list(units)
    labels = layers.labels_for(members, unit_layer=True)
    chunk = {"members": members, "candidates": [members], "linked": [members]}
    blocks = layers.leaf_blocks(units, chunk, labels, [])
    assert "keep 1 linked set(s) in one group" in blocks[0]


def test_the_run_hands_a_linked_set_to_one_layer_task_and_rejects_a_split(tmp_path: Path):
    """The plan's leaf task carries the linked set, and an answer that splits it comes back
    with a shape error naming it; the same answer accepted a second time keeps it on record."""
    from test_host_run import _answer

    repo = tmp_path / "paired"
    (repo / "src" / "types").mkdir(parents=True)
    (repo / "src" / "plugins").mkdir(parents=True)
    (repo / "src" / "types" / "index.d.ts").write_text(
        "export interface Tooltip { title?: string; }\nexport interface Scale { min?: number; }\n",
        encoding="utf-8")
    (repo / "src" / "plugins" / "plugin.tooltip.js").write_text(
        "export class Tooltip {\n  constructor(cfg) { this.cfg = cfg; }\n"
        "  update() { return this.cfg; }\n}\n", encoding="utf-8")
    run_dir = Path(host_run.plan(repo, tmp_path / "run", review="none", jobs=4)["run_dir"])
    errors = []
    for _ in range(60):
        batch = host_run.next_tasks(run_dir)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            prompt = Path(item["prompt_file"]).read_text(encoding="utf-8")
            Path(item["output_file"]).write_text(
                json.dumps(_answer({"kind": item["kind"]}, prompt)), encoding="utf-8")
            result = host_run.submit(run_dir, item["task"], usage={"total_tokens": 1000, "source": "test"})
            if not result.get("accepted"):
                errors.append(result.get("error") or "")
    state = json.loads((run_dir / "host" / "state.json").read_text(encoding="utf-8"))
    layer_tasks = [task for task in state["tasks"].values()
                   if task["kind"] == "layer" and task["level"] == 1]
    assert layer_tasks
    sets = [group for task in layer_tasks for group in task.get("linked") or []]
    assert any(any("index.d.ts::interface::Tooltip" in uid for uid in group)
               and any("plugin.tooltip.js" in uid for uid in group) for group in sets)
    assert any("linked these units" in error for error in errors), errors
