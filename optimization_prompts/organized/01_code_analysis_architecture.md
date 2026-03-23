# 代码获取与架构优化

> 主题：通过代码分析获取代码库的架构图、依赖关系等方面的算法与策略优化。

---

## 1. 当前 graph-sitter 提供的数据

graph-sitter 通过 `Codebase("./")` 一行代码加载整个项目，提供三种图：

| 关系类型                     | 含义                                                 | 功能关联强度                 |
| ---------------------------- | ---------------------------------------------------- | ---------------------------- |
| 函数调用图 (Call Graph)      | `函数A.function_calls → [函数B, 函数C]`，跨文件      | **最强** — A 运行依赖 B      |
| 类继承图 (Inheritance Graph) | `类A.base_classes → [类B]`，跨文件                   | **很强** — A 的行为由 B 定义 |
| 模块依赖图 (Import Graph)    | `file_A.imports → [file_B, ...]`，resolve 到实际文件 | **强** — 至少有一个引用      |

**当前问题**：`dependency.py` 只用了文件级 import 关系来建图，**函数调用图和继承图被完全丢弃**。

---

## 2. 构建加权多关系图

将三层信号合成一个加权有向图：

```python
G = nx.DiGraph()

# 边的来源1：文件间 import（权重=1）
for file in snapshot.files:
    for target in file.import_sources:
        G.add_edge(file.filepath, target, weight=1, type="import")

# 边的来源2：跨文件函数调用（权重=2，因为比 import 更紧密）
for func in snapshot.functions:
    for called_func_name in func.calls:
        callee_file = find_file_of_function(called_func_name, snapshot)
        if callee_file and callee_file != func.filepath:
            G.add_edge(func.filepath, callee_file, weight=2, type="call")

# 边的来源3：类继承（权重=3，最紧密的关联）
for cls in snapshot.classes:
    for base in cls.base_classes:
        base_file = find_file_of_class(base, snapshot)
        if base_file and base_file != cls.filepath:
            G.add_edge(cls.filepath, base_file, weight=3, type="inheritance")
```

**效果对比**（以 Flask 为例）：

- 当前实现：`app.py → sansio/app.py` 总边权 = 1（只有 import）
- 改进后：总边权 = 1 + 3 + 2 = 6（import + 继承 + 函数调用叠加）
- → Louvain 更不容易把 app.py 和 sansio/ 分开

---

## 3. 三个核心图算法

### 3.1 SCC（强连通分量）— 找出不可分割的最小单元

互相 import 的文件组不能拆分到不同模块：

```
原始图：
  app.py ←→ ctx.py ←→ globals.py (互相 import，形成 SCC)
  sansio/app.py → sansio/scaffold.py
  app.py → sansio/app.py

压缩后 DAG：
  [app+ctx+globals] → [sansio/app] → [sansio/scaffold]
  views.py → [app+ctx+globals]
  cli.py → [app+ctx+globals]
```

SCC 内的文件 = **功能天生耦合的代码**，它们互相依赖到无法拆开。

### 3.2 DAG 层级分析 — 决定纵向层次

在 SCC 压缩后的 DAG 上计算每个节点的深度（最长路径）：

```python
depth(node) = max(depth(parent) + 1 for parent in node.dependents) if has_dependents else 0
```

Flask 的结果：

- **depth=0**（最底层实现）：`sansio/scaffold.py`
- **depth=1**（中间层）：`sansio/app.py`
- **depth=2**（核心门面，被很多上层使用）：`app.py + ctx.py + globals.py` [SCC 紧耦合]
- **depth=3**（高层使用者）：`views.py, cli.py, testing.py, blueprints.py`

**关键洞察**：代码的抽象层次不是我们计算出来的，而是开发者在写 import 语句时就已经定义好了的。

### 3.3 Louvain — 同层内的横向分组

同一层级内可能有多个独立功能，用 Louvain 区分：

```
depth=3 的文件：{views.py, cli.py, testing.py, blueprints.py, templating.py}

Louvain 分组结果：
  功能组1: {views.py, blueprints.py}  ← 都关于请求处理
  功能组2: {cli.py}                   ← 独立功能
  功能组3: {testing.py}               ← 独立功能
  功能组4: {templating.py}            ← 独立功能
```

### 三者的关系

| 需要回答的问题                           | 用什么工具           |
| ---------------------------------------- | -------------------- |
| 哪些文件功能相关，应放一起？（横向分组） | 加权图 + Louvain/SCC |
| 谁是高层入口，谁是底层实现？（纵向分层） | DAG 层级分析         |
| 哪些文件紧耦合到不可分割？（最小单元）   | SCC（强连通分量）    |

---

## 4. 功能锥体（Feature Cone）提取

### 4.1 核心思想

从依赖图的"叶子"（入口点）出发，向下追踪依赖，直到遇到被多个功能共享的代码为止。每个叶子 + 它的专属依赖链 = 一个"功能锥体"。

### 4.2 算法步骤

**Step 1**: 找功能入口点（Feature Roots）

- 定义：入度为 0 或入度来自外部（不被项目内其他代码依赖）的节点

**Step 2**: 从每个入口向下追踪，标记"专属"和"共享"

```
views.py 的依赖链：
  views.py → app.py → sansio/app.py → sansio/scaffold.py
  views.py → wrappers.py
  views.py → ctx.py → globals.py

cli.py 的依赖链：
  cli.py → app.py → sansio/app.py → sansio/scaffold.py

app.py 被 views, cli, testing 三个入口都依赖 → "共享代码"
wrappers.py 只被 views.py 使用 → views 功能的"专属代码"
```

**Step 3**: 划分结果

```
功能 "请求处理" (root: views.py):
  专属代码: views.py, wrappers.py, ctx.py
  共享依赖: → core (app.py, globals.py)

功能 "CLI" (root: cli.py):
  专属代码: cli.py
  共享依赖: → core (app.py)

基础设施 "Core" (被 3+ 功能共享):
  app.py, globals.py, config.py
  共享依赖: → sansio (更底层的基础设施)

基础设施 "SansIO 抽象层" (被 Core 依赖):
  sansio/app.py, sansio/scaffold.py
```

### 4.3 与其他方案的对比

| 维度         | DAG 层级优先       | Louvain 优先         | 功能锥体                      |
| ------------ | ------------------ | -------------------- | ----------------------------- |
| 顶层分类     | 按抽象层级         | 按图社区             | **按功能用途**                |
| 回答什么     | 代码在哪个抽象层？ | 代码在图上联系紧密？ | **要改 X 功能看哪里？**       |
| 适合谁       | 架构师理解抽象分层 | 数学最优分割         | **AI 快速定位修改范围**       |
| 共享代码处理 | 和独占代码混在一起 | 被移除               | **独立成基础设施 + 交叉引用** |

---

## 5. Louvain 的重新定位

当前实现把 Louvain 当主力，存在以下问题：

1. **有向图被强制转为无向图**：`A imports B ≠ B imports A`，方向被丢失
2. **高入度节点被粗暴移除**：如 `globals.py, helpers.py` 直接被踢出分析，但它们恰恰是理解架构的关键文件
3. **结果命名不反映功能**：找不到目录前缀就叫 `module_0, module_7`

**正确的定位**：

| 场景                     | 用什么              | 原因                            |
| ------------------------ | ------------------- | ------------------------------- |
| 有明确目录结构的代码     | 目录树 + 图修正     | 开发者的组织意图 > 算法         |
| 目录扁平（所有文件在根） | Louvain             | 没有目录信号，只能靠依赖关系    |
| 单个大目录需要细分       | Louvain 子分组      | 当一个目录有 20+ 文件时需要拆分 |
| 跨目录的功能关联         | 图的 SCC + PageRank | 找到跨目录但功能耦合的文件      |

---

## 6. 完整分组与深度策略

### 输入

- `dependency_graph`（有向图，边=import/调用/继承）
- `file_tree`（目录结构）
- `per_file_tokens`（每文件 token 数）

### 算法

**Step 1**: 初始分组（目录树 + 图混合）

```
├── 有子目录的 → 每个子目录 = 一个候选模块
├── 根级散落文件 → 用 Louvain 在子图上做社区发现
│   → 结果命名：取每个社区中 PageRank 最高的文件名
└── 大目录（>15文件） → 对该目录子图再跑一次 Louvain
```

**Step 2**: 图边界修正

```
├── 强连通分量检查：互相 import 的文件 → 不能拆到不同模块
├── 继承链检查：class A(B) → A 和 B 的文档需要交叉引用
├── 高扇入检测：被 5+ 模块 import 的文件 → 标记为"共享组件"
└── 凝聚度得分：内部边/(内部边+外部边)
    < 0.3 → 分组可能不合理，标记给 LLM Reviewer 审查
```

**Step 3**: Token 预算决定文档粒度

```
├── 模块总 token < 500 → 合并到父节点
├── 模块总 token 500-6000 → 单篇 OVERVIEW（深度=1）
├── 模块总 token > 6000 → OVERVIEW + 子 DETAIL
│   └── 子文档分割方式：
│       ├── 有子目录 → 按子目录分
│       ├── 无子目录但有类 → 按类分
│       └── 纯函数 → 按 Louvain 功能集群分
└── 未通过凝聚度检查 → 交给 Validator Agent
```

**Step 4**: 生成依赖元数据

```
每个模块文档必须包含：
├── "本模块依赖" → 列出 import 了哪些其他模块
├── "被谁依赖" → 列出哪些模块 import 了本模块
├── "继承关系" → 本模块中的类继承自哪个模块
└── "共享组件" → 本模块使用了哪些高扇入的公共文件
```

### 输出

- `doc_tree`: 文档树（可变深度，非均匀）
- `cross_refs`: 每个模块的依赖/被依赖/继承关系
- `review_flags`: 凝聚度不足的模块列表（交给 Validator Agent）

---

## 7. 新 MCP 流水线输出

MCP Server 应按顺序生成 5 个 JSON 文件（可合并为一次 `analyze_codebase(path)` 调用）：

| 输出文件                | 内容                                 |
| ----------------------- | ------------------------------------ |
| `01_structure.json`     | 文件、函数、类、所有依赖边           |
| `02_dag.json`           | SCC 压缩后的 DAG + 层级分配          |
| `03_feature_cones.json` | 功能分组 + 共享基础设施              |
| `04_file_tokens.json`   | 每文件 Token 估算                    |
| `05_task_manifest.json` | Agent 任务分配（batch/single/split） |

---

## 8. Token 估算改进

- **当前做法**：`行数 × 15`（误差 ±50%）
- **改进做法**：`字符数 ÷ 4`（更准确）
- **新增文件级明细**：不仅返回模块级汇总，还要返回每个文件的 token 数

---

## 9. 可保留的现有实现

以下组件的核心逻辑可以保留：

- ✅ graph-sitter 解析层（`parser/`）
- ✅ Louvain 分组算法（`graph/`），但需改为辅助角色
- ✅ Token 估算算法（`budget/estimator.py`），但需改用字符数/4
- ✅ DAG 拓扑排序（`graph/ordering.py`）
- ✅ Mermaid 图生成（`doc/mermaid.py`）
