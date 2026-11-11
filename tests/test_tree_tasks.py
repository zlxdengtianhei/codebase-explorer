"""The module tree is made by the program and only named by the model: skeleton freeze, naming tasks,
node-by-node answers with program-made titles, old-run handling, and the entry page."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe import checks, docs, host_run, treename
from test_host_run import _answer, _answer_task, _drive


def _repo(tmp_path: Path, dirs=("alpha", "beta", "gamma"), files=10) -> Path:
    repo = tmp_path / "repo"
    for d in dirs:
        (repo / "src" / d).mkdir(parents=True)
        for i in range(files):
            (repo / "src" / d / f"mod{i}.py").write_text(
                f"def {d}_{i}_a(x):\n    return x + {i}\n\ndef {d}_{i}_b(x):\n    return {d}_{i}_a(x) * 2\n")
    return repo


def _until_names(tmp_path, monkeypatch, *, batch_tokens=None, jobs=8):
    if batch_tokens:
        monkeypatch.setattr(treename, "BATCH_TOKENS", batch_tokens)
    run = Path(host_run.plan(_repo(tmp_path), tmp_path / "run", review="none", jobs=jobs)["run_dir"])
    while True:
        batch = host_run.next_tasks(run)["tasks"]
        assert batch
        if any(item["kind"] == "tree_name" for item in batch):
            return run, batch
        for item in batch:
            assert _answer_task(run, item, _answer(item, Path(item["prompt_file"]).read_text()))["accepted"]


def _state(run):
    return json.loads((run / "host/state.json").read_text())


def test_skeleton_is_frozen_once_and_the_naming_batches_run_in_parallel_before_tree_top(tmp_path, monkeypatch):
    run, batch = _until_names(tmp_path, monkeypatch, batch_tokens=400)
    state = _state(run)
    names = [item for item in batch if item["kind"] == "tree_name"]
    assert len(names) == len(state["skeleton"]["batches"]) > 1 and len(names) == len(batch)
    assert "tree_top" in state["tasks"] and state["tasks"]["tree_top"]["status"] == "pending"
    frozen = state["skeleton"]
    assert host_run.next_tasks(run)["tasks"] == [] and _state(run)["skeleton"] == frozen
    for item in names[:-1]:
        assert _answer_task(run, item, _answer(item, Path(item["prompt_file"]).read_text()))["accepted"]
    assert host_run.next_tasks(run)["tasks"] == []          # one naming batch is still out
    last = names[-1]
    assert _answer_task(run, last, _answer(last, Path(last["prompt_file"]).read_text()))["accepted"]
    top = host_run.next_tasks(run)["tasks"]
    assert [item["task"] for item in top] == ["tree_top"]
    assert _answer_task(run, top[0], _answer(top[0], Path(top[0]["prompt_file"]).read_text()))["accepted"]
    assert _drive(run) == ["system"]
    state = _state(run)
    assert state["status"] == "complete" and state["verify"]["ok"]
    tree = json.loads((run / "host/accepted/tree.json").read_text())
    ids = [n["id"] for n in tree["nodes"]]
    assert ids == [n["id"] for n in frozen["nodes"]]       # the structure is the skeleton's, nothing else
    assert checks.validate_tree(tree, set(json.loads((run / "catalog.json").read_text())["units"])) == []


def test_changed_detail_drops_the_skeleton_and_starts_the_naming_over(tmp_path, monkeypatch):
    run, batch = _until_names(tmp_path, monkeypatch)
    item = batch[0]
    assert _answer_task(run, item, _answer(item, Path(item["prompt_file"]).read_text()))["accepted"]
    before = _state(run)
    path = run / "host/accepted/module_1.json"
    value = json.loads(path.read_text())
    value["units"][0]["explain"] = "A changed explanation of the first unit."
    path.write_text(json.dumps(value))
    again = host_run.next_tasks(run)["tasks"]
    after = _state(run)
    assert after["skeleton"]["input_digest"] != before["skeleton"]["input_digest"]
    assert [row["task"] for row in again] == ["tree_name_1"] and after["tasks"]["tree_name_1"]["attempts"] == 0
    assert not (run / "host/accepted/tree_name_1.json").exists()


def test_a_bad_node_is_asked_again_alone_and_the_good_ones_are_kept(tmp_path, monkeypatch):
    run, batch = _until_names(tmp_path, monkeypatch)
    item = batch[0]
    value = _answer(item, Path(item["prompt_file"]).read_text())
    first_title = value["modules"][0]["title"]
    value["modules"][1]["title"] = first_title                      # a duplicate title
    value["modules"][2]["evidence_units"] = ["u9999"]               # a unit that is not theirs
    result = _answer_task(run, item, value)
    assert not result["accepted"] and result["error"].startswith("incomplete: 2 of 3 node(s) not named")
    again = host_run.next_tasks(run)["tasks"][0]
    prompt = Path(again["prompt_file"]).read_text()
    assert "Answer again ONLY for: M2, M3" in prompt and first_title in prompt.split("Titles already taken")[1]
    fixed = _answer(again, prompt)
    fixed["modules"] = fixed["modules"][1:]                         # only the two bad ones
    assert _answer_task(run, again, fixed)["accepted"]
    names = json.loads((run / "host/accepted/tree_name_1.json").read_text())["names"]
    assert len(names) == 3 and not any(r.get("program_made") for r in names.values())
    assert any(r["title"] == first_title for r in names.values())
    assert not (run / "host/partial/tree_name_1.json").exists()


def test_nodes_still_unnamed_after_the_last_answer_get_program_titles_and_the_tree_is_valid(tmp_path, monkeypatch):
    run, batch = _until_names(tmp_path, monkeypatch)
    item = batch[0]
    assert not _answer_task(run, item, {"modules": []})["accepted"]
    again = host_run.next_tasks(run)["tasks"][0]
    final = _answer_task(run, again, "not json at all")
    assert final["accepted"] and final["normalized"] and len(final["flags"]) == 3
    assert all(flag.startswith("program-made title for M") for flag in final["flags"])
    _drive(run)
    state = _state(run)
    assert state["status"] == "complete" and state["verify"]["ok"]
    tree = json.loads((run / "host/accepted/tree.json").read_text())
    made = [n for n in tree["nodes"] if n.get("note")]
    assert len(made) == 3 and all("program-made" in n["note"] for n in made)
    titles = [n["title"] for n in made]
    assert len(set(titles)) == 3 and not any(t[-1].isdigit() for t in titles)
    summary = json.loads((run / "summary.json").read_text())
    assert summary["tree"]["program_made_titles"] == 3
    assert "program-made" in (run / "docs/RUN.md").read_text()
    assert checks.validate_tree(tree, set(json.loads((run / "catalog.json").read_text())["units"])) == []


def test_a_failed_naming_task_leaves_a_renderable_program_titled_tree(tmp_path, monkeypatch):
    run, batch = _until_names(tmp_path, monkeypatch)
    for _ in range(2):
        host_run.submit(run, "tree_name_1", error="provider_down")
        host_run.next_tasks(run)
    assert _state(run)["tasks"]["tree_name_1"]["status"] == "failed"
    host_run.render(run)
    notes = (run / "docs/RUN.md").read_text()
    assert "program" in notes and "tree_name_1" in notes
    assert host_run.verify(run)["ok"] is False                      # the task is not done, the docs still stand
    assert (run / "docs/INDEX.md").read_text().count("→ [nodes/") == 3


def test_an_empty_run_completes_without_a_tree_task(tmp_path):
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    run = Path(host_run.plan(repo, tmp_path / "run", review="none")["run_dir"])
    host_run.next_tasks(run)
    state = _state(run)
    assert state["status"] in {"running", "complete"} and not any(
        t["kind"] in host_run.TREE_KINDS for t in state["tasks"].values())
    tree = json.loads((run / "host/accepted/tree.json").read_text())
    assert [n["id"] for n in tree["nodes"]] == ["root"]
    assert state["tasks"]["system"]["status"] == "done"


@pytest.mark.parametrize("kind", ["names", "tree"])
def test_a_run_planned_with_the_old_tree_tasks_asks_for_a_new_plan(tmp_path, kind):
    run = Path(host_run.plan(_repo(tmp_path, dirs=("alpha",), files=2), tmp_path / "run", review="none")["run_dir"])
    state = _state(run)
    state["tasks"][kind] = {**state["tasks"]["module_1"], "id": kind, "kind": kind, "module": None}
    (run / "host/state.json").write_text(json.dumps(state))
    for action in (lambda: host_run.next_tasks(run), lambda: host_run.resume(run),
                   lambda: host_run.completion_prompt(run, "module_1"),
                   lambda: host_run.submit(run, "module_1", error="x")):
        with pytest.raises(host_run.HostRunError, match="run `plan` again"):
            action()


def test_a_finished_old_run_still_renders_and_searches(tmp_path):
    run = Path(host_run.plan(_repo(tmp_path, dirs=("alpha",), files=3), tmp_path / "run", review="none")["run_dir"])
    _drive(run)
    state = _state(run)
    tree = json.loads((run / "host/accepted/tree.json").read_text())
    for tid in [t for t, row in state["tasks"].items() if row["kind"] in host_run.TREE_KINDS]:
        state["tasks"].pop(tid)
        (run / f"host/accepted/{tid}.json").unlink(missing_ok=True)
    state.pop("skeleton")
    state["tasks"]["names"] = {**state["tasks"]["module_1"], "id": "names", "kind": "names", "module": None}
    state["tasks"]["tree"] = {**state["tasks"]["module_1"], "id": "tree", "kind": "tree", "module": None}
    (run / "host/state.json").write_text(json.dumps(state))
    assert host_run.render(run)["status"] in {"complete", "partial"}
    assert host_run.verify(run)["ok"]
    assert docs.find(run, "alpha_0_a")
    # A tree that used region subtrees cannot be composed any more; the error says what to do.
    state["aggregation"] = {"regions": [{"id": "region-0001", "unit_ids": []}]}
    (run / "host/state.json").write_text(json.dumps(state))
    with pytest.raises(host_run.HostRunError, match="region trees"):
        host_run.render(run)
    assert tree["nodes"]


# ----------------------------------------------------------------- treename

def _tiny(n=6):
    units = {f"a.py::function::f{i}::{i}": {"summary": f"Does job number {i} in module a.",
                                            "ranges": [{"path": f"pkg/a{i % 2}.py", "lines": [[1, 3]]}]}
             for i in range(n)}
    ids = sorted(units)
    nodes = [{"id": "root", "parent": None, "unit_ids": [], "level": 0},
             {"id": "l1", "parent": "root", "unit_ids": ids[:3], "level": 1},
             {"id": "l2", "parent": "root", "unit_ids": ids[3:], "level": 1}]
    return units, treename.Tree(nodes)


def _row(label, title="Job runner", evidence=("u1", "u2")):
    return {"id": label, "title": title, "capability": "Runs the jobs of this module.",
            "summary": "Come here for jobs. It holds them.", "evidence_units": list(evidence)}


def test_decode_names_keeps_good_modules_and_names_what_is_wrong_with_the_rest():
    units, tree = _tiny()
    batch = ["l1", "l2"]
    answer = {"modules": [_row("M1", "Alpha"), {**_row("M2", "Alpha", ("u4", "u5")), "capability": "word " * 60}]}
    good, errors = treename.decode_names(answer, batch, tree, {"l1", "l2"}, set())
    assert list(good) == ["l1"]                     # both say "Alpha": the first stays, the later one is asked again
    assert "used by another module" in " ".join(errors["l2"])
    assert "one sentence of about 25 words" in " ".join(errors["l2"])
    answer = {"modules": [_row("M1", "Alpha"), _row("M2", "Beta", ("u1", "u2"))]}   # u1 and u2 belong to M1
    good, errors = treename.decode_names(answer, batch, tree, {"l1", "l2"}, set())
    assert list(good) == ["l1"] and "evidence_units" in errors["l2"][0]
    assert good["l1"]["evidence_units"] == sorted(tree.nodes["l1"]["unit_ids"])[:2]
    with pytest.raises(ValueError):
        treename.decode_names({"nodes": []}, batch, tree, {"l1"}, set())


def test_decode_top_needs_a_full_sentence_and_a_title_that_is_not_a_childs():
    units, tree = _tiny()
    names = {"l1": {"title": "Alpha"}, "l2": {"title": "Beta"}}
    short = {"groups": [{"id": "G1", "title": "Whole", "capability": "Too short.", "summary": "s."}]}
    good, errors = treename.decode_top(short, tree, names, {"root"}, set())
    assert not good and "full sentence" in errors["root"][0]
    same = {"groups": [{"id": "G1", "title": "alpha", "capability": "A full sentence about the whole system here.",
                        "summary": "s."}]}
    assert "repeats the title" in treename.decode_top(same, tree, names, {"root"}, set())[1]["root"][0]


def test_program_titles_are_never_numbered_and_avoid_the_titles_of_siblings():
    units, tree = _tiny()
    first = treename.program_record(units, tree.members("l1"))
    assert first["program_made"] and not first["title"][-1].isdigit()
    second = treename.program_record(units, tree.members("l1"), avoid={treename.normalize_title(first["title"])})
    assert second["title"] != first["title"] and not second["title"][-1].isdigit()


def test_assemble_replaces_a_title_that_a_sibling_already_uses_and_derives_dependencies():
    units, tree = _tiny()
    ids = sorted(units)
    records = {"root": {"title": "System", "capability": "The whole system in one sentence for you.", "summary": "s",
                        "evidence_units": []},
               "l1": {"title": "Same", "capability": "One.", "summary": "s", "evidence_units": ids[:2]},
               "l2": {"title": "same", "capability": "Two.", "summary": "s", "evidence_units": ids[:1]}}
    edges = [{"from": ids[0], "to": ids[4], "kind": "call", "count": 3},
             {"from": ids[1], "to": ids[5], "kind": "relation", "count": 2, "provenance": "model_inferred"}]
    tree_json = treename.assemble(tree, records, units, edges, "repo")
    nodes = {n["id"]: n for n in tree_json["nodes"]}
    assert nodes["l1"]["title"] == "Same" and "program-made" in nodes["l2"]["note"]
    assert nodes["l2"]["evidence_units"] == []     # evidence that is not in the node is dropped
    assert tree_json["depends_on"] == [{"from": "l1", "to": "l2", "basis": "3 resolved call/import edge(s)"}]
    assert checks.validate_tree(tree_json, set(units)) == []


# --------------------------------------------------------------- entry page

def _render_tree(tmp_path, nodes, units, *, source_tokens=None, system=None):
    return docs.render(run_dir=tmp_path, source_root=tmp_path / "myrepo", inventory={}, units=units,
                       dispositions={}, languages={}, tree={"nodes": nodes, "depends_on": []},
                       system=system or {"overview": "Two sentences. About the repo."}, source_tokens=source_tokens)


def _units(n):
    return {f"grp:u{i}": {"id": f"grp:u{i}", "kind": "group", "explain": "Explains it.",
                          "ranges": [{"path": f"pkg/f{i % 4}.py", "lines": [[1, 10 + i]]}]} for i in range(n)}


def _nodes(units, capability="Does a thing."):
    ids = sorted(units)
    nodes = [{"id": "root", "parent": None, "title": "Root", "capability": capability, "summary": "s",
              "unit_ids": []}]
    for t in range(2):
        nodes.append({"id": f"t{t}", "parent": "root", "title": f"Top {t}", "capability": capability,
                      "summary": "s", "unit_ids": []})
        for c in range(2):
            nodes.append({"id": f"t{t}c{c}", "parent": f"t{t}", "title": f"Leaf {t}{c}", "capability": capability,
                          "summary": "s", "unit_ids": ids[(2 * t + c) * 3:(2 * t + c) * 3 + 3]})
    return nodes


def test_entry_page_draws_the_whole_tree_with_capability_lines_and_moves_the_rest_to_two_pages(tmp_path):
    units = _units(12)
    meta = _render_tree(tmp_path, _nodes(units, "Owns the capability of this part."), units, source_tokens=1_000_000)
    index = (tmp_path / "docs/INDEX.md").read_text()
    assert index.startswith("# myrepo: code map\n\nTwo sentences. About the repo.\n\n## Modules\n")
    assert "- **Top 0** — Owns the capability of this part. (6 units" in index
    assert "  - **Leaf 01** — Owns the capability of this part. (3 units" in index
    assert "](nodes/t0c1.md)" in index
    assert "Maintenance navigation" not in index and "How to read this report" not in index
    assert "DEPENDENCIES.md" in index and "RUN.md" in index and "## Read further" in index
    assert "flowchart" not in index and "## Graph coverage" not in index
    assert "## Dependency list" in (tmp_path / "docs/DEPENDENCIES.md").read_text()
    run_page = (tmp_path / "docs/RUN.md").read_text()
    assert "## Graph coverage" in run_page and "## Reading stats" in run_page
    assert meta["index"]["levels"] == meta["index"]["levels_shown"] == 2 and not meta["index"]["over_budget"]
    assert meta["index"]["budget"] == 30_000 and meta["index"]["files_per_node"] == 3


def test_representative_files_are_the_ones_with_most_unit_lines():
    ranges = {"a": [{"path": "x/big.py", "lines": [[1, 50]]}], "b": [{"path": "x/small.py", "lines": [[1, 2]]}],
              "c": [{"path": "x/big.py", "lines": [[60, 70]]}, {"path": "y/mid.py", "lines": [[1, 20]]}]}
    assert docs._rank_files({}, ranges, ["a", "b", "c"]) == ["x/big.py", "y/mid.py", "x/small.py"]


def test_short_file_names_gain_a_directory_only_where_the_name_is_not_unique():
    names = docs._short_names(["a/x/capabilities.rb", "a/y/capabilities.rb", "a/models.rb", "b/models.rb",
                               "lib/only.rb", "top.rb"])
    assert names["a/x/capabilities.rb"] == "x/capabilities.rb" and names["a/y/capabilities.rb"] == "y/capabilities.rb"
    assert names["a/models.rb"] == "a/models.rb" and names["b/models.rb"] == "b/models.rb"
    assert names["lib/only.rb"] == "only.rb" and names["top.rb"] == "top.rb"


def test_entry_page_over_budget_folds_the_deepest_level_first_then_shows_one_file_per_node(tmp_path):
    units = _units(12)
    long = "Owns a long capability sentence that needs many tokens to say. " * 3
    nodes = _nodes(units, long)
    full = _render_tree(tmp_path, nodes, units, source_tokens=1_000_000)["index"]
    # a budget just under the full page: the leaf level folds away, files stay at three
    import cbe.docs as d
    monkey_budget = full["tokens"] - 20
    d.INDEX_MIN_TOKENS, saved = monkey_budget, d.INDEX_MIN_TOKENS
    try:
        folded = _render_tree(tmp_path, nodes, units)["index"]
        assert folded["levels_shown"] == 1 and folded["files_per_node"] == 3 and not folded["over_budget"]
        text = (tmp_path / "docs/INDEX.md").read_text()
        assert "Top 0" in text and "Leaf 00" not in text
        d.INDEX_MIN_TOKENS = folded["tokens"] - 20
        smaller = _render_tree(tmp_path, nodes, units)["index"]
        assert smaller["files_per_node"] == 1 and smaller["levels_shown"] == 1
        d.INDEX_MIN_TOKENS = 10
        floor = _render_tree(tmp_path, nodes, units)["index"]
        assert floor["over_budget"] and floor["levels_shown"] == 1 and floor["files_per_node"] == 1
    finally:
        d.INDEX_MIN_TOKENS = saved
    assert (tmp_path / "docs/nodes/t0c0.md").is_file()          # folded nodes keep their pages
