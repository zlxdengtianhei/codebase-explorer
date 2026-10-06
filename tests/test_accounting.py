"""Budget skeleton accounting tests (post 2026-09-21 trace-audit removal).

Deleted tests (sub-agent event trace audit removed from cbe.accounting/cbe.runner):
- test_protocol_shape_sanitized_fixture: parse_native_jsonl/project_native_events projection deleted.
- test_history_replay_does_not_repeat_initial: ingest_native_trace/TraceContext deleted.
- test_additional_read_is_a_new_event: ingest_native_trace tool-read auditing deleted.
- test_event_reimport_is_idempotent: ingest_native_trace re-import idempotency deleted.
- test_unknown_complete_text_is_upper_bound: trace-derived upper-bound events deleted.
- test_empty_unknown_result_upper_bound_zero: trace-derived upper-bound events deleted.
- test_missing_result_is_unverified_not_zero: trace-derived unverified/gap detection deleted.
- test_upper_bound_exceed_is_not_confirmed_overrun: trace-derived upper-bound occupancy deleted.
- test_known_source_over_cap_is_confirmed_overrun: ingest_native_trace deleted.
- test_failed_event_replay_idempotent: ingest_native_trace deleted.
- test_bound_shrink_keeps_event: shrink_unknown_event deleted.
- test_usage_reconcile_not_double_added: usage_from_native reconciliation deleted
  (the surviving usage_from_result assertions are kept in test_usage_from_result_keeps_original_field_names).
- test_invoke_llm_consumes_runtime_streams_and_formal_route: runtime-stream/route evidence collection deleted
  (collect_llm_artifacts now only persists cli stdout/stderr).
- test_status_line_without_route_does_not_forge_model: formal-route evidence and _actual_model_from_route deleted.
- test_codex_multi_block_and_function_output_and_no_double_item_completed: codex native trace ingest deleted.
- test_codex_second_read_counts_again_unread_path_is_zero_l: codex native trace ingest deleted.
- test_codex_bad_line_compaction_missing_result_wrong_bind: codex native trace ingest and NativeBindError deleted.
- test_read_name_is_not_packet_evidence_and_enoent_does_not_settle: codex packet-read evidence deleted.
- test_legal_jsonl_without_trailing_newline_is_not_truncated: parse_codex_native_jsonl deleted.
- test_unknown_event_msg_and_compaction_with_history: codex native trace ingest deleted.
- test_usage_conflict_is_unavailable_not_last_version: usage_from_codex deleted.
- test_verified_instruction_match_is_source_free_wrapper_still_u: InstructionResource matching deleted.
- test_filecontent_json_wrapper_matches_instruction_keeps_unknown_u: FileContent instruction matching deleted.
- test_filecontent_full_raw_matches_even_when_limit_in_args: FileContent instruction matching deleted.
- test_filecontent_reaudit_shrinks_existing_unknown_without_deleting_event: instruction re-audit deleted.
- test_filecontent_changed_hash_and_truncation_are_not_whole_exemptions: FileContent instruction matching deleted.
- test_filecontent_extra_text_only_deducts_verified_spans: FileContent instruction matching deleted.
- test_editsapplied_and_terminal_envelopes_stay_u_not_output_for_prompt: trace envelope auditing deleted.
- test_current_instruction_files_use_filecontent_shape_when_hash_stable: instruction resource matching deleted.
- test_chat_pair_replaces_envelope_once_not_double_count: native/chat pairing deleted.
- test_unknown_tool_uses_complete_chat_text: native/chat pairing deleted.
- test_session_mismatch_keeps_envelope: native/chat pairing deleted.
- test_duplicate_conflict_and_missing_result_are_unverified_or_fallback: pair_native_and_chat deleted.
- test_truncated_chat_binding_falls_back_to_envelope: chat binding audit deleted.
- test_compacted_tail_without_early_tools_is_unverified: chat compaction audit deleted.
- test_extra_synthetic_input_is_not_dropped: chat reinjection audit deleted.
- test_verified_host_block_hits_across_positions: host instruction block matching deleted.
- test_same_type_business_text_is_not_exempt: host instruction block matching deleted.
- test_enrolled_source_priority_over_instruction_resource: instruction resource matching deleted.
- test_no_chat_keeps_envelope_fallback: ingest_native_trace deleted.
- test_chat_numbered_instruction_match_on_selected_text: numbered instruction matching deleted.
- test_frozen_prompt_does_not_double_count_initial_source: frozen-prompt/chat audit deleted.

Renamed: test_codex_in_flight_reservation_allows_other_source_and_finite_u is kept as
test_in_flight_reservation_allows_other_source_and_finite_u (it never used codex ingest;
it exercises reservation occupancy and can_reserve, which survive).
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cbe.accounting import (
    COUNTED_KNOWN,
    COUNTED_NONE,
    COUNTED_RESERVE,
    COUNTED_UNVERIFIED,
    COUNTED_UPPER,
    DELIVERY_PACKET,
    PRESENTATION_AUDIT_NO_NATIVE,
    can_reserve,
    ensure_initial_exposure,
    estimate_tokens,
    finalize_not_sent_presentation,
    logical_exposure_status,
    occupancy_from_calls,
    overall_token_budget,
    remaining_chars,
    usage_from_result,
)
from cbe.models import CallRecord
from cbe.store import (
    BudgetError,
    LedgerStore,
    reconcile_call_delivery,
    reserve_call,
    set_budget_policy,
    show_budget_policy,
)


def _packet_read_record(call_id: str, packet_hash: str | None, chars: int) -> dict:
    extra = {
        "delivery": DELIVERY_PACKET,
        "packed_source_chars": chars,
        "reservation_chars": chars,
        "packet_hash": packet_hash,
    }
    return {
        "call_id": call_id,
        "task_id": "task:review:1",
        "input_hash": "h",
        "source_spans": [{"path": "pkg/mod.py", "start": 0, "end": chars}],
        "source_chars": 0,
        "state": "prepared",
        "delivery": DELIVERY_PACKET,
        "packet_hash": packet_hash,
        "source_exposures": [],
        "extra": extra,
    }


def test_language_estimators_are_not_mixed() -> None:
    assert estimate_tokens(3500, "python") == 1000
    assert estimate_tokens(4000, "typescript") == 1000
    assert estimate_tokens(3800, "javascript") == 1000


def test_replay_of_durable_raw_does_not_double_count() -> None:
    calls = {
        "a": {"state": "imported", "source_chars": 100},
    }
    assert remaining_chars(100, calls) == 100
    calls["a"]["state"] = "imported"
    ok, _ = can_reserve(100, calls, 100)
    assert ok


def test_unknown_sent_is_kept() -> None:
    calls = {"u": {"state": "uncertain", "source_chars": 50}}
    assert remaining_chars(50, calls) == 50


def test_concurrent_reserve_cannot_exceed_cap(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "run")
    ledger = {
        "schema": "cbe-semantic-ledger/1",
        "run_id": "t",
        "source_revision": "rev_test",
        "ledger_revision": -1,
        "inventory": {"s_chars": 20},
        "tasks": {},
        "details": {},
        "groups": {},
        "calls": {},
        "reviews": {},
        "budget": {"s_chars": 20},
    }
    store.create(ledger)
    errors: list[str] = []
    ok: list[str] = []

    def attempt(call_id: str) -> None:
        try:
            def mutate(current: dict) -> dict:
                reserve_call(
                    current,
                    CallRecord(
                        call_id=call_id,
                        task_id="t",
                        input_hash="h",
                        source_spans=[],
                        source_chars=30,
                        state="prepared",
                    ),
                )
                return current

            store.mutate(mutate)
            ok.append(call_id)
        except BudgetError as exc:
            errors.append(str(exc))

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(attempt, ["c1", "c2"]))
    assert len(ok) == 1
    assert errors
    ledger = store.open()
    assert len(ledger["calls"]) == 1


def test_usage_from_result_keeps_original_field_names() -> None:
    empty = usage_from_result(None)
    assert empty["provider_usage"] == "unavailable"
    named = usage_from_result({"usage": {"input_tokens": 3, "cache_read_input_tokens": 9}})
    assert named["provider_usage"]["cache_read_input_tokens"] == 9
    assert "cached_tokens" not in named


def test_overall_budget_counts_native_total_once_and_keeps_unknown_delivery() -> None:
    ledger = {
        "documentation_policy": {"source_tokens": 100, "tokenizer": "o200k_base"},
        "calls": {
            "positive": {"state": "imported", "extra": {"send_evidence": "sent_native"},
                         "usage": {"input_tokens": 150, "cached_input_tokens": 120,
                                   "output_tokens": 30, "reasoning_output_tokens": 12}},
            "unknown": {"state": "uncertain", "extra": {}, "usage": "unavailable"},
            "no_usage": {"state": "imported", "extra": {"send_evidence": "sent_native"},
                         "usage": "unavailable"},
            "prepared": {"state": "prepared", "extra": {}, "usage": None},
        },
    }
    report = overall_token_budget(ledger)
    assert report["known_total_tokens"] == 180
    assert report["cached_input_tokens"] == 120
    assert report["reasoning_output_tokens"] == 12
    assert report["unknown_delivery_call_ids"] == ["unknown"]
    assert report["unknown_usage_call_ids"] == ["no_usage"]
    assert report["unresolved_call_ids"] == ["no_usage", "unknown"]
    assert report["status"] == "measured_with_unknowns"
    ledger["calls"]["positive"]["usage"]["output_tokens"] = 60
    over = overall_token_budget(ledger)
    assert over["exceeds_reference_limit"] is True
    assert over["reference_limit_tokens"] == 200
    assert over["status"] == "measured_with_unknowns"


def test_module_first_reservation_no_total_gate_but_same_task_delivery_guard() -> None:
    ledger = {
        "documentation_policy": {"version": "module-first-v2", "source_tokens": 100},
        "inventory": {"s_chars": 1000},
        "calls": {
            "sent": {"call_id": "sent", "task_id": "other", "state": "imported",
                     "extra": {"send_evidence": "sent_native"},
                     "usage": {"input_tokens": 201, "output_tokens": 0}},
            "no_usage": {"call_id": "no_usage", "task_id": "other", "state": "imported",
                         "extra": {"send_evidence": "sent_native"}, "usage": "unavailable"},
        },
    }
    # Over the 2S reference and one unknown-usage call no longer block new claims.
    reserved = reserve_call(ledger, CallRecord("new", "task", "hash", [], 0, "prepared"))
    assert reserved.state == "prepared"
    assert "new" in ledger["calls"]
    ledger["calls"]["uncertain"] = {
        "call_id": "uncertain", "task_id": "task", "state": "uncertain", "extra": {},
    }
    with pytest.raises(BudgetError, match="unproven delivery"):
        reserve_call(ledger, CallRecord("again", "task", "hash", [], 0, "prepared"))
    assert "again" not in ledger["calls"]
    # A different task is not blocked by that uncertain call.
    ok = reserve_call(ledger, CallRecord("other-task", "task2", "hash", [], 0, "prepared"))
    assert ok.state == "prepared"
    # Explicit reconciliation with a recorded evidence search frees the guard.
    reconciled = reconcile_call_delivery(
        ledger, "uncertain", conclusion="no_delivery_evidence",
        searched=["run/raw/", "celery-receipts/", "run/provider/"],
    )
    assert reconciled.state == "released"
    assert reconciled.extra["disposition"] == "reconciled_no_delivery_evidence"
    assert reconciled.extra["reconciliation"]["searched"]
    after = reserve_call(ledger, CallRecord("now-ok", "task", "hash", [], 0, "prepared"))
    assert after.state == "prepared"
    report = overall_token_budget(ledger)
    assert "uncertain" not in report["unknown_delivery_call_ids"]
    # Positive evidence or wrong conclusion cannot be reconciled away.
    with pytest.raises(BudgetError, match="positive delivery evidence"):
        reconcile_call_delivery(ledger, "sent", conclusion="no_delivery_evidence", searched=["x"])
    with pytest.raises(ValueError, match="supported conclusion"):
        reconcile_call_delivery(ledger, "now-ok", conclusion="delivered_after_all", searched=["x"])


def test_resume_uncertain_and_prepared_still_occupy(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "run-occ")
    ledger = {
        "schema": "cbe-semantic-ledger/1",
        "run_id": "t",
        "source_revision": "rev_test",
        "ledger_revision": -1,
        "inventory": {"s_chars": 50},
        "tasks": {},
        "details": {},
        "groups": {},
        "calls": {},
        "reviews": {},
        "budget": {"s_chars": 50},
    }
    store.create(ledger)

    def add_uncertain(current: dict) -> dict:
        reserve_call(
            current,
            CallRecord(
                call_id="sent-unknown",
                task_id="t",
                input_hash="h",
                source_spans=[],
                source_chars=40,
                state="prepared",
            ),
        )
        from cbe.store import mark_call

        mark_call(current, "sent-unknown", state="uncertain")
        return current

    store.mutate(add_uncertain)
    opened = store.open()
    assert remaining_chars(50, opened["calls"]) == 60  # cap 100 - 40
    ok, _ = can_reserve(50, opened["calls"], 70)
    assert ok is False
    # A new call that fits after the uncertain reserve.
    ok2, _ = can_reserve(50, opened["calls"], 50)
    assert ok2 is True


def test_detail_prompt_does_not_duplicate_signature_source() -> None:
    from cbe.ir import CharSpan
    from cbe.packets import Packet
    from cbe.runner import build_detail_prompt

    packet = Packet(
        packet_id="p",
        path="mod.py",
        language="python",
        spans=(CharSpan(0, 12),),
        symbol_ids=("mod.py::function::ok::0",),
        parent_symbol_id=None,
        slice_index=0,
        slice_count=1,
        content_hash="h",
        source_chars=12,
    )
    source = "def ok():\n    return 1\n"
    prompt = json.loads(
        build_detail_prompt(
            packet=packet,
            source=source,
            symbols=[
                {
                    "id": "mod.py::function::ok::0",
                    "kind": "function",
                    "name": "ok",
                    "qualified_name": "ok",
                    "parent_id": None,
                    "span": {"start": 0, "end": 12},
                    "exclusive_spans": [{"start": 0, "end": 12}],
                    "signature": "def ok():",
                    "extra": {"body": source},
                }
            ],
            edges=[],
        )
    )
    assert prompt["source"] == source
    blob = json.dumps(prompt["symbols"])
    assert "def ok():" not in blob
    assert source not in blob
    assert prompt["source"].count("def ok") == 1
    names = [item["name"] for item in prompt["schema"]]
    assert names == ["symbol_id", "behavior", "inputs_outputs", "effects", "failures", "dependencies", "unresolved"]
    assert prompt["placeholder_example"]["details"][0]["symbol_id"] == "<copy supplied id>"
    assert "unique result file this CLI attempt injects" in prompt["result_file_rule"]
    assert "--result-file" not in json.dumps(prompt)
    assert prompt["resources"]["cbe_skill"].endswith("codebase-explorer/SKILL.md")
    assert prompt["resources"]["detail_reference"].endswith("references/detail.md")
    from cbe.runner import CLEAN_CONTEXT_PATH

    if CLEAN_CONTEXT_PATH:
        assert prompt["resources"]["clean_context"].endswith("clean-context/SKILL.md")
    else:
        assert "clean_context" not in prompt["resources"]


def test_in_flight_reservation_allows_other_source_and_finite_u() -> None:
    reserved = _packet_read_record("call-a", "h1", 10)
    ensure_initial_exposure(reserved)
    calls = {"call-a": reserved}
    occ = occupancy_from_calls(calls)
    assert occ["reserved_chars"] == 10
    assert occ["unbounded_source_gap"] is False
    ok, _ = can_reserve(20, calls, 10)
    assert ok is True
    upper_record = {
        "call_id": "u",
        "state": "imported",
        "source_chars": 0,
        "source_exposures": [
            {
                "event_id": "u1",
                "counted_as": COUNTED_UPPER,
                "source_chars": 5,
                "event_kind": "tool_read",
            }
        ],
        "extra": {"mocked": False},
    }
    ok2, _ = can_reserve(20, {"u": upper_record}, 10)
    assert ok2 is True


def test_released_sent_attempt_and_repeated_spans_still_consume_two_pass_budget() -> None:
    def sent(call_id: str, start: int, end: int, state: str = "imported") -> dict:
        record = {"call_id": call_id, "state": state, "source_chars": end - start,
                  "source_spans": [{"path": "service.py", "start": start, "end": end}],
                  "extra": {"send_evidence": "sent_http"}}
        ensure_initial_exposure(record)
        return record

    calls = {"a": sent("a", 0, 10), "b": sent("b", 5, 15),
             "retry": sent("retry", 0, 10, "released")}
    occupied = occupancy_from_calls(calls)
    assert occupied["known_source_chars"] == 30
    assert occupied["covered_source_chars"] == 15
    assert occupied["first_read_source_chars"] == 15
    assert occupied["repeated_source_chars"] == 15
    assert can_reserve(15, calls, 1)[0] is False


def test_is_not_sent_bootstrap_requires_predispatch_exception() -> None:
    from cbe.runner import is_not_sent_bootstrap

    yaml_fail = {
        "returncode": 1,
        "stderr": "Traceback (most recent call last):\nModuleNotFoundError: No module named 'yaml'\n",
        "protocol": {"start": {}, "route": None, "native_path": None},
    }
    assert is_not_sent_bootstrap(yaml_fail) is True
    empty_fail = {"returncode": 1, "protocol": {}}
    assert is_not_sent_bootstrap(empty_fail) is False
    reset_fail = {
        "returncode": 1,
        "stderr": "Connection reset after request sent",
        "protocol": {},
    }
    assert is_not_sent_bootstrap(reset_fail) is False
    started = {
        "returncode": 1,
        "stderr": "ModuleNotFoundError: No module named 'yaml'",
        "protocol": {"start": {"task": "llm_cli_grok_x", "line": "llm: START ..."}},
    }
    assert is_not_sent_bootstrap(started) is False


def test_single_reservation_hash_update_and_historical_merge() -> None:
    record = _packet_read_record("call-review-1", None, 72)
    record["packet_hash"] = None
    record["extra"]["packet_hash"] = None
    ensure_initial_exposure(record)
    reservations = [item for item in record["source_exposures"] if item["event_kind"] == "reservation"]
    assert len(reservations) == 1
    assert reservations[0]["event_id"] == "call-review-1:reservation:packet"
    record["packet_hash"] = "abc123"
    record["extra"]["packet_hash"] = "abc123"
    ensure_initial_exposure(record)
    reservations = [item for item in record["source_exposures"] if item["event_kind"] == "reservation"]
    assert len(reservations) == 1
    assert reservations[0]["packet_hash"] == "abc123"
    record["source_exposures"].append(
        {
            "event_id": "call-review-1:reservation:abc123",
            "event_kind": "reservation",
            "source_chars": 72,
            "counted_as": COUNTED_RESERVE,
            "packet_hash": "abc123",
        }
    )
    ensure_initial_exposure(record)
    occ = occupancy_from_calls({"c": record})
    assert occ["reserved_chars"] == 72


def test_source0_allowed_when_occupancy_exceeds_cap_or_unbounded() -> None:
    heavy = {
        "call_id": "h",
        "state": "imported",
        "source_chars": 0,
        "source_exposures": [
            {"event_id": "k", "counted_as": COUNTED_KNOWN, "source_chars": 400, "event_kind": "initial"}
        ],
        "extra": {"mocked": False, "unbounded_source_gap": True},
    }
    ok, reason = can_reserve(50, {"h": heavy}, 0)
    assert ok is True
    assert "source_chars=0" in reason
    ok_src, _ = can_reserve(50, {"h": heavy}, 10)
    assert ok_src is False


def test_bootstrap_demotes_incorrect_known_initial() -> None:
    from cbe.accounting import promote_initial_for_state

    record = {
        "call_id": "c",
        "state": "durable",
        "source_chars": 6370,
        "source_exposures": [
            {
                "event_id": "c:initial",
                "event_kind": "initial",
                "source_chars": 6370,
                "counted_as": COUNTED_KNOWN,
            }
        ],
        "extra": {"send_evidence": "not_sent_bootstrap", "disposition": "bootstrap_failed"},
    }
    promote_initial_for_state(record)
    assert record["source_exposures"][0]["counted_as"] == COUNTED_NONE
    occ = occupancy_from_calls({"c": record})
    assert occ["known_source_chars"] == 0
    assert occ["reserved_chars"] == 0


def test_placeholder_example_is_accepted_by_existing_parser() -> None:
    from cbe.store import parse_detail_item

    item = {
        "symbol_id": "mod.py::function::ok::0",
        "behavior": "returns one from the exclusive interval",
        "inputs_outputs": [],
        "effects": [],
        "failures": [],
        "dependencies": [],
        "unresolved": [],
    }
    record, error = parse_detail_item(item, expected_ids={"mod.py::function::ok::0"})
    assert error is None
    assert record is not None
    assert record.behavior.startswith("returns one")


def test_not_sent_leftover_unverified_flag_and_unknown_send_negative() -> None:
    leftover = {
        "call_id": "old",
        "state": "durable",
        "source_chars": 100,
        "exposure_evidence": "unverified",
        "source_exposures": [
            {
                "event_id": "old:initial",
                "event_kind": "initial",
                "counted_as": COUNTED_NONE,
                "source_chars": 100,
                "reason": "released_unconsumed_not_sent",
            }
        ],
        "extra": {
            "send_evidence": "not_sent_bootstrap",
            "disposition": "bootstrap_failed",
            "reconcile_basis": "cli_predispatch_bootstrap_exception_and_terminated",
        },
    }
    new_call = {
        "call_id": "new",
        "state": "imported",
        "exposure_evidence": "complete",
        "source_exposures": [
            {
                "event_id": "new:initial",
                "event_kind": "initial",
                "counted_as": COUNTED_KNOWN,
                "source_chars": 10,
            },
            {
                "event_id": "new:u",
                "event_kind": "tool_read",
                "counted_as": COUNTED_UPPER,
                "source_chars": 50,
                "reason": "unknown_complete_text",
            },
        ],
        "extra": {"send_evidence": "presented"},
    }
    occ = occupancy_from_calls({"old": leftover, "new": new_call})
    assert occ["evidence_completeness"] == "unverified"
    assert logical_exposure_status(100, occ) == "unverified"
    finalize_not_sent_presentation(leftover)
    assert leftover["exposure_evidence"] == "complete"
    assert leftover["extra"]["presentation_audit"] == PRESENTATION_AUDIT_NO_NATIVE
    occ2 = occupancy_from_calls({"old": leftover, "new": new_call})
    assert occ2["evidence_completeness"] == "complete"
    assert occ2["known_source_chars"] == 10
    assert occ2["possible_source_upper_chars"] == 50
    assert logical_exposure_status(100, occ2) == "within_upper_bound"

    unknown = {
        "call_id": "u",
        "state": "durable",
        "exposure_evidence": "unverified",
        "source_exposures": [
            {
                "event_id": "u:initial",
                "event_kind": "initial",
                "counted_as": COUNTED_RESERVE,
                "source_chars": 10,
            }
        ],
        "extra": {"send_evidence": "unknown"},
    }
    finalize_not_sent_presentation(unknown)
    assert unknown["exposure_evidence"] == "unverified"
    assert occupancy_from_calls({"u": unknown})["evidence_completeness"] == "unverified"

    missing = {
        "call_id": "m",
        "state": "imported",
        "exposure_evidence": "unverified",
        "source_exposures": [
            {
                "event_id": "m:missing",
                "counted_as": COUNTED_UNVERIFIED,
                "reason": "tool_use_without_result",
                "source_chars": 0,
            }
        ],
        "extra": {"send_evidence": "not_sent_bootstrap"},
    }
    finalize_not_sent_presentation(missing)
    assert missing.get("extra", {}).get("presentation_audit") != PRESENTATION_AUDIT_NO_NATIVE
    assert occupancy_from_calls({"m": missing})["evidence_completeness"] == "unverified"


def _budget_run(tmp_path: Path) -> Path:
    store = LedgerStore(tmp_path / "run")
    ledger = {
        "schema": "cbe-semantic-ledger/1",
        "run_id": "t",
        "source_revision": "rev_test",
        "ledger_revision": -1,
        "inventory": {"s_chars": 20},
        "tasks": {},
        "details": {},
        "groups": {},
        "calls": {},
        "reviews": {},
        "budget": {"s_chars": 20},
    }
    store.create(ledger)
    return tmp_path / "run"


def _reserve_call(current: dict, call_id: str, chars: int) -> None:
    reserve_call(
        current,
        CallRecord(
            call_id=call_id,
            task_id="t",
            input_hash="h",
            source_spans=[],
            source_chars=chars,
            state="prepared",
        ),
    )


def test_dispatch_policy_cannot_relax_hard_two_pass_cap(tmp_path: Path) -> None:
    run = _budget_run(tmp_path)
    store = LedgerStore(run)

    def over_default_cap() -> None:
        store.mutate(lambda cur: (_reserve_call(cur, "c_default", 50), cur)[1])

    with pytest.raises(BudgetError) as excinfo:
        over_default_cap()
    assert "source-exposure budget exceeded" in str(excinfo.value)
    assert "dispatch_multiplier=2" in str(excinfo.value)

    with pytest.raises(Exception, match="out of range"):
        set_budget_policy(run, multiplier=3.0,
            reason="Older relaxation is superseded by the hard two-pass rule", set_by="t-owner")
    set_budget_policy(run, multiplier=2.0,
        reason="Keep the strict source ceiling for this run", set_by="t-owner")
    ledger = store.open()
    assert ledger["budget"]["cap_chars"] == 40
    assert ledger["budget"]["dispatch_cap_chars"] == 40
    assert ledger["budget"]["dispatch_cap_multiplier"] == 2.0


def test_budget_policy_verb_records_provenance_and_requires_reason(tmp_path: Path) -> None:
    run = _budget_run(tmp_path)

    with pytest.raises(Exception, match=">= 20 chars"):
        set_budget_policy(run, multiplier=1.5, reason="too short")
    with pytest.raises(Exception, match="out of range"):
        set_budget_policy(run, multiplier=9.0, reason="invalid multiplier needs an explicit on-record reason")

    policy = set_budget_policy(
        run,
        multiplier=1.5,
        reason="Tighten the reading cap for this particular frozen run",
        set_by="t-owner",
    )
    assert policy["source_read_cap_multiplier"] == 1.5
    assert policy["set_by"] == "t-owner"
    assert len(policy["history"]) == 1
    assert policy["history"][0]["source_read_cap_multiplier"] == 1.5

    shown = show_budget_policy(run)
    assert shown["source_read_cap_multiplier"] == 1.5
    assert shown["history"] == policy["history"]

    fresh = _budget_run(tmp_path / "other")
    assert show_budget_policy(fresh)["history"] == []
