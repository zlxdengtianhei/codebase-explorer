# INDEX Agent 分割/聚合能力验证报告

> **验证对象**: SKILL.md Phase 4 INDEX Agent Prompt + Phase 5 Semantic Reorganization
> **验证日期**: 2026-03-24
> **验证输入**:
> - `.agents/skills/codebase-explorer/SKILL.md` (Phase 4 INDEX Agent Prompt)
> - `optimization_prompts/results/02b_skill_design_v2.md` Section 5 (INDEX Agent 设计)
> - `optimization_prompts/results/03_final_progressive_scheme.md` Section 2.3 (Flask 文档树) + Section 2.4 (Agent 角色边界表)
> - `optimization_prompts/results/02a_code_analysis_v2.md` Section 4.3 (03_feature_cones.json schema) + Section 4.5 (05_task_manifest.json schema)

---

## 1. 模拟分析: INDEX Agent 处理 Flask 代码库

假设 Flask 代码库已完成 Phase 1-3, 以下 JSON 数据和 SNIPPET 文件已生成:

### 1.1 假设的输入数据

**03_feature_cones.json** 包含 7 个 cone (基于 03_final_progressive_scheme.md Section 2.3):

| cone_id | cone_name | exclusive_files | exclusive_total_tokens | dag_layer |
|---------|-----------|-----------------|------------------------|-----------|
| feature_request_handling | 请求处理 | views.py, wrappers.py | 5880 | 3 |
| feature_cli | CLI 命令行接口 | cli.py | 8750 | 3 |
| feature_testing | 测试工具 | testing.py | 4400 | 3 |
| feature_blueprints | 蓝图系统 | blueprints.py | 3200 | 3 |
| infra_core_runtime | 核心应用运行时 (SCC) | app.py, ctx.py, globals.py | 24650 | 2 |
| infra_sansio | SansIO 应用抽象层 | sansio/app.py, sansio/scaffold.py | 14034 | 1 |
| feature_json_serialization | JSON 序列化 | json/__init__.py, json/provider.py | 3500 | 2 |

**05_task_manifest.json** 包含的任务分配 (基于 02a Section 4.5):

| task_id | type | feature_cones | total_tokens |
|---------|------|---------------|--------------|
| task_001 | single | feature_cli | 10750 |
| task_002 | batch | feature_request_handling, feature_testing | 16280 |
| task_003 | split (Part 1) | infra_core_runtime | 13051 |
| task_004 | split (Part 2) | infra_core_runtime | 11600 |
| task_005 | single | feature_blueprints | 5200 |
| task_006 | batch | feature_json_serialization, infra_sansio | ~17534 |

**SNIPPET 文件** 全部存在于 `.codebase-analysis/snippets/` 目录下 (7 个 cone 各一个 SNIPPET).

---

### 1.2 场景 A: Batch 任务聚合 (task_002: request_handling + testing)

**输入条件**: task_002 是 batch 类型, 包含 `feature_request_handling` 和 `feature_testing` 两个 cone. Phase 3 DETAIL Agent 已为每个 cone 分别生成 DETAIL.md 和 SNIPPET.md.

**INDEX Agent 需要完成的工作**:
1. 从 `03_feature_cones.json` 读取两个 cone 的架构信息
2. 从 `snippets/cone_request_handling.md` 和 `snippets/cone_testing.md` 读取摘要
3. 在 INDEX.md 的核心功能列表中, 为两个 cone 分别创建条目
4. 根据 `doc_plan.needs_overview` 判断是否为每个 cone 生成 OVERVIEW.md
5. 在 Mermaid 图中准确反映两个 cone 的依赖关系 (来自 `dependency_map`)

**当前 Prompt 能力评估**:

| 能力需求 | 支持度 | 分析 |
|----------|--------|------|
| 识别 batch 内含多个 cone | **部分支持** | Prompt 模板通过 `{{#each cone_snippets}}` 迭代所有 cone, 但未明确说明 batch 的概念. INDEX Agent 收到的是"所有 cone"的数据, 不区分哪些 cone 来自同一个 batch task. 这在 Phase 4 初始组装时是正确的 (INDEX Agent 看到全局), 但 02b Section 2 描述 Phase 4 为"按 batch 并行"的多个 INDEX Agent, 而 SKILL.md 的 Prompt 模板呈现的是单个 INDEX Agent 处理所有 cone. |
| 为每个 cone 生成独立条目 | **完全支持** | `{{#each cones_by_layer_desc}}` 按 DAG 层级遍历所有 cone, 每个 cone 获得一个 `### {{cone_name}}` 条目 |
| 生成正确的 Mermaid 图 | **完全支持** | Check 2 (Dependency Edge Consistency) 明确要求边数精确匹配 `dependency_map` |
| 判断是否需要 OVERVIEW | **完全支持** | Check 4 (OVERVIEW Requirement) 明确要求仅当 `doc_plan.needs_overview: true` 时生成 |

**关键发现**: SKILL.md 的 INDEX Agent Prompt 设计为**单个全局 INDEX Agent**, 但 02b Section 2 的 Phase 4 设计为**多个 INDEX Agent 按 batch 并行**. 这是一个设计不一致. SKILL.md 没有体现"batch 级 INDEX"的概念 -- 它只有一个全局 INDEX.md 的输出.

---

### 1.3 场景 B: Split 任务处理 (task_003/004: core_runtime 拆分)

**输入条件**: `infra_core_runtime` 因 token 超出预算被拆分为两个 split 任务:
- Part 1 (task_003): `app.py` -> `DETAIL_app.md`
- Part 2 (task_004): `ctx.py + globals.py` -> `DETAIL_ctx_globals.md`

Phase 3 的两个 split DETAIL Agent 已分别生成:
- `.codebase-docs/core-runtime/DETAIL_app.md`
- `.codebase-docs/core-runtime/DETAIL_ctx_globals.md`
- `.codebase-analysis/snippets/cone_core_runtime.md` (仅 Part 1 Agent 生成)

**INDEX Agent 需要完成的工作**:
1. 识别 `core-runtime` 有多个 DETAIL 文件 (split 场景)
2. 为 `core-runtime` 生成 OVERVIEW.md, 列出两个 DETAIL 子文件及其职责
3. 在 OVERVIEW.md 中生成组件列表: `[DETAIL_app.md](DETAIL_app.md)` 和 `[DETAIL_ctx_globals.md](DETAIL_ctx_globals.md)`
4. 在 INDEX.md 中使用 `cone_core_runtime.md` SNIPPET 内容嵌入摘要, 并链接到 `core-runtime/OVERVIEW.md`

**当前 Prompt 能力评估**:

| 能力需求 | 支持度 | 分析 |
|----------|--------|------|
| 识别 split 产生的多个 DETAIL | **部分支持** | Prompt 中 OVERVIEW 模板的"组件列表"段确实列出了 `DETAIL_views.md`, `DETAIL_ctx.md` 等链接示例. 但 Prompt 没有解释如何从输入数据中获知某个 cone 有多个 DETAIL 文件. `doc_plan_json` 中应包含此信息, 但 Prompt 没有明确说明 `doc_plan` 中 split 任务的 DETAIL 文件列表结构 |
| 生成 OVERVIEW.md 的组件列表 | **完全支持** | OVERVIEW 模板明确包含 `## 组件列表` 段, 示例展示了表格格式的 DETAIL 链接 |
| 正确的相对路径链接 | **完全支持** | Link Path Rules 表清晰定义了 depth 0/1/2 的 `../` 规则. OVERVIEW.md (depth 1) 到 DETAIL.md (same dir) 使用 `DETAIL.md` 直接引用 |
| 处理单一 SNIPPET 映射多个 DETAIL | **部分支持** | Prompt 按 cone 维度嵌入 SNIPPET, 这是正确的 (一个 cone 只有一个 SNIPPET). 但 Prompt 没有明确说明: 当 cone 被 split 时, INDEX.md 的链接应指向 OVERVIEW.md 而非 DETAIL.md |

**关键发现**: `doc_plan_json` 的 schema 未在 SKILL.md 或 02b 中完整定义. INDEX Agent 需要从 `doc_plan_json` 获知哪些 cone 有多个 DETAIL 文件, 但当前 Prompt 没有解释 `doc_plan` 中的具体字段结构. 这导致 INDEX Agent 无法确定性地区分 "single DETAIL" 和 "split DETAIL" 场景.

---

### 1.4 场景 C: Single Cone (task_001: CLI, task_005: blueprints)

**输入条件**: `feature_cli` 和 `feature_blueprints` 各为 single 类型任务, 每个 cone 只有一个 DETAIL.md:
- `.codebase-docs/cli/DETAIL_cli.md`
- `.codebase-docs/blueprints/DETAIL_blueprints.md`
- 各自的 SNIPPET 文件已存在

**INDEX Agent 需要完成的工作**:
1. 在 INDEX.md 中嵌入 SNIPPET 内容, 链接到 `cli/DETAIL_cli.md` 和 `blueprints/DETAIL_blueprints.md`
2. 根据 `doc_plan.needs_overview` 判断 -- single DETAIL cone 通常不需要 OVERVIEW
3. 在 `doc-index.json` 中为每个 cone 创建完整的条目

**当前 Prompt 能力评估**:

| 能力需求 | 支持度 | 分析 |
|----------|--------|------|
| 嵌入 SNIPPET 到 INDEX.md | **完全支持** | `{{embed_snippet_content}}` 直接嵌入 SNIPPET 文本 |
| 生成正确的链接 | **完全支持** | INDEX.md (depth 0) 到 DETAIL.md (depth 1): `{cone}/DETAIL.md` -- Link Path Rules 覆盖此场景 |
| 跳过不需要的 OVERVIEW | **完全支持** | Check 4 明确: 仅当 `needs_overview: true` 时生成 |
| 生成 doc-index.json | **完全支持** | Output 3 schema 完整, 包含 `cone_id`, `detail_path`, `source_files`, `dependencies` 等必要字段 |

**结论**: Single cone 场景是 INDEX Agent 最简单的处理路径, 当前 Prompt 完全覆盖.

---

### 1.5 场景 D: 缺失 SNIPPET 处理

**输入条件**: 假设 `feature_testing` 的 DETAIL Agent 因故未完成, 其 SNIPPET 文件不存在.

**INDEX Agent 需要完成的工作**:
1. 在 Pre-Flight Validation Check 1 中识别缺失的 SNIPPET
2. 在 INDEX.md 中写入 placeholder: `### 测试工具 _(documentation pending)_`
3. 在 `doc-index.json` 中标记 `status: "pending"`
4. 不为此 cone 生成 OVERVIEW.md

**当前 Prompt 能力评估**: **完全支持**. Check 1 (SNIPPET Completeness) 明确定义了缺失处理方案, 包括 placeholder 格式和 doc-index.json 的 status 设置.

---

## 2. Phase 5 Reorganization Agent 能力验证

### 2.1 验证对象

Phase 5 Reorganization Agent 的设计来源:
- 02b Section 6.5 (Semantic Reorganization 完整设计)
- SKILL.md Phase 5 段 (当前为空 -- SKILL.md 将 Phase 5 定义为"Validate (Automated Script)", 没有 Reorganization Agent)

**重要发现**: SKILL.md 中的 Phase 5 是"验证脚本", **不是 Semantic Reorganization**. 02b 的 6-Phase 工作流 (Index -> Validate -> DETAIL -> INDEX Assembly -> Semantic Reorganization -> Validate) 与 SKILL.md 的 5-Phase 工作流 (Index -> Validate -> DETAIL -> INDEX Assembly -> Validate) 存在结构性差异. SKILL.md 尚未包含 Phase 5 Semantic Reorganization 的任何内容.

以下验证基于 **02b Section 6.5 的设计文档**, 而非 SKILL.md 中的实际 Prompt.

### 2.2 操作 1: Move (移动 DETAIL 到另一个 Group)

**场景**: Reorganization Agent 发现 `DETAIL_test_json.md` (当前在 `test-suite` group) 实际上与 `json-serialization` group 的功能更相关.

**操作步骤** (02b 定义):
1. 读 `doc-manifest.json`
2. `mv .codebase-docs/test-suite/DETAIL_test_json.md` -> `.codebase-docs/json-serialization/DETAIL_test_json.md`
3. 更新 manifest: 修改 `groups.test-suite.detail_ids`, `groups.json-serialization.detail_ids`, `details.test-json.group`, `details.test-json.path`
4. 更新 DETAIL 内部的相对链接

**能力评估**:
- **操作协议**: 完整定义. 02b 给出了 4 步操作流程.
- **工具依赖**: 仅需 LLM 内置的 Read/Write/Edit + Bash `mv`. 不需要新 MCP 工具.
- **一致性保证**: `doc-manifest.json` 作为 SSOT, 每次操作后立即更新.
- **支持度**: **完全支持** (在 02b 设计层面).

**潜在问题**:
- DETAIL 内部的相对链接更新需要 LLM 理解当前 depth 和目标 depth 的差异. 02b Prompt 没有提供类似 Phase 4 的 "Link Path Rules" 表给 Reorganization Agent.

### 2.3 操作 2: Merge (合并多个小 DETAIL)

**场景**: `DETAIL_test_cliapp_app.md` 和 `DETAIL_test_cliapp_factory.md` 两个 DETAIL 都描述 CLI 测试 fixture, 应合并为 `DETAIL_cli_app_fixtures.md`.

**操作步骤** (02b 定义):
1. 读取所有待合并的 DETAIL 文件
2. 创建新 DETAIL:
   - 拼接所有 `@unit` 段 (保持标记不变)
   - LLM 为合并内容写新的功能概述
   - 合并 YAML frontmatter 中的 `source_files`
3. 删除旧 DETAIL 文件
4. 更新 manifest: 新 detail entry 替代旧 entries

**能力评估**:
- **@unit 段拼接**: 依赖 Phase 3 DETAIL Agent 正确生成 `@unit` 标记. 02b Section 4.3 强制要求多文件 cone 的 DETAIL 使用 `@unit`. 但单文件 cone 的 DETAIL 不含 `@unit`, 合并两个单文件 cone 的 DETAIL 时, 需要 Reorganization Agent **新增** `@unit` 标记 (02b 约束说"不添加或删除 @unit 标记").
- **功能概述重写**: 02b 明确要求 LLM 为合并后的内容写新的功能概述, 这是 LLM 的核心能力.
- **支持度**: **部分支持**. 合并两个多文件 DETAIL 没有问题; 但合并两个单文件 DETAIL (无 `@unit` 标记) 时存在歧义 -- 02b 约束 "不添加 @unit" 与合并后需要 `@unit` 标记的隐含需求矛盾.

### 2.4 操作 3: Split (从 DETAIL 中抽取 @unit)

**场景**: `DETAIL_blog_feature.md` 包含 `blog.py`, `auth.py`, `db.py` 三个 `@unit`, 其中 `auth.py` 应移到 `auth-module` group.

**操作步骤** (02b 定义):
1. 读 DETAIL
2. 用 `<!-- @unit: filepath` 和 `<!-- @/unit: filepath -->` 定位要抽取的段落
3. 抽取内容写入新 DETAIL_B (含新 YAML frontmatter 和功能概述)
4. 原 DETAIL_A 移除被抽取段, 更新 frontmatter 和功能概述
5. 更新 manifest

**能力评估**:
- **@unit 定位**: 02b 提供了精确的正则匹配模式 (`<!-- @unit: filepath` ... `<!-- @/unit: filepath -->`). LLM 可以通过字符串搜索定位.
- **抽取后的文件完整性**: 02b 要求被抽取后的原 DETAIL 更新功能概述, 这需要 LLM 的语义理解.
- **Token 更新**: `@unit` 标记中的 `tokens` 值可用于 manifest 的 `tokens` 字段更新.
- **支持度**: **完全支持** (在 02b 设计层面). 这是 Phase 5 最核心也是设计最完整的操作.

### 2.5 操作 4: Create/Dissolve Group

**场景 A (Create)**: 将多个认证相关的 DETAIL 归入新创建的 `auth-module` group.

**操作步骤** (02b 定义):
1. `mkdir .codebase-docs/auth-module/`
2. 写新 INDEX.md
3. manifest 中添加 group entry

**场景 B (Dissolve)**: 某个 group 只剩一个 DETAIL, 解散并将其移入 parent group.

**操作步骤** (02b 定义):
1. 将 group 内所有 `detail_ids` 转移到 parent group
2. 删除 group 的 INDEX.md 和目录
3. manifest 中删除 group entry

**能力评估**:
- **Create**: 操作简单, 仅需 mkdir + write. 但 02b 没有定义 Create Group 后新 INDEX.md 的具体模板格式 (Phase 5 的 INDEX.md 与 Phase 4 的有何不同?).
- **Dissolve**: 操作明确, 但 02b 没有定义 Dissolve 的触发条件 (什么情况下 group 应被解散? 是否仅当 detail_ids 为空时?).
- **支持度**: **部分支持**. 基本操作协议有定义, 但触发条件和 INDEX 模板未明确.

---

## 3. 能力矩阵

### 3.1 Phase 4 INDEX Agent (SKILL.md 当前 Prompt)

| 操作类型 | 当前支持度 | 关键缺口 |
|----------|-----------|---------|
| 嵌入 SNIPPET 到 INDEX.md | **完全支持** | -- |
| Mermaid 图生成 (cone 级) | **完全支持** | -- |
| OVERVIEW.md 生成 (multi-DETAIL cone) | **完全支持** | -- |
| 相对路径链接 (全部深度) | **完全支持** | -- |
| Pre-Flight Validation (缺失 SNIPPET) | **完全支持** | -- |
| Pre-Flight Validation (边一致性) | **完全支持** | -- |
| doc-index.json 生成 | **完全支持** | -- |
| Batch 并行 INDEX 组装 | **缺失** | SKILL.md 设计为单个 INDEX Agent, 02b 设计为按 batch 并行 |
| doc-manifest.json 初始化 | **缺失** | SKILL.md 输出不含 doc-manifest.json, 02b 要求 Phase 4 初始化 flat 结构 |
| Split DETAIL 识别与 OVERVIEW 关联 | **部分支持** | Prompt 示例展示了 split 链接, 但未说明如何从输入数据判断哪些 cone 是 split |
| doc_plan_json schema 说明 | **缺失** | Prompt 引用 `{{doc_plan_json}}` 但未定义其 schema, Agent 不知道如何解读 |

### 3.2 Phase 5 Reorganization Agent (02b Section 6.5 设计)

| 操作类型 | 当前支持度 | 关键缺口 |
|----------|-----------|---------|
| Move (DETAIL 跨 group 移动) | **完全支持** | 缺少移动后的链接更新规则表 |
| Merge (多个小 DETAIL 合并) | **部分支持** | 单文件 DETAIL (无 @unit) 合并时的标记处理有歧义 |
| Split (从 DETAIL 抽取 @unit) | **完全支持** | -- |
| Create Group (新建语义分组) | **部分支持** | 新 group INDEX.md 模板未定义; 创建触发条件不明确 |
| Dissolve Group (解散空 group) | **部分支持** | 触发条件未明确定义 |
| doc-manifest.json 更新 | **完全支持** | -- |
| 自底向上执行流程 | **完全支持** | Level N -> Level 0 的层级执行协议清晰 |
| @unit 标记定位 | **完全支持** | 标记格式和正则匹配模式明确 |
| 功能概述重写 (合并/拆分后) | **完全支持** | LLM 核心能力, Prompt 明确要求 |

---

## 4. SKILL.md 与 02b 设计文档的差异分析

### 4.1 结构性差异

| 维度 | SKILL.md (当前实现) | 02b (设计规范) | 差异严重度 |
|------|-------------------|---------------|-----------|
| Phase 数量 | 5 Phases (Index, Validate, DETAIL, INDEX, Validate) | 6 Phases (Index, Validate, DETAIL, INDEX, Reorg, Validate) | **HIGH** -- 缺失 Phase 5 Semantic Reorganization |
| Phase 4 并行策略 | 单个 INDEX Agent 处理所有 cone | 多个 INDEX Agent 按 batch 并行 | **MEDIUM** -- 单 Agent 可工作但不支持大型代码库并行 |
| Phase 4 输出 | INDEX.md + OVERVIEW.md + doc-index.json | INDEX.md + OVERVIEW.md + doc-manifest.json (初始版) | **HIGH** -- 缺失 doc-manifest.json |
| doc_plan.json | 引用但未定义 schema | 02b 未完整定义 schema (但 02a 的 04_file_tokens.json 是实际文件) | **MEDIUM** -- 命名混乱 |
| 输入文件 3 名称 | `04_doc_plan.json` (在 Prompt 模板中) | `04_file_tokens.json` (02a/02c 权威命名) | **MEDIUM** -- SKILL.md 使用了 02b 的旧命名 |

### 4.2 字段命名差异 (Check 5 裁决未在 SKILL.md 中执行)

03_final_progressive_scheme.md Check 5 裁决: Validator Prompt 中的字段名应以 02a JSON schema 为准.

| SKILL.md Prompt 中的字段 | 02a JSON schema 权威字段 | 状态 |
|--------------------------|------------------------|------|
| `cone_name` | `name` | **未更新** |
| `files` | `exclusive_files` | **未更新** |
| `cone_token_estimate` | `exclusive_total_tokens` | **未更新** |
| `layers` | `layers_within_cone` | **未更新** |
| `dependency_edges` | 顶层 `weighted_edges` (不在 cone 对象内) | **未更新** |

注: 这些字段主要影响 Phase 2 Validator Prompt, 但 INDEX Agent Prompt 中引用的 `{{feature_cones_json}}` 也会受到影响 -- INDEX Agent 需要知道用什么字段名来解析 cone 数据.

---

## 5. 识别的可改进点

### 改进点 1 (HIGH): SKILL.md 缺失 Phase 5 Semantic Reorganization

**问题**: SKILL.md 的 5-Phase 工作流完全没有 Semantic Reorganization 阶段. 02b Section 6.5 定义了完整的 Phase 5 设计 (包括 doc-manifest.json schema, 四种操作协议, Reorganization Prompt 模板, 自底向上执行流程), 但这些内容未被纳入 SKILL.md.

**影响**: 对于含有大量孤岛 cone 的代码库 (如 Flask 的 54 个 cone 中 50 个是 1-file cone), 没有 Phase 5 意味着文档结构将保持扁平, 无法通过语义理解进行合并/拆分/分组.

**建议修复**: 在 SKILL.md 中新增 Phase 5 段, 包含:
- Reorganization Agent Prompt 模板 (从 02b Section 6.5 迁移)
- doc-manifest.json schema
- 四种操作 (Move/Merge/Split/Create Group) 的协议说明
- `@unit` 标记的角色说明
- 自底向上的执行流程
- 将当前 Phase 5 (Validate) 重编号为 Phase 6

### 改进点 2 (HIGH): Phase 4 Prompt 缺失 doc-manifest.json 初始化

**问题**: 02b Section 2 明确说 Phase 4 需要初始化 `doc-manifest.json` (flat 结构), 但 SKILL.md 的 INDEX Agent Prompt 的 Outputs 段只定义了 3 个输出 (INDEX.md, OVERVIEW.md, doc-index.json), 没有 doc-manifest.json.

**影响**: 如果 Phase 5 被补充到 SKILL.md 中, 它将无法获取 Phase 4 应产出的 doc-manifest.json, 导致 Reorganization Agent 没有 SSOT.

**建议修复**: 在 INDEX Agent Prompt 模板的 Outputs 段新增 Output 4: doc-manifest.json, 包含:
- Schema 定义 (从 02b Section 6.5 迁移)
- 初始化规则: flat 结构, 每个 DETAIL 一个 entry, 每个 group 从 batch 对应的 cone 集合初始化
- 字段填充来源: `details.*.units` 从 DETAIL 的 `@unit` 标记提取; `details.*.tokens` 从 DETAIL 字符数 / 4 估算

### 改进点 3 (MEDIUM): doc_plan_json 输入 schema 未定义

**问题**: INDEX Agent Prompt 的 Input 3 引用 `{{doc_plan_json}}`, 但 SKILL.md 和 02b 都没有定义 `doc_plan.json` 的完整 schema. 02a/02c 的权威文件 4 是 `04_file_tokens.json` (per-file token 估算), 而 02b 使用了 `04_doc_plan.json` (文档树结构) 这个不同名称. 03_final_progressive_scheme.md Check 2 裁决以 02a/02c 命名为准 (`04_file_tokens.json`), 这意味着 `doc_plan_json` 这个输入来源不确定.

**建议修复**:
- 确定 `doc_plan_json` 的实际数据来源. 可能选项:
  - 来自 `04_file_tokens.json` (仅包含 token 信息, 不含文档树结构)
  - 来自 `05_task_manifest.json` (包含 `output_files` 和 `feature_cones` 字段, 可推断文档结构)
  - 新增一个导出字段, 在 `analyze_codebase()` 输出中增加 `needs_overview` 判断
- 在 Prompt 中明确定义 `doc_plan_json` 的 schema, 至少包含:
  ```json
  {
    "cones": [
      {
        "cone_id": "feature_cli",
        "needs_overview": false,
        "detail_count": 1,
        "detail_files": ["cli/DETAIL_cli.md"]
      }
    ]
  }
  ```

### 改进点 4 (MEDIUM): INDEX Agent 不知道 split DETAIL 的文件列表

**问题**: 当 cone 被 split 时, Phase 3 产出多个 `DETAIL_{slug}.md` 文件. INDEX Agent 需要在 OVERVIEW.md 的"组件列表"中列出这些文件, 但 Prompt 没有说明从哪个输入获取 split cone 的 DETAIL 文件列表.

**建议修复**: 在 `doc_plan_json` 或 `05_task_manifest.json` 的注入数据中, 对 split 类型的 cone 明确列出所有 DETAIL 文件路径:
```json
{
  "cone_id": "infra_core_runtime",
  "needs_overview": true,
  "detail_files": [
    "core-runtime/DETAIL_app.md",
    "core-runtime/DETAIL_ctx_globals.md"
  ]
}
```

### 改进点 5 (LOW): Reorganization Prompt 缺少 Link Path Rules

**问题**: Phase 4 的 INDEX Agent Prompt 包含详细的 "Link Path Rules" 表 (depth 0/1/2 到各类文档的 `../` 计算). Phase 5 的 Reorganization Prompt (02b Section 6.5) 没有类似的链接规则表. Move 操作后, DETAIL 内部的相对链接需要更新, 但 Agent 没有规则表指导.

**建议修复**: 在 Reorganization Prompt 模板中添加 Link Path Rules 段, 或至少添加一条指令: "Move 操作后, 按照 DETAIL 新位置的 depth 重新计算所有相对链接 (参照 INDEX Agent 的 Link Path Rules)".

### 改进点 6 (LOW): Merge 操作对单文件 DETAIL 的 @unit 处理歧义

**问题**: 02b Section 6.5 约束"不添加或删除 @unit 标记". 但单文件 cone 的 DETAIL 不含 `@unit` (02b Section 4.3 规则: `file_count == 1` 时不需要). 合并两个单文件 DETAIL 时, 结果应该是多文件 DETAIL (需要 `@unit`), 这与"不添加 @unit"的约束矛盾.

**建议修复**: 修改约束为: "不删除已有的 @unit 标记; 合并操作产生的新多文件 DETAIL 必须为原始各文件的内容添加 @unit 标记".

---

## 6. 验收标准自评

| 验收标准 | 状态 | 说明 |
|---------|------|------|
| Flask 示例的模拟分析涵盖至少 3 种场景 | **PASS** | 覆盖 4 种场景: Batch 聚合 (1.2), Split 处理 (1.3), Single Cone (1.4), 缺失 SNIPPET 处理 (1.5) |
| 明确指出 INDEX Agent 当前 Prompt 中 >= 2 个可改进点 | **PASS** | 指出 6 个可改进点: (1) 缺失 Phase 5, (2) 缺失 doc-manifest.json, (3) doc_plan_json 未定义, (4) split DETAIL 列表获取, (5) Reorg 缺 Link Rules, (6) Merge @unit 歧义 |
| Phase 5 能力验证覆盖 Move/Merge/Split/Create Group 四种操作 | **PASS** | Section 2.2-2.5 分别验证四种操作, 包含场景、步骤和支持度评估 |
| 输出包含"能力矩阵"表格 | **PASS** | Section 3 包含 Phase 4 (11 项) 和 Phase 5 (9 项) 两个能力矩阵表格 |
