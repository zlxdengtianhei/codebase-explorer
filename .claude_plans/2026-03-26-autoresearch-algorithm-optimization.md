> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

# PLAN: Autoresearch-Style Algorithm Optimization (Round 3)

```yaml
checkpoint:
  phase: 3
  status: completed
  last_completed_task: T-12
  timestamp: 2026-03-26T00:30:00Z
  notes: |
    ALL 12 TASKS COMPLETE.
    Phase 2: T-05 KEPT (+1.2), T-06 KEPT (+0.6), T-07 DISCARDED, T-08 DISCARDED.
    Final mean: 77.9 (baseline 76.1, +1.8). All 795 tests pass.
```

---

## Block 0 — Vision Constraint

```yaml
Vision:
  original_prompt: |
    四项目评估结果汇总（Rich:38, FastAPI:57, Scrapy:47, Celery:52）发现四个共性根因：
    1. exclusive_files 唯一性不变量被违反 — 同一文件出现在多个 cone 的 exclusive_files
    2. Facade penalty 过于激进 — FastAPI __init__.py BFS 被完全阻断，导致 mega-cone
    3. Hub 检测无法区分"高引用的功能模块"和"高引用的工具" — Celery beat/canvas/result 被误标为 infra
    4. 框架型 repo root 数量过多 — Scrapy 72 个 root 导致碎片化

    用户要求：参考 Karpathy autoresearch（Modify→Verify→Keep/Discard→Repeat）思想，
    按照之前两轮优化的积累，持续进行算法优化。测试加入 oh-my-openagent 仓库。
  hard_constraints:
    - 不可破坏现有通过的 244+ 测试
    - 每次算法变更必须有机械化评分验证（autoresearch 核心原则）
    - 不可修改 MCP server 接口签名（已有消费者）
    - 保持代码不可变风格（frozen dataclass，不 mutate）
    - 文件 <800 行，函数 <50 行
  done_from_user_perspective: |
    所有 5 个测试仓库（Rich、FastAPI、Scrapy、Celery、oh-my-openagent）的算法产出质量
    显著提升，四个共性根因被解决，且每次变更有机械化评分验证。综合评分均值 ≥ 80（当前约 48.5）。
    评分基础设施是高质量的、可复用的：7 维度评分 + 每仓库 ground truth + 诊断报告 + 回归检测。
```

---

## Block 1 — Context

### 背景

这是 codebase-explorer 的第三轮算法优化。前两轮已完成：
- **Round 1** (Mar 23-24): SKILL.md 重设计 + 7 个 MCP 工具实现
- **Round 2** (Mar 25): Weight-aware BFS、dynamic shared threshold、cone rebalancing、semantic hints（14 任务）

本轮引入 **Karpathy autoresearch** 方法论核心思想：
- **机械化评分**：替代人工判断，用可重复的评分函数量化改进
- **小表面积变更**：每轮只改一个算法组件
- **Keep/Discard 决策**：评分提升则 commit，否则 git reset
- **自主迭代**：改完测完自动决策，无需人工干预

### 四个根因（来自四仓库评估）

| # | 根因 | 影响仓库 | 严重度 |
|---|------|---------|--------|
| 1 | exclusive_files 重复归属 | Rich(18个), Scrapy(12个) | CRITICAL |
| 2 | Facade penalty 阻断 root 首跳 BFS | FastAPI(__init__.py) | HIGH |
| 3 | Hub 检测不区分功能模块/工具 | Celery(beat/canvas/result) | HIGH |
| 4 | 框架型 repo >20 roots 碎片化 | Scrapy(72 roots) | MEDIUM |

### 执行预算

```
预估总任务数: 12
预估每任务耗时: 15 分钟
预估总耗时: 180 分钟
Context 窗口评估: 可能需要 /clear 一次（Phase 1 结束时）
```

---

## Block 2 — Execution Progress

### Phase 1: 评分基础设施（重点投入）
- [x] T-01: 克隆测试仓库（oh-my-openagent 为 TS 项目，改用 flask） → Bash → test_repos/flask/
- [x] T-02: 构建 7 维度评分引擎 scoring_harness.py → /od → tests/scoring_harness.py
- [x] T-03: 构建 per-repo ground truth + 诊断报告器 → /od → tests/ground_truth.py + tests/diagnostic_reporter.py
- [x] T-04: 采集 5 仓库基线分数 + 生成诊断基线报告 → /od → tests/baseline_scores.json (mean=76.1)

### Phase 2: Autoresearch 修复循环
- [x] T-05: 修复 exclusive_files 唯一归属 → KEPT (+1.2) → promote contested to infra
- [x] T-06: 修复 facade penalty 首跳保护 → KEPT (+0.6) → depth tracking, skip penalty at depth=0
- [x] T-07: 修复 hub 检测增加 out-degree 区分 → DISCARDED (Celery D3 unchanged, Flask -1.3)
- [x] T-08: 修复框架型 repo directory-first 聚合 → DISCARDED (Rich -3.6)

### Phase 3: 验证与回归保护
- [x] T-09: 全量跨仓库基准测试 + 回归报告 → tests/benchmark_report.json + tests/benchmark_diagnostic.md (mean=77.9, +1.8)
- [x] T-10: 编写/更新单元测试（含评分工具测试） → tests/test_scoring_harness.py (47 tests)
- [x] T-11: 回归保护 pytest marker → tests/test_regression_scores.py (19 tests, @pytest.mark.slow)
- [x] T-12: 代码审查 + 最终验证 → 795 tests pass, no security issues, no CRITICAL issues

---

## Block 3 — Agent Responsibility Matrix

### T-01: 克隆 oh-my-openagent 测试仓库

```
Task T-01 规格：
  Skill: Bash（git clone）
  操作范围:
    创建: [test_repos/oh-my-openagent/]
    修改: []
    禁止修改: [src/*, tests/*] — 原因: 纯 setup 任务
  复用: 无
  预期日志输出:
    - "Cloning into 'oh-my-openagent'..."
    - "done."
  验收标准:
    - [ ] test_repos/oh-my-openagent/ 目录存在且包含 Python 源码
    - [ ] git status 显示为 untracked 目录
  回滚策略:
    回滚点: 当前 HEAD
    替代方案: 手动下载 ZIP 解压
    丢弃条件: 仓库不存在或无 Python 代码
  超时: 2 分钟
  Sub-agent 所需背景:
    领域知识: git clone 操作
    架构位置: test_repos/ 目录存放所有基准测试仓库
    参考文件: 无
    注意事项: 使用 --depth=1 减少克隆时间
```

### T-02: 构建 7 维度评分引擎（核心基础设施）

```
Task T-02 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/scoring_harness.py]
    修改: []
    禁止修改: [src/graph/feature_cone.py, src/server.py] — 原因: 评分工具不改算法
  复用: 无
  预期日志输出:
    - "[SCORING] Harness initialized for {repo_name}"
    - "[SCORING] D1-Uniqueness: {score}/15"
    - "[SCORING] D2-Distribution: {score}/15"
    - "[SCORING] D3-InfraAccuracy: {score}/15"
    - "[SCORING] D4-Coverage: {score}/10"
    - "[SCORING] D5-DirCoherence: {score}/15"
    - "[SCORING] D6-DepIntegrity: {score}/15"
    - "[SCORING] D7-NamingQuality: {score}/15"
    - "[SCORING] Total: {total}/100"
  验收标准:
    - [ ] python tests/scoring_harness.py --repo test_repos/rich 退出码 0 并输出 JSON
    - [ ] 评分包含 7 个维度 + 总分 0-100
    - [ ] python tests/scoring_harness.py --all 对所有 test_repos/* 子目录批量评分
    - [ ] 输出可序列化为 JSON（包含 per-dimension breakdown）
    - [ ] --compare baseline.json 模式输出 before/after delta
    - [ ] pytest tests/test_scoring_harness.py 通过（≥12 个测试）
  回滚策略:
    回滚点: T-01 完成后
    替代方案: 如果 7 维度过于复杂，先实现 4 核心维度（D1-D4），后续 T-03 补充剩余
    丢弃条件: 无法 import feature_cone 模块
  超时: 20 分钟
  Sub-agent 所需背景:
    领域知识: |
      Karpathy autoresearch 核心原则：需要一个"机械化评分函数"替代人工判断。
      这是整个优化流程的基石——评分质量决定了后续所有 Keep/Discard 决策的准确性。

      **7 维度评分设计（总分 100）：**

      D1. Uniqueness (15分): exclusive_files 跨 cone 无重复
         score = 15 * (1 - violation_count / total_exclusive_files)
         violation = 同一文件出现在 2+ cone 的 exclusive_files 中

      D2. Distribution (15分): Cone 大小分布均匀度
         base = 15 * (1 - gini(cone_sizes))
         penalty: mega-cone (>50% files) 扣 10 分
         penalty: >60% single-file cones 扣 5 分
         floor: 0

      D3. InfraAccuracy (15分): 基础设施分类正确率
         对每个文件用 semantic_hints.classify_file() 判断期望分类
         known_infra_patterns = {"utils", "config", "exceptions", "compat", "constants"}
         score = 15 * correctly_classified / total_known_patterns
         incorrectly_classified = 应为 infra 但在 cone 中 + 不应为 infra 但在 infra 中

      D4. Coverage (10分): 文件覆盖完整性
         covered = 在某个 cone.exclusive_files 或 infrastructure_nodes 中的文件数
         score = 10 * covered / total_non_test_files
         orphan 文件（不在任何 cone 也不在 infra）每个扣 0.5 分

      D5. DirectoryCoherence (15分): 同目录文件倾向同 cone
         对每个目录，计算其文件被分到多少个不同 cone
         coherence = 1 - (avg_cones_per_dir - 1) / max_possible_spread
         score = 15 * coherence
         完美 = 同目录文件全在同一 cone（coherence=1）

      D6. DependencyIntegrity (15分): 强依赖链不被拆分
         对每对 (A→B) 强依赖（call + inherit 边），检查 A 和 B 是否在同一 cone
         score = 15 * same_cone_pairs / total_strong_dep_pairs
         只计算 weight≥2 的边（call 和 inherit），忽略纯 import

      D7. NamingQuality (15分): Cone 命名质量
         - 无重复名称: 5分（有重复则 0）
         - 非 generic 名称（不含 "misc", "other", "group"）: 5分
         - 名称与内容语义匹配（名称中的关键词出现在文件路径中）: 5分

      **CLI 接口设计：**
      ```
      # 单仓库评分
      python tests/scoring_harness.py --repo test_repos/rich

      # 批量评分所有仓库
      python tests/scoring_harness.py --all

      # 与基线对比
      python tests/scoring_harness.py --all --compare tests/baseline_scores.json

      # JSON 输出（供程序消费）
      python tests/scoring_harness.py --repo test_repos/rich --json

      # 详细模式（显示每维度的扣分细节）
      python tests/scoring_harness.py --repo test_repos/rich --verbose
      ```

      **输出 JSON Schema：**
      ```json
      {
        "repo": "rich",
        "timestamp": "2026-03-26T12:00:00Z",
        "dimensions": {
          "uniqueness": {"score": 14.2, "max": 15, "details": {"violations": 1, "total": 85}},
          "distribution": {"score": 12.0, "max": 15, "details": {"gini": 0.2, "mega_cones": 0}},
          "infra_accuracy": {"score": 13.5, "max": 15, "details": {"correct": 18, "total": 20}},
          "coverage": {"score": 9.5, "max": 10, "details": {"covered": 95, "total": 100}},
          "dir_coherence": {"score": 11.0, "max": 15, "details": {"avg_spread": 1.3}},
          "dep_integrity": {"score": 13.0, "max": 15, "details": {"preserved": 42, "total": 48}},
          "naming_quality": {"score": 12.0, "max": 15, "details": {"duplicates": 0, "generic": 1}}
        },
        "total": 85.2,
        "cone_count": 8,
        "infra_count": 12,
        "file_count": 100
      }
      ```

    架构位置: tests/ 目录下的独立评分工具，import src.graph.feature_cone 和 src.graph.grouper
    参考文件:
      - src/graph/feature_cone.py — FeatureCone dataclass（exclusive_files, shared_deps, entry_point, name）
      - src/graph/grouper.py — extract_feature_cones() 调用入口，返回 ConeResult
      - src/graph/dependency.py — build_weighted_dependency_graph() 构建加权图
      - src/graph/semantic_hints.py — classify_file() 语义分类
      - src/parser/codebase.py — CodebaseParser.parse() 解析代码
    注意事项: |
      - 评分函数必须是纯函数（给定相同输入，输出相同分数）
      - Gini 系数自行实现，不引入新依赖
      - 处理路径格式差异（统一用 posixpath）
      - --verbose 模式的扣分细节对后续诊断至关重要
      - 每个维度的 score 函数应该是独立的（便于单独测试和调试）
      - 考虑空仓库/极小仓库的边界情况（<5 文件时部分维度可能无意义）
```

### T-03: 构建 per-repo ground truth + 诊断报告器

```
Task T-03 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/ground_truth.py, tests/diagnostic_reporter.py]
    修改: [tests/scoring_harness.py]  — 集成 ground truth 检查
    禁止修改: [src/*] — 原因: 纯测试基础设施
  复用: tests/scoring_harness.py (T-02 产出)
  预期日志输出:
    - "[GROUND_TRUTH] Loaded {N} expectations for {repo}"
    - "[GROUND_TRUTH] Checking: {file} expected={expected_class}, actual={actual_class} → {PASS|FAIL}"
    - "[DIAGNOSTIC] Generating report for {repo}..."
    - "[DIAGNOSTIC] Top 3 weakest dimensions: {dims}"
    - "[DIAGNOSTIC] Actionable recommendations: {count}"
  验收标准:
    - [ ] ground_truth.py 包含所有 5 仓库的期望分类定义
    - [ ] diagnostic_reporter.py 生成 Markdown 报告，包含：
      - 每仓库 7 维度雷达图（ASCII）
      - 每维度 Top 3 扣分原因
      - 对下一步优化的 actionable 建议
    - [ ] ground truth 检查集成到 scoring_harness.py 的 InfraAccuracy 维度
    - [ ] python tests/diagnostic_reporter.py --repo test_repos/rich 生成可读报告
    - [ ] pytest tests/test_ground_truth.py 通过
  回滚策略:
    回滚点: T-02 完成后
    替代方案: 简化 ground truth 为仅 infra/non-infra 二分类（不区分具体 cone）
    丢弃条件: 无（基础设施不会失败）
  超时: 20 分钟
  Sub-agent 所需背景:
    领域知识: |
      **为什么需要 ground truth：**
      机械化评分只能检查"结构性质量"（无重复、均匀分布等），但无法判断"语义正确性"
      （beat.py 是否应该在 infra 中？）。Ground truth 补充这一能力。

      **Per-repo ground truth 定义格式：**
      ```python
      GROUND_TRUTH = {
          "rich": {
              "must_be_infra": [
                  "rich/console.py",     # 核心渲染引擎，被所有组件使用
                  "rich/text.py",        # 基础文本类型
                  "rich/style.py",       # 样式系统基础
                  "rich/segment.py",     # 渲染段基础
              ],
              "must_not_be_infra": [
                  "rich/markdown.py",    # 功能模块：Markdown 渲染
                  "rich/table.py",       # 功能模块：表格渲染
                  "rich/progress.py",    # 功能模块：进度条
              ],
              "must_be_same_cone": [
                  ("rich/markdown.py", "rich/markup.py"),  # Markdown 功能组
              ],
          },
          "fastapi": {
              "must_be_infra": [],  # FastAPI infra 较少
              "must_not_be_infra": [
                  "fastapi/middleware/*",    # 中间件是独立功能
                  "fastapi/security/*",     # 安全是独立功能
              ],
              "must_be_separate_cones": [
                  "fastapi/middleware",      # 中间件单独分组
                  "fastapi/security",        # 安全单独分组
                  "fastapi/openapi",         # OpenAPI 单独分组
              ],
          },
          "scrapy": {
              "must_be_infra": [
                  "scrapy/crawler.py",
                  "scrapy/settings/*",
                  "scrapy/exceptions.py",
              ],
              "must_not_be_infra": [
                  "scrapy/spidermiddlewares/*",
                  "scrapy/downloadmiddlewares/*",
              ],
          },
          "celery": {
              "must_be_infra": [
                  "celery/app/*.py",         # 核心 app 框架
                  "celery/utils/*.py",       # 工具代码
              ],
              "must_not_be_infra": [
                  "celery/beat.py",          # 定时任务 — 功能模块！
                  "celery/canvas.py",        # 任务组合 — 功能模块！
                  "celery/result.py",        # 结果后端 — 功能模块！
              ],
          },
          "oh-my-openagent": {
              # 待 T-01 克隆后由 Explore agent 分析填充
              "must_be_infra": [],
              "must_not_be_infra": [],
          },
      }
      ```

      **诊断报告器设计：**
      输入：scoring_harness 的 JSON 输出 + ground truth 检查结果
      输出：Markdown 格式诊断报告，包含：

      1. **概览表**：5 仓库 × 7 维度评分矩阵
      2. **雷达图**（ASCII）：每仓库的 7 维度可视化
         ```
         Uniqueness ████████████░░░  12/15
         Distribution ██████████░░░░░  10/15
         InfraAccuracy ███████████████  15/15
         ...
         ```
      3. **Ground Truth 违规清单**：
         - FAIL: celery/beat.py expected=not_infra, actual=infra (hub mis-detection)
      4. **维度弱点分析**：每维度 Top 3 扣分文件/cone
      5. **Actionable 建议**：基于扣分模式自动推荐下一步优化方向
         例如："D5-DirCoherence 弱 → 建议增加 directory_affinity_score 权重"

      **ground truth 如何集成到 scoring_harness.py：**
      在 D3-InfraAccuracy 维度中，除了 semantic_hints 判断外，
      额外检查 ground_truth 中的 must_be_infra / must_not_be_infra 定义。
      每个 ground truth 违规扣 1 分（D3 总分 15 分内）。

    架构位置: tests/ 目录，与 scoring_harness.py 配合使用
    参考文件:
      - tests/scoring_harness.py — T-02 产出的评分引擎
      - src/graph/feature_cone.py — FeatureCone 数据结构
      - src/graph/semantic_hints.py — classify_file() 参考
    注意事项: |
      - ground truth 定义中的路径使用 glob 模式（如 "celery/utils/*.py"）
      - oh-my-openagent 的 ground truth 先留空，T-04 基线评估时由 Explore agent 填充
      - 诊断报告要足够详细，使人能直接从报告中判断下一步该改什么
      - ASCII 雷达图使用 █ 和 ░ 字符，不依赖外部库
```

### T-04: 采集 5 仓库基线分数 + 生成诊断基线报告

```
Task T-04 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/baseline_scores.json, tests/baseline_diagnostic.md]
    修改: [tests/ground_truth.py] — 填充 oh-my-openagent 的 ground truth
    禁止修改: [src/*] — 原因: 仅运行评分，不改算法
  复用: tests/scoring_harness.py (T-02), tests/ground_truth.py (T-03), tests/diagnostic_reporter.py (T-03)
  预期日志输出:
    - "[BASELINE] Running 7-dimension scoring for rich..."
    - "[BASELINE] Running 7-dimension scoring for fastapi..."
    - "[BASELINE] Running 7-dimension scoring for scrapy..."
    - "[BASELINE] Running 7-dimension scoring for celery..."
    - "[BASELINE] Running 7-dimension scoring for oh-my-openagent..."
    - "[BASELINE] All 5 repos scored. Aggregate mean: {score}/100"
    - "[BASELINE] Generating diagnostic report..."
    - "[BASELINE] Weakest dimension across repos: {dim}"
  验收标准:
    - [ ] baseline_scores.json 包含 5 个仓库的 7 维度评分 + 总分
    - [ ] baseline_diagnostic.md 包含完整诊断报告（概览表 + 雷达图 + ground truth 检查 + 建议）
    - [ ] oh-my-openagent 的 ground truth 已填充（至少 3 条 must_be_infra + 3 条 must_not_be_infra）
    - [ ] 聚合均值已计算并记录
  回滚策略:
    回滚点: T-03 完成后
    替代方案: 跳过评分失败的仓库（标记为 N/A）
    丢弃条件: 3+ 仓库评分失败
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      运行完整评分流水线：
      1. 先用 Explore agent 分析 oh-my-openagent 代码结构，填充 ground truth
      2. 对 5 个仓库运行 scoring_harness.py --all --json > baseline_scores.json
      3. 用 diagnostic_reporter.py 生成 baseline_diagnostic.md
      4. baseline_diagnostic.md 将作为后续优化的"地图"——从最弱维度开始修复
    架构位置: test_repos/ 下 5 个仓库
    参考文件:
      - tests/scoring_harness.py
      - tests/ground_truth.py
      - tests/diagnostic_reporter.py
    注意事项: |
      - oh-my-openagent 可能是小型仓库（<50 文件），ground truth 相应简化
      - 如果某仓库 parse 失败，记录错误但继续其余仓库
      - baseline_scores.json 是后续所有 Keep/Discard 决策的基准
      - baseline_diagnostic.md 是人可读的，要清晰明了
```

### T-05: 修复 exclusive_files 唯一归属

```
Task T-05 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: []
    修改: [src/graph/feature_cone.py]
    禁止修改: [src/server.py, src/graph/grouper.py, tests/scoring_harness.py] — 原因: 其他任务负责
  复用: 无
  预期日志输出:
    - "[FEATURE_CONE] Resolving exclusive_files uniqueness: {N} conflicts found"
    - "[FEATURE_CONE] Assigned {file} to cone {cone_name} (affinity={score})"
    - "[SCORING] Uniqueness improved: {before} → {after}"
  验收标准:
    - [ ] pytest tests/test_feature_cone.py 全部通过
    - [ ] 对所有 5 仓库运行评分，Uniqueness 维度 ≥ 23/25（即 violations < 8% of files）
    - [ ] 不增加 mega-cone 数量（Distribution 维度不下降）
    - [ ] 总分均值 ≥ baseline 均值（autoresearch Keep 条件）
  回滚策略:
    回滚点: T-04 完成后的 git commit
    替代方案: 改用 "last-writer-wins" 策略（按 BFS 遍历顺序，后访问者覆盖先访问者）
    丢弃条件: 总分均值下降 > 5 分
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      【问题】同一文件出现在多个 cone 的 exclusive_files 中（Rich 18 个，Scrapy 12 个）。
      违反了 "exclusive_files 跨 cone 互斥" 不变量。

      【根因】feature_cone.py 第 483-510 行 — 初始归属基于 node_cones 集合大小:
      if len(belonging_cones) == 1: 归入 exclusive_files
      但 BFS 可能从多个 root 都到达同一文件，且各自将其标记为 exclusive。

      【修复方案】在 BFS 完成后、构建 FeatureCone 对象前，增加唯一归属解析步骤：
      1. 对每个被多 root 到达的文件，计算其对各 root 的 affinity 分数
      2. 将文件分配给 affinity 最高的 root（max affinity owner）
      3. 对于其余 root，该文件从 exclusive_files 移到 shared_deps

      【实现位置】在 extract_feature_cones() 函数中，约 line 480 附近，
      在 "Build cones" 循环之前插入唯一归属解析。

      【Autoresearch 原则】修改后运行 scoring_harness.py：
      - 若 Uniqueness 维度提升且总分不降 → git commit
      - 若总分下降 > 5 → git reset --hard 到回滚点
    架构位置: feature_cone.py 是核心算法模块，修改需格外谨慎
    参考文件:
      - src/graph/feature_cone.py — 重点读 lines 440-530（cone 构建区域）
      - tests/test_feature_cone.py — 现有测试用例
      - tests/scoring_harness.py — 评分验证工具
    注意事项: |
      - _affinity_bfs() 返回的 affinity_scores dict 可直接用于归属决策
      - 注意 frozen dataclass 不可变，需在构建 FeatureCone 前完成归属分配
      - 不要改变 shared_threshold 的计算逻辑（T-05 Round 2 已优化过）
```

### T-06: 修复 facade penalty 首跳保护

```
Task T-06 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: []
    修改: [src/graph/feature_cone.py, src/graph/semantic_hints.py]
    禁止修改: [src/server.py, src/graph/grouper.py] — 原因: 其他模块接口不变
  复用: 无
  预期日志输出:
    - "[FEATURE_CONE] Facade {file}: depth=0, penalty skipped (first-hop protection)"
    - "[FEATURE_CONE] Facade {file}: depth={N}, penalty applied (0.3x)"
    - "[SCORING] Distribution improved: {before} → {after}"
  验收标准:
    - [ ] pytest tests/test_feature_cone.py 全部通过
    - [ ] FastAPI 评分 Distribution 维度 ≥ 20/25（无 mega-cone）
    - [ ] 其他 4 仓库评分不下降 > 2 分
    - [ ] 总分均值 ≥ 上一步均值
  回滚策略:
    回滚点: T-05 完成后的 git commit
    替代方案: 将 FACADE_PENALTY 从 0.3 调至 0.5（缓和而非消除）
    丢弃条件: FastAPI 出现更多 mega-cone 或总分下降 > 5
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      【问题】FastAPI 的 __init__.py 是 re-export facade，BFS 从 root 到达它时
      affinity 被 FACADE_PENALTY(0.3) 惩罚：0.3 × 0.3 × 0.7 = 0.063 < AFFINITY_CUTOFF(0.08)，
      导致 BFS 被完全阻断。30+ 文件变成 orphan，被合并成一个 mega-cone。

      【修复方案】Facade penalty 改为仅在 BFS depth > 1 时生效：
      - depth=0（root 的直接后继）：不施加 facade penalty，保留 root 首跳 BFS 的完整可达性
      - depth>1：正常施加 facade penalty，防止 re-export 扩散

      【实现位置】_affinity_bfs() 函数（feature_cone.py ~line 258-307）：
      在 penalty 应用处增加 depth 检查：
      ```python
      if node in facade_nodes and depth > 1:
          ea *= FACADE_PENALTY
      ```
      当前代码在 line ~295 只检查 `if node in facade_nodes`。

      注意 _affinity_bfs 需要追踪每个节点的 BFS depth（当前可能只追踪 affinity 不追踪 depth）。
      如果没有 depth 信息，需要在 BFS 队列元素中增加 depth 字段。
    架构位置: _affinity_bfs() 是 BFS 核心，修改影响所有 cone 的构建
    参考文件:
      - src/graph/feature_cone.py — 重点读 _affinity_bfs() 函数
      - src/graph/semantic_hints.py — is_reexport_facade() 检测逻辑
      - tests/test_feature_cone.py — 现有 BFS 测试
    注意事项: |
      - BFS 队列目前是 deque，元素格式需确认（可能是 (node, affinity)）
      - 增加 depth 追踪不应引入性能退化
      - FastAPI test_repos/fastapi 必须能复现该问题
```

### T-07: 修复 hub 检测增加 out-degree 区分

```
Task T-07 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: []
    修改: [src/graph/feature_cone.py]
    禁止修改: [src/graph/semantic_hints.py, src/server.py] — 原因: 接口不变
  复用: 无
  预期日志输出:
    - "[HUB_DETECT] {file}: in_degree={N}, out_degree={M}, ratio={R} → {tool|functional}"
    - "[HUB_DETECT] Functional module {file} kept in cone (out_degree > threshold)"
    - "[SCORING] InfraAccuracy improved: {before} → {after}"
  验收标准:
    - [ ] pytest tests/test_feature_cone.py 全部通过
    - [ ] Celery 评分 InfraAccuracy 维度 ≥ 20/25
    - [ ] beat.py, canvas.py, result.py 不被标记为 infrastructure
    - [ ] 真正的工具文件（utils.py, compat.py）仍被正确标记为 infrastructure
    - [ ] 总分均值 ≥ 上一步均值
  回滚策略:
    回滚点: T-06 完成后的 git commit
    替代方案: 将 hub 检测阈值从 0.3 提高到 0.5（减少误标数量）
    丢弃条件: Rich/FastAPI 的 InfraAccuracy 下降 > 5 分
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      【问题】Celery 的 beat.py、canvas.py、result.py 是核心功能模块，
      但因为 in-degree 高（被很多文件导入），hub 检测将它们误标为 infrastructure。

      【根因】_detect_hub_nodes() 只看 in-degree centrality + raw in-degree，
      不考虑 out-degree。工具文件（utils, compat）通常 out-degree 低（被调用但不调用别人），
      功能模块（beat, canvas）通常 out-degree 高（既被调用，自身也调用很多依赖）。

      【修复方案】在 hub 检测中增加 out-degree/in-degree ratio 判断：
      - ratio < 0.3（out-degree 远低于 in-degree）→ 确认为 infrastructure（工具/通用代码）
      - ratio >= 0.3（out-degree 接近或超过 in-degree）→ 保留为功能模块，不标记为 hub

      【实现位置】_detect_hub_nodes() 函数（feature_cone.py ~line 167-210）：
      在计算 hub_score 后、过滤 pre_infra 前，增加 out-degree ratio 过滤。

      【量化标准】
      - utils.py: in_degree=15, out_degree=2 → ratio=0.13 → infrastructure ✓
      - beat.py: in_degree=12, out_degree=8 → ratio=0.67 → functional module ✓
    架构位置: _detect_hub_nodes() 被 extract_feature_cones() 调用，影响 infrastructure_nodes 集合
    参考文件:
      - src/graph/feature_cone.py — 重点读 _detect_hub_nodes()
      - tests/test_feature_cone.py — 现有 hub 检测测试
    注意事项: |
      - 0.3 threshold 是初始值，可能需要在评分反馈中微调
      - out-degree 要在 DAG（无环图）上计算，不是原始 graph
      - 注意小图（<10 节点）的 ratio 可能不稳定
```

### T-08: 修复框架型 repo directory-first 聚合

```
Task T-08 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: []
    修改: [src/graph/feature_cone.py, src/graph/grouper.py]
    禁止修改: [src/server.py, src/parser/codebase.py] — 原因: 接口不变
  复用: 无
  预期日志输出:
    - "[FEATURE_CONE] Framework repo detected: {N} roots > 20 threshold"
    - "[FEATURE_CONE] Switching to directory-first aggregation"
    - "[FEATURE_CONE] Directory group {dir}: {N} files merged"
    - "[SCORING] Distribution improved: {before} → {after}"
  验收标准:
    - [ ] pytest tests/test_feature_cone.py 全部通过
    - [ ] Scrapy root 数量降至 ≤ 20 有效 roots
    - [ ] Scrapy 评分 Distribution 维度 ≥ 18/25
    - [ ] 非框架型仓库（Rich, oh-my-openagent）不触发 directory-first 模式
    - [ ] 总分均值 ≥ 上一步均值
  回滚策略:
    回滚点: T-07 完成后的 git commit
    替代方案: 简单上限 cap — 只取 in-degree 最低的 20 个 root
    丢弃条件: Scrapy 总分下降或其他仓库受影响 > 3 分
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      【问题】Scrapy 有 72 个 root（in-degree=0 的文件），
      导致 shared_threshold = max(2, round(sqrt(72)*1.2)) = 11，
      使中等共享文件（在 8 个 cone 中）无法被提升为 infrastructure。

      【根因】框架型 repo 有大量独立的入口点（每个 spider middleware、download handler
      都是独立入口），BFS 产生大量小 cone，fragmentation 严重。

      【修复方案】检测框架型 repo（root 数 > 20）时切换聚合策略：
      1. 检测条件：len(roots) > 20
      2. 先按一级目录分组：同一子包下的 roots 合并为一个"超级 root"
      3. 从超级 root 出发做 BFS（超级 root 内的文件自动成为 exclusive）
      4. shared_threshold 在合并后的超级 root 数量上计算

      【实现位置】extract_feature_cones() 函数开头（~line 440），
      在 roots = find_feature_roots() 之后插入检测和合并逻辑。

      【示例】Scrapy:
      - spidermiddlewares/ 下 12 个 root → 合并为 1 个超级 root
      - downloadmiddlewares/ 下 8 个 root → 合并为 1 个超级 root
      - 72 roots → ~15 超级 roots → shared_threshold 降至合理范围
    架构位置: 影响 feature_cone.py 的入口逻辑和 grouper.py 的调用方式
    参考文件:
      - src/graph/feature_cone.py — find_feature_roots() 和 extract_feature_cones()
      - src/graph/grouper.py — extract_feature_cones() 调用入口
      - test_repos/scrapy/ — 实际测试仓库
    注意事项: |
      - 超级 root 合并必须保留原始文件的 BFS 可达性
      - 目录分组使用 posixpath 处理（项目内部统一用 posix 路径）
      - 不要影响非框架型仓库（检测条件必须充分）
```

### T-09: 全量跨仓库基准测试 + 回归报告

```
Task T-09 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/benchmark_report.json, tests/benchmark_diagnostic.md]
    修改: []
    禁止修改: [src/*] — 原因: 纯测试，不改代码
  复用: tests/scoring_harness.py (T-02), tests/baseline_scores.json (T-04), tests/diagnostic_reporter.py (T-03)
  预期日志输出:
    - "[BENCHMARK] Running final 7-dimension evaluation..."
    - "[BENCHMARK] Rich: {before} → {after} (Δ={delta})"
    - "[BENCHMARK] FastAPI: {before} → {after} (Δ={delta})"
    - "[BENCHMARK] Scrapy: {before} → {after} (Δ={delta})"
    - "[BENCHMARK] Celery: {before} → {after} (Δ={delta})"
    - "[BENCHMARK] oh-my-openagent: {before} → {after} (Δ={delta})"
    - "[BENCHMARK] Aggregate mean: {before} → {after}"
    - "[BENCHMARK] Ground truth pass rate: {rate}%"
  验收标准:
    - [ ] 所有 5 仓库评分完成，无错误
    - [ ] 总分均值 ≥ 80（目标）
    - [ ] 无单仓库总分下降 > 5 分（相对 baseline）
    - [ ] benchmark_report.json 包含 before/after 7 维度全对比
    - [ ] benchmark_diagnostic.md 包含改进摘要 + 剩余弱点分析
    - [ ] ground truth 违规数 ≤ baseline 违规数的 50%
  回滚策略:
    回滚点: T-08 完成后的 git commit
    替代方案: 如果某仓库下降，选择性回退该仓库对应的修复
    丢弃条件: 总分均值 < baseline 均值（整体恶化）
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: |
      运行完整评分 + 对比 + 诊断流水线：
      1. python tests/scoring_harness.py --all --json > tests/benchmark_report.json
      2. python tests/scoring_harness.py --all --compare tests/baseline_scores.json（看 delta）
      3. python tests/diagnostic_reporter.py --current tests/benchmark_report.json --baseline tests/baseline_scores.json > tests/benchmark_diagnostic.md
      4. 检查每个仓库每维度的改进幅度，标记回归（delta < -2）
    架构位置: 纯验证任务
    参考文件:
      - tests/scoring_harness.py, tests/diagnostic_reporter.py, tests/baseline_scores.json
    注意事项: |
      - 如果总分均值 < 80，报告中必须列出最弱维度和推荐的后续优化
      - benchmark_diagnostic.md 是给用户看的最终报告，要清晰、有洞察
```

### T-10: 编写/更新单元测试（含评分工具测试）

```
Task T-10 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/test_scoring_harness.py, tests/test_ground_truth.py]
    修改: [tests/test_feature_cone.py]
    禁止修改: [src/*] — 原因: 纯测试任务
  复用: 无
  预期日志输出:
    - "[TEST] Added test_exclusive_files_uniqueness_invariant"
    - "[TEST] Added test_facade_penalty_first_hop_protection"
    - "[TEST] Added test_hub_detection_out_degree_filter"
    - "[TEST] Added test_framework_repo_directory_first"
    - "[TEST] Added test_scoring_dimension_uniqueness"
    - "[TEST] Added test_scoring_dimension_distribution"
    - "[TEST] Added test_gini_coefficient"
    - "[TEST] Added test_ground_truth_matching"
    - "[TEST] All tests passing"
  验收标准:
    - [ ] pytest tests/ 全部通过（包括新增测试）
    - [ ] 算法回归测试 ≥ 8 个（每个根因修复 2 个：正例 + 反例）
    - [ ] 评分工具测试 ≥ 12 个（每维度至少 1 个 + 边界情况 + ground truth）
    - [ ] 现有 244+ 测试不受影响
  回滚策略:
    回滚点: T-09 完成后
    替代方案: 减少测试数量但覆盖所有维度的核心路径
    丢弃条件: 无
  超时: 20 分钟
  Sub-agent 所需背景:
    领域知识: |
      需要两类测试：

      **A. 算法回归测试（test_feature_cone.py 新增）：**
      1. exclusive_files 唯一性：构造图使同一文件被多 root BFS 到达，验证最终只属于一个 cone
      2. facade penalty 首跳保护：构造 facade node 作为 root 的直接后继，验证 BFS 不被阻断
      3. hub out-degree 过滤：构造高 in-degree 但也高 out-degree 的节点，验证不被标为 infra
      4. framework repo 目录合并：构造 >20 roots，验证自动触发 directory-first 模式

      **B. 评分工具测试（test_scoring_harness.py 新增）：**
      1. 每个维度的纯函数测试（给定 mock cones，验证评分正确）
      2. gini 系数计算正确性（已知输入/输出对）
      3. mega-cone 扣分逻辑
      4. 空输入/边界情况（0 cones, 1 cone, 100% single-file）
      5. JSON 输出格式符合 Schema
      6. --compare 模式的 delta 计算正确

      **C. ground truth 测试（test_ground_truth.py 新增）：**
      1. glob 模式匹配正确性
      2. must_be_infra / must_not_be_infra 检查逻辑
      3. must_be_same_cone / must_be_separate_cones 检查逻辑
    架构位置: tests/ 目录下的 pytest 测试
    参考文件:
      - tests/test_feature_cone.py — 现有测试结构
      - tests/scoring_harness.py — 评分引擎
      - tests/ground_truth.py — ground truth 定义
    注意事项: |
      - 使用 pytest fixtures 复用图构建代码
      - 测试应该独立，不依赖外部 test_repos
      - 使用 networkx.DiGraph 构造最小化测试图
      - 评分工具测试使用 mock FeatureCone 对象
```

### T-11: 回归保护 — 评分检查集成到 pytest

```
Task T-11 规格：
  Skill: orchestrated-development (/od)
  操作范围:
    创建: [tests/test_regression_scores.py]
    修改: [tests/conftest.py] — 添加 pytest marker 配置
    禁止修改: [src/*] — 原因: 纯测试任务
  复用: tests/scoring_harness.py, tests/ground_truth.py
  预期日志输出:
    - "[REGRESSION] Registered pytest marker: @pytest.mark.regression"
    - "[REGRESSION] Score floor check: {repo} >= {floor}"
    - "[REGRESSION] Ground truth check: {repo} violations <= {max}"
  验收标准:
    - [ ] pytest -m regression 运行所有回归测试
    - [ ] 每个仓库有 score floor 测试（当前分数 - 5 分容忍度）
    - [ ] 每个仓库有 ground truth 违规上限测试
    - [ ] pytest tests/test_regression_scores.py 全部通过
  回滚策略:
    回滚点: T-10 完成后
    替代方案: 简化为仅检查总分均值 ≥ 某阈值
    丢弃条件: 无
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: |
      **目的：** 确保未来的代码修改不会使评分回退。

      **设计：**
      ```python
      @pytest.mark.regression
      @pytest.mark.parametrize("repo", ["rich", "fastapi", "scrapy", "celery", "oh-my-openagent"])
      def test_score_floor(repo):
          """Each repo's total score must not drop below established floor."""
          result = score_repo(f"test_repos/{repo}")
          floor = SCORE_FLOORS[repo]  # 从 benchmark_report.json 中取当前分数 - 5
          assert result["total"] >= floor, f"{repo}: {result['total']} < floor {floor}"

      @pytest.mark.regression
      def test_aggregate_mean():
          """Aggregate mean across all repos must stay >= 75."""
          scores = [score_repo(f"test_repos/{r}")["total"] for r in REPOS]
          assert statistics.mean(scores) >= 75

      @pytest.mark.regression
      @pytest.mark.parametrize("repo", REPOS)
      def test_ground_truth_violations(repo):
          """Ground truth violations must not increase."""
          violations = check_ground_truth(repo)
          max_violations = MAX_VIOLATIONS[repo]  # 从 benchmark_report.json 取
          assert len(violations) <= max_violations
      ```

      **pytest marker 配置：** 在 conftest.py 中注册 `regression` marker，
      使 `pytest -m regression` 可以单独运行回归检查。

      **SCORE_FLOORS 和 MAX_VIOLATIONS：** 从 tests/benchmark_report.json 动态读取，
      或在 test_regression_scores.py 中硬编码（取 T-09 benchmark 的结果 - 5 分容忍度）。
    架构位置: tests/ 目录
    参考文件:
      - tests/scoring_harness.py
      - tests/ground_truth.py
      - tests/benchmark_report.json
      - tests/conftest.py
    注意事项: |
      - 回归测试跳过不存在的 test_repos（用 pytest.mark.skipif）
      - 标记为 @pytest.mark.slow 因为需要 parse 整个仓库
      - 不要让这些测试阻塞常规 pytest 运行（需要显式 -m regression 才运行）
```

### T-12: 代码审查 + 最终验证

```
Task T-12 规格：
  Skill: agent: code-reviewer
  操作范围:
    创建: []
    修改: [] — 审查不修改代码
    禁止修改: [*] — 只读审查
  复用: 无
  预期日志输出:
    - "[REVIEW] Scanning modified files..."
    - "[REVIEW] Issues found: CRITICAL={N}, HIGH={N}, MEDIUM={N}"
  验收标准:
    - [ ] 零 CRITICAL 问题
    - [ ] HIGH 问题 ≤ 2
    - [ ] 所有 HIGH 问题有修复建议
    - [ ] pytest tests/ 全部通过（最终确认）
    - [ ] pytest -m regression 全部通过
  回滚策略:
    回滚点: T-11 完成后
    替代方案: 无（审查不改代码）
    丢弃条件: 无
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: Python 代码质量审查（安全性、可读性、架构合规）
    架构位置: 审查 src/graph/feature_cone.py 和 tests/ 目录的所有修改
    参考文件:
      - src/graph/feature_cone.py
      - src/graph/semantic_hints.py
      - src/graph/grouper.py
      - tests/scoring_harness.py
      - tests/ground_truth.py
      - tests/diagnostic_reporter.py
      - tests/test_feature_cone.py
      - tests/test_scoring_harness.py
      - tests/test_regression_scores.py
    注意事项: |
      - 重点关注 frozen dataclass 不可变约束是否被违反
      - 评分工具的纯函数性（无副作用）
      - ground truth 定义的路径 glob 安全性
```

---

## Block 4 — Parallel Execution Map

```
并行组 A（同时启动，最多 2 个）：T-01, T-02
  依赖：无
  约束：T-01 克隆仓库，T-02 写评分引擎，无共享写入目标
  最大并行数：2

串行步骤：T-03（等待 T-01 + T-02 完成）
  依赖：需要 T-02 的评分引擎 + T-01 的仓库（oh-my-openagent ground truth 需要分析）
  原因：ground truth 定义需要知道仓库结构，诊断报告器需要评分引擎

串行步骤：T-04（等待 T-03 完成）
  依赖：需要 T-02 评分引擎 + T-03 ground truth + T-01 仓库
  原因：基线评分需要完整基础设施

串行链（每步依赖前一步的评分结果）：T-05 → T-06 → T-07 → T-08
  依赖：每步需要前一步完成后的代码状态 + 评分验证
  原因：Autoresearch 原则 — 每次只改一个组件，评分后再决定下一步
  注意：如果某步 Discard（评分下降），尝试替代方案后再继续

串行步骤：T-09（等待 T-08 完成）
  依赖：需要所有 4 个修复都完成
  原因：全量基准测试比较完整改进幅度

并行组 B（同时启动，最多 2 个）：T-10, T-11
  依赖：T-09 完成
  约束：T-10 写单元测试，T-11 写回归测试，文件不重叠
  最大并行数：2

串行步骤：T-12（等待 T-10 + T-11 完成）
  依赖：需要所有测试就绪后做最终代码审查
  原因：审查范围包含所有新增代码
```

**DAG 可视化：**
```
T-01 ─┐
      ├─→ T-03 ─→ T-04 ─→ T-05 ─→ T-06 ─→ T-07 ─→ T-08 ─→ T-09 ─┬─→ T-10 ─┐
T-02 ─┘                                                               └─→ T-11 ─┼─→ T-12
                                                                                  └────┘
```

---

## Block 5 — File Decomposition

| 文件路径 | 操作 | 负责任务 | Agent |
|----------|------|---------|-------|
| test_repos/oh-my-openagent/ | 创建（clone） | T-01 | Bash |
| tests/scoring_harness.py | 创建 | T-02 | /od |
| tests/ground_truth.py | 创建 | T-03 | /od |
| tests/diagnostic_reporter.py | 创建 | T-03 | /od |
| tests/baseline_scores.json | 创建 | T-04 | /od |
| tests/baseline_diagnostic.md | 创建 | T-04 | /od |
| src/graph/feature_cone.py | 修改 | T-05, T-06, T-07, T-08 | /od（严格串行） |
| src/graph/semantic_hints.py | 修改 | T-06 | /od |
| src/graph/grouper.py | 修改 | T-08 | /od |
| tests/benchmark_report.json | 创建 | T-09 | /od |
| tests/benchmark_diagnostic.md | 创建 | T-09 | /od |
| tests/test_feature_cone.py | 修改 | T-10 | /od |
| tests/test_scoring_harness.py | 创建 | T-10 | /od |
| tests/test_ground_truth.py | 创建 | T-10 | /od |
| tests/test_regression_scores.py | 创建 | T-11 | /od |
| tests/conftest.py | 修改 | T-11 | /od |

**写入冲突分析：**
- feature_cone.py 被 T-05/T-06/T-07/T-08 修改，四个任务严格串行，无冲突
- T-10 和 T-11 写不同测试文件（test_feature_cone vs test_regression_scores），可并行
- scoring_harness.py 在 T-02 创建后，T-03 修改集成 ground truth，两者串行

---

## Block 6 — Phase Structure

### Phase 1: 评分基础设施建设（T-01, T-02, T-03, T-04）— 重点投入

**入口条件：** 项目代码可编译，现有测试通过
**退出条件：**
- oh-my-openagent 已克隆
- 7 维度评分引擎可运行（--repo / --all / --compare / --verbose 四种模式）
- 5 仓库 ground truth 定义完整（每仓库 ≥3 条 must_be + ≥3 条 must_not_be）
- 诊断报告器可生成 Markdown 报告
- baseline_scores.json + baseline_diagnostic.md 已生成
- ≥12 个评分工具单元测试通过

**质量门控：** 评分引擎必须是"可信赖的"——在后续 Phase 2 中，所有 Keep/Discard 决策
都基于它的输出。如果评分引擎有 bug，后续所有优化方向都会出错。因此：
- 每个维度的评分函数必须有独立单元测试
- 已知边界情况（0 cones, 1 mega-cone, 全 single-file）必须有测试
- gini 系数计算对 [1,1,1,1] 返回 0，对 [0,0,0,100] 接近 1

### Phase 2: Autoresearch Fix Loop（T-05, T-06, T-07, T-08）

**入口条件：** Phase 1 完成，baseline 已采集，评分引擎已验证
**退出条件：**
- 4 个根因修复均已尝试（Keep 或替代方案已应用）
- 每步都有评分验证记录
- 无单仓库总分下降 > 5 分

**Autoresearch 决策规则（每个 T-xx 完成后）：**
```
# 运行评分
current = scoring_harness.py --all --json
previous = 上一步的评分（T-05 用 baseline，T-06 用 T-05 后的分数，以此类推）

IF current.mean >= previous.mean:
    git commit -m "fix: {description} — score: {before}→{after}"  # KEEP
ELIF current.mean >= previous.mean - 2:
    git commit  # KEEP（微小下降可接受，整体趋势正确）
ELSE:
    git reset --hard {rollback_point}  # DISCARD
    尝试替代方案（每个 T-xx 规格中已定义）
    IF 替代方案也 DISCARD:
        跳过此修复，继续下一个
```

### Phase 3: 验证与回归保护（T-09, T-10, T-11, T-12）

**入口条件：** Phase 2 完成
**退出条件：**
- benchmark_report.json 显示总分均值 ≥ 80（目标）
- benchmark_diagnostic.md 包含完整改进分析
- 算法回归测试 ≥ 8 个通过
- 评分工具测试 ≥ 12 个通过
- 回归保护 pytest marker 就绪（pytest -m regression 可运行）
- 代码审查零 CRITICAL 问题

---

## Block 7 — Context Recovery Protocol

（已在文件顶部。）

恢复步骤：
1. 读取 Block 2 进度 checkbox
2. 读取 checkpoint YAML 中的 phase 和 last_completed_task
3. 调用 /od 从首个 `[ ]` 任务继续

---

## Block 8 — Validation / Success Criteria

### 评分目标（核心指标）

| # | 标准 | 验证方式 | 优先级 |
|---|------|---------|--------|
| 1 | **总分均值 ≥ 80** | `python tests/scoring_harness.py --all --json` → aggregate_mean | P0 |
| 2 | 无单仓库总分 < 65 | benchmark_report.json 中每个 total ≥ 65 | P0 |
| 3 | D1-Uniqueness ≥ 13/15（所有仓库） | 每仓库 uniqueness.score ≥ 13 | P0 |
| 4 | D2-Distribution: 无 mega-cone | 每仓库 distribution.details.mega_cones == 0 | P0 |
| 5 | D3-InfraAccuracy ≥ 12/15（所有仓库） | 每仓库 infra_accuracy.score ≥ 12 | P1 |
| 6 | D5-DirCoherence ≥ 10/15（所有仓库） | 每仓库 dir_coherence.score ≥ 10 | P1 |
| 7 | D6-DepIntegrity ≥ 10/15（所有仓库） | 每仓库 dep_integrity.score ≥ 10 | P1 |
| 8 | Ground truth 违规总数 ≤ baseline 的 50% | ground truth 检查 | P1 |

### 代码质量

| # | 标准 | 验证方式 |
|---|------|---------|
| 9 | 现有 244+ 测试全部通过 | `pytest tests/ --tb=short -m "not regression"` 退出码 0 |
| 10 | 新增算法回归测试 ≥ 8 个 | `pytest tests/test_feature_cone.py -v --co \| wc -l` |
| 11 | 新增评分工具测试 ≥ 12 个 | `pytest tests/test_scoring_harness.py tests/test_ground_truth.py -v --co \| wc -l` |
| 12 | 回归保护测试通过 | `pytest -m regression` 退出码 0 |
| 13 | 代码审查零 CRITICAL | code-reviewer agent 报告 |
| 14 | feature_cone.py < 1400 行 | `wc -l src/graph/feature_cone.py` |
| 15 | 所有函数 < 50 行 | code-reviewer 检查 |

### 基础设施质量

| # | 标准 | 验证方式 |
|---|------|---------|
| 16 | 评分引擎 4 种 CLI 模式可用 | `--repo`, `--all`, `--compare`, `--verbose` 各运行一次 |
| 17 | 7 维度评分均有独立单元测试 | test_scoring_harness.py 中每维度 ≥1 测试 |
| 18 | 诊断报告包含雷达图 + 扣分分析 + 建议 | baseline_diagnostic.md 人工可读 |
| 19 | 5 仓库 ground truth 各 ≥3 条规则 | ground_truth.py 中检查 |
