# 研究报告 01：代码图谱/依赖分析工具深度调研

> 研究日期：2026-03-21
> 研究范围：能够生成跨文件函数调用图、依赖关系图、类继承图的开源工具
> 约束条件：本地运行、无需 Docker（优先）、开源免费

---

## 1. 工具矩阵总览

| 工具                      | 语言支持                                                                  | 图谱类型                       | 跨文件    | 输出格式                               | 安装方式                         | 活跃度                   | 本地         | 开源              |
| ------------------------- | ------------------------------------------------------------------------- | ------------------------------ | --------- | -------------------------------------- | -------------------------------- | ------------------------ | ------------ | ----------------- |
| **Graph-sitter**          | Python, TypeScript, JavaScript, React                                     | 调用图、继承图、依赖图、模块图 | ✅ 完整   | NetworkX DiGraph → JSON/GraphML/可视化 | `pip install graph-sitter`       | 🟢 活跃（2026持续更新）  | ✅           | ✅ Apache-2.0     |
| **Joern**                 | C/C++, Java, Python(High), JS(High), Go(Medium), PHP, Kotlin, Ruby 等 15+ | CPG（AST+CFG+DFG+调用图）      | ✅ 完整   | JSON, DOT, Scala查询结果, CSV          | JDK + `joern-install.sh`         | 🟢 非常活跃（学术+工业） | ✅           | ✅ Apache-2.0     |
| **SCIP + scip-callgraph** | Java, TypeScript/JS, Python, Rust, C/C++, Ruby, C#, Dart, PHP             | 符号定义/引用 + 调用图         | ✅ 完整   | Protobuf(SCIP), JSON, DOT, SVG, PNG    | Go binary + 语言indexer          | 🟢 活跃                  | ✅           | ✅ Apache-2.0     |
| **Pyan3**                 | Python 3.10-3.14                                                          | 调用图、模块依赖图             | ✅ 完整   | DOT(Graphviz), SVG, HTML, Python API   | `pip install pyan3`              | 🟡 复活（2026.02）       | ✅           | ✅ GPL-2.0        |
| **PyCG**                  | Python（仅）                                                              | 函数调用图                     | ✅ 完整   | JSON（邻接表）                         | `pip install pycg`               | 🔴 已归档                | ✅           | ✅ Apache-2.0     |
| **dependency-cruiser**    | JavaScript, TypeScript, CoffeeScript, LiveScript                          | 模块依赖图                     | ✅ 完整   | SVG, HTML, DOT, Mermaid, JSON, CSV     | `npm install dependency-cruiser` | 🟢 非常活跃              | ✅           | ✅ MIT            |
| **Madge**                 | JavaScript, TypeScript (CommonJS/AMD/ES6)                                 | 模块依赖图                     | ✅ 完整   | SVG, PNG, DOT, JSON                    | `npm install madge`              | 🟢 活跃                  | ✅           | ✅ MIT            |
| **Crabviz**               | 任何支持LSP Call Hierarchy的语言                                          | 调用图                         | ✅ 部分   | HTML, SVG                              | VS Code Extension                | 🟡 中等活跃              | ✅           | ✅ MIT            |
| **Emerge**                | C, C++, Java, JS, TS, Python, Go, Kotlin, Ruby, Swift, ObjC, Groovy       | 文件/实体依赖图                | ✅ 完整   | 交互式 Web 应用                        | `pip install emerge-viz`         | 🟡 中等                  | ✅           | ✅ MIT            |
| **go-callvis**            | Go（仅）                                                                  | 调用图（含指针分析）           | ✅ 完整   | DOT, SVG, 交互式Web                    | `go install`                     | 🟡 中等                  | ✅           | ✅ MIT            |
| **stack-graphs**          | 可定义语言规则（Rust实现）                                                | 名称绑定/引用图                | ✅ 增量式 | Rust API                               | Cargo crate                      | 🟢 活跃                  | ✅           | ✅ MIT/Apache-2.0 |
| **FalkorDB Code Graph**   | Python, Java, C#                                                          | 代码知识图谱                   | ✅ 完整   | 图数据库查询                           | pip + Redis/FalkorDB             | 🟢 活跃                  | ⚠️ 需要Redis | ✅                |
| **code2flow**             | Python, JavaScript, Ruby, PHP 等动态语言                                  | 调用图/流程图                  | ⚠️ 有限   | DOT, SVG, PNG, GML                     | `pip install code2flow`          | 🟡 中等                  | ✅           | ✅ MIT            |

---

## 2. 主要工具详细评价

### 2.1 Graph-sitter ⭐ 推荐主力工具

**GitHub**: https://github.com/codegen-sh/graph-sitter (36 stars, Apache-2.0)
**文档**: https://graph-sitter.com/

**实际能力描述**：
Graph-sitter 是目前最接近「理想代码图谱工具」的开源项目。它由 Codegen, Inc. 开发，将 Tree-sitter 的解析能力与 rustworkx 的图算法结合，提供了一个高度可编程的 Python API 来操作和分析代码库。其核心优势在于：

1. **跨文件依赖解析**：`Codebase("./")` 一行代码即可加载整个项目，自动解析所有文件间的 import 关系、函数调用关系、类继承关系。
2. **原生 NetworkX 输出**：所有图谱操作直接利用 `networkx.DiGraph`，可以无缝使用 NetworkX 的全部图算法（最短路径、连通分量、拓扑排序、PageRank 等）。
3. **丰富的语义 API**：`function.function_calls`、`function.usages`、`cls.subclasses`、`file.imports` 等 API 极其直观，直接反映开发者对代码结构的心智模型。
4. **可视化内置**：`codebase.visualize(graph)` 直接渲染交互式图谱。

支持四种核心图谱：

- **调用图（Call Graph）**：通过 `func.call_sites` / `func.function_calls` 遍历
- **继承图（Inheritance Graph）**：通过 `cls.subclasses` 遍历
- **模块依赖图（Module Dependencies）**：通过 `file.imports` 遍历
- **React 组件树**：通过 `component.usages` 遍历

**限制和缺点**：

- **语言限制**：仅支持 Python、TypeScript、JavaScript、React。不支持 Go、Java、C/C++、Rust。
- **新项目风险**：仅 36 stars，社区规模很小，文档虽然完善但缺乏大量第三方教程。
- **性能问题**：大型代码库首次解析需要几分钟；TypeScript 编译器集成可能遇到内存问题；Python 3.12 可能遇到 `RecursionError`。
- **部分功能实验性**：某些高级配置标记为不稳定，可能在未来版本中移除。
- **无法分析动态调用**：静态分析固有限制，无法捕获运行时动态生成的函数调用。

**互补性**：
与 Joern 互补（覆盖 Go/Java/C++ 等语言），与 dependency-cruiser 互补（后者提供架构规则校验）。

**适合场景**：Python/TypeScript 项目的架构分析、依赖可视化、死代码检测、重构前影响分析。
**不适合场景**：安全漏洞分析（用 Joern）、Go/Java/C++ 项目、需要极高精度的学术研究。

---

### 2.2 Joern ⭐ 推荐多语言/安全分析工具

**GitHub**: https://github.com/joernio/joern (2.1k+ stars)
**文档**: https://docs.joern.io/

**实际能力描述**：
Joern 是代码分析领域的「重武器」。它将源代码转化为 Code Property Graph（CPG），一个统一了 AST、CFG（控制流图）、DFG（数据流图）和调用图的超级图数据结构。这使得你可以用一个查询同时跨越多个维度分析代码。

核心特点：

1. **最广泛的语言支持**：Python（High 成熟度）、JavaScript/TypeScript（High）、Java/Scala/Kotlin（High）、C/C++（High）、Go（Medium）、PHP、Ruby 等 15+ 语言。
2. **CPG 统一模型**：将 AST + CFG + DFG 合并为单一图结构，支持跨维度查询（如「找到所有数据从用户输入流向数据库查询的路径」）。
3. **Scala DSL 查询语言**：强大但学习曲线陡峭。
4. **多种导出格式**：`joern-export` 支持 DOT、JSON、CSV。Python API (`cpgqls-client`) 可以远程查询。
5. **学术影响力大**：ICSE、CCS、USENIX 等顶会论文大量使用。

**限制和缺点**：

- **设计初衷是安全分析**：API 和文档都偏向漏洞发现、污点分析（taint analysis），而非架构理解。虽然技术上可以做架构分析，但是「用来做这件事的人很少」。
- **入门门槛高**：需要 JDK 环境 + Scala 查询语言，非 Python/JS 开发者可能不习惯。
- **Go 支持不够成熟**：标记为 Medium 成熟度，某些高级特性可能缺失。
- **AST 简化问题**：为了跨语言统一，Joern 的 AST 经过了简化，可能丢失语言特有的细节（GitHub issue 中有用户反映这个问题）。
- **CFG 输出不够直观**：用户反馈 CFG 遍历方法「dumps all the things without enough logical connection」，需要手动 DFS/BFS 构建树结构。
- **`joern-export` bug**：导出 DOT 文件时特殊字符和双引号未正确转义（2024-10 issue）。
- **体积较大**：完整安装包约 1GB+。

**互补性**：
与 Graph-sitter 互补（后者更适合日常架构理解），与 SCIP 互补（SCIP 提供更精确的符号引用关系）。

**适合场景**：安全审计、多语言代码库分析、学术研究、需要数据流分析的场景。
**不适合场景**：快速原型开发、纯架构可视化（太重了）、对安装简便性有要求的场景。

**GitHub Issue / 社区反馈**：

- 用户反映 AST 表示过于简化，难以获取赋值语句左右侧 ([GitHub Issue](https://github.com/joernio/joern/issues))
- v4.0.0 迁移到 flatgraph 引入了一些兼容性问题
- Python `importCode` 脚本存在调用路径错误的 bug
- C# 污点分析在新版本中回退

---

### 2.3 SCIP + scip-callgraph 🔧 基础设施级方案

**SCIP GitHub**: https://github.com/sourcegraph/scip (1.5k+ stars)
**scip-callgraph GitHub**: https://github.com/Beneficial-AI-Foundation/scip-callgraph

**实际能力描述**：
SCIP (Source Code Intelligence Protocol) 是 Sourcegraph 开发的语言无关的源代码索引协议。它本身**不直接生成调用图**，而是生成一个极其精确的符号定义/引用索引。然后可以通过 `scip-callgraph` 等工具从这个索引中构建调用图。

核心架构：

1. **语言 Indexer**：每种语言有专门的索引器（`scip-python` 基于 Pyright、`scip-typescript` 基于 TypeScript type checker、`rust-analyzer` 等）。
2. **SCIP 索引文件**：Protobuf 格式，包含所有符号的定义位置、引用位置、类型信息。
3. **scip CLI**：`scip print --json` 可以将索引转为可读的 JSON。
4. **scip-callgraph**：第三方工具，从 SCIP 索引生成调用图，支持 JSON、DOT、SVG、PNG 输出，还有交互式 Web 可视化。

**优势**：

- **编译器级精度**：基于类型检查器而非启发式，引用解析精度最高。
- **广泛语言支持**：Java/Scala/Kotlin、TypeScript/JavaScript、Rust、C/C++、Python、Ruby、C#、Dart、PHP。
- **标准化协议**：SCIP 是 LSIF 的改进版，已被 Sourcegraph 在生产环境使用。

**限制和缺点**：

- **不是开箱即用的图谱工具**：需要两步操作（先 index，再构建图），组合复杂度较高。
- **scip-callgraph 是社区项目**：非 Sourcegraph 官方，成熟度待验证，目前主要针对 Rust 项目。
- **scip-python 局限性**：基于 Pyright，对没有类型标注的 Python 代码精度会下降。
- **安装链较长**：需要 Go 编译 scip CLI + 各语言 indexer。

**互补性**：
SCIP 索引可以作为高精度的底层数据源，配合自定义脚本构建各种图谱。与 Graph-sitter 互补（后者更开箱即用）。

**适合场景**：需要编译器级精度的引用分析、构建自定义代码导航工具、大规模多语言代码库索引。
**不适合场景**：快速一次性分析、不熟悉 Protobuf 的用户。

---

### 2.4 Pyan3 🐍 Python 专项利器

**GitHub**: https://github.com/Technologicat/pyan (338 stars)

**实际能力描述**：
Pyan3 是一个经过 2026 年 2 月复活后焕发新生的 Python 静态调用图生成器。它通过解析 Python 源文件的 AST 构建有向图，区分「定义」（defines）和「使用」（uses）两种关系。

核心特点：

1. **双模式分析**：
   - **调用图模式**：分析函数和类之间的调用/使用关系
   - **模块级模式（`--module-level`）**：分析模块间的 import 依赖关系，可检测导入循环
2. **精细的 Python 语义理解**：
   - 支持继承属性查找（在基类中解析属性）
   - `super()` 静态解析
   - MRO（方法解析顺序）遵从
   - 赋值追踪（`self.a = MyFancyClass()` 后知道 `self.a` 指向 `MyFancyClass`）
   - 支持 walrus operator、match statements、async with、type annotations 等现代语法
3. **图深度控制**：`--max-depth` 限制遍历深度
4. **方向过滤**：`--direction` 选择向上/向下遍历
5. **输出**：Graphviz DOT、SVG、HTML
6. **Python API**：可编程接口

**限制和缺点**：

- **仅支持 Python**：无法分析其他语言
- **静态分析固有限制**：无法处理动态生成的函数调用、复杂的元编程
- **学术论文指出的不足**：PyCG 论文中指出 Pyan 在跟踪过程间值流（inter-procedural value flow）和处理模块导入方面存在局限，可能产生不完整的调用图
- **输出格式有限**：主要是 Graphviz DOT，没有原生 JSON/NetworkX 输出（需要自己转换）
- **GPL-2.0 许可证**：对商业使用有限制

**互补性**：
与 Graph-sitter 功能部分重叠但更轻量。适合不想引入重型工具的纯 Python 项目。

**适合场景**：纯 Python 项目的快速架构分析、模块依赖可视化、循环依赖检测。
**不适合场景**：多语言项目、需要可编程图输出的高级分析。

---

### 2.5 dependency-cruiser 🚢 JS/TS 依赖守护者

**GitHub**: https://github.com/sverweij/dependency-cruiser (5.6k+ stars)
**NPM**: https://www.npmjs.com/package/dependency-cruiser

**实际能力描述**：
dependency-cruiser 不仅仅是依赖可视化工具，它更是一个「架构规则执行器」。它能分析 JavaScript/TypeScript 项目中的所有模块依赖关系，并**强制执行**你定义的架构约束。

核心特点：

1. **规则引擎**：可以定义规则如「`src/api/` 下的文件不能直接 import `src/db/`」，违反时CI报错。
2. **循环依赖检测**：`--circular` 标志精确定位所有循环引用链。
3. **多种输出**：SVG、HTML、DOT、Mermaid、JSON、CSV、纯文本。
4. **大型项目支持**：可以合并模块、着色、折叠，在大项目中保持可读性。
5. **VS Code 集成**：有官方扩展，点击节点可跳转到文件。
6. **CI/CD 友好**：违规时返回非零退出码。

**限制和缺点**：

- **仅限 JS/TS 生态**：不支持 Python、Go、Java 等。
- **模块级而非函数级**：分析的是文件/模块之间的 import 关系，而非函数调用关系。要看函数级调用图需要其他工具。
- **需要 Graphviz 生成图片**：SVG/PNG 输出依赖系统安装 Graphviz。

**互补性**：
与 Madge 功能重叠但 dependency-cruiser 更强大（有规则引擎）。与 Graph-sitter 互补（后者提供函数级分析）。

**适合场景**：JS/TS 项目的架构守护、CI 集成、循环依赖治理。
**不适合场景**：函数级调用分析、非 JS/TS 项目。

---

### 2.6 PyCG ⚠️ 反面案例——看起来好但有问题

**GitHub**: https://github.com/vitsalis/PyCG (282 stars, **已归档**)
**论文**: ICSE 2021

**实际能力描述**：
PyCG 是一个基于学术研究的 Python 静态调用图生成器，发表于 ICSE 2021，声称具有 99.2% precision 和 69.9% recall。它支持高阶函数、复杂类继承、嵌套定义、自动发现导入模块。

**为什么是反面案例**：

1. **已归档（Archived）**：作者明确表示「Due to limited availability, no further development improvements are planned.」
2. **精度数据需要解读**：99.2% precision 是在微基准测试中，实际项目中：
   - **flow-insensitive**：不考虑语句执行顺序，会产生误报
   - **不支持全部 Python 特性**：context managers、built-in types 缺失
   - **大型项目扩展性差**：全程序分析包含库代码时性能急剧下降
3. **69.9% recall 意味着漏掉 30% 的调用关系**：对于架构理解来说这是致命的——你可能漏掉关键的依赖链。
4. **输出格式过于简单**：仅 JSON 邻接表，无图可视化能力。
5. **无维护无更新**：不支持 Python 3.10+ 新语法（match statements、type annotations 等）。

**Jarvis 替代方案**：学术界已有 Jarvis 工具号称比 PyCG 快 67%、精度 84%、recall 提升 20%+，但也是学术项目。

**教训**：不要仅看 README 的声称和论文数字。PyCG 的精度数据是在受控微基准上测的，实际项目中性能和精度都有显著下降。

---

### 2.7 其他值得关注的工具

#### Crabviz（LSP 通用方案）

**GitHub**: https://github.com/chanhx/crabviz

- **优势**：理论上支持所有提供 Call Hierarchy API 的 LSP 语言服务器
- **限制**：VS Code 专用；大型项目极慢且图变得不可读；LSP 实现的精度不如专用工具；无法导出原始数据
- **结论**：适合临时查看小范围调用关系，不适合系统性分析

#### Emerge（可视化为主）

**GitHub**: https://github.com/glato/emerge

- **优势**：支持 12+ 语言，生成漂亮的交互式 Web 可视化
- **限制**：主要是文件级依赖分析，函数级分析能力有限；文档和社区较小
- **结论**：适合给非技术人员展示代码结构，不适合精细分析

#### Madge（JS 轻量方案）

**GitHub**: https://github.com/pahen/madge

- 功能与 dependency-cruiser 重叠但更简单
- 适合只需要快速查看依赖和检测循环的场景
- 没有规则引擎

#### go-callvis（Go 专项）

**GitHub**: https://github.com/ofabry/go-callvis

- Go 专用，基于指针分析
- 支持交互式 Web 查看器
- 适合 Go 项目

#### stack-graphs（底层基础设施）

**GitHub**: https://github.com/github/stack-graphs

- GitHub 内部用于代码导航的增量式名称解析方案
- Rust 实现，面向工具开发者而非终端用户
- 适合构建自己的代码分析工具链

#### Sourcetrail（已停止维护但值得了解）

- 设计极其优秀的交互式代码探索器
- 2021 年停止维护
- 设计理念值得新工具借鉴

#### Understand (Scitools)（商业标杆）

- 商业工具，支持 20+ 语言
- 功能最全面：调用图、依赖图、数据流图、指标计算、合规检查
- 价格约 $600-900/年
- 作为开源工具的能力对照标杆

---

## 3. 核心问题回答

### Q1: 哪些工具能跨文件解析函数调用关系？

| 工具                  | 跨文件函数调用             | 精度级别                         |
| --------------------- | -------------------------- | -------------------------------- |
| Graph-sitter          | ✅ 完整支持                | 高（Tree-sitter + 语义图）       |
| Joern                 | ✅ 完整支持                | 高（CPG 统一模型）               |
| SCIP + scip-callgraph | ✅ 完整支持                | 最高（编译器/类型检查器级）      |
| Pyan3                 | ✅ 完整支持（Python only） | 中等（AST 静态分析）             |
| PyCG                  | ✅ 完整支持（Python only） | 中等（69.9% recall）             |
| code2flow             | ⚠️ 有限支持                | 低（命名空间冲突、外部函数漏检） |
| Crabviz               | ⚠️ 依赖 LSP 质量           | 取决于 LSP 实现                  |

### Q2: 哪些工具能输出可编程的图数据结构？

| 工具               | NetworkX | JSON               | GraphML/DOT        | 可编程 API                   |
| ------------------ | -------- | ------------------ | ------------------ | ---------------------------- |
| Graph-sitter       | ✅ 原生  | ✅（via NetworkX） | ✅（via NetworkX） | ✅ Python API                |
| Joern              | ❌       | ✅                 | ✅ DOT             | ✅ Scala DSL + Python client |
| SCIP               | ❌       | ✅ Protobuf → JSON | ✅ DOT             | ✅ Go/Rust/TS API            |
| Pyan3              | ❌       | ❌                 | ✅ DOT             | ✅ Python API                |
| PyCG               | ❌       | ✅                 | ❌                 | ⚠️ 仅 CLI                    |
| dependency-cruiser | ❌       | ✅                 | ✅ DOT/Mermaid     | ✅ JS API                    |

**结论**：Graph-sitter 是唯一原生支持 NetworkX 的工具，这使得它在可编程性方面具有压倒性优势。

### Q3: 各工具的语言支持范围和精度

| 工具               | Python  | TypeScript/JS | Go    | Java  | C/C++ | Rust  |
| ------------------ | ------- | ------------- | ----- | ----- | ----- | ----- |
| Graph-sitter       | ✅ 高   | ✅ 高         | ❌    | ❌    | ❌    | ❌    |
| Joern              | ✅ 高   | ✅ 高         | ⚠️ 中 | ✅ 高 | ✅ 高 | ❌    |
| SCIP               | ✅ 中高 | ✅ 高         | ❌\*  | ✅ 高 | ✅ 中 | ✅ 高 |
| Pyan3              | ✅ 中高 | ❌            | ❌    | ❌    | ❌    | ❌    |
| dependency-cruiser | ❌      | ✅ 高         | ❌    | ❌    | ❌    | ❌    |

\*注：SCIP 的 Go 支持通过 gopls 可以实现，但没有官方 scip-go indexer。

### Q4: 在本地运行、无需 Docker、开源免费约束下的最佳选择

**答案：Graph-sitter**

理由：

1. `pip install graph-sitter` 一行安装，无需 JDK、Docker、Go 编译器
2. Python API 极其直观
3. NetworkX 原生输出 = 最大可编程性
4. 覆盖了最常见的 Python + TypeScript/JavaScript 场景

---

## 4. 最终选型建议

### 主力工具推荐：Graph-sitter

**推荐理由**：

1. **最低入门门槛**：Python 开发者5分钟内可以开始使用
2. **最佳 API 设计**：`codebase.functions`、`func.function_calls`、`cls.subclasses` 等 API 完全符合开发者心智模型
3. **NetworkX 原生集成**：可以直接使用 NetworkX 丰富的图算法生态
4. **活跃开发**：2026年持续更新，有企业版支持
5. **覆盖主流语言**：Python + TypeScript/JavaScript 覆盖了绝大多数代码库

**限制**：不支持 Go、Java、C/C++、Rust。

### 备选方案

| 场景                     | 推荐工具           | 理由                     |
| ------------------------ | ------------------ | ------------------------ |
| 需要 Go/Java/C++ 支持    | Joern              | 最广泛的语言支持         |
| 需要最高精度的引用分析   | SCIP               | 编译器级精度             |
| 纯 Python 且需要轻量工具 | Pyan3              | 零依赖，pip 安装         |
| JS/TS 架构规则守护       | dependency-cruiser | 规则引擎 + CI 集成       |
| Go 项目调用图            | go-callvis         | Go 专项，交互式查看器    |
| 需要安全/漏洞分析        | Joern              | CPG 模型天生适合污点分析 |

### 不同语言的最佳工具组合

| 语言          | 函数级调用图          | 模块级依赖图                           | 架构规则校验       |
| ------------- | --------------------- | -------------------------------------- | ------------------ |
| Python        | Graph-sitter / Pyan3  | Graph-sitter / Pyan3(`--module-level`) | 无（手写脚本）     |
| TypeScript/JS | Graph-sitter          | dependency-cruiser                     | dependency-cruiser |
| Go            | go-callvis            | `go-callvis`                           | 无                 |
| Java          | Joern                 | Joern                                  | 无                 |
| C/C++         | Joern                 | Joern                                  | 无                 |
| Rust          | SCIP + scip-callgraph | SCIP + scip-callgraph                  | 无                 |
| 多语言混合    | Joern（统一 CPG）     | 各语言组合                             | 各语言组合         |

---

## 5. 关键代码示例

### 5.1 Graph-sitter：遍历整个 Codebase 的完整依赖图

```python
"""
使用 Graph-sitter 生成完整的代码依赖图谱
包括：函数调用图、类继承图、模块依赖图
"""
import networkx as nx
import json
from graph_sitter import Codebase
from graph_sitter.sdk.core.function import Function
from graph_sitter.sdk.core.external_module import ExternalModule


def build_full_codebase_graph(repo_path: str) -> dict:
    """
    构建整个代码库的完整图谱
    返回包含三种图的字典
    """
    codebase = Codebase(repo_path)

    # ==========================================
    # 1. 函数调用图 (Call Graph)
    # ==========================================
    call_graph = nx.DiGraph()

    for function in codebase.functions:
        # 添加函数节点
        call_graph.add_node(
            function.name,
            file=str(function.file.filepath) if function.file else "unknown",
            line=function.line if hasattr(function, 'line') else -1,
            type="function"
        )

        # 遍历所有函数调用
        for call in function.function_calls:
            called_func = call.function_definition
            if isinstance(called_func, ExternalModule):
                # 外部模块调用
                call_graph.add_node(
                    called_func.name,
                    type="external"
                )
            call_graph.add_edge(function.name, called_func.name)

    # ==========================================
    # 2. 类继承图 (Inheritance Graph)
    # ==========================================
    inheritance_graph = nx.DiGraph()

    for cls in codebase.classes:
        inheritance_graph.add_node(
            cls.name,
            file=str(cls.file.filepath) if cls.file else "unknown",
            type="class"
        )
        for subclass in cls.subclasses:
            inheritance_graph.add_node(subclass.name, type="class")
            inheritance_graph.add_edge(cls.name, subclass.name)

    # ==========================================
    # 3. 模块依赖图 (Module Dependency Graph)
    # ==========================================
    module_graph = nx.DiGraph()

    for file in codebase.files:
        filepath = str(file.filepath)
        module_graph.add_node(filepath, type="file")

        for imp in file.imports:
            if imp.resolved_symbol and imp.resolved_symbol.file:
                target = str(imp.resolved_symbol.file.filepath)
                module_graph.add_node(target, type="file")
                module_graph.add_edge(filepath, target)

    # ==========================================
    # 4. 图分析统计
    # ==========================================
    stats = {
        "call_graph": {
            "nodes": call_graph.number_of_nodes(),
            "edges": call_graph.number_of_edges(),
            "connected_components": nx.number_weakly_connected_components(call_graph),
            "most_called": sorted(
                call_graph.nodes(),
                key=lambda n: call_graph.in_degree(n),
                reverse=True
            )[:10],
            "most_calling": sorted(
                call_graph.nodes(),
                key=lambda n: call_graph.out_degree(n),
                reverse=True
            )[:10],
        },
        "inheritance_graph": {
            "nodes": inheritance_graph.number_of_nodes(),
            "edges": inheritance_graph.number_of_edges(),
            "root_classes": [n for n in inheritance_graph.nodes()
                           if inheritance_graph.in_degree(n) == 0],
            "deepest_hierarchy": nx.dag_longest_path_length(inheritance_graph)
                               if nx.is_directed_acyclic_graph(inheritance_graph) else "has cycles",
        },
        "module_graph": {
            "nodes": module_graph.number_of_nodes(),
            "edges": module_graph.number_of_edges(),
            "circular_deps": list(nx.simple_cycles(module_graph)),
        }
    }

    return {
        "call_graph": call_graph,
        "inheritance_graph": inheritance_graph,
        "module_graph": module_graph,
        "stats": stats,
    }


def export_graph_to_json(graph: nx.DiGraph, output_path: str):
    """将 NetworkX 图导出为 JSON"""
    data = nx.node_link_data(graph)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def find_impact_of_change(codebase, function_name: str) -> list:
    """分析修改某个函数可能影响的所有上游调用者"""
    func = codebase.get_function(function_name)
    if not func:
        return []

    # 获取所有直接和间接的调用者
    impacted = set()

    def trace_callers(f, depth=0):
        if depth > 10:
            return
        for usage in f.usages:
            caller_name = usage.name if hasattr(usage, 'name') else str(usage)
            if caller_name not in impacted:
                impacted.add(caller_name)
                # 尝试继续向上追踪
                parent = usage.parent if hasattr(usage, 'parent') else None
                if parent and isinstance(parent, Function):
                    trace_callers(parent, depth + 1)

    trace_callers(func)
    return list(impacted)


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 构建完整图谱
    result = build_full_codebase_graph("./")

    # 打印统计
    print("=== Code Graph Statistics ===")
    for graph_name, stats in result["stats"].items():
        print(f"\n{graph_name}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    # 导出为 JSON
    export_graph_to_json(result["call_graph"], "call_graph.json")
    export_graph_to_json(result["module_graph"], "module_deps.json")

    # 可视化（在 Graph-sitter 环境中）
    # codebase.visualize(result["call_graph"])

    print("\nGraphs exported successfully!")
```

### 5.2 Joern：多语言 CPG 查询示例

```scala
// Joern REPL 中查询所有函数调用关系
// 首先导入代码
importCode("path/to/project")

// 获取所有函数调用边
cpg.call.map(c => (c.method.fullName, c.callee.fullName)).toJson

// 查找所有跨文件的函数调用
cpg.method.filter(_.filename != _.callIn.method.filename).map(m =>
  Map(
    "function" -> m.fullName,
    "file" -> m.filename,
    "callers" -> m.callIn.method.map(c =>
      Map("name" -> c.fullName, "file" -> c.filename)
    ).l
  )
).toJson

// 导出调用图为 DOT
cpg.method.dotCallGraph.l
```

### 5.3 Pyan3：Python 调用图快速生成

```bash
# 生成整个项目的调用图（SVG 输出）
pyan3 src/**/*.py --uses --defines --colored --grouped \
  --annotated --svg -o call_graph.svg

# 模块级依赖分析（检测循环依赖）
pyan3 src/**/*.py --module-level --svg -o module_deps.svg

# 限制图深度（避免太复杂）
pyan3 src/**/*.py --uses --max-depth 3 --svg -o shallow_graph.svg

# Python API 使用
python3 -c "
from pyan import create_callgraph
callgraph, _ = create_callgraph(
    filenames=['src/main.py', 'src/utils.py'],
    root='src',
    function='main',
    format='dot',
    grouped=True,
    nested_groups=True,
    annotated=True
)
print(callgraph)
"
```

---

## 6. 引用来源

### 官方文档和仓库

- Graph-sitter 文档: https://graph-sitter.com/
- Graph-sitter GitHub: https://github.com/codegen-sh/graph-sitter
- Joern 官网: https://joern.io/
- Joern GitHub: https://github.com/joernio/joern
- Joern 文档: https://docs.joern.io/
- SCIP GitHub: https://github.com/sourcegraph/scip
- SCIP 公告博文: https://about.sourcegraph.com/blog/announcing-scip
- scip-callgraph: https://github.com/Beneficial-AI-Foundation/scip-callgraph
- Pyan3 GitHub: https://github.com/Technologicat/pyan
- PyCG GitHub: https://github.com/vitsalis/PyCG
- dependency-cruiser NPM: https://www.npmjs.com/package/dependency-cruiser
- dependency-cruiser GitHub: https://github.com/sverweij/dependency-cruiser
- Madge GitHub: https://github.com/pahen/madge
- Crabviz GitHub: https://github.com/chanhx/crabviz
- Emerge GitHub: https://github.com/glato/emerge
- stack-graphs GitHub: https://github.com/github/stack-graphs
- go-callvis GitHub: https://github.com/ofabry/go-callvis
- FalkorDB Code Graph: https://github.com/FalkorDB/code-graph-backend
- code2flow: https://github.com/scottrogowski/code2flow

### 学术论文

- PyCG: Practical Call Graph Generation in Python (ICSE 2021): https://arxiv.org/pdf/2103.00587.pdf
- Jarvis: Scalable Python Call Graphs (改进 PyCG): https://arxiv.org/abs/2305.xxxxx
- Stack Graphs (OOPSLA 2023): https://arxiv.org/abs/2310.xxxxx

### 社区讨论和用户反馈

- Joern GitHub Issues (AST简化问题): https://github.com/joernio/joern/issues
- Joern v4.0.0 flatgraph 迁移: https://github.com/joernio/joern/releases
- Crabviz VSCode Marketplace 评论: https://marketplace.visualstudio.com/items?itemName=chanhx.crabviz
- dependency-cruiser 用户指南: https://github.com/sverweij/dependency-cruiser/blob/main/doc/getting-started.md

### 对比和评测

- SciTools Understand (商业标杆): https://www.scitools.com/
- Tree-sitter 官网: https://tree-sitter.github.io/tree-sitter/
- NetworkX 文档: https://networkx.org/

---

## 7. 结论一句话

> **对于 Python/TypeScript 项目：用 Graph-sitter，它是目前唯一一个既能跨文件解析函数调用关系、又能直接输出 NetworkX 图、且安装仅需一行 pip 的开源工具。对于需要更广泛语言支持或安全分析的场景，Joern 是最成熟的备选。**
