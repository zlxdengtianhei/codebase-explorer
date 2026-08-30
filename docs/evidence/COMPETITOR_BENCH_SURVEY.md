# CBE 竞品与 benchmark 调研（COMPETITOR_BENCH_SURVEY）

> 2026-08-30 ｜ cbe-opt 席 ｜ 来源：D1 报告（`tmp/system_effect_validation_20260824/D1_codebase_understanding_eval.md`）+ 查证报告 §2.1/§6.3 + 对 OpenCode/DeepSeek 仓结构的 GitHub API 实查（2026-08-30）。
> 本轮只定评测方案，不跑全量。诚实边界：语义解释仅 Python、celery 级大仓未打通。

## 1. 同类项目逐个档案

### DeepWiki（Cognition）
- 来源 URL：https://docs.devin.ai/work-with-devin/deepwiki ｜ 第三方证据见 D1 §4.1（OpenWrt/blopker/Julia/HN/BigGo）。
- 评测方式：代理指标（覆盖率、引用深度、wiki 体量与仓体量相关性），无下游任务效用指标；SWD-Bench 独立量化排名末位（47.37%，D1 S1）。
- 实现异同：粗粒度模块摘要，无函数级、无依赖感知拓扑、无信息不对称 review；托管服务，生成后不随代码更新且不可删（OpenWrt 维护者投诉）。
- 开源方式：闭源托管服务（非开源仓）；`.devin/wiki.json` 让维护者指定页面结构。
- 对 CBE 含义：DeepWiki 的反面教材——幻觉被自信地当权威、不更新不可删；CBE 必须带置信度标注+时间戳+可重生。

### zread（Zread CLI / zread-skill）
- 来源 URL：https://zread.ai/cli ｜ https://github.com/ZreadAI/zread-skill （r003 E4_claims_raw.md P7 记录，2026-08-13）。
- 评测方式：r003 round4 用预先冻结的确定性判据量入口页（zread 39/40）；无下游任务效用。
- 实现异同：本地仓文档生成 CLI + skill（`./.zread/wiki/current`），帮 agent 用生成页代替逐文件爬源；非函数级语义、非依赖感知、无信息不对称 review。
- 开源方式：zread-skill 仓公开（github.com/ZreadAI/zread-skill）；CLI 本体见 zread.ai/cli，license 待核验。
- 对 CBE 含义：zread 是检索面竞品（入口/导航），与 CBE 函数级语义解释正交；CBE 亮点在 zread 没有的语义层。

### RepoAgent（EMNLP 2024 Demo）
- 来源 URL：https://arxiv.org/abs/2402.16667 ｜ https://github.com/UASTL/RepoAgent
- 评测方式：盲测偏好实验，生成文档 vs 人写胜率 70%（Transformers）/91.33%（LlamaIndex），3 评估者×150 样本；SWD-Bench 细粒度第一（52.63%，D1 S1）。
- 实现异同：细粒度（code snippet 级），依赖感知拓扑序（DocAgent ablation 证实拓扑序有用）；无信息不对称 review 隔离测量。
- 开源方式：开源仓（待核验 license；论文 Demo 级）。
- 对 CBE 含义：RepoAgent 是函数级+依赖感知的最近竞品；CBE 全符号覆盖 + 独立盲评链路是差异点。

### DocAgent（Meta/facebookresearch）
- 来源 URL：https://arxiv.org/abs/2504.08725 ｜ https://github.com/facebookresearch/DocAgent
- 评测方式：Completeness DA-CL 0.953 vs 0.724；Truthfulness 95.7% vs 61.1%；ablation 证实拓扑序有用（D1 S5）。
- 实现异同：五 agent（Reader/Searcher/Writer/Verifier/Orchestrator）+ 依赖感知拓扑序；有 Verifier 但其独立贡献未被隔离测量（D1 §3.3 缺口）。
- 开源方式：开源（facebookresearch）；license 待核验。
- 对 CBE 含义：DocAgent 的 Verifier 与 CBE 独立 review 同类；D1 §3.3 警示 LLM verifier 有 confirmation bias，review 必须信息不对称（reviewer 只拿原子断言+源码）。

### aider repomap
- 来源 URL：https://github.com/paul-gauthier/aider ｜ repomap 是 aider 的仓库地图功能。
- 评测方式：无独立下游效用评测（aider 主测 edit/commit 成功率，repomap 是其检索组件）。
- 实现异同：基于 ranked, importance-weighted code map 的检索，非语义文档；函数级但非全符号覆盖文档。
- 开源方式：Apache-2.0（aider 主仓）。
- 对 CBE 含义：aider repomap 是检索式消费的同类（D1 §6.2 支持检索式）；CBE 文档应可被这类检索消费。

### 2026 新品
- OpenWiki（LangChain，2026-07）：https://www.langchain.com/blog/introducing-openwiki-brains-general-purpose-wiki-memory-for-agents — 通用 agent wiki memory CLI；无第三方效果评测（D1 §4.4）。
- Sourcegraph CodeScaleBench（2026）：https://sourcegraph.com/resources/ebooks/code-scale-bench-report — 厂商自建 370 tasks；主张 context retrieval quality 直接预测任务成功；作者自曝方法论顾虑（D1 §4.2）。
- KGCompass / Codebase-Memory（arXiv:2603.27277）：https://arxiv.org/abs/2603.27277 — Tree-Sitter 知识图谱，SWE-bench Lite 58.3%（⚠️ 单源转引，D1 S2）。

## 2. 异同表

| 项目 | 粒度 | 依赖感知 | 独立 review | 消费形态 | 全符号覆盖 | 开源/License | 下游效用证据 |
|---|---|---|---|---|---|---|---|
| DeepWiki | 模块 | 无 | 无 | 托管/常驻 | 代理(体量相关) | 闭源 | 代理指标；SWD 末位 |
| zread | 文件/检索 | 无 | 无 | 检索(MCP) | 否 | 待核验 | 无 |
| RepoAgent | 函数/snippet | 有(拓扑) | 盲测偏好 | 文档 | 否(部分) | 开源(待核验) | 偏好+SWD 52.63% |
| DocAgent | 函数/snippet | 有(拓扑) | 有(未隔离) | 文档 | 否 | 开源(facebookresearch) | Completeness/Truthfulness |
| aider repomap | 函数(map) | 有(重要性) | 无 | 检索 | 否(map) | Apache-2.0 | 无独立 |
| OpenWiki | 通用 wiki | ? | 无 | 检索/常驻 | 否 | 待核验 | 无 |
| **CBE** | **函数级** | **有(Feature Cone)** | **有(信息不对称盲评)** | **检索(MCP+Skill)** | **是(全符号)** | **MIT(已声明,待补文件)** | **r006 flask 415/415 独立门放行; r003 入口页对标** |

**我们的亮点**：函数级全符号覆盖 + Feature Cone 依赖感知 + 信息不对称独立盲评链路（r006 flask 415/415 有独立门放行证据）+ 一条命令可复算的竞品对标（r003 round4 入口页 2/40 vs DeepWiki 38/40 vs zread 39/40）。RepoAgent/DocAgent 是最近竞品，但二者皆无 CBE 的全符号覆盖目标 + 可复算对标脚本。

## 3. 开源方式参考（RULINGS C-2/C-3）

### 实查：OpenCode（sst/opencode，2026-08-30 GitHub API）
- LICENSE：MIT（spdx_id=MIT）。
- 顶层结构：LICENSE、README.md（含 20+ 语种翻译）、CONTRIBUTING.md（10,367 bytes）、SECURITY.md、AGENTS.md、CONTEXT.md、.github、.gitleaksignore（用 gitleaks 做密钥扫描）、package.json、bun.lock、flake.nix、多 SDK。
- 特点：多语 README、显式 SECURITY/CONTRIBUTING、用 gitleaks 守卫、AGENTS.md 给 agent 入口。

### 实查：DeepSeek（deepseek-ai/DeepSeek-V3，2026-08-30 GitHub API）
- LICENSE：双 license——LICENSE-CODE（MIT）+ LICENSE-MODEL（DeepSeek 模型 license）；无单一 LICENSE。
- 顶层结构：LICENSE-CODE、LICENSE-MODEL、README.md、README_WEIGHTS.md、.github、inference/、figures/、.gitignore；无 CONTRIBUTING.md。
- 特点：模型权重与代码分 license、README_WEIGHTS 明示权重条款；这是模型发布形态，非工具发布。

### 对 CBE 的开源建议（消费上述调研）
- License：pyproject 已声明 MIT，补一个 `LICENSE` 文件（MIT 全文），对齐 OpenCode/RepoAgent；CBE 是工具不是模型，用单一 MIT 即可（不学 DeepSeek 双 license）。
- README：对齐 OpenCode 多段结构（功能/安装/使用/贡献/License）；功能描述必须附测试结果（RULINGS B-2/D 派生），且必须含 C5 多层原型本轮证据，不只引旧 flask 415/415。
- CONTRIBUTING：补一份简短 CONTRIBUTING.md（对齐 OpenCode）。
- SECURITY.md：可选（OpenCode 有）；CBE 可加一份简短的漏洞报告指引。
- 密钥扫描：对齐 OpenCode 的 .gitleaksignore + 全历史 gitleaks 扫描（C6 执行）；历史 bundle 已脱敏（07-10 迁移制备），原始未脱敏 bundle 绝不发布。
- 仓结构：剔 .venv（569M）与 test_repos 嵌套 clone（123M）；test_repos 换 pin commit 的拉取脚本（C6 执行）。
- 形态：MCP server + Skill 双形态（RULINGS E-3 贴主流），不新引依赖；消费形态检索式（D1 禁常驻注入）。

## 4. benchmark 选型结论与理由

### 不拿用户任务做评测（RULINGS E-4），替代集如下

**首选：SWD-Bench（documentation-driven）**
- 来源：https://arxiv.org/abs/2604.06793 ｜ 4170 条，三类功能驱动 QA。
- 理由：唯一为此（仓库级文档质量经下游任务）而生的 benchmark；不用 LLM-as-judge 给文档打分；排序 RepoAgent 52.63% > DocAgent 49.12% > AutoDoc 49.12% > DeepWiki 47.37% > 无文档 43.86%，函数级胜模块级（支持 CBE 路线）。
- 用法：把 CBE 生成文档作为 SWE-Agent 的文档条件，跑 issue 解决率与 file location 率，对照无文档/DeepWiki 臂。

**必做对照：Code-QA-Bench（三条件设计）**
- 来源：https://arxiv.org/abs/2605.29277。
- 理由：closed-book / code-only / documented 三条件；没有 code-only 列，任何正效应都无法排除 agent 本来就能从代码推出来（D1 §1.1 S3）；doc-dependent mean Δdoc=+0.071 p<0.003；Where 类唯一显著（定位/导航价值）。
- 用法：CBE 文档作 documented 臂，必须同时跑 code-only 臂。

**次选**
- LongCodeArena module summarization（CompScore，交换顺序问两次消位置偏置）：https://huggingface.co/datasets/JetBrains-Research/lca-module-summarization
- CodeRAG-Bench（把生成文档当 datastore 测检索召回+下游）：https://code-rag-bench.github.io

### 禁用
- SWE-bench Verified：污染 + 59.4% 缺陷测试（OpenAI 2026-02 停用）；用 SWE-bench Live / SWE-rebench 若需 SWE 类。
- 常驻注入形态：ETH（n=138）+ Khatri（n=288）独立零/负效应（D1 R1/R2）。
- BLEU/ROUGE：与人评相关性差，误判率最高 70%（D1 §3.1）。
- LLM-as-judge 直接给文档打分：效度中等且有 confirmation bias（D1 §3.2/§3.3）。

### 评测纪律
- 消费形态必须检索式，不常驻注入。
- review 必须信息不对称：reviewer 只拿原子断言+源码，不看叙述包装（D1 §3.3 MARCH）。
- 样本量：<120 任务只报效应量区间，不下有效/无效结论（Khatri 功效分析）。
- 验证用 task-based + gold test，不用 LLM-as-judge 给文档打分（SWD-Bench 方法论）。
- 绝不把生成文档做成常驻注入（D1 警告）。

### CBE 本轮可跑的最小评测方案 proposal（只定方案不跑全量）
1. 修 r003 四臂导航评测第 56 行污染（四份评委 prompt 被污染成同一句，r003 自述修复成本低），重跑四道禁全文检索导航题 + base 对照臂 + 合规评委。
2. 扩展竞品对标判据面：r003 round4 仅量入口页（2/40 vs DeepWiki 38/40 vs zread 39/40），扩到导航任务与覆盖，做成可写进 README 的公开 benchmark（一条命令可复算）。
3. 补内部诊断点名的三轴：成体系介绍（配第二判定者+负对照，目前唯一读数是编排者单人首读）、有效覆盖、成本 token 效率。
4. 诚实边界：语义仅 Python、celery 级大仓未打通、独立 review 隔离贡献尚无隔离测量（D1 §3.3 缺口，本轮评测方案须含一臂做信息不对称 vs 对称的对比）。

## 5. 我们的亮点与诚实边界

**亮点**
- 函数级全符号覆盖（flask 415/415、httpx 521/521 真解释，r002 首达 r006 独立门重做放行）。
- 依赖感知 Feature Cone（SCC+DAG，确定性产出）。
- 信息不对称独立盲评链路（r007 blind-v3 完整 320-candidate 流程，虽有 fail_closed 但流程真实）。
- 一条命令可复算竞品对标（r003 round4 入口页读数）。
- 本轮 C5 多层递归原型 + celery 台账分批 materialize（after>33）。

**诚实边界**
- 语义解释仅 Python（r007 TS/JS 仅 syntax_only shadow，未通）。
- celery 级大仓未打通（33/3258，C5 只做分批增量）。
- 独立 review 的隔离贡献尚无隔离测量证据（D1 §3.3 文献空白 + CBE 自身未测）。
- 本调研的 zread 仓/license、RepoAgent/DocAgent/OpenWiki 的 license 部分未逐项实查（标待核验）；DeepWiki/RepoAgent/DocAgent 的下游效用数字全部来自 D1 转引，未独立复核。

## 6. 残差
- zread CLI 本体 license 与实现细节待后续核验（zread-skill 仓公开，URL 已补）。
- 2026 新品（OpenWiki/CodeScaleBench/KGCompass）的 license 与实测未逐项核验（D1 转引）。
- 本调研未跑任何 benchmark 全量（本轮只定方案，RULINGS E-4 + packet C3 要求）。