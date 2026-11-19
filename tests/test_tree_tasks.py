"""Detail-first layered clustering: chunks, program checks, fallback, the run's task order, pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cbe import host_run, layers
from test_host_run import _answer, _answer_task, _drive, _repo


def _units(count: int = 6) -> dict:
    return {f"a.py::function::fn{i}::0": {"id": f"a.py::function::fn{i}::0", "kind": "function",
                                          "explain": f"`fn{i}` adds {i} to its argument and returns it.",
                                          "summary": f"`fn{i}` adds {i}. ", "ranges": [{"path": "a.py", "lines": [[i + 1, i + 1]]}]}
            for i in range(count)}


def test_leaf_chunks_keep_candidate_groups_whole_and_bound_the_detail():
    units = _units(12)
    candidates = [[f"a.py::function::fn{i}::0" for i in range(6)],
                  [f"a.py::function::fn{i}::0" for i in range(6, 12)]]
    chunks = layers.leaf_chunks(units, candidates)
    assert sorted(uid for chunk in chunks for uid in chunk["members"]) == sorted(members := [u for c in candidates for u in c])
    seen = [group for chunk in chunks for group in chunk["candidates"]]
    assert all(group in candidates for group in seen) and len(seen) == len(candidates)


def _big_repo(tmp_path: Path) -> Path:
    """One file with fourteen small functions: more than one group may hold."""
    repo = tmp_path / "big"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "maths.py").write_text(
        "\n".join(f"def fn{i}(value):\n    return value + {i}\n" for i in range(14)), encoding="utf-8")
    return repo


def test_leaf_chunks_bound_how_many_members_one_task_holds():
    # Design 2.3: a chunk holds at most about 120 members, so one author can group it.
    units = _units(200)
    members = sorted(units)
    chunks = layers.leaf_chunks(units, [members[:100], members[100:]])
    assert [len(chunk["members"]) for chunk in chunks] == [100, 100]
    assert layers.expected_groups(120) == 15


def test_decode_requires_every_member_once_and_two_to_twelve_members():
    members = ["u" + str(i) for i in range(1, 5)]
    labels = {member: member for member in members}
    ok = {"groups": [{"title": "One", "capability": "Does one job.",
                      "summary": "One summary.", "members": ["u1", "u2"]},
                     {"title": "Two", "capability": "Does another job.",
                      "summary": "Another summary.", "members": ["u3", "u4"]}]}
    groups, flags = layers.decode(ok, {"members": members}, labels, 1, {})
    assert len(groups) == 2 and not flags
    with pytest.raises(layers.LayerError, match="without a group"):
        layers.decode({"groups": [{**ok["groups"][0], "members": ["u1", "u2", "u3"]}]},
                      {"members": members}, labels, 1, {})
    with pytest.raises(layers.LayerError, match="more than one group"):
        layers.decode({"groups": [ok["groups"][0], {**ok["groups"][0]}]},
                      {"members": members}, labels, 1, {})
    # A group of one is asked back once too; on the last answer the program merges it.
    short = {"groups": [{**ok["groups"][0], "members": ["u1"]},
                        {**ok["groups"][1], "members": ["u2", "u3", "u4"]}]}
    with pytest.raises(layers.LayerShapeError, match="needs 2 to 12"):
        layers.decode(short, {"members": members}, labels, 1, {})
    groups, flags = layers.decode(short, {"members": members}, labels, 1, {}, allow_split=True)
    assert [len(group["members"]) for group in groups] == [4] and any("merged" in flag for flag in flags)
    # A group above the ceiling goes back to the same author once (design 2.3).
    many = [f"u{i}" for i in range(1, 15)]
    labels_many = {member: member for member in many}
    answer = {"groups": [{"title": "Big", "capability": "Does a lot.", "summary": "Big summary.",
                          "members": many}]}
    with pytest.raises(layers.LayerShapeError, match="Divide each of them by function"):
        layers.decode(answer, {"members": many}, labels_many, 1, {})
    # A second oversized answer is cut along the candidate grouping, and each part says what
    # it holds in its own words: names once each, never the parent group's sentence.
    candidates = [many[:5], many[5:10], many[10:]]
    groups, flags = layers.decode(answer, {"members": many, "candidates": candidates},
                                  labels_many, 1, {}, allow_split=True)
    assert [len(group["members"]) for group in groups] == [5, 5, 4]
    assert all(group["title"].startswith("Big") for group in groups)
    assert groups[0]["capability"].startswith("Part 1 of 3 of Big: it holds `u1`, `u2`")
    assert "Big summary" not in groups[0]["summary"]
    assert groups[0]["summary"] != groups[1]["summary"]
    assert any("split" in flag for flag in flags)
    # Members of one group are named once each, however many candidates they come from.
    names = {"u1": "fn", "u2": "fn", "u3": "other"}
    one = {"groups": [{"title": "Big", "capability": "Does a lot.", "summary": "Big summary.",
                       "members": many}]}
    cut, _ = layers.decode(one, {"members": many, "candidates": [many[:3], many[3:]]},
                           labels_many, 1, {}, allow_split=True, names=names)
    assert cut[0]["capability"].count("`fn`") == 1 and "`other`" in cut[0]["capability"]


def test_on_the_last_answer_left_out_members_join_their_candidate_group():
    # Design 2.3: an answer that does not partition the members is asked again once. When the
    # last answer still leaves some out, its own groups are kept and the leftovers join them.
    members = [f"u{i}" for i in range(1, 7)]
    labels = {member: member for member in members}
    candidates = [members[:3], members[3:]]
    answer = {"groups": [{"title": "Left", "capability": "One job.", "summary": "Left part.",
                          "members": ["u1", "u2"]},
                         {"title": "Right", "capability": "Another job.", "summary": "Right part.",
                          "members": ["u4", "u5"]}]}
    chunk = {"members": members, "candidates": candidates}
    with pytest.raises(layers.LayerError, match="without a group"):
        layers.decode(answer, chunk, labels, 1, {})
    groups, flags = layers.decode(answer, chunk, labels, 1, {}, allow_split=True)
    assert [group["members"] for group in groups] == [["u1", "u2", "u3"], ["u4", "u5", "u6"]]
    assert any("left out" in flag for flag in flags)


def test_decode_trims_a_summary_and_names_the_program_trimming():
    members = ["u1", "u2"]
    answer = {"groups": [{"title": "One", "capability": "Does one job.",
                          "summary": "word " * 500, "members": members}]}
    groups, flags = layers.decode(answer, {"members": members}, {m: m for m in members}, 1, {})
    assert any("summary trimmed" in flag for flag in flags)
    assert "…" in groups[0]["summary"]


def test_a_program_cut_keeps_every_member_in_a_group_of_two_or_more():
    # Every member lands in exactly one part, and no part is left with one member.
    for size in range(2, 40):
        members = [f"u{i}" for i in range(size)]
        for width in (2, 5, 7, 12):
            candidates = [members[i:i + width] for i in range(0, size, width)]
            parts = layers._cut_by_candidates(members, candidates, 2)
            assert sorted(m for part in parts for m in part) == sorted(members), (size, width)
            assert all(len(part) >= 2 for part in parts), (size, width, [len(p) for p in parts])


def test_fallback_uses_candidates_and_marks_the_groups():
    units = _units(5)
    members = sorted(units)
    chunk = {"members": members, "candidates": [members]}
    groups = layers.fallback_groups(chunk, 1, units, {}, chunk["candidates"])
    assert len(groups) == 1 and groups[0]["note"].startswith("program-made")
    assert groups[0]["members"] == members


def test_assemble_links_parents_and_puts_the_overview_on_the_root():
    units = _units(4)
    ids = sorted(units)
    left = {"id": "g1", "title": "Arithmetic", "capability": "Adds numbers.",
            "summary": "Small helpers.", "members": ids[:2], "subtree": ids[:2]}
    right = {"id": "g3", "title": "Comparison", "capability": "Compares numbers.",
             "summary": "More helpers.", "members": ids[2:], "subtree": ids[2:]}
    top = {"id": "g2", "title": "Core", "capability": "The whole library.",
           "summary": "Everything.", "members": ["g1", "g3"], "subtree": ids}
    tree = layers.assemble([[left, right], [top]], {"overview": "A helper library for arithmetic."}, "repo", [])
    nodes = {node["title"]: node for node in tree["nodes"]}
    assert nodes["Core"]["parent"] is None
    assert nodes["Core"]["summary"] == "A helper library for arithmetic."
    assert nodes["Arithmetic"]["parent"] == nodes["Core"]["id"]
    assert nodes["Comparison"]["parent"] == nodes["Core"]["id"]


def test_a_single_child_layer_is_skipped():
    units = _units(2)
    ids = sorted(units)
    leaf = {"id": "g1", "title": "Arithmetic", "capability": "Adds numbers.",
            "summary": "Small helpers.", "members": ids, "subtree": ids}
    wrapper = {"id": "g2", "title": "Arithmetic layer", "capability": "Wraps one group.",
               "summary": "One child.", "members": ["g1"], "subtree": ids}
    tree = layers.assemble([[leaf], [wrapper]], {"overview": "Arithmetic only."}, "repo", [])
    assert [node["title"] for node in tree["nodes"]] == ["Arithmetic"]
    assert tree["nodes"][0]["parent"] is None
    assert tree["nodes"][0]["unit_ids"] == ids


def test_a_run_groups_layer_by_layer_and_writes_the_overview_last(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    handed = _drive(run)
    assert handed[-1] == "overview"
    layer_tasks = [task for task in handed if task.startswith("layer_")]
    assert layer_tasks and all(task.startswith("layer_1_") for task in layer_tasks)
    assert handed.index(layer_tasks[0]) < handed.index("overview")
    state = json.loads((run / "host/state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    summary = json.loads((run / "summary.json").read_text())
    assert summary["tree"]["levels"] == len(summary["layer_shape"]) >= 1
    assert summary["layer_shape"][0]["groups"] >= 1
    assert summary["read_tokens"] > 0
    assert summary["source_read_tokens"] == 0  # a host subagent reads its own files; the basis says so
    if summary["source_tokens"] >= 20_000:
        assert summary["read_ratio"] <= 2.0
    assert summary["pages"]["ratio"] is not None
    assert summary["detail_tokens"]["count"] >= 1


def test_an_unusable_layer_answer_is_asked_once_then_grouped_by_the_program(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    for _ in range(20):
        batch = host_run.next_tasks(run)["tasks"]
        if not batch:
            break
        for item in batch:
            prompt = Path(item["prompt_file"]).read_text()
            value = "not json at all" if item["kind"] == "layer" else _answer({"kind": item["kind"]}, prompt)
            Path(item["output_file"]).write_text(value if isinstance(value, str) else json.dumps(value))
            result = host_run.submit(run, item["task"])
            if item["kind"] == "layer":
                assert not result["accepted"] or result["normalized"]
    state = json.loads((run / "host/state.json").read_text())
    assert state["status"] == "complete" and state["verify"]["ok"]
    tree = json.loads((run / "summary.json").read_text())["tree"]
    assert tree["program_made_groups"] >= 1
    assert "program-made" in (run / "docs/RUN.md").read_text()


def test_an_oversized_group_is_asked_back_once_then_cut_by_the_candidates(tmp_path):
    # Design 2.3: over twelve members the same author is asked again; a second oversized
    # answer is cut by the program along the candidate grouping, and RUN.md records it.
    run = Path(host_run.plan(_big_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    batch: list[dict] = []
    for _ in range(10):
        batch = host_run.next_tasks(run)["tasks"]
        if not batch or batch[0]["kind"] != "module":
            break
        for item in batch:
            prompt = Path(item["prompt_file"]).read_text()
            Path(item["output_file"]).write_text(json.dumps(_answer({"kind": item["kind"]}, prompt)))
            assert host_run.submit(run, item["task"])["accepted"]
    assert [item["kind"] for item in batch] == ["layer"]
    labels = re.findall(r"(?m)^[ \t]+(u\d+):", Path(batch[0]["prompt_file"]).read_text())
    assert len(labels) > 12
    big = {"groups": [{"title": "Everything", "capability": "Does everything.",
                       "summary": "All of it at once.", "members": labels}]}
    Path(batch[0]["output_file"]).write_text(json.dumps(big))
    first = host_run.submit(run, batch[0]["task"])
    assert not first["accepted"] and "Divide each of them by function" in first["error"]
    again = host_run.next_tasks(run)["tasks"]
    assert [item["task"] for item in again] == [batch[0]["task"]]  # the same author, one more try
    Path(again[0]["output_file"]).write_text(json.dumps(big))
    second = host_run.submit(run, again[0]["task"])
    assert second["accepted"] and any("split into" in flag for flag in second["flags"])
    _drive(run)
    summary = json.loads((run / "summary.json").read_text())
    assert summary["tree"]["oversized_answers_sent_back"] >= 1
    assert summary["tree"]["program_split_parts"] >= 1
    run_md = (run / "docs/RUN.md").read_text()
    assert "## Clustering" in run_md and "program cut:" in run_md
    assert "sent back once for division by function" in run_md
    assert "No graph was provided to this run" in run_md


def test_changed_detail_drops_the_layers_and_the_overview(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=8)["run_dir"])
    _drive(run)
    path = run / "host/accepted/module_1.json"
    value = json.loads(path.read_text())
    value["units"][0]["explain"] = "A changed explanation of the first unit."
    path.write_text(json.dumps(value))
    again = host_run.next_tasks(run)["tasks"]
    state = json.loads((run / "host/state.json").read_text())
    assert [item["kind"] for item in again] == ["layer"]
    assert state["tasks"].get("overview") is None


def test_pages_hold_prose_only_and_index_writes_the_commands_once(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    index = (run / "docs/INDEX.md").read_text()
    assert index.count("cbe find --run-dir") == 1 and "cbe query --run-dir" in index
    assert "## Modules" in index
    assert "units)" not in index and "`" + "id`" not in index  # no unit counts or ids on the entry page
    pages = list((run / "docs/nodes").glob("*.md"))
    assert pages
    for page in pages:
        text = page.read_text()
        for gone in ('<a id=', "[f1]:", "Look up code:", "Parent:", "· ["):
            assert gone not in text, (page.name, gone)
    leaf = next(page for page in pages if "### `" in page.read_text())
    assert "### `" in leaf.read_text()


def test_pages_name_a_symbol_and_give_one_symbol_one_detail(tmp_path):
    # Design 2.4: a heading is the symbol name, never ``path:symbol`` and never a line range.
    # Design 2.1: the two chunks of one overload pair are one detail.
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    catalog = json.loads((run / "catalog.json").read_text())
    headings = [line.strip() for page in (run / "docs/nodes").glob("*.md")
                for line in page.read_text().splitlines() if line.startswith("### `")]
    assert headings
    for line in headings:
        name = line[4:].strip().strip("`")
        assert "::" not in name and "(L" not in name, name
        assert name in catalog["short_names"].values(), name
    overload = [uid for uid in catalog["units"] if "reserve_run" in uid]
    assert len(overload) == 1
    assert any("reserve_run" in member for member in catalog["units"][overload[0]]["folded_members"])
    assert sum(line.count("### `reserve_run`") for line in headings) == 1


def test_verify_reports_page_budget_and_group_bounds(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    checks = {row["check"]: row for row in host_run.verify(run)["checks"]}
    assert checks["pages_within_budget"]["ok"]
    assert checks["group_sizes_within_bounds"]["ok"]
