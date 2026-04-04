# V5 实施状态报告

> 版本：07 | 前置文档：`06_v5_mcp_skill_redesign.md`（需求定义）、`00_vision_and_requirements.md`（愿景）
> 日期：2026-03-28
> 对应分支：`feature/codebase-explorer-impl-2026-03-22`

---

## 一、执行概要

基于 `06_v5` 定义的 R1-R10 需求和 `00_vision` 的 6 条设计思想，执行了完整的 V5 重构。通过 5 轮 Judge 迭代，在 Flask test repo 上达到 24/24 ALL_PASS。

**关键数字：**

| 指标 | 数值 |
|------|------|
| 代码提交 | 10 commits（4 架构 + 1 测试基础设施 + 5 迭代修复） |
| 单元测试 | 680 通过 |
| E2E 迭代 | 5 轮（14→21→23→23→24） |
| E2E 验证 repo | 1/5（仅 Flask） |
| Judge 评分 | 24/24 ALL_PASS（Flask） |

---

## 二、R1-R10 逐条状态

### 已实现并验证（Judge PASS）

| 需求 | 实现方式 | 验证证据 |
|------|---------|---------|
| **R1** MCP 只做文件→模块映射 | `get_modules(summary)` 仅返回模块元信息（名称/文件数/token/依赖），不含函数名/签名 | Judge R1 PASS；summary 返回 <3KB |
| **R2** 函数级依赖 | `get_function_deps(file)` 返回跨文件 source→target 函数调用；结果写入 `06_function_deps.json` | Judge R2 PASS；JSON 含 23 个文件的函数依赖 |
| **R3** 上下文注入控制 | summary 模式不含文件列表；detail 模式只返回单模块文件 | Judge R3 PASS |
| **R4** Token 预算驱动 | `get_modules(module_id)` 返回每文件 `token_count`；`token_budget` 在 summary 中返回 | Judge R4 PASS |
| **R7** 固定格式 | DETAIL: YAML front matter + `<!-- module/file/index-fragment -->` 标记；INDEX: YAML + Mermaid + `<!-- module-index -->` 标记 | Judge R7 PASS |
| **R8** 工具化重组 | `doc_operation` 支持 7 种操作：get_template, get_protocol, update_index, move_detail, list_module_files, merge_modules, reorder_modules | Judge R8 PASS |
| **R9** 可插拔算法 | `GroupingStrategy` Protocol + `FeatureConeStrategy` 实现 + `CODEBASE_EXPLORER_STRATEGY` 环境变量切换 | Judge R9 PASS；`strategy_used` 写入 JSON |
| **R10** 目录+依赖融合 | Feature Cone（Louvain + directory affinity + SCC）产出跨目录模块 | Judge R10 PASS；Flask 的 3 个 cone 均跨多目录 |

### 已实现但验证不充分

| 需求 | 实现方式 | 不足之处 |
|------|---------|---------|
| **R5** DETAIL 三步输出 | E2E prompt 指示逐文件执行：读源码→写四段→查依赖→写 index-fragment | 见下方"Skill 验证缺口"一节 |
| **R6** INDEX 由片段拼合 | `doc_operation("update_index")` 扫描 DETAIL 中的 `<!-- index-fragment -->` 块，直接拼合为 INDEX | 机制已实现并验证；但 Skill 中对此的描述与 E2E prompt 存在差异 |

---

## 三、愿景对照（00_vision 的 6 条设计思想）

| 思想 | 状态 | 说明 |
|------|------|------|
| **思想 1：功能优先，层级内嵌** | ✅ 已实现 | Module 按功能命名（"Tutorial Application & Documentation Setup"），INDEX/Mermaid 使用功能名而非 module_id；模块内文件按 DAG layer 排序 |
| **思想 2：确定性 vs 语义 职责分离** | ✅ 已实现 | MCP 仅输出结构化 JSON（文件列表/依赖图/token 数）；所有语义描述（Purpose/Data Flow/Key Interfaces/Dependencies）由 Agent 读源码产出 |
| **思想 3：架构是计算常量** | ✅ 已实现 | 6 个 JSON 文件持久化架构信息（01_structure → 06_function_deps）；Agent 不"发现"架构，只"填充"语义 |
| **思想 4：三种图算法各司其职** | ✅ 已实现 | SCC（tarjan）→ DAG（condensation）→ Louvain（community detection）+ directory affinity 后处理 |
| **思想 5：每步持久化，断点恢复** | ✅ 已实现 | `submit_analysis` 持久化进度到 state.json；`get_progress` 恢复；Skill 文档包含 Context Compression Recovery 协议 |
| **思想 6：动态预算，按需分配** | ⚠️ 部分实现 | `build_task_manifest` 按 15-30% 比例分配预算；`get_modules(module_id)` 返回每文件 token_count。但 E2E 中 Agent 未严格执行预算截断（未见 Agent 因预算不足而停止读文件的证据） |

---

## 四、实施步骤完成度

### Step 1-5：代码与文档重构 ✅

| Step | 状态 | 主要变更 |
|------|------|---------|
| **Step 1** 清理遗留代码 | ✅ 完成 | 删除 database.py、_tree_builder.py、6 个 legacy models、aiosqlite/jinja2 依赖 |
| **Step 2** MCP Server 修复 | ✅ 完成 | computed fields（layers_within_cone, cohesion_score）、get_modules detail 用 DAG 依赖、删 get_feature_cones、缓存加入 06_function_deps |
| **Step 3** doc_operation 改进 | ✅ 完成 | update_index 扫描 index-fragment、block-level move_detail、list_module_files 别名、get_template/get_protocol 更新 |
| **Step 4** Skill 文档重写 | ✅ 完成 | SKILL.md（9 tools, 4 phases）、DOC_TEMPLATES.md、MCP_TOOLS_REFERENCE.md、4 个 phase 文件、QUALITY_STANDARDS.md |
| **Step 5** 测试更新 | ✅ 完成 | 修复 7 个测试文件的 import 错误；680 tests pass |

### Step 6：Judge-Driven E2E 评估 ⚠️ 部分完成

| 子步骤 | 状态 | 说明 |
|--------|------|------|
| E2E 基础设施搭建 | ✅ | run_real_e2e.sh、verify_real_e2e.sh（17项）、judge_prompt.md（24项）、build_judge_input.sh |
| Flask E2E 迭代 | ✅ | 5 轮迭代达到 24/24 ALL_PASS |
| celery E2E | ❌ 未执行 | |
| fastapi E2E | ❌ 未执行 | |
| rich E2E | ❌ 未执行 | |
| scrapy E2E | ❌ 未执行 | |

---

## 五、Skill 验证缺口（关键未验证项）

### 问题描述

E2E 测试中，子 Claude Code 收到的是 `run_real_e2e.sh` 中**硬编码的详细 prompt**（117 行），而非通过调用 `/codebase-explorer` Skill 来执行。这意味着：

**Step 4 重写的所有 Skill 文档（SKILL.md、phase 文件、DOC_TEMPLATES.md 等）从未在 E2E 中被实际加载和使用。**

### E2E Prompt 与 Skill 的已知差异

| 维度 | E2E Prompt（实际测试的） | Skill 文档（未测试的） |
|------|------------------------|---------------------|
| **Sub-agent** | 单线程逐模块处理 | Phase 3 要求 "spawn one sub-agent per module"（并行） |
| **Token budget** | 一句 "Scale doc depth proportionally" | 完整预算逻辑：`accumulated_tokens + file_token_count <= budget`，超出即停 |
| **依赖写入** | 一步到位写四段 | Step 1 写占位符 → Step 2 调 get_function_deps 替换 |
| **Phase 4 review** | 后期迭代追加了 mandatory review | 结构化 3 步检查（名称→错误放置→排序） |
| **Style constraints** | 无 | 6 条约束（英文内容、中文 section header、无主观评价等） |
| **Phase 5 验证** | 无 | phase5-verify.md 有完整质量检查清单 |
| **INDEX DETAIL 链接** | 无 `[→ DETAIL]` 链接 | DOC_TEMPLATES 要求 `[→ DETAIL]({module_id}/DETAIL.md)` |
| **move_detail 参数** | `filepath="src/flask/app.py"`（正确） | phase4-index.md 写的 `file_path="DETAIL.md"`（**错误**） |

### 影响评估

Skill 文档中的 phase4-index.md 关于 `move_detail` 的参数示例是**错误的**（`file_path="DETAIL.md"` 应为 `filepath="src/xxx.py"`）。如果真实用户通过 Skill 执行 Phase 4，move_detail 调用会失败。

其余差异属于"Skill 更详细但 E2E prompt 更直接"的风格差异，不影响功能正确性，但意味着 Skill 指导下的 Agent 行为可能与 E2E 测试验证过的行为不完全一致。

---

## 六、与 06_v5 设计方案的偏差

### 6.1 已实现但实现方式不同

| 06_v5 设计 | 实际实现 | 偏差原因 |
|-----------|---------|---------|
| **5 Phase**（Phase 5 = 语义重组） | **4 Phase**（Phase 4 = INDEX 组装 + 重组合并） | Plan 讨论中决定合并，减少 Agent 交互轮次 |
| **三文档模型**（INDEX + OVERVIEW + DETAIL） | **两文档模型**（INDEX + DETAIL） | Plan 讨论中决定去掉 OVERVIEW，index-fragment 替代其功能 |
| **TwoStageStrategy** 作为默认 | **FeatureConeStrategy** 作为默认 | 沿用已有的 feature cone 提取作为基础策略 |
| DETAIL 每文件两段（函数与类 + 依赖关系） | DETAIL 每文件四段（功能概述 + 数据流 + 核心接口 + 依赖关系） | Plan 讨论中确定四段更符合"理解代码功能"的目标 |
| `update_index` 替换指定模块摘要 | `update_index` 全量重新组装 INDEX | 全量重建更可靠，避免部分更新导致不一致 |

### 6.2 未实现

| 06_v5 设计 | 状态 | 说明 |
|-----------|------|------|
| **FusionStrategy**（DIS 增强图 → Louvain） | ❌ P4 优先级，未实施 | `strategies.py` 预留了接口，可后续添加 |
| **DirectoryFirstStrategy** | ❌ P4 优先级，未实施 | 同上 |
| `analyze_codebase` 的 `exclude_paths` / `include_tests` 参数 | ⚠️ 部分 | `_EXCLUDED_DIRS` 硬编码排除已实现；用户自定义 `exclude_paths` 参数未暴露 |
| `split_module` 的文件级拆分（指定 new_modules + files 分组） | ⚠️ 简化 | 当前 `split_module`（别名 `list_module_files`）仅列出模块文件，需配合 `move_detail` 手动移动 |
| **扩展 ground truth + scoring harness 对接** | ⚠️ 部分 | `scoring_harness.py` 和 `ground_truth.py` 存在但未在 V5 E2E 中使用 |

---

## 七、代码质量

### 测试覆盖

| 测试类别 | 数量 | 覆盖范围 |
|---------|------|---------|
| 单元测试 | 680 | server, server_helpers, graph, parser, budget, depth_planner, state, feature_cone, semantic_hints, weighted_graph, doc_operation |
| E2E pipeline | 1 (Flask) | 完整 4-phase + Judge 24 项 |
| MCP integration | ✅ | test_mcp_integration.py |

### 已删除的遗留代码

| 文件/模块 | 说明 |
|-----------|------|
| `src/state/database.py` | V1 SQLite 层 |
| `src/doc/_tree_builder.py` | 仅被已删函数调用 |
| 6 个 SQLite 模型（ProjectRecord 等） | V1 遗留 |
| `get_feature_cones` MCP tool | 被 `get_modules` 替代 |
| `aiosqlite`, `jinja2` 依赖 | 不再使用 |

---

## 八、后续工作建议

按优先级排序：

### P0：必须完成

1. **修复 Skill phase4-index.md 中 move_detail 的参数错误**
   - 当前：`file_path="DETAIL.md"`
   - 应改为：`filepath="src/xxx.py"`（与 MCP 工具实际参数一致）

2. **在剩余 4 个 test repo 上运行 E2E + Judge**
   - celery, fastapi, rich, scrapy
   - 验证 V5 在不同规模/结构的项目上均能通过
   - Flask 仅有 35 文件 / 3 cones，不能代表大型项目

3. **Skill 端到端验证**
   - 用真实的 `/codebase-explorer` Skill 调用（而非硬编码 prompt）跑一次完整 E2E
   - 验证 Skill 文档能否正确指导 Claude 完成 4-Phase 管线
   - 对比 Skill-driven 产出与 prompt-driven 产出的质量差异

### P1：应该完成

4. **对齐 E2E prompt 与 Skill 文档**
   - INDEX 生成的 DETAIL 链接（`[→ DETAIL]({module_id}/DETAIL.md)`）
   - Phase 5 质量验证步骤
   - Style constraints（英文内容、中文 section header）
   - Token budget 截断逻辑

5. **完善 split_module 为真正的文件级拆分**
   - 06_v5 设计了 `new_modules: [{name, files}]` 参数
   - 当前只是列出文件，无法一次性拆分到新模块

### P2：可以推迟

6. **实现 FusionStrategy 和 DirectoryFirstStrategy**
7. **暴露 `exclude_paths` / `include_tests` 参数给用户**
8. **将 scoring harness 集成到 E2E 评估中（ARI/NMI 指标）**

---

## 附录：Commit 历史

```
e7a7985 feat(v5): E2E ALL_PASS — 24/24 Judge score — iteration 5
53d617b experiment: iter4 — fix R5 (move_detail leaves orphaned heading)
1a89bef experiment: iter3 — fix V1 (functional names in Mermaid + INDEX headings)
aa2a695 experiment: iter2 — fix V4 (Mermaid edges) + V7 (mandatory Phase 4 review)
96fa845 experiment: iter1 — add strategy_used to JSON, improve E2E prompt
13ceaa5 test(e2e): update E2E prompt, verify script, judge prompt for V5
db034a4 test: update tests for V5 architecture
8655fde docs(skill): rewrite for V5 4-phase pipeline, two-document model
e0b24e8 feat(server): V5 server tools — computed fields, doc_operation, remove get_feature_cones
70cca50 refactor: remove dead V1 code (database.py, tree_builder.py, legacy models, unused deps)
```
