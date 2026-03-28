# V5 MCP 输出重设计 + Skill 执行协议重构

> 本文档是 V4 (`05_v4_architecture_detection_redesign.md`) 的后续演进。
> 基于 V4 的 6 路调研结论和 brainstorm 讨论，重新定义 MCP 的输出职责、Skill 的执行协议、以及文档的固定格式。
> 后续 Agent 在实施前**必须先阅读本文档 + V4 记录 + V3 记录**。

---

## 一、需求全貌

### 1.1 核心问题

当前系统的实际表现与愿景严重脱节。V4 诊断的三层问题依然存在：

| 层 | 问题 | 表现 |
|---|------|------|
| MCP 算法 | 无目录排除、索引 .venv/ | 247 个 cone，1.2MB JSON，12,907 个文件 |
| MCP 输出 | 全量 dump，无分级 | get_feature_cones 90K 字符，get_dependency_graph 11.5MB |
| Skill 执行 | 管线断裂后无降级路径 | 退化为手动分析，产出按目录组织的 API reference |

但 V4 的方案侧重于"算法提升 ARI"，忽视了更根本的问题：**即使算法完美，当前的 MCP 输出格式和 Skill 执行协议也无法产出合格的架构文档。**

### 1.2 重新定义的需求

以下按优先级排列，每条需求都从用户原始表述中提取。

#### 需求 R1：MCP 只做"文件→功能模块"分类

> "MCP 其实都不需要函数名，你只需要把这个文件在哪个分组、哪个层级，或者哪一个功能类中分类好就可以了。"

MCP 的核心输出是**分好层级的文件组织**——哪些文件属于哪个功能模块，模块之间的依赖关系是什么。

不需要：
- 函数名称或签名（LLM 自己读源码获取）
- 函数功能描述（LLM 写）
- 代码片段或 snippet

需要：
- 文件→模块的映射
- 模块间的依赖关系
- 模块在 DAG 中的层级
- 每个模块的 token 量估算

#### 需求 R2：MCP 提供函数级依赖关系

> "MCP 还是要给出函数的依赖。在给出 details 文件的时候，需要把与这个文件中有关的函数依赖也给到 LLM。要让它在 details 中说明这些函数相互之间的依赖关系。"

MCP 需要额外提供的信息：
- 文件 A 的函数 foo() 调用了文件 B 的函数 bar()
- 文件 A 的类 X 继承了文件 B 的类 Y

这不是用于分组的，而是用于 **DETAIL 文档中描述依赖关系的数据来源**。LLM 在写某个文件的 DETAIL 时，需要知道该文件的函数与其他文件的函数之间的调用关系。

#### 需求 R3：MCP 输出过滤——控制上下文注入量

> "不要让过多的上下文全部一次性注入到所有 agent 的上下文中，以避免出现错误。"

过滤机制的本质不是"提供不同视图"，而是**防止上下文溢出**：

- 主 Agent 只看到模块列表摘要（名称、文件数、token 数、依赖）
- 写 DETAIL 的 sub-agent 只看到自己负责的模块的文件列表 + 函数依赖
- 不相关的模块信息不应注入

#### 需求 R4：Token 预算驱动的渐进式读码

> "让 subagent 每一次提取出一定量的文件，这个量是与 Token 总量挂钩的。如果 Token 量超过了阈值，就停止读取新文件。这个操作一直持续进行，让 subagent 逐步完成代码文件的阅读。"

Sub-agent 的执行协议：
1. 从 MCP 获取自己负责的模块文件列表 + 各文件的 token 数
2. 按 token 预算逐批读取源码文件
3. 每读一个文件，完成三步输出（见 R5）
4. 累计 token 接近预算上限时，停止当前批次
5. 下一个 sub-agent 或下一批次继续未完成的文件
6. **全局停止条件：代码库中所有文件都已被阅读并产出 DETAIL**

该协议需要兼容 Claude Code、Codex 等现有 CLI 工具。

#### 需求 R5：DETAIL 逐文件生成，三步输出

> "LLM 在生成 Detail 输出时，应该是逐个文件进行的。"

对功能模块中的每个文件，sub-agent 执行：

1. **Step 1 — 函数描述**：读源码，给出文件中各函数/类的作用
2. **Step 2 — 依赖关系**：从 MCP 获取函数级依赖，说明该文件与其他文件/函数的调用关系
3. **Step 3 — INDEX 片段**：给出该文件/模块在 INDEX 中应该写的摘要

完成一个文件后，再进入下一个文件，重复以上步骤。

#### 需求 R6：INDEX 由 DETAIL 片段直接拼合

> "把这个 index 最终应该是可以直接生成出来的。应该是可以直接组合在一起的。"

- Sub-agent 写 DETAIL 时同时输出 INDEX 片段
- 所有 sub-agent 完成后，INDEX 由这些片段**直接拼合**而成
- 不需要另一个 agent 从头撰写 INDEX
- INDEX 是渐进式披露的入口：用户看 INDEX 就能知道"要找某个功能去哪个 DETAIL"

#### 需求 R7：固定格式的 DETAIL 和 INDEX

> "Index 和 Detail 都应该有一个固定的输出格式。这样做的目的是让 Agent 能够快速进行所需的重新安排和更新。"

固定格式的目的：
- Phase 5 重组 agent 可以通过**工具**精准移动/调整内容块
- 不需要 LLM 手动重写/添加/删除文本
- 通过固定协议，工具能识别出"具体哪一块内容"，将其提取并放到合适的位置

#### 需求 R8：Phase 5 重组工具化

> "应该通过一个固定的工具，识别出具体哪一块内容，将其提取出来并放到合适的位置。"

Phase 5 重组 agent 的工作方式：
1. 读 INDEX，了解各模块功能全貌
2. 判断模块划分是否需要调整（合并/拆分/重命名）
3. 通过**注入 prompt 的工具**执行操作：
   - 移动某个 DETAIL 块到另一个模块
   - 更新 INDEX 中的某个模块摘要
   - 合并两个模块的 DETAIL
   - 拆分一个模块为多个
4. 工具负责格式合规，LLM 只负责决策

#### 需求 R9：可插拔的分类算法 + 统一输出接口

> "最终应该有一个统一的接口。如果我们实现了不同的方案，可以用那个统一接口来进行算法的更换，然后直接进行测试。"

- 目录优先、融合、两阶段三种方案都应可实现
- 换算法时不影响 Skill、DETAIL/INDEX 生成、Phase 5 重组
- 统一的输出格式使得 scoring harness 可以直接对比不同算法

#### 需求 R10：目录 + 依赖融合的分类方式

> "无论是通过目录引导，还是通过图关系引导，最终给出的结果都应该是按照功能模块进行分类的。"

文件分类应融合两种信号：
- **目录结构**：开发者对功能的天然分组
- **依赖图**：代码之间的实际调用关系

两种信号的权重应自适应——目录结构好的项目（如 Scrapy）多依赖目录信号，扁平项目（如 Rich）多依赖依赖图信号。

---

## 二、设计方案

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────┐
│ MCP Server                                               │
│                                                           │
│  analyze_codebase:                                        │
│    智能排除(.venv 等)                                     │
│    → Parser → CodebaseSnapshot                            │
│    → 加权依赖图(文件级 + 函数级)                          │
│    → GroupingStrategy(可插拔) → FunctionalModule[]         │
│    → Token 估算 → 任务分配                                │
│    → 输出 JSON 文件 + state.json                          │
│                                                           │
│  get_modules(summary):                                    │
│    → 模块列表(名称, 文件数, token, 依赖的其他模块)        │
│                                                           │
│  get_modules(module_id):                                  │
│    → 模块内文件列表 + 各文件 token 数                     │
│                                                           │
│  get_function_deps(file_path):                            │
│    → 该文件的函数 → 被调用的外部函数列表                  │
│                                                           │
│  get_dependency_graph(scope=module, target=module_id):    │
│    → 该模块内文件间的依赖 Mermaid 图                      │
│                                                           │
│  submit_analysis(task_id, ...):                           │
│    → 更新任务状态                                         │
│                                                           │
│  [新] doc_operation(op_type, ...):                        │
│    → 结构化文档操作(移动/合并/拆分 DETAIL 块)             │
└──────────────────────┬────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│ Skill (主 Agent 执行流程)                                  │
│                                                             │
│  Phase 1 — 索引                                            │
│    调 analyze_codebase(path, exclude=[...])                 │
│    结果：JSON 文件已持久化                                  │
│                                                             │
│  Phase 2 — 任务分配                                        │
│    调 get_modules(summary)                                  │
│    → 看到所有模块摘要，按 token 预算分配 sub-agent 任务     │
│    → 每个 sub-agent 负责 1~N 个模块                         │
│                                                             │
│  Phase 3 — DETAIL 生成（并行 sub-agent）                   │
│    每个 sub-agent：                                         │
│      调 get_modules(module_id) → 获取文件列表               │
│      对每个文件：                                           │
│        a. 读源码 → 写函数描述                               │
│        b. 调 get_function_deps(file) → 写依赖关系           │
│        c. 写 INDEX 片段                                     │
│        → 追加到 DETAIL 文件（固定格式）                     │
│        → 检查 token 预算 → 继续或停止                       │
│      调 submit_analysis 报告完成                             │
│    全局停止条件：所有文件已被阅读并产出 DETAIL               │
│                                                             │
│  Phase 4 — INDEX 拼合                                      │
│    收集所有 sub-agent 产出的 INDEX 片段                     │
│    按模块顺序拼合为完整 INDEX.md                            │
│    附加全局依赖 Mermaid 图                                  │
│                                                             │
│  Phase 5 — 语义重组                                        │
│    重组 Agent 读 INDEX → 了解各模块功能                     │
│    判断是否需要调整模块划分                                  │
│    通过 doc_operation 工具执行结构化操作：                    │
│      - move_detail: 移动文件的 DETAIL 到另一模块             │
│      - merge_modules: 合并两个模块                           │
│      - split_module: 拆分一个模块                            │
│      - update_index: 更新 INDEX 中某模块的摘要               │
│    更新后的 INDEX.md + DETAIL 文件即为最终产物                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 MCP 改进

#### 2.2.1 智能范围排除

`analyze_codebase` 新增自动排除 + 用户自定义排除：

**自动排除列表**（硬编码）：
```
.venv/  venv/  node_modules/  __pycache__/  .git/
dist/  build/  .tox/  .mypy_cache/  .pytest_cache/
.eggs/  *.egg-info/
```

**非核心目录检测**（标记但不排除，供 Skill 决定处理深度）：
```
tests/  test/  docs/  docs_src/  examples/  scripts/  benchmarks/
```

**新参数**：
```python
async def analyze_codebase(
    path: str,
    languages: list[str] | None = None,
    output_dir: str | None = None,
    force_reindex: bool = False,
    exclude_paths: list[str] | None = None,   # 新增：额外排除路径
    include_tests: bool = False,               # 新增：是否索引测试目录
) -> dict:
```

#### 2.2.2 函数级依赖提取

当前 `CodebaseParser` 已提取文件级 import 关系。需要扩展提取函数级调用关系。

**新增数据结构**：
```python
@dataclass(frozen=True)
class FunctionDependency:
    source_file: str        # 调用方文件
    source_function: str    # 调用方函数名
    target_file: str        # 被调用文件
    target_function: str    # 被调用函数名
    dep_type: str           # "call" | "inherit" | "import"
```

**新增 MCP Tool**：
```python
@mcp.tool(annotations={"readOnlyHint": True})
async def get_function_deps(
    file: str,              # 文件路径
    module_id: str | None = None,  # 可选：限制在模块内
) -> dict:
    """获取指定文件的函数级依赖关系。

    返回该文件中每个函数/类调用的外部函数/类列表。
    仅包含跨文件的调用关系（同文件内的调用不返回）。
    """
```

**返回格式**：
```json
{
  "file": "src/graph/feature_cone.py",
  "dependencies": [
    {
      "source_function": "extract_feature_cones",
      "calls": [
        {"target_file": "src/graph/weighted_graph.py", "target_function": "build_weighted_dependency_graph", "dep_type": "call"},
        {"target_file": "src/parser/codebase.py", "target_function": "CodebaseParser.parse", "dep_type": "call"}
      ]
    },
    {
      "source_function": "_louvain_communities",
      "calls": [
        {"target_file": "networkx", "target_function": "louvain_communities", "dep_type": "call"}
      ]
    }
  ]
}
```

#### 2.2.3 可插拔分类算法接口

**统一数据结构**：

```python
@dataclass(frozen=True)
class FunctionalModule:
    module_id: str                    # 唯一标识
    name: str                         # 人类可读名称
    files: tuple[str, ...]            # 模块中的文件路径
    layer: int                        # DAG 层级（0 = 最底层）
    depends_on: tuple[str, ...]       # 依赖的其他模块 ID
    token_count: int                  # 模块总 token 估算
    directory_hint: str               # 主目录路径（辅助信息）

@dataclass(frozen=True)
class GroupingResult:
    modules: dict[str, FunctionalModule]  # module_id → FunctionalModule
    infrastructure: tuple[str, ...]        # 基础设施文件
    strategy_used: str                     # 使用的算法名称
    metadata: dict                         # 算法特有的元信息
```

**统一算法协议**：

```python
from typing import Protocol

class GroupingStrategy(Protocol):
    """所有分类算法必须实现此协议。"""

    @property
    def name(self) -> str:
        """算法名称，用于日志和元信息。"""
        ...

    def group(
        self,
        graph: nx.DiGraph,
        snapshot: CodebaseSnapshot,
    ) -> GroupingResult:
        """执行分类，返回统一格式的结果。

        Args:
            graph: 加权依赖图（节点=文件，边=依赖关系+权重）
            snapshot: 代码库解析快照（含文件列表、函数、类等）

        Returns:
            GroupingResult，包含功能模块字典和基础设施文件列表。
        """
        ...
```

**三种实现**：

| 策略类 | 算法名 | 实现路径 | 优先级 |
|--------|--------|---------|--------|
| `TwoStageStrategy` | `two_stage` | 现有 Louvain → 目录后处理 | P0（先实现） |
| `FusionStrategy` | `fusion` | DIS 增强图 → Louvain | P1（后续） |
| `DirectoryFirstStrategy` | `directory_first` | 目录分组 → Louvain fallback | P2（可选） |

**配置方式**：

```python
# server.py 中
GROUPING_STRATEGY = os.environ.get("CODEBASE_EXPLORER_STRATEGY", "two_stage")

def get_strategy(name: str) -> GroupingStrategy:
    strategies = {
        "two_stage": TwoStageStrategy(),
        "fusion": FusionStrategy(),
        "directory_first": DirectoryFirstStrategy(),
    }
    return strategies.get(name, TwoStageStrategy())
```

#### 2.2.4 两阶段策略的具体算法

```python
class TwoStageStrategy:
    """Stage 1: Louvain 聚类（不动）→ Stage 2: 目录后处理。"""

    name = "two_stage"

    def group(self, graph, snapshot) -> GroupingResult:
        # Stage 1: 复用现有 Louvain
        cones, infra = extract_feature_cones(graph, snapshot)

        # Stage 2: 目录后处理
        modules = self._post_process_with_directories(cones, snapshot)
        return GroupingResult(
            modules=modules,
            infrastructure=tuple(infra),
            strategy_used=self.name,
            metadata={},
        )

    def _post_process_with_directories(self, cones, snapshot):
        """用目录结构对 cone 做二次组织。

        规则：
        1. 统计每个 cone 的文件目录分布
        2. >80% 文件在同一目录 → 以该目录命名，保持完整
        3. 跨多目录的 cone → 按主目录+次目录拆分为子组
        4. 同目录下多个 <3 文件的小 cone → 合并
        5. 计算模块间依赖关系
        """
        ...
```

#### 2.2.5 MCP Tool 重设计

**重命名 `get_feature_cones` → `get_modules`**（语义更清晰）：

**Summary 模式**（无参数调用）：

```json
{
  "status": "success",
  "total_modules": 8,
  "total_files": 24,
  "total_tokens": 45000,
  "strategy_used": "two_stage",
  "modules": [
    {
      "module_id": "graph-analysis",
      "name": "Graph Analysis",
      "file_count": 5,
      "token_count": 12000,
      "layer": 1,
      "depends_on": ["parser", "infrastructure"],
      "directory_hint": "src/graph/"
    },
    {
      "module_id": "parser",
      "name": "Code Parser",
      "file_count": 3,
      "token_count": 8000,
      "layer": 0,
      "depends_on": [],
      "directory_hint": "src/parser/"
    }
  ],
  "infrastructure": {
    "file_count": 4,
    "token_count": 3000
  }
}
```

**Detail 模式**（传入 module_id）：

```json
{
  "status": "success",
  "module_id": "graph-analysis",
  "name": "Graph Analysis",
  "layer": 1,
  "depends_on": ["parser", "infrastructure"],
  "files": [
    {"filepath": "src/graph/feature_cone.py", "token_count": 3200},
    {"filepath": "src/graph/weighted_graph.py", "token_count": 2800},
    {"filepath": "src/graph/grouper.py", "token_count": 2100},
    {"filepath": "src/graph/semantic_hints.py", "token_count": 1900},
    {"filepath": "src/graph/__init__.py", "token_count": 200}
  ],
  "internal_layers": [
    ["src/graph/semantic_hints.py"],
    ["src/graph/weighted_graph.py", "src/graph/feature_cone.py"],
    ["src/graph/grouper.py"],
    ["src/graph/__init__.py"]
  ],
  "token_count": 12000
}
```

**关键变化**：
- Summary 模式不返回文件列表，只返回模块元信息
- Detail 模式只返回单个模块的文件，不返回其他模块
- 删除了 `exclusive_files` / `shared_deps` 等内部概念，改为更直觉的 `files` / `depends_on`

**`get_dependency_graph` 默认返回模块级依赖**：

```python
@mcp.tool()
async def get_dependency_graph(
    scope: Literal["project", "module", "file"] = "project",
    target: str | None = None,
    hops: int = 1,
) -> dict:
    """
    scope="project" → 模块间依赖 Mermaid 图（默认，节点=模块）
    scope="module"  → 模块内文件间依赖 Mermaid 图
    scope="file"    → 文件 N-hop 邻居子图
    """
```

`scope="project"` 返回的是模块级别的图（~10 个节点），而非文件级别的图（~1000 个节点），从根本上解决上下文溢出问题。

#### 2.2.6 doc_operation 工具

新增 MCP Tool，支持 Phase 5 重组 agent 执行结构化文档操作：

```python
@mcp.tool(annotations={"readOnlyHint": False})
async def doc_operation(
    op_type: Literal[
        "move_detail",      # 移动文件的 DETAIL 块到另一模块
        "merge_modules",    # 合并两个模块（DETAIL 拼合 + INDEX 更新）
        "split_module",     # 拆分模块（DETAIL 拆分 + INDEX 更新）
        "update_index",     # 更新 INDEX 中某模块的摘要
        "reorder_modules",  # 调整 INDEX 中模块的顺序
    ],
    params: dict,
) -> dict:
    """执行结构化文档操作。

    所有操作基于 DETAIL/INDEX 的固定格式标记进行，
    不需要 LLM 手动编辑文本。

    move_detail:
      params: {file_path: str, from_module: str, to_module: str}

    merge_modules:
      params: {source_module: str, target_module: str, new_name: str | None}

    split_module:
      params: {module_id: str, new_modules: [{name: str, files: [str]}]}

    update_index:
      params: {module_id: str, new_summary: str}

    reorder_modules:
      params: {module_order: [str]}  # module_id 列表，按期望顺序
    """
```

### 2.3 固定文档格式

#### 2.3.1 DETAIL 文件格式

每个功能模块一个 DETAIL 文件，位于 `.codebase-docs/{module_id}/DETAIL.md`。

```markdown
---
module_id: graph-analysis
module_name: Graph Analysis
files_documented: 5
total_tokens: 12000
generated_at: 2026-03-26T10:00:00Z
---

# Graph Analysis

<!-- module:graph-analysis -->

## src/graph/feature_cone.py

<!-- file:src/graph/feature_cone.py -->

### 函数与类

- **`extract_feature_cones(graph, snapshot)`** — 主入口函数。从加权依赖图中提取功能锥体（feature cones），每个锥体代表一个内聚的功能单元。返回 cones 字典和 infrastructure 文件列表。
- **`_louvain_communities(dag)`** — 调用 NetworkX 的 Louvain 社区检测算法，在无向化的加权图上发现社区结构。
- **`_merge_small_communities(communities, dag, min_size)`** — 将小于 min_size 的社区合并到边连接最多的邻居社区，使用 composite scoring（边数 + 目录亲和度）。
- **`_identify_infrastructure(dag, communities)`** — 通过 4 条标准识别基础设施文件：语义分类、额外词干匹配、re-export facade 检测、跨社区导入分析。

### 依赖关系

- `extract_feature_cones` 调用 `_louvain_communities`、`_merge_small_communities`、`_identify_infrastructure`（同文件内）
- `extract_feature_cones` 接收来自 `src/graph/weighted_graph.py:build_weighted_dependency_graph` 的输出作为输入
- `_identify_infrastructure` 调用 `src/graph/semantic_hints.py:classify_file` 和 `src/graph/semantic_hints.py:is_reexport_facade`

<!-- end:src/graph/feature_cone.py -->

## src/graph/weighted_graph.py

<!-- file:src/graph/weighted_graph.py -->

### 函数与类

- **`build_weighted_dependency_graph(snapshot)`** — 从 CodebaseSnapshot 构建加权有向图。边权重：import=1, call=2, inherit=3。返回 WeightedGraphResult。

### 依赖关系

- 被 `src/graph/feature_cone.py:extract_feature_cones` 调用
- 依赖 `src/parser/codebase.py:CodebaseSnapshot` 作为输入

<!-- end:src/graph/weighted_graph.py -->

...（其他文件）

<!-- end:graph-analysis -->
<!-- codebase-explorer: end -->
```

**格式要点**：
- YAML front matter 记录元信息
- HTML 注释标记模块边界（`<!-- module:xxx -->`）、文件边界（`<!-- file:xxx -->`、`<!-- end:xxx -->`）
- 这些标记使 `doc_operation` 工具可以精准定位和操作内容块
- 每个文件有"函数与类"和"依赖关系"两个固定节

#### 2.3.2 INDEX 文件格式

全局 INDEX 文件位于 `.codebase-docs/INDEX.md`。

```markdown
---
project_name: codebase-explorer
modules_count: 8
total_files: 24
generated_at: 2026-03-26T10:30:00Z
---

# Codebase Explorer — 架构概览

<!-- index:start -->

## 模块依赖图

```mermaid
graph TD
    parser["Code Parser"]
    graph["Graph Analysis"]
    budget["Budget Estimation"]
    doc["Document Planning"]
    state["State Management"]
    server["MCP Server"]
    helpers["Server Helpers"]

    server --> graph
    server --> budget
    server --> doc
    server --> state
    server --> helpers
    graph --> parser
    doc --> budget
    doc --> graph
```

## 模块总览

<!-- module-index:parser -->
### Code Parser (`src/parser/`)
解析代码库源文件，提取文件结构、函数签名、类定义和 import 关系。是整个分析管线的第一步。
→ [DETAIL](parser/DETAIL.md)
<!-- end-module-index:parser -->

<!-- module-index:graph-analysis -->
### Graph Analysis (`src/graph/`)
从解析结果构建加权依赖图，通过 Louvain 社区检测提取功能模块（feature cones），识别基础设施文件。核心算法层。
→ [DETAIL](graph-analysis/DETAIL.md)
<!-- end-module-index:graph-analysis -->

<!-- module-index:budget -->
### Budget Estimation (`src/budget/`)
估算每个文件的 token 数量，为任务分配提供预算约束。
→ [DETAIL](budget/DETAIL.md)
<!-- end-module-index:budget -->

...（其他模块）

<!-- index:end -->
<!-- codebase-explorer: end -->
```

**格式要点**：
- YAML front matter 记录全局元信息
- 模块依赖 Mermaid 图放在最前面（来自 `get_dependency_graph(scope="project")`）
- 每个模块有 `<!-- module-index:xxx -->` 标记
- 每个模块摘要包含：名称、目录、一句话功能描述、DETAIL 链接
- 摘要由 sub-agent 在 Phase 3 生成，Phase 4 直接拼合
- `doc_operation` 的 `update_index` / `reorder_modules` 通过标记精准修改

#### 2.3.3 INDEX 片段格式（Sub-agent 输出）

Sub-agent 在处理每个模块时，输出的 INDEX 片段格式：

```markdown
<!-- module-index:{module_id} -->
### {module_name} (`{directory_hint}`)
{一到两句话的功能描述}
→ [DETAIL]({module_id}/DETAIL.md)
<!-- end-module-index:{module_id} -->
```

Phase 4 拼合时，按模块依赖层级（从底层到顶层）排序后拼合即可。

### 2.4 Sub-agent 执行协议

#### 2.4.1 Token 预算驱动的渐进读码

```
输入：
  - module_ids: [str]         # 分配给本 sub-agent 的模块
  - token_budget: int         # 本 sub-agent 的 token 上限
  - output_dir: str           # 写入 DETAIL 的目录

执行：
  accumulated_tokens = 0

  for module_id in module_ids:
      module_info = get_modules(module_id)  # MCP 调用
      detail_lines = []
      index_fragment = ""

      for file_entry in module_info.files:
          # 预检查：加上这个文件会不会超预算？
          if accumulated_tokens + file_entry.token_count > token_budget:
              break  # 停止，剩余文件由下一批次处理

          # Step 1: 读源码，写函数描述
          source = read_file(file_entry.filepath)
          func_descriptions = describe_functions(source)

          # Step 2: 获取函数依赖，写依赖关系
          deps = get_function_deps(file_entry.filepath)  # MCP 调用
          dep_descriptions = describe_dependencies(deps)

          # Step 3: 追加到 DETAIL
          detail_lines.append(format_file_detail(
              filepath=file_entry.filepath,
              func_descriptions=func_descriptions,
              dep_descriptions=dep_descriptions,
          ))

          accumulated_tokens += file_entry.token_count

      # 写 DETAIL 文件
      write_detail(module_id, detail_lines)

      # Step 4: 写 INDEX 片段
      index_fragment = generate_index_fragment(module_id, module_info, detail_lines)
      write_index_fragment(module_id, index_fragment)

      # 报告完成
      submit_analysis(task_id=..., ...)

停止条件：
  - token_budget 耗尽 → 停止当前 sub-agent，主 Agent 派下一个
  - 所有文件已处理 → 全局完成
```

#### 2.4.2 兼容性设计

该协议仅使用以下原语，兼容 Claude Code / Codex / OpenCode：

| 原语 | Claude Code | Codex | OpenCode |
|------|------------|-------|----------|
| 读文件 | Read tool | read_file | Read tool |
| 写文件 | Write tool | write_file | Write tool |
| MCP 调用 | 原生支持 | 通过 MCP bridge | 原生支持 |
| Sub-agent | Task tool | 多 agent 模式 | Task tool |
| Token 计数 | MCP 提供估算 | MCP 提供估算 | MCP 提供估算 |

不依赖任何特定 CLI 工具的私有 API。Token 预算由 MCP 的 `get_modules(module_id)` 返回的 `token_count` 字段驱动，sub-agent 自行累加并在接近上限时停止。

### 2.5 Phase 5 重组协议

#### 2.5.1 重组 Agent 的 Prompt 注入

```markdown
你是架构重组 Agent。你的任务是审查当前的模块划分并进行必要的调整。

## 可用工具

- `doc_operation(op_type="move_detail", params={...})` — 移动文件
- `doc_operation(op_type="merge_modules", params={...})` — 合并模块
- `doc_operation(op_type="split_module", params={...})` — 拆分模块
- `doc_operation(op_type="update_index", params={...})` — 更新 INDEX
- `doc_operation(op_type="reorder_modules", params={...})` — 调整顺序

## 执行步骤

1. 读取 .codebase-docs/INDEX.md，了解所有模块
2. 如有需要，读取特定模块的 DETAIL.md 了解详情
3. 判断：
   - 是否有功能相似的模块应该合并？
   - 是否有过大的模块应该拆分？
   - 模块命名是否准确反映功能？
   - 模块顺序是否符合依赖逻辑（底层在前，顶层在后）？
4. 通过 doc_operation 执行调整
5. 最终检查 INDEX.md 的完整性

## 约束

- 不要手动编辑 DETAIL.md 或 INDEX.md 的文本
- 所有调整必须通过 doc_operation 工具
- 每次操作后检查结果是否正确
```

#### 2.5.2 doc_operation 的实现原理

所有操作基于 DETAIL 和 INDEX 中的 HTML 注释标记：

| 操作 | 标记定位 | 具体行为 |
|------|---------|---------|
| move_detail | `<!-- file:xxx -->` ... `<!-- end:xxx -->` | 从源 DETAIL 提取该块，追加到目标 DETAIL |
| merge_modules | `<!-- module:xxx -->` | 将源模块的所有文件块追加到目标模块 DETAIL，删除源 DETAIL 文件，合并 INDEX 摘要 |
| split_module | `<!-- file:xxx -->` | 根据 files 分组，将文件块分到新的 DETAIL 文件中，生成新的 INDEX 条目 |
| update_index | `<!-- module-index:xxx -->` | 替换标记之间的内容 |
| reorder_modules | `<!-- module-index:xxx -->` | 按指定顺序重排 INDEX 中的模块块 |

---

## 三、实施优先级

| 优先级 | 任务 | 改动范围 | 依赖 |
|--------|------|---------|------|
| **P0** | 智能范围排除（.venv 等） | `codebase.py`, `server.py` | 无 |
| **P0** | GroupingStrategy 协议 + TwoStageStrategy | 新文件 `src/graph/strategies.py` | 无 |
| **P0** | FunctionalModule 统一数据结构 | `src/state/models.py` | 无 |
| **P1** | get_modules 重设计（summary / detail 模式） | `server.py` | P0 |
| **P1** | get_function_deps 新 Tool | `server.py`, 扩展 parser | P0 |
| **P1** | get_dependency_graph 默认模块级 | `server.py`, `server_helpers.py` | P0 |
| **P2** | 固定格式 DETAIL/INDEX 模板 | SKILL.md, 新增模板文件 | P1 |
| **P2** | Sub-agent 执行协议（token 预算驱动） | SKILL.md | P1 |
| **P2** | INDEX 拼合逻辑 | SKILL.md | P2 |
| **P3** | doc_operation Tool（Phase 5 重组工具） | `server.py` | P2 |
| **P3** | Phase 5 重组 Agent prompt | SKILL.md | P3 |
| **P4** | FusionStrategy（DIS 增强图） | `src/graph/strategies.py` | P0 |
| **P4** | DirectoryFirstStrategy | `src/graph/strategies.py` | P0 |
| **P5** | 扩展 ground truth + scoring harness 对接 | `tests/` | P0 |

---

## 四、与 V4 方案的关系

V4（`05_v4_architecture_detection_redesign.md`）的方案 **部分保留、部分替代**：

| V4 提案 | V5 态度 | 说明 |
|---------|---------|------|
| 智能范围过滤 | **保留** | V5 直接采纳 |
| 目录共位边 + DIS | **推迟到 P4** | 作为 FusionStrategy 实现 |
| SCC 预处理 | **推迟** | 可作为 TwoStageStrategy 的增强 |
| 删 python-louvain | **保留** | 统一 NetworkX |
| 删 D1-D7 评分 | **保留** | 只保留 ARI/NMI |
| 扩展 ground truth | **保留** | 移至 P5 |
| MCP 输出格式（summary/detail） | **替代** | V5 设计了更完整的 get_modules 接口 |
| Skill 删 Phase 2 | **替代** | V5 重新设计了 5 个 Phase 的职责 |

---

## 五、已排除的方向

（继承自 V4，补充新条目）

| 方向 | 排除原因 |
|------|---------|
| Leiden 替换 Louvain | GPL-3.0 与 MIT 不兼容 |
| MCP 生成函数描述 | 违反"确定性分析 vs 语义理解"职责分离 |
| MCP 返回函数签名/docstring | 不需要，LLM 自己读源码获取 |
| 单次全量 dump 所有模块详情 | 必然导致上下文溢出 |
| LLM 手动编辑 DETAIL/INDEX 文本 | 不可控，用 doc_operation 工具替代 |
| Phase 2 验证 Agent（V4 提议保留后删除） | JSON 无语义，验证无意义 |

---

## 六、效果预期

| 改进 | 预期效果 | 信心度 |
|------|---------|--------|
| 智能范围排除 | 12,907 文件 → ~24 文件（自身项目），消除 99% 噪声 | 确定 |
| get_modules summary 模式 | 90K 字符 → ~2K 字符的摘要返回 | 确定 |
| get_dependency_graph 模块级 | 11.5MB → ~1K 字符的模块间图 | 确定 |
| 固定格式 DETAIL + INDEX | 从"空洞 API reference"→ 有函数描述和依赖关系的架构文档 | 高 |
| Token 预算驱动 | sub-agent 不再溢出上下文 | 高 |
| doc_operation 工具化 | Phase 5 重组可控、可重复 | 中高 |
| TwoStageStrategy | 对 5 个测试 repo 的 ARI 预期改善（目录后处理纠正） | 中 |
