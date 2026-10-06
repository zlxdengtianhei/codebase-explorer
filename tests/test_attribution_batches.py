"""Attribution batches give non-executable objects reviewed load-bearing
semantics or explicit attribution through the same fact machinery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cbe.ir import line_starts
from cbe.module_facts import (
    ATTRIBUTION_CONTRACT, claim, import_result, initialize, mark_delivered,
    register_attribution_batches,
)
from cbe.runner import analyze, query
from cbe.store import LedgerStore


def _run(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "tests").mkdir()
    filler = "EXAMPLES = {\n" + "".join(f"    'name_{i}': {i},\n" for i in range(600)) + "}\n"
    (repo / "pkg" / "service.py").write_text(
        filler
        + "REGISTRY = {}\n"
        + "\ndef register(name, fn):\n    REGISTRY[name] = fn\n"
        + "\nclass Handler:\n"
        + "    \"\"\"Container dispatching through dispatch().\"\"\"\n"
        + "    retries = 3\n\n"
        + "    def use(self, value):\n        return dispatch(value)\n"
        + "\ndef dispatch(value):\n"
        "    try:\n        return value + 1\n    except TypeError:\n        return None\n"
    )
    (repo / "tests" / "test_service.py").write_text(
        "class TestDispatch:\n"
        "    def test_dispatch(self):\n"
        "        from pkg.service import dispatch\n"
        "        assert dispatch(1) == 2\n"
        "        assert dispatch(None) is None\n"
    )
    run = tmp_path / "run"
    analyze(repo, run, documentation_profile="module-first-v2")
    return run


def _non_exec(run: Path) -> list[str]:
    ledger = LedgerStore(run).open()
    return sorted(sid for sid, symbol in ledger["inventory"]["symbols"].items()
                  if symbol["kind"] not in {"function", "method", "lambda"})


def _line_of(run: Path, sid: str) -> int:
    """A citable line inside the object's exclusive span (what the claim presents)."""
    ledger = LedgerStore(run).open()
    symbol = ledger["inventory"]["symbols"][sid]
    text = (Path(ledger["repo_root"]) / symbol["path"]).read_text()
    starts = line_starts(text)
    span = (symbol.get("exclusive_spans") or [symbol["span"]])[0]
    return max(index + 1 for index, pos in enumerate(starts) if pos <= span["start"])


def _delivery(run: Path, claim_value: dict) -> None:
    session_id = f"session-{claim_value['call_id']}"
    native = run.parent / f"{claim_value['call_id'].replace(':', '-')}-native.jsonl"
    native.write_text("\n".join(json.dumps(event) for event in [
        {"type": "session_meta", "payload": {"id": session_id}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": Path(
                claim_value["prompt_path"]).read_text()}]}},
        {"type": "turn_context", "payload": {"model": "gpt-6-sol"}},
    ]) + "\n")
    evidence = run.parent / f"{claim_value['call_id'].replace(':', '-')}-provider.json"
    evidence.write_text(json.dumps({
        "status": "completed", "task_id": claim_value["call_id"],
        "prompt_sha256": claim_value["prompt_sha256"],
        "requested_model": "gpt-6-sol",
        "attempts": [{"status": "success", "response_id": session_id,
                      "native_evidence_path": str(native), "observed_model": "gpt-6-sol",
                      "usage": {"input_tokens": 90, "output_tokens": 9}}],
    }))
    mark_delivered(run, claim_value["task_id"], evidence)


def test_registration_covers_every_non_executable_object_once(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    ledger_before = LedgerStore(run).open()
    fact_batches_before = set(ledger_before.get("fact_batches") or {})
    result = register_attribution_batches(run)
    assert result["object_count"] + result["syntax_evidenced_count"] == len(_non_exec(run)) > 0
    again = register_attribution_batches(run)
    assert again["already_registered"] is True
    ledger = LedgerStore(run).open()
    batches = ledger["attribution_batches"]
    assert all(batch_id.startswith("attr-batch:") for batch_id in batches)
    assigned = [sid for batch in batches.values() for sid in batch["input_ids"]]
    assert sorted(assigned + result["syntax_evidenced_ids"]) == _non_exec(run)
    assert all(ledger["fact_reviews"][sid]["state"] == "syntax_evidenced"
               for sid in result["syntax_evidenced_ids"])
    # Executable batch structure is untouched.
    assert fact_batches_before <= set(ledger["fact_batches"])
    for batch_id, batch in batches.items():
        assert ledger["tasks"][f"task:fact_author:{batch_id}"]["extra"]["attribution"] is True
        assert batch["source_chars"] > 0


def test_attribution_claim_import_and_review(tmp_path: Path) -> None:
    run = _run(tmp_path)
    initialize(run)
    register_attribution_batches(run)
    ledger = LedgerStore(run).open()
    batch_id = next(iter(ledger["attribution_batches"]))
    ids = ledger["attribution_batches"][batch_id]["input_ids"]

    author = claim(run, batch_id, owner="attribution-author")
    prompt = Path(author["prompt_path"]).read_text()
    assert ATTRIBUTION_CONTRACT.split("/")[0] not in prompt  # contract id is metadata, not prose
    assert "non-executable object" in prompt
    assert "explicit attribution" in prompt
    # The smaller default may split class and module residuals into separate
    # calls. This claim only carries the exclusive spans of its assigned IDs.
    packet = json.loads(Path(author["packet_path"]).read_text())
    assert packet["assigned_ids"] == ids
    assert packet["source"].strip()
    assert "def dispatch(value):" not in prompt
    _delivery(run, author)
    result_path = Path(author["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "envelope": author["envelope"], "author_id": "attribution-author",
        "items": [
            {"symbol_id": sid,
             "behavior": (
                 "Load-bearing: defines module-level state and registration used by "
                 f"member functions of {sid}."
                 if "module_residual" in sid else
                 "Container: behavior is carried by its member method facts; "
                 "class-level statements only declare defaults."
             ),
             "source_refs": [{"path": LedgerStore(run).open()["inventory"]["symbols"][sid]["path"],
                              "line": _line_of(run, sid)}]}
            for sid in ids
        ],
    }))
    imported = import_result(run, author["task_id"], result_path)
    assert imported["state"] == "committed"
    assert imported["accepted_items"] == len(ids)
    ledger = LedgerStore(run).open()
    for sid in ids:
        record = ledger["details"][sid]
        assert record["behavior"]
        assert all(span["path"] for span in record["source_spans"])

    reviewer = claim(run, batch_id, kind="review", owner="attribution-reviewer")
    assert reviewer["task_id"] == f"task:fact_review:{batch_id}"
    ledger = LedgerStore(run).open()
    review_task = ledger["tasks"][reviewer["task_id"]]
    assert review_task["input_ids"]
    draft = {sid: ledger["details"][sid] for sid in review_task["input_ids"]}
    checked = review_task["extra"]["assigned_ids"]
    content_hash = hashlib.sha256(json.dumps(
        draft, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    _delivery(run, reviewer)
    evidence = tmp_path / "attribution-review.txt"
    evidence.write_text("Independent check of each attribution against source.\n")
    review_path = Path(reviewer["result_path"])
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps({
        "envelope": reviewer["envelope"], "reviewer_id": "attribution-reviewer",
        "verdict": "accepted", "checked_ids": sorted(checked), "findings": [],
        "content_sha256": content_hash, "evidence_ref": str(evidence),
    }))
    reviewed = import_result(run, reviewer["task_id"], review_path)
    assert reviewed["state"] == "committed"
    assert reviewed["source_checked"] == len(checked)
    first_id = sorted(checked)[0]
    assert query(run, first_id)["explanation_state"] == "source_checked"
    from cbe.store import fragment_plan_residuals

    assert not any(
        item.get("task_id", "").startswith("task:fact_author:attr-batch:")
        for item in fragment_plan_residuals(LedgerStore(run).open())
    )


def test_attribution_review_claim_presents_exclusive_spans_and_contract(tmp_path: Path) -> None:
    """Review claims for attribution batches present exclusive spans and the
    attribution contract, not executable packet spans: without the marker the
    reviewer cannot see class bodies and flags sound drafts as unrepaired."""
    run = _run(tmp_path)
    initialize(run)
    register_attribution_batches(run)
    ledger = LedgerStore(run).open()
    batch_id = next(iter(ledger["attribution_batches"]))
    ids = ledger["attribution_batches"][batch_id]["input_ids"]

    author = claim(run, batch_id, owner="attribution-author")
    _delivery(run, author)
    result_path = Path(author["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "envelope": author["envelope"], "author_id": "attribution-author",
        "items": [
            {"symbol_id": sid,
             "behavior": ("Module-level state for member functions."
                         if "module_residual" in sid else
                         "Container: behavior lives in member method facts."),
             "source_refs": [{"path": LedgerStore(run).open()["inventory"]["symbols"][sid]["path"],
                               "line": _line_of(run, sid)}]}
            for sid in ids
        ],
    }))
    assert import_result(run, author["task_id"], result_path)["state"] == "committed"

    ledger = LedgerStore(run).open()
    assert ledger["tasks"][f"task:fact_review:{batch_id}"]["extra"].get("attribution") is True

    reviewer = claim(run, batch_id, kind="review", owner="attribution-reviewer")
    prompt = Path(reviewer["prompt_path"]).read_text()
    assert "non-executable object" in prompt          # attribution contract prose
    assert "assigned draft attribution" in prompt     # attribution review instruction
    assert "retries = 3" in prompt                    # class-level statement, exclusive span


def test_attribution_review_falls_back_to_batch_record_for_legacy_tasks(tmp_path: Path) -> None:
    """Review tasks created before the flag propagated still review under the
    attribution contract: the batch record is the authoritative source."""
    run = _run(tmp_path)
    initialize(run)
    register_attribution_batches(run)
    ledger = LedgerStore(run).open()
    batch_id = next(iter(ledger["attribution_batches"]))
    ids = ledger["attribution_batches"][batch_id]["input_ids"]

    author = claim(run, batch_id, owner="attribution-author")
    _delivery(run, author)
    result_path = Path(author["result_path"])
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "envelope": author["envelope"], "author_id": "attribution-author",
        "items": [
            {"symbol_id": sid,
             "behavior": ("Module-level state for member functions."
                         if "module_residual" in sid else
                         "Container: behavior lives in member method facts."),
             "source_refs": [{"path": LedgerStore(run).open()["inventory"]["symbols"][sid]["path"],
                               "line": _line_of(run, sid)}]}
            for sid in ids
        ],
    }))
    assert import_result(run, author["task_id"], result_path)["state"] == "committed"

    def strip_flag(led: dict) -> dict:
        led["tasks"][f"task:fact_review:{batch_id}"]["extra"].pop("attribution", None)
        return led
    LedgerStore(run).mutate(strip_flag)

    reviewer = claim(run, batch_id, kind="review", owner="legacy-reviewer")
    prompt = Path(reviewer["prompt_path"]).read_text()
    assert "non-executable object" in prompt
    assert "retries = 3" in prompt


def test_status_reports_attribution_progress(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from cbe.cli import main

    run = _run(tmp_path)
    initialize(run)
    register_attribution_batches(run)
    code = main(["status", "--run-dir", str(run), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    progress = payload["attribution_progress"]
    total = sum(progress.values())
    assert total == len(_non_exec(run))
    assert progress.get("catalogued", 0) + progress.get("syntax_evidenced", 0) == total
    assert progress.get("syntax_evidenced", 0) > 0


def test_module_author_requires_attribution_once_registered(tmp_path: Path) -> None:
    """After attribution-init, non-executable members gate module synthesis."""
    from cbe.module_workflow import _accepted_attributions

    run = _run(tmp_path)
    initialize(run)
    plan = json.loads((run / "module_plan.json").read_text(encoding="utf-8"))
    ledger = LedgerStore(run).open()
    gid = next(g for g, grp in plan["groups"].items()
               if grp.get("member_ids")
               and any(ledger["inventory"]["symbols"][s]["kind"] not in {"function", "method", "lambda"}
                       for s in grp["member_ids"]))
    group = plan["groups"][gid]
    # Before registration the gate is inert (legacy runs keep working).
    assert _accepted_attributions(ledger, gid, group) == {}
    register_attribution_batches(run)
    ledger = LedgerStore(run).open()
    with pytest.raises(ValueError, match="unattributed"):
        _accepted_attributions(ledger, gid, group)
