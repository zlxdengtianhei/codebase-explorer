---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive-disclosure architecture
  documentation using MCP tools (V2). Uses feature cone extraction for module
  grouping and token-aware task planning. LLM agents write documentation directly
  (no Jinja2 templates). Produces INDEX.md, OVERVIEW.md, and DETAIL.md files
  adapted to module complexity. Phase 5 Semantic Reorganization transforms flat
  document structure into hierarchical architecture via doc-manifest.json SSOT.
  Use for architecture documentation, code exploration, dependency visualization,
  or generating docs. Triggers on "architecture docs", "module overview",
  "code map", "dependency graph", "codebase analysis", or "generate docs".
version: 2.0.0
license: MIT
compatibility:
  - claude-code
  - codex
  - opencode
mcp_server: codebase-explorer
tools_count: 7
---

# Codebase Explorer V2

Analyze code structure and generate progressive architecture documentation.
Uses **Feature Cone extraction** (SCC + DAG + BFS) for semantic module grouping
and **token-aware task planning** for optimal agent delegation.

## Key Changes from V1

- **7 tools instead of 15** (streamlined API)
- **No SQLite** (JSON-based state management)
- **No Jinja2 templates** (LLM agents write docs directly)
- **Feature Cone grouping** (replaces Louvain as primary)
- **Token-aware bin packing** (better task distribution)

## When to Use

Use this skill when:

- User wants architecture documentation for a codebase
- User needs to understand code structure and dependencies
- User mentions "code map", "dependency graph", "architecture docs"
- Onboarding new team members to a codebase
- Before major refactoring to understand impact scope

Do NOT use when:

- User just wants to read/edit a single file (use normal tools)
- User wants API reference docs (use official documentation)
- Codebase is very small (< 100 lines)

## Prerequisites

The codebase-explorer MCP server must be running. Verify by calling
`analyze_codebase` on any directory.

---

## 6-Phase Workflow

### Phase 1: Index (MCP Automated)

**Entry Point:** `analyze_codebase(path, languages=None, output_dir=None, force_reindex=False)`

**What it does:**
1. Parse codebase → CodebaseSnapshot (graph-sitter)
2. Build weighted dependency graph (import + call + inherit edges)
3. Extract feature cones via SCC + DAG analysis
4. Estimate tokens per file (chars ÷ 4 method)
5. Build task manifest (greedy bin packing)
6. Write 5 JSON files + state.json

**Output Files (in `.codebase-analysis/`):**
- `01_structure.json` - File list + function/class metadata
- `02_dag.json` - Weighted dependency edges + Mermaid graph
- `03_feature_cones.json` - Cone groupings + layer structure
- `04_file_tokens.json` - Per-file token estimates
- `05_task_manifest.json` - Agent task queue (batch/single/split)
- `state.json` - Task status + coverage metrics

**Quality Gate:** `file_count > 0` AND `feature_cones.json` exists

**Example:**
```
User: Analyze the Flask codebase
→ Call analyze_codebase(path="/path/to/flask")
→ Returns: {"feature_cones_found": 7, "task_count": 12, ...}
```

---

### Phase 2: Validate Structure (Validator Agent)

**Input:** `03_feature_cones.json` (algorithm output)

**Agent Role:** Senior architect reviewing automated groupings

**Validation Criteria:**
1. **Semantic Cohesion** - Do files serve a single purpose?
2. **Dependency Boundary** - Are caller/callee properly separated?
3. **Size Appropriateness** - Flag cones > 30k tokens (split) or < 500 tokens (merge)
4. **Naming Quality** - Replace `cone_0` with semantic names like `request-handling`

**Agent Actions:**
- Assign semantic `name` for each cone
- Set `action: "keep" | "merge" | "split" | "rename"`
- Write reasoning in `validation_notes` field
- **Directly update** `03_feature_cones.json` (no approval needed)

**Constraints:**
- Single cone MUST NOT exceed 50k tokens (hard limit)
- Merged cone MUST NOT exceed 30k tokens
- Algorithm constraints have highest priority

**Validator Agent Prompt Template:**

```
# Feature Cone Validation Task

## Your Role

You are a senior software architect reviewing an automated code grouping result.
The grouping was produced by a graph algorithm (SCC + DAG layering + Louvain
community detection). Your job is to evaluate whether the groupings make
semantic sense for a developer audience, and to directly update the grouping
file if you find problems.

## Input: Feature Cones (Algorithm Output)

```json
{{feature_cones_json}}
```

## Project Context

- Project root: {{project_root}}
- Total source files: {{total_source_files}}
- Primary language: {{primary_language}}

## Validation Criteria

For each feature cone, evaluate:

### 1. Semantic Cohesion (most important)
- Do the files in this cone serve a single recognizable purpose?
- Would a developer intuitively group these files together?
- Is the cone name descriptive and accurate?

### 2. Dependency Boundary Integrity
- Does the cone contain both "caller" and "callee" files where they could be separated?
- Are there files that clearly belong to a DIFFERENT cone by function?

### 3. Size Appropriateness
- Cones with `exclusive_total_tokens > 30000`: Flag as "too large" (split candidate)
- Cones with `exclusive_total_tokens < 500` AND `exclusive_file_count == 1`: Flag as "too small" (merge candidate)
- Algorithm constraint: Do NOT suggest merging two cones whose combined `exclusive_total_tokens` exceeds 30000

### 4. Naming Quality
- Is the cone name `cone_N`? Suggest a semantic name.
- Does the name reflect the PRIMARY function?

## What You MUST Do

1. For each cone: assign a semantic `name`
2. For cones with problems: specify `action: "merge" | "split" | "rename" | "keep"`
3. Write your final judgment directly into the updated JSON structure
4. For each change, write a brief `reasoning` field (1-2 sentences)
5. Preserve all fields that the algorithm set (especially `exclusive_files`,
   `layers_within_cone`, `exclusive_total_tokens`, `shared_deps`, `dag_layer`,
   `cohesion_score`, `entry_point`) -- only update `name`, `action`,
   `validation_notes`, `confidence`, and `reasoning`

## Output Format

Output the COMPLETE updated `03_feature_cones.json` with your changes applied.

Use this schema for each cone:

```json
{
  "cone_id": "feature_request_handling",
  "name": "request-handling",             ← YOUR SEMANTIC NAME
  "action": "keep",                       ← keep | merge | split | rename
  "merge_target": null,                   ← if action=merge, target cone_id
  "split_into": null,                     ← if action=split, list of new groupings
  "confidence": "high",                   ← high | medium | low
  "reasoning": "These files collectively implement the request/response cycle...",
  "validation_notes": "Algorithm placed ctx.py and wrappers.py together correctly.",
  "exclusive_files": ["flask/views.py", "flask/ctx.py", "flask/wrappers.py"],
  "layers_within_cone": {{...preserve algorithm output...}},
  "shared_deps": {{...preserve algorithm output...}},
  "exclusive_total_tokens": 8400
}
```

## Rules

- NEVER change the `exclusive_files` list unless you are merging or splitting cones
- NEVER invent dependencies — use only what the dependency graph shows
- If unsure, set `action: "keep"` and `confidence: "low"` with a note
- Algorithm constraint violations are NOT allowed
- Write the full JSON — do not truncate or use "..." placeholders
```

---

### Phase 3: Generate DETAIL Docs (Parallel DETAIL Agents)

**Input:** `05_task_manifest.json` (task assignments)

**Processing Order:** MUST follow DAG topology (leaf nodes first, root nodes last)

**Task Types:**
- `batch` - Multiple small cones packed into one agent
- `single` - One cone per agent
- `split` - Large cone split across multiple agents

**Agent Outputs:**
- `.codebase-docs/{feature_name}/DETAIL.md` (or DETAIL_part1.md, DETAIL_part2.md, etc.)
- `.codebase-analysis/snippets/{cone_id}.md` (200-500 token summary)

**DETAIL Agent Prompt Template:**

```
# Code Documentation Task

## Task Identity

- Task ID: {{task_id}}
- Task type: {{task_type}}   ← batch | single | split
- Feature name: {{feature_name}}
- Output directory: .codebase-docs/{{feature_dir}}/

## Your Role

You are a technical documentation writer. Your job is to read the source files
listed below and produce TWO documents that explain what this feature does:

1. DETAIL.md — comprehensive technical explanation
2. SNIPPET.md — 200-500 token summary for embedding in the project INDEX

You have NO knowledge of other features' implementation details. You know
their names and public interfaces only (provided below as dependency context).

## Feature Context

### Position in Architecture

- Cone name: {{cone_name}}
- DAG layer: {{dag_layer}} of {{total_dag_layers}}
  (Layer 1 = foundational/no-dependencies, Layer N = top-level user-facing)
- Files in this cone: {{file_count}} files

### Files You Must Read and Document

{{#each files_in_cone}}
- {{filepath}}  ({{line_count}} lines, {{estimated_tokens}} tokens)
{{/each}}

### Dependencies (cones this cone imports from)

The following cones are depended upon by {{cone_name}}.
Their SNIPPET summaries are provided for context — do NOT repeat their details.

{{#each dependency_snippets}}
#### {{dep_cone_name}}
```
{{dep_snippet_content}}
```
{{/each}}

{{#if no_dependency_snippets}}
This cone has no upstream dependencies (it is a leaf/foundational component).
{{/if}}

### Dependents (cones that import from this cone)

The following cones USE this cone's interfaces:

{{#each dependent_cone_names}}
- {{this}}
{{/each}}

## Token Budget

- DETAIL.md: max {{detail_token_budget}} tokens
- SNIPPET.md: 200-500 tokens (hard constraint)

The DETAIL budget is {{budget_ratio}}% of source token estimate.

## Output 1: DETAIL.md

Write to: `.codebase-docs/{{feature_dir}}/DETAIL.md`

Use EXACTLY this structure:

```markdown
# {{feature_name}}

## 功能概述

（2-3 句话说明这组代码整体在做什么，针对 AI Agent 读者，聚焦功能用途而非实现细节）

## 核心接口

（列出 5-10 个最重要的函数/类，每个一行签名 + 一行说明）

- `function_name(param: type) -> ReturnType` — 说明
- `class ClassName(BaseClass)` — 说明

## 内部逻辑

（关键流程说明，3-8 个步骤，核心算法和设计决策，用编号列表）

## 设计决策

（为什么选择这种实现方式，有哪些值得注意的权衡）

## 在系统中的位置

- 依赖: {{dependencies_list_formatted}}
- 被使用: {{dependents_list_formatted}}
- 完整架构图请参见: [../OVERVIEW.md](../OVERVIEW.md) 或 [../../INDEX.md](../../INDEX.md)
```

## Output 2: SNIPPET.md

Write to: `.codebase-analysis/snippets/{{cone_id}}.md`

```markdown
## {{cone_name}}

（一段话，3-4 句，说明这个功能的用途、它处理什么输入、产出什么结果）

**核心接口：**
- `key_function_1()` — 简述
- `key_function_2()` — 简述
（最多 5 个，选最重要的）

**系统位置：** DAG 第 {{dag_layer}} 层。
依赖 {{dep_names_comma_separated}}。
被 {{dependent_names_comma_separated}} 使用。
```

## @unit Markup (MANDATORY for multi-file cones)

When `file_count > 1`, your DETAIL.md MUST wrap each source file's content
section with `@unit` fence markers:

<!-- @unit: {filepath} | tokens: {estimated_tokens} -->
### {filename} -- brief description

...documentation content for this file...

<!-- @/unit: {filepath} -->

Rules:
- `{filepath}` is the relative path from project root (e.g., `flask/views.py`)
- `tokens` value is the approximate token count for this section (written chars / 4)
- The **功能概述** and **设计决策** sections go OUTSIDE all @unit markers
  (at the top and bottom of the document)
- Single-file cones (`file_count == 1`) do NOT need @unit markers
- @unit markers are the foundation for Phase 5 Semantic Reorganization split operations
- Nested @unit markers are NOT supported

## Style Constraints (NON-NEGOTIABLE)

1. **Language**: 中文（Chinese）for 功能概述、内部逻辑、设计决策 sections.
   英文（English）for function signatures and technical terms.
2. **Headers**: Use ## for section headers, ### for subsections. NO #### or deeper.
3. **Lists**: Use `-` for unordered lists, `1.` for ordered steps.
4. **Code blocks**: Use triple backticks with language tag (` ```python `).
5. **Length discipline**:
   - 功能概述: EXACTLY 2-3 sentences
   - 核心接口: EXACTLY 5-10 items
   - SNIPPET: MUST be 200-500 tokens
6. **Perspective**: Write for an AI Agent reading the docs before modifying code.
   Focus on "what does this do and what can I call" not "how the code is structured".
7. **No opinions**: Do not say "elegant", "well-designed", "unfortunately".
   Describe facts.
8. **No repetition**: Do not re-describe dependency details already in their SNIPPET.

## Rules

- You MUST read every file listed in "Files You Must Read and Document"
  using available file-reading tools before writing any output
- Do NOT describe other cones' internal implementation
- The "在系统中的位置" section content is FIXED — use the values provided
- If task_type is "split": see additional instructions below
- Stay within token budgets — if running long, trim 设计决策 first, then 内部逻辑 details
```

**Split Task Additional Instructions (only for task_type == "split"):**

```
## 重要：这是一个拆分任务 (Part {{part_number}}/{{total_parts}})

功能 "{{cone_name}}" 的源码超过单 Agent 上下文限制，被拆分为 {{total_parts}} 个部分。

你负责 Part {{part_number}}，对应文件：
{{#each your_files}}
- {{filepath}} ({{line_count}} lines)
{{/each}}

### 其他 Part 的覆盖范围

{{#each sibling_parts}}
**Part {{part_number}} (由其他 Agent 负责):**
- 文件：{{file_list}}
- 主要职责：{{brief_responsibility}}
{{/each}}

### 拆分任务写作规则

1. 你的 DETAIL 文件命名为: `DETAIL_{{part_slug}}.md`
2. 在文件开头写一行: `<!-- Part {{part_number}}/{{total_parts}} of {{cone_name}} -->`
3. 对其他 Part 覆盖的文件，只写一行引用：
   `（{{filename}} 的详细说明请见 [DETAIL_{{other_part_slug}}.md](DETAIL_{{other_part_slug}}.md)）`
4. SNIPPET.md 只由 Part 1 的 Agent 生成，其他 Part 不生成 SNIPPET
5. Part 1 的 SNIPPET 需要概括整个功能（引用所有部分），而不只是 Part 1 的文件
```

---

### Phase 4: Assemble INDEX (INDEX Agent)

**Inputs:**
- `03_feature_cones.json` (architecture structure)
- `.codebase-analysis/snippets/*.md` (all cone summaries)
- `04_file_tokens.json` (per-file token estimates)
- `05_task_manifest.json` (task assignments + document tree structure)

**Outputs:**
- `.codebase-docs/INDEX.md`
- `.codebase-docs/{feature}/OVERVIEW.md` (for cones with sub-components)
- `.codebase-docs/doc-index.json`
- `.codebase-docs/doc-manifest.json` (initial flat structure for Phase 5)

**Key Constraint:** INDEX Agent NEVER reads source code files

**INDEX Agent Prompt Template:**

```
# Architecture Documentation Assembly Task

## Your Role

You are the architect of the final documentation. You assemble the project's
architecture overview from pre-computed data. You do NOT read source code files.
Your inputs are already processed — trust them.

## Input 1: Feature Cones Architecture

```json
{{feature_cones_json}}
```

## Input 2: Feature Summaries (SNIPPET files)

{{#each cone_snippets}}
### SNIPPET: {{cone_name}} ({{cone_id}})

```
{{snippet_content}}
```

{{/each}}

## Input 3: Task Manifest + Token Estimates

```json
{{task_manifest_json}}
```

```json
{{file_tokens_json}}
```

The task manifest (`05_task_manifest.json`) contains task assignments and
`output_files` structure. Use `feature_cones` in each task to determine which
cones map to which tasks. Use `04_file_tokens.json` for per-file token budget info.

For each cone, determine `needs_overview` as follows:
- `needs_overview: true` when the cone has multiple DETAIL files (split tasks)
- `needs_overview: true` when `exclusive_file_count > 3`
- `needs_overview: false` for single-file cones with one DETAIL

## PRE-FLIGHT VALIDATION (Mandatory)

Before writing any document, complete this validation checklist.

### Check 1: SNIPPET Completeness

For each cone in `03_feature_cones.json`, verify a SNIPPET was provided.
Missing SNIPPETs → Mark cone as status: "pending" in doc-index.json.
Write placeholder in INDEX.md: `### {{cone_name}} _(documentation pending)_`
Do NOT fabricate SNIPPET content.

### Check 2: Dependency Edge Consistency

The Mermaid diagram MUST contain EXACTLY the edges from `02_dag.json` (cone-level
edges). Use `edges` array from `02_dag.json` for cone dependency relationships.
DO NOT add edges based on SNIPPET inference.
DO NOT remove edges from the DAG.

### Check 3: Status Field Compliance

Only mark cone as "deprecated"/"experimental" if `03_feature_cones.json`
explicitly sets `status: "deprecated"` or `status: "experimental"`.
Do NOT infer status from SNIPPET content.

### Check 4: OVERVIEW Requirement

Only generate OVERVIEW.md for cones that meet the `needs_overview` criteria
(multiple DETAIL files from split tasks, or `exclusive_file_count > 3`).
Do not add or skip OVERVIEWs beyond these criteria.

## Outputs

### Output 1: INDEX.md

Write to: `.codebase-docs/INDEX.md`

Structure:
1. Project title + one-paragraph description
2. Mermaid dependency diagram (cone-level)
3. Feature list with one-paragraph summaries (from SNIPPETs)
4. Architecture layers breakdown
5. Getting started links to key OVERVIEWs

### Output 2: OVERVIEW.md files

For each cone with `needs_overview: true`:
- Write to: `.codebase-docs/{feature_dir}/OVERVIEW.md`
- Include: Purpose, component breakdown, usage examples, links to DETAIL files

### Output 3: doc-index.json

Write to: `.codebase-docs/doc-index.json`

Schema:
```json
{
  "project_name": "...",
  "generated_at": "ISO-8601",
  "source_file_coverage_percent": 87.5,
  "cones": [
    {
      "cone_id": "request-handling",
      "name": "Request Handling",
      "status": "complete",
      "detail_path": "request-handling/DETAIL.md",
      "snippet_path": "../.codebase-analysis/snippets/cone_request.md",
      "overview_path": "request-handling/OVERVIEW.md",
      "source_files": ["flask/views.py", "flask/ctx.py"],
      "dependencies": ["routing", "helpers"],
      "dependents": ["app-context"]
    }
  ]
}
```

### Output 4: doc-manifest.json (Initial Flat Structure)

Write to: `.codebase-docs/doc-manifest.json`

This file is the Single Source of Truth (SSOT) for document organization. Phase 4
initializes it as a flat structure; Phase 5 iterates it into a hierarchical structure.

Schema:
```json
{
  "version": "2.1",
  "status": "initial",
  "project_id": "{{project_id}}",
  "root_index": ".codebase-docs/INDEX.md",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",

  "details": {
    "<detail_id>": {
      "path": ".codebase-docs/<group>/<DETAIL_filename>.md",
      "source_files": ["<source_file_path_1>", "<source_file_path_2>"],
      "units": ["<source_file_path_1>", "<source_file_path_2>"],
      "tokens": 1200,
      "group": "<group_id>"
    }
  },

  "groups": {
    "<group_id>": {
      "name": "<Human Readable Group Name>",
      "index_path": ".codebase-docs/<group>/INDEX.md",
      "parent": null,
      "detail_ids": ["<detail_id_1>", "<detail_id_2>"],
      "subgroups": []
    }
  },

  "operations_log": []
}
```

Initialization rules:
- `status` MUST be `"initial"` (Phase 5 will transition to `"final"`)
- All `groups[*].parent` values MUST be `null` (flat, no hierarchy)
- All `groups[*].subgroups` arrays MUST be empty
- `details[*].units` is populated from the DETAIL's `@unit` markers
  (for single-file cones without @unit markers, `units` equals `source_files`)
- `details[*].tokens` is estimated from DETAIL character count / 4
- Each group maps to a batch from the task manifest's cone assignments
- `operations_log` is an empty array

## Link Path Rules

| From document | To INDEX.md | To {cone}/OVERVIEW.md | To {cone}/DETAIL.md |
|---------------|-------------|----------------------|---------------------|
| INDEX.md (depth 0) | self | `{cone}/OVERVIEW.md` | `{cone}/DETAIL.md` |
| OVERVIEW.md (depth 1) | `../INDEX.md` | `../{cone}/OVERVIEW.md` | `DETAIL.md` (same dir) |
| DETAIL.md (depth 1) | `../INDEX.md` | `OVERVIEW.md` (same dir) | sibling DETAIL: `./OTHER.md` |
| DETAIL.md (depth 2) | `../../INDEX.md` | `../OVERVIEW.md` | sibling: `./OTHER.md` |

## Style Constraints

1. **No source code** - Do not read or reference source file content
2. **Trust SNIPPETs** - Use SNIPPET content verbatim, do not paraphrase
3. **Consistent linking** - All links must be relative paths from the doc location
4. **Mermaid accuracy** - Diagram edges must match `02_dag.json` edges exactly
5. **Use authoritative field names** - Reference `name` (not `cone_name`),
   `exclusive_files` (not `files`), `exclusive_total_tokens` (not `cone_token_estimate`)
```

---

### Phase 5: Semantic Reorganization (Reorganization INDEX Agents)

**Purpose:** Transform Phase 4's flat, algorithm-derived document structure into a
semantically coherent, hierarchical documentation architecture. The dependency graph
parser cannot resolve all relationships (e.g., cross-package imports, dynamic dispatch).
This produces many "orphan cones" -- for example, Flask's 54 cones include 50 single-file
cones. Only an LLM that has read the actual DETAIL content can make correct reorganization
decisions.

**Core principle:** "Generate first, reorganize later."

**Inputs:**
- All `.codebase-docs/{group}/DETAIL*.md` files (with `@unit` markers)
- Phase 4 batch INDEX.md files
- `.codebase-docs/doc-manifest.json` (status: `"initial"`)
- `02_dag.json` (for Mermaid diagram generation)

**Outputs:**
- Reorganized DETAIL files (moved/merged/split)
- Regenerated group INDEX.md files
- `.codebase-docs/INDEX.md` (final root INDEX)
- `.codebase-docs/doc-manifest.json` (status: `"final"`, hierarchical)

**Key Constraint:** Reorganization INDEX Agents read DETAIL content but NEVER read
source code files. They operate on documentation structure, not on code.

#### Entry Conditions (Phase 4 Completion Flags)

Phase 5 begins when ALL of the following are true:

| Condition | How to check |
|-----------|--------------|
| All Phase 3 DETAIL tasks are `"complete"` in `state.json` | `state.json.tasks[*].status == "complete"` for all DETAIL tasks |
| All Phase 4 INDEX tasks are `"complete"` in `state.json` | `state.json.tasks["index_assembly"].status == "complete"` |
| `doc-manifest.json` exists and is valid JSON | File exists at `.codebase-docs/doc-manifest.json` with `version` field |
| `doc-manifest.json` has `details` and `groups` fields | Both top-level keys exist and are non-empty objects |
| At least one batch INDEX.md exists | At least one `groups[*].index_path` file exists on disk |
| All `details[*].path` files exist on disk | File existence check for every path in manifest |

If any condition is not met, Phase 5 MUST NOT start. Log the failing condition and
return control to the Skill orchestrator.

#### Exit Conditions (Phase 5 Completion Flags)

| Condition | How to verify |
|-----------|---------------|
| `doc-manifest.json` status is `"final"` | `doc-manifest.json.status == "final"` |
| Root `INDEX.md` has been regenerated | `.codebase-docs/INDEX.md` exists and was updated |
| Every `details[*].path` exists on disk | File existence check passes |
| Every `groups[*].index_path` exists on disk | File existence check passes |
| Referential integrity holds | All `group` refs valid, all `detail_ids` valid, all `subgroups` valid |
| `operations_log` exists | Field exists (may be `[]` for no-op) |

#### The Four Reorganization Operations

**Operation 1: Move** -- Transfer an entire DETAIL from one group to another.

When to use: A DETAIL is semantically misplaced in its current group.

Steps:
1. Read `doc-manifest.json`
2. Move file on disk: `mv .codebase-docs/<old-group>/DETAIL_x.md .codebase-docs/<new-group>/DETAIL_x.md`
3. Update manifest: change `details["x"].group` and `details["x"].path`, update both groups' `detail_ids`
4. Update internal relative links in the moved DETAIL (use Link Path Rules above)
5. Append operation record to `operations_log`

**Operation 2: Merge** -- Combine multiple small DETAILs into one.

When to use: Multiple DETAILs < 500 tokens each describe tightly coupled sub-features.
Combined token count must NOT exceed 8000 tokens.

Steps:
1. Read all source DETAIL files
2. Concatenate all @unit blocks (preserving markers and content)
3. LLM writes a new `## 功能概述` section for the merged content
4. Merge `source_files` and `units` arrays (union, deduplicated)
5. Write merged DETAIL; delete original files
6. Update manifest: create new entry, remove old entries, update group's `detail_ids`
7. Append operation record to `operations_log`

Special case for merging single-file DETAILs (no @unit markers):
When merging two DETAILs that lack @unit markers (single-file cones), the merge operation
MUST add @unit markers for each original file's content, since the result is now a
multi-file DETAIL. This is the ONE exception to the "do not add @unit" rule.

**Operation 3: Split** -- Extract @unit blocks from a DETAIL into a new DETAIL.

When to use: A multi-file DETAIL contains @unit blocks belonging to a different domain.

Preconditions: Source DETAIL must have @unit markers. Cannot split a single-file DETAIL.

Steps:
1. Read source DETAIL, locate target @unit block(s) via `<!-- @unit: {filepath}` markers
2. Extract matched content (including markers)
3. Write new DETAIL with extracted @unit block(s), new 功能概述, new 设计决策
4. Update source DETAIL: remove extracted blocks, LLM rewrites 功能概述
5. Update manifest: create new detail entry, update original entry (remove units, reduce tokens)
6. Append operation record to `operations_log`

**Operation 4: Create Group / Dissolve Group**

Create Group: Establish a new group directory with INDEX.md.
Steps: mkdir, LLM writes INDEX.md, add group to manifest, update parent's subgroups.

Dissolve Group: Remove an empty or too-small group, transfer DETAILs to parent.
Steps: Move all DETAILs to parent group, transfer subgroups, delete INDEX.md and directory,
remove group from manifest.

#### @unit Parsing Rules

Phase 5 parses @unit markers to identify splittable segments:

```python
import re

UNIT_PATTERN = re.compile(
    r'(<!-- @unit: (?P<filepath>[^\|]+?)\s*\|\s*tokens:\s*(?P<tokens>\d+)\s*-->)'
    r'(?P<content>.*?)'
    r'(<!-- @/unit: (?P=filepath)\s*-->)',
    re.DOTALL
)
```

Rules:
- Opening and closing @unit tags MUST have matching filepaths (backreference enforced)
- Nested @unit markers are NOT supported
- Content outside all @unit blocks = "global sections" (功能概述, 设计决策, 在系统中的位置)
- DETAILs without @unit markers are atomic -- Phase 5 cannot split them
- If a DETAIL has malformed @unit markers, treat it as atomic and log a warning

#### @unit Usage Per Operation

| Operation | How @unit is used |
|-----------|-------------------|
| **Move** | Entire DETAIL (with all @unit blocks) is moved. No @unit parsing needed. |
| **Merge** | All @unit blocks from source DETAILs are concatenated. Original @unit markers preserved. |
| **Split** | Specific @unit blocks extracted by matching filepath. Extracted content (incl. markers) placed in new DETAIL. Global sections must be regenerated for both files. |
| **Create Group** | Does not interact with @unit markers directly. |

**Invariant**: Phase 5 NEVER modifies the content within @unit markers. It only
moves @unit blocks between DETAIL files. The @unit content remains exactly as
Phase 3 DETAIL Agents wrote it.

#### Bottom-Up Hierarchical Processing Order

Processing order is determined by group hierarchy depth:

```
Level N (deepest):  Leaf groups with no subgroups
Level N-1:          Groups whose only children are Level N groups
...
Level 1:            Groups whose parent is the root
Level 0:            Root INDEX Agent (generates final INDEX.md)
```

Processing sequence:
1. Calculate levels for all groups
2. Sort groups by level DESCENDING (deepest first)
3. For each level (deepest to shallowest):
   a. Spawn Reorganization INDEX Agent for each group at this level (parallel within level)
   b. Each agent reads its group's DETAILs and sibling context
   c. Each agent outputs and executes reorganization plan
   d. Wait for all agents at this level to complete
   e. Merge manifest updates
4. Root INDEX Agent (Level 0):
   a. Read updated manifest
   b. Evaluate cross-group reorganization needs
   c. Generate final `.codebase-docs/INDEX.md`
   d. Set `manifest.status = "final"`
   e. Write final `doc-manifest.json`

#### doc-manifest.json State Transitions

```
Phase 4 Output        Phase 5 Processing         Phase 5 Done
┌──────────┐         ┌──────────────────┐       ┌──────────┐
│ "initial" │────────→│ "reorganizing"   │──────→│ "final"  │
│ flat      │         │ iterative updates│       │ hierarchy│
│ no parent │         │ add parents      │       │ stable   │
│ no subgrp │         │ add subgroups    │       │ verified │
│ ops_log=[]│         │ ops_log grows    │       │ ops_log  │
└──────────┘         └──────────────────┘       └──────────┘
```

Invariants that MUST hold at every state:
1. Every `detail.group` references a valid `groups` key
2. Every ID in `groups[*].detail_ids` references a valid `details` key
3. Every ID in `groups[*].subgroups` references a valid `groups` key
4. No circular parent chains exist
5. Union of all `groups[*].detail_ids` equals the set of all `details` keys
6. Every `details[*].path` file exists on disk
7. Every `groups[*].index_path` file exists on disk (after INDEX regeneration)

#### Reorganization INDEX Agent Prompt Template

```
# Semantic Reorganization Task — {{group_name}}

## Your Role

You are the Reorganization INDEX Agent for the **{{group_name}}** group.
Your responsibility is to review all DETAIL documents assigned to this group,
evaluate their semantic coherence, and reorganize them if needed.

You can read DETAIL content but you MUST NOT read source code files.
You operate on documentation structure, not on code.

## Current Document Manifest

```json
{{current_manifest}}
```

## Batch INDEX Context

The following INDEX documents provide the current organizational structure:

{{batch_index_content}}

## DETAIL Files in Your Group

{{#each detail_files}}
### {{detail_id}} ({{tokens}} tokens, {{unit_count}} units)

**Source files:** {{source_files_list}}

**功能概述 (first paragraph):**
{{first_paragraph}}

**@unit list:**
{{#each units}}
- `{{filepath}}` ({{tokens}} tokens)
{{/each}}
{{/each}}

## Sibling Groups (for context)

{{#each sibling_groups}}
- **{{group_name}}** ({{detail_count}} details): {{brief_description}}
{{/each}}

## Your Task

Analyze the DETAIL documents in your group and determine if reorganization is needed.

### Decision Criteria

1. **Semantic Misplacement**: Does any DETAIL describe functionality that clearly belongs
   to a sibling group? A DETAIL about JSON serialization testing should be in the
   json-serialization group, not the test-suite group.

2. **Redundant Small DETAILs**: Are there multiple DETAILs under 500 tokens that describe
   aspects of the same logical feature? Merge candidates must be in the same group and
   their combined tokens must not exceed 8000.

3. **Cross-Domain @units**: Does any multi-file DETAIL contain @unit blocks where some
   units belong to a completely different functional domain?

4. **Missing Subgroup Structure**: Are there 5+ DETAILs that share a common sub-theme
   that would benefit from a subgroup?

### Decision Priority

1. Do NOT reorganize unless there is a clear semantic reason
2. Prefer Move over Split (simpler operation)
3. Prefer Merge only when both DETAILs are very small (< 500 tokens each)
4. Create subgroups only when there are 3+ DETAILs that clearly belong together
5. Algorithm constraints are inviolable: never merge past 8000 tokens combined

## Output Format

Output a reorganization plan as JSON:

```json
{
  "group": "{{group_id}}",
  "analysis": "Brief 2-3 sentence analysis of the group's current state",
  "operations": [
    {
      "type": "move",
      "detail_id": "<detail_id>",
      "to_group": "<target_group_id>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "merge",
      "detail_ids": ["<id1>", "<id2>"],
      "new_name": "<merged document title>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "split",
      "detail_id": "<detail_id>",
      "extract_units": ["<filepath1>"],
      "to_group": "<target_group_id>",
      "reason": "<1-2 sentence justification>"
    },
    {
      "type": "create_group",
      "group_id": "<new_group_id>",
      "name": "<Human Readable Name>",
      "parent": "<parent_group_id or null>",
      "reason": "<1-2 sentence justification>"
    }
  ]
}
```

If no reorganization is needed, output:
```json
{
  "group": "{{group_id}}",
  "analysis": "All DETAILs are semantically coherent within this group. No changes needed.",
  "operations": []
}
```

## Execution Instructions

After outputting the plan, execute it:

1. **Create Group** operations first (target groups must exist before Move/Split)
2. **Split** operations second (creates new DETAILs that may need moving)
3. **Move** operations third (moves existing and newly split DETAILs)
4. **Merge** operations last (after all moves are done, merge within final groups)
5. After ALL operations: update `doc-manifest.json` with all changes
6. Regenerate this group's INDEX.md to reflect the new structure

## Constraints (NON-NEGOTIABLE)

- Do NOT add, delete, or modify content within @unit markers
- Only move @unit blocks between DETAIL files during Split operations
- After every Split or Merge, regenerate the affected DETAIL's `## 功能概述` section
- Keep @unit internal content exactly as Phase 3 DETAIL Agents wrote it
- Update `doc-manifest.json` after each operation to maintain consistency
- Do NOT read source code files — work only with DETAIL documents
- Do NOT create @unit markers that did not exist in Phase 3 output
  (exception: Merge of single-file DETAILs requires adding @unit markers)
- Combined token count for Merge must not exceed 8000
- Every DETAIL must belong to exactly one group after all operations
- When moving DETAILs, update relative links per the Link Path Rules table

## Style Constraints (Same as All Agents)

1. Language: 中文 for prose sections, English for technical terms/signatures
2. Headers: ## for sections, ### for subsections. No #### or deeper.
3. Mermaid: Use `graph TD`, valid identifiers, max 15 nodes
4. No opinions: Describe facts only
5. No first person: Use third person or imperative
```

#### Template Variable Injection Reference

| Variable | Source | Description |
|----------|--------|-------------|
| `{{group_name}}` | `manifest.groups[group_id].name` | Human-readable group name |
| `{{group_id}}` | Loop variable | Machine ID of the group |
| `{{current_manifest}}` | `doc-manifest.json` file content | Full JSON of current manifest |
| `{{batch_index_content}}` | Read from `groups[*].index_path` files | Concatenated Phase 4 INDEX content |
| `{{detail_files}}` | For each `detail_id` in group: read DETAIL, parse @units | Detail metadata array |
| `{{detail_id}}` | Key from `manifest.details` | Machine ID of each DETAIL |
| `{{tokens}}` | `manifest.details[detail_id].tokens` | Token count of the DETAIL |
| `{{unit_count}}` | `len(manifest.details[detail_id].units)` | Number of @unit blocks |
| `{{source_files_list}}` | `manifest.details[detail_id].source_files` | Comma-separated source paths |
| `{{first_paragraph}}` | Parsed from `## 功能概述` section | First 2-3 sentences |
| `{{units}}` | Parsed via @unit regex from DETAIL file | Array of `{filepath, tokens}` |
| `{{sibling_groups}}` | Groups where `parent == this_group.parent` and `id != this_group_id` | Peer group context |

#### Root INDEX Agent Special Responsibilities

The Root INDEX Agent runs last (after all group-level agents). Additional responsibilities:

1. **Global architecture overview**: Generate final `.codebase-docs/INDEX.md` with:
   - Project title and description
   - Mermaid dependency diagram at group level (edges from `02_dag.json`)
   - Feature list with summaries (from SNIPPET files)
   - Architecture layers breakdown
   - Cross-cutting concerns identification

2. **Empty group cleanup**: Dissolve groups with 0 DETAILs after lower-level reorganization

3. **Top-level grouping assessment**: Determine if top-level groups should be merged
   or if new meta-groups are needed

4. **Final manifest write**: Set `status: "final"` and verify all invariants

5. **Link regeneration**: Ensure all relative links in root INDEX.md point to reorganized structure

#### Error Handling

- **Agent failure**: Re-read `operations_log` to find completed operations. Roll back
  incomplete operations or re-run Phase 4 INDEX assembly to reset to `"initial"` state.
- **@unit parse failure**: Treat DETAIL as atomic (unsplittable). Log warning in
  `operations_log` with `type: "warning"`.
- **Token budget violation**: If Merge would exceed 8000 tokens, do NOT execute.
  Keep as separate DETAILs or create a subgroup with OVERVIEW instead.

---

### Phase 6: Validate (Automated Script)

**Quality Checks:**

```python
check_all_files_exist(doc_manifest)    # All planned docs generated
check_link_integrity(docs_dir)         # Markdown links resolve 100%
check_source_coverage(doc_index_json)  # Source file coverage >= 80%
check_snippet_coverage(feature_cones)  # Every cone has a SNIPPET
check_token_budgets(doc_index_json)    # Docs within budget
check_manifest_integrity(doc_manifest) # doc-manifest.json referential integrity
```

**Output:** `validation_report.json`

---

## MCP Tools Reference (7 Tools)

### 1. analyze_codebase(path, languages, output_dir, force_reindex)

Full analysis pipeline entry point. Writes 5 JSON files + state.json.

**Returns:**
```json
{
  "project_id": "abc123",
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

### 2. get_structure(module, file, function)

Query code structure from `01_structure.json`. Three mutually exclusive modes:
- `module` - Get all files in a cone
- `file` - Get detailed info for a single file
- `function` - Get function signature and dependencies
- None - Return project summary

### 3. get_feature_cones(cone_id)

Query feature cones from `03_feature_cones.json`.
- `cone_id=None` - Return summary list of all cones
- `cone_id="cone_cli"` - Return full details for specific cone

### 4. get_dependency_graph(scope, target, include_weights)

Generate Mermaid dependency graph from `02_dag.json`.
- `scope="project"` - Cone-level dependency graph
- `scope="cone"` - File-level graph within a cone
- `scope="file"` - Direct dependencies of a single file

### 5. get_progress(project_id)

Query task completion status from `state.json`.

**Returns:**
```json
{
  "tasks": {
    "total": 15,
    "pending": 3,
    "in_progress": 2,
    "complete": 10,
    "failed": 0,
    "progress_percent": 66.67
  },
  "documentation": {
    "details_written": 10,
    "snippets_written": 10,
    "source_file_coverage_percent": 78.5
  }
}
```

### 6. get_file_tokens(file, module)

Query file token estimates from `04_file_tokens.json`.
- `file` - Return single file token info
- `module` - Return all files in a cone + aggregate stats
- None - Return all files

### 7. submit_analysis(task_id, detail_paths, snippet_paths, tokens_used, source_files_covered, project_id, manifest_path)

Task completion callback. Called by DETAIL/INDEX Agent after writing docs.
Atomically updates `state.json` with completion status.

**Parameters:**
- `task_id: str` - Required. Task ID from `05_task_manifest.json`
- `detail_paths: list[str]` - Required. Paths to written docs (DETAIL/OVERVIEW/INDEX)
- `snippet_paths: list[str]` - Required. Paths to written SNIPPET files
- `tokens_used: int` - Required. Agent self-reported token consumption
- `source_files_covered: list[str] | None` - Optional. Source files documented
- `project_id: str | None` - Optional. Defaults to most recent `analyze_codebase` result
- `manifest_path: str | None` - Optional. Path to `doc-manifest.json` (Phase 4/5)

**Returns:**
```json
{
  "status": "success",
  "task_id": "task_abc",
  "tasks_remaining": 5,
  "progress_percent": 66.67,
  "source_file_coverage_percent": 78.5
}
```

---

## Usage Examples

### Example 1: Full Documentation Generation

```
User: Generate architecture docs for the Flask codebase

1. Phase 1: Call analyze_codebase(path="/path/to/flask")
   → Returns: {"feature_cones_found": 7, "task_count": 12}

2. Phase 2: Spawn Validator Agent
   → Reviews 03_feature_cones.json
   → Updates cone names, flags issues
   → Writes updated 03_feature_cones.json

3. Phase 3: Read 05_task_manifest.json
   → Get task queue (batch/single/split tasks)
   → Spawn DETAIL Agents (parallel, DAG order)
   → Each agent reads assigned files
   → Writes DETAIL.md (with @unit markers) + SNIPPET.md
   → Calls submit_analysis()

4. Check get_progress() until all DETAIL tasks complete

5. Phase 4: Spawn INDEX Agent
   → Reads all SNIPPETs + 03_feature_cones.json
   → Writes batch INDEX.md + OVERVIEWs + doc-index.json
   → Initializes doc-manifest.json (flat structure)

6. Phase 5: Spawn Reorganization INDEX Agents (bottom-up)
   → Level N agents process deepest groups first (parallel within level)
   → Each agent evaluates semantic coherence of DETAILs
   → Executes Move/Merge/Split/Create Group operations
   → Root INDEX Agent generates final INDEX.md
   → Writes doc-manifest.json (status: "final")

7. Phase 6: Run validation script
   → Checks links, coverage, budgets, manifest integrity
   → Writes validation_report.json

Output: .codebase-docs/ directory with semantically organized documentation
```

### Example 2: Resume Interrupted Session

```
User: Continue the previous documentation generation

1. Call get_progress()
   → Check state.json for pending/in_progress tasks

2. Read 05_task_manifest.json
   → Get remaining tasks

3. Spawn DETAIL Agents for remaining tasks
   → Continue from where we left off

4. Complete workflow as normal
```

### Example 3: Query Without Generating Docs

```
User: Show me the feature structure of this codebase

1. Call analyze_codebase(path="/path/to/project")
   → Get 5 JSON files

2. Call get_feature_cones()
   → Return summary of all cones

3. Call get_dependency_graph(scope="project")
   → Return Mermaid diagram of cone dependencies

(No agent spawning, no doc generation)
```

---

## Troubleshooting

### Problem: analyze_codebase returns 0 feature cones

**Cause:** Codebase may have circular dependencies that prevent cone extraction

**Solution:**
1. Check `01_structure.json` for file count
2. Check `02_dag.json` for circular_deps field
3. If circular deps exist, may need manual cone assignment

### Problem: DETAIL Agent exceeds token budget

**Cause:** Source files larger than expected

**Solution:**
1. Task manifest should have created split task
2. If not, manually split cone in `03_feature_cones.json`
3. Re-run Phase 3 with updated manifest

### Problem: Links in INDEX.md are broken

**Cause:** Incorrect relative path calculation

**Solution:**
1. Check INDEX Agent followed link path rules
2. Verify DETAIL files exist at expected locations
3. Run validation script to identify broken links

### Problem: Source file coverage < 80%

**Cause:** Some cones not documented

**Solution:**
1. Call get_progress() to find pending tasks
2. Spawn remaining DETAIL Agents
3. Ensure all cones have SNIPPET files

---

## Best Practices

1. **Always run analyze_codebase first** - Generates required JSON files
2. **Follow DAG order** - Process cones from leaf to root in Phase 3
3. **Monitor progress** - Use get_progress() to track completion
4. **Use @unit markers** - Multi-file cones MUST have @unit markers for Phase 5
5. **Initialize doc-manifest.json** - Phase 4 creates the flat structure for Phase 5
6. **Reorganize bottom-up** - Phase 5 processes deepest groups first
7. **Validate after reorganization** - Run Phase 6 validation script
8. **Handle large cones** - Split tasks prevent context overflow
9. **Resume gracefully** - state.json enables session recovery

---

## Architecture Principles

1. **Separation of Concerns**
   - MCP Server: Deterministic analysis (no LLM)
   - Skill: Orchestration (no LLM decisions)
   - Agents: Semantic understanding + doc writing (LLM)
   - Phase 5: Semantic reorganization (LLM reads docs, not source code)

2. **Progressive Disclosure**
   - INDEX.md: Project overview
   - OVERVIEW.md: Component summaries
   - DETAIL.md: Implementation details
   - Depth adapts to complexity

3. **Token Awareness**
   - Chars ÷ 4 estimation (< 15% error)
   - Bin packing for task distribution
   - Split tasks for large cones

4. **Idempotency**
   - JSON files can be regenerated
   - state.json tracks progress
   - Resume from interruption

---

## References

For detailed algorithm documentation, see:
- `optimization_prompts/results/02a_code_analysis_v2.md` - Algorithm design
- `optimization_prompts/results/02c_responsibility_v2.md` - Tool API signatures
- `optimization_prompts/results/03_final_progressive_scheme.md` - Final specification
