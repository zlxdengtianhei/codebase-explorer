# 研究任务 05：MCP Server 实现最佳实践

## ⚠️ 前置依赖

**在开始本任务之前，请先阅读以下前置研究结果**（如果存在）：

1. `results/01_code_graph_tools.md` — 了解选定的图谱工具（如 graph-sitter）的 API，MCP 工具需要封装这些
2. `results/04_progressive_doc_standards.md` — 了解文档层级结构，MCP 工具需要支持生成这些结构
3. `results/03_docagent_architecture.md` — 了解多 Agent 协作模式，MCP 工具需要支持状态追踪

如果这些文件不存在，可以独立执行本任务，但在"工具设计草案"部分需要标注"待与前置任务结果对齐"。

**关键**：阅读前置结果后，在设计 MCP 工具时要确保：

- 工具参数和返回值与图谱工具的数据结构**兼容**
- 工具能力覆盖文档生成流程的**所有步骤**
- 状态管理支持多 Agent 的**互斥分析追踪**

## 研究目标

研究使用 **FastMCP (Python)** 构建本地 MCP Server 的完整最佳实践，包括：工具设计模式、状态管理、错误处理、测试策略、以及与各 AI IDE/CLI 的兼容性验证。

### 核心问题

1. FastMCP 3.0 的最新 API 和能力是什么？
2. MCP 工具设计的最佳实践是什么？（参数设计、返回值格式、错误处理）
3. MCP Server 如何管理**持久化状态**（如 SQLite 数据库）？
4. 如何确保与 Claude Code / Gemini CLI / OpenCode / Codex CLI 的兼容？
5. MCP Server 的**调试和测试**怎么做？

## 搜索关键词

### 第一轮：FastMCP 核心

- `FastMCP 3.0 tutorial Python MCP server tool implementation 2026`
- `FastMCP best practices tool design patterns`
- `FastMCP server SQLite state management example`
- `FastMCP STDIO transport local server setup`
- `mcp python sdk tool decorator parameter design`

### 第二轮：MCP 设计模式

- `MCP server tool design best practices parameter naming return format`
- `MCP tool error handling retry pattern`
- `MCP server resource vs tool when to use which`
- `MCP server long running task progress reporting`
- `MCP server stateful session management`

### 第三轮：兼容性

- `MCP server compatible Claude Code Gemini CLI OpenCode`
- `MCP STDIO vs HTTP transport compatibility AI IDE`
- `claude mcp add local server configuration`
- `gemini cli mcp server setup STDIO`
- `opencode mcp server configuration`
- `codex CLI MCP integration setup`

### 第四轮：测试与调试

- `MCP server testing strategy unit test integration test`
- `FastMCP testing mock tool calls`
- `MCP Inspector debugging tool`
- `MCP server logging best practices`

## 深入阅读方向

### 必须阅读的资源

1. **FastMCP 官方文档**：https://gofastmcp.com/
   - 完整阅读 Getting Started
   - 重点：Server, Tools, Resources, Context 章节
   - 重点：Deployment 和 Transport 配置

2. **FastMCP GitHub**：https://github.com/jlowin/fastmcp
   - 查看 examples/ 目录下的示例
   - 查看 最近 issue 和 discussions

3. **MCP 规范**：https://modelcontextprotocol.io/
   - 特别是 Tool 的输入/输出规范
   - Resource 的使用场景
   - Transport 层协议细节

4. **现有的优秀 MCP Server 参考实现**：
   - `mcp-server-sqlite`：SQLite MCP Server
   - `mcp-server-filesystem`：文件系统 MCP Server
   - `code-graph-rag` MCP 实现
   - 分析它们的工具设计模式

5. **Claude Code MCP 配置文档**：
   - 如何注册本地 MCP Server
   - 配置文件格式

6. **Gemini CLI MCP 支持**：
   - 搜索 Gemini CLI + MCP 的配置教程

### 可选深入

- MCP Streamable HTTP transport（适合远程部署场景）
- MCP 认证和授权（如果需要多用户支持）
- MCP Server 热重载开发模式

## 产出要求

### 保存位置

`results/05_mcp_server_patterns.md`

### 必须包含的内容

1. **FastMCP 3.0 核心 API 速查**：
   - 工具定义方式
   - 参数类型支持
   - 返回值格式
   - Context 和 State 管理

2. **工具设计规范**（非常重要）：
   - 命名规范
   - 参数设计最佳实践
   - 返回值应该包含什么
   - 错误处理模式
   - 文档字符串规范（agent 依赖这个理解工具能力）

3. **我们系统所需的工具设计草案**：

| 工具名         | 参数            | 返回值   | 说明 |
| -------------- | --------------- | -------- | ---- |
| index_codebase | path, languages | 索引摘要 | ...  |
| get_modules    | sort_by         | 模块列表 | ...  |
| ...            | ...             | ...      | ...  |

4. **SQLite 状态管理代码模式**：
   - 如何在 FastMCP Server 中初始化和使用 SQLite
   - 线程安全注意事项
   - 数据库迁移策略

5. **各 AI IDE/CLI 的 MCP Server 注册方式**：
   - Claude Code 的配置
   - Gemini CLI 的配置
   - OpenCode 的配置
   - Codex CLI 的配置（如果支持）
   - 统一兼容的配置建议

6. **测试策略**：
   - 单元测试模式
   - 集成测试方式
   - 手动调试方法

7. **完整代码骨架**：
   - server.py 的完整骨架代码（可运行）
   - 包含工具定义 + SQLite 初始化 + 错误处理

## 质量标准

- 必须基于 FastMCP 3.0（不是旧版本）
- 工具设计规范必须参考至少 3 个优秀的现有 MCP Server 实现
- 兼容性部分必须实际验证或引用可靠来源
- 代码骨架必须可直接运行（不是伪代码）
