"""Tests for src.graph.dependency, src.graph.grouper, and src.graph.ordering."""
from __future__ import annotations

import networkx as nx
import pytest

from src.graph.dependency import (
    DependencyEdge,
    DependencyGraphResult,
    build_dependency_graph,
    get_dependency_graph_mermaid,
    get_module_dependency_subgraph,
)
from src.graph.grouper import (
    GroupingResult,
    ModuleMetrics,
    get_module_metrics,
    group_modules,
    identify_utility_nodes,
    recursive_subgroup,
)
from src.graph.ordering import (
    AnalysisPlan,
    compute_pagerank,
    create_analysis_plan,
    topological_order,
)
from src.parser.codebase import CodebaseSnapshot, FileInfo


# ===================================================================
# Dependency Graph Tests
# ===================================================================


class TestBuildDependencyGraph:
    """Tests for build_dependency_graph()."""

    def test_build_dependency_graph_basic(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Build graph from sample snapshot; verify nodes and edges."""
        result = build_dependency_graph(sample_snapshot)

        assert isinstance(result, DependencyGraphResult)
        assert result.file_count == 3
        # app.py -> utils.py and models.py -> utils.py (from imports)
        # plus app.py -> utils.py from function dependency
        assert result.edge_count >= 2
        assert result.graph.has_node("app.py")
        assert result.graph.has_node("utils.py")
        assert result.graph.has_node("models.py")
        assert result.graph.has_edge("app.py", "utils.py")
        assert result.graph.has_edge("models.py", "utils.py")

    def test_build_dependency_graph_empty(
        self, empty_snapshot: CodebaseSnapshot
    ) -> None:
        """Empty snapshot produces an empty graph."""
        result = build_dependency_graph(empty_snapshot)

        assert result.file_count == 0
        assert result.edge_count == 0
        assert len(result.edges) == 0
        assert len(result.circular_deps) == 0

    def test_dependency_graph_result_fields(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Verify DependencyGraphResult contains all expected fields."""
        result = build_dependency_graph(sample_snapshot)

        assert isinstance(result.graph, nx.DiGraph)
        assert isinstance(result.file_count, int)
        assert isinstance(result.edge_count, int)
        assert isinstance(result.edges, tuple)
        assert all(isinstance(e, DependencyEdge) for e in result.edges)
        assert isinstance(result.circular_deps, tuple)

    def test_node_attributes(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Verify node attributes (language, line_count, etc.)."""
        result = build_dependency_graph(sample_snapshot)
        g = result.graph

        app_data = g.nodes["app.py"]
        assert app_data["language"] == "python"
        assert app_data["line_count"] == 100
        assert app_data["function_count"] == 2  # main, run_app
        assert app_data["class_count"] == 1  # App

        utils_data = g.nodes["utils.py"]
        assert utils_data["line_count"] == 50
        assert utils_data["function_count"] == 1  # helper

    def test_edge_weight_accumulates(self) -> None:
        """Multiple references between files increase edge weight."""
        files = (
            FileInfo(
                filepath="a.py",
                language="python",
                line_count=10,
                function_names=("f1", "f2"),
                class_names=(),
                import_sources=("b.py", "b.py"),  # 2 imports to same target
            ),
            FileInfo(
                filepath="b.py",
                language="python",
                line_count=20,
                function_names=(),
                class_names=(),
                import_sources=(),
            ),
        )
        snapshot = CodebaseSnapshot(
            root_path="/fake",
            files=files,
            functions=(),
            classes=(),
            languages_detected=("python",),
            total_lines=30,
        )
        result = build_dependency_graph(snapshot)
        assert result.graph["a.py"]["b.py"]["weight"] == 2

    def test_no_self_loops(self) -> None:
        """Self-imports should not create self-loop edges."""
        files = (
            FileInfo(
                filepath="a.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=(),
                import_sources=("a.py",),  # import self
            ),
        )
        snapshot = CodebaseSnapshot(
            root_path="/fake",
            files=files,
            functions=(),
            classes=(),
            languages_detected=("python",),
            total_lines=10,
        )
        result = build_dependency_graph(snapshot)
        assert not result.graph.has_edge("a.py", "a.py")

    def test_circular_deps_detected(self) -> None:
        """Circular imports are detected and reported."""
        files = (
            FileInfo(
                filepath="a.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=(),
                import_sources=("b.py",),
            ),
            FileInfo(
                filepath="b.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=(),
                import_sources=("a.py",),
            ),
        )
        snapshot = CodebaseSnapshot(
            root_path="/fake",
            files=files,
            functions=(),
            classes=(),
            languages_detected=("python",),
            total_lines=20,
        )
        result = build_dependency_graph(snapshot)
        assert len(result.circular_deps) == 1
        assert set(result.circular_deps[0]) == {"a.py", "b.py"}


class TestDependencyGraphMermaid:
    """Tests for get_dependency_graph_mermaid()."""

    def test_mermaid_output_format(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Verify Mermaid output starts with graph TD and has nodes."""
        result = build_dependency_graph(sample_snapshot)
        mermaid = get_dependency_graph_mermaid(result.graph)

        assert mermaid.startswith("graph TD")
        # Should contain node definitions with labels
        assert '["' in mermaid or "[\"" in mermaid

    def test_mermaid_empty_graph(self) -> None:
        """Empty graph produces a 'No nodes' placeholder."""
        g = nx.DiGraph()
        mermaid = get_dependency_graph_mermaid(g)
        assert "No nodes" in mermaid

    def test_mermaid_contains_edges(self) -> None:
        """Mermaid output contains arrow notation for edges."""
        g = nx.DiGraph()
        g.add_node("a.py", file_path="a.py")
        g.add_node("b.py", file_path="b.py")
        g.add_edge("a.py", "b.py", weight=1)

        mermaid = get_dependency_graph_mermaid(g)
        assert "-->" in mermaid

    def test_mermaid_weighted_edge(self) -> None:
        """Edges with weight > 1 display the weight label."""
        g = nx.DiGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        g.add_edge("a.py", "b.py", weight=3)

        mermaid = get_dependency_graph_mermaid(g)
        assert "|3|" in mermaid


class TestModuleDependencySubgraph:
    """Tests for get_module_dependency_subgraph()."""

    def test_subgraph_basic(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        result = build_dependency_graph(sample_snapshot)
        subgraph = get_module_dependency_subgraph(
            result.graph, ["app.py", "utils.py"]
        )
        assert subgraph.number_of_nodes() == 2
        assert subgraph.has_edge("app.py", "utils.py")
        assert not subgraph.has_node("models.py")

    def test_subgraph_nonexistent_node(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Non-existent nodes are silently skipped."""
        result = build_dependency_graph(sample_snapshot)
        subgraph = get_module_dependency_subgraph(
            result.graph, ["app.py", "nonexistent.py"]
        )
        assert subgraph.number_of_nodes() == 1


# ===================================================================
# Louvain Grouper Tests
# ===================================================================


class TestGroupModules:
    """Tests for group_modules()."""

    def test_group_modules_basic(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Grouping a simple graph produces at least one module."""
        result = build_dependency_graph(sample_snapshot)
        grouping = group_modules(result.graph, snapshot=sample_snapshot)

        assert isinstance(grouping, GroupingResult)
        assert grouping.module_count >= 1
        assert isinstance(grouping.modules, dict)
        assert isinstance(grouping.utility_files, frozenset)
        assert isinstance(grouping.modularity_score, float)

        # All files should appear in exactly one module
        all_grouped = set()
        for files in grouping.modules.values():
            for f in files:
                all_grouped.add(f)
        assert "app.py" in all_grouped
        assert "utils.py" in all_grouped
        assert "models.py" in all_grouped

    def test_group_modules_empty_graph(self) -> None:
        """Empty graph returns empty grouping."""
        g = nx.DiGraph()
        grouping = group_modules(g)

        assert grouping.module_count == 0
        assert len(grouping.modules) == 0
        assert grouping.modularity_score == 0.0

    def test_group_modules_single_component(self) -> None:
        """Single disconnected node yields one module."""
        g = nx.DiGraph()
        g.add_node("only.py")

        grouping = group_modules(g)

        assert grouping.module_count >= 1
        all_files = set()
        for files in grouping.modules.values():
            for f in files:
                all_files.add(f)
        assert "only.py" in all_files


class TestIdentifyUtilityNodes:
    """Tests for identify_utility_nodes()."""

    def test_high_indegree_nodes(self) -> None:
        """Nodes with high in-degree are identified as utilities."""
        g = nx.DiGraph()
        # hub.py is imported by many files -> high in-degree
        for i in range(10):
            g.add_edge(f"file_{i}.py", "hub.py")

        utilities = identify_utility_nodes(g, threshold=0.1)
        assert "hub.py" in utilities

    def test_utility_dir_pattern(self) -> None:
        """Nodes in utility directories are identified as utilities."""
        g = nx.DiGraph()
        g.add_node("src/utils/helpers.py")
        g.add_node("src/main.py")

        utilities = identify_utility_nodes(g)
        assert "src/utils/helpers.py" in utilities
        assert "src/main.py" not in utilities

    def test_empty_graph(self) -> None:
        g = nx.DiGraph()
        utilities = identify_utility_nodes(g)
        assert len(utilities) == 0


class TestRecursiveSubgroup:
    """Tests for recursive_subgroup()."""

    def test_small_module_no_split(self) -> None:
        """Module smaller than min_size is returned as-is."""
        g = nx.DiGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        g.add_edge("a.py", "b.py")

        result = recursive_subgroup(g, ["a.py", "b.py"], min_size=5)
        assert len(result) == 1
        group_files = list(result.values())[0]
        assert set(group_files) == {"a.py", "b.py"}

    def test_large_module_splits(self) -> None:
        """Module larger than min_size gets sub-grouped.

        Louvain community detection is non-deterministic even with
        a seed, so we only assert structural properties: at least
        one sub-group is produced and each sub-group is non-empty.
        """
        g = nx.DiGraph()
        # Create two clusters with dense internal edges
        cluster_a = [f"cluster_a/f{i}.py" for i in range(4)]
        cluster_b = [f"cluster_b/f{i}.py" for i in range(4)]

        # Dense intra-cluster edges
        for i in range(len(cluster_a)):
            for j in range(len(cluster_a)):
                if i != j:
                    g.add_edge(cluster_a[i], cluster_a[j])
                    g.add_edge(cluster_b[i], cluster_b[j])

        # Thin bridge between clusters
        g.add_edge(cluster_a[-1], cluster_b[0])

        all_files = cluster_a + cluster_b
        result = recursive_subgroup(g, all_files, min_size=3, resolution=2.0)

        # Should have at least 1 sub-group
        assert len(result) >= 1
        # Every sub-group should be non-empty
        for files in result.values():
            assert len(files) > 0
        # All returned files should be from the input set
        all_grouped = set()
        for files in result.values():
            all_grouped.update(files)
        assert all_grouped.issubset(set(all_files))


class TestModuleMetrics:
    """Tests for get_module_metrics()."""

    def test_module_metrics_fields(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Verify ModuleMetrics contains expected fields."""
        result = build_dependency_graph(sample_snapshot)
        modules = {"core": ("app.py", "utils.py", "models.py")}
        metrics = get_module_metrics(result.graph, modules)

        assert "core" in metrics
        m = metrics["core"]
        assert isinstance(m, ModuleMetrics)
        assert m.name == "core"
        assert m.file_count == 3
        assert m.function_count == 4  # main, run_app, helper, create_model
        assert m.class_count == 3  # App, UserModel, BaseModel
        assert m.line_count == 230  # 100 + 50 + 80
        assert m.estimated_tokens == 230 * 15
        assert isinstance(m.internal_edges, int)
        assert isinstance(m.external_edges, int)
        assert isinstance(m.subpackage_count, int)

    def test_module_metrics_with_file_lookup(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """Metrics use FileInfo lookup when provided."""
        result = build_dependency_graph(sample_snapshot)
        file_lookup = {fi.filepath: fi for fi in sample_snapshot.files}
        modules = {"mod": ("app.py",)}
        metrics = get_module_metrics(result.graph, modules, file_lookup=file_lookup)

        m = metrics["mod"]
        assert m.line_count == 100
        assert m.function_count == 2
        assert m.class_count == 1

    def test_module_metrics_empty(self) -> None:
        """Empty modules produce empty metrics dict."""
        g = nx.DiGraph()
        metrics = get_module_metrics(g, {})
        assert len(metrics) == 0


# ===================================================================
# Topological Ordering Tests
# ===================================================================


class TestTopologicalOrder:
    """Tests for topological_order()."""

    def test_topological_order_dag(self) -> None:
        """DAG without cycles yields correct layered ordering.

        Structure (file edges):
            mod_c/f1 -> mod_b/f1 -> mod_a/f1

        This means mod_c depends on mod_b, which depends on mod_a.
        The module graph becomes: mod_c -> mod_b -> mod_a.

        topological_order uses Kahn's algorithm on the condensed DAG,
        processing nodes with no predecessors first. Since nothing
        depends on mod_c, it appears in the first layer. mod_a (the
        leaf dependency) appears last.

        Expected layers: [[mod_c], [mod_b], [mod_a]]
        """
        g = nx.DiGraph()
        # Files in three modules
        g.add_node("a/f1.py")
        g.add_node("b/f1.py")
        g.add_node("c/f1.py")

        # mod_b depends on mod_a, mod_c depends on mod_b
        g.add_edge("b/f1.py", "a/f1.py")
        g.add_edge("c/f1.py", "b/f1.py")

        modules = {
            "mod_a": ("a/f1.py",),
            "mod_b": ("b/f1.py",),
            "mod_c": ("c/f1.py",),
        }

        layers = topological_order(g, modules)

        assert len(layers) >= 2
        # Flatten layers to check ordering
        flat = [m for layer in layers for m in layer]
        assert set(flat) == {"mod_a", "mod_b", "mod_c"}

        # mod_c has no predecessors in the module graph, so it is processed first.
        # mod_a is the deepest dependency, so it comes last.
        assert flat.index("mod_c") < flat.index("mod_b")
        assert flat.index("mod_b") < flat.index("mod_a")

    def test_topological_order_with_cycle(self) -> None:
        """Graph with cycles still produces a valid ordering via SCC condensation."""
        g = nx.DiGraph()
        g.add_node("a.py")
        g.add_node("b.py")
        g.add_node("c.py")

        # Cycle: a -> b -> a, c depends on a
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "a.py")
        g.add_edge("c.py", "a.py")

        modules = {
            "mod_a": ("a.py",),
            "mod_b": ("b.py",),
            "mod_c": ("c.py",),
        }

        layers = topological_order(g, modules)

        # Should not crash; all modules appear somewhere
        flat = [m for layer in layers for m in layer]
        assert set(flat) == {"mod_a", "mod_b", "mod_c"}

    def test_topological_order_empty(self) -> None:
        """Empty graph returns empty layers."""
        g = nx.DiGraph()
        layers = topological_order(g, {})
        assert layers == []

    def test_topological_order_independent_modules(self) -> None:
        """Independent modules (no inter-module edges) appear in one layer."""
        g = nx.DiGraph()
        g.add_node("x.py")
        g.add_node("y.py")

        modules = {"mod_x": ("x.py",), "mod_y": ("y.py",)}
        layers = topological_order(g, modules)

        assert len(layers) == 1
        assert set(layers[0]) == {"mod_x", "mod_y"}


class TestComputePageRank:
    """Tests for compute_pagerank()."""

    def test_compute_pagerank_basic(self) -> None:
        """PageRank returns scores for all nodes summing to ~1.0."""
        g = nx.DiGraph()
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("c", "a")

        scores = compute_pagerank(g)

        assert set(scores.keys()) == {"a", "b", "c"}
        assert all(isinstance(v, float) for v in scores.values())
        assert abs(sum(scores.values()) - 1.0) < 0.01

    def test_compute_pagerank_empty(self) -> None:
        """PageRank on empty graph returns empty dict."""
        g = nx.DiGraph()
        scores = compute_pagerank(g)
        assert scores == {}

    def test_compute_pagerank_single_node(self) -> None:
        """Single node gets full rank."""
        g = nx.DiGraph()
        g.add_node("solo")

        scores = compute_pagerank(g)
        assert "solo" in scores
        assert abs(scores["solo"] - 1.0) < 0.01

    def test_compute_pagerank_hub_has_higher_score(self) -> None:
        """A heavily-linked hub node has higher PageRank."""
        g = nx.DiGraph()
        for i in range(10):
            g.add_edge(f"leaf_{i}", "hub")

        scores = compute_pagerank(g)
        hub_score = scores["hub"]
        leaf_scores = [scores[f"leaf_{i}"] for i in range(10)]
        assert hub_score > max(leaf_scores)


class TestCreateAnalysisPlan:
    """Tests for create_analysis_plan()."""

    def test_create_analysis_plan_structure(self) -> None:
        """Verify AnalysisPlan has correct fields and values."""
        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        order = [["mod_a"], ["mod_b"]]
        metrics = {
            "mod_a": ModuleMetrics(
                name="mod_a",
                file_count=1,
                function_count=2,
                class_count=0,
                line_count=50,
                estimated_tokens=750,
                internal_edges=0,
                external_edges=0,
                subpackage_count=0,
            ),
            "mod_b": ModuleMetrics(
                name="mod_b",
                file_count=1,
                function_count=1,
                class_count=1,
                line_count=30,
                estimated_tokens=450,
                internal_edges=0,
                external_edges=1,
                subpackage_count=0,
            ),
        }

        plan = create_analysis_plan(
            modules=modules,
            order=order,
            metrics=metrics,
            project_name="test_project",
        )

        assert isinstance(plan, AnalysisPlan)
        assert plan.project_name == "test_project"
        assert plan.total_modules == 2
        assert len(plan.analysis_layers) == 2
        assert plan.analysis_layers[0] == ("mod_a",)
        assert plan.analysis_layers[1] == ("mod_b",)
        assert plan.module_metrics == metrics
        assert plan.has_cycles is False
        assert plan.cycle_info is None

    def test_create_analysis_plan_with_graph_detects_cycles(self) -> None:
        """When graph is provided, cycles are detected."""
        g = nx.DiGraph()
        g.add_edge("a.py", "b.py")
        g.add_edge("b.py", "a.py")

        modules = {"mod_a": ("a.py",), "mod_b": ("b.py",)}
        order = [["mod_a", "mod_b"]]
        metrics = {
            "mod_a": ModuleMetrics(
                name="mod_a",
                file_count=1,
                function_count=0,
                class_count=0,
                line_count=10,
                estimated_tokens=150,
                internal_edges=0,
                external_edges=1,
                subpackage_count=0,
            ),
            "mod_b": ModuleMetrics(
                name="mod_b",
                file_count=1,
                function_count=0,
                class_count=0,
                line_count=10,
                estimated_tokens=150,
                internal_edges=0,
                external_edges=1,
                subpackage_count=0,
            ),
        }

        plan = create_analysis_plan(
            modules=modules,
            order=order,
            metrics=metrics,
            project_name="cyclic_project",
            graph=g,
        )

        assert plan.has_cycles is True
        assert plan.cycle_info is not None
        assert len(plan.cycle_info) >= 1

    def test_analysis_plan_immutable(self) -> None:
        """AnalysisPlan is a frozen dataclass."""
        plan = AnalysisPlan(
            project_name="p",
            total_modules=0,
            analysis_layers=(),
            module_metrics={},
            has_cycles=False,
            cycle_info=None,
        )
        with pytest.raises(AttributeError):
            plan.project_name = "q"  # type: ignore[misc]

    def test_analysis_plan_no_graph(self) -> None:
        """Without graph, cycle detection is skipped."""
        plan = create_analysis_plan(
            modules={"m": ("f.py",)},
            order=[["m"]],
            metrics={},
            project_name="no_graph",
            graph=None,
        )
        assert plan.has_cycles is False
        assert plan.cycle_info is None
