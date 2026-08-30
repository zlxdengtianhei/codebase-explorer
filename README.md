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
ir/3 恢复后全量收集 1235 测试：1213 passed / 5 skipped / 17 failed（**开发树读数**：产自 monorepo 开发谱系 commit 3fcb3da42c，该谱系正在向本仓同步；本仓当前快照的实测见上一段 106 passed），
17 个失败均证明先存或环境（16 个因 test_repos 离盘、1 个 e2e 在恢复前沙箱同现；见诚实边界与 r008 护航回执）。

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

### celery 分批 materialize（2026-08-30 本轮真实证据，C5 part2）

对 celery（HEAD `c35b1d5e`，closed world 161 文件 / 3258 符号）跑通「claim → 整批校验 → 提交」真缝分批 materialize：
driver 回放 r007 冻结的 160 个真实 LLM 解释（logs_v3 public/responses，153 份响应），72 个符号经 72 批提交落进 canonical 台账，
台账 explained 33 → 105（105/3258 ≈ 3.2%，为原读数的 3.2 倍），driver 正常收敛
（`claim None after 37312 claims: no unleased non-fresh candidates`），stdout 末行 `[PASS] explained 77 -> 105`（该轮 77→105，战役累计 33→105）。

- 以下为**开发树运行证据**（monorepo r008 运行，关键文件已 vendor 进本仓 docs/evidence/）：canonical 台账 `celery_c35b1d5e/closed_world_161/.codebase-analysis/semantic_ledger.json`
  （种子由 r007 `snapshot/CELERY_REV24_LEDGER.json` rebind repo_root 而来：store.commit 对 repo_root 有机械守卫，台账迁 canonical 新家；
  before=33 对齐与 rebind 记录见 [docs/evidence/c5_celery_before_snapshot.md](docs/evidence/c5_celery_before_snapshot.md)）
- 逐批证据：[docs/evidence/c5_celery_materialize_log.jsonl](docs/evidence/c5_celery_materialize_log.jsonl)（72 条 batch_committed + run_end 汇总）；before=33 对齐记录：[docs/evidence/c5_celery_before_snapshot.md](docs/evidence/c5_celery_before_snapshot.md)
- 残差：160 个预计算符号落册 72 个；其余 88 个中，10 个所在 SCC 批混有非目标符号（被「整批全目标才提交」机制排除），
  78 个所在批全为目标符号但依赖前沿尚未就绪（终态 scheduler state 中未进入 live packet），随依赖落册可在后续批次认领；
  剩余 3153 个符号未覆盖，待后续批次。

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
  celery 本轮 materialize 管道已打通，explained 33 → 105（105/3258 ≈ 3.2%，证据见上「测试结果」节），
  剩余 3153 个符号待后续批次；django、sqlalchemy 等大仓仍从未有语义生产。
- **ir/3 import 缺陷已修复（2026-08-30，commit 3fcb3da42c）**：`src/ir` 升到 cbe-ir/3（恢复暂停分支 ac7f5d5b65 的
  26 个 src + 13 个 tests 文件，逐 blob 一致），`reverse_edges` 期望的 5 个类型（CallOutcome 等）import 恢复，
  semantic-service 链打通，celery materialize 的前置阻塞解除。残差：`l2_cluster`/`l2_status` 仍 dormant
  （依赖分支 file_cards → feature_cone 危险区，缓行）。
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