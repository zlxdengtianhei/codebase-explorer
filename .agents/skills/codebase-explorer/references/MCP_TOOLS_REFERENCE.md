# MCP Tools Reference (V5)

> Load this file when you need full parameter specifications and return values
> for the 9 V5 MCP tools.

## Table of Contents

1. [Tool Overview](#1-tool-overview)
2. [analyze_codebase](#2-analyze_codebase)
3. [get_structure](#3-get_structure)
4. [get_modules](#4-get_modules)
5. [get_function_deps](#5-get_function_deps)
6. [doc_operation](#6-doc_operation)
7. [get_dependency_graph](#7-get_dependency_graph)
8. [get_progress](#8-get_progress)
9. [get_file_tokens](#9-get_file_tokens)
10. [submit_analysis](#10-submit_analysis)
11. [Error Reference](#11-error-reference)

---

## 1. Tool Overview

V5 has exactly **9 tools**. There is no SQLite database, no Jinja2 templates, and
no `get_feature_cones` tool (use `get_modules` instead). All state is stored as JSON
files under `.codebase-analysis/`. LLM agents write documentation directly.

| Tool | Phase | Purpose |
|------|-------|---------|
| `analyze_codebase` | 1 | Full pipeline: parse → graph → cones → 6 JSON files |
| `get_structure` | 1-4 | Query file/function/class metadata |
| `get_modules` | 2-4 | Module listing (summary or detail with file lists) |
| `get_function_deps` | 3 | Cross-file function call dependencies per file |
| `doc_operation` | 3-4 | Template/protocol info + INDEX assembly + reorganization |
| `get_dependency_graph` | 3-4 | Mermaid dependency graph (project, cone, or file scope) |
| `get_progress` | any | Check task completion status for recovery |
| `get_file_tokens` | 3 | Per-file token estimates |
| `submit_analysis` | 3-4 | Mark task complete, update state.json |

---

## 2. analyze_codebase

Full analysis pipeline entry point. Parses the codebase, builds a weighted
dependency graph, extracts feature cones via SCC + DAG analysis, estimates
tokens per file (chars / 4), and writes 6 JSON files plus state.json.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `str` | Yes | -- | Absolute path to the codebase root directory |
| `languages` | `list["python"\|"typescript"\|"javascript"] \| null` | No | `null` | Languages to analyze. null = auto-detect |
| `output_dir` | `str \| null` | No | `null` | Output directory. null = `{path}/.codebase-analysis/` |
| `force_reindex` | `bool` | No | `false` | Re-run even if output files already exist |
| `exclude_paths` | `list[str] \| null` | No | `null` | Additional directories/files to exclude (e.g. `["vendor/", "generated/"]`) |
| `include_tests` | `bool` | No | `false` | Include test directories (tests/, test/) in analysis |

**Returns:**
```json
{
  "status": "success",
  "project_id": "abc123",
  "output_dir": "/path/.codebase-analysis/",
  "files_analyzed": 127,
  "feature_cones_found": 9,
  "task_count": 15,
  "total_tokens": 45000,
  "files": {
    "01_structure": "/path/.codebase-analysis/01_structure.json",
    "02_dag": "/path/.codebase-analysis/02_dag.json",
    "03_feature_cones": "/path/.codebase-analysis/03_feature_cones.json",
    "04_file_tokens": "/path/.codebase-analysis/04_file_tokens.json",
    "05_task_manifest": "/path/.codebase-analysis/05_task_manifest.json"
  },
  "state_file": "/path/.codebase-analysis/state.json"
}
```

**Output files written to `.codebase-analysis/`:**

| File | Content |
|------|---------|
| `01_structure.json` | File list, function/class metadata |
| `02_dag.json` | Weighted dependency edges + Mermaid graph |
| `03_feature_cones.json` | Feature cone groupings + layer structure + cohesion_score |
| `04_file_tokens.json` | Per-file token estimates (chars / 4) |
| `05_task_manifest.json` | Agent task queue |
| `06_function_deps.json` | Cross-file function call relationships |
| `state.json` | Task status + coverage metrics |

**Notes:** Idempotent unless `force_reindex=true`. Must be called before any other tool.
Token estimation: characters / 4 (uniform for all languages). Test directories are excluded
by default; set `include_tests=true` to include them.

**Example:**
```
analyze_codebase(path="/home/user/flask", languages=["python"], force_reindex=true)
```

---

## 3. get_structure

Query code structure metadata from `01_structure.json`. Three mutually exclusive
query modes: module, file, or function.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module` | `str \| null` | No | `null` | Module/cone name — returns all files in that module |
| `file` | `str \| null` | No | `null` | File path — returns detailed file info |
| `function` | `str \| null` | No | `null` | Function name — returns signature + dependencies |

Pass at most one parameter at a time. Passing none returns project summary.

**Returns (project summary — no params):**
```json
{
  "status": "success",
  "data": {
    "project_id": "abc123",
    "file_count": 42,
    "function_count": 156,
    "class_count": 28,
    "languages": ["python"],
    "cone_count": 9
  }
}
```

**Precondition:** `analyze_codebase` must have been called.

---

## 4. get_modules

Query functional modules. Two modes:
- **Summary** (no `module_id`): Returns compact list with metadata only (< 3KB). Use first to discover module IDs.
- **Detail** (with `module_id`): Returns single module with full file list and token counts.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_id` | `str \| null` | No | `null` | Module ID for detail view. null = summary of all modules |

**Returns (summary — no module_id):**
```json
{
  "status": "success",
  "total_modules": 9,
  "total_files": 42,
  "total_tokens": 45000,
  "grouping": {
    "strategy_used": "feature_cone",
    "available_strategies": ["feature_cone", "louvain"]
  },
  "token_budget": {
    "total_project_tokens": 45000,
    "budget_limit": 100000,
    "within_budget": true
  },
  "inter_module_deps": {
    "total_edges": 12,
    "modules_with_deps": 7
  },
  "modules": [
    {
      "module_id": "routing",
      "name": "Routing",
      "file_count": 3,
      "token_count": 7200,
      "layer": 1,
      "depends_on": ["globals", "exceptions"],
      "directory_hint": "flask/"
    }
  ],
  "infrastructure": {
    "file_count": 2,
    "token_count": 1200
  }
}
```

**Returns (detail — specific module_id):**
```json
{
  "status": "success",
  "module_id": "routing",
  "name": "Routing",
  "layer": 1,
  "depends_on": ["globals", "exceptions"],
  "files": [
    {"filepath": "flask/routing.py", "token_count": 2800},
    {"filepath": "flask/map.py", "token_count": 2100}
  ],
  "internal_layers": [["flask/map.py"], ["flask/routing.py"]],
  "token_count": 7200
}
```

**Precondition:** `analyze_codebase` must have been called.

---

## 5. get_function_deps

Get cross-file function-level dependencies for a specific file. Only cross-file
calls are returned; same-file internal calls are excluded.

Use during Phase 3 DETAIL generation to populate the 依赖关系 section.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | `str` | Yes | -- | File path to query function dependencies for |
| `module_id` | `str \| null` | No | `null` | Optional: limit results to within-module dependencies only |

**Returns:**
```json
{
  "status": "success",
  "file": "flask/routing.py",
  "dependencies": [
    {
      "source_function": "add_url_rule",
      "calls": [
        {
          "target_file": "flask/globals.py",
          "target_function": "current_app"
        }
      ]
    }
  ]
}
```

If no cross-file dependencies are found:
```json
{
  "status": "success",
  "file": "flask/globals.py",
  "dependencies": [],
  "message": "No cross-file function dependencies found for this file"
}
```

**Precondition:** `analyze_codebase` must have been called. Reads from `06_function_deps.json`.
If that file is missing, re-run `analyze_codebase(force_reindex=true)`.

---

## 6. doc_operation

Documentation operations for DETAIL/INDEX generation and Phase 4 reorganization.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `operation` | `str` | Yes | -- | One of: `get_template`, `get_protocol`, `move_detail`, `merge_modules`, `split_module`, `update_index`, `reorder_modules` |
| `source_module` | `str \| null` | No | `null` | Source module ID (for `move_detail`, `merge_modules`, `split_module`) |
| `target_module` | `str \| null` | No | `null` | Target module ID (for `move_detail`, `merge_modules`) |
| `file_path` | `str \| null` | No | `null` | File path to move (for `move_detail`) |
| `new_order` | `list[str] \| null` | No | `null` | Ordered list of module IDs (for `reorder_modules`) |

### Operation: get_template

Returns YAML front matter format and HTML marker format for DETAIL and INDEX documents.

```
doc_operation(operation="get_template")
```

Returns the required YAML front matter fields, HTML marker patterns
(`<!-- module:{id} -->`, `<!-- file:{path} -->`, `<!-- index-fragment:{id} -->`),
and the three sections each file block must contain.

### Operation: get_protocol

Returns the three-step DETAIL protocol and INDEX assembly rules.

```
doc_operation(operation="get_protocol")
```

Returns the three-step per-file protocol:
1. Step 1 — Read source file and write function/class descriptions
2. Step 2 — Call `get_function_deps` and write cross-file dependency relationships
3. Step 3 — Write `<!-- index-fragment:{module_id} -->` block (after all files done)

Also returns the token budget accumulation rule and INDEX assembly method
(direct concatenation of all index-fragment blocks).

### Operation: update_index

Assembles INDEX.md from `<!-- index-fragment -->` blocks in all DETAIL files.
Also builds a module-level Mermaid graph from `02_dag.json`.

```
doc_operation(operation="update_index")
```

Returns:
```json
{
  "status": "success",
  "operation": "update_index",
  "index_path": "/path/.codebase-docs/INDEX.md",
  "module_count": 9,
  "message": "INDEX.md regenerated with 9 sections."
}
```

### Operation: move_detail

Move a DETAIL file from one module directory to another.

```
doc_operation(
  operation="move_detail",
  source_module="old_module_id",
  target_module="new_module_id",
  file_path="DETAIL.md"
)
```

Requires: `source_module`, `target_module`, `file_path`

### Operation: merge_modules

Move all files from `source_module` directory into `target_module` directory.

```
doc_operation(
  operation="merge_modules",
  source_module="module_a",
  target_module="module_b"
)
```

Requires: `source_module`, `target_module`

### Operation: split_module

List all files in a module directory (to inspect before moving files out).
This is a read-only listing operation — use `move_detail` to actually reassign files.

```
doc_operation(operation="split_module", source_module="large_module")
```

Returns list of files in the module. Use `move_detail` after inspection.

### Operation: reorder_modules

Set the display order for modules in the next INDEX assembly.

```
doc_operation(operation="reorder_modules", new_order=["module_a", "module_b", "module_c"])
```

Saves order to `doc-index.json`. Call `update_index` afterward to apply.

**Precondition for editing operations:** `analyze_codebase` must have been called.
Read-only operations (`get_template`, `get_protocol`) work without a project.

---

## 7. get_dependency_graph

Generate a Mermaid dependency graph from `02_dag.json`.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scope` | `"project"\|"cone"\|"module"\|"file"` | No | `"project"` | Graph scope (`cone` and `module` are aliases) |
| `target` | `str \| null` | No | `null` | Cone ID or file path (required when scope is `cone`/`module`/`file`) |
| `include_weights` | `bool` | No | `false` | Include edge weight labels |
| `hops` | `int` | No | `1` | N-hop neighbors for scope=file |

**Returns:**
```json
{
  "status": "success",
  "nodes": ["routing", "globals", "app"],
  "edges": [
    {"source": "app", "target": "routing", "weight": 5}
  ],
  "circular_deps": [],
  "mermaid_graph": "graph TD\n  app --> routing\n  routing --> globals"
}
```

**Scope behavior:**
- `scope="project"` — Module-level aggregated graph (all modules as nodes)
- `scope="cone"` or `scope="module"` — File-level graph within a specific module (`target` = module ID)
- `scope="file"` — N-hop neighbor subgraph centered on a single file (`target` = file path)

**Precondition:** `analyze_codebase` must have been called.

---

## 8. get_progress

Query task completion status from `state.json`. Use for recovery and resume.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = most recent `analyze_codebase` result |

**Returns:**
```json
{
  "status": "success",
  "project_id": "abc123",
  "tasks": {
    "total": 15,
    "pending": 3,
    "in_progress": 2,
    "complete": 10,
    "failed": 0,
    "progress_percent": 66.67
  },
  "documentation": {
    "output_dir": "/path/.codebase-docs/",
    "index_written": false,
    "details_written": 10,
    "snippets_written": 0,
    "total_planned": 15,
    "source_file_coverage_percent": 78.5
  },
  "next_pending_tasks": ["task_routing", "task_sessions"]
}
```

**Precondition:** `analyze_codebase` must have been called.

---

## 9. get_file_tokens

Query per-file token estimates from `04_file_tokens.json`.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file` | `str \| null` | No | `null` | File path — returns token info for that file |
| `module` | `str \| null` | No | `null` | Module/cone ID — returns all files in module + aggregate stats |

Pass at most one parameter. Passing none returns all files.

**Returns (module mode):**
```json
{
  "status": "success",
  "cone_id": "routing",
  "file_count": 3,
  "total_tokens": 7200,
  "avg_tokens_per_file": 2400.0,
  "max_file_tokens": 2800,
  "files": [
    {
      "filepath": "flask/routing.py",
      "language": "python",
      "char_count": 11200,
      "line_count": 382,
      "estimated_tokens": 2800,
      "method": "chars"
    }
  ]
}
```

**Token estimation:** `estimated_tokens = char_count / 4` (uniform for all languages).

**Precondition:** `analyze_codebase` must have been called.

---

## 10. submit_analysis

Task completion callback. Called by DETAIL agents after writing documentation files.
Atomically updates `state.json` with completion status and coverage metrics.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | `str` | Yes | -- | Task ID from `05_task_manifest.json` |
| `detail_paths` | `list[str]` | Yes | -- | Absolute paths to written DETAIL files |
| `snippet_paths` | `list[str]` | Yes | -- | Absolute paths to written SNIPPET files (pass `[]` if none) |
| `tokens_used` | `int` | Yes | -- | Agent self-reported token consumption |
| `source_files_covered` | `list[str] \| null` | No | `null` | Source files documented in this task |
| `project_id` | `str \| null` | No | `null` | Project ID. null = most recent `analyze_codebase` result |

**Returns:**
```json
{
  "status": "success",
  "task_id": "task_routing",
  "tasks_remaining": 5,
  "progress_percent": 66.67,
  "source_file_coverage_percent": 78.5
}
```

**Notes:**
- All paths in `detail_paths` and `snippet_paths` must exist and be within the project directory
- MCP automatically appends `<!-- codebase-explorer: end -->` marker if missing
- For Phase 3 tasks: pass `snippet_paths=[]` (V5 does not use SNIPPET files)

**Example:**
```
submit_analysis(
  task_id="task_routing",
  detail_paths=["/path/.codebase-docs/routing/DETAIL.md"],
  snippet_paths=[],
  tokens_used=3200,
  source_files_covered=["flask/routing.py", "flask/map.py"]
)
```

---

## 11. Error Reference

| Error | Tool(s) | Description | Recovery |
|-------|---------|-------------|----------|
| `PROJECT_NOT_FOUND` | All except `analyze_codebase` | No analysis output exists | Call `analyze_codebase` first |
| `MODULE_NOT_FOUND` | `get_modules`, `get_file_tokens` | Invalid module ID | Call `get_modules()` to list valid IDs |
| `FILE_NOT_FOUND` | `get_structure`, `get_file_tokens`, `get_function_deps` | File path not in index | Verify path is relative to project root |
| `INVALID_PATH` | `analyze_codebase` | Path does not exist or is not a directory | Provide valid absolute path |
| `TASK_NOT_FOUND` | `submit_analysis` | task_id not in manifest | Read `05_task_manifest.json` for valid IDs |
| `TASK_ALREADY_COMPLETE` | `submit_analysis` | Task was already submitted | Idempotent — safe to ignore |
| `UNSUPPORTED_LANGUAGE` | `analyze_codebase` | No supported files found | Try with explicit `languages` param |
| `TIMEOUT` | `analyze_codebase` | Parsing exceeded time limit | Index a smaller subdirectory |
| `FUNCTION_DEPS_NOT_FOUND` | `get_function_deps` | `06_function_deps.json` missing | Re-run `analyze_codebase(force_reindex=true)` |
| `PATH_TRAVERSAL_REJECTED` | `submit_analysis` | File is outside project directory | Use paths within project root only |
