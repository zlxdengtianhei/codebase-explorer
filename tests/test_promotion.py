from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from cbe.promotion import PromotionBudgetError, PromotionError, promote_symbol
from cbe.runner import RunnerError, analyze, build_detail_task, import_result
from cbe.store import LedgerStore, claim_task, load_unique_packets, submit_details


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    lookup = "LOOKUP = {\n" + "".join(f"    'message-{index}': {index},\n" for index in range(240)) + "}\n\n"
    (repo / "service.py").write_text(
        lookup + "def label(value):\n    return str(value)\n\n"
        "def retry(client, value):\n"
        "    try:\n        return client.publish(value)\n"
        "    except OSError:\n        return client.retry(value)\n",
        encoding="utf-8",
    )
    return repo


def _brief_id(ledger: dict) -> str:
    policies = ledger["documentation_policy"]["symbols"]
    return next(sid for sid, item in policies.items() if item["tier"] == "brief" and ledger["inventory"]["symbols"][sid]["name"] == "label")


def _task_for(ledger: dict, symbol_id: str) -> tuple[str, dict]:
    return next(
        (task_id, task)
        for task_id, task in ledger["tasks"].items()
        if task["kind"] == "detail" and symbol_id in (task.get("extra") or {}).get("output_policy", {})
    )


def test_consumes_promotion_request_rekeys_task_and_rejects_late_envelope(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    store = LedgerStore(run_dir)
    before = store.open()
    symbol_id = _brief_id(before)
    task_id, raw = _task_for(before, symbol_id)
    old_hash = raw["input_hash"]
    old_reserve = before["documentation_policy"]["repair_reserve_tokens"]
    old_quota = before["documentation_policy"]["symbols"][symbol_id]["suggested_output_tokens"]
    old_envelope: dict = {}

    def request(current: dict) -> dict:
        task = claim_task(
            current, task_id=task_id, owner="promotion-test", owner_pid=os.getpid(),
            lease_seconds=600, raw_exists=False,
        )
        old_envelope.update({
            "task_id": task_id, "generation": task.generation,
            "owner": task.owner, "input_hash": task.input_hash,
        })
        submit_details(
            current, task_id=task_id, owner="promotion-test", generation=task.generation,
            items=[{
                "symbol_id": symbol_id,
                "needs_promotion": {"source_line": 245, "missing_fact": "Raises if conversion fails."},
            }],
            packet=load_unique_packets(current)[task.packet_id], call_id=None,
        )
        return current

    store.mutate(request)
    result = promote_symbol(run_dir, symbol_id)
    after = store.open()
    new_policy = after["documentation_policy"]["symbols"][symbol_id]
    new_task = after["tasks"][task_id]

    assert result["to_tier"] == "standard"
    assert new_policy["tier"] == "standard"
    assert new_policy["required_fields"] == ["behavior", "effects", "failures"]
    assert new_policy["suggested_output_tokens"] > old_quota
    assert after["documentation_policy"]["repair_reserve_tokens"] < old_reserve
    assert new_task["input_hash"] != old_hash
    assert new_task["generation"] == old_envelope["generation"] + 1
    assert new_task["state"] == "pending"
    assert symbol_id in new_task["extra"]["repair_ids"]
    assert new_task["extra"]["output_policy"][symbol_id]["tier"] == "standard"

    stale_result = tmp_path / "stale.json"
    stale_result.write_text(json.dumps({
        "envelope": old_envelope,
        "details": [{"symbol_id": symbol_id, "behavior": "old result"}],
    }), encoding="utf-8")
    with pytest.raises(RunnerError, match="stale generation"):
        import_result(run_dir, task_id, stale_result)
    with pytest.raises(PromotionError, match="only the next tier deep"):
        promote_symbol(run_dir, symbol_id, tier="brief", reason="Do not downgrade", source_line=245)
    second = promote_symbol(
        run_dir, symbol_id, tier="deep", reason="Also document the input contract.", source_line=245
    )
    assert second["from_tier"] == "standard"
    assert LedgerStore(run_dir).open()["documentation_policy"]["symbols"][symbol_id]["tier"] == "deep"


def test_budget_exhaustion_is_atomic(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    store = LedgerStore(run_dir)
    symbol_id = _brief_id(store.open())

    def exhaust(current: dict) -> dict:
        current["documentation_policy"]["repair_reserve_tokens"] = 1
        return current

    store.mutate(exhaust)
    before = store.open()
    with pytest.raises(PromotionBudgetError):
        promote_symbol(run_dir, symbol_id, reason="The helper hides a failure path.", source_line=245)
    after = store.open()
    assert after["ledger_revision"] == before["ledger_revision"]
    assert after["documentation_policy"] == before["documentation_policy"]


def test_promoted_packet_repair_keeps_other_accepted_symbols(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    store = LedgerStore(run_dir)
    before = store.open()
    symbol_id = _brief_id(before)
    task_id, task_raw = _task_for(before, symbol_id)
    assert len(task_raw["input_ids"]) >= 2

    def first_import(current: dict) -> dict:
        task = claim_task(current, task_id=task_id, owner="first", owner_pid=os.getpid(),
                          lease_seconds=600, raw_exists=False)
        submit_details(
            current, task_id=task_id, owner="first", generation=task.generation,
            items=[{
                "symbol_id": sid, "behavior": "Initial behavior.",
                "inputs_outputs": [], "effects": [], "failures": [],
                "dependencies": [], "unresolved": [],
            } for sid in task.input_ids],
            packet=load_unique_packets(current)[task.packet_id], call_id=None,
        )
        return current

    first = store.mutate(first_import)
    assert first["tasks"][task_id]["state"] == "committed"
    promote_symbol(run_dir, symbol_id, reason="Boundary needs a fuller account.", source_line=245)

    def repair_one(current: dict) -> dict:
        task = claim_task(current, task_id=task_id, owner="repair", owner_pid=os.getpid(),
                          lease_seconds=600, raw_exists=False)
        submit_details(
            current, task_id=task_id, owner="repair", generation=task.generation,
            items=[{
                "symbol_id": symbol_id, "behavior": "More precise behavior.",
                "inputs_outputs": [], "effects": [], "failures": [],
                "dependencies": [], "unresolved": [],
            }],
            packet=load_unique_packets(current)[task.packet_id], call_id=None,
        )
        return current

    repaired = store.mutate(repair_one)
    assert repaired["tasks"][task_id]["state"] == "committed"
    assert set(repaired["tasks"][task_id]["output_refs"]) == set(task_raw["input_ids"])


def test_legacy_run_cannot_promote(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    sid = next(iter(LedgerStore(run_dir).open()["inventory"]["symbols"]))
    with pytest.raises(ValueError, match="weighted-v1"):
        promote_symbol(run_dir, sid, reason="Needs an exception note", source_line=1)


def test_fragment_promotion_spends_one_canonical_reserve_and_invalidates_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_large.py").write_text(
        "def test_long(value):\n    result = 0\n"
        + "".join(f"    result += {index}\n" for index in range(250))
        + "    return result\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CBE_PACKET_WINDOW_CHARS", "800")
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    store = LedgerStore(run_dir)
    before = store.open()
    symbol_id = next(
        sid for sid, symbol in before["inventory"]["symbols"].items()
        if symbol["name"] == "test_long"
    )
    assert before["documentation_policy"]["symbols"][symbol_id]["tier"] == "brief"
    fragment_tasks = [
        (task_id, task)
        for task_id, task in before["tasks"].items()
        if task["kind"] == "detail"
        and any(
            fragment.get("symbol_id") == symbol_id
            for fragment in (task.get("extra") or {}).get("fragments", [])
        )
    ]
    assert len(fragment_tasks) >= 2
    old_quota = before["documentation_policy"]["symbols"][symbol_id]["suggested_output_tokens"]
    old_reserve = before["documentation_policy"]["repair_reserve_tokens"]
    old_hashes = {task_id: task["input_hash"] for task_id, task in fragment_tasks}
    fragment_id = fragment_tasks[0][1]["input_ids"][0]
    merge_id = f"task:merge:{symbol_id}"
    old_merge_hash = before["tasks"][merge_id]["input_hash"]

    def accepted(current: dict) -> dict:
        current["details"][fragment_id] = {
            "symbol_id": fragment_id, "behavior": "Old fragment fact.",
            "provenance": {"role": "fragment", "canonical_symbol_id": symbol_id},
            "revision": 1, "input_hash": old_hashes[fragment_tasks[0][0]],
        }
        current["details"][symbol_id] = {
            "symbol_id": symbol_id, "behavior": "Old combined fact.",
            "provenance": {"role": "canonical", "fresh": True},
            "revision": 1, "input_hash": old_merge_hash,
        }
        current["groups"]["test-flow"] = {
            "group_id": "test-flow", "member_ids": [symbol_id], "children": [],
            "question_answered": "What does the test do?", "grouping_reason": "fixture",
            "entry_routes": [symbol_id], "relations": [], "body": "Old group description.",
            "version": 1, "parent_id": None, "partial": False, "extra": {},
        }
        return current

    store.mutate(accepted)
    result = promote_symbol(run_dir, symbol_id, reason="The test may raise for bad inputs.", source_line=2)
    after = store.open()
    policy = after["documentation_policy"]
    delta = result["quota_delta_tokens"]
    assert policy["repair_reserve_tokens"] == old_reserve - delta
    assert policy["symbols"][symbol_id]["suggested_output_tokens"] == old_quota + delta
    assert after["details"][fragment_id]["provenance"]["historical"] is True
    assert after["details"][symbol_id]["provenance"]["historical"] is True
    assert after["groups"]["test-flow"]["extra"]["stale"] is True
    assert after["tasks"][merge_id]["input_hash"] != old_merge_hash
    for task_id, old_task in fragment_tasks:
        new_task = after["tasks"][task_id]
        assert new_task["input_hash"] != old_hashes[task_id]
        assert new_task["generation"] == old_task["generation"] + 1
        fragment_policy = new_task["extra"]["output_policy"][new_task["input_ids"][0]]
        assert fragment_policy["tier"] == "standard"
        assert fragment_policy["shared_canonical_budget"] == old_quota + delta


def test_evidenced_deep_quota_top_up_from_88_to_148_is_atomic(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    store = LedgerStore(run_dir)
    symbol_id = _brief_id(store.open())
    promote_symbol(run_dir, symbol_id, reason="Exception path needs detail.", source_line=245)
    promote_symbol(run_dir, symbol_id, reason="Nested order needs detail.", source_line=245)

    def seed_real_quota(current: dict) -> dict:
        policy = current["documentation_policy"]
        symbol_policy = policy["symbols"][symbol_id]
        assert symbol_policy["tier"] == "deep"
        adjustment = 88 - symbol_policy["suggested_output_tokens"]
        symbol_policy["suggested_output_tokens"] = 88
        policy["detail_allocated_tokens"] += adjustment
        policy["detail_pool_tokens"] += adjustment
        policy["repair_reserve_tokens"] -= adjustment
        task_id, raw = _task_for(current, symbol_id)
        rebuilt = build_detail_task(
            load_unique_packets(current)[raw["packet_id"]], symbol_policies=policy["symbols"]
        )
        raw["input_hash"] = rebuilt.input_hash
        raw["extra"] = rebuilt.extra
        current["tasks"][task_id] = raw
        return current

    store.mutate(seed_real_quota)
    before = store.open()
    task_id, task = _task_for(before, symbol_id)
    assert before["documentation_policy"]["symbols"][symbol_id]["suggested_output_tokens"] == 88
    reserve = before["documentation_policy"]["repair_reserve_tokens"]
    assert reserve >= 60

    with pytest.raises(PromotionError, match="valid promotion_requested"):
        promote_symbol(run_dir, symbol_id, extra_tokens=60)
    with pytest.raises(PromotionError, match="already deep"):
        promote_symbol(run_dir, symbol_id, reason="A fact", source_line=245)
    result = promote_symbol(
        run_dir, symbol_id, tier="deep", extra_tokens=60,
        reason="Reject precedes Retry and clears traceback.", source_line=245,
    )
    after = store.open()
    assert result["budget_only"] is True
    assert result["from_tier"] == result["to_tier"] == "deep"
    assert result["quota_delta_tokens"] == 60
    assert after["documentation_policy"]["symbols"][symbol_id]["suggested_output_tokens"] == 148
    assert after["documentation_policy"]["repair_reserve_tokens"] == reserve - 60
    assert after["tasks"][task_id]["input_hash"] != task["input_hash"]
    assert after["tasks"][task_id]["generation"] == task["generation"] + 1

    exhausted_dir = tmp_path / "exhausted"
    shutil.copytree(run_dir, exhausted_dir)
    exhausted_store = LedgerStore(exhausted_dir)
    exhausted_store.mutate(lambda current: _set_reserve(current, 59))
    exhausted_before = exhausted_store.open()
    with pytest.raises(PromotionBudgetError):
        promote_symbol(
            exhausted_dir, symbol_id, extra_tokens=60,
            reason="The same nested path needs still more detail.", source_line=245,
        )
    exhausted_after = exhausted_store.open()
    assert exhausted_after["ledger_revision"] == exhausted_before["ledger_revision"]
    assert exhausted_after["documentation_policy"] == exhausted_before["documentation_policy"]


def _set_reserve(current: dict, tokens: int) -> dict:
    current["documentation_policy"]["repair_reserve_tokens"] = tokens
    return current
