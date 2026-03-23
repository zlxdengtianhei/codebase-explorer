"""Dynamic depth decision algorithm for documentation planning.

Implements the three-dimensional depth engine (design/depth_strategy.md):
1. Structural Depth -- based on subpackage_count.
2. Complexity Depth -- based on weighted function/class/line counts.
3. Token Depth -- based on estimated_tokens.

Final depth = max(structural, complexity, token), capped at 5.
Budget uses geometric-decay model with decay factor 0.6.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from src.graph.grouper import ModuleMetrics
from src.state.models import ModuleRecord

logger = logging.getLogger(__name__)

# -- Constants ---------------------------------------------------------------

MAX_DEPTH = 5

_STRUCTURAL_THRESHOLDS: tuple[tuple[int, int], ...] = (
    (0, 0), (2, 1), (5, 2), (10, 3), (20, 4),
)
_COMPLEXITY_THRESHOLDS: tuple[tuple[float, int], ...] = (
    (10.0, 0), (30.0, 1), (100.0, 2), (300.0, 3), (600.0, 4),
)
_TOKEN_THRESHOLDS: tuple[tuple[int, int], ...] = (
    (500, 0), (2_000, 1), (8_000, 2), (32_000, 3), (128_000, 4),
)
_MIN_BUDGETS_PER_LEVEL: dict[int, int] = {
    0: 800, 1: 1200, 2: 2000, 3: 1500, 4: 1500, 5: 1500,
}

_BASE_BUDGET_RATIO = 0.15
_DEPTH_MULTIPLIER = 0.5
_UTILITY_BUDGET_FACTOR = 0.6
_DECAY_FACTOR = 0.6
_MIN_BUDGET = 500
_MAX_BUDGET = 50_000
_MIN_LINES_PER_DOC = 30
_MIN_TOKENS_PER_DOC = 200
_MIN_FUNCTIONS_PER_DOC = 2
_MIN_CLASSES_PER_DOC = 1
_MIN_LINES_FOR_STANDALONE = 100
_SMALL_MODULE_MAX_COMPONENTS = 10
_SMALL_MODULE_MAX_LINES = 200

# -- Enums & data models (all immutable) ------------------------------------


class SplitStrategy(Enum):
    """How to subdivide a module into sub-documents."""
    SUBPACKAGE = "subpackage"
    CLASS = "class"
    FUNCTION_GROUP = "function_group"
    FILE = "file"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class DocumentPlan:
    """Plan for a single documentation node."""
    depth: int
    split_strategy: SplitStrategy
    doc_budget_per_level: tuple[int, ...]
    should_merge_parent: bool
    termination_reason: str


@dataclass(frozen=True)
class DocPlanNode:
    """A single node in the planned documentation tree."""
    path: str
    level: int
    target: str
    token_budget: int
    doc_type: str  # "index" | "overview" | "detail"
    parent_path: str | None
    children_paths: tuple[str, ...]


@dataclass(frozen=True)
class DocStructurePlan:
    """Complete documentation structure plan for a project."""
    doc_tree: tuple[DocPlanNode, ...]
    total_docs: int
    max_depth: int
    depth_decisions: dict[str, dict]

# -- Depth calculation helpers -----------------------------------------------


def _calc_structural_depth(subpackage_count: int) -> int:
    """Map subpackage count to structural depth (0-5)."""
    for threshold, depth in _STRUCTURAL_THRESHOLDS:
        if subpackage_count <= threshold:
            return depth
    return MAX_DEPTH


def _calc_complexity_depth(
    function_count: int, class_count: int,
    line_count: int, cyclomatic_complexity: float,
) -> int:
    """Map complexity score to complexity depth (0-5)."""
    score = (
        function_count * 1.0 + class_count * 3.0
        + line_count / 100.0 + cyclomatic_complexity * 2.0
    )
    for threshold, depth in _COMPLEXITY_THRESHOLDS:
        if score < threshold:
            return depth
    return MAX_DEPTH


def _calc_token_depth(estimated_tokens: int) -> int:
    """Map estimated token count to token depth (0-5)."""
    for threshold, depth in _TOKEN_THRESHOLDS:
        if estimated_tokens < threshold:
            return depth
    return MAX_DEPTH

# -- Public API: depth calculation -------------------------------------------


def calculate_depth(metrics: ModuleMetrics) -> int:
    """Calculate the optimal documentation depth for a module.

    Depth is the *maximum* of structural, complexity, and token depths,
    constrained by utility-module and small-module rules.

    Returns: Integer depth from 0 (summary only) to 5 (maximum nesting).
    """
    structural = _calc_structural_depth(metrics.subpackage_count)
    complexity = _calc_complexity_depth(
        metrics.function_count, metrics.class_count,
        metrics.line_count, 0.0,
    )
    token = _calc_token_depth(metrics.estimated_tokens)
    raw_depth = max(structural, complexity, token)

    if metrics.name.startswith("_utilities"):
        raw_depth = min(raw_depth, 2)
    if metrics.line_count < _MIN_LINES_FOR_STANDALONE and metrics.function_count < 5:
        raw_depth = 0

    # Small-module constraint: modules with few components stay flat (depth 1).
    # A module with fewer than 10 total components (functions + classes) and
    # fewer than 200 lines does not benefit from being split further.
    total_components = metrics.function_count + metrics.class_count
    if (
        raw_depth >= 2
        and total_components < _SMALL_MODULE_MAX_COMPONENTS
        and metrics.line_count < _SMALL_MODULE_MAX_LINES
    ):
        raw_depth = 1

    return min(raw_depth, MAX_DEPTH)

# -- Split strategy selection ------------------------------------------------


def select_split_strategy(metrics: ModuleMetrics) -> SplitStrategy:
    """Select the optimal split strategy for sub-documents.

    Priority: SUBPACKAGE > CLASS > FUNCTION_GROUP > HYBRID > FILE.
    """
    if metrics.subpackage_count >= 2:
        return SplitStrategy.SUBPACKAGE
    if metrics.class_count >= 3:
        if metrics.class_count / max(metrics.function_count, 1) >= 0.3:
            return SplitStrategy.CLASS
    if metrics.function_count >= 5 and metrics.class_count <= 2:
        return SplitStrategy.FUNCTION_GROUP
    if metrics.file_count >= 5 and metrics.class_count >= 2 and metrics.function_count >= 10:
        return SplitStrategy.HYBRID
    return SplitStrategy.FILE

# -- Termination conditions --------------------------------------------------


def should_terminate(
    current_depth: int, metrics: ModuleMetrics, remaining_budget: int,
) -> tuple[bool, str]:
    """Determine whether to stop generating deeper documents.

    Returns: Tuple of (should_stop, reason).
    """
    if current_depth >= MAX_DEPTH:
        return True, f"max_depth_reached ({MAX_DEPTH})"
    if metrics.line_count < _MIN_LINES_PER_DOC:
        return True, f"below_min_lines ({metrics.line_count} < {_MIN_LINES_PER_DOC})"
    if remaining_budget < _MIN_TOKENS_PER_DOC:
        return True, f"budget_exhausted ({remaining_budget} < {_MIN_TOKENS_PER_DOC})"
    if metrics.function_count < _MIN_FUNCTIONS_PER_DOC and metrics.class_count < _MIN_CLASSES_PER_DOC:
        return True, "no_meaningful_split"
    if metrics.name.startswith("_utilities") and current_depth >= 2:
        return True, "utility_module_depth_limit"
    if metrics.file_count == 1 and metrics.class_count <= 1:
        return True, "single_unit_file"
    return False, ""

# -- Token budget allocation -------------------------------------------------


def calculate_total_budget(metrics: ModuleMetrics, depth: int) -> int:
    """Calculate total documentation token budget for a module.

    Base budget is ~15% of source tokens, scaled by depth multiplier.
    """
    base_ratio = _BASE_BUDGET_RATIO
    if metrics.name.startswith("_utilities"):
        base_ratio *= _UTILITY_BUDGET_FACTOR
    depth_multiplier = 1.0 + depth * _DEPTH_MULTIPLIER
    base_budget = int(metrics.estimated_tokens * base_ratio * depth_multiplier)
    return max(_MIN_BUDGET, min(_MAX_BUDGET, base_budget))


def allocate_budget_per_level(total_budget: int, depth: int) -> tuple[int, ...]:
    """Distribute budget across levels using geometric decay (factor 0.6).

    Per-level minimums are enforced; result is re-normalised if total
    exceeds the budget.
    """
    if depth == 0:
        return (min(total_budget, 300),)

    weights = tuple(_DECAY_FACTOR ** i for i in range(depth + 1))
    total_weight = sum(weights)
    budgets = [int(total_budget * w / total_weight) for w in weights]

    for i in range(len(budgets)):
        budgets[i] = max(budgets[i], _MIN_BUDGETS_PER_LEVEL.get(i, 1500))

    total_allocated = sum(budgets)
    if total_allocated > total_budget:
        scale = total_budget / total_allocated if total_allocated > 0 else 1.0
        budgets = [int(b * scale) for b in budgets]

    return tuple(budgets)

# -- Single-module documentation planning ------------------------------------


def plan_documentation(metrics: ModuleMetrics) -> DocumentPlan:
    """Create a complete documentation plan for one module.

    Steps: calculate depth, check merge, select split, allocate budget.
    """
    depth = calculate_depth(metrics)

    if depth == 0 or metrics.line_count < _MIN_LINES_FOR_STANDALONE:
        return DocumentPlan(
            depth=0, split_strategy=SplitStrategy.FILE,
            doc_budget_per_level=(300,),
            should_merge_parent=True, termination_reason="below_minimum_size",
        )

    strategy = select_split_strategy(metrics)
    total_budget = calculate_total_budget(metrics, depth)
    budgets = allocate_budget_per_level(total_budget, depth)

    return DocumentPlan(
        depth=depth, split_strategy=strategy,
        doc_budget_per_level=budgets,
        should_merge_parent=False, termination_reason="",
    )

# -- Project-level doc structure planning ------------------------------------


def plan_doc_structure(
    project_id: str,
    modules: list[ModuleRecord],
    metrics: dict[str, ModuleMetrics],
) -> DocStructurePlan:
    """Plan the full documentation tree for a project.

    Produces a flat list of DocPlanNode entries with paths, levels,
    token budgets, and parent/children links.
    """
    from src.doc._tree_builder import build_doc_tree, depth_reason

    plans: dict[str, DocumentPlan] = {}
    depth_decisions: dict[str, dict] = {}

    for mod in modules:
        mod_metrics = metrics.get(mod.name)
        if mod_metrics is None:
            logger.warning("No metrics for module %s; skipping", mod.name)
            continue
        plan = plan_documentation(mod_metrics)
        plans[mod.name] = plan
        depth_decisions[mod.name] = {
            "depth": plan.depth,
            "split_strategy": plan.split_strategy.value,
            "should_merge_parent": plan.should_merge_parent,
            "reason": plan.termination_reason or depth_reason(mod_metrics, plan),
        }

    nodes = build_doc_tree(project_id, modules, plans, metrics)
    max_depth_val = max((n.level for n in nodes), default=0)

    logger.info(
        "Planned %d documents across %d depth levels for project %s",
        len(nodes), max_depth_val, project_id,
    )

    return DocStructurePlan(
        doc_tree=tuple(nodes), total_docs=len(nodes),
        max_depth=max_depth_val, depth_decisions=depth_decisions,
    )


# ---------------------------------------------------------------------------
# V2 Functions (DAG-based depth calculation and task manifest)
# ---------------------------------------------------------------------------


def calculate_feature_cone_depth(
    cone_tokens: int,
    dag_layers: int = 1,
    token_budget: int = 100000,
) -> int:
    """Calculate documentation depth for a feature cone based on DAG layers.

    V2 replacement for three-dimensional threshold tables.

    Args:
        cone_tokens: Estimated token count for the cone.
        dag_layers: Number of DAG layers in the cone (default: 1).
        token_budget: Available token budget for documentation.

    Returns:
        Recommended depth level (0-5).

    Example:
        >>> depth = calculate_feature_cone_depth(12000, dag_layers=3, token_budget=100000)
        >>> print(f"Depth: {depth}")
    """
    # Base depth from DAG layers (capped at 5)
    base_depth = min(dag_layers, MAX_DEPTH)

    # Adjust based on token budget
    # Small cones (low tokens) get reduced depth
    if cone_tokens < 2000:
        adjusted_depth = min(base_depth, 1)
    elif cone_tokens < 8000:
        adjusted_depth = min(base_depth, 2)
    elif cone_tokens < 32000:
        adjusted_depth = min(base_depth, 3)
    else:
        adjusted_depth = base_depth

    logger.info(
        "[depth_planner] cone depth=%d (dag_layers=%d, cone_tokens=%d, budget=%d)",
        adjusted_depth, dag_layers, cone_tokens, token_budget,
    )

    return adjusted_depth


def build_task_manifest(
    cones: dict[str, dict],
    file_tokens: dict[str, int],
    context_budget: int = 100000,
) -> dict:
    """Build task manifest for agent execution (V2).

    Implements First-Fit Decreasing (FFD) bin-packing algorithm to
    assign feature cones to batch/single/split tasks based on token budget.

    Args:
        cones: Dictionary of cone_id -> cone_data with exclusive_files, shared_deps.
        file_tokens: Dictionary of file_path -> estimated_tokens.
        context_budget: Maximum tokens per task (default: 100k).

    Returns:
        Task manifest dictionary for 05_task_manifest.json.

    Example:
        >>> manifest = build_task_manifest(cones, file_tokens, context_budget=100000)
        >>> print(f"Created {len(manifest['tasks'])} tasks")
    """
    tasks: dict[str, dict] = {}
    task_counter = 1

    # Sort cones by token count (decreasing) for FFD
    cone_sizes = []
    for cone_id, cone_data in cones.items():
        exclusive_files = cone_data.get("exclusive_files", [])
        total_tokens = sum(file_tokens.get(f, 0) for f in exclusive_files)
        cone_sizes.append((cone_id, total_tokens))

    cone_sizes.sort(key=lambda x: x[1], reverse=True)

    # Bin packing: assign cones to tasks
    current_batch: list[str] = []
    current_batch_tokens = 0
    batch_task_id = None

    for cone_id, cone_tokens in cone_sizes:
        # Large cone: single task
        if cone_tokens > context_budget * 0.8:
            task_id = f"task_{task_counter:03d}"
            tasks[task_id] = {
                "type": "single",
                "cone_ids": [cone_id],
                "estimated_tokens": cone_tokens,
                "status": "pending",
            }
            task_counter += 1
            logger.info(
                "[depth_planner] created single task %s for cone %s (%d tokens)",
                task_id, cone_id, cone_tokens,
            )

        # Fits in current batch
        elif current_batch_tokens + cone_tokens <= context_budget:
            current_batch.append(cone_id)
            current_batch_tokens += cone_tokens

        # Batch full, create task
        else:
            if current_batch:
                batch_task_id = f"task_{task_counter:03d}"
                tasks[batch_task_id] = {
                    "type": "batch",
                    "cone_ids": current_batch.copy(),
                    "estimated_tokens": current_batch_tokens,
                    "status": "pending",
                }
                task_counter += 1
                logger.info(
                    "[depth_planner] created batch task %s with %d cones (%d tokens)",
                    batch_task_id, len(current_batch), current_batch_tokens,
                )

            # Start new batch
            current_batch = [cone_id]
            current_batch_tokens = cone_tokens

    # Final batch
    if current_batch:
        batch_task_id = f"task_{task_counter:03d}"
        tasks[batch_task_id] = {
            "type": "batch",
            "cone_ids": current_batch.copy(),
            "estimated_tokens": current_batch_tokens,
            "status": "pending",
        }
        logger.info(
            "[depth_planner] created final batch task %s with %d cones (%d tokens)",
            batch_task_id, len(current_batch), current_batch_tokens,
        )

    logger.info(
        "[depth_planner] built task manifest: %d tasks for %d cones",
        len(tasks), len(cones),
    )

    return {
        "schema_version": "2.0",
        "tasks": tasks,
        "context_budget": context_budget,
    }
