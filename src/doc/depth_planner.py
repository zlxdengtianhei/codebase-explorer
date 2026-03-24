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


CONTEXT_BUDGET = 100_000
"""Default token budget per agent task context window."""

SPLIT_FILL_RATIO = 0.8
"""When splitting a large cone, fill each part to 80% of usable budget."""

INFRA_CONTEXT_TOKENS = 2_000
"""Token budget reserved per task for infrastructure context summaries."""


def _collect_cone_files(cone_data: dict) -> list[str]:
    """Return all exclusive files from a cone data dict (immutable helper)."""
    return list(cone_data.get("exclusive_files", []))


def _cone_exclusive_tokens(
    cone_data: dict, file_tokens: dict[str, int],
) -> int:
    """Sum exclusive-file tokens for a cone (immutable helper)."""
    return sum(
        file_tokens.get(f, 0)
        for f in cone_data.get("exclusive_files", [])
    )


def _split_cone_by_dag_layer(
    cone_id: str,
    cone_data: dict,
    file_tokens: dict[str, int],
    usable_budget: int,
    start_id: int,
) -> list[dict]:
    """Split an oversized cone into multiple tasks grouped by DAG layer.

    Files are grouped by their cone-internal layer (from ``layers_within_cone``
    or the cone-level ``layer`` field).  When no per-file layer information is
    available, files are ordered by descending token count and packed greedily.

    Each resulting part fills up to ``SPLIT_FILL_RATIO * usable_budget`` tokens.

    Args:
        cone_id: Identifier of the cone being split.
        cone_data: Cone metadata dict with ``exclusive_files``, ``layer``, etc.
        file_tokens: Global file-path -> token map.
        usable_budget: Budget available after reserving infrastructure context.
        start_id: First task-counter value for numbering the split parts.

    Returns:
        List of task dicts (one per split part), ready to merge into the
        manifest ``tasks`` dict.
    """
    exclusive_files = _collect_cone_files(cone_data)
    target_tokens = int(usable_budget * SPLIT_FILL_RATIO)

    # Sort files by token count descending (largest first), which
    # approximates DAG-layer ordering when explicit layer info is absent.
    # When layers_within_cone is available we sort by layer descending first.
    layers_within = cone_data.get("layers_within_cone", {})

    def _file_sort_key(fp: str) -> tuple[int, int]:
        """(negative layer, negative tokens) so highest layer / largest come first."""
        layer = -1  # default: unknown
        for layer_idx, layer_files in layers_within.items():
            if fp in layer_files:
                layer = int(layer_idx)
                break
        return (-layer, -file_tokens.get(fp, 0))

    sorted_files = sorted(exclusive_files, key=_file_sort_key)

    # Greedily pack files into parts
    parts: list[list[str]] = []
    current_part: list[str] = []
    current_tokens = 0

    for fp in sorted_files:
        fp_tokens = file_tokens.get(fp, 0)
        if current_tokens + fp_tokens > target_tokens and current_part:
            parts.append(current_part)
            current_part = [fp]
            current_tokens = fp_tokens
        else:
            current_part.append(fp)
            current_tokens += fp_tokens

    if current_part:
        parts.append(current_part)

    # Build task dicts for each part
    n_parts = len(parts)
    split_tasks: list[dict] = []
    shared_deps = list(cone_data.get("shared_deps", []))

    for idx, part_files in enumerate(parts):
        task_id = f"task_{start_id + idx:03d}"
        part_tokens = sum(file_tokens.get(f, 0) for f in part_files)
        total_tokens = part_tokens + INFRA_CONTEXT_TOKENS

        dependencies: list[str] = []
        if idx > 0:
            dependencies.append(f"task_{start_id + idx - 1:03d}")

        split_tasks.append({
            "task_id": task_id,
            "type": "split",
            "cone_ids": [cone_id],
            "split_total_parts": n_parts,
            "split_part_index": idx + 1,
            "files": part_files,
            "infrastructure_context": shared_deps,
            "exclusive_tokens": part_tokens,
            "infra_context_tokens": INFRA_CONTEXT_TOKENS,
            "total_tokens": total_tokens,
            "context_budget": part_tokens + INFRA_CONTEXT_TOKENS,
            "dependencies": dependencies,
            "status": "pending",
        })

    return split_tasks


def build_task_manifest(
    cones: dict[str, dict],
    file_tokens: dict[str, int],
    context_budget: int = CONTEXT_BUDGET,
) -> dict:
    """Build a task manifest for agent execution using FFD bin-packing.

    Implements the First-Fit Decreasing (FFD) algorithm defined in
    ``02a_code_analysis_v2.md`` Section 5.  Cones are sorted by
    ``exclusive_tokens`` descending and assigned to tasks as follows:

    * **split** -- cone tokens exceed ``context_budget``; the cone is split
      along DAG layers into multiple sub-tasks.
    * **single** -- cone fits within budget on its own (or is the sole
      occupant of a bin after first-fit).
    * **batch** -- multiple small cones packed into one task.

    A final **INDEX Assembly** task is always appended, depending on all
    preceding detail tasks.

    Args:
        cones: ``{cone_id: cone_data}`` where ``cone_data`` contains
            ``exclusive_files``, ``shared_deps``, ``layer``, etc.
        file_tokens: ``{file_path: estimated_tokens}`` for every file.
        context_budget: Maximum tokens per task (default ``CONTEXT_BUDGET``).

    Returns:
        Task manifest dict matching the ``05_task_manifest.json`` schema::

            {
                "schema_version": "2.0",
                "context_budget": 100000,
                "tasks": { "task_001": {...}, ... }
            }

    Example:
        >>> manifest = build_task_manifest(cones, file_tokens)
        >>> print(f"Created {len(manifest['tasks'])} tasks")
    """
    import math

    tasks: dict[str, dict] = {}
    task_counter = 1
    cone_count = len(cones)

    usable_budget = context_budget - INFRA_CONTEXT_TOKENS

    logger.info(
        "[TASK-PACK] Packing %d cones into tasks, budget=%d",
        cone_count, context_budget,
    )

    # Step 1: Sort cones by exclusive_tokens descending (FFD ordering)
    cone_sizes: list[tuple[str, int]] = []
    for cone_id, cone_data in cones.items():
        tokens = _cone_exclusive_tokens(cone_data, file_tokens)
        cone_sizes.append((cone_id, tokens))

    cone_sizes = sorted(cone_sizes, key=lambda x: x[1], reverse=True)

    # Step 2: Process each cone -- split / first-fit into bins
    #
    # open_bins tracks bins that still have capacity:
    #   each bin = {"task_id": str, "cone_ids": [...], "used_tokens": int}
    open_bins: list[dict] = []

    batch_count = 0
    single_count = 0
    split_count = 0

    for cone_id, cone_tokens in cone_sizes:
        cone_data = cones[cone_id]
        shared_deps = list(cone_data.get("shared_deps", []))
        exclusive_files = _collect_cone_files(cone_data)

        if cone_tokens > usable_budget:
            # Case A: Oversized cone -- split by DAG layer
            n_parts = math.ceil(
                cone_tokens / (usable_budget * SPLIT_FILL_RATIO),
            )
            split_tasks = _split_cone_by_dag_layer(
                cone_id, cone_data, file_tokens,
                usable_budget, task_counter,
            )
            for st in split_tasks:
                tasks[st["task_id"]] = st
            task_counter += len(split_tasks)
            split_count += len(split_tasks)
        else:
            # Case B: Try to fit into an existing open bin (First Fit)
            placed = False
            for b in open_bins:
                if b["remaining"] >= cone_tokens:
                    b["cone_ids"].append(cone_id)
                    b["used_tokens"] += cone_tokens
                    b["remaining"] -= cone_tokens
                    b["files"].extend(exclusive_files)
                    b["shared_deps"] = sorted(
                        set(b["shared_deps"]) | set(shared_deps),
                    )
                    placed = True
                    break

            if not placed:
                # Open a new bin
                new_bin = {
                    "task_id": f"task_{task_counter:03d}",
                    "cone_ids": [cone_id],
                    "used_tokens": cone_tokens,
                    "remaining": usable_budget - cone_tokens,
                    "files": list(exclusive_files),
                    "shared_deps": list(shared_deps),
                }
                open_bins.append(new_bin)
                task_counter += 1

    # Step 3: Convert open bins into Task entries
    for b in open_bins:
        task_type = "single" if len(b["cone_ids"]) == 1 else "batch"
        total_tokens = b["used_tokens"] + INFRA_CONTEXT_TOKENS

        tasks[b["task_id"]] = {
            "task_id": b["task_id"],
            "type": task_type,
            "cone_ids": b["cone_ids"],
            "files": b["files"],
            "infrastructure_context": b["shared_deps"],
            "exclusive_tokens": b["used_tokens"],
            "infra_context_tokens": INFRA_CONTEXT_TOKENS,
            "total_tokens": total_tokens,
            "context_budget": context_budget,
            "dependencies": [],
            "status": "pending",
        }
        if task_type == "batch":
            batch_count += 1
        else:
            single_count += 1

    # Step 4: Append INDEX Assembly task (depends on all preceding tasks)
    detail_task_ids = sorted(tasks.keys())
    index_task_id = f"task_{task_counter:03d}"
    index_infra_tokens = 8_000  # INDEX reads all SNIPPET.md files

    tasks[index_task_id] = {
        "task_id": index_task_id,
        "type": "index",
        "cone_ids": ["all"],
        "files": [],
        "infrastructure_context": [],
        "exclusive_tokens": 0,
        "infra_context_tokens": index_infra_tokens,
        "total_tokens": index_infra_tokens,
        "context_budget": context_budget,
        "dependencies": detail_task_ids,
        "status": "pending",
    }

    logger.info(
        "[TASK-PACK] Result: %d batch, %d single, %d split tasks",
        batch_count, single_count, split_count,
    )

    return {
        "schema_version": "2.0",
        "context_budget": context_budget,
        "total_tasks": len(tasks),
        "tasks": tasks,
    }
