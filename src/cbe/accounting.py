"""Logical source-exposure accounting (mechanical counting).

The historical source-presentation counter reserves a packet at claim and
reconciles delivery evidence. It remains useful for source provenance and is
the reading budget the user kept ("read the source at most about twice").

A call is one production attempt. Total native model usage is measured and
reported per call with original field names; the 2*source_tokens line is an
informational reference, not an admission gate. Unknown usage (delivery
proven, cost missing) and unknown delivery (resend-protected) stay separate
facts. Native input includes cached input; reasoning output is part of output.
"""

from __future__ import annotations

import hashlib
from typing import Any

CHARS_PER_TOKEN = {
    "python": 3.5,
    "typescript": 4.0,
    "javascript": 3.8,
}

USAGE_INT_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)
DELIVERY_INLINE = "inline_initial"
DELIVERY_PACKET = "packet_read"

COUNTED_KNOWN = "known_source"
COUNTED_UPPER = "possible_source"
COUNTED_RESERVE = "reserve"
COUNTED_NONE = "not_source"
COUNTED_UNVERIFIED = "unverified"
PRESENTATION_AUDIT_NO_NATIVE = "no_model_source_presentation"


def estimate_tokens(char_count: int, language: str) -> int:
    if char_count < 0:
        char_count = 0
    ratio = CHARS_PER_TOKEN.get(language.lower(), 3.8)
    return int(char_count / ratio) if ratio else 0


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def initial_event_id(call_id: str) -> str:
    return f"{call_id}:initial"


def reservation_event_id(call_id: str, packet_hash: str | None = None) -> str:
    # One planned packet reservation per call. Hash updates the same event; it is not an id key.
    return f"{call_id}:reservation:packet"


def delivery_of(record: dict[str, Any]) -> str:
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    value = record.get("delivery") or extra.get("delivery") or DELIVERY_INLINE
    return str(value)


def copy_usage_fields(payload: Any) -> dict[str, Any] | str:
    """Keep original usage keys. Do not invent net-input or billing aliases."""
    if not isinstance(payload, dict):
        return "unavailable"
    copied: dict[str, Any] = {}
    for key, value in payload.items():
        copied[key] = value
    return copied if copied else "unavailable"


def delivery_evidence_is_positive(call: dict[str, Any]) -> bool:
    """True when the call record itself proves the prompt reached a model.

    Positive evidence is a native/http delivery marker (``send_evidence``) or a
    bound native path/receipt on a completed state. Absence means delivery is
    unknown, which is a different fact from missing usage.
    """
    extra = call.get("extra") if isinstance(call.get("extra"), dict) else {}
    send = str(extra.get("send_evidence") or "")
    if send in {"sent_native", "sent_http", "presented"}:
        return True
    state = str(call.get("state") or "")
    if state in {"sent", "imported", "durable"} and (
        call.get("native_path") or extra.get("delivery_receipt")
    ):
        return True
    return False


def possibly_sent(call: dict[str, Any]) -> bool:
    """Whether the call may have reached a model at all (cost possible)."""
    state = str(call.get("state") or "")
    extra = call.get("extra") if isinstance(call.get("extra"), dict) else {}
    send = str(extra.get("send_evidence") or "")
    positively_sent = send in {"sent_native", "sent_http", "presented"}
    if state in {"prepared", "released"} and not positively_sent:
        return False
    if send in {"not_sent_bootstrap", "bootstrap_failed"}:
        return False
    return positively_sent or state in {
        "sent", "imported", "durable", "uncertain",
    }


def overall_token_budget(ledger: dict[str, Any]) -> dict[str, Any]:
    """Summarize proven model usage and unresolved facts in the same ledger.

    Measurement report, not an admission gate. Three facts stay separate:
    proven native usage, delivery-proven calls whose usage is missing
    (``unknown_usage_call_ids``; cost unknown, never zero), and calls whose
    delivery itself is unproven (``unknown_delivery_call_ids``; the task is
    protected from resend). The 2*source_tokens line is kept as a reference
    (``exceeds_reference_limit``), not an admission rule; the half-source
    publication gate is enforced elsewhere. Prepared calls have no model cost.
    Native totals take precedence. Cache inclusion follows the host contract;
    DSH and Claude cache counters are additional input, Codex cache is a subset.
    """

    policy = ledger.get("documentation_policy") or {}
    source_tokens = policy.get("source_tokens")
    limit = 2 * int(source_tokens) if type(source_tokens) is int and source_tokens > 0 else None
    totals = {key: 0 for key in (
        "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens",
    )}
    proven: list[str] = []
    unknown_usage: list[str] = []
    unknown_delivery: list[str] = []
    gross = 0
    partial_usage: list[str] = []
    counter_observed = {key: False for key in totals}
    counter_missing = {key: [] for key in totals}
    calls = dict(ledger.get("calls") or {})
    for iid, invocation in (ledger.get("native_invocations") or {}).items():
        calls[iid] = {"state": "imported" if invocation.get("delivery_proven") else "prepared",
                      "extra": {"send_evidence": "sent_native" if invocation.get("delivery_proven") else None,
                                "delivery_evidence": "host_tool_result" if invocation.get("evidence") else "controller_attested"},
                      "usage": invocation.get("usage", "unavailable")}
    for call_id, call in sorted(calls.items()):
        iid = ((call.get("extra") or {}).get("native_handoff") or {}).get("invocation_id")
        if iid:
            if iid not in ledger.get("native_invocations", {}):
                unknown_delivery.append(call_id)
            continue
        if not possibly_sent(call):
            continue
        if not delivery_evidence_is_positive(call):
            unknown_delivery.append(call_id)
            continue
        usage = call.get("usage")
        if not isinstance(usage, dict):
            unknown_usage.append(call_id)
            continue
        complete_io = not any(
            type(usage.get(key)) is not int or usage[key] < 0
            for key in ("input_tokens", "output_tokens")
        )
        native_total = usage.get("total_tokens")
        if type(native_total) is int and native_total >= 0:
            gross += native_total
            if not complete_io:
                partial_usage.append(call_id)
        elif complete_io:
            subtotal = usage["input_tokens"] + usage["output_tokens"]
            if usage.get("cache_included_in_input") is False:
                # Missing cache counters make the aggregate unknown rather
                # than implicitly zero. Keep known input/output in the report.
                if type(usage.get("cached_input_tokens")) is not int:
                    unknown_usage.append(call_id)
                    continue
                subtotal += usage["cached_input_tokens"]
                creation = usage.get("cache_creation_input_tokens")
                if type(creation) is int:
                    subtotal += creation
            gross += subtotal
        else:
            unknown_usage.append(call_id)
            continue
        proven.append(call_id)
        for key in totals:
            value = usage.get(key)
            if type(value) is int and value >= 0:
                totals[key] += value
                counter_observed[key] = True
            else:
                counter_missing[key].append(call_id)
    unknowns = unknown_usage or unknown_delivery
    return {
        "tokenizer": policy.get("tokenizer"),
        "source_tokens": source_tokens,
        "reference_limit_tokens": limit,
        "known_input_tokens": totals["input_tokens"] if counter_observed["input_tokens"] else None,
        "cached_input_tokens": totals["cached_input_tokens"] if counter_observed["cached_input_tokens"] else None,
        "known_output_tokens": totals["output_tokens"] if counter_observed["output_tokens"] else None,
        "reasoning_output_tokens": totals["reasoning_output_tokens"] if counter_observed["reasoning_output_tokens"] else None,
        "known_total_tokens": gross,
        "partial_usage_call_ids": partial_usage,
        "parent_usage": "unavailable",
        "scope": "child_calls_only; parent/controller usage is not collected",
        "unavailable_counter_call_ids": counter_missing,
        "reference_headroom_tokens": limit - gross if limit is not None else None,
        "exceeds_reference_limit": limit is not None and gross > limit,
        "proven_call_count": len(proven),
        "unknown_usage_call_ids": unknown_usage,
        "unknown_delivery_call_ids": unknown_delivery,
        "unresolved_call_ids": unknown_usage + unknown_delivery,
        "status": (
            "unavailable_source_denominator" if limit is None
            else "measured_with_unknowns" if unknowns
            else "measured"
        ),
    }


def usage_from_result(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extract provider usage with original names only. Missing usage is unavailable."""
    if not isinstance(payload, dict):
        return {"provider_usage": "unavailable"}
    usage = payload.get("usage")
    if isinstance(usage, dict):
        out: dict[str, Any] = {
            "provider_usage": copy_usage_fields(usage),
        }
        for key in ("num_turns", "modelUsage", "total_cost_usd", "model"):
            if key in payload:
                out[key] = payload.get(key)
        return out
    return {"provider_usage": "unavailable"}


def _send_evidence_of(record: dict[str, Any]) -> str:
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    value = extra.get("send_evidence") or extra.get("disposition") or ""
    return str(value)


def _is_mock_record(record: dict[str, Any]) -> bool:
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    if extra.get("mocked") is True:
        return True
    if record.get("actual_model") == "mock":
        return True
    return False


def ensure_initial_exposure(record: dict[str, Any]) -> dict[str, Any]:
    call_id = str(record.get("call_id") or "")
    exposures = list(record.get("source_exposures") or [])
    event_id = initial_event_id(call_id)
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    delivery = delivery_of(record)
    packet_hash = record.get("packet_hash") or extra.get("packet_hash")
    if delivery == DELIVERY_PACKET:
        if not any(item.get("event_id") == event_id for item in exposures):
            exposures.append(
                {
                    "event_id": event_id,
                    "role_session_id": record.get("role_session_id") or call_id,
                    "event_kind": "initial",
                    "evidence_ref": "packet_path_only",
                    "source_spans": [],
                    "source_chars": 0,
                    "counted_as": COUNTED_NONE,
                    "delivery": DELIVERY_PACKET,
                    "reason": "packet_read_initial_is_path_only",
                }
            )
        res_chars = int(extra.get("reservation_chars") or extra.get("packed_source_chars") or 0)
        spans = list(record.get("source_spans") or extra.get("source_spans") or [])
        rid = reservation_event_id(call_id, packet_hash)
        existing_reservations = [
            item
            for item in exposures
            if item.get("event_kind") == "reservation"
            and str(item.get("event_id") or "").startswith(f"{call_id}:reservation:")
        ]
        if res_chars > 0:
            if existing_reservations:
                primary = existing_reservations[0]
                if primary.get("event_id") != rid:
                    primary["merged_from_event_id"] = primary.get("event_id")
                    primary["event_id"] = rid
                if packet_hash:
                    primary["packet_hash"] = packet_hash
                    primary["evidence_ref"] = f"packet:{packet_hash}"
                primary["reservation_id"] = rid
                if primary.get("counted_as") == COUNTED_RESERVE:
                    primary["source_chars"] = res_chars
                    primary["source_spans"] = spans or primary.get("source_spans") or []
                for extra_res in existing_reservations[1:]:
                    if extra_res.get("counted_as") == COUNTED_RESERVE:
                        extra_res["counted_as"] = COUNTED_NONE
                        extra_res["reason"] = "historical_duplicate_reservation_merged"
                        extra_res["merged_into"] = rid
            else:
                exposures.append(
                    {
                        "event_id": rid,
                        "role_session_id": record.get("role_session_id") or call_id,
                        "event_kind": "reservation",
                        "evidence_ref": f"packet:{packet_hash}",
                        "source_spans": spans,
                        "source_chars": res_chars,
                        "counted_as": COUNTED_RESERVE,
                        "packet_hash": packet_hash,
                        "reservation_id": rid,
                        "reason": "packet_read_planned_source",
                    }
                )
        record["source_exposures"] = exposures
        record["delivery"] = DELIVERY_PACKET
        return record
    if any(item.get("event_id") == event_id for item in exposures):
        record["source_exposures"] = exposures
        return record
    chars = int(record.get("source_chars") or 0)
    spans = list(record.get("source_spans") or [])
    if chars <= 0 and not spans:
        record["source_exposures"] = exposures
        return record
    state = record.get("state") or "prepared"
    send = _send_evidence_of(record)
    counted = COUNTED_RESERVE
    if (state == "released" and not delivery_evidence_is_positive(record)) or send in {"not_sent_bootstrap", "bootstrap_failed"}:
        counted = COUNTED_NONE
    elif _is_mock_record(record) and state in {"durable", "imported"}:
        counted = COUNTED_KNOWN
    elif send in {"presented", "sent_native", "sent_http"} and state in {"durable", "imported", "sent", "released"}:
        counted = COUNTED_KNOWN
    exposures.append(
        {
            "event_id": event_id,
            "role_session_id": record.get("role_session_id") or call_id,
            "event_kind": "initial",
            "evidence_ref": "prompt_injection",
            "source_spans": spans,
            "source_chars": chars,
            "counted_as": counted,
            "delivery": DELIVERY_INLINE,
        }
    )
    record["source_exposures"] = exposures
    record.setdefault("delivery", DELIVERY_INLINE)
    return record


def promote_initial_for_state(record: dict[str, Any]) -> dict[str, Any]:
    ensure_initial_exposure(record)
    state = record.get("state")
    event_id = initial_event_id(str(record.get("call_id") or ""))
    exposures = list(record.get("source_exposures") or [])
    delivery = delivery_of(record)
    send = _send_evidence_of(record)
    mocked = _is_mock_record(record)
    for item in exposures:
        kind = item.get("event_kind")
        if kind == "reservation":
            if (state == "released" and not delivery_evidence_is_positive(record)) or send in {"not_sent_bootstrap", "bootstrap_failed"}:
                item["counted_as"] = COUNTED_NONE
                item["reason"] = "released_unconsumed_not_sent"
            continue
        if item.get("event_id") != event_id:
            continue
        if delivery == DELIVERY_PACKET:
            item["counted_as"] = COUNTED_NONE
            item["source_chars"] = 0
            continue
        current = item.get("counted_as")
        if (state == "released" and not delivery_evidence_is_positive(record)) or send in {"not_sent_bootstrap", "bootstrap_failed"}:
            item["counted_as"] = COUNTED_NONE
            item["reason"] = item.get("reason") or "released_unconsumed_not_sent"
            continue
        if current == COUNTED_KNOWN:
            continue
        elif mocked and state in {"durable", "imported"} and current == COUNTED_RESERVE:
            item["counted_as"] = COUNTED_KNOWN
        elif send in {"presented", "sent_native", "sent_http"} and current == COUNTED_RESERVE:
            item["counted_as"] = COUNTED_KNOWN
        elif state in {"prepared", "sent", "uncertain"} and current not in {COUNTED_KNOWN, COUNTED_UPPER}:
            item["counted_as"] = COUNTED_RESERVE
        # durable/imported without send evidence keeps the reserve; never invent L.
    record["source_exposures"] = exposures
    return record


_GAP_TOKENS = (
    "missing",
    "incomplete",
    "truncat",
    "compacted_without",
    "bad_line",
    "unpaired",
    "encrypted",
    "unsupported_content",
)


def _reason_is_unbounded_gap(reason: str | None) -> bool:
    text = str(reason or "")
    return any(token in text for token in _GAP_TOKENS)


def presentation_events_are_finite(record: dict[str, Any]) -> bool:
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    if extra.get("unbounded_source_gap"):
        return False
    for item in record.get("source_exposures") or []:
        if item.get("counted_as") == COUNTED_UNVERIFIED:
            return False
        if _reason_is_unbounded_gap(item.get("reason")):
            return False
    return True


def finalize_not_sent_presentation(record: dict[str, Any]) -> dict[str, Any]:
    """Completeness for a classified predispatch not-sent attempt.

    Requires send_evidence already classified as not_sent_bootstrap/bootstrap_failed and
    every presentation event finite.
    """
    send = _send_evidence_of(record)
    if send not in {"not_sent_bootstrap", "bootstrap_failed"}:
        return record
    if not presentation_events_are_finite(record):
        return record
    extra = dict(record.get("extra") or {})
    extra["presentation_audit"] = PRESENTATION_AUDIT_NO_NATIVE
    extra["exposure_evidence_basis"] = "predispatch_terminated"
    record["extra"] = extra
    record["exposure_evidence"] = "complete"
    return record


def occupancy_from_calls(calls: dict[str, dict[str, Any]]) -> dict[str, Any]:
    known = 0
    upper = 0
    reserved = 0
    unknown_ids: list[str] = []
    unverified_ids: list[str] = []
    gap_ids: list[str] = []
    evidence = "complete"
    unbounded = False
    reservation_max: dict[str, int] = {}
    first_seen: dict[str, list[tuple[int, int]]] = {}
    first_read = 0
    repeated_read = 0
    covered: dict[str, list[tuple[int, int]]] = {}
    for record in calls.values():
        state = record.get("state")
        if state == "released" and not delivery_evidence_is_positive(record):
            continue
        extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
        mocked = _is_mock_record(record)
        call_id = str(record.get("call_id") or "")
        if record.get("exposure_evidence") == "unverified":
            if extra.get("presentation_audit") != PRESENTATION_AUDIT_NO_NATIVE:
                evidence = "unverified"
        if extra.get("unbounded_source_gap") and not mocked:
            unbounded = True
        exposures = record.get("source_exposures")
        if not exposures:
            chars = int(record.get("source_chars") or 0)
            send = _send_evidence_of(record)
            if send in {"not_sent_bootstrap", "bootstrap_failed"}:
                continue
            if state in {"prepared", "sent", "uncertain"}:
                reserved += chars
            elif state in {"durable", "imported"}:
                if mocked or send in {"presented", "sent_native"}:
                    known += chars
                else:
                    reserved += chars
            continue
        for item in exposures:
            counted = item.get("counted_as")
            chars = int(item.get("source_chars") or 0)
            event_id = str(item.get("event_id") or "")
            if counted == COUNTED_KNOWN:
                for span in item.get("source_spans") or []:
                    path = span.get("path")
                    start, end = span.get("start"), span.get("end")
                    if not isinstance(path, str) or type(start) is not int or type(end) is not int or end <= start:
                        continue
                    previous = first_seen.setdefault(path, [])
                    fresh = end - start
                    for old_start, old_end in _merged_intervals(previous):
                        fresh -= max(0, min(end, old_end) - max(start, old_start))
                    fresh = max(0, fresh)
                    first_read += fresh
                    repeated_read += end - start - fresh
                    previous.append((start, end))
                    covered.setdefault(path, []).append((start, end))
            if counted == COUNTED_UNVERIFIED:
                evidence = "unverified"
                if event_id:
                    unverified_ids.append(event_id)
                if not mocked and _reason_is_unbounded_gap(item.get("reason")):
                    unbounded = True
                    if event_id:
                        gap_ids.append(event_id)
                continue
            if counted == COUNTED_RESERVE:
                if item.get("event_kind") == "reservation":
                    reservation_max[call_id] = max(reservation_max.get(call_id, 0), chars)
                else:
                    reserved += chars
                continue
            if item.get("dual_occupancy"):
                known_part = int(item.get("occupancy_known_chars") or 0)
                upper_part = int(item.get("occupancy_upper_chars") or 0)
                known += known_part
                upper += upper_part
                if upper_part > 0 and event_id:
                    unknown_ids.append(event_id)
                continue
            if counted == COUNTED_KNOWN:
                known += chars
            elif counted == COUNTED_UPPER:
                upper += chars
                if event_id:
                    unknown_ids.append(event_id)
            elif counted in {COUNTED_NONE, None}:
                continue
            else:
                evidence = "unverified"
                if event_id:
                    unverified_ids.append(event_id)
    reserved += sum(reservation_max.values())
    return {
        "known_source_chars": known,
        "possible_source_upper_chars": upper,
        "exposure_upper_chars": known + upper,
        "reserved_chars": reserved,
        "occupancy_chars": known + upper + reserved,
        "unknown_span_event_ids": unknown_ids,
        "unverified_event_ids": unverified_ids,
        "unbounded_source_gap": unbounded,
        "unbounded_gap_event_ids": gap_ids,
        "evidence_completeness": evidence,
        "first_read_source_chars": first_read,
        "repeated_source_chars": repeated_read,
        "covered_source_chars": sum(
            sum(end - start for start, end in _merged_intervals(spans))
            for spans in covered.values()
        ),
    }


def _merged_intervals(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def spent_source_chars(calls: dict[str, dict[str, Any]]) -> int:
    """Occupancy against 2S: known + bounded-unknown + active reserves."""
    return int(occupancy_from_calls(calls)["occupancy_chars"])


def remaining_chars(s_chars: int, calls: dict[str, Any]) -> int:
    cap = 2 * max(0, s_chars)
    return cap - spent_source_chars(calls)


def logical_exposure_status(s_chars: int, occupancy: dict[str, Any]) -> str:
    cap = 2 * max(0, s_chars)
    known = int(occupancy.get("known_source_chars") or 0)
    used = int(occupancy.get("occupancy_chars") or 0)
    if known > cap:
        return "confirmed_overrun"
    if occupancy.get("evidence_completeness") == "unverified":
        return "unverified"
    if used <= cap:
        return "within_upper_bound"
    return "upper_bound_insufficient"


def can_reserve(s_chars: int, calls: dict[str, dict[str, Any]], needed: int,
                *, cap_multiplier: float | None = None,
                strict: bool = True) -> tuple[bool, str]:
    """Report new source dispatch against the run's reading ceiling.

    Strict compatibility runs still enforce a ceiling; native report runs
    retain the measurement and can proceed with a justified extra read.
    """
    occ = occupancy_from_calls(calls)
    multiplier = (
        float(cap_multiplier) if isinstance(cap_multiplier, (int, float)) and cap_multiplier > 0
        else 2.0
    )
    multiplier = min(multiplier, 2.0)
    cap = int(multiplier * max(0, s_chars))
    left = cap - int(occ["occupancy_chars"])
    status = logical_exposure_status(s_chars, occ)
    detail = (
        f"remaining={left} needed={needed} cap={cap} "
        f"dispatch_multiplier={multiplier:g} "
        f"known={occ['known_source_chars']} upper={occ['possible_source_upper_chars']} "
        f"reserved={occ['reserved_chars']} status={status} "
        f"unbounded_source_gap={occ.get('unbounded_source_gap')}"
    )
    if needed <= 0:
        return True, f"source_chars=0 work proceeds even if occupancy exceeds cap or a gap is open; {detail}"
    if not strict:
        return True, f"source reading guidance only; {detail}"
    if occ.get("unbounded_source_gap"):
        return False, f"unbounded_source_gap: cannot dispatch new source until a finite bound exists; {detail}"
    if needed <= left:
        return True, detail
    return False, f"source-exposure budget exceeded: {detail} S_chars={s_chars}"


def sync_budget(ledger: dict[str, Any]) -> dict[str, Any]:
    calls = ledger.get("calls") or {}
    s_chars = int((ledger.get("inventory") or {}).get("s_chars") or 0)
    occ = occupancy_from_calls(calls)
    status = logical_exposure_status(s_chars, occ)
    budget = ledger.setdefault("budget", {})
    budget["s_chars"] = s_chars
    budget["known_source_chars"] = occ["known_source_chars"]
    budget["possible_source_upper_chars"] = occ["possible_source_upper_chars"]
    budget["exposure_upper_chars"] = occ["exposure_upper_chars"]
    budget["reserved_chars"] = occ["reserved_chars"]
    budget["source_exposure_chars"] = occ["occupancy_chars"]
    budget["first_read_source_chars"] = occ["first_read_source_chars"]
    budget["repeated_source_chars"] = occ["repeated_source_chars"]
    budget["covered_source_chars"] = occ["covered_source_chars"]
    # Occupancy alias so older status readers do not see a silent zero.
    budget["source_read_chars"] = occ["occupancy_chars"]
    budget["source_read_chars_meaning"] = "occupancy alias of source_exposure_chars (L+U+reserve)"
    budget["unknown_span_event_ids"] = occ["unknown_span_event_ids"]
    budget["unverified_event_ids"] = occ["unverified_event_ids"]
    budget["unbounded_source_gap"] = occ.get("unbounded_source_gap")
    budget["unbounded_gap_event_ids"] = occ.get("unbounded_gap_event_ids") or []
    if not calls:
        budget["evidence_completeness"] = "run_packets"
        budget["budget_evidence"] = "run_packets"
        budget["logical_exposure_status"] = "within_upper_bound"
    else:
        budget["evidence_completeness"] = occ["evidence_completeness"]
        budget["budget_evidence"] = occ["evidence_completeness"]
        budget["logical_exposure_status"] = status
    budget["provider_source_input_chars"] = None
    # Reference line (never redefined by a relaxed dispatch multiplier): the
    # reading preference the final accounting always reports against.
    budget["cap_chars"] = 2 * s_chars
    policy = ledger.get("budget_policy") or {}
    raw_multiplier = policy.get("source_read_cap_multiplier")
    multiplier = (
        float(raw_multiplier) if isinstance(raw_multiplier, (int, float)) and raw_multiplier > 0
        else 2.0
    )
    budget["dispatch_cap_multiplier"] = min(multiplier, 2.0)
    budget["dispatch_cap_chars"] = int(min(multiplier, 2.0) * max(0, s_chars))
    return budget


def _release_matching_reservation(
    exposures: list[dict[str, Any]],
    *,
    packet_hash: str | None,
    call_id: str,
) -> None:
    rid = reservation_event_id(call_id, packet_hash)
    prefix = f"{call_id}:reservation:"
    for item in exposures:
        if item.get("event_kind") != "reservation":
            continue
        event_id = str(item.get("event_id") or "")
        if event_id == rid or event_id.startswith(prefix) or (packet_hash and item.get("packet_hash") == packet_hash):
            if item.get("counted_as") == COUNTED_RESERVE:
                item["counted_as"] = COUNTED_NONE
                item["reason"] = "reservation_settled_by_tool_read"
