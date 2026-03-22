"""Unit tests for the budget management layer.

Covers: estimator (char/line/module token estimation, zero-input edge case)
and controller (allocation, stop conditions, usage recording, MCP interface).
"""
from __future__ import annotations

import pytest

from src.budget.estimator import (
    CHARS_PER_TOKEN,
    TOKENS_PER_LINE,
    FileInfo,
    estimate_module_tokens,
    estimate_tokens_from_chars,
    estimate_tokens_from_lines,
)
from src.budget.controller import AnalysisBudgetController


# ===========================================================================
# Estimator tests
# ===========================================================================


class TestEstimateTokensFromChars:
    """Character-based token estimation."""

    def test_estimate_tokens_from_chars_python(self):
        chars = 3500
        tokens = estimate_tokens_from_chars(chars, "python")
        expected = int(chars / CHARS_PER_TOKEN["python"])
        assert tokens == expected

    def test_estimate_tokens_from_chars_typescript(self):
        chars = 4000
        tokens = estimate_tokens_from_chars(chars, "typescript")
        expected = int(chars / CHARS_PER_TOKEN["typescript"])
        assert tokens == expected

    def test_zero_input_chars(self):
        assert estimate_tokens_from_chars(0, "python") == 0


class TestEstimateTokensFromLines:
    """Line-based token estimation."""

    def test_estimate_tokens_from_lines(self):
        lines = 100
        tokens = estimate_tokens_from_lines(lines, "python")
        expected = lines * TOKENS_PER_LINE["python"]
        assert tokens == expected

    def test_zero_input_lines(self):
        assert estimate_tokens_from_lines(0, "python") == 0


class TestEstimateModuleTokens:
    """Module-level token aggregation."""

    def test_estimate_module_tokens(self):
        files = [
            FileInfo(filepath="a.py", language="python", line_count=50, char_count=1750),
            FileInfo(filepath="b.py", language="python", line_count=80, char_count=2800),
        ]
        result = estimate_module_tokens(files, module_name="core")
        assert result.module_name == "core"
        assert result.file_count == 2
        assert result.total_chars == 1750 + 2800
        assert result.total_lines == 50 + 80
        assert result.estimated_tokens > 0
        assert result.language == "python"

    def test_estimate_module_tokens_empty(self):
        result = estimate_module_tokens([], module_name="empty")
        assert result.estimated_tokens == 0
        assert result.file_count == 0
        assert result.language == "unknown"


# ===========================================================================
# Controller tests
# ===========================================================================


class TestBudgetControllerInitial:
    """Initial state checks."""

    def test_initial_status(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000, total_modules=5,
        )
        status = ctrl.get_status()
        assert status.total_budget == 100_000
        assert status.used_tokens == 0
        assert status.remaining_tokens == 100_000
        assert status.usage_percent == 0.0
        assert status.modules_analyzed == 0
        assert status.modules_remaining == 5
        assert status.should_stop is False


class TestBudgetControllerAllocation:
    """Allocation logic."""

    def test_allocate_within_budget(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000, max_tokens_per_module=10_000,
        )
        alloc = ctrl.allocate("core", 5000)
        assert alloc.allocated_tokens == 5000
        assert alloc.remaining_budget == 95_000
        assert alloc.warning is None

    def test_allocate_exceeds_module_limit(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000, max_tokens_per_module=10_000,
        )
        alloc = ctrl.allocate("huge_module", 15_000)
        assert alloc.allocated_tokens == 10_000
        assert alloc.warning is not None
        assert "exceeds" in alloc.warning.lower() or "capped" in alloc.warning.lower()


class TestBudgetControllerStopConditions:
    """should_stop evaluation."""

    def test_should_stop_budget_exhausted(self):
        ctrl = AnalysisBudgetController(
            total_budget=10_000, max_tokens_per_module=10_000,
        )
        ctrl.allocate("mod", 9_600)
        ctrl.record_usage("mod", 9_600)
        stop, reason = ctrl.should_stop()
        assert stop is True
        assert reason == "budget_exhausted"

    def test_should_stop_all_completed(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000, total_modules=2,
        )
        ctrl.allocate("m1", 1000)
        ctrl.record_usage("m1", 800)
        ctrl.allocate("m2", 1000)
        ctrl.record_usage("m2", 900)
        stop, reason = ctrl.should_stop()
        assert stop is True
        assert reason == "all_modules_completed"

    def test_should_stop_consecutive_failures(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000,
            max_consecutive_failures=3,
        )
        ctrl.record_failure("m1")
        ctrl.record_failure("m2")
        ctrl.record_failure("m3")
        stop, reason = ctrl.should_stop()
        assert stop is True
        assert reason == "consecutive_failures"


class TestBudgetControllerRecordUsage:
    """Usage recording."""

    def test_record_usage(self):
        ctrl = AnalysisBudgetController(
            total_budget=100_000, total_modules=3,
        )
        ctrl.allocate("mod_a", 5000)
        ctrl.record_usage("mod_a", 4500)
        status = ctrl.get_status()
        assert status.used_tokens == 4500
        assert status.modules_analyzed == 1
        assert status.modules_remaining == 2


class TestBudgetControllerMCPInterface:
    """MCP-compatible dict interface."""

    def test_check_budget_status_dict(self):
        ctrl = AnalysisBudgetController(
            total_budget=50_000, total_modules=4,
        )
        result = ctrl.check_budget_status("proj_42")
        assert isinstance(result, dict)
        assert result["project_id"] == "proj_42"
        assert result["status"] == "ok"
        assert "summary" in result
        assert "data" in result
        data = result["data"]
        assert data["total_budget"] == 50_000
        assert data["remaining_tokens"] == 50_000
        assert data["should_stop"] is False
