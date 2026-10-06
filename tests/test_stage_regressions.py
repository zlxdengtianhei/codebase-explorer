"""Stage regressions for claim CAS and surviving import paths (post trace-audit removal).

Deleted tests (sub-agent event trace audit removed from cbe.accounting/cbe.runner/cbe.cli):
- test_native_fallback_must_not_drop_list_text: native fallback projection deleted with ingest_native_trace.
- test_native_fallback_projects_mixed_tool_result_and_text: native fallback projection deleted.
- test_native_fallback_unknown_non_text_is_unverified: native fallback projection deleted.
- test_native_list_text_not_double_added_when_chat_used: native/chat pairing deleted.
- test_rejected_chat_falls_back_to_native_list_text: chat binding audit deleted.
- test_reinjected_prompt_must_not_reuse_initial_source_credit: frozen-prompt audit deleted.
- test_reinjected_prompt_reingest_is_idempotent: frozen-prompt audit deleted.
- test_prompt_index_without_matching_input_keeps_unknown_upper: frozen-prompt audit deleted.
- test_one_frozen_prompt_plus_new_synthetic_counts_synthetic: frozen-prompt audit deleted.
- test_multi_block_native_user_text_each_projected: native user-text projection deleted.
- test_bound_review_without_native_evidence_is_not_committed: bind_native_review and the review
  needs_evidence gate deleted (review import no longer requires a native trace).
- test_review_can_import_after_real_native_trace: native trace evidence import deleted.
- test_wrong_native_child_is_rejected: codex native child binding deleted.
- test_unpaired_native_user_is_not_dropped_when_chat_copied: native/chat pairing deleted.
- test_paired_same_event_counts_once: native/chat pairing deleted.
- test_two_same_text_presentations_count_twice: native/chat pairing deleted.
- test_truncated_chat_keeps_unpaired_native_unverified_or_upper: chat binding audit deleted.
- test_tool_pair_does_not_cover_extra_native_user: tool pairing audit deleted.
- test_repeat_source_and_unknown_tail_are_both_in_occupancy: dual-occupancy trace audit deleted.
- test_repeat_credit_delete_reingest_and_third_copy: repeat-presentation trace audit deleted.
- test_instruction_and_no_resource_and_unicode_escape_and_upgrade: InstructionResource matching deleted.
- test_header_only_native_is_not_committed: native evidence gate deleted.
- test_late_complete_read_clears_evidence_and_is_idempotent: native evidence gate deleted.
- test_include_source_delivery_rejects_incomplete_reads: review_source_delivery audit and
  is_authorized_astra_native_model deleted.
- test_committed_without_delivery_is_corrected: delivery-evidence correction gate deleted.
- test_same_text_is_only_candidate_without_event_bridge: event-bridge pairing deleted.
- test_two_bridged_same_text_presentations_count_twice: event-bridge pairing deleted.
- test_review_requires_frozen_delivery_identity_tampered_packet: packet identity audit deleted.
- test_tampered_packet_restore_then_complete_trace_commits_and_is_idempotent: packet identity
  audit and native trace import deleted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbe.runner import (
    analyze,
    claim_kind,
    import_result,
    work,
)
from cbe.store import StaleWriteError, claim_task, submit_details


def test_stale_generation_same_owner_must_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("def unique(x):\n    return x\n")
    state = analyze(repo, tmp_path / "run")
    task_id = next(iter(state["tasks"]))
    old = claim_task(state, task_id=task_id, owner="same-owner", owner_pid=None, lease_seconds=1)
    new = claim_task(state, task_id=task_id, owner="same-owner", owner_pid=None, lease_seconds=1)
    assert new.generation > old.generation
    with pytest.raises(StaleWriteError):
        submit_details(
            state,
            task_id=task_id,
            owner="same-owner",
            generation=old.generation,
            items=[],
            packet=None,
            call_id=None,
        )


def test_mock_detail_work_still_commits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("def ok():\n    return 1\n")
    run = tmp_path / "run"
    analyze(repo, run)
    work(run, model="mock")
    ledger = json.loads((run / "semantic_ledger.json").read_text())
    assert ledger["details"]
    # actual_model route evidence is deleted; the surviving mock marker is extra.mocked.
    assert all((call.get("extra") or {}).get("mocked") is True for call in ledger["calls"].values())


def _review_payload(claim: dict, review_id: str) -> dict:
    return {
        "envelope": claim["envelope"],
        "review_id": review_id,
        "verdict": "ok",
        "notes": "Synthetic review payload.",
        "source_chars": 0,
    }


def test_non_include_source_review_does_not_require_packet_read(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "calc.py").write_text("def scaled(x):\n    return x * 2\n")
    run = tmp_path / "run"
    analyze(repo, run)
    work(run, model="mock")
    state = json.loads((run / "semantic_ledger.json").read_text())
    sid = next(key for key, value in state["inventory"]["symbols"].items() if value["name"] == "scaled")
    ids = tmp_path / "review-ids.json"
    ids.write_text(json.dumps([sid]))
    claim = claim_kind(run, kind="review", target_ids_file=ids, include_source=False)
    output = tmp_path / "review-result.json"
    output.write_text(json.dumps(_review_payload(claim, "no-source")))
    accepted = import_result(run, claim["task_id"], output)
    assert accepted["state"] == "committed", accepted
