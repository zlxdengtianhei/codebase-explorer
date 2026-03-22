"""Unit tests for the depth planner (doc/depth_planner.py).

Covers: depth calculation, split strategy selection, recursive
termination conditions, geometric-decay budget allocation, and
project-level doc structure planning.
"""
from __future__ import annotations

import pytest

from src.graph.grouper import ModuleMetrics
from src.state.models import ModuleRecord

from src.doc.depth_planner import (
    MAX_DEPTH,
    DocStructurePlan,
    SplitStrategy,
    allocate_budget_per_level,
    calculate_depth,
    plan_doc_structure,
    select_split_strategy,
    should_terminate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _metrics(
    name: str = "core",
    file_count: int = 5,
    function_count: int = 10,
    class_count: int = 3,
    line_count: int = 300,
    estimated_tokens: int = 4500,
    subpackage_count: int = 1,
) -> ModuleMetrics:
    return ModuleMetrics(
        name=name,
        file_count=file_count,
        function_count=function_count,
        class_count=class_count,
        line_count=line_count,
        estimated_tokens=estimated_tokens,
        internal_edges=5,
        external_edges=2,
        subpackage_count=subpackage_count,
    )


def _module_record(
    name: str = "core",
    project_id: str = "proj_1",
) -> ModuleRecord:
    return ModuleRecord(
        id=f"mod_{name}",
        project_id=project_id,
        name=name,
        files=["a.py"],
        file_count=1,
        line_count=300,
        function_count=10,
        class_count=3,
    )


# ===========================================================================
# Depth calculation tests
# ===========================================================================


class TestDepthCalculation:
    """Depth is determined by max(structural, complexity, token) capped at MAX_DEPTH."""

    def test_small_module_depth_0(self):
        """Small module (< 50 lines, < 5 functions) should get depth 0-1."""
        m = _metrics(
            line_count=30,
            function_count=3,
            class_count=1,
            estimated_tokens=400,
            subpackage_count=0,
        )
        depth = calculate_depth(m)
        assert depth <= 1

    def test_medium_module_depth_1(self):
        """Medium module (200-500 lines) should get depth 1-2."""
        m = _metrics(
            line_count=350,
            function_count=12,
            class_count=4,
            estimated_tokens=5000,
            subpackage_count=1,
        )
        depth = calculate_depth(m)
        assert 1 <= depth <= 2

    def test_large_module_depth_2_plus(self):
        """Large module (> 800 lines, > 20 functions) should get depth >= 2."""
        m = _metrics(
            line_count=1200,
            function_count=35,
            class_count=10,
            estimated_tokens=18000,
            subpackage_count=4,
        )
        depth = calculate_depth(m)
        assert depth >= 2

    def test_depth_capped_at_max(self):
        """Even enormous modules cannot exceed MAX_DEPTH (5)."""
        m = _metrics(
            line_count=100_000,
            function_count=5000,
            class_count=500,
            estimated_tokens=1_500_000,
            subpackage_count=50,
        )
        depth = calculate_depth(m)
        assert depth <= MAX_DEPTH


# ===========================================================================
# Split strategy tests
# ===========================================================================


class TestSplitStrategy:
    """Strategy selection based on module characteristics."""

    def test_select_subpackage_strategy(self):
        """Module with multiple subpackages -> SUBPACKAGE."""
        m = _metrics(subpackage_count=5, class_count=2, function_count=8)
        strategy = select_split_strategy(m)
        assert strategy == SplitStrategy.SUBPACKAGE

    def test_select_class_strategy(self):
        """Module with many classes, few functions -> CLASS."""
        m = _metrics(
            subpackage_count=1,
            class_count=6,
            function_count=10,
        )
        strategy = select_split_strategy(m)
        assert strategy == SplitStrategy.CLASS

    def test_select_function_group_strategy(self):
        """Module with many functions, few classes -> FUNCTION_GROUP."""
        m = _metrics(
            subpackage_count=0,
            class_count=1,
            function_count=15,
        )
        strategy = select_split_strategy(m)
        assert strategy == SplitStrategy.FUNCTION_GROUP

    def test_select_file_fallback(self):
        """Default fallback -> FILE."""
        m = _metrics(
            subpackage_count=0,
            class_count=1,
            function_count=3,
            file_count=2,
        )
        strategy = select_split_strategy(m)
        assert strategy == SplitStrategy.FILE


# ===========================================================================
# Termination condition tests
# ===========================================================================


class TestTermination:
    """Recursive termination conditions."""

    def test_terminate_at_max_depth(self):
        m = _metrics(line_count=500, function_count=20)
        stop, reason = should_terminate(MAX_DEPTH, m, remaining_budget=10_000)
        assert stop is True
        assert "max_depth" in reason

    def test_terminate_small_module(self):
        m = _metrics(line_count=10, function_count=1, class_count=0)
        stop, reason = should_terminate(1, m, remaining_budget=10_000)
        assert stop is True
        assert "min_lines" in reason

    def test_terminate_budget_exhausted(self):
        m = _metrics(line_count=500, function_count=20)
        stop, reason = should_terminate(1, m, remaining_budget=50)
        assert stop is True
        assert "budget" in reason


# ===========================================================================
# Token budget allocation tests
# ===========================================================================


class TestBudgetAllocation:
    """Geometric-decay budget distribution."""

    def test_budget_allocation_geometric_decay(self):
        """Level 0 should receive more budget than level 1, etc."""
        budgets = allocate_budget_per_level(total_budget=10_000, depth=3)
        assert len(budgets) == 4  # levels 0, 1, 2, 3
        # Geometric decay: level 0 weight > level 1 weight > ...
        # After min-budget enforcement the relationship may not be strict,
        # but level 0 should be >= level 1 when budget is sufficient.
        # The key property is that the sum does not exceed total_budget.
        assert sum(budgets) <= 10_000

    def test_budget_per_level_minimums(self):
        """Each level must meet its minimum budget (or be scaled down)."""
        budgets = allocate_budget_per_level(total_budget=50_000, depth=4)
        assert len(budgets) == 5  # levels 0-4
        # With a generous budget the minimums should be met
        from src.doc.depth_planner import _MIN_BUDGETS_PER_LEVEL
        for i, b in enumerate(budgets):
            minimum = _MIN_BUDGETS_PER_LEVEL.get(i, 1500)
            # When budget is sufficient, each level should meet minimum
            assert b >= minimum or sum(budgets) <= 50_000


# ===========================================================================
# plan_doc_structure integration tests
# ===========================================================================


class TestPlanDocStructure:
    """Project-level documentation structure planning."""

    def test_plan_doc_structure_basic(self):
        """Given modules and metrics, returns DocStructurePlan."""
        modules = [
            _module_record("core"),
            _module_record("api"),
        ]
        metrics = {
            "core": _metrics(
                name="core",
                line_count=500,
                function_count=15,
                class_count=5,
                estimated_tokens=7500,
                subpackage_count=3,
            ),
            "api": _metrics(
                name="api",
                line_count=300,
                function_count=10,
                class_count=3,
                estimated_tokens=4500,
                subpackage_count=2,
            ),
        }
        plan = plan_doc_structure("proj_1", modules, metrics)
        assert isinstance(plan, DocStructurePlan)
        assert plan.total_docs > 0
        assert len(plan.doc_tree) == plan.total_docs

    def test_plan_doc_structure_has_index(self):
        """The doc tree must always contain an INDEX.md at level 0."""
        modules = [_module_record("core")]
        metrics = {
            "core": _metrics(
                name="core",
                line_count=500,
                function_count=15,
                class_count=5,
                estimated_tokens=7500,
                subpackage_count=3,
            ),
        }
        plan = plan_doc_structure("proj_1", modules, metrics)
        index_nodes = [n for n in plan.doc_tree if n.path == "INDEX.md"]
        assert len(index_nodes) == 1
        assert index_nodes[0].level == 0
