# 研究报告 06：Agent Skill (SKILL.md) 设计

> **研究日期**: 2026-03-22
> **状态**: ✅ 完成
> **前置依赖**:
>
> - 01_code_graph_tools.md ✅ — Graph-sitter 为主力图谱工具，NetworkX 原生输出
> - 02_auto_module_grouping.md ✅ — Louvain 三层分组方案（目录→算法→LLM）
> - 03_docagent_architecture.md ✅ — 嵌套循环编排、Writer-Verifier 迭代精炼
> - 04_progressive_doc_standards.md ✅ — 三层文档（INDEX/OVERVIEW/ARCHITECTURE）+ Token 预算
> - 05_mcp_server_patterns.md ✅ — FastMCP 3.0 + SQLite 状态管理 + STDIO transport

---

## 目录

1. [SKILL.md 格式规范总结](#1-skillmd-格式规范总结)
2. [各工具的 Skill 发现路径对比](#2-各工具的-skill-发现路径对比)
3. [5个优秀 Skill 的分析](#3-5个优秀-skill-的分析)
4. [我们的 Skill 设计草案](#4-我们的-skill-设计草案)
5. [兼容性建议](#5-兼容性建议)
6. [测试 Checklist](#6-测试-checklist)

---

## 1. SKILL.md 格式规范总结

### 1.1 官方规范来源

Agent Skills 标准由 Anthropic 于 2025 年底发起，已发展为跨平台开放标准。官方规范维护在 **https://agentskills.io/specification**。

### 1.2 YAML Frontmatter 字段

| 字段                       | 是否必选           | 约束                                                                                       | 说明                                                |
| -------------------------- | ------------------ | ------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| **`name`**                 | ✅ 必选            | 1-64 字符，仅小写字母+数字+连字符，不以连字符开头/结尾，不含连续连字符，必须与父目录名匹配 | Skill 唯一标识符                                    |
| **`description`**          | ✅ 必选            | 1-1024 字符，需说明"做什么"和"何时使用"                                                    | **Agent 触发 Skill 的核心依据**，应包含具体关键词   |
| `license`                  | 可选               | 简短许可证标识                                                                             | 如 `Apache-2.0`、`MIT`                              |
| `compatibility`            | 可选               | 1-500 字符                                                                                 | 环境要求（工具、运行时、网络等）                    |
| `metadata`                 | 可选               | string → string 键值映射                                                                   | 任意扩展元数据（author、version 等）                |
| `allowed-tools`            | 可选               | 工具名列表                                                                                 | 限制 Skill 可使用的工具集合                         |
| `disable-model-invocation` | 可选 (Claude Code) | boolean                                                                                    | 设为 `true` 时 Skill 仅能通过 `/slash-command` 触发 |
| `user-invocable`           | 可选 (Claude Code) | boolean                                                                                    | 设为 `false` 时 Skill 不能通过 `/` 命令触发         |
| `context`                  | 可选 (Claude Code) | `fork` \| `agent`                                                                          | 执行上下文模式                                      |
| `argument-hint`            | 可选 (Claude Code) | 提示文本                                                                                   | 如 `[issue-number]`                                 |
| `effort`                   | 可选 (Claude Code) | `low` \| `medium` \| `high` \| `max`                                                       | 推理努力级别                                        |

**Frontmatter 最小示例**：

```yaml
---
name: codebase-explorer
description: Analyze code structure and generate progressive architecture documentation. Use when exploring unfamiliar codebases, generating module overviews, or creating architecture docs.
---
```

**完整 Frontmatter 示例**：

```yaml
---
name: codebase-explorer
description: >-
  Analyze code structure and generate progressive architecture documentation
  using MCP tools. Automatically indexes codebases, groups modules, and produces
  INDEX/OVERVIEW/ARCHITECTURE docs at three levels of detail. Use whenever the
  user wants to understand a codebase's architecture, generate documentation,
  or explore module dependencies.
license: Apache-2.0
compatibility: Requires Python 3.11+, graph-sitter, and the codebase-explorer MCP server
metadata:
  author: codebase-explorer
  version: "0.1.0"
---
```

### 1.3 Markdown Body 推荐结构

```markdown
# Skill 名称

简要说明 Skill 的核心能力和适用场景。

## When to Use

- 触发条件列表
- 明确的正面和负面触发条件

## Workflow

### Phase 1: xxx

步骤描述...

### Phase 2: xxx

步骤描述...

### Phase N: xxx

步骤描述...

## Quality Rules

嵌入的质量控制规则和检查点。

## Reference Files

- 指向 scripts/、references/、assets/ 的链接
- 说明何时需要加载这些文件
```

**设计原则**：

1. **SKILL.md body 控制在 < 500 行**（推荐 < 5000 tokens）
2. **使用祈使句**（"Do X" 而非 "You should do X"）
3. **解释 Why 而非仅 What**（让 Agent 理解意图，而非机械执行）
4. **避免过度 MUST/NEVER**（用推理和解释代替硬性约束）
5. **包含具体示例**（input/output 对照）

### 1.4 子文件类型

| 目录          | 用途                            | 加载时机                           | 大小建议                                    |
| ------------- | ------------------------------- | ---------------------------------- | ------------------------------------------- |
| `scripts/`    | 可执行脚本（确定性/重复性任务） | Agent 需要时执行（不加载到上下文） | 无限制                                      |
| `references/` | 静态文档（API 文档、模式说明）  | SKILL.md 指引下按需加载            | 每文件 < 300 行时无需目录；> 300 行需含 TOC |
| `assets/`     | 模板、图标、字体等资源文件      | 输出时使用                         | 无限制                                      |

**关键模式**：按领域变体组织

```
codebase-explorer/
├── SKILL.md            # 主工作流 + 路由选择逻辑
├── scripts/
│   ├── validate_docs.py   # 文档链接完整性校验
│   └── token_counter.py   # Token 预算计算
├── references/
│   ├── WORKFLOW.md         # 完整工作流参考（从 SKILL.md 引用）
│   ├── DOC_TEMPLATES.md    # Jinja2 文档模板
│   └── MCP_TOOLS.md        # MCP 工具详细参数说明
└── assets/
    └── doc-config.yaml     # 默认文档生成配置
```

### 1.5 渐进式加载（Progressive Disclosure）

这是 Agent Skills 标准的**核心设计**，直接决定了 Token 效率：

```
Level 1: 发现（Discovery）
  ├── 时机：Agent 启动时
  ├── 加载：所有 Skill 的 name + description（~100 tokens/skill）
  └── 目的：判断哪个 Skill 与用户请求相关

Level 2: 激活（Activation）
  ├── 时机：Agent 判定某 Skill 相关时
  ├── 加载：该 Skill 的完整 SKILL.md body（< 5000 tokens）
  └── 目的：获取详细工作流指令

Level 3: 执行（Execution）
  ├── 时机：SKILL.md 指令要求加载特定资源时
  ├── 加载：scripts/、references/、assets/ 中的指定文件
  └── 目的：获取模板、运行脚本、查阅详细文档
```

**对我们的意义**：我们的 SKILL.md 必须在 Level 2 就提供完整的工作流概述，而将 MCP 工具调用的详细参数、文档模板等放在 references/ 中按需加载。

### 1.6 文件大小/Token 限制建议

| 文件                | 建议上限                 | 理由                                |
| ------------------- | ------------------------ | ----------------------------------- |
| SKILL.md body       | < 500 行 / < 5000 tokens | 每次 Skill 激活时会完整加载到上下文 |
| 单个 reference 文件 | < 300 行                 | > 300 行时需含 TOC，便于 Agent 定位 |
| description 字段    | < 1024 字符              | agentskills.io 规范限制             |
| name 字段           | 1-64 字符                | agentskills.io 规范限制             |

---

## 2. 各工具的 Skill 发现路径对比

### 2.1 路径对照表

| 工具            | Workspace 路径                       | 通用别名                 | Global 路径                        | 优先级说明                                       |
| --------------- | ------------------------------------ | ------------------------ | ---------------------------------- | ------------------------------------------------ |
| **Claude Code** | `.claude/skills/<name>/SKILL.md`     | `.agents/skills/` 也支持 | `~/.claude/skills/<name>/SKILL.md` | Workspace > Global；支持 `packages/*/` 嵌套发现  |
| **Gemini CLI**  | `.gemini/skills/<name>/SKILL.md`     | `.agents/skills/` 也支持 | `~/.gemini/skills/<name>/SKILL.md` | Workspace > User > Extension；`/skills` 命令管理 |
| **OpenCode**    | `.opencode/skills/<name>/SKILL.md`   | `.agents/skills/` 也支持 | `~/.config/opencode/skills/`       | 兼容 Claude 文件约定                             |
| **Codex CLI**   | `.codex/skills/<name>/SKILL.md`      | `.agents/skills/` 也支持 | `~/.codex/skills/`                 | 支持显式和隐式激活                               |
| **Cursor**      | `.cursor/skills/<name>/SKILL.md`     | —                        | `~/.cursor/skills/`                | 也从 `.claude/` 和 `.codex/` 目录加载            |
| **Kiro**        | `.kiro/skills/<name>/SKILL.md`       | —                        | `~/.kiro/skills/`                  | Workspace > Global                               |
| **通用**        | **`.agents/skills/<name>/SKILL.md`** | —                        | `~/.agents/skills/`                | **最大公约数路径，被多数工具支持**               |

### 2.2 跨工具兼容推荐布局

```
project-root/
├── .agents/                    # 通用路径（最大兼容性）
│   └── skills/
│       └── codebase-explorer/
│           ├── SKILL.md
│           ├── scripts/
│           ├── references/
│           └── assets/
├── .claude/                    # Claude Code 专用（若需 Claude 特定功能）
│   └── skills/
│       └── codebase-explorer -> ../../.agents/skills/codebase-explorer  # 符号链接
├── .gemini/                    # Gemini CLI 专用
│   └── skills/
│       └── codebase-explorer -> ../../.agents/skills/codebase-explorer  # 符号链接
└── .mcp.json                   # MCP Server 配置（Claude Code 共享）
```

**推荐策略**：将 Skill 文件存放在 `.agents/skills/` 中，然后在各工具的专用目录中创建符号链接。这样：

- 只维护一份 Skill 源文件
- 所有支持的工具都能发现
- Git 友好（可以在 `.gitignore` 中排除符号链接目标目录或选择性追踪）

### 2.3 各工具的激活机制差异

| 工具            | 标准显式激活         | 隐式激活（Agent 自主判断） | 特殊功能                                                |
| --------------- | -------------------- | -------------------------- | ------------------------------------------------------- |
| **Claude Code** | `/skill-name [args]` | ✅ 基于 description 匹配   | `context: fork` 子 Agent 执行、`$ARGUMENTS` 替换、hooks |
| **Gemini CLI**  | `/skills` 命令管理   | ✅ 基于 description 匹配   | `activate_skill` 工具 + 用户同意确认                    |
| **OpenCode**    | 命令行触发           | ✅ 基于 description 匹配   | 兼容 Claude 约定                                        |
| **Codex CLI**   | 命令触发             | ✅ 基于 description 匹配   | —                                                       |
| **Cursor**      | 自动加载             | ✅ 基于 description 匹配   | 也读取 `.cursorrules`                                   |

---

## 3. 5个优秀 Skill 的分析

### 3.1 skill-creator（Anthropic 官方）

**来源**: https://github.com/anthropics/skills (内置于 Claude Code)
**目录所在**: 本项目 `.agents/skills/skill-creator/`

**设计亮点**：

1. **完整的迭代改进循环**：Draft → Test → Review → Improve → Repeat（这与我们参考的 DocAgent Writer-Verifier 模式高度一致）
2. **渐进式资源引用**：SKILL.md body 486 行，但通过引用 `agents/grader.md`、`agents/comparator.md`、`agents/analyzer.md` 等子 Agent 文档将执行细节延迟加载
3. **跨平台适配**：专门有 "Claude.ai-specific instructions" 和 "Cowork-Specific Instructions" 章节
4. **Description 优化工具链**：包含 `scripts/run_loop.py` 用于自动优化 description 触发准确率
5. **评估框架内置**：`eval-viewer/generate_review.py` 为 HTML 评审查看器，实现了完整的基准测试流程

**值得借鉴**：

- **子 Agent 指令文档化**（`agents/` 目录模式）—— 我们可以用类似模式将 MCP 工具调用指南文档化
- **"解释 Why 而非强制 MUST"** 的写作风格 —— 使 Agent 理解意图而非盲从规则
- **环境感知**（检测是否有子 Agent、浏览器、CLI 等能力后选择不同路径）

### 3.2 orchestration-planning（/op）

**来源**: 本项目 `.agents/skills/orchestration-planning/`

**设计亮点**：

1. **严格的 Phase 结构**：Phase 0 理解 → Phase 0.5 Skill 发现（强制步骤）→ Phase 1 生成 PLAN → Phase 2 审查 → Phase 3 交接
2. **Skill 发现机制**：Phase 0.5 强制要求 Sub-agent 扫描所有现有 Skill，避免使用过时的静态矩阵
3. **Context 恢复协议**：PLAN 文件最顶端的恢复指令，解决 `/clear` 后 Agent 状态丢失问题
4. **并行执行规则**：明确的 DAG 并行组 + 写入冲突检测规则
5. **强制要求 Checklist**：8 个必须区块 + 验收标准 + 日志模式

**值得借鉴**：

- **Context 恢复协议** —— 我们的 Skill 也需要处理长任务中 Agent Context 压缩后的状态恢复
- **PLAN 8 区块结构** —— 可参考用于我们的多模块分析任务拆解
- **"违反则计划无效"的强制要求表格** —— 用于质量控制的关键约束

### 3.3 awesome-copilot / ADR Skill（GitHub 官方）

**来源**: https://github.com/github/awesome-copilot

**设计亮点**：

1. **Architecture Decision Record (ADR) Skill**：自动生成 AI 优化的架构决策记录
2. **GitHub Actions Workflow Spec**：为 CI/CD 工作流生成形式化规范文档
3. **Azure Resource Analysis**：分析 IaC 文件并生成优化 GitHub Issues
4. **Bicep Deployment Validation**：多步骤验证工作流（语法→what-if→权限检查）

**值得借鉴**：

- **输出格式明确模板化**（每个 Skill 都有精确的输出文档模板）
- **多步骤验证工作流**（与我们三层文档生成的多步骤流程一致）
- **面向"AI 消费"的文档优化**

### 3.4 code-analyze Skill

**来源**: https://github.com/skillmatic-ai/awesome-agent-skills (skillmatic-ai 社区)

**设计亮点**：

1. **静态分析 + 复杂度指标 + 代码质量洞察**三位一体
2. **通过 `scripts/main.sh` 执行确定性分析**（而非依赖 LLM 猜测）
3. **结构化 JSON 输出**用于后续处理

**值得借鉴**：

- **脚本执行确定性任务** —— 我们的 Graph-sitter 分析、Token 计数等都应通过脚本执行
- **结构化输出格式** —— MCP 工具返回的 JSON 可直接被 Skill 引用

### 3.5 deep-research Skill（多轮搜索研究）

**来源**: 本项目 `.agents/skills/research/` (及社区多种实现)

**设计亮点**：

1. **多维并行调研**模式 —— 同时启动多个搜索维度的 Sub-agent
2. **置信度评估**机制 —— 每条信息的可信度分级
3. **渐进式深入**策略 —— 先广后深，避免初始阶段 Token 浪费
4. **结构化报告模板** —— 强制输出格式包含来源引用

**值得借鉴**：

- **多维并行** —— 我们分析不同模块可以并行进行
- **渐进式深入** —— 与我们 Level 0 → Level 1 → Level 2 的文档生成策略一致
- **结构化输出** —— 每个步骤的中间结果都有明确格式

### 3.6 小结：优秀 Skill 的共同特征

| 特征                 | 说明                                                |
| -------------------- | --------------------------------------------------- |
| **Phase 化工作流**   | 将复杂任务分为明确的阶段，每个阶段有入口和出口条件  |
| **渐进式资源加载**   | SKILL.md 只放工作流概述，详细参考放到 references/   |
| **脚本化确定性操作** | 不依赖 LLM 做可以用脚本的事（验证、计算、文件操作） |
| **质量控制检查点**   | 在关键节点嵌入验证步骤（Verifier 模式或 Checklist） |
| **跨环境适配**       | 检测可用能力后选择不同执行路径                      |
| **Context 恢复**     | 长任务需要处理 Agent 上下文压缩后的状态恢复         |

---

## 4. 我们的 Skill 设计草案

### 4.1 Skill 目录结构

```
.agents/skills/codebase-explorer/
├── SKILL.md                        # 主入口（< 500 行）
├── scripts/
│   ├── validate_doc_links.py       # 文档链接完整性校验
│   ├── count_tokens.py             # Token 预算计算
│   └── check_coverage.py           # 文档覆盖率检查
├── references/
│   ├── WORKFLOW_DETAIL.md           # 完整工作流参考（Phase 详细步骤）
│   ├── DOC_TEMPLATES.md             # Jinja2 文档模板（Level 0/1/2）
│   ├── MCP_TOOLS_REFERENCE.md       # MCP 工具参数和返回值详细说明
│   ├── QUALITY_STANDARDS.md         # 文档质量标准和密度控制规则
│   └── GROUPING_ALGORITHMS.md       # 模块分组算法参考
└── assets/
    └── doc-config.yaml              # 默认文档生成配置
```

### 4.2 完整 SKILL.md 初稿

```markdown
---
name: codebase-explorer
description: >-
  Analyze codebase structure and generate progressive architecture documentation
  at three detail levels (INDEX → OVERVIEW → ARCHITECTURE). Uses MCP tools to
  index code, detect modules via Louvain community detection, build dependency
  graphs, and produce token-budgeted Markdown docs with Mermaid diagrams.
  Use this skill whenever the user wants to understand a codebase's architecture,
  generate module documentation, visualize dependencies, explore unfamiliar code,
  or audit code structure. Also use when they mention "architecture docs",
  "module overview", "code map", "dependency graph", or "codebase analysis".
compatibility: Requires the codebase-explorer MCP server running locally (Python 3.11+)
metadata:
  author: codebase-explorer
  version: "0.1.0"
---

# Codebase Explorer

Analyze code structure and generate progressive architecture documentation.
Produces three levels of docs — from project overview down to component internals —
using automated dependency graph analysis and LLM-powered content generation.

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
- The codebase is a single file or script

## Prerequisites

The codebase-explorer MCP server must be running. Verify by calling
`get_analysis_status` — if it fails, tell the user to start the server:
```

python /path/to/codebase-explorer/server.py

```

## Workflow Overview

The workflow has 5 phases. Each phase produces concrete outputs that feed
the next. You must follow these phases in order.

### Phase 1: Index the Codebase

**Goal**: Build the dependency graph from source code.

1. Call `index_codebase(path=<repo_path>)` with the target repository path
2. Wait for indexing to complete (check progress via `get_analysis_status`)
3. Note the returned `index_id` — you'll need it for all subsequent calls
4. Report the summary statistics to the user:
   - Total files, functions, classes
   - Detected languages

**Quality gate**: Indexing must return `status: "success"` before proceeding.

### Phase 2: Discover and Group Modules

**Goal**: Identify the logical module structure of the codebase.

1. Call `get_modules(sort_by="size")` to get the auto-grouped module list
2. Review the module grouping with the user:
   - Present the module list with file counts
   - Ask if the grouping looks reasonable
   - Note any modules the user wants to merge or split
3. For each module, call `get_module_detail(module_name=<name>)` to get:
   - Files in the module
   - Public interfaces
   - Dependencies on other modules
   - Mermaid dependency graph

**Quality gate**: User confirms the module grouping is acceptable.

### Phase 3: Generate Level 0 — INDEX.md

**Goal**: Create a one-page project overview.

1. Gather data:
   - Project name and description (from README or package.json)
   - Technology stack (from dependency files)
   - Module list with one-line descriptions
   - Overall dependency graph (Mermaid)
   - Key entry points
2. Call `generate_index_doc(index_id=<id>)` to generate the INDEX.md
3. Verify the output:
   - **Token budget**: Must be 800–1,200 tokens
   - **Completeness**: All modules listed with descriptions
   - **Mermaid graph**: Present and renders correctly
   - **Navigation links**: Point to all Level 1 docs

If budget is exceeded, prioritize: module list > entry points > tech stack.

Write the INDEX.md to the project root.

### Phase 4: Generate Level 1 — OVERVIEW.md per Module

**Goal**: Create module-level overviews for each discovered module.

Process modules in dependency order (dependencies first):

1. For each module:
   a. Call `claim_analysis_task(module_name=<name>, agent_id="main")`
   b. Call `get_module_detail(module_name=<name>)` if not already cached
   c. Call `generate_overview_doc(module_name=<name>)`
   d. Verify output:
      - **Token budget**: 1,200–2,000 tokens
      - **Public interfaces**: All exported symbols listed with signatures
      - **Dependency graph**: Shows relationships to other modules
      - **Navigation**: Links to parent INDEX.md and child ARCHITECTURE.md files
   e. Write OVERVIEW.md to `docs/<module_name>/OVERVIEW.md`
   f. Call `release_analysis_task(task_id=<id>, result_status="done")`

2. **Checkpoint**: After completing every 3 modules:
   - Report progress to the user
   - Run `scripts/check_coverage.py` to verify coverage
   - Run `scripts/validate_doc_links.py` to check link integrity

**Quality gate**: All modules have OVERVIEW.md files with valid links.

### Phase 5: Generate Level 2 — ARCHITECTURE.md per Component

**Goal**: Create detailed component docs for complex modules.

Not all modules need Level 2. Prioritize:
- Modules with > 5 files
- Modules with high cyclomatic complexity
- Modules the user specifically requested

For each target component:

1. Call `get_component_detail(component_id=<id>)`
2. Call `generate_architecture_doc(component_id=<id>)`
3. Verify output:
   - **Token budget**: 2,000–4,000 tokens
   - **Class documentation**: All core classes with method tables
   - **Function documentation**: Key functions with signatures
   - **Internal structure**: Mermaid class/call diagram
   - **Data flow**: At least one data flow diagram
   - **Navigation**: Links back to parent OVERVIEW.md

4. Write ARCHITECTURE.md to `docs/<module>/<component>/ARCHITECTURE.md`

### Phase 6: Final Validation

1. Run `scripts/validate_doc_links.py <project_root>` — all links must resolve
2. Run `scripts/count_tokens.py <project_root>` — verify token budgets
3. Generate `doc-index.json` with all document paths and metadata
4. Present the final summary to the user:
   - Total documents generated
   - Overall coverage percentage
   - Total token count
   - Any known gaps or issues

## Quality Control Rules

These rules are embedded throughout the workflow. They exist because
without them, generated documents tend to be either too verbose (wasting
tokens) or too sparse (missing critical information).

### Token Budget Enforcement

| Level | File | Budget | Enforcement |
|-------|------|--------|-------------|
| 0 | INDEX.md | 800–1,200 tokens | Truncate from bottom: metrics → tech stack → descriptions |
| 1 | OVERVIEW.md | 1,200–2,000 tokens | Fold file list > 15 items; compress interface descriptions |
| 2 | ARCHITECTURE.md | 2,000–4,000 tokens | Limit to top-5 classes; summarize minor functions |

### Checkpoint Rule

After analyzing every 3 modules, you MUST:
1. Save all generated documents to disk
2. Report progress (X of Y modules complete)
3. Validate link integrity of generated documents

This exists because long analysis sessions risk losing work to context
window overflow or unexpected errors. Intermediate saves prevent that.

### Dependency-Order Processing

Always process modules in topological dependency order. If Module A depends
on Module B, complete B's documentation first. This ensures that when
documenting A's dependencies, you can reference B's documentation.

If cycles exist, process the largest strongly-connected component (SCC) as
a single unit, then proceed to dependent modules.

### Mermaid Diagram Requirements

Every OVERVIEW.md must contain at least one Mermaid diagram showing:
- Module dependencies (who imports whom)
- Direction of data flow

Every ARCHITECTURE.md must contain at least one Mermaid diagram showing:
- Internal class/function relationships

Use Mermaid because:
1. GitHub/GitLab render it natively
2. LLMs can parse it as structured text
3. It's version-control friendly

## MCP Tool Quick Reference

For detailed parameter specifications, see [MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md).

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `index_codebase` | Build dependency graph | `path`, `languages` |
| `get_modules` | List auto-grouped modules | `sort_by` |
| `get_module_detail` | Module details for OVERVIEW | `module_name` |
| `get_component_detail` | Component details for ARCHITECTURE | `component_id` |
| `get_function_callers` | Trace call chains | `function_name`, `depth` |
| `get_dependency_graph` | Dependency visualization | `scope`, `target` |
| `generate_index_doc` | Generate INDEX.md | `index_id` |
| `generate_overview_doc` | Generate OVERVIEW.md | `module_name` |
| `generate_architecture_doc` | Generate ARCHITECTURE.md | `component_id` |
| `get_analysis_status` | Check progress | `index_id` |
| `claim_analysis_task` | Mutex lock for module | `module_name`, `agent_id` |
| `release_analysis_task` | Release mutex | `task_id`, `result_status` |

## Document Templates

For complete Jinja2 templates for each document level, see
[DOC_TEMPLATES.md](references/DOC_TEMPLATES.md).

## Error Recovery

If `index_codebase` fails:
- Check the path is absolute and the directory exists
- Try with specific `languages` filter

If `generate_*_doc` returns content exceeding token budget:
- Re-call with a note to the MCP server (future: budget parameter)
- Manually truncate following the priority rules above

If `claim_analysis_task` returns `claimed: false`:
- Another agent or session is analyzing this module
- Wait or skip to a different module

## Additional Resources

- [WORKFLOW_DETAIL.md](references/WORKFLOW_DETAIL.md) — Expanded step-by-step sub-procedures
- [QUALITY_STANDARDS.md](references/QUALITY_STANDARDS.md) — Document quality rubric
- [GROUPING_ALGORITHMS.md](references/GROUPING_ALGORITHMS.md) — Module grouping algorithm details
```

### 4.3 多步骤工作流编码方式

我们的 Skill 工作流采用了以下编码模式，综合了前置研究的最佳实践：

| 模式                  | 来源                         | 在 Skill 中的体现                                              |
| --------------------- | ---------------------------- | -------------------------------------------------------------- |
| **Phase 化阶段**      | orchestration-planning Skill | 6 个有序 Phase，每个 Phase 有目标、步骤、质量门                |
| **依赖感知拓扑处理**  | DocAgent Navigator (03)      | Phase 4 按依赖序处理模块                                       |
| **嵌套循环编排**      | DocAgent Orchestrator (03)   | Phase 4 内的 claim → detail → generate → verify → release 循环 |
| **渐进式文档生成**    | 04 文档标准                  | Level 0 → Level 1 → Level 2 逐层深入                           |
| **MCP 工具调用**      | 05 MCP 模式                  | 每个 Phase 明确指定调用哪个 MCP 工具                           |
| **Graph-sitter 图谱** | 01 图谱工具                  | Phase 1 通过 `index_codebase` 调用 Graph-sitter                |
| **Louvain 分组**      | 02 分组算法                  | Phase 2 的模块分组由 `get_modules` 内部执行 Louvain            |

### 4.4 质量控制规则的嵌入方式

质量控制通过三种机制嵌入：

1. **Phase 内质量门（Quality Gate）**
   - 每个 Phase 末尾有明确的通过条件
   - 不满足条件不能进入下一 Phase

2. **中间检查点（Checkpoint Rule）**
   - 每 3 个模块强制保存和验证
   - 借鉴 orchestration-planning 的 Checkpoint YAML 思路

3. **Token 预算执行**
   - 每层文档都有硬性 Token 上限
   - 超出时有明确的裁剪优先级
   - 借鉴 DocAgent 的 `_constrain_context_length` 策略

4. **脚本化验证**
   - `validate_doc_links.py` 验证链接完整性
   - `count_tokens.py` 验证 Token 预算
   - `check_coverage.py` 验证文档覆盖率
   - 借鉴 skill-creator 的脚本执行模式

### 4.5 与 MCP 工具的配合说明

```
Agent 读取 SKILL.md
    ↓
Phase 1: 调用 MCP 工具 index_codebase(path)
    ↓ （内部：Graph-sitter 解析 → NetworkX 图谱 → SQLite 存储）
Phase 2: 调用 MCP 工具 get_modules(sort_by)
    ↓ （内部：Louvain 社区检测 → 模块分组）
Phase 3: 调用 MCP 工具 generate_index_doc(index_id)
    ↓ （内部：Jinja2 模板 → Token 预算裁剪）
Phase 4: 循环调用 MCP 工具：
    claim_analysis_task → get_module_detail → generate_overview_doc → release_analysis_task
    ↓ （内部：互斥锁 → 数据查询 → 模板渲染 → 锁释放）
Phase 5: 循环调用 MCP 工具：
    get_component_detail → generate_architecture_doc
    ↓ （内部：调用图/继承图查询 → 详细文档渲染）
Phase 6: 运行 scripts/ 中的验证脚本
```

MCP 工具的详细参数规格（来自 05_mcp_server_patterns.md）放在 `references/MCP_TOOLS_REFERENCE.md` 中，不在 SKILL.md 主体中占用 Token。

---

## 5. 兼容性建议

### 5.1 确保跨工具兼容的规则

| 规则                            | 原因                                                    | 实施方式                                                           |
| ------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| **使用 `.agents/skills/` 路径** | 被 Claude、Gemini、OpenCode、Codex 多数工具支持         | 主文件放在 `.agents/skills/`，其他路径用符号链接                   |
| **仅使用标准 frontmatter 字段** | 非标准字段可能被某些工具忽略或报错                      | 只用 `name`、`description`、`compatibility`、`metadata`、`license` |
| **避免 Claude 专属功能**        | `context: fork`、`hooks`、`$ARGUMENTS` 等仅 Claude 支持 | 在 SKILL.md body 中用条件说明替代                                  |
| **文件路径使用相对路径**        | 绝对路径在不同机器上不兼容                              | 所有 references/ 引用使用相对于 SKILL.md 的路径                    |
| **description 保持通用语义**    | 各工具的触发机制细节不同                                | 描述"做什么+何时使用"，不引用任何特定工具的功能                    |
| **脚本使用跨平台语言**          | 有些环境可能没有 bash                                   | 优先用 Python 脚本，提供 shebang 行                                |

### 5.2 需要避免的工具特定语法

| 语法                             | 所属工具                     | 替代方案                                 |
| -------------------------------- | ---------------------------- | ---------------------------------------- |
| `context: fork`                  | Claude Code                  | 在 body 中写"启动 Sub-agent 执行此步骤"  |
| `$ARGUMENTS`, `$0`, `$1`         | Claude Code                  | 在 body 中写"用户提供的参数"             |
| `${CLAUDE_SESSION_ID}`           | Claude Code                  | 不使用，或在 references/ 中说明          |
| `disable-model-invocation: true` | Claude Code                  | 在 description 中明确触发条件            |
| `hooks:`                         | Claude Code                  | 不使用                                   |
| `allowed-tools:`                 | Claude Code + agentskills.io | 可以使用（标准字段），但某些工具可能忽略 |
| `/skills` 管理命令               | Gemini CLI                   | 不依赖此命令，使用文件系统发现           |

### 5.3 推荐的目录布局

```
project-root/
├── .agents/
│   └── skills/
│       └── codebase-explorer/
│           ├── SKILL.md                    # 主指令（< 500 行）
│           ├── scripts/
│           │   ├── validate_doc_links.py   # Python 3.11+ 兼容
│           │   ├── count_tokens.py
│           │   └── check_coverage.py
│           ├── references/
│           │   ├── WORKFLOW_DETAIL.md       # 详细工作流步骤
│           │   ├── DOC_TEMPLATES.md         # 文档模板
│           │   ├── MCP_TOOLS_REFERENCE.md   # MCP 工具参数详解
│           │   ├── QUALITY_STANDARDS.md     # 质量标准
│           │   └── GROUPING_ALGORITHMS.md   # 分组算法参考
│           └── assets/
│               └── doc-config.yaml          # 默认配置
├── .mcp.json                               # MCP Server 配置（Claude Code 共享）
└── server.py                               # MCP Server 入口
```

### 5.4 如何维护单源多目标

```bash
# setup-skill-links.sh — 为所有支持的工具创建符号链接
#!/bin/bash
SKILL_DIR=".agents/skills/codebase-explorer"

# Claude Code
mkdir -p .claude/skills
ln -sf "../../$SKILL_DIR" .claude/skills/codebase-explorer

# Gemini CLI
mkdir -p .gemini/skills
ln -sf "../../$SKILL_DIR" .gemini/skills/codebase-explorer

# 添加更多工具...
echo "Skill links created for all supported tools."
```

---

## 6. 测试 Checklist

### 6.1 Skill 加载验证

| 步骤                   | 验证方法                                                   | 预期结果     |
| ---------------------- | ---------------------------------------------------------- | ------------ |
| **Frontmatter 语法**   | YAML lint 或 `skills-ref validate ./codebase-explorer`     | 无错误       |
| **name 字段规范**      | 检查：lowercase + hyphen，无连续连字符，与目录名匹配       | 通过         |
| **description 长度**   | `wc -c` 检测                                               | 1-1024 字符  |
| **SKILL.md body 大小** | `wc -l` 检测                                               | < 500 行     |
| **文件引用完整性**     | 检查 SKILL.md 中所有 `[text](path)` 链接的目标文件是否存在 | 所有链接有效 |

### 6.2 各工具发现验证

| 工具            | 验证命令                                                | 预期结果                 |
| --------------- | ------------------------------------------------------- | ------------------------ |
| **Claude Code** | `claude` 启动后问 "list skills"                         | 显示 `codebase-explorer` |
| **Gemini CLI**  | `gemini` 会话中执行 `/skills list`                      | 显示 `codebase-explorer` |
| **OpenCode**    | 启动后查看 Skill 列表                                   | 显示 `codebase-explorer` |
| **通用验证**    | 在 `.agents/skills/codebase-explorer/` 下 `ls SKILL.md` | 文件存在                 |

### 6.3 Skill 触发验证

| 测试 Prompt            | 预期行为                         | 验证方法                          |
| ---------------------- | -------------------------------- | --------------------------------- |
| "分析这个项目的架构"   | 自动触发 codebase-explorer Skill | Agent 响应包含 Phase 1 步骤       |
| "生成模块文档"         | 自动触发                         | Agent 开始调用 MCP 工具           |
| "这个函数是干什么的？" | **不应触发**（太小的请求）       | Agent 直接回答                    |
| "帮我修改 README"      | **不应触发**（文档编辑而非生成） | Agent 使用普通编辑功能            |
| "画一个依赖图"         | 应触发                           | Agent 调用 `get_dependency_graph` |

### 6.4 工作流完整性验证

| 检查项       | 验证方法                      | 通过标准                     |
| ------------ | ----------------------------- | ---------------------------- |
| Phase 1 完成 | 检查 SQL 中 codebase_index 表 | 有 status="completed" 的记录 |
| Phase 2 完成 | 检查 get_modules 返回值       | 模块列表非空                 |
| Phase 3 完成 | 检查 INDEX.md 文件            | 存在且 token 数在 800-1200   |
| Phase 4 完成 | 检查所有 OVERVIEW.md          | 每个模块都有对应文件         |
| Phase 5 完成 | 检查 ARCHITECTURE.md          | 目标组件都有对应文件         |
| Phase 6 完成 | 运行 validate_doc_links.py    | 返回 `valid: true`           |

### 6.5 跨工具行为一致性验证

1. **相同 Prompt 测试**：
   - 用同一个测试仓库，分别在 Claude Code 和 Gemini CLI 中触发 Skill
   - 验证两者都能正确发现并激活 Skill
   - 验证 MCP 工具调用序列一致

2. **输出格式验证**：
   - 生成的 INDEX.md / OVERVIEW.md / ARCHITECTURE.md 在不同工具中应结构一致
   - Mermaid 图在 GitHub / GitLab 上正确渲染

3. **错误处理验证**：
   - MCP Server 未启动时，Skill 应给出清晰的错误提示
   - 无效路径时，Skill 应优雅失败而非崩溃

---

## 7. 引用来源

### 官方规范

- Agent Skills 规范: https://agentskills.io/specification
- Agent Skills 文档: https://agentskills.io/
- Claude Code Skills 文档: https://docs.anthropic.com/en/docs/claude-code/skills
- Gemini CLI Skills 文档: https://geminicli.com/ (Skills 章节)
- OpenCode 文档: https://opencode.ai/
- Codex CLI 文档: https://openai.com/index/codex-cli/

### Skill 示例来源

- Anthropic Skills: https://github.com/anthropics/skills
- GitHub awesome-copilot: https://github.com/github/awesome-copilot
- skillmatic-ai/awesome-agent-skills: https://github.com/skillmatic-ai/awesome-agent-skills
- heilcheng/awesome-agent-skills: https://github.com/heilcheng/awesome-agent-skills
- Skills Directory 市场: https://skillsdirectory.com/

### Skill 设计教程

- Strapi SKILL.md 教程: https://strapi.io/ (Agent Skills 文章)
- Medium Agent Skills 系列: 多篇关于 Skill 设计的实战文章
- thepromptindex.com: SKILL.md 跨平台兼容性指南
- kiro.dev: Skill 设计最佳实践

### 前置研究

- `results/01_code_graph_tools.md` — Graph-sitter 作为主力图谱工具
- `results/02_auto_module_grouping.md` — Louvain 三层分组方案
- `results/03_docagent_architecture.md` — 嵌套循环编排 + Writer-Verifier 模式
- `results/04_progressive_doc_standards.md` — 三层文档结构 + Token 预算标准
- `results/05_mcp_server_patterns.md` — FastMCP 3.0 MCP Server + SQLite 状态管理

---

## 附录 A：SKILL.md 与其他配置格式的对比

| 特征           | SKILL.md                         | .cursorrules | CLAUDE.md      | copilot-instructions.md |
| -------------- | -------------------------------- | ------------ | -------------- | ----------------------- |
| **形式**       | YAML frontmatter + Markdown body | 纯文本规则   | Markdown       | Markdown                |
| **粒度**       | 单个可复用能力包                 | 项目全局规则 | 项目全局上下文 | 项目全局指令            |
| **触发方式**   | 按需激活（渐进加载）             | 始终加载     | 始终加载       | 始终加载                |
| **子文件支持** | ✅scripts/references/assets/     | ❌           | ❌             | ❌                      |
| **脚本执行**   | ✅ scripts/ 目录                 | ❌           | ❌             | ❌                      |
| **跨工具兼容** | ✅ 开放标准                      | Cursor 专用  | Claude 专用    | Copilot 专用            |
| **版本控制**   | ✅ Git 友好（文件系统）          | ✅           | ✅             | ✅                      |
| **Token 效率** | ✅ 三层渐进加载                  | ❌ 全量加载  | ❌ 全量加载    | ❌ 全量加载             |

SKILL.md 的核心优势在于**渐进式加载**和**可组合的子文件结构**，这使它特别适合我们的复杂多步骤分析工作流。

## 附录 B：description 字段优化建议

基于 skill-creator 的 description 优化方法论：

1. **描述功能 + 触发条件**：
   - ✅ "Analyze codebase structure and generate progressive architecture documentation. Use when exploring unfamiliar codebases, generating module overviews, or creating architecture docs."
   - ❌ "A tool for code analysis."

2. **包含关键词覆盖**：
   - 在 description 中包含用户可能使用的多种表述："architecture docs"、"module overview"、"code map"、"dependency graph"、"codebase analysis"

3. **稍微"主动"一些**：
   - Agent 倾向于"少触发"而非"多触发"，所以 description 应该稍微推一把
   - 例如加上："Also use when they mention..."

4. **避免过于宽泛**：
   - ❌ "Use for any code-related task"（会覆盖太多不相关的请求）
   - ✅ 具体列出适用场景
