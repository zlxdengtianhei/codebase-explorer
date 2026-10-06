"""Allocate a frozen weighted documentation budget before model production."""

from __future__ import annotations

from math import floor
from typing import Any


class DocumentationBudgetInfeasible(ValueError):
    """The fixed layout and starting writing recommendations exceed the target."""


# Allocation floors are writing recommendations, not proven semantic minima.
MINIMUM_TOKENS = {"brief": 6, "standard": 20, "deep": 90}
# Deep records must keep ordered failure and state transitions. The first
# Celery reader pilot showed that a proportional split left only 88 tokens for
# trace_task and collapsed two distinct Reject paths into one wrong statement.
# Transfer a few tokens from thousands of simple helpers to the rare deep
# symbols without changing the global ceiling.
EXTRA_WEIGHT = {"brief": 4, "standard": 6, "deep": 15}


def allocate_symbol_tokens(
    policies: dict[str, dict[str, Any]],
    *,
    source_tokens: int,
    navigation_tokens: int,
    report_infeasible: bool = False,
) -> dict[str, Any]:
    """Reserve navigation, group explanation, and repair headroom before calls.

    All allocations are integer o200k_base content tokens. A producer can use
    less, but no collection of fully used quotas can exceed the detail pool.
    The final renderer still checks actual Markdown, including headings and
    links, because this reservation is an upper-bound planning instrument.
    """

    limit = source_tokens // 2
    available = limit - navigation_tokens
    if available <= 0 and not report_infeasible:
        raise DocumentationBudgetInfeasible(
            f"fixed navigation uses {navigation_tokens} tokens but the published cap is {limit}"
        )
    repair_reserve = max(64, max(0, available) // 10)
    group_reserve = max(32, max(0, available) // 4)
    detail_pool = available - repair_reserve - group_reserve
    minimums = {
        sid: MINIMUM_TOKENS[str(policy["tier"])]
        for sid, policy in policies.items()
    }
    minimum_total = sum(minimums.values())
    infeasible = detail_pool < minimum_total
    if infeasible and not report_infeasible:
        raise DocumentationBudgetInfeasible(
            f"detail minimum {minimum_total} exceeds its pool {detail_pool}; "
            f"navigation={navigation_tokens}, group_reserve={group_reserve}, "
            f"repair_reserve={repair_reserve}, cap={limit}"
        )
    # Report mode still replaces the old unconstrained suggestions. The
    # starting allocations are recommendations, not an admission gate.
    # Their necessary excess is explicit instead of silently keeping a much
    # larger stale allocation after the strict allocator raises.
    extra_pool = max(0, detail_pool - minimum_total)
    wanted = {
        sid: max(0, int(policy["suggested_output_tokens"]) - minimums[sid])
        * EXTRA_WEIGHT[str(policy["tier"])]
        for sid, policy in policies.items()
    }
    wanted_total = sum(wanted.values())
    if wanted_total <= extra_pool:
        extras = wanted
    else:
        exact = {sid: extra_pool * value / wanted_total for sid, value in wanted.items()}
        extras = {sid: floor(value) for sid, value in exact.items()}
        leftover = extra_pool - sum(extras.values())
        for sid in sorted(exact, key=lambda item: (-(exact[item] - extras[item]), item))[:leftover]:
            extras[sid] += 1
    for sid, policy in policies.items():
        policy["suggested_output_tokens"] = minimums[sid] + extras[sid]
        policy["allocation_basis"] = "behavior_display"
    return {
        "source_tokens": source_tokens,
        "published_cap_tokens": limit,
        "fixed_navigation_tokens": navigation_tokens,
        "detail_pool_tokens": detail_pool,
        "detail_allocated_tokens": sum(
            int(policy["suggested_output_tokens"]) for policy in policies.values()
        ),
        "group_reserve_tokens": group_reserve,
        "repair_reserve_tokens": repair_reserve,
        "allocation_status": "necessary_overage" if infeasible else "within_target",
        "minimum_contract_tokens": minimum_total,
        "allocation_interpretation": "starting writing recommendations, not proven semantic minima or quality",
        "recommended_total_tokens": navigation_tokens + group_reserve + repair_reserve
        + sum(int(policy["suggested_output_tokens"]) for policy in policies.values()),
        "necessary_overage_tokens": max(0, minimum_total - detail_pool),
    }
