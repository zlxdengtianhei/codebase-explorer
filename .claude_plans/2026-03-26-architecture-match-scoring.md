> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

# 架构匹配度评分体系 — D8 ClusterARI + D9 LLM-as-Judge

```yaml
Checkpoint:
  phase: 3
  status: done
  last_completed_task: T-07
  baseline_mean: 74.19
  baseline_file: tests/baseline_scores.json
```

---

## Block 0 — Vision Constraint

```yaml
Vision:
  original_prompt: |
    这两个点你都要进行实现。这两个度量方法确实是我希望的度量方法。
    你应该按照之前的计划：
    1. 保持最小的代码修改
    2. 持续进行多次迭代
    3. 每次迭代都要评判这两个新的度量方法，看它们的效果是否有提升
    也就是那个 AutoResearch 的核心思想。

    前置上下文（用户在上一轮的核心关切）：
    "针对这几个代码库，直接通过我的算法去进行架构分类得到的结果，
    跟它原始架构应该的样子是比较匹配的，占比 80% 匹配。是否达到了这个效果呢？"
    "你这个评分机制其实并没有完整地反映出来我之前的愿景"
    "我希望它的整个架构应该和原始架构保持类似"
  hard_constraints:
    - 主编排者绝不自己写代码——所有文件修改通过 Sub-agent 完成
    - 每次迭代一个原子变化，不混合多个改动（AutoResearch 原则）
    - 每次迭代后用所有 9 个维度（D1-D9）评判效果
    - 保持最小代码修改
    - 使用 .venv/bin/python（Python 3.13）
    - 不引入重量级依赖（不加 scikit-learn），ARI 用纯 Python 实现
    - LLM-as-Judge 默认关闭（--llm-judge flag），无 API key 时优雅降级
    - 不破坏现有 D1-D7 的逻辑和回归测试
  done_from_user_perspective: |
    1. 评分体系新增 D8（ClusterARI）和 D9（LLM SemanticCoherence）
    2. D8 通过人工标注的功能分组 vs 算法分组对比，直接回答"架构匹配度"
    3. D9 通过 LLM 判断每个 cone 是否构成有意义的功能单元
    4. 全部 9 维度归一化为百分比（0-100），可用于 AutoResearch 迭代
    5. 5 repo 基线建立，后续每次算法改动都用 9 维度验证
```

---

## Block 1 — Context

### 背景

当前 scoring_harness.py 有 7 个维度（D1-D7，满分 100），但这些维度衡量的是**间接代理指标**（结构不变量、统计属性、文件名启发式），而非用户真正关心的"算法分组是否匹配真实架构"。

用户的核心需求是验证：feature cone 算法产出的功能分组是否与代码库的真实功能架构一致。需要两个新维度：

- **D8 ClusterARI**：将 5 个 repo 的文件人工标注到"正确的功能分组"，然后用 Adjusted Rand Index 对比算法输出 vs 人工标注。ARI=1 表示完美匹配，ARI=0 表示与随机分组无异。
- **D9 LLM SemanticCoherence**：让 LLM（Haiku 4.5）阅读每个 cone 的文件列表，判断"这是否构成一个有意义的功能单元"（0-4 整数打分）。平均分反映 cone 的语义质量。

### 前置工作

- feature_cone.py 已完成 V3 Louvain 优化（391 行，无死代码）
- 7 维评分基线已建立（mean 83.26/100）
- 5 个 test repo：celery, fastapi, flask, rich, scrapy
- 回归测试已更新（736 tests pass）

### 执行预算

```
预估总任务数: 7
预估每任务耗时: 5-15 分钟
预估总耗时: ~60 分钟
Context 窗口评估: 单 session 可完成
```

---

## Block 2 — Execution Progress

### Phase 1: Ground Truth 标注
- [x] T-01: 探索 5 个 repo 的真实功能架构 → Explore agent (parallel) → 5 repo 架构分析完成
- [x] T-02: 编写 CLUSTER_GROUND_TRUTH 标注 → general-purpose → 216 files, 5 repos, 720 tests pass

### Phase 2: 评分基础设施
- [x] T-03: 实现纯 Python ARI + score_clustering_ari() → ARI/NMI 纯 Python, 720 tests pass
- [x] T-04: 实现 LLM-as-Judge + 缓存 → 3-tier graceful degradation, 720 tests pass
- [x] T-05: 集成 D8+D9 到 score_repo，归一化为百分制 → 8 dims active, total=percentage, 720 tests pass

### Phase 3: 基线 + 回归
- [x] T-06: 运行全量 9 维评分 → mean 74.19%, ARI 0.00-0.29, baseline_scores.json 更新
- [x] T-07: 更新回归测试 floor 值 → 736 tests pass, all floors updated to percentage-based

---

## Block 3 — Agent Responsibility Matrix

### Task T-01 规格：探索 5 个 repo 的功能架构

```
Skill: sub-agent type: Explore（并行，5 个 repo 各一个 agent）
操作范围:
  创建: 无
  修改: 无
  禁止修改: 所有源码文件 — 原因: 纯调研任务
复用: 无
预期日志输出: 无（调研任务）
验收标准:
  - [ ] 每个 repo 输出 5-10 个功能分组，每组列出核心文件
  - [ ] 标注哪些文件属于 infrastructure
回滚策略:
  回滚点: 无需回滚（不修改文件）
  替代方案: 手动阅读 README + 目录结构
  丢弃条件: N/A
超时: 5 分钟/repo
Sub-agent 所需背景（零起点思维）:
  - 领域知识: 什么是"功能分组"——按用户用途而非目录结构划分
  - 架构位置: 这些是被分析的目标 repo，不是当前项目
  - 参考文件: 各 repo 的 README.md, 顶层 __init__.py, docs/
  - 注意事项: 关注功能边界，不是代码实现细节。目标是回答"这个库提供了哪些独立功能？"
```

### Task T-02 规格：编写 CLUSTER_GROUND_TRUTH 标注

```
Skill: general-purpose
操作范围:
  创建: 无
  修改: [tests/ground_truth.py]
  禁止修改: [src/*, tests/scoring_harness.py] — 原因: T-02 只负责标注数据
复用: T-01 的架构分析报告
预期日志输出: 无（数据编写）
验收标准:
  - [ ] CLUSTER_GROUND_TRUTH dict 添加到 ground_truth.py
  - [ ] 5 个 repo 各有 20-40 个文件标注
  - [ ] 每个 repo 有 4-10 个功能分组标签
  - [ ] infra 文件标注为 "__infra__" 分组
  - [ ] pytest tests/test_regression_scores.py -x -q --tb=short -k "not slow" 通过
回滚策略:
  回滚点: git stash（T-02 之前的 ground_truth.py）
  替代方案: 从 README + 目录结构自动推断初始标注
  丢弃条件: N/A（标注是必须的）
超时: 10 分钟
Sub-agent 所需背景（零起点思维）:
  - 领域知识: CLUSTER_GROUND_TRUTH 是 file->group_label 映射，用于 ARI 对比
  - 架构位置: ground_truth.py 已有 GROUND_TRUTH（约束规则），新增 CLUSTER_GROUND_TRUTH（分组映射）
  - 参考文件: tests/ground_truth.py（现有格式），T-01 的调研结果
  - 注意事项:
    - 文件路径必须用 posixpath 相对路径，匹配 cone.exclusive_files 的格式
    - 不需要标注所有文件，只标注分组归属明确的文件
    - infra 文件用 "__infra__" 标签
    - 测试文件可以不标注（已有 _separate_testing_files 处理）
```

### Task T-03 规格：实现 ARI + score_clustering_ari()

```
Skill: general-purpose
操作范围:
  创建: 无
  修改: [tests/scoring_harness.py]
  禁止修改: [src/*, tests/ground_truth.py] — 原因: T-03 只负责评分函数
复用: tests/ground_truth.py 中的 CLUSTER_GROUND_TRUTH
预期日志输出:
  - "D8 ClusterARI: {score}/{max}" — 评分结果可见
验收标准:
  - [ ] adjusted_rand_index() 纯 Python 函数（不依赖 sklearn）
  - [ ] score_clustering_ari() 返回 DimensionResult
  - [ ] 无 CLUSTER_GROUND_TRUTH 的 repo → 返回 max_score（不惩罚）
  - [ ] 基本单元测试验证 ARI 计算正确性
  - [ ] pytest tests/ -x -q --tb=short -k "not slow" 通过
回滚策略:
  回滚点: git stash
  替代方案: 用 sklearn.metrics.adjusted_rand_score（需加依赖）
  丢弃条件: N/A
超时: 10 分钟
Sub-agent 所需背景（零起点思维）:
  - 领域知识: ARI 公式 = (RI - E[RI]) / (max(RI) - E[RI])，基于列联表计数和组合数
  - 架构位置: scoring_harness.py 已有 7 个 score_*() 函数，T-03 新增第 8 个
  - 参考文件: tests/scoring_harness.py（现有评分函数的签名模式）
  - 注意事项:
    - ARI 范围 [-1, 1]，但评分要 floor 到 0（max(0, ari) * max_score）
    - 只对 CLUSTER_GROUND_TRUTH 中有标注的文件计算，未标注文件排除
    - infra 文件在算法输出中标记为 "__infra__" 参与对比
    - max_score 建议 15 分（与其他维度对齐）
```

### Task T-04 规格：实现 LLM-as-Judge + 缓存

```
Skill: general-purpose
操作范围:
  创建: [tests/llm_judge_cache.json]（初始为空 {}）
  修改: [tests/scoring_harness.py]
  禁止修改: [src/*, tests/ground_truth.py] — 原因: T-04 只负责 LLM 评分函数
复用: Anthropic Python SDK（如已安装），或 HTTP 请求
预期日志输出:
  - "D9 LLM-Judge: {score}/{max} (cached: {N}/{total})" — 评分结果 + 缓存命中
验收标准:
  - [ ] score_semantic_coherence_llm() 返回 DimensionResult
  - [ ] 无 ANTHROPIC_API_KEY 时 → 返回 neutral score（不惩罚）
  - [ ] 缓存机制：相同 cone 内容 hash → 复用缓存
  - [ ] 0-4 整数打分 + JSON 输出格式
  - [ ] pytest tests/ -x -q --tb=short -k "not slow" 通过
回滚策略:
  回滚点: git stash
  替代方案: 用 heuristic 替代 LLM（文件路径共同前缀比例作为 coherence proxy）
  丢弃条件: Anthropic SDK 不可用且 HTTP 调用过于复杂
超时: 10 分钟
Sub-agent 所需背景（零起点思维）:
  - 领域知识: LLM-as-Judge 模式 — system prompt 定义评分标准，user prompt 传入 cone 数据
  - 架构位置: scoring_harness.py 新增第 9 个评分函数
  - 参考文件: tests/scoring_harness.py（现有评分函数模式）
  - 注意事项:
    - 模型: claude-haiku-4-5-20251001，temperature=0
    - 缓存 key: sha256(cone_name + "\n".join(sorted(exclusive_files)))
    - 缓存存储: tests/llm_judge_cache.json
    - <3 文件的 cone 跳过判断（太小无意义）
    - 评分: avg(score/4) * max_score，max_score 建议 15 分
    - 需要 `import anthropic` — 如果库不存在，优雅降级
```

### Task T-05 规格：集成 D8+D9，归一化百分制

```
Skill: general-purpose
操作范围:
  创建: 无
  修改: [tests/scoring_harness.py]
  禁止修改: [src/*, tests/ground_truth.py]
复用: T-03 和 T-04 产出的函数
预期日志输出:
  - score_repo() 输出包含 9 个维度
验收标准:
  - [ ] score_repo() 调用 D8 和 D9
  - [ ] ScoringResult.total 归一化为百分比（total / max_possible * 100）
  - [ ] CLI --llm-judge flag 控制 D9 启用
  - [ ] CLI 输出显示 9 个维度
  - [ ] pytest tests/ -x -q --tb=short -k "not slow" 通过
回滚策略:
  回滚点: git stash
  替代方案: D9 默认 skip，只集成 D8
  丢弃条件: N/A
超时: 10 分钟
Sub-agent 所需背景（零起点思维）:
  - 领域知识: score_repo() 是 7 维评分的主入口，需要扩展到 9 维
  - 架构位置: scoring_harness.py 的 score_repo() 和 CLI main()
  - 参考文件: tests/scoring_harness.py（score_repo 函数和 CLI 部分）
  - 注意事项:
    - 归一化: total = sum(scores) / sum(max_scores) * 100
    - D9 仅在 enable_llm_judge=True 时调用；False 时不计入 max_possible
    - 更新 scoring_result_to_dict() 以包含新维度
    - 更新 CLI verbose 输出格式
```

### Task T-06 规格：运行全量 9 维评分，建立基线

```
Skill: general-purpose
操作范围:
  创建: 无
  修改: [tests/baseline_scores.json]
  禁止修改: [src/*]
复用: scoring_harness.py --all --json
验收标准:
  - [ ] 5 repo 的 9 维评分结果保存到 baseline_scores.json
  - [ ] D8 ARI 每个 repo 有有效分数（非 skip）
  - [ ] 打印对比：旧 7 维 mean vs 新 9 维 mean
回滚策略:
  回滚点: 旧 baseline_scores.json
  替代方案: N/A
  丢弃条件: N/A
超时: 5 分钟
```

### Task T-07 规格：更新回归测试

```
Skill: general-purpose
操作范围:
  创建: 无
  修改: [tests/test_regression_scores.py]
  禁止修改: [src/*]
验收标准:
  - [ ] SCORE_FLOORS 更新为新 9 维百分制 floor（当前分 - 3）
  - [ ] AGGREGATE_MEAN_FLOOR 更新
  - [ ] 新增 D8 维度 floor 检查
  - [ ] pytest tests/ -x -q --tb=short 全部通过
回滚策略:
  回滚点: git stash
  替代方案: N/A
  丢弃条件: N/A
超时: 10 分钟
```

---

## Block 4 — Parallel Execution Map

```
并行组 A（同时启动，最多 2 个）：T-01a (celery+fastapi+flask), T-01b (rich+scrapy)
  依赖：无
  约束：只读调研，无文件修改
  最大并行数：2

串行步骤：T-02
  依赖：T-01 完成（需要架构分析报告）
  原因：标注需要基于调研结果

串行步骤：T-03
  依赖：T-02 完成（需要 CLUSTER_GROUND_TRUTH）
  原因：ARI 函数需要读取标注数据

串行步骤：T-04
  依赖：T-03 完成（同文件 scoring_harness.py）
  原因：避免写入冲突

串行步骤：T-05
  依赖：T-03 + T-04 完成
  原因：集成需要 D8 和 D9 函数都就绪

串行步骤：T-06
  依赖：T-05 完成
  原因：评分需要完整 pipeline

串行步骤：T-07
  依赖：T-06 完成（需要基线分数）
  原因：floor 值取决于基线
```

---

## Block 5 — File Decomposition

| 文件 | 任务 | 操作 |
|------|------|------|
| tests/ground_truth.py | T-02 | 修改：新增 CLUSTER_GROUND_TRUTH dict |
| tests/scoring_harness.py | T-03, T-04, T-05 | 修改：新增 ARI 函数 + LLM judge + 集成 |
| tests/llm_judge_cache.json | T-04 | 创建：空 JSON |
| tests/baseline_scores.json | T-06 | 修改：更新为 9 维结果 |
| tests/test_regression_scores.py | T-07 | 修改：更新 floor 值 |

**无任务修改 src/ 下的任何文件。**

---

## Block 6 — Phase Structure

### Phase 1: Ground Truth 标注（T-01, T-02）
- 入口条件：5 个 test repo 存在于 test_repos/
- 退出条件：CLUSTER_GROUND_TRUTH 写入 ground_truth.py，5 repo 各 20+ 文件标注

### Phase 2: 评分基础设施（T-03, T-04, T-05）
- 入口条件：Phase 1 完成
- 退出条件：score_repo() 输出 9 维结果，pytest 全通过

### Phase 3: 基线 + 回归（T-06, T-07）
- 入口条件：Phase 2 完成
- 退出条件：baseline_scores.json 更新，回归测试通过

---

## Block 7 — Context Recovery Protocol

（见文件顶部）

恢复所需文件：
1. 本 PLAN 文件 → 进度和任务详情
2. tests/scoring_harness.py → 当前评分管线状态
3. tests/ground_truth.py → 标注数据
4. optimization_prompts/results/04_feature_cone_optimization_v3.md → 优化历史

---

## Block 8 — Validation / Success Criteria

```yaml
Success:
  必须满足:
    - [ ] D8 (ClusterARI) 在 5 个 repo 上产出有效 ARI 分数（非 skip）
    - [ ] D9 (LLM-Judge) 在有 API key 时可运行，无 key 时优雅降级
    - [ ] 总分归一化为百分制（0-100），向后兼容
    - [ ] pytest tests/ -x -q --tb=short 全部通过（含 slow tests）
    - [ ] baseline_scores.json 包含 9 维结果
    - [ ] 回归测试 floor 值已更新
  期望:
    - D8 ARI 在 3+ repo 上 > 0.3（说明算法分组比随机好）
    - D9 LLM avg score > 2.0/4.0（多数 cone 至少"可接受"）
  验证命令:
    - .venv/bin/python -m pytest tests/ -x -q --tb=short
    - .venv/bin/python tests/scoring_harness.py --all --verbose
```
