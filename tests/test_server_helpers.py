"""Tests for src/server_helpers.py — pure helper functions extracted from server.py."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import pytest

from src.server_helpers import (
    build_file_to_cone_map,
    build_graph_from_dag,
    build_module_level_graph,
    compute_cone_layers,
    compute_depends_on_cones,
    compute_inter_module_deps_from_dag,
    find_latest_project_dir,
    is_utility_cone,
    now_iso,
    project_id_from_path,
    render_mermaid,
    resolve_output_dir,
    short_mermaid_label,
    validate_json_files_exist,
    write_analysis_outputs,
)


# ---------------------------------------------------------------------------
# now_iso
# ---------------------------------------------------------------------------


class TestNowIso:
    def test_returns_valid_iso_format(self):
        result = now_iso()
        # Should parse without error
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None

    def test_returns_utc_timestamp(self):
        result = now_iso()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo == UTC

    def test_returns_string(self):
        result = now_iso()
        assert isinstance(result, str)

    def test_contains_t_separator(self):
        """ISO format uses T between date and time."""
        result = now_iso()
        assert "T" in result


# ---------------------------------------------------------------------------
# project_id_from_path
# ---------------------------------------------------------------------------


class TestProjectIdFromPath:
    def test_deterministic(self):
        """Same path always produces same ID."""
        path = "/home/user/my-project"
        assert project_id_from_path(path) == project_id_from_path(path)

    def test_length_is_12(self):
        result = project_id_from_path("/some/path")
        assert len(result) == 12

    def test_hex_characters_only(self):
        result = project_id_from_path("/any/path")
        assert re.fullmatch(r"[0-9a-f]{12}", result)

    def test_different_paths_produce_different_ids(self):
        id_a = project_id_from_path("/path/a")
        id_b = project_id_from_path("/path/b")
        assert id_a != id_b

    @pytest.mark.parametrize(
        "path",
        [
            "",
            "/",
            "/a/very/deeply/nested/path/to/some/file",
            "relative/path",
            "C:\\Windows\\Path",
        ],
        ids=["empty", "root", "deep_nesting", "relative", "windows"],
    )
    def test_always_returns_12_hex_chars(self, path: str):
        result = project_id_from_path(path)
        assert len(result) == 12
        assert re.fullmatch(r"[0-9a-f]{12}", result)


# ---------------------------------------------------------------------------
# find_latest_project_dir
# ---------------------------------------------------------------------------


class TestFindLatestProjectDir:
    def test_returns_none_when_no_dirs(self, tmp_path: Path):
        """No .codebase-analysis dirs at all."""
        with patch(
            "src.server_helpers.Path.cwd", return_value=tmp_path
        ), patch("src.server_helpers.Path.home", return_value=tmp_path):
            result = find_latest_project_dir()
        assert result is None

    def test_finds_single_dir(self, tmp_path: Path):
        analysis_dir = tmp_path / "project" / ".codebase-analysis"
        analysis_dir.mkdir(parents=True)
        (analysis_dir / "state.json").write_text("{}")

        with patch(
            "src.server_helpers.Path.cwd", return_value=tmp_path
        ), patch("src.server_helpers.Path.home", return_value=tmp_path / "nonexistent"):
            result = find_latest_project_dir()

        assert result == analysis_dir

    def test_returns_most_recent(self, tmp_path: Path):
        """When multiple dirs exist, returns the most recently modified one."""
        import os
        import time

        older_dir = tmp_path / "old" / ".codebase-analysis"
        older_dir.mkdir(parents=True)
        (older_dir / "state.json").write_text("{}")

        # Ensure different mtimes
        time.sleep(0.05)

        newer_dir = tmp_path / "new" / ".codebase-analysis"
        newer_dir.mkdir(parents=True)
        (newer_dir / "state.json").write_text("{}")

        with patch(
            "src.server_helpers.Path.cwd", return_value=tmp_path
        ), patch("src.server_helpers.Path.home", return_value=tmp_path / "nonexistent"):
            result = find_latest_project_dir()

        assert result == newer_dir

    def test_ignores_dir_without_state_json(self, tmp_path: Path):
        """Directories without state.json are not candidates."""
        analysis_dir = tmp_path / "project" / ".codebase-analysis"
        analysis_dir.mkdir(parents=True)
        # No state.json created

        with patch(
            "src.server_helpers.Path.cwd", return_value=tmp_path
        ), patch("src.server_helpers.Path.home", return_value=tmp_path / "nonexistent"):
            result = find_latest_project_dir()

        assert result is None


# ---------------------------------------------------------------------------
# resolve_output_dir
# ---------------------------------------------------------------------------


class TestResolveOutputDir:
    def test_with_explicit_output_dir(self, tmp_path: Path):
        output = str(tmp_path / "custom-output")
        result = resolve_output_dir("/some/project", output)
        assert result == Path(output).resolve()

    def test_defaults_to_codebase_analysis(self):
        result = resolve_output_dir("/some/project", None)
        assert result == Path("/some/project").resolve() / ".codebase-analysis"

    def test_empty_string_output_dir_uses_default(self):
        """Empty string is falsy, so default path should be used."""
        result = resolve_output_dir("/some/project", "")
        assert result == Path("/some/project").resolve() / ".codebase-analysis"

    def test_returns_resolved_path(self, tmp_path: Path):
        result = resolve_output_dir(str(tmp_path), None)
        assert result.is_absolute()


# ---------------------------------------------------------------------------
# validate_json_files_exist
# ---------------------------------------------------------------------------


_REQUIRED_FILES = [
    "01_structure.json",
    "02_dag.json",
    "03_feature_cones.json",
    "04_file_tokens.json",
    "05_task_manifest.json",
    "06_function_deps.json",
]


class TestValidateJsonFilesExist:
    def test_all_present(self, tmp_path: Path):
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("{}")
        assert validate_json_files_exist(tmp_path) is True

    def test_none_present(self, tmp_path: Path):
        assert validate_json_files_exist(tmp_path) is False

    @pytest.mark.parametrize("missing_file", _REQUIRED_FILES)
    def test_one_missing(self, tmp_path: Path, missing_file: str):
        """Removing any single file should fail validation."""
        for f in _REQUIRED_FILES:
            (tmp_path / f).write_text("{}")
        (tmp_path / missing_file).unlink()
        assert validate_json_files_exist(tmp_path) is False

    def test_empty_directory(self, tmp_path: Path):
        assert validate_json_files_exist(tmp_path) is False

    def test_nonexistent_directory(self, tmp_path: Path):
        bogus = tmp_path / "does-not-exist"
        assert validate_json_files_exist(bogus) is False


# ---------------------------------------------------------------------------
# build_graph_from_dag
# ---------------------------------------------------------------------------


class TestBuildGraphFromDag:
    def test_empty_inputs(self):
        graph = build_graph_from_dag([], [])
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_nodes_only(self):
        graph = build_graph_from_dag(["a.py", "b.py"], [])
        assert set(graph.nodes()) == {"a.py", "b.py"}
        assert graph.number_of_edges() == 0

    def test_edges_with_weight_and_types(self):
        nodes = ["a.py", "b.py"]
        edges = [
            {"source": "a.py", "target": "b.py", "weight": 3, "edge_types": ["import", "call"]},
        ]
        graph = build_graph_from_dag(nodes, edges)
        assert graph.has_edge("a.py", "b.py")
        assert graph["a.py"]["b.py"]["weight"] == 3
        assert graph["a.py"]["b.py"]["edge_types"] == ["import", "call"]

    def test_default_weight_is_one(self):
        edges = [{"source": "a.py", "target": "b.py"}]
        graph = build_graph_from_dag(["a.py", "b.py"], edges)
        assert graph["a.py"]["b.py"]["weight"] == 1

    def test_default_edge_types_is_empty_list(self):
        edges = [{"source": "a.py", "target": "b.py"}]
        graph = build_graph_from_dag(["a.py", "b.py"], edges)
        assert graph["a.py"]["b.py"]["edge_types"] == []

    def test_round_trip(self):
        """Build a graph, extract nodes/edges, rebuild — structure should match."""
        original = nx.DiGraph()
        original.add_node("x.py")
        original.add_node("y.py")
        original.add_edge("x.py", "y.py", weight=5, edge_types=["inherit"])

        nodes = list(original.nodes())
        edges = [
            {
                "source": u,
                "target": v,
                "weight": d["weight"],
                "edge_types": d["edge_types"],
            }
            for u, v, d in original.edges(data=True)
        ]

        rebuilt = build_graph_from_dag(nodes, edges)
        assert set(rebuilt.nodes()) == set(original.nodes())
        assert set(rebuilt.edges()) == set(original.edges())
        for u, v, d in original.edges(data=True):
            assert rebuilt[u][v]["weight"] == d["weight"]
            assert rebuilt[u][v]["edge_types"] == d["edge_types"]

    def test_edges_create_implicit_nodes(self):
        """Edges referencing unlisted nodes should still create them."""
        edges = [{"source": "x.py", "target": "y.py", "weight": 1}]
        graph = build_graph_from_dag([], edges)
        assert "x.py" in graph.nodes()
        assert "y.py" in graph.nodes()


# ---------------------------------------------------------------------------
# short_mermaid_label
# ---------------------------------------------------------------------------


class TestShortMermaidLabel:
    @pytest.mark.parametrize(
        "filepath, expected",
        [
            ("app.py", "app.py"),
            ("src/app.py", "src/app.py"),
            ("a/b/c/d.py", "c/d.py"),
            ("very/deep/nested/path/file.ts", "path/file.ts"),
        ],
        ids=["single_component", "two_components", "four_components", "five_components"],
    )
    def test_last_two_components(self, filepath: str, expected: str):
        assert short_mermaid_label(filepath) == expected

    def test_escapes_double_quotes(self):
        assert "'" in short_mermaid_label('src/"quoted".py')

    def test_escapes_brackets(self):
        result = short_mermaid_label("src/array[0].ts")
        assert "[" not in result
        assert "]" not in result
        assert "(" in result
        assert ")" in result

    def test_empty_string(self):
        result = short_mermaid_label("")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# render_mermaid
# ---------------------------------------------------------------------------


class TestRenderMermaid:
    def test_empty_graph(self):
        graph = nx.DiGraph()
        result = render_mermaid(graph)
        assert "No nodes" in result
        assert result.startswith("graph TD")

    def test_single_node(self):
        graph = nx.DiGraph()
        graph.add_node("src/main.py")
        result = render_mermaid(graph)
        assert "graph TD" in result
        assert "src/main.py" in result
        # Should have a node definition but no edges
        assert "-->" not in result

    def test_two_nodes_one_edge_no_weights(self):
        graph = nx.DiGraph()
        graph.add_edge("a.py", "b.py", weight=2, edge_types=["import"])
        result = render_mermaid(graph)
        assert "-->" in result
        # Should NOT include weight annotation by default
        assert "w=" not in result

    def test_with_weights(self):
        graph = nx.DiGraph()
        graph.add_edge("a.py", "b.py", weight=3, edge_types=["import", "call"])
        result = render_mermaid(graph, include_weights=True)
        assert "w=3" in result
        assert "import/call" in result

    def test_edge_without_types_uses_dep(self):
        graph = nx.DiGraph()
        graph.add_edge("a.py", "b.py", weight=1, edge_types=[])
        result = render_mermaid(graph, include_weights=True)
        assert "dep w=1" in result

    def test_node_ids_are_safe(self):
        """Node IDs in Mermaid must not contain special characters."""
        graph = nx.DiGraph()
        graph.add_node("src/my-file[0].py")
        result = render_mermaid(graph)
        lines = result.split("\n")
        node_line = [l for l in lines if l.strip().startswith("n0")][0]
        # The ID part (before the bracket) should be clean
        assert node_line.strip().startswith("n0[")

    def test_deterministic_output(self):
        """Same graph produces same Mermaid output."""
        graph = nx.DiGraph()
        graph.add_edge("a.py", "b.py")
        graph.add_edge("b.py", "c.py")
        r1 = render_mermaid(graph)
        r2 = render_mermaid(graph)
        assert r1 == r2


# ---------------------------------------------------------------------------
# is_utility_cone
# ---------------------------------------------------------------------------


class TestIsUtilityCone:
    @pytest.mark.parametrize(
        "name",
        [
            "utils.py",
            "src/helpers/format.py",
            "lib/crypto.py",
            "core/base.py",
            "internal/config.py",
            "shared/constants.py",
            "middleware/auth.py",
            "src/logging.py",
            "errors.py",
            "exceptions.py",
            "src/types.py",
            "common/util.py",
        ],
        ids=[
            "utils", "helpers", "lib", "core_base", "internal_config",
            "shared_constants", "middleware", "logging", "errors",
            "exceptions", "types", "common_util",
        ],
    )
    def test_keyword_match(self, name: str):
        assert is_utility_cone(name, layer=5, total_cones=1) is True

    def test_non_utility_name(self):
        assert is_utility_cone("auth/login.py", layer=5, total_cones=1) is False

    def test_layer_zero_with_more_than_two_cones(self):
        """Layer 0 (leaf) with >2 total cones is utility."""
        assert is_utility_cone("feature.py", layer=0, total_cones=5) is True

    def test_layer_zero_with_two_cones_is_not_utility(self):
        """Layer 0 with exactly 2 cones does NOT trigger the layer heuristic."""
        assert is_utility_cone("feature.py", layer=0, total_cones=2) is False

    def test_layer_zero_with_one_cone_is_not_utility(self):
        assert is_utility_cone("feature.py", layer=0, total_cones=1) is False

    def test_high_fan_out(self):
        """Cone whose exclusive files appear in >=3 other cones' shared_deps."""
        all_cones = {
            "core": {"exclusive_files": ["core/engine.py"], "shared_deps": []},
            "auth": {"exclusive_files": [], "shared_deps": ["core/engine.py"]},
            "api": {"exclusive_files": [], "shared_deps": ["core/engine.py"]},
            "cli": {"exclusive_files": [], "shared_deps": ["core/engine.py"]},
        }
        result = is_utility_cone(
            "core",
            layer=5,
            total_cones=1,
            all_cones=all_cones,
        )
        assert result is True

    def test_low_fan_out_not_utility(self):
        """Cone depended on by only 2 others — below threshold of 3."""
        all_cones = {
            "engine": {"exclusive_files": ["engine/run.py"], "shared_deps": []},
            "auth": {"exclusive_files": [], "shared_deps": ["engine/run.py"]},
            "api": {"exclusive_files": [], "shared_deps": ["engine/run.py"]},
        }
        result = is_utility_cone(
            "engine",
            layer=5,
            total_cones=1,
            all_cones=all_cones,
        )
        assert result is False

    def test_no_exclusive_files_no_fan_out_check(self):
        """If cone has no exclusive_files, fan-out check is skipped."""
        all_cones = {
            "engine": {"exclusive_files": [], "shared_deps": []},
            "auth": {"exclusive_files": [], "shared_deps": ["engine/run.py"]},
            "api": {"exclusive_files": [], "shared_deps": ["engine/run.py"]},
            "cli": {"exclusive_files": [], "shared_deps": ["engine/run.py"]},
        }
        result = is_utility_cone(
            "engine",
            layer=5,
            total_cones=1,
            all_cones=all_cones,
        )
        assert result is False

    def test_windows_backslash_path(self):
        """Windows paths with backslashes should be normalised and matched."""
        assert is_utility_cone("src\\helpers\\format.py", layer=5, total_cones=1) is True

    def test_all_cones_none_skips_fan_out(self):
        """When all_cones is None the fan-out check is not performed."""
        result = is_utility_cone("feature.py", layer=5, total_cones=1, all_cones=None)
        assert result is False


# ---------------------------------------------------------------------------
# compute_cone_layers
# ---------------------------------------------------------------------------


class TestComputeConeLayers:
    def test_empty_files(self):
        assert compute_cone_layers([], [], []) == []

    def test_single_file_no_edges(self):
        layers = compute_cone_layers(["a.py"], ["a.py"], [])
        assert layers == [["a.py"]]

    def test_linear_chain(self):
        """a -> b -> c should produce three layers (Kahn BFS, predecessors-first)."""
        files = ["a.py", "b.py", "c.py"]
        edges = [
            {"source": "a.py", "target": "b.py"},
            {"source": "b.py", "target": "c.py"},
        ]
        layers = compute_cone_layers(files, files, edges)
        assert len(layers) == 3
        # a has no predecessors => layer 0 (root)
        # b's only predecessor (a) removed => layer 1
        # c's only predecessor (b) removed => layer 2
        assert layers[0] == ["a.py"]
        assert layers[1] == ["b.py"]
        assert layers[2] == ["c.py"]

    def test_diamond_graph(self):
        """Diamond: a -> b, a -> c, b -> d, c -> d."""
        files = ["a.py", "b.py", "c.py", "d.py"]
        edges = [
            {"source": "a.py", "target": "b.py"},
            {"source": "a.py", "target": "c.py"},
            {"source": "b.py", "target": "d.py"},
            {"source": "c.py", "target": "d.py"},
        ]
        layers = compute_cone_layers(files, files, edges)
        # a has no predecessors => layer 0
        # b and c: predecessor a removed => layer 1
        # d: predecessors b, c removed => layer 2
        assert layers[0] == ["a.py"]
        assert sorted(layers[1]) == ["b.py", "c.py"]
        assert layers[2] == ["d.py"]

    def test_cycle_is_broken(self):
        """Cycles should be broken (all remaining dumped into a layer)."""
        files = ["a.py", "b.py"]
        edges = [
            {"source": "a.py", "target": "b.py"},
            {"source": "b.py", "target": "a.py"},
        ]
        layers = compute_cone_layers(files, files, edges)
        # Both nodes have predecessors in remaining; fallback dumps them all
        total_files = sum(len(layer) for layer in layers)
        assert total_files == 2

    def test_ignores_edges_outside_cone(self):
        """Edges involving files not in the cone should be excluded."""
        cone_files = ["a.py", "b.py"]
        dag_nodes = ["a.py", "b.py", "c.py"]
        edges = [
            {"source": "a.py", "target": "b.py"},
            {"source": "a.py", "target": "c.py"},  # c not in cone
        ]
        layers = compute_cone_layers(cone_files, dag_nodes, edges)
        all_in_layers = [f for layer in layers for f in layer]
        assert "c.py" not in all_in_layers
        assert set(all_in_layers) == {"a.py", "b.py"}

    def test_independent_files(self):
        """Files with no edges between them all land in layer 0."""
        files = ["a.py", "b.py", "c.py"]
        layers = compute_cone_layers(files, files, [])
        assert len(layers) == 1
        assert sorted(layers[0]) == ["a.py", "b.py", "c.py"]


# ---------------------------------------------------------------------------
# compute_depends_on_cones
# ---------------------------------------------------------------------------


class TestComputeDependsOnCones:
    def test_empty_shared_deps(self):
        assert compute_depends_on_cones("cone_a", [], {}) == []

    def test_no_overlap(self):
        all_cones = {
            "cone_a": {"exclusive_files": ["a1.py"]},
            "cone_b": {"exclusive_files": ["b1.py"]},
        }
        result = compute_depends_on_cones("cone_a", ["x.py"], all_cones)
        assert result == []

    def test_overlap_with_one_cone(self):
        all_cones = {
            "cone_a": {"exclusive_files": ["a1.py"]},
            "cone_b": {"exclusive_files": ["shared.py", "b1.py"]},
        }
        result = compute_depends_on_cones("cone_a", ["shared.py"], all_cones)
        assert result == ["cone_b"]

    def test_overlap_with_multiple_cones(self):
        all_cones = {
            "cone_a": {"exclusive_files": ["a1.py"]},
            "cone_b": {"exclusive_files": ["shared.py"]},
            "cone_c": {"exclusive_files": ["shared.py", "other.py"]},
        }
        result = compute_depends_on_cones("cone_a", ["shared.py"], all_cones)
        assert result == ["cone_b", "cone_c"]

    def test_excludes_self(self):
        """A cone should never depend on itself."""
        all_cones = {
            "cone_a": {"exclusive_files": ["shared.py"]},
            "cone_b": {"exclusive_files": ["shared.py"]},
        }
        result = compute_depends_on_cones("cone_a", ["shared.py"], all_cones)
        assert "cone_a" not in result

    def test_returns_sorted(self):
        all_cones = {
            "z_cone": {"exclusive_files": ["s.py"]},
            "a_cone": {"exclusive_files": ["s.py"]},
            "m_cone": {"exclusive_files": ["s.py"]},
            "self": {"exclusive_files": []},
        }
        result = compute_depends_on_cones("self", ["s.py"], all_cones)
        assert result == sorted(result)

    def test_cone_without_exclusive_files_key(self):
        """Cones missing the 'exclusive_files' key should be handled gracefully."""
        all_cones = {
            "cone_a": {"exclusive_files": ["a.py"]},
            "cone_b": {},  # no exclusive_files key
        }
        result = compute_depends_on_cones("cone_a", ["something.py"], all_cones)
        assert result == []


# ---------------------------------------------------------------------------
# write_analysis_outputs
# ---------------------------------------------------------------------------


class TestWriteAnalysisOutputs:
    """Test the JSON file writing function using a tmp directory."""

    @staticmethod
    def _make_snapshot():
        """Create a minimal snapshot-like object."""
        from src.parser.codebase import (
            ClassInfo,
            CodebaseSnapshot,
            FileInfo,
            FunctionInfo,
        )

        fi = FileInfo(
            filepath="main.py",
            language="python",
            line_count=42,
            char_count=800,
            function_names=("run",),
            class_names=(),
            import_sources=(),
        )
        return CodebaseSnapshot(
            root_path="/fake",
            files=(fi,),
            functions=(),
            classes=(),
            languages_detected=("python",),
            total_lines=42,
        )

    @staticmethod
    def _make_weighted_result():
        """Create a minimal weighted-result-like object."""
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class _FakeResult:
            node_count: int = 1
            edge_count: int = 0
            total_weight: int = 0

        return _FakeResult()

    def test_writes_all_files(self, tmp_path: Path):
        output = tmp_path / "out"
        output.mkdir()

        graph = nx.DiGraph()
        graph.add_node("main.py")

        state = write_analysis_outputs(
            output_path=output,
            project_id="abc123",
            resolved_path=Path("/fake"),
            snapshot=self._make_snapshot(),
            weighted_result=self._make_weighted_result(),
            graph=graph,
            cones={},
            infrastructure=[],
            cone_dicts={},
            file_tokens={"main.py": 100},
            file_details=[{"filepath": "main.py", "tokens": 100}],
            task_manifest={"tasks": {}},
        )

        for f in _REQUIRED_FILES:
            assert (output / f).exists(), f"{f} was not written"
        assert (output / "state.json").exists()

    def test_state_structure(self, tmp_path: Path):
        output = tmp_path / "out"
        output.mkdir()

        graph = nx.DiGraph()
        graph.add_node("main.py")

        task_manifest = {
            "tasks": {
                "task-1": {"description": "Write docs"},
                "task-2": {"description": "Write tests"},
            }
        }

        state = write_analysis_outputs(
            output_path=output,
            project_id="abc123",
            resolved_path=Path("/fake"),
            snapshot=self._make_snapshot(),
            weighted_result=self._make_weighted_result(),
            graph=graph,
            cones={},
            infrastructure=[],
            cone_dicts={},
            file_tokens={"main.py": 100},
            file_details=[],
            task_manifest=task_manifest,
        )

        assert state["project_id"] == "abc123"
        assert state["status"] == "analysis_complete"
        assert "task-1" in state["tasks"]
        assert "task-2" in state["tasks"]
        assert state["tasks"]["task-1"]["status"] == "pending"

    def test_structure_json_contents(self, tmp_path: Path):
        output = tmp_path / "out"
        output.mkdir()

        graph = nx.DiGraph()
        graph.add_node("main.py")

        write_analysis_outputs(
            output_path=output,
            project_id="proj42",
            resolved_path=Path("/fake"),
            snapshot=self._make_snapshot(),
            weighted_result=self._make_weighted_result(),
            graph=graph,
            cones={},
            infrastructure=[],
            cone_dicts={},
            file_tokens={},
            file_details=[],
            task_manifest={"tasks": {}},
        )

        data = json.loads((output / "01_structure.json").read_text())
        assert data["project_id"] == "proj42"
        assert data["file_count"] == 1
        assert data["files"][0]["filepath"] == "main.py"

    def test_dag_json_contents(self, tmp_path: Path):
        output = tmp_path / "out"
        output.mkdir()

        graph = nx.DiGraph()
        graph.add_edge("a.py", "b.py", weight=2, edge_types=["import"])

        write_analysis_outputs(
            output_path=output,
            project_id="proj42",
            resolved_path=Path("/fake"),
            snapshot=self._make_snapshot(),
            weighted_result=self._make_weighted_result(),
            graph=graph,
            cones={},
            infrastructure=[],
            cone_dicts={},
            file_tokens={},
            file_details=[],
            task_manifest={"tasks": {}},
        )

        data = json.loads((output / "02_dag.json").read_text())
        assert data["project_id"] == "proj42"
        assert len(data["edges"]) == 1
        assert data["edges"][0]["weight"] == 2

    def test_documentation_metadata_in_state(self, tmp_path: Path):
        output = tmp_path / "out"
        output.mkdir()

        graph = nx.DiGraph()

        state = write_analysis_outputs(
            output_path=output,
            project_id="abc",
            resolved_path=Path("/fake"),
            snapshot=self._make_snapshot(),
            weighted_result=self._make_weighted_result(),
            graph=graph,
            cones={},
            infrastructure=[],
            cone_dicts={},
            file_tokens={},
            file_details=[],
            task_manifest={"tasks": {"t1": {}}},
        )

        doc = state["documentation"]
        assert doc["output_dir"] == str(output)
        assert doc["index_written"] is False
        assert doc["total_planned"] == 1
        assert doc["source_file_coverage_percent"] == 0.0


# ---------------------------------------------------------------------------
# build_file_to_cone_map
# ---------------------------------------------------------------------------


class TestBuildFileToConeMap:
    def test_empty_cones(self):
        assert build_file_to_cone_map({}) == {}

    def test_single_cone_with_files(self):
        cones = {"auth": {"exclusive_files": ["auth/login.py", "auth/signup.py"]}}
        result = build_file_to_cone_map(cones)
        assert result == {"auth/login.py": "auth", "auth/signup.py": "auth"}

    def test_multiple_cones(self):
        cones = {
            "auth": {"exclusive_files": ["auth/login.py"]},
            "api": {"exclusive_files": ["api/routes.py"]},
        }
        result = build_file_to_cone_map(cones)
        assert result["auth/login.py"] == "auth"
        assert result["api/routes.py"] == "api"

    def test_cone_without_exclusive_files(self):
        cones = {"empty": {}}
        result = build_file_to_cone_map(cones)
        assert result == {}


# ---------------------------------------------------------------------------
# compute_inter_module_deps_from_dag
# ---------------------------------------------------------------------------


class TestComputeInterModuleDepsFromDag:
    def test_cross_module_edge_creates_dep(self):
        cones = {
            "auth": {"exclusive_files": ["auth/login.py"]},
            "api": {"exclusive_files": ["api/routes.py"]},
        }
        edges = [{"source": "api/routes.py", "target": "auth/login.py"}]
        deps = compute_inter_module_deps_from_dag(cones, edges)
        assert "auth" in deps["api"]

    def test_same_module_edge_no_dep(self):
        cones = {
            "auth": {"exclusive_files": ["auth/login.py", "auth/signup.py"]},
        }
        edges = [{"source": "auth/login.py", "target": "auth/signup.py"}]
        deps = compute_inter_module_deps_from_dag(cones, edges)
        assert deps["auth"] == set()

    def test_empty_edges(self):
        cones = {"auth": {"exclusive_files": ["a.py"]}, "api": {"exclusive_files": ["b.py"]}}
        deps = compute_inter_module_deps_from_dag(cones, [])
        assert all(len(v) == 0 for v in deps.values())

    def test_edge_to_unknown_file_ignored(self):
        cones = {"auth": {"exclusive_files": ["a.py"]}}
        edges = [{"source": "a.py", "target": "unknown.py"}]
        deps = compute_inter_module_deps_from_dag(cones, edges)
        assert deps["auth"] == set()

    def test_multiple_cross_module_edges(self):
        cones = {
            "auth": {"exclusive_files": ["auth.py"]},
            "api": {"exclusive_files": ["api.py"]},
            "db": {"exclusive_files": ["db.py"]},
        }
        edges = [
            {"source": "api.py", "target": "auth.py"},
            {"source": "api.py", "target": "db.py"},
        ]
        deps = compute_inter_module_deps_from_dag(cones, edges)
        assert deps["api"] == {"auth", "db"}


# ---------------------------------------------------------------------------
# build_module_level_graph
# ---------------------------------------------------------------------------


class TestBuildModuleLevelGraph:
    def test_nodes_equal_cone_count(self):
        cones = {
            "auth": {"exclusive_files": ["a.py"]},
            "api": {"exclusive_files": ["b.py"]},
            "db": {"exclusive_files": ["c.py"]},
        }
        graph = build_module_level_graph(cones, [])
        assert graph.number_of_nodes() == 3

    def test_cross_module_edge_weight(self):
        cones = {
            "auth": {"exclusive_files": ["a.py"]},
            "api": {"exclusive_files": ["b.py"]},
        }
        edges = [
            {"source": "b.py", "target": "a.py"},
            {"source": "b.py", "target": "a.py"},  # duplicate edge
        ]
        graph = build_module_level_graph(cones, edges)
        assert graph.has_edge("api", "auth")
        assert graph["api"]["auth"]["weight"] == 2

    def test_same_module_edges_no_graph_edge(self):
        cones = {"auth": {"exclusive_files": ["a.py", "b.py"]}}
        edges = [{"source": "a.py", "target": "b.py"}]
        graph = build_module_level_graph(cones, edges)
        assert graph.number_of_edges() == 0

    def test_empty_cones(self):
        graph = build_module_level_graph({}, [])
        assert graph.number_of_nodes() == 0
