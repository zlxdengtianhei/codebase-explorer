# Quality Standards Reference (V5)

> Load this file when you need to verify documentation quality or understand
> the acceptance criteria for each phase.

## Table of Contents

1. [INDEX.md Checklist](#1-indexmd-checklist)
2. [DETAIL.md Checklist](#2-detailmd-checklist)
3. [Coverage Standards](#3-coverage-standards)
4. [Content Quality Standards](#4-content-quality-standards)
5. [Phase Gate Criteria](#5-phase-gate-criteria)

---

## 1. INDEX.md Checklist

The INDEX.md is assembled by `doc_operation("update_index")` from DETAIL fragments.

- [ ] YAML front matter present (`project`, `total_modules`, `generated_by`)
- [ ] Mermaid dependency graph present in `## Module Dependency Graph` section
- [ ] Mermaid graph edges match `02_dag.json` module-level edges (no fabricated edges)
- [ ] Every module has a `<!-- module-index:{module_id} -->` block
- [ ] Every module entry includes file count and token count
- [ ] Every module entry has a link to its `DETAIL.md`
- [ ] Links resolve (DETAIL files exist at the paths referenced)
- [ ] `<!-- codebase-explorer: end -->` marker present at end of file

---

## 2. DETAIL.md Checklist

Each module's DETAIL.md must pass all checks.

### Structure Checks

- [ ] YAML front matter present with all required fields: `module_id`, `module_name`, `file_count`, `generated_at`, `token_budget`
- [ ] `<!-- module:{module_id} -->` opening marker present
- [ ] `<!-- end:module:{module_id} -->` closing marker present (or `<!-- end:{module_id} -->`)
- [ ] `<!-- codebase-explorer: end -->` marker at end of file

### Per-File Checks (for each file in the module)

- [ ] `<!-- file:{filepath} -->` opening marker present
- [ ] `<!-- end:file:{filepath} -->` closing marker present
- [ ] `#### 功能概述 (Purpose)` section present — describes what file does and why
- [ ] `#### 数据流 (Data Flow)` section present — describes input/transform/output flow
- [ ] `#### 核心接口 (Key Interfaces)` section present — lists function/class signatures
- [ ] `#### 依赖关系 (Dependencies)` section present — lists specific cross-file dependencies

### Index Fragment Check

- [ ] `<!-- index-fragment:{module_id} -->` block present
- [ ] Fragment contains 2-3 sentences describing module purpose
- [ ] Fragment mentions key entry points (function/class names)
- [ ] Fragment includes file count and token count
- [ ] `<!-- end:index-fragment:{module_id} -->` closing marker present

---

## 3. Coverage Standards

### Threshold: >= 80% Source File Coverage

Coverage measures the fraction of source files that have been documented.

```
coverage = documented_source_files / total_source_files
```

| Coverage | Grade | Action |
|----------|-------|--------|
| >= 95% | Excellent | No action needed |
| 80-94% | Acceptable | Note uncovered files in final report |
| 60-79% | Below standard | Must document critical modules before completion |
| < 60% | Unacceptable | Analysis is incomplete; continue or report blocker |

Check current coverage with `get_progress()` — see `source_file_coverage_percent`.

### What Counts as "Documented"

A source file is considered documented if:
1. Its containing module has a DETAIL.md
2. The DETAIL.md has a file block for this specific file (`<!-- file:{filepath} -->`)
3. The file block contains all four required sections

---

## 4. Content Quality Standards

### 功能概述 (Purpose) — What to Check

- Answers "what does this file do and why does it exist?"
- Mentions the file's role within its module
- Does NOT describe implementation details (no line-by-line walkthrough)
- Does NOT just restate the filename

**Good:** "Implements URL routing for Flask HTTP requests by building and querying
a Rule-based dispatch table. All incoming requests pass through this file's match()
logic before reaching view functions."

**Bad:** "This file imports werkzeug.routing and defines several classes."

### 数据流 (Data Flow) — What to Check

- Describes the data flow path: what comes in, what transforms happen, what goes out
- Mentions specific input types and output types
- Does NOT describe every line of code
- Is specific to this file (not the whole module)

### 核心接口 (Key Interfaces) — What to Check

- Lists the most important public functions and classes
- Includes actual signatures: `function_name(param: Type) -> ReturnType`
- Each entry has a brief purpose description
- Does NOT list private helpers (`_foo`) unless they are critical
- Does NOT document every parameter in detail

### 依赖关系 (Dependencies) — What to Check

- Lists specific function calls: "Calls `globals.current_app` to access app context"
- Does NOT just say "imports X" without explaining why
- Uses function/class names from the actual code (verified via `get_function_deps`)
- Includes both outgoing calls (what this file calls) and incoming usage if notable

### Index Fragment — What to Check

- Stands alone: a reader who hasn't seen DETAIL can understand the module
- Mentions 1-2 key entry points by name
- Does NOT exceed 3 sentences
- Is different from any individual file's 功能概述 (covers the whole module)

---

## 5. Phase Gate Criteria

### Phase 1 -> Phase 2 Gate

| Criterion | Required |
|-----------|----------|
| `analyze_codebase` returned `status: "success"` | Yes |
| `03_feature_cones.json` exists with at least one module | Yes |
| `06_function_deps.json` exists | Yes |
| `files_analyzed > 0` in response | Yes |

### Phase 2 -> Phase 3 Gate

| Criterion | Required |
|-----------|----------|
| `get_modules()` returns non-empty module list | Yes |
| No module has `token_count > 50000` without a split plan | Yes |
| All source files are assigned to a module (no unassigned files) | Yes |

### Phase 3 -> Phase 4 Gate

| Criterion | Required |
|-----------|----------|
| All tasks in `05_task_manifest.json` have status `"complete"` | Yes |
| `get_progress()` shows `progress_percent == 100` | Yes |
| All module directories have a `DETAIL.md` file | Yes |
| Each `DETAIL.md` has an `<!-- index-fragment -->` block | Yes |

### Phase 4 Completion

| Criterion | Required |
|-----------|----------|
| `.codebase-docs/INDEX.md` exists and is non-empty | Yes |
| INDEX.md contains a Mermaid graph | Yes |
| INDEX.md has a `<!-- module-index -->` block for every module | Yes |
| All DETAIL links in INDEX.md resolve to existing files | Yes |
| Source file coverage >= 80% | Yes |
| Final summary reported to user | Yes |
