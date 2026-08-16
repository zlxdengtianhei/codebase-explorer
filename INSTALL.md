# Codebase Explorer 安装与运行

这份文档从空白宿主开始，把现有 stdio MCP server 和语义 skill 接到 Claude Code、Codex、
OpenCode 或读 `~/.agents/skills` 的宿主（含 Grok）。安装只让工具可发现；完整产品运行还要走
analyze、语义生产、render、review 四阶段。

## 1. 前置条件

- Python 3.12 或 3.13（本 checkout 的 `.python-version` 钉的是 3.13.11；`pyproject.toml` 上界 `<3.14`）
- [uv](https://docs.astral.sh/uv/)
- 一个本地 Codebase Explorer checkout

本文用：

```text
/absolute/path/to/codebase-explorer
```

代表实现目录。当前 context-infra checkout 的真实路径是：

```text
/Users/lexuanzhang/context-infra/adhoc_jobs/codebase_explorer_20260321/impl/codebase-explorer
```

仓内 `.mcp.json` 用同一绝对路径启动 stdio server。Skill 真源是
`.agents/skills/codebase-explorer/`。只复制 skill、不把 MCP server 挂到**当前正在用的那个宿主**，
不算安装完成。

## 2. 安装依赖并预检 server

```bash
cd /absolute/path/to/codebase-explorer
uv sync

uv run python - <<'PY'
import asyncio
from src.server import mcp

tools = asyncio.run(mcp.list_tools())
print(f"count={len(tools)}")
print("\n".join(tool.name for tool in tools))
PY
```

成功判据：`count=14`，名称逐字等于 README 中的 14 项。这个命令直接消费
`await mcp.list_tools()`，不要用设计文档里的预期清单替代它。

## 3. 安装 Agent Skill

仓内真源是一份。每个会读 skill 的宿主各有一份拷贝，必须逐字节相同。
**不要用 `scripts/install-skill.sh`**：它默认只写 `~/.claude/skills`，且目标目录已存在时
`cp -r` 会套娃出 `codebase-explorer/codebase-explorer/`。一律用下面的 `rsync`。

### Claude Code

```bash
mkdir -p ~/.claude/skills/codebase-explorer
rsync -a --delete \
  /absolute/path/to/codebase-explorer/.agents/skills/codebase-explorer/ \
  ~/.claude/skills/codebase-explorer/
```

### Agents / Grok（`~/.agents/skills`）

Grok Build 与部分 agent 宿主读的是这个目录，不是 `~/.codex/skills`。

```bash
mkdir -p ~/.agents/skills/codebase-explorer
rsync -a --delete \
  /absolute/path/to/codebase-explorer/.agents/skills/codebase-explorer/ \
  ~/.agents/skills/codebase-explorer/
```

### Codex

Codex 文档路径是 `~/.codex/skills`。若本机 Codex 实际读的是 `~/.agents/skills`，
上一节已经覆盖；两套都装也可以，但内容必须与仓内真源一致。

```bash
mkdir -p ~/.codex/skills/codebase-explorer
rsync -a --delete \
  /absolute/path/to/codebase-explorer/.agents/skills/codebase-explorer/ \
  ~/.codex/skills/codebase-explorer/
```

复制命令的源目录带末尾 `/`。验证没有重复套娃，并且两份活拷贝一致：

```bash
test -f ~/.claude/skills/codebase-explorer/SKILL.md
test ! -e ~/.claude/skills/codebase-explorer/codebase-explorer
test -f ~/.agents/skills/codebase-explorer/SKILL.md
test ! -e ~/.agents/skills/codebase-explorer/codebase-explorer
diff -ru ~/.agents/skills/codebase-explorer ~/.claude/skills/codebase-explorer
```

## 4. 挂载 MCP Server

### Claude Code

推荐 user scope：

```bash
claude mcp add --scope user --transport stdio codebase-explorer -- \
  uv run \
  --directory /absolute/path/to/codebase-explorer \
  python -m src.server
```

等价的 `~/.claude.json` server object：

```json
{
  "mcpServers": {
    "codebase-explorer": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/codebase-explorer",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```

只合并 `codebase-explorer` 成员，不覆盖配置文件的其他键。

### Codex

```bash
codex mcp add codebase-explorer -- \
  uv run \
  --directory /absolute/path/to/codebase-explorer \
  python -m src.server
```

等价的 `~/.codex/config.toml`：

```toml
[mcp_servers.codebase-explorer]
command = "uv"
args = [
  "run",
  "--directory",
  "/absolute/path/to/codebase-explorer",
  "python",
  "-m",
  "src.server",
]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 120
```

### OpenCode

把下面的成员合并到 `~/.config/opencode/opencode.json` 的 `mcp` object：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "codebase-explorer": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--directory",
        "/absolute/path/to/codebase-explorer",
        "python",
        "-m",
        "src.server"
      ],
      "enabled": true,
      "timeout": 20000
    }
  }
}
```

## 5. 宿主侧 discovery

修改配置后重启宿主。Skill 文件出现在 `~/.claude/skills` / `~/.agents/skills` **不等于**
MCP 已连接。本 checkout 的活 MCP 挂载是实现目录里的 `.mcp.json`（以及同目录
`opencode.json`）。在 monorepo 根目录打开宿主时，根上没有 `.mcp.json`，user-scope 也必须
单独登记，否则宿主看不到这 14 个工具。

```bash
claude mcp get codebase-explorer
claude mcp list

codex mcp get codebase-explorer
codex mcp list

NO_COLOR=1 opencode mcp list
```

成功判据：server 状态 connected，宿主显示 README 中列出的 14 个工具。只看到 skill 文件不算
MCP 已连接；只看到 MCP server 而 skill 仍列旧工具也不算可用。`claude mcp list` 在部分环境
会长时间无输出，不要把它当成唯一判据；以 §2 的 `await mcp.list_tools()` 和下面的五连调用为准。

## 6. 契约测试

```bash
cd /absolute/path/to/codebase-explorer
uv run pytest -q tests/test_skill_contract.py
```

这条测试直接比较仓内 skill 的工具声明集合和 `await mcp.list_tools()`。改名、漏工具或多写
幽灵工具都会令它失败。

全局同步后可复核文件相同：

```bash
diff -ru \
  /absolute/path/to/codebase-explorer/.agents/skills/codebase-explorer \
  ~/.claude/skills/codebase-explorer
diff -ru \
  /absolute/path/to/codebase-explorer/.agents/skills/codebase-explorer \
  ~/.agents/skills/codebase-explorer
```

空输出代表活拷贝与仓内真源一致。

### 6.1 接线五连（不经宿主、直接 stdio）

不依赖 Claude/Codex user-scope 是否已登记。对一个至少 3 个 Python 文件的目录：

```bash
cd /absolute/path/to/codebase-explorer
uv run python - <<'PY'
import asyncio, json, time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

impl = Path("/absolute/path/to/codebase-explorer")
spec = json.loads((impl / ".mcp.json").read_text())
server = spec["mcpServers"]["codebase-explorer"]
params = StdioServerParameters(command=server["command"], args=server["args"], cwd=str(impl))
repo = Path("/absolute/path/to/small-python-repo")

async def main():
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("list_tools", len(tools.tools), [t.name for t in tools.tools])
            async def call(name, args):
                t0 = time.perf_counter()
                result = await session.call_tool(name, args)
                text = result.content[0].text
                payload = json.loads(text)
                print(name, round((time.perf_counter()-t0)*1000, 1), "ms", payload.get("status"))
                return payload
            analyzed = await call("analyze_codebase", {"path": str(repo), "force_reindex": True})
            root = analyzed["output_dir"]
            await call("get_structure", {"output_dir": root})
            await call("get_modules", {"output_dir": root})
            await call("get_dependency_graph", {"scope": "project", "output_dir": root})
            progress = await call("get_semantic_progress", {"output_dir": root})
            print("coverage", progress.get("coverage_percent"), "symbols", progress.get("totals"))

asyncio.run(main())
PY
```

成功判据：`list_tools` 长度为 14 且名称与 README 一致；五次调用 `status=success`。
这只证明接线，不证明语义生产完成（完成契约见 §7 / §9）。

## 7. 第一次真实运行

在新 Codex session 中要求：

```text
使用 codebase-explorer 分析 /absolute/path/to/target-repo。
执行完整语义闭环：analyze；循环 claim/submit 到静态符号覆盖 100%；
render_semantic_docs；最后执行独立 semantic review。
所有后续 MCP 调用都传 analyze 返回的 output_dir。
```

运行中：

1. `analyze_codebase` 返回 `output_dir`、结构图和 semantic ledger；
2. MCP host 从 `CODEX_THREAD_ID` 取得真实 Codex exec session 作为 lease owner，
   并从 `$CODEX_HOME/sessions` 自动定位其唯一 rollout，以最终结构化输出作为提交证明；
3. `get_semantic_progress` 独立复算覆盖，目标是 100%、无 uncovered/stale；
4. renderer 写 `.codebase-docs/INDEX.md` 与 module `DETAIL.md`；
5. server 调度独立 Codex reviewer；`revision_required` 会让对应符号重新进入生产循环。

## 8. 断点恢复

至少保存：

- target repo 绝对路径；
- `output_dir`；
- 最后一个未提交 packet 的 `batch_id`、`source_revision`、完整 payload；
- producer 的真实 Codex thread ID；对应 rollout 由 server 在
  `$CODEX_HOME/sessions` 内自动解析，不作为 MCP 参数传入。

恢复同一 Codex exec session，使 MCP host 的 `CODEX_THREAD_ID` 仍等于 lease owner；MCP
重连后先调用 `get_semantic_progress(output_dir=...)`。未过期 packet 可用与提交内容完全一致的
原 rollout 证明整批重试；lease 过期则重新 claim。提交失败不会部分更新 ledger/docs。

## 9. 验收边界

```bash
uv run pytest -q \
  tests/test_skill_contract.py \
  tests/real/test_semantic_disclosure_e2e.py
```

这两份测试验证工具契约和管道性质。它们不验真实解释质量。真实产品验收还需要：

- 对真实代码库跑到静态符号覆盖 100%；
- INDEX 中有依赖图，DETAIL 中有函数级 symbol blocks；
- 独立 review 返回 accepted；
- 人或独立 verifier 对真实解释做语义判断。

当前 server 没有 runtime coverage 导入工具。需要按测试执行热度排阅读优先级时，应将它记录为
待实现能力，不能用静态覆盖结果冒充。
