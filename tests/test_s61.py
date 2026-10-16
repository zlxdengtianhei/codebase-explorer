"""S61 user-visible correction notices, tolerant dispositions and diagnostics."""
import copy
import json

import pytest

from cbe import checks, docs, host_run
from test_generate import _semantic_answer, _tiny_repo


def _run(tmp_path, change=None, tree=None, repair=False):
    run = tmp_path / "run"
    host_run.plan(_tiny_repo(tmp_path), run, review="all" if repair else "none", jobs=20, driver="script")
    changed = None
    for _ in range(20):
        batch = host_run.next_tasks(run, limit=20)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            value = _semantic_answer(host_run.completion_prompt(run, item["task"]))
            if item["task"] == "module_1" and change:
                changed = change(value)
            if item["kind"] == "review" and repair:
                value = {"decision": "needs_repair", "issues": ["Please check the explanation."]}
            if item["kind"] == "tree" and tree:
                tree(value)
            path = run / "answer.json"
            path.write_text(json.dumps(value))
            result = host_run.submit(run, item["task"], result=path)
            if item["kind"] != "module" or not change:
                assert result["accepted"], result
    assert host_run.verify(run)["ok"]
    return run, changed


def _wrong_definition(value):
    good = value["units"][0]["id"]
    bad = good.rsplit("::", 1)[0] + "::999999_full"
    value["units"][0]["id"] = bad
    value["dispositions"][good]["unit"] = bad
    return bad, good


def test_corrected_definition_notice_status_summary_and_body_accounting(tmp_path):
    run, (bad, good) = _run(tmp_path, _wrong_definition)
    page = (run / "docs/nodes/root.md").read_text()
    notice = next(line for line in page.splitlines() if "ID corrected by CBE" in line)
    assert bad in notice and good in notice
    assert "may be inaccurate" in notice and "model wrote this body under the wrong ID" in notice
    assert "to the inventory ID" in notice
    assert not any("\u4e00" <= char <= "\u9fff" for char in notice)
    assert page.count("ID corrected by CBE") == 1
    assert page.index("### ") < page.index(notice) < page.index("does its job.")
    summary = json.loads((run / "summary.json").read_text())
    assert summary["id_corrected_count"] == 2
    assert {(row["task"], row["original"], row["corrected"]) for row in summary["id_corrected"]} == {
        ("module_1", bad, good)}
    status = (run / "STATUS.md").read_text()
    assert "id_corrected 2" in status.splitlines()
    assert any(line.startswith("- module_1: ") and bad in line
               and good in line for line in status.splitlines())
    assert "normalized (2)" not in status
    assert "module_1" in summary["normalized"]
    before = docs.layer_metrics(run)
    state_path = run / "host/state.json"
    state = json.loads(state_path.read_text())
    state["tasks"]["module_1"]["flags"] = []
    state_path.write_text(json.dumps(state))
    host_run.render(run)
    after = docs.layer_metrics(run)
    assert before["model_body_tokens"] == after["model_body_tokens"]
    assert before["semantic_breakdown"]["node_text"] > after["semantic_breakdown"]["node_text"]
    assert "ID corrected by CBE" not in (run / "docs/nodes/root.md").read_text()


def test_reference_only_correction_stays_off_unit_page(tmp_path):
    def change(value):
        good = value["units"][0]["id"]
        bad = good.rsplit("::", 1)[0] + "::999999_tmp"
        value["units"][0]["relations"] = [{"kind": "use", "target": bad}]
        value["units"][0]["members"] = [bad]
        value["dispositions"][good]["unit"] = bad
    run, _ = _run(tmp_path, change)
    assert "ID corrected by CBE" not in (run / "docs/nodes/root.md").read_text()
    assert json.loads((run / "summary.json").read_text())["id_corrected_count"] == 3


def test_superseded_module_notice_does_not_label_repair_prose(tmp_path):
    run, _ = _run(tmp_path, _wrong_definition, repair=True)
    assert "ID corrected by CBE" not in (run / "docs/nodes/root.md").read_text()
    assert json.loads((run / "summary.json").read_text())["id_corrected_count"] == 2


@pytest.mark.parametrize("extra_first", [False, True])
def test_duplicate_disposition_dropped_and_answer_accepted(tmp_path, extra_first):
    def change(value):
        good = value["units"][0]["id"]
        bad = good + "_dup"
        original = copy.deepcopy(value["dispositions"][good])
        extra = {bad: {"how": "index_only", "reason": "Stray disposition must not replace the real one."}}
        value["dispositions"] = ({**extra, **value["dispositions"]} if extra_first
                                 else {**value["dispositions"], **extra})
        return bad, good, original
    run, (bad, good, original) = _run(tmp_path, change)
    accepted = json.loads((run / "host/accepted/module_1.json").read_text())
    assert bad not in accepted["dispositions"]
    assert accepted["dispositions"][good] == original
    flags = json.loads((run / "host/state.json").read_text())["tasks"]["module_1"]["flags"]
    assert any(bad in flag and "dropped" in flag for flag in flags)


def test_identity_diagnostic_precedes_many_shape_errors_in_retry(tmp_path):
    run = tmp_path / "run"
    host_run.plan(_tiny_repo(tmp_path), run, review="none", jobs=20, driver="script")
    host_run.next_tasks(run, limit=20)
    value = _semantic_answer(host_run.completion_prompt(run, "module_1"))
    good = value["units"][-1]["id"]
    bad = good.rsplit("::", 1)[0] + "::999999_tmp"
    noisy = copy.deepcopy(value["units"][0])
    noisy.update(kind="bad", explain="", extras="bad", relations="bad", uncertainties="bad", members="bad")
    value["units"] = [copy.deepcopy(noisy) for _ in range(4)] + [value["units"][-1]]
    value["units"][-1]["id"] = bad
    answer = run / "answer.json"
    answer.write_text(json.dumps(value))
    assert not host_run.submit(run, "module_1", result=answer)["accepted"]
    host_run.next_tasks(run, limit=20)
    prompt = host_run.completion_prompt(run, "module_1")
    # Both the bounded rejection and retry excerpt must retain actionable identity information.
    error = json.loads((run / "host/state.json").read_text())["tasks"]["module_1"]["errors"][-1]
    assert error.startswith(f"schema_error:unit id {bad} is not in this batch's inventory")
    assert bad in prompt and good in prompt and "candidates:" in prompt


def test_source_drift_requests_new_plan(tmp_path):
    run, _ = _run(tmp_path)
    host_run.mark_partial(run, "source_not_embedded", "jobs.py: changed since the plan (digest mismatch)")
    action = host_run.status(run)["next_action"]
    assert "new plan" in action.lower() and "source" in action.lower()
    assert "resume" not in action and "Rejected answers" not in action
    host_run.mark_partial(run, "source_not_delivered", "module_1: no source delivered")
    assert "--resume" in host_run.status(run)["next_action"]


def test_titles_escaped_in_outline_children_parent_and_dependencies(tmp_path):
    title = r"Root [x] (detail) \\ *literal*"
    child_title = "Child ] text [z]"
    def tree(value):
        root = value["nodes"][0]
        root["title"] = title
        value["nodes"].append({"id": "child", "parent": "root", "title": child_title,
                               "unit_ids": [], "capability": "Child", "summary": "Child."})
        value["depends_on"] = [{"from": "root", "to": "child", "basis": "Uses child."}]
    run, _ = _run(tmp_path, tree=tree)
    expected_root = r"Root \[x\] \(detail\) \\\\ \*literal\*"
    expected_child = r"Child \] text \[z\]"
    root = (run / "docs/nodes/root.md").read_text()
    assert f"[{expected_child}](child.md)" in root.split("**Children.**")[1].split("**Depends on.**")[0]
    assert f"[{expected_child}](child.md)" in root.split("**Depends on.**")[1]
    assert f"Parent: [{expected_root}](root.md)" in (run / "docs/nodes/child.md").read_text()
    assert f"[{expected_root}](nodes/root.md)" in (run / "docs/INDEX.md").read_text()
