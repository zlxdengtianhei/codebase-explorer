# 研究报告 05：MCP Server 实现最佳实践

> **研究日期**: 2026-03-22
> **状态**: ✅ 完成
> **基于**: FastMCP 3.0 (2026-01-19 发布) + MCP 规范 2025-11-05
> **前置依赖**: 01_code_graph_tools.md ✅ | 03_docagent_architecture.md ✅ | 04_progressive_doc_standards.md ✅

---

## 目录

1. [FastMCP 3.0 核心 API 速查](#1-fastmcp-30-核心-api-速查)
2. [工具设计规范](#2-工具设计规范)
3. [我们系统所需的工具设计草案](#3-我们系统所需的工具设计草案)
4. [SQLite 状态管理代码模式](#4-sqlite-状态管理代码模式)
5. [各 AI IDE/CLI 的 MCP Server 注册方式](#5-各-ai-idecli-的-mcp-server-注册方式)
6. [测试策略](#6-测试策略)
7. [完整代码骨架](#7-完整代码骨架)

---

## 1. FastMCP 3.0 核心 API 速查

### 1.1 工具定义方式

```python
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from fastmcp.exceptions import ToolError
from typing import Annotated, Literal
from pydantic import Field

mcp = FastMCP(
    name="CodebaseExplorer",
    instructions="分析代码库结构，生成渐进式架构文档。",
    version="0.1.0",
)

# 基本工具定义 — 函数名即工具名，docstring 即工具描述
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

# 高级工具定义 — 自定义名称、描述、标签、注解
@mcp.tool(
    name="index_codebase",
    description="索引并分析指定路径的代码库结构",
    tags={"analysis", "indexing"},
    annotations={
        "title": "Index Codebase",
        "readOnlyHint": True,        # 不修改数据
        "idempotentHint": True,      # 幂等
        "openWorldHint": False,      # 不访问外部系统
    },
    timeout=120.0,                   # 超时 120 秒
)
async def index_codebase_impl(
    path: Annotated[str, Field(description="代码库根目录的绝对路径")],
    languages: Annotated[
        list[str] | None,
        Field(description="要分析的语言列表，如 ['python', 'typescript']")
    ] = None,
    ctx: Context = None,
) -> dict:
    """索引指定路径的代码库，构建函数调用图、类继承图和模块依赖图。"""
    await ctx.report_progress(progress=0, total=100)
    # ... 实现
    return {"status": "indexed", "files": 42}
```

### 1.2 参数类型支持

| 类型分类          | 支持的 Python 类型                        |
| ----------------- | ----------------------------------------- | ------------------------ |
| **基本类型**      | `int`, `float`, `str`, `bool`, `bytes`    |
| **时间类型**      | `datetime`, `date`, `timedelta`           |
| **集合类型**      | `list[str]`, `dict[str, int]`, `set[int]` |
| **可选类型**      | `float                                    | None`, `Optional[float]` |
| **联合类型**      | `str                                      | int`, `Union[str, int]`  |
| **枚举/字面量**   | `Literal["A", "B"]`, `Enum` 子类          |
| **路径/ID**       | `Path`, `UUID`                            |
| **Pydantic 模型** | 任何 `BaseModel` 子类                     |
| **数据类**        | `@dataclass` 装饰的类                     |

**参数元数据**（v2.11.0+）：

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def search(
    query: Annotated[str, Field(description="搜索查询字符串")],
    limit: Annotated[int, Field(description="最大结果数", ge=1, le=100)] = 10,
    sort_by: Annotated[
        Literal["relevance", "name", "complexity"],
        Field(description="排序方式")
    ] = "relevance",
) -> list[dict]:
    """搜索代码库中的符号。"""
    ...
```

### 1.3 返回值格式

| 返回类型               | MCP 传输格式                        | 说明                                         |
| ---------------------- | ----------------------------------- | -------------------------------------------- |
| `str`                  | `TextContent`                       | 最常用，直接文本                             |
| `dict` / Pydantic 模型 | `structuredContent` + `TextContent` | 自动双输出                                   |
| `list[...]`            | 每项按规则转换                      | 支持混合类型列表                             |
| `int`, `float`, `bool` | 仅 `TextContent`（无 schema 时）    | 有 `-> int` 注解时也生成 `structuredContent` |
| `bytes`                | `BlobResourceContents`              | Base64 编码                                  |
| `Image(path=...)`      | `ImageContent`                      | 图片返回                                     |
| `None`                 | 空响应                              | 无内容                                       |

**结构化输出推荐**（v2.10.0+）：返回 `dict` 或 Pydantic 模型时，FastMCP 自动生成 `structuredContent`，LLM 可以直接解析 JSON。

### 1.4 Context 能力速查

```python
from fastmcp import Context

@mcp.tool
async def my_tool(data: str, ctx: Context) -> str:
    # 日志
    await ctx.debug("调试信息")
    await ctx.info("处理中...")
    await ctx.warning("警告信息")
    await ctx.error("错误信息")

    # 进度报告
    await ctx.report_progress(progress=50, total=100)

    # Session State（跨请求持久化，v3.0.0+）
    count = await ctx.get_state("counter") or 0
    await ctx.set_state("counter", count + 1)
    await ctx.delete_state("old_key")

    # 读取资源
    resources = await ctx.list_resources()
    content = await ctx.read_resource("resource://config")

    # LLM Sampling（请求客户端 LLM 生成文本）
    response = await ctx.sample("请总结以下内容...", temperature=0.7)

    # Lifespan Context（服务器启动时初始化的共享资源）
    db = ctx.lifespan_context["db"]

    # 请求元数据
    request_id = ctx.request_id
    client_id = ctx.client_id

    return "done"
```

### 1.5 Lifespan（生命周期管理）

```python
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
import aiosqlite

@lifespan
async def db_lifespan(server):
    """服务器启动时初始化 SQLite，关闭时清理。"""
    db = await aiosqlite.connect("codebase_explorer.db")
    await db.execute("CREATE TABLE IF NOT EXISTS ...")
    await db.commit()
    try:
        yield {"db": db}  # 通过 ctx.lifespan_context["db"] 访问
    finally:
        await db.close()

# 组合多个 lifespan
mcp = FastMCP("MyServer", lifespan=db_lifespan | another_lifespan)
```

### 1.6 Resource 与 Tool 的选择

| 维度           | Tool                             | Resource                                     |
| -------------- | -------------------------------- | -------------------------------------------- |
| **控制方**     | AI 模型决定何时调用              | 应用程序/用户控制                            |
| **用途**       | 执行操作、计算、修改状态         | 提供静态/动态数据                            |
| **类比**       | REST API 的 POST/PUT/DELETE      | REST API 的 GET                              |
| **适合**       | `index_codebase`, `generate_doc` | `config://settings`, `graph://module/{name}` |
| **我们的选择** | ✅ 主要使用 Tool                 | ⚠️ 仅用于暴露静态配置和缓存数据              |

---

## 2. 工具设计规范

### 2.1 命名规范

基于 MCP 规范和 3 个参考实现（mcp-server-sqlite、mcp-server-filesystem、code-graph-rag）的分析：

| 规则                  | 说明                                                           | 示例                                                |
| --------------------- | -------------------------------------------------------------- | --------------------------------------------------- |
| **使用 `snake_case`** | MCP 规范允许 a-z, A-Z, 0-9, \_, -, .，但 snake_case 是社区主流 | `index_codebase`, `get_modules`                     |
| **动词开头**          | 工具名以动作动词开头                                           | `get_`, `list_`, `create_`, `analyze_`, `generate_` |
| **最大 128 字符**     | MCP 规范限制                                                   | —                                                   |
| **领域前缀（可选）**  | 工具多时按领域分组                                             | `graph_get_modules`, `doc_generate_overview`        |
| **避免缩写**          | LLM 需要语义清晰的名称                                         | ✅ `get_function_callers` ❌ `get_fn_clrs`          |

**参考实现的命名模式**：

- **mcp-server-sqlite**: `read_query`, `write_query`, `create_table`, `list_tables`, `describe_table`
- **mcp-server-filesystem**: `read_file`, `write_file`, `list_directory`, `search_files`, `get_file_info`
- **code-graph-rag**: `index_repository`, `query_graph`, `get_entity_details`

### 2.2 参数设计最佳实践

1. **使用 Annotated + Field 提供参数描述**（LLM 依赖这些描述选择参数值）
2. **必选参数在前，可选参数在后**
3. **使用 Literal 限制枚举值**而非 str（LLM 更容易选择正确值）
4. **默认值要合理**（减少 LLM 决策负担）
5. **避免布尔参数**（用枚举值代替，语义更清晰）
6. **复杂输入用 Pydantic 模型**

```python
# ❌ 不好的参数设计
@mcp.tool
def analyze(p, l=None, d=False): ...

# ✅ 好的参数设计
@mcp.tool
def analyze_codebase(
    path: Annotated[str, Field(description="代码库根目录路径")],
    languages: Annotated[
        list[Literal["python", "typescript", "javascript"]] | None,
        Field(description="要分析的编程语言，None 表示自动检测")
    ] = None,
    depth: Annotated[
        Literal["shallow", "standard", "deep"],
        Field(description="分析深度: shallow=仅模块, standard=模块+函数, deep=全量")
    ] = "standard",
) -> dict:
    """分析代码库结构，构建依赖图谱。返回包含模块数、函数数、类数的统计摘要。"""
    ...
```

### 2.3 返回值规范

1. **始终返回 `dict`**（结构化输出，LLM 可解析）
2. **包含 `status` 字段**（"success", "partial", "error"）
3. **包含 `summary` 字段**（人类可读的一句话摘要）
4. **数据在 `data` 字段中**
5. **错误信息在 `error` 字段中**

```python
# 标准返回格式
{
    "status": "success",
    "summary": "成功索引 42 个文件，发现 156 个函数和 28 个类",
    "data": {
        "files_count": 42,
        "functions_count": 156,
        "classes_count": 28,
        "modules": [...]
    }
}
```

### 2.4 错误处理模式

```python
from fastmcp.exceptions import ToolError

@mcp.tool
async def index_codebase(path: str) -> dict:
    """索引代码库。"""
    # 1. 参数验证 → ToolError（消息总是发送给客户端）
    if not os.path.isdir(path):
        raise ToolError(f"路径不存在或不是目录: {path}")

    try:
        result = await do_indexing(path)
        return {"status": "success", "data": result}
    except PermissionError as e:
        # 2. 可恢复错误 → 返回错误状态
        return {"status": "error", "error": f"权限不足: {e}", "suggestion": "请检查目录权限"}
    except Exception as e:
        # 3. 不可恢复错误 → ToolError
        raise ToolError(f"索引失败: {e}")
```

**三层错误处理策略**：

| 层级         | 处理方式                            | 场景                 |
| ------------ | ----------------------------------- | -------------------- |
| **参数验证** | `raise ToolError(msg)`              | 路径不存在、参数无效 |
| **业务错误** | 返回 `{"status": "error", ...}`     | 部分失败、权限不足   |
| **系统错误** | `raise ToolError(msg)` 或让异常冒泡 | 数据库损坏、内存不足 |

### 2.5 文档字符串规范

**Agent 依赖 docstring 理解工具能力**，这是最重要的设计要素之一。

```python
@mcp.tool
def get_module_dependencies(
    module_name: Annotated[str, Field(description="模块名称")],
    direction: Annotated[
        Literal["imports", "imported_by", "both"],
        Field(description="依赖方向")
    ] = "both",
    include_external: Annotated[bool, Field(description="是否包含外部依赖")] = False,
) -> dict:
    """获取指定模块的依赖关系图。

    返回该模块导入的其他模块（imports）和/或依赖该模块的其他模块（imported_by）。
    结果包含 Mermaid 格式的依赖图和结构化的依赖列表。

    使用场景：
    - 了解模块的上下游关系
    - 评估修改某模块的影响范围
    - 生成 OVERVIEW.md 中的依赖关系章节

    注意：必须先调用 index_codebase 建立索引后才能使用此工具。
    """
    ...
```

**Docstring 必须包含**：

1. **一句话功能描述**（第一行）
2. **详细说明**（何时使用、返回什么）
3. **使用场景**（帮助 Agent 判断何时调用）
4. **前置条件**（如"必须先调用 index_codebase"）

---

## 3. 我们系统所需的工具设计草案

> 工具参数和返回值已与 01_code_graph_tools.md（Graph-sitter API）、04_progressive_doc_standards.md（文档层级结构）、03_docagent_architecture.md（多 Agent 状态追踪）对齐。

### 3.1 核心工具矩阵

| 工具名                      | 参数                                                                    | 返回值                                                                             | 注解                       | 说明                                                          |
| --------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | -------------------------- | ------------------------------------------------------------- |
| `index_codebase`            | `path: str`, `languages: list[str] \| None`                             | `{status, summary, data: {files_count, functions_count, classes_count, index_id}}` | readOnly, idempotent       | 使用 Graph-sitter 解析代码库，构建 NetworkX 图谱，存入 SQLite |
| `get_modules`               | `sort_by: Literal["name","size","complexity"]`, `index_id: str \| None` | `{modules: [{name, file_count, function_count, description, path}]}`               | readOnly                   | 获取 Louvain 分组后的模块列表                                 |
| `get_module_detail`         | `module_name: str`                                                      | `{name, files, public_interfaces, dependencies, metrics, mermaid_graph}`           | readOnly                   | 获取模块详情，用于生成 OVERVIEW.md                            |
| `get_component_detail`      | `component_id: str`                                                     | `{name, classes, functions, call_graph, inheritance, data_flow, mermaid}`          | readOnly                   | 获取组件详情，用于生成 ARCHITECTURE.md                        |
| `get_function_callers`      | `function_name: str`, `depth: int = 2`                                  | `{callers: [{name, file, line}], call_chain_mermaid}`                              | readOnly                   | 追踪函数调用链（对应 Graph-sitter `func.usages`）             |
| `get_dependency_graph`      | `scope: Literal["project","module","component"]`, `target: str \| None` | `{nodes, edges, mermaid_graph, circular_deps}`                                     | readOnly                   | 获取依赖图（对应 Graph-sitter `module_graph`）                |
| `generate_index_doc`        | `index_id: str`, `format: Literal["markdown","json"] = "markdown"`      | `{doc_content, token_count, coverage}`                                             | 非 readOnly                | 生成 Level 0 INDEX.md                                         |
| `generate_overview_doc`     | `module_name: str`                                                      | `{doc_content, token_count, coverage}`                                             | 非 readOnly                | 生成 Level 1 OVERVIEW.md                                      |
| `generate_architecture_doc` | `component_id: str`                                                     | `{doc_content, token_count, coverage}`                                             | 非 readOnly                | 生成 Level 2 ARCHITECTURE.md                                  |
| `get_analysis_status`       | `index_id: str \| None`                                                 | `{status, progress, modules_analyzed, errors}`                                     | readOnly                   | 查询分析状态（支持多 Agent 互斥追踪）                         |
| `claim_analysis_task`       | `module_name: str`, `agent_id: str`                                     | `{claimed, task_id, expires_at}`                                                   | 非 readOnly, 非 idempotent | 互斥锁：Agent 声明正在分析某模块                              |
| `release_analysis_task`     | `task_id: str`, `result_status: Literal["done","failed","skipped"]`     | `{released}`                                                                       | 非 readOnly                | 释放互斥锁                                                    |

### 3.2 与前置研究的数据结构对齐

**与 01_code_graph_tools.md 对齐**：

| Graph-sitter API      | 我们的 MCP 工具                        |
| --------------------- | -------------------------------------- |
| `Codebase("./")`      | `index_codebase(path)`                 |
| `codebase.functions`  | `get_component_detail(id).functions`   |
| `func.function_calls` | `get_function_callers(name)`           |
| `file.imports`        | `get_dependency_graph(scope="module")` |
| `cls.subclasses`      | `get_component_detail(id).inheritance` |
| `nx.DiGraph` → JSON   | 所有工具返回的 `mermaid_graph` 字段    |

**与 04_progressive_doc_standards.md 对齐**：

| 文档层级                 | 生成工具                    | Token 预算  |
| ------------------------ | --------------------------- | ----------- |
| Level 0: INDEX.md        | `generate_index_doc`        | 800-1,200   |
| Level 1: OVERVIEW.md     | `generate_overview_doc`     | 1,200-2,000 |
| Level 2: ARCHITECTURE.md | `generate_architecture_doc` | 2,000-4,000 |

**与 03_docagent_architecture.md 对齐**：

| DocAgent 模式            | 对应工具/机制                                   |
| ------------------------ | ----------------------------------------------- |
| 拓扑排序处理顺序         | `get_modules(sort_by="dependency")` 返回拓扑序  |
| Reader-Searcher 信息驱动 | `get_module_detail` + `get_component_detail`    |
| Writer-Verifier 迭代精炼 | `generate_*_doc` 工具 + Agent 侧验证逻辑        |
| 互斥处理追踪             | `claim_analysis_task` + `release_analysis_task` |

---

## 4. SQLite 状态管理代码模式

### 4.1 初始化模式（Lifespan + aiosqlite）

```python
import aiosqlite
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from pathlib import Path

DB_PATH = Path.home() / ".codebase-explorer" / "state.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS codebase_index (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    stats_json TEXT
);

CREATE TABLE IF NOT EXISTS analysis_tasks (
    id TEXT PRIMARY KEY,
    module_name TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'in_progress',
    UNIQUE(module_name, status)  -- 互斥：同一模块同时只能有一个 in_progress
);

CREATE TABLE IF NOT EXISTS generated_docs (
    id TEXT PRIMARY KEY,
    index_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,       -- 'index', 'overview', 'architecture'
    target_name TEXT NOT NULL,
    content TEXT,
    token_count INTEGER,
    coverage REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (index_id) REFERENCES codebase_index(id)
);

-- 版本控制
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""

@lifespan
async def db_lifespan(server):
    """初始化 SQLite 数据库连接。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")   # WAL 模式支持并发读
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(SCHEMA_SQL)
    await db.commit()
    try:
        yield {"db": db}
    finally:
        await db.close()

mcp = FastMCP("CodebaseExplorer", lifespan=db_lifespan)
```

### 4.2 线程安全注意事项

| 问题                   | 解决方案                                                    |
| ---------------------- | ----------------------------------------------------------- |
| SQLite 默认单写        | 使用 WAL 模式 (`PRAGMA journal_mode=WAL`) 允许并发读 + 单写 |
| aiosqlite 线程安全     | aiosqlite 内部使用独立线程执行 SQLite 操作，异步安全        |
| 多 Agent 互斥          | 使用数据库级 UNIQUE 约束 + `INSERT OR FAIL` 实现乐观锁      |
| FastMCP STDIO 是单进程 | STDIO 模式下天然无并发问题；HTTP 模式需注意                 |

### 4.3 数据库迁移策略

```python
MIGRATIONS = {
    2: """
        ALTER TABLE codebase_index ADD COLUMN language_filter TEXT;
    """,
    3: """
        CREATE INDEX idx_docs_index_id ON generated_docs(index_id);
    """,
}

async def run_migrations(db: aiosqlite.Connection):
    async with db.execute("SELECT version FROM schema_version") as cursor:
        row = await cursor.fetchone()
        current_version = row[0] if row else 0

    for version, sql in sorted(MIGRATIONS.items()):
        if version > current_version:
            await db.executescript(sql)
            await db.execute(
                "UPDATE schema_version SET version = ?", (version,)
            )
            await db.commit()
```

---

## 5. 各 AI IDE/CLI 的 MCP Server 注册方式

### 5.1 Claude Code

```bash
# 方式 1: CLI 命令添加（推荐）
claude mcp add codebase-explorer \
  --transport stdio \
  --scope project \
  -- python /path/to/server.py

# 方式 2: 项目级配置文件 .mcp.json（推荐团队共享）
```

`.mcp.json`（放在项目根目录）：

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "DB_PATH": "/path/to/state.db"
      }
    }
  }
}
```

**Scope 说明**: `local`=当前目录, `project`=通过 `.mcp.json` 共享, `user`=全局可用

### 5.2 Gemini CLI

```bash
# 方式 1: CLI 命令（v2.12.3+ 支持）
gemini mcp add codebase-explorer -- python /path/to/server.py

# 方式 2: FastMCP 自动安装
fastmcp install gemini-cli /path/to/server.py

# 方式 3: settings.json 手动配置
```

`~/.gemini/settings.json`：

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "transport": "stdio"
    }
  }
}
```

### 5.3 OpenCode

OpenCode 支持 MCP 客户端连接。配置方式：

```toml
# ~/.config/opencode/config.toml 或项目 .opencode.toml
[mcp.codebase-explorer]
command = "python"
args = ["/path/to/server.py"]
transport = "stdio"
```

### 5.4 Codex CLI (OpenAI)

```toml
# ~/.codex/config.toml
[mcp_servers.codebase-explorer]
command = "python"
args = ["/path/to/server.py"]
```

或通过 CLI：

```bash
codex mcp add codebase-explorer python /path/to/server.py
```

### 5.5 统一兼容建议

| 要点            | 建议                                                |
| --------------- | --------------------------------------------------- |
| **Transport**   | 使用 STDIO（所有客户端都支持，最大兼容性）          |
| **启动方式**    | `python server.py`（避免 `uv run` 等工具链差异）    |
| **stdout 保护** | 绝不在 STDIO 模式下直接 `print()` — 会破坏 JSON-RPC |
| **日志**        | 使用 `ctx.info()` 等 MCP 日志，或写入 stderr        |
| **入口**        | `if __name__ == "__main__": mcp.run()` 标准入口     |
| **依赖管理**    | 提供 `pyproject.toml` + `uv.lock` 保证可重现        |
| **配置共享**    | 项目级 `.mcp.json` 让团队共享配置                   |

---

## 6. 测试策略

### 6.1 单元测试（In-Memory Client）

FastMCP 支持 **内存内测试**，无需启动真实服务器进程：

```python
# tests/test_tools.py
import pytest
from fastmcp.client import Client
from server import mcp  # 导入你的 FastMCP 实例

# pyproject.toml 中设置:
# [tool.pytest.ini_options]
# asyncio_mode = "auto"

@pytest.fixture
async def client():
    async with Client(transport=mcp) as c:
        yield c

async def test_list_tools(client):
    tools = await client.list_tools()
    tool_names = {t.name for t in tools}
    assert "index_codebase" in tool_names
    assert "get_modules" in tool_names

async def test_index_codebase(client, tmp_path):
    # 创建测试代码文件
    (tmp_path / "main.py").write_text("def hello(): pass")

    result = await client.call_tool(
        name="index_codebase",
        arguments={"path": str(tmp_path)}
    )
    assert result.data is not None
    assert result.data["status"] == "success"

async def test_invalid_path(client):
    result = await client.call_tool(
        name="index_codebase",
        arguments={"path": "/nonexistent/path"}
    )
    # ToolError 会被捕获为 isError=True
    assert any(c.type == "text" and "不存在" in c.text for c in result)

# 参数化测试
@pytest.mark.parametrize("sort_by", ["name", "size", "complexity"])
async def test_get_modules_sort(client, sort_by):
    result = await client.call_tool(
        name="get_modules",
        arguments={"sort_by": sort_by}
    )
    assert result.data is not None
```

### 6.2 集成测试

```python
# tests/test_integration.py
import pytest
from fastmcp.client import Client

@pytest.fixture
async def client_with_indexed_repo(client, test_repo_path):
    """预先索引测试仓库的集成测试 fixture"""
    await client.call_tool("index_codebase", {"path": str(test_repo_path)})
    yield client

async def test_full_doc_generation_flow(client_with_indexed_repo):
    client = client_with_indexed_repo

    # 1. 获取模块列表
    modules = await client.call_tool("get_modules", {"sort_by": "name"})
    assert modules.data["modules"]

    # 2. 获取第一个模块详情
    module = modules.data["modules"][0]
    detail = await client.call_tool(
        "get_module_detail", {"module_name": module["name"]}
    )
    assert detail.data["public_interfaces"] is not None

    # 3. 生成文档
    doc = await client.call_tool(
        "generate_overview_doc", {"module_name": module["name"]}
    )
    assert doc.data["token_count"] <= 2000  # Level 1 预算
```

### 6.3 MCP Inspector 手动调试

```bash
# 方式 1: npx 启动 Inspector Web UI
npx @modelcontextprotocol/inspector python server.py

# 方式 2: FastMCP 内置 dev 命令
fastmcp dev server.py

# 方式 3: Inspector CLI 模式（CI 可用）
npx @modelcontextprotocol/inspector --cli python server.py
```

**Inspector 调试清单**：

1. ✅ 验证 Server 连接和能力协商
2. ✅ 列出所有 Tools，检查 schema 和 description
3. ✅ 逐个工具测试正常输入
4. ✅ 测试边界情况（空路径、超长输入、特殊字符）
5. ✅ 测试错误响应格式
6. ✅ 检查 Resources 和 Prompts（如果有）

---

## 7. 完整代码骨架

```python
#!/usr/bin/env python3
"""
Codebase Explorer MCP Server
使用 FastMCP 3.0 构建的代码库分析和文档生成 MCP Server。
"""

import os
import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

import aiosqlite
from pydantic import Field
from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from fastmcp.exceptions import ToolError

# ============================================================
# 配置
# ============================================================

DB_PATH = Path(os.environ.get(
    "CODEBASE_EXPLORER_DB",
    str(Path.home() / ".codebase-explorer" / "state.db")
))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS codebase_index (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'pending',
    stats_json TEXT,
    graph_json TEXT
);
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id TEXT PRIMARY KEY,
    index_id TEXT NOT NULL,
    module_name TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    claimed_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress',
    FOREIGN KEY (index_id) REFERENCES codebase_index(id)
);
CREATE TABLE IF NOT EXISTS generated_docs (
    id TEXT PRIMARY KEY,
    index_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    target_name TEXT NOT NULL,
    content TEXT,
    token_count INTEGER,
    coverage REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (index_id) REFERENCES codebase_index(id)
);
"""

# ============================================================
# Lifespan: 数据库初始化
# ============================================================

@lifespan
async def db_lifespan(server):
    """初始化 SQLite 数据库。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(SCHEMA_SQL)
    await db.commit()
    try:
        yield {"db": db}
    finally:
        await db.close()

# ============================================================
# Server 实例
# ============================================================

mcp = FastMCP(
    name="CodebaseExplorer",
    version="0.1.0",
    instructions="""代码库结构分析和渐进式文档生成服务器。

工作流程:
1. 调用 index_codebase 索引目标代码库
2. 调用 get_modules 查看模块列表
3. 调用 get_module_detail / get_component_detail 查看详情
4. 调用 generate_*_doc 生成对应层级的文档

注意: 所有查询工具需要先完成索引。""",
    lifespan=db_lifespan,
)

# ============================================================
# 辅助函数
# ============================================================

def _get_db(ctx: Context) -> aiosqlite.Connection:
    """从 lifespan context 获取数据库连接。"""
    return ctx.lifespan_context["db"]

# ============================================================
# 工具定义
# ============================================================

@mcp.tool(
    annotations={
        "title": "Index Codebase",
        "readOnlyHint": False,
        "idempotentHint": True,
    },
    timeout=120.0,
)
async def index_codebase(
    path: Annotated[str, Field(description="代码库根目录的绝对路径")],
    languages: Annotated[
        list[Literal["python", "typescript", "javascript"]] | None,
        Field(description="要分析的语言，None 表示自动检测")
    ] = None,
    ctx: Context = None,
) -> dict:
    """索引代码库，构建函数调用图、类继承图和模块依赖图。

    使用 Graph-sitter 解析代码结构并存入本地数据库。
    索引完成后，可以通过 get_modules 等工具查询分析结果。

    使用场景：首次分析代码库或代码发生重大变更后重建索引。
    """
    if not os.path.isdir(path):
        raise ToolError(f"路径不存在或不是目录: {path}")

    db = _get_db(ctx)
    index_id = str(uuid.uuid4())[:8]

    await ctx.info(f"开始索引: {path}")
    await ctx.report_progress(progress=0, total=100)

    # TODO: 集成 Graph-sitter
    # from graph_sitter import Codebase
    # codebase = Codebase(path)

    # 模拟索引过程
    file_count = len(list(Path(path).rglob("*.py")))
    await ctx.report_progress(progress=50, total=100)

    stats = {
        "files_count": file_count,
        "functions_count": 0,  # TODO
        "classes_count": 0,    # TODO
        "languages": languages or ["python"],
    }

    await db.execute(
        "INSERT INTO codebase_index (id, path, status, stats_json) VALUES (?, ?, ?, ?)",
        (index_id, path, "completed", json.dumps(stats)),
    )
    await db.commit()

    await ctx.report_progress(progress=100, total=100)
    await ctx.info(f"索引完成: {index_id}")

    return {
        "status": "success",
        "summary": f"成功索引 {file_count} 个文件",
        "data": {"index_id": index_id, **stats},
    }


@mcp.tool(
    annotations={"title": "Get Modules", "readOnlyHint": True},
)
async def get_modules(
    sort_by: Annotated[
        Literal["name", "size", "complexity"],
        Field(description="排序方式")
    ] = "name",
    index_id: Annotated[
        str | None,
        Field(description="索引 ID，None 使用最新索引")
    ] = None,
    ctx: Context = None,
) -> dict:
    """获取代码库的模块列表。

    返回经过自动分组的模块列表，每个模块包含名称、文件数、简要描述。
    可用于了解代码库整体结构和决定深入分析的优先级。

    前置条件：必须先调用 index_codebase 建立索引。
    """
    db = _get_db(ctx)

    if index_id is None:
        async with db.execute(
            "SELECT id FROM codebase_index ORDER BY created_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise ToolError("没有可用的索引，请先调用 index_codebase")
            index_id = row[0]

    # TODO: 实际模块分组逻辑
    return {
        "status": "success",
        "summary": f"索引 {index_id} 包含的模块列表",
        "data": {"index_id": index_id, "modules": []},
    }


@mcp.tool(
    annotations={"title": "Claim Analysis Task", "readOnlyHint": False},
)
async def claim_analysis_task(
    module_name: Annotated[str, Field(description="要分析的模块名称")],
    agent_id: Annotated[str, Field(description="Agent 标识符")],
    ttl_minutes: Annotated[int, Field(description="锁定时长(分钟)", ge=1, le=60)] = 10,
    ctx: Context = None,
) -> dict:
    """声明正在分析某个模块（互斥锁）。

    防止多个 Agent 同时分析同一模块。如果模块已被其他 Agent 锁定，
    返回 claimed=false 及当前锁定者信息。

    使用场景：多 Agent 协作时，在开始分析模块前调用此工具。
    """
    db = _get_db(ctx)
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ttl_minutes)

    # 清理过期任务
    await db.execute(
        "DELETE FROM analysis_tasks WHERE expires_at < ? AND status = 'in_progress'",
        (now.isoformat(),),
    )

    # 检查是否已被锁定
    async with db.execute(
        "SELECT agent_id, expires_at FROM analysis_tasks "
        "WHERE module_name = ? AND status = 'in_progress'",
        (module_name,),
    ) as cursor:
        existing = await cursor.fetchone()
        if existing:
            return {
                "status": "conflict",
                "claimed": False,
                "locked_by": existing[0],
                "expires_at": existing[1],
            }

    # 释放锁
    await db.execute(
        "INSERT INTO analysis_tasks (id, index_id, module_name, agent_id, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (task_id, "latest", module_name, agent_id, expires_at.isoformat()),
    )
    await db.commit()

    return {
        "status": "success",
        "claimed": True,
        "task_id": task_id,
        "expires_at": expires_at.isoformat(),
    }


@mcp.tool(
    annotations={"title": "Release Analysis Task", "readOnlyHint": False},
)
async def release_analysis_task(
    task_id: Annotated[str, Field(description="任务 ID")],
    result_status: Annotated[
        Literal["done", "failed", "skipped"],
        Field(description="完成状态")
    ] = "done",
    ctx: Context = None,
) -> dict:
    """释放模块分析的互斥锁。

    分析完成后调用此工具释放锁，允许其他 Agent 使用该模块。
    """
    db = _get_db(ctx)
    await db.execute(
        "UPDATE analysis_tasks SET status = ? WHERE id = ?",
        (result_status, task_id),
    )
    await db.commit()
    return {"status": "success", "released": True}


@mcp.tool(
    annotations={"title": "Get Analysis Status", "readOnlyHint": True},
)
async def get_analysis_status(
    index_id: Annotated[str | None, Field(description="索引 ID")] = None,
    ctx: Context = None,
) -> dict:
    """查询当前分析状态，包括正在进行的任务和已完成的文档。

    使用场景：了解多 Agent 协作的整体进度。
    """
    db = _get_db(ctx)

    active_tasks = []
    async with db.execute(
        "SELECT module_name, agent_id, status FROM analysis_tasks "
        "WHERE status = 'in_progress'"
    ) as cursor:
        async for row in cursor:
            active_tasks.append({
                "module": row[0], "agent": row[1], "status": row[2]
            })

    completed_docs = []
    async with db.execute(
        "SELECT doc_type, target_name, token_count FROM generated_docs"
    ) as cursor:
        async for row in cursor:
            completed_docs.append({
                "type": row[0], "target": row[1], "tokens": row[2]
            })

    return {
        "status": "success",
        "data": {
            "active_tasks": active_tasks,
            "completed_docs": completed_docs,
            "active_count": len(active_tasks),
            "completed_count": len(completed_docs),
        },
    }


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    mcp.run()  # 默认 STDIO transport
```

---

## 8. 引用来源

### 官方文档

- FastMCP 文档: https://gofastmcp.com/ （Tools, Resources, Context, Lifespan, Testing 章节）
- FastMCP GitHub: https://github.com/PrefectHQ/fastmcp
- MCP 规范: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector

### 参考实现

- mcp-server-sqlite (PyPI): https://pypi.org/project/mcp-server-sqlite/
- mcp-server-filesystem: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- code-graph-rag: GitHub 上的代码图谱 RAG MCP 实现

### AI IDE 配置

- Claude Code MCP 文档: https://docs.anthropic.com/en/docs/claude-code/mcp
- Gemini CLI MCP: https://blog.google/technology/developers/gemini-cli-mcp-fastmcp/
- OpenAI Codex CLI: https://openai.com/index/codex-cli/
- OpenCode: https://github.com/opencode-ai/opencode

### 设计参考

- MCP 工具设计最佳实践: https://thenewstack.io/mcp-best-practices/
- Docker MCP 最佳实践: https://docs.docker.com/ai/mcp-best-practices/
- MCP 规范 - Tool 命名规则: https://modelcontextprotocol.io/specification/2025-06-18/server/tools

---

## 9. 快速结论

> **使用 FastMCP 3.0 + aiosqlite + STDIO transport 构建本地 MCP Server 是当前最成熟的方案。** 关键设计决策：
>
> 1. **Lifespan 管理 SQLite 连接**，通过 `ctx.lifespan_context` 在所有工具间共享
> 2. **工具返回标准化 dict**（status + summary + data），兼顾 LLM 解析和人类可读
> 3. **互斥锁用数据库 UNIQUE 约束**实现，支持多 Agent 协作
> 4. **STDIO transport 是跨客户端最大公约数**（Claude Code / Gemini CLI / Codex CLI / OpenCode 全部支持）
> 5. **In-Memory Client 测试**是 FastMCP 官方推荐的测试方式，快速且确定性强
