"""Consumer checks for the versioned, weighted Detail production contract."""

from __future__ import annotations

import json
import os
from pathlib import Path

from cbe.runner import analyze, build_detail_prompt, claim_kind, import_result
from cbe.store import LedgerStore, claim_task, submit_details


def test_cli_analyze_defaults_to_weighted_profile() -> None:
    from cbe.cli import build_parser

    args = build_parser().parse_args([
        "analyze", "--repo", "/tmp/cbe-repo", "--run-dir", "/tmp/cbe-run",
    ])
    assert args.documentation_profile == "weighted-v1"


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    lookup = "LOOKUP = {\n" + "".join(
        f"    'message-{index}': {index},\n" for index in range(240)
    ) + "}\n\n"
    (repo / "service.py").write_text(
        lookup +
        "def label(value):\n"
        "    return str(value)\n\n"
        "def send_and_retry(client, value):\n"
        "    try:\n"
        "        return client.publish(value)\n"
        "    except OSError:\n"
        "        return client.retry(value)\n",
        encoding="utf-8",
    )
    return repo


def test_weighted_analyze_rejects_infeasible_tiny_source(tmp_path: Path) -> None:
    repo = tmp_path / "tiny"
    repo.mkdir()
    (repo / "one.py").write_text("def one():\n    return 1\n", encoding="utf-8")
    run_dir = tmp_path / "run-tiny"
    from cbe.documentation_budget import DocumentationBudgetInfeasible
    import pytest

    with pytest.raises(DocumentationBudgetInfeasible):
        analyze(repo, run_dir, documentation_profile="weighted-v1")
    assert not (run_dir / "semantic_ledger.json").exists()


def test_weighted_analyze_freezes_policy_in_tasks_and_prompts(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    run_dir = tmp_path / "run"
    ledger = analyze(repo, run_dir, documentation_profile="weighted-v1")
    policy = ledger["documentation_policy"]
    assert policy["version"] == "weighted-v1"
    assert set(policy["symbols"]) == set(ledger["inventory"]["symbols"])
    assert policy["symbols"]
    for item in policy["symbols"].values():
        assert item["tier"] in {"brief", "standard", "deep"}
        assert item["signals"]
        assert item["suggested_output_tokens"] > 0

    claimed = claim_kind(run_dir, kind="detail", count=1)
    assert claimed["claimed"]
    first = claimed["claimed"][0]
    task = LedgerStore(run_dir).open()["tasks"][first["task_id"]]
    assert task["extra"]["policy_version"] == "weighted-v1"
    assert set(task["extra"]["output_policy"]) == set(task["input_ids"])
    prompt = json.loads(Path(first["prompt_path"]).read_text(encoding="utf-8"))
    assert all(item["output_policy"]["tier"] in {"brief", "standard", "deep"} for item in prompt["symbols"])
    assert all(item["output_policy"]["suggested_output_tokens"] > 0 for item in prompt["symbols"])
    assert {item["id"] for item in prompt["symbols"]} == set(task["input_ids"])
    assert "cbe_skill" not in prompt["resources"]
    assert "detail_reference" not in prompt["resources"]


def test_weighted_detail_prompt_preserves_assignment_and_source_without_grading_history() -> None:
    from cbe.ir import CharSpan
    from cbe.packets import Packet

    source = "def fn():\n    return other()\n\ndef other():\n    return 1\n"
    packet = Packet(
        packet_id="packet-1", path="service.py", language="python",
        spans=(CharSpan(0, len(source)),), symbol_ids=("service.fn", "service.other"),
        parent_symbol_id=None, slice_index=0, slice_count=1,
        content_hash="hash", source_chars=len(source),
    )
    other_start = source.index("def other")
    owned = [{"start": 0, "end": 10}, {"start": 14, "end": other_start}]
    policy = {
        "tier": "standard", "required_fields": ["behavior", "effects", "failures"],
        "suggested_output_tokens": 45, "shared_canonical_budget": 90,
        "score": 7, "signals": ["risk:io_or_persist"],
        "promotion_history": [{"source_line": 2, "missing_fact": "effect"}],
        "policy_version": "weighted-detail-v2",
    }
    symbols = [
        {
            "id": "service.fn::frag::a", "kind": "function", "name": "fn",
            "qualified_name": "fn", "parent_id": None,
            "span": {"start": 0, "end": other_start}, "exclusive_spans": owned,
            "canonical_symbol_id": "service.fn", "fragment_id": "service.fn::frag::a",
            "fragment_index": 0, "fragment_count": 2,
            "slice_index": 0, "slice_count": 2, "owned_spans": owned,
            "output_policy": policy, "tier": "standard",
            "required_fields": policy["required_fields"],
            "suggested_output_tokens": 45,
        },
        {
            "id": "service.other", "kind": "function", "name": "other",
            "qualified_name": "other", "parent_id": None,
            "span": {"start": other_start, "end": len(source)},
            "exclusive_spans": [{"start": other_start, "end": len(source)}],
            "output_policy": {
                "tier": "brief", "required_fields": ["behavior"],
                "suggested_output_tokens": 11, "score": 1, "signals": ["small"],
            },
        },
    ]
    edges = [{"subject_id": "service.fn", "target_id": "service.other", "kind": "call"}]
    envelope = {"task_id": "task-1", "generation": 2, "input_hash": "hash"}
    feedback = [{"code": "review_revision", "symbol_id": "service.fn::frag::a"}]

    raw = build_detail_prompt(
        packet=packet, source=source, symbols=symbols, edges=edges,
        envelope=envelope, result_path="/tmp/detail.json", feedback=feedback,
    )
    prompt = json.loads(raw)
    assert "\n" not in raw  # weighted JSON is compact; source newlines are escaped
    assert prompt["documentation_profile"] == "weighted-v1"
    assert {item["id"] for item in prompt["symbols"]} == {
        "service.fn::frag::a", "service.other",
    }
    fragment = prompt["symbols"][0]
    assert fragment["output_policy"] == {
        "tier": "standard", "required_fields": ["behavior", "effects", "failures"],
        "suggested_output_tokens": 45, "shared_canonical_budget": 90,
    }
    assert fragment["canonical_symbol_id"] == "service.fn"
    assert fragment["fragment_id"] == "service.fn::frag::a"
    assert fragment["fragment_index"] == 0
    assert fragment["fragment_count"] == 2
    assert fragment["owned_spans"] == owned
    assert fragment["span"] == {"start": 0, "end": other_start}
    assert "exclusive_spans" not in fragment
    assert "tier" not in fragment  # the binding value appears only in output_policy
    assert prompt["symbols"][1]["output_policy"] == {
        "tier": "brief", "required_fields": ["behavior"],
        "suggested_output_tokens": 11,
    }
    assert prompt["source"] == source
    assert source not in json.dumps(prompt["symbols"])
    assert prompt["spans"] == [{"start": 0, "end": len(source)}]
    assert prompt["direct_edges"] == edges
    assert prompt["envelope"] == envelope
    assert prompt["review_feedback"] == feedback
    assert "/tmp/detail.json" in prompt["result_file_rule"]
    assert "promotion_history" not in raw
    assert "risk:io_or_persist" not in raw


def test_legacy_detail_prompt_keeps_pretty_shape_and_structural_metadata() -> None:
    from cbe.ir import CharSpan
    from cbe.packets import Packet

    packet = Packet(
        packet_id="legacy", path="service.py", language="python",
        spans=(CharSpan(0, 10),), symbol_ids=("service.fn",),
        parent_symbol_id=None, slice_index=0, slice_count=1,
        content_hash="hash", source_chars=10,
    )
    symbol = {
        "id": "service.fn", "kind": "function", "name": "fn",
        "qualified_name": "fn", "parent_id": None,
        "span": {"start": 0, "end": 10},
        "exclusive_spans": [{"start": 0, "end": 10}],
    }
    raw = build_detail_prompt(packet=packet, source="return 1\n", symbols=[symbol], edges=[])
    prompt = json.loads(raw)
    assert raw.startswith('{\n  "role": "Detail producer",\n')
    assert prompt["symbols"] == [symbol]
    assert "documentation_profile" not in prompt
    assert prompt["placeholder_example"]["details"][0]["symbol_id"] == "<copy supplied id>"


def test_import_rejects_missing_required_weighted_fact(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analyze(_repo(tmp_path), run_dir)
    store = LedgerStore(run_dir)

    def claim_with_policy(current: dict) -> dict:
        task_id = next(tid for tid, task in current["tasks"].items() if task["kind"] == "detail")
        task = current["tasks"][task_id]
        target = task["input_ids"][0]
        task["extra"]["policy_version"] = "weighted-v1"
        task["extra"]["output_policy"] = {
            target: {
                "tier": "deep",
                "required_fields": ["behavior", "effects"],
                "suggested_output_tokens": 100,
            }
        }
        claim_task(
            current, task_id=task_id, owner="weighted-test", owner_pid=os.getpid(),
            lease_seconds=600, raw_exists=False,
        )
        return current

    ledger = store.mutate(claim_with_policy)
    task_id = next(tid for tid, task in ledger["tasks"].items() if task["kind"] == "detail")
    task = ledger["tasks"][task_id]
    target = task["input_ids"][0]

    def import_missing_effect(current: dict) -> dict:
        submit_details(
            current, task_id=task_id, owner="weighted-test",
            generation=task["generation"],
            items=[{"symbol_id": target, "behavior": "publishes a message"}],
            packet=None, call_id=None,
        )
        return current

    result = store.mutate(import_missing_effect)
    assert result["tasks"][task_id]["state"] == "needs_repair"
    assert any(
        item.get("code") == "required_field_missing" and item.get("symbol_id") == target
        for item in result["tasks"][task_id]["residual"]
    )


def test_weighted_group_claim_and_import_use_same_projection_hash(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    ledger = analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    symbols = ledger["inventory"]["symbols"]
    selected = [sid for sid, item in symbols.items() if item["name"] in {"label", "send_and_retry"}]
    assert len(selected) == 2
    store = LedgerStore(run_dir)

    def seed(current: dict) -> dict:
        for sid in selected:
            current["details"][sid] = {
                "symbol_id": sid, "behavior": "Handles one service action.",
                "inputs_outputs": [], "effects": [], "failures": [],
                "dependencies": [], "unresolved": [], "revision": 1,
                "provenance": {},
            }
        return current

    store.mutate(seed)
    ids_path = tmp_path / "selected.json"
    ids_path.write_text(json.dumps(selected), encoding="utf-8")
    claimed = claim_kind(run_dir, kind="group", input_ids_file=ids_path, owner="weighted-group-test")
    assert claimed["opened_task"]
    packet = json.loads(Path(claimed["packet"]).read_text(encoding="utf-8"))
    assert packet["projection"]["projection_version"]
    result_path = tmp_path / "group-result.json"
    result_path.write_text(json.dumps({
        "envelope": claimed["envelope"],
        "groups": [{
            "group_id": "service-actions", "member_ids": selected, "children": [],
            "question_answered": "How are service actions handled?",
            "grouping_reason": "Both functions handle service actions.",
            "presentation": "navigation", "entry_routes": [], "relations": [],
        }],
        "deferred_ids": [],
    }), encoding="utf-8")
    result = import_result(run_dir, claimed["task_id"], result_path)
    assert result["state"] == "committed"
    assert store.open()["groups"]["service-actions"]["extra"]["presentation"] == "navigation"


def test_reviewed_navigation_claim_rekeys_changed_children_and_replaces_same_id(tmp_path: Path) -> None:
    from cbe.runner import _invalidate_reviewed
    from cbe.store import _fresh_group_body

    run_dir = tmp_path / "run"
    ledger = analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    selected = [sid for sid, item in ledger["inventory"]["symbols"].items()
                if item["name"] in {"label", "send_and_retry"}]
    store = LedgerStore(run_dir)

    def seed(current: dict) -> dict:
        for sid in selected:
            current["details"][sid] = {
                "symbol_id": sid, "behavior": "Handles one service action.",
                "effects": [], "failures": [], "unresolved": [],
                "revision": 1, "provenance": {},
            }
        return current

    store.mutate(seed)
    ids_path = tmp_path / "selected.json"
    ids_path.write_text(json.dumps(selected), encoding="utf-8")
    first = claim_kind(run_dir, kind="group", input_ids_file=ids_path)
    result_path = tmp_path / "group-first.json"
    result_path.write_text(json.dumps({
        "envelope": first["envelope"], "groups": [{
            "group_id": "service-actions", "member_ids": selected, "children": [],
            "question_answered": "How are service actions handled?",
            "grouping_reason": "Both provide service actions.",
            "presentation": "navigation", "entry_routes": [], "relations": [],
        }], "deferred_ids": [],
    }), encoding="utf-8")
    assert import_result(run_dir, first["task_id"], result_path)["state"] == "committed"

    def flag_and_change(current: dict) -> dict:
        _invalidate_reviewed(current, {"findings": [{
            "group_id": "service-actions", "issue": "Misleading module question",
            "correction": "Describe both responsibilities accurately",
        }]})
        current["details"][selected[0]]["behavior"] = "Names a service result."
        return current

    before = store.mutate(flag_and_change)
    repair_id = "task:group:review:service-actions"
    old_hash = before["tasks"][repair_id]["input_hash"]
    assert _fresh_group_body(before, "service-actions") is None
    repair = claim_kind(run_dir, kind="group", task_id=repair_id)
    assert repair["opened_task"]
    assert repair["envelope"]["input_hash"] != old_hash
    packet = json.loads(Path(repair["packet"]).read_text(encoding="utf-8"))
    assert packet["replace_group_id"] == "service-actions"
    assert packet["review_feedback"][0]["issue"] == "Misleading module question"
    result_path.write_text(json.dumps({
        "envelope": repair["envelope"], "groups": [{
            "group_id": "service-actions", "member_ids": selected, "children": [],
            "question_answered": "How are labeling and retries handled?",
            "grouping_reason": "The functions expose distinct service actions.",
            "presentation": "navigation", "entry_routes": [], "relations": [],
        }], "deferred_ids": [],
    }), encoding="utf-8")
    assert import_result(run_dir, repair_id, result_path)["state"] == "committed"
    after = store.open()
    assert _fresh_group_body(after, "service-actions") is not None
    assert not after["groups"]["service-actions"]["extra"].get("review_hold")


def test_review_revision_immediately_invalidates_group_and_ancestors() -> None:
    from cbe.runner import _invalidate_reviewed
    from cbe.models import TaskRecord

    ledger = {
        "documentation_policy": {"version": "weighted-v1"},
        "details": {"service.fn": {
            "symbol_id": "service.fn", "behavior": "Old fact", "revision": 1,
            "provenance": {},
        }},
        "groups": {
            "child": {"group_id": "child", "member_ids": ["service.fn"], "children": [],
                      "body": "Old child claim", "version": 1, "parent_id": "root", "extra": {}},
            "root": {"group_id": "root", "member_ids": [], "children": ["child"],
                     "body": "Old root claim", "version": 1, "parent_id": None, "extra": {}},
        },
        "tasks": {"task:detail:one": TaskRecord(
            task_id="task:detail:one", kind="detail", input_ids=["service.fn"],
            input_hash="old", state="committed",
        ).to_dict()},
    }
    _invalidate_reviewed(ledger, {"findings": [{
        "symbol_id": "service.fn", "issue": "Old fact is wrong", "evidence": "source line 10",
    }]})
    assert ledger["details"]["service.fn"]["provenance"]["stale"]
    assert ledger["groups"]["child"]["extra"]["body_stale"]
    assert ledger["groups"]["root"]["extra"]["body_stale"]
    assert ledger["tasks"]["task:group_body:child"]["state"] == "pending"


def test_reviewed_detail_can_replace_stale_record_after_packet_rekey() -> None:
    from cbe.models import TaskRecord

    ledger = {
        "details": {"service.fn": {
            "symbol_id": "service.fn", "behavior": "Incorrect old fact",
            "input_hash": "old-packet-hash", "revision": 1,
            "provenance": {"stale": True, "review_flag": "incorrect"},
        }},
        "tasks": {"task:detail:one": TaskRecord(
            task_id="task:detail:one", kind="detail", input_ids=["service.fn"],
            input_hash="new-packet-hash", state="leased", owner="repair-author",
            generation=2, extra={
                "policy_version": "weighted-v1",
                "output_policy": {"service.fn": {
                    "tier": "brief", "required_fields": ["behavior"],
                    "suggested_output_tokens": 30,
                }},
                "repair_ids": ["service.fn"],
            },
        ).to_dict()},
    }
    result = submit_details(
        ledger, task_id="task:detail:one", owner="repair-author",
        generation=2, items=[{"symbol_id": "service.fn", "behavior": "Corrected fact"}],
        packet=None, call_id=None,
    )
    assert result.state == "committed"
    assert ledger["details"]["service.fn"]["behavior"] == "Corrected fact"
    assert not ledger["details"]["service.fn"]["provenance"].get("stale")


def test_oversized_weighted_group_packet_releases_lease(tmp_path: Path, monkeypatch) -> None:
    from cbe.runner import RunnerError
    import pytest

    run_dir = tmp_path / "run"
    ledger = analyze(_repo(tmp_path), run_dir, documentation_profile="weighted-v1")
    selected = [sid for sid, symbol in ledger["inventory"]["symbols"].items()
                if symbol["name"] in {"label", "send_and_retry"}]
    store = LedgerStore(run_dir)

    def seed(current: dict) -> dict:
        for sid in selected:
            current["details"][sid] = {"symbol_id": sid, "behavior": "Handles one action.",
                                      "effects": [], "failures": [], "unresolved": [],
                                      "revision": 1, "provenance": {}}
        return current

    store.mutate(seed)
    ids_path = tmp_path / "ids.json"
    ids_path.write_text(json.dumps(selected), encoding="utf-8")
    monkeypatch.setenv("CBE_GROUP_PACKET_WINDOW_CHARS", "2000")
    with pytest.raises(RunnerError, match="lease was released"):
        claim_kind(run_dir, kind="group", input_ids_file=ids_path)
    group_tasks = [task for task in store.open()["tasks"].values() if task["kind"] == "group"]
    assert len(group_tasks) == 1
    assert group_tasks[0]["state"] == "needs_repair"
    assert group_tasks[0]["owner"] is None
