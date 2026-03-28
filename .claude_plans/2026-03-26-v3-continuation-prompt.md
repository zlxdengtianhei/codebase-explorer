> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 阅读本文件了解任务背景和约束
> 2. 阅读 `/Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/04_feature_cone_optimization_v3.md` 了解历史优化记录
> 3. 阅读愿景文档 `/Users/lexuanzhang/code/codebase-explorer/optimization_prompts/organized/00_vision_and_requirements.md`
> 4. 按照本文件的工作流程继续执行

---

# Feature Cone 算法持续优化 — 执行 Prompt

## 你的角色

你是**主编排者（Orchestrator）**。你的职责是：
- 阅读代码、分析问题、设计改动方案
- 将**所有代码修改**委派给 Sub-agent（`general-purpose` 类型的 Task 工具）
- 验证 Sub-agent 的产出
- 决定 keep/discard
- 更新优化记录文档

**你绝不自己写代码、修改文件、运行测试。全部通过 Sub-agent 完成。**

## 必须先阅读的文件

在任何操作之前，先读取以下文件建立完整的上下文：

1. **优化历史** — `/Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/04_feature_cone_optimization_v3.md`
   - 包含已尝试的方法、废弃的方向、当前指标、已知问题
   - **避免重复已失败的方向**（递归 Louvain 拆分、合并 size cap、BFS 参数调优）

2. **愿景文档** — `/Users/lexuanzhang/code/codebase-explorer/optimization_prompts/organized/00_vision_and_requirements.md`
   - 核心原则：功能优先，层级内嵌
   - 最终用户是 AI Agent（vibe coding）
   - SCC/DAG/Louvain 三种算法各司其职

3. **V2 代码分析架构** — `/Users/lexuanzhang/code/codebase-explorer/optimization_prompts/results/02a_code_analysis_v2.md`
   - 加权图构建规则、SCC/DAG/Feature Cone 的设计
   - 5 个 JSON 输出文件的 schema

4. **当前算法代码** — `src/graph/feature_cone.py`
   - 关注 `extract_feature_cones` 及其调用的函数
   - 注意文件中有大量 V1 遗留死代码（见优化历史第五节）

5. **语义分析工具** — `src/graph/semantic_hints.py`
   - `classify_file` — 返回 testing/models/api/cli/config/utils/exceptions/unknown
   - `directory_affinity_score` — 返回 0.0-1.0 的目录亲和度（**当前未使用**）
   - `is_reexport_facade` — 检测 __init__.py 是否为 re-export facade（**Louvain 路径未使用**）

## 已完成的工作（不需要重复）

1. oh-my-openagent 已克隆到 `test_repos/oh-my-openagent`（但它是 TypeScript 项目，parser 不支持）
2. BFS-from-roots 已被 Louvain 替代（`extract_feature_cones` 已重写）
3. `_identify_infrastructure` 已简化为使用 `classify_file`
4. 测试中 BFS 参数的期望值已更新
5. `_split_large_community` 和 `_group_overflow` 已删除
6. 795 个测试全部通过

## 立即需要做的（Phase 1: 清理）

### 任务 1: 删除死代码

feature_cone.py 中有 11 个函数不再被 `extract_feature_cones` 调用（详见优化历史第五节）。需要：

1. 删除这 11 个函数及其关联的常量（`SHARED_THRESHOLD_MIN`, `FANIN_INFRASTRUCTURE_RATIO`, `EDGE_AFFINITY`, `AFFINITY_DECAY`, `AFFINITY_CUTOFF`, `FACADE_PENALTY`, `CALL_INHERIT_RATIO_THRESHOLD`, `SPARSE_DENSITY_THRESHOLD`, `BOOSTED_IMPORT_AFFINITY`, `SPARSE_AFFINITY_CUTOFF`, `MAX_MERGED_CONE_SIZE`）
2. 更新 `src/graph/__init__.py` — 移除 `find_feature_roots` 和 `assign_scc_to_cone` 的导出
3. 删除测试中直接测试死代码的用例（如 `TestAffinityBfs`, `TestDetectHubNodes`, `TestRebalanceCones` 等）
4. 更新 `from ... import` 语句
5. 确保 `pytest tests/ -q` 全部通过
6. 目标：feature_cone.py < 500 行

**委派方式**：启动一个 `general-purpose` Sub-agent，提供完整的死代码列表和依赖关系。

### 任务 2: 替换 oh-my-openagent

oh-my-openagent 是 TypeScript 项目，parser 不支持。需要：
- 找一个中等大小（100-500 个 Python 文件）的开源 Python 项目作为第 6 个测试仓库
- 克隆到 `test_repos/` 下
- 建议：`httpx`, `pydantic`, `typer`, `textual` 等

## 持续优化（Phase 2: AutoResearch 循环）

完成清理后，按 AutoResearch 方法持续优化：

### 每次迭代的流程

```
1. 选择一个待改善的指标（参考优化历史第四节的"未解决问题"）
2. 设计一个原子改动方案
3. 委派 Sub-agent 执行改动
4. 委派 Sub-agent 运行验证：
   - pytest tests/ -q（全部通过？）
   - 5 repo 的 modularity, cohesion, cone_count, infra_ratio
5. 对比改动前后的指标
6. KEEP（指标改善 + 测试通过）或 DISCARD（git reset）
7. 更新 04_feature_cone_optimization_v3.md 记录此次实验
```

### 验证命令

Sub-agent 应运行以下验证脚本（使用 `.venv/bin/python`）：

```python
import networkx as nx
from networkx.algorithms.community import modularity
from src.parser.codebase import parse_project
from src.graph.dependency import build_weighted_dependency_graph
from src.graph.feature_cone import extract_feature_cones

repos = ['test_repos/celery', 'test_repos/fastapi', 'test_repos/flask', 'test_repos/rich', 'test_repos/scrapy']
for repo in repos:
    snap = parse_project(repo)
    dag = build_weighted_dependency_graph(snap).graph
    udag = dag.to_undirected()
    cones, infra = extract_feature_cones(dag, snap)
    # ... compute modularity, cohesion, print results
```

### 当前基线（每次迭代的对比基准）

| Repo | Modularity | Cohesion | Cones | Infra% |
|------|-----------|----------|-------|--------|
| celery | +0.191 | 28.1% | 26 | 13% |
| fastapi | +0.219 | 41.6% | 23 | 1% |
| flask | -0.037 | 45.5% | 10 | 30% |
| rich | +0.091 | 33.7% | 22 | 12% |
| scrapy | +0.395 | 39.6% | 29 | 11% |

### KEEP/DISCARD 规则

- **KEEP if**: 平均 modularity 不下降 AND 平均 cohesion 不下降 AND pytest 全部通过
- **DISCARD if**: 任何 repo 的 modularity 下降 >0.05 OR cohesion 下降 >5% OR 测试失败
- **同等效果选更简单的实现**

### 候选优化方向（按优先级排序）

1. **Flask infra 过高（30%）** — 检查 classify_file 对 Flask 内部模块的分类是否合理
2. **FastAPI mega-cone（362 文件）** — 考虑仅对 FastAPI 使用更高 resolution（不要用递归拆分，已证明无效）
3. **利用 directory_affinity_score** — 可以在 _merge_small_communities 中用作 tiebreaker
4. **改善 cone 命名** — 很多 cone 以 "testing-" 开头，说明测试分离可能不够干净

### 已知禁区（不要尝试）

- 递归 Louvain 拆分 — 产生大量碎片，合并时重建 mega-cone（V3a 已证明无效）
- 合并 size cap + overflow 分组 — 产生人工 chunk（V3b 已证明无效）
- BFS-from-roots 回退 — 根本策略缺陷，不可修复
- 同时修改多个函数 — 违反 AutoResearch 原子变化原则

## 强制规则

1. **你（Orchestrator）不修改任何文件** — 所有文件修改通过 Sub-agent 的 Task 工具完成
2. **每次迭代一个原子变化** — 不混合多个改动
3. **每次迭代更新 v3 文档** — 在 `04_feature_cone_optimization_v3.md` 中记录实验和结果
4. **删除死代码** — 每次迭代结束时检查是否有新产生的死代码，立即清理
5. **给 Sub-agent 提供完整 context** — 包括：修改哪个文件、修改哪个函数、期望的行为变化、验证命令
6. **使用 `.venv/bin/python`** — 系统 python3 是 3.9，项目需要 3.13

## Sub-agent Prompt 模板

委派代码修改时，使用以下结构：

```
你需要修改 {文件路径}。

## 背景
{为什么要做这个改动，解决什么问题}

## 具体要求
1. {精确的修改描述}
2. {精确的修改描述}

## 当前代码状态
{相关函数的当前实现概述}

## 验证
修改完成后运行：
1. .venv/bin/python -m pytest tests/ -x -q --tb=short
2. {验证脚本}

## 约束
- 不要修改 {列出不应修改的文件}
- 不要新建文件
- 保持代码简单
```
