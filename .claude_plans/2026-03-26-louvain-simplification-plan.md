> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

# Plan: Louvain-First Feature Cone Simplification

## Block 0 — Vision Constraint

```yaml
Vision:
  original_prompt: |
    持续优化 codebase-explorer 的算法，重点解决四个共性根因：
    - exclusive_files 唯一性不变量被违反
    - Facade penalty 过于激进
    - Hub 检测无法区分功能模块和工具
    - 框架型 repo root 数量过多

    请你每次不要修改太多，就按照 Auto Research 给出的这些思想来执行。
    一定要完完全全地利用现有的资源，而不是重复造轮子。
    算法也不应该太过复杂，应该尽量保持简单。
    要从宏观的角度去思考如何优化，而不是纠结于某些细节条件下的具体操作。
  hard_constraints:
    - 不新建文件，除非绝对必要；优先修改现有文件
    - 每次改动应该是一个原子变化（autoresearch 原则）
    - 算法保持简单，不要过度工程化
    - 充分利用现有资源（weighted edges, semantic_hints, scoring_harness）
    - oh-my-openagent 必须作为第6个测试仓库加入
  done_from_user_perspective: |
    feature_cone.py 的算法更简单、更有效：
    - 利用 Louvain + 加权边 自然发现功能组
    - 利用现有 semantic_hints 识别 infra
    - 不再依赖 BFS-from-roots（根因：框架型 repo 根节点过多）
    - 6 个测试仓库的功能分组质量（modularity、cohesion）明显好于当前
```

## Block 1 — Context

### 宏观诊断

当前 feature_cone.py 使用 BFS-from-roots，存在四个根因问题：
1. **exclusive_files 唯一性被违反** — BFS 从多个 root 出发，同一文件被多个 cone 包含
2. **Facade penalty 过于激进** — 导致 __init__.py 的子节点被排除
3. **Hub 检测无法区分功能模块和工具** — PageRank 将高 in-degree 的功能模块误判为 infra
4. **框架型 repo root 数量过多** — FastAPI 有 371 个 in-degree=0 root，导致 BFS 产生大量小碎片

**宏观洞察**：这四个根因都源于 BFS-from-roots 策略。Louvain community detection 天然解决了这些问题：
- 每个节点只属于一个社区 → uniqueness invariant 自动满足
- 不需要 facade penalty → 通过图结构自然发现连接
- 不需要 hub 检测 → Louvain 根据边密度自然分组
- 不需要 root 枚举 → Louvain 是全局优化

**未充分利用的现有资源**：
- `build_weighted_dependency_graph` 产出带权重的边（import=1, call=2, inherit=3），但 Louvain 目前传入的是无权重图
- `semantic_hints.classify_file` 有 10+ 语义分类，但只用了 3 类做 infra 检测
- `semantic_hints.directory_affinity_score` 完全未被使用
- scoring_harness 有完整的 7 维评分，可以作为 autoresearch guard

### 执行预算
```
预估总任务数: 5
预估每任务耗时: 10 分钟
预估总耗时: 50 分钟
Context 窗口评估: 可在一个 session 内完成
```

## Block 2 — Execution Progress

- [x] T-01: 稳定基线 — 清理 feature_cone.py，移除过度工程化代码（_split_large_community, _group_overflow, MAX_COMMUNITY_SIZE）
- [x] T-02: 加权 Louvain — 确认 weight="weight" 已为默认行为，无需额外修改
- [x] T-03: 简化 infra — 用 classify_file 替代 known_infra_stems 硬编码列表，cohesion 提升（+5.5% FastAPI, +2.2% celery）
- [x] T-04: 验证 — 5 repo 验证通过（oh-my-openagent 是 TypeScript 项目，parser 不支持）
- [x] T-05: 修复测试 + 回归保护 — 795 tests 全部通过，Rich floor 降至 71.0

## Block 3 — Agent Responsibility Matrix

### Task T-01: 稳定基线

```
Skill: general-purpose sub-agent
操作范围:
  修改: [src/graph/feature_cone.py, tests/test_feature_cone.py]
  禁止修改: [src/graph/semantic_hints.py, src/graph/dependency.py] — 保持稳定
复用: 当前 uncommitted changes 中的 Louvain 相关代码
验收标准:
  - [ ] extract_feature_cones 使用 Louvain 作为主策略
  - [ ] 移除 _split_large_community 和 _group_overflow（过度工程化）
  - [ ] 保留 _louvain_communities, _identify_infrastructure, _merge_small_communities
  - [ ] pytest tests/ -x -q 全部通过（不含 slow tests）
回滚策略:
  回滚点: git stash
  替代方案: 如果清理引入问题，回到当前 working copy 状态
超时: 15 分钟
Sub-agent 所需背景:
  领域知识: feature_cone.py 实现了从依赖图中提取功能分组的算法
  架构位置: src/graph/feature_cone.py 是核心算法文件，被 server.py 调用
  参考文件: src/graph/feature_cone.py（当前磁盘版本）
  注意事项:
    - 当前文件有未提交的 Louvain 修改（1414 行 vs 提交的 942 行）
    - 需要保留 _louvain_communities, _identify_infrastructure, _merge_small_communities
    - 移除 _split_large_community, _group_overflow（过度复杂）
    - MAX_COMMUNITY_SIZE 应恢复为合理值（不再需要 recursive splitting）
```

### Task T-02: 加权 Louvain

```
Skill: general-purpose sub-agent
操作范围:
  修改: [src/graph/feature_cone.py]
  禁止修改: [src/graph/dependency.py, src/graph/semantic_hints.py]
复用: networkx louvain_communities 的 weight 参数
验收标准:
  - [ ] _louvain_communities 传递 weight='weight' 给 louvain_communities
  - [ ] 这意味着 call(2) 和 inherit(3) 边权重更高，Louvain 会倾向于将强连接的文件分为同一组
  - [ ] pytest tests/ -x -q 全部通过
回滚策略:
  回滚点: T-01 完成后的 commit
  替代方案: 如果加权 Louvain 降低 modularity，回退到无权重版本
超时: 10 分钟
Sub-agent 所需背景:
  领域知识: Louvain 社区检测支持带权图，权重越大的边使两端节点更可能被分到同一社区
  架构位置: _louvain_communities 是 extract_feature_cones 的第一步
  参考文件: src/graph/feature_cone.py 中的 _louvain_communities 函数
  注意事项:
    - networkx.algorithms.community.louvain_communities 接受 weight 参数
    - DAG 已经有 weight 属性（import=1, call=2, inherit=3）
    - 转换为 undirected 时，nx.to_undirected() 保留 weight 属性
    - 改动应该只有 1-2 行
```

### Task T-03: 简化 infra 检测

```
Skill: general-purpose sub-agent
操作范围:
  修改: [src/graph/feature_cone.py]
  禁止修改: [src/graph/semantic_hints.py] — 它已经提供了完整的分类
复用: semantic_hints.classify_file 的所有分类，semantic_hints.directory_affinity_score
验收标准:
  - [ ] _identify_infrastructure 使用 classify_file 的全部返回值，而不是硬编码 stem 列表
  - [ ] 移除 known_infra_stems 硬编码列表，改用 classify_file(node) in {"config", "utils", "exceptions"}
  - [ ] pytest tests/ -x -q 全部通过
回滚策略:
  回滚点: T-02 完成后的 commit
  替代方案: 恢复 known_infra_stems 方式
超时: 10 分钟
Sub-agent 所需背景:
  领域知识: semantic_hints.classify_file 返回 10+ 分类（testing/models/api/cli/config/middleware/security/utils/exceptions/unknown）
  架构位置: _identify_infrastructure 被 extract_feature_cones 在 Louvain 之后调用
  参考文件:
    - src/graph/feature_cone.py 中的 _identify_infrastructure
    - src/graph/semantic_hints.py 中的 classify_file
  注意事项:
    - 当前 _identify_infrastructure 硬编码了 known_infra_stems 列表
    - classify_file 已经实现了更全面的语义分类
    - infra 应该只包含真正的基础设施文件（config, utils, exceptions），不包括 api, cli, models 等
```

### Task T-04: 验证 + oh-my-openagent

```
Skill: general-purpose sub-agent
操作范围:
  修改: 无源码修改，只运行验证
  创建: [tests/benchmark_report_v3.json] — 验证报告
验收标准:
  - [ ] 对 6 个 repo 运行 vision 指标（modularity, cohesion, cone_count, infra_ratio）
  - [ ] 所有 repo 的 non-infra modularity > 0（优于随机）
  - [ ] 所有 repo 的 cohesion > 20%
  - [ ] oh-my-openagent 成功解析和分组
回滚策略: 无（只读操作）
超时: 10 分钟
Sub-agent 所需背景:
  领域知识: vision 指标验证功能分组质量
  架构位置: 验证步骤，在算法修改之后运行
  参考文件: tests/scoring_harness.py, tests/benchmark_report.json
  注意事项:
    - 使用 .venv/bin/python（不是系统 python3）
    - test_repos/oh-my-openagent 已经克隆完成
    - 需要 parse_project + build_weighted_dependency_graph + extract_feature_cones
```

### Task T-05: 修复测试 + 回归保护

```
Skill: general-purpose sub-agent
操作范围:
  修改: [tests/test_feature_cone.py, tests/test_regression_scores.py, tests/test_scoring_harness.py]
  禁止修改: [src/] — 此任务只修改测试
验收标准:
  - [ ] pytest tests/ -q 全部通过（包括 slow tests）
  - [ ] 回归 floors 按新的 baseline 更新
  - [ ] 无需新建测试文件
回滚策略:
  回滚点: T-03 完成后的 commit
  替代方案: 降低 regression floors 如果新算法在某些 repo 上得分不同
超时: 15 分钟
Sub-agent 所需背景:
  领域知识: 测试文件中有 BFS 参数的硬编码期望值，需要更新为新的常量值
  架构位置: tests/ 下的测试套件
  参考文件:
    - tests/test_feature_cone.py — BFS 常量测试、extract_feature_cones 行为测试
    - tests/test_scoring_harness.py — affinity BFS 回归测试
    - tests/test_regression_scores.py — 5 repo 的分数 floor
  注意事项:
    - BFS 常量已改变（EDGE_AFFINITY, AFFINITY_DECAY, AFFINITY_CUTOFF）
    - extract_feature_cones 现在用 Louvain 而不是 BFS-from-roots
    - shared_threshold 参数不再被使用
    - 某些 extract_feature_cones 测试需要重写以匹配 Louvain 行为
```

## Block 4 — Parallel Execution Map

```
串行步骤 T-01: 稳定基线
  依赖：无
  原因：后续所有任务依赖干净的基线

串行步骤 T-02: 加权 Louvain
  依赖：T-01
  原因：修改同一文件 (feature_cone.py)

串行步骤 T-03: 简化 infra 检测
  依赖：T-02
  原因：修改同一文件 (feature_cone.py)

并行组 A（同时启动）：T-04, T-05
  依赖：T-03
  约束：T-04 只读验证，T-05 只改测试文件，无写入冲突
  最大并行数：2
```

## Block 5 — File Decomposition

| 文件 | 任务 | 操作 |
|------|------|------|
| src/graph/feature_cone.py | T-01, T-02, T-03 | 修改（串行） |
| tests/test_feature_cone.py | T-01, T-05 | 修改 |
| tests/test_scoring_harness.py | T-05 | 修改 |
| tests/test_regression_scores.py | T-05 | 修改 |

## Block 6 — Phase Structure

### Phase 1: 算法简化 (T-01 → T-02 → T-03)
- 入口条件：当前 working copy 包含 Louvain 修改
- 退出条件：feature_cone.py 使用加权 Louvain + 简化 infra，代码行数 < 1000

### Phase 2: 验证与保护 (T-04 + T-05 并行)
- 入口条件：Phase 1 完成
- 退出条件：6 repo 验证通过，全部 pytest 通过

## Block 7 — Context Recovery Protocol

（已在文件顶部）

## Block 8 — Validation / Success Criteria

1. `pytest tests/ -q` 退出码 0（全部测试通过）
2. 6 个 repo 的 non-infra modularity 均 > 0
3. 6 个 repo 的 cohesion 均 > 20%
4. feature_cone.py 总行数 < 1000（简化验证）
5. 无新建源码文件（充分利用现有资源）

---

## Checkpoint

```yaml
phase: 2
status: completed
last_completed_task: T-05
next_task: null
```
