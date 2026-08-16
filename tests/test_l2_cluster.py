"""Tests for deterministic L2 partitioning and naming contracts."""
from __future__ import annotations

import networkx as nx
import pytest

from src.graph.file_cards import FileCard, TopSymbol
from src.graph.feature_cone import SurfaceReachability
from src.semantic.l2_cluster import (
    CandidateCluster,
    ClusterError,
    L2Partition,
    UnassignedFile,
    apply_directory_fallback,
    assemble_clusters,
    build_naming_prompt,
    cluster_cohesion,
    cluster_relations,
    measure_single_file_cluster_distances,
    name_is_structural,
    partition_by_shared_signature,
)


def _reachability() -> SurfaceReachability:
    return SurfaceReachability(
        seed_paths=("entry-a", "entry-b"),
        closures={
            "entry-a": frozenset({"a1", "a2", "shared"}),
            "entry-b": frozenset({"entry-b", "shared"}),
        },
        signatures={
            "a1": frozenset({"entry-a"}),
            "a2": frozenset({"entry-a"}),
            "shared": frozenset({"entry-a", "entry-b"}),
        },
        unreached=("orphan.py",),
    )


def test_partition_groups_exact_shared_signatures_and_exposes_residual_reason():
    graph = nx.DiGraph([("a1", "a2")])
    graph.add_nodes_from(("shared", "orphan.py"))
    paths = ("a1", "a2", "shared", "orphan.py")
    first, residuals = partition_by_shared_signature(
        _reachability(), graph, paths, {"a1": 1, "a2": 1, "shared": 2}, max_files=1
    )
    second, second_residuals = partition_by_shared_signature(
        _reachability(), graph, paths, {"a1": 1, "a2": 1, "shared": 2}, max_files=1
    )
    assert first == second
    assert residuals == second_residuals
    assert {candidate.member_paths for candidate in first} == {("a1",), ("a2",), ("shared",)}
    assert residuals[0].path == "orphan.py"
    assert residuals[0].reason
    assert residuals[0].reason_code == "unreferenced_public_module"
    assert {candidate.signature for candidate in first if candidate.member_paths == ("shared",)} == {
        frozenset({"entry-a", "entry-b"})
    }


def test_cluster_relations_carry_file_edge_evidence():
    graph = nx.DiGraph([("feature", "shared")])
    reachability = SurfaceReachability(
        seed_paths=("entry",),
        closures={"entry": frozenset({"feature", "shared"})},
        signatures={"feature": frozenset({"entry"}), "shared": frozenset({"entry", "other"})},
        unreached=(),
    )
    candidates, _ = partition_by_shared_signature(
        reachability, graph, ("feature", "shared"), {"feature": 1, "shared": 1}
    )
    relations = cluster_relations(candidates, graph)
    feature = next(candidate for candidate in candidates if candidate.member_paths == ("feature",))
    shared = next(candidate for candidate in candidates if candidate.member_paths == ("shared",))
    relation = relations[feature.cluster_id][0]
    assert relation.to_cluster == shared.cluster_id
    assert relation.edge_evidence == (("feature", "shared"),)
    assert relation.evidence_granularity == "file"


def test_naming_payload_is_fixed_partition_and_source_free():
    candidates, _ = partition_by_shared_signature(
        _reachability(), nx.DiGraph(), ("a1", "a2", "shared"), {"a1": 1, "a2": 1, "shared": 2}
    )
    cards = tuple(
        FileCard(
            path=path,
            language="python",
            exported_names=(),
            symbol_count=1,
            symbol_kinds={"function": 1},
            top_symbols=(TopSymbol("s", "does one thing"),),
            effects_histogram={},
            out_files=(),
            in_files=(),
        )
        for path in ("a1", "a2", "shared")
    )
    prompt = build_naming_prompt(candidates, cards, {}, repo_name="fixture")
    assert "The partition is already computed" in prompt
    assert "behavior" not in prompt
    assert "source_body" not in prompt
    assert "does one thing" in prompt
    assert name_is_structural("shared infrastructure")
    assert not name_is_structural("send an HTTP request")


def test_partition_readings_include_confidence_and_unassigned_share():
    candidates, unassigned = partition_by_shared_signature(
        _reachability(), nx.DiGraph(), ("a1", "a2", "shared", "orphan.py"), {"a1": 4, "a2": 4, "shared": 2}
    )
    named = {
        candidate.cluster_id: {
            "name": "send a request",
            "purpose": "Sends requests through the public client.",
            "boundary_not": ["Does not configure deployment infrastructure."],
            "confidence": "medium",
        }
        for candidate in candidates
    }
    clusters, diagnostics = assemble_clusters(candidates, named, {}, {})
    assert not diagnostics
    readings = L2Partition(clusters, candidates, unassigned).readings(10, 4)
    assert readings["unassigned_path_share"] == 0.25
    assert readings["confidence_distribution"] == {"high": 0, "medium": len(clusters), "low": 0}
    assert readings["largest_cluster_symbol_share"] == 0.8


def test_empty_boundary_not_is_rejected():
    candidates, _ = partition_by_shared_signature(
        _reachability(), nx.DiGraph(), ("a1", "a2", "shared"), {"a1": 1, "a2": 1, "shared": 1}
    )
    named = {
        candidate.cluster_id: {
            "name": "send a request",
            "purpose": "Sends requests through the public client.",
            "boundary_not": [],
            "confidence": "high",
        }
        for candidate in candidates
    }
    with pytest.raises(ClusterError, match="boundary_not is empty"):
        assemble_clusters(candidates, named, {}, {})


def test_unnamed_cluster_survives_without_a_naming_call():
    """The deterministic-only path builds a partition with no model reply.

    The reject rule above fires on a *model answer* that omits boundaries.  If
    it also fired on an absent answer, every naming-free run would crash, which
    is how the five-repository deterministic measurement is produced.
    """
    candidates, _ = partition_by_shared_signature(
        _reachability(), nx.DiGraph(), ("a1", "a2", "shared"), {"a1": 1, "a2": 1, "shared": 1}
    )
    clusters, diagnostics = assemble_clusters(candidates, {}, {}, {})
    assert len(clusters) == len(candidates)
    assert all(record.confidence == "low" for record in clusters)
    assert all(d.startswith("unnamed_cluster:") for d in diagnostics)


# ---------------------------------------------------------------------------
# Directory fallback (F1 §2.5 first retreat)
# ---------------------------------------------------------------------------


def _residuals(*paths: str) -> tuple[UnassignedFile, ...]:
    return tuple(
        UnassignedFile(path=p, reason_code="unreferenced_public_module", reason="no entry reaches it")
        for p in paths
    )


def test_directory_fallback_groups_by_first_segment_and_marks_seed_kind():
    residuals = _residuals("db/a.py", "db/b.py", "http/c.py", "top.py")
    clusters, absorbed = apply_directory_fallback(
        residuals, {"db/a.py": 3, "db/b.py": 4, "http/c.py": 5, "top.py": 6}
    )
    by_signature = {next(iter(c.signature)): c for c in clusters}
    assert set(by_signature) == {"dir:db", "dir:http", "dir:(package_root)"}
    assert by_signature["dir:db"].member_paths == ("db/a.py", "db/b.py")
    assert by_signature["dir:db"].symbol_count == 7
    assert {c.seed_kind for c in clusters} == {"directory"}
    assert all(c.fallback_reason for c in clusters)
    assert len(absorbed) == len(residuals)
    assert {r.reason_code for r in absorbed} == {"unreferenced_public_module"}


def test_directory_fallback_never_mixes_seed_kinds_into_one_cluster():
    """A surface-seeded cluster and a directory-seeded one make different claims.

    Merging them would let a shelf ("db/") be read as a capability, which is the
    exact confusion §2.5 calls a retreat rather than a fix.
    """
    surface_clusters, residuals = partition_by_shared_signature(
        _reachability(), nx.DiGraph(), ("a1", "a2", "shared", "orphan.py"), {"a1": 1}
    )
    fallback, _ = apply_directory_fallback(residuals, {})
    assert {c.seed_kind for c in surface_clusters} == {"public_surface"}
    assert {c.seed_kind for c in fallback} == {"directory"}
    assert not {c.cluster_id for c in surface_clusters} & {c.cluster_id for c in fallback}


def test_directory_fallback_splits_one_extra_level_when_over_budget():
    residuals = _residuals(*(f"db/backends/f{i}.py" for i in range(3)), "db/models.py", "db/utils.py")
    clusters, _ = apply_directory_fallback(residuals, {}, max_files=4)
    keys = {next(iter(c.signature)) for c in clusters}
    assert keys == {"dir:db/backends", "dir:db/(directly)"}

    under_budget, _ = apply_directory_fallback(residuals, {}, max_files=9)
    assert {next(iter(c.signature)) for c in under_budget} == {"dir:db"}


def test_directory_fallback_on_empty_residuals_is_a_no_op():
    assert apply_directory_fallback((), {}) == ((), ())


def test_layer_slices_share_one_signature_group_id():
    """Layers of one function must be groupable back into that function.

    Without this the renderer has to parse ``--L<n>`` off the cluster id, and a
    reader sees four capabilities where flask has one split into four levels.
    """
    graph = nx.DiGraph([("a1", "a2")])
    candidates, _ = partition_by_shared_signature(
        _reachability(), graph, ("a1", "a2", "shared"), {"a1": 40, "a2": 40, "shared": 1}
    )
    layered = [c for c in candidates if c.layer_index is not None]
    assert len(layered) == 2, "the over-budget signature group should split by layer"
    assert len({c.signature_group_id for c in layered}) == 1
    assert all(c.cluster_id.startswith(c.signature_group_id) for c in candidates)
    assert all(c.signature_group_id for c in candidates)


# ---------------------------------------------------------------------------
# Cohesion (T3: flag members that do not fit the cluster)
# ---------------------------------------------------------------------------


def _ctx_typing_cluster():
    """The real flask shape: ``ctx.py`` imports ``typing.py`` at runtime, and
    ``typing.py`` holds 0 of the cluster's 30 symbols (module-level aliases only).
    """
    graph = nx.DiGraph([("ctx.py", "typing.py")])
    return graph, partition_by_shared_signature(
        SurfaceReachability(
            seed_paths=("app.py",),
            closures={"app.py": frozenset({"ctx.py", "typing.py"})},
            signatures={
                "ctx.py": frozenset({"app.py", "blueprints.py"}),
                "typing.py": frozenset({"app.py", "blueprints.py"}),
            },
            unreached=(),
        ),
        graph,
        ("ctx.py", "typing.py"),
        {"ctx.py": 30, "typing.py": 0},
    )[0]


def test_cohesion_flags_a_zero_symbol_member_the_edge_signal_misses():
    """Negative control for the edge signal, which passes this cluster.

    ``ctx.py -> typing.py`` is a real runtime import, so internal degree is
    non-zero for both members and ``isolated_members`` stays empty.  If
    zero-symbol members were not their own flag, the one cluster known to be
    mis-grouped would come back green.
    """
    graph, candidates = _ctx_typing_cluster()
    scores = cluster_cohesion(
        candidates, graph, {"ctx.py": {"class": 2, "function": 5, "method": 23}, "typing.py": {}}
    )
    flagged = [s for s in scores if s.low_cohesion]
    assert len(flagged) == 1
    assert flagged[0].zero_symbol_members == ("typing.py",)
    assert flagged[0].isolated_members == ()  # the edge signal alone says "fine"
    assert flagged[0].internal_edges == 1
    assert flagged[0].flag_reasons == ("zero_symbol_member",)


def test_cohesion_flags_an_isolated_member_with_symbols():
    """The other half: content present, but nothing ties it to its siblings."""
    _, candidates = _ctx_typing_cluster()
    edgeless = nx.DiGraph()
    edgeless.add_nodes_from(("ctx.py", "typing.py"))
    scores = cluster_cohesion(
        candidates,
        edgeless,
        {"ctx.py": {"function": 30}, "typing.py": {"class": 4}},
    )
    flagged = [s for s in scores if s.low_cohesion]
    assert flagged[0].isolated_members == ("ctx.py", "typing.py")
    assert flagged[0].zero_symbol_members == ()
    assert flagged[0].flag_reasons == ("isolated_member",)
    assert flagged[0].max_kind_divergence == 1.0


def test_cohesion_passes_a_connected_cluster_and_carries_seed_kind():
    graph = nx.DiGraph([("a1", "a2")])
    candidates, residuals = partition_by_shared_signature(
        _reachability(), graph, ("a1", "a2", "shared", "orphan.py"), {"a1": 1, "a2": 1, "shared": 1}
    )
    fallback, _ = apply_directory_fallback(residuals, {"orphan.py": 2})
    kinds = {p: {"function": 2} for p in ("a1", "a2", "shared", "orphan.py")}
    scores = {s.cluster_id: s for s in cluster_cohesion(candidates + fallback, graph, kinds)}
    connected = next(s for s in scores.values() if s.member_count == 2)
    assert connected.internal_edges == 1
    assert connected.edge_density == 0.5
    assert not connected.low_cohesion
    assert connected.flag_reasons == ()
    assert {s.seed_kind for s in scores.values()} == {"public_surface", "directory"}
    singletons = [s for s in scores.values() if s.member_count == 1]
    assert singletons and not any(s.low_cohesion for s in singletons)
    assert all(m.kind_divergence is None for m in singletons[0].members)


def test_single_file_distance_reports_signature_directory_and_dependency_signals():
    """Layer slices expose the evidence needed before deciding to merge them."""
    graph = nx.DiGraph([("a1", "a2")])
    candidates, _ = partition_by_shared_signature(
        _reachability(),
        graph,
        ("a1", "a2", "shared"),
        {"a1": 40, "a2": 40, "shared": 1},
    )
    singletons = tuple(c for c in candidates if len(c.member_paths) == 1)
    distances = measure_single_file_cluster_distances(singletons, graph)

    pair = next(d for d in distances if {d.left_path, d.right_path} == {"a1", "a2"})
    assert pair.same_signature_group
    assert pair.signature_jaccard == 1.0
    assert pair.directory_proximity == 1.0
    assert pair.dependency_edge_density == 0.5
    assert pair.edge_evidence == (("a1", "a2"),)


def test_single_file_distance_does_not_call_different_directories_close_by_name():
    """A same-looking stem is not a merge signal when directory context differs."""
    candidates = (
        CandidateCluster(
            cluster_id="left",
            kind="shared",
            signature=frozenset({"entry-a"}),
            member_paths=("api/client.py",),
            symbol_count=2,
            signature_group_id="left",
        ),
        CandidateCluster(
            cluster_id="right",
            kind="shared",
            signature=frozenset({"entry-b"}),
            member_paths=("transport/client.py",),
            symbol_count=2,
            signature_group_id="right",
        ),
    )
    graph = nx.DiGraph()
    graph.add_nodes_from(("api/client.py", "transport/client.py"))
    pair = measure_single_file_cluster_distances(candidates, graph)[0]
    assert not pair.same_signature_group
    assert pair.signature_jaccard == 0.0
    assert pair.directory_proximity == 0.0
    assert pair.dependency_edge_density == 0.0
