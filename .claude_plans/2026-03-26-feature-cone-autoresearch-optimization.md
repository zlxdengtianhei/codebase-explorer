> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

# Feature Cone AutoResearch 优化

```yaml
Checkpoint:
  phase: 3
  status: complete
  last_completed_task: T-11
  baseline_mean: 83.26
  baseline_file: tests/baseline_scores.json
```

---

## Block 0 — Vision Constraint

```yaml
Vision:
  original_prompt: |
    你要计划好，按照这个 OP skill 中的内容，你作为主编排者，
    所有的具体代码修改都应该让 Subagent 进行，你要给 Subagent 提供足够的 context。
    请你每次不要修改太多，就按照 Auto Research 给出的这些思想来执行。
    一定要完完全全地利用现有的资源，而不是重复造轮子去新建什么东西。
    你要思考现有的这些资源，你到底是否完整地使用了它们，是否真正发挥出了它们的最大用处。
    算法也不应该太过复杂，应该尽量保持简单。
    要从宏观的角度去思考如何优化，而不是纠结于某些细节条件下的具体操作。
    每次迭代都需要删除之前的死代码。
    维持一个文档介绍尝试过的方法。
  hard_constraints:
    - 主编排者绝不自己写代码——所有文件修改通过 Sub-agent 完成
    - 每次迭代一个原子变化，不混合多个改动
    - 每次迭代后删除新产生的死代码
    - 每次迭代更新 optimization_prompts/results/04_feature_cone_optimization_v3.md
    - 充分利用现有资源（scoring_harness、ground_truth、directory_affinity_score、is_reexport_facade）
    - 算法保持简单，宏观思考优化方向
    - 使用 .venv/bin/python（项目需要 Python 3.13）
    - 不要尝试已废弃方向：递归 Louvain 拆分、合并 size cap、BFS-from-roots 回退
  done_from_user_perspective: |
    feature_cone.py 代码干净（无死代码，<500行），
    7维评分 aggregate mean 显著高于基线 76.12，
    每个 repo 无单维度严重退化（>5 分），
    所有改动都有完整记录和可复现的评分数据。
```

---

## Block 1 — Context

### 背景

feature_cone.py 已从 V1 BFS-from-roots 演进到 V3 Louvain 社区检测，但仍有 11 个 V1 死函数（~800 行）。当前 Louvain 实现在 7 维评分上达到 aggregate mean 76.12/100，有明确的提升空间。

### 当前最弱维度分析（从基线数据）

| 维度 | 最弱 Repo | 分数 | 最大可提升 | 根因 |
|------|----------|------|-----------|------|
| D6 DepIntegrity | fastapi | 3.16/15 | +11.84 | Louvain 忽略边权重，强依赖链被分入不同社区 |
| D3 InfraAccuracy | rich | 2.14/15 | +12.86 | _identify_infrastructure 使用 classify_file 但未匹配更多 infra 词根 |
| D2 Distribution | scrapy | 8.06/15 | +6.94 | Gini ~0.46，cone 大小不均 |
| D5 DirCoherence | rich | 9.75/15 | +5.25 | 同目录文件分散到多个 cone |

### 宏观优化策略

不纠结单个条件分支，而是从三个宏观方向出发：
1. **让 Louvain 尊重强依赖** — 在构建无向图时放大强边权重（D6 最大收益）
2. **扩大 infra 识别覆盖面** — 整合未使用的 is_reexport_facade + 扩展词根匹配（D3 最大收益）
3. **用 directory_affinity_score 优化合并** — 小社区合并时倾向同目录（D5 + D2 收益）

### 已有资源清单（必须利用）

| 资源 | 路径 | 当前状态 | 本计划用途 |
|------|------|---------|-----------|
| 7 维评分引擎 | tests/scoring_harness.py | 可用，CLI 支持 --all --compare --json | 每次迭代的机械化验证工具 |
| Ground truth | tests/ground_truth.py | 5 repo 定义，check_ground_truth() | 语义正确性验证 |
| 基线分数 | tests/baseline_scores.json | 2026-03-26 快照，mean=76.12 | 每次迭代的对比基准 |
| classify_file | src/graph/semantic_hints.py | 已用于 _identify_infrastructure | 继续使用 |
| directory_affinity_score | src/graph/semantic_hints.py | **完全未使用** | T-05 整合到 _merge_small_communities |
| is_reexport_facade | src/graph/semantic_hints.py | **Louvain 路径未使用** | T-04 整合到 _identify_infrastructure |
| 优化记录文档 | optimization_prompts/results/04_feature_cone_optimization_v3.md | 已有 V1-V3 记录 | 每次迭代追加 |

### 执行预算

```
执行预算:
  预估总任务数: 8
  预估每任务耗时: 8 分钟
  预估总耗时: 64 分钟
  Context 窗口评估: 可在一个 session 内完成，但可能需要 1 次 /clear
```

---

## Block 2 — Execution Progress

### Phase 1: Foundation（清理 + 基线确认）
- [x] T-01: 删除 feature_cone.py 中 11 个死函数及相关常量/测试/导出 → refactor-cleaner → 产出: 干净的 feature_cone.py (391 行)
- [x] T-02: 刷新基线评分 → general-purpose → 产出: baseline_scores.json (mean: 82.58→83.26)

### Phase 2: AutoResearch 原子迭代
- [x] T-03: 扩大 _identify_infrastructure 的 infra 词根覆盖 + 整合 is_reexport_facade → KEEP (+0.68, mean 83.26)
- [x] T-04: 放大 Louvain 强边权重 → DISCARDED (flask -4.04, rich -3.00, mean 82.27)
- [x] T-05: directory_affinity_score tiebreaker in merge → KEEP (分数不变，tiebreaker 保留)
- [x] T-06: 清理 oh-my-openagent + 死代码扫描 → 完成，无死代码

### Phase 3: Validation
- [x] T-07: 全量评分 + 回归测试 floors 更新 → 736 tests pass, floors: celery≥80, fastapi≥81, flask≥85, rich≥71, scrapy≥82, mean≥80
- [x] T-08: 代码审查 → 0 CRITICAL, 3 HIGH, 5 MEDIUM, 6 LOW
- [x] T-09: 修复 stale node_to_comm bug (HIGH-2) → KEEP (正确性修复，分数不变)
- [x] T-10: FeatureCone list→tuple 真正不可变 (HIGH-1) → KEEP (736 tests pass)
- [x] T-11: middleware/security 加入 infra_categories (HIGH-3) → DISCARDED (FastAPI security/ 误分类，mean 82.67)

---

## Block 3 — Agent Responsibility Matrix

### Task T-01 规格

```
Task T-01: 删除 feature_cone.py 死代码
  Skill: agent: refactor-cleaner
  操作范围:
    修改:
      - src/graph/feature_cone.py（删除 11 个函数 + 11 个常量）
      - src/graph/__init__.py（移除 find_feature_roots, assign_scc_to_cone 导出）
      - tests/test_feature_cone.py（删除 TestAffinityBfs, TestDetectHubNodes, TestRebalanceCones 等死代码测试）
      - tests/test_graph.py（移除对死函数的 import 和测试）
    禁止修改:
      - src/graph/semantic_hints.py — 原因: 不在此任务范围
      - src/server.py — 原因: 不在此任务范围
      - tests/scoring_harness.py — 原因: 评分工具不应被修改
  复用: 无
  预期日志输出:
    - "pytest tests/ -q" 全部通过
  验收标准:
    - [ ] feature_cone.py < 500 行
    - [ ] 以下函数已删除: compute_shared_threshold, find_feature_roots, _detect_hub_nodes, _compute_adaptive_params, _affinity_bfs, _promote_high_fanin_to_infrastructure, _split_mega_cone, _find_package_dir, _merge_orphan_cones, rebalance_cones, assign_scc_to_cone
    - [ ] 以下常量已删除: SHARED_THRESHOLD_MIN, FANIN_INFRASTRUCTURE_RATIO, EDGE_AFFINITY, AFFINITY_DECAY, AFFINITY_CUTOFF, FACADE_PENALTY, CALL_INHERIT_RATIO_THRESHOLD, SPARSE_DENSITY_THRESHOLD, BOOSTED_IMPORT_AFFINITY, SPARSE_AFFINITY_CUTOFF, MAX_MERGED_CONE_SIZE
    - [ ] __init__.py 不再导出 find_feature_roots, assign_scc_to_cone
    - [ ] .venv/bin/python -m pytest tests/ -x -q --tb=short 退出码 0
  回滚策略:
    回滚点: 当前 working copy（git stash）
    替代方案: 分批删除（先函数，后常量，后测试）
    丢弃条件: 删除后测试大面积失败（>10 个）且原因不明
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: feature_cone.py 从 BFS (V1) 演进到 Louvain (V3)，V1 的函数不再被调用
    架构位置: src/graph/feature_cone.py 是 feature cone 提取的核心，被 grouper.py 和 server.py 调用
    参考文件:
      - optimization_prompts/results/04_feature_cone_optimization_v3.md 第五节（死代码列表）
      - src/graph/__init__.py（导出列表）
      - src/graph/feature_cone.py（读取全文，定位死函数行号）
    注意事项:
      - 有些测试直接 import 死函数（如 _affinity_bfs, MAX_MERGED_CONE_SIZE），需要删除这些测试
      - grouper.py 和 server.py 只用 extract_feature_cones 和 FeatureCone，不受影响
      - 保留所有活跃函数: _louvain_communities, _identify_infrastructure, _merge_small_communities, extract_feature_cones, _parent_dir, _separate_testing_files, _generate_cone_name, _semantic_suffix, _rename_cones
```

### Task T-02 规格

```
Task T-02: 刷新基线评分
  Skill: general-purpose（run scoring_harness）
  操作范围:
    修改:
      - tests/baseline_scores.json（用新评分覆盖）
    禁止修改: 所有 src/ 文件 — 原因: 此任务仅运行评分
  复用: tests/scoring_harness.py（--all --json）
  预期日志输出:
    - "[SCORING] Scoring {repo}..." 对每个 repo
    - 最终 JSON 输出包含 aggregate_mean
  验收标准:
    - [ ] .venv/bin/python tests/scoring_harness.py --all --json 成功输出 JSON
    - [ ] 输出保存到 tests/baseline_scores.json
    - [ ] aggregate_mean 与删除死代码前差异 <2 分（死代码删除不应影响算法行为）
  回滚策略:
    回滚点: 旧 baseline_scores.json 的 git stash
    替代方案: 手动运行 scoring_harness 单 repo 逐个验证
    丢弃条件: 评分引擎本身报错无法运行
  超时: 5 分钟
  Sub-agent 所需背景:
    领域知识: scoring_harness.py 是 7 维评分工具，跑在 5 个 test_repos 上
    架构位置: 独立的评测工具，不影响主代码
    参考文件:
      - tests/scoring_harness.py（了解 CLI 参数）
    注意事项:
      - 使用 .venv/bin/python，不是系统 python
      - oh-my-openagent 是 TypeScript，scoring 会跳过（try/except）
      - 保存 JSON 到 tests/baseline_scores.json
```

### Task T-03 规格

```
Task T-03: 扩大 infra 识别 + 整合 is_reexport_facade
  Skill: general-purpose
  操作范围:
    修改:
      - src/graph/feature_cone.py 中的 _identify_infrastructure 函数
    禁止修改:
      - src/graph/semantic_hints.py — 原因: 利用现有函数，不改其实现
      - tests/scoring_harness.py — 原因: 评分工具不应被修改
  复用:
    - semantic_hints.is_reexport_facade（检测 __init__.py 是否为 re-export facade）
    - semantic_hints.classify_file（已在用）
  预期日志输出:
    - pytest 全部通过
    - scoring_harness 输出 D3 分数变化
  验收标准:
    - [ ] _identify_infrastructure 调用 is_reexport_facade
    - [ ] D3 InfraAccuracy aggregate 不下降（对比 T-02 基线）
    - [ ] Rich D3 从 2.14 有所提升
    - [ ] .venv/bin/python -m pytest tests/ -x -q --tb=short 退出码 0
    - [ ] .venv/bin/python tests/scoring_harness.py --all --compare tests/baseline_scores.json 显示 delta
  回滚策略:
    回滚点: T-02 完成后的状态
    替代方案: 仅扩展 infra 词根列表，不整合 is_reexport_facade
    丢弃条件: D3 aggregate 下降 >2 分
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识:
      - _identify_infrastructure 当前用 classify_file 判断 infra（testing/models/api/cli/config/utils/exceptions 类别）
      - is_reexport_facade(path, dag) 检查 __init__.py 是否只做 re-export，这些文件本质是 infra
      - D3 用 known_infra_stems（utils, config, constants 等）评估分类准确性
      - Rich D3=2.14 是因为 errors.py, abc.py, logging.py 未被识别为 infra
    架构位置: _identify_infrastructure 在 extract_feature_cones 主流程中被调用，接收 Louvain 社区输出
    参考文件:
      - src/graph/feature_cone.py（_identify_infrastructure 函数）
      - src/graph/semantic_hints.py（is_reexport_facade, classify_file 的实现）
      - tests/baseline_scores.json（D3 当前分数）
    注意事项:
      - 只修改 _identify_infrastructure 一个函数
      - 不要增加新的外部导入
      - 保持逻辑简单：增加 is_reexport_facade 判断 + 扩展词根匹配（abc, errors, log, logging, compat, base）
      - 不要过度分类——功能模块（api, cli, middleware）不应变成 infra
```

### Task T-04 规格

```
Task T-04: 放大 Louvain 输入图的强边权重
  Skill: general-purpose
  操作范围:
    修改:
      - src/graph/feature_cone.py 中的 _louvain_communities 函数
    禁止修改:
      - src/graph/weighted_graph.py — 原因: 不改变上游权重定义
      - src/graph/semantic_hints.py — 原因: 不在此任务范围
  复用: 现有 dag 的 weight 属性（import=1, call=2, inherit=3）
  预期日志输出:
    - pytest 全部通过
    - scoring_harness D6 分数变化
  验收标准:
    - [ ] _louvain_communities 在构建无向图时对强边（weight≥2）做放大
    - [ ] D6 DepIntegrity aggregate 提升（对比 T-03 后基线）
    - [ ] FastAPI D6 从 3.16 有所提升
    - [ ] 无任何 repo 的 D6 下降 >3 分
    - [ ] .venv/bin/python -m pytest tests/ -x -q --tb=short 退出码 0
  回滚策略:
    回滚点: T-03 完成后的状态
    替代方案: 改用指数放大（weight²）而非线性放大
    丢弃条件: D6 aggregate 下降 OR 其他维度 aggregate 下降 >3 分
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识:
      - _louvain_communities 将 DAG 转为无向图后调用 nx.community.louvain_communities
      - 当前直接用 dag 的 weight 属性（import=1, call=2, inherit=3）
      - D6 检查 weight≥2 的边是否在同一 cone 内
      - 假设：如果 Louvain 输入图中强边权重更突出，社区检测会更倾向于保持强依赖在同一社区
    架构位置: _louvain_communities 是 extract_feature_cones 的第一步
    参考文件:
      - src/graph/feature_cone.py（_louvain_communities 函数）
      - tests/baseline_scores.json（D6 当前分数）
    注意事项:
      - 只修改 _louvain_communities 中构建无向图的逻辑
      - 简单方案：对 weight≥2 的边乘以 2（即 call=4, inherit=6）
      - 保留 resolution=1.0 和 seed=42（Louvain 参数不变）
      - 如果方案 A（线性乘 2）效果不好，替代方案是 weight²（1→1, 2→4, 3→9）
```

### Task T-05 规格

```
Task T-05: 用 directory_affinity_score 优化 _merge_small_communities
  Skill: general-purpose
  操作范围:
    修改:
      - src/graph/feature_cone.py 中的 _merge_small_communities 函数
    禁止修改:
      - src/graph/semantic_hints.py — 原因: 利用现有函数
      - _louvain_communities, _identify_infrastructure — 原因: 一次只改一个函数
  复用: semantic_hints.directory_affinity_score（返回 0.0-1.0 的目录亲和度）
  预期日志输出:
    - pytest 全部通过
    - scoring_harness D5 分数变化
  验收标准:
    - [ ] _merge_small_communities 导入并使用 directory_affinity_score
    - [ ] D5 DirCoherence aggregate 不下降
    - [ ] Rich D5 从 9.75 有所提升
    - [ ] .venv/bin/python -m pytest tests/ -x -q --tb=short 退出码 0
  回滚策略:
    回滚点: T-04 完成后的状态
    替代方案: 仅在边数相等时用 directory_affinity_score 做 tiebreaker（更保守）
    丢弃条件: D5 aggregate 下降 >2 分 OR 其他维度 aggregate 下降 >3 分
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识:
      - _merge_small_communities 将 <min_size 的小社区合并到"边最多的邻居社区"
      - directory_affinity_score(file_a, file_b) 返回 0.0-1.0 表示两个文件路径的目录相似度
      - 当前合并决策纯基于边数，不考虑目录结构
      - 假设：如果在边数相近时倾向合并到同目录社区，D5 会提升
    架构位置: _merge_small_communities 在 _louvain_communities 之后、_identify_infrastructure 之前调用
    参考文件:
      - src/graph/feature_cone.py（_merge_small_communities 函数）
      - src/graph/semantic_hints.py（directory_affinity_score 的签名和实现）
      - tests/baseline_scores.json（D5 当前分数）
    注意事项:
      - 保持简单：在选择合并目标时，综合考虑 (edge_count + dir_affinity_bonus)
      - dir_affinity_bonus 可以是：avg(directory_affinity_score(f1, f2)) * 边数权重
      - 不要过度复杂化——如果 directory_affinity_score 的 API 不适合批量调用，改用更简单的路径前缀匹配
```

### Task T-06 规格

```
Task T-06: 清理 oh-my-openagent + 最终死代码扫描
  Skill: agent: refactor-cleaner
  操作范围:
    修改:
      - 删除 test_repos/oh-my-openagent/（TypeScript 项目，parser 不支持）
      - src/graph/feature_cone.py（如有新死代码则清理）
    禁止修改:
      - tests/scoring_harness.py — 原因: 评分工具不应被修改
  复用: 无
  预期日志输出:
    - "pytest tests/ -q" 全部通过
  验收标准:
    - [ ] test_repos/oh-my-openagent/ 已删除
    - [ ] feature_cone.py 无未使用的函数或常量
    - [ ] .venv/bin/python -m pytest tests/ -x -q --tb=short 退出码 0
  回滚策略:
    回滚点: T-05 完成后的状态
    替代方案: 仅删除 oh-my-openagent，不做死代码扫描
    丢弃条件: 无（纯清理操作）
  超时: 5 分钟
  Sub-agent 所需背景:
    领域知识: oh-my-openagent 是 TypeScript 项目，parser 只能解析 Python，它在 scoring_harness 中会被 try/except 跳过
    架构位置: test_repos/ 存放测试用仓库
    参考文件: 无需读代码，纯文件操作
    注意事项:
      - 用 rm -rf test_repos/oh-my-openagent/ 删除
      - 检查 feature_cone.py 是否有未使用的 import 或函数（通过 grep 确认）
```

### Task T-07 规格

```
Task T-07: 全量评分 + 回归测试
  Skill: general-purpose
  操作范围:
    修改:
      - tests/test_regression_scores.py（更新分数下限）
    禁止修改: 所有 src/ 文件 — 原因: 此任务仅运行评分和写测试
  复用: tests/scoring_harness.py, tests/ground_truth.py
  预期日志输出:
    - scoring_harness 全量输出
    - ground_truth violations 列表
  验收标准:
    - [ ] .venv/bin/python tests/scoring_harness.py --all --verbose --compare tests/baseline_scores.json 输出 delta
    - [ ] aggregate_mean >= 76.12（不低于原基线）
    - [ ] 无任何 repo 的 total 下降 >5 分
    - [ ] test_regression_scores.py 中每个 repo 有分数下限测试（当前分数 -3）
    - [ ] .venv/bin/python -m pytest tests/test_regression_scores.py -v 全部通过
  回滚策略:
    回滚点: T-06 完成后的状态
    替代方案: 放宽下限容差至 -5
    丢弃条件: 无（仅评测和写测试）
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识:
      - scoring_harness 输出 7 维分数 + total/100 + aggregate mean
      - ground_truth 检查语义分类正确性
      - test_regression_scores.py 已存在，需要更新下限值
    架构位置: 测试层，不影响主代码
    参考文件:
      - tests/scoring_harness.py（CLI 用法）
      - tests/test_regression_scores.py（现有测试结构）
      - tests/ground_truth.py（check_ground_truth 函数）
    注意事项:
      - 用 .venv/bin/python 运行
      - 保存最终评分 JSON 到 tests/baseline_scores.json（覆盖）
```

### Task T-08 规格

```
Task T-08: 代码审查
  Skill: agent: python-reviewer
  操作范围:
    修改: 无（只读审查）
  复用: 无
  验收标准:
    - [ ] 零 CRITICAL 问题
    - [ ] HIGH 问题已评估（可接受或修复）
  回滚策略: 无需回滚
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: feature_cone.py 是用 Louvain 社区检测做功能模块分组的算法
    参考文件:
      - src/graph/feature_cone.py
      - src/graph/semantic_hints.py
    注意事项: 关注代码简洁性、无死代码、无 hardcoded magic numbers
```

---

## Block 4 — Parallel Execution Map

```
Phase 1（串行）:
  T-01: 删除死代码
    依赖：无
  T-02: 刷新基线评分
    依赖：T-01（死代码删除可能影响 import 链）
    原因：需要 T-01 的产出作为干净起点

Phase 2（串行，AutoResearch 原子循环）:
  T-03: 扩大 infra 识别
    依赖：T-02（需要基线评分做对比）
    原因：AutoResearch 要求每次一个原子变化 + 机械化对比
  T-04: 放大强边权重
    依赖：T-03（需要 T-03 后的评分做对比）
    原因：同上
  T-05: directory_affinity_score 整合
    依赖：T-04（需要 T-04 后的评分做对比）
    原因：同上
  T-06: 清理 + 死代码扫描
    依赖：T-05（在所有算法改动后进行最终清理）

Phase 3（串行）:
  T-07: 全量评分 + 回归测试
    依赖：T-06（需要所有改动完成）
  T-08: 代码审查
    依赖：T-07（审查最终代码）
```

**为什么全串行**：AutoResearch 方法论的核心是"一次一个原子变化 → 评分 → keep/discard"。每个任务的基线都是上一个任务的产出。并行会破坏因果链。

---

## Block 5 — File Decomposition

| 文件 | 涉及任务 | 操作 |
|------|---------|------|
| src/graph/feature_cone.py | T-01, T-03, T-04, T-05, T-06 | 修改（每次不同函数） |
| src/graph/__init__.py | T-01 | 修改（移除死导出） |
| src/graph/semantic_hints.py | 无 | 只读（被 T-03, T-05 引用但不修改） |
| tests/test_feature_cone.py | T-01 | 修改（删除死测试） |
| tests/test_graph.py | T-01 | 修改（移除死 import） |
| tests/baseline_scores.json | T-02, T-07 | 覆盖写入 |
| tests/test_regression_scores.py | T-07 | 修改（更新下限） |
| test_repos/oh-my-openagent/ | T-06 | 删除 |
| optimization_prompts/results/04_feature_cone_optimization_v3.md | T-03, T-04, T-05 | 追加（每次迭代记录） |

**写入冲突检查**：feature_cone.py 被多个任务修改，但它们是严格串行的（Phase 2 全串行），无冲突。

---

## Block 6 — Phase Structure

### Phase 1: Foundation

**入口条件**：feature_cone.py 存在且有 11 个死函数；795 测试通过
**退出条件**：
- feature_cone.py < 500 行
- 所有测试通过
- baseline_scores.json 已刷新
- aggregate mean 与旧基线差异 <2 分

### Phase 2: AutoResearch Iterations

**入口条件**：Phase 1 完成，baseline_scores.json 已刷新
**退出条件**（每个 task）：
- 评分 aggregate mean >= 前一步的值（KEEP）
- 或评分下降 → git reset 到前一步（DISCARD）→ 跳过此优化方向
- v3 文档已更新

**AutoResearch 循环协议**（每个 T-03/T-04/T-05 执行后）：
```
1. Sub-agent 完成代码修改
2. Sub-agent 运行: .venv/bin/python -m pytest tests/ -x -q --tb=short
3. Sub-agent 运行: .venv/bin/python tests/scoring_harness.py --all --json
4. Orchestrator 对比 JSON 输出与 baseline
5. IF aggregate_mean >= previous AND 无单 repo 下降 >5:
     KEEP → git add + commit "experiment: {描述} — score: {before}→{after}"
     更新 baseline_scores.json
     Sub-agent 更新 v3 文档
   ELIF aggregate_mean >= previous - 2:
     KEEP（微退可接受）→ 同上
   ELSE:
     DISCARD → git checkout -- src/graph/feature_cone.py
     Sub-agent 在 v3 文档记录"已尝试，效果不佳，已丢弃"
6. 进入下一个 task
```

### Phase 3: Validation

**入口条件**：Phase 2 所有 task 完成（无论 keep/discard）
**退出条件**：
- 最终评分报告已生成
- 回归测试已创建且通过
- 代码审查零 CRITICAL

---

## Block 7 — Context Recovery Protocol

（已放置在文件最顶端）

恢复步骤：
1. 阅读本文件（特别是 Block 2 的 checkbox 列表）
2. 阅读 `optimization_prompts/results/04_feature_cone_optimization_v3.md`（了解历史和当前状态）
3. 阅读 `tests/baseline_scores.json`（了解当前评分基线）
4. 从首个 `[ ]` 任务继续执行

---

## Block 8 — Validation / Success Criteria

1. **feature_cone.py < 500 行**（无死代码）— 验证: `wc -l src/graph/feature_cone.py`
2. **aggregate_mean >= 76.12**（不低于原基线）— 验证: `scoring_harness --all --json | jq .aggregate_mean`
3. **无单 repo total 下降 >5 分**— 验证: `scoring_harness --all --compare tests/baseline_scores.json`
4. **所有测试通过**— 验证: `.venv/bin/python -m pytest tests/ -x -q --tb=short`
5. **回归测试存在且通过**— 验证: `.venv/bin/python -m pytest tests/test_regression_scores.py -v`
6. **v3 文档已更新**— 验证: `04_feature_cone_optimization_v3.md` 有新的实验记录
7. **代码审查零 CRITICAL**— 验证: python-reviewer agent 输出

---

## Appendix: AutoResearch Keep/Discard 决策矩阵

| 条件 | 决策 | 操作 |
|------|------|------|
| aggregate ↑ AND 无单 repo ↓>5 AND pytest pass | KEEP | git commit, 更新 baseline |
| aggregate ↓ ≤2 AND 无单 repo ↓>5 AND pytest pass | KEEP（微退可接受） | git commit, 更新 baseline |
| aggregate ↓ >2 OR 单 repo ↓>5 | DISCARD | git checkout 恢复, 记录到 v3 |
| pytest fail | DISCARD | git checkout 恢复, 记录到 v3 |
| Sub-agent 超时 | DISCARD | 记录到 v3, 尝试替代方案 |

## Appendix: Sub-agent 通用 Prompt 模板

```
你需要修改 {文件路径}。

## 愿景约束（Vision Constraint）
{复制 Block 0 的 hard_constraints}

## 背景
{为什么要做这个改动，解决什么问题，关联的评分维度}

## 具体要求
1. {精确的修改描述}
2. {精确的修改描述}

## 参考文件（先阅读再改动）
- {文件路径}: {需要关注的内容}

## 验证
修改完成后运行：
1. .venv/bin/python -m pytest tests/ -x -q --tb=short
2. .venv/bin/python tests/scoring_harness.py --all --json

## 约束
- 不要修改 {列出不应修改的文件}
- 不要新建文件
- 保持代码简单
- 使用 .venv/bin/python
```
