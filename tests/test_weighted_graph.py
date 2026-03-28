"""Tests for src/graph/weighted_graph.py — weighted multi-relation dependency graph.

Covers:
- build_weighted_dependency_graph
- Edge weight accumulation (import=1, call=2, inherit=3)
- Multiple relation types on the same edge
- Empty / single-node / disconnected graphs
- WeightedGraphResult metadata (node_count, edge_count, total_weight, summary)
"""

from __future__ import annotations

import pytest

from src.graph.weighted_graph import (
    EDGE_WEIGHTS,
    WeightedGraphResult,
    build_weighted_dependency_graph,
)
from src.parser.codebase import (
    ClassInfo,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file(path: str, imports: tuple[str, ...] = ()) -> FileInfo:
    """Shorthand FileInfo factory."""
    return FileInfo(
        filepath=path,
        language="python",
        line_count=50,
        function_names=(),
        class_names=(),
        import_sources=imports,
    )


def _func(
    name: str,
    filepath: str,
    dependencies: tuple[str, ...] = (),
) -> FunctionInfo:
    """Shorthand FunctionInfo factory."""
    return FunctionInfo(
        name=name,
        filepath=filepath,
        start_line=1,
        end_line=10,
        parameters=(),
        return_type=None,
        calls=(),
        dependencies=dependencies,
    )


def _cls(
    name: str,
    filepath: str,
    base_classes: tuple[str, ...] = (),
) -> ClassInfo:
    """Shorthand ClassInfo factory."""
    return ClassInfo(
        name=name,
        filepath=filepath,
        start_line=1,
        end_line=20,
        methods=(),
        base_classes=base_classes,
        subclasses=(),
    )


def _snapshot(
    files: tuple[FileInfo, ...] = (),
    functions: tuple[FunctionInfo, ...] = (),
    classes: tuple[ClassInfo, ...] = (),
) -> CodebaseSnapshot:
    """Build a minimal CodebaseSnapshot."""
    total_lines = sum(f.line_count for f in files)
    return CodebaseSnapshot(
        root_path="/fake",
        files=files,
        functions=functions,
        classes=classes,
        languages_detected=("python",),
        total_lines=total_lines,
    )


# ---------------------------------------------------------------------------
# Empty and trivial graphs
# ---------------------------------------------------------------------------


class TestEmptyAndTrivialGraphs:
    """Edge cases: empty, single-node, no-edge graphs."""

    def test_empty_snapshot(self):
        """Empty snapshot produces an empty graph."""
        result = build_weighted_dependency_graph(_snapshot())
        assert result.node_count == 0
        assert result.edge_count == 0
        assert result.total_weight == 0

    def test_single_node_no_edges(self):
        """A single file with no imports produces 1 node, 0 edges."""
        result = build_weighted_dependency_graph(
            _snapshot(files=(_file("solo.py"),))
        )
        assert result.node_count == 1
        assert result.edge_count == 0
        assert result.total_weight == 0
        assert result.graph.has_node("solo.py")

    def test_disconnected_nodes(self):
        """Two files with no dependency produce 2 nodes, 0 edges."""
        result = build_weighted_dependency_graph(
            _snapshot(files=(_file("a.py"), _file("b.py")))
        )
        assert result.node_count == 2
        assert result.edge_count == 0


# ---------------------------------------------------------------------------
# Import edges (weight = 1)
# ---------------------------------------------------------------------------


class TestImportEdges:
    """Import-only dependency edges (weight = 1)."""

    def test_single_import_edge(self):
        """app.py imports utils.py => edge(app.py, utils.py, weight=1)."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("app.py", imports=("utils.py",)),
                    _file("utils.py"),
                ),
            )
        )
        assert result.edge_count == 1
        edge_data = result.graph["app.py"]["utils.py"]
        assert edge_data["weight"] == EDGE_WEIGHTS["import"]  # 1
        assert "import" in edge_data["edge_types"]

    def test_import_to_unknown_file_ignored(self):
        """Importing a file not in the snapshot is silently ignored."""
        result = build_weighted_dependency_graph(
            _snapshot(files=(_file("app.py", imports=("nonexistent.py",)),))
        )
        assert result.edge_count == 0

    def test_self_import_ignored(self):
        """A file importing itself is ignored."""
        result = build_weighted_dependency_graph(
            _snapshot(files=(_file("app.py", imports=("app.py",)),))
        )
        assert result.edge_count == 0

    def test_multiple_import_edges(self):
        """Multiple import targets create separate edges."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("app.py", imports=("utils.py", "config.py")),
                    _file("utils.py"),
                    _file("config.py"),
                ),
            )
        )
        assert result.edge_count == 2
        assert result.total_weight == 2


# ---------------------------------------------------------------------------
# Call edges (weight = 2)
# ---------------------------------------------------------------------------


class TestCallEdges:
    """Function-call dependency edges (weight = 2)."""

    def test_single_call_edge(self):
        """A function in app.py depends on utils.py => edge weight=2."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(_file("app.py"), _file("utils.py")),
                functions=(_func("main", "app.py", dependencies=("utils.py",)),),
            )
        )
        assert result.edge_count == 1
        edge_data = result.graph["app.py"]["utils.py"]
        assert edge_data["weight"] == EDGE_WEIGHTS["call"]  # 2
        assert "call" in edge_data["edge_types"]

    def test_call_to_self_ignored(self):
        """Function depending on its own file is ignored."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(_file("app.py"),),
                functions=(_func("main", "app.py", dependencies=("app.py",)),),
            )
        )
        assert result.edge_count == 0


# ---------------------------------------------------------------------------
# Inheritance edges (weight = 3)
# ---------------------------------------------------------------------------


class TestInheritanceEdges:
    """Class-inheritance dependency edges (weight = 3)."""

    def test_single_inherit_edge(self):
        """Child class inherits from parent => edge weight=3."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(_file("child.py"), _file("parent.py")),
                classes=(
                    _cls("Parent", "parent.py"),
                    _cls("Child", "child.py", base_classes=("Parent",)),
                ),
            )
        )
        assert result.edge_count == 1
        edge_data = result.graph["child.py"]["parent.py"]
        assert edge_data["weight"] == EDGE_WEIGHTS["inherit"]  # 3
        assert "inherit" in edge_data["edge_types"]

    def test_inherit_unknown_class_ignored(self):
        """Inheriting from a class not in the snapshot is ignored."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(_file("child.py"),),
                classes=(_cls("Child", "child.py", base_classes=("MissingParent",)),),
            )
        )
        assert result.edge_count == 0

    def test_duplicate_class_name_skipped(self):
        """Ambiguous class name (duplicates) => no edge created."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(_file("a.py"), _file("b.py"), _file("c.py")),
                classes=(
                    _cls("Base", "a.py"),
                    _cls("Base", "b.py"),  # duplicate name
                    _cls("Child", "c.py", base_classes=("Base",)),
                ),
            )
        )
        # "Base" is ambiguous => no inheritance edge created
        assert result.edge_count == 0


# ---------------------------------------------------------------------------
# Weight accumulation (multiple relation types)
# ---------------------------------------------------------------------------


class TestWeightAccumulation:
    """Weights accumulate when multiple relation types exist between same files."""

    def test_import_plus_call_accumulates(self):
        """import(1) + call(2) on same edge => weight=3."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("app.py", imports=("utils.py",)),
                    _file("utils.py"),
                ),
                functions=(_func("main", "app.py", dependencies=("utils.py",)),),
            )
        )
        assert result.edge_count == 1
        edge_data = result.graph["app.py"]["utils.py"]
        assert edge_data["weight"] == EDGE_WEIGHTS["import"] + EDGE_WEIGHTS["call"]  # 3
        assert set(edge_data["edge_types"]) == {"import", "call"}

    def test_import_plus_inherit_accumulates(self):
        """import(1) + inherit(3) on same edge => weight=4."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("child.py", imports=("parent.py",)),
                    _file("parent.py"),
                ),
                classes=(
                    _cls("Parent", "parent.py"),
                    _cls("Child", "child.py", base_classes=("Parent",)),
                ),
            )
        )
        edge_data = result.graph["child.py"]["parent.py"]
        assert edge_data["weight"] == EDGE_WEIGHTS["import"] + EDGE_WEIGHTS["inherit"]  # 4
        assert set(edge_data["edge_types"]) == {"import", "inherit"}

    def test_all_three_types_accumulate(self):
        """import(1) + call(2) + inherit(3) = weight 6."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("child.py", imports=("parent.py",)),
                    _file("parent.py"),
                ),
                functions=(
                    _func("do_stuff", "child.py", dependencies=("parent.py",)),
                ),
                classes=(
                    _cls("Parent", "parent.py"),
                    _cls("Child", "child.py", base_classes=("Parent",)),
                ),
            )
        )
        edge_data = result.graph["child.py"]["parent.py"]
        assert edge_data["weight"] == (
            EDGE_WEIGHTS["import"] + EDGE_WEIGHTS["call"] + EDGE_WEIGHTS["inherit"]
        )
        assert set(edge_data["edge_types"]) == {"import", "call", "inherit"}


# ---------------------------------------------------------------------------
# WeightedGraphResult metadata & summary
# ---------------------------------------------------------------------------


class TestWeightedGraphResultMetadata:
    """Tests for WeightedGraphResult fields and summary string."""

    def test_result_fields(self):
        """node_count, edge_count, total_weight are correct."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("app.py", imports=("utils.py", "config.py")),
                    _file("utils.py"),
                    _file("config.py"),
                ),
            )
        )
        assert result.node_count == 3
        assert result.edge_count == 2
        assert result.total_weight == 2  # 2 import edges * 1

    def test_summary_string_format(self):
        """Summary contains expected structure."""
        result = build_weighted_dependency_graph(
            _snapshot(
                files=(
                    _file("app.py", imports=("utils.py",)),
                    _file("utils.py"),
                ),
            )
        )
        assert "2 nodes" in result.summary
        assert "1 edges" in result.summary
        assert "import_edges=1" in result.summary
        assert "call_edges=0" in result.summary
        assert "inherit_edges=0" in result.summary
        assert "total_weight=1" in result.summary

    def test_frozen_dataclass(self):
        """WeightedGraphResult is frozen."""
        result = build_weighted_dependency_graph(_snapshot())
        with pytest.raises(AttributeError):
            result.node_count = 999  # type: ignore[misc]

    def test_node_attributes_populated(self):
        """Nodes carry language, line_count, function_count, class_count attrs."""
        fi = FileInfo(
            filepath="app.py",
            language="python",
            line_count=100,
            function_names=("main", "helper"),
            class_names=("App",),
            import_sources=(),
        )
        result = build_weighted_dependency_graph(_snapshot(files=(fi,)))
        node_data = result.graph.nodes["app.py"]
        assert node_data["language"] == "python"
        assert node_data["line_count"] == 100
        assert node_data["function_count"] == 2
        assert node_data["class_count"] == 1


# ---------------------------------------------------------------------------
# Integration: sample_snapshot from conftest
# ---------------------------------------------------------------------------


class TestWithSampleSnapshot:
    """Integration test using the sample_snapshot fixture from conftest."""

    def test_sample_snapshot_graph(self, sample_snapshot: CodebaseSnapshot):
        """Build graph from the conftest sample_snapshot fixture."""
        result = build_weighted_dependency_graph(sample_snapshot)
        # 3 files: app.py, utils.py, models.py
        assert result.node_count == 3
        # app.py -> utils.py (import + call), models.py -> utils.py (import)
        assert result.edge_count == 2
        # app.py -> utils.py: import(1) + call(2) = 3
        # models.py -> utils.py: import(1) = 1
        assert result.total_weight == 4

        edge_app_utils = result.graph["app.py"]["utils.py"]
        assert edge_app_utils["weight"] == 3
        assert set(edge_app_utils["edge_types"]) == {"import", "call"}

        edge_models_utils = result.graph["models.py"]["utils.py"]
        assert edge_models_utils["weight"] == 1
        assert edge_models_utils["edge_types"] == ["import"]
