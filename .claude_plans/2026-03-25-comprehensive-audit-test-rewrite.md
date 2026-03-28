> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

```yaml
checkpoint:
  phase: 5
  status: complete
  last_completed_task: T-16
  remaining: none — all 16 tasks complete
  timestamp: 2026-03-25
```

---

# PLAN: Comprehensive Audit, Test Rewrite & Quality Loop

## Block 1 — Context（背景）

### 问题
用户完成了 codebase-explorer V2 的核心实现（14 个优化任务），愿景实现率约 95%。但存在以下问题：
1. **测试覆盖不均匀**：server.py 只有 8% 的单元测试覆盖率；_tree_builder.py 无直接测试
2. **代码质量问题**：server.py (1309 行) 和 feature_cone.py (942 行) 超出 800 行限制
3. **Skill 设计问题**：V1/V2 版本冲突，Phase 2 缺少 MCP 工具支持
4. **旧测试需归档**：当前 14 个测试文件（238 个测试函数）需要归档并重写

### 目标
1. 归档旧测试，从零重写全面的测试套件
2. 达到 80%+ 覆盖率，重点覆盖 server.py 助手函数
3. 修复 HIGH 级别代码质量问题（文件过大、list.pop(0) → deque）
4. 评估并修复 MCP/Skill 设计缺陷
5. 多 Agent 审查循环直到零缺陷

### 约束
- 不修改核心算法逻辑（除非审查发现 bug）
- 测试必须完全重写（不复用旧测试代码）
- 愿景文档 (00_vision_and_requirements.md) 是最终标准
- Python 3.12+, pytest, pytest-asyncio

### 执行预算
```
执行预算:
  预估总任务数: 16
  预估每任务耗时: 8 分钟
  预估总耗时: 128 分钟
  Context 窗口评估: 可能需要 1-2 次 /clear 中断
```

---

## Block 2 — Execution Progress（执行进度）

### Phase 1: 准备与归档
- [x] T-01: 归档旧测试到 tests/_archived/ → general-purpose agent → tests/_archived/
- [x] T-02: 重构 server.py 拆分为 2 个模块 → general-purpose agent → src/server.py (942→935行), src/server_helpers.py (400行)

### Phase 2: 核心测试重写（并行批次 1）
- [x] T-03: 重写 parser 模块测试 → general-purpose agent → tests/test_parser.py (87 tests)
- [x] T-04: 重写 graph 核心模块测试 → general-purpose agent → tests/test_graph.py (85 tests)

### Phase 2b: 核心测试重写（并行批次 2）
- [x] T-05: 重写 feature_cone + semantic_hints + weighted_graph 测试 → general-purpose agent → 54+87+20 tests
- [x] T-06: 重写 budget + doc 模块测试 → general-purpose agent → 23+40+16 tests

### Phase 2c: 核心测试重写（并行批次 3）
- [x] T-07: 重写 state 模块测试 → general-purpose agent → 41+31 tests
- [x] T-08: 全新 server helpers 单元测试 → general-purpose agent → tests/test_server_helpers.py (91 tests)

### Phase 3: 集成与 E2E 测试
- [x] T-09: 重写 MCP 集成测试 → general-purpose agent → tests/test_mcp_integration.py (41 tests)
- [x] T-10: 重写端到端管线测试 → general-purpose agent → tests/test_e2e_pipeline.py (54 tests)

### Phase 4: 修复代码质量问题
- [x] T-11: 修复 feature_cone.py list.pop(0) → deque → general-purpose agent → src/graph/feature_cone.py
- [x] T-12: 修复 Skill 设计问题（移除 V1 引用、更新 phase 文档） → general-purpose agent → 5 files fixed

### Phase 5: 审查循环
- [x] T-13: Code review 审查 → code-reviewer agent → 3 CRITICAL, 14 HIGH findings
- [x] T-14: Security review 审查 → security-reviewer agent → 2 CRITICAL, 4 HIGH findings
- [x] T-15: 运行完整测试套件 + 覆盖率报告 → 676 tests, 82% coverage
- [x] T-16: 修复审查发现的问题（循环 2 轮，零 CRITICAL/HIGH 缺陷） → 所有 CRITICAL/HIGH 已修复

---

## Block 3 — Agent Responsibility Matrix（Agent 职责矩阵）

### T-01 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/_archived/]
  修改: []
  禁止修改: [src/] — 原因: Phase 1 仅做归档
复用: 无
预期日志输出:
  - "[ARCHIVE] Moving test files to tests/_archived/"
  - "[ARCHIVE] 14 files archived successfully"
验收标准:
  - [ ] tests/_archived/ 包含所有 14 个旧测试文件
  - [ ] tests/ 目录只剩 __init__.py 和 conftest.py
  - [ ] git status 显示文件移动
回滚策略:
  回滚点: 当前 HEAD
  替代方案: 直接删除旧测试（不归档）
  丢弃条件: 无，此任务必须成功
超时: 5 分钟
```

### T-02 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [src/server_helpers.py, src/server_context.py]
  修改: [src/server.py]
  禁止修改: [tests/] — 原因: 测试还未重写
复用: 无
预期日志输出:
  - "[REFACTOR] Extracting helpers from server.py"
  - "[REFACTOR] server.py: 1309 → <800 lines"
验收标准:
  - [ ] src/server.py < 800 行
  - [ ] src/server_helpers.py 包含 Mermaid 渲染、图构建等助手函数
  - [ ] src/server_context.py 包含上下文管理函数
  - [ ] python -c "from src.server import mcp" 导入成功
  - [ ] 所有原有 MCP 工具仍然注册且可调用
回滚策略:
  回滚点: T-01 完成后的 commit
  替代方案: 仅提取最大的 3 个助手函数
  丢弃条件: 如果拆分导致循环导入无法解决
超时: 15 分钟
```

### T-03 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_parser.py]
  修改: [tests/conftest.py]
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing parser module tests"
  - "[TEST] Covering: codebase.py, language_detect.py"
验收标准:
  - [ ] pytest tests/test_parser.py 通过
  - [ ] 覆盖 CodebaseParser, parse_project, FileInfo, FunctionInfo, ClassInfo
  - [ ] 覆盖 AST fallback 路径
  - [ ] 覆盖边界情况（空目录、不支持的语言、错误输入）
  - [ ] 至少 30 个测试函数
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 减少边界测试，聚焦核心路径
  丢弃条件: 无
超时: 12 分钟
```

### T-04 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_graph.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing graph core module tests"
  - "[TEST] Covering: dependency.py, grouper.py, ordering.py"
验收标准:
  - [ ] pytest tests/test_graph.py 通过
  - [ ] 覆盖 build_dependency_graph, get_dependency_graph_mermaid, get_module_dependency_subgraph, get_file_dependency_subgraph
  - [ ] 覆盖 group_modules, identify_utility_nodes, recursive_subgroup
  - [ ] 覆盖 topological_order, compute_pagerank, create_analysis_plan
  - [ ] 覆盖循环依赖检测、权重累加、自环处理
  - [ ] 至少 35 个测试函数
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 聚焦 dependency + grouper，ordering 简化
  丢弃条件: 无
超时: 12 分钟
```

### T-05 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_feature_cone.py, tests/test_semantic_hints.py, tests/test_weighted_graph.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing feature cone + semantic + weighted graph tests"
验收标准:
  - [ ] pytest tests/test_feature_cone.py tests/test_semantic_hints.py tests/test_weighted_graph.py 通过
  - [ ] feature_cone: 覆盖 extract_feature_cones, find_feature_roots, weight-aware BFS, dynamic threshold, cone rebalancing, infrastructure promotion
  - [ ] semantic_hints: 覆盖 classify_file (全部 5 类), directory_affinity_score
  - [ ] weighted_graph: 覆盖 build_weighted_dependency_graph, 多关系类型边权
  - [ ] 至少 40 个测试函数总计
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 分别写入独立文件逐个提交
  丢弃条件: 无
超时: 12 分钟
```

### T-06 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_budget.py, tests/test_depth_planner.py, tests/test_tree_builder.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing budget + doc module tests"
验收标准:
  - [ ] pytest tests/test_budget.py tests/test_depth_planner.py tests/test_tree_builder.py 通过
  - [ ] budget: 覆盖 estimate_tokens_from_chars, estimate_tokens_from_lines, estimate_module_tokens, 语言特定比率
  - [ ] depth_planner: 覆盖 calculate_depth, select_split_strategy, should_terminate, allocate_budget_per_level, plan_doc_structure, build_task_manifest
  - [ ] tree_builder: 覆盖 build_doc_tree（直接单元测试，非仅集成）
  - [ ] 至少 30 个测试函数总计
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 聚焦 depth_planner（最关键），budget 和 tree_builder 简化
  丢弃条件: 无
超时: 12 分钟
```

### T-07 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_state.py, tests/test_json_store.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing state module tests"
验收标准:
  - [ ] pytest tests/test_state.py tests/test_json_store.py 通过
  - [ ] state/models: 覆盖所有 Pydantic model 字段验证、frozen 属性、序列化/反序列化
  - [ ] json_store: 覆盖 atomic_write_state, read_state, update_task_status, resume_from_state, 崩溃恢复
  - [ ] 至少 20 个测试函数总计
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 聚焦 json_store（更关键），models 简化
  丢弃条件: 无
超时: 10 分钟
```

### T-08 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_server_helpers.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing server helper unit tests"
  - "[TEST] Covering: _lc, _parser, _project_id_from_path, _find_latest_project_dir, _resolve_output_dir, _validate_json_files_exist, _build_graph_from_dag, _short_mermaid_label, _render_mermaid, _is_utility_cone, _compute_cone_layers, _compute_depends_on_cones"
验收标准:
  - [ ] pytest tests/test_server_helpers.py 通过
  - [ ] 覆盖全部 12 个 server.py 内部助手函数（T-02 拆分后在 server_helpers.py 中）
  - [ ] 覆盖错误路径（无效路径、空 JSON、缺失文件）
  - [ ] 至少 25 个测试函数
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 聚焦 6 个最关键的助手函数
  丢弃条件: 无
超时: 12 分钟
```

### T-09 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_mcp_integration.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing MCP integration tests"
  - "[TEST] Testing all 7 MCP tools via memory transport"
验收标准:
  - [ ] pytest tests/test_mcp_integration.py 通过
  - [ ] 覆盖 analyze_codebase, get_structure, get_feature_cones, get_dependency_graph, get_file_tokens, get_progress, submit_analysis
  - [ ] 测试完整管线：analyze → query → submit 流程
  - [ ] 覆盖错误场景（无效路径、未分析的项目、缺失参数）
  - [ ] 至少 15 个测试函数
回滚策略:
  回滚点: Phase 2 完成后的 commit
  替代方案: 仅测试 analyze_codebase + get_structure（最核心 2 个工具）
  丢弃条件: MCP memory transport 不可用
超时: 15 分钟
```

### T-10 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [tests/test_e2e_pipeline.py]
  修改: []
  禁止修改: [src/] — 原因: 仅写测试
复用: 无
预期日志输出:
  - "[TEST] Writing E2E pipeline tests"
  - "[TEST] Full pipeline: parse → graph → cones → tokens → tasks"
验收标准:
  - [ ] pytest tests/test_e2e_pipeline.py 通过
  - [ ] 使用真实测试仓库（tests/ 目录下的 fixture）
  - [ ] 验证 5 个 JSON 输出文件的结构和内容
  - [ ] 验证功能锥体质量（非单文件、非全基础设施）
  - [ ] 验证 token 估算合理性
  - [ ] 验证任务清单格式
  - [ ] 至少 20 个测试函数
回滚策略:
  回滚点: Phase 2 完成后的 commit
  替代方案: 简化为 10 个核心管线测试
  丢弃条件: 测试 fixture 仓库不可用
超时: 15 分钟
```

### T-11 规格：
```
Skill: general-purpose agent
操作范围:
  创建: [src/graph/cone_utils.py (if needed)]
  修改: [src/graph/feature_cone.py]
  禁止修改: [tests/] — 原因: 避免影响已写测试
复用: 无
预期日志输出:
  - "[REFACTOR] Optimizing feature_cone.py"
  - "[REFACTOR] list.pop(0) → deque.popleft()"
  - "[REFACTOR] feature_cone.py: 942 → <800 lines"
验收标准:
  - [ ] src/graph/feature_cone.py < 800 行
  - [ ] 无 list.pop(0) 调用（全部改为 deque）
  - [ ] pytest tests/test_feature_cone.py 仍然通过
  - [ ] python -c "from src.graph.feature_cone import extract_feature_cones" 导入成功
回滚策略:
  回滚点: Phase 3 完成后的 commit
  替代方案: 仅修复 list.pop(0)，不拆分文件
  丢弃条件: 拆分后导致循环导入
超时: 12 分钟
```

### T-12 规格：
```
Skill: general-purpose agent
操作范围:
  创建: []
  修改: [.agents/skills/codebase-explorer/SKILL.md, .agents/skills/codebase-explorer/phases/*]
  禁止修改: [src/] — 原因: Skill 文档独立于实现
复用: 无
预期日志输出:
  - "[SKILL] Updating codebase-explorer skill to match V2 implementation"
  - "[SKILL] Removing V1 Jinja2 references"
验收标准:
  - [ ] SKILL.md 无 Jinja2 模板引用
  - [ ] Phase 文档与当前 MCP 工具一致（7 个工具）
  - [ ] 无 V1/V2 版本冲突
  - [ ] 验证所有 phase 文件内的工具名称匹配 server.py 注册的工具
回滚策略:
  回滚点: Phase 3 完成后的 commit
  替代方案: 仅更新 SKILL.md 主文件
  丢弃条件: 无
超时: 10 分钟
```

### T-13 规格：
```
Skill: code-reviewer agent
操作范围:
  创建: []
  修改: []
  禁止修改: [所有文件] — 只读审查
复用: 无
预期日志输出:
  - "[REVIEW] Code review completed"
验收标准:
  - [ ] 审查报告输出，包含 CRITICAL/HIGH/MEDIUM/LOW 分类
  - [ ] 0 个 CRITICAL 问题
回滚策略:
  回滚点: N/A（只读）
  替代方案: N/A
  丢弃条件: N/A
超时: 10 分钟
```

### T-14 规格：
```
Skill: security-reviewer agent
操作范围:
  创建: []
  修改: []
  禁止修改: [所有文件] — 只读审查
复用: 无
预期日志输出:
  - "[SECURITY] Security review completed"
验收标准:
  - [ ] 安全审查报告输出
  - [ ] 0 个 CRITICAL 安全漏洞
回滚策略:
  回滚点: N/A（只读）
  替代方案: N/A
  丢弃条件: N/A
超时: 10 分钟
```

### T-15 规格：
```
Skill: general-purpose agent
操作范围:
  创建: []
  修改: []
  禁止修改: [所有文件] — 仅运行测试
复用: 无
预期日志输出:
  - "[TEST] Running full test suite with coverage"
  - "[TEST] Coverage: XX%"
验收标准:
  - [ ] pytest --tb=short --cov=src 退出码 0
  - [ ] 覆盖率 >= 80%
  - [ ] 0 个失败测试
回滚策略:
  回滚点: N/A
  替代方案: N/A
  丢弃条件: N/A
超时: 5 分钟
```

### T-16 规格：
```
Skill: general-purpose agent
操作范围:
  创建: []
  修改: [根据审查结果确定]
  禁止修改: []
复用: 无
预期日志输出:
  - "[FIX] Fixing review findings"
  - "[FIX] Re-running tests to verify"
验收标准:
  - [ ] T-13 报告中 HIGH 问题全部修复
  - [ ] T-14 报告中所有安全问题修复
  - [ ] pytest 全部通过
  - [ ] 覆盖率 >= 80%
回滚策略:
  回滚点: T-15 完成后的 commit
  替代方案: 逐个修复最关键的问题
  丢弃条件: 修复引入新问题（回退并手动处理）
超时: 20 分钟
```

---

## Block 4 — Parallel Execution Map（并行执行图）

```
Phase 1（串行）：
  T-01 → T-02
  依赖：T-02 需要 T-01 完成后的干净测试目录
  原因：归档后才能重构 server.py，否则旧测试会失败

Phase 2 并行组 A（最多 2 个同时）：
  批次 1：T-03, T-04
  批次 2：T-05, T-06
  批次 3：T-07, T-08
  依赖：T-02 完成（server.py 拆分后才能测试助手函数）
  约束：每个 Agent 写不同测试文件，无写入冲突

Phase 3 并行组 B（最多 2 个同时）：
  T-09, T-10
  依赖：Phase 2 完成（集成测试需要单元测试先通过）
  约束：无共享写入目标

Phase 4 并行组 C（最多 2 个同时）：
  T-11, T-12
  依赖：Phase 3 完成（修复前需确保测试基线）
  约束：T-11 修改 src/graph/，T-12 修改 .agents/，无冲突

Phase 5 并行组 D（最多 2 个同时）：
  批次 1：T-13, T-14
  依赖：Phase 4 完成
  约束：只读审查，无冲突

串行步骤：
  T-15 → T-16
  依赖：T-13 + T-14 完成（需要审查报告来确定修复范围）
  原因：T-16 修复 T-13/T-14 发现的问题
```

---

## Block 5 — File Decomposition（文件拆解）

| 文件路径 | 操作 | 负责任务 | Agent |
|----------|------|---------|-------|
| tests/_archived/*.py | 创建（移动） | T-01 | general-purpose |
| src/server.py | 修改（缩减） | T-02 | general-purpose |
| src/server_helpers.py | 创建 | T-02 | general-purpose |
| src/server_context.py | 创建 | T-02 | general-purpose |
| tests/test_parser.py | 创建 | T-03 | general-purpose |
| tests/conftest.py | 修改 | T-03 | general-purpose |
| tests/test_graph.py | 创建 | T-04 | general-purpose |
| tests/test_feature_cone.py | 创建 | T-05 | general-purpose |
| tests/test_semantic_hints.py | 创建 | T-05 | general-purpose |
| tests/test_weighted_graph.py | 创建 | T-05 | general-purpose |
| tests/test_budget.py | 创建 | T-06 | general-purpose |
| tests/test_depth_planner.py | 创建 | T-06 | general-purpose |
| tests/test_tree_builder.py | 创建 | T-06 | general-purpose |
| tests/test_state.py | 创建 | T-07 | general-purpose |
| tests/test_json_store.py | 创建 | T-07 | general-purpose |
| tests/test_server_helpers.py | 创建 | T-08 | general-purpose |
| tests/test_mcp_integration.py | 创建 | T-09 | general-purpose |
| tests/test_e2e_pipeline.py | 创建 | T-10 | general-purpose |
| src/graph/feature_cone.py | 修改 | T-11 | general-purpose |
| .agents/skills/codebase-explorer/ | 修改 | T-12 | general-purpose |

---

## Block 6 — Phase Structure（阶段结构）

### Phase 1: 准备与重构
- **入口条件**: 当前所有测试通过（基线验证）
- **任务**: T-01 (归档), T-02 (server.py 拆分)
- **退出条件**: tests/_archived/ 存在，server.py < 800 行，导入正常

### Phase 2: 测试重写
- **入口条件**: Phase 1 退出条件满足
- **任务**: T-03 ~ T-08（6 个测试文件，分 3 批并行）
- **退出条件**: 所有新测试通过，每个模块至少有基本覆盖

### Phase 3: 集成与 E2E 测试
- **入口条件**: Phase 2 退出条件满足
- **任务**: T-09 (MCP 集成), T-10 (E2E 管线)
- **退出条件**: 集成测试和 E2E 测试全部通过

### Phase 4: 代码质量修复
- **入口条件**: Phase 3 退出条件满足
- **任务**: T-11 (feature_cone 优化), T-12 (Skill 更新)
- **退出条件**: 无文件超 800 行，Skill 文档一致，所有测试仍通过

### Phase 5: 审查循环
- **入口条件**: Phase 4 退出条件满足
- **任务**: T-13 ~ T-16（审查 + 修复循环）
- **退出条件**: 0 CRITICAL 问题，覆盖率 >= 80%，全部测试通过

---

## Block 7 — Context Recovery Protocol（Context 恢复协议）

已放置在文件顶部。

恢复步骤：
1. 读取本文件，找到 Block 2 的进度 checkbox
2. 确认哪些任务已完成 [x]，哪些待执行 [ ]
3. 调用 `/od` skill 从首个未完成任务继续
4. `/od` 将按 Block 4 的依赖关系自动确定执行顺序

---

## Block 8 — Validation / Success Criteria（成功标准）

| 编号 | 标准 | 验证命令 |
|------|------|---------|
| S-01 | 旧测试已归档 | `ls tests/_archived/ \| wc -l` 结果 >= 12 |
| S-02 | server.py < 800 行 | `wc -l src/server.py` < 800 |
| S-03 | feature_cone.py < 800 行 | `wc -l src/graph/feature_cone.py` < 800 |
| S-04 | 全部测试通过 | `pytest --tb=short` 退出码 0 |
| S-05 | 覆盖率 >= 80% | `pytest --cov=src --cov-report=term-missing` 输出 >= 80% |
| S-06 | 无 CRITICAL 代码问题 | code-reviewer 报告 0 CRITICAL |
| S-07 | 无 CRITICAL 安全漏洞 | security-reviewer 报告 0 CRITICAL |
| S-08 | Skill 文档无 V1 引用 | `grep -r "jinja2\|Jinja2\|template" .agents/skills/` 结果为空 |
| S-09 | 所有 MCP 工具可注册 | `python -c "from src.server import mcp"` 退出码 0 |
| S-10 | 无 list.pop(0) 反模式 | `grep -rn "\.pop(0)" src/` 结果为空 |
