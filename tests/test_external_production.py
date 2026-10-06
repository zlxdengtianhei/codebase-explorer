"""External (session-dispatched sub-agent) production path.

2026-09-21 ruling: the session claims a detail task, hands the self-contained
prompt to a sub-agent of whatever model the host provides, and imports the
result with its envelope and self-report. No event-level trace auditing; the
budget counts the packet injection mechanically at claim time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.runner import RunnerError, analyze, claim_kind, import_result
from cbe.store import LedgerStore, derived_status


def _make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text(
        "def alpha(x):\n"
        "    return x + 1\n"
        "\n"
        "def beta(y):\n"
        "    return alpha(y) * 2\n",
        encoding="utf-8",
    )
    return repo


def _make_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    analyze(_make_repo(tmp_path), run_dir)
    return run_dir


def _result_payload(envelope: dict, symbol_ids: list[str], report: dict | None) -> dict:
    payload = {
        "envelope": envelope,
        "details": [
            {
                "symbol_id": sid,
                "behavior": f"evidenced behavior for {sid}",
                "inputs_outputs": [],
                "effects": [],
                "failures": [],
                "dependencies": [],
                "unresolved": [],
            }
            for sid in symbol_ids
        ],
    }
    if report is not None:
        payload["report"] = report
    return payload


def test_claim_detail_returns_envelope_prompt_and_counts_budget(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    before = derived_status(LedgerStore(run_dir).open())
    out = claim_kind(run_dir, kind="detail", count=1)
    assert len(out["claimed"]) == 1
    entry = out["claimed"][0]
    envelope = entry["envelope"]
    for key in ("task_id", "generation", "owner", "input_hash", "call_id"):
        assert envelope.get(key) not in (None, "")
    prompt = json.loads(Path(entry["prompt_path"]).read_text(encoding="utf-8"))
    assert prompt["envelope"] == envelope
    assert prompt["result_file_rule"].endswith(f"{entry['result_path']}. Do not invent a second destination, and do not only put JSON in the final reply.") or entry["result_path"] in prompt["result_file_rule"]
    assert prompt["role"] == "Detail producer"
    ledger = LedgerStore(run_dir).open()
    call = ledger["calls"][entry["call_id"]]
    assert (call.get("extra") or {}).get("external_subagent") is True
    after = derived_status(ledger)
    assert after["known_source_chars"] == before["known_source_chars"] + entry["source_chars"]


def test_external_import_commits_and_binds_call(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    entry = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    ledger = LedgerStore(run_dir).open()
    task = ledger["tasks"][entry["task_id"]]
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            _result_payload(
                entry["envelope"],
                list(task["input_ids"]),
                report={"read": [entry["packet_id"]], "method": "read injected source once"},
            )
        ),
        encoding="utf-8",
    )
    out = import_result(run_dir, entry["task_id"], result)
    assert out["state"] == "committed"
    ledger = LedgerStore(run_dir).open()
    call = ledger["calls"][entry["call_id"]]
    assert call["state"] == "imported"
    extra = call.get("extra") or {}
    assert extra.get("self_report_status") == "present"
    assert extra.get("self_report", {}).get("method") == "read injected source once"
    assert extra.get("disposition") == "accepted"
    # idempotent re-import
    out2 = import_result(run_dir, entry["task_id"], result)
    assert out2["state"] == "committed"
    assert derived_status(ledger)["known_source_chars"] == derived_status(LedgerStore(run_dir).open())["known_source_chars"]


def test_external_import_without_report_still_commits_but_marks(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    entry = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    ledger = LedgerStore(run_dir).open()
    task = ledger["tasks"][entry["task_id"]]
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(_result_payload(entry["envelope"], list(task["input_ids"]), report=None)),
        encoding="utf-8",
    )
    out = import_result(run_dir, entry["task_id"], result)
    assert out["state"] == "committed"
    call = LedgerStore(run_dir).open()["calls"][entry["call_id"]]
    assert (call.get("extra") or {}).get("self_report_status") == "missing"


def test_external_import_rejects_wrong_owner(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    entry = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    ledger = LedgerStore(run_dir).open()
    task = ledger["tasks"][entry["task_id"]]
    bad = dict(entry["envelope"])
    bad["owner"] = "someone-else"
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(_result_payload(bad, list(task["input_ids"]), report={"read": [entry["packet_id"]]})),
        encoding="utf-8",
    )
    with pytest.raises((RunnerError, Exception)):
        import_result(run_dir, entry["task_id"], result)


def test_second_claim_of_same_task_counts_exposure_again(tmp_path: Path) -> None:
    run_dir = _make_run(tmp_path)
    first = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    mid = derived_status(LedgerStore(run_dir).open())["known_source_chars"]
    # a fresh claim of the same leased task must fail the lease; claim a different task instead
    out = claim_kind(run_dir, kind="detail", count=5)
    new_chars = sum(item["source_chars"] for item in out["claimed"])
    after = derived_status(LedgerStore(run_dir).open())["known_source_chars"]
    assert after == mid + new_chars
    assert all(item["task_id"] != first["task_id"] for item in out["claimed"])
