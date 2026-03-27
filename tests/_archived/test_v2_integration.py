"""V2 Integration tests: semantic quality checks for the analysis pipeline.

Verifies that the MCP pipeline produces meaningful, non-degenerate output
when run against the codebase-explorer's own source code.
"""
from __future__ import annotations

import os

import pytest

from src.graph.feature_cone import extract_feature_cones
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser


@pytest.fixture(scope="module")
def self_analysis():
    """Parse the project's own source code and run the analysis pipeline."""
    parser = CodebaseParser()
    snapshot = parser.parse(os.path.abspath("src"))
    result = build_weighted_dependency_graph(snapshot)
    graph = result.graph
    cones, infrastructure = extract_feature_cones(graph, snapshot)
    return {
        "snapshot": snapshot,
        "graph": graph,
        "result": result,
        "cones": cones,
        "infrastructure": infrastructure,
    }


class TestFeatureConeQuality:
    """Feature cones should not be degenerate."""

    def test_cones_not_all_single_file(self, self_analysis):
        """At least 50% of cones should have >1 exclusive file."""
        cones = self_analysis["cones"]
        multi = [c for c in cones.values() if len(c.exclusive_files) > 1]
        ratio = len(multi) / len(cones) if cones else 0
        assert ratio >= 0.5, (
            f"Only {len(multi)}/{len(cones)} cones have >1 exclusive file"
        )

    def test_no_init_py_as_entry_point(self, self_analysis):
        """No __init__.py should appear as cone entry_point."""
        cones = self_analysis["cones"]
        init_entries = [
            c.entry_point for c in cones.values()
            if c.entry_point.endswith("__init__.py")
        ]
        assert not init_entries, f"__init__.py found in cone entries: {init_entries}"


class TestEdgeTypeDiversity:
    """DAG edges should have multiple types (import, call, inherit)."""

    def test_at_least_two_edge_types(self, self_analysis):
        """The graph should contain at least 2 different edge types."""
        graph = self_analysis["graph"]
        types = set()
        for _, _, data in graph.edges(data=True):
            types.update(data.get("edge_types", []))
        assert len(types) >= 2, f"Only found edge types: {types}"


class TestDependencyResolution:
    """AST parser should resolve cross-file dependencies."""

    def test_some_functions_have_dependencies(self, self_analysis):
        """At least 1 FunctionInfo should have non-empty dependencies."""
        snapshot = self_analysis["snapshot"]
        with_deps = [f for f in snapshot.functions if f.dependencies]
        assert len(with_deps) >= 1, "No functions have resolved dependencies"
