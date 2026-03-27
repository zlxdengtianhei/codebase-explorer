# Codebase Explorer V5 — Usage Examples

This document collects usage examples for the codebase-explorer skill workflow.

---

## Example 1: Complete 4-Phase Documentation Generation

```
User: Generate architecture docs for the Flask codebase

Phase 1 — Analysis:
1. Call analyze_codebase(path="/path/to/flask", force_reindex=true)
   -> Returns: {"feature_cones_found": 7, "files_analyzed": 42, ...}

2. Call get_modules() to see module summary
   -> Returns list of 7 modules with file counts and token counts

Phase 2 — Auto-Validation (no LLM, rule-based):
3. Review get_modules() output:
   - Check each module: token_count, file_count, layer
   - Flag any module with token_count > 50000 (too large, needs attention)
   - Flag any module with file_count == 1 (single-file module, potential merge)
   - Confirm all source files are assigned to a module

Phase 3 — Parallel DETAIL generation:
4. For each module, spawn a sub-agent with:
   - module_id and file list (from get_modules(module_id=X))
   - DETAIL template (from doc_operation("get_template"))
   - Three-step protocol (from doc_operation("get_protocol"))

   Each sub-agent:
   a. Reads source files
   b. Writes four sections per file: 功能概述, 数据流, 核心接口, 依赖关系
   c. Calls get_function_deps(file=X) to enrich 依赖关系 sections
   d. Writes <!-- index-fragment:{module_id} --> block
   e. Calls submit_analysis(task_id, detail_paths, snippet_paths=[], tokens_used)

5. Monitor with get_progress() until all DETAIL tasks are complete

Phase 4 — INDEX Assembly + Semantic Reorganization:
6. Call doc_operation("update_index")
   -> Assembles INDEX.md from all index-fragment blocks in DETAIL files
   -> Generates module-level Mermaid dependency graph
   -> Writes .codebase-docs/INDEX.md

7. Review INDEX.md for semantic coherence:
   - Are module names functional (e.g., "request-handling") not directory-based?
   - Are related modules grouped near each other in the listing?
   - Are there obvious misplacements?

8. If reorganization needed:
   a. doc_operation("move_detail", source_module="X", target_module="Y", file_path="DETAIL.md")
   b. doc_operation("update_index")  <- re-assemble after changes

Output: .codebase-docs/ with INDEX.md + one DETAIL.md per module
```

---

## Example 2: Checkpoint Recovery

```
User: Continue the previous documentation generation (context was interrupted)

1. Call get_progress()
   -> Returns: {"tasks": {"pending": 4, "complete": 5, "failed": 0}, "next_pending_tasks": [...]}

2. From next_pending_tasks, identify which modules still need DETAIL docs

3. Spawn DETAIL sub-agents for remaining pending tasks only
   -> Each agent: get_modules(module_id=X) -> read source -> write DETAIL -> submit_analysis()

4. When get_progress() shows all tasks complete, proceed to Phase 4:
   -> doc_operation("update_index") to assemble final INDEX.md
```

---

## Example 3: Query-Only (No Documentation Generation)

```
User: Show me the module structure of this codebase

1. Call analyze_codebase(path="/path/to/project")
   -> Get 6 JSON files in .codebase-analysis/

2. Call get_modules()
   -> Return summary of all modules with file counts, token counts, layers

3. Call get_dependency_graph(scope="project")
   -> Return Mermaid module-level dependency graph

(No sub-agents spawned, no DETAIL files written)

Optionally:
4. Call get_modules(module_id="specific_module")
   -> Return file list for that module

5. Call get_dependency_graph(scope="file", target="src/main.py", hops=2)
   -> Return 2-hop dependency neighborhood for main.py
```

---

## MCP Tool Quick Reference (9 Tools)

### 1. analyze_codebase(path, languages, output_dir, force_reindex, exclude_paths, include_tests)

Full analysis pipeline. Writes 6 JSON files + state.json to `.codebase-analysis/`.

Output files:
- `01_structure.json` — file/function/class metadata
- `02_dag.json` — weighted dependency edges + Mermaid
- `03_feature_cones.json` — module groupings + layer structure + cohesion_score
- `04_file_tokens.json` — per-file token estimates (chars / 4)
- `05_task_manifest.json` — agent task queue
- `06_function_deps.json` — cross-file function call relationships

### 2. get_structure(module, file, function)

Query code structure from `01_structure.json`. Three mutually exclusive modes:
- `module` — Get all files in a module
- `file` — Get detailed info for a single file
- `function` — Get function signature and dependencies
- None — Return project summary

### 3. get_modules(module_id)

Query functional modules:
- `module_id=None` — Summary of all modules (compact, < 3KB)
- `module_id="routing"` — Detail for one module (file list + token counts + layers)

Use summary first to discover valid module IDs, then detail for sub-agent tasks.

### 4. get_function_deps(file, module_id)

Cross-file function call dependencies for a single file.
- Returns which functions in `file` call functions in other files
- `module_id` — Optional: filter to within-module calls only
- Reads from `06_function_deps.json`

### 5. doc_operation(operation, source_module, target_module, file_path, new_order)

Documentation operations:
- `get_template` — DETAIL and INDEX format specification
- `get_protocol` — Three-step DETAIL writing protocol
- `update_index` — Assemble INDEX.md from index-fragment blocks
- `move_detail` — Move a DETAIL file between module directories
- `merge_modules` — Move all files from one module into another
- `split_module` — List files in a module (inspection before moving)
- `reorder_modules` — Set display order for INDEX assembly

### 6. get_dependency_graph(scope, target, include_weights, hops)

Mermaid dependency graph from `02_dag.json`:
- `scope="project"` — Module-level graph (all modules as nodes)
- `scope="cone"` or `scope="module"` — File-level graph within one module
- `scope="file"` — N-hop neighborhood centered on a single file

### 7. get_progress(project_id)

Task completion status from `state.json`.
Returns counts of pending/in_progress/complete/failed tasks and next pending task IDs.
Use for recovery after interruption.

### 8. get_file_tokens(file, module)

Per-file token estimates from `04_file_tokens.json`:
- `file` — Return single file token info
- `module` — Return all files in a module + aggregate stats
- None — Return all files

### 9. submit_analysis(task_id, detail_paths, snippet_paths, tokens_used, source_files_covered, project_id)

Task completion callback. Called by DETAIL agents after writing docs.
Atomically updates `state.json` with completion status and coverage metrics.
Pass `snippet_paths=[]` for V5 (no SNIPPET files used).
