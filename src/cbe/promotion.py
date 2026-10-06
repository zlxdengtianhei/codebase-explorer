"""Evidence-backed, budgeted promotion of one weighted Detail symbol.

Promotion is a ledger mutation. It rekeys every packet that owns a fragment of
the canonical symbol, preserving other accepted packet outputs while making
old envelopes unusable. It never reads source or makes a model call.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cbe.documentation_budget import MINIMUM_TOKENS
from cbe.models import TaskRecord
from cbe.store import (
    LedgerStore,
    ancestor_group_ids,
    group_selection_input_hash,
    invalidate_group_bodies,
    is_historical_task,
    load_unique_packets,
    mark_detail_historical,
)
from cbe.token_budget import count_text_tokens
from cbe.weighting import REQUIRED_FIELDS_BY_TIER


class PromotionError(ValueError):
    """The requested promotion cannot safely change the frozen run."""


class PromotionBudgetError(PromotionError):
    """The next tier cannot be funded from the run's remaining repair reserve."""


_NEXT_TIER = {"brief": "standard", "standard": "deep"}


def _source_line(value: Any) -> int | str | dict[str, Any]:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict) and isinstance(value.get("line"), int) and not isinstance(value["line"], bool) and value["line"] > 0:
        return {key: value[key] for key in sorted(value)}
    raise PromotionError("source_line must identify a nonempty source line")


def _owned_outputs(task: TaskRecord, packet: Any, symbol_id: str) -> list[str]:
    outputs = [
        fragment.output_id
        for fragment in packet.fragments
        if fragment.symbol_id == symbol_id and fragment.output_id in task.input_ids
    ]
    if not packet.fragments and symbol_id in task.input_ids:
        outputs.append(symbol_id)
    return outputs


def _request_evidence(tasks: list[tuple[TaskRecord, Any, list[str]]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task, _packet, outputs in tasks:
        for residual in task.residual:
            if residual.get("code") != "promotion_requested" or residual.get("symbol_id") not in outputs:
                continue
            raw = residual.get("evidence") or {}
            if not isinstance(raw, dict) or not isinstance(raw.get("missing_fact"), str) or not raw["missing_fact"].strip():
                continue
            try:
                source_line = _source_line(raw.get("source_line"))
            except PromotionError:
                continue
            item = {
                "source": "producer_request",
                "source_line": source_line,
                "missing_fact": raw["missing_fact"].strip(),
                "output_id": residual["symbol_id"],
            }
            identity = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if identity not in seen:
                seen.add(identity)
                evidence.append(item)
    return evidence


def promote_symbol(
    run_dir: Path | str,
    symbol_id: str,
    *,
    tier: str | None = None,
    reason: str | None = None,
    source_line: Any = None,
    extra_tokens: int | None = None,
) -> dict[str, Any]:
    """Advance one tier, or fund an evidenced deep-tier quota top-up.

    A valid ``promotion_requested`` residual supplies source evidence. A manual
    promotion instead requires both ``reason`` and ``source_line``. The
    mutation is atomic; reserve exhaustion leaves the ledger untouched.
    """
    if not isinstance(symbol_id, str) or not symbol_id:
        raise PromotionError("symbol_id must be a nonempty canonical ID")
    if extra_tokens is not None and (
        not isinstance(extra_tokens, int) or isinstance(extra_tokens, bool) or extra_tokens <= 0
    ):
        raise PromotionError("extra_tokens must be a positive integer")
    if (reason is None) != (source_line is None):
        raise PromotionError("manual promotion requires both reason and source_line")
    manual: dict[str, Any] | None = None
    if reason is not None:
        if not isinstance(reason, str) or not reason.strip():
            raise PromotionError("reason must be nonempty")
        manual = {
            "source": "manual",
            "source_line": _source_line(source_line),
            "missing_fact": reason.strip(),
        }
    result: dict[str, Any] = {}
    store = LedgerStore(Path(run_dir))

    def mutate(ledger: dict[str, Any]) -> dict[str, Any]:
        from cbe.runner import _register_merge_tasks, build_detail_task, edges_for_selection

        documentation = ledger.get("documentation_policy") or {}
        if documentation.get("version") != "weighted-v1":
            raise PromotionError("promotion requires a weighted-v1 run")
        policies = documentation.get("symbols") or {}
        old_policy = policies.get(symbol_id)
        if not isinstance(old_policy, dict) or symbol_id not in ((ledger.get("inventory") or {}).get("symbols") or {}):
            raise PromotionError(f"unknown canonical symbol: {symbol_id}")
        old_tier = old_policy.get("tier")
        next_tier = _NEXT_TIER.get(old_tier)
        budget_only = old_tier == "deep" and extra_tokens is not None
        if budget_only:
            next_tier = "deep"
            if tier is not None and tier != "deep":
                raise PromotionError("deep quota top-up cannot change or downgrade the tier")
        elif next_tier is None:
            raise PromotionError(f"symbol {symbol_id} is already deep or has invalid tier {old_tier}")
        elif tier is not None and tier != next_tier:
            raise PromotionError(f"only the next tier {next_tier} is allowed from {old_tier}")

        packets = load_unique_packets(ledger)
        tasks_raw = ledger.get("tasks") or {}
        affected: list[tuple[TaskRecord, Any, list[str]]] = []
        for raw in tasks_raw.values():
            if raw.get("kind") != "detail":
                continue
            task = TaskRecord.from_dict(raw)
            if is_historical_task(task):
                continue
            packet = packets.get(task.packet_id or "")
            if packet is None:
                continue
            outputs = _owned_outputs(task, packet, symbol_id)
            if outputs:
                affected.append((task, packet, outputs))
        if not affected:
            raise PromotionError(f"no detail packet owns canonical symbol {symbol_id}")

        evidence = _request_evidence(affected)
        if manual is not None:
            evidence.append(manual)
        if not evidence:
            raise PromotionError("promotion requires a valid promotion_requested residual or reason plus source_line")
        evidence.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
        fact_text = "\n".join(item["missing_fact"] for item in evidence)
        delta = max(
            MINIMUM_TOKENS[next_tier] - MINIMUM_TOKENS[str(old_tier)],
            count_text_tokens(fact_text) + 8,
            extra_tokens or 0,
        )
        remaining = int(documentation.get("repair_reserve_tokens") or 0)
        if remaining < delta:
            raise PromotionBudgetError(
                f"repair reserve needs {delta} tokens but only {remaining} remain for {symbol_id}"
            )

        new_policy = dict(old_policy)
        new_policy["tier"] = next_tier
        new_policy["required_fields"] = list(REQUIRED_FIELDS_BY_TIER[next_tier])
        new_policy["suggested_output_tokens"] = int(old_policy["suggested_output_tokens"]) + delta
        signals = set(old_policy.get("signals") or []) | {
            "promotion:evidenced", f"promotion:tier={next_tier}",
        }
        if budget_only:
            signals.add("promotion:budget_top_up")
        new_policy["signals"] = sorted(signals)
        history = list(old_policy.get("promotion_history") or [])
        history.append({
            "from_tier": old_tier,
            "to_tier": next_tier,
            "quota_delta_tokens": delta,
            "budget_only": budget_only,
            "evidence": evidence,
        })
        new_policy["promotion_history"] = history
        policies[symbol_id] = new_policy
        documentation["symbols"] = policies
        documentation.setdefault("repair_reserve_initial_tokens", remaining + int(documentation.get("repair_reserve_spent_tokens") or 0))
        documentation["repair_reserve_tokens"] = remaining - delta
        documentation["repair_reserve_spent_tokens"] = int(documentation.get("repair_reserve_spent_tokens") or 0) + delta
        documentation["detail_pool_tokens"] = int(documentation.get("detail_pool_tokens") or 0) + delta
        documentation["detail_allocated_tokens"] = int(documentation.get("detail_allocated_tokens") or 0) + delta
        committed = (
            int(documentation.get("detail_allocated_tokens") or 0)
            + int(documentation.get("group_reserve_tokens") or 0)
            + int(documentation.get("repair_reserve_tokens") or 0)
            + int(documentation.get("fixed_navigation_tokens") or 0)
        )
        if committed > int(documentation.get("published_cap_tokens") or 0):
            raise PromotionBudgetError("promotion would violate the published token budget allocation")
        ledger["documentation_policy"] = documentation

        details = ledger.setdefault("details", {})
        affected_ids = {symbol_id}
        updated_tasks: list[str] = []
        for task, packet, outputs in affected:
            affected_ids.update(outputs)
            rebuilt = build_detail_task(packet, symbol_policies=policies)
            if rebuilt.input_ids != task.input_ids:
                raise PromotionError(f"packet input IDs changed for {task.task_id}")
            old_extra = task.extra or {}
            repair_ids = set(old_extra.get("repair_ids") or []) | set(outputs)
            new_extra = dict(rebuilt.extra)
            new_extra["repair_ids"] = [ident for ident in task.input_ids if ident in repair_ids]
            new_extra["original_input_ids"] = list(task.input_ids)
            if old_extra.get("review_feedback"):
                new_extra["review_feedback"] = old_extra["review_feedback"]
            task.extra = new_extra
            task.input_hash = rebuilt.input_hash
            task.generation += 1
            task.state = "pending"
            task.owner = None
            task.owner_pid = None
            task.lease_until = None
            task.output_refs = [ident for ident in task.output_refs if ident not in outputs]
            task.residual = [
                item for item in task.residual
                if not (item.get("code") == "promotion_requested" and item.get("symbol_id") in outputs)
            ]
            tasks_raw[task.task_id] = task.to_dict()
            updated_tasks.append(task.task_id)

        for ident in sorted(affected_ids):
            if isinstance(details.get(ident), dict):
                details[ident] = mark_detail_historical(details[ident], reason="tier_promotion")
        if f"task:merge:{symbol_id}" in tasks_raw:
            generated: dict[str, TaskRecord] = {}
            _register_merge_tasks(generated, list(packets.values()), symbol_policies=policies)
            merge_id = f"task:merge:{symbol_id}"
            rebuilt_merge = generated.get(merge_id)
            if rebuilt_merge is None:
                raise PromotionError(f"merge plan vanished for {symbol_id}")
            merge = TaskRecord.from_dict(tasks_raw[merge_id])
            if is_historical_task(merge):
                raise PromotionError(f"merge task is historical for active symbol {symbol_id}")
            merge.input_hash = rebuilt_merge.input_hash
            merge.extra = dict(rebuilt_merge.extra)
            merge.generation += 1
            merge.state = "pending"
            merge.owner = None
            merge.owner_pid = None
            merge.lease_until = None
            merge.output_refs = []
            merge.residual = []
            tasks_raw[merge_id] = merge.to_dict()
            updated_tasks.append(merge_id)

        groups = ledger.get("groups") or {}
        invalidated: set[str] = set()
        for group_id, group in groups.items():
            if symbol_id in (group.get("member_ids") or []):
                invalidated.add(group_id)
                invalidated.update(ancestor_group_ids(ledger, group_id))
        if invalidated:
            invalidate_group_bodies(ledger, sorted(invalidated))
        for task_id, raw in list(tasks_raw.items()):
            if raw.get("kind") != "group":
                continue
            task = TaskRecord.from_dict(raw)
            if is_historical_task(task):
                continue
            if not (set(task.input_ids) & ({symbol_id} | invalidated) or set(task.output_refs) & invalidated):
                continue
            internal, boundary, _endpoints = edges_for_selection(ledger, list(task.input_ids))
            task.input_hash = group_selection_input_hash(ledger, list(task.input_ids), internal + boundary)
            task.generation += 1
            task.state = "stale"
            task.owner = None
            task.owner_pid = None
            task.lease_until = None
            task.residual = [{"code": "dependency_promoted", "symbol_id": symbol_id}]
            tasks_raw[task_id] = task.to_dict()
            updated_tasks.append(task_id)
        ledger["tasks"] = tasks_raw
        result.update({
            "symbol_id": symbol_id,
            "from_tier": old_tier,
            "to_tier": next_tier,
            "budget_only": budget_only,
            "quota_delta_tokens": delta,
            "repair_reserve_remaining_tokens": remaining - delta,
            "updated_tasks": sorted(updated_tasks),
            "invalidated_detail_ids": sorted(affected_ids),
            "invalidated_group_ids": sorted(invalidated),
            "evidence": evidence,
        })
        return ledger

    store.mutate(mutate)
    return result
