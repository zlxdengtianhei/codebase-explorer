"""The host calls these two verbs; no provider config or model launcher exists."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.native_handoff import next_work, record, record_event
from cbe.native_session import parse_dsh_session
from cbe.runner import analyze
from cbe.store import LedgerStore, StaleWriteError


def _offer_fresh_claim(run: Path, claim: dict) -> dict:
    # These fixtures hold the just-created claim in the same process. Exercise
    # its explicit offer, rather than ask next_work to infer historical delivery.
    from cbe.native_handoff import _offer
    return _offer(run, claim["task_id"], claim, None)


def test_stable_native_next_reuses_only_workflow_flag_read(tmp_path, monkeypatch):
    from cbe import module_facts
    run = _run(tmp_path, review_mode=None)
    module_facts.initialize(run, batched=True, auto_budget=True, auto_input_cap=8000)
    module_facts.register_attribution_batches(run)
    def historical_run(ledger):
        ledger.pop("native_default_review_mode", None)
        return ledger
    LedgerStore(run).mutate(historical_run)
    reads = 0
    original = LedgerStore.read_unlocked
    def counted(store):
        nonlocal reads
        if store.run_dir == run.resolve():
            reads += 1
        return original(store)
    monkeypatch.setattr(LedgerStore, "read_unlocked", counted)
    result = next_work(run, owner="controller")
    assert result["status"] == "ready"
    # Latest locked reads stay; native setup also avoids claim's redundant
    # initialization read after confirming the workflow in the same call.
    # Native finalization and offer share their latest locked commit.
    assert reads == 6


def test_one_oversize_review_does_not_starve_independent_authors(tmp_path):
    from cbe import module_facts
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(8):
        (repo / f"ops_{i}.py").write_text(f"def f_{i}(value):\n    return value + {i}\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True, max_output_estimate=1000, max_input_tokens=8000)
    item = next_work(run, owner="controller", review_bundles=False, review_mode="full")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    def large_review(ledger):
        reviews = [t for t in ledger["tasks"].values() if t["kind"] == "fact_review" and t["state"] == "pending"]
        assert reviews
        reviews[0]["residual"] = [{"reason": "Indivisible review finding " * 9000}]
        return ledger
    before = LedgerStore(run).mutate(large_review)
    result = next_work(run, owner="controller", review_bundles=False)
    assert result["status"] == "ready" and result["items"]
    assert result["layout_blockers"][0]["diagnostic"]["actual_prompt_tokens"] > 8000
    assert result["layout_blockers"][0]["diagnostic"]["model_sent"] is False
    assert result["items"][0]["role"] == "fact_author"
    after = LedgerStore(run).open()
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())
    blocked = result["layout_blockers"][0]["task_id"]
    assert after["tasks"][blocked] == before["tasks"][blocked]


def test_nonprogress_single_fact_keeps_others_in_same_review_runnable(tmp_path, monkeypatch):
    from cbe import module_facts, native_handoff
    repo = tmp_path / "fair-repo"
    repo.mkdir()
    for index in range(8):
        (repo / f"f{index}.py").write_text(f"def f{index}(v):\n    return v + {index}\n")
    run = tmp_path / "fair-run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True, max_output_estimate=3000)
    item = next_work(run, owner="controller", review_bundles=False, review_mode="full")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", _business_result(run, item))
    selected = {}
    def require_all(ledger):
        task = next(t for t in ledger["tasks"].values() if t["kind"] == "fact_review" and t["state"] == "pending")
        task["extra"]["required_review_ids"] = list(task["input_ids"])
        selected.update(task_id=task["task_id"], bad=task["input_ids"][0], all=list(task["input_ids"]))
        return ledger
    before = LedgerStore(run).mutate(require_all)
    original = native_handoff._claim
    def blocked(run_dir, task_id, ident, kind, owner):
        if task_id == selected["task_id"]:
            raise module_facts.ReviewNonprogressError([selected["bad"]])
        return original(run_dir, task_id, ident, kind, owner)
    monkeypatch.setattr(native_handoff, "_claim", blocked)
    result = next_work(run, owner="controller", review_bundles=False)
    assert result["status"] == "ready"
    ready = next(i for i in result["items"] if i["role"] == "fact_review")
    after = LedgerStore(run).open()
    packet = json.loads(Path(after["calls"][ready["call_id"]]["extra"]["packet_path"]).read_text())
    assert set(packet["assigned_ids"]) == set(selected["all"]) - {selected["bad"]}
    assert result["layout_blockers"][0]["diagnostic"]["code"] == "review_context_nonprogress"
    assert after["tasks"][selected["task_id"]]["input_ids"] == selected["all"]
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())


def test_native_next_refreshes_flags_after_policy_mutation(tmp_path, monkeypatch):
    from cbe import module_facts
    run = _run(tmp_path)
    module_facts.initialize(run, batched=True, auto_budget=True, auto_input_cap=8000)
    module_facts.register_attribution_batches(run)
    def legacy(ledger):
        ledger["documentation_policy"]["budget_mode"] = "strict"
        return ledger
    LedgerStore(run).mutate(legacy)
    original = LedgerStore.mutate
    adopted = False
    refreshed = False
    opening = LedgerStore.open
    def mutate(store, callback):
        nonlocal adopted
        result = original(store, callback)
        if callback.__name__ == "adopt":
            adopted = True
        return result
    def opened(store):
        nonlocal refreshed
        result = opening(store)
        if adopted:
            refreshed = True
        return result
    monkeypatch.setattr(LedgerStore, "mutate", mutate)
    monkeypatch.setattr(LedgerStore, "open", opened)
    merge = module_facts.merge_ready
    def merge_after_refresh(*args, **kwargs):
        assert adopted and refreshed
        return merge(*args, **kwargs)
    monkeypatch.setattr(module_facts, "merge_ready", merge_after_refresh)
    assert next_work(run, owner="controller")["status"] == "ready"
    assert adopted and refreshed


def test_native_next_observes_interleaved_current_ledger_after_flag_snapshot(tmp_path, monkeypatch):
    from cbe import module_facts
    run = _run(tmp_path)
    module_facts.initialize(run, batched=True, auto_budget=True, auto_input_cap=8000)
    module_facts.register_attribution_batches(run)
    original = LedgerStore.open
    injected = False
    def opened(store):
        nonlocal injected
        snapshot = original(store)
        if store.run_dir == run.resolve() and not injected:
            injected = True
            def update(ledger):
                ledger["interleaved_marker"] = "retained"
                return ledger
            LedgerStore(run).mutate(update)
        return snapshot
    monkeypatch.setattr(LedgerStore, "open", opened)
    assert next_work(run, owner="controller")["status"] == "ready"
    assert original(LedgerStore(run))["interleaved_marker"] == "retained"


def test_only_invalid_json_backslashes_are_literalized():
    from cbe.native_handoff import _literal_invalid_escapes
    invalid = r'{"pattern":"%(\w)","legal":"\n\u0041\\w"}'
    repaired, offsets = _literal_invalid_escapes(invalid)
    assert json.loads(repaired) == {"pattern": r"%(\w)", "legal": "\nA\\w"}
    assert len(offsets) == 1
    assert _literal_invalid_escapes(repaired) == (repaired, [])
    malformed = r'{"pattern":"\uQQQQ"}'
    assert _literal_invalid_escapes(malformed) == (malformed, [])
    with pytest.raises(json.JSONDecodeError):
        json.loads(malformed)


def test_escape_recovery_retains_raw_and_does_not_bypass_identity(tmp_path):
    from cbe.native_handoff import _normalize_result
    run = _run(tmp_path)
    item = next_work(run, owner="test")["items"][0]
    ledger = LedgerStore(run).open()
    task = ledger["tasks"][item["task_id"]]
    packet = json.loads(Path(ledger["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
    payload = _business_result(run, item)
    payload["items"][0]["behavior"] = r"regex \w"
    raw = json.dumps(payload).replace(r"\\w", r"\w").encode()
    source = tmp_path / "response.txt"
    source.write_bytes(raw)
    result = _normalize_result(run, item["task_id"], item["call_id"], source, packet, task)
    assert json.loads(result.read_bytes())["items"][0]["behavior"] == r"regex \w"
    assert (run / "native" / f"{item['call_id']}.response.txt").read_bytes() == raw
    assert (run / "native" / f"{item['call_id']}.json-transform.json").exists()
    assert _normalize_result(run, item["task_id"], item["call_id"], source, packet, task) == result
    payload["envelope"] = {"call_id": "wrong"}
    source.write_text(json.dumps(payload).replace(r"\\w", r"\w"))
    with pytest.raises(StaleWriteError, match="conflicting native envelope"):
        _normalize_result(run, item["task_id"], item["call_id"], source, packet, task)


@pytest.mark.parametrize("scope", ["fact", "module", "system"])
def test_child_permission_boundary_reaches_every_dispatch(scope):
    from cbe.native_handoff import _dispatch_prompt

    packet = {"instruction": "business contract", "prompt": "business contract",
              "assignments": [], "source": "frozen evidence"}
    prompt = _dispatch_prompt(packet, scope).decode()
    assert "terminal host_blocked" in prompt
    assert "exact error, tool/action" in prompt
    assert "This report is not business JSON" in prompt
    assert "Do not repeat the denied action" in prompt
    assert "permission channel before retry" in prompt
    assert "business contract" in prompt
    assert prompt.endswith("END_CBE_NATIVE_PACKET\n")


def _run(tmp_path: Path, review_mode: str | None = "full") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text(
        "VALUES = {\n" + "".join(f"    'v{i}': {i},\n" for i in range(160))
        + "}\n\ndef twice(value):\n    return value * 2\n", encoding="utf-8")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    if review_mode is not None:
        from cbe.review_policy import configure
        configure(run, review_mode)
    return run


def _record(tmp_path: Path, run: Path, item: dict, status: str, result: dict | None = None) -> dict:
    handle = f"child-{item['call_id']}"
    host = tmp_path / f"{status}-{handle}.json"
    host.write_text(json.dumps({
        "child_handle": handle, "observed_model": "host-model",
        **({"usage": {"input_tokens": 120, "output_tokens": 20}}
           if status == "completed" else {}),
    }), encoding="utf-8")
    event = {
        "schema": "native_handoff_v1", "status": status,
        "call_id": item["call_id"], "task_id": item["task_id"],
        "generation": item["generation"], "prompt_sha256": item["prompt_sha256"],
        "host": "test-host", "child_handle": handle,
        "evidence_level": "host_tool_result", "evidence_ref": str(host),
        "transport": "inline", "additional_reads": "unknown",
    }
    if result is not None:
        event["result"] = result
    event_path = tmp_path / f"{status}-{item['call_id']}.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    return record_event(run, item["call_id"], event_path)


def _business_result(run: Path, item: dict) -> dict:
    ledger = LedgerStore(run).open()
    packet = json.loads(Path(ledger["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
    role = item["role"]
    if role == "fact_author":
        return {"items": [
            {"symbol_id": row["symbol_id"], "behavior": "Doubles its input or defines a value.",
             **({"behavior_contract": {"claims": [], "claim_refs": [], "local_view_gaps": [], "current_unresolved": []}}
                if packet.get("behavior_contract_required") else {}),
             "source_refs": [{"symbol_id": row["symbol_id"]}]}
            for row in packet["assignments"]
        ]}
    if role == "fact_review":
        return {"verdict": "accepted", "checked_ids": packet["assigned_ids"],
                "findings": [], "evidence_summary": "Each assigned claim matches its source."}
    if role == "module_author":
        gid = packet["metadata"]["group_id"]
        plan = json.loads((run / "module_plan.json").read_text())
        sid = plan["groups"][gid]["member_ids"][0]
        source = ledger["inventory"]["symbols"][sid]["path"]
        return {"content": {"summary": "The module doubles values.",
                            "flow": "twice returns value times two.", "uncertainties": "",
                            "key_symbols": [sid], "source_refs": [{"path": source, "line": 1}]}}
    if role in {"module_review", "system_review"}:
        return {"verdict": "accepted", "findings": []}
    if role == "system_author":
        return {"overview": "A small value module.", "entry_points": "Call twice.",
                "lifecycle": "The function returns immediately.",
                "data_flow": "An input becomes twice its value.", "uncertainties": "No other paths are shown."}
    raise AssertionError(role)


def test_new_native_writer_requires_contract_without_rewriting_old_business(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    assert item["role"] == "fact_author"
    _record(tmp_path, run, item, "started")
    result = _business_result(run, item)
    for row in result["items"]:
        row.pop("behavior_contract")
    before = LedgerStore(run).open()
    with pytest.raises(ValueError, match=r"requires items\[i\].behavior_contract"):
        _record(tmp_path, run, item, "completed", result)
    after = LedgerStore(run).open()
    assert after["details"] == before["details"]
    raw = json.loads((run / "raw" / f"{item['call_id']}.json").read_text())
    assert all("behavior_contract" not in row for row in raw["items"])


def test_normal_writer_shared_rule_reaches_review_and_one_public_authority(tmp_path: Path) -> None:
    from cbe.behavior_contracts import accepted_projection
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("def rule(value):\n return value * 2\n\ndef wrapper(value):\n return rule(value)\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    ledger = LedgerStore(run).open()
    ids = {symbol["name"]: sid for sid, symbol in ledger["inventory"]["symbols"].items()}
    owner_text = "The returned value is doubled."
    action = next_work(run, owner="synthetic-controller", review_mode="full")
    saw_contract_review = False
    while action["status"] != "complete":
        assert action["status"] == "ready", action
        item = action["items"][0]
        packet = json.loads(Path(LedgerStore(run).open()["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
        result = _business_result(run, item)
        if item["role"] == "fact_author":
            for row in result["items"]:
                if row["symbol_id"] == ids["rule"]:
                    row["behavior"] = "Transforms a value."
                    row["behavior_contract"]["claims"] = [{"id": "double", "effect": owner_text}]
                elif row["symbol_id"] == ids["wrapper"]:
                    row["behavior"] = "Delegates to rule."
                    row["behavior_contract"]["claim_refs"] = [{"symbol_id": ids["rule"], "claim_id": "double"}]
        elif item["role"] == "fact_review":
            has_contract = any(row.get("behavior_contract") for row in packet.get("draft_projection") or [])
            if has_contract:
                assert "Review behavior together with behavior_contract" in packet["instruction"]
                saw_contract_review = True
        _record(tmp_path, run, item, "started")
        _record(tmp_path, run, item, "completed", result)
        action = next_work(run, owner="synthetic-controller")
    ledger = LedgerStore(run).open()
    assert saw_contract_review
    assert accepted_projection(ledger, ids["wrapper"])["claim_refs"][0]["status"] == "accepted"
    pages = "\n".join(path.read_text() for path in Path(ledger["reader_output_dir"]).rglob("*.md"))
    assert pages.count(owner_text) == 1
    assert "Rule:" in pages


def test_native_host_handoff_reuses_fact_module_system_imports(tmp_path: Path) -> None:
    run = _run(tmp_path)
    first = next_work(run, owner="controller", model="host-model")
    assert first["status"] == "ready"
    assert next_work(run, owner="controller")["status"] == "needs_reconciliation"
    seen = set()
    while first["status"] != "complete":
        assert first["status"] == "ready", first
        item = first["items"][0]
        assert item["call_id"] not in seen
        seen.add(item["call_id"])
        _record(tmp_path, run, item, "started")
        assert next_work(run, owner="controller")["status"] == "waiting"
        completed = _record(tmp_path, run, item, "completed", _business_result(run, item))
        assert completed["status"] == "completed"
        first = next_work(run, owner="controller", model="host-model")
    assert len(seen) >= 6
    assert Path(first["reader_index"]).is_file()
    assert first["native_usage"]["known_total_tokens"] == 140 * len(seen)
    assert first["token_budget"]["policy"] == "report"


def test_native_record_rejects_wrong_generation_and_child_rebinding(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    host = tmp_path / "host.json"
    host.write_text(json.dumps({"child_handle": "child-one"}))
    event = {"schema": "native_handoff_v1", "status": "started",
             "call_id": item["call_id"], "task_id": item["task_id"],
             "generation": item["generation"] + 1,
             "prompt_sha256": item["prompt_sha256"], "host": "test-host",
             "child_handle": "child-one", "evidence_level": "host_tool_result",
             "evidence_ref": str(host)}
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event))
    with pytest.raises(StaleWriteError, match="generation"):
        record_event(run, item["call_id"], path)
    event["generation"] = item["generation"]
    path.write_text(json.dumps(event))
    record_event(run, item["call_id"], path)
    event["child_handle"] = "child-two"
    path.write_text(json.dumps(event))
    with pytest.raises(ValueError, match="child handle"):
        record_event(run, item["call_id"], path)


def _dsh_session(path: Path, item: dict, result: dict, *, handle: str = "native-child") -> Path:
    prompt = Path(item["dispatch_prompt_path"]).read_text()
    events = [
        {"type": "session", "id": handle, "origin": "subagent", "parentSession": "parent"},
        {"type": "assistant/message", "data": {
            "message": {"id": "request-1", "source": {"kind": "model", "model": "glm-5.3-flash"},
                        "content": [{"type": "tool-call", "name": "read"}]},
            "usage": {"inputTokens": 10, "cacheReadTokens": 0, "outputTokens": 2, "totalTokens": 12}}},
        {"type": "tool/result", "data": {"meta": {"lines": [
            {"number": i + 1, "text": line} for i, line in enumerate(prompt.splitlines())]}}},
        {"type": "assistant/message", "data": {
            "message": {"id": "request-2", "source": {"kind": "model", "model": "glm-5.3-flash"},
                        "content": [{"type": "text", "text": json.dumps(result)}]},
            "usage": {"inputTokens": 5831, "cacheReadTokens": 1152, "outputTokens": 117, "totalTokens": 7100}}},
    ]
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    return path


def test_public_record_imports_exact_dsh_child_final_and_native_total(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="dsh", child_handle="native-child")
    session = _dsh_session(tmp_path / "child.jsonl", item, _business_result(run, item))
    result = record(run, item["call_id"], status="completed", host="dsh", session_file=session)
    assert result["status"] == "completed"
    ledger = LedgerStore(run).open()
    call = ledger["calls"][item["call_id"]]
    assert call["usage"]["total_tokens"] == 7112
    assert call["usage"]["cached_input_tokens"] == 1152
    assert call["extra"]["source_observation"]["prompt_presentations_conditional_upper"] == 1
    assert call["exposure_evidence"] == "unverified"
    from cbe.accounting import overall_token_budget
    assert overall_token_budget(ledger)["known_total_tokens"] == 7112
    assert overall_token_budget(ledger)["parent_usage"] == "unavailable"
    assert record(run, item["call_id"], status="completed", host="dsh", session_file=session)["idempotent"]


def test_public_record_fallback_never_invents_usage(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="codex", child_handle="child-a")
    result = tmp_path / "result.json"
    result.write_text(json.dumps(_business_result(run, item)))
    record(run, item["call_id"], status="completed", host="codex", result_path=result)
    call = LedgerStore(run).open()["calls"][item["call_id"]]
    assert call["usage"] == "unavailable"
    assert call["extra"]["delivery_evidence"] == "controller_attested"
    assert call["actual_model"] is None


def test_public_record_rejects_other_child_artifact(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="dsh", child_handle="child-a")
    artifact = tmp_path / "wrong.json"
    artifact.write_text(json.dumps({"child_handle": "child-b", "result": _business_result(run, item)}))
    with pytest.raises(ValueError, match="child handle"):
        record(run, item["call_id"], status="completed", host="dsh", host_result=artifact)


def test_dsh_missing_counter_is_unknown_and_duplicate_message_not_counted(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    session = _dsh_session(tmp_path / "child.jsonl", item, {})
    events = [json.loads(line) for line in session.read_text().splitlines()]
    events[1]["data"]["usage"].pop("cacheReadTokens")
    events.append(events[-1])
    session.write_text("\n".join(json.dumps(row) for row in events))
    parsed = parse_dsh_session(session, child_handle="native-child",
                               dispatch_prompt=Path(item["dispatch_prompt_path"]).read_bytes())
    assert "cached_input_tokens" not in parsed["usage"]
    assert parsed["usage"]["total_tokens"] == 7112
    assert parsed["request_count"] == 2


def test_author_child_cannot_be_reused_for_review_under_host_alias(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="codex", child_handle="same-child")
    result = tmp_path / "author.json"
    result.write_text(json.dumps(_business_result(run, item)))
    record(run, item["call_id"], status="completed", host="codex", result_path=result)
    reviewer = next_work(run, owner="controller")["items"][0]
    with pytest.raises(ValueError, match="fresh child"):
        record(run, reviewer["call_id"], status="started", host="Codex_App", child_handle="same-child")


def test_dsh_chunked_prompt_reads_and_retained_history_upper(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    session = _dsh_session(tmp_path / "chunked.jsonl", item, {})
    events = [json.loads(line) for line in session.read_text().splitlines()]
    lines = events[2]["data"]["meta"]["lines"]
    cut = len(lines) // 2
    events[2]["data"]["meta"]["lines"] = lines[:cut]
    later_read = {"type": "tool/result", "data": {"meta": {"lines": lines[cut:]}}}
    final = events[-1]
    intermediate = json.loads(json.dumps(final))
    intermediate["data"]["message"]["id"] = "request-intermediate"
    intermediate["data"]["message"]["content"] = [{"type": "tool-call", "name": "write"}]
    events = events[:3] + [later_read, intermediate, final]
    session.write_text("\n".join(json.dumps(row) for row in events))
    record(run, item["call_id"], status="started", host="dsh", child_handle="native-child")
    observation = parse_dsh_session(session, child_handle="native-child",
                                   dispatch_prompt=Path(item["dispatch_prompt_path"]).read_bytes())
    assert observation["source_observation"]["prompt_presentations_conditional_upper"] == 2
    # Replace the synthetic final with valid business semantics for import.
    events[-1]["data"]["message"]["content"] = [{"type": "text", "text": json.dumps(_business_result(run, item))}]
    session.write_text("\n".join(json.dumps(row) for row in events))
    record(run, item["call_id"], status="completed", host="dsh", session_file=session)
    call = LedgerStore(run).open()["calls"][item["call_id"]]
    assert any(row["event_kind"] == "reinjection" and row["counted_as"] == "possible_source"
               for row in call["source_exposures"])


def test_failed_call_requires_observed_terminal_failure_and_keeps_cost(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="dsh", child_handle="failed-child")
    evidence = tmp_path / "failure.json"
    evidence.write_text(json.dumps({"child_handle": "failed-child", "usage": {"total_tokens": 41}}))
    with pytest.raises(ValueError, match="terminal child failure"):
        record(run, item["call_id"], status="failed", host="dsh", host_result=evidence)
    # A rejected controller request is not an accepted immutable event.
    complete = tmp_path / "terminal-failure.json"
    complete.write_text(json.dumps({"child_handle": "failed-child", "status": "failed",
                                    "usage": {"total_tokens": 41}}))
    record(run, item["call_id"], status="failed", host="dsh", host_result=complete)
    from cbe.accounting import overall_token_budget
    ledger = LedgerStore(run).open()
    assert ledger["tasks"][item["task_id"]]["state"] == "pending"
    report = overall_token_budget(ledger)
    assert report["known_total_tokens"] == 41
    assert report["known_input_tokens"] is None


def test_cumulative_snapshot_is_differenced_once_and_missing_baseline_unknown() -> None:
    from cbe.native_handoff import _usage
    snapshot = {"input_tokens": 180, "output_tokens": 30, "total_tokens": 240}
    prior = {"native_usage_baseline": {"input_tokens": 100, "output_tokens": 10, "total_tokens": 120}}
    assert _usage({"usage_kind": "cumulative"}, snapshot, prior) == {
        "input_tokens": 80, "output_tokens": 20, "total_tokens": 120}
    assert _usage({"usage_kind": "cumulative"}, snapshot, {}) == "unavailable"


def test_seeded_child_is_not_independent_and_changed_session_cannot_rewrite_evidence(tmp_path: Path) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    session = _dsh_session(tmp_path / "session.jsonl", item, _business_result(run, item))
    events = [json.loads(line) for line in session.read_text().splitlines()]
    events[0]["isSeeded"] = True
    session.write_text("\n".join(json.dumps(row) for row in events))
    with pytest.raises(ValueError, match="fresh native child"):
        parse_dsh_session(session, child_handle="native-child",
                          dispatch_prompt=Path(item["dispatch_prompt_path"]).read_bytes())
    events[0]["isSeeded"] = False
    session.write_text("\n".join(json.dumps(row) for row in events))
    record(run, item["call_id"], status="started", host="dsh", child_handle="native-child")
    record(run, item["call_id"], status="completed", host="dsh", session_file=session)
    call = LedgerStore(run).open()["calls"][item["call_id"]]
    accepted_event = Path(call["extra"]["native_event_ref"])
    accepted_bytes = accepted_event.read_bytes()
    observation = Path(json.loads(accepted_bytes)["evidence_ref"])
    observation_bytes = observation.read_bytes()
    events[-1]["data"]["usage"]["totalTokens"] += 1
    session.write_text("\n".join(json.dumps(row) for row in events))
    with pytest.raises(StaleWriteError, match="already recorded"):
        record(run, item["call_id"], status="completed", host="dsh", session_file=session)
    assert accepted_event.read_bytes() == accepted_bytes
    assert observation.read_bytes() == observation_bytes


@pytest.mark.parametrize("host", ["codex", "claude-code"])
def test_explicit_other_host_transcript_preserves_its_own_usage_contract(tmp_path: Path, host: str) -> None:
    from cbe.native_session import parse_session
    prompt = b"Exact frozen task\n"
    if host == "codex":
        events = [
            {"type": "session_meta", "payload": {"id": "child"}},
            {"type": "turn_context", "payload": {"model": "observed-codex-model"}},
            {"type": "response_item", "payload": {"type": "message", "role": "user",
                 "content": [{"type": "input_text", "text": prompt.decode()}]}},
            {"type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}}}},
            {"type": "event_msg", "payload": {"type": "token_count", "info": {
                "total_token_usage": {"input_tokens": 150, "output_tokens": 35,
                                      "cached_input_tokens": 100, "total_tokens": 185}}}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                 "phase": "final_answer", "content": [{"type": "output_text", "text": "{}"}]}},
        ]
    else:
        events = [
            {"type": "user", "agentId": "child", "isSidechain": True,
             "message": {"content": prompt.decode()}},
            {"type": "assistant", "agentId": "child", "isSidechain": True, "message": {
                "id": "real-message-1",
                "model": "observed-claude-model", "content": [{"type": "text", "text": "{}"}],
                "usage": {"input_tokens": 100, "output_tokens": 20,
                          "cache_read_input_tokens": 80, "cache_creation_input_tokens": 10}}},
        ]
    session = tmp_path / "explicit.jsonl"
    session.write_text("\n".join(json.dumps(row) for row in events))
    result = parse_session(session, host=host, child_handle="child", dispatch_prompt=prompt)
    assert result["final"] == "{}"
    if host == "codex":
        assert result["usage"]["total_tokens"] == 185
        assert result["usage"]["cache_included_in_input"] is True
    else:
        assert result["usage"]["cached_input_tokens"] == 80
        assert result["usage"]["cache_creation_input_tokens"] == 10
        assert result["usage"]["cache_included_in_input"] is False


def test_native_default_uses_existing_small_packet_plan_without_dropping_symbols(tmp_path: Path) -> None:
    repo = tmp_path / "many-functions"
    repo.mkdir()
    (repo / "ops.py").write_text("VALUES = {" + ",".join(f"'v{i}':{i}" for i in range(160)) + "}\n" + "\n".join(
        f"def operation_{i}(value):\n    if value is None:\n        return {i}\n    return value + {i}\n"
        for i in range(100)))
    run = tmp_path / "small-packets"
    analyze(repo, run, documentation_profile="module-first-v2")
    item = next_work(run, owner="controller")["items"][0]
    assert item["prompt_tokens"] <= 8000
    assert Path(item["dispatch_prompt_path"]).read_text().endswith("END_CBE_NATIVE_PACKET\n")
    ledger = LedgerStore(run).open()
    assert all(batch["max_input_tokens"] <= 8000 for batch in ledger["fact_batches"].values())
    assigned = {sid for batch in ledger["fact_batches"].values() for sid in batch["input_ids"]}
    executable = {sid for sid, symbol in ledger["inventory"]["symbols"].items()
                  if symbol["kind"] in {"function", "method", "lambda"}}
    assert executable <= assigned
    assert len(ledger["fact_batches"]) > 1


def test_local_preparation_write_failure_retries_without_ambiguous_delivery(tmp_path: Path, monkeypatch) -> None:
    from cbe import module_facts
    run = _run(tmp_path)
    writer = module_facts.atomic_write_bytes
    def broken(path, raw):
        raise OSError("simulated local disk fault")
    monkeypatch.setattr(module_facts, "atomic_write_bytes", broken)
    with pytest.raises(OSError, match="local disk fault"):
        next_work(run, owner="controller")
    ledger = LedgerStore(run).open()
    failed = next(iter(ledger["calls"].values()))
    assert failed["state"] == "released"
    assert failed["extra"]["send_evidence"] == "not_sent_bootstrap"
    monkeypatch.setattr(module_facts, "atomic_write_bytes", writer)
    assert next_work(run, owner="controller")["status"] == "ready"


def test_prepared_local_artifacts_without_host_evidence_are_not_reoffered(tmp_path: Path) -> None:
    from cbe import module_facts
    run = _run(tmp_path)
    module_facts.initialize(run, batched=True, auto_budget=True, auto_input_cap=8000)
    ledger = LedgerStore(run).open()
    batch_id = next(iter(ledger["fact_batches"]))
    claim = module_facts.claim(run, batch_id, owner="controller/fact_author")
    before = LedgerStore(run).open()
    result = next_work(run, owner="controller")
    assert result["status"] == "needs_reconciliation"
    assert result["items"][0]["call_id"] == claim["call_id"]
    assert result["items"][0]["recovery_action"] == "inspect_original_host_window_and_reconcile_existing_call"
    assert "dispatch_prompt_path" not in result["items"][0]
    assert "recovered_local_preparation" not in result
    assert LedgerStore(run).open()["calls"] == before["calls"]


@pytest.mark.parametrize("later_status", ["offered", "failed"])
@pytest.mark.parametrize("split_after_ready", [False, True])
def test_unknown_preparation_keeps_later_active_visible_and_independent_work_runnable(tmp_path: Path, monkeypatch, later_status: str, split_after_ready: bool) -> None:
    from cbe import module_facts, native_handoff
    repo = tmp_path / "repo"
    repo.mkdir()
    for index in range(30):
        (repo / f"ops_{index}.py").write_text(f"def f_{index}(value):\n    return value + {index}\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True, max_output_estimate=1000, max_input_tokens=8000)
    module_facts.register_attribution_batches(run)
    batches = sorted(LedgerStore(run).open()["fact_batches"])
    assert len(batches) > 2
    unknown = module_facts.claim(run, batches[0], owner="original-controller/fact_author")
    offered = module_facts.claim(run, batches[1], owner="original-controller/fact_author")
    later = native_handoff._offer(run, offered["task_id"], offered, None)
    if later_status == "failed":
        _record(tmp_path, run, later, "started")
        # A controller-attested failure has no host terminal proof and keeps
        # its current lease protected. A host-proven failure is released instead.
        record(run, later["call_id"], status="failed", host="test-host",
               child_handle=f"child-{later['call_id']}")
    before = LedgerStore(run).open()
    if split_after_ready:
        claim = native_handoff._claim
        attempts = []
        def layout_after_one(run_dir, task_id, ident, kind, owner):
            attempts.append(task_id)
            if len(attempts) == 2:
                assert kind == "fact_author"
                raise module_facts.PromptLayoutError(scope="native_fact_complete",
                    ids=before["tasks"][task_id]["input_ids"], tokens=8001, cap=8000)
            return claim(run_dir, task_id, ident, kind, owner)
        monkeypatch.setattr(native_handoff, "_claim", layout_after_one)
        monkeypatch.setattr(module_facts, "split_pending_repair", lambda *args, **kwargs: True)
    result = next_work(run, owner="new-controller", count=2 if split_after_ready else 1, review_bundles=False)
    assert result["status"] == "ready"
    assert result["items"][0]["call_id"] not in {unknown["call_id"], offered["call_id"]}
    assert {item["call_id"] for item in result["active"]} == {unknown["call_id"], offered["call_id"]}
    assert all(item["status"] == "needs_reconciliation" for item in result["active"])
    after = LedgerStore(run).open()
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())


@pytest.mark.parametrize("malformed", ["{}", "not-json"])
def test_completed_invalid_business_output_is_repairable_and_replay_idempotent(tmp_path: Path, malformed: str) -> None:
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    record(run, item["call_id"], status="started", host="test", child_handle="bad-child")
    result = tmp_path / "bad-result.txt"
    result.write_text(malformed)
    rejected = record(run, item["call_id"], status="completed", host="test", result_path=result)
    assert rejected["status"] == "result_rejected"
    assert rejected["model_completed"] is True
    ledger = LedgerStore(run).open()
    assert ledger["tasks"][item["task_id"]]["state"] == "needs_repair"
    assert ledger["calls"][item["call_id"]]["extra"]["native_handoff"]["status"] == "completed"
    assert ledger["calls"][item["call_id"]]["state"] == "imported"
    assert record(run, item["call_id"], status="completed", host="test", result_path=result)["idempotent"]
    repair = next_work(run, owner="controller")
    assert repair["status"] == "ready"
    assert repair["items"][0]["task_id"] == item["task_id"]
    assert rejected["reason"] in Path(repair["items"][0]["dispatch_prompt_path"]).read_text()


@pytest.mark.parametrize("changed_input", [False, True])
def test_split_repair_can_replace_existing_same_source_facts(tmp_path, changed_input):
    from cbe import module_facts
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("class A(factory()):\n    pass\nclass B(factory()):\n    pass\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    original = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, original, "started")
    _record(tmp_path, run, original, "completed", _business_result(run, original))
    before = LedgerStore(run).open()
    tid = original["task_id"]
    ids = before["tasks"][tid]["input_ids"]
    assert len(ids) >= 2
    def require_repair(ledger):
        task = ledger["tasks"][tid]
        task["state"] = "needs_repair"
        task["extra"]["repair_ids"] = ids
        task["residual"] = [{"symbol_id": sid, "reason": "Correct the behavior."} for sid in ids]
        if changed_input:
            task["input_hash"] = "f" * 64
        return ledger
    LedgerStore(run).mutate(require_repair)
    assert module_facts.split_pending_repair(run, tid)
    split = LedgerStore(run).open()
    assert split["details"] == before["details"]
    assert split["calls"] == before["calls"]
    assert all(split["tasks"][f"task:fact_author:{bid}"]["input_hash"] ==
               split["tasks"][tid]["input_hash"]
               for bid in split["tasks"][tid]["extra"]["superseded_by"])
    for bid in split["tasks"][tid]["extra"]["superseded_by"]:
        if changed_input:
            # A random hash is not a new frozen input. Reject before any model
            # call instead of consuming a call and rejecting its output later.
            with pytest.raises(StaleWriteError, match="ancestry input or source revision mismatch"):
                module_facts.claim(run, bid, owner="controller/fact_author")
            assert LedgerStore(run).open()["details"] == before["details"]
            assert LedgerStore(run).open()["calls"] == before["calls"]
            continue
        claim = module_facts.claim(run, bid, owner="controller/fact_author")
        item = _offer_fresh_claim(run, claim)
        _record(tmp_path, run, item, "started")
        result = _record(tmp_path, run, item, "completed", _business_result(run, item))
        assert result["state"] == "committed", result
        assert result["accepted_items"] == len(split["fact_batches"][bid]["input_ids"])


@pytest.mark.parametrize("damage", [None, "revision", "scope", "contract", "hash", "missing"])
def test_legacy_split_identity_requires_proven_same_source_ancestry(damage):
    from cbe import module_facts
    from cbe.models import TaskRecord
    ledger = {"source_revision": "frozen", "tasks": {}, "fact_batches": {}}
    for tid, bid, ids in [("root", "whole", ["a", "b", "c"]), ("child", "part", ["a", "b"])]:
        batch = {"batch_id": bid, "input_ids": ids}
        ledger["fact_batches"][bid] = batch
        h = module_facts._sha_json({"contract": "module-facts/1", "batch": batch, "source_revision": "frozen"})
        task = TaskRecord(tid, "fact_author", ids, h, "needs_repair",
                          extra={"fact_contract": "module-facts/1", "batch_id": bid})
        ledger["tasks"][tid] = task.to_dict()
    ledger["tasks"]["root"]["extra"]["superseded_by"] = ["part"]
    ledger["tasks"]["child"]["extra"]["split_from"] = "root"
    if damage == "revision": ledger["source_revision"] = "different"
    if damage == "scope": ledger["tasks"]["child"]["input_ids"] = ["outside"]
    if damage == "contract": ledger["tasks"]["root"]["extra"]["fact_contract"] = "different"
    if damage == "hash": ledger["tasks"]["child"]["input_hash"] = "unknown"
    if damage == "missing": del ledger["tasks"]["root"]
    if damage:
        with pytest.raises(StaleWriteError):
            module_facts._split_input_identity(ledger, TaskRecord.from_dict(ledger["tasks"]["child"]))
    else:
        assert module_facts._split_input_identity(ledger, TaskRecord.from_dict(ledger["tasks"]["child"])) == ledger["tasks"]["root"]["input_hash"]


def test_pending_repair_split_preserves_history_and_feedback(tmp_path):
    from cbe import module_facts
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "objects.py").write_text("class A(factory()):\n    pass\nclass B(factory()):\n    pass\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    item = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", {"items": []})
    before = LedgerStore(run).open()
    task = before["tasks"][item["task_id"]]
    ids = task["extra"]["repair_ids"]
    assert len(ids) >= 2
    calls = before["calls"]
    def repeated_errors(ledger):
        ledger["tasks"][item["task_id"]]["extra"]["repair_ids"] = ids + ids
        return ledger
    LedgerStore(run).mutate(repeated_errors)
    assert module_facts.split_pending_repair(run, item["task_id"])
    after = LedgerStore(run).open()
    assert after["calls"] == calls
    replacements = after["tasks"][item["task_id"]]["extra"]["superseded_by"]
    children = [after["tasks"][f"task:fact_author:{bid}"] for bid in replacements]
    combined = [sid for child in children for sid in child["input_ids"]]
    assert sorted(combined) == sorted(ids)
    assert len(combined) == len(set(combined))
    assert all(child["residual"] for child in children)
    assert not module_facts.split_pending_repair(run, item["task_id"])
    # An indivisible global finding remains intact and stops at a singleton.
    def oversize(ledger):
        for child in children:
            ledger["tasks"][child["task_id"]]["residual"].append(
                {"reason": "global finding " * 9000})
        return ledger
    LedgerStore(run).mutate(oversize)
    blocked = next_work(run, owner="controller")
    assert blocked["status"] == "needs_layout"
    assert len(blocked["diagnostic"]["assigned_ids"]) == 1
    assert blocked["diagnostic"]["next_action"] == "provide_explicit_fragment_contract_or_larger_host_window"
    count = len(LedgerStore(run).open()["fact_batches"])
    assert next_work(run, owner="controller")["status"] == "needs_layout"
    assert len(LedgerStore(run).open()["fact_batches"]) == count


@pytest.mark.parametrize("role", ["module_author", "module_review", "system_author", "system_review"])
def test_module_system_format_rejection_retries_same_task_and_preserves_prior_stages(tmp_path: Path, role: str) -> None:
    run = _run(tmp_path)
    while True:
        item = next_work(run, owner="controller")["items"][0]
        record(run, item["call_id"], status="started", host="test", child_handle=item["call_id"])
        if item["role"] == role:
            break
        path = tmp_path / "business.json"
        path.write_text(json.dumps(_business_result(run, item)))
        record(run, item["call_id"], status="completed", host="test", result_path=path)
    original_facts = json.loads(json.dumps(LedgerStore(run).open()["details"]))
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("{}")
    rejected = record(run, item["call_id"], status="completed", host="test", result_path=invalid)
    assert rejected["status"] == "result_rejected"
    assert record(run, item["call_id"], status="completed", host="test", result_path=invalid)["idempotent"]
    repaired = next_work(run, owner="controller")["items"][0]
    assert repaired["task_id"] == item["task_id"]
    assert LedgerStore(run).open()["details"] == original_facts
    assert rejected["reason"] in Path(repaired["dispatch_prompt_path"]).read_text()


def test_system_revision_native_prompt_contains_previous_draft_and_specific_findings(tmp_path: Path) -> None:
    run = _run(tmp_path)
    original_prompt = None
    while True:
        item = next_work(run, owner="controller")["items"][0]
        record(run, item["call_id"], status="started", host="test", child_handle=item["call_id"])
        if item["role"] == "system_author":
            original_prompt = Path(item["dispatch_prompt_path"]).read_bytes()
        result = _business_result(run, item)
        if item["role"] == "system_review":
            result = {"verdict": "revision_required", "findings": [
                {"reason": "Unsupported background lifecycle claim; preserve supported value flow."}]}
        path = tmp_path / "system-business.json"
        path.write_text(json.dumps(result))
        record(run, item["call_id"], status="completed", host="test", result_path=path)
        if item["role"] == "system_review":
            break
    repair = next_work(run, owner="controller")["items"][0]
    assert repair["role"] == "system_author"
    prompt = Path(repair["dispatch_prompt_path"]).read_bytes()
    assert prompt != original_prompt
    assert b"Unsupported background lifecycle claim" in prompt
    assert b"previous_draft" in prompt
    assert repair["source_chars"] == 0


def test_review_large_draft_uses_partial_existing_view_and_preserves_unchecked_obligations(tmp_path: Path) -> None:
    repo = tmp_path / "review-window"
    repo.mkdir()
    (repo / "ops.py").write_text("VALUES = {" + ",".join(f"'v{i}':{i}" for i in range(160)) + "}\n" + "\n".join(
        f"def f_{i}(value):\n    try:\n        return value + {i}\n    except TypeError:\n        return None\n"
        for i in range(20)))
    run = tmp_path / "review-run"
    analyze(repo, run, documentation_profile="module-first-v2")
    while True:
        item = next_work(run, owner="controller", review_mode="full")["items"][0]
        ledger = LedgerStore(run).open()
        packet = json.loads(Path(ledger["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
        record(run, item["call_id"], status="started", host="test", child_handle=item["call_id"])
        if item["role"] == "fact_author" and all(row["kind"] in {"function", "method", "lambda"} for row in packet["assignments"]):
            break
        interim = tmp_path / "interim.json"
        interim.write_text(json.dumps(_business_result(run, item)))
        record(run, item["call_id"], status="completed", host="test", result_path=interim)
    ids = [row["symbol_id"] for row in packet["assignments"]]
    result = tmp_path / "large-draft.json"
    result.write_text(json.dumps({"items": [{"symbol_id": sid,
        "behavior": "Returns the adjusted value and catches TypeError. " * 150,
        "behavior_contract": {"claims": [], "claim_refs": [], "local_view_gaps": [], "current_unresolved": []},
        "source_refs": [{"symbol_id": sid}]} for sid in ids]}))
    record(run, item["call_id"], status="completed", host="test", result_path=result)
    saved = json.loads(json.dumps(LedgerStore(run).open()["details"]))
    review = next_work(run, owner="controller")["items"][0]
    assert review["role"] == "fact_review"
    ledger = LedgerStore(run).open()
    review_packet = json.loads(Path(ledger["calls"][review["call_id"]]["extra"]["packet_path"]).read_text())
    assert len(review_packet["assigned_ids"]) < len(ids)
    assert ledger["calls"][review["call_id"]]["extra"]["actual_prompt_tokens"] <= 8000
    assert ledger["details"] == saved
    record(run, review["call_id"], status="started", host="test", child_handle="window-reviewer")
    result.write_text(json.dumps({"verdict": "accepted", "checked_ids": review_packet["assigned_ids"],
                                 "findings": [], "evidence_summary": "All assigned facts match the provided spans."}))
    record(run, review["call_id"], status="completed", host="test", result_path=result)
    task = LedgerStore(run).open()["tasks"][review["task_id"]]
    assert task["state"] == "needs_repair"
    assert task["residual"]
    subsequent = next_work(run, owner="controller")["items"][0]
    assert subsequent["role"] == "fact_review"
    current = LedgerStore(run).open()
    subsequent_packet = json.loads(Path(current["calls"][subsequent["call_id"]]["extra"]["packet_path"]).read_text())
    assert not set(subsequent_packet["assigned_ids"]) & set(review_packet["assigned_ids"])


def test_single_attribution_object_over_window_is_explicit_not_silently_skipped(tmp_path: Path) -> None:
    repo = tmp_path / "unsplittable"
    repo.mkdir()
    (repo / "startup.py").write_text('SIDE_EFFECT = activate([' + ','.join(
        f'"entry_{i}"' for i in range(6000)) + '])\ndef f():\n    return 1\n')
    run = tmp_path / "unsplittable-run"
    analyze(repo, run, documentation_profile="module-first-v2")
    result = next_work(run, owner="controller")
    assert result["status"] == "needs_layout"
    assert result["diagnostic"]["next_action"] == "provide_explicit_fragment_contract_or_larger_host_window"
    assert len(result["diagnostic"]["assigned_ids"]) == 1
    assert result["diagnostic"]["model_sent"] is False
    assert not LedgerStore(run).open()["calls"]


def test_cross_file_attribution_assignments_and_reference_repair(tmp_path):
    from cbe.ir import line_starts
    from bisect import bisect_right
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("test_azureblockblob.py", "test_base.py"):
        # This test exercises model attribution; pure method containers now
        # have program syntax evidence and intentionally avoid that path.
        (repo / name).write_text("import os\n\nclass Backend:\n    marker = object()\n    def run(self):\n" +
                               "        value = 1\n" * 25 + "        return value\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    offered = next_work(run, owner="controller", count=20)
    ledger = LedgerStore(run).open()
    item = next(i for i in offered["items"] if ledger["tasks"][i["task_id"]]["extra"].get("attribution"))
    packet = json.loads(Path(ledger["calls"][item["call_id"]]["extra"]["packet_path"]).read_text())
    assert {a["source_path"] for a in packet["assignments"]} == {"test_azureblockblob.py", "test_base.py"}
    for assignment in packet["assignments"]:
        symbol = ledger["inventory"]["symbols"][assignment["symbol_id"]]
        assert assignment["source_path"] == symbol["path"]
        start = (symbol.get("exclusive_spans") or [symbol["span"]])[0]["start"]
        assert assignment["start_line"] == bisect_right(line_starts((repo / symbol["path"]).read_text()), start)
    result = _business_result(run, item)
    residual = next(row for row in result["items"] if row["symbol_id"].startswith("test_azureblockblob.py::"))
    residual["source_refs"].append({"path": "test_azureblockblob.py", "line": 20})
    _record(tmp_path, run, item, "started")
    rejected = _record(tmp_path, run, item, "completed", result)
    assert rejected["status"] == "result_rejected"
    assert "outside its assigned packet" in rejected["reason"]
    assert _record(tmp_path, run, item, "completed", result)["status"] == "result_rejected"
    repair = next_work(run, owner="controller")
    assert repair["status"] == "ready"
    assert rejected["reason"] in Path(repair["items"][0]["dispatch_prompt_path"]).read_text()


def test_executable_fragment_repair_split_retains_merge_and_review_obligations(tmp_path, monkeypatch):
    from cbe import module_facts, runner
    from cbe.packets import pack_inventory
    monkeypatch.setattr(runner, "packet_window", lambda: 700)
    monkeypatch.setattr(module_facts, "_pack_for_batches", lambda ledger, inventory, *args:
                        pack_inventory(inventory, repo=Path(ledger["repo_root"]), window_chars=700))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("def big(value):\n" + "".join(
        f"    value = value + {i}\n" for i in range(120)) + "    return value\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True)
    ledger = LedgerStore(run).open()
    tid = next(key for key, task in ledger["tasks"].items()
               if task["kind"] == "fact_author" and len(task["input_ids"]) > 1)
    original_ids = ledger["tasks"][tid]["input_ids"]
    assert any(task["kind"] == "merge" and set(original_ids).intersection(
        task["extra"]["fragment_ids"]) for task in ledger["tasks"].values())
    review_id = "task:fact_review:retained-history"
    def prepare(ledger):
        task = ledger["tasks"][tid]
        task["state"] = "needs_repair"
        task["extra"]["repair_ids"] = original_ids
        task["residual"] = [{"symbol_id": sid, "reason": "Correct this fragment."} for sid in original_ids]
        ledger["tasks"][review_id] = {**task, "task_id": review_id, "kind": "fact_review",
                                     "extra": {"required_review_ids": list(original_ids)}, "state": "needs_repair"}
        detail = {"symbol_id": original_ids[0], "behavior": "Previously accepted fragment."}
        ledger["details"][original_ids[0]] = detail
        ledger.setdefault("fact_reviews", {})[original_ids[0]] = {
            "state": "source_checked", "content_sha256": module_facts._sha_json(detail)}
        return ledger
    LedgerStore(run).mutate(prepare)
    before = LedgerStore(run).open()
    assert module_facts.split_pending_repair(run, tid)
    after = LedgerStore(run).open()
    assert after["tasks"][review_id] == before["tasks"][review_id]
    children = [f"task:fact_author:{bid}" for bid in after["tasks"][tid]["extra"]["superseded_by"]]
    assert after["details"] == before["details"]
    assert after["fact_reviews"] == before["fact_reviews"]
    assert {sid for child in children for sid in after["tasks"][child]["input_ids"]} == set(original_ids[1:])
    for merge in after["tasks"].values():
        if merge["kind"] != "merge":
            continue
        fragments = set(merge["extra"]["fragment_ids"])
        for child in children:
            if fragments.intersection(after["tasks"][child]["input_ids"]):
                assert child in merge["extra"]["slice_task_ids"]
        assert tid not in merge["extra"]["slice_task_ids"]
    for child in children:
        bid = after["tasks"][child]["extra"]["batch_id"]
        claimed = module_facts.claim(run, bid, owner="repair-author", kind="author")
        packet = json.loads(Path(claimed["packet_path"]).read_text())
        assert set(packet["assigned_ids"]) == set(after["tasks"][child]["input_ids"])
        assert packet["repair_findings"]


def test_single_executable_repair_overflow_is_stable(tmp_path):
    run = _run(tmp_path)
    item = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, item, "started")
    _record(tmp_path, run, item, "completed", {})
    def finding(ledger):
        task = ledger["tasks"][item["task_id"]]
        assert len(task["extra"]["repair_ids"]) == 1
        task["residual"].append({"reason": "Keep this indivisible global finding. " * 5000})
        return ledger
    LedgerStore(run).mutate(finding)
    before = LedgerStore(run).open()
    for _ in range(2):
        outcome = next_work(run, owner="controller")
        assert outcome["status"] == "needs_layout"
        assert len(outcome["diagnostic"]["assigned_ids"]) == 1
    after = LedgerStore(run).open()
    assert after["fact_batches"] == before["fact_batches"]
    assert after["calls"] == before["calls"]


def test_wide_review_request_prepares_progressive_current_evidence(tmp_path):
    from cbe import module_facts
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("class Outer(factory()):\n    marker = activate()\n    class Inner(factory()):\n" +
        "".join(f"        field_{i} = '{'x' * 70}'\n" for i in range(100)))
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    # Preserve this original narrow-review context counterexample as an old
    # initialized run. Full mode legitimately adds other same-file source views;
    # this compatibility test retains the original frozen sampling scope.
    def historical(ledger):
        ledger.pop("native_default_review_mode", None)
        return ledger
    LedgerStore(run).mutate(historical)
    module_facts.initialize(run, batched=True, auto_budget=True, auto_input_cap=8000)
    author = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, author, "started")
    _record(tmp_path, run, author, "completed", _business_result(run, author))
    ledger = LedgerStore(run).open()
    task_id = next(tid for tid, task in ledger["tasks"].items() if task["kind"] == "fact_review")
    outer = next(sid for sid in ledger["tasks"][task_id]["input_ids"] if "::class::Outer::" in sid)
    from cbe import module_facts
    claim = module_facts.claim(run, task_id.removeprefix("task:fact_review:"), owner="controller/fact_review",
                              kind="review", review_ids=[outer])
    review = _offer_fresh_claim(run, claim)
    finding = {"symbol_id": outer, "reason": "The nested definition is missing from this view.",
               "needed_source": {"path": "ops.py", "start_line": 4, "end_line": 103}}
    _record(tmp_path, run, review, "started")
    _record(tmp_path, run, review, "completed", {"verdict": "needs_context", "checked_ids": [outer],
             "findings": [finding], "evidence_summary": "Outer declaration is visible; nested context is missing."})
    first = next_work(run, owner="controller")["items"][0]
    before = LedgerStore(run).open()
    packet = json.loads(Path(before["calls"][first["call_id"]]["extra"]["packet_path"]).read_text())
    window = next(w for w in packet["requested_context"] if "requested_start_line" in w)
    assert window["end_line"] < 103
    assert first["prompt_tokens"] <= 8000
    assert "review_only_current_presented_source" in Path(first["dispatch_prompt_path"]).read_text()
    assert finding in before["tasks"][first["task_id"]]["residual"]
    _record(tmp_path, run, first, "started")
    _record(tmp_path, run, first, "completed", {"verdict": "needs_context", "checked_ids": [outer],
             "findings": [finding], "evidence_summary": "Need the remaining requested source; not claiming full coverage."})
    for _ in range(8):
        second = next_work(run, owner="controller")["items"][0]
        after = LedgerStore(run).open()
        current = json.loads(Path(after["calls"][second["call_id"]]["extra"]["packet_path"]).read_text())
        subsequent = next((w for w in current.get("requested_context") or [] if "requested_start_line" in w), None)
        if subsequent is not None:
            break
        _record(tmp_path, run, second, "started")
        _record(tmp_path, run, second, "completed", _business_result(run, second))
    else:
        raise AssertionError("full review/fair scheduling lost the requested context obligation")
    assert subsequent["start_line"] > window["end_line"]
    assert after["details"] == before["details"]


def test_repaired_audit_id_remains_required_and_has_real_source(tmp_path, monkeypatch):
    from cbe import module_facts
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ops.py").write_text("def f(x):\n    return x + 1\n\ndef g(x):\n    return x - 1\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True)
    monkeypatch.setattr(module_facts, "_tiered_review_ids", lambda ledger, packets, ids: ids[:1])
    seed = LedgerStore(run).open()
    bid = next(bid for bid, batch in seed["fact_batches"].items() if len(batch["input_ids"]) > 1)
    claim = module_facts.claim(run, bid, owner="controller/fact_author", kind="author")
    author = _offer_fresh_claim(run, claim)
    _record(tmp_path, run, author, "started")
    _record(tmp_path, run, author, "completed", _business_result(run, author))
    claim = module_facts.claim(run, bid, owner="controller/fact_review", kind="review")
    review = _offer_fresh_claim(run, claim)
    ledger = LedgerStore(run).open()
    packet = json.loads(Path(ledger["calls"][review["call_id"]]["extra"]["packet_path"]).read_text())
    sampled = packet["assigned_ids"][0]
    target = next(sid for sid in ledger["tasks"][review["task_id"]]["input_ids"] if sid != sampled)
    _record(tmp_path, run, review, "started")
    _record(tmp_path, run, review, "completed", {"verdict": "accepted", "checked_ids": [sampled],
             "findings": [], "evidence_summary": "Checked the sampled function."})
    saved = LedgerStore(run).open()["details"][sampled]
    bid = review["task_id"].removeprefix("task:fact_review:")
    claim = module_facts.claim(run, bid, owner="controller/fact_review", kind="review", review_ids=[target])
    audit = _offer_fresh_claim(run, claim)
    _record(tmp_path, run, audit, "started")
    _record(tmp_path, run, audit, "completed", {"verdict": "revision_required", "checked_ids": [target],
             "findings": [{"symbol_id": target, "reason": "Correct the function behavior."}],
             "evidence_summary": "The explicitly audited function requires repair."})
    claim = module_facts.claim(run, bid, owner="controller/fact_author", kind="author")
    repair = _offer_fresh_claim(run, claim)
    _record(tmp_path, run, repair, "started")
    _record(tmp_path, run, repair, "completed", _business_result(run, repair))
    claim = module_facts.claim(run, bid, owner="controller/fact_review", kind="review")
    subsequent = _offer_fresh_claim(run, claim)
    after = LedgerStore(run).open()
    current = json.loads(Path(after["calls"][subsequent["call_id"]]["extra"]["packet_path"]).read_text())
    assert current["assigned_ids"] == [target]
    assert current["assignments"][0]["symbol_id"] == target
    assert "def g" in current["source"] or "def f" in current["source"]
    assert after["details"][sampled] == saved
    assert target in after["tasks"][subsequent["task_id"]]["extra"]["required_review_ids"]
    _record(tmp_path, run, subsequent, "started")
    _record(tmp_path, run, subsequent, "completed", {"verdict": "accepted", "checked_ids": [target],
             "findings": [], "evidence_summary": "The repaired function matches its presented source."})
    assert LedgerStore(run).open()["tasks"][subsequent["task_id"]]["state"] == "committed"
    # A redundant queue entry with all current checks satisfied needs no model.
    def redundant(ledger):
        ledger["tasks"][subsequent["task_id"]]["state"] = "pending"
        return ledger
    LedgerStore(run).mutate(redundant)
    before_calls = LedgerStore(run).open()["calls"]
    next_work(run, owner="controller")
    final = LedgerStore(run).open()
    assert final["tasks"][subsequent["task_id"]]["state"] == "committed"
    assert {cid for cid, call in final["calls"].items() if call["task_id"] == subsequent["task_id"]} == {
        cid for cid, call in before_calls.items() if call["task_id"] == subsequent["task_id"]}


def test_legacy_empty_review_packet_requires_actual_bound_empty_evidence(tmp_path):
    import hashlib
    from cbe.native_handoff import _empty_review_packet
    path = tmp_path / "packet.json"
    raw = json.dumps({"assigned_ids": [], "assignments": [], "source": ""}).encode()
    path.write_bytes(raw)
    call = {"packet_hash": hashlib.sha256(raw).hexdigest(),
            "extra": {"assigned_ids": [], "packet_path": str(path)}}
    assert _empty_review_packet(call)
    path.write_text(json.dumps({"assigned_ids": ["object"], "assignments": [], "source": "evidence"}))
    with pytest.raises(StaleWriteError, match="packet hash"):
        _empty_review_packet(call)
    call["packet_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert not _empty_review_packet(call)


def test_full_fact_feedback_rebuilds_current_module_system_render_and_query(tmp_path):
    from cbe import module_facts, module_workflow, system_workflow
    from cbe.runner import query
    run = _run(tmp_path)
    def finish(revision=False):
        roles = []
        for _ in range(20):
            result = next_work(run, owner="controller")
            if result["status"] == "complete":
                return result, roles
            assert result["status"] == "ready", result
            item = result["items"][0]
            roles.append(item["role"])
            _record(tmp_path, run, item, "started")
            payload = _business_result(run, item)
            if revision and item["role"] == "module_author":
                payload["content"]["summary"] = "Mechanism fixture: module rebuilt from revised facts."
            _record(tmp_path, run, item, "completed", payload)
        raise AssertionError("feedback did not complete")
    finish()
    before = LedgerStore(run).open()
    sid = next(sid for sid, symbol in before["inventory"]["symbols"].items() if symbol["kind"] == "function")
    review_id = next(tid for tid, task in before["tasks"].items()
                     if task["kind"] == "fact_review" and sid in task["input_ids"])
    bid = review_id.removeprefix("task:fact_review:")
    claim = module_facts.claim(run, bid, owner="controller/fact_review", kind="review", review_ids=[sid])
    audit = _offer_fresh_claim(run, claim)
    _record(tmp_path, run, audit, "started")
    _record(tmp_path, run, audit, "completed", {"verdict": "revision_required", "checked_ids": [sid],
             "findings": [{"symbol_id": sid, "reason": "Clarify the input/return contract."}],
             "evidence_summary": "The claimed function contract requires a targeted correction."})
    repair = next_work(run, owner="controller")["items"][0]
    _record(tmp_path, run, repair, "started")
    payload = _business_result(run, repair)
    payload["items"][0]["behavior"] = "Returns twice the passed value. Mechanism repair fixture."
    _record(tmp_path, run, repair, "completed", payload)
    assert module_workflow.accepted_package(LedgerStore(run).open())["modules"] == {}
    assert system_workflow.accepted_system(LedgerStore(run).open()) is None
    complete, roles = finish(revision=True)
    assert {"fact_review", "module_author", "module_review", "system_author", "system_review"} <= set(roles)
    after = LedgerStore(run).open()
    assert all(after["calls"][cid] == call for cid, call in before["calls"].items())
    gid = next(iter(module_workflow.accepted_package(after)["modules"]))
    assert after["module_records"][gid]["history"]
    assert after["system_record"]["history"]
    assert query(run, gid)["record"]["summary"].startswith("Mechanism fixture")
    assert Path(complete["reader_index"]).is_file()
    manifest = json.loads((Path(complete["reader_index"]).parent / "manifest.json").read_text())
    assert manifest["accepted_group_explanation_count"] > 0
    calls = len(after["calls"])
    module_workflow.initialize(run)
    system_workflow.initialize(run)
    assert next_work(run, owner="controller")["status"] == "complete"
    assert len(LedgerStore(run).open()["calls"]) == calls


def test_published_navigation_commands_execute_from_custom_output(tmp_path):
    import shlex
    from string import Template
    import subprocess
    import sys
    from cbe.render import render
    run = _run(tmp_path)
    for _ in range(20):
        result = next_work(run, owner="controller")
        if result["status"] == "complete":
            break
        item = result["items"][0]
        _record(tmp_path, run, item, "started")
        _record(tmp_path, run, item, "completed", _business_result(run, item))
    else:
        raise AssertionError("fixture did not complete")
    output = tmp_path / "custom reader output"
    render(run, output)
    index = (output / "INDEX.md").read_text()
    assert str(tmp_path) not in index
    block = index.split("```sh\n", 1)[1].split("```", 1)[0]
    variables = {"CBE_RUN_DIR": str(run), "CBE_PLAN_PATH": str(run / "module_plan.json")}
    responses = []
    for line in block.splitlines():
        if line.startswith(("RUN=", "PLAN=", "GROUP=", "ID=")):
            key, value = line.split("=", 1)
            variables[key] = Template(shlex.split(value)[0]).substitute(variables)
            if key in {"RUN", "PLAN"}:
                assert Path(variables[key]).exists()
            continue
        argv = shlex.split(line)
        argv = [variables.get(arg.removeprefix("$"), arg) for arg in argv]
        command = [sys.executable, "-m", "cbe", *argv[1:]]
        completed = subprocess.run(command, cwd=tmp_path / "repo", capture_output=True, text=True)
        assert completed.returncode == 0, (command, completed.stderr)
        responses.append(json.loads(completed.stdout))
    members, module, symbol, target = responses
    assert symbol["id"] if "id" in symbol else symbol["symbol_id"]
    assert module["type"] == "module_explanation"
    assert target["id"] in {item["symbol_id"] for item in members["items"]}
    page = Path(target["absolute_path"].split("#", 1)[0])
    assert page.is_relative_to(output) and page.is_file()


@pytest.mark.parametrize("role", ["module_author", "system_author"])
def test_later_stage_disk_failure_is_known_unsent_and_recovers(tmp_path: Path, monkeypatch, role: str) -> None:
    from cbe import module_facts
    run = _run(tmp_path)
    while True:
        ledger = LedgerStore(run).open()
        # Once the preceding stage is accepted, the next call creates the
        # selected later-stage author. Use the existing completion loop.
        ready_scope = (all(module_facts.accepted_fact(ledger, sid)
                           for sid in ledger["inventory"]["symbols"])
                       if role == "module_author" else
                       bool(ledger.get("module_records")) and all(
                           row.get("state") == "accepted" for row in ledger["module_records"].values()))
        if ready_scope:
            break
        item = next_work(run, owner="controller")["items"][0]
        record(run, item["call_id"], status="started", host="test", child_handle=item["call_id"])
        result = tmp_path / "business.json"
        result.write_text(json.dumps(_business_result(run, item)))
        record(run, item["call_id"], status="completed", host="test", result_path=result)
    writer = module_facts.atomic_write_bytes
    def fail_write(path, raw):
        raise OSError("later-stage disk fault")
    monkeypatch.setattr(module_facts, "atomic_write_bytes", fail_write)
    with pytest.raises(OSError, match="disk fault"):
        next_work(run, owner="controller")
    ledger = LedgerStore(run).open()
    failed = [call for call in ledger["calls"].values() if call["task_id"].startswith(f"task:{role}")][-1]
    assert failed["state"] == "released"
    assert failed["extra"]["send_evidence"] == "not_sent_bootstrap"
    monkeypatch.setattr(module_facts, "atomic_write_bytes", writer)
    repaired = next_work(run, owner="controller")
    assert repaired["status"] == "ready"
    assert repaired["items"][0]["role"] == role


def test_rejected_raw_residual_cannot_readd_same_hash_checked_fact_to_layout_retry(tmp_path: Path) -> None:
    """Construct the real failure's scope lifecycle without a model verdict."""
    from cbe import module_facts
    repo = tmp_path / "scope-repo"
    repo.mkdir()
    (repo / "ops.py").write_text("def f(x):\n return x + 1\n\ndef g(x):\n return x - 1\n")
    run = tmp_path / "scope-run"
    analyze(repo, run, documentation_profile="module-first-v2")
    module_facts.initialize(run, batched=True)
    ledger = LedgerStore(run).open()
    bid = next(bid for bid, batch in ledger["fact_batches"].items() if len(batch["input_ids"]) == 2)
    author = _offer_fresh_claim(run, module_facts.claim(run, bid, owner="synthetic/author"))
    _record(tmp_path, run, author, "started")
    _record(tmp_path, run, author, "completed", _business_result(run, author))
    def require_both(current):
        task = current["tasks"]["task:fact_review:" + bid]
        task["extra"]["required_review_ids"] = list(task["input_ids"])
        return current
    LedgerStore(run).mutate(require_both)
    review = _offer_fresh_claim(run, module_facts.claim(run, bid, owner="synthetic/reviewer", kind="review"))
    ids = LedgerStore(run).open()["tasks"][review["task_id"]]["input_ids"]
    checked, pending = ids
    _record(tmp_path, run, review, "started")
    _record(tmp_path, run, review, "completed", {"verdict": "accepted", "checked_ids": [checked],
        "findings": [], "evidence_summary": "Constructed partial source-check fixture."})
    review = _offer_fresh_claim(run, module_facts.claim(run, bid, owner="synthetic/reviewer2",
        kind="review", review_ids=[pending]))
    _record(tmp_path, run, review, "started")
    invalid = run / "raw" / f"{review['call_id']}.json"
    invalid.write_text('{"invalid_fixture":true}')
    module_facts.reject_result(run, review["task_id"], invalid, reason="synthetic bad shape", repair_ids=ids)
    def lower_cap(current):
        current["fact_batches"][bid]["max_input_tokens"] = 1
        return current
    LedgerStore(run).mutate(lower_cap)
    before = LedgerStore(run).open()
    assert module_facts.accepted_fact(before, checked)
    assert any(item.get("symbol_id") == checked for item in before["tasks"][review["task_id"]]["residual"])
    with pytest.raises(module_facts.PromptLayoutError) as default:
        module_facts.claim(run, bid, owner="synthetic/retry", kind="review")
    # The current one-ID view can hit the separately protected nonprogress
    # guard first. Both diagnostics must describe only the still-owned pending
    # scope; the old code instead reaches the whole-prompt guard with two IDs.
    assert default.value.diagnostic["assigned_ids"] == [pending]
    with pytest.raises(module_facts.PromptLayoutError):
        module_facts.claim(run, bid, owner="synthetic/retry", kind="review",
            review_ids=default.value.diagnostic["assigned_ids"])
    with pytest.raises(ValueError, match="nonempty subset"):
        module_facts.claim(run, bid, owner="synthetic/wrong", kind="review", review_ids=[checked])
    assert LedgerStore(run).open() == before
