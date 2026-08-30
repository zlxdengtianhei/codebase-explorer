# Codebase Explorer

Codebase Explorer 是本地 MCP Server 与 Agent Skill。它把代码库解析为依赖图和全量符号清单，
按功能模块（Feature Cone）划分，递归生成多层渐进式披露文档（L0 入口 → L1 模块 → L2 文件 → L3 符号），
函数级语义解释写入 canonical ledger，并可交独立 reviewer 信息不对称复核。

> 设计真源：[docs/DESIGN.md](docs/DESIGN.md)（多层递归 + 功能架构优先 + 递归深度守卫 + 确定层瘦身）。

## 为什么这样设计

用一两个文档描述整个代码库、动辄 8000 多行，是错的。复杂系统要多层结构与渐进式披露：
底层详细文档，往上逐层抽象，整体递归关系。Codebase Explorer 以**功能模块划分**（Feature Cone）
为主分层，而非物理文件树；两者冲突时以功能架构为主，文件树作兜底参照。递归深度有上限
（`MAX_DEPTH`）并有真实触发守卫，防止递归过深。思路借鉴 Obsidian 的双向链接与渐进披露，
但不照搬其扁平知识图谱——代码有深嵌套，递归层级是第一性。

## 产物

```text
<repo>/
├── .codebase-analysis/
│   ├── active-run.json          # 确定性分析产物 + canonical ledger 入口
│   ├── semantic_ledger.json     # canonical truth：符号 explained/residual 状态
│   ├── .runs/<run>/             # 01_structure / 02_dag / 03_feature_cones / 04_file_tokens / 05_task_manifest / 06_function_deps
│   └── semantic_reviews/
└── 多层 INDEX/DETAIL 树（L0 入口 → L1 模块 INDEX → L2 文件 DETAIL → L3 符号 DETAIL，递归，带 depth_capped 守卫）
```

canonical truth 是 `semantic_ledger.json`。Markdown 是可重建投影，不是第二份人工真源。

## 测试结果（附证据，不只列命令）

### 确定性核心（2026-08-30 于本仓发布快照实测）
```
$ uv run pytest -q tests/test_skill_contract.py tests/test_server_helpers.py
106 passed in 5.66s
```
`test_skill_contract.py` 在 skill 与 server 工具名漂移时变红；`test_server_helpers.py` 覆盖确定性辅助。
全量收集 1108 测试，其中依赖 semantic-service 的测试因一个已知 import 缺陷在收集期报错（见诚实边界）。

### 第一米 MCP 接线（2026-08-30 本轮真实证据）
真实 MCP stdio 会话调用 `analyze_codebase` 跑通 flask，server `codebase-explorer/1.26.0` 暴露 14 工具，
确定性流水线生成 `active-run.json` 于目标仓（1526 bytes，0600）。
receipt：[docs/evidence/c4_mcp_call_receipt.md](docs/evidence/c4_mcp_call_receipt.md)。

### 多层递归原型（2026-08-30 本轮真实证据，C5）
渲染器原型：[docs/evidence/c5_multilayer_renderer.py](docs/evidence/c5_multilayer_renderer.py)（正式并入 src/doc 的工作在路上），消费 C4 产出的 03_feature_cones.json
（flask 3 个功能模块 cli/provider/blueprints）+ 01_structure.json + 06_function_deps.json。
- MAX_DEPTH=4 自然树：`c5_tree_depth4/`，层数统计 L0=1 / L1=3 / L2=6 / L3=65（4 层 ≥3），无截断。
- MAX_DEPTH=2 守卫触发：`c5_tree_depth2/`，递归守卫对 L2 文件（如 `json/tag.py` 44 符号）触发 `DEPTH_CAPPED`，
  截断平铺并标注 `depth_capped=true`。守卫为纯决策单元（仅 `(depth, symbol_count, has_substructure) → LEAF/DESCEND/DEPTH_CAPPED`）。

```
$ python3 c5_multilayer_renderer.py --gen-dir <flask generation> --out-dir c5_tree_depth4 --max-depth 4
{"layer_node_counts": {"0":1,"1":3,"2":6,"3":65}, "max_layer_reached": 3, "depth_capped_events": []}
$ python3 c5_multilayer_renderer.py ... --max-depth 2
{"depth_capped_events": [{"layer":"L2","file":"json/tag.py","symbol_count":44,"decision":"DEPTH_CAPPED"}, ...]}
```

### 竞品对标读数（可复算）
r003 round4 用预先冻结的确定性判据量入口页导航（一条命令可复算）：

| 工具 | 入口页导航读数 |
|---|---|
| DeepWiki | 38/40 |
| zread | 39/40 |
| **Codebase Explorer** | 2/40（早期；本轮多层原型 + 函数级语义是差异点） |

外部文献（SWD-Bench，4170 条）：函数级细粒度文档（RepoAgent 52.63%）> 模块级（DeepWiki 47.37%）> 无文档（43.86%），
支持函数级路线。完整竞品与 benchmark 调研：[docs/evidence/COMPETITOR_BENCH_SURVEY.md](docs/evidence/COMPETITOR_BENCH_SURVEY.md)。

## 诚实边界

- **语义解释仅 Python**。TypeScript/JavaScript 仅 `syntax_only` 影子分析，未通。
- **大仓尚未全量打通**。flask 415/415、httpx 521/521 全符号真解释（历史，r002 首达、r006 独立门放行）；
  celery 停在 33/3258（约 1%），django、sqlalchemy 等大仓从未有语义生产。本轮 C5 只做 flask 多层原型 + 守卫触发演示，
  celery 分批 materialize（after>33）阻塞于一个 import 缺陷的修复（见下）。
- **已知 import 缺陷（影响 semantic-service 测试与 celery materialize）**：`src/graph/reverse_edges.py` 期望 cbe-ir/3
  的 5 个类型（CallOutcome 等），但当前 `src/ir` 仍是 cbe-ir/2，import 失败。确定性分析流水线（C4 第一米）不受影响，
  semantic-service 链受影响。修复 = 推广已暂停的 ir/3 semantic 分支，是后续工作。
- **独立 review 的隔离贡献尚无隔离测量证据**：reviewer 信息不对称是设计要求（防 LLM verifier confirmation bias），
  但其相对非对称 review 的增量贡献尚未隔离测出。
- **消费形态必须检索式，禁常驻注入**：两项独立研究（ETH n=138、Khatri n=288）在常驻注入形态下零/负效应。

## 快速开始

完整接线见 [INSTALL.md](INSTALL.md)。

```bash
uv sync
uv run python -m src.server
```

核验 14 个真实工具：
```bash
uv run python - <<'PY'
import asyncio
from src.server import mcp
tools = asyncio.run(mcp.list_tools())
print(len(tools), [t.name for t in tools])
PY
```

## 项目结构

```text
src/
├── server.py            # FastMCP 14 工具
├── parser/  graph/  semantic/  state/  budget/  doc/
.agents/skills/codebase-explorer/   # Skill 真源
```

## Requirements
- Python 3.12 或 3.13 ｜ uv ｜ MCP host（Claude Code / Codex / OpenCode）

## License
MIT（见 [LICENSE](LICENSE)）。