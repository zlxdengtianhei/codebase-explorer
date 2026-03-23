---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive-disclosure architecture
  documentation using MCP tools. Automatically indexes codebases, groups modules
  via Louvain community detection, and produces dynamic N-layer docs (INDEX,
  OVERVIEW, DETAIL) whose depth adapts to module complexity. Use whenever the
  user wants to understand a codebase's architecture, generate documentation,
  explore module dependencies, or visualize code structure. Also triggers on
  "architecture docs", "module overview", "code map", "dependency graph",
  "codebase analysis", or "generate docs".
version: 1.0.0
license: MIT
compatibility:
  - claude-code
  - codex
  - opencode
  - gemini-cli
mcp_server: codebase-explorer
tools_count: 15
---

# Codebase Explorer

Analyze code structure and generate progressive architecture documentation.
Produces dynamic N-layer docs -- from a one-page project index down to
component-level internals -- whose depth automatically adapts to each module's
complexity. Small utility modules get a single overview; large subsystems get
4-5 levels of detail.

## When to Use

Use this skill when:

- The user wants to understand an unfamiliar codebase's structure
- The user asks for architecture documentation or module overviews
- The user needs to visualize dependencies between modules
- The user mentions "code map", "dependency graph", "architecture docs"
- A new team member needs onboarding documentation
- Before a major refactoring to understand impact scope

Do NOT use when:

- The user just wants to read or edit a single file (use normal tools)
- The user wants API reference docs for a library (use official docs)
- The codebase is a single file or script (< 100 lines)

## Prerequisites

The codebase-explorer MCP server must be running. Verify by calling
`get_analysis_status` -- if it fails, tell the user to start the server:

```
uv run python -m codebase_explorer.server
```

## Quick Start

1. **Install**: `uv add codebase-explorer` or configure in `.mcp.json`
2. **Configure**: Copy `assets/doc-config.yaml` to project root (optional)
3. **Run**: Tell the agent "analyze this codebase" or use `/codebase-explorer`

## Workflow

The workflow has 5 phases. Each phase produces concrete outputs that feed
the next. Follow these phases in order.

### Phase 1: Index

**Goal**: Build the code graph from source files.

1. Call `index_codebase(path=<repo_path>)`
2. Check progress via `get_analysis_status` until `status: "success"`
3. Note the `project_id` for all subsequent calls
4. Report summary stats to the user (files, functions, classes, languages)

**Quality gate**: `status: "success"` before proceeding.

### Phase 2: Plan

**Goal**: Discover modules, create the analysis plan, and plan document structure.

1. Call `get_modules(sort_by="dependency")` to get Louvain-grouped modules
2. Present module list to the user; confirm grouping is acceptable
3. Call `create_analysis_plan()` to generate chunked analysis tasks in
   topological dependency order
4. Call `plan_doc_structure()` to build the documentation tree

The doc structure planner uses the **Dynamic Depth Engine** to decide how
deep each module's documentation goes. This is NOT fixed 3-layer -- depth
is determined by three factors:

```
depth = max(structural_depth, complexity_depth, token_depth)
```

- **Structural**: based on subpackage count (0 = flat, 5 = 20+ subpackages)
- **Complexity**: based on function/class counts and cyclomatic complexity
- **Token**: based on estimated source token count

Result: small modules get depth 0-1 (merged or single overview), complex
subsystems get depth 3-5 with recursive DETAIL documents.

**Quality gate**: User confirms module grouping. Analysis plan created.

### Phase 3: Analyze

**Goal**: Analyze each module and submit structured results.

Loop until all modules are analyzed:

1. Call `get_next_batch(batch_size=3)` for the next set of modules
2. For each module in the batch:
   a. Call `get_cross_ref_context(module_name)` for dependency summaries
   b. Read source files and analyze the module
   c. Call `submit_analysis(module_name, description, public_interfaces,
      key_data_structures, dependencies, patterns_identified, ...)`
3. Call `check_budget_status(used_tokens, modules_completed)` to decide
   whether to continue or save a checkpoint
4. If `should_stop: true`, call `save_checkpoint(phase="module_analysis")`
   and resume later with `load_checkpoint()`

**Checkpoint rule**: After every 3 modules, save progress and validate
intermediate results. Long sessions risk context window overflow -- frequent
saves prevent lost work.

**Quality gate**: All modules have analysis results submitted.

### Phase 4: Generate

**Goal**: Generate documentation following the planned tree structure.

Process documents from the doc tree returned by `plan_doc_structure()`,
generating from leaves to root:

1. For each doc node (bottom-up by level):
   a. Call `generate_doc(target, level, token_budget, parent_path, children)`
   b. Verify the returned `actual_tokens` fits within `token_budget`
   c. Write content to the specified path under the output directory
2. Generate `doc-index.json` summarizing all documents

**Token budget enforcement** -- when content exceeds budget, trim in this order:

| Priority | Content Type | Action |
|----------|-------------|--------|
| 1 (keep) | Names, signatures, descriptions | Always include |
| 2 | Dependencies, architecture diagram | High priority |
| 3 | Class/function details, data flow | Medium priority |
| 4 | Implementation notes, examples | Trim first |

**Quality gate**: All planned documents generated within token budgets.

### Phase 5: Validate

**Goal**: Verify documentation quality.

1. Call `get_analysis_status()` to confirm all tasks completed
2. Validate link integrity: every `[text](path)` link resolves
3. Verify token budgets: each document within its allocated budget
4. Check coverage: documented modules / total modules >= 80%
5. Present final summary to the user:
   - Total documents generated
   - Coverage percentage
   - Total token count
   - Max depth used
   - Any gaps or issues

**Quality standards** (see [QUALITY_STANDARDS.md](references/QUALITY_STANDARDS.md)):

| Metric | Threshold |
|--------|-----------|
| Module coverage | >= 80% |
| Link validity | 100% |
| Token budget compliance | >= 90% of docs within budget |
| Mermaid diagram presence | Every OVERVIEW has one |

## Dynamic Depth Feature

The documentation depth is NOT fixed. The depth planner evaluates each module
independently and assigns depth 0-5 based on its metrics:

| Depth | Meaning | When Applied |
|-------|---------|-------------|
| 0 | Summary only | Merged into parent (< 100 LOC, < 5 functions) |
| 1 | OVERVIEW only | Small modules (< 500 LOC) |
| 2 | OVERVIEW + DETAIL | Medium modules (500-2000 LOC) |
| 3 | Three-level nesting | Complex modules (2000+ LOC, subpackages) |
| 4 | Four-level nesting | Large subsystems (5000+ LOC) |
| 5 | Maximum depth | Framework-scale modules (10000+ LOC) |

Split strategies for deeper levels:

- **SUBPACKAGE**: Split by subdirectory (preferred when 2+ balanced subpackages)
- **CLASS**: Split by class (for OOP-heavy code with 3+ classes)
- **FUNCTION_GROUP**: Split by function clusters (functional style)
- **FILE**: Split by individual files (fallback)

Units below the minimum documentable threshold (30 lines, 2 functions, 200
tokens) are merged into their parent document rather than getting a separate
file.

## MCP Tool Quick Reference

For detailed parameters, see [MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md).

| # | Tool | Purpose |
|---|------|---------|
| 1 | `index_codebase` | Parse codebase, build dependency graph, run Louvain grouping |
| 2 | `get_modules` | List auto-detected modules with metrics |
| 3 | `get_module_detail` | Get files, interfaces, dependencies for one module |
| 4 | `get_dependency_graph` | Get Mermaid dependency diagram (project or module scope) |
| 5 | `estimate_module_tokens` | Estimate token counts for modules |
| 6 | `create_analysis_plan` | Generate chunked analysis tasks in DAG order |
| 7 | `check_budget_status` | Check if agent should stop and save progress |
| 8 | `get_next_batch` | Get next batch of modules to analyze |
| 9 | `submit_analysis` | Submit structured analysis results for a module |
| 10 | `get_analysis_status` | Get overall progress and task status |
| 11 | `save_checkpoint` | Save analysis checkpoint for session resume |
| 12 | `load_checkpoint` | Restore checkpoint to continue previous session |
| 13 | `get_cross_ref_context` | Build cross-reference context from dependency summaries |
| 14 | `plan_doc_structure` | Plan documentation tree with dynamic depth decisions |
| 15 | `generate_doc` | Generate a single document using Jinja2 templates |

## Configuration

Default configuration is in [assets/doc-config.yaml](assets/doc-config.yaml).
Copy to the project root to override defaults:

```yaml
output_dir: .codebase-docs
max_depth: 5
budget:
  total_tokens: 50000
  max_per_module: 10000
depth:
  min_lines_for_split: 200
  min_components_for_split: 15
  decay_factor: 0.6
```

## Error Recovery

**Index fails**: Check path is absolute and directory exists. Try with
explicit `languages` filter.

**Token budget exceeded**: Re-call `generate_doc` with reduced scope.
Follow priority-based trimming (keep interfaces, trim examples).

**Checkpoint restore**: Call `load_checkpoint()` to resume. The checkpoint
includes analyzed modules and pending queue -- no work is duplicated.

**Claimed task conflict**: Another agent has the module locked. Skip to a
different module in the batch.

## Reference Files

Load these only when you need detailed specifications:

- [WORKFLOW_DETAIL.md](references/WORKFLOW_DETAIL.md) -- Expanded step-by-step procedures with MCP call examples
- [MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md) -- Full parameter and return value specifications for all 15 tools
- [DOC_TEMPLATES.md](references/DOC_TEMPLATES.md) -- Jinja2 template variable lists, output examples, token budget guide
- [QUALITY_STANDARDS.md](references/QUALITY_STANDARDS.md) -- Coverage, link validity, token compliance, and depth validation standards
