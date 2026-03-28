# Server Module — OVERVIEW

> `src/server.py` (940 lines) + `src/server_helpers.py` (421 lines)

FastMCP protocol entry point. Registers 7 MCP tools for AI Agent consumption. All query tools are read-only; `analyze_codebase` and `submit_analysis` mutate state.

## Architecture

```mermaid
graph TB
    MCP["FastMCP Server<br/>lifespan → CodebaseParser singleton"]

    subgraph Tools["7 MCP Tools"]
        T1["analyze_codebase (write)"]
        T2["get_structure (read)"]
        T3["get_feature_cones (read)"]
        T4["get_dependency_graph (read)"]
        T5["get_progress (read)"]
        T6["get_file_tokens (read)"]
        T7["submit_analysis (write)"]
    end

    SH["server_helpers.py<br/>Pure functions, no MCP deps"]

    MCP --> Tools
    Tools --> SH

    T1 --> parser["parser/"]
    T1 --> graph["graph/"]
    T1 --> doc["doc/"]
    T1 --> budget["budget/"]
    T7 --> state["state/"]
```

## Server Initialization

```python
@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[dict]:
    yield {"parser": CodebaseParser()}

mcp = FastMCP("codebase-explorer", lifespan=_lifespan)
```

The `CodebaseParser` is instantiated once and shared across all tool invocations via the FastMCP lifespan context pattern.

## MCP Tool Registration Pattern

Tools are registered with `@mcp.tool()` using `Annotated[type, Field(description=...)]` for MCP schema generation. Protocol hints via `annotations`:
- `readOnlyHint: True` — tool does not modify state
- `readOnlyHint: False` — tool writes state
- `idempotentHint: True` — repeated calls are safe

## Tool Signatures

### 1. analyze_codebase

```python
async def analyze_codebase(
    path: Annotated[str, Field(description="Absolute path to the codebase root")],
    languages: Annotated[list[Literal["python", "typescript", "javascript"]] | None, Field(...)] = None,
    output_dir: Annotated[str | None, Field(...)] = None,
    force_reindex: Annotated[bool, Field(...)] = False,
    ctx: Context = None,
) -> dict
```

Runs the full deterministic analysis pipeline:
`parse → weighted DAG → feature cones → SCC condensation → token estimation → task manifest → 5 JSON files + state.json`

Includes Louvain fallback if >70% of cones are single-file (degraded quality signal).

### 2. get_structure

```python
async def get_structure(
    module: Annotated[str | None, Field(description="Module/cone name")] = None,
    file: Annotated[str | None, Field(description="File path")] = None,
    function: Annotated[str | None, Field(description="Function name")] = None,
) -> dict
```

Queries `01_structure.json`. Four mutually exclusive modes: summary (no params), module, file, or function lookup.

### 3. get_feature_cones

```python
async def get_feature_cones(
    cone_id: Annotated[str | None, Field(description="Cone ID. None = all cones.")] = None,
) -> dict
```

Queries `03_feature_cones.json`. With `cone_id`, returns full detail including internal topological layers (`compute_cone_layers`) and inter-cone dependencies (`compute_depends_on_cones`).

### 4. get_dependency_graph

```python
async def get_dependency_graph(
    scope: Annotated[Literal["project", "cone", "file"], Field(...)] = "project",
    target: Annotated[str | None, Field(...)] = None,
    include_weights: Annotated[bool, Field(...)] = False,
    hops: Annotated[int, Field(...)] = 1,
) -> dict
```

Generates Mermaid flowchart from `02_dag.json`. Three scopes: `project` (full graph), `cone` (cone's exclusive + shared files), `file` (N-hop neighbors, max 5). Detects circular dependencies via SCC.

### 5. get_progress

```python
async def get_progress(
    project_id: Annotated[str | None, Field(...)] = None,
) -> dict
```

Reads `state.json`, returns task completion counts (pending/in_progress/complete/failed) and documentation coverage metrics.

### 6. get_file_tokens

```python
async def get_file_tokens(
    file: Annotated[str | None, Field(...)] = None,
    module: Annotated[str | None, Field(...)] = None,
) -> dict
```

Queries `04_file_tokens.json`. Three modes: all files, single file, or all files in a cone/module.

### 7. submit_analysis

```python
async def submit_analysis(
    task_id: Annotated[str, Field(description="Task ID from task_manifest")],
    detail_paths: Annotated[list[str], Field(...)],
    snippet_paths: Annotated[list[str], Field(...)],
    tokens_used: Annotated[int, Field(...)],
    source_files_covered: Annotated[list[str] | None, Field(...)] = None,
    project_id: Annotated[str | None, Field(...)] = None,
) -> dict
```

Called by DETAIL Agent after writing documentation. Validates file paths exist and are within project directory (path traversal guard), appends end marker, atomically updates `state.json`, recalculates coverage percentage.

## server_helpers.py — Pure Function Reference

All functions are stateless, have zero FastMCP/Context dependency, and are independently testable.

| Function | Signature | Purpose |
|----------|-----------|---------|
| `now_iso` | `() → str` | UTC ISO 8601 timestamp |
| `project_id_from_path` | `(path: str) → str` | SHA-256 first 12 hex chars, deterministic project ID |
| `find_latest_project_dir` | `() → Path \| None` | Search CWD/HOME for newest `.codebase-analysis/` (depth ≤ 4) |
| `resolve_output_dir` | `(path: str, output_dir: str \| None) → Path` | Resolve absolute output path |
| `validate_json_files_exist` | `(output_dir: Path) → bool` | Check all 5 JSON files present (cache hit detection) |
| `build_graph_from_dag` | `(nodes: list[str], edges: list[dict]) → nx.DiGraph` | Deserialize 02_dag.json → graph |
| `render_mermaid` | `(graph: nx.DiGraph, *, include_weights: bool = False) → str` | nx.DiGraph → Mermaid `graph TD` string |
| `is_utility_cone` | `(cone_name: str, *, layer: int = 0, total_cones: int = 1, all_cones: dict \| None = None) → bool` | 3-heuristic utility classification (name / layer / fan-out) |
| `compute_cone_layers` | `(cone_files: list[str], dag_nodes: list[str], dag_edges: list[dict]) → list[list[str]]` | Kahn-style BFS topological layering within a cone |
| `compute_depends_on_cones` | `(cone_id: str, cone_shared_deps: list[str], all_cones: dict) → list[str]` | Intersection-based inter-cone dependency computation |
| `write_analysis_outputs` | `(*, output_path, project_id, resolved_path, snapshot, weighted_result, graph, cones, infrastructure, cone_dicts, file_tokens, file_details, task_manifest) → dict` | Serialize all results to 6 JSON files |

## Internal Dependencies

```python
# server.py imports:
from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import build_task_manifest
from src.graph.feature_cone import extract_feature_cones, FeatureCone
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.parser.codebase import CodebaseParser, CodebaseParseError
from src.server_helpers import (build_graph_from_dag, compute_cone_layers,
    compute_depends_on_cones, find_latest_project_dir, is_utility_cone,
    now_iso, project_id_from_path, render_mermaid, resolve_output_dir,
    validate_json_files_exist, write_analysis_outputs)
from src.state.json_store import atomic_write_state, read_state, update_task_status
from src.graph.grouper import group_modules  # conditional fallback

# server_helpers.py imports:
from src.state.json_store import atomic_write_state  # local import in write_analysis_outputs
```
