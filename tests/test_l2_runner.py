"""Tests for the product-owned deterministic L2 directory fallback seam."""
from __future__ import annotations

from src.semantic.l2_cluster import (
    CandidateCluster,
    UnassignedFile,
    compose_candidates_with_directory_fallback,
)


def test_runner_composes_directory_fallback_without_mixing_seed_kinds():
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

    candidates, remaining, fallback = compose_candidates_with_directory_fallback(
        surface, residual, {"plugins/a.py": 4, "plugins/b.py": 5}
    )

    assert remaining == ()
    assert [c.cluster_id for c in candidates] == ["feature--api", "dirseed--plugins--L0"]
    assert candidates[-1].layer_index == 0
    assert {c.seed_kind for c in candidates} == {"public_surface", "directory"}
    assert fallback["applied"] is True
    assert fallback["cluster_count"] == 1
    assert fallback["absorbed_paths"] == ["plugins/a.py", "plugins/b.py"]
    assert fallback["absorbed_symbol_count"] == 9
    assert fallback["unassigned_before"] == 2
    assert fallback["unassigned_after"] == 0


def test_runner_composition_without_residuals_is_a_no_op():
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

    candidates, remaining, fallback = compose_candidates_with_directory_fallback(
        surface, (), {}
    )

    assert candidates == surface
    assert remaining == ()
    assert fallback == {
        "applied": False,
        "cluster_count": 0,
        "absorbed_paths": [],
        "absorbed_symbol_count": 0,
        "unassigned_before": 0,
        "unassigned_after": 0,
    }
