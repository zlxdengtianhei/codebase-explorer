"""Weighted grouping contracts at the ledger boundary."""

from __future__ import annotations

from cbe.models import TaskRecord
from cbe.store import (
    _fresh_group_body,
    content_fingerprint,
    frontier_ids,
    invalidate_group_bodies,
    narrative_evidence_summary,
    submit_groups,
    validate_group_evidence_summary,
)


def _detail(symbol_id: str, behavior: str) -> dict:
    return {
        "symbol_id": symbol_id,
        "behavior": behavior,
        "nav_sentence": behavior,
        "inputs_outputs": [],
        "effects": [f"{symbol_id} writes state"],
        "failures": [],
        "unresolved": None,
        "revision": 1,
        "provenance": {},
    }


def _ledger(*, weighted: bool, group_limit: int = 2) -> dict:
    ledger = {
        "details": {"one": _detail("one", "Load configuration"), "two": _detail("two", "Start worker")},
        "groups": {},
        "tasks": {
            "task:group:test": TaskRecord(
                task_id="task:group:test",
                kind="group",
                input_ids=["one", "two"],
                input_hash="h1",
                state="leased",
                owner="worker",
                generation=1,
            ).to_dict()
        },
    }
    if weighted:
        ledger["documentation_policy"] = {"version": "weighted-v1", "group_limit": group_limit}
    return ledger


def _submit(ledger: dict, plans: list[dict]) -> TaskRecord:
    return submit_groups(
        ledger,
        task_id="task:group:test",
        owner="worker",
        generation=1,
        input_hash="h1",
        plans=plans,
    )


def _plan(group_id: str, *, presentation: str | None = None, body: str = "") -> dict:
    plan = {
        "group_id": group_id,
        "member_ids": ["one", "two"],
        "children": [],
        "question_answered": "How does startup work?",
        "grouping_reason": "Both functions control startup.",
        "entry_routes": ["one"],
        "relations": [],
        "body": body,
    }
    if presentation is not None:
        plan["presentation"] = presentation
    return plan


def test_weighted_navigation_is_fresh_without_group_body_task() -> None:
    ledger = _ledger(weighted=True)
    task = _submit(ledger, [_plan("startup", presentation="navigation")])

    assert task.state == "committed"
    group = ledger["groups"]["startup"]
    assert group["body"] == ""
    assert group["extra"]["presentation"] == "navigation"
    assert "task:group_body:startup" not in ledger["tasks"]
    assert _fresh_group_body(ledger, "startup") is group
    assert frontier_ids(ledger)["groups"] == ["startup"]
    summary = group["extra"]["evidence_summary"]
    assert "Load configuration" in summary["behavior"]
    assert "Start worker" in summary["behavior"]
    assert summary["effects"] == [
        {"source_id": "one", "value": ["one writes state"]},
        {"source_id": "two", "value": ["two writes state"]},
    ]
    assert summary["unresolved"] == [
        {"source_id": "one", "value": None},
        {"source_id": "two", "value": None},
    ]


def test_narrative_body_derives_child_evidence_instead_of_requiring_duplicate_model_output() -> None:
    from cbe.runner import _weighted_group_body_errors

    ledger = _ledger(weighted=True)
    ledger["documentation_policy"]["group_body_content_tokens"] = 20
    task = _submit(ledger, [_plan("startup", presentation="narrative")])
    assert task.state == "committed"
    group = ledger["groups"]["startup"]
    summary = narrative_evidence_summary(ledger, group, "Loads config, then starts the worker.")
    assert summary["behavior"] == "Loads config, then starts the worker."
    assert summary["effects"] == [
        {"source_id": "one", "value": ["one writes state"]},
        {"source_id": "two", "value": ["two writes state"]},
    ]
    assert not _weighted_group_body_errors(
        ledger, {"body": "Loads config, then starts the worker."}, group_id="startup"
    )
    assert _weighted_group_body_errors(
        ledger, {"body": "Repeats a long explanation of the same behavior many times " * 10},
        group_id="startup",
    )[0]["code"] == "group_body_over_budget"


def test_reviewed_group_error_hides_body_and_passes_feedback_to_repair() -> None:
    from cbe.runner import _invalidate_reviewed, build_group_body_prompt
    from cbe.store import group_body_input_hash

    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="narrative")])
    group = ledger["groups"]["startup"]
    group["body"] = "The worker starts before loading configuration."
    group["extra"]["evidence_summary"] = narrative_evidence_summary(ledger, group, group["body"])
    ledger["tasks"]["task:group_body:startup"]["state"] = "committed"
    before = group_body_input_hash(ledger, group)

    _invalidate_reviewed(ledger, {
        "findings": [{
            "group_id": "startup",
            "issue": "Reversed startup order",
            "evidence": "one loads configuration; two starts worker",
            "correction": "Load configuration before starting worker",
        }]
    })

    assert _fresh_group_body(ledger, "startup") is None
    assert ledger["tasks"]["task:group_body:startup"]["state"] == "pending"
    assert group_body_input_hash(ledger, group) != before
    prompt = build_group_body_prompt(group, [], weighted=True, quota_tokens=75)
    assert "Reversed startup order" in prompt
    assert "Load configuration before starting worker" in prompt


def test_reviewed_navigation_group_stays_hidden_until_regrouped() -> None:
    from cbe.runner import _invalidate_reviewed
    from cbe.store import _refresh_navigation_group

    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="navigation")])
    assert _fresh_group_body(ledger, "startup") is not None

    _invalidate_reviewed(ledger, {
        "findings": [{
            "group_id": "startup",
            "issue": "This is a misleading directory title",
            "correction": "Use a question that fits both children",
            "evidence": "The two children have separate startup responsibilities",
        }]
    })

    assert _fresh_group_body(ledger, "startup") is None
    repair = ledger["tasks"]["task:group:review:startup"]
    assert repair["state"] == "pending"
    assert repair["input_ids"] == ["one", "two"]
    assert repair["extra"]["replace_group_id"] == "startup"
    assert "misleading directory title" in repair["extra"]["review_feedback"][0]["issue"]
    _refresh_navigation_group(ledger, "startup")
    assert _fresh_group_body(ledger, "startup") is None


def test_review_regroup_rejects_new_id_before_orphaning_parent() -> None:
    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="navigation")])
    ledger["tasks"]["task:group:review:startup"] = TaskRecord(
        task_id="task:group:review:startup", kind="group",
        input_ids=["one", "two"], input_hash="review-hash", state="leased",
        owner="review-author", generation=1,
        extra={"created_by": "source_review", "replace_group_id": "startup"},
    ).to_dict()
    task = submit_groups(
        ledger, task_id="task:group:review:startup", owner="review-author",
        generation=1, input_hash="review-hash",
        plans=[_plan("replacement", presentation="navigation")],
        replace_group_id="startup",
    )
    assert task.state == "needs_repair"
    assert any(item["code"] == "review_regroup_requires_same_id" for item in task.residual)
    assert "replacement" not in ledger["groups"]


def test_weighted_group_limit_rejects_without_writing() -> None:
    ledger = _ledger(weighted=True, group_limit=0)
    task = _submit(ledger, [_plan("startup", presentation="navigation")])

    assert task.state == "needs_repair"
    assert any(item["code"] == "group_limit_exceeded" for item in task.residual)
    assert ledger["groups"] == {}
    assert "task:group_body:startup" not in ledger["tasks"]


def test_legacy_group_still_queues_body_and_requires_it_for_frontier() -> None:
    ledger = _ledger(weighted=False)
    task = _submit(ledger, [_plan("startup")])

    assert task.state == "committed"
    assert ledger["tasks"]["task:group_body:startup"]["state"] == "pending"
    assert _fresh_group_body(ledger, "startup") is None
    assert frontier_ids(ledger)["groups"] == []


def test_navigation_child_change_rebuilds_facts_without_model_task() -> None:
    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="navigation")])
    before = content_fingerprint(ledger["groups"]["startup"])
    ledger["details"]["one"]["effects"] = ["one deletes state"]

    assert _fresh_group_body(ledger, "startup") is None
    invalidate_group_bodies(ledger, ["startup"])
    assert _fresh_group_body(ledger, "startup") is not None
    assert "task:group_body:startup" not in ledger["tasks"]
    assert content_fingerprint(ledger["groups"]["startup"]) != before
    assert ledger["groups"]["startup"]["extra"]["evidence_summary"]["effects"][0] == {
        "source_id": "one", "value": ["one deletes state"]
    }


def test_navigation_group_waits_for_repaired_child_without_omitting_its_facts() -> None:
    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="navigation")])
    ledger["details"]["one"]["provenance"]["stale"] = True

    invalidate_group_bodies(ledger, ["startup"])
    assert _fresh_group_body(ledger, "startup") is None
    assert "evidence_summary" not in ledger["groups"]["startup"]["extra"]
    assert "task:group_body:startup" not in ledger["tasks"]

    ledger["details"]["one"]["provenance"].pop("stale")
    ledger["details"]["one"]["failures"] = ["Raises on invalid config"]
    invalidate_group_bodies(ledger, ["startup"])
    assert _fresh_group_body(ledger, "startup") is not None
    assert ledger["groups"]["startup"]["extra"]["evidence_summary"]["failures"][0] == {
        "source_id": "one", "value": ["Raises on invalid config"]
    }


def test_group_limit_ignores_replaced_history() -> None:
    ledger = _ledger(weighted=True, group_limit=1)
    ledger["groups"]["prior"] = {
        "group_id": "prior", "member_ids": [], "children": [], "body": "old",
        "version": 1, "extra": {"replaced_by": ["later"]},
    }
    task = _submit(ledger, [_plan("startup", presentation="navigation")])
    assert task.state == "committed"
    assert set(ledger["groups"]) == {"prior", "startup"}


def test_group_limit_still_counts_active_groups() -> None:
    ledger = _ledger(weighted=True, group_limit=1)
    ledger["groups"]["prior"] = {
        "group_id": "prior", "member_ids": [], "children": [], "body": "old",
        "version": 1, "extra": {},
    }
    task = _submit(ledger, [_plan("startup", presentation="navigation")])
    assert task.state == "needs_repair"
    assert {item["code"] for item in task.residual} >= {"group_limit_exceeded"}
    assert set(ledger["groups"]) == {"prior"}


def test_narrative_summary_distinguishes_unknown_from_checked_absent() -> None:
    assert validate_group_evidence_summary({
        "behavior": "Starts the worker", "effects": [], "failures": None, "unresolved": []
    })
    assert not validate_group_evidence_summary({
        "behavior": "Starts the worker", "effects": "none", "failures": None, "unresolved": []
    })
    assert not validate_group_evidence_summary({
        "behavior": " ", "effects": [], "failures": None, "unresolved": []
    })
    assert not validate_group_evidence_summary({
        "behavior": "Starts the worker", "effects": [], "failures": None
    })

    ledger = _ledger(weighted=True)
    plan = _plan("startup", presentation="narrative", body="Starts the worker")
    plan["evidence_summary"] = {
        "behavior": "Starts the worker", "effects": [], "failures": None, "unresolved": []
    }
    task = _submit(ledger, [plan])
    assert task.state == "needs_repair"
    assert any(item["code"] == "weighted_group_body_must_use_task" for item in task.residual)

    ledger = _ledger(weighted=True)
    task = _submit(ledger, [_plan("startup", presentation="narrative")])
    assert task.state == "committed"
    assert ledger["tasks"]["task:group_body:startup"]["state"] == "pending"


def test_presentation_is_part_of_group_content_fingerprint() -> None:
    ledger = _ledger(weighted=True)
    _submit(ledger, [_plan("startup", presentation="navigation")])
    group = ledger["groups"]["startup"]
    original = content_fingerprint(group)
    group["extra"]["presentation"] = "narrative"
    assert content_fingerprint(group) != original


def test_weighted_navigation_rejects_body_and_single_child_passthrough() -> None:
    ledger = _ledger(weighted=True)
    with_body = _submit(ledger, [_plan("startup", presentation="navigation", body="Duplicated prose")])
    assert with_body.state == "needs_repair"
    assert any(item["code"] == "navigation_body_forbidden" for item in with_body.residual)
    assert ledger["groups"] == {}

    ledger = _ledger(weighted=True)
    plan = _plan("startup", presentation="navigation")
    plan["member_ids"] = ["one"]
    task = submit_groups(
        ledger,
        task_id="task:group:test",
        owner="worker",
        generation=1,
        input_hash="h1",
        plans=[plan],
        deferred_ids=["two"],
    )
    assert task.state == "needs_repair"
    assert any(item["code"] == "empty_pass_through_chain" for item in task.residual)
