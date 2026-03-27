"""Tests for weighted dependency graph builder."""

from __future__ import annotations

from src.graph.weighted_graph import (
    WeightedGraphResult,
    build_weighted_dependency_graph,
)
from src.parser.codebase import (
    ClassInfo,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
)


def _make_simple_import_snapshot() -> CodebaseSnapshot:
    """Create snapshot with simple import dependencies."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="main.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=(),
                import_sources=("utils.py",),
            ),
            FileInfo(
                filepath="utils.py",
                language="python",
                line_count=5,
                function_names=(),
                class_names=(),
                import_sources=(),
            ),
        ),
        functions=(),
        classes=(),
        languages_detected=("python",),
        total_lines=15,
    )


def _make_call_dependency_snapshot() -> CodebaseSnapshot:
    """Create snapshot with function call dependencies."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="main.py",
                language="python",
                line_count=10,
                function_names=("main",),
                class_names=(),
                import_sources=("utils.py",),
            ),
            FileInfo(
                filepath="utils.py",
                language="python",
                line_count=5,
                function_names=("helper",),
                class_names=(),
                import_sources=(),
            ),
        ),
        functions=(
            FunctionInfo(
                name="main",
                filepath="main.py",
                start_line=1,
                end_line=5,
                parameters=(),
                return_type=None,
                calls=("helper",),
                dependencies=("utils.py",),
            ),
            FunctionInfo(
                name="helper",
                filepath="utils.py",
                start_line=1,
                end_line=5,
                parameters=(),
                return_type=None,
                calls=(),
                dependencies=(),
            ),
        ),
        classes=(),
        languages_detected=("python",),
        total_lines=15,
    )


def _make_inheritance_snapshot() -> CodebaseSnapshot:
    """Create snapshot with class inheritance."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="child.py",
                language="python",
                line_count=10,
                function_names=(),
                class_names=("Child",),
                import_sources=("parent.py",),
            ),
            FileInfo(
                filepath="parent.py",
                language="python",
                line_count=5,
                function_names=(),
                class_names=("Parent",),
                import_sources=(),
            ),
        ),
        functions=(),
        classes=(
            ClassInfo(
                name="Child",
                filepath="child.py",
                start_line=1,
                end_line=10,
                methods=(),
                base_classes=("Parent",),
                subclasses=(),
            ),
            ClassInfo(
                name="Parent",
                filepath="parent.py",
                start_line=1,
                end_line=5,
                methods=(),
                base_classes=(),
                subclasses=("Child",),
            ),
        ),
        languages_detected=("python",),
        total_lines=15,
    )


def _make_multiple_relations_snapshot() -> CodebaseSnapshot:
    """Create snapshot with multiple relation types between same files."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="app.py",
                language="python",
                line_count=20,
                function_names=("run",),
                class_names=("App",),
                import_sources=("core.py",),
            ),
            FileInfo(
                filepath="core.py",
                language="python",
                line_count=15,
                function_names=("init",),
                class_names=("BaseApp",),
                import_sources=(),
            ),
        ),
        functions=(
            FunctionInfo(
                name="run",
                filepath="app.py",
                start_line=1,
                end_line=10,
                parameters=(),
                return_type=None,
                calls=("init",),
                dependencies=("core.py",),
            ),
            FunctionInfo(
                name="init",
                filepath="core.py",
                start_line=1,
                end_line=5,
                parameters=(),
                return_type=None,
                calls=(),
                dependencies=(),
            ),
        ),
        classes=(
            ClassInfo(
                name="App",
                filepath="app.py",
                start_line=12,
                end_line=20,
                methods=(),
                base_classes=("BaseApp",),
                subclasses=(),
            ),
            ClassInfo(
                name="BaseApp",
                filepath="core.py",
                start_line=7,
                end_line=15,
                methods=(),
                base_classes=(),
                subclasses=("App",),
            ),
        ),
        languages_detected=("python",),
        total_lines=35,
    )


def _make_duplicate_names_snapshot() -> CodebaseSnapshot:
    """Create snapshot with duplicate function/class names across files."""
    return CodebaseSnapshot(
        root_path="/test",
        files=(
            FileInfo(
                filepath="a.py",
                language="python",
                line_count=5,
                function_names=("helper",),
                class_names=(),
                import_sources=(),
            ),
            FileInfo(
                filepath="b.py",
                language="python",
                line_count=5,
                function_names=("helper",),  # Duplicate name
                class_names=(),
                import_sources=(),
            ),
            FileInfo(
                filepath="main.py",
                language="python",
                line_count=10,
                function_names=("main",),
                class_names=(),
                import_sources=(),
            ),
        ),
        functions=(
            FunctionInfo(
                name="helper",
                filepath="a.py",
                start_line=1,
                end_line=5,
                parameters=(),
                return_type=None,
                calls=(),
                dependencies=(),
            ),
            FunctionInfo(
                name="helper",
                filepath="b.py",
                start_line=1,
                end_line=5,
                parameters=(),
                return_type=None,
                calls=(),
                dependencies=(),
            ),
            FunctionInfo(
                name="main",
                filepath="main.py",
                start_line=1,
                end_line=10,
                parameters=(),
                return_type=None,
                calls=("helper",),  # Ambiguous call
                dependencies=(),
            ),
        ),
        classes=(),
        languages_detected=("python",),
        total_lines=20,
    )


class TestBuildWeightedDependencyGraph:
    """Test weighted dependency graph construction."""

    def test_import_edge_weight(self):
        """Import edges should have weight=1."""
        snapshot = _make_simple_import_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        assert result.graph.has_edge("main.py", "utils.py")
        edge_data = result.graph.get_edge_data("main.py", "utils.py")
        assert edge_data["weight"] == 1
        assert "import" in edge_data["edge_types"]

    def test_call_edge_weight(self):
        """Call edges should have weight=2."""
        snapshot = _make_call_dependency_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        # Should have both import (weight=1) and call (weight=2)
        assert result.graph.has_edge("main.py", "utils.py")
        edge_data = result.graph.get_edge_data("main.py", "utils.py")
        assert edge_data["weight"] == 3  # 1 (import) + 2 (call)
        assert "import" in edge_data["edge_types"]
        assert "call" in edge_data["edge_types"]

    def test_inheritance_edge_weight(self):
        """Inheritance edges should have weight=3."""
        snapshot = _make_inheritance_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        # Should have both import (weight=1) and inherit (weight=3)
        assert result.graph.has_edge("child.py", "parent.py")
        edge_data = result.graph.get_edge_data("child.py", "parent.py")
        assert edge_data["weight"] == 4  # 1 (import) + 3 (inherit)
        assert "import" in edge_data["edge_types"]
        assert "inherit" in edge_data["edge_types"]

    def test_multiple_relations_cumulative_weight(self):
        """Multiple relations should accumulate weights."""
        snapshot = _make_multiple_relations_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        # app.py -> core.py: import (1) + call (2) + inherit (3) = 6
        assert result.graph.has_edge("app.py", "core.py")
        edge_data = result.graph.get_edge_data("app.py", "core.py")
        assert edge_data["weight"] == 6
        assert "import" in edge_data["edge_types"]
        assert "call" in edge_data["edge_types"]
        assert "inherit" in edge_data["edge_types"]

    def test_duplicate_function_names_skipped(self):
        """Duplicate function names should not create call edges."""
        snapshot = _make_duplicate_names_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        # main.py calls helper, but helper exists in both a.py and b.py
        # So no call edge should be created (conservative strategy)
        assert not result.graph.has_edge("main.py", "a.py")
        assert not result.graph.has_edge("main.py", "b.py")

    def test_result_metadata(self):
        """Result should contain correct metadata."""
        snapshot = _make_simple_import_snapshot()
        result = build_weighted_dependency_graph(snapshot)

        assert result.node_count == 2
        assert result.edge_count == 1
        assert result.total_weight == 1
        assert "import_edges=1" in result.summary

    def test_empty_snapshot(self):
        """Empty snapshot should produce empty graph."""
        snapshot = CodebaseSnapshot(
            root_path="/test",
            files=(),
            functions=(),
            classes=(),
            languages_detected=(),
            total_lines=0,
        )
        result = build_weighted_dependency_graph(snapshot)

        assert result.node_count == 0
        assert result.edge_count == 0
        assert result.total_weight == 0

    def test_self_loops_excluded(self):
        """Self-loops should be excluded."""
    def test_self_loops_excluded(self):
        """Self-loops should be excluded."""
        snapshot = CodebaseSnapshot(
            root_path="/test",
            files=(
                FileInfo(
                    filepath="self.py",
                    language="python",
                    line_count=10,
                    function_names=(),
                    class_names=(),
                    import_sources=("self.py",),  # Self-import
                ),
            ),
            functions=(),
            classes=(),
            languages_detected=("python",),
            total_lines=10,
        )
        result = build_weighted_dependency_graph(snapshot)

        # Should have node but no self-loop
        assert result.graph.has_node("self.py")
        assert not result.graph.has_edge("self.py", "self.py")
