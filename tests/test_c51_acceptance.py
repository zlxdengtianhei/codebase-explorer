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
