# Skill 设计优化 V2

> 本文档基于 T-01（当前架构说明）、核心需求（00_vision_and_requirements.md）和 V1 Skill 设计（02_skill_design.md）产出。
> 禁止修改本文件（只读参考）。

---

## 1. V1→V2 改进摘要

### V1 的核心问题

V1 Skill 在设计上存在三处根本性错误，导致 E2E 测试全部失败：

| 问题 | V1 现状 | 根因 |
|------|---------|------|
| 文档内容空洞 | DETAIL.md 只有 Jinja2 骨架，Token 使用率 5-29% | MCP `generate_doc()` 不调用 LLM，Agent 没有读源码工具 |
| 链接断裂 85% | 52/61 条链接失效 | `make_relative_link()` 没有按文档深度计算 `../` 前缀 |
| 覆盖率 0% | `doc-index.json` 的 `source_files` 字段为空 | `build_doc_index()` 未传递 `source_files` 列表 |

### V2 的核心改变

1. **职责重新划分**：MCP Server 只做确定性计算（解析、图算法、Token 估算），输出 JSON 文件。Agent 做语义理解（阅读源码、撰写文档、审查合理性）。
2. **删除 Jinja2 生成器**：`generate_doc()` 工具从 MCP 中移除，文档由 DETAIL Agent 直接用 Markdown 写出。
3. **新增 `get_file_content()` 工具**：让 DETAIL Agent 有能力通过 MCP 读取源文件内容。
4. **完整 Prompt 模板**：V1 缺少完整的 Validator、DETAIL、INDEX Agent Prompt 模板，V2 全部补齐。
5. **Split 任务策略改为 Option C**：大型功能锥体不合并，每个部分独立成一个 DETAIL 文件，OVERVIEW.md 统一链接。
6. **完整 doc-index.json Schema**：支持链接校验、覆盖率计算、断点恢复三大用途。

---

## 2. 精化的 5-Phase 工作流

```
Phase 1: Index（MCP 自动执行）
    ↓ 产出: 01_structure.json, 02_dependency_graph.json
Phase 2: Validate Structure（Validator Agent，单 Agent）
    ↓ 产出: 03_feature_cones.json（含审查意见），04_doc_plan.json
Phase 3: Generate DETAIL Docs（DETAIL Agents，并行）
    ↓ 产出: {feature}/DETAIL*.md + {feature}/SNIPPET.md
Phase 4: Assemble INDEX（INDEX Agent，单 Agent）
    ↓ 产出: INDEX.md + */OVERVIEW.md + doc-index.json
Phase 5: Validate（自动脚本）
    ↓ 产出: validation_report.json
```

### Phase 1: Index（MCP 自动）

**调用序列：**

```
analyze_codebase(path) →
    parse_with_graph_sitter() →
    build_weighted_dependency_graph() →  # import + call + inheritance
    extract_sccs() →                     # 强连通分量
    dag_layering() →                     # 拓扑分层
    louvain_grouping() →                 # 同层横向分组（fallback）
    estimate_tokens_per_cone() →
    build_task_manifest()
```

**产出文件（全部写到 `.codebase-analysis/`）：**

- `01_structure.json`：文件列表 + 函数/类元数据
- `02_dependency_graph.json`：加权有向边（import/call/inherit）+ Mermaid 图
- `03_feature_cones.json`（初稿，待 Phase 2 审查）：锥体分组 + 层级结构
- `04_doc_plan.json`：每个锥体的文档预算 + 分割策略
- `05_task_manifest.json`：Agent 任务清单（batch/single/split 类型）

**质量门控：** `01_structure.json` 的 `file_count > 0` 且 `03_feature_cones.json` 存在后才能进入 Phase 2。

### Phase 2: Validate Structure（Validator Agent）

**输入：** `03_feature_cones.json`（MCP 算法产出的初稿）
**行为：** Validator Agent 读取分组，从语义视角评估每个锥体的合理性，输出建议。
**产出：** 更新后的 `03_feature_cones.json`（Agent 直接修改，见第 3 节权威性决策）

**异常处理路径：**

```
Validator 建议 merge → 检查两个锥体是否有 >60% 公共依赖文件
    YES → 执行 merge，更新 03_feature_cones.json
    NO  → 保留原分组，记录 disagreement 到 validation_notes

Validator 建议 split → 检查目标锥体 token 数是否 > 30k
    YES → 执行 split，更新 04_doc_plan.json 中分割策略
    NO  → 保留原分组，记录 disagreement 到 validation_notes
```

### Phase 3: Generate DETAIL Docs（并行 DETAIL Agents）

**并行策略：**

- `batch` 类型任务：多个小锥体打包给单个 Agent
- `single` 类型任务：一个锥体一个 Agent
- `split` 类型任务：一个锥体拆分给多个 Agent，每个 Agent 负责部分文件

**处理顺序（关键）：** 必须按 DAG 拓扑顺序，从叶节点（无依赖的锥体）开始，向根节点推进。目的：当依赖锥体的 Agent 运行时，其依赖的锥体的 SNIPPET.md 已经存在，可以注入上下文。

**产出：**

- `.codebase-docs/{feature_name}/DETAIL.md`（或 DETAIL_part1.md, DETAIL_views.md 等）
- `.codebase-analysis/snippets/{cone_id}.md`（SNIPPET 文件，用于 Phase 4 注入）

### Phase 4: Assemble INDEX（单 INDEX Agent）

**输入：**

- `03_feature_cones.json`（架构结构，Phase 2 确认）
- 所有 `.codebase-analysis/snippets/*.md`
- `04_doc_plan.json`（文档树结构）

**输出：**

- `.codebase-docs/INDEX.md`
- `.codebase-docs/{feature}/OVERVIEW.md`（有子组件的锥体）
- `.codebase-docs/doc-index.json`

**约束：** INDEX Agent 不读任何源码文件。所有内容来自 SNIPPET 文件和 feature_cones.json。

### Phase 5: Validate（自动脚本）

**检查项：**

```python
check_all_files_exist(doc_plan)        # 所有计划文档已生成
check_link_integrity(docs_dir)         # Markdown 链接解析 100%
check_source_coverage(doc_index_json)  # 源文件覆盖率 >= 80%
check_snippet_coverage(feature_cones)  # 每个锥体都有 SNIPPET
check_token_budgets(doc_index_json)    # 文档在预算内
```

---

## 3. Validator Agent（Phase 2）完整 Prompt 模板

### 权威性决策：Option B（Agent 直接修改）

**选择 Option B 的理由：**

V1 设计提出的 Option A（Validator 只建议，Skill 编排者决定是否执行）在实践中存在问题：当 Skill 编排者是同一个 Claude 进程时，"决定是否执行"这个动作本质上是再次调用 LLM 的判断，等于把语义判断责任推给了编排层而不是专责 Agent。这导致职责模糊。

Option B（Validator 直接修改 `03_feature_cones.json`）的好处：

1. **幂等性**：Validator 写出的文件是最终结构，后续 Phase 只读不写该文件，避免并发冲突。
2. **可审计**：修改前后的 diff 可以用 git 追踪，人工审查时清晰可见。
3. **明确的权威归属**：`03_feature_cones.json` 的所有者从"算法产出"变成"算法 + 语义审查的联合产出"，语义合理性由 Validator 负责，Skill 编排者不再介入语义判断。

**冲突解决规则（两轮 Validator 结果矛盾）：**

若系统运行两轮验证（如用户主动触发重新验证），采用以下优先级规则：

> **规则：第二轮 Validator 的意见优先，除非第一轮有明确的 `confidence: high` 标注且第二轮没有提供新证据（仅凭感觉）。**

实操规则：

1. 第一轮结果写入 `03_feature_cones.json`，同时保留 `validation_notes` 字段记录建议理由
2. 第二轮 Validator 读取第一轮结果（含 `validation_notes`）
3. 第二轮若 merge 某个已被第一轮 split 的锥体：检查两个锥体的 `cone_token_estimate` 之和是否 > 30k，若超过则锥体应保持分割状态（算法规则优先于语义偏好）
4. 算法约束（token 上限、依赖边数量）具有最高优先级，Validator 建议不能违反算法约束

### Validator Agent Prompt 模板

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
- Project description (if known): {{project_description}}

## Dependency Graph Summary

The following Mermaid diagram shows how files depend on each other:

```mermaid
{{dependency_mermaid}}
```

## Validation Criteria

For each feature cone, evaluate:

### 1. Semantic Cohesion (most important)
- Do the files in this cone serve a single recognizable purpose?
- Would a developer intuitively group these files together?
- Is the cone name descriptive and accurate?

### 2. Dependency Boundary Integrity
- Does the cone contain both "caller" and "callee" files where they could be separated?
- Are there files that clearly belong to a DIFFERENT cone by function but are
  grouped here due to import topology?

### 3. Size Appropriateness
- Cones with `cone_token_estimate > 30000`: Flag as "too large" (split candidate)
- Cones with `cone_token_estimate < 500` AND `file_count == 1`: Flag as "too small" (merge candidate)
- Algorithm constraint: Do NOT suggest merging two cones whose combined tokens exceed 30000

### 4. Naming Quality
- Is the cone name `cone_N` or similarly opaque? Suggest a semantic name.
- Does the name reflect the PRIMARY function (not implementation detail)?

## What You MUST Do

1. For each cone: assign a semantic `cone_name` (replacing `cone_0`, `cone_1`, etc.)
2. For cones with problems: specify `action: "merge" | "split" | "rename" | "keep"`
3. Write your final judgment directly into the updated JSON structure
4. For each change, write a brief `reasoning` field (1-2 sentences)
5. Preserve all fields that the algorithm set (especially `files`, `layers`,
   `dependency_edges`, `cone_token_estimate`) — only update `cone_name`,
   `action`, `validation_notes`, and `confidence`

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
- If unsure about a grouping, set `action: "keep"` and `confidence: "low"`
  with a note — do not make uncertain changes
- Algorithm constraint violations are NOT allowed:
  - A single cone MUST NOT exceed 50000 tokens (hard limit)
  - A merge result MUST NOT exceed 30000 tokens
- Write the full JSON — do not truncate or use "..." placeholders
```

---

## 4. DETAIL Agent Prompt 模板（含所有注入变量）

### 依赖顺序的含义

DETAIL Agent **不需要**知道整个项目结构。它只需要：

1. 自己的锥体数据（文件列表、层级结构、Token 预算）
2. 直接依赖锥体的 SNIPPET（如果已经生成）
3. 直接被依赖锥体的名字（但不需要其完整 DETAIL，防止上下文溢出）

这意味着任务调度必须按 DAG 拓扑顺序处理锥体：叶节点（无依赖）优先，根节点（被最多锥体依赖）最后。当一个 Agent 处理锥体 X 时，锥体 X 所依赖的所有锥体（Y, Z, ...）的 SNIPPET 必须已经写到磁盘，可以注入。

### 完整 DETAIL Agent Prompt 模板

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
Their SNIPPET summaries are provided for context — do NOT repeat their details in your DETAIL.md.

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

The following cones USE this cone's interfaces. Name them in your "System Position" section:

{{#each dependent_cone_names}}
- {{this}}
{{/each}}

## Token Budget

- DETAIL.md: max {{detail_token_budget}} tokens
- SNIPPET.md: 200-500 tokens (hard constraint — this will be embedded elsewhere)

The DETAIL budget is calculated as {{budget_ratio}}% of the source token estimate
({{source_token_estimate}} source tokens × {{budget_ratio}}% = {{detail_token_budget}}).

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

## Style Constraints

These constraints are NON-NEGOTIABLE for output consistency across parallel agents:

1. **Language**: 中文（Chinese）for 功能概述、内部逻辑、设计决策 sections.
   英文（English）for function signatures and technical terms.
2. **Headers**: Use ## for section headers, ### for subsections. NO #### or deeper.
3. **Lists**: Use `-` for unordered lists, `1.` for ordered steps.
4. **Code blocks**: Use triple backticks with language tag (` ```python `).
5. **Length discipline**:
   - 功能概述: EXACTLY 2-3 sentences, no more
   - 核心接口: EXACTLY 5-10 items, no more, no fewer
   - SNIPPET: MUST be 200-500 tokens
6. **Perspective**: Write for an AI Agent reading the docs before modifying code.
   Focus on "what does this do and what can I call" not "how the code is structured".
7. **No opinions**: Do not say "elegant", "well-designed", "unfortunately".
   Describe facts.
8. **No repetition**: Do not re-describe dependency details already in their SNIPPET.
   One-line reference is sufficient.

## Rules

- You MUST read every file listed in "Files You Must Read and Document"
  using the available file-reading tools before writing any output
- Do NOT describe other cones' internal implementation (you don't have access anyway)
- The "在系统中的位置" section content is FIXED — use the values provided in
  `{{dependencies_list_formatted}}` and `{{dependents_list_formatted}}`, do not modify
- If task_type is "split": see additional instructions below
- Stay within token budgets — if running long, trim 设计决策 first, then 内部逻辑 details
```

### Split 任务附加说明（仅当 task_type == "split" 时注入）

```
## 重要：这是一个拆分任务 (Part {{part_number}}/{{total_parts}})

功能 "{{cone_name}}" 的源码超过单 Agent 上下文限制，被拆分为 {{total_parts}} 个部分。

你负责 Part {{part_number}}，对应文件：
{{#each your_files}}
- {{filepath}} ({{line_count}} lines)
{{/each}}

### 其他 Part 的覆盖范围（兄弟摘要）

{{#each sibling_parts}}
**Part {{part_number}} (由其他 Agent 负责):**
- 文件：{{file_list}}
- 主要职责：{{brief_responsibility}}
  （由 task_manifest 预先描述，基于文件名和行数估算）
{{/each}}

### 拆分任务写作规则

1. 你的 DETAIL 文件命名为: `DETAIL_{{part_slug}}.md`
   （例如：DETAIL_views.md, DETAIL_ctx.md, DETAIL_wrappers.md）
2. 在文件开头写一行: `<!-- Part {{part_number}}/{{total_parts}} of {{cone_name}} -->`
3. 对其他 Part 覆盖的文件，只写一行引用：
   `（{{filename}} 的详细说明请见 [DETAIL_{{other_part_slug}}.md](DETAIL_{{other_part_slug}}.md)）`
4. SNIPPET.md 只由 Part 1 的 Agent 生成，其他 Part 不生成 SNIPPET
5. Part 1 的 SNIPPET 需要概括整个功能（引用所有部分），而不只是 Part 1 的文件
```

---

## 5. INDEX Agent Prompt 模板（含一致性验证规则）

### INDEX Agent 的核心约束

INDEX Agent 永远不读源码。它只有三类输入：

1. `03_feature_cones.json`：架构骨架（谁依赖谁、层级结构）
2. `snippets/*.md`：每个锥体的 200-500 token 摘要
3. `04_doc_plan.json`：文档树结构（哪些锥体需要 OVERVIEW，哪些只有 DETAIL）

### 完整 INDEX Agent Prompt 模板

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

## PRE-FLIGHT VALIDATION (Mandatory Before Writing Anything)

Before writing any document, complete this validation checklist.
If any check fails, output the failure as a WARNING at the top of your response
and handle the missing item as specified.

### Check 1: SNIPPET Completeness

For each cone in `03_feature_cones.json`, verify a SNIPPET was provided above.

Missing SNIPPETs → Mark the cone as status: "pending" in doc-index.json.
Write a placeholder in INDEX.md:
```
### {{cone_name}} _(documentation pending)_
```
Do NOT fabricate SNIPPET content.

### Check 2: Dependency Edge Consistency

The Mermaid dependency diagram you will generate in INDEX.md MUST contain
EXACTLY the edges listed in `dependency_map` within `03_feature_cones.json`.
Rule: DO NOT add edges based on what you infer from SNIPPET content.
Rule: DO NOT remove edges that appear in `dependency_map` even if SNIPPETs
don't mention them.

Verify: Count of Mermaid edges == count of entries in `dependency_map`. If
mismatch, recount before finalizing.

### Check 3: Status Field Compliance

Only mark a cone as "deprecated" or "experimental" in INDEX.md if the
`03_feature_cones.json` explicitly sets `status: "deprecated"` or
`status: "experimental"` for that cone. Do NOT infer status from SNIPPET content.

### Check 4: OVERVIEW Requirement

Only generate OVERVIEW.md for cones where `doc_plan.needs_overview: true`
in `04_doc_plan.json`. Do not add or skip OVERVIEWs.

## Outputs

### Output 1: INDEX.md

Write to: `.codebase-docs/INDEX.md`
Token budget: max {{index_token_budget}} tokens (typically 3000)

Structure:

```markdown
# {{project_name}}

## 架构概览

（一段话，3-5 句，描述项目整体功能和主要技术）

```mermaid
{{GENERATE_FROM_dependency_map_IN_feature_cones_json}}
```

## 核心功能

（按 DAG 层级排列，从高层用户功能到底层基础设施）

{{#each cones_by_layer_desc}}
### {{cone_name}}

{{embed_snippet_content}}

→ [详细说明]({{detail_link}})

{{/each}}

## 共享基础设施

（仅列出 is_shared_utility: true 的锥体）

## 典型数据流

（描述一个典型的端到端请求/操作如何流经这些功能层）
```

### Output 2: Per-Feature OVERVIEW.md

For each cone where `doc_plan.needs_overview: true`:

Write to: `.codebase-docs/{{feature_dir}}/OVERVIEW.md`
Token budget: max {{overview_token_budget}} tokens (typically 1500)

```markdown
# {{cone_name}} 功能概览

## 功能定位

（本功能在整个项目中的作用，2-3 句）

## 组件列表

（列出本功能包含的所有 DETAIL 文档，附一句说明）

- [DETAIL_views.md](DETAIL_views.md) — 请求入口层
- [DETAIL_ctx.md](DETAIL_ctx.md) — 上下文管理

## 内部依赖关系

```mermaid
（仅显示本功能内部文件之间的依赖，从 02_dependency_graph.json 取子图）
```

## 与其他功能的接口

- 依赖: {{dep_cones}}
- 被使用: {{dependent_cones}}

→ [返回项目 INDEX](../INDEX.md)
```

### Output 3: doc-index.json

Write to: `.codebase-docs/doc-index.json`

See Section 7 for complete schema.

## Style Constraints (Same as DETAIL Agent)

1. Language: 中文 for prose sections, English for technical terms/signatures
2. Headers: ## for sections, ### for subsections
3. Mermaid: Use `graph TD` direction, node IDs must be valid identifiers
4. Cone names: Use the `cone_name` field from `03_feature_cones.json`, not `cone_id`
5. Links: ALL links must be relative paths. Calculate `../` prefixes based on
   file depth. INDEX.md is at depth 0, OVERVIEW.md at depth 1, DETAIL.md at depth 1 or 2.
6. No code examples: INDEX and OVERVIEW do not contain code snippets
7. No internal implementation details: Those belong in DETAIL only

## Link Path Rules (Prevents the V1 Link Failure)

| From document | To INDEX.md | To {cone}/OVERVIEW.md | To {cone}/DETAIL.md |
|---------------|-------------|----------------------|---------------------|
| INDEX.md (depth 0) | self | `{cone}/OVERVIEW.md` | `{cone}/DETAIL.md` |
| OVERVIEW.md (depth 1) | `../INDEX.md` | `../{cone}/OVERVIEW.md` | `DETAIL.md` (same dir) |
| DETAIL.md (depth 1) | `../INDEX.md` | `OVERVIEW.md` (same dir) | sibling DETAIL: `./OTHER.md` |
| DETAIL.md (depth 2) | `../../INDEX.md` | `../OVERVIEW.md` | sibling: `./OTHER.md` |

When writing any `[text](path)` link, check against this table first.

## Rules

- NEVER read source code files — all needed information is in your inputs
- NEVER fabricate cone dependencies not in `dependency_map`
- NEVER copy full DETAIL content into INDEX — embed SNIPPETs only
- Complete the Pre-Flight Validation checklist before writing any output
- If a SNIPPET is missing, write the "pending" placeholder — do NOT estimate content
```

---

## 6. Split 任务处理策略（Option C + 文件命名规范）

### 决策：Option C（无需合并，每部分独立成文件）

**选择 Option C 的理由：**

Option A（Dedicated Merge Agent）引入了额外的串行等待步骤：所有部分完成后必须等待 Merge Agent，这破坏了并行性的优势，并且 Merge Agent 面临的上下文量和单 Agent 处理整个锥体一样大。

Option B（INDEX Agent 负责合并）让 INDEX Agent 承担了源码理解的职责，违反了"INDEX Agent 不读源码"的核心约束。

Option C 的优势：

1. **无额外等待**：每个部分完成即可写入磁盘，Phase 4 直接使用
2. **独立可读**：每个 DETAIL 文件自成体系，读者可以只读自己关心的部分
3. **OVERVIEW 承担导航**：通过 OVERVIEW.md 的组件列表链接，读者能找到所有子文档

### 文件命名规范

**命名原则：** 使用描述性名称，不使用 `part_1`、`part_2` 这类纯序号。名称来源优先级：

1. 子目录名（如果锥体内文件按目录分布）
2. 主要类名（如果按类拆分）
3. 功能语义（如 `routing`、`ctx`、`serialization`）
4. fallback：文件名去掉扩展名（如 `views`、`ctx`、`wrappers`）

**命名格式：**

```
DETAIL_{slug}.md
```

其中 `{slug}` 是英文小写、连字符分隔的语义标签。

**示例（Flask request-handling 锥体拆分）：**

```
.codebase-docs/request-handling/
├── OVERVIEW.md          ← INDEX Agent 生成，列出所有 DETAIL 子文件
├── DETAIL_views.md      ← Part 1: flask/views.py (入口层)
├── DETAIL_ctx.md        ← Part 2: flask/ctx.py (上下文管理)
└── DETAIL_wrappers.md   ← Part 3: flask/wrappers.py (请求/响应封装)
```

**OVERVIEW.md 如何引用拆分部分：**

```markdown
## 组件列表

本功能被拆分为以下详细文档：

| 组件 | 文件 | 职责 |
|------|------|------|
| [DETAIL_views.md](DETAIL_views.md) | `flask/views.py` | 请求路由入口，MethodView 基类 |
| [DETAIL_ctx.md](DETAIL_ctx.md) | `flask/ctx.py` | 请求上下文和应用上下文管理 |
| [DETAIL_wrappers.md](DETAIL_wrappers.md) | `flask/wrappers.py` | Request/Response 对象封装 |
```

### 兄弟摘要注入格式

当拆分任务的 Agent 需要知道其他部分在覆盖什么，`05_task_manifest.json` 中的 `sibling_summary` 字段格式如下：

```json
{
  "task_id": "request-handling-split-2",
  "cone_id": "cone_0",
  "cone_name": "request-handling",
  "task_type": "split",
  "part_number": 2,
  "total_parts": 3,
  "part_slug": "ctx",
  "your_files": ["flask/ctx.py"],
  "sibling_parts": [
    {
      "part_number": 1,
      "part_slug": "views",
      "file_list": ["flask/views.py"],
      "brief_responsibility": "HTTP method dispatching and URL routing entry point. Defines MethodView base class."
    },
    {
      "part_number": 3,
      "part_slug": "wrappers",
      "file_list": ["flask/wrappers.py"],
      "brief_responsibility": "Flask-specific Request and Response subclasses extending Werkzeug base types."
    }
  ]
}
```

`brief_responsibility` 字段由 MCP Server 在生成 task manifest 时基于文件名和行数自动生成简短描述，不需要 LLM 分析（纯文本模板化生成）。

---

## 7. doc-index.json 完整 Schema（带示例值）

```json
{
  "schema_version": "2.0",
  "generated_at": "2026-03-23T00:00:00Z",
  "project_root": "/Users/lexuanzhang/code/flask",
  "output_dir": ".codebase-docs",
  "phase_completed": "phase_4",

  "summary": {
    "total_source_files": 24,
    "documented_source_files": 22,
    "undocumented_source_files": 2,
    "coverage_percent": 91.7,
    "total_docs": 14,
    "docs_complete": 12,
    "docs_pending": 2,
    "total_actual_tokens": 28640,
    "total_budget_tokens": 34200,
    "budget_utilization_percent": 83.7
  },

  "documents": [
    {
      "path": "INDEX.md",
      "doc_type": "index",
      "level": 0,
      "target": "root",
      "token_budget": 3000,
      "actual_tokens": 2847,
      "status": "complete",
      "generated_at": "2026-03-23T01:23:45Z",
      "generated_by_agent": "index-agent-001",
      "source_files": [],
      "links_to": [
        "request-handling/OVERVIEW.md",
        "cli/OVERVIEW.md",
        "core/OVERVIEW.md",
        "sansio/OVERVIEW.md",
        "json-serialization/DETAIL_json.md"
      ],
      "linked_from": []
    },
    {
      "path": "request-handling/OVERVIEW.md",
      "doc_type": "overview",
      "level": 1,
      "target": "request-handling",
      "cone_id": "cone_0",
      "token_budget": 1500,
      "actual_tokens": 1342,
      "status": "complete",
      "generated_at": "2026-03-23T01:24:10Z",
      "generated_by_agent": "index-agent-001",
      "source_files": [],
      "links_to": [
        "../INDEX.md",
        "DETAIL_views.md",
        "DETAIL_ctx.md",
        "DETAIL_wrappers.md"
      ],
      "linked_from": ["INDEX.md"]
    },
    {
      "path": "request-handling/DETAIL_views.md",
      "doc_type": "detail",
      "level": 2,
      "target": "request-handling",
      "cone_id": "cone_0",
      "part_slug": "views",
      "part_number": 1,
      "total_parts": 3,
      "token_budget": 1800,
      "actual_tokens": 1654,
      "status": "complete",
      "generated_at": "2026-03-23T01:18:22Z",
      "generated_by_agent": "detail-agent-003",
      "source_files": ["flask/views.py"],
      "links_to": [
        "../INDEX.md",
        "OVERVIEW.md",
        "DETAIL_ctx.md"
      ],
      "linked_from": ["OVERVIEW.md"]
    },
    {
      "path": "request-handling/DETAIL_ctx.md",
      "doc_type": "detail",
      "level": 2,
      "target": "request-handling",
      "cone_id": "cone_0",
      "part_slug": "ctx",
      "part_number": 2,
      "total_parts": 3,
      "token_budget": 2200,
      "actual_tokens": 2091,
      "status": "complete",
      "generated_at": "2026-03-23T01:19:05Z",
      "generated_by_agent": "detail-agent-004",
      "source_files": ["flask/ctx.py"],
      "links_to": ["../INDEX.md", "OVERVIEW.md"],
      "linked_from": ["OVERVIEW.md", "DETAIL_views.md"]
    },
    {
      "path": "cli/DETAIL_cli.md",
      "doc_type": "detail",
      "level": 1,
      "target": "cli",
      "cone_id": "cone_1",
      "part_slug": "cli",
      "part_number": null,
      "total_parts": 1,
      "token_budget": 1200,
      "actual_tokens": 0,
      "status": "pending",
      "generated_at": null,
      "generated_by_agent": null,
      "source_files": ["flask/cli.py"],
      "links_to": [],
      "linked_from": ["INDEX.md"]
    }
  ],

  "coverage_detail": {
    "documented_files": [
      "flask/views.py",
      "flask/ctx.py",
      "flask/wrappers.py",
      "flask/cli.py",
      "flask/app.py",
      "flask/globals.py",
      "flask/config.py",
      "flask/sansio/scaffold.py",
      "flask/sansio/app.py",
      "flask/json/__init__.py",
      "flask/json/provider.py"
    ],
    "undocumented_files": [
      "flask/debughelpers.py",
      "flask/testing.py"
    ],
    "excluded_files": [
      "flask/__init__.py",
      "flask/__main__.py"
    ]
  },

  "link_validation": {
    "total_links": 42,
    "valid_links": 42,
    "broken_links": [],
    "last_validated_at": "2026-03-23T01:30:00Z"
  },

  "feature_cones_ref": ".codebase-analysis/03_feature_cones.json",
  "task_manifest_ref": ".codebase-analysis/05_task_manifest.json"
}
```

### 各字段用途说明

| 字段 | 用途 |
|------|------|
| `schema_version` | 允许未来版本迁移脚本检测格式变化 |
| `phase_completed` | 断点恢复：知道流水线运行到了哪个阶段 |
| `summary.coverage_percent` | 自动计算：`documented_source_files / total_source_files * 100` |
| `summary.docs_pending` | 断点恢复：多少文档还未生成 |
| `documents[].status` | `complete` \| `pending` \| `failed` — 断点恢复核心字段 |
| `documents[].generated_by_agent` | 审计：哪个 Agent 生成了这个文档 |
| `documents[].part_number` / `total_parts` | Split 任务溯源：识别哪些文件是同一锥体的子部分 |
| `documents[].links_to` | 链接校验：脚本可以检查每个路径是否真实存在 |
| `documents[].linked_from` | 反向链接校验：确保没有孤立文档（linked_from 为空则是孤立文档）|
| `coverage_detail.excluded_files` | `__init__.py`、`__main__.py` 等无实质内容的文件不计入覆盖率 |
| `link_validation` | 自动校验脚本运行结果的记录区，Phase 5 填写 |
| `feature_cones_ref` | 溯源：知道 doc-index.json 来自哪个分析版本 |

---

## 8. 并行 Agent 输出一致性机制

### 选择 Approach A（Prompt 级别一致性约束）

**理由：** Approach B（后处理 Style Normalizer）在实践中会重写 Agent 已写好的文档，这可能改变技术术语的措辞，引入意义偏差。对于技术文档，准确性优先于风格一致性。

**强约束的关键：** 不是模糊的"保持一致"，而是每个决策点都有明确的规定。以下是所有 DETAIL Agent Prompt 和 INDEX Agent Prompt 中都必须包含的完整约束节：

### 样式约束节（嵌入所有 Agent Prompt 的完整版本）

```markdown
## Style Constraints (Non-Negotiable)

These rules apply to ALL output documents. They exist because your output will
be combined with output from other agents running in parallel. Inconsistency
between documents degrades the documentation quality.

### Language Rules
- Prose sections (功能概述, 内部逻辑, 设计决策): Write in Chinese (简体中文)
- Technical identifiers (function names, class names, file paths): Keep in English
- Mixed-language pattern: `function_name()` — 中文说明
- Section headers: Use Chinese for DETAIL.md sections, English acceptable in INDEX.md

### Document Structure Rules
- H1 (`#`): Document title only — exactly ONE per document
- H2 (`##`): Major sections — use the exact section names specified in the prompt
- H3 (`###`): Subsections only — do not use for list items
- H4 (`####`) and deeper: PROHIBITED — restructure content instead
- Bold (`**text**`): Only for emphasis on critical warnings or key terms
- Italic (`*text*`): PROHIBITED — use bold or restructure instead

### List Formatting Rules
- Function/interface lists: Use `-` bullet with this EXACT format:
  `- \`signature()\` — one-line description`
- Numbered lists: Only for sequential steps (内部逻辑 section)
- Maximum nesting: 2 levels (bullet inside bullet). No deeper.

### Code Block Rules
- ALWAYS include language tag: ` ```python `, ` ```json `, ` ```mermaid `
- No language tag = prohibited
- Inline code: Use backticks for `function_names`, `filenames`, `ClassName`

### Length Rules (Strict)
- 功能概述 section: 2-3 sentences. Counted strictly — 1 or 4+ sentences is wrong.
- 核心接口 section: 5-10 items. Fewer means incomplete; more means lack of prioritization.
- SNIPPET.md total: 200-500 tokens. Write to target 300-400 tokens for headroom.
- 设计决策 section: 2-5 sentences. If no clear design decisions exist, write 2 sentences about what the code intentionally avoids doing.

### Mermaid Rules (INDEX/OVERVIEW only)
- Use `graph TD` (top-down)
- Node IDs: camelCase identifiers matching `cone_id` or file basename without extension
- Edge style: `-->` for dependency, `-. .->` for optional/weak dependency
- No styling (`style`, `classDef`) — keep diagrams minimal
- Maximum nodes: 15. If more, group into subgraph clusters.

### Prohibited Content
- Do NOT use: "elegant", "beautiful", "unfortunately", "simple", "just", "easy"
- Do NOT use: passive voice for critical claims (say "X does Y", not "Y is done by X")
- Do NOT use: first person ("I", "we") — write in third person or imperative
- Do NOT copy-paste source code blocks larger than 5 lines into documentation
  (quote signatures only, not implementation)
```

---

## 9. SKILL.md 触发词与部分执行策略

### 更新后的 YAML Frontmatter

```yaml
---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive-disclosure architecture
  documentation. Uses MCP tools for deterministic code graph analysis (file
  parsing, dependency graph, feature cone extraction, token estimation), then
  dispatches parallel agents to read source code and write feature-oriented docs.

  Full workflow triggers on: "architecture docs", "analyze codebase", "code map",
  "generate docs", "document this codebase", "explain the codebase structure",
  "onboarding docs", "before I refactor".

  Partial workflow triggers:
  - Dependency graph only: "dependency graph", "show me the module graph",
    "what depends on X"
  - Structure analysis only: "index the codebase", "scan the codebase",
    "what modules does this have"
  - Validate existing docs: "validate docs", "check doc coverage",
    "are the docs up to date"
  - Regenerate specific cone: "regenerate docs for X", "update docs for module Y"

version: 2.0.0
compatibility: [claude-code, codex, opencode, gemini-cli]
mcp_server: codebase-explorer
phase_entry_points:
  full: "phase_1"
  graph_only: "phase_1_graph_only"
  validate_only: "phase_5"
  regenerate_cone: "phase_3_single"
---
```

### 部分执行（Partial Execution）策略

系统不总是需要运行完整的 5-Phase 流水线。以下是各触发场景与对应入口：

| 用户意图 | 触发关键词示例 | 入口 Phase | 产出 |
|----------|---------------|-----------|------|
| 完整文档生成 | "generate architecture docs" | Phase 1 → 5 全量 | 全部文档 |
| 仅依赖图 | "show me the dependency graph" | Phase 1（仅图）| `02_dependency_graph.json` + Mermaid |
| 仅结构分析 | "scan this codebase", "index it" | Phase 1 → 2 | `01-04_*.json` 文件 |
| 仅验证已有文档 | "validate docs", "check coverage" | Phase 5 | `validation_report.json` |
| 重新生成单个功能 | "regenerate docs for cli module" | Phase 3（单锥体）| `{cone}/DETAIL*.md` + 更新 `doc-index.json` |
| 查看模块结构 | "what modules does this codebase have" | Phase 1 + `get_modules` | 控制台输出 |

### Phase 入口点定义

**`phase_1_graph_only`**：运行 `analyze_codebase()` 但在完成 `02_dependency_graph.json` 后立即停止。向用户展示 Mermaid 图并询问是否继续。

**`phase_3_single`**：跳过 Phase 1-2（读取已有 `03_feature_cones.json`），只重新生成指定锥体的 DETAIL 文档。前提：`01-04_*.json` 必须已存在。

**`phase_5`**：直接读取 `doc-index.json` 和文档目录，运行链接校验和覆盖率检查，输出 `validation_report.json`。不需要 MCP 工具，可以纯脚本运行。

### 新增触发词（V2 补充）

在 V1 触发词基础上新增：

```
"explain the codebase"
"I'm new to this codebase"
"onboarding documentation"
"what does this project do"
"before I start the refactoring"
"map out the dependencies"
"find all callers of X"
"which files are most central"
"update the architecture docs"
"the docs are stale"
"regenerate docs for [module name]"
"check if docs are up to date"
```

---

## 10. 遗留问题

以下问题在本文档设计范围内已识别，但需要在实施阶段进一步明确：

### 问题 1：`get_file_content()` 工具的实现

V2 设计假设 MCP Server 新增 `get_file_content(filepath: str) -> str` 工具，让 DETAIL Agent 能读取源码。V1 缺少此工具是 E2E 失败的核心原因之一。该工具需要：

- 路径安全校验（防止 path traversal，只允许读取 `project_root` 内的文件）
- 返回值 Token 估算（以便 Agent 判断是否超出上下文限制）
- 编码处理（非 UTF-8 文件的 fallback）

**待决定：** 工具返回原始文件内容还是带行号的格式？建议带行号（有助于 Agent 在 DETAIL 中引用代码行）。

### 问题 2：Phase 2 Validator 的超时策略

Validator Agent 可能陷入过度分析（尤其是大型项目，锥体数量 > 20 时）。需要定义：

- Token 预算上限（建议 Validator 的上下文消耗不超过 50k tokens）
- 超时后的 fallback：直接接受 MCP 算法产出，跳过语义审查

### 问题 3：并行 DETAIL Agent 的任务分配机制

当有多个 DETAIL Agent 同时运行时，如何确保：

- 没有两个 Agent 处理同一个锥体（原子性取任务）
- Agent 崩溃后任务不丢失（可重试）

V1 中 `get_next_batch()` 工具的"原子标记"机制是否足够？需要评估在真正并行（多个 Claude Code 进程）场景下的竞争条件。

### 问题 4：`brief_responsibility` 的生成质量

Split 任务的 `sibling_parts[].brief_responsibility` 字段由 MCP 基于文件名模板生成，不调用 LLM。对于命名不规范的文件（如 `utils.py`、`helpers.py`），生成的描述质量可能很低，影响 Agent 对"兄弟部分"的理解。

**缓解方案**：当文件名不具描述性时，MCP 可以将文件的第一个类/函数名附加到描述中（如 `utils.py → "Utility functions including format_datetime(), parse_config()"`）。

### 问题 5：doc-index.json 的 `linked_from` 字段维护

`linked_from` 需要在 INDEX Agent 写完所有文档后，通过反向扫描每个文档的 `links_to` 来计算。这是一个后处理步骤，应该在 Phase 5 的验证脚本中执行，而不是在 INDEX Agent 运行时动态维护（否则 Agent 需要在写完每个文档后更新所有已写文档的 `linked_from`，增加了不必要的复杂性）。

**决定：** `linked_from` 字段由 Phase 5 验证脚本计算并回填 `doc-index.json`。INDEX Agent 只需填写 `links_to`。
