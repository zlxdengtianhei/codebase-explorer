"""Tests for src/graph/dependency.py, src/graph/grouper.py, and src/graph/ordering.py."""
from __future__ import annotations

import pytest
import networkx as nx

from src.parser.codebase import (
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
    ClassInfo,
)
from src.graph.dependency import (
    DependencyEdge,
    DependencyGraphResult,
    build_dependency_graph,
    get_dependency_graph_mermaid,
    get_module_dependency_subgraph,
    get_file_dependency_subgraph,
)
from src.graph.grouper import (
    GroupingResult,
    ModuleMetrics,
    group_modules,
    identify_utility_nodes,
    UTILITY_MODULE_PREFIX,
)
from src.graph.ordering import (
    AnalysisPlan,
    topological_order,
    compute_pagerank,
    create_analysis_plan,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_file(
    filepath: str,
    *,
    language: str = "python",
    line_count: int = 50,
    function_names: tuple[str, ...] = (),
    class_names: tuple[str, ...] = (),
    import_sources: tuple[str, ...] = (),
) -> FileInfo:
    return FileInfo(
        filepath=filepath,
        language=language,
        line_count=line_count,
        function_names=function_names,
        class_names=class_names,
        import_sources=import_sources,
    )


def _make_snapshot(
    files: tuple[FileInfo, ...],
    *,
    root_path: str = "/fake/project",
    functions: tuple[FunctionInfo, ...] = (),
    classes: tuple[ClassInfo, ...] = (),
) -> CodebaseSnapshot:
    total_lines = sum(f.line_count for f in files)
    return CodebaseSnapshot(
        root_path=root_path,
        files=files,
        functions=functions,
        classes=classes,
        languages_detected=("python",),
        total_lines=total_lines,
    )


def _make_digraph(edges: list[tuple[str, str]], **edge_attrs) -> nx.DiGraph:
    """Build a simple DiGraph from edge tuples with optional attributes."""
    g = nx.DiGraph()
    for src, tgt in edges:
        g.add_edge(src, tgt, **edge_attrs)
    return g


# ---------------------------------------------------------------------------
# TestDependencyEdge & TestDependencyGraphResult
# ---------------------------------------------------------------------------


class TestDependencyEdge:
    """Tests for the DependencyEdge frozen dataclass."""

    def test_creation(self):
        edge = DependencyEdge(source="a.py", target="b.py", weight=3, edge_type="import")
        assert edge.source == "a.py"
        assert edge.target == "b.py"
        assert edge.weight == 3
        assert edge.edge_type == "import"

    def test_immutability(self):
        edge = DependencyEdge(source="a.py", target="b.py", weight=1, edge_type="import")
        with pytest.raises(AttributeError):
            edge.weight = 5  # type: ignore[misc]

    def test_equality(self):
        e1 = DependencyEdge(source="a.py", target="b.py", weight=1, edge_type="import")
        e2 = DependencyEdge(source="a.py", target="b.py", weight=1, edge_type="import")
        assert e1 == e2


class TestDependencyGraphResult:
    """Tests for the DependencyGraphResult frozen dataclass."""

    def test_immutability(self):
        result = DependencyGraphResult(
            graph=nx.DiGraph(),
            file_count=0,
            edge_count=0,
            edges=(),
            circular_deps=(),
        )
        with pytest.raises(AttributeError):
            result.file_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestBuildDependencyGraph
# ---------------------------------------------------------------------------


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph()."""

    def test_empty_snapshot(self, empty_snapshot: CodebaseSnapshot):
        result = build_dependency_graph(empty_snapshot)
        assert result.file_count == 0
        assert result.edge_count == 0
        assert result.edges == ()
        assert result.circular_deps == ()

    def test_single_file_no_deps(self):
        snap = _make_snapshot((_make_file("solo.py"),))
        result = build_dependency_graph(snap)
        assert result.file_count == 1
        assert result.edge_count == 0
        assert "solo.py" in result.graph.nodes()

    def test_basic_dependency(self, sample_snapshot: CodebaseSnapshot):
        """sample_snapshot: app.py -> utils.py, models.py -> utils.py."""
        result = build_dependency_graph(sample_snapshot)
        assert result.file_count == 3
        assert result.edge_count >= 2
        assert result.graph.has_edge("app.py", "utils.py")
        assert result.graph.has_edge("models.py", "utils.py")

    def test_self_loop_ignored(self):
        """Files importing themselves should not create self-loop edges."""
        f = _make_file("self.py", import_sources=("self.py",))
        snap = _make_snapshot((f,))
        result = build_dependency_graph(snap)
        assert result.edge_count == 0
        assert not result.graph.has_edge("self.py", "self.py")

    def test_unresolved_imports_ignored(self):
        """Imports to files not in the snapshot should not create edges."""
        f = _make_file("main.py", import_sources=("nonexistent.py",))
        snap = _make_snapshot((f,))
        result = build_dependency_graph(snap)
        assert result.edge_count == 0

    def test_weight_accumulation_from_imports(self):
        """Multiple import references from one file to another accumulate."""
        f_a = _make_file("a.py", import_sources=("b.py", "b.py"))
        f_b = _make_file("b.py")
        snap = _make_snapshot((f_a, f_b))
        result = build_dependency_graph(snap)
        edge_data = result.graph.get_edge_data("a.py", "b.py")
        assert edge_data is not None
        assert edge_data["weight"] == 2

    def test_weight_accumulation_from_functions(self):
        """Function-level dependencies also contribute to edge weight."""
        f_a = _make_file("a.py", import_sources=("b.py",))
        f_b = _make_file("b.py")
        func = FunctionInfo(
            name="do_stuff",
            filepath="a.py",
            start_line=1,
            end_line=10,
            parameters=(),
            return_type=None,
            calls=(),
            dependencies=("b.py",),
        )
        snap = _make_snapshot((f_a, f_b), functions=(func,))
        result = build_dependency_graph(snap)
        edge_data = result.graph.get_edge_data("a.py", "b.py")
        assert edge_data is not None
        # One from import_sources, one from function dependency
        assert edge_data["weight"] == 2

    def test_circular_dependencies_detected(self):
        """Mutually dependent files form an SCC detected as circular."""
        f_a = _make_file("a.py", import_sources=("b.py",))
        f_b = _make_file("b.py", import_sources=("a.py",))
        snap = _make_snapshot((f_a, f_b))
        result = build_dependency_graph(snap)
        assert len(result.circular_deps) == 1
        assert set(result.circular_deps[0]) == {"a.py", "b.py"}

    def test_no_circular_deps_in_dag(self, sample_snapshot: CodebaseSnapshot):
        result = build_dependency_graph(sample_snapshot)
        assert result.circular_deps == ()

    def test_node_attributes(self, sample_snapshot: CodebaseSnapshot):
        result = build_dependency_graph(sample_snapshot)
        node_data = result.graph.nodes["app.py"]
        assert node_data["language"] == "python"
        assert node_data["line_count"] == 100
        assert node_data["function_count"] == 2  # main, run_app
        assert node_data["class_count"] == 1  # App

    def test_edge_import_type_is_local(self, sample_snapshot: CodebaseSnapshot):
        result = build_dependency_graph(sample_snapshot)
        edge_data = result.graph.get_edge_data("app.py", "utils.py")
        assert edge_data["import_type"] == "local"

    def test_edges_tuple_matches_graph(self, sample_snapshot: CodebaseSnapshot):
        result = build_dependency_graph(sample_snapshot)
        graph_edges = set(result.graph.edges())
        edge_tuples = {(e.source, e.target) for e in result.edges}
        assert graph_edges == edge_tuples


# ---------------------------------------------------------------------------
# TestMermaidOutput
# ---------------------------------------------------------------------------


class TestMermaidOutput:
    """Tests for get_dependency_graph_mermaid()."""

    def test_empty_graph(self):
        g = nx.DiGraph()
        output = get_dependency_graph_mermaid(g)
        assert output.startswith("graph TD")
        assert "No nodes" in output

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node("main.py")
        output = get_dependency_graph_mermaid(g)
        assert "graph TD" in output
        assert "main.py" in output

    def test_basic_edge(self):
        g = _make_digraph([("src/app.py", "src/utils.py")], weight=1)
        output = get_dependency_graph_mermaid(g)
        assert "graph TD" in output
        # Should have arrows
        assert "-->" in output

    def test_weighted_edge_shows_label(self):
        g = nx.DiGraph()
        g.add_edge("a.py", "b.py", weight=3)
        output = get_dependency_graph_mermaid(g)
        assert "-->|3|" in output

    def test_weight_one_no_label(self):
        g = nx.DiGraph()
        g.add_edge("a.py", "b.py", weight=1)
        output = get_dependency_graph_mermaid(g)
        lines = output.split("\n")
        edge_lines = [l for l in lines if "-->" in l]
        # Weight-1 edges should use plain --> without |...|
        for line in edge_lines:
            assert "-->|" not in line

    def test_node_ids_are_safe(self):
        """Node identifiers must start with 'n' and be alphanumeric."""
        g = nx.DiGraph()
        g.add_node("some/path with [brackets].py")
        output = get_dependency_graph_mermaid(g)
        # Should not contain raw brackets in the output (they break Mermaid)
        # The label escaping replaces [ with ( and ] with )
        assert "[brackets]" not in output

    def test_short_label_uses_last_two_components(self):
        g = nx.DiGraph()
        g.add_node("a/b/c/d.py")
        output = get_dependency_graph_mermaid(g)
        # Short label should be "c/d.py" (last two components)
        assert "c/d.py" in output


# ---------------------------------------------------------------------------
# TestSubgraphs
# ---------------------------------------------------------------------------


class TestSubgraphs:
    """Tests for get_module_dependency_subgraph and get_file_dependency_subgraph."""

    def test_module_subgraph_basic(self):
        g = _make_digraph([("a.py", "b.py"), ("b.py", "c.py"), ("c.py", "d.py")])
        sub = get_module_dependency_subgraph(g, ["a.py", "b.py"])
        assert set(sub.nodes()) == {"a.py", "b.py"}
        assert sub.has_edge("a.py", "b.py")
        assert not sub.has_edge("b.py", "c.py")

    def test_module_subgraph_invalid_files_ignored(self):
        g = _make_digraph([("a.py", "b.py")])
        sub = get_module_dependency_subgraph(g, ["a.py", "nonexistent.py"])
        assert set(sub.nodes()) == {"a.py"}

    def test_module_subgraph_empty_files(self):
        g = _make_digraph([("a.py", "b.py")])
        sub = get_module_dependency_subgraph(g, [])
        assert sub.number_of_nodes() == 0

    def test_file_subgraph_hops_1(self):
        g = _make_digraph([("a.py", "b.py"), ("b.py", "c.py"), ("c.py", "d.py")])
        sub = get_file_dependency_subgraph(g, "b.py", hops=1)
        # b.py predecessor=a.py, successor=c.py
        assert "b.py" in sub.nodes()
        assert "a.py" in sub.nodes()
        assert "c.py" in sub.nodes()
        assert "d.py" not in sub.nodes()

    def test_file_subgraph_hops_2(self):
        g = _make_digraph([("a.py", "b.py"), ("b.py", "c.py"), ("c.py", "d.py")])
        sub = get_file_dependency_subgraph(g, "b.py", hops=2)
        assert set(sub.nodes()) == {"a.py", "b.py", "c.py", "d.py"}

    def test_file_subgraph_missing_file(self):
        g = _make_digraph([("a.py", "b.py")])
        sub = get_file_dependency_subgraph(g, "missing.py")
        assert sub.number_of_nodes() == 0

    def test_file_subgraph_isolated_node(self):
        g = nx.DiGraph()
        g.add_node("solo.py")
        sub = get_file_dependency_subgraph(g, "solo.py", hops=1)
        assert set(sub.nodes()) == {"solo.py"}


# ---------------------------------------------------------------------------
# TestIdentifyUtilityNodes
# ---------------------------------------------------------------------------


class TestIdentifyUtilityNodes:
    """Tests for identify_utility_nodes()."""

    def test_empty_graph(self):
        g = nx.DiGraph()
        assert identify_utility_nodes(g) == frozenset()

    def test_high_in_degree_detected(self):
        """A node referenced by many others exceeds the threshold."""
        g = nx.DiGraph()
        for i in range(20):
            g.add_edge(f"client_{i}.py", "core.py")
        # in-degree(core.py) = 20, total = 21, threshold 0.1 => 2.1
        utils = identify_utility_nodes(g, threshold=0.1)
        assert "core.py" in utils

    def test_utility_dir_pattern_detected(self):
        g = nx.DiGraph()
        g.add_node("src/utils/helper.py")
        g.add_node("src/main.py")
        utils = identify_utility_nodes(g, threshold=1.0)  # high threshold so in-degree won't trigger
        assert "src/utils/helper.py" in utils
        assert "src/main.py" not in utils

    @pytest.mark.parametrize(
        "dir_name",
        ["utils", "util", "common", "shared", "helpers", "lib", "tools"],
    )
    def test_all_default_dir_patterns(self, dir_name: str):
        g = nx.DiGraph()
        g.add_node(f"src/{dir_name}/something.py")
        utils = identify_utility_nodes(g, threshold=1.0)
        assert f"src/{dir_name}/something.py" in utils

    def test_custom_dir_patterns(self):
        g = nx.DiGraph()
        g.add_node("src/vendor/third.py")
        utils = identify_utility_nodes(
            g, threshold=1.0, utility_dir_patterns=("vendor",)
        )
        assert "src/vendor/third.py" in utils

    def test_single_node_not_utility_by_degree(self):
        """A single node has in-degree 0, never exceeds threshold."""
        g = nx.DiGraph()
        g.add_node("only.py")
        utils = identify_utility_nodes(g, threshold=0.1)
        assert "only.py" not in utils


# ---------------------------------------------------------------------------
# TestGroupModules
# ---------------------------------------------------------------------------


class TestGroupModules:
    """Tests for group_modules()."""

    def test_empty_graph(self):
        g = nx.DiGraph()
        result = group_modules(g)
        assert result.module_count == 0
        assert result.modules == {}
        assert result.utility_files == frozenset()
        assert result.modularity_score == 0.0

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node("only.py")
        result = group_modules(g)
        assert result.module_count >= 1
        all_files = [f for files in result.modules.values() for f in files]
        assert "only.py" in all_files

    def test_grouping_result_is_frozen(self):
        g = nx.DiGraph()
        result = group_modules(g)
        with pytest.raises(AttributeError):
            result.module_count = 99  # type: ignore[misc]

    def test_utilities_separated(self):
        """Utility nodes should be placed in the _utilities module."""
        g = nx.DiGraph()
        for i in range(20):
            g.add_edge(f"client_{i}.py", "src/utils/shared.py")
        result = group_modules(g, utility_threshold=0.01)
        assert "src/utils/shared.py" in result.utility_files
        if UTILITY_MODULE_PREFIX in result.modules:
            assert "src/utils/shared.py" in result.modules[UTILITY_MODULE_PREFIX]

    def test_all_files_assigned(self):
        """Every node in the graph should appear in exactly one module."""
        g = _make_digraph([("a.py", "b.py"), ("c.py", "d.py")])
        result = group_modules(g)
        all_assigned = {f for files in result.modules.values() for f in files}
        assert all_assigned == set(g.nodes())


# ---------------------------------------------------------------------------
# TestModuleMetrics dataclass
# ---------------------------------------------------------------------------


class TestModuleMetricsDataclass:
    """Tests for ModuleMetrics frozen dataclass."""

    def test_immutability(self):
        m = ModuleMetrics(
            name="test",
            file_count=1,
            function_count=2,
            class_count=0,
            line_count=50,
            estimated_tokens=750,
            internal_edges=0,
            external_edges=0,
            subpackage_count=0,
        )
        with pytest.raises(AttributeError):
            m.file_count = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestTopologicalOrder
# ---------------------------------------------------------------------------


class TestTopologicalOrder:
    """Tests for topological_order()."""

    def test_empty_modules(self):
        g = nx.DiGraph()
        layers = topological_order(g, {})
        assert layers == []

    def test_single_module(self):
        g = nx.DiGraph()
        g.add_node("a.py")
        layers = topological_order(g, {"mod_a": ("a.py",)})
        assert len(layers) == 1
        assert "mod_a" in layers[0]

    def test_linear_dependency_chain(self):
        """A -> B -> C produces layers starting with the top-level consumer.

        The topological_order function uses Kahn's algorithm starting from
        nodes with no incoming edges (top-level consumers), so mod_a (which
        nothing depends on) appears in the first layer, and mod_c (the leaf
        dependency) appears last.
        """
        g = _make_digraph([("a.py", "b.py"), ("b.py", "c.py")])
        modules = {
            "mod_a": ("a.py",),
            "mod_b": ("b.py",),
            "mod_c": ("c.py",),
        }
        layers = topological_order(g, modules)
        # Flatten to determine order
        flat = [mod for layer in layers for mod in layer]
        # mod_a appears before mod_b, mod_b before mod_c
        assert flat.index("mod_a") < flat.index("mod_b")
        assert flat.index("mod_b") < flat.index("mod_c")

    def test_parallel_modules(self):
        """Independent modules should appear in the same layer."""
        g = nx.DiGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        layers = topological_order(g, modules)
        # Both should be in the same layer (no inter-module edges)
        assert len(layers) == 1
        assert set(layers[0]) == {"mod_a", "mod_b"}

    def test_circular_modules_handled(self):
        """Circular module deps should still produce a valid ordering."""
        g = _make_digraph([("a.py", "b.py"), ("b.py", "a.py")])
        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        layers = topological_order(g, modules)
        flat = [mod for layer in layers for mod in layer]
        # Both modules should appear somewhere
        assert set(flat) == {"mod_a", "mod_b"}

    def test_all_modules_present_in_output(self):
        g = _make_digraph([("a.py", "b.py"), ("c.py", "b.py")])
        modules = {
            "mod_a": ("a.py",),
            "mod_b": ("b.py",),
            "mod_c": ("c.py",),
        }
        layers = topological_order(g, modules)
        flat = {mod for layer in layers for mod in layer}
        assert flat == {"mod_a", "mod_b", "mod_c"}


# ---------------------------------------------------------------------------
# TestComputePagerank
# ---------------------------------------------------------------------------


class TestComputePagerank:
    """Tests for compute_pagerank()."""

    def test_empty_graph(self):
        g = nx.DiGraph()
        scores = compute_pagerank(g)
        assert scores == {}

    def test_single_node(self):
        g = nx.DiGraph()
        g.add_node("x")
        scores = compute_pagerank(g)
        assert "x" in scores
        assert abs(scores["x"] - 1.0) < 1e-4

    def test_scores_sum_to_one(self):
        g = _make_digraph([("a", "b"), ("b", "c"), ("c", "a")])
        scores = compute_pagerank(g)
        total = sum(scores.values())
        assert abs(total - 1.0) < 1e-4

    def test_sink_node_receives_rank(self):
        """A node with no outgoing edges should still get PageRank."""
        g = _make_digraph([("a", "b"), ("a", "c")])
        scores = compute_pagerank(g)
        assert scores["b"] > 0
        assert scores["c"] > 0

    @pytest.mark.parametrize("alpha", [0.5, 0.85, 0.99])
    def test_alpha_values(self, alpha: float):
        g = _make_digraph([("a", "b"), ("b", "c")])
        scores = compute_pagerank(g, alpha=alpha)
        assert len(scores) == 3
        assert abs(sum(scores.values()) - 1.0) < 1e-3

    def test_star_topology_center_has_highest_rank(self):
        """In a star graph (many -> center), center should have highest rank."""
        g = nx.DiGraph()
        for i in range(10):
            g.add_edge(f"spoke_{i}", "hub")
        scores = compute_pagerank(g)
        assert scores["hub"] == max(scores.values())


# ---------------------------------------------------------------------------
# TestCreateAnalysisPlan
# ---------------------------------------------------------------------------


class TestCreateAnalysisPlan:
    """Tests for create_analysis_plan()."""

    def _make_metrics(self, name: str) -> ModuleMetrics:
        return ModuleMetrics(
            name=name,
            file_count=1,
            function_count=1,
            class_count=0,
            line_count=10,
            estimated_tokens=150,
            internal_edges=0,
            external_edges=0,
            subpackage_count=0,
        )

    def test_basic_plan(self):
        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        order = [["mod_b", "mod_a"]]
        metrics = {
            "mod_a": self._make_metrics("mod_a"),
            "mod_b": self._make_metrics("mod_b"),
        }
        plan = create_analysis_plan(modules, order, metrics, project_name="test")
        assert plan.project_name == "test"
        assert plan.total_modules == 2
        assert plan.analysis_layers == (("mod_b", "mod_a"),)
        assert plan.has_cycles is False
        assert plan.cycle_info is None

    def test_plan_is_frozen(self):
        plan = create_analysis_plan({}, [], {}, project_name="x")
        with pytest.raises(AttributeError):
            plan.project_name = "changed"  # type: ignore[misc]

    def test_cycle_detection_with_graph(self):
        g = _make_digraph([("a.py", "b.py"), ("b.py", "a.py")])
        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        order = [["mod_a", "mod_b"]]
        metrics = {
            "mod_a": self._make_metrics("mod_a"),
            "mod_b": self._make_metrics("mod_b"),
        }
        plan = create_analysis_plan(modules, order, metrics, graph=g)
        assert plan.has_cycles is True
        assert plan.cycle_info is not None
        assert len(plan.cycle_info) >= 1

    def test_no_cycles_without_graph(self):
        """Without a graph argument, cycle detection is skipped."""
        modules = {"mod_a": ("a.py",)}
        order = [["mod_a"]]
        metrics = {"mod_a": self._make_metrics("mod_a")}
        plan = create_analysis_plan(modules, order, metrics)
        assert plan.has_cycles is False
        assert plan.cycle_info is None

    def test_empty_plan(self):
        plan = create_analysis_plan({}, [], {})
        assert plan.total_modules == 0
        assert plan.analysis_layers == ()


# ---------------------------------------------------------------------------
# TestAnalysisPlanDataclass
# ---------------------------------------------------------------------------


class TestAnalysisPlanDataclass:
    """Tests for the AnalysisPlan frozen dataclass."""

    def test_immutability(self):
        plan = AnalysisPlan(
            project_name="p",
            total_modules=0,
            analysis_layers=(),
            module_metrics={},
            has_cycles=False,
            cycle_info=None,
        )
        with pytest.raises(AttributeError):
            plan.total_modules = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TestEdgeCases (cross-cutting)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Cross-cutting edge case tests."""

    def test_large_circular_group(self):
        """A ring of N files should form one circular dependency group."""
        n = 6
        files = [_make_file(f"f{i}.py", import_sources=(f"f{(i+1) % n}.py",)) for i in range(n)]
        snap = _make_snapshot(tuple(files))
        result = build_dependency_graph(snap)
        assert len(result.circular_deps) == 1
        assert set(result.circular_deps[0]) == {f"f{i}.py" for i in range(n)}

    def test_diamond_dependency(self):
        """Diamond pattern: A -> B, A -> C, B -> D, C -> D."""
        files = (
            _make_file("a.py", import_sources=("b.py", "c.py")),
            _make_file("b.py", import_sources=("d.py",)),
            _make_file("c.py", import_sources=("d.py",)),
            _make_file("d.py"),
        )
        snap = _make_snapshot(files)
        result = build_dependency_graph(snap)
        assert result.edge_count == 4
        assert result.circular_deps == ()

    def test_mermaid_roundtrip_node_count(self):
        """Mermaid output should reference every node in the graph."""
        g = _make_digraph([("a.py", "b.py"), ("b.py", "c.py")])
        output = get_dependency_graph_mermaid(g)
        for node in ("a.py", "b.py", "c.py"):
            assert node in output

    def test_topological_order_diamond(self):
        """Diamond: mod_a depends on mod_b and mod_c, both depend on mod_d.

        Kahn's algorithm starts from nodes with no incoming edges (top-level
        consumers), so mod_a (nothing depends on it) is first, mod_d last.
        """
        g = _make_digraph([
            ("a.py", "b.py"),
            ("a.py", "c.py"),
            ("b.py", "d.py"),
            ("c.py", "d.py"),
        ])
        modules = {
            "mod_a": ("a.py",),
            "mod_b": ("b.py",),
            "mod_c": ("c.py",),
            "mod_d": ("d.py",),
        }
        layers = topological_order(g, modules)
        flat = [mod for layer in layers for mod in layer]
        assert flat.index("mod_a") < flat.index("mod_b")
        assert flat.index("mod_a") < flat.index("mod_c")
        assert flat.index("mod_b") < flat.index("mod_d")
        assert flat.index("mod_c") < flat.index("mod_d")

    def test_grouping_result_type(self):
        result = GroupingResult(
            modules={"m": ("a.py",)},
            utility_files=frozenset({"u.py"}),
            modularity_score=0.5,
            module_count=1,
        )
        assert isinstance(result.utility_files, frozenset)
        assert isinstance(result.modules, dict)

    @pytest.mark.parametrize(
        "node_count",
        [2, 5, 10, 50],
    )
    def test_pagerank_sums_to_one_various_sizes(self, node_count: int):
        g = nx.DiGraph()
        for i in range(node_count):
            g.add_edge(f"n{i}", f"n{(i + 1) % node_count}")
        scores = compute_pagerank(g)
        assert abs(sum(scores.values()) - 1.0) < 1e-3
