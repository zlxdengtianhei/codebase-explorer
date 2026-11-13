# 代码图：有哪几种，CBE 用了哪些

[English](code-graphs.md)

**先说结论。**

- 代码图把关于代码的事实存成节点和边。每种图回答一类问题：哪个文件依赖哪个，哪个函数调用哪个，语句按什么次序执行，一个值流到哪里。
- CBE 能建四种：导入、调用、控制流（CFG），以及要求时才建的数据流。都是可选的；没有图，CBE 照样写出地图。
- 调用、控制流和数据流的边由 Joern 出。导入由 Grimp（Python）和 dependency-cruiser（JavaScript、TypeScript）解析。Tree-sitter 不出边：它负责把文件切成块、找出符号。
- 之后 CBE 用 Louvain 社区发现把代码单元聚成模块。模型只给模块起名。
- CBE 没有用 SCIP 或语言服务器的索引、CodeQL，也没有用按排序裁剪的符号地图。第 3 节写了有记录的理由。
- 调用边是最弱的一环。“已解析”只说明分析器把这次调用连到了一个目标，不证明连对了。第 4 节列出已知的错。

## 1. 图的种类

| 种类 | 回答什么问题 | 在 CBE 里 |
|---|---|---|
| 导入 | 哪个文件或包依赖哪个？ | Python 用 Grimp，JavaScript 和 TypeScript 用 dependency-cruiser；别的语言只有 Joern 记下的导入声明，连不到具体文件 |
| 调用 | 哪个函数调用哪个？ | Joern 跑了才有 |
| 控制流（CFG） | 一个函数里的语句可能按什么次序执行？ | Joern 跑了才有 |
| 数据流 | 一个变量的哪次赋值会流到哪次使用？ | Joern，只在 `cbe graph build --with-dataflow` 时导出 |

CBE 给每条调用边和导入边一个状态：`resolved`（已解析）、`ambiguous`（有歧义）、`unresolved`（未解析）或 `external`（仓外）。控制流图不是运行时的轨迹。详见 [Generate and query code graphs](reference.md#generate-and-query-code-graphs)。

## 2. 别人怎样建代码图

**按排序裁剪的符号地图（aider）。** Tree-sitter 找出名字在哪里定义、在哪里被用。文件成为图的节点，再按重要性挑出定义，裁到一个 token 预算以内（`--map-tokens`，缺省 1k token）（[文档](https://aider.chat/docs/repomap.html)、[设计文章](https://aider.chat/2023/10/22/repomap.html)）。[aider 的代码](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py)里排序用的是 PageRank。它要的是一段短提示，不是一张完整的图。

**语言服务器、LSIF 与 SCIP。** 语言服务器按语言精确回答“跳到定义”“找引用”。[LSIF](https://microsoft.github.io/language-server-protocol/overviews/lsif/overview/) 把这些回答存下来，工具不用开着服务器也能用。[SCIP](https://github.com/sourcegraph/scip) 是 Sourcegraph 为同一用途做的新索引格式（[发布说明](https://sourcegraph.com/blog/announcing-scip)）。索引器按语言、事先跑，通常要一个能构建的工程。

**代码属性图（Joern）。** [2014 年的论文](https://mlsec.tu-berlin.de/docs/2014-ieeesp.pdf)把语法树、控制流图和程序依赖图合成一张图。[Joern](https://docs.joern.io/) 为多种语言建这种图并支持查询；[CPG 规范](https://cpg.joern.io/)定义了它的各层，调用图是其中一层。

**查询式分析（CodeQL）。** [CodeQL](https://codeql.github.com/docs/codeql-overview/about-codeql/) 先从源码抽出一个关系数据库（编译型语言靠观察构建过程），再用 QL 查询。

**社区发现（Louvain、Leiden）。** 这类方法把图分成内部连得紧的几组。[Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html) 是按模块度的启发式算法。[Leiden 的论文](https://arxiv.org/abs/1810.08473)指出 Louvain 可能分出连得很差、甚至连不通的组，而 Leiden 分出的组保证连通。[GraphRAG](https://microsoft.github.io/graphrag/index/default_dataflow/) 用 Leiden 建分层的组，再让模型给每组写摘要。

## 3. CBE 用了什么，没用什么

- **Tree-sitter** 在语法边界上切开每个文件、找出符号。每个字节都落在某一块里。
- **Joern 4.0.654** 出调用、控制流，要求时出数据流。连同 Java 约 1.9 GB；`cbe graph setup` 把 Joern 装进你的用户缓存目录，找不到 Java 21 或更高版本时连 Java 运行时一起装（[调用图](../README.zh-CN.md#调用图)）。CBE 只调分析器，不自己写分析器（`src/cbe/graph.py`：“It never re-implements a language analyzer”）。
- **Grimp** 出 Python 的导入图（`graphs` 额外依赖）。**dependency-cruiser** 出 JavaScript 和 TypeScript 的导入图（要 Node.js）。
- **Louvain**（networkx，固定随机种子）把单元聚成模块。边的权重来自调用与导入、同文件同目录、用词相近。进入一个单元的边要除以 `ln(e + 入度)`，这样人人都调的工具函数不会把所有东西粘成一个模块（`src/cbe/skeleton.py`）。分组也用写讲解的模型报的关系；只靠这类关系连起来的模块对，在依赖视图里标“模型推断”。

| 路线 | 用了吗 | 为什么没用 |
|---|---|---|
| SCIP、LSIF、语言服务器 | 没有 | 设计记录（CBE 没有实测）：每种语言各有前提，例如能构建的工程、`compile_commands.json`、特定的 Node 版本，所以对随手指向的仓库常常跑不起来。能跑的地方更准。 |
| 在 Tree-sitter 上自己做名字解析 | 没有（2026 年 10 月换成 Joern） | 设计记录：每种语言一套规则，要一直维护；别家公开的准确率都是自报的。 |
| CodeQL | 没有 | 没有记录。 |
| 按排序裁剪的符号地图 | 没有 | 目标不同：aider 把地图裁到 token 预算以内；CBE 建一棵覆盖每个单元的模块树。 |
| Leiden | 没有 | 没有记录。 |

## 4. 各语言

状态取自 `cbe languages`（`call_graph` 字段），条件取自 [README](../README.zh-CN.md#调用图)，最后一栏是后来的检查发现的错。不管调用图状态如何，下面每种语言的源码解析和切块都能用（Ruby、Rust、PHP、C# 要装 `languages` 额外依赖；Kotlin、Swift 要装 `languages-community`）。

| 语言 | 状态 | 已知会错或偏弱的地方 |
|---|---|---|
| Python | works | 缺省的 `uv tool install codebase-explorer` 不带 Grimp，导入图就缺了，唯一的提示是一长串诊断输出的最后一行；要装 `graphs` 额外依赖。在 markupsafe 上（2026-11-13 的一次走查，还没进本仓的评测），31 处 `self.__class__(...)` 被连到测试文件里一个无关的 `Proxy.__class__`，还标成已解析。推导式里的调用是已知弱点。 |
| C、C++ | works | 不跑预处理：宏可能被当成函数，宏多的头文件切得粗。 |
| JavaScript、TypeScript | works | 动态导入、CommonJS 和仓外目标可能只解析一部分。 |
| Java | works | 解析结果受工程类型和依赖影响。 |
| Go | works | 跨包的调用可能停在未解析或仓外。 |
| Ruby | works | 动态分派可能把调用连到另一个类的同名方法；CBE 把很多这类调用标成有歧义，仍有一些连错。接收者类型偏弱。 |
| Rust、PHP | needs_tool | Rust 要 `cargo` 和 Cargo 工程布局。PHP 要 `php` 7 或更高版本。 |
| C# | partial | 调用重载方法时只解析到这一组重载。在 GuardClauses 上，2,322 条调用里 993 条标成未解析；其中约 955 条是仓外方法、`nameof` 或构造调用，仓内真连不上的 14 条。 |
| Kotlin | known_failure | Joern 4.0.654 在一个 146 个文件的仓库上停下；两个文件的小例子能跑。 |
| Swift、TSX | untested | |

`cbe graph setup` 和整条流程在 Linux x86_64 上测过，macOS 还没测。看一张图要读它的 `capabilities` 和 `diagnostics`，不要只看大小（[reference](reference.md#generate-and-query-code-graphs)）。其他限制见[已知限制](../README.zh-CN.md#已知限制)。
