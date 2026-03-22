"""Doc-tree builder for project-level documentation planning.

Internal module that builds the flat list of ``DocPlanNode`` entries
from per-module ``DocumentPlan`` results.  Called by
``depth_planner.plan_doc_structure``.
"""

from __future__ import annotations

import logging

from src.graph.grouper import ModuleMetrics
from src.state.models import ModuleRecord

from src.doc.depth_planner import (
    DocPlanNode,
    DocumentPlan,
    SplitStrategy,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public (to depth_planner)
# ---------------------------------------------------------------------------


def build_doc_tree(
    project_id: str,
    modules: list[ModuleRecord],
    plans: dict[str, DocumentPlan],
    metrics: dict[str, ModuleMetrics],
) -> list[DocPlanNode]:
    """Build the flat list of ``DocPlanNode`` for the project.

    Args:
        project_id: Unique project identifier.
        modules: Module records from the database.
        plans: Per-module documentation plans.
        metrics: Per-module metrics.

    Returns:
        List of ``DocPlanNode`` forming the documentation tree.
    """
    nodes: list[DocPlanNode] = []

    # Determine non-mergeable modules (depth > 0)
    active_modules = [
        m for m in modules
        if m.name in plans and not plans[m.name].should_merge_parent
    ]

    # Level 0: INDEX node
    overview_paths = tuple(f"{m.name}/OVERVIEW.md" for m in active_modules)
    index_budget = _index_budget(plans, active_modules)
    index_node = DocPlanNode(
        path="INDEX.md",
        level=0,
        target="root",
        token_budget=index_budget,
        doc_type="index",
        parent_path=None,
        children_paths=overview_paths,
    )
    nodes.append(index_node)

    # Level 1+: per-module subtrees
    for mod in active_modules:
        plan = plans[mod.name]
        mod_metrics = metrics.get(mod.name)
        subtree = _build_module_subtree(
            module_name=mod.name,
            plan=plan,
            mod_metrics=mod_metrics,
            parent_path="INDEX.md",
            current_level=1,
        )
        nodes.extend(subtree)

    return nodes


def depth_reason(metrics: ModuleMetrics, plan: DocumentPlan) -> str:
    """Build a human-readable reason string for the depth decision."""
    return (
        f"{metrics.line_count} lines, "
        f"{metrics.function_count} functions, "
        f"{metrics.class_count} classes, "
        f"depth={plan.depth}"
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _index_budget(
    plans: dict[str, DocumentPlan],
    active_modules: list[ModuleRecord],
) -> int:
    """Compute token budget for the INDEX document."""
    for mod in active_modules:
        plan = plans.get(mod.name)
        if plan and len(plan.doc_budget_per_level) > 0:
            return plan.doc_budget_per_level[0]
    return 800


def _build_module_subtree(
    module_name: str,
    plan: DocumentPlan,
    mod_metrics: ModuleMetrics | None,
    parent_path: str,
    current_level: int,
) -> list[DocPlanNode]:
    """Recursively build nodes for one module's subtree."""
    nodes: list[DocPlanNode] = []
    budgets = plan.doc_budget_per_level

    # Level 1: OVERVIEW
    level_budget = budgets[current_level] if current_level < len(budgets) else 1200

    # Determine children for this overview
    children_paths: tuple[str, ...] = ()
    if plan.depth >= 2:
        children_paths = _plan_children_paths(module_name, plan, mod_metrics)

    overview_path = f"{module_name}/OVERVIEW.md"
    overview_node = DocPlanNode(
        path=overview_path,
        level=current_level,
        target=module_name,
        token_budget=level_budget,
        doc_type="overview",
        parent_path=parent_path,
        children_paths=children_paths,
    )
    nodes.append(overview_node)

    # Level 2+: DETAIL nodes
    for child_path in children_paths:
        child_name = (
            child_path.rsplit("/", 1)[0] if "/" in child_path else child_path
        )
        child_level = current_level + 1
        child_budget = (
            budgets[child_level] if child_level < len(budgets) else 1500
        )

        detail_node = DocPlanNode(
            path=child_path,
            level=child_level,
            target=child_name.replace("/", "."),
            token_budget=child_budget,
            doc_type="detail",
            parent_path=overview_path,
            children_paths=(),
        )
        nodes.append(detail_node)

    return nodes


def _plan_children_paths(
    module_name: str,
    plan: DocumentPlan,
    mod_metrics: ModuleMetrics | None,
) -> tuple[str, ...]:
    """Determine child document paths based on split strategy."""
    if mod_metrics is None:
        return ()

    if plan.split_strategy == SplitStrategy.SUBPACKAGE:
        count = max(mod_metrics.subpackage_count, 1)
        return tuple(
            f"{module_name}/sub_{i}/DETAIL.md" for i in range(count)
        )

    if plan.split_strategy == SplitStrategy.CLASS:
        count = max(mod_metrics.class_count, 1)
        return tuple(
            f"{module_name}/class_{i}/DETAIL.md" for i in range(count)
        )

    if plan.split_strategy == SplitStrategy.FUNCTION_GROUP:
        group_count = max(1, mod_metrics.function_count // 5)
        return tuple(
            f"{module_name}/group_{i}/DETAIL.md" for i in range(group_count)
        )

    if plan.split_strategy == SplitStrategy.HYBRID:
        sub_count = max(mod_metrics.subpackage_count, 1)
        return tuple(
            f"{module_name}/component_{i}/DETAIL.md" for i in range(sub_count)
        )

    # FILE fallback
    count = max(mod_metrics.file_count, 1)
    return tuple(
        f"{module_name}/file_{i}/DETAIL.md" for i in range(count)
    )
