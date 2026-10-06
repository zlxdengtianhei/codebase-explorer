"""Weighted refresh must re-freeze source, allocations, and task contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.documentation_budget import DocumentationBudgetInfeasible
from cbe.inventory import Inventory
from cbe.graph import GraphSnapshot
from cbe.promotion import promote_symbol
from cbe.render import estimate_weighted_navigation_tokens
from cbe.runner import analyze, claim_kind, import_result, refresh, work
from cbe.store import LedgerStore, frontier_ids
from cbe.token_budget import count_source_tokens
from cbe.weighting import assign_detail_priorities


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    lookup = "LOOKUP = {\n" + "".join(
        f"    'message-{index}': {index},\n" for index in range(280)
    ) + "}\n\n"
    (repo / "service.py").write_text(
        lookup
        + "def label(value):\n    return str(value)\n\n"
        + "def send_and_retry(client, value):\n"
        + "    try:\n        return client.publish(value)\n"
        + "    except OSError:\n        return client.retry(value)\n",
        encoding="utf-8",
    )
    return repo


def _symbol_id(ledger: dict, name: str) -> str:
    return next(
        sid for sid, symbol in ledger["inventory"]["symbols"].items()
        if symbol["name"] == name
    )


def test_weighted_refresh_reallocates_and_rekeys_affected_work(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    first = analyze(repo, run_dir, documentation_profile="weighted-v1")
    old_id = _symbol_id(first, "send_and_retry")
    old_source_tokens = first["documentation_policy"]["source_tokens"]
    work(run_dir, model="mock", limit=20)
    committed = LedgerStore(run_dir).open()
    assert old_id in committed["details"]
    old_task = next(
        task for task in committed["tasks"].values()
        if task["kind"] == "detail" and old_id in task["input_ids"]
    )

    path = repo / "service.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "return client.retry(value)",
            "return client.retry(value, countdown=5)",
        ),
        encoding="utf-8",
    )
    refresh(run_dir, repo)
    changed = LedgerStore(run_dir).open()
    new_id = _symbol_id(changed, "send_and_retry")
    policy = changed["documentation_policy"]
    assert policy["source_tokens"] == count_source_tokens(changed["inventory"], repo)
    assert policy["source_tokens"] > old_source_tokens
    assert policy["published_cap_tokens"] == policy["source_tokens"] // 2
    assert set(policy["symbols"]) == set(changed["inventory"]["symbols"])
    static = assign_detail_priorities(
        Inventory.from_dict(changed["inventory"]),
        GraphSnapshot.from_dict(changed["graph"]),
        repo,
    )
    assert policy["symbols"][new_id]["tier"] == static[new_id]["tier"]
    assert changed["details"][new_id]["provenance"]["stale"] is True
    new_task = next(
        task for task in changed["tasks"].values()
        if task["kind"] == "detail" and new_id in task["input_ids"] and task["state"] == "pending"
    )
    assert new_task["extra"]["policy_version"] == "weighted-v1"
    assert new_task["extra"]["output_policy"][new_id] == policy["symbols"][new_id]
    assert new_task["input_hash"] != old_task["input_hash"]
    assert policy["detail_allocated_tokens"] <= policy["detail_pool_tokens"]


def test_weighted_refresh_rejects_late_claim_envelope(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    claimed = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    old_task_id = claimed["task_id"]
    old_envelope = claimed["envelope"]
    path = repo / "service.py"
    path.write_text(path.read_text(encoding="utf-8") + "\ndef added():\n    return 42\n", encoding="utf-8")

    refresh(run_dir, repo)
    refreshed = LedgerStore(run_dir).open()
    assert refreshed["tasks"][old_task_id]["state"] == "stale"
    assert refreshed["tasks"][old_task_id]["generation"] > old_envelope["generation"]
    result = tmp_path / "late.json"
    result.write_text(json.dumps({"envelope": old_envelope, "details": []}), encoding="utf-8")
    with pytest.raises(Exception, match="stale|generation|owner|not writable"):
        import_result(run_dir, old_task_id, result)


def test_weighted_refresh_without_source_change_keeps_active_assignment(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    claimed = claim_kind(run_dir, kind="detail", count=1)["claimed"][0]
    before = LedgerStore(run_dir).open()["tasks"][claimed["task_id"]]

    refresh(run_dir, repo)
    after = LedgerStore(run_dir).open()["tasks"][claimed["task_id"]]
    assert after["state"] == "leased"
    assert after["generation"] == before["generation"]
    assert after["input_hash"] == before["input_hash"]
    assert after["owner"] == before["owner"]


def test_weighted_refresh_preserves_evidenced_promotion_on_unchanged_symbol(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    first = analyze(repo, run_dir, documentation_profile="weighted-v1")
    old_id = _symbol_id(first, "label")
    assert first["documentation_policy"]["symbols"][old_id]["tier"] == "brief"
    promote_symbol(run_dir, old_id, reason="The string conversion may fail.", source_line=285)
    promoted = LedgerStore(run_dir).open()["documentation_policy"]["symbols"][old_id]
    assert promoted["tier"] == "standard"

    path = repo / "service.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace("    'message-0': 0,", "    'message-0': 0,\n    'message-extra': 1,"),
        encoding="utf-8",
    )
    refresh(run_dir, repo)
    second = LedgerStore(run_dir).open()
    new_id = _symbol_id(second, "label")
    preserved = second["documentation_policy"]["symbols"][new_id]
    assert preserved["tier"] == "standard"
    assert preserved["promotion_history"] == promoted["promotion_history"]
    assert preserved["required_fields"] == promoted["required_fields"]


def test_weighted_refresh_invalidates_function_when_file_constant_changes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    work(run_dir, model="mock", limit=20)
    path = repo / "service.py"
    path.write_text(
        path.read_text(encoding="utf-8").replace("    'message-0': 0,", "    'message-0': 99,"),
        encoding="utf-8",
    )

    refresh(run_dir, repo)
    ledger = LedgerStore(run_dir).open()
    label_id = _symbol_id(ledger, "label")
    assert ledger["details"][label_id]["provenance"]["stale"] is True
    assert any(
        task["kind"] == "detail" and label_id in task["input_ids"] and task["state"] == "pending"
        for task in ledger["tasks"].values()
    )


def test_weighted_refresh_rekeys_fragment_merge_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    source = "def outer():\n" + "".join(
        f"    value_{index} = {index}\n" for index in range(180)
    ) + "    return value_179\n"
    path = repo / "nested.py"
    path.write_text(source, encoding="utf-8")
    monkeypatch.setenv("CBE_PACKET_WINDOW_CHARS", "180")
    run_dir = tmp_path / "run"
    initial = analyze(repo, run_dir, documentation_profile="weighted-v1")
    outer_id = _symbol_id(initial, "outer")
    merge_id = f"task:merge:{outer_id}"
    old_merge = initial["tasks"][merge_id]
    assert len(old_merge["extra"]["fragment_ids"]) > 1
    fragment_id = old_merge["extra"]["fragment_ids"][0]

    def remember_fragment(current: dict) -> dict:
        current["details"][fragment_id] = {
            "symbol_id": fragment_id,
            "behavior": "First source fragment",
            "inputs_outputs": [], "effects": [], "failures": [],
            "dependencies": [], "unresolved": [],
            "nav_sentence": "First source fragment",
            "source_spans": [], "packet_id": None,
            "input_hash": "old-fragment-input", "revision": 1,
            "provenance": {
                "role": "fragment", "fragment_id": fragment_id,
                "canonical_symbol_id": outer_id,
            },
        }
        return current

    LedgerStore(run_dir).mutate(remember_fragment)

    path.write_text(source.replace("return value_179", "return value_179 + 1"), encoding="utf-8")
    refresh(run_dir, repo)
    refreshed = LedgerStore(run_dir).open()
    new_outer_id = _symbol_id(refreshed, "outer")
    merge = refreshed["tasks"][f"task:merge:{new_outer_id}"]
    assert merge["state"] == "pending"
    assert merge["extra"]["policy_version"] == "weighted-v1"
    assert merge["extra"]["output_policy"][new_outer_id] == refreshed["documentation_policy"]["symbols"][new_outer_id]
    assert merge["input_hash"] != old_merge["input_hash"]
    assert refreshed["details"][fragment_id]["provenance"]["stale"] is True
    assert refreshed["details"][fragment_id]["provenance"]["historical"] is True
    if new_outer_id == outer_id:
        assert merge["generation"] > old_merge["generation"]


def test_weighted_refresh_invalidates_and_recovers_navigation_group(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    work(run_dir, model="mock", limit=20)
    ledger = LedgerStore(run_dir).open()
    members = [_symbol_id(ledger, "label"), _symbol_id(ledger, "send_and_retry")]
    ids_file = tmp_path / "ids.json"
    ids_file.write_text(json.dumps(members), encoding="utf-8")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=ids_file)
    result = tmp_path / "group.json"
    result.write_text(json.dumps({
        "envelope": claimed["envelope"],
        "groups": [{
            "group_id": "service-navigation",
            "presentation": "navigation",
            "children": [],
            "member_ids": members,
            "question_answered": "How does the service send values?",
            "grouping_reason": "Service entry and retry functions.",
            "entry_routes": members,
            "relations": [],
        }],
        "deferred_ids": [],
    }), encoding="utf-8")
    assert import_result(run_dir, claimed["task_id"], result)["state"] == "committed"
    before = LedgerStore(run_dir).open()
    assert "service-navigation" in frontier_ids(before)["groups"]
    assert "task:group_body:service-navigation" not in before["tasks"]
    review_ids = tmp_path / "review-ids.json"
    review_ids.write_text(json.dumps([members[0]]), encoding="utf-8")
    review_claim = claim_kind(run_dir, kind="review", target_ids_file=review_ids)
    review_before = LedgerStore(run_dir).open()["tasks"][review_claim["task_id"]]

    path = repo / "service.py"
    path.write_text(path.read_text(encoding="utf-8").replace("    'message-0': 0,", "    'message-0': 99,"), encoding="utf-8")
    refresh(run_dir, repo)
    stale = LedgerStore(run_dir).open()
    assert stale["groups"]["service-navigation"]["extra"]["stale"] is True
    assert "service-navigation" not in frontier_ids(stale)["groups"]
    assert "task:group_body:service-navigation" not in stale["tasks"]
    review_after = stale["tasks"][review_claim["task_id"]]
    assert review_after["state"] == "stale"
    assert review_after["generation"] > review_before["generation"]
    without_groups = dict(stale)
    without_groups["groups"] = {}
    assert stale["documentation_policy"]["fixed_navigation_tokens"] == (
        estimate_weighted_navigation_tokens(without_groups)["navigation_tokens"]
    )

    work(run_dir, model="mock", limit=20)
    repaired = LedgerStore(run_dir).open()
    assert "service-navigation" in frontier_ids(repaired)["groups"]
    assert repaired["groups"]["service-navigation"]["extra"]["evidence_summary"]["behavior"]


def test_weighted_refresh_budget_failure_is_atomic(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    analyze(repo, run_dir, documentation_profile="weighted-v1")
    ledger_file = run_dir / "semantic_ledger.json"
    before = ledger_file.read_bytes()
    (repo / "service.py").write_text("def label(value):\n    return str(value)\n", encoding="utf-8")

    with pytest.raises(DocumentationBudgetInfeasible):
        refresh(run_dir, repo)
    assert ledger_file.read_bytes() == before
