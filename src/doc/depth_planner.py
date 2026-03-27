"""V5 depth calculation and task manifest builder.

DAG-based depth calculation and FFD bin-packing for agent task assignment.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAX_DEPTH = 5


# ---------------------------------------------------------------------------
# V2/V5 Functions (DAG-based depth calculation and task manifest)
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
