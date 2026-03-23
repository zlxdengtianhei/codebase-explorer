# 职责分离优化 V2

> 本文档由 T-02c 任务产出，基于 T-01（当前架构分析）、V1 职责分离设计、V1 问题诊断，
> 以及核心需求愿景文档，给出完整的 MCP Server / Skill / Agent 三层职责边界增强版设计。
>
> **状态**: 设计规范文档，禁止修改源文件。

---

## Section 1: V1 → V2 改进摘要

V1 设计在三个维度上犯了系统性错误，V2 逐一修正：

| V1 中模糊或错误的地方 | V2 的澄清与纠正 |
|----------------------|----------------|
| MCP Server 兼任代码解析、任务调度、Jinja2 文档生成三件事 | 严格三层分离：MCP 做确定性计算，Skill 做编排调度，Agent 做语义理解和文档撰写 |
| `generate_doc()` 用 Jinja2 模板渲染文档，不涉及任何 LLM 调用 | 文档撰写全权移交 LLM Agent，MCP Server 不再持有任何 Jinja2 逻辑 |
| Agent 没有读取源码的工具，`submit_analysis()` 传入空数据 | Agent 使用内置文件读取能力直接读磁盘源码；MCP 提供文件路径和结构索引 |
| 15 个 MCP 工具，其中 6 个与文档生成直接相关，9 个高度重叠 | 精简为 7 个工具（6 个查询工具 + 1 个完成回调），职责边界清晰 |
| SQLite WAL + 5 张表 + Checkpoint 系统，为单 Agent 顺序流程过度设计 | 替换为单一 `state.json` 文件，支持原子写入和断点恢复 |
| Louvain 社区检测作为唯一分组主力，丢失有向图信息 | 主力改为 SCC + DAG 分层（功能锥体提取），Louvain 降为扁平目录的辅助工具 |
| Token 估算用行数 × 系数（误差 ±50%） | 改用字符数 ÷ 4（误差 < 15%），文件级粒度 |
| 模块命名为 `module_0`、`module_7`，无语义 | 功能锥体以 DAG 入口文件名或目录名命名，如 `cone_cli`、`cone_request_handling` |
| `create_analysis_plan`、`plan_doc_structure` 需要多次独立调用 | 合并进 `analyze_codebase`，一次调用完成全部分析，写出 5 个 JSON 文件 |
| Phase 3（分析）和 Phase 4（生成）之间数据管道断裂，内容空洞 | 消除 Phase 4（Jinja2 生成）；Phase 3 Agent 直接写 DETAIL.md，数据不经 SQLite 中转 |
| `save_checkpoint` / `load_checkpoint` 与任务状态分离，逻辑分散 | `state.json` 的 task status 字段即为断点标记，无需额外 Checkpoint 系统 |
| `get_cross_ref_context` 从空数据库拼接空上下文 | INDEX Agent 直接读取各 SNIPPET.md 文件，上下文由实际文档内容构成 |

### V2 三层职责边界（最终版）

```
MCP Server（确定性，零 LLM）
  职责: 代码解析、加权依赖图、SCC/DAG/Louvain、功能锥体提取、Token 估算、任务装箱分配
  输出: 5 个 JSON 文件 + state.json（写入 {codebase}/.codebase-analysis/）
  不做: 任何文档撰写、任何 LLM 判断、任何内容生成

Skill（编排层，零 LLM 直接决策）
  职责: 读取 05_task_manifest.json 决定 Agent 调度顺序、更新 state.json 任务状态
  输入: 5 个 JSON 文件（分析结果）
  输出: 调度指令，不直接写文档
  不做: 读取源码、做语义判断

Agent（LLM 智能层）
  职责: 读源码文件 → 理解语义 → 撰写 DETAIL.md 和 SNIPPET.md → 调用 submit_analysis
  输入: 源码文件路径（由 task_manifest 指定）+ 03_feature_cones.json（架构骨架）
  输出: {cone}/DETAIL.md + {cone}/SNIPPET.md（直接写入磁盘）
  不做: 运行任何图算法、做任何确定性计算
```

---

## Section 2: 6 个新 MCP 工具完整 API 设计

### Tool 1: `analyze_codebase` — 全流水线入口

**定位**: 一次调用完成全部确定性分析，写出 5 个 JSON 文件和 `state.json`，供后续所有 Agent 使用。

```python
async def analyze_codebase(
    path: str,
    languages: list[str] | None = None,
    output_dir: str | None = None,
    force_reindex: bool = False,
) -> dict:
    """
    运行完整分析流水线（纯确定性，零 LLM）:
      1. CodebaseParser.parse(path, languages) → CodebaseSnapshot
         （graph-sitter 解析：FileInfo + FunctionInfo + ClassInfo）
      2. build_weighted_dependency_graph(snapshot) → nx.DiGraph
         （import 边权重 1，函数调用边权重 2，继承边权重 3）
      3. nx.strongly_connected_components(graph) → SCC 检测
         （找出互相依赖、必须一起文档化的最小单元）
      4. nx.condensation(graph) → DAG（有向无环图）
         → topological_order() → 分层列表 [[layer0], [layer1], ...]
      5. extract_feature_cones(dag, snapshot) → 功能锥体列表
         （每个 cone 是从入口文件到底层实现的完整依赖链）
      6. estimate_tokens_per_file(snapshot) → {filepath: token_count}
         （字符数 ÷ CHARS_PER_TOKEN，Python=3.5, TS=4.0, JS=3.8）
      7. pack_tasks(cones, file_tokens) → task_manifest
         （贪心装箱：token 降序，每 batch < 100k，生成 batch/single/split 任务）
      8. 写出 5 个 JSON 文件 + state.json 到 output_dir

    参数说明:
      path: 代码库根目录的绝对路径
      languages: 限定分析语言；None = 自动检测
      output_dir: JSON 文件写入目录；None = {path}/.codebase-analysis/
      force_reindex: False 时，若 output_dir 已存在且 5 个文件完整，直接返回缓存结果

    返回值 Schema:
    {
        "status": "success",
        "project_id": str,              # sha256(path)[:12]，用于幂等性去重
        "output_dir": str,              # 实际写入目录的绝对路径
        "files_analyzed": int,          # 解析到的源文件总数
        "feature_cones_found": int,     # 提取出的功能锥体数量（主分组）
        "modules_louvain": int,         # Louvain 辅助分组数（用于扁平目录）
        "task_count": int,              # task_manifest 中的总任务数
        "total_tokens": int,            # 所有源文件 token 估算之和
        "files": {
            "01_structure":     str,    # 绝对路径: 01_structure.json
            "02_dag":           str,    # 绝对路径: 02_dag.json
            "03_feature_cones": str,    # 绝对路径: 03_feature_cones.json
            "04_file_tokens":   str,    # 绝对路径: 04_file_tokens.json
            "05_task_manifest": str,    # 绝对路径: 05_task_manifest.json
        },
        "state_file": str,              # 绝对路径: state.json
    }
    """
```

**设计说明**:
- `project_id` 使用路径的 SHA256 前 12 位，确保同一项目多次分析复用同一 ID
- `force_reindex=False` 时，若 `.codebase-analysis/` 目录已存在且所有 5 个 JSON 文件完整，直接读取现有文件返回，跳过耗时解析
- 此工具替代 V1 的 `index_codebase` + `create_analysis_plan` + `plan_doc_structure` 三个调用

---

### Tool 2: `get_structure` — 查询代码结构

**定位**: 查询已分析的代码结构（文件、函数、类、依赖关系）。数据来自 `01_structure.json`，无需重新解析。

```python
async def get_structure(
    module: str | None = None,
    file: str | None = None,
    function: str | None = None,
) -> dict:
    """
    从 01_structure.json 查询代码结构信息。三个参数互斥，至多提供一个。

    当 module 不为 None（按模块/功能锥体查询）:
      返回该功能锥体包含的所有文件列表，以及每个文件的函数名、类名、import 路径列表。
      {
          "query_type": "module",
          "module_name": str,
          "files": [
              {
                  "filepath": str,
                  "language": str,
                  "line_count": int,
                  "function_names": [str],
                  "class_names": [str],
                  "import_sources": [str],   # 已解析的绝对路径
              }
          ],
          "file_count": int,
          "total_functions": int,
          "total_classes": int,
      }

    当 file 不为 None（按文件查询）:
      返回该文件的函数签名、类定义、import 关系、被哪些文件 import（反向索引）。
      {
          "query_type": "file",
          "filepath": str,
          "language": str,
          "line_count": int,
          "functions": [
              {
                  "name": str,
                  "line_start": int,
                  "line_end": int,
                  "calls": [str],          # 调用的函数名列表
                  "dependencies": [str],   # 依赖的文件绝对路径列表
              }
          ],
          "classes": [
              {
                  "name": str,
                  "base_classes": [str],   # 父类名列表（字符串，非路径）
                  "methods": [str],
              }
          ],
          "import_sources": [str],         # 该文件 import 的其他文件路径
          "imported_by": [str],            # 哪些文件 import 了本文件（反向索引）
      }

    当 function 不为 None（按函数查询）:
      返回该函数的签名、所在文件、跨文件依赖（dependencies 字段）。
      {
          "query_type": "function",
          "function_name": str,
          "matches": [                     # 同名函数可能出现在多个文件
              {
                  "filepath": str,
                  "line_start": int,
                  "line_end": int,
                  "calls": [str],
                  "dependencies": [str],   # FunctionInfo.dependencies（文件路径列表）
              }
          ],
      }

    当三个参数均为 None（返回整体摘要）:
      {
          "query_type": "summary",
          "file_count": int,
          "function_count": int,
          "class_count": int,
          "language_breakdown": {"python": int, "typescript": int},
          "most_imported_files": [{"filepath": str, "import_count": int}],
          "circular_deps": [[str, str, ...]],
      }
    """
```

**设计说明**:
- `file` 参数支持绝对路径或相对于项目根目录的相对路径
- `imported_by` 字段是预计算的反向索引，存储在 `01_structure.json` 中，`analyze_codebase` 时生成
- 替代 V1 的 `get_modules` 和 `get_module_detail` 两个工具

---

### Tool 3: `get_feature_cones` — 查询功能锥体

**定位**: 查询功能分组结果（功能锥体）。数据来自 `03_feature_cones.json`，无需重新计算。

```python
async def get_feature_cones(
    cone_id: str | None = None,
) -> dict:
    """
    返回功能锥体（Feature Cone）信息。数据来自 03_feature_cones.json。

    一个 Feature Cone 代表一个由 DAG 依赖关系决定的功能单元：
      - 包含从入口文件（高 PageRank / DAG 最上层）到底层实现的完整依赖链
      - cone 内的文件在功能上紧密关联（互相依赖或同属一条依赖路径）
      - cone 之间可能有共享依赖（标记为 shared_deps）

    当 cone_id 为 None（返回所有锥体的摘要列表）:
    {
        "status": "success",
        "total_cones": int,
        "cones": [
            {
                "cone_id": str,           # e.g., "cone_cli"
                "name": str,              # 语义名称（入口文件名或目录名）
                "entry_file": str,        # 入口文件绝对路径（DAG 最上层）
                "is_utility": bool,       # 是否为共享基础组件
                "file_count": int,
                "total_tokens": int,
                "layer": int,             # 在全局 DAG 中的层级（0=底层依赖）
            }
        ],
    }

    当 cone_id 不为 None（返回该锥体的完整详情）:
    {
        "status": "success",
        "cone_id": str,
        "name": str,
        "entry_file": str,
        "is_utility": bool,
        "file_count": int,
        "total_tokens": int,
        "layer": int,
        "files": [str],                   # 锥体内所有文件的绝对路径列表
        "layers": [                       # 锥体内部的 DAG 分层（from bottom to entry）
            {
                "depth": int,             # 0 = 最底层实现
                "files": [str],
                "tokens": int,
            }
        ],
        "shared_deps": [str],             # 被多个 cone 共享的文件路径
        "depends_on_cones": [str],        # 该 cone 依赖的其他 cone ID
    }
    """
```

**设计说明**:
- 功能锥体（Feature Cone）是 V2 的核心概念，取代 V1 的 Louvain 社区"模块"
- `cone_id` 是唯一标识符（如 `cone_cli`），`name` 是语义名称（可能相同也可能不同）
- `shared_deps` 字段显式标注跨 cone 的共享文件，避免在多处重复文档化同一文件
- DETAIL Agent 在撰写文档前调用此工具获取 `files` 和 `layers`，明确文档化范围

---

### Tool 4: `get_dependency_graph` — 依赖图（增强版）

**定位**: 生成 Mermaid 依赖图。数据来自 `02_dag.json`。V2 相比 V1 增加 `scope="file"` 和 `include_weights` 参数。

```python
async def get_dependency_graph(
    scope: Literal["project", "cone", "file"] = "project",
    target: str | None = None,
    include_weights: bool = False,
) -> dict:
    """
    生成 Mermaid 依赖图。数据来自 02_dag.json。

    scope="project":
      全项目功能锥体级依赖图（节点 = 功能锥体，边 = 跨 cone 依赖）
      target: 不需要（忽略）

    scope="cone":
      单个功能锥体内部的文件级依赖图
      target: cone_id（如 "cone_request_handling"）

    scope="file":
      以单个文件为中心，显示其直接依赖和被直接依赖关系（前后各一跳）
      target: 文件路径（绝对路径或相对路径）

    include_weights=True 时，在 Mermaid 边标签上显示边类型：
      import=1, call=2, inherit=3（来自 build_weighted_dependency_graph）

    返回值 Schema:
    {
        "status": "success",
        "scope": str,
        "target": str | None,
        "mermaid_graph": str,         # 完整的 Mermaid graph 语法字符串
        "node_count": int,            # 图中节点数
        "edge_count": int,            # 图中边数
        "circular_deps": [            # 循环依赖列表（SCC > 1 的节点集合）
            [str, str, ...]
        ],
    }
    """
```

**设计说明**:
- `scope="cone"` 是 V2 新增的，支持"查看某功能锥体内部文件依赖"的需求
- `circular_deps` 列出 SCC 中超过 1 个节点的强连通分量，这些必须一起文档化
- 数据来自预计算的 `02_dag.json`，不重新解析代码库

---

### Tool 5: `get_progress` — 任务完成状态

**定位**: 查询文档化任务的完成进度。数据来自 `state.json`。替代 V1 的三个工具。

```python
async def get_progress(
    project_id: str | None = None,
) -> dict:
    """
    查询 state.json 中的任务完成状态和文档覆盖率。

    用于 Skill 判断：
      - 哪些 DETAIL Agent 任务已完成
      - 哪些任务待执行或失败需要重试
      - 整体完成百分比和文档覆盖率

    直接读取 {project_root}/.codebase-analysis/state.json，不访问 SQLite。

    返回值 Schema:
    {
        "status": "success",
        "project_id": str,
        "tasks": {
            "total": int,
            "pending": int,
            "in_progress": int,
            "complete": int,
            "failed": int,
            "progress_percent": float,    # complete / total * 100
        },
        "documentation": {
            "output_dir": str,
            "index_written": bool,        # INDEX.md 是否已写入
            "details_written": int,       # 磁盘上已存在的 DETAIL.md 数
            "snippets_written": int,      # 磁盘上已存在的 SNIPPET.md 数
            "total_planned": int,         # task_manifest 规划的总文档数
            "source_file_coverage_percent": float,  # 覆盖的源文件比例 * 100
        },
        "next_pending_tasks": [           # 当前可以执行的 pending task ID 列表
            str
        ],
    }
    """
```

**设计说明**:
- 直接读取 `state.json`，不访问任何数据库
- `source_file_coverage_percent` 由 MCP Server 从 `state.json.documentation.source_files_covered` 计算
- 替代 V1 的 `get_analysis_status`、`check_budget_status`、`load_checkpoint` 三个工具

---

### Tool 6: `get_file_tokens` — 每文件 Token 估算

**定位**: 返回文件级 Token 估算。数据来自 `04_file_tokens.json`。

```python
async def get_file_tokens(
    file: str | None = None,
    module: str | None = None,
) -> dict:
    """
    返回文件级 Token 估算明细。数据来自 04_file_tokens.json。

    估算方法: 字符数 ÷ CHARS_PER_TOKEN（误差 < 15%）
    CHARS_PER_TOKEN = {"python": 3.5, "typescript": 4.0, "javascript": 3.8}

    当 file 和 module 均为 None（返回所有文件）:
    {
        "status": "success",
        "total_tokens": int,
        "file_count": int,
        "files": [
            {
                "filepath": str,         # 相对于项目根目录的路径
                "language": str,
                "char_count": int,
                "line_count": int,
                "estimated_tokens": int,
                "method": "chars_div_4",
                "cone_id": str | None,   # 所属功能锥体 ID
            }
        ],
    }

    当 file 不为 None（返回单文件的 token 明细）:
    {
        "status": "success",
        "filepath": str,
        "language": str,
        "char_count": int,
        "line_count": int,
        "estimated_tokens": int,
        "method": "chars_div_4",
        "cone_id": str | None,
    }

    当 module 不为 None（返回该功能锥体的所有文件 + 聚合统计）:
    {
        "status": "success",
        "cone_id": str,
        "file_count": int,
        "total_tokens": int,
        "avg_tokens_per_file": float,
        "max_file_tokens": int,
        "files": [
            {
                "filepath": str,
                "char_count": int,
                "line_count": int,
                "estimated_tokens": int,
                "method": "chars_div_4",
            }
        ],
    }
    """
```

**设计说明**:
- 使用字符数 ÷ 4 方法（替代 V1 的行数 × 12），误差从 ±50% 降至 < 15%
- `module` 参数接受 cone_id，返回该锥体内所有文件的聚合统计
- Skill 用 `module` 查询验证任务装箱是否合理（每 batch < 100k tokens）

---

### Tool 7（回调工具）: `submit_analysis` — DETAIL Agent 完成回调

**定位**: DETAIL Agent 写完文件后调用，注册完成信号并更新 `state.json`。

```python
async def submit_analysis(
    task_id: str,
    detail_paths: list[str],
    snippet_paths: list[str],
    tokens_used: int,
    source_files_covered: list[str] | None = None,
    project_id: str | None = None,
) -> dict:
    """
    DETAIL Agent 完成写文件后调用，注册完成信号并原子更新 state.json。

    参数:
      task_id: 来自 05_task_manifest.json 的任务 ID
      detail_paths: 已写入磁盘的 DETAIL.md 绝对路径列表
      snippet_paths: 已写入磁盘的 SNIPPET.md 绝对路径列表
      tokens_used: Agent 自报的 token 消耗量（用于统计）
      source_files_covered: 本次文档覆盖的源文件路径列表（用于覆盖率计算）
      project_id: 项目 ID；None = 使用最近一次 analyze_codebase 的结果

    MCP Server 执行步骤:
      1. 验证 detail_paths 和 snippet_paths 中的文件确实存在于磁盘（非空）
      2. 原子更新 state.json:
           tasks[task_id].status = "complete"
           tasks[task_id].completed_at = utcnow()
           tasks[task_id].output_files[*].status = "complete"
           documentation.details_written += len(detail_paths)
           documentation.snippets_written += len(snippet_paths)
           documentation.source_files_covered += source_files_covered（去重）
           documentation.source_file_coverage_percent = 重新计算
      3. 原子写入：先写 state.json.tmp，再 os.replace → state.json

    返回值 Schema:
    {
        "status": "success",
        "task_id": str,
        "tasks_remaining": int,           # 仍为 pending 或 in_progress 的任务数
        "progress_percent": float,        # complete / total * 100
        "source_file_coverage_percent": float,
    }
    """
```

**与 V1 submit_analysis 的关键区别**:
- V1 要求传入 `description`、`public_interfaces`、`key_data_structures` 等 10 个内容字段，存入 SQLite
- V2 只需 5 个参数，仅注册文件路径和统计数据，文档内容由 Agent 直接写入磁盘

---

## Section 3: 工具迁移映射表（旧 15 → 新 7）

以下完整说明每一个 V1 工具的去向：

| 旧工具 | 处置方式 | 归入 V2 工具 / 原因 |
|--------|---------|-------------------|
| `index_codebase` | MERGED | `analyze_codebase` — 解析、建图、分组、写 JSON 全部整合进一次调用 |
| `get_modules` | MERGED | `get_feature_cones` — V1"模块"概念升级为"功能锥体"；概念不同但数据对等 |
| `get_module_detail` | MERGED | `get_structure(module=...)` — 文件列表和函数/类详情由 get_structure 按锥体查询返回 |
| `get_dependency_graph` | KEPT + ENHANCED | `get_dependency_graph` — 同名工具保留；新增 `scope="file"`，`include_weights` 参数 |
| `estimate_module_tokens` | MERGED | `get_file_tokens` — 粒度从模块级细化到文件级；估算算法从行数×系数改为字符数÷4 |
| `create_analysis_plan` | DELETED（内化） | `analyze_codebase` — DAG 拓扑排序 + 任务装箱算法在 analyze_codebase 内部完成，结果写入 05_task_manifest.json |
| `check_budget_status` | DELETED（内化） | `get_progress` — Token 预算在 analyze_codebase 装箱时已验证；运行时预算由 get_progress.documentation 替代 |
| `get_next_batch` | DELETED | Skill 直接读 `05_task_manifest.json` — Skill 不再需要通过 MCP 查询下一批，直接遍历 JSON 中 status="pending" 的任务 |
| `submit_analysis` | MODIFIED（大幅简化） | `submit_analysis`（V2 简化版）— 从 10 个内容字段简化为 5 个路径/统计字段；不再写 SQLite，改为更新 state.json |
| `get_analysis_status` | MERGED | `get_progress` — 任务状态汇总完全由 get_progress 返回，合并了 analysis_status 和 checkpoint 信息 |
| `save_checkpoint` | DELETED | 不需要 — `state.json` 中的 task status 字段（in_progress / complete）即为断点标记，无需额外 checkpoint 机制 |
| `load_checkpoint` | DELETED | 不需要 — Skill 启动时读 `state.json`，找到 in_progress 或 pending 的任务自动续行（恢复算法见 Section 5） |
| `get_cross_ref_context` | DELETED | Agent 直接读 SNIPPET.md — V2 中 SNIPPET.md 文件即是跨引用上下文；INDEX Agent 直接读所有 SNIPPET.md，无需 MCP 工具拼接 |
| `plan_doc_structure` | DELETED（内化） | `analyze_codebase` — 文档树规划（功能锥体提取、深度计算、Token 预算分配）在 analyze_codebase 内部完成，结果写入 05_task_manifest.json |
| `generate_doc` | DELETED（移交 Agent） | 无对应工具 — 文档撰写是 LLM Agent 的责任，不是 MCP Server 的责任；Jinja2 渲染在 V2 中完全移除 |

**净效果**: 15 个工具精简为 7 个（6 个查询工具 + 1 个完成回调），每个工具职责唯一且明确。

---

## Section 4: JSON 状态文件完整 Schema

取代 V1 的 SQLite + 5 张表 + Checkpoint 系统。存储路径：`{codebase_path}/.codebase-analysis/state.json`。

```json
{
  "schema_version": "2.0",

  "project": {
    "id": "a3f9c2b1d4e8",
    "root_path": "/path/to/flask",
    "analyzed_at": "2026-03-23T10:30:00Z",
    "languages": ["python"],
    "file_count": 24,
    "function_count": 150,
    "class_count": 25,
    "total_lines": 2600,
    "total_chars": 94400,
    "total_tokens": 23600,
    "analysis_status": "complete"
  },

  "analysis_files": {
    "01_structure":     "01_structure.json",
    "02_dag":           "02_dag.json",
    "03_feature_cones": "03_feature_cones.json",
    "04_file_tokens":   "04_file_tokens.json",
    "05_task_manifest": "05_task_manifest.json"
  },

  "tasks": {
    "task_001": {
      "type": "batch",
      "status": "complete",
      "cone_ids": ["cone_cli", "cone_json"],
      "estimated_tokens": 18400,
      "output_files": [
        {
          "path": ".codebase-docs/cli/DETAIL.md",
          "tokens_written": 1340,
          "status": "complete"
        },
        {
          "path": ".codebase-docs/cli/SNIPPET.md",
          "tokens_written": 280,
          "status": "complete"
        },
        {
          "path": ".codebase-docs/json/DETAIL.md",
          "tokens_written": 920,
          "status": "complete"
        },
        {
          "path": ".codebase-docs/json/SNIPPET.md",
          "tokens_written": 210,
          "status": "complete"
        }
      ],
      "started_at": "2026-03-23T10:35:00Z",
      "completed_at": "2026-03-23T10:36:45Z",
      "error": null
    },

    "task_002": {
      "type": "single",
      "status": "in_progress",
      "cone_ids": ["cone_request_handling"],
      "estimated_tokens": 42000,
      "output_files": [
        {
          "path": ".codebase-docs/request_handling/DETAIL.md",
          "tokens_written": null,
          "status": "pending"
        },
        {
          "path": ".codebase-docs/request_handling/SNIPPET.md",
          "tokens_written": null,
          "status": "pending"
        }
      ],
      "started_at": "2026-03-23T10:37:00Z",
      "completed_at": null,
      "error": null
    },

    "task_003": {
      "type": "split",
      "status": "pending",
      "cone_ids": ["cone_core_engine"],
      "estimated_tokens": 85000,
      "split_subtasks": ["task_003a", "task_003b"],
      "output_files": [],
      "started_at": null,
      "completed_at": null,
      "error": null
    },

    "task_003a": {
      "type": "split_part",
      "status": "pending",
      "cone_ids": ["cone_core_engine"],
      "split_layer": 0,
      "estimated_tokens": 41000,
      "output_files": [
        {
          "path": ".codebase-docs/core_engine/layer0/DETAIL.md",
          "tokens_written": null,
          "status": "pending"
        },
        {
          "path": ".codebase-docs/core_engine/layer0/SNIPPET.md",
          "tokens_written": null,
          "status": "pending"
        }
      ],
      "started_at": null,
      "completed_at": null,
      "error": null
    },

    "task_003b": {
      "type": "split_part",
      "status": "pending",
      "cone_ids": ["cone_core_engine"],
      "split_layer": 1,
      "estimated_tokens": 44000,
      "output_files": [
        {
          "path": ".codebase-docs/core_engine/layer1/DETAIL.md",
          "tokens_written": null,
          "status": "pending"
        },
        {
          "path": ".codebase-docs/core_engine/layer1/SNIPPET.md",
          "tokens_written": null,
          "status": "pending"
        }
      ],
      "started_at": null,
      "completed_at": null,
      "error": null
    },

    "index_assembly": {
      "type": "index",
      "status": "pending",
      "depends_on": ["task_001", "task_002", "task_003"],
      "cone_ids": [],
      "estimated_tokens": 0,
      "output_files": [
        {
          "path": ".codebase-docs/INDEX.md",
          "tokens_written": null,
          "status": "pending"
        },
        {
          "path": ".codebase-docs/doc-index.json",
          "tokens_written": null,
          "status": "pending"
        }
      ],
      "started_at": null,
      "completed_at": null,
      "error": null
    }
  },

  "documentation": {
    "output_dir": ".codebase-docs/",
    "index_written": false,
    "overviews_written": 0,
    "details_written": 2,
    "snippets_written": 2,
    "total_planned": 12,
    "source_files_covered": [
      "src/cli.py",
      "src/json_utils.py"
    ],
    "source_file_coverage_percent": 8.3,
    "total_tokens_written": 2750
  },

  "metadata": {
    "codebase_explorer_version": "2.0.0",
    "created_at": "2026-03-23T10:30:00Z",
    "last_updated_at": "2026-03-23T10:36:45Z",
    "graph_algorithm": "scc_dag_louvain_fallback",
    "token_estimation_method": "chars_div_4"
  }
}
```

### Schema 设计要点

1. **任务粒度**: `tasks` 字典以 `task_id` 为键，支持 O(1) 状态查询和更新，无需遍历数组
2. **子任务支持**: `type="split"` 的任务包含 `split_subtasks` 字段，引用各子任务 ID；子任务独立执行
3. **文件级跟踪**: 每个任务内的 `output_files` 数组跟踪单个 DETAIL.md/SNIPPET.md 状态，实现文件级精度的断点恢复
4. **并发安全**: 只有 Skill 层通过 MCP `submit_analysis` 更新 `state.json`，Agent 只写 Markdown 文件，无并发写冲突
5. **覆盖率计算**: `documentation.source_files_covered` 由 `submit_analysis` 追加，`source_file_coverage_percent = len(covered) / project.file_count * 100`
6. **原子写入**: 所有写操作先写 `state.json.tmp`，再 `os.replace(tmp, state.json)`，防止写入中断导致 JSON 损坏

---

## Section 5: 断点恢复机制详细设计

### 恢复场景

当一个 DETAIL Agent 在执行 `task_002` 时崩溃或超时，`state.json` 中留下 `"status": "in_progress"` 但 `completed_at` 为 null，且输出文件的 `status` 仍为 `"pending"`。下次 Skill 启动时必须能够正确处理这种状态。

### 恢复算法（伪代码）

```
FUNCTION resume_from_state(project_root):
    state_path = join(project_root, ".codebase-analysis/state.json")
    state = read_json(state_path)
    tasks = state["tasks"]
    modified = False

    # Step 1: 处理 in_progress 任务（可能是崩溃遗留）
    FOR task_id, task IN tasks.items() WHERE task["status"] == "in_progress":
        all_files_complete = True
        FOR output_file IN task["output_files"]:
            full_path = join(project_root, output_file["path"])
            IF NOT file_exists(full_path):
                all_files_complete = False
                BREAK
            IF file_size(full_path) < 200:   # 排除意外创建的空文件
                all_files_complete = False
                BREAK
            IF NOT file_ends_with_marker(full_path, "<!-- codebase-explorer: end -->"):
                all_files_complete = False
                BREAK

        IF all_files_complete:
            # 文件已写完，只是 submit_analysis 未被调用（Agent 崩溃在最后一步）
            FOR output_file IN task["output_files"]:
                output_file["status"] = "complete"
                output_file["tokens_written"] = estimate_file_tokens(output_file["path"])
            task["status"] = "complete"
            task["completed_at"] = utcnow()
            modified = True
        ELSE:
            # 文件未写完，重置为 pending 等待重新执行
            task["status"] = "pending"
            task["started_at"] = null
            FOR output_file IN task["output_files"]:
                output_file["status"] = "pending"
                output_file["tokens_written"] = null
            modified = True

    IF modified:
        # Step 1b: 原子写入更新后的 state
        write_tmp = state_path + ".tmp"
        write_json(write_tmp, state)
        os.replace(write_tmp, state_path)

    # Step 2: 收集可执行的 pending 任务（依赖项已全部 complete）
    pending_tasks = []
    FOR task_id, task IN tasks.items():
        IF task["status"] != "pending":
            CONTINUE
        deps = task.get("depends_on", [])
        IF ALL(tasks[dep]["status"] == "complete" FOR dep IN deps):
            pending_tasks.append(task_id)

    # Step 3: 按 task_manifest 中的原始顺序恢复执行
    task_order = read_json(
        join(project_root, ".codebase-analysis/05_task_manifest.json")
    )["task_order"]
    ordered_pending = [t for t in task_order IF t IN set(pending_tasks)]

    RETURN ordered_pending   # 按顺序依次派发给 DETAIL Agent

END FUNCTION
```

### 文件完整性判断规则

| 规则 | 说明 |
|------|------|
| 文件存在 | `Path(output_file.path).exists()` 为 True |
| 文件非空 | 文件大小 > 200 字节，排除意外创建的空文件 |
| 包含结束标记 | 文件末尾最后 10 行包含 `<!-- codebase-explorer: end -->` |

DETAIL Agent 在写完 DETAIL.md 和 SNIPPET.md 后，必须在每个文件末尾追加 `<!-- codebase-explorer: end -->` 作为完整写入的信号。若无此标记，视为写入中断，重置为 `pending`。

### 状态转换图

```
                      Skill 标记任务开始
pending ──────────────────────────────────► in_progress
  ▲                                              │
  │                                             ├──── Agent 完成写文件 ────► Agent 调用 submit_analysis
  │  恢复算法:                                   │                                    │
  │  文件不完整/无结束标记                        │                                    ▼
  │                                             │                               complete ◄──── 恢复算法:
  └────────────────── in_progress ◄─────────────┘                                            文件已完整
                            │
                            │ 连续 3 次尝试后仍失败
                            ▼
                         failed
                            │
                            │ Skill 手动重置（可选）
                            ▼
                         pending（重试）
```

### `state.json` 原子写入实现

```python
import os, json, tempfile
from pathlib import Path

def atomic_write_state(state_path: Path, state: dict) -> None:
    """原子写入 state.json，防止写入中断导致 JSON 损坏。"""
    tmp_path = state_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, state_path)  # POSIX 原子操作
```

---

## Section 6: `submit_analysis()` 最终决策

### 两个候选方案

**Option A: 删除 `submit_analysis`，Skill 轮询文件系统**
- Skill 在派发任务后定期扫描磁盘，检测 DETAIL.md 是否出现
- Agent 不需要主动通知，只需写文件
- 问题: Skill 需要持续轮询，并需读取文件内容估算 token 数；Agent 无法传递 `source_files_covered` 信息

**Option B: 保留简化版 `submit_analysis`，作为显式完成回调**
- Agent 写完文件后主动调用 `submit_analysis(task_id, detail_paths, snippet_paths, ...)`
- MCP Server 验证文件存在并更新 `state.json`
- Agent 可以传递 `tokens_used` 和 `source_files_covered`

### 决策：选择 Option B

**理由**:

1. **显式信号比轮询更可靠**: Agent 天然知道"自己刚刚写完了什么"，一次显式回调比 Skill 轮询磁盘更清晰、无竞争条件
2. **覆盖率计算依赖 Agent 自报**: `source_files_covered` 列表只有 Agent 才知道（根据实际阅读了哪些文件），MCP Server 无法自动推断
3. **tokens_used 自报比重新计算准确**: Agent 知道自身消耗的 token 数（包括 prompt），比 MCP Server 重新读文件估算更精确
4. **状态一致性**: 一次 MCP 调用原子更新 `state.json` 的多个字段，避免 Skill 需要多步操作

### V2 最终签名（完整版）

```python
async def submit_analysis(
    task_id: str,                              # 来自 05_task_manifest.json 的任务 ID
    detail_paths: list[str],                   # 已写入磁盘的 DETAIL.md 绝对路径列表
    snippet_paths: list[str],                  # 已写入磁盘的 SNIPPET.md 绝对路径列表
    tokens_used: int,                          # Agent 自报的 token 消耗量（含 prompt）
    source_files_covered: list[str] | None = None,  # 本次覆盖的源文件路径列表
    project_id: str | None = None,             # None = 最近一次 analyze_codebase 的结果
) -> dict:
    """
    DETAIL Agent 完成写文件后调用的明确完成回调。

    MCP Server 执行：
      1. 验证 detail_paths 和 snippet_paths 中的文件存在于磁盘且非空
      2. 原子更新 state.json：
           tasks[task_id].status = "complete"
           tasks[task_id].completed_at = utcnow()
           tasks[task_id].output_files[i].status = "complete"
           tasks[task_id].output_files[i].tokens_written = (从文件实际读取后估算)
           documentation.details_written += len(detail_paths)
           documentation.snippets_written += len(snippet_paths)
           documentation.source_files_covered += source_files_covered（去重合并）
           documentation.source_file_coverage_percent = 重新计算
           metadata.last_updated_at = utcnow()
      3. 原子写入：先写 state.json.tmp，再 os.replace → state.json
    """
    return {
        "status": "success",
        "task_id": str,
        "tasks_remaining": int,
        "progress_percent": float,
        "source_file_coverage_percent": float,
    }
```

### V2 与 V1 submit_analysis 对比

| 维度 | V1 submit_analysis | V2 submit_analysis |
|------|-------------------|--------------------|
| 参数数量 | 10 个（大量内容字段） | 5-6 个（路径 + 统计） |
| 核心内容 | `description`、`public_interfaces`、`key_data_structures`、`dependencies`、`patterns_identified` 等结构化分析数据 | `detail_paths`、`snippet_paths`（文件已存在磁盘）|
| 存储目标 | SQLite `analysis_results` 表 | `state.json` 任务状态字段 |
| 文档内容流向 | 数据库 → Jinja2 → 输出骨架 | Agent 直接写磁盘 Markdown → 源文件无中转 |
| 覆盖率更新 | 不更新（V1 覆盖率为 0%） | 实时追加 `source_files_covered`，立即反映 |
| 验证 | 不验证内容（接受空字符串） | 验证文件物理存在且含结束标记 |

---

## Section 7: `src/` 文件去留决策表

以下列出 `src/` 目录下所有 24 个 `.py` 文件的处置方案：

| 文件 | 决策 | 所需具体变更 |
|------|------|------------|
| `src/server.py` | MODIFY | 移除全部 15 个旧工具及其 import；新增 7 个工具（analyze_codebase、get_structure、get_feature_cones、get_dependency_graph 增强版、get_progress、get_file_tokens、submit_analysis 简化版）；移除 aiosqlite、Jinja2、SQLite 相关 import；移除 `_lifespan` 中 Database / CheckpointManager / DocumentGenerator 初始化；新增 JSON 文件读写逻辑；新增 `get_file_content()` 内部辅助函数 |
| `src/__init__.py` | KEEP | 无变更 |
| `src/parser/codebase.py` | KEEP | 核心解析能力不变；`CodebaseParser.parse()` 和 `CodebaseSnapshot` 保持原样 |
| `src/parser/language_detect.py` | KEEP | 语言检测逻辑不变 |
| `src/parser/__init__.py` | KEEP | 无变更 |
| `src/graph/dependency.py` | MODIFY | 新增 `build_weighted_dependency_graph()` 函数，区分 import 边（权重 1）、函数调用边（权重 2）、继承边（权重 3）；新增 `class_name_to_file` 和 `function_name_to_file` 查找表，用于将类名/函数名字符串解析为文件路径；原 `build_dependency_graph()` 保留以向后兼容；新增 `get_file_dependency_subgraph(graph, file_path, hops=1)` 函数支持 scope="file" |
| `src/graph/grouper.py` | MODIFY | 新增 `extract_feature_cones(dag, snapshot)` 函数，基于 SCC 检测 + DAG 分层实现功能锥体提取（主力算法）；原 `group_modules()` Louvain 分组保留但降为辅助角色，仅在扁平目录（无明显目录层级结构）时调用；新增 `get_cone_metrics()` 函数返回 cone 粒度的统计指标 |
| `src/graph/ordering.py` | KEEP | DAG 拓扑排序逻辑正确；`topological_order()` 在 `analyze_codebase` 流水线中继续使用 |
| `src/graph/__init__.py` | KEEP | 无变更 |
| `src/budget/estimator.py` | MODIFY | 保留 `estimate_tokens_from_lines()` 函数（向后兼容，但标记为 deprecated）；新增主力函数 `estimate_tokens_from_chars(char_count, language)` 使用 `CHARS_PER_TOKEN = {"python": 3.5, "typescript": 4.0, "javascript": 3.8}`；新增 `estimate_file_tokens(file_path)` 直接读文件并返回估算结果 |
| `src/budget/controller.py` | DELETE | `AnalysisBudgetController` 类和 5 条停止规则整体删除；Token 预算验证移入 `analyze_codebase` 内部的装箱算法；运行时预算跟踪由 `state.json` 承担 |
| `src/budget/__init__.py` | MODIFY | 移除对 `controller.py` 的导出（若有）；保留对 `estimator.py` 的导出 |
| `src/state/database.py` | DELETE | 5 张 SQLite 表的全部 CRUD 操作删除；由新文件 `src/state/json_store.py` 替代（需新建） |
| `src/state/checkpoint.py` | DELETE | `CheckpointManager` 整体删除；断点恢复由 `state.json` 的 task status 字段 + 恢复算法替代（见 Section 5） |
| `src/state/models.py` | MODIFY | 删除 SQLite 对应的 dataclass：`ProjectRecord`、`ModuleRecord`、`AnalysisTask`、`AnalysisResult`、`DocNode`；新增 JSON schema 对应的 dataclass：`StateFile`、`ProjectMeta`、`TaskRecord`、`OutputFileRecord`、`DocumentationMeta`（全部为 frozen=True 不可变对象） |
| `src/state/_schema.py` | DELETE | SQLite 建表 DDL 脚本整体删除；JSON Schema 验证改用 Python dataclass + 手动校验 |
| `src/state/__init__.py` | MODIFY | 更新导出：移除 Database、CheckpointManager；新增 JsonStore 导出（待新建文件） |
| `src/doc/depth_planner.py` | REPLACE | 删除三维阈值表方案（三张 `_STRUCTURAL_THRESHOLDS`、`_COMPLEXITY_THRESHOLDS`、`_TOKEN_THRESHOLDS` 查表）；替换为基于 DAG 分层数量的深度计算算法：`calculate_feature_cone_depth(cone, dag)` → 深度 = 锥体内 DAG 层数，受 token 预算约束；小模块约束保留：总组件 < 10 且行数 < 200 时强制 depth=1 |
| `src/doc/mermaid.py` | KEEP | Mermaid 图生成逻辑正确；`get_dependency_graph_mermaid()` 在增强版 `get_dependency_graph` 工具中继续使用 |
| `src/doc/generator.py` | DELETE | `DocumentGenerator` 类和 `generate_doc()` 方法整体删除；文档撰写完全移交 LLM Agent；Jinja2 在 V2 中完全不需要 |
| `src/doc/templates.py` | DELETE | `TemplateRenderer` 类和所有 Jinja2 模板引用删除 |
| `src/doc/_tree_builder.py` | REPLACE | 删除基于 `DocPlanNode` 的文档树构建逻辑；替换为 `build_task_manifest(cones, file_tokens, context_budget=100000)` 函数：输入功能锥体列表和文件 token 数，输出 `05_task_manifest.json`（包含 task 列表、装箱结果、任务执行顺序） |
| `src/doc/_context.py` | DELETE | `make_relative_link()` 和 `build_doc_index()` 函数删除（V1 链接断裂根因在此文件）；V2 中 Agent 负责正确生成相对路径；`doc-index.json` 由 INDEX Agent 生成 |
| `src/doc/__init__.py` | MODIFY | 更新导出：移除 DocumentGenerator、TemplateRenderer；保留 MermaidGenerator；新增 build_task_manifest 导出（来自改造后的 _tree_builder.py） |

### 模板文件

| 文件 | 决策 | 原因 |
|------|------|------|
| `src/templates/index.md.j2` | DELETE | Jinja2 模板全部删除；V2 文档由 Agent 撰写 |
| `src/templates/overview.md.j2` | DELETE | 同上 |
| `src/templates/detail.md.j2` | DELETE | 同上 |

### 需要新建的文件（不在现有 src/ 中）

| 新文件 | 用途 |
|--------|------|
| `src/state/json_store.py` | JSON 文件读写，替代 database.py；实现原子写入、状态查询、任务状态更新 |
| `src/analysis/__init__.py` | 新子模块 init |
| `src/analysis/feature_cone_extractor.py` | 功能锥体提取（SCC + DAG 分层算法），从 grouper.py 中解耦出来 |
| `src/analysis/task_packer.py` | 装箱算法（贪心 bin-packing），按 token 数将功能锥体分配到 batch/single/split 任务 |

### 汇总统计

| 决策 | 文件数 | 关键文件 |
|------|--------|---------|
| KEEP（保留不变） | 7 | `codebase.py`、`language_detect.py`、`graph/ordering.py`、`doc/mermaid.py`、`__init__.py` × 4 |
| MODIFY（修改） | 8 | `server.py`、`graph/dependency.py`、`graph/grouper.py`、`budget/estimator.py`、`budget/__init__.py`、`state/models.py`、`state/__init__.py`、`doc/__init__.py` |
| DELETE（删除） | 7 | `budget/controller.py`、`state/database.py`、`state/checkpoint.py`、`state/_schema.py`、`doc/generator.py`、`doc/templates.py`、`doc/_context.py` |
| REPLACE（重写） | 2 | `doc/depth_planner.py`（阈值表 → DAG 分层）、`doc/_tree_builder.py`（DocPlanNode → task_manifest）|
| DELETE（模板文件） | 3 | `src/templates/*.j2` × 3 |
| 新建 | 4 | `state/json_store.py`、`analysis/__init__.py`、`analysis/feature_cone_extractor.py`、`analysis/task_packer.py` |

---

## Section 8: 遗留问题

以下问题在本设计文档中未完全解决，需要在后续设计或实现阶段处理：

### 8.1 `get_file_content()` 大文件处理策略

当一个源文件超过 100K tokens（约 400K 字符），Agent 无法在单次上下文中完整阅读。有三个选项：

- **选项 A: 截断返回** — 返回前 N 行 + 警告，简单但可能遗漏关键实现
- **选项 B: 返回错误并提示分段** — 强制 Agent 调用多次，每次指定 `line_start` 和 `line_end`
- **选项 C: 自动分段写多个 DETAIL.md** — 在 `analyze_codebase` 装箱时识别大文件，拆分为 `split_part` 子任务

目前假设采用选项 C（已体现在 `type="split_part"` 的任务类型设计中），但具体的分段边界算法（如何选择合适的分割点，保留完整的函数/类定义不被截断）需要进一步设计。

### 8.2 `analyze_codebase()` 在无源码文件时的行为

当 `path` 目录下没有 Python/TypeScript/JavaScript 文件时（如只有 HTML/CSS/YAML），`CodebaseParser.parse()` 会返回空的 `CodebaseSnapshot`。`analyze_codebase` 应该：
- 返回错误？（简单但不友好）
- 写出最小化的 JSON 文件（空文件列表）并返回成功？（允许 Skill 优雅降级）
- 自动扩展语言支持范围？

这影响 MCP Server 的错误处理逻辑设计。

### 8.3 Skill 在无功能入口点时的处理（纯库代码）

功能锥体提取依赖于"入口文件"（DAG 最上层，in-degree 为 0 的节点）。对于纯库代码（所有文件都互相导入，无明确入口），in-degree 为 0 的节点可能为空或数量极少。

当前 `02a_code_analysis_v2.md` 定义了 fallback：以 in-degree 最低的节点集合作为 Feature Root。但若整个依赖图是一个强连通分量（全 SCC），所有节点 in-degree 相同，此时应如何定义"入口"？需要明确 fallback 到 Louvain 的触发条件。

### 8.4 Validator Agent 的介入工具

V2 需求（`00_vision_and_requirements.md` Section 3）提到引入"审查 Agent 检查分组/深度是否语义合理"。当前 7 个工具设计中未为审查 Agent 专门提供"修改功能锥体分组"的工具。

审查 Agent 若需要调整分组，当前只能通过直接修改 `03_feature_cones.json` 文件实现，绕过 MCP Server 的状态管理。是否需要新增 `adjust_feature_cone(cone_id, add_files, remove_files)` 这样的工具？

### 8.5 INDEX Agent 的写文件机制

INDEX Agent 不读源码，仅基于 `03_feature_cones.json` + 所有 SNIPPET.md 撰写 `INDEX.md` 和各 `OVERVIEW.md`。但 `submit_analysis` 当前设计只接受 `detail_paths` 和 `snippet_paths`，不接受 `overview_paths` 或 `index_paths`。

INDEX Assembly 任务（`type="index"`）的完成信号如何传递？是否需要扩展 `submit_analysis` 支持 `overview_paths` 和 `index_path` 参数，还是设计独立的 `submit_index_assembly()` 工具？

---

*文档版本: V2.0 | 生成时间: 2026-03-23 | 基于: T-01 架构分析 + organized/03_responsibility_separation.md + organized/04_current_issues_diagnosis.md + organized/00_vision_and_requirements.md + src/server.py 源码审查*
