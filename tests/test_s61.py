"""S61 run-status guidance and escaping of model-written titles."""
import json

from cbe import docs, host_run
from test_generate import _semantic_answer, _tiny_repo


def _run(tmp_path, repair=False):
    run = tmp_path / "run"
    host_run.plan(_tiny_repo(tmp_path), run, review="all" if repair else "none", jobs=20, driver="script")
    for _ in range(20):
        batch = host_run.next_tasks(run, limit=20)
        if not batch["tasks"]:
            break
        for item in batch["tasks"]:
            value = _semantic_answer(host_run.completion_prompt(run, item["task"]))
            if item["kind"] == "review" and repair:
                value = {"decision": "needs_repair", "issues": ["Please check the explanation."]}
            path = run / "answer.json"
            path.write_text(json.dumps(value))
            result = host_run.submit(run, item["task"], result=path)
            assert result["accepted"], result
    assert host_run.verify(run)["ok"]
    return run, None


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
    units = {uid: {"id": uid, "kind": "group", "explain": "A useful explanation."}
             for uid in ("grp:one", "grp:two")}
    tree = {"nodes": [{"id": "root", "parent": None, "title": title, "unit_ids": ["grp:one"],
                       "capability": "Root capability.", "summary": "Root."},
                      {"id": "child", "parent": "root", "title": child_title, "unit_ids": ["grp:two"],
                       "capability": "Child capability.", "summary": "Child."}],
            "depends_on": [{"from": "root", "to": "child", "basis": "Uses child."}]}
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={}, units=units, dispositions={},
                languages={}, tree=tree)
    expected_root = r"Root \[x\] \(detail\) \\\\ \*literal\*"
    expected_child = r"Child \] text \[z\]"
    root = (tmp_path / "docs/nodes/root.md").read_text()
    assert f"[{expected_child}](child.md)" in root.split("**Children.**")[1].split("**Depends on.**")[0]
    assert f"[{expected_child}](child.md)" in root.split("**Depends on.**")[1]
    assert f"Parent: [{expected_root}](root.md)" in (tmp_path / "docs/nodes/child.md").read_text()
    assert f"**{expected_child}**" in (tmp_path / "docs/INDEX.md").read_text()
