# Codebase Explorer V5 — Troubleshooting

This document collects common issues and their solutions for the codebase-explorer V5 workflow.

---

## Problem: analyze_codebase returns 0 feature cones

**Cause:** Codebase may have circular dependencies that prevent cone extraction, or
all files ended up in the Louvain fallback grouping.

**Solution:**
1. Check `01_structure.json` for `file_count` — if 0, the parser found no supported files
2. Check `02_dag.json` for `circular_deps` field — if present, cones may be degraded
3. If many single-file cones: this is normal for some codebases; proceed with documentation
4. Try with explicit `languages` param: `analyze_codebase(path=X, languages=["python"])`

---

## Problem: get_function_deps returns error "Function deps not found"

**Cause:** `06_function_deps.json` was not generated (old cache from before V5).

**Solution:**
1. Re-run `analyze_codebase(path=X, force_reindex=true)`
2. The `06_function_deps.json` file will be regenerated alongside the other 5 JSON files

---

## Problem: index-fragment extraction fails — update_index produces empty INDEX

**Cause:** DETAIL files are missing the `<!-- index-fragment:{module_id} -->` block,
or the block has incorrect formatting.

**Solution:**
1. Inspect each DETAIL.md and verify it contains:
   ```
   <!-- index-fragment:{module_id} -->
   ...content...
   <!-- end:index-fragment:{module_id} -->
   ```
2. The closing tag must be `<!-- end:index-fragment:{module_id} -->` (not `<!-- /index-fragment -->`)
3. If fragments are missing, re-run Phase 3 DETAIL generation for the affected modules
4. After fixing, call `doc_operation("update_index")` again

---

## Problem: update_index produces INDEX with no Mermaid graph

**Cause:** `02_dag.json` is missing or `03_feature_cones.json` has no cone data.

**Solution:**
1. Verify `02_dag.json` exists in `.codebase-analysis/`
2. Check that `03_feature_cones.json` has a non-empty `cones` object
3. Re-run `analyze_codebase(force_reindex=true)` if either file is missing or empty

---

## Problem: DETAIL file is missing one or more of the four sections

**Cause:** Sub-agent did not follow the four-section format per file.

**Required sections for each file block:**
1. `#### 功能概述 (Purpose)` — What the file does and why it exists
2. `#### 数据流 (Data Flow)` — How data flows through the file
3. `#### 核心接口 (Key Interfaces)` — Important functions and classes with signatures
4. `#### 依赖关系 (Dependencies)` — Cross-file dependencies with specific function names

**Solution:**
1. Re-run Phase 3 for the affected module
2. Ensure the sub-agent prompt includes `doc_operation("get_template")` output
3. Verify the prompt states: "Write FOUR sections per file: 功能概述, 数据流, 核心接口, 依赖关系"

---

## Problem: DETAIL module token count > 50k — agent context overflow

**Cause:** A single module has too many files for one agent context.

**Solution:**
1. Identify the large module via `get_modules()` — check `token_count` field
2. Use `doc_operation("split_module", source_module=X)` to list files in the module
3. Write DETAIL for half the files manually (first sub-agent covers files 1-N/2)
4. Write second DETAIL for remaining files (second sub-agent covers files N/2+1-N)
5. Each DETAIL should have its own `<!-- index-fragment -->` block
6. Both get assembled into INDEX by `doc_operation("update_index")`

---

## Problem: Context compression — session interrupted mid-Phase 3

**Cause:** Claude Code context window approached its limit during Phase 3.

**Recovery steps:**
1. Call `submit_analysis` for any in-progress task (to persist partial progress)
2. Start a new session
3. Read SKILL.md to restore context
4. Call `get_progress()` — shows which tasks are pending, in_progress, complete
5. Resume from the first pending task in `next_pending_tasks`
6. Continue spawning sub-agents for remaining pending modules

---

## Problem: Links in INDEX.md point to DETAIL files that don't exist

**Cause:** `update_index` assembled fragments from modules that don't have DETAIL files
written yet, or file paths in fragments are wrong.

**Solution:**
1. Call `get_progress()` — check that all DETAIL tasks show `"complete"`
2. Verify DETAIL files exist at `.codebase-docs/{module_id}/DETAIL.md`
3. If files are missing, re-run Phase 3 for the missing modules
4. Re-run `doc_operation("update_index")` after all DETAIL files are present

---

## Problem: MCP server not responding / connection refused

**Cause:** The codebase-explorer MCP server process is not running.

**Solution:**
1. Check MCP server configuration in Claude Code settings
2. Verify the server is listed in `.claude/settings.json` under `mcpServers`
3. Restart Claude Code to reinitialize MCP connections
4. Check server logs for startup errors

---

## Problem: Source file coverage below 80%

**Cause:** Some modules were not documented in Phase 3.

**Solution:**
1. Call `get_progress()` — check `source_file_coverage_percent` and `next_pending_tasks`
2. Spawn DETAIL sub-agents for all pending tasks
3. Re-run `doc_operation("update_index")` after all tasks complete
4. Coverage is tracked per source file, not per module — verify each module has DETAIL
