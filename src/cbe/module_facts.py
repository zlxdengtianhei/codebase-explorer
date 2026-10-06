"""Source-partitioned, recoverable short facts for module-first runs.

The existing ledger owns fact tasks, calls, drafts and reviews. Packet files are
immutable inputs; a claim prepares a packet but does not assert model delivery.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import statistics
import uuid
from bisect import bisect_right
from datetime import timedelta
from pathlib import Path
from typing import Any

from cbe.accounting import can_reserve, copy_usage_fields
from cbe.inventory import Inventory
from cbe.callable_contracts import contracts_for, prompt_contract, behavior_token_recommendation
from cbe.ir import CharSpan, line_starts
from cbe.models import CallRecord, TaskRecord
from cbe.packets import Packet, PacketIndex, load_frozen_offsets, merge_char_spans, pack_inventory, packet_source
from cbe.store import (
    BudgetError,
    LedgerStore,
    LeaseError,
    StaleWriteError,
    atomic_write_bytes,
    iso,
    mark_call,
    pid_alive,
    reserve_call,
    submit_details,
    utc_now,
)
from cbe.token_budget import count_text_tokens, tokenizer_version


CONTRACT = "module-facts/1"
ATTRIBUTION_CONTRACT = "fact-attribution/1"


class FactReferenceError(ValueError):
    """Completed business output cites invalid evidence; binding stays strict."""


class _SourcePartitionBudgetError(ValueError):
    """One pass found source partitions needing the same adaptive split."""

    def __init__(self, packet_ids: list[str]):
        self.packet_ids = tuple(packet_ids)
        super().__init__(f"single source partition exceeds batch targets: {packet_ids[0]}")


class PromptLayoutError(ValueError):
    def __init__(self, *, scope: str, ids: list[str], tokens: int, cap: int):
        self.diagnostic = {"code": "prompt_layout_infeasible", "scope": scope,
                           "assigned_ids": ids, "actual_prompt_tokens": tokens,
                           "max_input_tokens": cap,
                           "next_action": "split_pending_assignments" if len(ids) > 1
                           else "provide_explicit_fragment_contract_or_larger_host_window",
                           "accepted_results_preserved": True, "model_sent": False}
        super().__init__(f"batch prompt {tokens} exceeds {cap} tokens")


class ReviewContextWindowError(PromptLayoutError):
    def __init__(self, *, sid: str | None, path: str, reason: str):
        self.diagnostic = {"code": "review_context_window_unavailable", "scope": "review_context",
                           "assigned_ids": [sid] if sid else [], "path": path,
                           "reason": reason, "next_action": "refine_review_context_request",
                           "accepted_results_preserved": True, "model_sent": False}
        ValueError.__init__(self, reason + "; refine the requested evidence span, not --full-context")


class ReviewNonprogressError(PromptLayoutError):
    """A repeated evidence request cannot advance the current review."""

    def __init__(self, ids: list[str]):
        self.diagnostic = {
            "code": "review_context_nonprogress", "scope": "review_context",
            "assigned_ids": ids,
            "reason": "requested context adds no frozen source to the prior review view",
            "next_action": "resolve_finding_from_existing_evidence_or_request_distinct_frozen_span",
            "accepted_results_preserved": True, "model_sent": False,
        }
        ValueError.__init__(self, "nonprogress: " + self.diagnostic["reason"])


def _requested_review_window(text: str, start_line: int, end_line: int,
                             seen: list[CharSpan], *, sid: str | None, path: str) -> tuple[int, int]:
    """First not-yet-presented, whole-line <=5000-char request window."""
    starts = line_starts(text)
    first = max(1, start_line - 1)  # one boundary line, explicitly reported
    last = min(end_line, len(starts))
    covered = merge_char_spans(seen)
    while first <= last:
        boundary = starts[first - 1]
        finish = first
        while finish <= last:
            right = starts[finish] if finish < len(starts) else len(text)
            if right - boundary > 5000:
                break
            finish += 1
        finish -= 1
        if finish < first:
            raise ReviewContextWindowError(sid=sid, path=path,
                                           reason="one requested source line exceeds the 5000-character context window")
        right = starts[finish] if finish < len(starts) else len(text)
        shown = sum(max(0, min(right, span.end) - max(boundary, span.start)) for span in covered)
        if shown < right - boundary:
            return first, finish
        first = finish + 1
    raise ReviewContextWindowError(sid=sid, path=path,
                                   reason="all requested windows were already presented; the finding remains unresolved")

ATTRIBUTION_AUTHOR_INSTRUCTION = (
    "Explain each assigned non-executable object (class or module residual) from only the "
    "frozen source below. Return exactly one JSON object without Markdown, with envelope "
    "copied verbatim, and items. Do not guess or report your model identity; the controller "
    "binds the author role to the claim and native session. Each item needs symbol_id, concise "
    "behavior and source_refs. behavior must be either load-bearing semantics visible in the "
    "shown source (registration, module or class side effects, decorators, dynamic class "
    "construction, data invariants maintained by the statements) or an explicit attribution: "
    "name what the object is for and which member functions or named facts carry its behavior, "
    "and say so plainly when the shown statements are only structural. For the assigned "
    "object's evidence, use [{symbol_id: <its exact assigned ID>}]; the controller fills the "
    "frozen path and start line. Use an additional explicit {path, line} only for a numbered "
    "source line actually shown in the message; do not guess coordinates. Do not invent "
    "behavior that the shown statements do not support; an accurate structural attribution is "
    "a correct answer.\n"
    "Use the numeric assignment allocation as a brevity target. Do not use tools or "
    "count tokens or words yourself; the controller checks size. Spend space on "
    "distinct side effects, conditions and failures; cite lines instead of restating them."
)
ATTRIBUTION_REVIEW_INSTRUCTION = (
    "Independently inspect each assigned draft attribution for a non-executable object "
    "(class or module residual). Check only assigned IDs against the shown frozen source; "
    "unassigned IDs must not be called individually source-checked. Verify that load-bearing "
    "claims (side effects, registration, decorators, dynamic behavior) match the shown "
    "statements and that container attributions are consistent with the shown class or module "
    "structure; an accurate structural attribution is acceptable and must not be flagged as "
    "an error merely for being short. If a claim might be correct but material surrounding "
    "context is absent, return verdict needs_context with findings [{symbol_id, reason, "
    "needed_source: {path, start_line, end_line}}] naming the smallest frozen span needed; do "
    "not call the author wrong just because this review packet omitted it. Otherwise return "
    "exactly one JSON object without Markdown, with envelope copied verbatim, verdict "
    "(accepted, revision_required or needs_context), checked_ids, findings, content_sha256 "
    "and evidence_ref. checked_ids must name attributions you individually compared to "
    "source. Return evidence_ref equal to evidence_path. Put one concise decisive path:line "
    "citation per checked ID in evidence_summary; the controller persists this response "
    "at evidence_path. Do not use tools or restate draft/source text. Do not guess or report your model "
    "identity; the controller binds reviewer role to the claim/native session."
)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_json(value: Any) -> str:
    return _sha_bytes(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


ACCEPTED_FACT_STATES = frozenset({"source_checked", "batch_accepted", "syntax_evidenced", "mechanically_validated"})


def accepted_fact(ledger: dict, sid: str) -> bool:
    """True when this symbol holds a review-accepted, hash-bound fact.

    Used by refresh carrying and by claim filtering so an already accepted
    fact is never silently re-produced or re-asked. A detail whose review hash
    no longer matches is not accepted.
    """
    detail = (ledger.get("details") or {}).get(sid)
    if not isinstance(detail, dict):
        return False
    review = (ledger.get("fact_reviews") or {}).get(sid) or {}
    return (
        review.get("state") in ACCEPTED_FACT_STATES
        and review.get("content_sha256") == _sha_json(detail)
    )


def repair_review_ids(ledger: dict, author: TaskRecord) -> set[str]:
    """Recover a bound targeted repair after old commit cleared repair_ids."""
    ids = set(author.extra.get("repair_ids") or [])
    call = ledger.get("calls", {}).get(author.extra.get("call_id")) or {}
    assigned = set((call.get("extra") or {}).get("assigned_ids") or [])
    if (call.get("task_id") == author.task_id and call.get("input_hash") == author.input_hash
        and call.get("state") == "imported" and assigned and assigned < set(author.input_ids)
        and set(author.extra.get("assigned_ids") or []) == assigned):
        ids.update(assigned)
    return ids & set(author.input_ids)


def _message_projection(packet: dict) -> bytes:
    """The sole user message sent to a model; frozen source appears exactly once."""
    source_label = (
        "Frozen source partitions (each span appears once):\n" + packet["source"]
        if packet.get("batch_id") else
        f"Frozen source from {packet['packet']['path']}:\n" + packet["source"]
    )
    parts = [
        packet["instruction"],
        "Envelope (copy verbatim):\n" + json.dumps(packet["envelope"], ensure_ascii=False, separators=(",", ":")),
        "Assignments (canonical ID equals symbol_id unless explicit):\n" + json.dumps(
            compact_assignments(packet["assignments"]), ensure_ascii=False, separators=(",", ":")),
        source_label,
    ]
    if packet.get("repair_findings"):
        parts.append(("Previous independent review findings to check:\n" if packet.get("kind") == "review"
                      else "Previous independent review findings to repair:\n")
                         + json.dumps(packet["repair_findings"], ensure_ascii=False, separators=(",", ":")))
    if packet.get("review_question"):
        parts.append("Independent review dispute to resolve from frozen source:\n"
                     + packet["review_question"])
    if packet.get("context_limits"):
        parts.append("Review context limits:\n" + json.dumps(packet["context_limits"], ensure_ascii=False, separators=(",", ":")))
    if packet.get("composition_prior"):
        parts.append("Prior source-bound obligations (retain original acceptance states):\n" + json.dumps(packet["composition_prior"], ensure_ascii=False, separators=(",", ":")))
    if packet.get("composition_prior_states"):
        parts.append("Original obligation acceptance states:\n" + json.dumps(packet["composition_prior_states"], separators=(",", ":")))
    if packet.get("composition_findings"):
        parts.append("Original unresolved findings whose mappings need independent review:\n" + json.dumps(packet["composition_findings"], ensure_ascii=False, separators=(",", ":")))
    if packet.get("accepted_dependencies"):
        parts.append("Bound accepted dependency facts (static links do not prove runtime binding):\n" + json.dumps(packet["accepted_dependencies"], ensure_ascii=False, separators=(",", ":")))
    if packet.get("draft") is not None:
        parts.append(("Previous draft facts to repair:\n" if packet.get("kind") == "author"
                      else "Draft facts to review:\n") + json.dumps(
            packet.get("draft_projection") or packet["draft"], ensure_ascii=False, separators=(",", ":")))
        parts.append("Draft content_sha256 = envelope.input_hash" if
                     packet["draft_content_sha256"] == packet["envelope"]["input_hash"] else
                     "Draft content_sha256: " + packet["draft_content_sha256"])
        if packet.get("evidence_path"):
            parts.append("Independent evidence_path: " + packet["evidence_path"])
    return ("\n\n".join(parts) + "\n").encode("utf-8")


def compact_assignments(assignments: list[dict]) -> list[dict]:
    """Lossless transport: an absent canonical ID explicitly equals symbol_id."""
    return [{k: v for k, v in item.items() if not (
        k == "canonical_symbol_id" and v == item.get("symbol_id"))}
        for item in assignments]



def _fact_instruction(attribution: bool, kind: str) -> str:
    if attribution:
        instruction = (ATTRIBUTION_AUTHOR_INSTRUCTION if kind == "author"
                       else ATTRIBUTION_REVIEW_INSTRUCTION)
        instruction += (
            " Containers locate canonical members; algorithms belong to member facts. "
            "Expanded views do not require expanded claims. Findings are instructions, not source."
            " Preserve maintenance-bearing diagnostic templates, literal keys/choices and material "
            "empty/failure/unused-capacity branches visible in assigned statements."
        )
    else:
        instruction = (
            "Explain each assigned ID from only the frozen source below. Return exactly one JSON "
            "object without Markdown, with envelope copied verbatim, "
            "and items. Do not guess or report your model identity; the controller binds the "
            "author role to the claim and native session. Each item needs symbol_id, concise behavior and "
            "source_refs. For the assigned function's evidence, use [{symbol_id: <its exact assigned ID>}]; "
            "the controller fills the frozen path and start line. Use an additional explicit {path, line} "
            "only for a numbered source line actually shown in the message; do not guess coordinates. "
            "For deep or elevated-risk assignments, explain inputs/outputs, state effects, failure "
            "conditions and uncertainty in concise behavior prose; brief assignments need the "
            "key behavioral distinction. Describe concrete branches and effects visible in the "
            "supplied spans. A callee name or returned object's name alone does not establish its "
            "downstream behavior; state the call and the evidence boundary while still explaining "
            "the function's meaningful role. Flag a missing dependency implementation only when "
            "it would materially change a maintenance conclusion, for a separately counted source review.\n"
            "Aim near each assignment's suggested_output_tokens behavior-only allocation "
            "(program declaration syntax is budgeted separately); preserve "
            "necessary branches and failures if they need a little more space. "
            "Do not calculate token or word counts or use tools; the controller checks size. "
            "Use a short sentence for simple functions and concise clauses for complex ones. "
            "Prioritize concrete conditions, state effects, and distinct failure paths; "
            "Preserve exact return keys, diagnostic text/templates (including placeholders), and literal "
            "field names or choices used to select/count values when they define a maintenance contract. "
            "State material empty-input, failure and unused-capacity branches, including what remains "
            "unchanged or unallocated. Keep these in concise behavior with source_refs; quote only "
            "contract-bearing literals, not whole source or incidental labels. "
            "Program-provided callable_syntax describes declaration parameters/default expressions, "
            "not runtime guarantees. The program publishes this syntax separately: explain behavior, "
            "effects and failures without re-copying a parameter table or signature. Explain material "
            "runtime argument constraints only when evidenced by the supplied source."
            " Program syntax_atoms give exact statement syntax and lexical guards; preserve their "
            "ordering, bare-return None and conditional effects. They do not prove reachability, "
            "runtime binding or dynamic effects. Optional syntax_atom_refs must name only displayed "
            "atom IDs; optional syntax_assertions compare structured callable/literal/return-key "
            "facts mechanically. Avoid copying the atoms into prose when the program already publishes them."
            if kind == "author" else
            "Independently inspect every assigned draft fact. Check only assigned IDs against the shown frozen "
            "source; unassigned IDs must not be called individually "
            "source-checked. If a claim might be correct but material surrounding context is absent, "
            "return verdict needs_context with findings [{symbol_id, reason, needed_source: "
            "{path, start_line, end_line}}] naming the smallest frozen span needed; do not call "
            "the author wrong just because this review packet omitted it. Otherwise return exactly one JSON "
            "object without Markdown, with envelope copied verbatim, "
            "verdict (accepted, revision_required or needs_context), checked_ids, findings, "
            "content_sha256 and evidence_ref. checked_ids must name facts you individually compared "
            "to source. Return evidence_ref equal to evidence_path and include a concise "
            "evidence_summary with one decisive path:line per checked ID; the controller "
            "persists this response there. Do not use tools. Do not guess or report "
            "your model identity; the controller binds reviewer role to the claim/native session. Name exact source-backed "
            "errors, including lost return/selection keys, diagnostic text/templates and material empty, "
            "failure or unused-capacity branches; distinguish incidental literals from maintenance "
            "contracts. Do not adopt author claims or expand review scope. "
            "Use file-level guards, globals and directly relevant "
            "callee bodies only if they are visibly included in this frozen packet; distinguish "
            "missing review context from a false author claim. VERDICT DECISION RULE (binding): "
            "choose revision_required only for a claim you can refute with a numbered line shown "
            "in this packet; a plausible claim whose evidence span is not shown (for example a "
            "callee body outside the packet) makes the verdict needs_context with needed_source, "
            "never revision_required."
        )
    return instruction


def _packet(ledger: dict, packet_id: str) -> Packet:
    for raw in (ledger.get("packets") or {}).get("packets") or []:
        if raw.get("packet_id") == packet_id:
            return Packet.from_dict(raw)
    raise ValueError(f"unknown frozen fact packet: {packet_id}")


def _batch_packets(ledger: dict, unit_id: str) -> list[Packet]:
    raw = (ledger.get("fact_batches") or {}).get(unit_id)
    if raw and raw.get("superseded"):
        raise StaleWriteError(f"fact batch {unit_id} was superseded before any claim")
    return [_packet(ledger, packet_id) for packet_id in raw["packet_ids"]] if raw else [_packet(ledger, unit_id)]


def _packet_output_ids(packet: Packet, symbols: dict) -> list[str]:
    return [fragment.output_id for fragment in packet.fragments
            if symbols[fragment.symbol_id]["kind"] in {"function", "method", "lambda"}]


def _batch_assignments(packets: list[Packet], symbols: dict) -> list[str]:
    return list(dict.fromkeys(sid for packet in packets for sid in _packet_output_ids(packet, symbols)))


def _batch_windows(ledger: dict, max_output_estimate: int) -> dict[str, int]:
    """Use symbol density to avoid a short file with many tiny functions overrunning output."""
    inventory = ledger["inventory"]
    policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}
    estimated_by_path: dict[str, int] = {}
    for sid, symbol in inventory["symbols"].items():
        if symbol["kind"] not in {"function", "method", "lambda"}:
            continue
        tier = (policy.get(sid) or {}).get("tier")
        quota = (policy.get(sid) or {}).get("suggested_output_tokens")
        estimated_by_path[symbol["path"]] = estimated_by_path.get(symbol["path"], 0) + (
            int(quota) + 35 if quota is not None else {
                "deep": 300, "standard": 220, "brief": 190,
            }.get(tier, 220))
    return {
        path: max(1200, min(20000, int(max_output_estimate * record["char_length"] /
            max(1, estimated_by_path.get(path, 0)))))
        for path, record in inventory["files"].items()
    }


def _pack_for_batches(ledger: dict, inventory: Inventory, max_output_estimate: int,
                      max_input_tokens: int = 8000) -> PacketIndex:
    windows = _batch_windows(ledger, max_output_estimate)
    symbols = ledger["inventory"]["symbols"]
    policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}
    for _ in range(8):
        packets = pack_inventory(inventory, repo=Path(ledger["repo_root"]),
                                 window_chars=20000, window_chars_by_path=windows)
        oversized: set[str] = set()
        for packet in packets.packets:
            estimate = 300 + sum((
                int((policy.get(fragment.symbol_id) or {}).get("suggested_output_tokens")) + 35
                if (policy.get(fragment.symbol_id) or {}).get("suggested_output_tokens") is not None
                else {"deep": 300, "standard": 220, "brief": 190}.get(
                    (policy.get(fragment.symbol_id) or {}).get("tier"), 220))
                for fragment in packet.fragments
                if symbols[fragment.symbol_id]["kind"] in {"function", "method", "lambda"})
            if estimate > max_output_estimate:
                oversized.add(packet.path)
        try:
            plan_batches(ledger, packets, max_input_tokens=max_input_tokens,
                         max_output_estimate=max_output_estimate)
        except ValueError as exc:
            if isinstance(exc, _SourcePartitionBudgetError):
                bad_ids = set(exc.packet_ids)
                oversized.update(packet.path for packet in packets.packets if packet.packet_id in bad_ids)
                # All independently oversized input partitions were found by
                # the exact same single-packet estimate in this planning pass.
                # They need not queue one path per adaptive retry.
            else:
                prefix = "single source partition exceeds batch targets: "
                if not str(exc).startswith(prefix):
                    raise
                packet_id = str(exc)[len(prefix):]
                bad = next((item for item in packets.packets if item.packet_id == packet_id), None)
                if bad is None:
                    raise
                oversized.add(bad.path)
        if not oversized:
            return packets
        for path in oversized:
            windows[path] = max(250, windows[path] // 2)
    raise ValueError(f"source partitions still exceed output estimate after adaptive splitting: {sorted(oversized)[:3]}")


def plan_batches(ledger: dict, packets: PacketIndex, *, max_input_tokens: int = 8000,
                 max_output_estimate: int = 3000) -> dict[str, dict]:
    """Deterministically group adjacent related source partitions by both prompt and output size."""
    if max_input_tokens < 1000 or max_output_estimate < 1000:
        raise ValueError("batch token targets must be at least 1000")
    symbols = ledger["inventory"]["symbols"]
    policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}
    eligible = [packet for packet in packets.packets if _packet_output_ids(packet, symbols)]
    repo = Path(ledger["repo_root"])
    # The frozen file records are invariant for this planning invocation. Do
    # not reconstruct every symbol in the inventory just to locate each file.
    frozen_files = Inventory.from_dict(ledger["inventory"]).files
    offsets: dict[str, Any] = {}
    starts_by_path: dict[str, tuple[int, ...]] = {}

    def source(packet: Packet) -> str:
        if packet.path not in offsets:
            offsets[packet.path] = load_frozen_offsets(repo, packet.path,
                                                        frozen_files[packet.path])
            starts_by_path[packet.path] = line_starts(offsets[packet.path].text)
        return "\n\n".join(
            _numbered_source_span(packet.path, span, offsets[packet.path].text,
                                  starts=starts_by_path[packet.path])
            for span in packet.spans
        )

    source_by_id = {packet.packet_id: source(packet) for packet in eligible}
    callable_syntax = contracts_for(ledger, frozen_files=frozen_files)
    # Packet paths are stable and naturally cluster same-directory code and tests.
    eligible.sort(key=lambda packet: (packet.path.split("/")[0], packet.path, packet.slice_index, packet.packet_id))

    def output_estimate(group: list[Packet]) -> int:
        total = 300  # envelope and JSON framing
        for sid in _batch_assignments(group, symbols):
            canonical = next((f.symbol_id for p in group for f in p.fragments if f.output_id == sid), sid)
            tier = (policy.get(canonical) or {}).get("tier")
            quota = (policy.get(canonical) or {}).get("suggested_output_tokens")
            total += int(quota) + 35 if quota is not None else {
                "deep": 300, "standard": 220, "brief": 190,
            }.get(tier, 220)
        return total

    def prompt_tokens(group: list[Packet]) -> int:
        from cbe.syntax_facts import assignment_facts
        assignments = _batch_assignments(group, symbols)
        skeleton = {
            "instruction": _fact_instruction(False, "author"),
            "envelope": {"task_id": "task:fact_author:batch:" + "0" * 16,
                         "generation": 100, "owner": "gpt-6-sol-fact-author",
                         "input_hash": "0" * 64, "call_id": "call:fact:" + "0" * 32},
            "assignments": [{
                "symbol_id": sid,
                "canonical_symbol_id": next((f.symbol_id for p in group for f in p.fragments
                    if f.output_id == sid), sid),
                "name": symbols[next((f.symbol_id for p in group for f in p.fragments
                    if f.output_id == sid), sid)]["qualified_name"],
                "kind": symbols[next((f.symbol_id for p in group for f in p.fragments
                    if f.output_id == sid), sid)]["kind"],
                **({"callable_syntax": prompt_contract(callable_syntax[canonical])}
                   if (canonical := next((f.symbol_id for p in group for f in p.fragments
                                          if f.output_id == sid), sid)) in callable_syntax else {}),
                **assignment_facts(ledger, canonical,
                    next(([span.to_dict() for span in f.owned_spans] for p in group for f in p.fragments if f.output_id == sid), None)),
                "source_path": next(p.path for p in group if sid in _packet_output_ids(p, symbols)),
                "start_line": 999,
                "tier_signal": (policy.get(next((f.symbol_id for p in group for f in p.fragments
                    if f.output_id == sid), sid)) or {}).get("tier"),
                "suggested_output_tokens": behavior_token_recommendation(
                    policy.get(next((f.symbol_id for p in group for f in p.fragments if f.output_id == sid), sid)) or {},
                    callable_syntax.get(next((f.symbol_id for p in group for f in p.fragments if f.output_id == sid), sid))),
            } for sid in assignments],
            "batch_id": "batch:preview", "source": "\n\n".join(source_by_id[p.packet_id] for p in group),
        }
        # The exact source numbering and assignment schema are represented;
        # margin covers the full author instruction and live envelope values.
        return count_text_tokens(_message_projection(skeleton).decode()) + 500

    oversized_ids = [packet.packet_id for packet in eligible
                     if prompt_tokens([packet]) > max_input_tokens
                     or output_estimate([packet]) > max_output_estimate]
    if oversized_ids:
        raise _SourcePartitionBudgetError(oversized_ids)
    grouped: list[list[Packet]] = []
    current: list[Packet] = []
    for packet in eligible:
        candidate = [*current, packet]
        if current and (prompt_tokens(candidate) > max_input_tokens or
                        output_estimate(candidate) > max_output_estimate):
            grouped.append(current)
            current = [packet]
        else:
            current = candidate
        if prompt_tokens(current) > max_input_tokens or output_estimate(current) > max_output_estimate:
            raise ValueError(f"single source partition exceeds batch targets: {packet.packet_id}")
    if current:
        grouped.append(current)
    batches: dict[str, dict] = {}
    for group in grouped:
        digest = _sha_json([packet.packet_id for packet in group])[:16]
        batch_id = f"batch:{digest}"
        assigned = _batch_assignments(group, symbols)
        review_ids = set(_tiered_review_ids(ledger, group, assigned))
        review_spans: dict[str, list[CharSpan]] = {}
        review_canonical: dict[str, list[str]] = {}
        for packet in group:
            for fragment in packet.fragments:
                if fragment.output_id in review_ids:
                    review_spans.setdefault(packet.path, []).extend(fragment.owned_spans)
                    review_canonical.setdefault(packet.path, []).append(fragment.symbol_id)
        review_chars = 0
        for path, spans in review_spans.items():
            spans.extend(_review_context_spans(ledger, path, review_canonical[path], offsets[path].text,
                                               starts=starts_by_path[path]))
            review_chars += sum(span.length for span in merge_char_spans(spans))
        batches[batch_id] = {
            "packet_ids": [packet.packet_id for packet in group],
            "input_ids": assigned,
            "source_chars": sum(packet.source_chars for packet in group),
            "planned_review_source_chars": review_chars,
            "planned_source_checked_count": len(review_ids),
            "estimated_prompt_tokens": prompt_tokens(group),
            "estimated_output_tokens": output_estimate(group),
            "max_input_tokens": max_input_tokens,
            "max_output_estimate": max_output_estimate,
        }
    return batches


def _resource_plan(ledger: dict, run_dir: Path, batches: dict[str, dict],
                   usage_baseline_run: Path | None = None) -> dict[str, Any]:
    """Pre-dispatch estimate; native receipts replace the fixed-input prior."""
    policy = ledger.get("documentation_policy") or {}
    s_chars = int(ledger["inventory"]["s_chars"])
    s_tokens = int(policy["source_tokens"])
    usage_ledger = ledger
    if usage_baseline_run is not None and not any(
        isinstance(call.get("usage"), dict) for call in (ledger.get("calls") or {}).values()
    ):
        usage_ledger = LedgerStore(Path(usage_baseline_run).resolve()).open()
        if usage_ledger["source_revision"] != ledger["source_revision"]:
            raise ValueError("usage baseline must use the same frozen source revision")
    observed = [
        max(0, int(call["usage"]["input_tokens"]) - int((call.get("extra") or {})["actual_prompt_tokens"]))
        for call in (usage_ledger.get("calls") or {}).values()
        if isinstance(call.get("usage"), dict)
        and type(call["usage"].get("input_tokens")) is int
        and type((call.get("extra") or {}).get("actual_prompt_tokens")) is int
    ]
    host_fixed = int(statistics.median(observed)) if observed else 3000
    symbols = ledger["inventory"]["symbols"]
    if ledger.get("attribution_workflow_version"):
        attribution_ids = {
            sid for batch in (ledger.get("attribution_batches") or {}).values()
            for sid in batch.get("input_ids") or []
        }
    else:
        from cbe.syntax_attribution import syntax_attribution

        attribution_ids = {
            sid for sid, symbol in symbols.items()
            if symbol["kind"] not in {"function", "method", "lambda"}
            and syntax_attribution(ledger, sid) is None
        }
    attribution = [symbols[sid] for sid in sorted(attribution_ids)]
    attribution_chars = sum(sum(
        int(span["end"]) - int(span["start"])
        for span in (symbol.get("exclusive_spans") or [symbol["span"]])
    ) for symbol in attribution)
    plan_path = run_dir / "module_plan.json"
    module_count = 0
    if plan_path.exists():
        module_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        module_count = sum(bool(group.get("member_ids"))
                           for group in (module_plan.get("groups") or {}).values())
    author_calls = len(batches)
    author_prompt = sum(batch["estimated_prompt_tokens"] for batch in batches.values())
    author_output = sum(batch["estimated_output_tokens"] for batch in batches.values())
    review_chars = sum(batch["planned_review_source_chars"] for batch in batches.values())
    review_calls = author_calls
    attr_calls = (
        len(ledger.get("attribution_batches") or {})
        if ledger.get("attribution_workflow_version") else
        (max(1, (attribution_chars + 11999) // 12000) if attribution_chars else 0)
    )
    stages = {
        "fact_authors": {"calls": author_calls, "source_chars": sum(batch["source_chars"] for batch in batches.values()),
                         "input_tokens": author_prompt + host_fixed * author_calls,
                         "output_tokens": author_output},
        "fact_reviews": {"calls": review_calls, "source_chars": review_chars,
                         "input_tokens": review_chars // 4 + 200 * sum(batch["planned_source_checked_count"] for batch in batches.values()) + host_fixed * review_calls,
                         "output_tokens": 200 * review_calls},
        "attribution_author_and_review": {"calls": attr_calls * 2, "source_chars": attribution_chars * 2,
                         "input_tokens": attribution_chars // 2 + host_fixed * attr_calls * 2,
                         "output_tokens": 200 * len(attribution)},
        "module_author_and_review": {"calls": module_count * 2, "source_chars": 0,
                         "input_tokens": module_count * (1200 + 2 * host_fixed),
                         "output_tokens": module_count * 500},
    }
    planned_source = sum(item["source_chars"] for item in stages.values())
    repair_source = max(0, 2 * s_chars - planned_source)
    repair_calls = max(1, (author_calls + attr_calls + module_count + 9) // 10)
    stages["repair_reserve"] = {"calls": repair_calls, "source_chars": repair_source,
                                 "input_tokens": repair_calls * (host_fixed + 1500),
                                 "output_tokens": repair_calls * 500}
    return {
        "source_chars": s_chars, "source_tokens": s_tokens,
        "tokenizer": "o200k_base", "tokenizer_version": tokenizer_version(),
        "source_cap_chars": 2 * s_chars, "published_cap_tokens": s_tokens // 2,
        "host_fixed_input_tokens_per_call": host_fixed,
        "host_fixed_basis": "native_receipt_median" if observed else "uncalibrated_prior",
        "usage_baseline_run": (str(Path(usage_baseline_run).resolve())
                               if usage_baseline_run and usage_ledger is not ledger else None),
        "stages": stages,
        "estimated_calls": sum(item["calls"] for item in stages.values()),
        "estimated_input_tokens": sum(item["input_tokens"] for item in stages.values()),
        "estimated_output_tokens": sum(item["output_tokens"] for item in stages.values()),
        "planned_source_chars_before_repair": planned_source,
        "planned_source_within_cap": planned_source <= 2 * s_chars,
    }


def _auto_batch_plan(
    ledger: dict, run_dir: Path, *,
    max_input_cap: int | None = None, max_output_cap: int | None = None,
    usage_baseline_run: Path | None = None,
) -> tuple[PacketIndex, dict[str, dict], dict[str, Any], list[dict[str, Any]]]:
    """Choose a feasible pre-dispatch plan by full-run cost, not packet size.

    Explicit caps are ceilings: they never become a reason to silently choose
    a larger input or output target.  Every candidate uses the same frozen
    inventory, risk policy and source admission rule.
    """
    candidates = [(4000, 3000), (8000, 3000), (16000, 6000), (24000, 6000)]
    if max_input_cap is not None or max_output_cap is not None:
        exact_input = max_input_cap if max_input_cap is not None else 24000
        exact_output = max_output_cap if max_output_cap is not None else (
            6000 if exact_input >= 16000 else 3000
        )
        candidates.append((exact_input, exact_output))
    inventory = Inventory.from_dict(ledger["inventory"])
    scenarios: list[dict[str, Any]] = []
    feasible: list[tuple[int, int, int, PacketIndex, dict[str, dict], dict[str, Any]]] = []
    for input_target, output_target in sorted(set(candidates)):
        if max_input_cap is not None and input_target > max_input_cap:
            continue
        if max_output_cap is not None and output_target > max_output_cap:
            continue
        try:
            packets = _pack_for_batches(ledger, inventory, output_target, input_target)
            batches = plan_batches(ledger, packets, max_input_tokens=input_target,
                                   max_output_estimate=output_target)
            resource = _resource_plan(ledger, run_dir, batches, usage_baseline_run)
            total = resource["estimated_input_tokens"] + resource["estimated_output_tokens"]
            row = {"max_input_tokens": input_target,
                   "max_output_estimate": output_target,
                   "batch_count": len(batches),
                   "planned_source_chars": resource["planned_source_chars_before_repair"],
                   "source_cap_chars": resource["source_cap_chars"],
                   "estimated_total_tokens": total,
                   "feasible": resource["planned_source_within_cap"]}
            scenarios.append(row)
            if row["feasible"] or (ledger.get("documentation_policy") or {}).get("budget_mode") == "report":
                feasible.append((total, input_target, output_target,
                                 packets, batches, resource))
        except ValueError as exc:
            scenarios.append({"max_input_tokens": input_target,
                              "max_output_estimate": output_target,
                              "feasible": False, "reason": str(exc)})
    if not feasible:
        raise ValueError(f"no usable pre-dispatch fact plan within explicit caps: {scenarios}")
    # Prefer a within-guidance candidate when one exists. Report-mode runs
    # still choose a useful plan when every candidate exceeds 2*S.
    if (ledger.get("documentation_policy") or {}).get("budget_mode") == "report":
        within = [item for item in feasible if item[5]["planned_source_within_cap"]]
        if within:
            feasible = within
    _, chosen_input, chosen_output, packets, batches, resource = min(
        feasible, key=lambda item: item[:3]
    )
    resource["auto_selected_targets"] = {
        "max_input_tokens": chosen_input,
        "max_output_estimate": chosen_output,
    }
    return packets, batches, resource, scenarios


def _module_for_symbol(ledger: dict, run_dir: Path, symbol_id: str) -> str | None:
    plan = json.loads((run_dir / "module_plan.json").read_text(encoding="utf-8"))
    for group_id, group in plan["groups"].items():
        if symbol_id in (group.get("member_ids") or []):
            return group_id
    return None


def _tiered_review_ids(ledger: dict, packets: list[Packet], candidate_ids: list[str]) -> list[str]:
    """Deep and elevated-risk facts are checked; ordinary facts get stable stratified samples."""
    from cbe.review_policy import mode, selected
    if mode(ledger) is not None:
        return selected(ledger, candidate_ids)
    policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}
    symbols = ledger["inventory"]["symbols"]
    canonical = {fragment.output_id: fragment.symbol_id for packet in packets for fragment in packet.fragments}
    selected: set[str] = set()
    for sid in candidate_ids:
        current = canonical.get(sid, sid)
        item = policy.get(current) or {}
        signals = set(item.get("signals") or [])
        tier = item.get("tier")
        elevated = tier == "deep" or bool(signals & {
            "risk:exception_boundary", "risk:io_or_persist", "risk:security_boundary",
        })
        selector = int(hashlib.sha256(sid.encode()).hexdigest()[:8], 16)
        if elevated or (tier == "standard" and selector % 3 == 0) or selector % 10 == 0:
            selected.add(sid)
    # Every source partition with a draft receives at least one direct comparison.
    for packet in packets:
        ids = [sid for sid in candidate_ids if sid in _packet_output_ids(packet, symbols)]
        if ids and not selected.intersection(ids):
            selected.add(min(ids, key=lambda sid: hashlib.sha256(sid.encode()).hexdigest()))
    return [sid for sid in candidate_ids if sid in selected]


def _review_context_spans(ledger: dict, path: str, selected_ids: list[str],
                          text: str, *, max_chars: int | None = None,
                          starts: tuple[int, ...] | None = None) -> tuple[CharSpan, ...]:
    """Relevant same-file guard, global and whole direct-callee evidence.

    The source ledger, rather than a silent character truncation, bounds the
    resulting view. A caller may give a smaller explicit planning limit.
    """
    if not selected_ids:
        return ()
    tree: ast.Module | None = None
    if path.endswith(".py"):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            pass
    starts = line_starts(text) if starts is None else starts
    symbols = ledger["inventory"]["symbols"]
    by_id = {sid: symbols[sid] for sid in selected_ids if sid in symbols and symbols[sid]["path"] == path}
    if not by_id:
        return ()

    def lines_span(start: int, end: int) -> CharSpan | None:
        if not 1 <= start <= end <= len(starts):
            return None
        return CharSpan(starts[start - 1], starts[end] if end < len(starts) else len(text))

    candidates: list[tuple[int, CharSpan]] = []
    definitions: dict[str, list[ast.AST]] = {}
    imports: dict[str, ast.AST] = {}
    for node in tree.body if tree is not None else []:
        names: list[str] = []
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [child.id for target in targets for child in ast.walk(target)
                     if isinstance(child, ast.Name)]
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.asname or alias.name.split(".")[0] for alias in node.names]
            for name in names:
                imports[name] = node
        for name in names:
            definitions.setdefault(name, []).append(node)
    functions = [node for node in (ast.walk(tree) if tree is not None else ())
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))]
    edges = (ledger.get("graph") or {}).get("edges") or []
    for sid, symbol in by_id.items():
        span = symbol["span"]
        line = bisect_right(starts, span["start"])
        matched = min((node for node in functions if getattr(node, "lineno", -1) == line),
                      key=lambda node: getattr(node, "end_lineno", line) - line, default=None)
        if tree is not None and matched is not None:
            # Capture enclosing module/class branch conditions, not sibling bodies.
            for node in ast.walk(tree):
                if isinstance(node, ast.If) and node.lineno < line <= getattr(node, "end_lineno", -1):
                    if any(child.lineno <= line <= getattr(child, "end_lineno", -1)
                           for child in [*node.body, *node.orelse] if hasattr(child, "lineno")):
                        part = lines_span(node.lineno, node.lineno)
                        if part:
                            candidates.append((0, part))
            used = {node.id for node in ast.walk(matched) if isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)}
            for name in sorted(used):
                for node in definitions.get(name, []):
                    part = lines_span(node.lineno, getattr(node, "end_lineno", node.lineno))
                    if part:
                        candidates.append((1, part))
                        for nested in ast.walk(node):
                            if isinstance(nested, ast.Name) and nested.id in imports:
                                imported = imports[nested.id]
                                import_span = lines_span(imported.lineno, imported.lineno)
                                if import_span:
                                    candidates.append((1, import_span))
        elif line > 1:
            # Tree-sitter inventory/graph still supplies spans for JS/TS; nearby
            # lexical context is bounded and explicitly marked incomplete.
            part = lines_span(max(1, line - 4), line - 1)
            if part:
                candidates.append((1, part))
        direct = [edge.get("target_id") for edge in edges if edge.get("subject_id") == sid
                  and edge.get("target_id") in symbols
                  and symbols[edge["target_id"]]["path"] == path]
        for target_id in direct:
            target = symbols[target_id]
            start_line = bisect_right(starts, target["span"]["start"])
            end_line = bisect_right(starts, max(target["span"]["start"], target["span"]["end"] - 1))
            part = lines_span(start_line, end_line)
            if part:
                candidates.append((2, part))
    seen: set[tuple[int, int]] = set()
    chosen: list[CharSpan] = []
    total = 0
    for _, part in sorted(candidates, key=lambda value: (value[0], value[1].start)):
        key = (part.start, part.end)
        if key in seen or (max_chars is not None and total + part.length > max_chars):
            continue
        seen.add(key)
        chosen.append(part)
        total += part.length
    return merge_char_spans(chosen)


def _numbered_source_span(path: str, span: CharSpan, text: str, *,
                          starts: tuple[int, ...] | None = None) -> str:
    """Show each frozen character once with explicit 1-based citation labels."""
    starts = line_starts(text) if starts is None else starts
    line = bisect_right(starts, span.start)
    body: list[str] = []
    for piece in text[span.start:span.end].splitlines(keepends=True):
        body.append(f"L{line}: {piece}")
        line += piece.count("\n")
    return f"Frozen source path {path}: chars {span.start}:{span.end}\n" + "".join(body)


def initialize(run_dir: Path, *, batched: bool = False,
               max_input_tokens: int = 8000,
               max_output_estimate: int = 3000,
               usage_baseline_run: Path | None = None,
               auto_budget: bool = False,
               auto_input_cap: int | None = None,
               auto_output_cap: int | None = None) -> dict[str, Any]:
    """Register source-partition tasks once, preserving any prior module work."""
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    old = store.open()
    if old.get("fact_workflow_version"):
        return {"packet_count": len((old.get("packets") or {}).get("packets") or []),
                "fact_task_count": sum(t.get("kind") == "fact_author" for t in (old.get("tasks") or {}).values()),
                "batch_count": sum(not b.get("superseded") for b in (old.get("fact_batches") or {}).values())}
    if (old.get("documentation_policy") or {}).get("version") != "module-first-v2":
        raise ValueError("short facts require module-first-v2")
    from cbe.runner import _register_merge_tasks, build_detail_task
    inventory = Inventory.from_dict(old["inventory"])
    if auto_budget:
        if not batched:
            raise ValueError("auto-budget requires batched fact production")
        packets, batches, auto_resource, auto_scenarios = _auto_batch_plan(
            old, run_dir, max_input_cap=auto_input_cap,
            max_output_cap=auto_output_cap,
            usage_baseline_run=usage_baseline_run,
        )
    else:
        packets = (_pack_for_batches(old, inventory, max_output_estimate, max_input_tokens) if batched
                   else pack_inventory(inventory, repo=Path(old["repo_root"]), window_chars=60000))
        batches = plan_batches(old, packets, max_input_tokens=max_input_tokens,
                               max_output_estimate=max_output_estimate) if batched else {}
    new_tasks: dict[str, TaskRecord] = {}
    packet_to_task: dict[str, str] = {}
    if batched:
        packet_map = {packet.packet_id: packet for packet in packets.packets}
        for batch_id, batch in batches.items():
            selected = [packet_map[pid] for pid in batch["packet_ids"]]
            fragments = [fragment.to_dict() for packet in selected for fragment in packet.fragments]
            task_id = f"task:fact_author:{batch_id}"
            task = TaskRecord(task_id, "fact_author", list(batch["input_ids"]),
                              _sha_json({"contract": CONTRACT, "batch": batch,
                                         "source_revision": old["source_revision"]}), "pending",
                              extra={"fact_contract": CONTRACT, "batch_id": batch_id,
                                     "packet_ids": list(batch["packet_ids"]),
                                     "fragments": fragments, "review_policy": "tiered-v1"})
            new_tasks[task_id] = task
            packet_to_task.update({pid: task_id for pid in batch["packet_ids"]})
    else:
        for packet in packets.packets:
            if not packet.symbol_ids and not packet.fragments:
                continue
            task = build_detail_task(packet)
            task.task_id = f"task:fact_author:{packet.packet_id}"
            task.kind = "fact_author"
            task.input_hash = _sha_json({"contract": CONTRACT, "packet": packet.to_dict(),
                                         "input_ids": task.input_ids})
            task.extra["fact_contract"] = CONTRACT
            new_tasks[task.task_id] = task
            packet_to_task[packet.packet_id] = task.task_id
    # Merge tasks use the existing fragment identity and source-free merger.
    merge_tasks: dict[str, TaskRecord] = {}
    _register_merge_tasks(merge_tasks, packets.packets)
    for task in list(merge_tasks.values()):
        if batched and old["inventory"]["symbols"][task.input_ids[0]]["kind"] not in {"function", "method", "lambda"}:
            merge_tasks.pop(task.task_id)
            continue
        mapped = [packet_to_task.get(value.removeprefix("task:detail:"))
                  for value in task.extra.get("slice_task_ids") or []]
        if any(value is None for value in mapped):
            raise ValueError(f"merge has an unassigned source fragment: {task.task_id}")
        task.extra["slice_task_ids"] = mapped

    carried = {"tasks": 0}

    def mutate(ledger: dict) -> dict | None:
        if ledger.get("fact_workflow_version"):
            return None
        if ledger["source_revision"] != old["source_revision"]:
            raise StaleWriteError("source revision changed during fact initialization")
        tasks = ledger.setdefault("tasks", {})
        for task in [*new_tasks.values(), *merge_tasks.values()]:
            if task.task_id in tasks:
                raise ValueError(f"fact task already exists: {task.task_id}")
            tasks[task.task_id] = task.to_dict()
        ledger["packets"] = packets.to_dict()
        ledger["fact_workflow_version"] = 1
        # Preserve reviews carried by a staged refresh before initialization.
        ledger.setdefault("fact_reviews", {})
        for task_id, raw in tasks.items():
            if not task_id.startswith("task:fact_") or raw.get("state") != "pending":
                continue
            ids = list(raw.get("input_ids") or [])
            if ids and all(accepted_fact(ledger, sid) for sid in ids):
                raw["state"] = "committed"
                raw["output_refs"] = ids
                extra = dict(raw.get("extra") or {})
                extra["satisfied_by_accepted_facts"] = True
                raw["extra"] = extra
                carried["tasks"] += 1
        if batched:
            ledger["fact_batches"] = batches
        return ledger

    store.mutate(mutate)
    return {"packet_count": len(packets.packets), "fact_task_count": len(new_tasks),
            "batch_count": len(batches),
            "satisfied_task_count": carried["tasks"],
            "planned_source_chars": sum(batch["source_chars"] for batch in batches.values()),
            "planned_review_source_chars": sum(batch["planned_review_source_chars"] for batch in batches.values()),
            "estimated_output_tokens": sum(batch["estimated_output_tokens"] for batch in batches.values()),
            "resource_plan": _resource_plan(store.open(), run_dir, batches, usage_baseline_run) if batched else None,
            **({"auto_selected_targets": auto_resource["auto_selected_targets"],
                "auto_scenarios": auto_scenarios,
                "batches": batches} if auto_budget else {})}


def preview_auto_batches(run_dir: Path, *, max_input_cap: int | None = None,
                         max_output_cap: int | None = None,
                         usage_baseline_run: Path | None = None) -> dict[str, Any]:
    """Read-only first-use candidate comparison with explicit ceilings."""
    run_dir = Path(run_dir).resolve()
    ledger = LedgerStore(run_dir).open()
    if ledger.get("fact_workflow_version"):
        raise ValueError("auto-budget preview applies before fact initialization")
    packets, batches, resource, scenarios = _auto_batch_plan(
        ledger, run_dir, max_input_cap=max_input_cap,
        max_output_cap=max_output_cap, usage_baseline_run=usage_baseline_run,
    )
    return {"source_revision": ledger["source_revision"],
            "packet_count": len(packets.packets), "batch_count": len(batches),
            "batches": batches, "resource_plan": resource,
            "auto_selected_targets": resource["auto_selected_targets"],
            "auto_scenarios": scenarios}


def preview_batches(run_dir: Path, *, max_input_tokens: int = 8000,
                    max_output_estimate: int = 3000,
                    usage_baseline_run: Path | None = None) -> dict[str, Any]:
    """Read-only exact frozen-source batch plan for a not-yet-initialized run."""
    ledger = LedgerStore(Path(run_dir).resolve()).open()
    expected_ids: set[str] | None = None
    scope = "all_uninitialized"
    if ledger.get("fact_workflow_version"):
        if not ledger.get("fact_batches"):
            raise ValueError("this run uses unbatched fact tasks")
        packets = PacketIndex.from_dict(ledger["packets"])
        if ledger.get("fact_batching_policy"):
            expected_ids = {
                batch_id for batch_id, batch in ledger["fact_batches"].items()
                if not batch.get("superseded") and not batch.get("attribution") and
                (ledger["tasks"][f"task:fact_author:{batch_id}"]["state"] == "pending")
            }
            pending_packet_ids = {pid for batch_id in expected_ids
                                  for pid in ledger["fact_batches"][batch_id]["packet_ids"]}
            packets = PacketIndex(packets.window_chars,
                                  [packet for packet in packets.packets
                                   if packet.packet_id in pending_packet_ids])
            scope = "active_pending_only"
        else:
            scope = "all_initialized"
    else:
        inventory = Inventory.from_dict(ledger["inventory"])
        packets = _pack_for_batches(ledger, inventory, max_output_estimate, max_input_tokens)
    batches = plan_batches(ledger, packets, max_input_tokens=max_input_tokens,
                           max_output_estimate=max_output_estimate)
    active_executable_ids = {
        batch_id for batch_id, batch in (ledger.get("fact_batches") or {}).items()
        if not batch.get("attribution") and not batch.get("superseded")
    }
    if scope == "all_initialized" and set(batches) != active_executable_ids:
        raise ValueError("preview targets would change persisted batch IDs")
    scenarios: dict[str, Any] = {}
    for target in sorted({4000, 8000, max_input_tokens}):
        try:
            candidate = plan_batches(ledger, packets, max_input_tokens=target,
                                     max_output_estimate=max_output_estimate)
            resource = _resource_plan(ledger, Path(run_dir), candidate, usage_baseline_run)
            scenarios[str(target)] = {
                "batch_count": len(candidate), "estimated_calls": resource["estimated_calls"],
                "estimated_input_tokens": resource["estimated_input_tokens"],
                "estimated_output_tokens": resource["estimated_output_tokens"],
            }
        except ValueError as exc:
            scenarios[str(target)] = {"infeasible": str(exc)}
    return {"source_revision": ledger["source_revision"], "scope": scope,
            "matches_active_batch_ids": (set(batches) == expected_ids if expected_ids is not None else None),
            "packet_count": len(packets.packets), "batch_count": len(batches),
            "executable_assignment_count": sum(len(batch["input_ids"]) for batch in batches.values()),
            "planned_source_chars": sum(batch["source_chars"] for batch in batches.values()),
            "planned_review_source_chars": sum(batch["planned_review_source_chars"] for batch in batches.values()),
            "planned_source_checked_count": sum(batch["planned_source_checked_count"] for batch in batches.values()),
            "estimated_prompt_tokens": sum(batch["estimated_prompt_tokens"] for batch in batches.values()),
            "estimated_output_tokens": sum(batch["estimated_output_tokens"] for batch in batches.values()),
            "batches": batches,
            "resource_plan": _resource_plan(ledger, Path(run_dir), batches, usage_baseline_run),
            "input_target_scenarios": scenarios}


def rebatch_pending(run_dir: Path, *, max_input_tokens: int = 8000,
                    max_output_estimate: int = 3000) -> dict[str, Any]:
    """Atomically supersede only never-claimed fact batches in the existing ledger."""
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    before = store.open()
    if not before.get("fact_batches"):
        raise ValueError("rebatching requires initialized fact batches")
    active_pending: dict[str, dict] = {}
    for batch_id, batch in before["fact_batches"].items():
        if batch.get("superseded") or batch.get("attribution"):
            continue
        task_id = f"task:fact_author:{batch_id}"
        task = TaskRecord.from_dict(before["tasks"][task_id])
        if task.state == "pending" and not task.extra.get("call_id") and not any(
            call.get("task_id") == task_id for call in (before.get("calls") or {}).values()
        ):
            active_pending[batch_id] = batch
    packet_ids = {pid for batch in active_pending.values() for pid in batch["packet_ids"]}
    full_index = PacketIndex.from_dict(before["packets"])
    subset = PacketIndex(full_index.window_chars,
                         [packet for packet in full_index.packets if packet.packet_id in packet_ids])
    replacement = plan_batches(before, subset, max_input_tokens=max_input_tokens,
                               max_output_estimate=max_output_estimate)
    if {pid for batch in replacement.values() for pid in batch["packet_ids"]} != packet_ids:
        raise ValueError("rebatch output does not cover exactly the pending source partitions")
    packet_map = {packet.packet_id: packet for packet in full_index.packets}
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        if ledger["source_revision"] != before["source_revision"]:
            raise StaleWriteError("source revision changed during rebatch")
        for batch_id in active_pending:
            task_id = f"task:fact_author:{batch_id}"
            task = TaskRecord.from_dict(ledger["tasks"][task_id])
            if task.state != "pending" or task.extra.get("call_id") or any(
                call.get("task_id") == task_id for call in (ledger.get("calls") or {}).values()
            ):
                raise StaleWriteError(f"pending batch was claimed during rebatch: {batch_id}")
        if set(ledger.get("fact_batches") or {}) != set(before["fact_batches"]):
            raise StaleWriteError("fact batch plan changed during rebatch")
        packet_to_new = {pid: batch_id for batch_id, batch in replacement.items()
                         for pid in batch["packet_ids"]}
        changed_old = []
        for batch_id, old_batch in active_pending.items():
            if batch_id in replacement and replacement[batch_id]["packet_ids"] == old_batch["packet_ids"]:
                continue
            old_batch = ledger["fact_batches"][batch_id]
            old_batch["superseded"] = True
            old_batch["superseded_by"] = sorted({packet_to_new[pid] for pid in old_batch["packet_ids"]})
            task_id = f"task:fact_author:{batch_id}"
            task = TaskRecord.from_dict(ledger["tasks"][task_id])
            task.state = "stale"
            task.extra["superseded"] = True
            task.extra["superseded_by"] = old_batch["superseded_by"]
            ledger["tasks"][task_id] = task.to_dict()
            changed_old.append(batch_id)
        added = []
        for batch_id, batch in replacement.items():
            if batch_id in ledger["fact_batches"] and not ledger["fact_batches"][batch_id].get("superseded"):
                continue
            if batch_id in ledger["fact_batches"]:
                raise StaleWriteError(f"rebatch ID collides with historical batch: {batch_id}")
            selected = [packet_map[pid] for pid in batch["packet_ids"]]
            task_id = f"task:fact_author:{batch_id}"
            fragments = [fragment.to_dict() for packet in selected for fragment in packet.fragments]
            task = TaskRecord(task_id, "fact_author", list(batch["input_ids"]),
                              _sha_json({"contract": CONTRACT, "batch": batch,
                                         "source_revision": ledger["source_revision"]}), "pending",
                              extra={"fact_contract": CONTRACT, "batch_id": batch_id,
                                     "packet_ids": list(batch["packet_ids"]),
                                     "fragments": fragments, "review_policy": "tiered-v1"})
            ledger["tasks"][task_id] = task.to_dict()
            ledger["fact_batches"][batch_id] = batch
            added.append(batch_id)
        active_packet_task = {
            pid: f"task:fact_author:{batch_id}"
            for batch_id, batch in ledger["fact_batches"].items() if not batch.get("superseded")
            for pid in batch["packet_ids"]
        }
        fragment_packet = {fragment.fragment_id: packet.packet_id
                           for packet in full_index.packets for fragment in packet.fragments}
        for raw in ledger["tasks"].values():
            if raw.get("kind") != "merge" or raw.get("state") == "committed":
                continue
            extra = raw.get("extra") or {}
            fragment_ids = extra.get("fragment_ids") or []
            if fragment_ids:
                extra["slice_task_ids"] = [active_packet_task[fragment_packet[fid]]
                                           for fid in fragment_ids]
        ledger["fact_batching_policy"] = {"max_input_tokens": max_input_tokens,
                                          "max_output_estimate": max_output_estimate,
                                          "rebatch_from_count": len(active_pending),
                                          "rebatch_to_count": len(replacement)}
        output.update({"source_revision": ledger["source_revision"],
                       "superseded_count": len(changed_old), "new_count": len(added),
                       "pending_batch_count": len(replacement),
                       "new_batch_ids": added, "superseded_batch_ids": changed_old,
                       "pending_source_chars": sum(b["source_chars"] for b in replacement.values())})
        return ledger

    store.mutate(mutate)
    return output


def adopt_review_efficiency(run_dir: Path) -> dict[str, Any]:
    """Explicitly migrate only never-claimed attribution work in this run."""
    from cbe.syntax_attribution import syntax_attribution
    output = {"strategy": "syntax-containers-v2", "syntax_ids": [], "retained_task_ids": []}

    def mutate(ledger: dict) -> dict:
        for tid, raw in ledger["tasks"].items():
            extra = raw.get("extra") or {}
            if raw.get("kind") != "fact_author" or not extra.get("attribution"):
                continue
            batch_id = extra.get("batch_id")
            batch = (ledger.get("fact_batches") or {}).get(batch_id)
            if (raw.get("state") != "pending" or raw.get("owner") or raw.get("lease_until")
                or raw.get("residual") or extra.get("call_id") or extra.get("repair_ids")
                or extra.get("audit_review_ids") or extra.get("superseded") or not batch
                or f"task:fact_review:{batch_id}" in ledger["tasks"]
                or any(c.get("task_id") == tid for c in ledger.get("calls", {}).values())
                or any(sid in ledger.get("details", {}) or sid in ledger.get("fact_reviews", {})
                       for sid in raw["input_ids"])):
                output["retained_task_ids"].append(tid)
                continue
            determined = {sid: syntax_attribution(ledger, sid) for sid in raw["input_ids"]}
            determined = {sid: detail for sid, detail in determined.items() if detail is not None}
            if not determined:
                continue
            for sid, detail in determined.items():
                ledger.setdefault("details", {})[sid] = detail
                ledger.setdefault("fact_reviews", {})[sid] = {
                    "state": "syntax_evidenced", "content_sha256": _sha_json(detail),
                    "source_revision": ledger["source_revision"], "evidence_kind": "program_syntax",
                    "frozen_content_sha256": detail["provenance"]["frozen_content_sha256"],
                }
            remaining = [sid for sid in raw["input_ids"] if sid not in determined]
            raw["input_ids"] = remaining
            raw["input_hash"] = _sha_json({"contract": ATTRIBUTION_CONTRACT,
                "source_revision": ledger["source_revision"], "input_ids": sorted(remaining)})
            raw["generation"] = int(raw.get("generation", 0)) + 1
            if not remaining:
                raw["state"] = "committed"
                raw["output_refs"] = sorted(determined)
            batch["input_ids"] = remaining
            batch["source_chars"] = sum(span["end"]-span["start"] for sid in remaining
                for span in ledger["inventory"]["symbols"][sid].get("exclusive_spans", []))
            for table in ("attribution_batches",):
                if batch_id in ledger.get(table, {}):
                    ledger[table][batch_id] = dict(batch)
            output["syntax_ids"].extend(sorted(determined))
        if output["syntax_ids"]:
            ledger.setdefault("review_efficiency_history", []).append({
                "strategy": output["strategy"], "source_revision": ledger["source_revision"],
                "syntax_ids": list(output["syntax_ids"]), "set_at": iso(),
            })
        return ledger

    LedgerStore(run_dir).mutate(mutate)
    return output


def register_attribution_batches(run_dir: Path, *, max_batch_chars: int = 12000) -> dict[str, Any]:
    """Register attribution batches covering every non-executable symbol once.

    Non-executable inventory objects (classes and module residuals) are not
    assigned by executable fact batches. This registers same-ledger
    ``fact_author`` tasks whose assignments are those objects, presented through
    their frozen exclusive spans, so load-bearing semantics or explicit
    attribution are produced and reviewed under the same claim/import/review
    machinery. Existing executable batches, prepared packets and historical
    calls are untouched; registration is idempotent.
    """
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)

    def plan(ledger: dict) -> dict[str, Any]:
        if not ledger.get("fact_workflow_version"):
            raise ValueError("attribution batches require initialized fact workflow")
        if ledger.get("attribution_workflow_version"):
            batches = ledger.get("attribution_batches") or {}
            syntax_count = sum(
                (ledger.get("fact_reviews") or {}).get(sid, {}).get("state") == "syntax_evidenced"
                for sid, symbol in ledger["inventory"]["symbols"].items()
                if symbol["kind"] not in {"function", "method", "lambda"}
            )
            return {"batch_count": len(batches),
                    "object_count": sum(len(b.get("input_ids") or []) for b in batches.values()),
                    "syntax_evidenced_count": syntax_count,
                    "already_registered": True}
        symbols = ledger["inventory"]["symbols"]
        files = ledger["inventory"]["files"]
        from cbe.syntax_attribution import syntax_attribution

        syntax_records: dict[str, dict[str, Any]] = {}
        non_exec: dict[str, list[tuple[str, dict]]] = {}
        for sid, symbol in sorted(symbols.items()):
            if symbol["kind"] in {"function", "method", "lambda"}:
                continue
            syntax = syntax_attribution(ledger, sid)
            if syntax is not None:
                syntax_records[sid] = syntax
                continue
            non_exec.setdefault(symbol["path"], []).append((sid, symbol))
        packets_by_path: dict[str, list[str]] = {}
        for packet in (ledger.get("packets") or {}).get("packets") or []:
            packets_by_path.setdefault(packet["path"], []).append(packet["packet_id"])
        batches: dict[str, dict[str, Any]] = {}
        tasks: dict[str, TaskRecord] = {}
        current_ids: list[str] = []
        current_chars = 0
        current_packets: set[str] = set()
        frozen_inventory = Inventory.from_dict(ledger["inventory"])
        source_cache: dict[str, Any] = {}
        starts_cache: dict[str, tuple[int, ...]] = {}

        def attribution_prompt_tokens(ids: list[str]) -> int:
            spans: dict[str, list[CharSpan]] = {}
            assignments = []
            policy = (ledger.get("documentation_policy") or {}).get("symbols") or {}
            for sid in sorted(ids):
                symbol = symbols[sid]
                path = symbol["path"]
                if path not in source_cache:
                    source_cache[path] = load_frozen_offsets(Path(ledger["repo_root"]), path,
                                                            frozen_inventory.files[path])
                    starts_cache[path] = line_starts(source_cache[path].text)
                owned = symbol.get("exclusive_spans") or [symbol["span"]]
                spans.setdefault(path, []).extend(CharSpan.from_dict(span) for span in owned)
                assignments.append({"symbol_id": sid, "canonical_symbol_id": sid,
                    "name": symbol["qualified_name"], "kind": symbol["kind"],
                    "source_path": path, "start_line": bisect_right(starts_cache[path], owned[0]["start"]),
                    "tier_signal": (policy.get(sid) or {}).get("tier"),
                    "suggested_output_tokens": (policy.get(sid) or {}).get("suggested_output_tokens")})
            source = "\n\n".join(_numbered_source_span(path, span, source_cache[path].text,
                                 starts=starts_cache[path])
                                 for path in sorted(spans) for span in merge_char_spans(spans[path]))
            payload = {"instruction": _fact_instruction(True, "author"), "assignments": assignments,
                       "batch_id": "attr-batch:preview", "source": source,
                       "envelope": {"task_id": "task:fact_author:attr-batch:" + "0" * 16,
                       "generation": 100, "owner": "native-planning-controller/author",
                       "input_hash": "0" * 64, "call_id": "call:fact:" + "0" * 32}}
            return count_text_tokens(_message_projection(payload).decode()) + 500

        def exclusive_chars(symbol: dict) -> int:
            return sum(span["end"] - span["start"]
                       for span in (symbol.get("exclusive_spans") or [symbol["span"]]))

        def flush() -> None:
            nonlocal current_ids, current_chars, current_packets
            if not current_ids:
                return
            payload = {"contract": ATTRIBUTION_CONTRACT,
                       "source_revision": ledger["source_revision"],
                       "input_ids": sorted(current_ids)}
            batch_id = "attr-batch:" + _sha_json(payload)[:16]
            chars = current_chars
            packet_ids = sorted(current_packets)
            if not packet_ids:
                raise ValueError("attribution batch has no frozen packets")
            batches[batch_id] = {
                "packet_ids": packet_ids,
                "input_ids": sorted(current_ids),
                "source_chars": chars,
                "planned_review_source_chars": chars,
                "planned_source_checked_count": max(1, len(current_ids) // 10),
                "attribution": True,
                "max_input_tokens": 8000,
                "estimated_prompt_tokens": attribution_prompt_tokens(current_ids),
                "estimated_output_tokens": 120 * len(current_ids),
            }
            tasks[f"task:fact_author:{batch_id}"] = TaskRecord(
                f"task:fact_author:{batch_id}", "fact_author", sorted(current_ids),
                _sha_json(payload), "pending",
                extra={"fact_contract": ATTRIBUTION_CONTRACT, "batch_id": batch_id,
                       "packet_ids": packet_ids, "fragments": [],
                       "review_policy": "tiered-v1", "attribution": True},
            )
            current_ids = []
            current_chars = 0
            current_packets = set()

        # Small per-file residuals merge across files up to the batch char cap,
        # mirroring how executable batches group adjacent paths.
        for path in sorted(non_exec):
            file_packets = sorted(set(packets_by_path.get(path) or []))
            for sid, symbol in non_exec[path]:
                size = exclusive_chars(symbol)
                if current_ids and current_chars + size > max_batch_chars:
                    flush()
                if current_ids and attribution_prompt_tokens([*current_ids, sid]) > 8000:
                    flush()
                measured = attribution_prompt_tokens([sid])
                if measured > 8000:
                    raise PromptLayoutError(scope="attribution_author", ids=[sid], tokens=measured, cap=8000)
                current_ids.append(sid)
                current_chars += size
                current_packets.update(file_packets)
        flush()
        def mutate(inner: dict) -> dict:
            if inner.get("attribution_workflow_version"):
                return None
            if inner["source_revision"] != ledger["source_revision"]:
                raise StaleWriteError("source revision changed during attribution registration")
            for task_id, task in tasks.items():
                if task_id in inner.setdefault("tasks", {}):
                    raise ValueError(f"attribution task already exists: {task_id}")
                inner["tasks"][task_id] = task.to_dict()
            fact_batches = inner.setdefault("fact_batches", {})
            for batch_id, batch in batches.items():
                if batch_id in fact_batches:
                    raise ValueError(f"attribution batch already exists: {batch_id}")
                fact_batches[batch_id] = batch
            for sid, detail in syntax_records.items():
                if sid in inner.setdefault("details", {}) or sid in inner.setdefault("fact_reviews", {}):
                    raise ValueError(f"syntax attribution would overwrite existing fact: {sid}")
                inner["details"][sid] = detail
                inner["fact_reviews"][sid] = {
                    "state": "syntax_evidenced", "content_sha256": _sha_json(detail),
                    "source_revision": inner["source_revision"],
                    "evidence_kind": "program_syntax",
                    "frozen_content_sha256": detail["provenance"]["frozen_content_sha256"],
                }
            inner["attribution_batches"] = batches
            inner["attribution_workflow_version"] = 1
            return inner

        store.mutate(mutate)
        return {"batch_count": len(batches),
                "object_count": sum(len(b["input_ids"]) for b in batches.values()),
                "syntax_evidenced_count": len(syntax_records),
                "syntax_evidenced_ids": sorted(syntax_records),
                "source_chars": sum(b["source_chars"] for b in batches.values()),
                "already_registered": False}

    ledger = store.open()
    result = plan(ledger)
    return result


def validate_input_limit(value: int | None) -> None:
    if value is not None and (type(value) is not int or not 1000 <= value <= 24000):
        raise ValueError("max_input_tokens must be an integer within 1000..24000")


def _refresh_pending_review_draft(ledger: dict, task: TaskRecord,
                                  author: TaskRecord, full_draft: dict) -> None:
    """Reconnect a future review after a canonical rewrite in the same scope.

    The store lock is held by claim. No historical call or fact verdict changes.
    A changed source, scope, live lease or unresolved delivery cannot be rebound.
    """
    current_hash = _sha_json(full_draft)
    if task.input_hash == current_hash:
        return
    if (task.state not in {"pending", "needs_repair"} or pid_alive(task.owner_pid) or author.state != "committed"
        or not any(call.get("task_id") == task.task_id
                   and call.get("input_hash") == task.input_hash
                   and call.get("state") in {"imported", "released"}
                   for call in ledger.get("calls", {}).values())
        or len(task.input_ids) != len(set(task.input_ids))
        or len(author.output_refs) != len(set(author.output_refs))
        or set(task.input_ids) != set(author.output_refs)
        or any(sid not in ledger.get("inventory", {}).get("symbols", {})
               or not isinstance(full_draft.get(sid), dict) for sid in task.input_ids)
        or any(call.get("task_id") == task.task_id and call.get("state") in {"prepared", "sent", "uncertain", "durable"}
               for call in ledger.get("calls", {}).values())):
        raise StaleWriteError("fact draft changed before review; only same-scope unleased reviews with terminal historical calls may refresh")
    entry = {"reason": "current_canonical_draft", "source_revision": ledger["source_revision"],
             "old_input_hash": task.input_hash, "current_input_hash": current_hash,
             "old_generation": task.generation, "new_generation": task.generation + 1,
             "old_owner": task.owner, "old_call_id": task.extra.get("call_id"),
             "old_result_sha256": task.extra.get("result_sha256"),
             "input_ids": list(task.input_ids), "recorded_at": iso(utc_now())}
    task.extra.setdefault("draft_binding_history", []).append(entry)
    # A historical bounded review set cannot hide current unaccepted members
    # after another canonical writer changed the whole draft identity.
    outstanding = {sid for sid in task.input_ids if not accepted_fact(ledger, sid)}
    task.extra["required_review_ids"] = sorted(set(task.extra.get("required_review_ids") or []) | outstanding)
    task.input_hash = current_hash
    task.generation += 1
    task.owner = None
    task.owner_pid = None
    task.lease_until = None
    task.extra.pop("call_id", None)
    task.extra.pop("packet_hash", None)
    task.extra.pop("result_sha256", None)
    # Existing per-fact checks, residuals and canonical lineage stay bound to
    # their original hashes. Claim selects only unsatisfied current facts.


def claim(run_dir: Path, packet_id: str, *, owner: str, kind: str = "author",
          review_ids: list[str] | None = None,
          full_context: bool = False,
          review_question: str | None = None,
          require_behavior_contract: bool = False,
          max_input_tokens: int | None = None,
          _workflow_initialized: bool = False,
          _defer_local_ready: bool = False) -> dict[str, Any]:
    """Prepare one immutable author/review packet and reserve its source read."""
    run_dir = Path(run_dir).resolve()
    validate_input_limit(max_input_tokens)
    if kind not in {"author", "review"} or not owner.strip():
        raise ValueError("kind must be author or review, and owner must be nonempty")
    if review_question and kind != "review":
        raise ValueError("review_question applies only to review claims")
    if not _workflow_initialized:
        initialize(run_dir)
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}
    prepared_artifacts: list[tuple[Path, bytes]] = []

    def mutate(ledger: dict) -> dict:
        if not ledger.get("fact_workflow_version"):
            raise StaleWriteError("fact workflow initialization changed before claim")
        selected_review_ids = review_ids
        question = review_question
        packets = _batch_packets(ledger, packet_id)
        batched = packet_id in (ledger.get("fact_batches") or {})
        packet = packets[0]
        # The batch record is the authoritative attribution source: review
        # tasks created before the flag propagated carry no extra marker, and
        # without it a review claim presents executable-packet spans and the
        # executable contract instead of each object's exclusive spans.
        batch_attribution = bool(
            (ledger.get("fact_batches") or {}).get(packet_id, {}).get("attribution")
        ) or packet_id.startswith("attr-")
        author_id = f"task:fact_author:{packet_id}"
        author = TaskRecord.from_dict(ledger["tasks"][author_id])
        if kind == "author":
            _validate_author_input(ledger, author, packets)
        task_id = author_id if kind == "author" else f"task:fact_review:{packet_id}"
        if kind == "review":
            if author.state != "committed":
                raise LeaseError("fact review requires an imported author batch")
            raw = ledger["tasks"].get(task_id)
            if raw is None:
                raise LeaseError("fact review has not been queued")
            task = TaskRecord.from_dict(raw)
            if selected_review_ids is None:
                selected_review_ids = task.extra.get("reader_audit_ids")
            if question is None:
                question = task.extra.get("reader_question")
            supplemental_audit = selected_review_ids is not None and (
                task.state == "committed" or bool(task.extra.get("audit_mode"))
            )
            if task.state == "committed" and not supplemental_audit:
                raise LeaseError(f"{task_id} already committed; explicit review_ids are required for an audit")
            full_draft = {sid: ledger["details"][sid] for sid in author.output_refs}
            _refresh_pending_review_draft(ledger, task, author, full_draft)
            reviews = ledger.get("fact_reviews") or {}
            target_ids = [
                sid for sid in task.input_ids
                if not (
                    (reviews.get(sid) or {}).get("state") == "source_checked"
                    and (reviews.get(sid) or {}).get("content_sha256") == _sha_json(full_draft[sid])
                )
            ]
            # Refresh-carried accepted facts (either accepted state, hash-bound)
            # keep their earlier acceptance and are not re-reviewed by default.
            required_now = set(task.extra.get("required_review_ids") or [])
            # Repair/audit obligations survive historical re-sampling bugs.
            required_now.update(repair_review_ids(ledger, author) & set(task.input_ids))
            required_now.update(sid for sid in task.extra.get("audit_review_ids") or [] if sid in task.input_ids)
            required_now.update(finding["symbol_id"] for finding in task.residual
                                if isinstance(finding, dict) and finding.get("symbol_id") in task.input_ids)
            task.extra["required_review_ids"] = sorted(required_now)
            target_ids = [sid for sid in target_ids
                          if sid in required_now or not accepted_fact(ledger, sid)]
            # One authority for both the automatic presentation and its bounded
            # subset retries. Historical residuals can survive a rejected raw
            # result even after the same draft fact was independently checked.
            # Keep their history/required IDs, but never re-add a satisfied fact
            # to the current unresolved presentation.
            pending_review_ids = set(target_ids)
            if selected_review_ids is None and batched:
                required = task.extra.get("required_review_ids")
                target_ids = ([sid for sid in required if sid in target_ids]
                              if required is not None else _tiered_review_ids(ledger, packets, target_ids))
                if (task.extra.get("attribution") or batch_attribution) and not target_ids:
                    target_ids = [min(task.input_ids,
                                      key=lambda sid: hashlib.sha256(sid.encode()).hexdigest())]
                for finding in task.residual:
                    if isinstance(finding, dict) and finding.get("symbol_id") in pending_review_ids and (
                        finding["symbol_id"] not in target_ids
                    ):
                        target_ids.append(finding["symbol_id"])
            if selected_review_ids is not None:
                allowable = set(task.input_ids) if supplemental_audit else pending_review_ids
                if not selected_review_ids or len(selected_review_ids) != len(set(selected_review_ids)) or not set(selected_review_ids) <= allowable:
                    raise ValueError("review_ids must be a nonempty subset of current fact IDs")
                target_ids = list(selected_review_ids)
            delegated = {sid for sid, delegated_id in (task.extra.get("canonical_delegations") or {}).items()
                         if (ledger.get("tasks", {}).get(delegated_id) or {}).get("state") != "committed"
                         or accepted_fact(ledger, sid)}
            target_ids = [sid for sid in target_ids if sid not in delegated]
            if supplemental_audit:
                task.extra["audit_mode"] = True
                task.extra["audit_review_ids"] = sorted(set(task.extra.get("audit_review_ids") or []) | set(selected_review_ids or []))
                task.extra["required_review_ids"] = sorted(required_now | set(selected_review_ids or []))
            if task.extra.get("reader_audit_ids"):
                task.extra.pop("reader_audit_ids", None)
                task.extra.pop("reader_question", None)
            if not target_ids:
                raise LeaseError("fact review has no unresolved source-check targets; use explicit review_ids for a new audit")
            draft = full_draft
        else:
            if selected_review_ids is not None:
                raise ValueError("review_ids apply only to review claims")
            task = author
            draft = None
            if task.extra.get("repair_ids"):
                # A targeted repair keeps its exact symbol scope.
                target_ids = list(task.extra["repair_ids"])
                draft = {sid: ledger["details"][sid] for sid in target_ids
                         if sid in ledger.get("details", {})} or None
            else:
                target_ids = [sid for sid in task.input_ids if not accepted_fact(ledger, sid)]
                if not target_ids:
                    raise LeaseError(
                        f"{task_id} is fully satisfied by accepted facts; "
                        "use a review audit or explicit repair to revisit it"
                    )
            target_ids = [sid for sid in target_ids if sid not in (task.extra.get("canonical_delegations") or {})]
            if not target_ids:
                raise LeaseError("fact scope delegated to its canonical composition")
        if task.state == "stale":
            raise StaleWriteError(f"fact task {task_id} was superseded")
        if max_input_tokens is not None and (task.state not in {"pending", "needs_repair"}
            or any(c.get("task_id") == task_id and c.get("state") in {"prepared", "sent", "uncertain", "durable"}
                   for c in ledger.get("calls", {}).values())):
            raise LeaseError("input limit applies only to fresh unclaimed tasks; reconcile existing calls first")
        if task.state == "committed" and not (kind == "review" and task.extra.get("audit_mode")):
            raise LeaseError(f"{task_id} already committed")
        composition = author.extra.get("canonical_composition") or {}
        if composition:
            from cbe.behavior_contracts import digest
            for sid, expected in composition["prior_detail_hashes"].items():
                if (kind != "review" or not composition.get("prior_details")) and digest(ledger["details"].get(sid)) != expected:
                    raise StaleWriteError("canonical composition input changed")
            if kind == "author":
                draft = composition.get("prior_details") or {sid: ledger["details"][sid] for sid in composition["fragment_ids"]}
        now = utc_now()
        if task.state == "leased" and task.lease_until and task.lease_until > iso(now):
            raise LeaseError(f"{task_id} leased by {task.owner}")
        inventory = Inventory.from_dict(ledger["inventory"])
        offsets_by_path = {
            path: load_frozen_offsets(Path(ledger["repo_root"]), path, inventory.files[path])
            for path in {item.path for item in packets}
        }
        fragment_map = {fragment.output_id: (item, fragment) for item in packets
                        for fragment in item.fragments}
        packet_by_id = {fragment.output_id: item for item in packets
                        for fragment in item.fragments}
        symbols = ledger["inventory"]["symbols"]
        attribution = bool(task.extra.get("attribution")) or batch_attribution
        spans_by_path: dict[str, list[CharSpan]] = {}
        if composition:
            for sid in target_ids:
                symbol = symbols[sid]
                span = symbol["span"]
                spans_by_path.setdefault(symbol["path"], []).append(CharSpan(span["start"], span["end"]))
        elif attribution:
            # Attribution assignments are presented through each object's
            # frozen exclusive span (class-level and module-level statements),
            # not through the executable packet spans.
            for sid in target_ids:
                symbol = symbols[sid]
                for span in (symbol.get("exclusive_spans") or [symbol["span"]]):
                    spans_by_path.setdefault(symbol["path"], []).append(
                        CharSpan(span["start"], span["end"]))
            offsets_by_path = {
                **offsets_by_path,
                **{path: load_frozen_offsets(Path(ledger["repo_root"]), path, inventory.files[path])
                   for path in spans_by_path if path not in offsets_by_path},
            }
        else:
            for item in packets:
                offsets = offsets_by_path[item.path]
                if kind == "author" and (full_context or (
                    set(target_ids) == set(task.input_ids) and not task.extra.get("split_from"))):
                    spans = tuple(item.spans)
                else:
                    narrowed: list[CharSpan] = []
                    for sid in target_ids:
                        if packet_by_id.get(sid) != item:
                            continue
                        fragment = fragment_map[sid][1]
                        narrowed.extend(fragment.owned_spans)
                    spans = merge_char_spans(narrowed)
                    if kind == "review":
                        selected_canonical = [fragment_map[sid][1].symbol_id for sid in target_ids
                                              if packet_by_id.get(sid) == item]
                        spans = merge_char_spans([*spans, *_review_context_spans(
                            ledger, item.path, selected_canonical, offsets.text)])
                if spans:
                    spans_by_path.setdefault(item.path, []).extend(spans)
        if kind == "review" and not attribution:
            # A partition's owned spans omit nested executable children. The
            # author's prose can still depend on the enclosing function's
            # ordered behavior, so a direct review sees its full symbol span.
            for sid in target_ids:
                canonical = fragment_map[sid][1].symbol_id if sid in fragment_map else sid
                symbol = symbols.get(canonical)
                if symbol and symbol["path"] in inventory.files:
                    span = symbol["span"]
                    spans_by_path.setdefault(symbol["path"], []).append(
                        CharSpan(span["start"], span["end"]))
            # Direct graph dependencies may live in another enrolled file.
            # Show their complete frozen symbol spans, with no arbitrary prefix.
            canonical_ids = {fragment_map[sid][1].symbol_id for sid in target_ids
                             if sid in fragment_map}
            for edge in (ledger.get("graph") or {}).get("edges") or []:
                if edge.get("subject_id") not in canonical_ids:
                    continue
                target = symbols.get(edge.get("target_id"))
                if not target or target["path"] not in inventory.files:
                    continue
                path = target["path"]
                if path not in offsets_by_path:
                    offsets_by_path[path] = load_frozen_offsets(
                        Path(ledger["repo_root"]), path, inventory.files[path])
                span = target["span"]
                spans_by_path.setdefault(path, []).append(CharSpan(span["start"], span["end"]))
        requested_context: list[dict[str, Any]] = []
        requested_spans: dict[str, list[CharSpan]] = {}
        fact_view_candidates: dict[str, dict[str, list[CharSpan]]] = {}
        # A changed draft invalidates semantic acceptance, not frozen source.
        # Carry only the per-fact evidence actually shown in the same revision.
        support = task.extra.get("repair_source_views") or {}
        for sid in target_ids:
            view = support.get(sid) or {}
            if view.get("source_revision") != ledger["source_revision"]:
                continue
            for span in view.get("spans") or []:
                path = span.get("path")
                if path not in inventory.files:
                    continue
                if path not in offsets_by_path:
                    offsets_by_path[path] = load_frozen_offsets(
                        Path(ledger["repo_root"]), path, inventory.files[path])
                start, end = span.get("start"), span.get("end")
                if (type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(offsets_by_path[path].text)):
                    raise ValueError("invalid frozen repair source view")
                spans_by_path.setdefault(path, []).append(CharSpan(start, end))
        if kind == "review":
            for finding in task.residual:
                if not isinstance(finding, dict):
                    continue
                if finding.get("symbol_id") and finding["symbol_id"] not in target_ids:
                    continue
                needed = finding.get("needed_source")
                if not isinstance(needed, dict):
                    continue
                path = needed.get("path")
                if not isinstance(path, str) or path not in inventory.files:
                    # A reviewer may name an unenrolled path it never saw
                    # enrolled. The frozen envelope cannot present it; keep
                    # the finding and skip only the context request instead of
                    # dead-ending every later resume round of the batch.
                    continue
                if path not in offsets_by_path:
                    offsets_by_path[path] = load_frozen_offsets(Path(ledger["repo_root"]), path,
                                                                inventory.files[path])
                starts = line_starts(offsets_by_path[path].text)
                start_line, end_line = needed.get("start_line"), needed.get("end_line")
                if type(start_line) is not int or type(end_line) is not int:
                    continue
                # Reviewers routinely overestimate file length (lines past
                # EOF). Clamp the request into the frozen bounds instead of
                # raising: a hard failure here makes every later review round
                # of the batch fail deterministically before any model call.
                # A request that lies entirely outside the file is dropped.
                start_line = max(1, min(start_line, len(starts)))
                end_line = min(end_line, len(starts))
                if start_line > end_line:
                    continue
                start = starts[start_line - 1]
                end = starts[end_line] if end_line < len(starts) else len(offsets_by_path[path].text)
                if end - start > 5000 and not full_context:
                    seen = [CharSpan(span["start"], span["end"])
                            for prior in ledger.get("calls", {}).values()
                            if prior.get("task_id") == task_id
                            and (prior.get("extra") or {}).get("draft_sha256") == task.input_hash
                            and (prior.get("extra") or {}).get("send_evidence") in {"sent_native", "sent_http"}
                            for span in prior.get("source_spans") or [] if span["path"] == path]
                    original_start, original_end = start_line, end_line
                    start_line, end_line = _requested_review_window(
                        offsets_by_path[path].text, start_line, end_line, seen,
                        sid=finding.get("symbol_id"), path=path)
                    start = starts[start_line - 1]
                    end = starts[end_line] if end_line < len(starts) else len(offsets_by_path[path].text)
                    requested_context.append({"path": path, "requested_start_line": original_start,
                                              "requested_end_line": original_end,
                                              "start_line": start_line, "end_line": end_line,
                                              "remaining_start_line": end_line + 1 if end_line < original_end else None,
                                              "historical_windows_are_not_current_evidence": True})
                spans_by_path.setdefault(path, []).append(CharSpan(start, end))
                requested_spans.setdefault(path, []).append(CharSpan(start, end))
                # Record the honored (clamped) span so the reviewer sees the
                # exact context it received, not the range it invented.
                requested_context.append(
                    {"path": path, "start_line": start_line, "end_line": end_line})
            for sid in target_ids:
                canonical = fragment_map[sid][1].symbol_id if sid in fragment_map else sid
                symbol = symbols[canonical]
                path = symbol["path"]
                own = (symbol.get("exclusive_spans") or [symbol["span"]]) if attribution else [symbol["span"]]
                relevant: dict[str, list[CharSpan]] = {
                    path: [CharSpan(span["start"], span["end"]) for span in own]
                }
                if not attribution:
                    relevant[path].extend(_review_context_spans(
                        ledger, path, [canonical], offsets_by_path[path].text))
                    for edge in (ledger.get("graph") or {}).get("edges") or []:
                        if edge.get("subject_id") != canonical:
                            continue
                        target = symbols.get(edge.get("target_id"))
                        if target and target["path"] in inventory.files:
                            span = target["span"]
                            relevant.setdefault(target["path"], []).append(
                                CharSpan(span["start"], span["end"]))
                for ref in ((draft or {}).get(sid, {}).get("provenance") or {}).get("source_refs") or []:
                    ref_path, line = ref.get("path"), ref.get("line")
                    if ref_path not in inventory.files or type(line) is not int:
                        continue
                    if ref_path not in offsets_by_path:
                        offsets_by_path[ref_path] = load_frozen_offsets(
                            Path(ledger["repo_root"]), ref_path, inventory.files[ref_path])
                    text_starts = line_starts(offsets_by_path[ref_path].text)
                    if 1 <= line <= len(text_starts):
                        relevant.setdefault(ref_path, []).append(CharSpan(
                            text_starts[line - 1],
                            text_starts[line] if line < len(text_starts)
                            else len(offsets_by_path[ref_path].text)))
                for finding in task.residual:
                    if isinstance(finding, dict) and finding.get("symbol_id") == sid:
                        for ref_path, spans in requested_spans.items():
                            relevant.setdefault(ref_path, []).extend(spans)
                fact_view_candidates[sid] = relevant
            previous_view = task.extra.get("view_spans") or []
            previous_scope = set(task.extra.get("assigned_ids") or [])
            prior_relevant: dict[str, list[CharSpan]] = {}
            if previous_view:
                mapped = task.extra.get("view_spans_by_fact") or {}
                mapped_all = all(
                    (mapped.get(sid) or {}).get("source_revision") == ledger["source_revision"]
                    and (mapped.get(sid) or {}).get("detail_sha256") == _sha_json(draft[sid])
                    for sid in target_ids
                )
                if mapped_all:
                    for sid in target_ids:
                        for old in mapped[sid]["spans"]:
                            prior_relevant.setdefault(old["path"], []).append(
                                CharSpan(old["start"], old["end"]))
                elif set(target_ids) == previous_scope:
                    # Same assigned scope: the complete prior view is cumulative.
                    for old in previous_view:
                        path = old.get("path")
                        if path in inventory.files:
                            prior_relevant.setdefault(path, []).append(
                                CharSpan(old["start"], old["end"]))
                else:
                    # A resolved batch narrows to remaining IDs. Preserve all
                    # previously shown evidence relevant to those IDs; the
                    # nine already checked facts need no second presentation.
                    target_paths = {
                        symbols[fragment_map[sid][1].symbol_id if sid in fragment_map else sid]["path"]
                        for sid in target_ids
                    }
                    for old in previous_view:
                        path = old.get("path")
                        if path in target_paths:
                            # Historical batch views had no per-fact map. Keep
                            # all previously displayed spans of that fact's
                            # file; context there may bear on its assertions.
                            prior_relevant.setdefault(path, []).append(
                                CharSpan(old["start"], old["end"]))
                            continue
                        for current in merge_char_spans(spans_by_path.get(path) or []):
                            start = max(old["start"], current.start)
                            end = min(old["end"], current.end)
                            if end > start:
                                prior_relevant.setdefault(path, []).append(CharSpan(start, end))
                for path, spans in prior_relevant.items():
                    if path not in offsets_by_path:
                        offsets_by_path[path] = load_frozen_offsets(
                            Path(ledger["repo_root"]), path, inventory.files[path])
                    spans_by_path.setdefault(path, []).extend(spans)
        presentation = {path: merge_char_spans(spans) for path, spans in spans_by_path.items()}
        spans_out = [{"path": path, "start": span.start, "end": span.end}
                     for path, spans in presentation.items() for span in spans]
        fact_view_updates: dict[str, dict[str, Any]] = {}
        if kind == "review":
            for sid, candidates in fact_view_candidates.items():
                relevant: dict[str, list[CharSpan]] = {}
                for path, spans in candidates.items():
                    for span in merge_char_spans(spans):
                        for shown in presentation.get(path) or ():
                            start, end = max(span.start, shown.start), min(span.end, shown.end)
                            if end > start:
                                relevant.setdefault(path, []).append(CharSpan(start, end))
                if len(target_ids) == 1:
                    for path, spans in prior_relevant.items():
                        relevant.setdefault(path, []).extend(spans)
                fact_view_updates[sid] = {
                    "source_revision": ledger["source_revision"],
                    "detail_sha256": _sha_json(draft[sid]),
                    "spans": [{"path": path, "start": span.start, "end": span.end}
                              for path, spans in relevant.items()
                              for span in merge_char_spans(spans)],
                }
        prior_chars = sum(span.length for spans in (prior_relevant.values() if kind == "review" else ())
                          for span in merge_char_spans(spans))
        view_delta_chars = max(0, sum(span["end"] - span["start"] for span in spans_out) - prior_chars)
        if kind == "review" and task.state == "needs_repair" and task.extra.get("view_spans"):
            previous_chars = prior_chars
            current_chars = sum(span["end"] - span["start"] for span in spans_out)
            requested_new = sum(
                max(0, span.length - sum(
                    max(0, min(span.end, old.end) - max(span.start, old.start))
                    for old in merge_char_spans(prior_relevant.get(path) or [])
                ))
                for path, spans in requested_spans.items() for span in merge_char_spans(spans)
            )
            if (task.extra.get("view_draft_hash") == task.input_hash
                and ((requested_spans and requested_new == 0)
                     or (not requested_spans and set(target_ids) == previous_scope
                         and current_chars <= previous_chars))):
                raise ReviewNonprogressError([
                    sid for sid in target_ids if any(
                        isinstance(finding, dict) and finding.get("symbol_id") == sid
                        and isinstance(finding.get("needed_source"), dict)
                        for finding in task.residual)
                ] or target_ids)
        source = "\n\n".join(
            _numbered_source_span(path, span, offsets_by_path[path].text)
            for path, spans in sorted(presentation.items()) for span in spans
        )
        callable_syntax = contracts_for(ledger, [fragment_map[sid][1].symbol_id
                                                if sid in fragment_map else sid for sid in target_ids])
        assignments = []
        from cbe.syntax_facts import assignment_facts
        for sid in target_ids:
            item = packet_by_id.get(sid, packet)
            canonical = fragment_map[sid][1].symbol_id if sid in fragment_map else sid
            symbol = symbols.get(canonical)
            if symbol is None:
                raise ValueError(f"fact task has no frozen symbol: {sid}")
            path = symbol["path"] if attribution else item.path
            start = ((symbol.get("exclusive_spans") or [symbol["span"]])[0]["start"] if attribution
                     else fragment_map[sid][1].owned_spans[0].start if sid in fragment_map
                     else symbol["span"]["start"])
            assignments.append({
                "symbol_id": sid, "canonical_symbol_id": canonical,
                "name": symbol["qualified_name"], "kind": symbol["kind"],
                "source_path": path,
                "explanation_scope": "canonical" if sid == canonical else "owned_span_delta",
                **({"owned_spans": [span.to_dict() for span in fragment_map[sid][1].owned_spans]}
                   if sid != canonical else {}),
                **({"callable_syntax": prompt_contract(callable_syntax[canonical])}
                   if canonical in callable_syntax else {}),
                **assignment_facts(ledger, canonical,
                    [span.to_dict() for span in fragment_map[sid][1].owned_spans] if sid in fragment_map else
                    [span.to_dict() for span in presentation.get(path, [])]),
                "start_line": bisect_right(line_starts(offsets_by_path[path].text), start),
                "tier_signal": ((ledger.get("documentation_policy") or {}).get("symbols") or {}).get(
                    canonical, {}
                ).get("tier"),
                "suggested_output_tokens": (behavior_token_recommendation(
                    ((ledger.get("documentation_policy") or {}).get("symbols") or {}).get(canonical, {}),
                    callable_syntax.get(canonical)) if kind == "author" else
                    ((ledger.get("documentation_policy") or {}).get("symbols") or {}).get(canonical, {}).get("suggested_output_tokens")),
            })
        task.generation += 1
        task.state = "leased"
        task.owner = owner
        task.owner_pid = None
        task.lease_until = iso(now + timedelta(hours=1))
        call_id = f"call:fact:{uuid.uuid4().hex}"
        envelope = {"task_id": task_id, "generation": task.generation, "owner": owner,
                    "input_hash": task.input_hash, "call_id": call_id}
        instruction = _fact_instruction(attribution, kind)
        if kind == "author" and not attribution:
            instruction += (
                " Each canonical ID has one authoritative explanation. For owned_span_delta, "
                "describe only conditions/effects/failures owned by its spans; larger evidence views "
                "do not grant ownership of the full function. Shared rules belong in one owner's "
                "behavior_contract.claims [{id,condition,effect,failure}]; other objects use "
                "claim_refs [{symbol_id,claim_id}] and only unique behavior deltas; code binds hashes. "
                "Keep local_view_gaps [{dependency_id,reason}] separate from current_unresolved. "
                "Do not repeat signatures or shared rules. Omit a literal template only when "
                "the program already publishes its exact declaration authority; otherwise keep "
                "the contract-bearing diagnostic once in its owner claim."
            )
            instruction += (
                " Required new writing shape: items[i].behavior is only the object's short role and unique "
                "delta; items[i].behavior_contract has claims, claim_refs, local_view_gaps and current_unresolved. "
                "Put each source-backed maintenance condition/effect/failure once in claims, not again in behavior. "
                "Example: {behavior:'Selects a budget.',behavior_contract:{claims:[{id:'selection',"
                "condition:'<source-backed condition>',effect:'<source-backed effect>',failure:'<if evidenced>'}],"
                "claim_refs:[],local_view_gaps:[],current_unresolved:[]}}. This example is shape only. "
                "Use a shown accepted owner's symbol_id/claim_id for genuinely shared rules; never invent an owner. "
                "Copy both IDs from that owner's displayed claims. Empty or omitted claims means no claimable IDs. "
                "A dependency_id/reason object belongs only in local_view_gaps, never claim_refs. "
                "Bound accepted dependency facts may supply missing local evidence, but static links alone never "
                "prove runtime execution; preserve genuinely unresolved relations."
            )
        if kind == "review" and not attribution:
            instruction += (
                " Review behavior together with behavior_contract: check every owned condition/effect/failure, "
                "all material branches, fields, empty-input and priority rules. Check claim_refs against shown "
                "same-version accepted owners; check local_view_gaps separately from current_unresolved. "
                "A bound accepted dependency can supply its reviewed fact, while a static reference cannot "
                "establish runtime execution. Report repeated shared rules or duplicated claim prose as a "
                "writing finding without deleting maintenance obligations."
            )
        if composition:
            from cbe.behavior_contracts import obligations, finding_obligations
            if kind == "author":
                if task.extra.get("context_reconciliation_decision"):
                    instruction += " Operator's targeted revision scope (not a semantic verdict): " + task.extra["context_reconciliation_decision"]["reason"]
                instruction += (
                    " This is a canonical composition, not concatenation: produce one behavior "
                    "and behavior_contract. Preserve all old maintenance obligations via coverage "
                    "{old_id:{claims:[local_claim_id or unique_delta]}}; code binds old hashes. "
                    "Semantic equivalence of each mapping is subject to independent review. "
                    "Old local evidence gaps may be resolved only from the shown source or bound "
                    "accepted dependency evidence; genuine unknowns remain current_unresolved. "
                    "Old obligations: " + json.dumps({**obligations(draft), **finding_obligations(composition.get("findings") or [])}, separators=(",", ":"))
                )
                example_key = next(iter({**obligations(draft), **finding_obligations(composition.get("findings") or [])}), "<exact Old obligations ID>")
                instruction += (
                    " Coverage location is binding: items[i].behavior_contract.coverage, never items[i].coverage. "
                    "Minimal placement example (replace prose and map EVERY complete Old obligations key): "
                    + json.dumps({"items": [{"symbol_id": "<assigned canonical ID>", "behavior": "<unique behavior delta>",
                        "source_refs": [{"symbol_id": "<assigned canonical ID>"}], "behavior_contract": {
                            "claims": [{"id": "c1", "condition": "<source-backed condition>", "effect": "<source-backed effect>"}],
                            "coverage": {example_key: {"claims": ["c1"]}}, "current_unresolved": []}}]}, separators=(",", ":"))
                    + " Each coverage claims array contains only existing local claim IDs, literal unique_delta, "
                      "or current_unresolved:<zero-based index>. Keep field suffixes such as :behavior; "
                      "finding IDs include their full hash. Do not put explanatory prose in claims arrays. "
                      "The code supplies old hashes; mapping shape alone does not prove semantic coverage."
                )
            else:
                instruction += " Verify the canonical coverage mapping preserves every old condition, failure and effect; mappings alone are not evidence of equivalence."
        canonical_targets = {fragment_map[sid][1].symbol_id if sid in fragment_map else sid for sid in target_ids}
        dependency_ids = {edge.get("target_id") for edge in (ledger.get("graph") or {}).get("edges") or []
                          if edge.get("subject_id") in canonical_targets and edge.get("target_id") not in canonical_targets}
        if kind == "review" and isinstance(draft, dict):
            # Shared rule ownership need not coincide with a syntactic call.
            # The reviewer consumes the exact accepted owner named by the draft.
            dependency_ids.update(ref.get("symbol_id")
                for record in draft.values()
                for ref in ((record.get("provenance") or {}).get("behavior_contract") or {}).get("claim_refs") or []
                if ref.get("symbol_id") not in canonical_targets)
        accepted_dependencies = [{"symbol_id": sid, "behavior": ledger["details"][sid]["behavior"],
                                  "review_state": ledger["fact_reviews"][sid]["state"],
                                  "source_refs": (ledger["details"][sid].get("provenance") or {}).get("source_refs") or [],
                                  "claims": ((ledger["details"][sid].get("provenance") or {}).get("behavior_contract") or {}).get("claims") or []}
                                 for sid in sorted(dependency_ids) if accepted_fact(ledger, sid)]
        payload = {"contract": ATTRIBUTION_CONTRACT if attribution else CONTRACT,
                   "behavior_contract_required": bool(require_behavior_contract and kind == "author" and not attribution),
                   "kind": kind, "source_revision": ledger["source_revision"],
                   "packet": packet.to_dict() if not batched else None,
                   "batch_id": packet_id if batched else None,
                   "packets": [item.to_dict() for item in packets] if batched else None,
                   "full_context": full_context,
                   "review_question": question,
                   "requested_context": requested_context,
                   "context_limits": ([
                       {"path": path, "automatic_context": (
                           "python_ast_and_direct_graph" if path.endswith(".py")
                           else "direct_graph_and_nearby_lines" if path.endswith((".js", ".jsx", ".ts", ".tsx"))
                           else "none"),
                        "may_omit_material_context": True,
                        **({"requested_context_windows": [window for window in requested_context
                              if window["path"] == path and "requested_start_line" in window],
                            "review_only_current_presented_source": True}
                           if any(window["path"] == path and "requested_start_line" in window
                                  for window in requested_context) else {})}
                       for path in sorted(offsets_by_path)
                   ] if kind == "review" and batched and not full_context else None),
                   "source": source, "assigned_ids": target_ids,
                   "assignments": assignments,
                   "instruction": instruction, "draft": draft,
                   "accepted_dependencies": accepted_dependencies,
                   "composition_prior": (composition.get("prior_details") or {sid: ledger["details"][sid] for sid in composition["fragment_ids"]}
                                         if composition and kind == "review" else None),
                   "composition_findings": composition.get("findings") if composition and kind == "review" else None,
                   "composition_prior_states": composition.get("prior_review_states") if composition else None,
                   "draft_projection": ([
                       {"symbol_id": sid, "behavior": record.get("behavior"),
                        "source_refs": (record.get("provenance") or {}).get("source_refs") or [],
                        **({"behavior_contract": (record.get("provenance") or {})["behavior_contract"]}
                           if (record.get("provenance") or {}).get("behavior_contract") else {}),
                        **{field: record[field] for field in (
                            "inputs_outputs", "effects", "failures", "dependencies", "unresolved")
                           if record.get(field) not in (None, "", [], {})}}
                       for sid, record in sorted(draft.items()) if sid in target_ids or composition
                   ] if draft is not None else None),
                   "repair_findings": list(task.residual),
                   "draft_content_sha256": task.input_hash if draft is not None else None,
                   "evidence_path": str(run_dir / "reviews" / f"{call_id}.md") if kind == "review" else None,
                   "envelope": envelope}
        encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
        packet_path = run_dir / "packets" / f"{call_id}.json"
        packet_hash = _sha_bytes(encoded)
        prompt_path = run_dir / "prompts" / f"{call_id}.txt"
        prompt_bytes = _message_projection(payload)
        prompt_hash = _sha_bytes(prompt_bytes)
        if batched or max_input_tokens is not None:
            planned = ledger["fact_batches"][packet_id] if batched else None
            # Native's complete wrapper differs from the provider projection.
            # Check both from this very packet before creating a claim, so the
            # existing review narrowing and repair splitting see the real cap.
            from cbe.native_handoff import _dispatch_prompt
            actual_prompt_tokens = max(count_text_tokens(prompt_bytes.decode()),
                                      count_text_tokens(_dispatch_prompt(payload, "fact").decode()))
            input_cap = max_input_tokens if max_input_tokens is not None else planned["max_input_tokens"]
            if actual_prompt_tokens > input_cap:
                raise PromptLayoutError(scope=f"{'attribution' if attribution else 'fact'}_{kind}",
                                        ids=list(target_ids), tokens=actual_prompt_tokens,
                                        cap=input_cap)
        call = CallRecord(
            call_id, task_id, task.input_hash,
            spans_out,
            sum(span["end"] - span["start"] for span in spans_out), "prepared", packet_hash=packet_hash,
            prompt_chars=len(prompt_bytes.decode("utf-8")),
            extra={"external_subagent": True, "packet_id": packet_id, "packet_path": str(packet_path),
                   "behavior_contract_required": payload["behavior_contract_required"],
                   "prompt_path": str(prompt_path), "prompt_sha256": prompt_hash,
                   "prompt_projection": "fact-text-v1", "full_context": full_context,
                   "actual_prompt_tokens": count_text_tokens(prompt_bytes.decode()),
                   "assigned_ids": list(target_ids), "draft_sha256": task.input_hash if kind == "review" else None,
                   "view_spans": spans_out, "view_sha256": _sha_json(spans_out),
                   "view_delta_chars": view_delta_chars,
                   "preparation_stage": "local_artifacts_pending",
                   **({"effective_max_input_tokens": input_cap, "planned_max_input_tokens": planned["max_input_tokens"] if batched else None} if max_input_tokens is not None else {})},
        )
        if kind == "review":
            # Preserve first presentation of still-pending author partitions.
            # Their full frozen cost is known before a reviewer consumes slack.
            future_author_chars = 0
            for pending_id, pending_raw in (ledger.get("tasks") or {}).items():
                if pending_raw.get("kind") != "fact_author" or pending_raw.get("state") != "pending":
                    continue
                if (pending_raw.get("extra") or {}).get("call_id"):
                    continue
                unit_id = pending_id.removeprefix("task:fact_author:")
                batch = (ledger.get("fact_batches") or {}).get(unit_id)
                if batch and not batch.get("superseded"):
                    future_author_chars += int(batch["source_chars"])
                elif not batch:
                    future_author_chars += _packet(ledger, unit_id).source_chars
            policy = ledger.get("budget_policy") or {}
            ok, reason = can_reserve(
                int(ledger["inventory"]["s_chars"]), ledger.get("calls") or {},
                call.source_chars + future_author_chars,
                cap_multiplier=policy.get("source_read_cap_multiplier"),
                strict=(ledger.get("documentation_policy") or {}).get("budget_mode") != "report",
            )
            if not ok:
                raise BudgetError(
                    f"review would spend unpresented author source reserve={future_author_chars}; {reason}")
        reserve_call(ledger, call)
        # All layout, source-budget and claim validations precede publication.
        # Rejected preparation cannot leave an unbound consumable packet.
        prepared_artifacts.extend([(packet_path, encoded), (prompt_path, prompt_bytes)])
        task.extra["call_id"] = call_id
        task.extra["packet_hash"] = packet_hash
        task.extra["assigned_ids"] = list(target_ids)
        if kind == "review":
            task.extra["view_spans"] = spans_out
            task.extra["view_sha256"] = _sha_json(spans_out)
            task.extra["view_draft_hash"] = task.input_hash
            task.extra.setdefault("view_spans_by_fact", {}).update(fact_view_updates)
            task.extra["view_delta_chars"] = view_delta_chars
        ledger["tasks"][task_id] = task.to_dict()
        output.update({"task_id": task_id, "call_id": call_id, "envelope": envelope,
                       "packet_path": str(packet_path), "packet_sha256": packet_hash,
                       "prompt_path": str(prompt_path), "prompt_sha256": prompt_hash,
                       "result_path": str(run_dir / "raw" / f"{call_id}.json")})
        if max_input_tokens is not None:
            output["effective_max_input_tokens"] = input_cap
        return ledger

    store.mutate(mutate)
    # Persist the binding first. A crash/file failure leaves a recognizable
    # prepared call for reconciliation, never an unbound consumable artifact.
    finalize_local_preparation(run_dir, output, prepared_artifacts,
                               defer_ready=_defer_local_ready)
    return output


def finalize_local_preparation(run_dir: Path, output: dict,
                               prepared_artifacts: list[tuple[Path, bytes]],
                               *, defer_ready: bool = False) -> None:
    store = LedgerStore(run_dir)
    try:
        for path, data in prepared_artifacts:
            atomic_write_bytes(path, data)
    except OSError:
        abort_local_preparation(run_dir, output["task_id"], output["call_id"])
        raise
    if defer_ready:
        # Native offer validates these artifacts and finalizes in its locked
        # commit. Until then the durable pending binding remains recoverable.
        return
    def finalized(current: dict) -> dict:
        mark_call(current, output["call_id"], extra={"preparation_stage": "local_artifacts_ready"})
        return current
    store.mutate(finalized)


def abort_local_preparation(run_dir: Path, task_id: str, call_id: str) -> None:
    """Only pre-offer local preparation is positively known never dispatched."""
    def abort(ledger: dict) -> dict:
        call = ledger["calls"][call_id]
        extra = call.get("extra") or {}
        if call.get("state") != "prepared" or extra.get("native_handoff"):
            raise StaleWriteError("cannot abort a delivered or offered preparation")
        if extra.get("preparation_stage") != "local_artifacts_pending":
            raise StaleWriteError("local preparation is not known incomplete")
        raw = ledger["tasks"][task_id]
        if (raw.get("extra") or {}).get("call_id") != call_id:
            raise StaleWriteError("local preparation task binding changed")
        raw.update(state="pending", owner=None, lease_until=None)
        raw["extra"].pop("call_id", None)
        mark_call(ledger, call_id, state="released", extra={
            "preparation_stage": "local_artifacts_failed", "send_evidence": "not_sent_bootstrap",
            "disposition": "local_io_not_sent"})
        return ledger
    LedgerStore(run_dir).mutate(abort)


def verify_prepared_delivery_binding(ledger: dict, task_id: str, call_id: str,
                                     binding: tuple[str, str]) -> tuple[TaskRecord, dict]:
    """Verify the active claim and deterministic packet/prompt bytes.

    Both the configured provider and host-native handoff consume this exact
    check before they can mark a call as delivered.
    """
    task = TaskRecord.from_dict(ledger["tasks"][task_id])
    call = (ledger.get("calls") or {}).get(call_id)
    if call is None or call.get("state") not in {"prepared", "sent", "imported"}:
        raise StaleWriteError("task has no current prepared or imported call")
    if call.get("task_id") != task_id or binding[0] != call_id:
        raise StaleWriteError("delivery call belongs to another task")
    if task.extra.get("call_id") != call_id:
        raise StaleWriteError("delivery call is no longer the active claim")
    call_extra = call.get("extra") or {}
    expected_prompt_hash = call_extra.get("prompt_sha256") or call.get("packet_hash")
    if binding[1] != expected_prompt_hash:
        raise StaleWriteError("delivery evidence does not bind the actual prompt")
    packet_path = Path(call_extra["packet_path"])
    if _sha_bytes(packet_path.read_bytes()) != call["packet_hash"]:
        raise StaleWriteError("prepared packet bytes changed")
    prompt_path_value = call_extra.get("prompt_path")
    if prompt_path_value:
        prompt_path = Path(prompt_path_value)
        packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
        if call_extra.get("prompt_projection") == "module-text-v1":
            from cbe.module_workflow import _prompt_projection

            projected = _prompt_projection(packet_payload, task.kind)
        else:
            projected = _message_projection(packet_payload)
        if prompt_path.read_bytes() != projected:
            raise StaleWriteError("prompt differs from the deterministic packet projection")
        if _sha_bytes(prompt_path.read_bytes()) != expected_prompt_hash:
            raise StaleWriteError("prepared prompt bytes changed")
    return task, call


def mark_delivered(run_dir: Path, task_id: str, evidence_path: Path) -> dict[str, Any]:
    """Bind a successful Provider receipt to positive delivery evidence.

    Two evidence kinds are accepted, never mixed or fabricated:
    - ``native_session``: a Codex-style native session JSONL plus the provider
      receipt, verified against session/model/prompt hashes (historical path).
    - ``http_api_v1``: a provider-chain HTTP leg receipt with no native
      session. Delivery is established from the receipt's own bindings:
      requested/observed model agreement, the call id, and the prompt hash of
      the persisted deterministic prompt. No session or tool-read set is
      invented; usage missing stays an unknown cost.
    """
    run_dir = Path(run_dir).resolve()
    evidence_path = Path(evidence_path).resolve()
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict) or evidence.get("status") not in {"completed", "artifact_unverified"}:
        raise ValueError("a completed or artifact-unverified native provider receipt is required")
    attempts = [item for item in evidence.get("attempts") or []
                if isinstance(item, dict) and item.get("status") in {"success", "partial_native"}]
    if len(attempts) != 1:
        raise ValueError("provider receipt needs exactly one delivered attempt")
    attempt = attempts[0]
    partial_native = attempt.get("status") == "partial_native"
    if partial_native and evidence.get("status") != "artifact_unverified":
        raise ValueError("partial native delivery must remain artifact_unverified")
    native_path_value = str(attempt.get("native_evidence_path") or "")
    native_path = Path(native_path_value) if native_path_value else None
    use_native = native_path is not None and native_path.is_absolute() and native_path.is_file()
    observed_model = attempt.get("observed_model")
    requested_model = evidence.get("requested_model")
    delivery_extra: dict[str, Any] = {}
    if use_native:
        session_id = attempt.get("response_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("provider receipt lacks native session evidence")
        if not isinstance(observed_model, str) or not observed_model or observed_model != requested_model:
            raise ValueError("native delivery requires observed_model == requested_model")
        native_session = None
        native_model = None
        native_prompt_hashes: set[str] = set()
        with native_path.open(encoding="utf-8") as stream:
            for line in stream:
                event = json.loads(line)
                payload = event.get("payload") or {}
                if event.get("type") == "session_meta" and native_session is None:
                    native_session = payload.get("id") or payload.get("session_id")
                if event.get("type") == "turn_context":
                    native_model = payload.get("model")
                if event.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
                    for item in payload.get("content") or []:
                        if isinstance(item, dict) and isinstance(item.get("text"), str):
                            native_prompt_hashes.add(_sha_bytes(item["text"].encode()))
        if native_session != session_id or native_model != observed_model:
            raise ValueError("provider receipt disagrees with native session/model")
        delivery_kind = "native_session"
        native_path_str = str(native_path)
        send_evidence = "sent_native"
    else:
        # HTTP leg: no native session exists; bind identity from the receipt.
        if native_path_value:
            raise ValueError("receipt names a native evidence path that is not a readable absolute file")
        if not isinstance(observed_model, str) or not observed_model or observed_model != requested_model:
            raise ValueError("http delivery requires receipt observed_model == requested_model")
        response_id = attempt.get("response_id")
        session_id = (
            response_id if isinstance(response_id, str) and response_id
            else f"{attempt.get('route_id') or 'route'}@{evidence.get('started_at') or 'unknown-start'}"
        )
        native_prompt_hashes = set()
        native_path_str = None
        delivery_kind = "dsh_native_partial_v1" if partial_native else "http_api_v1"
        send_evidence = "sent_http"
        delivery_extra = {
            "response_id": response_id if isinstance(response_id, str) and response_id else None,
            "route_id": attempt.get("route_id"),
            "provider": attempt.get("provider"),
            "stop_reason": attempt.get("stop_reason"),
            "model_evidence_source": attempt.get("model_evidence_source"),
            "native_dsh_session_path": evidence.get("native_dsh_session_path"),
            "tool_event_count": attempt.get("tool_event_count"),
            "unbounded_source_gap": bool(attempt.get("tool_reads_unverified")),
        }
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        call_id = evidence.get("task_id")
        task, call = verify_prepared_delivery_binding(
            ledger, task_id, call_id, (call_id, evidence.get("prompt_sha256")))
        call_extra = call.get("extra") or {}
        expected_prompt_hash = call_extra.get("prompt_sha256") or call.get("packet_hash")
        if delivery_kind in {"http_api_v1", "dsh_native_partial_v1"}:
            stamped = call_extra.get("requested_model")
            if stamped and stamped != requested_model:
                raise StaleWriteError(
                    f"delivery model {requested_model} differs from the model stamped on this call ({stamped})"
                )
        elif expected_prompt_hash not in native_prompt_hashes:
            raise ValueError("native session did not contain the projected prompt")
        usage = copy_usage_fields(attempt.get("usage"))
        usage_reported = isinstance(usage, dict) and any(
            isinstance(usage.get(key), int) for key in ("input_tokens", "output_tokens")
        )
        if delivery_kind in {"http_api_v1", "dsh_native_partial_v1"} and not usage_reported:
            # Delivered per the receipt, cost unknown: keep it visible, never zero.
            usage = "unavailable"
        for exposure in call.get("source_exposures") or []:
            if exposure.get("event_kind") == "initial":
                exposure["role_session_id"] = session_id
                exposure["evidence_ref"] = str(native_path or evidence_path)
        next_state = "imported" if call.get("state") == "imported" else "sent"
        mark_call(ledger, call_id, state=next_state, native_path=native_path_str,
                  role_session_id=session_id, native_session_id=session_id,
                  actual_model=observed_model, usage=usage,
                  exposure_evidence="unverified" if attempt.get("tool_reads_unverified") else "complete",
                  extra={"delivery_receipt": str(evidence_path),
                         "delivery_evidence": (
                             "native_prompt_and_turn_context" if delivery_kind == "native_session"
                             else "provider_receipt_partial_native_bindings" if partial_native
                             else "provider_receipt_http_bindings"
                         ),
                         "delivery_kind": delivery_kind,
                         "send_evidence": send_evidence,
                         "provider_status": evidence["status"],
                         "usage_status": "reported" if usage_reported else "unavailable",
                         **delivery_extra})
        output.update({"task_id": task_id, "call_id": call_id, "state": next_state})
        return ledger

    store.mutate(mutate)
    return output


def _current_task(ledger: dict, task_id: str, envelope: dict) -> tuple[TaskRecord, dict]:
    raw = (ledger.get("tasks") or {}).get(task_id)
    if raw is None:
        raise ValueError(f"unknown fact task: {task_id}")
    task = TaskRecord.from_dict(raw)
    for key, value in (("task_id", task_id), ("generation", task.generation),
                       ("owner", task.owner), ("input_hash", task.input_hash),
                       ("call_id", task.extra.get("call_id"))):
        if envelope.get(key) != value:
            raise StaleWriteError(f"fact envelope {key} mismatch")
    if task.state != "leased":
        raise LeaseError(f"fact task is {task.state}, expected leased")
    call = ledger["calls"][envelope["call_id"]]
    if call["packet_hash"] != task.extra.get("packet_hash"):
        raise StaleWriteError("fact task and call packet hashes differ")
    return task, call


def _checked_items(ledger: dict, packet: Packet, ids: set[str],
                   presented_spans: list[dict],
                   items: object,
                   presented_by_path: dict[str, list[dict]] | None = None) -> list[dict]:
    if not isinstance(items, list):
        raise ValueError("fact result requires items array")
    offsets = load_frozen_offsets(Path(ledger["repo_root"]), packet.path,
                                  Inventory.from_dict(ledger["inventory"]).files[packet.path])
    starts = line_starts(offsets.text)
    symbols = ledger["inventory"]["symbols"]
    fragments = {fragment.output_id: fragment for fragment in packet.fragments}
    foreign: dict[str, tuple[Any, list[int]]] = {}
    seen: set[str] = set()
    checked: list[dict] = []
    for value in items:
        if not isinstance(value, dict):
            raise ValueError("fact item must be an object")
        sid = value.get("symbol_id")
        if sid not in ids or sid in seen:
            raise ValueError(f"unknown or repeated fact ID: {sid}")
        seen.add(sid)
        # Deterministic alias normalization: the contract prose says "concise
        # behavior" and some models emit that phrase as the key. Map it to the
        # canonical field verbatim; the raw file keeps the original shape.
        behavior = value.get("behavior")
        if behavior is None and isinstance(value.get("concise_behavior"), str):
            behavior = value["concise_behavior"]
            value = dict(value)
            value["behavior"] = behavior
            value.pop("concise_behavior", None)
        if not isinstance(behavior, str) or not behavior.strip():
            raise ValueError(f"fact {sid} needs a nonempty behavior")
        refs = value.get("source_refs")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"fact {sid} needs source_refs")
        primary_spans = (
            [(span.start, span.end) for span in fragments[sid].owned_spans]
            if sid in fragments else
            [(span["start"], span["end"]) for span in
             (symbols[sid].get("exclusive_spans") or [symbols[sid]["span"]])]
            if sid in symbols else []
        )
        own_source_cited = False
        normalized_refs: list[dict[str, Any]] = []
        for ref in refs:
            if isinstance(ref, dict) and set(ref) == {"symbol_id"}:
                if ref["symbol_id"] != sid or not primary_spans:
                    raise FactReferenceError(f"fact {sid} has an invalid source symbol reference")
                ref = {"path": packet.path, "line": bisect_right(starts, primary_spans[0][0])}
            if not isinstance(ref, dict) or type(ref.get("line")) is not int:
                raise FactReferenceError(f"fact {sid} has an invalid source_ref")
            path = ref.get("path")
            if path == packet.path:
                line = ref["line"]
                if line < 1 or line > len(starts):
                    raise FactReferenceError(f"fact {sid} source line is outside frozen file")
                char = starts[line - 1]
                next_char = starts[line] if line < len(starts) else len(offsets.text)
                if not any(span["start"] < next_char and char < span["end"] for span in presented_spans):
                    raise FactReferenceError(f"fact {sid} cites source outside its assigned packet")
                own_source_cited |= any(left < next_char and char < right for left, right in primary_spans)
                normalized_refs.append(ref)
                continue
            # Cross-file supporting evidence: allowed only for another file whose
            # numbered source was actually presented to the model in this call.
            spans_of_path = (presented_by_path or {}).get(str(path))
            if not spans_of_path:
                raise FactReferenceError(f"fact {sid} has an invalid source_ref")
            if str(path) not in foreign:
                if str(path) not in (ledger["inventory"]["files"] or {}):
                    raise FactReferenceError(f"fact {sid} cites an unenrolled source path")
                foreign_offsets = load_frozen_offsets(
                    Path(ledger["repo_root"]), str(path),
                    Inventory.from_dict(ledger["inventory"]).files[str(path)])
                foreign[str(path)] = (foreign_offsets, line_starts(foreign_offsets.text))
            foreign_starts = foreign[str(path)][1]
            line = ref["line"]
            if line < 1 or line > len(foreign_starts):
                raise FactReferenceError(f"fact {sid} source line is outside frozen file")
            char = foreign_starts[line - 1]
            next_char = foreign_starts[line] if line < len(foreign_starts) else len(foreign[str(path)][0].text)
            if not any(span["start"] < next_char and char < span["end"] for span in spans_of_path):
                raise FactReferenceError(f"fact {sid} cites cross-file source outside the presented spans")
            normalized_refs.append(ref)
        if not own_source_cited:
            raise FactReferenceError(f"fact {sid} needs a citation within its own source span")
        # Length follows risk and understanding need (tier is a hint, not a hard
        # per-record length): genuinely deep assignments get a wider bound while
        # ordinary records stay tight against template bloat.
        canonical = fragments[sid].symbol_id if sid in fragments else sid
        is_executable = (ledger["inventory"]["symbols"].get(canonical) or {}).get("kind") in {
            "function", "method", "lambda"}
        tier = ((ledger.get("documentation_policy") or {}).get("symbols") or {}).get(canonical, {}).get("tier")
        # The tier is a concise target. Publication reports the actual ratio;
        # a longer accurate fact is not rejected solely for its length.
        if not is_executable:
            record_bound = 180
        elif tier == "deep":
            record_bound = 400
        elif tier == "standard":
            record_bound = 200
        else:
            record_bound = 140
        item = dict(value)
        from cbe.syntax_facts import check_atom_refs
        atom_refs = item.pop("syntax_atom_refs", None)
        check_atom_refs(ledger, fragments[sid].symbol_id if sid in fragments else sid, atom_refs, presented_spans)
        from cbe.review_policy import check_syntax_assertions
        check_syntax_assertions(ledger, sid, item.pop("syntax_assertions", None))
        item["source_refs"] = normalized_refs
        provenance = dict(item.get("provenance") or {})
        provenance["source_refs"] = normalized_refs
        provenance["fact_contract"] = CONTRACT
        item["provenance"] = provenance
        checked.append(item)
    return checked


def _parse_model_payload(text: str) -> tuple[dict[str, Any], str]:
    """Parse the model's JSON object; tolerate a deterministic prose prefix.

    Some transports/models prefix the JSON with an evidence preamble. The raw
    file keeps the original bytes; extraction only locates the trailing JSON
    object and records how it was found. Anything that does not parse stays an
    error.
    """
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload, "direct"
    except json.JSONDecodeError:
        pass
    end = text.rfind("}")
    if end > 0:
        # The verdict object is the response's payload: scan opening braces
        # right-to-left so prose dictionaries inside the preamble are skipped.
        positions = [i for i, ch in enumerate(text[:end]) if ch == "{"]
        for start in reversed(positions[-200:]):
            try:
                payload = json.loads(text[start : end + 1])
                if isinstance(payload, dict):
                    return payload, "json_after_prose_prefix"
            except json.JSONDecodeError:
                continue
    raise ValueError("fact result must be a JSON object")


def import_result(run_dir: Path, task_id: str, result_path: Path) -> dict[str, Any]:
    """Import current author or independent review result; no self-review credit."""
    run_dir = Path(run_dir).resolve()
    result_path = Path(result_path).resolve()
    result_bytes = result_path.read_bytes()
    result_hash = _sha_bytes(result_bytes)
    payload, payload_extraction = _parse_model_payload(result_bytes.decode("utf-8"))
    if payload_extraction != "direct":
        payload["payload_extraction"] = payload_extraction
    store = LedgerStore(run_dir)
    envelope_origin = "model_echo"
    if not isinstance(payload.get("envelope"), dict):
        # A provider result may omit the echoed transport envelope. Recover only
        # from the current positively delivered claim; keep the original raw.
        current = store.open()
        task_raw = (current.get("tasks") or {}).get(task_id)
        if task_raw is None:
            raise ValueError("fact result has no task for envelope recovery")
        task = TaskRecord.from_dict(task_raw)
        call_id = task.extra.get("call_id")
        call = (current.get("calls") or {}).get(call_id) or {}
        if call.get("state") not in {"sent", "imported"} or not (call.get("extra") or {}).get("delivery_receipt"):
            raise ValueError("fact result without envelope needs positive current delivery evidence")
        recovered = {
            "task_id": task_id, "generation": task.generation,
            "owner": task.owner, "input_hash": task.input_hash, "call_id": call_id,
        }
        flat_warnings: list[str] = []
        for key, value in recovered.items():
            if key not in payload or payload[key] == value:
                continue
            if key == "task_id":
                # The reserved raw path, active claim, generation and draft hash
                # already bind this result to the task; a model typo in the
                # echoed long task id is recorded, not silently trusted.
                flat_warnings.append(
                    f"flat task_id echo mismatch: {payload[key]!r} != {value!r}")
                continue
            raise StaleWriteError(f"flat fact envelope {key} mismatch")
        payload["envelope"] = recovered
        envelope_origin = "controller_from_delivered_call"
        if flat_warnings:
            payload["envelope_flat_echo_warnings"] = flat_warnings
    envelope = payload["envelope"]
    if result_path != run_dir / "raw" / f"{envelope.get('call_id')}.json":
        raise ValueError("fact result must use its reserved raw path")
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict | None:
        incoming_call = (ledger.get("calls") or {}).get(envelope.get("call_id"), {})
        incoming_invocation = ((incoming_call.get("extra") or {}).get("native_handoff") or {}).get("invocation_id")
        if (ledger.get("native_invocations") or {}).get(incoming_invocation, {}).get("host_blocked"):
            raise StaleWriteError("host-blocked invocation cannot import fact business results")
        raw = ledger["tasks"].get(task_id)
        if raw is None:
            raise ValueError(f"unknown fact task: {task_id}")
        if raw.get("state") == "committed" and all(envelope.get(key) == raw.get(key) for key in
            ("task_id", "generation", "owner", "input_hash")
        ) and envelope.get("call_id") == (raw.get("extra") or {}).get("call_id") and (
            (raw.get("extra") or {}).get("result_sha256") == result_hash
        ):
            output.update({"task_id": task_id, "state": "committed", "idempotent": True})
            return None
        if raw.get("kind") == "fact_review" and raw.get("state") == "needs_repair" and (
            (raw.get("extra") or {}).get("result_sha256") == result_hash
        ) and all(envelope.get(key) == raw.get(key) for key in
                  ("task_id", "generation", "owner", "input_hash")):
            checked_ids = set(payload.get("checked_ids") or [])
            if not checked_ids <= set((raw.get("extra") or {}).get("assigned_ids") or []):
                raise ValueError("fact review checked IDs must have been presented in this claim")
            findings = payload.get("findings") or []
            bad_ids = {item.get("symbol_id") for item in findings if isinstance(item, dict)
                       and item.get("symbol_id") in raw.get("input_ids", [])}
            if not bad_ids:
                bad_ids = set(raw.get("input_ids") or [])
            for sid in checked_ids - bad_ids:
                current = (ledger.get("fact_reviews") or {}).get(sid)
                if current and current.get("content_sha256") == _sha_json(ledger["details"][sid]):
                    current["state"] = "source_checked"
                    current["checked_source"] = True
            output.update({"task_id": task_id, "state": "needs_repair", "idempotent": True,
                           "reconciled_source_checked": len(checked_ids - bad_ids)})
            return ledger
        task, call = _current_task(ledger, task_id, envelope)
        if call["state"] != "sent":
            raise ValueError("fact result cannot be accepted without positive delivery evidence")
        packet_id = (call.get("extra") or {}).get("packet_id")
        packets = _batch_packets(ledger, packet_id)
        batched = packet_id in (ledger.get("fact_batches") or {})
        if task.kind == "fact_author":
            from cbe.behavior_contracts import digest as behavior_digest
            composition_input = task.extra.get("canonical_composition") or {}
            for sid, expected in composition_input.get("prior_detail_hashes", {}).items():
                if behavior_digest(ledger["details"].get(sid)) != expected:
                    raise StaleWriteError("canonical composition input changed before import")
            reported_author = payload.get("author_id")
            author = task.owner
            if not author:
                raise ValueError("fact author needs a claimed owner")
            raw_items = payload.get("items")
            if not isinstance(raw_items, list):
                raise ValueError("fact result requires items array")
            if batched:
                symbols = ledger["inventory"]["symbols"]
                attribution = bool(task.extra.get("attribution"))
                if attribution:
                    # Attribution batches map each object to the packet of its
                    # own file; evidence spans are the object's exclusive spans.
                    packet_by_path = {packet.path: packet for packet in packets}
                    owner_of = {sid: packet_by_path[symbols[sid]["path"]]
                                for sid in task.input_ids}
                    exclusive_of = {
                        sid: [CharSpan(span["start"], span["end"])
                              for span in (symbols[sid].get("exclusive_spans")
                                           or [symbols[sid]["span"]])]
                        for sid in task.input_ids
                    }
                else:
                    owner_of = {sid: packet for packet in packets
                                for sid in _packet_output_ids(packet, symbols)}
                    if task.extra.get("canonical_composition"):
                        owner_of = {sid: next(packet for packet in packets if packet.path == symbols[sid]["path"])
                                    for sid in task.input_ids}
                if len(raw_items) != len({item.get("symbol_id") for item in raw_items if isinstance(item, dict)}):
                    raise ValueError("batch fact result has duplicate symbol IDs")
                presented_by_path: dict[str, list[dict]] = {}
                for span in call.get("source_spans") or []:
                    presented_by_path.setdefault(str(span.get("path")), []).append(span)
                items: list[dict] = []
                for packet in packets:
                    subset = [item for item in raw_items if isinstance(item, dict)
                              and owner_of.get(item.get("symbol_id")) == packet]
                    if attribution:
                        ids = {sid for sid in task.input_ids
                               if symbols[sid]["path"] == packet.path}
                    else:
                        ids = {sid for sid in task.input_ids if owner_of.get(sid) == packet}
                    checked = _checked_items(ledger, packet, ids,
                                             [span for span in call.get("source_spans") or []
                                              if span["path"] == packet.path], subset,
                                             presented_by_path=presented_by_path)
                    for item in checked:
                        sid = item["symbol_id"]
                        fragment = next((f for f in packet.fragments if f.output_id == sid), None)
                        item["packet_id"] = packet.packet_id
                        item["input_hash"] = task.input_hash
                        if task.extra.get("canonical_composition"):
                            item["source_spans"] = [{"path": symbols[sid]["path"], **symbols[sid]["span"]}]
                        elif attribution and fragment is None:
                            item["source_spans"] = [
                                {"path": symbols[sid]["path"], **span.to_dict()}
                                for span in exclusive_of.get(sid, [])
                            ]
                        else:
                            item["source_spans"] = [
                                {"path": packet.path, **span.to_dict()} for span in
                                (fragment.owned_spans if fragment else packet.spans)
                            ]
                    items.extend(checked)
                if len(items) != len(raw_items):
                    raise ValueError("batch fact result contains unassigned items")
            else:
                items = _checked_items(ledger, packets[0], set(task.input_ids),
                                       call.get("source_spans") or [], raw_items)
            from cbe.behavior_contracts import validate, obligations, finding_obligations, check_coverage_location
            from cbe.behavior_contracts import contract as behavior_contract, digest as behavior_digest
            composition = task.extra.get("canonical_composition") or {}
            prior = composition.get("prior_details") or {sid: ledger["details"][sid] for sid in composition.get("fragment_ids") or []}
            available_claims = {
                (sid, claim["id"]): claim
                for sid, detail in (ledger.get("details") or {}).items() if accepted_fact(ledger, sid)
                and behavior_contract(detail).get("source_revision") == ledger["source_revision"]
                for claim in behavior_contract(detail).get("claims") or []}
            for item in items:
                for claim in (item.get("behavior_contract") or {}).get("claims") or []:
                    if isinstance(claim, dict) and isinstance(claim.get("id"), str):
                        available_claims[(item["symbol_id"], claim["id"])] = claim
            for item_index, item in enumerate(items):
                check_coverage_location(item)
                value = item.pop("behavior_contract", None)
                if (call.get("extra") or {}).get("behavior_contract_required") and not isinstance(value, dict):
                    raise ValueError("new native author contract requires items[i].behavior_contract; "
                        "write owned claims/shared references and unique behavior delta, not a duplicated full prose contract")
                if isinstance(value, dict):
                    if composition:
                        expected_obligations = {**obligations(prior), **finding_obligations(composition.get("findings") or [])}
                        for old_id, mapping in (value.get("coverage") or {}).items():
                            if old_id not in expected_obligations or not isinstance(mapping, dict):
                                raise ValueError(f"unknown canonical coverage obligation at behavior_contract.coverage[{old_id!r}]; "
                                    f"expected={sorted(expected_obligations)}; include exact field suffixes and finding IDs")
                            expected_hash = expected_obligations[old_id]["content_sha256"]
                            if mapping.get("old_sha256") not in (None, expected_hash):
                                raise StaleWriteError("canonical coverage old hash mismatch")
                            mapping["old_sha256"] = expected_hash
                    for ref_index, ref in enumerate(value.get("claim_refs") or []):
                        location = f"items[{item_index}].behavior_contract.claim_refs[{ref_index}]"
                        if not isinstance(ref, dict):
                            raise ValueError(f"{location}: shared claim reference must be an object")
                        missing = [key for key in ("symbol_id", "claim_id")
                                   if not isinstance(ref.get(key), str) or not ref[key].strip()]
                        if missing:
                            hint = "; dependency_id/reason belongs in local_view_gaps" if "dependency_id" in ref or "reason" in ref else ""
                            raise ValueError(f"{location}: shared claim reference missing {', '.join(missing)}{hint}")
                        shared = available_claims.get((ref.get("symbol_id"), ref.get("claim_id")))
                        if shared is None:
                            raise ValueError(f"{location}: shared claim reference has no same-revision owner for "
                                             f"symbol_id={ref['symbol_id']!r}, claim_id={ref['claim_id']!r}; "
                                             "copy only a displayed structured owner claim ID")
                        expected_hash = behavior_digest(shared)
                        if ref.get("content_sha256") not in (None, expected_hash):
                            raise StaleWriteError("shared claim hash mismatch")
                        ref["content_sha256"] = expected_hash
                if value is not None or composition:
                    item.setdefault("provenance", {})["behavior_contract"] = validate(
                        value, symbol_id=item["symbol_id"], source_revision=ledger["source_revision"],
                        owned_spans=item.get("source_spans") or [],
                        prior=prior if composition else None,
                        prior_findings=composition.get("findings") or [])
            submitted = submit_details(
                ledger, task_id=task_id, owner=task.owner or "",
                generation=task.generation, items=items, packet=None if batched else packets[0],
                call_id=envelope["call_id"],
            )
            for sid in submitted.output_refs:
                digest = _sha_json(ledger["details"][sid])
                previous = (ledger.get("fact_reviews") or {}).get(sid) or {}
                if previous.get("content_sha256") == digest and previous.get("state") == "source_checked":
                    continue
                ledger.setdefault("fact_reviews", {})[sid] = {
                    "state": "author_fact", "content_sha256": digest,
                    "author_id": author, "author_session_id": call.get("role_session_id"),
                    "reported_author_id": reported_author,
                    "reported_author_identity_mismatch": reported_author is not None and reported_author != author,
                    "call_id": envelope["call_id"],
                }
            if submitted.state == "committed":
                draft = {sid: ledger["details"][sid] for sid in submitted.output_refs}
                review_id = f"task:fact_review:{packet_id}"
                prior_review = ledger["tasks"].get(review_id) or {}
                prior_extra = prior_review.get("extra") or {}
                review_extra = {"author_id": author,
                                "author_session_id": call.get("role_session_id")}
                if task.extra.get("repair_source_views"):
                    review_extra["repair_source_views"] = task.extra["repair_source_views"]
                required = set(
                    _tiered_review_ids(ledger, packets, list(submitted.output_refs))
                    if batched else []
                )
                if composition:
                    required.update(submitted.output_refs)
                    review_extra["canonical_composition"] = composition
                required.update(task.extra.get("repair_ids") or [])
                required.update(ref["symbol_id"] for item in items
                                for ref in ((item.get("provenance") or {}).get("behavior_contract") or {}).get("claim_refs") or []
                                if ref["symbol_id"] in submitted.output_refs)
                required.update(repair_review_ids(ledger, submitted))
                required.update(sid for sid in prior_extra.get("required_review_ids") or []
                                if not accepted_fact(ledger, sid))
                audit = [sid for sid in prior_extra.get("audit_review_ids") or []
                         if not accepted_fact(ledger, sid)]
                required.update(audit)
                pending_findings = [finding for finding in prior_review.get("residual") or []
                                    if not isinstance(finding, dict) or not finding.get("symbol_id")
                                    or not accepted_fact(ledger, finding["symbol_id"])]
                if composition.get("reconciles_review_task"):
                    # A rewrite of a known finding requires explicit resolution;
                    # none must not mechanically erase the delegated obligation.
                    pending_findings.extend(composition.get("findings") or [])
                required.update(finding["symbol_id"] for finding in pending_findings
                                if isinstance(finding, dict) and finding.get("symbol_id"))
                review_extra["required_review_ids"] = sorted(required & set(submitted.output_refs))
                if audit:
                    review_extra["audit_review_ids"] = audit
                if submitted.extra.get("attribution"):
                    # Keep the attribution marker on the review task: review
                    # claims present each object's exclusive spans and the
                    # attribution contract only under this flag.
                    review_extra["attribution"] = True
                ledger["tasks"][review_id] = TaskRecord(
                    review_id, "fact_review", list(submitted.output_refs), _sha_json(draft),
                    "pending", residual=pending_findings, extra=review_extra,
                ).to_dict()
            submitted.extra["result_sha256"] = result_hash
            ledger["tasks"][task_id] = submitted.to_dict()
            output.update({"task_id": task_id, "state": submitted.state,
                           "accepted_items": len(submitted.output_refs),
                           "residuals": submitted.residual})
        elif task.kind == "fact_review":
            author = task.extra.get("author_id")
            reported_reviewer = payload.get("reviewer_id")
            reviewer = task.owner
            reviewer_session = call.get("role_session_id")
            if (
                not isinstance(reviewer, str) or not reviewer.strip() or reviewer == author
                or not reviewer_session or reviewer_session == task.extra.get("author_session_id")
            ):
                raise ValueError("fact reviewer must be a distinct native session")
            identity_mismatch = reported_reviewer is not None and reported_reviewer != reviewer
            draft = {sid: ledger["details"][sid] for sid in task.input_ids}
            digest = _sha_json(draft)
            if digest != task.input_hash or payload.get("content_sha256") != digest:
                raise StaleWriteError("fact review content hash mismatch")
            evidence = payload.get("evidence_ref") or str(run_dir / "reviews" / f"{envelope['call_id']}.md")
            if not isinstance(evidence, str) or not Path(evidence).is_absolute() or not Path(evidence).is_file():
                raise ValueError("fact review needs an existing absolute evidence_ref")
            checked_ids = payload.get("checked_ids")
            if not isinstance(checked_ids, list) or not checked_ids or len(checked_ids) != len(set(checked_ids)):
                raise ValueError("fact review needs unique checked_ids")
            assigned_ids = set(task.extra.get("assigned_ids") or [])
            if not set(checked_ids) <= assigned_ids:
                raise ValueError("fact review checked IDs must have been presented in this claim")
            verdict = payload.get("verdict")
            if verdict not in {"accepted", "revision_required", "needs_context"}:
                raise ValueError("fact review verdict is invalid")
            findings = payload.get("findings")
            if verdict in {"revision_required", "needs_context"} and (
                not isinstance(findings, list) or not findings
            ):
                raise ValueError("fact review nonacceptance needs findings")
            bad_ids = {
                (item.get("symbol_id") or item.get("id")) for item in (findings or [])
                if isinstance(item, dict)
                and (item.get("symbol_id") or item.get("id")) in task.input_ids
            }
            if verdict == "revision_required" and not bad_ids:
                bad_ids = set(task.input_ids)
            if verdict == "needs_context":
                if not bad_ids or any(
                    not isinstance(item, dict) or
                    not isinstance(item.get("needed_source"), dict) or
                    any(key not in item["needed_source"] for key in ("path", "start_line", "end_line"))
                    for item in findings
                ):
                    raise ValueError("needs_context requires named symbol IDs and frozen line spans")
            required_ids = set(task.extra.get("required_review_ids") or [])
            if "required_review_ids" not in task.extra and batched:
                # Historical in-flight reviews predate frozen sampling. Their
                # initial checked facts and named residuals are the minimum
                # required set; do not re-sample pending ordinary IDs.
                required_ids = {
                    sid for sid in task.input_ids
                    if (ledger["fact_reviews"].get(sid) or {}).get("state") == "source_checked"
                } | bad_ids | set(checked_ids)
                task.extra["required_review_ids"] = sorted(required_ids)
            for sid in task.input_ids:
                old_review = (ledger.get("fact_reviews") or {}).get(sid) or {}
                fact_digest = _sha_json(ledger["details"][sid])
                prior_checked = (
                    old_review.get("state") == "source_checked"
                    and old_review.get("content_sha256") == fact_digest
                )
                if prior_checked and sid not in checked_ids and sid not in bad_ids:
                    continue  # Preserve the actual earlier reviewer's scope and evidence.
                if old_review.get("state") == "mechanically_validated" and sid not in checked_ids and sid not in bad_ids:
                    continue  # A sampled review does not upgrade omitted narratives.
                if old_review.get("state") in {"needs_context", "needs_repair"} and (
                    sid not in checked_ids and sid not in bad_ids
                ):
                    continue  # Omission cannot clear a known, hash-bound finding.
                if task.extra.get("audit_mode") and sid not in checked_ids and sid not in bad_ids:
                    continue  # Supplemental audit has no authority over omitted facts.
                if verdict == "accepted":
                    state = "source_checked" if sid in checked_ids or prior_checked else "author_fact"
                elif sid in bad_ids:
                    state = "needs_context" if verdict == "needs_context" else "needs_repair"
                elif sid in checked_ids or prior_checked:
                    state = "source_checked"
                else:
                    state = "author_fact"
                ledger["fact_reviews"][sid] = {
                    "state": state,
                    "content_sha256": fact_digest,
                    "author_id": (old_review.get("author_id") if old_review.get("content_sha256") == fact_digest
                                  else author), "reviewer_id": reviewer,
                    "reviewer_session_id": reviewer_session,
                    "reported_reviewer_id": reported_reviewer,
                    "reported_identity_mismatch": identity_mismatch,
                    "evidence_ref": evidence, "checked_source": sid in checked_ids,
                    "call_id": envelope["call_id"],
                }
            still_bad = {
                sid for sid in task.input_ids
                if (ledger["fact_reviews"].get(sid) or {}).get("state") in {"needs_context", "needs_repair"}
            }
            missing_required = {
                sid for sid in required_ids
                if (ledger["fact_reviews"].get(sid) or {}).get("state") != "source_checked"
                or (ledger["fact_reviews"].get(sid) or {}).get("content_sha256") != _sha_json(ledger["details"][sid])
            }
            all_checked = verdict == "accepted" and not still_bad and not missing_required
            if all_checked:
                for sid in task.input_ids:
                    review = ledger["fact_reviews"].get(sid) or {}
                    if review.get("state") == "author_fact":
                        from cbe.review_policy import mode
                        review["state"] = "mechanically_validated" if mode(ledger) is not None else "batch_accepted"
            task.state = "committed" if all_checked else "needs_repair"
            preserved_findings = []
            for sid in sorted(still_bad - bad_ids):
                prior = [finding for finding in task.residual
                         if isinstance(finding, dict) and finding.get("symbol_id") == sid]
                preserved_findings.extend(prior or [{"symbol_id": sid, "reason": "unresolved previous review finding"}])
            task.residual = list(findings or []) + preserved_findings + [{"symbol_id": sid, "reason": "required source check outstanding"}
                 for sid in sorted(missing_required - bad_ids - still_bad)]
            task.extra["result_sha256"] = result_hash
            ledger["tasks"][task_id] = task.to_dict()
            if verdict == "revision_required":
                author_task = TaskRecord.from_dict(ledger["tasks"][f"task:fact_author:{packet_id}"])
                author_task.state = "needs_repair"
                author_task.generation += 1
                author_task.owner = None
                author_task.lease_until = None
                author_task.residual = list(findings)
                author_task.extra["repair_ids"] = sorted(bad_ids)
                author_task.extra["repair_source_views"] = {
                    sid: view for sid, view in (task.extra.get("view_spans_by_fact") or {}).items()
                    if sid in bad_ids and view.get("source_revision") == ledger["source_revision"]
                }
                ledger["tasks"][author_task.task_id] = author_task.to_dict()
            output.update({"task_id": task_id, "state": task.state,
                           "source_checked": sum(
                               ledger["fact_reviews"][sid]["state"] == "source_checked"
                               for sid in task.input_ids
                           ),
                           "batch_accepted": sum(
                               ledger["fact_reviews"][sid]["state"] == "batch_accepted"
                               for sid in task.input_ids
                           ),
                           "source_examined": len(checked_ids),
                           "findings": len(findings or []),
                           "reported_identity_mismatch": identity_mismatch})
        else:
            raise ValueError(f"unsupported fact task kind: {task.kind}")
        mark_call(ledger, envelope["call_id"], state="imported", raw_path=str(result_path))
        if envelope_origin != "model_echo":
            mark_call(ledger, envelope["call_id"],
                      extra={"envelope_origin": envelope_origin,
                             "raw_result_sha256": result_hash})
        return ledger

    store.mutate(mutate)
    return output


def _validate_author_input(ledger: dict, task: TaskRecord, packets: list[Packet]) -> None:
    """Bind a claim to its planned frozen input; never bless a foreign task hash."""
    contract = task.extra.get("fact_contract")
    if contract not in {CONTRACT, ATTRIBUTION_CONTRACT}:
        raise StaleWriteError("fact author contract differs from the frozen plan")
    if task.extra.get("split_from"):
        _split_input_identity(ledger, task)
        return
    composition = task.extra.get("canonical_composition") or {}
    if composition.get("reconciles_review_task"):
        # A context repair inherits the accepted fact's original source input,
        # not the new presentation batch hash. Prior details are frozen by the
        # composition's existing digest checks before any lease is acquired.
        prior = composition.get("prior_details") or {}
        values = {detail.get("input_hash") for detail in prior.values() if detail.get("input_hash")}
        if len(values) == 1:
            expected = values.pop()
        else:
            origin = ledger.get("tasks", {}).get(composition["reconciles_review_task"]) or {}
            expected = origin.get("input_hash")
    elif contract == ATTRIBUTION_CONTRACT:
        expected = _sha_json({"contract": ATTRIBUTION_CONTRACT,
            "source_revision": ledger["source_revision"], "input_ids": sorted(task.input_ids)})
    elif task.extra.get("batch_id"):
        batch = dict(ledger.get("fact_batches", {}).get(task.extra["batch_id"]) or {})
        if not batch or batch.get("input_ids") != task.input_ids:
            raise StaleWriteError("fact author scope differs from the frozen plan")
        batch.pop("superseded", None)
        batch.pop("superseded_by", None)
        expected = _sha_json({"contract": CONTRACT, "batch": batch,
                              "source_revision": ledger["source_revision"]})
    else:
        if len(packets) != 1:
            raise StaleWriteError("unbatched fact author has ambiguous frozen input")
        expected = _sha_json({"contract": CONTRACT, "packet": packets[0].to_dict(),
                              "input_ids": task.input_ids})
    if not expected or task.input_hash != expected:
        raise StaleWriteError(f"{task.task_id} fact author input hash differs from the frozen plan")


def _split_input_identity(ledger: dict, task: TaskRecord) -> str:
    """Recover only a provable same-revision partition lineage, never a claim."""
    chain = [task]
    seen = {task.task_id}
    while chain[-1].extra.get("split_from"):
        current = chain[-1]
        parent_id = current.extra["split_from"]
        raw = ledger["tasks"].get(parent_id)
        if raw is None or parent_id in seen:
            raise StaleWriteError("repair split has broken or cyclic ancestry")
        parent = TaskRecord.from_dict(raw)
        if (parent.kind != "fact_author"
                or parent.extra.get("fact_contract") != task.extra.get("fact_contract")
                or not set(current.input_ids) <= set(parent.input_ids)
                or current.extra.get("batch_id") not in parent.extra.get("superseded_by", [])):
            raise StaleWriteError("repair split ancestry scope or contract mismatch")
        chain.append(parent)
        seen.add(parent_id)
    if len(chain) == 1:
        return task.input_hash
    root = chain[-1]
    for node in chain:
        batch = dict(ledger.get("fact_batches", {}).get(node.extra.get("batch_id")) or {})
        if not batch or set(batch.get("input_ids", [])) != set(node.input_ids):
            raise StaleWriteError("repair split ancestry batch mismatch")
        batch.pop("superseded", None)
        batch.pop("superseded_by", None)
        expected = _sha_json({"contract": node.extra.get("fact_contract"), "batch": batch,
                              "source_revision": ledger["source_revision"]})
        if node is root and root.extra.get("fact_contract") == ATTRIBUTION_CONTRACT:
            expected = _sha_json({"contract": ATTRIBUTION_CONTRACT,
                                  "source_revision": ledger["source_revision"],
                                  "input_ids": sorted(root.input_ids)})
        # Older partitions hashed their subset; corrected partitions inherit
        # the root input. Both require the root's current frozen revision proof.
        if node.input_hash not in {root.input_hash, expected} or (node is root and node.input_hash != expected):
            raise StaleWriteError("repair split ancestry input or source revision mismatch")
    return root.input_hash


def split_pending_repair(run_dir: Path, task_id: str, *, allow_pending: bool = False) -> bool:
    """Split only unsent repair scope; retain historic calls and accepted facts."""
    changed = False

    def mutate(ledger: dict) -> dict:
        nonlocal changed
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        scope = task.extra.get("repair_ids") or (task.input_ids if allow_pending and task.state == "pending" else [])
        # Several validation residuals can refer to the same failed output.
        # Partition symbols once, rather than partitioning error occurrences.
        ids = list(dict.fromkeys(sid for sid in scope if not accepted_fact(ledger, sid)))
        if task.kind != "fact_author" or task.state not in ({"pending", "needs_repair"} if allow_pending else {"needs_repair"}) or len(ids) < 2:
            return ledger
        call = (ledger.get("calls") or {}).get(task.extra.get("call_id")) or {}
        if call.get("state") in {"prepared", "sent", "uncertain"}:
            return ledger
        input_identity = _split_input_identity(ledger, task)
        old_id = task.extra.get("batch_id")
        old = ledger["fact_batches"][old_id]
        replacements = []
        for subset in (ids[:len(ids) // 2], ids[len(ids) // 2:]):
            batch_id = "repair-batch" + _sha_json({"task": task_id, "generation": task.generation,
                                                  "ids": subset})[:16]
            new_id = f"task:fact_author:{batch_id}"
            if new_id in ledger["tasks"] or batch_id in ledger["fact_batches"]:
                raise StaleWriteError("repair split collides with historical batch")
            batch = {**old, "batch_id": batch_id, "input_ids": subset}
            batch.pop("superseded", None)
            batch.pop("superseded_by", None)
            residual = [finding for finding in task.residual
                        if not isinstance(finding, dict) or not finding.get("symbol_id")
                        or finding["symbol_id"] in subset]
            extra = {**task.extra, "batch_id": batch_id, "repair_ids": subset,
                     "split_from": task_id}
            for key in ("call_id", "superseded", "superseded_by"):
                extra.pop(key, None)
            child = TaskRecord(new_id, "fact_author", subset,
                               # Partition the work, not its frozen input identity.
                               # Existing same-source facts retain this hash; scope
                               # is separately bound by task/assigned IDs and the
                               # complete claimed packet hash.
                               input_identity,
                               task.state, residual=residual, extra=extra)
            ledger["fact_batches"][batch_id] = batch
            ledger["tasks"][new_id] = child.to_dict()
            replacements.append(batch_id)
        for raw in ledger["tasks"].values():
            if raw.get("kind") != "merge":
                continue
            extra = raw.get("extra") or {}
            if task_id not in (extra.get("slice_task_ids") or []):
                continue
            fragments = set(extra.get("fragment_ids") or [])
            replacement_tasks = [f"task:fact_author:{bid}" for bid in replacements
                                 if fragments.intersection(ledger["fact_batches"][bid]["input_ids"])]
            if replacement_tasks:
                extra["slice_task_ids"] = list(dict.fromkeys(
                    value for previous in extra["slice_task_ids"]
                    for value in (replacement_tasks if previous == task_id else [previous])))
        old["superseded"] = True
        old["superseded_by"] = replacements
        task.state = "stale"
        task.extra["superseded"] = True
        task.extra["superseded_by"] = replacements
        ledger["tasks"][task_id] = task.to_dict()
        changed = True
        return ledger

    LedgerStore(run_dir).mutate(mutate)
    return changed


def register_reader_findings(run_dir: Path, findings: list[dict]) -> dict:
    """Queue reader evidence on existing review tasks without claiming/sending.

    An active lease is untouched. Its pending findings remain on that task until
    its present work commits; native-next then activates a fresh audit generation.
    """
    if not isinstance(findings, list) or not findings:
        raise ValueError("reader findings must be a nonempty list")
    normalized = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("reader finding must be an object")
        target = finding.get("target_id", finding.get("symbol_id"))
        reason = finding.get("reason")
        if not isinstance(target, str) or not target or not isinstance(reason, str) or not reason.strip():
            raise ValueError("reader finding needs target_id (or symbol_id) and nonempty reason")
        normalized.append({"target_id": target, "reason": reason})
    result = []
    def mutate(ledger):
        for finding in normalized:
            target = finding["target_id"]
            if target == "system":
                tid = "task:system_review"
            elif target in (ledger.get("module_records") or {}):
                tid = f"task:module_review:{target}"
            else:
                matches = [tid for tid, task in ledger.get("tasks", {}).items()
                    if task.get("kind") == "fact_review" and target in task.get("input_ids", [])
                    and not (task.get("extra") or {}).get("superseded")]
                matches.sort(key=lambda tid: bool((ledger["tasks"][tid].get("extra") or {}).get("canonical_delegations")))
                tid = matches[0] if matches else None
            if tid not in ledger.get("tasks", {}):
                raise ValueError(f"reader finding has no current review target: {target}")
            task = ledger["tasks"][tid]
            extra = task.setdefault("extra", {})
            entry = {**finding, "source_revision": ledger["source_revision"]}
            entry["id"] = _sha_json(entry)
            seen = {item["id"] for item in extra.get("pending_reader_findings", []) + extra.get("reader_findings_history", [])}
            if entry["id"] not in seen:
                extra.setdefault("pending_reader_findings", []).append(entry)
            result.append({"target_id": target, "task_id": tid, "finding_id": entry["id"],
                "status": "already_registered" if entry["id"] in seen else "registered",
                "next_action": "native-next"})
        return ledger
    LedgerStore(run_dir).mutate(mutate)
    activate_reader_audits(run_dir)
    ledger = LedgerStore(run_dir).open()
    for item in result:
        task = ledger["tasks"][item["task_id"]]
        item["task_state"] = task["state"]
        if task["state"] == "leased":
            item["protected_call_id"] = (task.get("extra") or {}).get("call_id")
            item["next_action"] = "reconcile_current_call_then_native-next"
    return {"status": "reader_findings_registered", "items": result, "model_sent": False}


def activate_reader_audits(run_dir: Path, *, preview: dict | None = None) -> dict:
    """Activate queued findings only after the current review is committed."""
    store = LedgerStore(run_dir)
    preview = preview if preview is not None else store.open()
    if not any(task.get("state") == "committed" and (task.get("extra") or {}).get("pending_reader_findings")
               for task in preview.get("tasks", {}).values()):
        return {"activated": []}
    activated = []
    def mutate(ledger):
        for tid, raw in ledger.get("tasks", {}).items():
            extra = raw.get("extra") or {}
            pending = extra.get("pending_reader_findings") or []
            if raw.get("state") != "committed" or not pending:
                continue
            if any(entry["source_revision"] != ledger["source_revision"] for entry in pending):
                raise StaleWriteError("reader finding source revision changed; retain and rebind through a new explicit finding")
            task = TaskRecord.from_dict(raw)
            task.state = "pending"
            task.generation += 1
            task.owner = None
            task.lease_until = None
            task.extra.pop("call_id", None)
            task.extra.pop("packet_hash", None)
            task.extra["reader_question"] = "\n".join(entry["reason"] for entry in pending)
            if task.kind == "fact_review":
                ids = list(dict.fromkeys(entry["target_id"] for entry in pending))
                task.extra["audit_mode"] = True
                task.extra["reader_audit_ids"] = ids
                task.extra["audit_review_ids"] = list(dict.fromkeys([*task.extra.get("audit_review_ids", []), *ids]))
            elif task.kind == "module_review":
                gid = tid.removeprefix("task:module_review:")
                record = ledger["module_records"][gid]
                record.setdefault("history", []).append({"reason": "reader_audit_requested", "state": record["state"],
                    "record": json.loads(json.dumps(record["record"])), "input_hash": record["input_hash"]})
                record["state"] = "draft"
                task.residual.extend({"code": "reader_finding", "reason": entry["reason"]} for entry in pending)
            elif task.kind == "system_review":
                record = ledger["system_record"]
                record.setdefault("history", []).append({"reason": "reader_audit_requested", "state": record["state"],
                    "record": json.loads(json.dumps(record["record"])), "input_hash": record["input_hash"]})
                record["state"] = "draft"
                task.residual.extend({"code": "reader_finding", "reason": entry["reason"]} for entry in pending)
            else:
                raise ValueError("reader findings require an existing review task")
            task.extra.setdefault("reader_findings_history", []).extend(pending)
            task.extra.pop("pending_reader_findings", None)
            ledger["tasks"][tid] = task.to_dict()
            activated.append(tid)
        return ledger
    store.mutate(mutate)
    return {"activated": activated}


def release(run_dir: Path, task_id: str, *, owner: str) -> dict[str, Any]:
    """Release a lease; only never-sent prepared packets free their reservation."""
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        if task.state != "leased" or task.owner != owner:
            raise LeaseError("only the current fact owner may release")
        current_id = task.extra.get("call_id")
        if current_id and ledger["calls"][current_id].get("state") in {"prepared", "sent", "uncertain"}:
            from cbe.native_bundles import blocked_terminal_release
            if not blocked_terminal_release(ledger, current_id):
                raise LeaseError(f"{current_id} delivery is unresolved; use native-record terminal evidence or call-reconcile before releasing")
        call_id = task.extra.pop("call_id", None)
        task.extra.pop("packet_hash", None)
        task.state = "pending"
        task.generation += 1
        task.owner = None
        task.lease_until = None
        ledger["tasks"][task_id] = task.to_dict()
        if call_id:
            state = ledger["calls"][call_id]["state"]
            if state != "released":
                raise LeaseError(f"{call_id} has a completed result; preserve/import it instead of releasing")
            output["call_state"] = state
        output.update({"task_id": task_id, "state": task.state})
        return ledger

    store.mutate(mutate)
    return output


def reject_result(run_dir: Path, task_id: str, result_path: Path, *,
                  reason: str, repair_ids: list[str]) -> dict[str, Any]:
    """Quarantine delivered but invalid raw output without losing its known source cost."""
    run_dir = Path(run_dir).resolve()
    result_path = Path(result_path).resolve()
    if not reason.strip() or not repair_ids or len(repair_ids) != len(set(repair_ids)):
        raise ValueError("validation rejection needs a reason and unique repair IDs")
    raw_hash = _sha_bytes(result_path.read_bytes())
    store = LedgerStore(run_dir)
    output: dict[str, Any] = {}

    def mutate(ledger: dict) -> dict:
        task = TaskRecord.from_dict(ledger["tasks"][task_id])
        call_id = task.extra.get("call_id")
        call = (ledger.get("calls") or {}).get(call_id) or {}
        if task.state != "leased" or call.get("state") != "sent" or (
            (call.get("extra") or {}).get("send_evidence") not in {"sent_native", "sent_http"}
        ):
            raise StaleWriteError("only a current positively delivered result can be rejected")
        if result_path != run_dir / "raw" / f"{call_id}.json":
            raise ValueError("rejected result must use its reserved raw path")
        if not set(repair_ids) <= set(task.input_ids):
            raise ValueError("repair IDs must belong to the task")
        task.state = "needs_repair"
        task.generation += 1
        task.owner = None
        task.lease_until = None
        # Keep pending needs_context findings: a re-claim must still include the
        # frozen spans the reviewer named, instead of losing them to the
        # validation rejection of a different raw.
        kept_context = [
            finding for finding in task.residual
            if isinstance(finding, dict) and isinstance(finding.get("needed_source"), dict)
        ]
        task.residual = kept_context + [{"code": "invalid_model_result", "reason": reason,
                                         "symbol_id": sid} for sid in repair_ids]
        task.extra["repair_ids"] = list(repair_ids)
        task.extra["rejected_result_sha256"] = raw_hash
        ledger["tasks"][task_id] = task.to_dict()
        mark_call(ledger, call_id, state="imported", raw_path=str(result_path),
                  extra={"disposition": "validation_rejected", "validation_error": reason,
                         "raw_result_sha256": raw_hash})
        output.update({"task_id": task_id, "state": task.state, "call_id": call_id,
                       "repair_ids": repair_ids})
        return ledger

    store.mutate(mutate)
    return output


def queue_uncertainty_reconciliation(run_dir: Path, review_task_id: str, ids: list[str],
                                     *, decision: dict | None = None) -> str | None:
    """One bounded canonical rewrite for an unsent, blocked semantic review.

    It cannot accept the old assertion or erase its finding. The new writer and
    reviewer must cover every old field/finding, including explicit uncertainty.
    """
    from cbe.behavior_contracts import digest
    queued: list[str] = []
    def mutate(ledger: dict) -> dict | None:
        support = None
        decision_hash = _sha_json(decision) if decision is not None else None
        old = ledger["tasks"][review_task_id]
        if decision is not None:
            saved = old.get("extra", {}).get("context_reconciliation_decisions", {}).get(decision_hash)
            if saved:
                queued.append(saved)
                return None
            expected = {"run_id": ledger["run_id"], "source_revision": ledger["source_revision"],
                        "ledger_revision": ledger["ledger_revision"], "task_id": review_task_id,
                        "input_hash": old["input_hash"], "generation": old["generation"], "owner": old.get("owner")}
            if any(decision.get(k) != v for k, v in expected.items()):
                raise StaleWriteError("context reconciliation CAS identity differs")
            if (decision.get("schema") != "fact-context-reconciliation/1"
                or decision.get("authorize_targeted_author_revision") is not True
                or decision.get("symbol_ids") != ids or not decision.get("operator")
                or not isinstance(decision.get("reason"), str) or len(decision["reason"].strip()) < 20
                or old.get("kind") != "fact_review" or old.get("state") not in {"pending", "needs_repair"}):
                raise ValueError("explicit operator authorization for one unresolved fact's author revision required")
            if any(c.get("task_id") == review_task_id and c.get("state") in {"prepared", "sent", "uncertain", "durable"}
                   for c in ledger.get("calls", {}).values()):
                raise StaleWriteError("unresolved review call requires normal reconciliation first")
        if len(ids) != 1 or ids[0] not in ledger["inventory"]["symbols"]:
            return None
        sid = ids[0]
        if ledger["inventory"]["symbols"][sid]["kind"] not in {"function", "method", "lambda"}:
            return None
        findings = [item for item in old.get("residual") or []
                    if isinstance(item, dict) and item.get("symbol_id") == sid and item.get("reason")]
        if decision is not None:
            if (not any(isinstance(f.get("needed_source"), dict) for f in findings)
                or (ledger.get("fact_reviews", {}).get(sid) or {}).get("state") == "source_checked"
                or decision.get("detail_sha256") != digest(ledger["details"][sid])):
                raise StaleWriteError("target must retain a current unresolved context finding and exact draft hash")
            prior_delegation = old.get("extra", {}).get("canonical_delegations", {}).get(sid)
            if prior_delegation and (ledger.get("tasks", {}).get(prior_delegation) or {}).get("state") != "committed":
                raise StaleWriteError("existing canonical author must finish before another revision")
            contexts = decision.get("source_requests")
            if not isinstance(contexts, list) or not contexts:
                raise ValueError("exact enrolled frozen source locators required")
            inventory = Inventory.from_dict(ledger["inventory"])
            spans = []
            for locator in contexts:
                path = locator.get("path")
                if path not in inventory.files:
                    raise ValueError("source locator outside enrolled frozen scope")
                offsets = load_frozen_offsets(Path(ledger["repo_root"]), path, inventory.files[path])
                starts = line_starts(offsets.text)
                first, last = locator.get("start_line"), locator.get("end_line")
                if (type(first) is not int or type(last) is not int
                    or not 1 <= first <= last <= len(starts)):
                    raise ValueError("exact source locator outside frozen line bounds")
                spans.append({"path": path, "start": starts[first-1],
                              "end": starts[last] if last < len(starts) else len(offsets.text)})
            support = {sid: {"source_revision": ledger["source_revision"], "spans": spans}}
        if not findings or (accepted_fact(ledger, sid) and decision is None) or old.get("state") == "leased":
            return None
        prior_call = ledger.get("calls", {}).get((old.get("extra") or {}).get("call_id")) or {}
        if prior_call.get("state") in {"prepared", "sent", "uncertain"}:
            return None
        detail = ledger["details"][sid]
        composition = {"fragment_ids": [sid], "prior_detail_hashes": {sid: digest(detail)},
                       "prior_review_states": {sid: (ledger.get("fact_reviews", {}).get(sid) or {}).get("state")},
                       "prior_details": {sid: detail}, "findings": findings,
                       "reconciles_review_task": review_task_id}
        batch_id = "reconcile-" + digest({"revision": ledger["source_revision"],
                                          "detail": digest(detail), "findings": findings,
                                          **({"operator_decision": decision_hash} if decision is not None else {})})[:16]
        task_id = "task:fact_author:" + batch_id
        if task_id in ledger["tasks"]:
            return None
        old_batch_id = review_task_id.removeprefix("task:fact_review:")
        packets = _batch_packets(ledger, old_batch_id)
        packet_ids = [packet.packet_id for packet in packets
                      if packet.path == ledger["inventory"]["symbols"][sid]["path"]]
        ledger.setdefault("fact_batches", {})[batch_id] = {
            "batch_id": batch_id, "packet_ids": packet_ids, "input_ids": [sid],
            "max_input_tokens": 8000, "max_output_estimate": 3000,
            "source_chars": ledger["inventory"]["symbols"][sid]["span"]["end"] - ledger["inventory"]["symbols"][sid]["span"]["start"],
            "planned_review_source_chars": ledger["inventory"]["symbols"][sid]["span"]["end"] - ledger["inventory"]["symbols"][sid]["span"]["start"]}
        ledger["tasks"][task_id] = TaskRecord(
            task_id, "fact_author", [sid], detail.get("input_hash") or old["input_hash"], "pending",
            residual=findings, extra={"fact_contract": CONTRACT, "batch_id": batch_id,
                                      "packet_ids": packet_ids, "repair_ids": [sid],
                                      "canonical_composition": composition}).to_dict()
        if decision is not None:
            ledger["tasks"][task_id]["extra"].update(
                repair_source_views=support, context_reconciliation_decision=decision)
            old.setdefault("extra", {}).setdefault("context_reconciliation_decisions", {})[decision_hash] = task_id
        old.setdefault("extra", {}).setdefault("canonical_delegations", {})[sid] = task_id
        queued.append(task_id)
        return ledger
    LedgerStore(run_dir).mutate(mutate)
    return queued[0] if queued else None


def merge_ready(run_dir: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Queue one canonical author/review after accepted fragment evidence.

    Historical fragments and calls remain unchanged; a structural coverage map
    cannot confer acceptance on a new narrative.
    """
    run_dir = Path(run_dir).resolve()
    store = LedgerStore(run_dir)
    results: list[dict[str, Any]] = []

    while limit is None or len(results) < limit:

        def reserve(ledger: dict) -> dict | None:
            reviews = ledger.get("fact_reviews") or {}
            satisfied = False
            for replacement in list(ledger["tasks"].values()):
                composition = (replacement.get("extra") or {}).get("canonical_composition") or {}
                prior_task_id = composition.get("reconciles_review_task")
                if prior_task_id and replacement.get("state") == "committed" and all(
                    accepted_fact(ledger, sid) for sid in replacement["input_ids"]):
                    prior_task = ledger["tasks"][prior_task_id]
                    required = set((prior_task.get("extra") or {}).get("required_review_ids") or [])
                    if all((reviews.get(sid) or {}).get("state") == "source_checked"
                           and (reviews.get(sid) or {}).get("content_sha256") == _sha_json(ledger["details"][sid])
                           for sid in required):
                        # Unchanged non-required rows keep the existing batch
                        # acceptance policy; only named source checks claim S.
                        for sid in prior_task["input_ids"]:
                            review = reviews.get(sid) or {}
                            if review.get("state") == "author_fact" and review.get("content_sha256") == _sha_json(ledger["details"][sid]):
                                review["state"] = "batch_accepted"
                                review["acceptance_basis"] = "canonical_reconciliation_and_prior_bound_reviews"
                        prior_task["state"] = "stale"
                        prior_task["extra"]["superseded"] = True
                        prior_task["extra"]["superseded_by"] = [replacement["task_id"]]
                    prior_task.setdefault("extra", {})["canonical_covered_ids"] = replacement["input_ids"]
                    satisfied = True
            for tid, raw in ledger.get("tasks", {}).items():
                if (raw.get("kind") != "fact_review" or raw.get("state") not in {"pending", "needs_repair"}
                    or (raw.get("extra") or {}).get("audit_mode")):
                    continue
                task = TaskRecord.from_dict(raw)
                author = ledger["tasks"].get(tid.replace("task:fact_review:", "task:fact_author:", 1)) or {}
                if author.get("state") != "committed" or not task.input_ids:
                    continue
                draft = {sid: ledger["details"].get(sid) for sid in task.input_ids}
                if _sha_json(draft) != task.input_hash or not all(accepted_fact(ledger, sid) for sid in task.input_ids):
                    continue
                required = set(task.extra.get("required_review_ids") or []) | repair_review_ids(
                    ledger, TaskRecord.from_dict(author))
                if any((reviews.get(sid) or {}).get("state") != "source_checked" for sid in required):
                    continue
                if any(not isinstance(finding, dict) or finding.get("code") != "invalid_review_scope"
                       for finding in task.residual):
                    continue
                task.state = "committed"
                task.residual = []
                task.extra["completed_without_dispatch"] = "existing_hash_bound_source_checks"
                ledger["tasks"][tid] = task.to_dict()
                satisfied = True
            for task_id, raw in sorted((ledger.get("tasks") or {}).items()):
                if raw.get("kind") != "merge" or raw.get("state") not in {"pending", "needs_repair"}:
                    continue
                fragment_ids = (raw.get("extra") or {}).get("fragment_ids") or []
                if not fragment_ids or any(sid not in (ledger.get("details") or {}) for sid in fragment_ids):
                    continue
                if any(
                    set(fact_task.get("input_ids") or []) & set(fragment_ids)
                    and (fact_task.get("state") == "leased" or
                         (ledger.get("calls", {}).get((fact_task.get("extra") or {}).get("call_id")) or {}).get(
                             "state") in {"prepared", "sent", "uncertain"})
                    for fact_task in ledger["tasks"].values()
                    if fact_task.get("kind") in {"fact_author", "fact_review"}
                ):
                    continue
                # Fragment reviews prove their own evidence, not a concise
                # whole-function narrative. Queue one normal author/review
                # composition; never inherit semantic acceptance from join().
                from cbe.behavior_contracts import digest
                parent = (raw.get("extra") or {}).get("parent_symbol_id") or raw["input_ids"][0]
                parent_symbol = ledger["inventory"]["symbols"][parent]
                full_view_repair = False
                for fact_task in ledger["tasks"].values():
                    if fact_task.get("kind") != "fact_author" or fact_task.get("state") != "needs_repair":
                        continue
                    support = (fact_task.get("extra") or {}).get("repair_source_views") or {}
                    for sid in set(fragment_ids) & set(support):
                        spans = merge_char_spans([CharSpan(item["start"], item["end"])
                                                 for item in support[sid].get("spans") or []
                                                 if item["path"] == parent_symbol["path"]])
                        if any(span.start <= parent_symbol["span"]["start"]
                               and span.end >= parent_symbol["span"]["end"] for span in spans):
                            full_view_repair = True
                if not full_view_repair and any(not accepted_fact(ledger, sid) for sid in fragment_ids):
                    continue
                hashes = {sid: digest(ledger["details"][sid]) for sid in fragment_ids}
                composition_id = "canonical-" + digest({"parent": parent, "hashes": hashes,
                                                       "revision": ledger["source_revision"]})[:16]
                author_id = "task:fact_author:" + composition_id
                obsolete = [other for other in ledger["tasks"].values()
                            if other.get("kind") == "fact_author" and other.get("input_ids") == [parent]
                            and (other.get("extra") or {}).get("canonical_composition")
                            and other["task_id"] != author_id and other.get("state") not in {"stale", "committed"}]
                if any(other.get("state") == "leased" or
                       (ledger.get("calls", {}).get((other.get("extra") or {}).get("call_id")) or {}).get("state")
                       in {"prepared", "sent", "uncertain"} for other in obsolete):
                    continue
                for other in obsolete:
                    other["state"] = "stale"
                    other.setdefault("extra", {})["superseded"] = True
                    other["extra"]["superseded_by"] = [author_id]
                if accepted_fact(ledger, parent) and (ledger["tasks"].get(author_id) or {}).get("state") == "committed":
                    raw["state"] = "committed"
                    raw.setdefault("extra", {})["canonical_composition_task"] = author_id
                    satisfied = True
                    for old_task in ledger["tasks"].values():
                        delegates = (old_task.get("extra") or {}).get("canonical_delegations") or {}
                        covered = {sid for sid, destination in delegates.items() if destination == author_id}
                        if covered:
                            old_task.setdefault("extra", {})["canonical_covered_ids"] = sorted(covered)
                            old_task["extra"]["repair_ids"] = [sid for sid in old_task["extra"].get("repair_ids") or [] if sid not in covered]
                            if set(old_task.get("input_ids") or []) <= covered:
                                old_task["state"] = "stale"
                                old_task["extra"]["superseded"] = True
                                old_task["extra"]["superseded_by"] = [author_id]
                    continue
                if author_id not in ledger["tasks"]:
                    packet_ids = [packet["packet_id"] for packet in ledger["packets"]["packets"]
                                  if any(fragment.get("fragment_id") in fragment_ids
                                         for fragment in packet.get("fragments") or [])]
                    batch = {"batch_id": composition_id, "packet_ids": packet_ids,
                             "input_ids": [parent], "max_input_tokens": 8000,
                             "max_output_estimate": 3000,
                             "source_chars": parent_symbol["span"]["end"] - parent_symbol["span"]["start"],
                             "planned_review_source_chars": parent_symbol["span"]["end"] - parent_symbol["span"]["start"]}
                    ledger.setdefault("fact_batches", {})[composition_id] = batch
                    composition = {"fragment_ids": fragment_ids, "prior_detail_hashes": hashes,
                                   "prior_review_states": {sid: (reviews.get(sid) or {}).get("state") for sid in fragment_ids}}
                    ledger["tasks"][author_id] = TaskRecord(
                        author_id, "fact_author", [parent],
                        _sha_json({"contract": CONTRACT, "batch": batch,
                                   "source_revision": ledger["source_revision"]}), "pending",
                        extra={"fact_contract": CONTRACT, "batch_id": composition_id,
                               "packet_ids": packet_ids, "canonical_composition": composition}).to_dict()
                    raw.setdefault("extra", {})["canonical_composition_task"] = author_id
                    satisfied = True
                if full_view_repair:
                    for old_task in ledger["tasks"].values():
                        if old_task.get("kind") not in {"fact_author", "fact_review"} or old_task.get("state") == "leased":
                            continue
                        overlaps = set(old_task.get("input_ids") or []) & set(fragment_ids)
                        if overlaps:
                            old_task.setdefault("extra", {}).setdefault("canonical_delegations", {}).update(
                                {sid: author_id for sid in overlaps})
                continue
            return ledger if satisfied else None

        store.mutate(reserve)
        break
    return results
