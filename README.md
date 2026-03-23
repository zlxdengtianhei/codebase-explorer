# Codebase Explorer

一个本地运行的 MCP Server + Agent Skill，用于分析 Python/TypeScript/JavaScript 代码库结构并生成渐进式披露的架构文档。

## Features

- **语义级代码分析**: 使用 graph-sitter 进行跨文件依赖分析
- **智能模块分组**: Louvain 社区检测自动发现模块边界
- **动态文档深度**: 文档层级由模块复杂度自动决定（1-5层）
- **15 个 MCP 工具**: 完整的索引、分析、预算控制、文档生成工具链
- **Agent Skill**: 兼容 Claude Code / Codex / OpenCode / Gemini CLI
- **本地运行**: 完全本地，不依赖外部服务

## Quick Start

### Installation

```bash
pip install -e .
# 或
uv pip install -e .
```

详细安装指南（MCP Server 配置、Agent Skill 安装、多客户端适配）请参见 [INSTALL.md](INSTALL.md)。

### As MCP Server

配置 `.mcp.json`:

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "python",
      "args": ["-m", "src.server"],
      "transport": "stdio"
    }
  }
}
```

### As Agent Skill

将 `.agents/skills/codebase-explorer/` 复制到你的项目中。

## Usage

### 5-Phase Workflow

1. **Index**: `index_codebase(path)` — 解析代码库
2. **Plan**: `get_modules()` → `create_analysis_plan()` → `plan_doc_structure()` — 规划分析
3. **Analyze**: `get_next_batch()` → `submit_analysis()` 循环 — 分析模块
4. **Generate**: `generate_doc()` 按文档树 — 生成文档
5. **Validate**: 运行验证脚本 — 检查质量

### Dynamic Depth

文档深度由三维指标自动决定：

- 结构深度（子包数量）
- 复杂度深度（函数/类/行数加权）
- Token 深度（估算 token 数）

小模块（< 200行，< 10组件）→ depth 1
大模块（> 800行，> 20组件）→ depth 2-5

| Depth | Meaning | When Applied |
|-------|---------|-------------|
| 0 | Summary only | Merged into parent (< 100 LOC, < 5 functions) |
| 1 | OVERVIEW only | Small modules (< 500 LOC) |
| 2 | OVERVIEW + DETAIL | Medium modules (500-2000 LOC) |
| 3 | Three-level nesting | Complex modules (2000+ LOC, subpackages) |
| 4 | Four-level nesting | Large subsystems (5000+ LOC) |
| 5 | Maximum depth | Framework-scale modules (10000+ LOC) |

## MCP Tools (15)

| Category | Tools |
|----------|-------|
| Indexing | `index_codebase`, `get_modules`, `get_module_detail`, `get_dependency_graph` |
| Budget | `estimate_module_tokens`, `create_analysis_plan`, `check_budget_status` |
| Tasks | `get_next_batch`, `submit_analysis`, `get_analysis_status` |
| Checkpoint | `save_checkpoint`, `load_checkpoint`, `get_cross_ref_context` |
| Docs | `plan_doc_structure`, `generate_doc` |

## Requirements

- Python >= 3.11
- Dependencies: mcp, codegen (graph-sitter), networkx, python-louvain, jinja2, aiosqlite, pydantic

## Project Structure

```
src/
├── server.py          # MCP Server entry (15 tools)
├── parser/            # Graph-sitter code parsing
├── graph/             # Dependency graph + Louvain grouping
├── state/             # SQLite state management
├── budget/            # Token estimation + budget control
├── doc/               # Dynamic depth planner + doc generation
└── templates/         # Jinja2 templates (index, overview, detail)
```

## License

MIT
