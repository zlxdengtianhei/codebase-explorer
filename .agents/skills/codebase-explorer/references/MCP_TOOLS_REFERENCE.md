# MCP Tools Reference

> Load this file when you need full parameter specifications and return values.

## Table of Contents

1. [Indexing and Analysis Tools](#1-indexing-and-analysis-tools)
2. [Budget and Chunking Tools](#2-budget-and-chunking-tools)
3. [Task Management Tools](#3-task-management-tools)
4. [Checkpoint and Cross-Reference Tools](#4-checkpoint-and-cross-reference-tools)
5. [Document Generation Tools](#5-document-generation-tools)
6. [Error Codes](#6-error-codes)

---

## 1. Indexing and Analysis Tools

### index_codebase

Parse a codebase, build dependency graph, run Louvain community detection.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | `str` | Yes | -- | Absolute path to the codebase root directory |
| `languages` | `list["python"\|"typescript"\|"javascript"] \| null` | No | `null` | Languages to analyze. null = auto-detect |

**Returns**:
```json
{
  "status": "success",
  "summary": "Indexed 42 files, 156 functions, 28 classes",
  "data": {
    "project_id": "proj_abc123",
    "file_count": 42,
    "function_count": 156,
    "class_count": 28,
    "languages": ["python"],
    "module_count": 6
  }
}
```

**Notes**: Idempotent. Timeout: 120s. Must be called before any other tool.

**Example**:
```
index_codebase(path="/home/user/flask", languages=["python"])
```

---

### get_modules

Get the list of detected modules after Louvain grouping.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = use latest |
| `sort_by` | `"name"\|"size"\|"complexity"\|"dependency"` | No | `"name"` | Sort order. "dependency" = topological |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "project_id": "proj_abc123",
    "modules": [
      {
        "name": "core",
        "file_count": 8,
        "line_count": 2400,
        "function_count": 45,
        "class_count": 12,
        "is_utility": false
      }
    ],
    "total_modules": 6
  }
}
```

**Precondition**: `index_codebase` must have been called.

---

### get_module_detail

Get detailed information about a specific module.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | `str` | Yes | -- | Name of the module to inspect |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "name": "core",
    "files": ["src/core/app.py", "src/core/models.py"],
    "functions": [{"name": "create_app", "params": "(config: Config)", "file": "src/core/app.py"}],
    "classes": [{"name": "Flask", "methods": ["run", "route"], "file": "src/core/app.py"}],
    "dependencies": ["utils", "config"],
    "dependents": ["api", "cli"],
    "metrics": {"line_count": 2400, "complexity": 3.2},
    "mermaid_graph": "graph TD\n  core --> utils\n  core --> config"
  }
}
```

---

### get_dependency_graph

Get the dependency graph in Mermaid format.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scope` | `"project"\|"module"` | No | `"project"` | Graph scope |
| `target` | `str \| null` | No | `null` | Module name (required when scope="module") |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "nodes": [{"name": "core", "type": "module"}],
    "edges": [{"from": "api", "to": "core", "weight": 5}],
    "circular_deps": [["models", "schemas"]],
    "mermaid_graph": "graph TD\n  api --> core\n  core --> utils"
  }
}
```

---

## 2. Budget and Chunking Tools

### estimate_module_tokens

Estimate token counts for module(s) using character/line heuristics.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | `str \| null` | No | `null` | Module name. null = estimate all |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "estimates": [
      {"module": "core", "estimated_tokens": 28800,
       "line_count": 2400, "file_count": 8, "language": "python"}
    ],
    "total_tokens": 92000
  }
}
```

**Heuristics**: Python ~4.2 chars/token, TypeScript/JavaScript ~3.8 chars/token.

---

### create_analysis_plan

Generate a chunked analysis plan with DAG topological ordering.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |
| `max_tokens_per_batch` | `int` | No | `60000` | Max tokens per batch (10000-200000) |

**Returns**:
```json
{
  "status": "success",
  "summary": "Created 8 analysis tasks in 4 layers",
  "data": {
    "tasks": [
      {"batch": 0, "modules": ["utils", "config"],
       "estimated_tokens": 12000, "reason": "leaf_modules"},
      {"batch": 1, "modules": ["models"],
       "estimated_tokens": 18000, "reason": "layer_1"}
    ],
    "total_batches": 4,
    "total_modules": 8
  }
}
```

**Notes**: Idempotent. Leaf modules (no dependencies) are batched first.

---

### check_budget_status

Check whether the agent should stop and save progress.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `used_tokens` | `int` | Yes | -- | Tokens consumed so far |
| `modules_completed` | `int` | No | `0` | Modules analyzed this session |
| `pending_cross_refs` | `int` | No | `0` | Unresolved cross-references |
| `elapsed_minutes` | `float` | No | `0.0` | Minutes since session start |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "total_budget": 129000,
    "used_tokens": 85000,
    "remaining_tokens": 44000,
    "usage_percent": 65.9,
    "should_stop": false,
    "stop_reason": ""
  }
}
```

**Stop conditions**:
1. Token usage > 85% of budget
2. Pending cross-references > 3 unanalyzed modules
3. Elapsed time > 15 minutes

---

## 3. Task Management Tools

### get_next_batch

Get the next batch of modules to analyze.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |
| `batch_size` | `int` | No | `3` | Max modules per batch (1-10) |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "batch_index": 2,
    "modules": [
      {"name": "services", "files": ["src/services/auth.py"],
       "estimated_tokens": 24000,
       "dependency_summaries": "# Module: utils\nDescription: ..."}
    ],
    "remaining_batches": 2,
    "total_progress_percent": 50.0
  }
}
```

**Precondition**: `create_analysis_plan` must have been called.

---

### submit_analysis

Submit analysis results for a module.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | `str` | Yes | -- | Module name |
| `description` | `str` | Yes | -- | One-line description |
| `public_interfaces` | `list[str]` | Yes | -- | Public function/class signatures |
| `key_data_structures` | `list[str]` | Yes | -- | Important data structures |
| `dependencies` | `list[str]` | Yes | -- | Module dependencies |
| `patterns_identified` | `list[str]` | Yes | -- | Design patterns found |
| `detailed_analysis` | `str \| null` | No | `null` | Full markdown analysis |
| `mermaid_diagram` | `str \| null` | No | `null` | Internal structure diagram |
| `token_count` | `int` | No | `0` | Tokens consumed for this analysis |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "summary": "Analysis for 'services' saved. 6/8 modules complete.",
  "data": {
    "result_id": "res_abc",
    "modules_completed": 6,
    "modules_remaining": 2,
    "progress_percent": 75.0
  }
}
```

---

### get_analysis_status

Get overall analysis progress and task status.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "total_tasks": 8,
    "pending": 2,
    "in_progress": 0,
    "completed": 6,
    "failed": 0,
    "completed_modules": ["utils", "config", "models"],
    "errors": [],
    "progress_percent": 75.0
  }
}
```

---

## 4. Checkpoint and Cross-Reference Tools

### save_checkpoint

Save an analysis checkpoint for session resume.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `phase` | `"indexing"\|"module_analysis"\|"cross_reference"\|"doc_generation"` | Yes | -- | Current phase |
| `status` | `"in_progress"\|"completed"\|"interrupted"` | No | `"in_progress"` | Status |
| `tokens_processed` | `int` | No | `0` | Total tokens processed |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "summary": "Checkpoint saved: 6/8 modules analyzed",
  "data": {
    "checkpoint_id": "ckpt_abc",
    "analyzed_modules": ["utils", "config"],
    "pending_modules": ["api", "cli"],
    "progress_percent": 75.0
  }
}
```

---

### load_checkpoint

Load an analysis checkpoint to resume a previous session.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `checkpoint_id` | `str \| null` | No | `null` | Checkpoint ID. null = latest |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "summary": "Restored checkpoint: 6/8 modules analyzed",
  "data": {
    "checkpoint_id": "ckpt_abc",
    "phase": "module_analysis",
    "analyzed_modules": ["utils", "config"],
    "pending_modules": ["api", "cli"],
    "module_summaries": {
      "utils": {"description": "Shared utilities", "public_interfaces": ["sanitize()"]}
    },
    "progress_percent": 75.0,
    "tokens_processed": 45000
  }
}
```

---

### get_cross_ref_context

Build cross-reference context from dependency summaries.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `module_name` | `str` | Yes | -- | Module being analyzed |
| `max_tokens` | `int` | No | `16000` | Max tokens for context (500-30000) |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "target_module": "services",
    "context": "# Module: utils\nDescription: Shared utilities...\n---\n# Module: models\n...",
    "dependencies_resolved": 3,
    "dependencies_pending": 1,
    "context_tokens": 8500
  }
}
```

**Notes**: Returns summaries (not source code) of dependencies, ordered by
reference weight. Unanalyzed dependencies show file list and "pending" status.

---

## 5. Document Generation Tools

### plan_doc_structure

Plan the full documentation tree with dynamic depth decisions.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "summary": "Planned 12 documents across 3 depth levels",
  "data": {
    "doc_tree": [
      {"path": "INDEX.md", "level": 0, "target": "root",
       "token_budget": 1200, "parent": null,
       "children": ["core/OVERVIEW.md", "utils/OVERVIEW.md"]},
      {"path": "core/OVERVIEW.md", "level": 1, "target": "core",
       "token_budget": 2000, "parent": "INDEX.md",
       "children": ["core/app/DETAIL.md"]}
    ],
    "total_docs": 12,
    "max_depth": 3,
    "depth_decisions": {
      "core": {"depth": 2, "reason": "1453 lines, 28 components",
               "split_strategy": "subpackage"},
      "utils": {"depth": 1, "reason": "utility module, 200 lines",
                "split_strategy": "file"}
    }
  }
}
```

**Precondition**: All modules must be analyzed (submit_analysis complete).

---

### generate_doc

Generate a single document using Jinja2 templates.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | `str` | Yes | -- | Module name or "root" for INDEX |
| `level` | `int` | Yes | -- | 0=INDEX, 1=OVERVIEW, 2+=DETAIL (0-5) |
| `token_budget` | `int` | Yes | -- | Budget for this document (>= 200) |
| `parent_path` | `str \| null` | No | `null` | Parent doc path for back-links |
| `children` | `list[str] \| null` | No | `null` | Child doc paths for forward-links |
| `project_id` | `str \| null` | No | `null` | Project ID. null = latest |

**Returns**:
```json
{
  "status": "success",
  "data": {
    "path": "core/OVERVIEW.md",
    "content": "# Core Module\n\n> ...",
    "actual_tokens": 1850,
    "level": 1,
    "target": "core"
  }
}
```

**Template selection**:
- Level 0: `index.md.j2`
- Level 1: `overview.md.j2`
- Level 2+: `detail.md.j2` (universal, works at any depth)

---

## 6. Error Codes

| Error | Tool(s) | Description | Recovery |
|-------|---------|-------------|----------|
| `PROJECT_NOT_FOUND` | All except `index_codebase` | No project indexed yet | Call `index_codebase` first |
| `MODULE_NOT_FOUND` | `get_module_detail`, `submit_analysis` | Invalid module name | Check `get_modules` for valid names |
| `PLAN_NOT_CREATED` | `get_next_batch`, `generate_doc` | Analysis plan missing | Call `create_analysis_plan` |
| `ANALYSIS_INCOMPLETE` | `plan_doc_structure` | Not all modules analyzed | Complete pending analyses |
| `INVALID_PATH` | `index_codebase` | Path does not exist | Provide valid absolute path |
| `BUDGET_EXCEEDED` | `generate_doc` | Content exceeds token budget | Reduce scope or increase budget |
| `CHECKPOINT_NOT_FOUND` | `load_checkpoint` | No checkpoint exists | Start from Phase 1 |
| `TASK_CLAIMED` | `get_next_batch` | Module locked by another agent | Skip to next module in batch |
| `UNSUPPORTED_LANGUAGE` | `index_codebase` | Language not supported | Use python/typescript/javascript |
| `TIMEOUT` | `index_codebase` | Indexing exceeded 120s | Index a smaller directory |
