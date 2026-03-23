"""Tests for Feature Cone extraction algorithm."""

from __future__ import annotations

import networkx as nx

from src.graph.feature_cone import (
    FeatureCone,
    assign_scc_to_cone,
    extract_feature_cones,
    find_feature_roots,
)
from src.parser.codebase import CodebaseSnapshot, FileInfo


def _make_simple_dag() -> nx.DiGraph:
    """Create a simple DAG without SCC for testing.

    Structure:
        cli.py → app.py → utils.py
                 ↓
              helpers.py
    """
    G = nx.DiGraph()
    G.add_edge("cli.py", "app.py")
    G.add_edge("app.py", "utils.py")
    G.add_edge("app.py", "helpers.py")
    return G


def _make_dag_with_scc() -> nx.DiGraph:
    """Create a DAG with SCC for testing.

    Structure (after SCC condensation):
        views.py → [app.py + ctx.py] (SCC) → utils.py
        cli.py  → [app.py + ctx.py] (SCC) → helpers.py
    """
    G = nx.DiGraph()
    # SCC: app.py <-> ctx.py
    G.add_edge("app.py", "ctx.py")
    G.add_edge("ctx.py", "app.py")
    # Dependencies from SCC
    G.add_edge("app.py", "utils.py")
    G.add_edge("ctx.py", "helpers.py")
    # Dependencies to SCC
    G.add_edge("views.py", "app.py")
    G.add_edge("cli.py", "ctx.py")
    return G


def _make_minimal_snapshot() -> CodebaseSnapshot:
    """Create a minimal CodebaseSnapshot for testing."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="cli.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=(),
                import_sources=(),
            ),
        ),
        functions=(),
        classes=(),
        languages_detected=("python",),
        total_lines=10,
    )


class TestFindFeatureRoots:
    """Test finding feature roots in DAG."""

    def test_simple_dag_has_one_root(self):
        """Simple DAG with one entry point should have one root."""
        dag = _make_simple_dag()
        roots = find_feature_roots(dag)
        assert len(roots) == 1
        assert "cli.py" in roots

    def test_multiple_roots(self):
        """DAG with multiple entry points should have multiple roots."""
        G = nx.DiGraph()
        G.add_edge("entry1.py", "common.py")
        G.add_edge("entry2.py", "common.py")

        roots = find_feature_roots(G)
        assert len(roots) == 2
        assert "entry1.py" in roots
        assert "entry2.py" in roots

    def test_library_code_fallback(self):
        """Library code with no in-degree=0 nodes should fallback to min+1."""
        G = nx.DiGraph()
        # All nodes have in-degree > 0 (library code)
        G.add_edge("a.py", "b.py")
        G.add_edge("b.py", "c.py")
        G.add_edge("c.py", "a.py")  # Cycle, all in-degree >= 1

        roots = find_feature_roots(G)
        # Should fallback to min in-degree nodes
        assert len(roots) > 0
        # All nodes have in-degree 1, so all should be roots
        assert len(roots) == 3


class TestExtractFeatureCones:
    """Test feature cone extraction."""

    def test_simple_cone_extraction(self):
        """Extract cones from simple DAG."""
        dag = _make_simple_dag()
        snapshot = _make_minimal_snapshot()

        cones, infrastructure = extract_feature_cones(dag, snapshot, shared_threshold=2)

        # Should have one cone starting from cli.py
        assert len(cones) == 1
        assert "cli.py" in cones

        # Cone should contain all dependencies
        cone = cones["cli.py"]
        assert "cli.py" in cone.exclusive_files
        assert "app.py" in cone.exclusive_files
        assert "utils.py" in cone.exclusive_files
        assert "helpers.py" in cone.exclusive_files

        # No infrastructure nodes (only one cone)
        assert len(infrastructure) == 0

    def test_shared_infrastructure_detection(self):
        """Detect shared infrastructure nodes."""
        G = nx.DiGraph()
        # Two entry points sharing common dependency
        G.add_edge("entry1.py", "shared.py")
        G.add_edge("entry2.py", "shared.py")

        snapshot = _make_minimal_snapshot()

        cones, infrastructure = extract_feature_cones(G, snapshot, shared_threshold=2)

        # shared.py should be in infrastructure (shared by 2 cones)
        assert "shared.py" in infrastructure

        # Both cones should reference shared.py in shared_deps
        for cone in cones.values():
            assert "shared.py" in cone.shared_deps

    def test_cone_metadata(self):
        """Cone should have correct metadata."""
        dag = _make_simple_dag()
        snapshot = _make_minimal_snapshot()

        cones, _ = extract_feature_cones(dag, snapshot)

        cone = cones["cli.py"]
        assert cone.cone_id == "cli.py"
        assert cone.entry_point == "cli.py"
        assert len(cone.exclusive_files) > 0


class TestAssignSccToCone:
    """Test SCC assignment to cones."""

    def test_scc_assigned_to_dominant_cone(self):
        """SCC should be assigned to the cone with most members."""
        scc_members = ["app.py", "ctx.py", "globals.py"]

        # Create mock cone assignments
        # app.py and ctx.py belong to cone1, globals.py to cone2
        cone_assignments = {
            "app.py": "cone1",
            "ctx.py": "cone1",
            "globals.py": "cone2",
        }

        assigned_cone = assign_scc_to_cone(scc_members, cone_assignments)
        assert assigned_cone == "cone1"  # cone1 has 2 members, cone2 has 1

    def test_tie_goes_to_infrastructure(self):
        """SCC with equal cone membership should go to infrastructure."""
        scc_members = ["a.py", "b.py"]

        # Both cones have equal representation
        cone_assignments = {
            "a.py": "cone1",
            "b.py": "cone2",
        }

        assigned_cone = assign_scc_to_cone(scc_members, cone_assignments)
        assert assigned_cone == "infrastructure"

    def test_no_assignment_returns_infrastructure(self):
        """SCC members not in any cone should return infrastructure."""
        scc_members = ["orphan.py"]

        cone_assignments = {}  # No assignments

        assigned_cone = assign_scc_to_cone(scc_members, cone_assignments)
        assert assigned_cone == "infrastructure"


class TestIntegration:
    """Integration tests with real DAG structures."""

    def test_dag_with_scc(self):
        """Test DAG containing SCC."""
        dag = _make_dag_with_scc()
        snapshot = _make_minimal_snapshot()

        cones, infrastructure = extract_feature_cones(dag, snapshot)

        # Should have cones for views.py and cli.py (entry points)
        assert len(cones) >= 2

        # The SCC (app.py + ctx.py) should be shared
        # So it might end up in infrastructure
        # (depends on whether both entry points reach it)
