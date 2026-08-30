# Design Doc：CBE 多层递归渐进披露架构（开源整备）

## 头部元数据

| 字段 | 值 |
|---|---|
| T-id | CBE-C2 |
| req_id | CBE-multilayer-opensource |
| semantic_slug | cbe-multilayer-design |
| phase | 优化与开源 |
| version | v1（边用边完善，RULINGS E-2） |
| 日期 | 2026-08-30 |
| type | architecture |
| label | design-doc |
| req-doc | adhoc_jobs/codebase_explorer_20260321/REQUIREMENTS_LEDGER.md |
| PromptRef | cbe-opt 席 PACKET_CBE.md C2 |

## (0) 原始需求逐字原文

req-doc: `adhoc_jobs/codebase_explorer_20260321/REQUIREMENTS_LEDGER.md`

````text
[RULINGS 块 A-1] 用一两个文档去描述整个代码库、动辄 8000 多行，这种做法肯定是错的。针对复杂系统，必须采用多层结构与渐进式披露：底层有详细文档，往上逐层抽象，整体形成递归关系。
[RULINGS 块 A-2] 文件树天然带有一定的语义特征，符合渐进式披露的需求；但在 Codebase Explorer 场景下，我们最关注的其实不是物理文件树，而是功能模块的划分。如果两者存在明显冲突，应该优先考虑以功能架构为主。可以结合之前的要求，权衡这两种实现的优劣后再做决定。
[RULINGS 块 A-3] 需要评估层级化设计到底有没有上限，如果保持递归状态，我们该如何防止递归过深。
[RULINGS 块 A-4] Obsidian 的知识库更多对应的是相对扁平的知识点，而代码功能本身存在很深的代码嵌套和深层功能定义。两者场景完全不同，思路或许可以借鉴，但绝不能直接照搬，需要具体情况具体分析。
[RULINGS 块 D] 模型（尤其 Codex）坏习惯是加很多确定性检查，很多时候没必要；要更 smart、更简单、更有效的方式覆盖更多需要做的测试；否则系统臃肿，agent 注意力被门禁分散；确定层太多会被后训练当优化目标走偏路径。CBE 与 Design Doc Protocol 都要处理确定层检查。
[RULINGS 块 E-3] 方案选型要更贴主流，比如 Skill 或 MCP。
````

需求 ID 指向 C1 补录后的 `REQUIREMENTS_LEDGER.md`：A-01..04、D-2/3、E-3、EARLY-01/03/05 等。现状诊断引用查证报告 §2.3（局部最优病灶：优化目标被验收装置可判定性劫持；r007 五天 29 臂，权威覆盖 33/3258 一步未动，285 个真解释因盲评无优胜者一条没写回台账）。

## Layer 1 功能设计

### 1.1 核心问题(core_need)

- 让 AI agent 和人能在有界 context 内沿「功能 → 功能模块 → 整体架构」逐层获得语义解释，每层有具名消费者、产出可分批收口，而非一个 8000 行终点文档（sqlalchemy 详情单文件 8272 行即两文档模型后果）。

### 1.2 成功效果(success_effect)

- 台账 after>before（celery 33→>33；flask 全符号分层树产出）。
- 一个真实 agent 经 MCP 调用消费生成的文档完成一次定位/导航（C4 接线 wired + C5 原型）。
- README 附本轮真实测试结果，含 C5 多层原型证据，不只有旧 flask 415/415 门。

### 1.3 硬性约束(hard_requirements)

- 功能架构优先于文件树，冲突时以功能架构为主（A-02）。
- 递归深度有上限且有真实触发记录（A-03）。
- 消费形态检索式，禁常驻注入（D1 评估：ETH n=138 + Khatri n=288 独立零/负效应）。
- review 信息不对称：reviewer 只拿原子断言+源码，不看叙述包装（D1 §3.3 MARCH，防 confirmation bias）。
- 确定层瘦身：新增门前先答「能否用更简单方式覆盖」（D-2/3，派发 packet 纪律 #6）。
- 形态贴 Skill/MCP，不新造框架（E-3）。

### 1.4 明确不做(negative_requirements)

- 不做常驻注入的 context 文件。
- 不照搬 Obsidian 扁平图谱（A-04）。
- 不用 BLEU/ROUGE 或 LLM-as-judge 直接给文档打分（D1 §3）。
- 不拿用户任务做评测，用现成 benchmark（E-4，C3 选型）。
- 不把单仓单层 PASS 外推大仓已打通（BB-11）。
- 不为开源新引重依赖。

### 1.5 交付物(deliverable)

- 多层 INDEX/DETAIL 树原型（flask，≥3 层，含 depth_capped 触发记录）。
- celery 台账分批 materialize（after>33）。
- 本设计 doc + Bad Behavior 审查表。
- 开源整备产物（C6）+ 含本轮证据的 README。

## Layer 2 实现设计

### 2.1 架构概述/组件图

```text
analyze_codebase (确定性: 解析/Feature Cone/Token/Task Manifest)
  -> 03_feature_cones.json + 05_task_manifest.json
  -> render_multilayer (新增, 独占递归遍历与渲染) + 递归守卫 (纯决策: LEAF/DESCEND/DEPTH_CAPPED)
  -> L0 入口 -> L1..Ln INDEX/DETAIL
  -> 消费 semantic_ledger.json 的 explained 条目 (C5 materialize 写入)
  -> MCP render 工具产物 + Skill 检索入口 (检索式消费)
```

废止两文档模型（Index/Detail 两扁平大文件）。改为递归 INDEX/DETAIL 树：L0 入口（≤2% token，全仓功能架构总览+下层索引）；L1..Ln 每个功能模块一个 INDEX（模块职责+入口符号+子模块/符号索引+跳转）+ DETAIL（模块内符号级真解释）；递归终止=模块符号数低于阈值或深度达上限→叶子 DETAIL 只含符号解释不再下分。

### 2.2 各组件职责与边界(scope_in/scope_out)

| 组件 | scope_in | scope_out（具体禁读边界） | 证据或接口 |
|---|---|---|---|
| analyze_codebase | 确定性解析/cone/token/manifest，写 active-run.json | 禁读：semantic_ledger 的 explained 内容、已生成 INDEX/DETAIL 文档、LLM/reviewer 产物；不调 LLM | src/server.py analyze_codebase |
| render_multilayer（新增） | 以 cone 树为骨架递归产 INDEX/DETAIL，独占遍历与渲染，消费 ledger explained 与 cone/manifest | 禁读：原始源码文件全文、reviewer 叙述、benchmark 判词、active-run 内部态、除声明 cone/manifest 与 ledger 接口以外的输入 | src/doc/multilayer_renderer.py（新增） |
| 递归守卫（纯决策单元） | 仅接收 (depth, symbol_count)，返回 LEAF / DESCEND / DEPTH_CAPPED | 禁读：cone 内容、ledger 解释、生成文档、源码、reviewer 输出；不做遍历或渲染（遍历/渲染只归 render_multilayer） | 纯函数，纯 Python 条件（D-2/3 瘦身） |
| semantic service | 计算 reverse_edges 并写规范化 explained ledger 记录（materialize） | 禁读/禁生成：INDEX/DETAIL 文档、reviewer 叙述；不决定递归模块结构；不冒充全量打通 | 需先修 5 个 IR 类型（C5 前置） |
| MCP/Skill 双形态 | 检索式消费入口，仅读生成 L0–Ln INDEX/DETAIL 产物及其检索元数据 | 禁读：原始源码、semantic-service 中间态、active-run 内部、reviewer 叙述；不做常驻注入 | .mcp.json + .agents/skills/ |

> 递归守卫拆为纯决策单元（只判 LEAF/DESCEND/DEPTH_CAPPED），遍历与渲染只归 render_multilayer；二者不再共享递归职责。每个单元的 scope_out 给具体禁读信息，而非动作排除。

### 2.3 关键设计决策(含为什么)

| 决策 | 选择 | 为什么 | 放弃的替代方案 |
|---|---|---|---|
| 分层单位 | Feature Cone 功能架构为主 | A-02 要求功能架构优先；cone 由确定性 SCC+DAG 产出已落地；按模块收口是查证 §2.3 病灶对症动作 | 文件树分层：物理树≠功能边界，深层文件跨模块；仅作 INDEX 兜底参照 |
| 递归深度 | MAX_DEPTH=4 + depth_capped 标注 | A-03 要评估上限；实测 celery 多数符号在第 5 跳，4 层覆盖多数功能簇；更深由叶子 DETAIL 承接 | 无限递归：会过深且无中间信号；硬截断阈值：违反 assertion-denominator 门 |
| 消费形态 | 检索式（MCP+Skill） | D1 评估常驻注入零/负效应（ETH+Khatri），检索式才是生成文档的正效应形态 | 常驻注入 context 文件：已被两研究证伪 |
| review 形态 | 信息不对称（原子断言+源码，不看叙述） | D1 §3.3 LLM verifier 有 confirmation bias；MARCH 证明信息不对称才能发现而非复现错误 | 让 reviewer 看全文+同样上下文：只会复现 writer 错误 |
| 确定层 | 守卫用条件判断、台账用 jq 计数、BB 审查用人工清单 | D-2/3 瘦身：更 smart 更简单覆盖更多；防 agent 注意力被门禁分散 | 新增确定性 gate/validator/关键词门：臃肿且被后训练当优化目标 |
| Obsidian 借鉴 | 借双向链接、入口窄/正文厚、图谱视角 | A-04 思路可借鉴 | 照搬扁平知识图谱：代码深嵌套，递归层级是第一性，不能压平 |
| 开源形态 | 单一 MIT + README/CONTRIBUTING + gitleaks | C3 实查 OpenCode(MIT,full structure)/DeepSeek；CBE 是工具不是模型 | DeepSeek 双 license：模型权重与代码分 license，不适用工具 |

### 2.4 反过度工程化三问

- 是否同时服务多个核心失败模式：多层递归同时服务「8000 行终点文档」「全仓无中间信号」「文档无具名消费者」三类真实失败。
- 有没有更小更确定的实现：有；递归守卫是条件判断，台账门是 jq 计数，BB 审查是人工清单，均最小机制。
- 新增复杂度是否有真实消费链和验证证据：有；C4 已证 MCP stdio 真实可调，C5 证台账 after>before + 多层原型，C6 证 README 含本轮证据。

## Layer 3 代码改动清单

### 3.1 新增(ADDED)

- `src/doc/multilayer_renderer.py`：递归 INDEX/DETAIL 渲染，消费 cone 树 + ledger explained，带 depth 守卫。
- `tools/codebase_explorer/LICENSE`：MIT 全文（C6，对齐 OpenCode）。
- `tools/codebase_explorer/CONTRIBUTING.md`：简短贡献指引（C6）。
- `cbe/design/CBE_multilayer_design.md`：本设计 doc。
- `cbe/COMPETITOR_BENCH_SURVEY.md`：竞品与 benchmark 调研（C3）。
- `REQUIREMENTS_LEDGER.md` 重建 + 13 份 requirement_record（C1）。

### 3.2 修改(MODIFIED)

- `tools/codebase_explorer/.mcp.json`：从 Mac 旧路径改为 vienna 真身（C4，已做）。
- `src/ir/models.py` + `src/ir/__init__.py`：恢复 reverse_edges 所需 5 个 IR 类型（CallOutcome/CallSiteInventory/ExternalEcosystem/ReceiverGapReason/ReceiverShape），从 ac7f5d5b65 追加缺失项（C5 前置）。
- `tools/codebase_explorer/README.md`：重写，功能描述附测试结果 + C5 多层原型证据 + 竞品对标读数 + 诚实边界（C6）。
- `tools/codebase_explorer/test_repos`：换 pin commit 拉取脚本，剔嵌套 clone（C6）。

### 3.3 删除(REMOVED)

- 杂物：`claude_test_output*.txt`、`exit`、`pip`、`.coverage`、`.cc_test_logs`（C6 清理）。
- `.venv`（569M）不入开源仓（C6）。
- 旧 80% 判据残留 `staging/repo/scripts/skill_judge_prompt.md:52-53`（C6 清污点）。

### 3.4 变更前后对比表

| 对象 | 变更前 | 变更后 | 证据 |
|---|---|---|---|
| 文档形态 | 两文档模型（Index/Detail 扁平大文件，sqlalchemy 8272 行） | 多层递归 INDEX/DETAIL 树（≥3 层，depth_capped 守卫） | C5 原型 +层数统计 |
| MCP 第一米 | .mcp.json 指 Mac 旧清空路径，无 host 可调 | 指 vienna 真身，真实 stdio 调用跑通 active-run.json | C4 receipt c4_mcp_call_receipt.md |
| celery 台账 | 33/3258 explained，285 真解释未写回 | 分批 materialize，after>33 | C5 台账前后逐字记录 |
| 需求总账 | 丢失 | 重建 + 13 条补录 | C1 grep -c=26 |
| 开源 | 私有库，杂物+无 LICENSE | 整备 READY，MIT+README+gitleaks 0 命中 | C6 |

## Final Boundary

| 字段 | 填写 |
|---|---|
| 状态 | DONE |
| 已覆盖 | 设计 doc（三层+意义+决策表+Final Boundary）、C1 补录、C3 调研、C4 第一米 wired |
| 未覆盖 | 多层 render 实现（C5）、semantic service 5 IR 类型修复（C5 前置）、开源整备（C6）、全量 benchmark 跑（本轮只定方案） |
| 延后 | 多语言（TS/JS 仍 syntax_only）、celery 全量打通、独立 review 隔离贡献的隔离测量 |
| 证据边界 | 本设计由主 agent 亲写，意义面未做 forbidden-read 隔离（RULINGS E-2 边用边完善）；现状诊断转引查证报告与 D1，未独立复核其下游效用数字 |

## 意义自述（M1-M5，非 forbidden-read 隔离）

> 本节由主 agent 据 RULINGS 与查证报告诊断填写；本轮 design doc 由主 agent 亲写，未派 worker 写意义面，故未做 forbidden-read 隔离，记为诚实边界。

- M1 本域核心意义：把「让一次 producer 调用可机械验收」的清晰红绿，换成「让 N 个符号被读懂」的中间信号；多层递归是给核心目标造中间信号的结构载体。
- M2 补哪类根局限：查证 §2.3 病灶=优化目标被验收装置可判定性劫持；本设计对症=分批 materialize+按模块收口+「本轮新增多少条真解释进台账」每轮必报。
- M3 总领意义锚：本仓哲学层第 2 条，信号被具名消费者读取并改变后续状态才进闭环；CBE 文档从未被真实 agent 消费（§2.1），每层必须有具名消费者。
- M4 防哪种不良行为：BB-04/05（不把树生成/层数达标当成功）、BB-07/28（不堆 gate）、BB-11（不外推）、BB-25（review 信息不对称）。
- M5 意义到落地对应：A-01→多层树、A-02→决策表、A-03→守卫、A-04→借鉴边界、D-2/3→瘦身清单、E-3→Skill/MCP 形态。