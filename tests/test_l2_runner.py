"""Tests for the deterministic evidence runner's L2 composition seam."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from src.semantic.l2_cluster import CandidateCluster, UnassignedFile


RUNNER_PATH = (
    Path(__file__).resolve().parents[3]
    / "runs/r004_20260816_layered_architecture/evidence/clus/run_l2.py"
)


def _runner_module():
    spec = importlib.util.spec_from_file_location("cbe_r004_l2_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_composes_directory_fallback_without_mixing_seed_kinds():
    runner = _runner_module()
    surface = (
        CandidateCluster(
            cluster_id="feature--api",
            kind="exclusive",
            signature=frozenset({"api"}),
            member_paths=("api.py",),
            symbol_count=3,
            signature_group_id="feature--api",
        ),
    )
    residual = (
        UnassignedFile("plugins/a.py", "unreferenced_public_module", "not reached"),
        UnassignedFile("plugins/b.py", "unreferenced_public_module", "not reached"),
    )

    candidates, remaining, fallback = runner.compose_candidates_with_directory_fallback(
        surface, residual, {"plugins/a.py": 4, "plugins/b.py": 5}
    )

    assert remaining == ()
    assert [c.cluster_id for c in candidates] == ["feature--api", "dirseed--plugins--L0"]
    assert candidates[-1].layer_index == 0
    assert {c.seed_kind for c in candidates} == {"public_surface", "directory"}
    assert fallback["absorbed_paths"] == ["plugins/a.py", "plugins/b.py"]
    assert fallback["cluster_count"] == 1
