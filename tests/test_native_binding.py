import json
from pathlib import Path
import pytest
from cbe.native_binding import reconcile_binding, launch_proof
from cbe.native_handoff import next_work, record
from cbe.store import LedgerStore, StaleWriteError
from test_native_handoff import _run, _record, _business_result


def fixture(tmp_path):
    run = _run(tmp_path, review_mode=None)
    items = []
    while len(items) < 2:
        action = next_work(run, owner="controller")
        for item in action["items"]:
            _record(tmp_path, run, item, "started")
            _record(tmp_path, run, item, "completed", _business_result(run, item))
            items.append(item)
    parent = "actual-parent"
    parts, metas = [], []
    for index, item in enumerate(items[:2]):
        handle = f"agent_actual_{index}"
        directory = tmp_path / parent / handle
        directory.mkdir(parents=True)
        raw = run / "raw" / (item["call_id"] + ".json")
        prompt = f"Read {item['dispatch_prompt_path']} and write only {raw}"
        output = directory / "output.txt"
        output.write_text(str(raw))
        meta = directory / "metadata.json"
        meta.write_text(json.dumps({"agentId": handle, "parentSessionId": parent,
            "parentToolUseId": f"tool-{index}", "childSessionId": "sess_subagent_" + handle,
            "status": "completed", "completedAt": "now", "prompt": prompt, "outputFile": str(output)}))
        parts.append({"tool": "Agent", "call_id": f"tool-{index}", "status": "completed",
                      "input": {"prompt": prompt}, "output": "agentId: " + handle})
        metas.append(meta)
    public = tmp_path / "public.json"
    public.write_text(json.dumps({"parent_session_id": parent, "public_tool_parts": parts}))
    def wrong(ledger):
        ledger["calls"][items[0]["call_id"]]["extra"]["native_handoff"].pop("child_handle", None)
        ledger["calls"][items[1]["call_id"]]["extra"]["native_handoff"].update(host="zcode", child_handle="agent_actual_0")
        return ledger
    LedgerStore(run).mutate(wrong)
    return run, items[:2], metas, public


@pytest.mark.parametrize("fault", [None, "other_prompt", "other_tool", "input", "raw", "missing_other", "late_task"])
def test_pairing_corrects_only_actual_identity_preserves_business_and_cost(tmp_path, monkeypatch, fault):
    run, items, metas, public = fixture(tmp_path)
    if fault == "other_prompt":
        v=json.loads(metas[1].read_text());v["prompt"]="foreign";metas[1].write_text(json.dumps(v))
    elif fault == "other_tool":
        v=json.loads(public.read_text());v["public_tool_parts"][1]["call_id"]="foreign";public.write_text(json.dumps(v))
    elif fault == "input":
        def bad(l): l["calls"][items[0]["call_id"]]["input_hash"]="wrong";return l
        LedgerStore(run).mutate(bad)
    elif fault == "raw":
        (run/"raw"/(items[0]["call_id"]+".json")).write_text('{"envelope":{"call_id":"foreign"}}')
    elif fault == "missing_other":
        metas[1].unlink()
    before=LedgerStore(run).open()
    if fault == "late_task":
        original=LedgerStore.mutate
        def race(store, fn):
            def alter(l):l["tasks"][items[0]["task_id"]]["generation"]+=1;return l
            monkeypatch.setattr(LedgerStore,"mutate",original)
            original(store,alter)
            return original(store,fn)
        monkeypatch.setattr(LedgerStore,"mutate",race)
    args=dict(host_metadata=metas[0],conflicting_call_id=items[1]["call_id"],
              conflicting_metadata=metas[1],parent_public_evidence=public)
    if fault:
        with pytest.raises((StaleWriteError, FileNotFoundError)):reconcile_binding(run,items[0]["call_id"],**args)
        after=LedgerStore(run).open()
        assert after["calls"]==before["calls"]
    else:
        result=reconcile_binding(run,items[0]["call_id"],**args)
        after=LedgerStore(run).open()
        for key in ["tasks","details","fact_reviews","module_records","system_record"]:
            assert after.get(key)==before.get(key)
        for i,item in enumerate(items):
            c=after["calls"][item["call_id"]]
            assert c["usage"]==before["calls"][item["call_id"]]["usage"]
            assert c["state"]==before["calls"][item["call_id"]]["state"]
            assert c["extra"]["native_binding_history"][0]["handoff"]==before["calls"][item["call_id"]]["extra"]["native_handoff"]
            assert c["extra"]["native_handoff"]["child_handle"]==f"agent_actual_{i}"
        assert result["business_acceptance"]=="none"
        assert reconcile_binding(run,items[0]["call_id"],**args)["idempotent"]


def test_launch_metadata_refuses_parent_handcopied_wrong_handle(tmp_path):
    run, items, metas, public=fixture(tmp_path)
    with pytest.raises(StaleWriteError,match="supplied child handle"):
        record(run,items[0]["call_id"],status="started",host="zcode",child_handle="wrong",
               host_metadata=metas[0],parent_public_evidence=public)


@pytest.mark.parametrize("fault", [None, "partial", "body", "envelope", "original", "prebody"])
def test_same_reserved_path_normalization_first_retry_postimport_correction(tmp_path, monkeypatch, capsys, fault):
    run, items, metas, public = fixture(tmp_path)
    first = items[0]
    cid = first["call_id"]
    immutable = {}
    for item in items:
        response = run / "native" / (item["call_id"] + ".response.txt")
        immutable[item["call_id"]] = response.read_bytes()
        (run / "raw" / (item["call_id"] + ".json")).write_bytes(response.read_bytes())
        response.unlink()
    packet = json.loads(Path(LedgerStore(run).open()["calls"][cid]["extra"]["packet_path"]).read_bytes())
    def reset(ledger):
        call = ledger["calls"][cid]
        call["state"] = "prepared"
        extra = call["extra"]
        extra.pop("native_events", None)
        extra.pop("native_event_ref", None)
        extra["native_handoff"]["status"] = "offered"
        extra["native_handoff"].pop("host", None)
        task = ledger["tasks"][first["task_id"]]
        task.update(state="leased", owner=packet["envelope"]["owner"], generation=packet["envelope"]["generation"])
        return ledger
    LedgerStore(run).mutate(reset)
    args = dict(host_metadata=metas[0], conflicting_call_id=items[1]["call_id"],
                conflicting_metadata=metas[1], parent_public_evidence=public)
    from cbe import cli
    def public_command(argv):
        assert cli.main(argv) == 0
        return json.loads(capsys.readouterr().out)
    correction_argv = ["native-reconcile-binding", "--run-dir", str(run), "--call-id", cid,
        "--host-metadata", str(metas[0]), "--conflicting-call-id", items[1]["call_id"],
        "--conflicting-metadata", str(metas[1]), "--parent-public-evidence", str(public)]
    public_command(correction_argv)
    record_args = dict(host="zcode", host_metadata=metas[0], parent_public_evidence=public)
    record_argv = ["native-record", "--run-dir", str(run), "--call-id", cid,
        "--host", "zcode", "--host-metadata", str(metas[0]), "--parent-public-evidence", str(public)]
    public_command([*record_argv, "--status", "started"])
    raw = run / "raw" / (cid + ".json")
    if fault == "prebody":
        value = json.loads(raw.read_bytes())
        value["injected_before_normalization"] = "foreign"
        raw.write_text(json.dumps(value))
        before = LedgerStore(run).open()
        with pytest.raises(StaleWriteError, match="original pairing correction proof"):
            record(run, cid, status="completed", result_path=raw, **record_args)
        assert LedgerStore(run).open() == before
        assert not (run / "native" / (cid + ".response.txt")).exists()
        return
    # This is the real path geometry: task, launch final, and normalized result
    # all point into this same run, never outside at an untouched live raw.
    if fault == "partial":
        real_mutate = LedgerStore.mutate
        def precommit_failure(store, fn):
            raise StaleWriteError("actual launch evidence changed during record")
        monkeypatch.setattr(LedgerStore, "mutate", precommit_failure)
        with pytest.raises(StaleWriteError, match="actual launch evidence changed"):
            record(run, cid, status="completed", result_path=raw, **record_args)
        monkeypatch.setattr(LedgerStore, "mutate", real_mutate)
        partial = LedgerStore(run).open()
        assert partial["calls"][cid]["state"] == "sent"
        assert partial["calls"][cid]["extra"]["native_handoff"]["status"] == "started"
        assert partial["tasks"][first["task_id"]]["state"] == "leased"
        assert (run / "native" / (cid + ".response.txt")).read_bytes() == immutable[cid]
        assert raw.read_bytes() != immutable[cid]
    result = public_command([*record_argv, "--status", "completed", "--result", str(raw)])
    assert result["state"] == "committed"
    original = run / "native" / (cid + ".response.txt")
    assert original.read_bytes() == immutable[cid]
    assert raw.read_bytes() != immutable[cid]
    if fault in {"body", "envelope", "original"}:
        before = LedgerStore(run).open()
        if fault == "original":
            original.write_bytes(b'{"items":[]}')
        else:
            value = json.loads(raw.read_bytes())
            if fault == "envelope":
                value["envelope"]["call_id"] = "foreign"
            else:
                value["injected_body"] = "foreign"
            raw.write_text(json.dumps(value))
        with pytest.raises((StaleWriteError, ValueError)):
            reconcile_binding(run, cid, **args)
        with pytest.raises((StaleWriteError, ValueError)):
            record(run, cid, status="completed", result_path=raw, **record_args)
        assert LedgerStore(run).open() == before
    else:
        assert public_command([*record_argv, "--status", "completed", "--result", str(raw)])["idempotent"]
        assert public_command(correction_argv)["idempotent"]
