# V4 架构检测重设计 — Brainstorm 记录与方案

> 本文档记录 2026-03-26 的深度讨论过程，涵盖 MCP 算法、输出格式、Skill 执行流程三个层面的问题诊断与优化方案。
> 后续 Agent 在实施前**必须先阅读本文档 + V3 记录 (`04_feature_cone_optimization_v3.md`)**。

---

## 一、讨论背景

### 触发点

使用 codebase-explorer Skill 对自身代码库生成架构文档，结果严重偏离愿景：

1. MCP `analyze_codebase` 索引了 12,907 个文件（含 `.venv/` 和 `test_repos/`），产出 247 个 feature cone，最大 cone 包含 1,394 个 site-packages 文件
2. `get_feature_cones()` 返回 90K 字符超出上下文限制，`get_dependency_graph()` 返回 11.5MB 完全不可用
3. MCP 工具不可用后，Skill 的 6 阶段流程完全断裂，退化为手动 sub-agent 分析
4. 最终产出按源码目录组织（parser/, graph/, doc/），而非愿景要求的按功能组织
5. 没有 DETAIL 层、没有 @unit 标记、没有 SNIPPET、没有 doc-manifest.json

### 核心愿景回顾（来自 `00_vision_and_requirements.md`）

> **从代码的依赖关系中自动提取功能结构，用确定性分析划定骨架，用 LLM 填充语义，产出一套"功能优先、层级内嵌"的渐进式架构文档——让 AI Agent 在 vibe coding 中能从功能需求直接定位到需要修改的代码。**

关键设计原则：
- **功能优先，层级内嵌** — 顶层按功能分类，每个功能内保持依赖链层级
- **确定性分析 vs 语义理解 的职责分离** — MCP 做纯算法，Agent 做语义理解
- **架构信息是代码计算的常量** — 不是 Agent 发现的
- **每步持久化，支持断点恢复**
- **动态预算，按需分配**

---

## 二、问题诊断（三层）

### 问题 A：MCP 算法层 — 噪声淹没信号

| 文件 | 大小 | 问题 |
|------|------|------|
| `01_structure.json` | 9.6MB | 含 .venv/ 全部文件 |
| `02_dag.json` | 8.9MB | 含 .venv/ 全部依赖边 |
| `03_feature_cones.json` | 1.2MB | 247 个 cone，最大 1,394 文件 |

**根因 1：** `analyze_codebase` 没有目录排除机制。
**根因 2：** MCP 查询工具没有摘要/分页模式——要么全量 dump，要么查单个 cone。

### 问题 B：Skill 执行层 — 管线断裂后无降级路径

当 MCP 工具返回超大结果后，整个 Skill 的 6 阶段流程被放弃：
- 没有执行 Phase 2（验证 Agent）
- 没有执行 Phase 3（DETAIL Agent）
- 没有执行 Phase 4（INDEX Agent）
- 没有执行 Phase 5（语义重组）
- 产出的文档是 API reference 风格，不是架构文档

### 问题 C：算法质量 — Feature Cone 与人类直觉不匹配

V3 的 ARI（Adjusted Rand Index）仅 0.00-0.29，意味着算法分组与 ground truth 匹配度很差：

| Repo | ARI | NMI | 问题 |
|------|-----|-----|------|
| Flask | -0.01 | 0.225 | 比随机更差 |
| Rich | 0.06 | 0.365 | 几乎随机 |
| FastAPI | 0.155 | 0.496 | 差 |
| Scrapy | 0.187 | 0.520 | 差 |
| Celery | 0.286 | 0.582 | 最好但仍然差 |

---

## 三、6 路并行调研

启动了 6 个研究 Agent 并行调研，覆盖以下方向：

### 调研 1：软件架构恢复的学术方法

**关键发现：**
- **SARIF (FSE 2023)** 是当前最优方法：融合 结构依赖 + 语义相似度 + 目录结构 三个信号，比之前最佳方法提升 36.1%
- SARIF 的 "directory filtering" 算法能自动检测目录是按功能组织还是按层组织（MVC），并据此调权
- **Leiden 算法**支持多层图（multiplex），但 **GPL-3.0 许可证与项目 MIT 许可证不兼容**
- **DRH (Design Rule Hierarchy)** 可原则化地识别基础设施，替代当前的启发式规则
- **Infomap** 基于随机游走，能捕捉 Louvain 捕捉不到的信息流模式
- **共识聚类**（Consensus Clustering）：跑多个算法，取共识，最鲁棒但最复杂

**参考论文：**
- SARIF: Software Architecture Recovery with Information Fusion (FSE 2023)
- From Louvain to Leiden: Guaranteeing Well-Connected Communities (Nature, 2019)
- Decomposing God Header File via Multi-View Graph Clustering (2024)
- ACDC: Algorithm for Comprehension-Driven Clustering

### 调研 2：5 个 Test Repo 的 Ground Truth 分析

**关键发现：**

| Repo | 实际核心文件数 | 目录=架构？ | 难度 |
|------|--------------|------------|------|
| Scrapy | 178 | **完美 1:1** | 最容易 |
| Celery | 161 | 非常好（`app/` 有混合） | 较易 |
| FastAPI | **48**（非 1,118） | 子目录完美，根目录扁平 | 中等 |
| Flask | 24 | 好但很平 | 较难 |
| Rich | 100 | **只有一个目录** | 最难 |

**核心洞察：**
- **5 个 repo 全部按功能组织，不是按层（MVC）** — MVP 跨层问题在这些 Python 库中不存在
- **FastAPI 的 362 文件 mega-cone 是因为索引了 `docs_src/`（454 个示例文件）和 `tests/`（581 个文件）** — 核心库只有 48 个文件
- Flask 30% infra 比例合理（微框架本质上大量代码都是基础设施）
- 现有 `CLUSTER_GROUND_TRUTH`（216 个标注文件）质量高，与各 repo 官方文档一致
- Ground truth 需要扩展覆盖率

### 调研 3：项目内现有资源

**关键发现：** 原始设计文档 `01_code_analysis_architecture.md` 中提出了 3 个方向，在 V3 中**从未实现**：

1. **SCC 预处理** — 把互相导入的文件凝聚为超节点后再聚类（有详细伪代码）
2. **DAG 层级分析** — 用深度分层建立纵向层次
3. **目录优先 + 图修正** — 目录结构作为主信号，Louvain 仅用于扁平目录的 fallback

另外发现 `research_tasks/02_auto_module_grouping.md` 中调研过 Bunch、谱聚类、标签传播等替代算法。

### 调研 4：文件树 vs 依赖图融合策略

**关键发现：**

提出 **Directory Informativeness Score (DIS)** 指标——自动检测目录结构对分组有多大帮助：
- 高 DIS（Scrapy ~0.7）→ 目录边权重高，Louvain 倾向保持同目录文件在一起
- 低 DIS（Rich ~0.15）→ 目录边权重趋近 0，退化为纯依赖聚类
- Mega-directory（>50 文件）自动跳过，避免 O(n²) 虚假边

三个方案：
- **A) 增强图**（推荐先试）— 一个新函数 + 一行改动
- **B) 双聚类 + NMI 选择** — 更原则化但更复杂
- **C) 共识聚类** — 最鲁棒但 O(n²) + 三次 Louvain

### 调研 5：leidenalg 兼容性

**关键发现：** leidenalg 是 **GPL-3.0**，与项目 MIT 许可证不兼容。

替代方案评估：

| 方案 | 许可证 | 平台 | 多层图 | 结论 |
|------|--------|------|--------|------|
| leidenalg | GPL-3.0 | 全平台 | 原生 | **排除** |
| graspologic | MIT | 无 Apple Silicon | 不支持 | 排除 |
| **NetworkX 内置 Louvain + 增强图** | BSD | 纯 Python | 通过图增强模拟 | **采用** |

额外收获：可以删掉 `python-louvain` 依赖，NetworkX 3.x 内置了 Louvain。

### 调研 6：当前语言支持

当前支持 Python、TypeScript、JavaScript 三种语言。算法层面的改动（图增强、SCC 预处理）不涉及解析层，不会影响语言支持。

---

## 四、讨论中的关键决策

### 决策 1：优先级 — 先 MCP 算法，再 Skill

MCP 输出是 Skill 的输入，输入质量差导致后面全部崩盘。必须先让算法产出正确的功能分组。

### 决策 2：评估体系 — 砍掉 D1-D7，只保留 ARI/NMI

原有 9 维评分体系（D1 StructuralInvariant, D2 Distribution, D3 InfraAccuracy, D4 TestSeparation, D5 DirCoherence, D6 DepIntegrity, D7 NamingQuality, D8 ClusterARI, D9 LLM-as-Judge）中，D1-D7 是代理指标，优化它们不等于优化"分组是否正确"。**唯一有意义的指标是算法分组与 ground truth 的匹配程度。**

### 决策 3：Skill 阶段 — 删除 Phase 2，保持其余

Phase 2（验证 Agent 检查 MCP 的 feature cone 分组）在当前形态下无效——MCP 输出的 JSON 没有语义内容，Agent 不读代码无法判断分组是否正确。**验证推迟到 DETAIL + INDEX 生成后再做最终调整。**

### 决策 4：算法 vs LLM — 算法必须给出准确骨架

算法产出的功能分组必须作为最终骨架。LLM Agent 的作用是填充语义内容（写文档），而不是纠正算法错误。这与愿景一致：**"架构信息是代码计算的常量，不是 Agent 发现的"**。

### 决策 5：Leiden 排除，保持 NetworkX Louvain

GPL 许可证不兼容。通过增强图（注入目录共位边）在标准 Louvain 上实现类似多层图的效果。可以顺便删掉 `python-louvain` 依赖。

### 决策 6：Ground Truth 需要先扩展

当前只有 216 个文件有标注。在开始算法实验之前，需要为 5 个 repo 补全 ground truth，确保每次改动都有明确的对/错判断。

---

## 五、最终优化方案

### 5.1 MCP 算法改进

#### 变更概览

```
V3 (当前):
  依赖图(import=1,call=2,inherit=3) → Louvain(resolution=1.0) → 合并小社区 → 识别 infra → 命名

V4 (目标):
  智能范围过滤 → 依赖图 + 目录共位边(DIS 自适应权重) → SCC 凝聚
  → NetworkX Louvain → 合并小社区 → 识别 infra → 命名
```

#### 改动 1：智能范围过滤（预期影响：高）

**问题：** `analyze_codebase` 没有排除机制，索引了 .venv/ 等无关目录。

**方案：**
- 自动排除：`.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `.tox/`, `.mypy_cache/`
- 增加 `exclude_paths: list[str]` 参数，允许用户指定额外排除
- 预扫描报告："发现 X 文件分布在 Y 目录"，供 Skill 决定 scope
- 检测 `docs_src/`、`examples/`、`tests/` 等非核心目录，标记为 non-core

**预期效果：** FastAPI 从 1,118 → 48 文件，mega-cone 问题大概率消失。所有 repo 的信噪比大幅提升。

#### 改动 2：目录共位边注入（预期影响：中高）

**问题：** 目录结构是开发者对功能的天然分组，但当前 Louvain 完全看不到这个信号（仅在合并小社区时做 tiebreaker）。

**方案：** 在构建 Louvain 输入图时，为同目录文件添加共位边：

```python
def build_augmented_graph(dag: nx.DiGraph) -> nx.DiGraph:
    augmented = dag.copy()
    dis = directory_informativeness_score(dag)  # 0.0-1.0
    dir_weight = dis * 1.5  # 自适应权重

    if dir_weight < 0.01:
        return augmented  # 扁平目录，跳过

    for d, files in dir_groups.items():
        if len(files) < 2 or len(files) > 50:  # mega-dir 跳过
            continue
        for fi, fj in combinations(files, 2):
            # 加权共位边（不覆盖已有依赖边）
            boost = dir_weight * directory_affinity_score(fi, fj)
            if augmented.has_edge(fi, fj):
                augmented[fi][fj]["weight"] += boost
            else:
                augmented.add_edge(fi, fj, weight=boost, edge_types=["directory"])
    return augmented
```

**DIS (Directory Informativeness Score)** 的计算逻辑：
- 统计图中同目录内边数 vs 跨目录边数
- 校正随机期望值（大目录天然有更多同目录边）
- 高 DIS = 目录结构有信息量（如 Scrapy），低 DIS = 目录结构无信息量（如 Rich）

**三种场景下的行为：**

| 场景 | DIS | 效果 |
|------|-----|------|
| Scrapy（目录=架构） | ~0.7 | 目录边强烈拉同目录文件在一起 |
| FastAPI（子目录好，根目录扁平） | ~0.5 | 子目录内有加成，根目录文件靠依赖聚类 |
| Rich（单一扁平目录） | ~0.15 | 几乎无目录边（mega-dir 跳过），退化为纯依赖聚类 |

#### 改动 3：SCC 预处理（预期影响：中）

**问题：** 互相导入的文件（循环依赖）在功能上不可分割，但 Louvain 可能把它们拆到不同社区。

**方案：** Louvain 之前，用 `nx.strongly_connected_components()` 找到所有 SCC，将 >1 个节点的 SCC 凝聚为超节点。原始设计 `01_code_analysis_architecture.md` 中有详细伪代码。

**预期效果：** Flask 的 `app.py ↔ ctx.py ↔ globals.py` 环会被视为一个不可分割单元。

#### 改动 4：删除 python-louvain，统一 NetworkX（确定性改进）

**方案：** 删除 `python-louvain>=0.16` 依赖，删除 `grouper.py` 中的 `community_louvain` import 和 `_USE_COMMUNITY_LOUVAIN` 标志。统一使用 `networkx.community.louvain_communities()`。

#### 改动 5：删除 D1-D7 评分，只保留 ARI/NMI（确定性改进）

**方案：** 重写 `scoring_harness.py`，只保留 ARI 和 NMI 对 `CLUSTER_GROUND_TRUTH` 的计算。删除 D1-D7 的全部代码。

#### 改动 6：扩展 Ground Truth（基础设施）

**方案：** 基于调研 2 的结果，为 5 个 repo 补全 `CLUSTER_GROUND_TRUTH`：
- Scrapy：补充 `pqueues.py`, `squeues.py`, `shell.py` 等
- Celery：补充 `concurrency/`, `contrib/`, `loaders/` 等
- FastAPI：补充 `background.py`, `concurrency.py`, `cli.py` 等
- Rich：补充 `_unicode_data/`, 平台相关文件等
- Flask：已基本完整

### 5.2 MCP 输出格式优化

#### get_feature_cones() — 分级输出

**默认（summary 模式）：** 主 Agent 使用
```json
{
  "cones": [
    {"id": "worker", "name": "Worker Process", "file_count": 11,
     "token_count": 8500, "depends_on": ["transport", "task-execution"]}
  ],
  "infrastructure": {"file_count": 20, "token_count": 15000}
}
```

**详情模式（传入 cone_id）：** 子 Agent 写 DETAIL 时使用
```json
{
  "id": "worker", "name": "Worker Process",
  "exclusive_files": ["celery/worker/worker.py", ...],
  "shared_deps": ["celery/_state.py", ...],
  "layers_within_cone": [["worker.py"], ["strategy.py", "request.py"]],
  "entry_point": "celery/worker/worker.py"
}
```

#### get_dependency_graph() — 默认 cone 级别

**默认返回 cone 间依赖**（而非文件间依赖），可直接用于 Mermaid 图：
```
graph TD
  worker --> transport
  worker --> task-execution
  beat --> task-execution
```

传入 `scope="file"` 时才返回文件级别。

#### analyze_codebase — 增加排除参数

新增 `exclude_paths: list[str] | None` 参数。自动排除的默认列表可通过此参数覆盖或扩展。

### 5.3 Skill 流程调整

#### 删除 Phase 2（验证 Agent）

MCP 输出的 JSON 没有语义内容，Agent 不读代码无法判断分组正确性。验证推迟到 Phase 5（语义重组）。

#### Phase 1 后增加 "scope assessment"

检测到非核心代码（`docs_src/`, `examples/`, `scripts/`）时：
- 核心 cone → 完整 Phase 3-5 处理
- 非核心 cone → 只生成 OVERVIEW，标注 "由于该项被判断为非关键项目代码实现，仅给出 overview"

#### Phase 3-6 保持不变

6 阶段完整性是核心价值（尤其 Phase 5 语义重组）。问题在于 MCP 输入质量和 Skill 执行纪律，不在于流程设计。

---

## 六、实施优先级

| 优先级 | 任务 | 依赖 | 预期 ARI 影响 |
|--------|------|------|-------------|
| P0 | 扩展 5 个 repo 的 ground truth | 无 | 基础设施 |
| P0 | 删除 D1-D7 评分，简化为 ARI/NMI | 无 | 聚焦 |
| P1 | 智能范围过滤（exclude .venv/ 等） | 无 | 高（消除噪声） |
| P1 | 删除 python-louvain，统一 NetworkX | 无 | 代码简化 |
| P2 | 目录共位边 + DIS 自适应权重 | P1 | 中高 |
| P2 | SCC 预处理 | P1 | 中 |
| P3 | MCP 输出格式（summary/detail 分级） | P1 | Skill 可用性 |
| P3 | analyze_codebase exclude_paths 参数 | P1 | 用户体验 |
| P4 | Skill 删除 Phase 2 + scope assessment | P3 | 端到端流程 |

---

## 七、已排除的方向

| 方向 | 排除原因 |
|------|---------|
| Leiden 替换 Louvain | GPL-3.0 与 MIT 不兼容 |
| graspologic (MIT Leiden) | 无 Apple Silicon wheel，无 Python 3.13 支持 |
| D1-D7 代理指标优化 | 优化代理指标不等于优化"分组是否正确" |
| Phase 2 验证 Agent | MCP 输出无语义内容，Agent 无法判断正确性 |
| 递归 Louvain 拆分 (V3a) | 产生碎片社区，已在 V3 中废弃 |
| 强边权重放大 | V3 实验证明在 Flask/Rich 上回归 |
| security/middleware 加入 infra | FastAPI security/ 被错误分类为 infra |

---

## 八、未来可探索方向（不在 V4 范围内）

1. **SARIF 式三信号融合** — 加入语义相似度（标识符 TF-IDF）作为第三信号。需要扩展 parser 暴露标识符词汇表。
2. **DRH 基础设施检测** — 用 Design Rule Hierarchy 替代当前的启发式 `_identify_infrastructure`。
3. **Infomap 作为替代/补充** — 基于随机游走的社区检测，可能更好地捕捉信息流模式。
4. **共识聚类** — 跑多个算法取共识，最鲁棒但最复杂。
5. **SARIF 的 directory filtering** — 自动检测目录是按功能组织还是按层组织（MVC），动态调整目录信号权重。
6. **自适应 resolution 参数** — 根据图规模自动调整 Louvain 的 resolution（小 repo 用低 resolution，大 repo 用高 resolution）。

---

## 九、关键参考资料

### 学术论文
- SARIF: Software Architecture Recovery with Information Fusion (FSE 2023)
- From Louvain to Leiden: Guaranteeing Well-Connected Communities (Nature, 2019)
- Decomposing God Header File via Multi-View Graph Clustering (2024)
- ACDC: Algorithm for Comprehension-Driven Clustering
- ArchDRH: Architecture Recovery Based on Design Rule Hierarchy

### 项目内文档
- `optimization_prompts/organized/00_vision_and_requirements.md` — 愿景与需求
- `optimization_prompts/organized/01_code_analysis_architecture.md` — 原始设计（含未实现的 SCC + DAG + 目录优先方案）
- `optimization_prompts/results/04_feature_cone_optimization_v3.md` — V3 优化记录
- `tests/ground_truth.py` — 当前 ground truth（216 文件标注）
- `research_tasks/02_auto_module_grouping.md` — 模块分组算法调研

### 工具与库
- NetworkX `louvain_communities` — 内置 Louvain，BSD 许可证
- leidenalg — 优秀但 GPL-3.0 不兼容（已排除）
- `directory_affinity_score` (semantic_hints.py) — 已有但未充分利用
- `is_reexport_facade` (semantic_hints.py) — 已集成到 infra 识别

---

## 十、效果预期的诚实评估

| 改动 | 预期 ARI 变化 | 信心度 | 理由 |
|------|-------------|--------|------|
| 范围过滤 | 大幅提升 | 高 | 消除 90%+ 噪声文件 |
| 目录共位边 + DIS | 4/5 repo 提升 | 中高 | 4 个 repo 目录结构是强信号 |
| SCC 预处理 | Flask 改善 | 中 | 仅在有循环依赖时有效 |
| Louvain → Leiden | 微小提升 | 中 | 但 GPL 排除了这个选项 |
| 删 D1-D7 | 不直接提升 ARI | 确定 | 消除干扰，聚焦真正指标 |

**最大的不确定性：** 目录共位边的权重调参。DIS × 1.5 是初始建议，需要在 ground truth 上实验。权重过高会让所有同目录文件强制在一起（即使依赖关系说应该分开），权重过低则等于没加。
