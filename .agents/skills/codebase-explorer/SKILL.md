---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive-disclosure architecture
  documentation using MCP tools (V2). Uses feature cone extraction for module
  grouping and token-aware task planning. LLM agents write documentation directly
  (no Jinja2 templates). Produces INDEX.md, OVERVIEW.md, and DETAIL.md files
  adapted to module complexity. Use for architecture documentation, code
  exploration, dependency visualization, or generating docs. Triggers on
  "architecture docs", "module overview", "code map", "dependency graph",
  "codebase analysis", or "generate docs".
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

## 5-Phase Workflow

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
- Assign semantic `cone_name` for each cone
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
- Cones with `cone_token_estimate > 30000`: Flag as "too large" (split candidate)
- Cones with `cone_token_estimate < 500`: Flag as "too small" (merge candidate)
- Algorithm constraint: Do NOT suggest merging two cones whose combined tokens exceed 30000

### 4. Naming Quality
- Is the cone name `cone_N`? Suggest a semantic name.
- Does the name reflect the PRIMARY function?

## What You MUST Do

1. For each cone: assign a semantic `cone_name`
2. For cones with problems: specify `action: "merge" | "split" | "rename" | "keep"`
3. Write your final judgment directly into the updated JSON structure
4. For each change, write a brief `reasoning` field (1-2 sentences)
5. Preserve all algorithm-set fields (especially `files`, `layers`, `dependency_edges`)

## Output Format

Output the COMPLETE updated `03_feature_cones.json` with your changes applied.

Use this schema for each cone:

```json
{
  "cone_id": "cone_0",
  "cone_name": "request-handling",       ← YOUR SEMANTIC NAME
  "action": "keep",                       ← keep | merge | split | rename
  "merge_target": null,                   ← if action=merge, target cone_id
  "split_into": null,                     ← if action=split, list of new groupings
  "confidence": "high",                   ← high | medium | low
  "reasoning": "These files collectively implement the request/response cycle...",
  "validation_notes": "Algorithm placed ctx.py and wrappers.py together correctly.",
  "files": ["flask/views.py", "flask/ctx.py", "flask/wrappers.py"],
  "layers": {{...preserve algorithm output...}},
  "dependency_edges": {{...preserve algorithm output...}},
  "cone_token_estimate": 8400
}
```

## Rules

- NEVER change the `files` list unless you are merging or splitting cones
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
- `04_doc_plan.json` (document tree structure)

**Outputs:**
- `.codebase-docs/INDEX.md`
- `.codebase-docs/{feature}/OVERVIEW.md` (for cones with sub-components)
- `.codebase-docs/doc-index.json`

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

## Input 3: Document Plan

```json
{{doc_plan_json}}
```

## PRE-FLIGHT VALIDATION (Mandatory)

Before writing any document, complete this validation checklist.

### Check 1: SNIPPET Completeness

For each cone in `03_feature_cones.json`, verify a SNIPPET was provided.
Missing SNIPPETs → Mark cone as status: "pending" in doc-index.json.
Write placeholder in INDEX.md: `### {{cone_name}} _(documentation pending)_`
Do NOT fabricate SNIPPET content.

### Check 2: Dependency Edge Consistency

The Mermaid diagram MUST contain EXACTLY the edges in `dependency_map`.
DO NOT add edges based on SNIPPET inference.
DO NOT remove edges from `dependency_map`.

### Check 3: Status Field Compliance

Only mark cone as "deprecated"/"experimental" if `03_feature_cones.json`
explicitly sets `status: "deprecated"` or `status: "experimental"`.
Do NOT infer status from SNIPPET content.

### Check 4: OVERVIEW Requirement

Only generate OVERVIEW.md for cones where `doc_plan.needs_overview: true`.
Do not add or skip OVERVIEWs.

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
      "cone_name": "Request Handling",
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

## Style Constraints

1. **No source code** - Do not read or reference source file content
2. **Trust SNIPPETs** - Use SNIPPET content verbatim, do not paraphrase
3. **Consistent linking** - All links must be relative paths from the doc location
4. **Mermaid accuracy** - Diagram edges must match `dependency_map` exactly
```

---

### Phase 5: Validate (Automated Script)

**Quality Checks:**

```python
check_all_files_exist(doc_plan)        # All planned docs generated
check_link_integrity(docs_dir)         # Markdown links resolve 100%
check_source_coverage(doc_index_json)  # Source file coverage >= 80%
check_snippet_coverage(feature_cones)  # Every cone has a SNIPPET
check_token_budgets(doc_index_json)    # Docs within budget
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

### 7. submit_analysis(task_id, detail_paths, snippet_paths, tokens_used, source_files_covered)

Task completion callback. Called by DETAIL Agent after writing docs.
Atomically updates `state.json` with completion status.

**Returns:**
```json
{
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

1. Call analyze_codebase(path="/path/to/flask")
   → Returns: {"feature_cones_found": 7, "task_count": 12}

2. Spawn Validator Agent
   → Reviews 03_feature_cones.json
   → Updates cone names, flags issues
   → Writes updated 03_feature_cones.json

3. Read 05_task_manifest.json
   → Get task queue (batch/single/split tasks)

4. Spawn DETAIL Agents (parallel, DAG order)
   → Each agent reads assigned files
   → Writes DETAIL.md + SNIPPET.md
   → Calls submit_analysis()

5. Check get_progress() until all tasks complete

6. Spawn INDEX Agent
   → Reads all SNIPPETs
   → Writes INDEX.md + OVERVIEWs + doc-index.json

7. Run validation script
   → Checks links, coverage, budgets
   → Writes validation_report.json

Output: .codebase-docs/ directory with complete documentation
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
2. **Follow DAG order** - Process cones from leaf to root
3. **Monitor progress** - Use get_progress() to track completion
4. **Validate after generation** - Run Phase 5 validation script
5. **Handle large cones** - Split tasks prevent context overflow
6. **Resume gracefully** - state.json enables session recovery

---

## Architecture Principles

1. **Separation of Concerns**
   - MCP Server: Deterministic analysis (no LLM)
   - Skill: Orchestration (no LLM decisions)
   - Agents: Semantic understanding + doc writing (LLM)

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
