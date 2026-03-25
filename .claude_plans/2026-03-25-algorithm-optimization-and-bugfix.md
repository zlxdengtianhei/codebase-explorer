> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（[x] 已完成，[ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

# Plan: algorithm-optimization-and-bugfix

**Date**: 2026-03-25
**Project**: codebase-explorer `/Users/lexuanzhang/code/codebase-explorer`
**Plan file**: `.claude_plans/2026-03-25-algorithm-optimization-and-bugfix.md`

---

## Context（背景）

### 任务由来

Codebase Explorer V2 的核心算法（Feature Cone 提取）在边界条件下存在严重退化：

- **高散度**（工具库模式）：大量单文件锥体 → Louvain fallback → 随机分区，无语义意义
- **高聚合**（单体应用模式）：一个巨型锥体吞噬所有文件 → 无法区分功能
- **库代码**（无 in-degree=0 节点）：min_deg+1 fallback 选出过多 root → 全部变 infrastructure
- **深链模式**：线性依赖链被整体吸入一个锥体，无法按功能边界拆分

同时，`server.py` 存在一个阻塞性 Bug（`NameError: name 'layers' is not defined`，第 354 行），以及 `get_feature_cones` 工具中 3 个 TODO 未完成。

### 解决策略

1. **先修 Bug**（P0）：修复 server.py 的 `layers` NameError + 补完 `get_feature_cones` 的 TODO
2. **算法优化**（P0-P1）：权重感知 BFS、动态 SHARED_THRESHOLD、锥体再平衡、目录亲和力、命名规律识别、质量评分
3. **Flask 基准测试**（P1）：用 Flask 59 文件代码库做前后对比，量化优化效果
4. **LLM 语义评审**（P2）：将算法结果 + Flask 源码 + 算法逻辑全部输入 LLM，评估分类合理性

### 假设与约束

- Flask 仓库已在 `test_repos/flask`，无需重新克隆
- 所有算法修改必须保持不可变性原则（frozen dataclass）
- 每个 Phase 结束后 `uv run pytest tests/ -x` 必须全部通过
- 不修改 SKILL.md 和 phase 文档（本次聚焦算法层，不涉及 Agent 工作流变更）
- 最大并行数：2

### 执行预算

```
执行预算:
  预估总任务数: 14
  预估每任务耗时: 8 分钟
  预估总耗时: ~112 分钟
  Context 窗口评估: 可能需要 1-2 次 /clear 中断
```

---

## Execution Progress（执行进度）

### Phase 1 — Bug 修复与基础补完
- [x] T-01: 修复 server.py:354 `layers` NameError → `orchestrated-development` → 产出物: 修复后的 `src/server.py` ✅ 2026-03-25
- [x] T-02: 补完 get_feature_cones 三个 TODO（is_utility / layers / depends_on_cones） → `orchestrated-development` → 产出物: 修复后的 `src/server.py` ✅ 2026-03-25
- [x] T-03: 添加 MCP 传输层集成测试 → agent: `tdd-guide` → 产出物: `tests/test_server_mcp.py` ✅ 2026-03-25

### Phase 2 — 核心算法优化
- [ ] T-04: 实现权重感知 BFS（替换无界 BFS） → `orchestrated-development` → 产出物: 修改 `src/graph/feature_cone.py`
- [ ] T-05: 实现动态 SHARED_THRESHOLD → `orchestrated-development` → 产出物: 修改 `src/graph/feature_cone.py`
- [ ] T-06: 实现锥体大小再平衡 pass → `orchestrated-development` → 产出物: 新函数 in `src/graph/feature_cone.py`
- [ ] T-07: 实现目录亲和力合并 + 命名规律识别 → `orchestrated-development` → 产出物: 新文件 `src/graph/semantic_hints.py`
- [ ] T-08: 实现锥体质量评分（confidence_score） → `orchestrated-development` → 产出物: 新函数 in `src/graph/feature_cone.py`

### Phase 3 — Flask 基准测试与前后对比
- [ ] T-09: Flask 基线采集（优化前的算法跑 Flask） → agent: `Explore` → 产出物: `.claude_plans/artifacts/flask_baseline.json`
- [ ] T-10: Flask 优化后采集 + 定量对比报告 → agent: `Explore` → 产出物: `.claude_plans/artifacts/flask_optimized.json` + `flask_comparison.md`

### Phase 4 — LLM 语义评审
- [ ] T-11: LLM 阅读 Flask 全部源码 + 分类结果，评估分组语义合理性 → `deep-research` → 产出物: `.claude_plans/artifacts/flask_llm_review.md`
- [ ] T-12: 根据 LLM 评审反馈调整算法参数/逻辑 → `orchestrated-development` → 产出物: 相关文件修改

### Phase 5 — 验证与收尾
- [ ] T-13: 全量测试 + 覆盖率检查 → agent: `tdd-guide` → 产出物: 测试报告
- [ ] T-14: 代码审查 → agent: `code-reviewer` → 产出物: 审查报告

---

## Agent Responsibility Matrix（Agent 职责矩阵）

| Task ID | 描述 | Skill / Agent | 输入 | 输出产物 |
|---------|------|---------------|------|---------|
| T-01 | 修复 server.py:354 `layers` NameError | `orchestrated-development` | `src/server.py` | 修复后的 `src/server.py` |
| T-02 | 补完 get_feature_cones 三个 TODO | `orchestrated-development` | `src/server.py`, `02_dag.json` schema | 修复后的 `src/server.py` |
| T-03 | MCP 传输层集成测试 | agent: `tdd-guide` | `src/server.py` | `tests/test_server_mcp.py` |
| T-04 | 权重感知 BFS | `orchestrated-development` | `src/graph/feature_cone.py` | 修改后的 `feature_cone.py` + 新测试 |
| T-05 | 动态 SHARED_THRESHOLD | `orchestrated-development` | `src/graph/feature_cone.py` | 修改后的 `feature_cone.py` + 新测试 |
| T-06 | 锥体大小再平衡 | `orchestrated-development` | `src/graph/feature_cone.py` | 新函数 + 新测试 |
| T-07 | 目录亲和力 + 命名识别 | `orchestrated-development` | 算法设计文档 | `src/graph/semantic_hints.py` + 测试 |
| T-08 | 锥体质量评分 | `orchestrated-development` | `src/graph/feature_cone.py` | 新函数 + JSON schema 扩展 |
| T-09 | Flask 基线采集 | agent: `Explore` | `test_repos/flask`, 当前算法代码 | `flask_baseline.json` |
| T-10 | Flask 优化后对比 | agent: `Explore` | `test_repos/flask`, 优化后算法 | `flask_optimized.json` + `flask_comparison.md` |
| T-11 | LLM 语义评审 | `deep-research` | Flask 源码 + 分类结果 + 算法逻辑 | `flask_llm_review.md` |
| T-12 | 评审反馈实施 | `orchestrated-development` | T-11 报告 | 相关代码修改 |
| T-13 | 全量测试 | agent: `tdd-guide` | 所有修改后的文件 | 测试报告 |
| T-14 | 代码审查 | agent: `code-reviewer` | 所有修改后的文件 | 审查报告 |

---

### 实现类任务规格

#### T-01 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/server.py`]
  - 禁止修改: [`src/graph/feature_cone.py`, `src/graph/weighted_graph.py`] — 原因: 属 Phase 2 任务
- **复用**: 无
- **预期日志输出**:
  - `[analyze_codebase] Analysis complete` — E2E 验证 analyze_codebase 不再 crash
  - `[PIPELINE] feature cones: N cones, M layers` — 验证 layers 变量已正确定义
- **验收标准**:
  - [ ] `uv run pytest tests/ -x` 退出码 0
  - [ ] `server.py` 第 354 行不再引用未定义的 `layers` 变量
  - [ ] `grep -n "len(layers)" src/server.py` 返回 0 行
- **回滚策略**:
  - 回滚点: 当前 HEAD (27ff242)
  - 替代方案: 直接删除该 logger.info 行（信息不关键）
  - 丢弃条件: 不适用（必须修复的阻塞性 bug）
- **超时**: 5 分钟

#### T-02 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/server.py`]
  - 禁止修改: [`src/graph/feature_cone.py`] — 原因: 属 Phase 2 任务
- **复用**: `02_dag.json` 中已有的 DAG 数据用于 `layers` 和 `depends_on_cones` 计算
- **预期日志输出**:
  - `[get_feature_cones] Computed layers for cone` — 验证 layers 字段不再为空
- **验收标准**:
  - [ ] `uv run pytest tests/ -x` 退出码 0
  - [ ] `get_feature_cones` 返回的 `is_utility` 字段基于命名/layer 判断，非硬编码 False
  - [ ] `get_feature_cones` 返回的 `layers` 字段非空列表（对多文件锥体）
  - [ ] `get_feature_cones` 返回的 `depends_on_cones` 字段基于 shared_deps 计算
  - [ ] `grep "TODO" src/server.py` 中 get_feature_cones 相关 TODO 数量为 0
- **回滚策略**:
  - 回滚点: T-01 完成后的 commit
  - 替代方案: 仅实现 is_utility 和 depends_on_cones，layers 降级为 "coming soon"
  - 丢弃条件: 不适用
- **超时**: 10 分钟

#### T-03 规格
- **Skill**: agent: `tdd-guide`
- **操作范围**:
  - 创建: [`tests/test_server_mcp.py`]
  - 修改: 无
  - 禁止修改: [`src/server.py`] — 原因: 属 T-01/T-02
- **复用**: 参考 `tests/test_e2e_pipeline.py` 的测试模式
- **预期日志输出**:
  - `test_analyze_codebase_via_mcp PASSED` — 验证 MCP 传输层可用
- **验收标准**:
  - [ ] `tests/test_server_mcp.py` 文件存在
  - [ ] 至少包含 3 个测试：analyze_codebase / get_feature_cones / get_dependency_graph
  - [ ] `uv run pytest tests/test_server_mcp.py -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-02 完成后的 commit
  - 替代方案: 使用 httpx 直接调用 MCP endpoint（如果 FastMCP test client 不可用）
  - 丢弃条件: FastMCP 不支持测试模式且无法 mock
- **超时**: 15 分钟

#### T-04 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/graph/feature_cone.py`]
  - 创建: 可能扩展 `tests/test_feature_cone.py`
  - 禁止修改: [`src/server.py`] — 原因: Phase 1 已完成，接口不变
- **复用**: 已有的 `weighted_graph.py` 中的边权重数据
- **预期日志输出**:
  - `[FEATURE_CONE] BFS affinity cutoff at depth N for root X` — 验证权重衰减生效
  - `[FEATURE_CONE] Trimmed M weakly-connected files from cone X` — 验证弱边被截断
- **验收标准**:
  - [ ] `extract_feature_cones` 函数签名新增可选参数 `min_affinity: float = 0.1`
  - [ ] BFS 使用边权重计算亲和力衰减，weight=1(import) 衰减快，weight=3(inherit) 衰减慢
  - [ ] 深链场景测试：5 节点链通过 import 连接 → 锥体不超过 3 个文件
  - [ ] 高耦合场景测试：call+inherit 连接的文件始终保留在同一锥体
  - [ ] `uv run pytest tests/ -x` 退出码 0
  - [ ] 所有新增数据结构使用 `frozen=True` dataclass
- **回滚策略**:
  - 回滚点: Phase 1 完成后的 commit
  - 替代方案: 改用 BFS 深度限制（max_depth=3）而非权重衰减
  - 丢弃条件: 权重衰减导致 Flask 等真实项目的锥体全部退化为单文件
- **超时**: 15 分钟

#### T-05 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/graph/feature_cone.py`]
  - 创建: 可能扩展 `tests/test_feature_cone.py`
  - 禁止修改: [`src/graph/semantic_hints.py`] — 原因: 属 T-07
- **预期日志输出**:
  - `[FEATURE_CONE] Dynamic shared_threshold=N for M cones` — 验证动态计算
- **验收标准**:
  - [ ] `SHARED_THRESHOLD` 不再是全局常量，改为 `dynamic_shared_threshold(total_cones)` 函数
  - [ ] 3 锥体 → threshold=2；15 锥体 → threshold≥4；50 锥体 → threshold≥8
  - [ ] `uv run pytest tests/ -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-04 完成后的 commit
  - 替代方案: 使用 `max(2, total_cones // 5)` 简化公式
  - 丢弃条件: 不适用（纯数学函数，无外部依赖）
- **超时**: 10 分钟

#### T-06 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/graph/feature_cone.py`]
  - 创建: 可能扩展 `tests/test_feature_cone.py`
- **预期日志输出**:
  - `[FEATURE_CONE] Rebalance: split mega-cone X (N files > 50% total)` — 超大锥体被拆分
  - `[FEATURE_CONE] Rebalance: merged M single-file cones in dir Y` — 同目录小锥体被合并
- **验收标准**:
  - [ ] 新函数 `rebalance_cones()` 存在且被 `extract_feature_cones` 末尾调用
  - [ ] 超大锥体（>50% 文件）被按目录边界或 DAG layer 拆分
  - [ ] 同一目录下的单文件锥体被合并（至少 2 个才合并）
  - [ ] `uv run pytest tests/ -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-05 完成后的 commit
  - 替代方案: 仅实现拆分逻辑，跳过合并（降低复杂度）
  - 丢弃条件: 再平衡导致锥体数量爆炸（>原始的 3 倍）
- **超时**: 15 分钟

#### T-07 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 创建: [`src/graph/semantic_hints.py`, `tests/test_semantic_hints.py`]
  - 修改: [`src/graph/feature_cone.py`] — 调用 semantic_hints
  - 禁止修改: [`src/server.py`] — 原因: 接口不变
- **预期日志输出**:
  - `[SEMANTIC] Classified N/M files via naming patterns` — 命名规律识别生效
  - `[SEMANTIC] Directory affinity merged K orphan cones` — 目录亲和力合并生效
- **验收标准**:
  - [ ] `src/graph/semantic_hints.py` 文件存在，<200 行
  - [ ] `classify_file()` 函数支持至少 5 种语义类别（testing/models/api/cli/config）
  - [ ] `directory_affinity_score()` 函数返回 0.0-1.0 浮点数
  - [ ] `tests/test_semantic_hints.py` 覆盖核心函数
  - [ ] `uv run pytest tests/ -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-06 完成后的 commit
  - 替代方案: 仅实现 directory_affinity，跳过命名规律（更保守）
  - 丢弃条件: 命名规律的误分类率 > 30%（在 Flask 测试中观测）
- **超时**: 15 分钟

#### T-08 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: [`src/graph/feature_cone.py`]
  - 可能修改: [`src/server.py`] — 在 `03_feature_cones.json` 中输出 confidence_score
- **预期日志输出**:
  - `[FEATURE_CONE] Quality scores: min=X, max=Y, mean=Z` — 质量评分摘要
- **验收标准**:
  - [ ] `FeatureCone` dataclass 新增 `confidence_score: float = 0.0` 字段
  - [ ] `cone_quality_score()` 函数基于 3 个维度（目录一致性/内部连通性/命名一致性）
  - [ ] `03_feature_cones.json` 输出中每个 cone 包含 `confidence_score` 字段
  - [ ] `uv run pytest tests/ -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-07 完成后的 commit
  - 替代方案: 仅计算目录一致性（1 个维度），跳过其他 2 个
  - 丢弃条件: 不适用
- **超时**: 10 分钟

#### T-12 规格
- **Skill**: `orchestrated-development`
- **操作范围**:
  - 修改: 根据 T-11 评审结果决定（可能涉及 `feature_cone.py`, `semantic_hints.py` 的参数调优）
  - 禁止修改: 无新约束
- **预期日志输出**: 取决于具体调整内容
- **验收标准**:
  - [ ] T-11 报告中标记为 CRITICAL 的问题全部解决
  - [ ] T-11 报告中标记为 HIGH 的问题至少解决 50%
  - [ ] `uv run pytest tests/ -x` 退出码 0
- **回滚策略**:
  - 回滚点: T-08 完成后的 commit（Phase 2 终点）
  - 替代方案: 将未解决的 HIGH 问题记录为 known limitations
  - 丢弃条件: LLM 评审建议需要重写核心算法（超出本次范围）
- **超时**: 15 分钟

---

## Parallel Execution Map（并行执行图）

```
并行组 A（同时启动，最多 2 个）：T-01, T-02
  依赖：无
  约束：都修改 src/server.py 但不同区域（T-01: 第354行, T-02: get_feature_cones 函数）
  注意：虽然同文件，但修改区域不重叠。若冲突，改为串行 T-01 → T-02
  最大并行数：2

串行步骤（等待并行组 A 完成）：T-03
  依赖：需要 T-01 + T-02 的修复后 server.py
  原因：MCP 集成测试需要 server.py 无 bug 才能运行

--- Phase 1 完成 ---

串行链（T-04 → T-05，顺序执行）：
  T-04: 权重感知 BFS（修改 extract_feature_cones 核心逻辑）
  T-05: 动态 SHARED_THRESHOLD（依赖 T-04 的新 BFS 接口）
  依赖：Phase 1 完成
  原因：T-05 的阈值计算依赖 T-04 产出的锥体数量

串行步骤：T-06（锥体再平衡）
  依赖：T-04 + T-05
  原因：再平衡是 BFS + threshold 之后的后处理 pass

并行组 B（同时启动，最多 2 个）：T-07, T-08
  依赖：T-06 完成
  约束：T-07 创建新文件 semantic_hints.py, T-08 修改 feature_cone.py 不同函数
  最大并行数：2

--- Phase 2 完成 ---

串行步骤：T-09（Flask 基线采集 — 用优化前代码）
  ⚠️ 重要：T-09 必须在 Phase 2 开始前用 git stash 保存当前代码，
  或在 Phase 1 完成后单独采集。实际上，T-09 应该在 Phase 2 之前执行。
  重新安排：T-09 在 Phase 1 完成后、Phase 2 开始前执行（串行）
  依赖：Phase 1 完成
  原因：基线必须在算法优化前采集

串行步骤：T-10（Flask 优化后采集 + 对比）
  依赖：Phase 2 完成（T-04~T-08 全部完成）
  原因：需要完整的优化后算法

--- Phase 3 完成 ---

串行步骤：T-11（LLM 语义评审）
  依赖：T-10 完成（需要分类结果 + 对比报告）
  原因：LLM 需要完整的输入数据

串行步骤：T-12（评审反馈实施）
  依赖：T-11 完成
  原因：需要评审报告作为输入

--- Phase 4 完成 ---

并行组 C（同时启动，最多 2 个）：T-13, T-14
  依赖：T-12 完成
  约束：T-13 运行测试（只读），T-14 审查代码（只读），无写入冲突
  最大并行数：2
```

**修正后的执行序列**：
```
Phase 1:  [T-01 ∥ T-02] → T-03
Baseline: T-09 (Flask 基线采集)
Phase 2:  T-04 → T-05 → T-06 → [T-07 ∥ T-08]
Phase 3:  T-10 (Flask 优化后对比)
Phase 4:  T-11 → T-12
Phase 5:  [T-13 ∥ T-14]
```

---

## File Decomposition（文件拆解）

| 文件路径 | 操作 | 所属任务 | 负责 Agent |
|---------|------|---------|-----------|
| `src/server.py` | MODIFY (line 354 fix) | T-01 | orchestrated-development |
| `src/server.py` | MODIFY (get_feature_cones TODOs) | T-02 | orchestrated-development |
| `tests/test_server_mcp.py` | CREATE | T-03 | tdd-guide |
| `src/graph/feature_cone.py` | MODIFY (weight-aware BFS) | T-04 | orchestrated-development |
| `src/graph/feature_cone.py` | MODIFY (dynamic threshold) | T-05 | orchestrated-development |
| `src/graph/feature_cone.py` | MODIFY (rebalance pass) | T-06 | orchestrated-development |
| `src/graph/semantic_hints.py` | CREATE | T-07 | orchestrated-development |
| `tests/test_semantic_hints.py` | CREATE | T-07 | orchestrated-development |
| `src/graph/feature_cone.py` | MODIFY (quality score) | T-08 | orchestrated-development |
| `src/server.py` | MODIFY (output confidence_score) | T-08 | orchestrated-development |
| `.claude_plans/artifacts/flask_baseline.json` | CREATE | T-09 | Explore |
| `.claude_plans/artifacts/flask_optimized.json` | CREATE | T-10 | Explore |
| `.claude_plans/artifacts/flask_comparison.md` | CREATE | T-10 | Explore |
| `.claude_plans/artifacts/flask_llm_review.md` | CREATE | T-11 | deep-research |
| `tests/test_feature_cone.py` | MODIFY (new tests) | T-04/T-05/T-06/T-08 | orchestrated-development |

**受保护文件（不得修改）：**
- `.agents/skills/codebase-explorer/SKILL.md` — 原因: 本次不涉及 Skill 工作流变更
- `.agents/skills/codebase-explorer/phases/*.md` — 原因: Phase 文档不在本次范围
- `src/graph/weighted_graph.py` — 原因: 加权图构建逻辑已稳定，无需修改
- `src/budget/estimator.py` — 原因: Token 估算逻辑已稳定
- `src/doc/depth_planner.py` — 原因: 深度规划逻辑不在本次范围

---

## Phase Structure（阶段结构）

### Phase 1 — Bug 修复与基础补完
**入口条件**: 计划已获用户确认
**任务**: T-01, T-02（并行），然后 T-03（串行）
**退出条件**: `uv run pytest tests/ -x` 退出码 0 且 `grep "TODO" src/server.py | grep -c "get_feature_cones"` 返回 0

### Baseline — Flask 基线采集
**入口条件**: Phase 1 完成
**任务**: T-09（串行，在算法优化前执行）
**退出条件**: `.claude_plans/artifacts/flask_baseline.json` 存在且包含 cone_count、file_coverage 等字段

### Phase 2 — 核心算法优化
**入口条件**: Phase 1 完成 + T-09 基线已采集
**任务**: T-04 → T-05 → T-06 → [T-07 ∥ T-08]
**退出条件**: `uv run pytest tests/ -x` 退出码 0 且 `feature_cone.py` 包含 `rebalance_cones`、`dynamic_shared_threshold`、`cone_quality_score` 函数

### Phase 3 — Flask 优化后对比
**入口条件**: Phase 2 完成
**任务**: T-10
**退出条件**: `.claude_plans/artifacts/flask_comparison.md` 存在且包含前后对比表格

### Phase 4 — LLM 语义评审与反馈实施
**入口条件**: Phase 3 完成
**任务**: T-11 → T-12
**退出条件**: `.claude_plans/artifacts/flask_llm_review.md` 存在且 T-12 的修改通过测试

### Phase 5 — 验证与收尾
**入口条件**: Phase 4 完成
**任务**: [T-13 ∥ T-14]
**退出条件**: 下方成功标准区块中的全部条件满足

---

## Checkpoint（检查点）

```yaml
phase: 1
current_task: T-09
status: in_progress
last_updated: 2026-03-25T10:30:00Z
completed: [T-01, T-02, T-03]
pending: [T-09, T-04, T-05, T-06, T-07, T-08, T-10, T-11, T-12, T-13, T-14]
blocked: []
fix_loop_count: 0
current_fix_target: null
escalated: []
```

---

## Experiment Log（实验日志）

| Task | Attempt | Commit | 方案 | 关键指标 | Status | 描述 |
|------|---------|--------|------|---------|--------|------|
| T-01 | 1 | — | Replace len(layers) with total_layers | tests: 180/180 pass | keep | Fixed NameError at line 354 |
| T-02 | 1 | — | Added _is_utility_cone, _compute_cone_layers, _compute_depends_on_cones | tests: 180/180 pass | keep | Implemented 3 TODOs in get_feature_cones |
| T-03 | 1 | — | 8 MCP integration tests via memory transport | tests: 188/188 pass | keep | Created test_server_mcp.py with 8 tests covering all 7 MCP tools |

---

## Context Recovery Protocol（Context 恢复协议）

> **如果在 Context 压缩后读到此内容**：
> 1. 查看"执行进度"区块，确认当前进度（[x] 已完成，[ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

## Validation / Success Criteria（成功标准）

满足以下**全部**条件时，任务才算完成：

- [ ] `uv run pytest tests/ -x` 退出码 0，且测试数量 ≥ 190（当前 180 + 新增测试）
- [ ] `server.py` 中无 `NameError`：`grep -c "len(layers)" src/server.py` 返回 0
- [ ] `server.py` 中 get_feature_cones 相关 TODO 数量为 0
- [ ] `feature_cone.py` 包含 `dynamic_shared_threshold`、`rebalance_cones`、`cone_quality_score` 三个函数
- [ ] `src/graph/semantic_hints.py` 存在且包含 `classify_file` 和 `directory_affinity_score` 函数
- [ ] `tests/test_server_mcp.py` 存在且至少 3 个测试通过
- [ ] `tests/test_semantic_hints.py` 存在且通过
- [ ] `.claude_plans/artifacts/flask_baseline.json` 存在
- [ ] `.claude_plans/artifacts/flask_optimized.json` 存在
- [ ] `.claude_plans/artifacts/flask_comparison.md` 存在且包含定量对比（cone 数量/大小分布/单文件比例）
- [ ] `.claude_plans/artifacts/flask_llm_review.md` 存在且包含 LLM 对分类合理性的评估
- [ ] 优化后 Flask 的单文件锥体比例 < 60%（当前预计接近 90%+）
- [ ] 优化后 Flask 的最大锥体文件数 < 总文件数的 40%
- [ ] 所有新增数据结构使用 `frozen=True` dataclass（不可变性原则）
- [ ] 代码审查报告中无 CRITICAL 级别问题
- [ ] 执行进度中的所有任务已标记为 [x]
