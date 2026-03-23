# Skill 细节配置

> 主题：Skill 中的 Prompt 编写、文档结构规范（DETAIL / INDEX / SNIPPET）、动态预算计算、信息分层规则。

---

## 1. 新 Skill 结构设计

### 文件结构

```
.agents/skills/codebase-explorer/
├── SKILL.md                    ← 主文件，~150-200 行（大幅精简）
├── references/
│   ├── MCP_TOOLS.md            ← 6 个工具的简明参考（~150 行）
│   └── QUALITY_CHECKLIST.md    ← 验收清单（~80 行）
└── prompts/                    ← ★ 新增：Prompt 模板
    ├── detail_agent.md         ← DETAIL Agent 的 Prompt 模板
    └── index_agent.md          ← INDEX Agent 的 Prompt 模板
```

### 与旧 Skill 的对比

| 旧设计                              | 新设计                                             |
| ----------------------------------- | -------------------------------------------------- |
| 4 个 reference 文件共 ~1600 行      | SKILL.md ~150 行 + 2 个 Prompt 模板 + 1 个工具参考 |
| `DOC_TEMPLATES.md`（Jinja2 变量表） | **删除** — LLM 直接写 Markdown                     |
| `WORKFLOW_DETAIL.md`（15 工具步骤） | **合并到 SKILL.md** — 5 Phase 足够清晰             |
| `MCP_TOOLS_REFERENCE.md`（530 行）  | **精简为 `MCP_TOOLS.md`** ~150 行（6 个工具）      |
| `QUALITY_STANDARDS.md`（280 行）    | **精简为 `QUALITY_CHECKLIST.md`** ~80 行           |
| 没有 Prompt 模板                    | **新增 `prompts/`** 目录                           |

### 核心理念转变

> 旧 Skill 试图在文档中写清楚"模板怎么填"，因为文档确实是模板填出来的。
> 新 Skill 只需要告诉 Agent "你该读什么、写什么、不写什么"——因为真正的内容理解是 Agent 读了代码后自己产生的。

---

## 2. SKILL.md 主文件设计

### YAML Frontmatter

```yaml
---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive-disclosure architecture
  documentation. Uses MCP tools for deterministic code graph analysis, then
  dispatches agents to read source code and write feature-oriented docs.
  Triggers on: "architecture docs", "analyze codebase", "code map",
  "dependency graph", "generate docs".
version: 2.0.0
compatibility: [claude-code, codex, opencode, gemini-cli]
mcp_server: codebase-explorer
---
```

### 5 个 Phase

#### Phase 1: Analyze（MCP，自动）

- 调用 `analyze_codebase(path)` 运行完整流水线
- 产出 5 个 JSON 文件（`01_structure.json` → `05_task_manifest.json`）
- 向用户报告：功能数量、总 token、任务数

#### Phase 2: Validate Structure（LLM，一个 Agent）

- 读取 `03_feature_cones.json`
- 判断每个功能锥体的分组是否语义合理
- 输出 `validated_features.json`（含功能命名和调整建议）

#### Phase 3: Generate DETAIL Docs（LLM，并行 Agent）

- 读取 `05_task_manifest.json`
- 按任务类型（batch / single / split）分派 Agent
- 每个 Agent 产出：`{feature}/DETAIL.md` + `{feature}/SNIPPET.md`
- **上下文预算规则**：每个任务的源码 token < 100k（MCP 已在 task_manifest 中验证）

#### Phase 4: Assemble INDEX（LLM，一个 Agent）

- 输入：`03_feature_cones.json`（架构结构） + 所有 `SNIPPET.md`
- **不读源码**
- 产出：`INDEX.md`（含 Mermaid 架构图） + 各功能 `OVERVIEW.md` + `doc-index.json`

#### Phase 5: Validate（自动检查）

1. 所有 DETAIL + INDEX 文件存在
2. 所有 Markdown 链接可解析
3. 功能覆盖率 >= 80%
4. INDEX.md 总 token < 3000

---

## 3. 文档结构规范

### 三种文档类型

| 类型            | 作用                        | 谁产出                   | 内容来源                            |
| --------------- | --------------------------- | ------------------------ | ----------------------------------- |
| **DETAIL.md**   | 具体代码功能的详细说明      | DETAIL Agent（读源码）   | 源码理解 + 结构数据注入             |
| **SNIPPET.md**  | 200-500 token 的功能摘要    | DETAIL Agent（同时产出） | 对 DETAIL 的精炼                    |
| **INDEX.md**    | 项目级架构概览 + Mermaid 图 | INDEX Agent（不读源码）  | `feature_cones.json` + 所有 SNIPPET |
| **OVERVIEW.md** | 有子组件的功能的汇总        | INDEX Agent              | SNIPPET 汇总 + 依赖图               |

### DETAIL.md 格式规范

```markdown
# {功能名称}

## 功能概述

（2-3 句话说明这组代码整体在做什么）

## 核心接口

- `函数签名` — 用途说明
- `class 类名(基类)` — 用途说明
  （列出 5-10 个关键接口，每个 2 行描述）

## 内部逻辑

（关键流程说明，5-10 个步骤，核心算法和设计决策）

## 设计决策

（为什么选择这种实现方式）

## 在系统中的位置

- 依赖: {{dependencies_list}}
- 被使用: {{used_by_list}}
- 详细的架构关系请参见上级 INDEX 文档
```

### SNIPPET.md 格式规范

- 200-500 tokens
- 一段话概述 + 关键接口列表
- 标明依赖关系
- **注意**：此内容将被直接嵌入到上级 INDEX 文档中

### INDEX.md 格式规范

```markdown
# {项目名称}

## 架构概览

{Mermaid 依赖图，从 dependency_map 生成}

## 核心组件

{按层级排列，每个功能嵌入其 SNIPPET}
{每个功能后附 → DETAIL 链接}

## 数据流

{典型请求如何从业务层流到底层再返回}
```

### 文档树结构示例（Flask）

```
.codebase-docs/
├── INDEX.md                        # 项目概览 + Mermaid 图
├── request-handling/
│   ├── OVERVIEW.md                 # 请求处理功能全景
│   ├── views/DETAIL.md             # 入口层
│   ├── ctx/DETAIL.md               # 中间层
│   └── wrappers/DETAIL.md          # 辅助层
├── cli/
│   ├── OVERVIEW.md
│   └── cli/DETAIL.md
├── json-serialization/
│   └── OVERVIEW.md                 # 小功能，不需要 DETAIL
├── core/                           # 共享基础设施
│   ├── OVERVIEW.md
│   ├── app/DETAIL.md
│   ├── globals/DETAIL.md
│   └── config/DETAIL.md
└── sansio/                         # 最底层基础设施
    ├── OVERVIEW.md
    ├── scaffold/DETAIL.md
    └── app/DETAIL.md
```

---

## 4. 信息分层规则（避免重复）

| 内容                     |  写在 DETAIL   | 写在 INDEX |
| ------------------------ | :------------: | :--------: |
| 代码具体做了什么（语义） |       ✅       |     ❌     |
| 函数/类签名及参数说明    |       ✅       |     ❌     |
| 内部算法逻辑             |       ✅       |     ❌     |
| 代码示例                 |       ✅       |     ❌     |
| 功能摘要（SNIPPET）      |       ❌       |     ✅     |
| 跨功能架构图（Mermaid）  |       ❌       |     ✅     |
| 跨功能数据流             |       ❌       |     ✅     |
| 跨功能影响分析           |       ❌       |     ✅     |
| 依赖关系（一行简述）     | ✅（模板注入） |     ❌     |
| 功能间如何协作           |       ❌       |     ✅     |

**核心原则**：

- **DETAIL 说"我做什么"**
- **INDEX 说"大家怎么协作"**
- 架构关系不是 Agent "发现"的，而是代码分析预先计算好的

---

## 5. 动态文档预算

### 为什么不用固定 3000 token？

- 小模块浪费：200 行小模块不需要 3000 token 的文档
- 大模块不够：1400 行的 `app.py` 可能需要更多空间

### 动态计算公式

```python
def calc_detail_budget(source_tokens: int) -> int:
    """
    源码 tokens    文档预算比例     典型结果
    < 2000         30%             600 tokens
    2000-8000      25%             500-2000 tokens
    8000-30000     20%             1600-6000 tokens
    > 30000        15%             4500+ tokens（此时应该 split）
    """
    if source_tokens < 2000:
        ratio = 0.30
    elif source_tokens > 30000:
        ratio = 0.15
    else:
        ratio = 0.25

    budget = int(source_tokens * ratio)
    return max(800, min(6000, budget))  # 下限 800，上限 6000
```

### 3000 Token 的实际容量参考

| 语言/内容类型 | 3000 tokens ≈           |
| ------------- | ----------------------- |
| 英文纯文本    | ~2200 词（约 4 页 A4）  |
| 中文纯文本    | ~1500-1800 字           |
| Markdown 混合 | ~1800 词 / ~1200 中文字 |
| 纯代码        | ~200-250 行             |

### 代码量 vs 文档覆盖能力

| 代码类型                | 3000 token 文档能覆盖 |
| ----------------------- | --------------------- |
| 简单 CRUD / 配置        | 2000-3000 行          |
| 普通业务逻辑            | 800-1500 行           |
| 中等复杂度（框架代码）  | 400-800 行            |
| 高复杂度（算法/编译器） | 200-400 行            |

---

## 6. Prompt 模板设计

### DETAIL Agent Prompt 模板 (`prompts/detail_agent.md`)

```markdown
# Code Analysis Task

## Task Info

- Task ID: {{task_id}}
- Type: {{task_type}} (batch/single/split)

## Instructions

For each feature below, read all source files and produce TWO outputs:

### Output 1: DETAIL.md

Write at: `.codebase-docs/{{feature_name}}/DETAIL.md`

Structure:

1. **Title**: Give this feature a meaningful name
2. **Purpose**: 2-3 sentences on what this code does
3. **Core Interfaces**: Function/class signatures with brief descriptions
4. **Internal Logic**: Key algorithms, design decisions, data flow
5. **System Position** (use template below, do not modify):
```

## 在系统中的位置

- 依赖: {{dependencies_list}}
- 被使用: {{used_by_list}}
- 详细的架构关系请参见上级 INDEX 文档

```

Budget: Max {{detail_budget}} tokens per DETAIL.

### Output 2: SNIPPET.md
Write at: `.codebase-analysis/snippets/{{feature_id}}.md`
- 200-500 tokens
- One paragraph overview + key interface list
- This will be embedded in the parent INDEX document

## Features to Analyze
{{#each features}}
### {{cone_id}} ({{total_tokens}} tokens)
Files: {{file_list}}
Layers: {{layer_info}}
Dependencies: {{shared_deps}}
{{/each}}

## Rules
- Focus on WHAT the code does, not HOW the architecture fits together
- Do not describe other features' implementations
- Dependency info in "System Position" comes from the template — use as-is
- If task type is "split": only document your assigned files
```

### INDEX Agent Prompt 模板 (`prompts/index_agent.md`)

````markdown
# Architecture Documentation Assembly

## Your Role

You assemble the project's architecture overview from pre-existing data.
You do NOT read source code.

## Input 1: Architecture Structure

```json
{{feature_cones_json}}
```
````

## Input 2: Feature Summaries

{{#each snippets}}

### {{feature_name}}

{{snippet_content}}
{{/each}}

## Outputs

### 1. INDEX.md

Write at: `.codebase-docs/INDEX.md`

- Project Overview: One paragraph
- Architecture Diagram: Mermaid graph from dependency_map
- Features: Embed each SNIPPET with link to DETAIL
- Shared Infrastructure: Describe shared components
- Data Flow: Typical request flow through features
- Budget: Max 3000 tokens

### 2. Per-feature OVERVIEW.md

Only for features with sub-components.

### 3. doc-index.json

Metadata listing all generated documents.

## Rules

- Architecture diagram MUST match dependency_map exactly
- Feature summaries come from SNIPPETs — no code-level details
- Do not duplicate DETAIL content

````

### Split 类型任务的额外说明

```markdown
## 重要：这是一个拆分任务 (Part {{part_number}}/{{total_parts}})

本功能 "{{feature_name}}" 太大，被拆分为 {{total_parts}} 个子任务。
你负责 Part {{part_number}}: {{your_files}}

其他 Part 的内容（由其他 Agent 负责）：
{{sibling_summary}}

你在写 DETAIL.md 时：
- 只详细说明你负责的文件
- 提到其他 Part 内容时只需引用不需展开
- 输出标记为 "{{feature_name}}/DETAIL_part{{part_number}}.md"
````

---

## 7. 如何服务 Vibe Coding

### 典型场景

| 场景                       | AI 路径                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| "给 Flask 添加新 CLI 命令" | INDEX.md → cli/OVERVIEW.md → "在 cli.py 中添加 @app.cli.command()"  |
| "请求上下文有 bug"         | INDEX.md → request-handling/OVERVIEW.md → ctx/DETAIL.md             |
| "修改 Flask 类初始化"      | INDEX.md → core/OVERVIEW.md → "⚠️ 影响所有上层功能" → app/DETAIL.md |
| "整体架构是什么？"         | INDEX.md → "5 个功能 + 2 个基础设施层"                              |
