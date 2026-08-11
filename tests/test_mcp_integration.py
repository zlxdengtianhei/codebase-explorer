"""Integration tests for all 7 MCP tools via direct function invocation.

Tests the complete flow: analyze_codebase -> query tools -> submit_analysis.
Uses a temporary directory with real Python files as the test codebase.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from mcp.server.fastmcp.exceptions import ToolError

from src.parser.codebase import CodebaseParser
from src.server import (
    analyze_codebase,
    get_dependency_graph,
    get_file_tokens,
    get_progress,
    get_structure,
    submit_analysis,
)
from src.state.run_lifecycle import resolve_active_run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_python_file(path: Path, content: str) -> None:
    """Write a Python file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a small but realistic Python project for analysis.

    Structure:
        app.py       -- imports models, utils
        models.py    -- imports utils
        utils.py     -- no imports (leaf)
        cli.py       -- imports app
    """
    _write_python_file(
        tmp_path / "app.py",
        (
            "import models\n"
            "import utils\n"
            "\n"
            "class Application:\n"
            "    def __init__(self):\n"
            "        self.model = models.create_model()\n"
            "\n"
            "    def run(self):\n"
            "        utils.log('running')\n"
            "\n"
            "def main():\n"
            "    app = Application()\n"
            "    app.run()\n"
        ),
    )
    _write_python_file(
        tmp_path / "models.py",
        (
            "import utils\n"
            "\n"
            "class UserModel:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n"
            "\n"
            "class ProductModel:\n"
            "    def __init__(self, title):\n"
            "        self.title = title\n"
            "\n"
            "def create_model():\n"
            "    return UserModel('default')\n"
            "\n"
            "def validate_model(model):\n"
            "    return utils.validate(model)\n"
        ),
    )
    _write_python_file(
        tmp_path / "utils.py",
        (
            "def log(message):\n"
            "    print(message)\n"
            "\n"
            "def validate(obj):\n"
            "    return obj is not None\n"
            "\n"
            "def format_output(data):\n"
            "    return str(data)\n"
        ),
    )
    _write_python_file(
        tmp_path / "cli.py",
        (
            "import app\n"
            "\n"
            "def cli_main():\n"
            "    app.main()\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    cli_main()\n"
        ),
    )
    return tmp_path


def _make_mock_ctx() -> MagicMock:
    """Build a mock MCP Context that provides a CodebaseParser via lifespan."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"parser": CodebaseParser()}
    return ctx


@pytest.fixture
def mock_ctx() -> MagicMock:
    return _make_mock_ctx()


# ---------------------------------------------------------------------------
# Helper: run full analysis and return the output directory
# ---------------------------------------------------------------------------


async def _run_analysis(project_path: Path, output_dir: Path, ctx: MagicMock) -> dict:
    """Run analyze_codebase and return its result dict."""
    return await analyze_codebase(
        path=str(project_path),
        languages=["python"],
        output_dir=str(output_dir),
        force_reindex=True,
        ctx=ctx,
    )


@pytest_asyncio.fixture
async def analyzed_project(
    sample_project: Path,
    mock_ctx: MagicMock,
    tmp_path: Path,
) -> tuple[dict, Path]:
    """Run analysis on the sample project and return (result, output_dir).

    Also patches find_latest_project_dir so query tools can locate the output.
    """
    output_dir = tmp_path / ".codebase-analysis"
    result = await _run_analysis(sample_project, output_dir, mock_ctx)
    return result, output_dir


# ---------------------------------------------------------------------------
# Tool 1: analyze_codebase
# ---------------------------------------------------------------------------


class TestAnalyzeCodebase:
    @pytest.mark.asyncio
    async def test_successful_analysis(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """Full analysis pipeline completes and returns expected metadata."""
        output_dir = tmp_path / ".codebase-analysis"
        result = await _run_analysis(sample_project, output_dir, mock_ctx)

        assert result["status"] == "success"
        assert result["files_analyzed"] == 4
        assert result["feature_cones_found"] >= 1
        assert result["total_tokens"] > 0
        assert "project_id" in result

    @pytest.mark.asyncio
    async def test_generates_all_json_files(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """The immutable V2 anchor and selected generation are both complete."""
        output_dir = tmp_path / ".codebase-analysis"
        result = await _run_analysis(sample_project, output_dir, mock_ctx)

        generation = Path(result["canonical_state_file"]).parent
        expected_files = [
            "01_structure.json",
            "02_dag.json",
            "03_feature_cones.json",
            "04_file_tokens.json",
            "05_task_manifest.json",
            "06_function_deps.json",
        ]
        for fname in expected_files:
            assert (generation / fname).exists(), f"Missing: {fname}"
        assert (generation / "state-v3.json").exists()
        assert (output_dir / "state.json").exists()
        assert (output_dir / "active-run.json").exists()

    @pytest.mark.asyncio
    async def test_cache_hit_on_reanalysis(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """Second analysis with force_reindex=False returns cached result."""
        output_dir = tmp_path / ".codebase-analysis"
        await _run_analysis(sample_project, output_dir, mock_ctx)

        # Second call without force_reindex
        cached_result = await analyze_codebase(
            path=str(sample_project),
            languages=["python"],
            output_dir=str(output_dir),
            force_reindex=False,
            ctx=mock_ctx,
        )
        assert cached_result["cached"] is True
        assert cached_result["status"] == "success"

    @pytest.mark.asyncio
    async def test_invalid_path_raises_tool_error(self, mock_ctx: MagicMock, tmp_path: Path):
        """Passing a non-existent path raises ToolError."""
        bogus = str(tmp_path / "nonexistent")
        with pytest.raises(ToolError, match="Not a directory"):
            await analyze_codebase(
                path=bogus,
                ctx=mock_ctx,
            )

    @pytest.mark.asyncio
    async def test_state_json_has_pending_tasks(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """Selected V3 and immutable V2 begin with the same pending tasks."""
        output_dir = tmp_path / ".codebase-analysis"
        result = await _run_analysis(sample_project, output_dir, mock_ctx)

        state = json.loads((output_dir / "state.json").read_text())
        assert state["status"] == "analysis_complete"
        tasks = state.get("tasks", {})
        for task in tasks.values():
            assert task["status"] == "pending"
        selected = resolve_active_run(output_dir)
        assert selected.state_path == Path(result["canonical_state_file"])
        assert all(
            record.status == "pending"
            for record in selected.snapshot.legacy_submission.tasks
        )


# ---------------------------------------------------------------------------
# Tool 2: get_structure
# ---------------------------------------------------------------------------


class TestGetStructure:
    @pytest.mark.asyncio
    async def test_summary_mode(
        self, analyzed_project: tuple[dict, Path]
    ):
        """No arguments returns project summary with file/function/class counts."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_structure()

        assert result["status"] == "success"
        assert result["query_type"] == "summary"
        assert result["file_count"] == 4
        assert result["function_count"] > 0
        assert "language_breakdown" in result
        assert "python" in result["language_breakdown"]

    @pytest.mark.asyncio
    async def test_file_query_mode(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a specific file returns its details including functions."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_structure(file="app.py")

        assert result["status"] == "success"
        assert result["query_type"] == "file"
        assert result["filepath"] == "app.py"
        func_names = [f["name"] for f in result["functions"]]
        assert "main" in func_names

    @pytest.mark.asyncio
    async def test_function_query_mode(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a function by name returns its location(s)."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_structure(function="main")

        assert result["status"] == "success"
        assert result["query_type"] == "function"
        assert result["function_name"] == "main"
        assert len(result["matches"]) >= 1
        filepaths = [m["filepath"] for m in result["matches"]]
        assert "app.py" in filepaths

    @pytest.mark.asyncio
    async def test_module_query_mode(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying by module/cone name returns files within that cone."""
        from src.state.run_lifecycle import REQUIRED_ARTIFACTS, resolve_active_run

        _, output_dir = analyzed_project
        selected = resolve_active_run(output_dir)
        assert all(not (output_dir / name).exists() for name in REQUIRED_ARTIFACTS)

        # First discover a valid cone_id from feature cones
        cones_data = json.loads(
            (selected.generation_path / "03_feature_cones.json").read_text()
        )
        cones = cones_data.get("cones", {})
        if not cones:
            pytest.skip("No feature cones detected — cannot test module query")
        cone_id = next(iter(cones))
        expected_files = set(cones[cone_id].get("exclusive_files", []))
        structure = json.loads(
            (selected.generation_path / "01_structure.json").read_text()
        )
        expected_records = [
            item for item in structure["files"] if item["filepath"] in expected_files
        ]

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_structure(module=cone_id)

        assert result["status"] == "success"
        assert result["query_type"] == "module"
        assert result["module_name"] == cone_id
        assert {item["filepath"] for item in result["files"]} == expected_files
        assert result["file_count"] == len(expected_records)
        assert result["total_functions"] == sum(
            len(item["function_names"]) for item in expected_records
        )
        assert result["total_classes"] == sum(
            len(item["class_names"]) for item in expected_records
        )
        assert isinstance(result["files"], list)

    @pytest.mark.asyncio
    async def test_file_not_found_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a non-existent file raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="File not found"):
                await get_structure(file="nonexistent.py")

    @pytest.mark.asyncio
    async def test_function_not_found_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a non-existent function raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="Function.*not found"):
                await get_structure(function="nonexistent_func_xyz")

    @pytest.mark.asyncio
    async def test_no_project_raises_tool_error(self):
        """When no project directory exists, raises ToolError."""
        with patch("src.server_helpers.find_latest_project_dir", return_value=None):
            with pytest.raises(ToolError, match="No project found"):
                await get_structure()


# ---------------------------------------------------------------------------
# Tool 3: get_dependency_graph
# ---------------------------------------------------------------------------


class TestGetDependencyGraph:
    @pytest.mark.asyncio
    async def test_project_scope(self, analyzed_project: tuple[dict, Path]):
        """scope='project' returns module-level aggregated graph."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_dependency_graph(scope="project")

        assert result["status"] == "success"
        assert result["scope"] == "project"
        assert result["level"] == "module"
        # Module-level graph should have fewer nodes than file count
        assert result["node_count"] >= 1
        assert "mermaid_graph" in result
        assert result["mermaid_graph"].startswith("graph TD")
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)

    @pytest.mark.asyncio
    async def test_cone_scope(self, analyzed_project: tuple[dict, Path]):
        """scope='cone' returns the subgraph for a specific feature cone."""
        from src.state.run_lifecycle import REQUIRED_ARTIFACTS, resolve_active_run

        _, output_dir = analyzed_project
        selected = resolve_active_run(output_dir)
        assert all(not (output_dir / name).exists() for name in REQUIRED_ARTIFACTS)

        cones_data = json.loads(
            (selected.generation_path / "03_feature_cones.json").read_text()
        )
        dag_data = json.loads((selected.generation_path / "02_dag.json").read_text())
        cones = cones_data.get("cones", {})
        if not cones:
            pytest.skip("No cones found")
        cone_id = next(iter(cones))
        cone = cones[cone_id]
        expected_nodes = (
            set(cone.get("exclusive_files", [])) | set(cone.get("shared_deps", []))
        ) & set(dag_data["nodes"])
        expected_edges = {
            (edge["source"], edge["target"])
            for edge in dag_data["edges"]
            if edge["source"] in expected_nodes and edge["target"] in expected_nodes
        }

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_dependency_graph(scope="cone", target=cone_id)

        assert result["status"] == "success"
        assert result["scope"] == "cone"
        assert result["target"] == cone_id
        assert set(result["nodes"]) == expected_nodes
        assert {(edge["source"], edge["target"]) for edge in result["edges"]} == expected_edges
        assert result["node_count"] == len(result["nodes"])
        assert result["edge_count"] == len(result["edges"])
        assert isinstance(result["nodes"], list)
        assert isinstance(result["edges"], list)
        assert isinstance(result["mermaid_graph"], str)
        assert isinstance(result["circular_deps"], list)

    @pytest.mark.asyncio
    async def test_file_scope(self, analyzed_project: tuple[dict, Path]):
        """scope='file' returns the N-hop subgraph around a specific file."""
        from src.state.run_lifecycle import REQUIRED_ARTIFACTS, resolve_active_run

        _, output_dir = analyzed_project
        selected = resolve_active_run(output_dir)
        assert all(not (output_dir / name).exists() for name in REQUIRED_ARTIFACTS)

        # Find a valid file node from the DAG
        dag_data = json.loads((selected.generation_path / "02_dag.json").read_text())
        nodes = dag_data.get("nodes", [])
        assert len(nodes) >= 1, "DAG should have at least one node"
        target_file = nodes[0]
        expected_nodes = {target_file}
        for edge in dag_data["edges"]:
            if edge["source"] == target_file:
                expected_nodes.add(edge["target"])
            if edge["target"] == target_file:
                expected_nodes.add(edge["source"])
        expected_edges = {
            (edge["source"], edge["target"])
            for edge in dag_data["edges"]
            if edge["source"] in expected_nodes and edge["target"] in expected_nodes
        }

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_dependency_graph(
                scope="file", target=target_file, hops=1
            )

        assert result["status"] == "success"
        assert result["scope"] == "file"
        assert result["target"] == target_file
        assert target_file in result["nodes"]
        assert set(result["nodes"]) == expected_nodes
        assert {(edge["source"], edge["target"]) for edge in result["edges"]} == expected_edges
        assert result["node_count"] == len(expected_nodes)
        assert result["edge_count"] == len(expected_edges)
        assert isinstance(result["mermaid_graph"], str)
        assert isinstance(result["circular_deps"], list)

    @pytest.mark.asyncio
    async def test_include_weights(self, analyzed_project: tuple[dict, Path]):
        """include_weights=True produces weight annotations in Mermaid output."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_dependency_graph(
                scope="project", include_weights=True
            )

        assert result["status"] == "success"
        # If there are edges, the mermaid graph should contain weight annotations
        if result["edge_count"] > 0:
            assert "w=" in result["mermaid_graph"]

    @pytest.mark.asyncio
    async def test_cone_scope_missing_target_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """scope='cone' without a target raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="target.*required"):
                await get_dependency_graph(scope="cone", target=None)

    @pytest.mark.asyncio
    async def test_file_scope_nonexistent_file_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """scope='file' with a non-existent file raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="not found in dependency graph"):
                await get_dependency_graph(scope="file", target="no_such_file.py")

    @pytest.mark.asyncio
    async def test_no_project_raises_tool_error(self):
        """When no project exists, raises ToolError."""
        with patch("src.server_helpers.find_latest_project_dir", return_value=None):
            with pytest.raises(ToolError, match="No project found"):
                await get_dependency_graph()

    @pytest.mark.asyncio
    async def test_circular_deps_field_present(
        self, analyzed_project: tuple[dict, Path]
    ):
        """The response always includes a circular_deps field."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_dependency_graph(scope="project")

        assert "circular_deps" in result
        assert isinstance(result["circular_deps"], list)


# ---------------------------------------------------------------------------
# Tool 5: get_progress
# ---------------------------------------------------------------------------


class TestGetProgress:
    @pytest.mark.asyncio
    async def test_initial_progress(self, analyzed_project: tuple[dict, Path]):
        """After analysis, all tasks are pending and progress is 0%."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_progress()

        assert result["status"] == "success"
        tasks = result["tasks"]
        assert tasks["pending"] == tasks["total"]
        assert tasks["complete"] == 0
        assert tasks["progress_percent"] == 0.0
        assert "project_id" in result
        assert isinstance(result["next_pending_tasks"], list)

    @pytest.mark.asyncio
    async def test_documentation_metadata(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Progress response includes documentation metadata."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_progress()

        doc = result["documentation"]
        assert doc["index_written"] is False
        assert doc["details_written"] == 0
        assert doc["snippets_written"] == 0
        assert doc["source_file_coverage_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_no_project_raises_tool_error(self):
        """When no project exists, raises ToolError."""
        with patch("src.server_helpers.find_latest_project_dir", return_value=None):
            with pytest.raises(ToolError, match="No project found"):
                await get_progress()


# ---------------------------------------------------------------------------
# Tool 6: get_file_tokens
# ---------------------------------------------------------------------------


class TestGetFileTokens:
    @pytest.mark.asyncio
    async def test_all_files(self, analyzed_project: tuple[dict, Path]):
        """No arguments returns token summary with top files."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_file_tokens()

        assert result["status"] == "success"
        assert result["file_count"] == 4
        assert result["total_tokens"] > 0
        assert len(result["top_files"]) == 4
        assert result["showing"] == 4

    @pytest.mark.asyncio
    async def test_single_file(self, analyzed_project: tuple[dict, Path]):
        """Querying a specific file returns its token details."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_file_tokens(file="app.py")

        assert result["status"] == "success"
        assert result["filepath"] == "app.py"
        assert result["language"] == "python"
        assert result["estimated_tokens"] > 0
        assert result["char_count"] > 0
        assert result["line_count"] > 0

    @pytest.mark.asyncio
    async def test_module_filter(self, analyzed_project: tuple[dict, Path]):
        """Querying by module/cone ID returns only files in that cone."""
        from src.state.run_lifecycle import REQUIRED_ARTIFACTS, resolve_active_run

        _, output_dir = analyzed_project
        selected = resolve_active_run(output_dir)
        assert all(not (output_dir / name).exists() for name in REQUIRED_ARTIFACTS)

        cones_data = json.loads(
            (selected.generation_path / "03_feature_cones.json").read_text()
        )
        tokens_data = json.loads(
            (selected.generation_path / "04_file_tokens.json").read_text()
        )
        cones = cones_data.get("cones", {})
        if not cones:
            pytest.skip("No cones found")

        # Find a cone with at least one exclusive file
        cone_id = None
        for cid, cone in cones.items():
            if cone.get("exclusive_files"):
                cone_id = cid
                break
        if cone_id is None:
            pytest.skip("No cone with exclusive files")
        expected_paths = set(cones[cone_id]["exclusive_files"])
        expected_files = [
            item for item in tokens_data["files"] if item["filepath"] in expected_paths
        ]
        expected_total = sum(item["estimated_tokens"] for item in expected_files)

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await get_file_tokens(module=cone_id)

        assert result["status"] == "success"
        assert result["cone_id"] == cone_id
        assert {item["filepath"] for item in result["files"]} == expected_paths
        assert result["file_count"] == len(expected_files)
        assert result["total_tokens"] == expected_total
        assert result["max_file_tokens"] == max(
            item["estimated_tokens"] for item in expected_files
        )
        assert result["avg_tokens_per_file"] == expected_total / len(expected_files)
        assert isinstance(result["files"], list)

    @pytest.mark.asyncio
    async def test_file_not_found_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a non-existent file raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="File not found"):
                await get_file_tokens(file="nonexistent.py")

    @pytest.mark.asyncio
    async def test_module_not_found_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Querying a non-existent module raises ToolError."""
        _, output_dir = analyzed_project
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="Module/cone.*not found"):
                await get_file_tokens(module="nonexistent_cone_xyz")

    @pytest.mark.asyncio
    async def test_no_project_raises_tool_error(self):
        """When no project exists, raises ToolError."""
        with patch("src.server_helpers.find_latest_project_dir", return_value=None):
            with pytest.raises(ToolError, match="No project found"):
                await get_file_tokens()


# ---------------------------------------------------------------------------
# Tool 7: submit_analysis
# ---------------------------------------------------------------------------


class TestSubmitAnalysis:
    @pytest.mark.asyncio
    async def test_submit_updates_task_status(
        self, analyzed_project: tuple[dict, Path], tmp_path: Path
    ):
        """Submitting updates selected V3 while preserving the V2 anchor."""
        _, output_dir = analyzed_project

        # Read state to find a pending task
        state = json.loads((output_dir / "state.json").read_text())
        tasks = state.get("tasks", {})
        if not tasks:
            pytest.skip("No tasks in state")
        task_id = next(iter(tasks))

        # Create dummy output files that submit_analysis will verify
        detail_file = tmp_path / "docs" / "DETAIL.md"
        snippet_file = tmp_path / "docs" / "SNIPPET.md"
        detail_file.parent.mkdir(parents=True, exist_ok=True)
        detail_file.write_text("# Detail\nSome analysis content here.\n", encoding="utf-8")
        snippet_file.write_text("# Snippet\nSome snippet content.\n", encoding="utf-8")

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            result = await submit_analysis(
                task_id=task_id,
                detail_paths=[str(detail_file)],
                snippet_paths=[str(snippet_file)],
                tokens_used=500,
                source_files_covered=["app.py", "utils.py"],
            )

        assert result["status"] == "success"
        assert result["task_id"] == task_id
        assert result["progress_percent"] > 0.0

        # The root V2 lineage anchor is immutable; selected V3 owns current truth.
        updated_state = json.loads((output_dir / "state.json").read_text())
        assert updated_state == state
        current = resolve_active_run(output_dir).snapshot
        current_task = next(
            task for task in current.legacy_submission.tasks if task.task_id == task_id
        )
        assert current_task.status == "complete"

    @pytest.mark.asyncio
    async def test_submit_appends_end_marker(
        self, analyzed_project: tuple[dict, Path], tmp_path: Path
    ):
        """submit_analysis appends an end marker if not already present."""
        _, output_dir = analyzed_project

        state = json.loads((output_dir / "state.json").read_text())
        tasks = state.get("tasks", {})
        if not tasks:
            pytest.skip("No tasks in state")
        task_id = next(iter(tasks))

        detail_file = tmp_path / "docs" / "DETAIL_marker.md"
        detail_file.parent.mkdir(parents=True, exist_ok=True)
        detail_file.write_text("# Detail\nContent without end marker.\n", encoding="utf-8")

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            await submit_analysis(
                task_id=task_id,
                detail_paths=[str(detail_file)],
                snippet_paths=[],
                tokens_used=100,
            )

        content = detail_file.read_text(encoding="utf-8")
        assert "<!-- codebase-explorer: end -->" in content

    @pytest.mark.asyncio
    async def test_submit_does_not_duplicate_end_marker(
        self, analyzed_project: tuple[dict, Path], tmp_path: Path
    ):
        """If the end marker is already present, it should not be duplicated."""
        _, output_dir = analyzed_project

        state = json.loads((output_dir / "state.json").read_text())
        tasks = state.get("tasks", {})
        if not tasks:
            pytest.skip("No tasks in state")
        task_id = next(iter(tasks))

        content_with_marker = "# Detail\nContent.\n<!-- codebase-explorer: end -->\n"
        detail_file = tmp_path / "docs" / "DETAIL_dup.md"
        detail_file.parent.mkdir(parents=True, exist_ok=True)
        detail_file.write_text(content_with_marker, encoding="utf-8")

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            await submit_analysis(
                task_id=task_id,
                detail_paths=[str(detail_file)],
                snippet_paths=[],
                tokens_used=100,
            )

        final_content = detail_file.read_text(encoding="utf-8")
        marker_count = final_content.count("<!-- codebase-explorer: end -->")
        assert marker_count == 1

    @pytest.mark.asyncio
    async def test_submit_missing_file_raises_tool_error(
        self, analyzed_project: tuple[dict, Path]
    ):
        """Submitting a non-existent output file path raises ToolError."""
        _, output_dir = analyzed_project

        state = json.loads((output_dir / "state.json").read_text())
        tasks = state.get("tasks", {})
        if not tasks:
            pytest.skip("No tasks in state")
        task_id = next(iter(tasks))

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            with pytest.raises(ToolError, match="Path traversal rejected"):
                await submit_analysis(
                    task_id=task_id,
                    detail_paths=["/nonexistent/path/DETAIL.md"],
                    snippet_paths=[],
                    tokens_used=100,
                )

    @pytest.mark.asyncio
    async def test_submit_updates_documentation_metrics(
        self, analyzed_project: tuple[dict, Path], tmp_path: Path
    ):
        """submit_analysis increments documentation counters and coverage."""
        _, output_dir = analyzed_project

        state = json.loads((output_dir / "state.json").read_text())
        tasks = state.get("tasks", {})
        if not tasks:
            pytest.skip("No tasks in state")
        task_id = next(iter(tasks))

        detail_file = tmp_path / "docs" / "DETAIL_metrics.md"
        snippet_file = tmp_path / "docs" / "SNIPPET_metrics.md"
        detail_file.parent.mkdir(parents=True, exist_ok=True)
        detail_file.write_text("# Detail\n", encoding="utf-8")
        snippet_file.write_text("# Snippet\n", encoding="utf-8")

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            await submit_analysis(
                task_id=task_id,
                detail_paths=[str(detail_file)],
                snippet_paths=[str(snippet_file)],
                tokens_used=200,
                source_files_covered=["app.py"],
            )

        updated_state = json.loads((output_dir / "state.json").read_text())
        assert updated_state == state
        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            progress = await get_progress()
        doc = progress["documentation"]
        assert doc["details_written"] >= 1
        assert doc["snippets_written"] >= 1
        assert doc["source_file_coverage_percent"] > 0.0
        current = resolve_active_run(output_dir).snapshot
        assert "app.py" in current.legacy_submission.projection_metadata.source_files_covered

    @pytest.mark.asyncio
    async def test_no_project_raises_tool_error(self):
        """When no project exists, raises ToolError."""
        with patch("src.server_helpers.find_latest_project_dir", return_value=None):
            with pytest.raises(ToolError, match="No project found"):
                await submit_analysis(
                    task_id="fake-task",
                    detail_paths=[],
                    snippet_paths=[],
                    tokens_used=0,
                )


# ---------------------------------------------------------------------------
# End-to-end flow: analyze -> query -> submit
# ---------------------------------------------------------------------------


class TestEndToEndFlow:
    @pytest.mark.asyncio
    async def test_full_pipeline(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """Complete pipeline: analyze, query all tools, then submit."""
        output_dir = tmp_path / ".codebase-analysis"
        analysis_result = await _run_analysis(sample_project, output_dir, mock_ctx)
        assert analysis_result["status"] == "success"

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            # 1. get_structure — summary
            structure = await get_structure()
            assert structure["file_count"] == 4

            # 2. get_dependency_graph — project scope (module-level)
            dep_graph = await get_dependency_graph(scope="project")
            assert dep_graph["node_count"] >= 1

            # 3. get_progress — all pending initially
            progress = await get_progress()
            assert progress["tasks"]["complete"] == 0

            # 4. get_file_tokens — all files
            tokens = await get_file_tokens()
            assert tokens["file_count"] == 4

            # 5. submit_analysis — mark one task complete
            state = json.loads((output_dir / "state.json").read_text())
            tasks = state.get("tasks", {})
            if tasks:
                task_id = next(iter(tasks))

                detail_file = tmp_path / "docs" / "DETAIL_e2e.md"
                detail_file.parent.mkdir(parents=True, exist_ok=True)
                detail_file.write_text("# Full E2E Detail\n", encoding="utf-8")

                submit_result = await submit_analysis(
                    task_id=task_id,
                    detail_paths=[str(detail_file)],
                    snippet_paths=[],
                    tokens_used=300,
                    source_files_covered=["app.py"],
                )
                assert submit_result["status"] == "success"

                # 6. get_progress — verify one task completed
                progress_after = await get_progress()
                assert progress_after["tasks"]["complete"] >= 1
                assert progress_after["tasks"]["progress_percent"] > 0.0

    @pytest.mark.asyncio
    async def test_structure_file_query_matches_tokens(
        self, sample_project: Path, mock_ctx: MagicMock, tmp_path: Path
    ):
        """File details from get_structure and get_file_tokens are consistent."""
        output_dir = tmp_path / ".codebase-analysis"
        await _run_analysis(sample_project, output_dir, mock_ctx)

        with patch("src.server_helpers.find_latest_project_dir", return_value=output_dir):
            structure = await get_structure(file="utils.py")
            tokens = await get_file_tokens(file="utils.py")

        assert structure["filepath"] == tokens["filepath"]
        # Both should report the same line count
        assert structure["line_count"] == tokens["line_count"]
