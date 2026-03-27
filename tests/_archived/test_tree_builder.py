"""Tests for src/doc/_tree_builder.py -- documentation tree construction.

Covers:
- build_doc_tree with various module structures
- depth_reason human-readable explanations
- Edge cases: empty modules, single-file modules, no plans
- Detail node generation for different split strategies
"""
from __future__ import annotations

import pytest

from src.doc._tree_builder import build_doc_tree, depth_reason
from src.doc.depth_planner import (
    DocPlanNode,
    DocumentPlan,
    SplitStrategy,
)
from src.graph.grouper import ModuleMetrics
from src.state.models import ModuleRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _metrics(
    name: str = "core",
    file_count: int = 5,
    function_count: int = 10,
    class_count: int = 3,
    line_count: int = 500,
    estimated_tokens: int = 5000,
    subpackage_count: int = 0,
) -> ModuleMetrics:
    return ModuleMetrics(
        name=name,
        file_count=file_count,
        function_count=function_count,
        class_count=class_count,
        line_count=line_count,
        estimated_tokens=estimated_tokens,
        internal_edges=0,
        external_edges=0,
        subpackage_count=subpackage_count,
    )


def _module_record(name: str) -> ModuleRecord:
    return ModuleRecord(
        id=f"mod_{name}",
        project_id="proj_1",
        name=name,
    )


def _plan(
    depth: int = 1,
    strategy: SplitStrategy = SplitStrategy.FILE,
    budgets: tuple[int, ...] = (800, 1200),
    merge: bool = False,
    reason: str = "",
) -> DocumentPlan:
    return DocumentPlan(
        depth=depth,
        split_strategy=strategy,
        doc_budget_per_level=budgets,
        should_merge_parent=merge,
        termination_reason=reason,
    )


# ---------------------------------------------------------------------------
# build_doc_tree
# ---------------------------------------------------------------------------


class TestBuildDocTree:
    """Tests for build_doc_tree directly."""

    def test_empty_modules_produces_index_only(self) -> None:
        """No modules yields only the INDEX node with default budget."""
        nodes = build_doc_tree("proj_1", [], {}, {})
        assert len(nodes) == 1
        assert nodes[0].path == "INDEX.md"
        assert nodes[0].level == 0
        assert nodes[0].doc_type == "index"
        assert nodes[0].children_paths == ()

    def test_single_module_depth_one(self) -> None:
        """Single module with depth 1 produces INDEX + OVERVIEW."""
        mod = _module_record("core")
        plan = _plan(depth=1, budgets=(800, 1200))
        metrics = {"core": _metrics(name="core")}
        nodes = build_doc_tree("proj_1", [mod], {"core": plan}, metrics)

        assert len(nodes) == 2
        # First node is INDEX
        assert nodes[0].path == "INDEX.md"
        assert nodes[0].doc_type == "index"
        assert nodes[0].children_paths == ("core/OVERVIEW.md",)
        # Second node is OVERVIEW
        assert nodes[1].path == "core/OVERVIEW.md"
        assert nodes[1].level == 1
        assert nodes[1].doc_type == "overview"
        assert nodes[1].parent_path == "INDEX.md"
        assert nodes[1].token_budget == 1200

    def test_module_depth_two_generates_detail_nodes(self) -> None:
        """Depth 2 with CLASS strategy generates detail nodes."""
        mod = _module_record("models")
        plan = _plan(depth=2, strategy=SplitStrategy.CLASS,
                     budgets=(800, 1200, 1500))
        metrics = {"models": _metrics(name="models", class_count=4)}
        nodes = build_doc_tree("proj_1", [mod], {"models": plan}, metrics)

        # INDEX + OVERVIEW + 4 DETAIL nodes (class_0..class_3, capped at 5)
        detail_nodes = [n for n in nodes if n.doc_type == "detail"]
        assert len(detail_nodes) == 4
        assert all(n.level == 2 for n in detail_nodes)
        assert all(n.parent_path == "models/OVERVIEW.md" for n in detail_nodes)
        assert detail_nodes[0].path == "models/class_0/DETAIL.md"
        assert detail_nodes[0].token_budget == 1500

    def test_multiple_modules(self) -> None:
        """Multiple modules produce INDEX + one OVERVIEW per module."""
        mods = [_module_record("api"), _module_record("db")]
        plans = {
            "api": _plan(depth=1, budgets=(800, 1200)),
            "db": _plan(depth=1, budgets=(800, 1000)),
        }
        metrics = {
            "api": _metrics(name="api"),
            "db": _metrics(name="db"),
        }
        nodes = build_doc_tree("proj_1", mods, plans, metrics)

        # INDEX + 2 OVERVIEW = 3
        assert len(nodes) == 3
        overview_paths = {n.path for n in nodes if n.doc_type == "overview"}
        assert overview_paths == {"api/OVERVIEW.md", "db/OVERVIEW.md"}
        # INDEX children should list both overviews
        assert set(nodes[0].children_paths) == {"api/OVERVIEW.md", "db/OVERVIEW.md"}

    def test_module_without_plan_is_skipped(self) -> None:
        """Modules with no matching plan are excluded from the tree."""
        mods = [_module_record("core"), _module_record("orphan")]
        plans = {"core": _plan(depth=1, budgets=(800, 1200))}
        metrics = {"core": _metrics(name="core")}
        nodes = build_doc_tree("proj_1", mods, plans, metrics)

        # INDEX + core OVERVIEW = 2 (orphan skipped)
        assert len(nodes) == 2
        all_paths = {n.path for n in nodes}
        assert "orphan/OVERVIEW.md" not in all_paths

    def test_subpackage_strategy_detail_targets(self) -> None:
        """SUBPACKAGE strategy names details as subpkg_N."""
        mod = _module_record("pkg")
        plan = _plan(depth=2, strategy=SplitStrategy.SUBPACKAGE,
                     budgets=(800, 1200, 1500))
        metrics = {"pkg": _metrics(name="pkg", subpackage_count=3)}
        nodes = build_doc_tree("proj_1", [mod], {"pkg": plan}, metrics)

        detail_nodes = [n for n in nodes if n.doc_type == "detail"]
        assert len(detail_nodes) == 3
        assert detail_nodes[0].target == "subpkg_0"
        assert detail_nodes[2].target == "subpkg_2"

    def test_function_group_strategy_detail_targets(self) -> None:
        """FUNCTION_GROUP strategy names details as func_group_N."""
        mod = _module_record("utils")
        plan = _plan(depth=2, strategy=SplitStrategy.FUNCTION_GROUP,
                     budgets=(800, 1200, 1500))
        metrics = {"utils": _metrics(name="utils", function_count=15)}
        nodes = build_doc_tree("proj_1", [mod], {"utils": plan}, metrics)

        detail_nodes = [n for n in nodes if n.doc_type == "detail"]
        # 15 // 5 = 3 groups
        assert len(detail_nodes) == 3
        assert detail_nodes[0].target == "func_group_0"

    def test_file_strategy_detail_targets(self) -> None:
        """FILE strategy names details as file_N."""
        mod = _module_record("misc")
        plan = _plan(depth=2, strategy=SplitStrategy.FILE,
                     budgets=(800, 1200, 1500))
        metrics = {"misc": _metrics(name="misc", file_count=4)}
        nodes = build_doc_tree("proj_1", [mod], {"misc": plan}, metrics)

        detail_nodes = [n for n in nodes if n.doc_type == "detail"]
        assert len(detail_nodes) == 4
        assert detail_nodes[0].target == "file_0"

    def test_index_budget_from_first_plan(self) -> None:
        """INDEX node budget comes from the first plan's level-0 budget."""
        mod = _module_record("core")
        plan = _plan(depth=1, budgets=(999, 1200))
        nodes = build_doc_tree("proj_1", [mod], {"core": plan}, {})
        assert nodes[0].token_budget == 999

    def test_overview_uses_level_0_when_only_one_level(self) -> None:
        """When plan has only 1 budget level, overview uses level 0."""
        mod = _module_record("tiny")
        plan = _plan(depth=1, budgets=(500,))
        nodes = build_doc_tree("proj_1", [mod], {"tiny": plan}, {})
        overview = [n for n in nodes if n.doc_type == "overview"][0]
        assert overview.token_budget == 500

    def test_detail_fallback_budget(self) -> None:
        """When plan has <3 budget levels, detail budget falls back to 1500."""
        mod = _module_record("shallow")
        plan = _plan(depth=2, strategy=SplitStrategy.CLASS,
                     budgets=(800, 1200))  # only 2 levels, no index 2
        metrics = {"shallow": _metrics(name="shallow", class_count=2)}
        nodes = build_doc_tree("proj_1", [mod], {"shallow": plan}, metrics)
        detail_nodes = [n for n in nodes if n.doc_type == "detail"]
        assert len(detail_nodes) == 2
        assert all(n.token_budget == 1500 for n in detail_nodes)


# ---------------------------------------------------------------------------
# depth_reason
# ---------------------------------------------------------------------------


class TestDepthReason:
    """Tests for human-readable depth reason generation."""

    def test_depth_zero_summary_only(self) -> None:
        """Depth 0 reports 'summary_only'."""
        m = _metrics(line_count=50)
        p = _plan(depth=0)
        reason = depth_reason(m, p)
        assert "summary_only" in reason

    def test_depth_nonzero_includes_strategy(self) -> None:
        """Non-zero depth includes depth and strategy."""
        m = _metrics(line_count=500)
        p = _plan(depth=2, strategy=SplitStrategy.CLASS)
        reason = depth_reason(m, p)
        assert "depth=2" in reason
        assert "strategy=class" in reason

    def test_small_module_annotation(self) -> None:
        """Modules with <100 lines get 'small_module' annotation."""
        m = _metrics(line_count=50)
        p = _plan(depth=1, strategy=SplitStrategy.FILE)
        reason = depth_reason(m, p)
        assert "small_module" in reason

    def test_high_token_count_annotation(self) -> None:
        """Modules with >32000 tokens get 'high_token_count' annotation."""
        m = _metrics(line_count=5000, estimated_tokens=50000)
        p = _plan(depth=3, strategy=SplitStrategy.SUBPACKAGE)
        reason = depth_reason(m, p)
        assert "high_token_count" in reason

    def test_empty_reason_returns_default(self) -> None:
        """When no annotations match, returns 'default'."""
        # depth > 0, line_count >= 100, estimated_tokens <= 32000
        m = _metrics(line_count=200, estimated_tokens=5000)
        p = _plan(depth=1, strategy=SplitStrategy.FILE)
        reason = depth_reason(m, p)
        # Should have depth=1, strategy=file but no small_module/high_token_count
        assert "depth=1" in reason
        assert "small_module" not in reason
        assert "high_token_count" not in reason
