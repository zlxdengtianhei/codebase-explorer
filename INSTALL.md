# Codebase Explorer — Installation Guide

A local MCP Server + Agent Skill that analyzes Python/TypeScript/JavaScript codebases and generates progressive-disclosure architecture documentation with dynamic N-layer depth.

Two components:
- **MCP Server** — 15 tools for indexing, analysis, budget control, and doc generation
- **Agent Skill** — Structured workflow instructions for Claude Code / Codex / opencode / Gemini CLI

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- git

## Install MCP Server

### From Source (current)

```bash
git clone https://github.com/lexuanzhang/codebase-explorer.git
cd codebase-explorer
uv sync
```

Verify the server starts:

```bash
uv run python -m src.server
# Should start the MCP stdio server — press Ctrl+C to stop
```

### From PyPI (future — after package restructure)

```bash
# Not yet available. See "Future: PyPI Distribution" below.
uvx codebase-explorer
# or
pip install codebase-explorer
```

## Configure Your Agent

All configurations below assume you cloned the repo to a known absolute path.
Replace `/path/to/codebase-explorer` with your actual clone location.

### Claude Code

Option A — CLI command:

```bash
claude mcp add codebase-explorer \
  --transport stdio \
  -- uv run --directory /path/to/codebase-explorer python -m src.server
```

Option B — `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/codebase-explorer",
        "python", "-m", "src.server"
      ],
      "transport": "stdio"
    }
  }
}
```

### Codex (OpenAI)

```bash
codex mcp add codebase-explorer \
  -- uv run --directory /path/to/codebase-explorer python -m src.server
```

### opencode

Add to `opencode.json` in your project root:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "codebase-explorer": {
      "command": [
        "uv",
        "run",
        "--directory", "/path/to/codebase-explorer",
        "python", "-m", "src.server"
      ],
      "enabled": true,
      "type": "local"
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/codebase-explorer",
        "python", "-m", "src.server"
      ],
      "transport": "stdio"
    }
  }
}
```

### VS Code (Copilot)

Add to `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "codebase-explorer": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/codebase-explorer",
        "python", "-m", "src.server"
      ],
      "type": "stdio"
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/codebase-explorer",
        "python", "-m", "src.server"
      ]
    }
  }
}
```

## Install Agent Skill (Claude Code only)

The agent skill provides structured workflow instructions that guide the agent
through the 5-phase analysis process. This is optional but recommended.

### Automated

```bash
cd /path/to/codebase-explorer
bash scripts/install-skill.sh
```

### Manual

Copy the skill directory to your Claude Code skills location:

```bash
cp -r /path/to/codebase-explorer/.agents/skills/codebase-explorer \
  ~/.claude/skills/codebase-explorer
```

The skill directory contains:

```
codebase-explorer/
├── SKILL.md                          # Main skill instructions
├── assets/doc-config.yaml            # Default configuration
├── references/
│   ├── MCP_TOOLS_REFERENCE.md        # Full tool parameter specs
│   ├── WORKFLOW_DETAIL.md            # Detailed workflow steps
│   ├── DOC_TEMPLATES.md              # Template variable reference
│   └── QUALITY_STANDARDS.md          # Quality thresholds
└── scripts/
    ├── check_coverage.py             # Coverage validation
    └── validate_doc_links.py         # Link integrity check
```

## Verify Installation

Call the `get_analysis_status` tool from your agent. A successful response
(even with no active project) confirms the MCP server is connected:

```
> Call get_analysis_status

Expected: a JSON response with status information (not a connection error)
```

If the call fails, check:
1. The `--directory` path points to the cloned repo
2. `uv` is installed and on your PATH
3. Python >= 3.12 is available

## For Agents — Automated Setup

Below is a structured instruction block that an agent can parse and execute
to install codebase-explorer for Claude Code.

```yaml
# agent-executable: install-codebase-explorer
steps:
  - name: clone
    run: git clone https://github.com/lexuanzhang/codebase-explorer.git /tmp/codebase-explorer

  - name: install-dependencies
    run: cd /tmp/codebase-explorer && uv sync

  - name: configure-mcp
    run: |
      claude mcp add codebase-explorer \
        --transport stdio \
        -- uv run --directory /tmp/codebase-explorer python -m src.server

  - name: install-skill
    run: bash /tmp/codebase-explorer/scripts/install-skill.sh

  - name: verify
    run: |
      # Agent should call get_analysis_status via MCP to confirm connection
      echo "MCP server configured. Restart your agent session, then call get_analysis_status to verify."
```

## Future: PyPI Distribution

The current source layout uses a flat `src/` package with relative imports
(`from src.server import ...`). This works for local development but prevents
standard `pip install` distribution.

Planned restructure:

```
# Current                          # Future
src/                               codebase_explorer/
├── server.py                      ├── __init__.py
├── parser/                        ├── __main__.py      (entry point)
├── graph/                         ├── server.py
├── state/                         ├── parser/
├── budget/                        ├── graph/
├── doc/                           ├── state/
└── templates/                     ├── budget/
                                   ├── doc/
                                   └── templates/
```

Changes required:
1. Rename `src/` → `codebase_explorer/`
2. Update all internal imports (`from src.X` → `from codebase_explorer.X`)
3. Add `[project.scripts]` entry point in `pyproject.toml`:
   ```toml
   [project.scripts]
   codebase-explorer = "codebase_explorer.server:main"
   ```
4. Publish to PyPI

After restructure, installation simplifies to:

```bash
# Install
pip install codebase-explorer
# or
uvx codebase-explorer

# MCP config becomes:
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "uvx",
      "args": ["codebase-explorer"],
      "transport": "stdio"
    }
  }
}
```

This restructure is tracked separately and does not affect current from-source usage.
