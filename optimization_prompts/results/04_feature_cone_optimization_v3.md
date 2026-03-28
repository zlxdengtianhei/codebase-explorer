# Feature Cone 算法优化记录 V3

> 本文档记录 feature_cone.py 算法的所有优化尝试、结果与当前状态。
> 后续 Agent 在优化前**必须先阅读本文档**，避免重复已失败的方向。

---

## 一、算法演进时间线

### V1: BFS-from-roots（已废弃）

**思路**：从 in-degree=0 的 root 节点出发，用 affinity-decay BFS 向下追踪依赖，每个 root 形成一个 cone。

**问题（四个共性根因）**：
1. **exclusive_files 唯一性被违反** — 多个 root 的 BFS 覆盖同一文件，导致文件出现在多个 cone
2. **Facade penalty 过于激进** — `__init__.py` 的子节点被过度惩罚
3. **Hub 检测无法区分功能模块和工具** — PageRank 将高 in-degree 的功能模块误判为 infra
4. **框架型 repo root 数量过多** — FastAPI 有 371 个 root，产生大量碎片 cone

**实测数据**：
- 所有 repo 的 Newman modularity 为负（-0.02 ~ -0.17），即分组质量差于随机
- FastAPI: 700/1118 文件 (63%) 未被任何 BFS 覆盖
- 整体 cohesion 仅 12-27%

### V2: BFS + 参数调优（已废弃）

**尝试**：提高 BFS 参数以增大覆盖范围
- `EDGE_AFFINITY`: {1: 0.3→0.5, 2: 0.5→0.6, 3: 0.7→0.8}
- `AFFINITY_DECAY`: 0.7→0.85
- `AFFINITY_CUTOFF`: 0.08→0.02
- `MAX_MERGED_CONE_SIZE`: 15→60

**结果**：Rich cohesion 27%→67%，但 infra 膨胀至 34%。BFS 覆盖更广导致更多文件被多 cone 共享，被迫提升到 infra，治标不治本。

**教训**：BFS-from-roots 的根本缺陷在于策略本身，参数调优无法解决。

### V2.5: Uniqueness-to-infra 替代（已废弃）

**尝试**：对于被多 cone 覆盖的文件，不提升为 infra，而是分配给 affinity 最高的 cone。

**结果**：略微改善，但 infra 仍然过高。BFS 覆盖范围的根本问题未解决。

### V3: Louvain 社区检测（当前版本）

**思路**：用 Louvain 算法在加权无向图上做社区检测，天然解决四个根因：
- 每个节点只属于一个社区 → uniqueness invariant 自动满足
- 不需要 facade penalty → 通过图结构自然发现连接
- 不需要 hub 检测 → Louvain 根据边密度自然分组
- 不需要 root 枚举 → Louvain 是全局优化

**当前算法流程**（`extract_feature_cones`）：
1. `_louvain_communities(dag)` — Louvain 社区检测（`weight="weight"`, `resolution=1.0`, `seed=42`）
2. `_merge_small_communities(communities, dag, min_size=3)` — 将 <3 文件的小社区合并到边最多的邻居
3. `_identify_infrastructure(dag, communities)` — 语义分类 + 跨社区导入分析识别 infra
4. 构建 FeatureCone 对象
5. `_separate_testing_files` — 将测试文件从运行时 cone 分离
6. `_rename_cones` — 生成有意义的 cone 名称

---

## 二、已尝试并废弃的 V3 变体

### V3a: 递归 Louvain 拆分（废弃）

**尝试**：对超过 `MAX_COMMUNITY_SIZE` 的大社区，递归用更高 resolution 的 Louvain 拆分。

**问题**：
- 递归拆分产生大量 1-2 文件的碎片社区（FastAPI: 759 社区中 729 个 <3 文件）
- 合并碎片时又重新创建 mega-cone
- 增加了 `_split_large_community`、`_group_overflow` 两个复杂函数

**教训**：过度工程化。Louvain 在 `resolution=1.0` 的结果已经是最优 modularity，强行拆分只会破坏结构。

### V3b: 合并时的 size cap（废弃）

**尝试**：合并小社区时设定 `MAX_COMMUNITY_SIZE` 上限，超出的作为 overflow 按目录分组。

**问题**：FastAPI 产生大量人工的 80 文件 chunk（按目录字母序切割），完全不尊重图结构。

**教训**：按文件数量硬切割是错误方向。

---

## 三、当前实测指标（V3 最终版）

| Repo | Modularity | Cohesion | Cones | Infra | Max Cone |
|------|-----------|----------|-------|-------|----------|
| celery | +0.191 | 28.1% | 26 | 55 (13%) | 52 |
| fastapi | +0.219 | 41.6% | 23 | 12 (1%) | 362 |
| flask | -0.037 | 45.5% | 10 | 25 (30%) | 15 |
| rich | +0.091 | 33.7% | 22 | 26 (12%) | 24 |
| scrapy | +0.395 | 39.6% | 29 | 49 (11%) | 99 |
| **平均** | **+0.172** | **37.7%** | | | |

**对比 V1 基线**：modularity 从全负 → 4/5 正，cohesion 从 12-27% → 28-46%

### V3 + 死代码清理 + Infra 扩展（当前版本，2026-03-26）

**变更**：
1. 删除 11 个 V1 死函数 + 12 个常量（1288→364 行）
2. `_identify_infrastructure` 添加 Criterion 2（_EXTRA_INFRA_STEMS）和 Criterion 3（is_reexport_facade）
3. 7 维评分基线（scoring_harness）：

| Repo | Total/100 | D1 | D2 | D3 | D4 | D5 | D6 | D7 |
|------|----------|----|----|----|----|----|----|-----|
| celery | 83.32 | 15.0 | 10.26 | 12.50 | 10.0 | 12.11 | 8.45 | 15.0 |
| fastapi | 84.66 | 15.0 | 4.39 | 12.19 | 10.0 | 14.47 | 13.64 | 15.0 |
| flask | 88.57 | 15.0 | 8.69 | 12.27 | 10.0 | 12.61 | 15.0 | 15.0 |
| rich | 74.73 | 15.0 | 9.01 | 6.43 | 10.0 | 8.00 | 11.25 | 15.0 |
| scrapy | 85.02 | 15.0 | 7.93 | 13.27 | 10.0 | 13.31 | 10.71 | 14.83 |
| **平均** | **83.26** | | | | | | | |

### V3 实验：强边权重放大（废弃）

**假设**：在 `_louvain_communities` 中对 weight≥2 的边乘 2（call=4, inherit=6），让 Louvain 更倾向保持强依赖在同一社区。

**结果**：celery +1.17, scrapy +1.12，但 flask -4.04, rich -3.00。aggregate 从 83.26 降至 82.27。

**教训**：放大强边权重会改变所有社区边界，不只是强边。对小 repo（Flask）和 flat repo（Rich）产生负面连锁反应。废弃。

### V3 实验：directory_affinity_score 整合（保留）

**假设**：在 `_merge_small_communities` 中综合 edge_count + directory_affinity_score 作为合并目标选择，提升 D5 DirCoherence。

**实现**：`score = edges + avg_affinity * max_edges`，对大社区取前 20 文件样本避免 O(n²)。

**结果**：5-repo aggregate 不变（83.26），所有 repo 分数一致。原因是当前 edge-count 最大的目标恰好也是 directory 最亲近的。作为 tiebreaker 保留——边数相近时倾向同目录合并。**利用了之前完全未使用的 `directory_affinity_score` 资源。**

### V3 修复：stale node_to_comm in _merge_small_communities（保留）

**问题**：`_merge_small_communities` 中 `node_to_comm` 仅在函数开始时构建一次。当一个小社区合并到大社区后，后续小社区的邻居查找仍使用旧映射，导致已合并节点不可见。

**修复**：合并后立即更新 `node_to_comm`：
```python
merged[best_target].update(small_files)
for f in small_files:
    node_to_comm[f] = best_target
```

**结果**：5-repo 分数不变（83.26）。当前测试 repo 未触发此 bug（小社区之间恰好没有互为邻居），但修复是正确的，防止未来回归。

### V3 改进：FeatureCone 使用 tuple 替代 list（保留）

**问题**：`FeatureCone` 使用 `frozen=True` 但 `exclusive_files` 和 `shared_deps` 是 `list[str]`，仍可被 `.append()` 等方法原地修改。

**修复**：字段类型改为 `tuple[str, ...]`，所有构造处使用 `tuple()`。更新了 feature_cone.py、server.py、test_feature_cone.py、test_scoring_harness.py。

**结果**：736 测试全部通过，分数不变。真正的不可变数据结构。

### V3 实验：middleware/security 加入 infra_categories（废弃）

**假设**：`semantic_hints.py` 将文件分为 middleware 和 security 类别，这些同样是横切关注点，应加入 `_identify_infrastructure` 的 `infra_categories`。

**结果**：FastAPI 的 `fastapi/security/` 目录（6 个文件：oauth2.py、http.py 等）被错误分类为 infra。这些是功能模块，不是横切基础设施。ground truth 明确标记为 `must_not_be_infra`。aggregate 从 83.26 降至 82.67。

**教训**：`classify_file` 的 "security" 类别太宽泛——匹配了 `fastapi/security/` 这样的功能目录。"middleware" 单独可能可行，但未单独测试。废弃。

### V3 评分体系升级：D8 ClusterARI + D9 LLM-as-Judge（2026-03-26）

**动机**：原 7 维评分（D1-D7）衡量间接代理指标（结构不变量、统计属性、文件名启发式），无法直接回答"算法分组是否匹配真实架构"。

**新增维度**：
- **D8 ClusterARI (15分)**：纯 Python ARI 实现，对比 `CLUSTER_GROUND_TRUTH`（5 repo 共 216 个文件的人工标注）vs 算法 cone 分配。ARI=1 完美匹配，ARI=0 等同随机。
- **D9 LLM SemanticCoherence (15分)**：Haiku 4.5 判断 cone 语义质量（0-4 整数），JSON 缓存，opt-in `--llm-judge`。
- **总分归一化为百分制**：`total = raw_sum / max_possible * 100`

**9 维基线（D1-D8，D9 未启用）**：

| Repo | Total% | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 ARI(分) | ARI 值 | NMI |
|------|--------|----|----|----|----|----|----|-----|-----------|--------|-----|
| celery | 76.18 | 15.0 | 10.3 | 12.5 | 10.0 | 12.1 | 8.4 | 15.0 | 4.3 | 0.286 | 0.582 |
| fastapi | 75.63 | 15.0 | 4.4 | 12.2 | 10.0 | 14.5 | 13.6 | 15.0 | 2.3 | 0.155 | 0.496 |
| flask | 77.02 | 15.0 | 8.7 | 12.3 | 10.0 | 12.6 | 15.0 | 15.0 | 0.0 | -0.010 | 0.225 |
| rich | 65.77 | 15.0 | 9.1 | 6.4 | 10.0 | 8.0 | 11.3 | 15.0 | 0.9 | 0.061 | 0.365 |
| scrapy | 76.37 | 15.0 | 7.9 | 13.3 | 10.0 | 13.3 | 10.7 | 14.8 | 2.8 | 0.187 | 0.520 |
| **平均** | **74.19** | | | | | | | | | | |

**关键发现**：D8 揭示了算法与真实架构的差距——ARI 仅 0.00-0.29，说明 Louvain 社区与人工标注的功能分组匹配度有限。最弱的是 Flask（ARI=-0.01）和 Rich（ARI=0.06）。

---

## 四、已识别的未解决问题

### 问题 1: Flask 负 modularity (-0.037)
- Flask 是小 repo（83 节点），30% 被识别为 infra
- infra 比例过高挤压了 cone 的有效节点数
- 可能原因：`classify_file` 对 Flask 内部模块过度分类为 config/utils

### 问题 2: FastAPI 362 文件 mega-cone
- Louvain 在 `resolution=1.0` 对 FastAPI 产生 347 文件社区
- 递归拆分已被证明无效（V3a）
- 可能方向：提高 resolution 仅对大 repo，或接受大社区

### 问题 3: Scrapy 99 文件最大 cone
- 类似 FastAPI 的 mega-cone 问题，但程度较轻

### ~~问题 4: oh-my-openagent 是 TypeScript 项目~~ ✅ 已解决
- 已从 test_repos/ 删除，不再作为测试仓库

### ~~问题 5: 死代码（11 个函数）未清理~~ ✅ 已解决
- T-01 已删除全部 11 个死函数和 12 个常量
- feature_cone.py 从 1288 行精简至 ~391 行

### ~~问题 6: 未充分利用的现有资源~~ ✅ 已解决
- `directory_affinity_score` — T-05 集成为 _merge_small_communities 的 tiebreaker
- `is_reexport_facade` — T-03 集成为 _identify_infrastructure Criterion 3
- `scoring_harness` — 作为 AutoResearch guard 在每次迭代中使用

### 问题 7: Rich D3 InfraAccuracy (6.43/15) 是最低维度分
- 5-repo 中 Rich 的 D3 最低，拉低了 Rich 总分（74.73，5-repo 最低）
- 根因：ground truth 认为 "console" 不是 infra，但算法因跨社区导入将 console.py 归为 infra

### 问题 8: FastAPI D2 Distribution (4.39/15) 是最低维度分
- Gini 系数 0.71，cone 大小分布极不均匀（362 文件 mega-cone vs 几个小 cone）
- 与问题 2 (mega-cone) 相关联

### 问题 9: security 类别太宽泛，不宜直接加入 infra
- `classify_file("security")` 匹配 `fastapi/security/` 等功能目录
- 如要利用，需更精细的判断（如 security + 非 feature-bearing 目录结构）

---

## 五、当前代码结构

### feature_cone.py（~395 行，无死代码）

| 函数 | 用途 |
|------|------|
| `_louvain_communities` | Louvain 社区检测（weight=weight, resolution=1.0, seed=42）|
| `_merge_small_communities` | 合并 <3 文件社区（composite scoring: edges + dir_affinity）|
| `_identify_infrastructure` | 4 条件识别 infra（semantic + stems + facade + cross-community）|
| `extract_feature_cones` | 主入口 |
| `_parent_dir` | 路径工具 |
| `_separate_testing_files` | 测试文件分离 |
| `_generate_cone_name` | 生成 cone 名称（4 级 fallback）|
| `_semantic_suffix` | 语义后缀辅助 |
| `_rename_cones` | 重命名 + 去重 |

### 外部依赖
- `src/graph/__init__.py` 导出: `FeatureCone`, `extract_feature_cones`
- `src/graph/grouper.py` 导入: `extract_feature_cones`, `FeatureCone`
- `src/server.py` 导入: `extract_feature_cones`, `FeatureCone`

### FeatureCone 数据类型
- `exclusive_files: tuple[str, ...]` — 不可变
- `shared_deps: tuple[str, ...]` — 不可变
- `frozen=True` — 实例级不可变

---

## 六、AutoResearch 优化方法论

基于 Karpathy autoresearch 的核心原则，后续优化应遵循：

1. **一次一个原子变化** — 修改一个函数/参数，不混合多个改动
2. **机械化验证** — 每次改动后运行指标验证（modularity, cohesion, pytest）
3. **自动回滚** — 如果指标未改善或测试失败，`git reset` 回到改动前
4. **Git 是记忆** — 每个实验用 `experiment:` commit message，读 `git log` 避免重复
5. **简单优先** — 同等效果下选择更简单的实现
6. **记录所有尝试** — 更新本文档，包括废弃的方向
