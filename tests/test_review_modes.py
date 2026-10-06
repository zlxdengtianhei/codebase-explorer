"""Normal CLI policy lifecycle; synthetic host results, zero model launches."""
import json
from pathlib import Path

import pytest

from cbe import cli, module_facts
from cbe.native_handoff import next_work
from cbe.store import LedgerStore
from test_native_handoff import _run as _legacy_run, _record, _business_result


def _run(tmp_path):
    return _legacy_run(tmp_path, review_mode=None)


def command(capsys, *args):
    assert cli.main(list(args)) == 0
    return json.loads(capsys.readouterr().out)


def finish(tmp_path, capsys, run, mode):
    calls = []
    for tick in range(60):
        action = command(capsys, "native-next", "--run-dir", str(run), "--owner", "controller",
                         "--review-mode", mode)
        if action["status"] == "complete":
            return action, calls
        assert action["status"] == "ready", action
        for item in action["items"]:
            assert item["prompt_tokens"] <= 8000
            calls.append(item["role"])
            _record(tmp_path, run, item, "started")
            _record(tmp_path, run, item, "completed", _business_result(run, item))
    raise AssertionError("finite fixture did not complete")


@pytest.mark.parametrize("mode", ["none", "sample", "full"])
def test_normal_cli_every_mode_to_reader(tmp_path, capsys, mode):
    run = _run(tmp_path)
    action, calls = finish(tmp_path, capsys, run, mode)
    ledger = LedgerStore(run).open()
    assert all(module_facts.accepted_fact(ledger, sid) for sid in ledger["inventory"]["symbols"])
    index = Path(action["reader_index"]).read_text()
    assert f"Semantic review mode: {mode}" in index
    assert "full LLM review is not a proof" in index
    assert action["native_usage"]["details_command"]
    sid = next(sid for sid, symbol in ledger["inventory"]["symbols"].items() if symbol["kind"] == "function")
    result = command(capsys, "query", "--run-dir", str(run), "--id", sid)
    assert result
    assert result["type"] == "fact" and result["symbol_id"] == sid
    if mode == "none":
        assert not any(role.endswith("review") for role in calls)
        assert "mechanically validated; narrative semantics unverified" in index
        assert all(row["state"] in {"mechanically_validated", "syntax_evidenced"} for row in ledger["fact_reviews"].values())
        assert ledger["system_record"]["record"]["review"]["decision"] == "mechanically_validated"
        assert result["explanation_state"] == "mechanically_validated" and not result["individually_source_checked"]
    elif mode == "full":
        assert {"fact_review", "module_review", "system_review"} <= set(calls)
        assert all(row["state"] in {"source_checked", "syntax_evidenced"} for row in ledger["fact_reviews"].values())
    else:
        assert "fact_review" in calls


def test_new_default_none_and_old_run_explicit_migration(tmp_path):
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    assert LedgerStore(run).open()["review_policy"]["mode"] == "none"
    before = LedgerStore(run).open()
    action = next_work(run, owner="controller", review_mode="full")
    after = LedgerStore(run).open()
    assert after["calls"] == before["calls"]
    assert after["tasks"][item["task_id"]] == before["tasks"][item["task_id"]]
    assert action["status"] == "needs_reconciliation"
    assert item["call_id"] in action["items"][0]["reconciliation_command"]


def test_future_full_switch_retains_accepted_history(tmp_path, capsys):
    run = _run(tmp_path)
    finish(tmp_path, capsys, run, "none")
    before = LedgerStore(run).open()
    action, calls = finish(tmp_path, capsys, run, "full")
    after = LedgerStore(run).open()
    assert "fact_author" not in calls and "module_author" not in calls
    assert all(after["calls"][cid] == value for cid, value in before["calls"].items())
    assert all(row["state"] in {"source_checked", "syntax_evidenced"} for row in after["fact_reviews"].values())
    for gid, row in after["module_records"].items():
        assert row["history"][0]["record"] == before["module_records"][gid]["record"]
    assert action["status"] == "complete"


@pytest.mark.parametrize("mode", ["none", "sample", "full"])
def test_mechanical_citation_counterexample_all_modes(tmp_path, mode):
    run = _run(tmp_path)
    item = next_work(run, owner="controller", review_mode=mode)["items"][0]
    _record(tmp_path, run, item, "started")
    payload = _business_result(run, item)
    payload["items"][0]["source_refs"] = [{"path": "ops.py", "line": 999999}]
    before = LedgerStore(run).open()
    result = _record(tmp_path, run, item, "completed", payload)
    assert result["status"] == "result_rejected"
    assert "outside frozen file" in result["reason"]
    assert LedgerStore(run).open()["details"] == before["details"]
    assert (run / "raw" / f"{item['call_id']}.json").exists()


def test_formal_unknown_prepared_reconciliation_preserves_cost(tmp_path, capsys):
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    before = LedgerStore(run).open()
    searched = tmp_path / "searched.json"
    searched.write_text(json.dumps(["synthetic original host result window", "synthetic reserved raw path"]))
    command(capsys, "call-reconcile", "--run-dir", str(run), "--call-id", item["call_id"],
            "--searched-file", str(searched))
    after = LedgerStore(run).open()
    call = after["calls"][item["call_id"]]
    assert call["extra"]["reconciliation"]["searched"]
    assert call["state"] == "released"
    assert call["usage"] == before["calls"][item["call_id"]]["usage"]
    assert after["tasks"][item["task_id"]]["generation"] > before["tasks"][item["task_id"]]["generation"]
    fresh = next_work(run, owner="controller")["items"][0]
    assert fresh["call_id"] != item["call_id"]


def test_alternates_ready_author_review_without_wave_barrier():
    from cbe.native_handoff import _fair_candidates
    ledger = {"tasks": {}, "module_records": {"a": {"state": "draft"}}}
    for kind, ident in [("module_author", "b"), ("module_author", "c"), ("module_review", "a")]:
        tid = f"task:{kind}:{ident}"
        ledger["tasks"][tid] = {"kind": kind, "state": "pending", "input_ids": [ident]}
    rows = _fair_candidates(ledger, "module")
    assert [row[2] for row in rows] == ["module_review", "module_author", "module_author"]
    ledger["native_scheduler_last_role"] = "review"
    assert [row[2] for row in _fair_candidates(ledger, "module")][:2] == ["module_author", "module_review"]


@pytest.mark.parametrize("mode", ["none", "sample", "full"])
def test_structured_syntax_fact_disagreement_is_rejected(tmp_path, mode):
    run = _run(tmp_path)
    item = next_work(run, owner="controller", review_mode=mode)["items"][0]
    _record(tmp_path, run, item, "started")
    payload = _business_result(run, item)
    payload["items"][0]["syntax_assertions"] = {"return_keys": ["invented"]}
    before = LedgerStore(run).open()
    with pytest.raises(ValueError, match="syntax_assertions.return_keys"):
        _record(tmp_path, run, item, "completed", payload)
    assert LedgerStore(run).open()["details"] == before["details"]


def test_positive_sent_call_cannot_be_reconciled_as_unsent(tmp_path, capsys):
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, item, "started")
    before = LedgerStore(run).open()
    searched = tmp_path / "search.json"
    searched.write_text(json.dumps(["host window"]))
    assert cli.main(["call-reconcile", "--run-dir", str(run), "--call-id", item["call_id"],
                     "--searched-file", str(searched)]) == 2
    assert "positive delivery evidence" in capsys.readouterr().err
    assert LedgerStore(run).open() == before


def test_sample_has_less_direct_source_checks_than_full(tmp_path, capsys):
    from cbe.runner import analyze
    repo = tmp_path / "many"
    repo.mkdir()
    (repo / "ops.py").write_text("\n".join(f"def f{i}(x):\n return x + {i}\n" for i in range(24)))
    counts = {}
    for mode in ["sample", "full"]:
        run = tmp_path / mode
        analyze(repo, run, documentation_profile="module-first-v2")
        finish(tmp_path, capsys, run, mode)
        ledger = LedgerStore(run).open()
        counts[mode] = sum(row["state"] == "source_checked" for row in ledger["fact_reviews"].values())
        if mode == "sample":
            assert any(row["state"] == "mechanically_validated" for row in ledger["fact_reviews"].values())
    assert 0 < counts["sample"] < counts["full"]


def test_none_known_finding_is_actionable_without_auto_strong_review(tmp_path):
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    def known_finding(ledger):
        task = next(t for t in ledger["tasks"].values() if t["kind"] == "fact_review")
        sid = task["input_ids"][0]
        task["residual"] = [{"symbol_id": sid, "reason": "A concrete unsupported return condition"}]
        ledger["fact_reviews"][sid]["state"] = "needs_repair"
        return ledger
    LedgerStore(run).mutate(known_finding)
    action = next_work(run, owner="controller")
    assert action["status"] == "needs_resolution"
    assert action["unresolved"][0]["findings"]
    assert "--audit-task" in action["next_action"]
    assert not action["items"]


def test_none_preserves_strong_history_but_discloses_new_known_finding(tmp_path, capsys):
    run = _run(tmp_path)
    finish(tmp_path, capsys, run, "full")
    before = LedgerStore(run).open()
    def new_finding(ledger):
        task = next(t for t in ledger["tasks"].values() if t["kind"] == "fact_review")
        task["state"] = "pending"
        task["residual"] = [{"symbol_id": task["input_ids"][0], "reason": "Reader identified a material unsupported condition"}]
        return ledger
    LedgerStore(run).mutate(new_finding)
    action = next_work(run, owner="controller", review_mode="none")
    assert action["status"] == "needs_resolution" and action["unresolved"]
    assert LedgerStore(run).open()["fact_reviews"] == before["fact_reviews"]
    assert "cbe render" in action["render_action"]


def test_none_public_feedback_retains_question_until_explicit_semantic_audit(tmp_path, capsys):
    run = _run(tmp_path)
    finish(tmp_path, capsys, run, "full")
    before = LedgerStore(run).open()
    sid = next(s for s, symbol in before["inventory"]["symbols"].items() if symbol["kind"] == "function")
    finding = tmp_path / "actual-reader-finding.json"
    reason = "Reader identified an unsupported empty-input condition"
    finding.write_text(json.dumps([{"target_id": sid, "reason": reason}]))
    command(capsys, "native-feedback", "--run-dir", str(run), "--findings", str(finding))
    action = next_work(run, owner="controller", review_mode="none")
    assert action["status"] == "needs_resolution"
    assert any(row["reader_question"] == reason for row in action["unresolved"])
    assert LedgerStore(run).open()["calls"] == before["calls"]
    tid = next(row["task_id"] for row in action["unresolved"] if row["reader_question"] == reason)
    audit = next_work(run, owner="auditor", audit_tasks=[tid], review_bundles=False)
    assert audit["status"] == "ready" and audit["items"][0]["role"] == "fact_review"
    assert audit["items"][0]["review_dispatch"] == "manual-target"
    assert LedgerStore(run).open()["review_policy"]["mode"] == "none"
    packet = json.loads(Path(LedgerStore(run).open()["calls"][audit["items"][0]["call_id"]]["extra"]["packet_path"]).read_text())
    assert packet["assigned_ids"] == [sid] and packet["review_question"] == reason


@pytest.mark.parametrize("scope", ["module", "system"])
def test_none_known_module_system_finding_has_manual_target_to_reader(tmp_path, capsys, scope):
    run = _run(tmp_path)
    finish(tmp_path, capsys, run, "none")
    before = LedgerStore(run).open()
    target = next(iter(before["module_records"])) if scope == "module" else "system"
    finding = tmp_path / "reader-target.json"
    finding.write_text(json.dumps([{"target_id": target, "reason": "Reader requests a concrete condition audit"}]))
    command(capsys, "native-feedback", "--run-dir", str(run), "--findings", str(finding))
    action = next_work(run, owner="controller")
    assert action["status"] == "needs_resolution", action
    tid = f"task:module_review:{target}" if scope == "module" else "task:system_review"
    assert any(row["task_id"] == tid and "--audit-task" in row["target_action"] for row in action["unresolved"])
    assert LedgerStore(run).open()["calls"] == before["calls"]
    audit = command(capsys, "native-next", "--run-dir", str(run), "--owner", "explicit-auditor", "--audit-task", tid)
    assert audit["status"] == "ready"
    item = audit["items"][0]
    assert item["task_id"] == tid and item["review_dispatch"] == "manual-target"
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    for tick in range(10):
        final = next_work(run, owner="controller")
        if final["status"] == "complete":
            break
        if final["status"] == "needs_resolution":
            # A module change can expose a named dependent system obligation.
            # Explicitly authorize that target, never switch the run policy.
            final = next_work(run, owner="explicit-auditor", audit_tasks=[final["unresolved"][0]["task_id"]])
        assert final["status"] == "ready", final
        for child in final["items"]:
            if child["role"].endswith("review"):
                assert child["review_dispatch"] == "manual-target"
            _record(tmp_path, run, child, "started")
            _record(tmp_path, run, child, "completed", _business_result(run, child))
    else:
        raise AssertionError("targeted module/system chain did not finish")
    assert final["status"] == "complete"
    assert LedgerStore(run).open()["review_policy"]["mode"] == "none"


@pytest.mark.parametrize("fault", [None, "foreign_prompt", "late_raw", "member_generation", "wrong_agent", "wrong_tool", "wrong_parent"])
def test_cancelled_launch_gap_binds_actual_identity_and_preserves_unknown_cost(tmp_path, capsys, fault):
    from test_native_bundles import bundle
    from cbe.accounting import overall_token_budget
    run, items, item = bundle(tmp_path)
    iid = item["invocation_id"]
    metadata = tmp_path / "actual-parent" / "actual-host-agent" / "metadata.json"
    metadata.parent.mkdir(parents=True)
    output = tmp_path / "host-output.txt"
    terminal = "Agent was cancelled before the subagent returned findings or background launch completed"
    output.write_text(terminal)
    prompt = item["dispatch_prompt_path"]
    if fault == "foreign_prompt":
        prompt += ".unrelated"
    metadata.write_text(json.dumps({"agentId": "actual-host-agent", "parentToolUseId": "actual-launch-tool",
        "parentSessionId": "actual-parent", "childSessionId": "sess_subagent_actual-host-agent",
        "metadataFile": str(metadata), "status": "failed", "error": terminal,
        "prompt": "Read the task file:\n" + prompt + "\n", "outputFile": str(output),
        "profileSnapshot": {"excluded": "do not include this in the receipt"}}))
    import hashlib
    capture = tmp_path / "parent-public.json"
    invocation = LedgerStore(run).open()["native_invocations"][iid]
    capture.write_text(json.dumps({"parent": "actual-parent", "records": [{
        "invocation_id": iid, "invocation_record": invocation, "host_agent": "actual-host-agent",
        "host_metadata_path": str(metadata), "host_metadata_sha256": hashlib.sha256(metadata.read_bytes()).hexdigest(),
        "host_output_path": str(output), "host_output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "public_agent_parts": [{"call_id": "actual-launch-tool", "status": "error", "error": terminal,
            "input": {"prompt": "Read the task file:\n" + prompt + "\n"}}]}]}))
    if fault in {"wrong_agent", "wrong_tool", "wrong_parent"}:
        value = json.loads(metadata.read_text())
        value[{"wrong_agent": "agentId", "wrong_tool": "parentToolUseId", "wrong_parent": "parentSessionId"}[fault]] = "unrelated-identity"
        metadata.write_text(json.dumps(value))
    if fault == "late_raw":
        (run / "raw" / f"{iid}.json").write_text('{"late":true}')
    if fault == "member_generation":
        def change(ledger):
            ledger["tasks"][items[0]["task_id"]]["generation"] += 1
            return ledger
        LedgerStore(run).mutate(change)
    before = LedgerStore(run).open()
    argv = ["native-cancelled", "--run-dir", str(run), "--invocation-id", iid,
            "--host-metadata", str(metadata), "--host-output", str(output), "--parent-public-evidence", str(capture)]
    if fault:
        assert cli.main(argv) == 2
        capsys.readouterr()
        assert LedgerStore(run).open() == before
    else:
        result = command(capsys, *argv)
        after = LedgerStore(run).open()
        assert iid in overall_token_budget(after)["unknown_usage_call_ids"]
        for member in items:
            call = after["calls"][member["call_id"]]
            assert call["state"] == "released" and call["extra"]["model_delivery"] == "unknown"
            assert call["extra"]["send_evidence"] == "sent_native"
            assert call["usage"] == before["calls"][member["call_id"]]["usage"]
        assert after["details"] == before["details"] and after["fact_reviews"] == before["fact_reviews"]
        assert "profileSnapshot" not in Path(result["receipt"]).read_text()
        command(capsys, *argv)
        assert LedgerStore(run).open() == after
