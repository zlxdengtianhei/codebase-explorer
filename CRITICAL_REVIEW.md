# 批判性审视：多Agent代码库探索方案

> 生成时间：2026-03-21
> 基于深度调研的批判性分析

---

## 一、你的核心需求回溯

从你的多轮对话中，我提炼出以下**不可妥协的需求**：

| #   | 需求                                               | 关键词     |
| --- | -------------------------------------------------- | ---------- |
| 1   | 对**所有代码**进行检查，不遗漏                     | 完整性保证 |
| 2   | LLM + 确定性分析**相结合**                         | 混合架构   |
| 3   | **多Agent分工**，不在单Agent中完成                 | 分布式     |
| 4   | **监督机制**：监控每个Agent的token/代码量          | 资源管控   |
| 5   | Agent间**互斥探索**，不重复分析                    | 无冲突     |
| 6   | **记录机制**：确定性检查完成度                     | 可审计     |
| 7   | 输出**渐进式披露文档**：Index → Module → Component | 层级文档   |
| 8   | **本地MCP/Skill**，不依赖外部服务                  | 本地运行   |
| 9   | 兼容 Claude Code / Codex / OpenCode / Gemini CLI   | 跨工具     |

---

## 二、原方案的7个关键问题

### 问题1: ⚠️ graph-sitter ≠ 通用静态分析库

**原方案声称**：使用 graph-sitter 做代码图谱构建。

**实际情况**：

- graph-sitter（现名 codegen）是一个**代码操作和重构库**，不是分析库
- 它的核心 API（`function.move_to_file()`, `function.rename()`）面向**代码修改**
- 虽然它有 `.dependencies` 和 `.usages` 查询能力，但这是为重构服务的副产品
- **仅支持 Python, TypeScript, JavaScript, React**，不支持 Go, Rust, Java 等
- 它的定位是 "scriptable codemod engine"，不是 "codebase analyzer"

**结论**：graph-sitter 可以用作依赖分析的底层引擎，但**不要把它当作核心分析框架**。它提供了非常好的 API 来查询依赖关系，但缺少：

- 复杂度计算
- 模块边界检测
- 架构层级推断

### 问题2: ⚠️ SQLite 作为图数据库的局限性

**原方案声称**：用 SQLite nodes+edges 表替代 Neo4j/Memgraph。

**调研发现**：

- Neo4j 在 4 层深度图遍历上比 MySQL **快 1,135 倍**
- PostgreSQL + 递归 CTE 比 Neo4j **慢 74 倍**（3层连接查询）
- SQLite 的递归 CTE 不支持窗口函数，不支持递归部分的 LIMIT/ORDER BY

**但是**：对于代码库分析这个场景：

- 典型代码库的依赖图**深度很浅**（通常 3-5 层）
- 节点数量有限（数百到数千个模块/类/函数，非百万级）
- 查询模式简单（不需要 PageRank 等复杂图算法）
- **零部署成本**的优势巨大

**结论**：SQLite **在这个场景下是合理的**，但需要注意：

- 对于超大型项目（>10K 文件），可能需要缓存策略
- 避免深度递归查询（>5层）
- 考虑使用 graph-sitter 自带的 rustworkx 图引擎作为内存图替代

### 问题3: 🔴 缺失关键发现 — DocAgent (Facebook Research)

**原方案完全忽略了** DocAgent，这是一个与你需求**高度吻合**的现有工具：

| 你的需求       | DocAgent 的实现                                         |
| -------------- | ------------------------------------------------------- |
| 多Agent分工    | ✅ Reader + Searcher + Writer + Verifier + Orchestrator |
| 确定性分析     | ✅ AST 解析 → 依赖 DAG → 拓扑排序                       |
| 按依赖顺序处理 | ✅ 层级遍历，先处理依赖少的                             |
| 质量保证       | ✅ Verifier Agent 进行迭代验证                          |
| 开源           | ✅ MIT License (Facebook Research)                      |
| 本地运行       | ✅ 支持本地 LLM (vllm)                                  |

**DocAgent 的局限**：

- ❌ 只支持 Python（不支持 JS/TS/Go 等）
- ❌ 只生成 docstring，不生成架构文档
- ❌ 没有渐进式披露的文档层级
- ❌ 没有 MCP 接口
- ❌ 没有 token 预算控制

**价值**：DocAgent 的 **Navigator 模块**（AST → DAG → 拓扑排序）和 **多Agent协作模式**（Reader/Searcher/Writer/Verifier）是你应该**参考和借鉴**的核心设计模式。

### 问题4: ⚠️ "Skill驱动编排"的现实性问题

**原方案声称**：用 SKILL.md 替代 LangGraph 做 Agent 编排。

**这里有一个根本性矛盾**：

- SKILL.md 是**给 AI Agent 看的指令**，不是程序性的编排引擎
- "多Agent协作" 在 Skill 模式下意味着：**一个 AI Agent 需要手动多次调用 MCP 工具**
- 每次调用都依赖 AI 的"记忆"来维持状态，这正是你说的"context window有限"问题

**更好的思路**：

- MCP Server 本身就是编排引擎（通过工具暴露编排能力）
- Skill 只负责**教会 Agent 如何使用这些工具**
- 关键状态管理在 MCP Server 侧完成（SQLite），不依赖 Agent 记忆

### 问题5: ⚠️ Token 预算控制缺乏可操作性

**原方案的设计**：每 Agent 50K tokens 预算，80% 时触发 checkpoint。

**问题**：

- MCP Server **无法直接知道** Agent 消耗了多少 LLM tokens
- tree-sitter 的 "token" 和 LLM 的 "token" 是完全不同的概念
- Agent 侧的 token 消耗主要取决于 prompt + response，MCP Server 只能控制输入

**更务实的方案**：

- 用**文件行数/字符数**作为代理指标（而非 LLM token）
- MCP Server 控制每次返回给 Agent 的**代码量**（chunking）
- 在 Skill 中约定："分析完 N 个模块后必须提交中间结果"
- 让 **Agent 自己报告** token 使用情况（通过 submit_analysis 工具）

### 问题6: ⚠️ "互斥"机制过于复杂

**原方案设计了** claim_files 的原子性声明。

**但实际场景中**：

- 在 Skill 驱动模式下，通常**一次只有一个 Agent 在运行**
- 真正的"互斥"是**跨会话**的（上次分析了 A 模块，这次分析 B 模块）
- 这更像是一个**任务队列**，而非实时锁

**简化方案**：

- MCP Server 维护 `analysis_status` 表（file → analyzed/pending）
- 每次 Agent 启动时，MCP 返回下一批**未分析的文件**
- 分析完成后更新状态 → 这就是互斥+完整性的全部

### 问题7: 渐进式文档的层级划分缺乏自动化

**原方案描述了**文档结构 (INDEX.md → OVERVIEW.md → ARCHITECTURE.md)。

**但缺失了关键环节**：如何**自动决定**什么是顶层、什么是子层？

**需要的是**：

- 基于依赖图的 **社区检测算法**（自动发现模块边界）
- 基于入度/出度的 **重要性排序**（决定哪些模块最重要）
- 基于代码量的 **复杂度判断**（决定是否需要子层级）

---

## 三、这些工具到底能不能用？逐一判断

### ✅ 可以直接用

| 工具                  | 用途                          | 细节                                                |
| --------------------- | ----------------------------- | --------------------------------------------------- |
| **graph-sitter**      | 代码图谱构建                  | Apache-2.0, 本地, 支持 Py/TS/JS，自带跨文件依赖解析 |
| **FastMCP 3.0**       | MCP Server 框架               | 成熟稳定，支持 STDIO/HTTP，Python                   |
| **Agent Skills 标准** | 跨工具兼容 Skill              | Claude Code / Gemini CLI / OpenCode 均原生支持      |
| **tree-sitter**       | AST 解析（graph-sitter 底层） | 广泛语言支持，高性能                                |

### ⚠️ 可以参考但不能直接用

| 工具               | 参考价值                               | 不能直接用的原因                         |
| ------------------ | -------------------------------------- | ---------------------------------------- |
| **DocAgent**       | Navigator (DAG排序) + Multi-Agent 模式 | 仅支持 Python，仅生成 docstring          |
| **aider repomap**  | PageRank 排序 + token 预算裁剪策略     | 嵌入在 aider 内的模块，不可独立使用      |
| **Code-Graph-RAG** | MCP 集成范例                           | 依赖 Docker + Memgraph，违背"本地零依赖" |
| **RepoAgent**      | Git hook 增量更新 + 多线程并发         | 仅 Python，仅生成代码文档                |
| **Plandex**        | 项目地图 + 上下文管理策略              | 是完整工具链，不可拆分使用               |

### ❌ 不适合

| 工具           | 原因                                |
| -------------- | ----------------------------------- |
| **CODEXGRAPH** | 依赖 Neo4j Docker                   |
| **LangGraph**  | 过重，增加了大量非必要复杂度        |
| **HyperAgent** | 完整的 SE Agent，不可拆分           |
| **SCIP**       | 需要独立 indexer 安装，用途偏向 IDE |

---

## 四、修订后的推荐架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  修订架构 v2                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SKILL.md — "codebase-architecture-explorer"            │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ 教会 AI Agent:                                   │    │    │
│  │  │ 1. 何时/如何调用 MCP 工具                        │    │    │
│  │  │ 2. 分析多少代码后应停止当前会话                   │    │    │
│  │  │ 3. 如何写每一层级的文档                          │    │    │
│  │  │ 4. 文档格式模板和示例                            │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                        │ 读取 Skill 指令                         │
│                        ▼                                         │
│  ┌──────────── AI Agent (Claude/GPT/Gemini) ──────────┐        │
│  │  按 Skill 指令调用 MCP 工具 → 分析代码 → 写文档     │        │
│  └───────────────────┬────────────────────────────────┘        │
│                      │ 调用 MCP 工具                             │
│                      ▼                                           │
│  ┌─────────────── MCP Server ─────────────────────────┐        │
│  │                                                      │        │
│  │  Layer 1: 代码图谱 (确定性)                          │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ graph-sitter (Codebase API)                   │   │        │
│  │  │ ├── 自动跨文件依赖解析                         │   │        │
│  │  │ ├── .dependencies / .usages 查询               │   │        │
│  │  │ ├── 模块/类/函数完整图谱                       │   │        │
│  │  │ └── import 分析 (本地 vs 外部)                 │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  │                      │                                │        │
│  │  Layer 2: 状态管理 (确定性)                          │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ SQLite                                        │   │        │
│  │  │ ├── analysis_status (文件→状态)                │   │        │
│  │  │ ├── module_hierarchy (自动分组结果)             │   │        │
│  │  │ ├── analysis_results (Agent提交的分析)          │   │        │
│  │  │ └── doc_structure (文档骨架)                    │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  │                      │                                │        │
│  │  Layer 3: 工具接口                                   │        │
│  │  ┌──────────────────────────────────────────────┐   │        │
│  │  │ MCP Tools:                                     │   │        │
│  │  │ ├── index_codebase() → 构建图谱                │   │        │
│  │  │ ├── get_modules() → 模块列表+复杂度            │   │        │
│  │  │ ├── get_module_details(mod) → 依赖+函数+概述   │   │        │
│  │  │ ├── get_next_analysis_batch() → 未分析文件列表 │   │        │
│  │  │ ├── submit_analysis(mod, summary) → 提交结果   │   │        │
│  │  │ ├── get_progress() → 覆盖率百分比              │   │        │
│  │  │ └── generate_doc_skeleton() → 文档目录骨架     │   │        │
│  │  └──────────────────────────────────────────────┘   │        │
│  │                                                      │        │
│  └──────────────────────────────────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 关键变更点

| 原方案                            | 修订方案                                | 原因                                                                |
| --------------------------------- | --------------------------------------- | ------------------------------------------------------------------- |
| graph-sitter + 自己写 SQLite 图谱 | **直接用 graph-sitter 的 Codebase API** | graph-sitter 已经内置了完整的跨文件依赖图，不需要自己存 nodes/edges |
| nodes/edges SQLite 表             | 仅用 SQLite 存**分析状态**              | 图谱查询直接走 graph-sitter 内存图                                  |
| claim_files 互斥锁                | **get_next_analysis_batch()**           | 简化为任务队列模式                                                  |
| Token 预算控制                    | **代码量控制** (行数/文件数)            | MCP 无法观测 LLM token                                              |
| LangGraph 编排                    | **MCP 工具 + Skill 指令**               | 保持轻量                                                            |
| 自己写 AST 解析                   | 借鉴 **DocAgent 的 DAG 拓扑排序**       | 按依赖顺序处理，确保上下文完整                                      |

---

## 五、具体实现策略

### Phase 0: 验证 graph-sitter (1小时)

```bash
# 安装
uv pip install graph-sitter

# 验证核心功能
python3 -c "
from graph_sitter import Codebase
cb = Codebase('./')
print(f'Files: {len(cb.files)}')
print(f'Functions: {len(cb.functions)}')
print(f'Classes: {len(cb.classes)}')
for f in list(cb.functions)[:3]:
    print(f'  {f.name}: deps={len(f.dependencies)}, usages={len(f.usages)}')
"
```

如果 graph-sitter 工作良好 → 使用它作为核心。
如果 graph-sitter 有问题 → 退回到 tree-sitter + 自建图谱。

### Phase 1: MCP Server 核心 (2天)

仅 3 个文件：

- `server.py` — FastMCP 入口 + 工具定义
- `analyzer.py` — graph-sitter 封装 + 模块分组算法
- `state.py` — SQLite 状态管理

### Phase 2: Skill (1天)

- `SKILL.md` — 完整的分析流程指令 + 文档模板

### Phase 3: 文档模板 (0.5天)

- `templates/` — Jinja2 模板

---

## 六、与原方案的最终对比

| 维度        | 原方案                                                        | 修订方案                                                   |
| ----------- | ------------------------------------------------------------- | ---------------------------------------------------------- |
| 依赖安装    | tree-sitter + graph-sitter + fastmcp + 多个 tree-sitter-\* 包 | **graph-sitter + fastmcp** (graph-sitter 内置 tree-sitter) |
| 代码量      | ~500-800行 自定义代码                                         | **~300-500行**                                             |
| 图谱存储    | SQLite nodes/edges 表 (自建)                                  | graph-sitter 内存图 (现成)                                 |
| 状态存储    | SQLite (分析状态 + 图谱)                                      | SQLite (**仅分析状态**)                                    |
| 多Agent模式 | LangGraph → Skill                                             | **MCP工具 + Skill** (一致)                                 |
| 核心洞察    | 没有利用 DocAgent 的设计模式                                  | **借鉴 DocAgent 的 DAG 拓扑遍历**                          |
| 互斥机制    | 锁 (claim_files)                                              | **任务队列** (get_next_batch)                              |
| Token控制   | LLM token 计数                                                | **代码量** (行数/文件数)                                   |

---

## 七、需要你决策的问题

1. **语言范围**：graph-sitter 仅支持 Python/TS/JS/React。你的目标代码库会涉及其他语言吗？如果需要 Go/Rust/Java，需要退回到 tree-sitter 自建方案。

2. **文档最终形态**：你倾向于纯 Markdown 文档还是需要可交互的可视化（如 HTML + Mermaid 图）？

3. **运行模式**：你希望一次性分析整个代码库，还是需要增量更新（代码变更后只更新受影响的部分）？

4. **是否参照 DocAgent**：是否要克隆并研究 DocAgent 的源码，特别是它的 Navigator 和 Orchestrator 模块？
