"""Build the flat doc-tree list from per-module DocumentPlans.

Provides ``build_doc_tree`` (called by ``plan_doc_structure``) and the
``depth_reason`` helper that generates a human-readable explanation of
a depth decision.
"""
from __future__ import annotations

from src.doc.depth_planner import (
    DocPlanNode,
    DocumentPlan,
    SplitStrategy,
)
from src.graph.grouper import ModuleMetrics
from src.state.models import ModuleRecord


def depth_reason(metrics: ModuleMetrics, plan: DocumentPlan) -> str:
    """Return a human-readable reason for the chosen depth/strategy."""
    parts: list[str] = []
    if plan.depth == 0:
        parts.append("summary_only")
    else:
        parts.append(f"depth={plan.depth}")
        parts.append(f"strategy={plan.split_strategy.value}")
    if metrics.line_count < 100:
        parts.append("small_module")
    if metrics.estimated_tokens > 32_000:
        parts.append("high_token_count")
    return "; ".join(parts) if parts else "default"


def build_doc_tree(
    project_id: str,
    modules: list[ModuleRecord],
    plans: dict[str, DocumentPlan],
    metrics: dict[str, ModuleMetrics],
) -> list[DocPlanNode]:
    """Build a flat list of DocPlanNode entries for the project.

    Always starts with an INDEX.md node at level 0, followed by per-module
    OVERVIEW nodes at level 1 and optional DETAIL nodes at level 2+.
    """
    nodes: list[DocPlanNode] = []
    module_overview_paths: list[str] = []

    for mod in modules:
        plan = plans.get(mod.name)
        if plan is None:
            continue

        overview_path = f"{mod.name}/OVERVIEW.md"
        module_overview_paths.append(overview_path)

        children_paths: list[str] = []

        # Add detail nodes for depth >= 2
        if plan.depth >= 2:
            mod_metrics = metrics.get(mod.name)
            if mod_metrics is not None:
                detail_targets = _detail_targets(mod_metrics, plan)
                for target_name in detail_targets:
                    detail_path = f"{mod.name}/{target_name}/DETAIL.md"
                    children_paths.append(detail_path)
                    detail_budget = (
                        plan.doc_budget_per_level[2]
                        if len(plan.doc_budget_per_level) > 2
                        else 1500
                    )
                    nodes.append(DocPlanNode(
                        path=detail_path,
                        level=2,
                        target=target_name,
                        token_budget=detail_budget,
                        doc_type="detail",
                        parent_path=overview_path,
                        children_paths=(),
                    ))

        overview_budget = (
            plan.doc_budget_per_level[1]
            if len(plan.doc_budget_per_level) > 1
            else plan.doc_budget_per_level[0]
        )
        nodes.append(DocPlanNode(
            path=overview_path,
            level=1,
            target=mod.name,
            token_budget=overview_budget,
            doc_type="overview",
            parent_path="INDEX.md",
            children_paths=tuple(children_paths),
        ))

    # INDEX node at level 0 (always present)
    index_budget = 800
    if plans:
        first_plan = next(iter(plans.values()))
        index_budget = first_plan.doc_budget_per_level[0]

    nodes.insert(0, DocPlanNode(
        path="INDEX.md",
        level=0,
        target="root",
        token_budget=index_budget,
        doc_type="index",
        parent_path=None,
        children_paths=tuple(module_overview_paths),
    ))

    return nodes


def _detail_targets(
    metrics: ModuleMetrics, plan: DocumentPlan,
) -> list[str]:
    """Generate detail-level target names based on the split strategy."""
    if plan.split_strategy == SplitStrategy.CLASS:
        return [f"class_{i}" for i in range(min(metrics.class_count, 5))]
    if plan.split_strategy == SplitStrategy.FUNCTION_GROUP:
        groups = max(1, metrics.function_count // 5)
        return [f"func_group_{i}" for i in range(min(groups, 5))]
    if plan.split_strategy == SplitStrategy.SUBPACKAGE:
        return [f"subpkg_{i}" for i in range(min(metrics.subpackage_count, 5))]
    # FILE or HYBRID fallback
    return [f"file_{i}" for i in range(min(metrics.file_count, 5))]
