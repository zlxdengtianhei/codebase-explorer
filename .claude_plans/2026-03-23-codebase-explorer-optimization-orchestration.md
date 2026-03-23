> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

# Plan: codebase-explorer-optimization-orchestration

**Date**: 2026-03-23
**Version**: 1.0
**Project**: codebase-explorer @ `/Users/lexuanzhang/code/codebase-explorer`
**Plan File**: `/Users/lexuanzhang/code/codebase-explorer/.claude_plans/2026-03-23-codebase-explorer-optimization-orchestration.md`

---

## Block 1 — Context（背景）

### 任务背景

codebase-explorer v1.0 已完整实现（18个任务全部 ✅），但 E2E 测试揭示了3个系统性问题：

1. **流程错误**：MCP Server 直接用 Jinja2 模板生成文档，跳过了 LLM 真正阅读和理解代码的环节，`submit_analysis()` 从未被调用
2. **职责越界**：文档生成逻辑（应由 Agent 做）硬编码进了 MCP（应只做确定性计算）；SQLite + 5表 + checkpoint 系统对单 Agent 流程过度复杂
3. **算法不足**：深度规划用阈值表"猜"层级，而不是从 DAG 结构中读取；只用 import 边，丢弃了函数调用图和继承图；`module_0`/`module_7` 等无语义命名；52/61 链接断裂

用户在 `optimization_prompts/organized/` 中已整理了完整的第一版优化分析文档（5个文件）：
- `00_vision_and_requirements.md`：需求愿景（14个需求点 + 6条设计思想）— **核心文档，每个 Sub-agent 必须读**
- `01_code_analysis_architecture.md`：代码分析算法优化（SCC/DAG/功能锥体/加权图）
- `02_skill_design.md`：Skill 结构和 Prompt 设计优化
- `03_responsibility_separation.md`：MCP vs Skill vs Agent 职责边界，工具精简 15→6
- `04_current_issues_diagnosis.md`：E2E 问题诊断和可保留组件分析

**本计划目标**：通过6个 Agent 的编排，将上述第一版分析深化为 V2，最终产出一个可直接执行的实现优化 PLAN。

### 设计原则（来自需求文档）

- **MCP = 数据层**：确定性计算（代码解析、图算法、Token 估算），零 LLM
- **Skill = 编排层**：定义 Agent 工作流、Prompt 模板、调度策略
- **Agent = 智能层**：真正阅读代码并理解语义，撰写文档内容
- **功能优先**：以"功能锥体"（Feature Cone）组织文档，而非文件树
- **每步持久化**：流水线每步产出 JSON/Markdown 文件，支持断点恢复

### 约束条件

- 所有输出文件写入 `optimization_prompts/results/`（已创建）
- 最终 PLAN 写入 `.claude_plans/`
- **禁止**修改 `optimization_prompts/organized/` 中的任何现有文件
- **禁止**修改任何源代码（`src/`、`tests/`、`.agents/` 等）

### 执行预算

```
执行预算:
  预估总任务数: 6
  预估每任务耗时: 10-20 分钟
  预估总耗时: 70-120 分钟
  Context 窗口评估: 可能需要 2-3 轮 /clear，建议每个 Phase 后检查 context 用量
```

---

## Block 2 — Execution Progress（执行进度）

- [x] T-01: 当前架构说明 → sub-agent Explore → `optimization_prompts/results/01_current_architecture.md` ✅ 2026-03-23
- [x] T-02a: 代码分析架构优化 V2 → agent architect → `optimization_prompts/results/02a_code_analysis_v2.md` ✅ 2026-03-23
- [x] T-02b: Skill 设计优化 V2 → agent architect → `optimization_prompts/results/02b_skill_design_v2.md` ✅ 2026-03-23
- [x] T-02c: 职责分离优化 V2 → agent architect → `optimization_prompts/results/02c_responsibility_v2.md` ✅ 2026-03-23
- [x] T-03: 整合最终渐进式披露方案 → agent architect → `optimization_prompts/results/03_final_progressive_scheme.md` ✅ 2026-03-23
- [x] T-04: 生成具体实现优化 PLAN → general-purpose agent → `.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md` ✅ 2026-03-23

---

## Block 3 — Agent Responsibility Matrix（Agent 职责矩阵）

---

### T-01: 当前架构说明

```
Skill: sub-agent type Explore
目标: 对 codebase-explorer 的当前完整实现给出详细架构说明文档

输入（只读，不修改）:
  主要代码文件:
    - /Users/lexuanzhang/code/codebase-explorer/src/server.py
    - /Users/lexuanzhang/code/codebase-explorer/src/doc/depth_planner.py
    - /Users/lexuanzhang/code/codebase-explorer/src/doc/_tree_builder.py
    - /Users/lexuanzhang/code/codebase-explorer/src/doc/generator.py
    - /Users/lexuanzhang/code/codebase-explorer/src/graph/dependency.py
    - /Users/lexuanzhang/code/codebase-explorer/src/graph/grouper.py
    - /Users/lexuanzhang/code/codebase-explorer/src/graph/ordering.py
    - /Users/lexuanzhang/code/codebase-explorer/src/budget/estimator.py
    - /Users/lexuanzhang/code/codebase-explorer/src/budget/controller.py
    - /Users/lexuanzhang/code/codebase-explorer/src/state/database.py
    - /Users/lexuanzhang/code/codebase-explorer/src/state/models.py
  Skill 定义:
    - /Users/lexuanzhang/code/codebase-explorer/.agents/skills/codebase-explorer/SKILL.md
  已知问题:
    - /Users/lexuanzhang/code/codebase-explorer/tests/e2e_validation_report.md

操作范围:
  创建: [optimization_prompts/results/01_current_architecture.md]
  修改: []
  禁止修改: [src/, tests/, .agents/, optimization_prompts/organized/]

输出文档必须包含以下7个章节:
  1. 系统三层架构总览（MCP Server / Skill / Agent 职责现状）
  2. MCP Server 工具清单（全部15个工具，按功能分组，每个工具的输入/输出/作用）
  3. 代码分析层实现（parser/graph/budget 的关键函数和数据流）
  4. 文档生成层实现（depth_planner 三维算法 + generator Jinja2 流程 + 状态机 SQLite）
  5. Skill 工作流（5-Phase 全流程，每个 Phase 的角色和调用链）
  6. 完整数据流（从 index_codebase() 到 generate_doc() 的端到端路径，含数据格式）
  7. E2E 失败问题清单（来自 e2e_validation_report.md 的4类问题及根因）

验收标准:
  - [ ] 文件存在且 > 1500 tokens
  - [ ] 包含全部7个章节标题
  - [ ] 准确描述了15个 MCP 工具（通过搜索 server.py 确认数量）
  - [ ] 包含 depth_planner.py 的三维深度算法（三个维度：structural/complexity/token）
  - [ ] 包含 E2E 测试的4类失败原因

超时: 15 分钟
```

---

### T-02a: 代码分析架构优化 V2

```
Skill: agent architect
目标: 深化第一版代码分析优化文档，产出算法设计更完整、边界情况更清晰的 V2

输入（只读）:
  当前架构说明: optimization_prompts/results/01_current_architecture.md   [等待 T-01]
  核心需求文档: optimization_prompts/organized/00_vision_and_requirements.md
  V1 优化文档: optimization_prompts/organized/01_code_analysis_architecture.md

操作范围:
  创建: [optimization_prompts/results/02a_code_analysis_v2.md]
  修改: []
  禁止修改: [optimization_prompts/organized/, src/, tests/]

深度思考任务（必须逐一回答）:
  1. graph-sitter 的 API 可行性验证：
     - 是否提供 function_calls（跨文件函数调用图）？
     - 是否提供 class.base_classes（继承关系）？
     - 如果某个 API 不存在，备选方案是什么（AST 解析？）
  2. 加权多关系图的完整算法：
     - import 权重 1、call 权重 2、inheritance 权重 3 的依据？
     - 如何处理同一对文件间有多种关系（import + call）的情况？
  3. 功能锥体提取算法的完整步骤：
     - 如何定义"入口点"（Feature Root）？
     - 如何处理"共享代码"（被 N 个功能锥体都依赖）的阈值？N=2？N=3？
     - 如何处理循环依赖（SCC）的功能锥体归属？
  4. 5个 JSON 输出文件的完整 Schema：
     - 01_structure.json 的精确字段（特别是函数调用图和继承图如何表示）
     - 03_feature_cones.json 的精确字段（功能锥体结构、共享依赖表示）
     - 05_task_manifest.json 的精确字段（batch/single/split 类型的字段差异）
  5. 装箱算法（batch 任务分配）的具体实现：
     - 贪心策略的伪代码？
     - split 类型何时触发？如何决定拆成几份？
  6. Louvain 降级策略：
     - 何时使用目录树优先？何时 fallback 到 Louvain？
     - 判断标准是什么？

输出文档结构:
  1. V1→V2 改进摘要表格（哪些内容被细化、哪些被更正）
  2. graph-sitter API 可行性验证清单（含备选方案）
  3. 完整算法设计（SCC/DAG/功能锥体，含伪代码或步骤描述）
  4. 加权图构建的详细设计（含边去重、权重叠加逻辑）
  5. 5个 JSON 文件的完整 Schema（JSON 示例格式）
  6. 装箱算法伪代码
  7. Louvain 降级触发条件
  8. 遗留问题与需要实现时验证的假设

验收标准:
  - [ ] 文件存在且 > 1500 tokens
  - [ ] 包含 graph-sitter API 可行性分析（不能仅说"可行"，要列出具体 API 名称）
  - [ ] 包含5个 JSON 文件的 Schema（JSON 示例，不是文字描述）
  - [ ] 包含装箱算法伪代码
  - [ ] 功能锥体算法中明确了"共享代码"的判定阈值

超时: 15 分钟
```

---

### T-02b: Skill 设计优化 V2

```
Skill: agent architect
目标: 深化第一版 Skill 设计文档，澄清 Prompt 模板、Agent 协调、信息边界等细节

输入（只读）:
  当前架构说明: optimization_prompts/results/01_current_architecture.md   [等待 T-01]
  核心需求文档: optimization_prompts/organized/00_vision_and_requirements.md
  V1 优化文档: optimization_prompts/organized/02_skill_design.md

操作范围:
  创建: [optimization_prompts/results/02b_skill_design_v2.md]
  修改: []
  禁止修改: [optimization_prompts/organized/, .agents/skills/, src/]

深度思考任务（必须逐一回答）:
  1. Phase 2（Validate Structure）审查 Agent 的权限边界：
     - 审查 Agent 只能"建议"还是能直接修改 feature_cones.json？
     - 如果两轮审查结果矛盾，裁决机制是什么？
     - 审查 Agent 的 Prompt 应该是什么？（V1 中缺失）
  2. DETAIL Agent 信息注入的完整性：
     - DETAIL Agent 的 Prompt 中，"System Position"里的依赖信息是注入的
     - 除了依赖信息，还需要注入哪些"架构常量"？（功能名称？模块层级？）
     - Agent 如何知道自己负责的是"请求处理"功能而不是"CLI"功能？
  3. 并行 DETAIL Agent 的输出一致性：
     - 多个 Agent 并行产出的文档如何保持风格一致？
     - 需要 Linter Agent 还是依赖 Prompt 模板约束？
  4. Split 任务的合并策略：
     - 3个 Agent 各产出 DETAIL_part1/2/3.md 后，谁来合并？
     - 合并的具体规则（section 去重、cross-ref 重新生成）？
  5. INDEX Agent 的架构图一致性保证：
     - INDEX Agent 不读源码，但如何确认 SNIPPET 中的依赖关系正确？
     - 如果某个 SNIPPET 与 feature_cones.json 中的依赖数据矛盾，如何处理？
  6. doc-index.json 的完整 Schema：
     - 需要包含哪些字段以支持：链接验证、覆盖率计算、断点恢复？
  7. SKILL.md 的触发词和描述精化：
     - 现有触发词（"architecture docs", "analyze codebase" 等）是否完整？
     - 如何处理只有部分分析结果的情况（例如只想要依赖图，不想要完整文档）？

输出文档结构:
  1. V1→V2 改进摘要表格
  2. 精化的5-Phase 工作流（含决策树和异常处理路径）
  3. 审查 Agent（Phase 2）的完整 Prompt 模板
  4. 改进的 DETAIL Agent Prompt 模板（含所有注入变量的完整列表）
  5. 改进的 INDEX Agent Prompt 模板（含一致性验证规则）
  6. Split 任务合并算法
  7. doc-index.json 完整 Schema（JSON 示例）
  8. 并行 Agent 输出一致性机制
  9. 遗留问题

验收标准:
  - [ ] 文件存在且 > 1500 tokens
  - [ ] 包含审查 Agent 的权限规则（明确"建议"还是"直接修改"）
  - [ ] 包含所有3个 Agent 类型的 Prompt 模板
  - [ ] 给出 doc-index.json 的完整字段（JSON 示例格式）
  - [ ] 明确了 split 任务的合并负责方和规则

超时: 15 分钟
```

---

### T-02c: 职责分离优化 V2

```
Skill: agent architect
目标: 深化职责分离方案，给出6个新 MCP 工具的完整 API 设计，并整合问题诊断结论

输入（只读）:
  当前架构说明: optimization_prompts/results/01_current_architecture.md   [等待 T-01]
  核心需求文档: optimization_prompts/organized/00_vision_and_requirements.md
  V1 职责分离文档: optimization_prompts/organized/03_responsibility_separation.md
  V1 问题诊断文档: optimization_prompts/organized/04_current_issues_diagnosis.md

操作范围:
  创建: [optimization_prompts/results/02c_responsibility_v2.md]
  修改: []
  禁止修改: [optimization_prompts/organized/, src/, tests/]

深度思考任务（必须逐一回答）:
  1. 6个新 MCP 工具的完整 API 设计：
     - `analyze_codebase(path, languages?)` → 返回值的完整结构
     - `get_structure(module?, file?)` → 支持按模块查询还是按文件查询？
     - `get_feature_cones()` → 返回值格式
     - `get_dependency_graph(scope, target?)` → scope 取值范围？
     - `get_progress()` → 返回哪些字段（总任务数、完成数、每任务状态）
     - `get_file_tokens(file?, module?)` → 返回文件级明细还是模块级汇总？
  2. 工具迁移映射：旧15个工具逐一对应到新6个工具（合并/删除/保留）
  3. JSON 状态文件替代 SQLite：
     - 具体需要持久化哪些数据？（原 5 张表的数据）
     - JSON 状态文件的完整 Schema
     - 文件命名和存储路径（每个项目一个文件？放在哪里？）
  4. submit_analysis() 的去留：
     - V2 中 Agent 写完 DETAIL.md 就算完成，那分析结果存在哪里？
     - 是完全去掉 submit_analysis()，还是改为写文件路径？
  5. 断点恢复机制：
     - 如果 DETAIL Agent 在写第3个文件时失败，如何从第3个文件继续？
     - JSON 状态文件的 "status" 字段粒度是多少？（任务级？文件级？）
  6. 现有 src/ 文件逐一去留决策：
     - 精确列出：删除哪些文件、保留哪些文件、改造哪些文件
     - 改造的文件需要哪些具体修改

输出文档结构:
  1. V1→V2 改进摘要表格
  2. 6个新 MCP 工具的完整函数签名（含参数类型、返回值类型、示例）
  3. 工具迁移映射表（15→6，每个旧工具的去向和原因）
  4. JSON 状态文件完整 Schema（JSON 示例，至少3层嵌套）
  5. 断点恢复机制详细设计（状态机图 or 步骤描述）
  6. submit_analysis() 的最终决策（去留 + 理由）
  7. src/ 文件去留决策表（逐文件列出：删除/保留/改造 + 具体改动）
  8. 遗留问题

验收标准:
  - [ ] 文件存在且 > 1500 tokens
  - [ ] 包含6个工具的完整函数签名（包含参数类型标注）
  - [ ] JSON 状态文件的完整 Schema（JSON 示例）
  - [ ] 工具迁移映射表覆盖了旧15个工具的每一个
  - [ ] src/ 文件去留决策表逐文件列出（不能只说"大幅精简"）

超时: 15 分钟
```

---

### T-03: 整合最终渐进式披露方案

```
Skill: agent architect
目标: 读取所有 V2 文档，检查一致性，整合成最终的渐进式披露方案文档

输入（只读）:
  当前架构: optimization_prompts/results/01_current_architecture.md
  代码分析 V2: optimization_prompts/results/02a_code_analysis_v2.md
  Skill 设计 V2: optimization_prompts/results/02b_skill_design_v2.md
  职责分离 V2: optimization_prompts/results/02c_responsibility_v2.md
  核心需求: optimization_prompts/organized/00_vision_and_requirements.md

操作范围:
  创建: [optimization_prompts/results/03_final_progressive_scheme.md]
  修改: []
  禁止修改: [optimization_prompts/organized/, src/, tests/]

整合任务:
  步骤1: 跨文档一致性检查
    检查以下内容在三个 V2 文档中是否一致（如有矛盾，给出裁决）:
    - MCP 工具数量和名称（02a 和 02c 是否一致）
    - JSON 输出文件数量（5个？6个？名称是否一致）
    - 功能锥体（Feature Cone）的定义和提取流程
    - DETAIL Agent 读取的数据来源（MCP 工具还是 JSON 文件直接读）
    - 审查 Agent 的输入数据（来自 MCP 工具还是 JSON 文件）
    - 断点恢复依赖的状态存储（JSON 文件的字段名是否一致）
    - "功能命名"的负责方（MCP 算法还是审查 Agent 命名）

  步骤2: 整体架构一致性确认
    用以下6个图表确认整合后架构的一致性:
    - 完整数据流图（MCP JSON输出 → 审查Agent → DETAIL Agent → INDEX Agent → 产物）
    - 工具精简前后对比表（旧15个 vs 新6个，最终版本）
    - 文档树示意（以 Flask 为例，完整的 .codebase-docs/ 结构）
    - Agent 角色与职责边界（三类 Agent 的输入/输出/禁止访问）
    - JSON 状态文件结构（最终统一版 Schema）
    - 功能锥体提取完整流程（从 graph-sitter 原始数据到 03_feature_cones.json）

  步骤3: 渐进式披露方案（L0/L1/L2 三层）
    L0 — 全局概览（面向刚接触这个系统的工程师）:
      - 一句话总结：这次优化要改什么
      - 优化前 vs 优化后的对比（架构级）
      - 三层职责图（MCP/Skill/Agent）

    L1 — 模块视图（面向需要了解某个模块改什么的工程师）:
      每个功能模块提供:
        - 模块名称和简述
        - 优化方向（1-3条）
        - 参考文档：[文档名 § 章节名]（精确到章节）
        - 关键决策点（需要在实现时确认的事项）

    L2 — 实现指引（面向负责具体实现的工程师）:
      按文件（src/ 中的每个文件）列出:
        - 去留决策（删除/保留/改造）
        - 改造的话，具体改什么
        - 参考文档：[文档名 § 章节名]（精确到章节）

  步骤4: 实现优先级矩阵
    P0（必须先做，其他依赖它）: 列出任务
    P1（核心功能，完成后系统可用）: 列出任务
    P2（优化，完成后系统更好）: 列出任务
    依据：为什么这个优先级？（一句话理由）

输出文档结构:
  ## 1. 跨文档一致性检查结果
     矛盾点（含裁决）/ 重复设计（含合并建议）/ 模糊边界（含明确定义）
  ## 2. 整合后架构确认（6个图表）
  ## 3. 渐进式披露方案
     ### L0: 全局概览
     ### L1: 模块视图（代码分析模块 / Skill编排模块 / 职责边界模块）
     ### L2: 实现指引（逐文件）
  ## 4. 实现优先级矩阵（P0/P1/P2）

验收标准:
  - [ ] 文件存在且 > 2000 tokens
  - [ ] 跨文档一致性检查至少发现并裁决了3个具体矛盾或模糊点
  - [ ] L0/L1/L2 三层结构完整（每层都有实质内容）
  - [ ] L2 逐文件列出了 src/ 下至少10个文件的去留决策
  - [ ] 实现优先级矩阵区分了 P0/P1/P2 并给出理由

超时: 20 分钟
```

---

### T-04: 生成具体实现优化 PLAN

```
Skill: general-purpose
目标: 读取所有分析结果，按照 /op 规范，产出可直接执行的代码改造 PLAN

输入（只读）:
  OP 规范文档: ~/.claude/skills/orchestration-planning/SKILL.md
  核心需求: optimization_prompts/organized/00_vision_and_requirements.md
  最终方案: optimization_prompts/results/03_final_progressive_scheme.md   [等待 T-03]
  当前架构: optimization_prompts/results/01_current_architecture.md
  V2 文档:
    - optimization_prompts/results/02a_code_analysis_v2.md
    - optimization_prompts/results/02b_skill_design_v2.md
    - optimization_prompts/results/02c_responsibility_v2.md
  当前关键源文件（只读参考）:
    - src/server.py
    - src/doc/depth_planner.py
    - src/graph/dependency.py
    - src/graph/grouper.py
    - .agents/skills/codebase-explorer/SKILL.md

操作范围:
  创建: [.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md]
  修改: []
  禁止修改: [src/, tests/, .agents/, optimization_prompts/]

PLAN 产出要求（严格遵循 /op Skill 的 8 区块格式）:
  - 文件顶端必须有 Context 恢复协议头部
  - Block 1: 背景（包含执行预算）
  - Block 2: 执行进度（每个任务一个 checkbox，格式 "- [ ] T-XX: ..."）
  - Block 3: Agent 职责矩阵（每个任务的 Skill、输入、创建/修改/禁止修改文件、
              预期日志输出、验收标准、回滚策略、超时）
  - Block 4: 并行执行图（明确哪些任务可以并行，最大并行数2）
  - Block 5: 文件拆解（所有新建/修改的文件列表）
  - Block 6: 阶段结构（按阶段分组，每个阶段的入口/退出条件）
  - Block 7: Context 恢复协议（头部+中间状态恢复说明）
  - Block 8: 验收标准（bash 命令可验证的条件）
  - Checkpoint YAML

任务分解要求:
  - 每个需要删除、创建或改造的源文件（.py）各为一个独立任务
  - 任务总数预期 12-20 个
  - 区分三类任务：DEL（删除文件）、NEW（新建文件）、MOD（改造文件）
  - 严格标注每个任务禁止修改哪些其他文件
  - 每个实现任务必须包含预期日志模式（`[COMPONENT] action started/completed`）
  - 每个实现任务必须包含回滚策略

验收标准:
  - [ ] PLAN 文件存在于 .claude_plans/ 目录
  - [ ] 包含完整的8个区块（标题中有 Block 1 到 Block 8）
  - [ ] 至少12个 T-XX 任务（用 grep "^- \[ \] T-" 验证）
  - [ ] 每个任务有 "创建/修改/禁止修改" 三字段
  - [ ] Context 恢复协议头部在文件第1行

超时: 20 分钟
```

---

## Block 4 — Parallel Execution Map（并行执行图）

```
串行步骤（Phase 1）: T-01
  依赖: 无（起点）
  原因: T-02a/b/c 的 Prompt 中需要 T-01 产出的当前架构文档作为输入基础

并行组 A（T-01 完成后同时启动）: T-02a, T-02b
  依赖: T-01 完成
  约束: 各读不同的 V1 分析文档，各写不同的 V2 输出文件，无写入冲突
  最大并行数: 2

串行步骤（并行组 A 完成后启动）: T-02c
  依赖: T-01 完成（T-02c 与 T-02a/b 无数据依赖，仅受并行上限2限制）
  原因: 并行数上限为2，T-02c 等待并行组 A 完成后独立运行

串行步骤（Phase 3）: T-03
  依赖: T-02a + T-02b + T-02c 全部完成
  原因: 需要读取所有3个 V2 文档进行跨文档一致性检查

串行步骤（Phase 4）: T-04
  依赖: T-03 完成
  原因: 需要 03_final_progressive_scheme.md 中的 L2 实现指引和优先级矩阵
```

**执行时序图：**

```
Phase 1     Phase 2（批次1）  Phase 2（批次2）   Phase 3    Phase 4
T-01 ──────→ T-02a ─────────┐
             T-02b ─────────┤
                             ├──→ T-02c ────────→ T-03 ────→ T-04
                             │（等待批次1完成）
             （同时运行）────┘
```

---

## Block 5 — File Decomposition（文件拆解）

**新建文件（所有输出）：**

| 文件路径 | 操作 | 所属任务 | 负责 Agent |
|---------|------|---------|-----------|
| `optimization_prompts/results/01_current_architecture.md` | 创建 | T-01 | Explore |
| `optimization_prompts/results/02a_code_analysis_v2.md` | 创建 | T-02a | architect |
| `optimization_prompts/results/02b_skill_design_v2.md` | 创建 | T-02b | architect |
| `optimization_prompts/results/02c_responsibility_v2.md` | 创建 | T-02c | architect |
| `optimization_prompts/results/03_final_progressive_scheme.md` | 创建 | T-03 | architect |
| `.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md` | 创建 | T-04 | general-purpose |

**只读文件（多任务共享读取，无写入冲突）：**

| 文件 | 读取方（任务） |
|------|-------------|
| `optimization_prompts/organized/00_vision_and_requirements.md` | T-02a, T-02b, T-02c, T-03, T-04 |
| `optimization_prompts/organized/01_code_analysis_architecture.md` | T-02a |
| `optimization_prompts/organized/02_skill_design.md` | T-02b |
| `optimization_prompts/organized/03_responsibility_separation.md` | T-02c |
| `optimization_prompts/organized/04_current_issues_diagnosis.md` | T-02c |
| `optimization_prompts/results/01_current_architecture.md` | T-02a, T-02b, T-02c, T-03, T-04 |
| `src/server.py` | T-01, T-04 |
| `src/doc/depth_planner.py` | T-01, T-04 |
| `src/graph/dependency.py` | T-01 |
| `.agents/skills/codebase-explorer/SKILL.md` | T-01, T-04 |
| `~/.claude/skills/orchestration-planning/SKILL.md` | T-04 |
| `tests/e2e_validation_report.md` | T-01 |

---

## Block 6 — Phase Structure（阶段结构）

### Phase 1: 架构说明

**入口条件**: 计划开始执行，`optimization_prompts/organized/` 中的5个文件存在
**任务**: T-01
**退出条件**: `optimization_prompts/results/01_current_architecture.md` 存在，包含7个章节，> 1500 tokens

---

### Phase 2: 并行深化优化

**入口条件**: Phase 1 完成（`01_current_architecture.md` 存在且有效）
**任务**:
  - 批次1（并行）: T-02a + T-02b（同时启动）
  - 批次2（串行）: T-02c（等待批次1完成后启动）
**退出条件**: `02a_code_analysis_v2.md`、`02b_skill_design_v2.md`、`02c_responsibility_v2.md` 三个文件全部存在且各 > 1500 tokens

---

### Phase 3: 整合

**入口条件**: Phase 2 完成（三个 V2 文件全部存在）
**任务**: T-03
**退出条件**: `03_final_progressive_scheme.md` 存在，包含 L0/L1/L2 三层结构，> 2000 tokens，已完成跨文档一致性检查

---

### Phase 4: PLAN 生成

**入口条件**: Phase 3 完成（`03_final_progressive_scheme.md` 存在且有效）
**任务**: T-04
**退出条件**: `.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md` 存在，包含8个区块，至少12个 T-XX 任务

---

## Block 7 — Context Recovery Protocol（Context 恢复协议）

**Context 恢复协议头部已在文件顶端放置。**

### 中间状态恢复指引

| 已完成的最后任务 | 下一步 |
|----------------|--------|
| 无（刚开始） | 从 T-01 开始 |
| T-01 完成 | 启动 T-02a + T-02b（并行） |
| T-02a/b 完成，T-02c 未完成 | 启动 T-02c |
| T-02a/b/c 全完成 | 启动 T-03 |
| T-03 完成 | 启动 T-04 |

### 失败恢复

- 任务失败时，检查对应输出文件是否存在（部分写入？空文件？）
- 如文件不存在：重新运行该任务
- 如文件存在但不满足验收标准：带"重试"标注重新运行，告知 Agent 上次失败原因
- 任何任务失败超过2次：向用户报告失败原因和已产出的文件列表，请用户决策

---

## Block 8 — Validation / Success Criteria（成功标准）

整个编排完成的验证命令：

```bash
# 验证所有6个输出文件存在
ls -la /Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/
ls -la /Users/lexuanzhang/code/codebase-explorer/.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md

# 验证最终 PLAN 包含足够多的任务
grep -c "^- \[ \] T-" /Users/lexuanzhang/code/codebase-explorer/.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md
# 预期: >= 12

# 验证最终 PLAN 包含8个区块
grep -c "^## Block [1-8]" /Users/lexuanzhang/code/codebase-explorer/.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md
# 预期: 8

# 验证渐进式披露方案包含三层
grep -E "^### L[012]" /Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/03_final_progressive_scheme.md
# 预期: 至少3行

# 验证跨文档一致性检查存在
grep -c "矛盾\|一致性\|裁决" /Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/03_final_progressive_scheme.md
# 预期: >= 3
```

**最终成功标准**：

- [ ] `optimization_prompts/results/` 下存在5个有效的分析文档（T-01 ~ T-03 产出）
- [ ] `03_final_progressive_scheme.md` 包含跨文档一致性检查结果 + L0/L1/L2 三层
- [ ] `.claude_plans/2026-03-23-codebase-explorer-optimization-impl.md` 包含完整8区块 + ≥12个 T-XX 任务
- [ ] 最终 PLAN 文件的每个任务都有明确的文件创建/修改/禁止修改范围

---

## Checkpoint YAML

```yaml
checkpoint:
  phase: 4
  status: done
  current_task: null
  completed_tasks: [T-01, T-02a, T-02b, T-02c, T-03, T-04]
  failed_tasks: []
  last_updated: "2026-03-23T15:30:00"
  git:
    branch: feature/codebase-explorer-impl-2026-03-22
  notes: "All 6 tasks completed. Implementation PLAN ready at .claude_plans/2026-03-23-codebase-explorer-optimization-impl.md"
```
