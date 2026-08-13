# Codebase Explorer

Codebase Explorer 是本地 MCP Server 与 Agent Skill。它把代码库解析为依赖图和全量符号清单，
再由 Codex 按依赖顺序生成函数级语义解释，持久化覆盖账，渲染渐进式文档，并交给独立 Codex
reviewer 抽样复核。

当前 server 的真实导出面为 14 个工具。工具名由
`await mcp.list_tools()` 现算，skill 契约测试负责阻止两边再次漂移。

## 产物

```text
<repo>/
├── .codebase-analysis/
│   ├── active_run.json
│   ├── semantic_ledger.json
│   ├── semantic_events.jsonl
│   └── semantic_reviews/
└── .codebase-docs/
    ├── INDEX.md
    └── <module>/DETAIL.md
```

文档提供四个逻辑层级：

1. INDEX：项目入口、模块导航、Mermaid 依赖图；
2. module DETAIL：一个功能模块的文件和关系；
3. file section：文件职责与符号清单；
4. symbol block：函数、方法和类的语义解释。

canonical truth 是 `semantic_ledger.json`。Markdown 是可重建投影，不是第二份人工真源。

## 当前能力边界

- 结构分析：Python、TypeScript、JavaScript。
- 函数级语义清单和解释：目前为 Python。
- 覆盖率：`get_semantic_progress` 从源码清单独立复算静态符号覆盖。
- 运行时 coverage 导入：当前 14-tool API 尚未暴露，因此本版不能声称按真实执行热度排阅读顺序。
- E2E pytest：只证明管道连通、事务原子和重连恢复；真实语义质量由 Codex 生产与独立 review 证明。

## 快速开始

完整的 Claude Code、Codex 和 OpenCode 接线见 [INSTALL.md](INSTALL.md)。

```bash
uv sync
uv run python -m src.server
```

把仓内 skill 同步到 Claude Code 的全局 skill 目录：

```bash
mkdir -p ~/.claude/skills/codebase-explorer
rsync -a --delete \
  .agents/skills/codebase-explorer/ \
  ~/.claude/skills/codebase-explorer/
```

源路径末尾的 `/` 很重要。它复制目录内容，避免生成
`codebase-explorer/codebase-explorer/` 自套娃。

## 核验 14 个真实工具

```bash
uv run python - <<'PY'
import asyncio
from src.server import mcp

tools = asyncio.run(mcp.list_tools())
print(len(tools))
print("\n".join(tool.name for tool in tools))
PY
```

应输出：

```text
14
analyze_codebase
get_semantic_progress
claim_semantic_batch
submit_semantic_batch
get_semantic_review_batch
submit_semantic_review
get_structure
get_modules
get_function_deps
doc_operation
get_dependency_graph
get_progress
get_file_tokens
submit_analysis
```

## 运行语义闭环

Agent 按 [.agents/skills/codebase-explorer/SKILL.md](.agents/skills/codebase-explorer/SKILL.md)
执行四个阶段：

1. `analyze_codebase` 建结构、依赖图、符号清单和 canonical ledger；
2. 循环 `claim_semantic_batch` / `submit_semantic_batch`，直到静态符号覆盖 100%；
3. `doc_operation(operation="render_semantic_docs")` 从 ledger 重建 INDEX/DETAIL；
4. `get_semantic_review_batch` / `submit_semantic_review` 做 blind review，若要求修订则回到第 2 步。

所有后续调用都要传 `analyze_codebase` 返回的绝对 `output_dir`。MCP host 必须通过
`CODEX_THREAD_ID` 暴露真实 Codex exec session；claim 从该可信进程状态取得 lease owner，
submit 再到 `$CODEX_HOME/sessions` 自动定位唯一对应的 rollout。调用者不传 actor 或路径；
rollout 内的最终结构化 proof 必须与提交 payload 逐字等价。

## 测试

```bash
uv run pytest -q \
  tests/test_skill_contract.py \
  tests/real/test_semantic_disclosure_e2e.py
```

`test_skill_contract.py` 会在 skill 与 server 工具名漂移时变红。
`test_semantic_disclosure_e2e.py` 在临时仓库上走真实 MCP transport，验证失败提交不改
ledger/docs，以及保存的 lease packet 可在客户端重连后继续提交。

## 项目结构

```text
src/
├── server.py
├── parser/
├── graph/
├── semantic/
├── state/
├── budget/
└── doc/

.agents/skills/codebase-explorer/
├── SKILL.md
├── phases/
└── references/
```

## Requirements

- Python 3.12 或 3.13
- uv
- MCP host：Claude Code、Codex 或 OpenCode
- 真实语义生产和 review 使用 Codex session

## License

MIT
