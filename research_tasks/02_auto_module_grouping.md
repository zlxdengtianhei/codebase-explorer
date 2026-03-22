# 研究任务 02：代码自动模块分组算法

## 研究目标

给定一个代码库的依赖图谱（函数调用关系、import 关系、类继承关系），如何**自动地**将代码划分成有意义的功能模块组？这是整个渐进式文档生成的关键一步——决定了文档的层级结构。

### 核心问题

1. 图论中有哪些**社区检测/聚类算法**适合代码依赖图？
2. 已有哪些**代码特定的模块分组方法**？（不只是通用图算法）
3. 如何判断分组结果的**质量**（是否与人类理解一致）？
4. 如何处理**跨层级的关系**（一个函数被多个模块依赖）？
5. **目录结构**是否可以作为模块分组的强信号？

## 搜索关键词

### 第一轮：图聚类算法

- `graph community detection algorithm code dependency clustering`
- `Louvain algorithm modularity code structure detection`
- `spectral clustering software architecture recovery`
- `code module boundary detection algorithm`
- `software architecture recovery from source code 2024 2025`

### 第二轮：代码特定方法

- `software clustering techniques dependency graph survey`
- `automatic software modularization architecture extraction`
- `code community detection call graph module identification`
- `architectural pattern recognition source code static analysis`
- `bunch software clustering tool`

### 第三轮：实际实现

- `networkx community detection Louvain Python tutorial`
- `rustworkx graph partitioning clustering`
- `code module grouping heuristic directory structure imports`
- `hierarchical clustering dendrogram code architecture multi-level`
- `graph partitioning balanced code analysis`

### 第四轮：结合 LLM

- `LLM code architecture understanding module identification`
- `AI-assisted software architecture recovery`
- `LLM + static analysis code structure understanding hybrid`

## 深入阅读方向

### 必须阅读的资源

1. **Software Architecture Recovery 综述论文**
   - 搜索 "software architecture recovery survey" 获取最新综述
   - 关注方法分类：依赖分析、聚类、模式匹配

2. **Bunch 工具**（经典的软件聚类工具）
   - https://github.com/ArchitectureMining/Bunch
   - 评估其算法是否可以提取出来使用

3. **NetworkX 社区检测 API**
   - https://networkx.org/documentation/stable/reference/algorithms/community.html
   - 重点关注：`louvain_communities`, `label_propagation_communities`, `girvan_newman`
   - 这些能直接用在代码依赖图上

4. **ARC (Architecture Recovery by Clustering)**
   - 学术工作中的经典方法，搜索相关论文

5. **目录结构作为模块信号**
   - 多数项目的目录结构已经反映了模块划分
   - 研究：如何将目录结构与依赖图结合

### 可选深入

- `igraph` Python 库的社区检测能力
- `scikit-network` 图聚类
- WASM-based 代码地图可视化（如 `code-city`、`Gource`）

## 产出要求

### 保存位置

`results/02_auto_module_grouping.md`

### 必须包含的内容

1. **算法分类表格**：

| 算法 | 类型 | 适合代码图？ | 时间复杂度 | 可用库 | 需要参数？ |
| ---- | ---- | ------------ | ---------- | ------ | ---------- |

2. **推荐的分层方案**：
   - Level 0: 目录结构 → 初始分组
   - Level 1: 算法 X → 细化分组
   - Level 2: LLM → 语义验证
   - 详细说明每一层的输入/输出

3. **参考代码**：
   - 使用 NetworkX 对代码依赖图执行社区检测的完整示例代码
   - 输入：graph-sitter 产出的依赖图
   - 输出：模块分组结果

4. **评估标准**：
   - 如何衡量分组质量？
   - 人工验证 checklist

5. **跨层级处理策略**：
   - "工具类"函数（被多个模块依赖）如何归类？
   - 循环依赖如何处理？

## 质量标准

- 至少比较 5 种不同的聚类/分组方法
- 必须有一个可运行的代码示例
- 需要讨论"目录结构 vs 依赖图"哪个更可靠
- 需要验证所推荐算法的 Python 可用性（有库可调用）
