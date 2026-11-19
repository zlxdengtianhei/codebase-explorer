"""Detail-first layered clustering: chunks, program checks, fallback, the run's task order, pages."""
from __future__ import annotations

import json
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
    # A group of one is merged by the program, not sent back.
    groups, flags = layers.decode({"groups": [{**ok["groups"][0], "members": ["u1"]},
                                              {**ok["groups"][1], "members": ["u2", "u3", "u4"]}]},
                                  {"members": members}, labels, 1, {})
    assert [len(group["members"]) for group in groups] == [4] and any("merged" in flag for flag in flags)
    # A group above the ceiling is split by the program, keeping the model's title.
    many = [f"u{i}" for i in range(1, 15)]
    groups, flags = layers.decode(
        {"groups": [{"title": "Big", "capability": "Does a lot.", "summary": "Big summary.",
                     "members": many}]},
        {"members": many}, {member: member for member in many}, 1, {})
    assert [len(group["members"]) for group in groups] == [12, 2]
    assert all(group["title"].startswith("Big") for group in groups)
    assert any("split" in flag for flag in flags)


def test_decode_trims_a_summary_and_names_the_program_trimming():
    members = ["u1", "u2"]
    answer = {"groups": [{"title": "One", "capability": "Does one job.",
                          "summary": "word " * 500, "members": members}]}
    groups, flags = layers.decode(answer, {"members": members}, {m: m for m in members}, 1, {})
    assert any("summary trimmed" in flag for flag in flags)
    assert "…" in groups[0]["summary"]


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


def test_verify_reports_page_budget_and_group_bounds(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    checks = {row["check"]: row for row in host_run.verify(run)["checks"]}
    assert checks["pages_within_budget"]["ok"]
    assert checks["group_sizes_within_bounds"]["ok"]
