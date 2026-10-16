"""C51 real answers must satisfy the inventory contract before publication."""
import json
from pathlib import Path

import pytest

from cbe import checks, host_run
from test_generate import _semantic_answer, _tiny_repo


@pytest.mark.parametrize("sample", ["invented-config", "placeholder-app"])
def test_c51_real_answer_rejects_invented_inventory_id(sample):
    fixture = json.loads((Path(__file__).parent / "fixtures/c51" / f"{sample}.json").read_text())
    problems = checks.validate_details(fixture["payload"], fixture["paths"], fixture["inventory"], set())
    assert any(fixture["bad_id"] in error and "inventory" in error for error in problems)


def test_normalized_final_answer_with_wrong_unit_target_stays_failed(tmp_path):
    repo = _tiny_repo(tmp_path)
    (repo / "src/pkg/jobs.py").write_text("def first():\n    return 1\n\ndef second():\n    return 2\n")
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    for _ in range(2):
        host_run.next_tasks(run, limit=20)
        payload = _semantic_answer(host_run.completion_prompt(run, "module_1"))
        ids = list(payload["dispositions"])
        assert len(ids) > 1
        payload["dispositions"][ids[0]]["unit"] = ids[1]
        # This isolates the normalizer bypass: both targets are real inventory ids.
        result = host_run.submit(run, "module_1", error="schema_error:wrong target",
                                 raw_text=json.dumps(payload))
        assert not result["accepted"]
    assert result["task_status"] == "failed"
    assert not (run / "host/accepted/module_1.json").exists()


def test_normalized_shape_repair_is_still_accepted(tmp_path):
    repo = _tiny_repo(tmp_path)
    run = tmp_path / "run"
    host_run.plan(repo, run, review="none", jobs=20, driver="script")
    for _ in range(2):
        host_run.next_tasks(run, limit=20)
        payload = _semantic_answer(host_run.completion_prompt(run, "module_1"))
        payload["units"][0]["extras"] = None
        path = run / "answer.json"
        path.write_text(json.dumps(payload))
        result = host_run.submit(run, "module_1", result=path)
    assert result["accepted"] and result["normalized"]
    accepted = json.loads((run / "host/accepted/module_1.json").read_text())
    assert accepted["units"][0]["extras"] == []


@pytest.mark.parametrize("field", ["explain", "summary", "extras", "uncertainties", "overview", "capability"])
def test_model_link_shaped_text_is_literal_and_generated_links_still_checked(tmp_path, field):
    from cbe import docs
    from test_semantic import SRC, _inventory, _good_payload, _tree

    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg/jobs.py").write_text(SRC)
    inventory = _inventory()
    payload = _good_payload(inventory)
    units = {u["id"]: u for u in payload["units"]}
    unit = next(iter(units.values()))
    tree = _tree(list(units))
    bad = "Call environ['werkzeug.debug.preserve_context'](ctx) to save it."
    code = "`a[b](ctx)`\n\n```python\na[b](ctx)\n```"
    system = {"overview": "Overview.", "maintenance_navigation": "Start here."}
    if field == "extras":
        unit[field] = [{"topic": "contract", "note": bad}]
    elif field == "uncertainties":
        unit[field] = [bad]
    elif field == "overview":
        system[field] = bad
    elif field == "capability":
        tree["nodes"][0][field] = bad
    else:
        unit[field] = bad + "\n\n" + code
    run = tmp_path / "run"
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=payload["dispositions"], tree=tree, languages={"pkg/jobs.py": "python"},
                system=system)
    page = (run / "docs" / ("INDEX.md" if field == "overview" else "nodes/root.md")).read_text()
    assert r"preserve_context']\(ctx)" in page
    if field == "explain":
        assert code in page  # Escaping prose must preserve actual code.
    def verify_links():
        return next(row for row in docs.verify(run, inventory, units, payload["dispositions"], tree)
                    if row["check"] == "relative_links_resolve")
    assert verify_links()["ok"]
    with (run / "docs/nodes/root.md").open("a") as stream:
        stream.write("\n[broken generated navigation](missing-page.md)\n")
    assert not verify_links()["ok"]

