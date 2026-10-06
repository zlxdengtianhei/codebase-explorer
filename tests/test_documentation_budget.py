"""Planning checks for the published-token ceiling before any model call."""

from __future__ import annotations

import pytest

from cbe.documentation_budget import DocumentationBudgetInfeasible, allocate_symbol_tokens
from cbe.token_budget import check_render_budget, RenderBudgetExceeded


@pytest.mark.parametrize("published,status", [(501, "explainable_overage"),
                                               (549, "explainable_overage"),
                                               (551, "above_guidance")])
def test_report_policy_records_ratio_without_rejecting_publication(published, status) -> None:
    report = check_render_budget(1000, published, strict=False)
    assert report["ratio"] == published / 1000
    assert report["policy"] == "report"
    assert report["target_status"] == status
    with pytest.raises(RenderBudgetExceeded):
        check_render_budget(1000, published, strict=True)


def test_allocation_is_deterministic_and_reserves_group_and_repair_space() -> None:
    original = {
        "small": {"tier": "brief", "suggested_output_tokens": 120},
        "medium": {"tier": "standard", "suggested_output_tokens": 300},
        "large": {"tier": "deep", "suggested_output_tokens": 650},
    }
    first = {key: dict(value) for key, value in original.items()}
    second = {key: dict(value) for key, value in original.items()}
    a = allocate_symbol_tokens(first, source_tokens=1000, navigation_tokens=100)
    b = allocate_symbol_tokens(second, source_tokens=1000, navigation_tokens=100)
    assert a == b
    assert first == second
    assert first["small"]["suggested_output_tokens"] >= 6
    assert first["medium"]["suggested_output_tokens"] >= 15
    assert first["large"]["suggested_output_tokens"] >= 30
    assert first["large"]["suggested_output_tokens"] > 2 * first["medium"]["suggested_output_tokens"]
    assert (
        a["fixed_navigation_tokens"] + a["detail_allocated_tokens"]
        + a["group_reserve_tokens"] + a["repair_reserve_tokens"]
    ) <= a["published_cap_tokens"]


def test_preflight_refuses_more_navigation_than_the_half_code_ceiling() -> None:
    with pytest.raises(DocumentationBudgetInfeasible):
        allocate_symbol_tokens({}, source_tokens=30, navigation_tokens=16)


def test_report_infeasible_replaces_stale_large_suggestions_and_counts_excess() -> None:
    policies = {"a": {"tier": "deep", "suggested_output_tokens": 11740}}
    report = allocate_symbol_tokens(policies, source_tokens=100, navigation_tokens=80,
                                    report_infeasible=True)
    assert policies["a"]["suggested_output_tokens"] == 90
    assert report["allocation_status"] == "necessary_overage"
    assert report["recommended_total_tokens"] == 80 + 64 + 32 + 90
    assert report["necessary_overage_tokens"] == report["recommended_total_tokens"] - 50
