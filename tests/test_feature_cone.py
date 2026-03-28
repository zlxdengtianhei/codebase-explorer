"""Tests for src/graph/feature_cone.py — feature cone extraction algorithm.

Covers:
- extract_feature_cones (full pipeline with snapshot)
- _separate_testing_files
- _generate_cone_name / _rename_cones
- FeatureCone dataclass
- Various graph topologies (star, chain, diamond, disconnected)
"""

from __future__ import annotations

import pytest
import networkx as nx

from src.graph.feature_cone import (
    FeatureCone,
    _semantic_suffix,
    _separate_testing_files,
    _generate_cone_name,
    _rename_cones,
    extract_feature_cones,
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


def _make_snapshot(
    files: tuple[FileInfo, ...] = (),
    functions: tuple[FunctionInfo, ...] = (),
    classes: tuple[ClassInfo, ...] = (),
) -> CodebaseSnapshot:
    """Build a minimal CodebaseSnapshot for testing."""
    total_lines = sum(f.line_count for f in files)
    return CodebaseSnapshot(
        root_path="/fake",
        files=files,
        functions=functions,
        classes=classes,
        languages_detected=("python",),
        total_lines=total_lines,
    )


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


# ---------------------------------------------------------------------------
# T-01: Test file root filtering in extract_feature_cones
# ---------------------------------------------------------------------------


class TestTestFileRootFiltering:
    """Tests for T-01: test files filtered from roots before threshold calc."""

    def test_test_roots_excluded_from_threshold(self):
        """Test files as roots should be filtered out, reducing root count."""
        # 3 real roots + 5 test roots = 8 total
        # Without filtering: threshold = max(2, round(sqrt(8)*1.2)) = 3
        # With filtering: 3 roots -> threshold = max(2, round(sqrt(3)*1.2)) = 2
        dag = nx.DiGraph()
        dag.add_edge("cli.py", "shared.py", weight=1)
        dag.add_edge("api.py", "shared.py", weight=1)
        dag.add_edge("app.py", "shared.py", weight=1)
        for i in range(5):
            dag.add_edge(f"tests/test_{i}.py", "shared.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(
                _file(n) for n in dag.nodes()
            ),
        )
        cones, infra = extract_feature_cones(dag, snapshot)
        # shared.py should be infra (shared by all 3 non-test roots, threshold=2)
        assert "shared.py" in infra

    def test_all_test_roots_fallback(self):
        """If all roots are test files, fall back to unfiltered roots."""
        dag = nx.DiGraph()
        dag.add_edge("tests/test_a.py", "utils.py", weight=1)
        dag.add_edge("tests/test_b.py", "utils.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(_file(n) for n in dag.nodes()),
        )
        # Should not crash; falls back to unfiltered roots
        cones, infra = extract_feature_cones(dag, snapshot)
        assert len(cones) >= 1

    def test_test_nodes_still_in_dag(self):
        """Test files are filtered from roots but remain in the DAG for BFS."""
        dag = nx.DiGraph()
        dag.add_edge("cli.py", "tests/test_cli.py", weight=1)
        dag.add_edge("cli.py", "app.py", weight=1)

        snapshot = _make_snapshot(
            files=tuple(_file(n) for n in dag.nodes()),
        )
        cones, infra = extract_feature_cones(dag, snapshot)
        # test_cli.py should still be reachable via BFS from cli.py
        all_files = set()
        for cone in cones.values():
            all_files.update(cone.exclusive_files)
        all_files.update(infra)
        assert "tests/test_cli.py" in all_files


# ---------------------------------------------------------------------------
# extract_feature_cones (full pipeline)
# ---------------------------------------------------------------------------


class TestExtractFeatureCones:
    """Integration tests for extract_feature_cones."""

    def test_simple_chain(self):
        """Simple chain: cli.py -> app.py -> utils.py."""
        snapshot = _make_snapshot(
            files=(
                _file("cli.py", ("app.py",)),
                _file("app.py", ("utils.py",)),
                _file("utils.py"),
            ),
        )
        dag = nx.DiGraph()
        dag.add_edge("cli.py", "app.py", weight=1)
        dag.add_edge("app.py", "utils.py", weight=1)

        cones, infra = extract_feature_cones(dag, snapshot)
        assert len(cones) >= 1
        # All files should be accounted for
        all_files = set()
        for cone in cones.values():
            all_files.update(cone.exclusive_files)
        all_files.update(infra)
        assert {"cli.py", "app.py", "utils.py"}.issubset(all_files | set(infra))

    def test_star_topology_shared_infrastructure(self):
        """Star: A -> utils.py, B -> utils.py, C -> utils.py.

        With Louvain-based infra detection, a file needs both semantic hints
        (infra-like name) AND cross-community import to be classified as infra.
        We use 'utils.py' which matches the known infra stems.
        """
        dag = nx.DiGraph()
        dag.add_edge("A", "utils.py", weight=1)
        dag.add_edge("B", "utils.py", weight=1)
        dag.add_edge("C", "utils.py", weight=1)

        snapshot = _make_snapshot(
            files=(_file("A"), _file("B"), _file("C"), _file("utils.py")),
        )

        cones, infra = extract_feature_cones(dag, snapshot)
        # utils.py should be in infra OR all files in a single cone
        # (Louvain may group them all together for such a small graph)
        all_exclusive = set()
        for c in cones.values():
            all_exclusive.update(c.exclusive_files)
        all_accounted = all_exclusive | set(infra)
        assert {"A", "B", "C", "utils.py"}.issubset(all_accounted)

    def test_disconnected_graph_separate_cones(self):
        """Two disconnected components get separate cones."""
        dag = nx.DiGraph()
        dag.add_edge("a/main.py", "a/util.py", weight=1)
        dag.add_edge("b/main.py", "b/util.py", weight=1)

        snapshot = _make_snapshot(
            files=(
                _file("a/main.py", ("a/util.py",)),
                _file("a/util.py"),
                _file("b/main.py", ("b/util.py",)),
                _file("b/util.py"),
            ),
        )

        cones, infra = extract_feature_cones(dag, snapshot)
        # Should have at least 2 cones (one per component)
        assert len(cones) >= 2

    def test_empty_dag_raises_value_error(self):
        """An empty DAG raises ValueError (no nodes)."""
        dag = nx.DiGraph()
        snapshot = _make_snapshot()
        with pytest.raises(ValueError):
            extract_feature_cones(dag, snapshot)

    def test_louvain_groups_connected_components(self):
        """Louvain-based extraction groups well-connected components together.

        With Louvain, connected components with strong internal edges should
        form distinct cones. shared_threshold is no longer used.
        """
        dag = nx.DiGraph()
        # Two clear clusters with no cross-edges
        dag.add_edge("a/main.py", "a/core.py", weight=2)
        dag.add_edge("a/main.py", "a/helper.py", weight=1)
        dag.add_edge("a/core.py", "a/helper.py", weight=1)
        dag.add_edge("b/main.py", "b/engine.py", weight=2)
        dag.add_edge("b/main.py", "b/util.py", weight=1)
        dag.add_edge("b/engine.py", "b/util.py", weight=1)

        snapshot = _make_snapshot(
            files=(
                _file("a/main.py"), _file("a/core.py"), _file("a/helper.py"),
                _file("b/main.py"), _file("b/engine.py"), _file("b/util.py"),
            ),
        )

        cones, infra = extract_feature_cones(dag, snapshot)
        # Should have at least 2 cones (one per cluster)
        assert len(cones) >= 2
        # All files should be accounted for
        all_files = set()
        for c in cones.values():
            all_files.update(c.exclusive_files)
        all_files.update(infra)
        expected = {"a/main.py", "a/core.py", "a/helper.py",
                    "b/main.py", "b/engine.py", "b/util.py"}
        assert expected.issubset(all_files)


# ---------------------------------------------------------------------------
# _generate_cone_name / _rename_cones
# ---------------------------------------------------------------------------


class TestConeNaming:
    """Tests for _generate_cone_name and _rename_cones."""

    def test_testing_cone_name(self):
        """Files classified as testing produce 'testing' name."""
        name = _generate_cone_name(["tests/test_a.py", "tests/test_b.py"])
        assert name == "testing"

    def test_api_cone_name(self):
        """Files in api/ produce 'api' name."""
        name = _generate_cone_name(["api/routes.py", "api/handlers.py"])
        assert name == "api"

    def test_empty_files_returns_empty(self):
        """No files => 'empty'."""
        name = _generate_cone_name([])
        assert name == "empty"

    def test_unknown_files_fallback_to_directory(self):
        """Unknown-category files in same dir fall back to directory name."""
        name = _generate_cone_name(["mypackage/foo.py", "mypackage/bar.py"])
        assert name == "mypackage"

    def test_rename_disambiguates_with_semantic_suffix(self):
        """Duplicate names get semantic suffixes instead of numbers."""
        cones = [
            FeatureCone("c1", "c1", ("tests/test_a.py",), (), 0, 0),
            FeatureCone("c2", "c2", ("tests/test_b.py",), (), 0, 0),
        ]
        renamed = _rename_cones(cones)
        ids = [c.cone_id for c in renamed]
        # Should use semantic suffixes like testing-test_a, testing-test_b
        assert all("testing-" in i for i in ids)
        # No __init__ or plain numeric suffix
        assert all("-1" not in i and "-2" not in i for i in ids)

    def test_root_level_files_core_runtime(self):
        """Root-level unknown files get 'core-runtime' name."""
        name = _generate_cone_name(["setup.py", "pyproject.py"])
        assert name == "core-runtime"

    def test_init_replaced_with_parent_dir(self):
        """__init__.py as first file uses parent directory name."""
        name = _generate_cone_name(["pkg/sub/__init__.py"])
        assert name != "__init__"
        assert name == "sub"

    def test_new_categories_middleware(self):
        """Files classified as middleware produce 'middleware' name."""
        name = _generate_cone_name(["middleware.py", "auth_middleware.py"])
        assert name == "middleware"

    def test_new_categories_security(self):
        """Files in security/ produce 'security' name."""
        name = _generate_cone_name(["security/auth.py", "security/perms.py"])
        assert name == "security"

    def test_new_categories_utils(self):
        """utils.py is classified as 'utils'."""
        name = _generate_cone_name(["utils.py", "helpers.py"])
        assert name == "utils"

    def test_new_categories_exceptions(self):
        """exceptions.py is classified as 'exceptions'."""
        name = _generate_cone_name(["exceptions.py"])
        assert name == "exceptions"


# ---------------------------------------------------------------------------
# _separate_testing_files
# ---------------------------------------------------------------------------


class TestSeparateTestingFiles:
    """Tests for _separate_testing_files."""

    def test_separate_testing_files(self):
        """Testing files are separated from runtime files in a cone."""
        mixed = FeatureCone(
            "mixed", "mixed",
            ("src/app.py", "tests/test_app.py", "src/utils.py"),
            (), 0, 0,
        )
        result = _separate_testing_files([mixed])
        assert len(result) == 2
        cone_ids = {c.cone_id for c in result}
        assert "mixed" in cone_ids
        assert "mixed::testing" in cone_ids

    def test_all_testing_not_separated(self):
        """A cone that is all testing files is NOT split."""
        all_test = FeatureCone(
            "tests", "tests",
            ("tests/test_a.py", "tests/test_b.py"),
            (), 0, 0,
        )
        result = _separate_testing_files([all_test])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# FeatureCone dataclass
# ---------------------------------------------------------------------------


class TestFeatureConeDataclass:
    """Tests for FeatureCone frozen dataclass."""

    def test_frozen_immutable(self):
        """FeatureCone is frozen and cannot be mutated."""
        cone = FeatureCone("c", "entry.py", ("a.py",), ("b.py",), 0, 100)
        with pytest.raises(AttributeError):
            cone.cone_id = "new_id"  # type: ignore[misc]

    def test_fields_accessible(self):
        """All fields are accessible."""
        cone = FeatureCone("c", "entry.py", ("a.py",), ("b.py",), 2, 500)
        assert cone.cone_id == "c"
        assert cone.entry_point == "entry.py"
        assert cone.exclusive_files == ("a.py",)
        assert cone.shared_deps == ("b.py",)
        assert cone.layer == 2
        assert cone.token_count == 500
