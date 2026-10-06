"""Reader evidence enters normal fresh native work without old-call resend."""
import json
from pathlib import Path

import pytest

from cbe import module_facts
from cbe.cli import main
from cbe.native_handoff import next_work
from cbe.store import LedgerStore
from test_native_handoff import _run, _record, _business_result


def completed_run(tmp_path):
    run = _run(tmp_path)
    for _ in range(20):
        action = next_work(run, owner="controller", review_bundles=False)
        if action["status"] == "complete":
            return run
        assert action["status"] == "ready", action
        item = action["items"][0]
        _record(tmp_path, run, item, "started")
        _record(tmp_path, run, item, "completed", _business_result(run, item))
    raise AssertionError("fixture did not complete")


def test_cli_reader_finding_queues_accepted_target_and_native_next_claims_fresh(tmp_path, capsys):
    run = completed_run(tmp_path)
    before = LedgerStore(run).open()
    sid = next(sid for sid, symbol in before["inventory"]["symbols"].items() if symbol["kind"] == "function")
    finding = {"target_id": sid, "reason": "Reader could not find a material output field."}
    path = tmp_path / "reader-findings.json"
    path.write_text(json.dumps([finding]))
    assert main(["native-feedback", "--run-dir", str(run), "--findings", str(path)]) == 0
    registered = json.loads(capsys.readouterr().out)
    assert registered["model_sent"] is False
    tid = registered["items"][0]["task_id"]
    queued = LedgerStore(run).open()
    assert queued["calls"] == before["calls"]
    assert queued["details"] == before["details"]
    assert queued["tasks"][tid]["state"] == "pending"
    generation = queued["tasks"][tid]["generation"]
    repeated = module_facts.register_reader_findings(run, [finding])
    assert repeated["items"][0]["status"] == "already_registered"
    assert LedgerStore(run).open()["tasks"][tid]["generation"] == generation
    item = next_work(run, owner="reader-auditor", review_bundles=False)["items"][0]
    assert item["call_id"] not in before["calls"] and item["role"] == "fact_review"
    after = LedgerStore(run).open()
    packet = json.loads(Path(after["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
    assert packet["assigned_ids"] == [sid]
    assert packet["review_question"] == finding["reason"]
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())


def test_finding_waits_for_protected_current_call_then_activates_fresh_audit(tmp_path):
    run = completed_run(tmp_path)
    ledger = LedgerStore(run).open()
    sid = next(sid for sid, symbol in ledger["inventory"]["symbols"].items() if symbol["kind"] == "function")
    module_facts.register_reader_findings(run, [{"symbol_id": sid, "reason": "First finding."}])
    item = next_work(run, owner="auditor", review_bundles=False)["items"][0]
    before = LedgerStore(run).open()
    result = module_facts.register_reader_findings(run, [{"symbol_id": sid, "reason": "Later finding."}])
    after = LedgerStore(run).open()
    assert result["items"][0]["protected_call_id"] == item["call_id"]
    assert after["calls"] == before["calls"]
    assert after["tasks"][item["task_id"]]["generation"] == before["tasks"][item["task_id"]]["generation"]
    assert next_work(run, owner="auditor")["status"] == "needs_reconciliation"
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    new = next_work(run, owner="second-auditor", review_bundles=False)["items"][0]
    assert new["call_id"] != item["call_id"]
    ledger = LedgerStore(run).open()
    packet = json.loads(Path(ledger["calls"][new["call_id"]]["extra"]["packet_path"]).read_text())
    assert packet["review_question"] == "Later finding."


@pytest.mark.parametrize("scope", ["module", "system"])
def test_reader_finding_audits_existing_module_and_system_without_rewriting_semantics(tmp_path, scope):
    run = completed_run(tmp_path)
    before = LedgerStore(run).open()
    target = next(iter(before["module_records"])) if scope == "module" else "system"
    result = module_facts.register_reader_findings(run, [{"target_id": target, "reason": "Reader found a boundary contradiction."}])
    assert result["items"][0]["task_state"] == "pending"
    item = next_work(run, owner="reader-auditor", review_bundles=False)["items"][0]
    assert item["role"] == scope + "_review"
    after = LedgerStore(run).open()
    assert after["details"] == before["details"]
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())
    assert "boundary contradiction" in Path(item["dispatch_prompt_path"]).read_text()


def test_invalid_reader_target_does_not_partially_register_or_touch_old_calls(tmp_path):
    run = completed_run(tmp_path)
    before = LedgerStore(run).open()
    sid = next(sid for sid, symbol in before["inventory"]["symbols"].items() if symbol["kind"] == "function")
    with pytest.raises(ValueError, match="no current review target"):
        module_facts.register_reader_findings(run, [{"target_id": sid, "reason": "Valid finding."},
            {"target_id": "outside-frozen-scope", "reason": "Invalid target."}])
    assert LedgerStore(run).open() == before
