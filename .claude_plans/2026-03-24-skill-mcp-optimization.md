> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

```yaml
checkpoint:
  phase: 1
  status: in_progress
  last_completed_task: T-07
  next_task: null
  last_updated: 2026-03-24T17:30:00
  completed: [T-01, T-02, T-03, T-04, T-05, T-06, T-07]
  pending: []
  blocked: []
  status: validating
  fix_loop_count: 0
  current_fix_target: null
  escalated: []
  git:
    branch: feature/codebase-explorer-impl-2026-03-22
    initial_commit: ce79a6d
    commits_made: []
```

---

# PLAN: Codebase Explorer — SKILL.md 全面优化 + MCP 依赖图实现

## Block 1 — Context（背景）

### 问题描述

codebase-explorer 项目的 V2 优化方案已在 `optimization_prompts/results/` 中完整定义（5 份文档，权威规范为 `03_final_progressive_scheme.md`）。MCP Server 层（7 个工具中的 6 个）和状态管理层（json_store.py）已基本实现，但以下关键部分尚未完成：

**SKILL.md（完全未优化）**：
1. **Phase 5 Semantic Reorganization 完全缺失** — 无 Reorganization INDEX Agent 的 Prompt 模板、无 doc-manifest.json 完整 Schema、无 Move/Merge/Split/Create Group 四种操作的定义
2. **现有 Phase 2-4 Agent Prompt 字段名不一致** — 02b 使用 `cone_name`/`files`/`cone_token_estimate`，但权威 Schema（02a）使用 `name`/`exclusive_files`/`exclusive_total_tokens`
3. **Index Agent 的分割/聚合能力未经验证** — 用户核心关注点：按 Skill 协议，INDEX Agent 是否能正确地对功能进行分割与聚合

**MCP 工具（关键缺失）**：
4. `get_dependency_graph()` 是 stub（仅返回硬编码模板），无实际 Mermaid 图生成
5. `build_task_manifest()` 在 server.py 中被调用但可能未在 depth_planner.py 中完整实现

### 用户明确要求

1. 至少 3 个 Agent 从不同方面优化 SKILL.md + 1 个审查 Agent
2. E2E 测试必须验证：MCP 提供代码间依赖图 + 功能集合的聚合结果
3. 验证 Skill 协议是否能让 Index Agent 正确执行功能的分割/聚合

### 不可违反的约束

- 权威文档：字段名以 `02a_code_analysis_v2.md` JSON Schema 为准
- 权威文档：工具 API 以 `02c_responsibility_v2.md` Section 2 为准
- 权威文档：一致性裁决以 `03_final_progressive_scheme.md` 为准
- 所有 JSON 写操作必须使用原子写入（先 .tmp 再 os.replace）
- SKILL.md 中最终工具数为 7 个
- Feature Cone shared_threshold = 2
- 不得修改 optimization_prompts/results/ 中的源文档

### 执行预算

```
执行预算:
  预估总任务数: 7
  预估每任务耗时: 15 分钟
  预估总耗时: ~105 分钟
  最大并行数: 3（用户指定"至少 3 个 Agent"）
  Context 窗口评估: 可在一个 session 内完成（并行执行缩短实际时间至 ~50 分钟）
```

---

## Block 2 — Execution Progress（执行进度）

- [x] T-01: Phase 5 Semantic Reorganization 完整设计 → `general-purpose` Agent → `.claude_plans/artifacts/skill-phase5-design.md` ✅ 2026-03-24
- [x] T-02: Agent Prompt 字段一致性审计与修复 → `general-purpose` Agent → `.claude_plans/artifacts/skill-field-audit.md` ✅ 2026-03-24
- [x] T-03: Index Agent 分割/聚合能力验证 → `general-purpose` Agent → `.claude_plans/artifacts/skill-index-verification.md` ✅ 2026-03-24
- [x] T-04: SKILL.md 全量合并与综合审查 → `general-purpose` Agent → 修改后的 SKILL.md ✅ 2026-03-24
- [x] T-05: `get_dependency_graph()` 实现 → `general-purpose` Agent → `src/server.py` ✅ 2026-03-24
- [x] T-06: `build_task_manifest()` 验证/实现 → `general-purpose` Agent → `src/doc/depth_planner.py` ✅ 2026-03-24
- [x] T-07: E2E 集成测试 → `general-purpose` Agent → `tests/test_e2e_pipeline.py` ✅ 2026-03-24

---

## Block 3 — Agent Responsibility Matrix（Agent 职责矩阵）

### T-01: Phase 5 Semantic Reorganization 完整设计

```
Task T-01 规格：
  Skill: general-purpose (sub-agent)
  角色: Phase 5 设计师

  输入:
    必读:
      - optimization_prompts/results/02b_skill_design_v2.md Section 6.5（Phase 5 完整设计）
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.4（Agent 角色边界表，Reorganization INDEX Agent 行）
      - optimization_prompts/results/03_final_progressive_scheme.md lines 302-307（Phase 5 数据流）
    参考:
      - 当前 SKILL.md Phase 4 section（理解 Phase 4 → Phase 5 接口）

  操作范围:
    创建: [.claude_plans/artifacts/skill-phase5-design.md]
    修改: []
    禁止修改: [.agents/skills/codebase-explorer/SKILL.md, src/**] — 原因: 设计阶段仅产出设计文档

  产出内容要求:
    1. doc-manifest.json 完整 Schema（含初始版和最终版的字段区别）
    2. Reorganization INDEX Agent 完整 Prompt 模板（含变量注入格式）
    3. 四种操作（Move/Merge/Split/Create Group）的精确规则和示例
    4. @unit 标记如何在 Phase 5 中被解析和使用的规则
    5. Phase 5 入口条件（Phase 4 完成标志）和退出条件
    6. 自底向上层级处理的顺序定义
    7. doc-manifest.json 状态转换规则（flat → hierarchical）

  验收标准:
    - [ ] doc-manifest.json Schema 包含 groups/documents/operations 三个顶层字段
    - [ ] Reorganization Prompt 包含 {{batch_index_content}}, {{detail_files}}, {{current_manifest}} 注入变量
    - [ ] 四种操作各有至少一个 Flask 代码库的具体示例
    - [ ] @unit 解析规则与 Phase 3 DETAIL Agent 的 @unit 写入规则一致
    - [ ] 输出文档 > 2000 字

  回滚策略:
    回滚点: 无（仅创建新文件）
    替代方案: 如果 02b Section 6.5 不够详细，参考 03_final 的 L1-B section 自行设计
    丢弃条件: 无（设计文档总可以迭代）

  超时: 15 分钟
```

### T-02: Agent Prompt 字段一致性审计与修复

```
Task T-02 规格：
  Skill: general-purpose (sub-agent)
  角色: 协议一致性审计员

  输入:
    必读:
      - optimization_prompts/results/03_final_progressive_scheme.md Check 5 裁决（字段名权威决定）
      - optimization_prompts/results/02a_code_analysis_v2.md Section 4（5 个 JSON 的权威 Schema）
      - 当前 SKILL.md 全文（审计所有 Agent Prompt 中的字段引用）

  操作范围:
    创建: [.claude_plans/artifacts/skill-field-audit.md]
    修改: []
    禁止修改: [.agents/skills/codebase-explorer/SKILL.md, src/**] — 原因: 审计阶段仅产出审计报告

  产出内容要求:
    1. 逐 Agent Prompt 审计表：当前字段名 vs 权威字段名（02a），标记每个差异
    2. Validator Agent Prompt 修正版（使用 exclusive_files, name, exclusive_total_tokens, layers_within_cone）
    3. DETAIL Agent Prompt 字段校验（确认 files_in_cone, dependency_snippets 等注入变量与 JSON Schema 对应）
    4. INDEX Agent Prompt 字段校验（确认链接路径规则表正确性）
    5. submit_analysis() 参数与 02c Section 6 的对照
    6. state.json 任务状态值统一检查（pending/in_progress/complete/failed）
    7. 02b 的 doc-plan.json vs doc-manifest.json 命名统一

  验收标准:
    - [ ] 审计表覆盖全部 3 个现有 Agent Prompt（Validator, DETAIL, INDEX）
    - [ ] 每个差异项标注"02a 权威值"和"当前 SKILL.md 值"
    - [ ] 提供修正后的完整 Prompt 片段（可直接 copy-paste 替换）
    - [ ] submit_analysis() V2 签名与 02c Section 6 完全一致

  回滚策略:
    回滚点: 无（仅创建新文件）
    替代方案: 如果 SKILL.md 路径不明确，同时检查 .agents/skills/ 和 .claude/skills/ 两个位置
    丢弃条件: 无

  超时: 12 分钟
```

### T-03: Index Agent 分割/聚合能力验证

```
Task T-03 规格：
  Skill: general-purpose (sub-agent)
  角色: Index Agent 能力验证员

  输入:
    必读:
      - 当前 SKILL.md Phase 4 INDEX Agent Prompt（完整内容）
      - optimization_prompts/results/02b_skill_design_v2.md Section 5（INDEX Agent 设计）
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.3（文档树结构 Flask 示例）
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.4（Agent 角色边界表）
    参考:
      - 03_feature_cones.json schema（02a Section 4.3）
      - 05_task_manifest.json schema（02a Section 4.5）

  操作范围:
    创建: [.claude_plans/artifacts/skill-index-verification.md]
    修改: []
    禁止修改: [.agents/skills/codebase-explorer/SKILL.md, src/**]

  产出内容要求:
    1. 模拟分析：假设 Flask 代码库的 03_feature_cones.json 和 SNIPPET.md 文件已生成，INDEX Agent 收到 Phase 4 Prompt 后：
       a. 能否正确识别哪些 cone 应该被聚合（batch 任务中的多个小 cone）？
       b. 能否正确处理 split 任务（大 cone 被拆分后的多个 DETAIL 文件）？
       c. 能否生成正确的相对路径链接（../cone_name/DETAIL_xxx.md）？
       d. 能否在 OVERVIEW.md 中正确汇总多个 DETAIL 的信息？
    2. Phase 5 Reorganization Agent 能否基于 Phase 4 输出执行：
       a. Merge 操作：将只有 1 个 DETAIL 的小 cone 合并到相关大 cone
       b. Split 操作：将过大的 DETAIL 按 @unit 标记拆分
       c. Create Group 操作：将相关 cone 归入语义分组目录
    3. 识别 Prompt 中的缺失或歧义：Agent 可能无法正确执行的场景
    4. 提出改进建议（具体的 Prompt 补充或修改）

  验收标准:
    - [ ] Flask 示例的模拟分析涵盖至少 3 种场景（batch 聚合、split 处理、single cone）
    - [ ] 明确指出 INDEX Agent 当前 Prompt 中 >= 2 个可改进点
    - [ ] Phase 5 能力验证覆盖 Move/Merge/Split/Create Group 四种操作
    - [ ] 输出包含"能力矩阵"表格：操作类型 × 当前支持度（完全/部分/缺失）

  回滚策略:
    回滚点: 无（仅创建新文件）
    替代方案: 如果 Flask 示例数据不够，使用文档中的 Flask 24 文件示例数据
    丢弃条件: 无

  超时: 15 分钟
```

### T-04: SKILL.md 全量合并与综合审查

```
Task T-04 规格：
  Skill: general-purpose (sub-agent)
  角色: Skill 架构审查员 + 合并执行者

  输入:
    必读:
      - .claude_plans/artifacts/skill-phase5-design.md（T-01 产出）
      - .claude_plans/artifacts/skill-field-audit.md（T-02 产出）
      - .claude_plans/artifacts/skill-index-verification.md（T-03 产出）
      - 当前 SKILL.md 全文
      - optimization_prompts/results/03_final_progressive_scheme.md（权威规范）

  操作范围:
    创建: []
    修改: [.agents/skills/codebase-explorer/SKILL.md]
    禁止修改: [src/**, optimization_prompts/**] — 原因: 仅修改 SKILL.md

  执行步骤:
    1. 读取 T-01 产出，将 Phase 5 Semantic Reorganization 完整内容插入 SKILL.md
    2. 读取 T-02 产出，按审计报告修正所有 Agent Prompt 中的字段名
    3. 读取 T-03 产出，将改进建议融入 INDEX Agent 和 Phase 5 Prompt
    4. 综合审查合并后的 SKILL.md：
       a. 6 个 Phase 是否完整且逻辑连贯
       b. 所有 Agent Prompt 是否使用权威字段名
       c. Phase 间数据流是否无断裂（Phase N 的输出 = Phase N+1 的输入）
       d. 7 个 MCP 工具是否全部正确记录
       e. doc-manifest.json 在 Phase 4 初始化、Phase 5 迭代的流程是否清晰
    5. 产出最终审查报告（嵌入 SKILL.md 文件末尾注释或单独输出）

  预期日志输出:
    - "[SKILL-MERGE] Phase 5 section inserted — {line_count} lines"
    - "[SKILL-MERGE] Field name fixes applied — {fix_count} corrections"
    - "[SKILL-MERGE] INDEX Agent improvements applied — {improvement_count} changes"
    - "[SKILL-REVIEW] Final review — {issue_count} issues found"

  验收标准:
    - [ ] SKILL.md 包含完整的 Phase 1-6 工作流
    - [ ] Phase 5 包含 Reorganization INDEX Agent Prompt 模板
    - [ ] 所有 Prompt 字段名与 02a JSON Schema 一致（零差异）
    - [ ] doc-manifest.json Schema 在 SKILL.md 中有完整定义
    - [ ] T-03 报告中的改进建议至少 80% 被采纳或有拒绝理由
    - [ ] SKILL.md 总长度 > 800 行（确保内容充实）

  回滚策略:
    回滚点: git stash（合并前 stash 当前 SKILL.md）
    替代方案: 如果合并冲突严重，以 T-01 产出为基础重写 Phase 5，其他 Phase 仅做字段修正
    丢弃条件: 三次尝试后仍无法通过审查

  超时: 20 分钟
```

### T-05: `get_dependency_graph()` 完整实现

```
Task T-05 规格：
  Skill: general-purpose (sub-agent)
  角色: MCP 工具实现者

  输入:
    必读:
      - src/server.py（当前 get_dependency_graph stub，约 line 582-624）
      - optimization_prompts/results/02c_responsibility_v2.md Section 2（Tool 4: get_dependency_graph API 设计）
      - src/doc/mermaid.py（已有 MermaidGenerator，可复用）
      - src/graph/dependency.py（加权图已实现，需调用）
      - src/graph/weighted_graph.py（理解加权图数据结构）
    参考:
      - optimization_prompts/results/02a_code_analysis_v2.md Section 3.1（加权边定义）
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.2（工具迁移表）

  操作范围:
    创建: []
    修改: [src/server.py（仅 get_dependency_graph 函数体）]
    禁止修改: [.agents/skills/**, optimization_prompts/**, src/state/**, src/parser/**]

  实现要求:
    1. 从 .codebase-analysis/02_dag.json 读取 DAG 数据
    2. 支持参数: scope="project"|"cone"|"file", cone_id=str, file_path=str, include_weights=bool
    3. scope="project": 返回完整 DAG 的 Mermaid 图
    4. scope="cone": 返回指定 cone 内部的依赖子图
    5. scope="file": 返回指定文件的 N-hop 邻居子图（默认 hops=1）
    6. include_weights=True 时在 Mermaid 边上标注权重和关系类型
    7. 返回值包含: mermaid_graph(str), nodes(list), edges(list), circular_deps(list)
    8. 利用已有的 MermaidGenerator（src/doc/mermaid.py）和加权图模块

  预期日志输出:
    - "[DEP-GRAPH] Generating dependency graph scope={scope}"
    - "[DEP-GRAPH] Graph generated: {node_count} nodes, {edge_count} edges"

  验收标准:
    - [ ] scope="project" 返回包含所有 DAG 节点的 Mermaid 图
    - [ ] scope="file" 返回指定文件及其 1-hop 邻居的子图
    - [ ] include_weights=True 时边标注包含关系类型（import/call/inherit）
    - [ ] circular_deps 从 02_dag.json 的 SCC 数据中提取
    - [ ] 测试：对 test_repos/flask 运行后返回非空 Mermaid 字符串

  回滚策略:
    回滚点: git stash（修改前保存 server.py）
    替代方案: 如果 MermaidGenerator 不适用，直接拼接 Mermaid 字符串
    丢弃条件: 如果 02_dag.json 结构与预期完全不匹配

  超时: 15 分钟
```

### T-06: `build_task_manifest()` 验证与实现

```
Task T-06 规格：
  Skill: general-purpose (sub-agent)
  角色: 任务装箱算法实现者

  输入:
    必读:
      - src/server.py（line ~245，调用 build_task_manifest 的位置）
      - src/doc/depth_planner.py（检查 build_task_manifest 是否已存在）
      - optimization_prompts/results/02a_code_analysis_v2.md Section 5（FFD 装箱算法伪代码）
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.6（完整流程图末尾）
    参考:
      - 02a Section 4.5（05_task_manifest.json Schema）

  操作范围:
    创建: []
    修改: [src/doc/depth_planner.py]
    禁止修改: [.agents/skills/**, optimization_prompts/**, src/state/**]

  实现要求:
    1. 首先验证 build_task_manifest() 是否已存在且功能完整
    2. 如果缺失或不完整，按 02a Section 5 实现 FFD 装箱算法：
       a. CONTEXT_BUDGET = 100,000 tokens
       b. exclusive_tokens > budget → split 任务（按 DAG 层拆分）
       c. 多个小 cone → batch 任务（贪心装箱）
       d. 单个 cone ≤ budget → single 任务
       e. 最后追加 INDEX Assembly 任务
    3. 输出 05_task_manifest.json 格式的 dict
    4. 同时验证/更新 calculate_feature_cone_depth()：
       - V2 定义：depth = 锥体内 DAG 层数
       - 替换 V1 的三维阈值表（如果仍存在）

  预期日志输出:
    - "[TASK-PACK] Packing {cone_count} cones into tasks, budget={budget}"
    - "[TASK-PACK] Result: {batch_count} batch, {single_count} single, {split_count} split tasks"

  验收标准:
    - [ ] build_task_manifest() 函数存在且可从 server.py 正确 import
    - [ ] 输入 cone_dicts + file_tokens → 输出符合 05_task_manifest.json Schema
    - [ ] split 策略按 DAG 层拆分（非按文件随机拆分）
    - [ ] batch 策略满足 CONTEXT_BUDGET 约束
    - [ ] 测试：输入 Flask 24 文件数据后生成合理的任务分配

  回滚策略:
    回滚点: git stash
    替代方案: 如果 depth_planner.py 结构不适合，在 src/analysis/ 下新建 task_packer.py
    丢弃条件: 无

  超时: 15 分钟
```

### T-07: E2E 集成测试

```
Task T-07 规格：
  Skill: general-purpose (sub-agent)
  角色: E2E 测试工程师

  输入:
    必读:
      - src/server.py（所有 7 个 MCP 工具）
      - tests/test_e2e_pipeline.py（已有测试，需扩展）
      - .agents/skills/codebase-explorer/SKILL.md（Phase 4/5 Agent Prompt 验证）
    参考:
      - optimization_prompts/results/03_final_progressive_scheme.md Section 2.3（Flask 文档树）

  操作范围:
    创建: []
    修改: [tests/test_e2e_pipeline.py]
    禁止修改: [src/**, .agents/skills/**]

  测试要求:
    1. **依赖图测试**（用户要求 #1）:
       - 调用 analyze_codebase(test_repos/flask) 后
       - 调用 get_dependency_graph(scope="project") 返回非空 Mermaid 图
       - Mermaid 图包含 DAG 节点和边
       - 调用 get_dependency_graph(scope="file", file_path="flask/app.py") 返回 app.py 的邻居子图
    2. **功能集合测试**（用户要求 #2）:
       - 调用 get_feature_cones() 返回功能锥体列表
       - 每个 cone 包含 exclusive_files, name, entry_point 字段
       - cone 列表覆盖 Flask 代码库的主要功能区域
       - infrastructure_nodes 包含被多 cone 共享的文件
    3. **Index Agent 协议验证**（用户要求 #3）:
       - 读取 SKILL.md 中 Phase 4 INDEX Agent Prompt
       - 验证 Prompt 中引用的变量（{{feature_cones}}, {{snippet_contents}} 等）与实际 JSON 字段对应
       - 验证 Phase 5 Reorganization Prompt 的 @unit 解析规则与 Phase 3 DETAIL 的 @unit 写入规则一致
       - 验证 doc-manifest.json Schema 在 SKILL.md 中有定义
    4. **任务装箱测试**:
       - analyze_codebase 后 05_task_manifest.json 存在且包含有效任务
       - 任务类型包含 batch/single/split 中至少 2 种

  预期日志输出:
    - "[E2E] Test dependency_graph: {PASS/FAIL}"
    - "[E2E] Test feature_cones: {PASS/FAIL}"
    - "[E2E] Test index_agent_protocol: {PASS/FAIL}"
    - "[E2E] Test task_manifest: {PASS/FAIL}"

  验收标准:
    - [ ] pytest tests/test_e2e_pipeline.py 退出码 0
    - [ ] 依赖图测试：Mermaid 字符串包含 "graph" 或 "flowchart" 关键字
    - [ ] 功能集合测试：get_feature_cones 返回 >= 3 个 cone
    - [ ] Index 协议测试：SKILL.md 中 Phase 4 + Phase 5 的变量注入与 JSON Schema 100% 对应
    - [ ] 任务装箱测试：05_task_manifest.json 包含有效的 tasks 数组

  回滚策略:
    回滚点: 测试文件可随时重写
    替代方案: 如果 Flask test repo 不可用，使用项目自身代码库作为测试目标
    丢弃条件: 无

  超时: 20 分钟
```

---

## Block 4 — Parallel Execution Map（并行执行图）

```
并行组 A（同时启动，最多 3 个）：T-01, T-02, T-03
  依赖：无
  约束：各自写不同的设计文档（skill-phase5-design.md, skill-field-audit.md, skill-index-verification.md），无写入冲突
  最大并行数：3（用户指定"至少 3 个 Agent"）

并行组 B（同时启动，最多 2 个）：T-05, T-06
  依赖：无（与并行组 A 无文件冲突，可同时启动）
  约束：T-05 写 src/server.py 的 get_dependency_graph，T-06 写 src/doc/depth_planner.py，无冲突
  最大并行数：2
  注意：并行组 B 可与并行组 A 同时启动（不同文件，不同职责）

串行步骤（等待并行组 A 全部完成）：T-04
  依赖：T-01 + T-02 + T-03
  原因：需要读取三个设计产出物后合并到 SKILL.md

串行步骤（等待 T-04 + T-05 + T-06 全部完成）：T-07
  依赖：T-04 + T-05 + T-06
  原因：E2E 测试需要 SKILL.md 优化完成 + MCP 工具实现完成
```

**执行时间线**:
```
Time ──────────────────────────────────────────────────►

Phase 1:  [T-01]─────────┐
          [T-02]─────────┤ 并行组 A（Skill 设计）
          [T-03]─────────┘
                          ↓ 等待全部完成
Phase 2:                  [T-04]──────── 合并审查
          [T-05]────────────────────┐ 并行组 B（MCP 实现，与 Phase 1 同时启动）
          [T-06]────────────────────┘
                                     ↓ 等待 T-04 + T-05 + T-06
Phase 3:                             [T-07]──── E2E 测试
```

---

## Block 5 — File Decomposition（文件拆解）

| 文件路径 | 操作 | 归属任务 | 说明 |
|---------|------|---------|------|
| `.claude_plans/artifacts/skill-phase5-design.md` | CREATE | T-01 | Phase 5 完整设计文档 |
| `.claude_plans/artifacts/skill-field-audit.md` | CREATE | T-02 | 字段一致性审计报告 |
| `.claude_plans/artifacts/skill-index-verification.md` | CREATE | T-03 | Index Agent 能力验证报告 |
| `.agents/skills/codebase-explorer/SKILL.md` | MODIFY | T-04 | 合并 T-01/T-02/T-03 产出 |
| `src/server.py` | MODIFY | T-05 | get_dependency_graph 函数体 |
| `src/doc/depth_planner.py` | MODIFY | T-06 | build_task_manifest 函数 |
| `tests/test_e2e_pipeline.py` | MODIFY | T-07 | 扩展 E2E 测试 |

---

## Block 6 — Phase Structure（阶段结构）

### Phase 1: Skill 多维设计（并行，3 Agent）

**入口条件**: optimization_prompts/results/ 目录存在且文档可读
**退出条件**: T-01, T-02, T-03 三个设计文档均已创建且满足各自验收标准

| 任务 | 角色 | 产出 |
|------|------|------|
| T-01 | Phase 5 设计师 | skill-phase5-design.md |
| T-02 | 协议一致性审计员 | skill-field-audit.md |
| T-03 | Index Agent 能力验证员 | skill-index-verification.md |

### Phase 1.5: MCP 工具实现（并行，2 Agent，与 Phase 1 同时启动）

**入口条件**: src/server.py 和 src/doc/depth_planner.py 存在
**退出条件**: T-05 和 T-06 各自通过验收标准

| 任务 | 角色 | 产出 |
|------|------|------|
| T-05 | get_dependency_graph 实现者 | server.py 修改 |
| T-06 | build_task_manifest 实现者 | depth_planner.py 修改 |

### Phase 2: Skill 合并审查（串行，1 Agent）

**入口条件**: Phase 1 的三个设计文档全部完成
**退出条件**: SKILL.md 合并完成且通过综合审查

| 任务 | 角色 | 产出 |
|------|------|------|
| T-04 | Skill 架构审查员 | 修改后的 SKILL.md |

### Phase 3: E2E 集成测试（串行，1 Agent）

**入口条件**: Phase 1.5 和 Phase 2 全部完成
**退出条件**: 所有 E2E 测试通过

| 任务 | 角色 | 产出 |
|------|------|------|
| T-07 | E2E 测试工程师 | tests/test_e2e_pipeline.py |

---

## Block 7 — Context Recovery Protocol

已放置在文件最顶端（见文件开头）。

---

## Block 8 — Validation / Success Criteria（成功标准）

### 必须通过的验证（用户明确要求）

1. **MCP 依赖图**:
   - `get_dependency_graph(scope="project")` 对 Flask 代码库返回包含 DAG 节点和边的 Mermaid 图
   - `get_dependency_graph(scope="file", file_path="flask/app.py")` 返回 app.py 的邻居子图
   - 验证命令: `pytest tests/test_e2e_pipeline.py -k "dependency_graph" -v`

2. **功能集合聚合**:
   - `get_feature_cones()` 返回 >= 3 个语义命名的功能锥体
   - 每个 cone 包含 `exclusive_files`, `name`, `entry_point`
   - infrastructure_nodes 包含被多 cone 共享的文件
   - 验证命令: `pytest tests/test_e2e_pipeline.py -k "feature_cones" -v`

3. **Index Agent 分割/聚合能力**:
   - SKILL.md Phase 4 INDEX Agent Prompt 的变量注入与 JSON Schema 100% 对应
   - SKILL.md Phase 5 Reorganization Agent 可执行 Move/Merge/Split/Create Group
   - @unit 标记写入规则（Phase 3）与解析规则（Phase 5）一致
   - 验证命令: `pytest tests/test_e2e_pipeline.py -k "index_agent_protocol" -v`

4. **SKILL.md 完整性**:
   - 包含完整的 Phase 1-6 工作流
   - 所有 Agent Prompt 字段名与 02a 权威 Schema 一致
   - doc-manifest.json 完整 Schema 已定义
   - 验证命令: 人工审查 + T-04 的综合审查报告

### 全局验证

```bash
# 所有测试通过
pytest tests/test_e2e_pipeline.py -v --tb=short

# SKILL.md 完整性检查（关键字存在性）
grep -c "Phase 5" .agents/skills/codebase-explorer/SKILL.md  # >= 1
grep -c "doc-manifest.json" .agents/skills/codebase-explorer/SKILL.md  # >= 1
grep -c "Reorganization" .agents/skills/codebase-explorer/SKILL.md  # >= 1
grep -c "@unit" .agents/skills/codebase-explorer/SKILL.md  # >= 2
```

---

## 附录：关键参考文档路径

| 文档 | 路径 | 用途 |
|------|------|------|
| 权威最终规范 | `optimization_prompts/results/03_final_progressive_scheme.md` | 所有裁决和决策的最终权威 |
| 代码分析 V2 | `optimization_prompts/results/02a_code_analysis_v2.md` | JSON Schema 权威、算法伪代码 |
| Skill 设计 V2 | `optimization_prompts/results/02b_skill_design_v2.md` | Agent Prompt 模板、Phase 5 设计 |
| MCP 职责 V2 | `optimization_prompts/results/02c_responsibility_v2.md` | 7 个工具 API、state.json Schema |
| 当前架构分析 | `optimization_prompts/results/01_current_architecture.md` | V1 问题诊断（参考） |
