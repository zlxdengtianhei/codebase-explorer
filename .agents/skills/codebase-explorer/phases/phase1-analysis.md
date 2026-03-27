# Phase 1: Analysis (MCP Automated)

> **When to read this file:** You are starting a new codebase analysis or need to understand the automated indexing step.
>
> **Entry conditions:** User has requested architecture documentation and the codebase-explorer MCP server is running.

---

**Entry Point:** `analyze_codebase(path, languages=None, output_dir=None, force_reindex=False, exclude_paths=None, include_tests=False)`

**What it does:**
1. Parse codebase -> CodebaseSnapshot (graph-sitter)
2. Build weighted dependency graph (import + call + inherit edges)
3. Extract feature cones via SCC + DAG analysis (Louvain fallback if cones are degraded)
4. Estimate tokens per file (chars / 4 method)
5. Build task manifest
6. Write 6 JSON files + state.json

**Output Files (in `.codebase-analysis/`):**
- `01_structure.json` — File list + function/class metadata
- `02_dag.json` — Weighted dependency edges + Mermaid graph
- `03_feature_cones.json` — Module groupings + layer structure + cohesion_score + layers_within_cone
- `04_file_tokens.json` — Per-file token estimates (chars / 4)
- `05_task_manifest.json` — Agent task queue
- `06_function_deps.json` — Cross-file function call relationships
- `state.json` — Task status + coverage metrics

**After analysis:** Call `get_modules()` (no args) to see module summary overview.

**Quality Gate:** `file_count > 0` AND `03_feature_cones.json` has at least one module AND `06_function_deps.json` exists

**9 Available Tools:**
`analyze_codebase`, `get_structure`, `get_modules`, `get_function_deps`, `doc_operation`,
`get_dependency_graph`, `get_progress`, `get_file_tokens`, `submit_analysis`

**Example:**
```
User: Analyze the Flask codebase
-> Call analyze_codebase(path="/path/to/flask", force_reindex=true)
-> Returns: {"feature_cones_found": 7, "files_analyzed": 42, "total_tokens": 38000, ...}
-> Call get_modules() to see module summary
```

---

## Exit Condition

Phase 1 is complete when `analyze_codebase` returns successfully with `file_count > 0`,
`03_feature_cones.json` exists in the output directory, and `06_function_deps.json` exists.

**Next step:** Proceed to [Phase 2: Auto-Validation](./phase2-validation.md).
