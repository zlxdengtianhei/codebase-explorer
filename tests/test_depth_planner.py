"""Tests for src/doc/depth_planner.py -- documentation depth planning.

Covers:
- calculate_feature_cone_depth DAG-based depth
- build_task_manifest FFD bin-packing
- _split_cone_by_dag_layer layer splitting
"""
from __future__ import annotations

import pytest

from src.doc.depth_planner import (
    MAX_DEPTH,
    build_task_manifest,
    calculate_feature_cone_depth,
    CONTEXT_BUDGET,
    INFRA_CONTEXT_TOKENS,
)


# ---------------------------------------------------------------------------
# calculate_feature_cone_depth
# ---------------------------------------------------------------------------


class TestCalculateFeatureConeDepth:
    """Tests for DAG-based depth calculation."""

    def test_small_cone_capped_at_1(self) -> None:
        """Cones with <2000 tokens are capped at depth 1."""
        depth = calculate_feature_cone_depth(1000, dag_layers=5)
        assert depth <= 1

    def test_medium_cone_capped_at_2(self) -> None:
        """Cones with 2000-8000 tokens are capped at depth 2."""
        depth = calculate_feature_cone_depth(5000, dag_layers=5)
        assert depth <= 2

    def test_large_cone_capped_at_3(self) -> None:
        """Cones with 8000-32000 tokens are capped at depth 3."""
        depth = calculate_feature_cone_depth(20000, dag_layers=5)
        assert depth <= 3

    def test_very_large_cone_uses_dag_layers(self) -> None:
        """Cones with >=32000 tokens use base depth from dag_layers."""
        depth = calculate_feature_cone_depth(50000, dag_layers=4)
        assert depth == 4

    def test_dag_layers_capped_at_max_depth(self) -> None:
        """dag_layers > MAX_DEPTH are capped."""
        depth = calculate_feature_cone_depth(100000, dag_layers=10)
        assert depth == MAX_DEPTH

    def test_single_dag_layer(self) -> None:
        """Single DAG layer yields depth 1 for non-tiny cones."""
        depth = calculate_feature_cone_depth(10000, dag_layers=1)
        assert depth == 1

    def test_default_dag_layers(self) -> None:
        """Default dag_layers=1."""
        depth = calculate_feature_cone_depth(50000)
        assert depth == 1


# ---------------------------------------------------------------------------
# build_task_manifest
# ---------------------------------------------------------------------------


class TestBuildTaskManifest:
    """Tests for FFD bin-packing task manifest builder."""

    def test_empty_cones(self) -> None:
        """No cones produces manifest with only the INDEX task."""
        manifest = build_task_manifest({}, {})
        assert manifest["schema_version"] == "2.0"
        assert manifest["total_tasks"] == 1
        tasks = manifest["tasks"]
        index_task = list(tasks.values())[0]
        assert index_task["type"] == "index"

    def test_single_small_cone(self) -> None:
        """One small cone produces a single task + INDEX."""
        cones = {
            "cone_a": {
                "exclusive_files": ["a.py", "b.py"],
                "shared_deps": [],
            }
        }
        file_tokens = {"a.py": 500, "b.py": 300}
        manifest = build_task_manifest(cones, file_tokens)
        assert manifest["total_tasks"] == 2  # 1 single + 1 index
        tasks = manifest["tasks"]
        detail_tasks = [t for t in tasks.values() if t["type"] != "index"]
        assert len(detail_tasks) == 1
        assert detail_tasks[0]["type"] == "single"

    def test_batching_small_cones(self) -> None:
        """Multiple small cones that fit are batched together."""
        cones = {
            f"cone_{i}": {
                "exclusive_files": [f"file_{i}.py"],
                "shared_deps": [],
            }
            for i in range(5)
        }
        file_tokens = {f"file_{i}.py": 100 for i in range(5)}
        manifest = build_task_manifest(cones, file_tokens)
        tasks = manifest["tasks"]
        non_index = [t for t in tasks.values() if t["type"] != "index"]
        # 5 cones * 100 tokens = 500 tokens total, fits in one bin
        assert any(t["type"] == "batch" for t in non_index)

    def test_oversized_cone_is_split(self) -> None:
        """A cone exceeding context_budget is split into multiple tasks."""
        # Create a cone with tokens exceeding context_budget
        big_files = [f"big_{i}.py" for i in range(20)]
        cones = {
            "big_cone": {
                "exclusive_files": big_files,
                "shared_deps": [],
            }
        }
        # Each file = 10000 tokens, total = 200000 > 100000 budget
        file_tokens = {f: 10000 for f in big_files}
        manifest = build_task_manifest(cones, file_tokens, context_budget=100_000)
        tasks = manifest["tasks"]
        split_tasks = [t for t in tasks.values() if t["type"] == "split"]
        assert len(split_tasks) >= 2

    def test_index_task_depends_on_all(self) -> None:
        """The INDEX task depends on all preceding detail tasks."""
        cones = {
            "cone_a": {"exclusive_files": ["a.py"], "shared_deps": []},
            "cone_b": {"exclusive_files": ["b.py"], "shared_deps": []},
        }
        file_tokens = {"a.py": 1000, "b.py": 1000}
        manifest = build_task_manifest(cones, file_tokens)
        tasks = manifest["tasks"]
        index_tasks = [t for t in tasks.values() if t["type"] == "index"]
        assert len(index_tasks) == 1
        index_task = index_tasks[0]
        detail_ids = sorted(
            t["task_id"] for t in tasks.values() if t["type"] != "index"
        )
        assert index_task["dependencies"] == detail_ids

    def test_manifest_schema_version(self) -> None:
        """Manifest contains schema_version 2.0."""
        manifest = build_task_manifest({}, {})
        assert manifest["schema_version"] == "2.0"
        assert manifest["context_budget"] == CONTEXT_BUDGET
