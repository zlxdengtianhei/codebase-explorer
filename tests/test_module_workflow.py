from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from cbe.module_explanations import explanation_content_sha256
from cbe.module_facts import mark_delivered
from cbe.module_facts import _sha_json
from cbe.module_workflow import claim, import_result, initialize, release
from cbe.render import render
from cbe.runner import analyze
from cbe.store import LedgerStore, LeaseError, StaleWriteError


def _run(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    filler = "DATA = {\n" + "".join(f"    'item_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "service.py").write_text(filler + "\ndef dispatch(value):\n    return value + 1\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    plan = json.loads((run / "module_plan.json").read_text())
    gid = next(gid for gid, g in plan["groups"].items() if g.get("member_ids"))
    sid = plan["groups"][gid]["member_ids"][0]
    return run, gid, sid


def _delivery(run: Path, claimed: dict) -> None:
    session = "session-" + claimed["call_id"]
    native = run.parent / (claimed["call_id"].replace(":", "-") + ".jsonl")
    native.write_text("\n".join(json.dumps(event) for event in [
        {"type": "session_meta", "payload": {"id": session}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": Path(claimed["prompt_path"]).read_text()}]}},
        {"type": "turn_context", "payload": {"model": "gpt-6-sol"}},
    ]) + "\n")
    receipt = run.parent / (claimed["call_id"].replace(":", "-") + ".json")
    receipt.write_text(json.dumps({
        "status": "completed", "task_id": claimed["call_id"],
        "prompt_sha256": claimed["prompt_sha256"], "requested_model": "gpt-6-sol",
        "attempts": [{"status": "success", "response_id": session,
                      "native_evidence_path": str(native), "observed_model": "gpt-6-sol",
                      "usage": {"input_tokens": 100, "output_tokens": 10}}],
    }))
    mark_delivered(run, claimed["task_id"], receipt)


def test_module_claim_review_render_and_replay(tmp_path: Path) -> None:
    run, gid, sid = _run(tmp_path)
    assert initialize(run)["accepted"] == 0
    author = claim(run, gid, kind="module_author", owner="sol-author")
    assert Path(author["packet_path"]).exists()
    assert hashlib.sha256(Path(author["packet_path"]).read_bytes()).hexdigest() == author["packet_sha256"]
    assert hashlib.sha256(Path(author["prompt_path"]).read_bytes()).hexdigest() == author["prompt_sha256"]
    assert author["packet_sha256"] != author["prompt_sha256"]
    assert author["packet_path"] != author["result_path"]
    with pytest.raises(LeaseError):
        claim(run, gid, kind="module_author", owner="other-author")
    content = {"summary": "Dispatch returns a transformed value.",
               "flow": "The function adds one to its input and returns the result.",
               "uncertainties": "Only the local return path is shown.",
               "key_symbols": [sid], "source_refs": [{"path": "service.py", "line": 604}]}
    path = Path(author["result_path"])
    path.parent.mkdir()
    path.write_text(json.dumps({"envelope": author["envelope"], "content": content}))
    with pytest.raises(ValueError, match="delivery"):
        import_result(run, author["task_id"], path)
    _delivery(run, author)
    imported = import_result(run, author["task_id"], path)
    assert imported["state"] == "committed"
    assert import_result(run, author["task_id"], path)["idempotent"] is True
    review = claim(run, gid, kind="module_review", owner="sol-reviewer")
    evidence = tmp_path / "review.txt"
    evidence.write_text("I read source service.py and confirmed the return path.\n")
    reviewer_path = Path(review["result_path"])
    reviewer_path.write_text(json.dumps({"envelope": review["envelope"],
        "verdict": "accepted",
        "content_sha256": explanation_content_sha256({"author_id": "sol-author", **content}),
        "findings": [], "evidence_ref": str(evidence)}))
    _delivery(run, review)
    assert import_result(run, review["task_id"], reviewer_path)["accepted"] is True
    assert render(run)["accepted_group_explanation_count"] == 1
    ledger = LedgerStore(run).open()
    assert ledger["module_records"][gid]["state"] == "accepted"
    assert ledger["module_records"][gid]["usage"] == {"input_tokens": 100, "output_tokens": 10}
    assert ledger["budget"]["source_exposure_chars"] > 0


def test_module_release_rejects_late_result(tmp_path: Path) -> None:
    run, gid, sid = _run(tmp_path)
    first = claim(run, gid, kind="module_author", owner="first", max_source_tokens=1000)
    with pytest.raises(LeaseError, match="unresolved"):
        release(run, first["task_id"], owner="first")
    from cbe.native_handoff import reconcile_existing_call
    LedgerStore(run).mutate(lambda ledger: (reconcile_existing_call(ledger, first["call_id"],
        searched=["fixture: inspected local claim; no host/provider execution occurred"]) or ledger))
    assert LedgerStore(run).open()["calls"][first["call_id"]]["state"] == "released"
    second = claim(run, gid, kind="module_author", owner="second", max_source_tokens=1000)
    assert second["envelope"]["generation"] > first["envelope"]["generation"]
    stale = Path(first["result_path"])
    stale.parent.mkdir()
    stale.write_text(json.dumps({"envelope": first["envelope"], "author_id": "first", "content": {
        "summary": "x", "flow": "y", "uncertainties": "", "key_symbols": [sid],
        "source_refs": [{"path": "service.py", "line": 604}]}}))
    with pytest.raises(StaleWriteError):
        import_result(run, first["task_id"], stale)


def test_fact_mode_module_author_and_reviewer_receive_no_source(tmp_path: Path) -> None:
    run, gid, _ = _run(tmp_path)
    plan = json.loads((run / "module_plan.json").read_text())
    group = plan["groups"][gid]
    ledger = LedgerStore(run).open()
    function_ids = [sid for sid in group["member_ids"]
                    if ledger["inventory"]["symbols"][sid]["kind"] in {"function", "method", "lambda"}]
    assert function_ids

    def seed(current: dict) -> dict:
        current["fact_workflow_version"] = 1
        for sid in function_ids:
            detail = {"symbol_id": sid, "behavior": "Adds one and returns the value.",
                      "provenance": {"source_refs": [{"path": "service.py", "line": 604}]}}
            current.setdefault("details", {})[sid] = detail
            current.setdefault("fact_reviews", {})[sid] = {
                "state": "source_checked", "content_sha256": _sha_json(detail)}
        return current

    LedgerStore(run).mutate(seed)
    initialize(run)
    author = claim(run, gid, kind="module_author", owner="fact-author")
    author_packet = json.loads(Path(author["packet_path"]).read_text())
    assert author_packet["metadata"]["selected_sources"] == []
    assert LedgerStore(run).open()["calls"][author["call_id"]]["source_chars"] == 0
    assert "Adds one and returns" in Path(author["prompt_path"]).read_text()
    content = {"summary": "Dispatch transforms a value.",
               "flow": "Adds one and returns it.", "uncertainties": "",
               "key_symbols": [function_ids[0]],
               "source_refs": [{"path": "service.py", "line": 604}]}
    result = Path(author["result_path"])
    result.parent.mkdir(exist_ok=True)
    result.write_text(json.dumps({"envelope": author["envelope"], "content": content}))
    _delivery(run, author)
    import_result(run, author["task_id"], result)
    review = claim(run, gid, kind="module_review", owner="fact-reviewer")
    review_packet = json.loads(Path(review["packet_path"]).read_text())
    assert review_packet["metadata"]["selected_sources"] == []
    assert LedgerStore(run).open()["calls"][review["call_id"]]["source_chars"] == 0
    assert "unsupported" in Path(review["prompt_path"]).read_text()
    assert "DATA = {" not in Path(review["prompt_path"]).read_text()


def test_delivered_module_result_recovers_only_its_hash_echo(tmp_path: Path) -> None:
    run, gid, sid = _run(tmp_path)
    initialize(run)
    author = claim(run, gid, kind="module_author", owner="module-author")
    envelope = dict(author["envelope"])
    envelope["input_hash"] = envelope["input_hash"][:-1]
    result = Path(author["result_path"])
    result.parent.mkdir(exist_ok=True)
    result.write_text(json.dumps({"envelope": envelope, "content": {
        "summary": "Dispatch transforms a value.",
        "flow": "Adds one and returns the result.", "uncertainties": "",
        "key_symbols": [sid], "source_refs": [{"path": "service.py", "line": 604}],
    }}))
    _delivery(run, author)
    assert import_result(run, author["task_id"], result)["state"] == "committed"
    call = LedgerStore(run).open()["calls"][author["call_id"]]
    assert call["extra"]["envelope_origin"] == "controller_from_delivered_call"
    assert json.loads(result.read_text())["envelope"]["input_hash"] == envelope["input_hash"]


@pytest.mark.parametrize("active_state", ["leased", "prepared", "sent", "uncertain"])
def test_dependency_rebuild_refuses_unsettled_epoch_without_mutation(tmp_path: Path, active_state: str) -> None:
    from cbe.module_workflow import reopen_dependency_tasks
    from cbe.models import TaskRecord
    run, gid, _ = _run(tmp_path)
    initialize(run)
    ledger = LedgerStore(run).open()
    tasks = [TaskRecord.from_dict(row) for row in ledger["tasks"].values()
             if row["kind"] in {"module_author", "module_review"} and gid in row["input_ids"]]
    author = next(task for task in tasks if task.kind == "module_author")
    review = next(task for task in tasks if task.kind == "module_review")
    if active_state == "leased":
        author.state = "leased"
    else:
        ledger["calls"]["old-call"] = {"task_id": author.task_id, "state": active_state}
    before = json.dumps(ledger, sort_keys=True)
    with pytest.raises(StaleWriteError, match="active or uncertain"):
        reopen_dependency_tasks(ledger, author, review, "new-input", "fixture dependency changed")
    assert json.dumps(ledger, sort_keys=True) == before
