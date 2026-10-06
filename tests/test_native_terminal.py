import json
from pathlib import Path
import pytest
from cbe.native_terminal import reconcile_terminal
from cbe.store import LedgerStore, StaleWriteError
from cbe.accounting import overall_token_budget
from test_native_handoff import _run, _record, _business_result


def old_completed(tmp_path):
    from cbe.native_handoff import next_work
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    def obsolete(ledger):
        ledger["calls"][item["call_id"]]["state"] = "uncertain"
        task = ledger["tasks"][item["task_id"]]
        task["generation"] += 2
        task["extra"]["call_id"] = "a-new-call"
        return ledger
    LedgerStore(run).mutate(obsolete)
    event = Path(LedgerStore(run).open()["calls"][item["call_id"]]["extra"]["native_event_ref"])
    return run, item, event


def test_obsolete_completion_keeps_task_raw_cost_and_business(tmp_path):
    run, item, event = old_completed(tmp_path)
    before = LedgerStore(run).open()
    raw = (run / "raw" / (item["call_id"] + ".json")).read_bytes()
    result = reconcile_terminal(run, item["call_id"], event=event)
    after = LedgerStore(run).open()
    for key in ["tasks", "details", "fact_reviews", "source_revision"]:
        assert after[key] == before[key]
    assert overall_token_budget(after)["known_total_tokens"] == overall_token_budget(before)["known_total_tokens"]
    assert after["calls"][item["call_id"]]["usage"] == before["calls"][item["call_id"]]["usage"]
    assert after["calls"][item["call_id"]]["state"] == "released"
    assert (run / "raw" / (item["call_id"] + ".json")).read_bytes() == raw
    assert result["business_acceptance"] == "none"
    assert reconcile_terminal(run, item["call_id"], event=event)["idempotent"]


@pytest.mark.parametrize("fault", ["current", "event_identity", "no_terminal", "prompt_changed", "packet_changed", "call_input", "call_task", "call_generation", "source_revision", "raw_owner"])
def test_terminal_rejects_unbound_evidence_and_current_claim(tmp_path, fault):
    run, item, event = old_completed(tmp_path)
    if fault == "current":
        def current(ledger):
            task = ledger["tasks"][item["task_id"]]
            task["generation"] = item["generation"]
            task["extra"]["call_id"] = item["call_id"]
            return ledger
        LedgerStore(run).mutate(current)
    elif fault == "event_identity":
        value = json.loads(event.read_text()); value["child_handle"] = "foreign-child"
        event = tmp_path / "foreign.json"; event.write_text(json.dumps(value))
    elif fault == "no_terminal":
        def erase(ledger):
            ledger["calls"][item["call_id"]]["extra"]["native_events"].pop("completed")
            return ledger
        LedgerStore(run).mutate(erase)
    elif fault == "prompt_changed":
        Path(item["dispatch_prompt_path"]).write_text("changed")
    elif fault == "packet_changed":
        call = LedgerStore(run).open()["calls"][item["call_id"]]
        Path(call["extra"]["packet_path"]).write_text("changed")
    elif fault == "raw_owner":
        raw = run / "raw" / f"{item['call_id']}.json"
        payload = json.loads(raw.read_bytes());payload["envelope"]["owner"] = "foreign-owner"
        raw.write_text(json.dumps(payload))
    else:
        def corrupt(ledger):
            call = ledger["calls"][item["call_id"]]
            if fault == "call_input":call["input_hash"] = "wrong-frozen-input"
            elif fault == "call_task":call["task_id"] = "task:fact_author:foreign"
            elif fault == "call_generation":call["extra"]["native_handoff"]["generation"] += 1
            else:ledger["source_revision"] = "foreign-source-revision"
            return ledger
        LedgerStore(run).mutate(corrupt)
    before = LedgerStore(run).open()
    with pytest.raises(StaleWriteError):
        reconcile_terminal(run, item["call_id"], event=event)
    assert LedgerStore(run).open() == before


@pytest.mark.parametrize("fault", [None, "child_identity", "wrong_final", "no_terminal", "foreign_spawn"])
def test_codex_delayed_completion_requires_official_child_and_parent(tmp_path, fault):
    import hashlib
    run, item, original = old_completed(tmp_path)
    value = json.loads(original.read_text())
    value.update(host="codex", child_handle="/root/actual-child", evidence_level="controller_attested")
    raw = json.dumps(value).encode();digest = hashlib.sha256(raw).hexdigest()
    event = tmp_path / f"{item['call_id']}.completed.{digest}.json";event.write_bytes(raw)
    def historical(ledger):
        call = ledger["calls"][item["call_id"]]
        call["extra"]["native_handoff"].update(host="codex", child_handle="/root/actual-child", status="started")
        call["extra"]["native_events"].pop("completed")
        return ledger
    LedgerStore(run).mutate(historical)
    original_path = str(run/'raw'/f"{item['call_id']}.json")
    if fault == "wrong_final":original_path = "unrelated-result.json"
    child_meta = {"id":"actual-child-session", "parent_thread_id":"original-parent", "cwd":LedgerStore(run).open()["repo_root"],
        "source":{"subagent":{"thread_spawn":{"parent_thread_id":"original-parent", "agent_path":"/root/actual-child"}}}}
    if fault == "child_identity":child_meta["source"]["subagent"]["thread_spawn"]["agent_path"] = "/root/foreign"
    child_rows = [{"type":"session_meta","ordinal":0,"payload":child_meta},
        {"type":"response_item","ordinal":8,"payload":{"role":"assistant","phase":"final_answer","content":[{"type":"output_text","text":original_path}]}},
        {"type":"event_msg","ordinal":9,"payload":{"type":"task_complete","turn_id":"actual-turn"}}]
    if fault == "no_terminal":child_rows.pop()
    child=tmp_path/'public-child.jsonl';child.write_text("\n".join(json.dumps(row) for row in child_rows))
    parent_rows=[{"type":"session_meta","payload":{"id":"original-parent"}},
        {"type":"response_item","payload":{"type":"function_call","name":"spawn_agent","call_id":"actual-spawn","arguments":json.dumps({"task_name":"actual-child"})}},
        {"type":"response_item","payload":{"type":"function_call_output","call_id":"actual-spawn","output":json.dumps({"task_name":"/root/foreign" if fault=="foreign_spawn" else "/root/actual-child"})}}]
    parent=tmp_path/'public-parent.jsonl';parent.write_text("\n".join(json.dumps(row) for row in parent_rows))
    before=LedgerStore(run).open()
    if fault:
        with pytest.raises(StaleWriteError):
            reconcile_terminal(run,item['call_id'],event=event,host_session=child,parent_public_evidence=parent)
        assert LedgerStore(run).open()==before
    else:
        result=reconcile_terminal(run,item['call_id'],event=event,host_session=child,parent_public_evidence=parent)
        after=LedgerStore(run).open()
        assert result['current_task_unchanged'] and result['business_acceptance']=='none'
        assert after['tasks']==before['tasks'] and after['calls'][item['call_id']]['usage']==before['calls'][item['call_id']]['usage']
