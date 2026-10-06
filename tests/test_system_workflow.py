"""System-level synthesis: author + independent review in the same ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.module_facts import _message_projection
from cbe.runner import analyze
from cbe.store import LedgerStore
from cbe.system_workflow import accepted_system, claim, import_result, initialize


def _run_with_accepted_module(tmp_path: Path) -> Path:
    """A tiny run with one accepted module explanation in the ledger."""
    repo = tmp_path / "repo"
    repo.mkdir()
    filler = "EXAMPLES = {\n" + "".join(f"    'name_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "service.py").write_text(
        filler + "\ndef dispatch(value):\n    return value + 1\n", encoding="utf-8")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    ledger = LedgerStore(run).open()
    plan = json.loads((run / "module_plan.json").read_text(encoding="utf-8"))
    gid = next(g for g, grp in plan["groups"].items() if grp.get("member_ids"))
    member = plan["groups"][gid]["member_ids"][0]
    line_counts = 3
    record = {
        "author_id": "module-author",
        "summary": "Dispatches values through one pure function.",
        "flow": "Callers invoke dispatch; it returns value + 1.",
        "uncertainties": "",
        "key_symbols": [member],
        "source_refs": [{"path": "service.py", "line": 603}],
        "review": {
            "reviewer_id": "module-reviewer", "decision": "accepted",
            "content_sha256": "0" * 64,
            "source_revision": ledger["source_revision"],
            "evidence_ref": str(tmp_path / "module-evidence.txt"),
        },
    }
    from cbe.module_explanations import explanation_content_sha256
    record["review"]["content_sha256"] = explanation_content_sha256(record)
    (tmp_path / "module-evidence.txt").write_text("module review evidence\n")

    def mutate(inner: dict) -> dict:
        inner.setdefault("module_records", {})[gid] = {
            "state": "accepted", "record": record,
            "author_session_id": "session-author", "reviewer_session_id": "session-reviewer",
        }
        return inner

    LedgerStore(run).mutate(mutate)
    return run


def _system_delivery(run: Path, claim_value: dict) -> None:
    from cbe.module_facts import mark_delivered
    receipt = {
        "status": "completed", "task_id": claim_value["call_id"],
        "prompt_sha256": claim_value["prompt_sha256"],
        "requested_model": "glm-5.3",
        "attempts": [{"status": "success", "observed_model": "glm-5.3",
                      "response_id": f"resp-{claim_value['call_id'][-8:]}",
                      "usage": {"input_tokens": 100, "output_tokens": 20}}],
    }
    path = run.parent / f"{claim_value['call_id'].replace(':', '-')}-receipt.json"
    path.write_text(json.dumps(receipt))
    mark_delivered(run, claim_value["task_id"], path)


def test_system_author_review_and_acceptance(tmp_path: Path) -> None:
    run = _run_with_accepted_module(tmp_path)
    result = initialize(run)
    assert result["author_state"] == "pending"
    # Idempotent registration keeps task states.
    assert initialize(run)["author_state"] == "pending"

    author = claim(run, kind="system_author", owner="sys-author")
    prompt = Path(author["prompt_path"]).read_bytes()
    packet = json.loads(Path(author["packet_path"]).read_text())
    assert prompt == _message_projection(packet)
    assert "accepted module explanations" in packet["instruction"]
    _system_delivery(run, author)
    result_path = Path(author["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "envelope": author["envelope"],
        "overview": "A single-function dispatch service.",
        "entry_points": "dispatch() is the only entry point.",
        "lifecycle": " Stateless call; no lifecycle.",
        "data_flow": "Caller value in, incremented value out.",
        "uncertainties": "None beyond the module's own scope.",
    }))
    imported = import_result(run, "task:system_author", result_path)
    assert imported["system"] == "draft"

    reviewer = claim(run, kind="system_review", owner="sys-reviewer")
    _system_delivery(run, reviewer)
    evidence = tmp_path / "system-evidence.txt"
    evidence.write_text("system review evidence\n")
    draft = LedgerStore(run).open()["system_record"]["record"]
    from cbe.system_workflow import _content_hash
    review_path = Path(reviewer["result_path"])
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps({
        "envelope": reviewer["envelope"], "reviewer_id": "sys-reviewer",
        "verdict": "accepted", "findings": [],
        "content_sha256": _content_hash(draft), "evidence_ref": str(evidence),
    }))
    reviewed = import_result(run, "task:system_review", review_path)
    assert reviewed["system"] == "accepted"
    assert accepted_system(LedgerStore(run).open()) is not None


def test_system_review_must_be_distinct_session(tmp_path: Path) -> None:
    run = _run_with_accepted_module(tmp_path)
    initialize(run)
    author = claim(run, kind="system_author", owner="sys-author")
    _system_delivery(run, author)
    result_path = Path(author["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "envelope": author["envelope"],
        "overview": "o", "entry_points": "e", "lifecycle": "l",
        "data_flow": "d", "uncertainties": "u",
    }))
    import_result(run, "task:system_author", result_path)
    reviewer = claim(run, kind="system_review", owner="sys-reviewer")
    _system_delivery(run, reviewer)
    draft = LedgerStore(run).open()["system_record"]["record"]
    from cbe.system_workflow import _content_hash
    # Force the reviewer session to equal the author session.
    def mutate(inner: dict) -> dict:
        inner["calls"][reviewer["call_id"]]["role_session_id"] = (
            inner["system_record"]["author_session_id"])
        return inner
    LedgerStore(run).mutate(mutate)
    evidence = tmp_path / "system-evidence-2.txt"
    evidence.write_text("x\n")
    review_path = Path(reviewer["result_path"])
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps({
        "envelope": reviewer["envelope"], "verdict": "accepted", "findings": [],
        "content_sha256": _content_hash(draft), "evidence_ref": str(evidence),
    }))
    with pytest.raises(ValueError, match="distinct native session"):
        import_result(run, "task:system_review", review_path)


def test_initialize_requires_modules(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    filler = "EXAMPLES = {\n" + "".join(f"    'n_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "service.py").write_text(filler + "\ndef dispatch(value):\n    return value + 1\n")
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    with pytest.raises(ValueError, match="requires every implementation module"):
        initialize(run)
    forced = initialize(run, require_modules=False)
    assert forced["author_state"] == "pending"
