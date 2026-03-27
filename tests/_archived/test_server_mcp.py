"""MCP transport layer integration tests for codebase-explorer server.

Tests the 7 MCP tools via the FastMCP memory transport, validating that
the server tools work end-to-end through a real MCP client/server session.

Uses `create_connected_server_and_client_session` from the `mcp` library
to spin up an in-memory MCP server and client pair -- no network required.

Each test creates its own client session inside the test body to avoid
anyio cancel-scope task-affinity issues with pytest_asyncio fixtures.

The ``analyze_codebase`` tool writes output to a temporary directory
under ``Path.cwd()`` so that the read-only query tools (which use
``_find_latest_project_dir()`` to scan cwd) can find it.

Usage:
    uv run pytest tests/test_server_mcp.py -v
"""
from __future__ import annotations

import json
import shutil
import sys
import textwrap
import uuid
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.server import mcp as mcp_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_project(tmp_path: Path) -> Path:
    """Create a small multi-file Python project for analysis.

    Structure:
        app.py      - imports models and utils
        models.py   - imports utils
        utils.py    - no imports (leaf dependency)
        config.py   - standalone config
    """
    (tmp_path / "app.py").write_text(
        textwrap.dedent("""\
            import models
            import utils

            class Application:
                def __init__(self):
                    self.config = {}

                def run(self):
                    data = models.get_data()
                    return utils.format_output(data)

            def main():
                app = Application()
                app.run()
        """),
        encoding="utf-8",
    )

    (tmp_path / "models.py").write_text(
        textwrap.dedent("""\
            import utils

            class User:
                def __init__(self, name):
                    self.name = name

            class Post:
                def __init__(self, title, author):
                    self.title = title
                    self.author = author

            def get_data():
                return utils.load_json("data.json")

            def validate(data):
                if not data:
                    raise ValueError("Empty data")
                return True
        """),
        encoding="utf-8",
    )

    (tmp_path / "utils.py").write_text(
        textwrap.dedent("""\
            import json

            def format_output(data):
                return str(data)

            def load_json(path):
                with open(path) as f:
                    return json.load(f)

            def sanitize(text):
                return text.strip()
        """),
        encoding="utf-8",
    )

    (tmp_path / "config.py").write_text(
        textwrap.dedent("""\
            DATABASE_URL = "sqlite:///app.db"
            DEBUG = True
            SECRET_KEY = "dev-key"

            def get_config():
                return {
                    "db": DATABASE_URL,
                    "debug": DEBUG,
                }
        """),
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def analysis_output_dir():
    """Create a temporary analysis output directory under cwd.

    The read-only MCP tools use ``_find_latest_project_dir()`` which scans
    ``Path.cwd()`` for ``.codebase-analysis`` directories, choosing the
    most recently modified one.  By placing output under cwd with a unique
    name, we guarantee the test's data is found.

    Yields the output directory path and cleans up afterward.
    """
    unique = f".test-mcp-analysis-{uuid.uuid4().hex[:8]}"
    output = Path.cwd() / unique / ".codebase-analysis"
    output.mkdir(parents=True, exist_ok=True)
    yield output
    # Cleanup
    shutil.rmtree(output.parent, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_tool_result(result) -> dict:
    """Extract and parse JSON from an MCP call_tool result."""
    assert result.content, "Tool returned empty content"
    text = result.content[0].text
    return json.loads(text)


async def _analyze_project(
    client,
    project_path: Path,
    output_dir: Path,
) -> dict:
    """Run analyze_codebase via the MCP client and return parsed result."""
    result = await client.call_tool(
        "analyze_codebase",
        {
            "path": str(project_path),
            "output_dir": str(output_dir),
            "force_reindex": True,
        },
    )
    return _parse_tool_result(result)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_codebase_via_mcp(test_project, analysis_output_dir):
    """Call analyze_codebase tool and verify it returns valid analysis results.

    Validates:
    - Response status is 'success'
    - Project ID is generated
    - Output directory is set
    - Correct number of files analyzed
    - Feature cones are found
    - All 5 JSON output files are referenced
    - State file is created
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        data = await _analyze_project(client, test_project, analysis_output_dir)

        # Basic response shape
        assert data["status"] == "success"
        assert data["project_id"], "project_id must be non-empty"
        assert data["output_dir"], "output_dir must be non-empty"

        # File count: app.py, models.py, utils.py, config.py
        assert data["files_analyzed"] == 4

        # Feature cones should be found (at least 1)
        assert data["feature_cones_found"] >= 1

        # Task count should be positive
        assert data["task_count"] >= 1

        # Total tokens should be positive (chars / 3.5 per file)
        assert data["total_tokens"] > 0

        # All 5 JSON files should be referenced
        files = data["files"]
        expected_keys = [
            "01_structure",
            "02_dag",
            "03_feature_cones",
            "04_file_tokens",
            "05_task_manifest",
        ]
        for key in expected_keys:
            assert key in files, f"Missing output file key: {key}"
            assert Path(files[key]).exists(), f"Output file does not exist: {files[key]}"

        # State file should exist
        assert "state_file" in data
        assert Path(data["state_file"]).exists(), "state.json not found"


@pytest.mark.asyncio
async def test_get_feature_cones_via_mcp(test_project, analysis_output_dir):
    """Call get_feature_cones and verify the response contains expected fields.

    First runs analyze_codebase to generate data, then queries feature cones.

    Validates:
    - Response status is 'success'
    - total_cones is positive
    - Each cone has: cone_id, is_utility, file_count, layer
    - Querying a specific cone returns: layers, depends_on_cones, shared_deps
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project first
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get all feature cones
        result = await client.call_tool("get_feature_cones", {})
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert data["total_cones"] >= 1

        cones = data["cones"]
        assert len(cones) >= 1

        # Validate each cone has required fields
        for cone in cones:
            assert "cone_id" in cone, "cone must have cone_id"
            assert "is_utility" in cone, "cone must have is_utility"
            assert "file_count" in cone, "cone must have file_count"
            assert "layer" in cone, "cone must have layer"
            assert isinstance(cone["is_utility"], bool)
            assert isinstance(cone["file_count"], int)
            assert isinstance(cone["layer"], int)

        # Step 3: Query a specific cone by ID
        first_cone_id = cones[0]["cone_id"]
        detail_result = await client.call_tool(
            "get_feature_cones",
            {"cone_id": first_cone_id},
        )
        detail = _parse_tool_result(detail_result)

        assert detail["status"] == "success"
        assert detail["cone_id"] == first_cone_id

        # Specific-cone response must include these additional fields
        assert "layers" in detail, "detail must include layers"
        assert "depends_on_cones" in detail, "detail must include depends_on_cones"
        assert "shared_deps" in detail, "detail must include shared_deps"
        assert "files" in detail, "detail must include files"
        assert "is_utility" in detail

        # layers should be a list of lists (layer groups)
        assert isinstance(detail["layers"], list)
        # depends_on_cones should be a list of cone IDs
        assert isinstance(detail["depends_on_cones"], list)


@pytest.mark.asyncio
async def test_get_dependency_graph_via_mcp(test_project, analysis_output_dir):
    """Call get_dependency_graph and verify the response structure.

    First runs analyze_codebase, then queries the dependency graph at
    project scope.

    Validates:
    - Response status is 'success'
    - scope is 'project'
    - mermaid_graph is a valid Mermaid string
    - nodes list contains the test project's files
    - edges list has source/target/weight structure
    - node_count and edge_count are consistent
    - circular_deps is present (may be empty)
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project first
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get project-scope dependency graph
        result = await client.call_tool(
            "get_dependency_graph",
            {"scope": "project"},
        )
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert data["scope"] == "project"

        # Mermaid graph should start with "graph TD"
        mermaid = data["mermaid_graph"]
        assert mermaid.startswith("graph TD"), (
            f"Mermaid graph should start with 'graph TD', got: {mermaid[:50]}"
        )

        # Nodes should include our test files
        nodes = data["nodes"]
        assert len(nodes) >= 2, "Should have at least 2 nodes in the graph"
        assert data["node_count"] == len(nodes)

        # Edges should have proper structure
        edges = data["edges"]
        assert data["edge_count"] == len(edges)
        for edge in edges:
            assert "source" in edge, "edge must have source"
            assert "target" in edge, "edge must have target"
            assert "weight" in edge, "edge must have weight"
            assert isinstance(edge["weight"], (int, float))

        # circular_deps should be present (list, possibly empty)
        assert "circular_deps" in data
        assert isinstance(data["circular_deps"], list)


@pytest.mark.asyncio
async def test_get_dependency_graph_file_scope_via_mcp(
    test_project,
    analysis_output_dir,
):
    """Call get_dependency_graph with scope='file' and verify subgraph extraction.

    Validates that file-scoped queries return a neighborhood subgraph
    centered on the target file.
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get the project-level graph to find a valid file node
        project_result = await client.call_tool(
            "get_dependency_graph",
            {"scope": "project"},
        )
        project_data = _parse_tool_result(project_result)
        nodes = project_data["nodes"]

        # Pick a node that has edges (app.py should import others)
        target_node = None
        for node in nodes:
            if "app" in node.lower():
                target_node = node
                break
        if target_node is None and nodes:
            target_node = nodes[0]

        assert target_node is not None, "No nodes found in dependency graph"

        # Step 3: Query file-scope dependency graph
        result = await client.call_tool(
            "get_dependency_graph",
            {"scope": "file", "target": target_node, "hops": 1},
        )
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert data["scope"] == "file"
        assert data["target"] == target_node
        assert target_node in data["nodes"], (
            "Target node must appear in its own subgraph"
        )
        assert data["node_count"] >= 1


@pytest.mark.asyncio
async def test_get_progress_via_mcp(test_project, analysis_output_dir):
    """Call get_progress and verify task status tracking works.

    Validates:
    - Response status is 'success'
    - tasks breakdown has total/pending/complete counts
    - documentation section is present
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get progress
        result = await client.call_tool("get_progress", {})
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert "project_id" in data
        assert "tasks" in data

        tasks = data["tasks"]
        assert "total" in tasks
        assert "pending" in tasks
        assert "complete" in tasks
        assert "progress_percent" in tasks

        # After initial analysis, all tasks should be pending
        assert tasks["total"] >= 1
        assert tasks["pending"] >= 1
        assert tasks["complete"] == 0

        # Documentation section should exist
        assert "documentation" in data
        doc = data["documentation"]
        assert "output_dir" in doc
        assert "index_written" in doc


@pytest.mark.asyncio
async def test_get_file_tokens_via_mcp(test_project, analysis_output_dir):
    """Call get_file_tokens and verify token estimates are returned.

    Validates:
    - Response contains total_tokens and file_count
    - Each file entry has filepath, estimated_tokens, char_count
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get all file tokens
        result = await client.call_tool("get_file_tokens", {})
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert data["total_tokens"] > 0
        assert data["file_count"] == 4  # 4 test files

        files = data["files"]
        assert len(files) == 4

        for f in files:
            assert "filepath" in f
            assert "estimated_tokens" in f
            assert "char_count" in f
            assert f["estimated_tokens"] > 0
            assert f["char_count"] > 0


@pytest.mark.asyncio
async def test_get_structure_summary_via_mcp(test_project, analysis_output_dir):
    """Call get_structure with no arguments to get project summary.

    Validates:
    - query_type is 'summary'
    - file_count, function_count, class_count are present
    - language_breakdown includes python
    """
    async with create_connected_server_and_client_session(mcp_server) as client:
        # Step 1: Analyze the project
        await _analyze_project(client, test_project, analysis_output_dir)

        # Step 2: Get structure summary
        result = await client.call_tool("get_structure", {})
        data = _parse_tool_result(result)

        assert data["status"] == "success"
        assert data["query_type"] == "summary"
        assert data["file_count"] == 4
        assert data["function_count"] > 0
        assert "language_breakdown" in data
        assert "python" in data["language_breakdown"]


@pytest.mark.asyncio
async def test_list_tools_via_mcp():
    """Verify that the MCP server exposes all 7 expected tools."""
    async with create_connected_server_and_client_session(mcp_server) as client:
        tools_result = await client.list_tools()
        tool_names = sorted(t.name for t in tools_result.tools)

        expected = sorted([
            "analyze_codebase",
            "get_structure",
            "get_feature_cones",
            "get_dependency_graph",
            "get_progress",
            "get_file_tokens",
            "submit_analysis",
        ])

        assert tool_names == expected, (
            f"Expected tools {expected}, got {tool_names}"
        )
