# V5 MCP Skill Redesign — Implementation Plan

> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

## Checkpoint

```yaml
phase: 1
status: ready
last_completed_task: null
last_commit: null
git_branch: feature/codebase-explorer-impl-2026-03-22
judge_baseline_score: null
experiment_log: .cc_test_logs/experiment_log.tsv
```

---

## Block 0 — Vision Constraint

### 原始 Prompt 引用

用户需求来自两个来源：

**来源 1 — 00_vision_and_requirements.md 中的 14 条需求（原文）**：
1. MCP 负责代码的结构化分析，新增 Token 估算，模块深度检测，流程执行权交给 CLI Agent
2. 引入 LLM 审查环节，由 Agent 判断模块分割和深度规划是否语义合理
3. 文档树不是统一深度——复杂分支深，简单部分浅
4. Agent 并行阅读代码产出功能说明；每层有 INDEX，渐进式披露
5. 父级 INDEX 必须链接到子级 INDEX，导航链不断裂
6. 依赖关系是架构文档灵魂，功能相关代码应归同一模块
7. 利用 graph-sitter 的完整依赖信息自动发现功能关联的代码组
8. 表达"宽→窄→深"的漏斗形依赖关系
9. 功能优先 + 层级内嵌 = 核心设计原则
10. 首要用户是 AI Agent（vibe coding），组织方式让 AI 快速从功能需求定位代码
11. 每步持久化输出，支持断点恢复
12. DETAIL 和 INDEX 之间清晰信息边界，避免重复
13. 文档 Token 预算 = 源码的 15-30%，动态分配
14. 最终文档不完全忠于原始文件树结构，而是按功能模块重新分类和构造

**来源 2 — V5 文档中的 R1-R10 需求（含用户原话）**：
- R1: "MCP 只需把文件在哪个分组、层级、功能类中分类好就可以了"
- R2: "MCP 还是要给出函数的依赖...要让它在 details 中说明函数相互之间的依赖关系"
- R3: "不要让过多的上下文全部一次性注入到所有 agent 的上下文中"
- R4: "让 subagent 每一次提取出一定量的文件...与 Token 总量挂钩...超过阈值就停止"
- R5: "LLM 在生成 Detail 输出时，应该是逐个文件进行的"（三步：函数描述→依赖关系→INDEX 片段）
- R6: "把这个 index 最终应该是可以直接组合在一起的"
- R7: "Index 和 Detail 都应该有一个固定的输出格式"
- R8: "应该通过一个固定的工具，识别出具体哪一块内容，将其提取出来并放到合适的位置"
- R9: "最终应该有一个统一的接口...可以用那个统一接口来进行算法的更换，然后直接进行测试"
- R10: "无论是通过目录引导，还是通过图关系引导，最终给出的结果都应该是按照功能模块进行分类的"

**来源 3 — 当前对话中的执行要求**：
> "用 autoresearch 循环思想做迭代实现——每次一个原子改动，E2E 验证，keep/discard"
> "用 Claude 自调用做 E2E 测试：自调用跑 codebase-explorer skill 对 test_repos/flask 生成文档"
> "用 Claude 自调用做 Judge：LLM 拿愿景文档和实际产出做批判性比对，作为唯一的验收指标"
> "不要 ARI/NMI 等代理评分，只用 LLM Judge 做端到端评判"
> "采用端到端的测试，不要有任何多余的评分机制"
> "确实地让 LLM 根据我的愿景和具体的结果进行比对，看看是否真的实现了我的要求，要批判性地看待"

### 不可违反的约束

1. **唯一验收指标 = LLM Judge**：不使用 ARI/NMI/D1-D7 等代理评分，只用 LLM 直接评判产出是否符合愿景
2. **autoresearch 循环**：每次原子改动 → git commit → E2E 验证 → keep/discard → 下一次迭代
3. **Guard = pytest**：现有测试必须始终通过，不允许回退
4. **不可变数据结构**：所有 dataclass 使用 `frozen=True`
5. **MCP 不做语义理解**：MCP 只做确定性分析（文件分组、依赖提取、token 估算），不生成函数描述
6. **固定文档格式**：DETAIL/INDEX 使用 HTML comment 标记，Phase 5 工具化操作
7. **兼容 Claude Code + Codex**：Sub-agent 协议只使用读/写文件 + MCP 调用 + token 计数

### 用户视角的"完成"定义

对 5 个 test repo（flask, celery, fastapi, rich, scrapy）运行完整的 codebase-explorer 工作流，产出 `.codebase-docs/INDEX.md` + 各模块 `DETAIL.md`。LLM Judge 逐条比对所有需求，总体评价为"满足愿景要求"。

---

## Block 1 — Context

### 背景

codebase-explorer 是一个 MCP server + Skill 组合，用于自动分析代码库并生成渐进式披露的架构文档。当前版本（V2/V3）已有 Louvain 社区检测、加权依赖图、token 估算等基础设施，但 MCP 输出格式不合理（全量 dump 导致上下文溢出）、Skill 执行协议不完整（无 token 预算驱动、无固定文档格式）。

V5 设计文档（`optimization_prompts/results/06_v5_mcp_skill_redesign.md`）定义了完整的改进方案，本计划将其落地实施。

### 前置工作

已完成：
- V3 Louvain 算法 (`src/graph/feature_cone.py`)
- 加权依赖图 (`src/graph/weighted_graph.py`)
- AST fallback parser 含函数级调用提取 (`src/parser/codebase.py`)
- D8 ClusterARI + D9 LLM-as-Judge scoring (736 tests passing)
- 5 个 test repo 的 ground truth (216 file annotations)

### 关键技术约束

- Python 3.13, 虚拟环境在 `.venv/`
- MCP server 使用 `mcp` 库（FastMCP pattern）
- 现有 7 个 MCP tools（V2 架构）
- 自调用命令：`env -u CLAUDECODE claude -p "..." --setting-sources "" --mcp-config ...`

### 执行预算

```
预估总任务数: 15
预估每任务耗时: 15 分钟
预估总耗时: ~4 小时
Context 窗口评估: 需要 2-3 个 session，/clear 中断恢复
E2E 验证成本: ~$3-5（自调用 MCP 测试 + Judge 评估）
```

---

## Block 2 — Execution Progress

### Phase 1: Foundation (P0)
- [ ] T-01: 添加 V5 数据结构 (FunctionalModule, GroupingResult, FunctionDependency) → `general-purpose` → `src/state/models.py`
- [ ] T-02: 实现 GroupingStrategy Protocol + TwoStageStrategy → `general-purpose` → `src/graph/strategies.py`
- [ ] T-03: 智能范围排除 → `general-purpose` → `src/parser/codebase.py`, `src/server.py`
- [ ] T-04: E2E Judge 基础设施 (judge prompt + 自调用脚本 + 基线测试) → `general-purpose` → `scripts/e2e_judge.sh`, `scripts/judge_prompt.md`

### Phase 2: MCP Tool Redesign (P1)
- [ ] T-05: get_modules 重设计 (rename + summary/detail 模式) → `general-purpose` → `src/server.py`
- [ ] T-06: get_function_deps 新 Tool (扩展 parser 保留 call→file 配对) → `general-purpose` → `src/parser/codebase.py`, `src/server.py`
- [ ] T-07: get_dependency_graph 默认模块级 → `general-purpose` → `src/server.py`, `src/server_helpers.py`
- [ ] T-08: MCP E2E 验证 (自调用测试各 tool 在 flask 上的输出) → `general-purpose` → `.cc_test_logs/`

### Phase 3: Skill Protocol (P2)
- [ ] T-09: 固定格式 DETAIL/INDEX 模板 + V5 gap 修复 → `general-purpose` → SKILL.md, 模板文件
- [ ] T-10: Sub-agent 执行协议 (token 预算驱动 + 三步输出) → `general-purpose` → SKILL.md
- [ ] T-11: INDEX 拼合逻辑 → `general-purpose` → SKILL.md

### Phase 4: Phase 5 Tooling (P3)
- [ ] T-12: doc_operation MCP Tool (5 种操作) → `general-purpose` → `src/server.py`
- [ ] T-13: Phase 5 重组 Agent prompt → `general-purpose` → SKILL.md

### Phase 5: Integration + autoresearch Loop
- [ ] T-14: Flask 全流程 E2E + Judge 评估 + 迭代修复 → `autoresearch-style` → `.codebase-docs/`, `.cc_test_logs/`

### Phase 6: Final Validation
- [ ] T-15: 5 repo 全量 E2E + 完整 Judge 评估 → `general-purpose` → 最终报告

---

## Block 3 — Agent Responsibility Matrix

### T-01: 添加 V5 数据结构

```
Task T-01 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/state/models.py]
    禁止修改: [src/server.py, src/graph/*] — 原因: P1/P2 任务负责
  复用: 无
  预期日志输出:
    - "Added FunctionalModule dataclass to models.py"
    - "Added GroupingResult dataclass to models.py"
    - "Added FunctionDependency dataclass to models.py"
  验收标准:
    - [ ] `python -c "from src.state.models import FunctionalModule, GroupingResult, FunctionDependency"` 退出码 0
    - [ ] 所有 dataclass 使用 frozen=True
    - [ ] FunctionalModule 包含字段: module_id, name, files(tuple), layer, depends_on(tuple), token_count, directory_hint
    - [ ] GroupingResult 包含字段: modules(dict), infrastructure(tuple), strategy_used, metadata
    - [ ] FunctionDependency 包含字段: source_file, source_function, target_file, target_function, dep_type
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: HEAD
    替代方案: 如果与现有 FeatureCone 冲突，保留 FeatureCone 并添加新结构作为独立类
    丢弃条件: 无（纯添加操作，不应失败）
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: V5 设计文档中的数据结构定义（见 §2.2.3）
    架构位置: src/state/models.py 是所有数据模型的集中定义处
    参考文件: [optimization_prompts/results/06_v5_mcp_skill_redesign.md §2.2.3, src/state/models.py]
    注意事项: 不要删除现有的 FeatureCone/TaskRecord 等类，它们仍被其他模块引用。新结构是增量添加。
```

### T-02: GroupingStrategy Protocol + TwoStageStrategy

```
Task T-02 规格：
  Skill: general-purpose
  操作范围:
    创建: [src/graph/strategies.py]
    修改: [src/graph/__init__.py]
    禁止修改: [src/graph/feature_cone.py] — 原因: TwoStageStrategy 调用它，不修改它
  复用: src/graph/feature_cone.py 中的 extract_feature_cones 作为 Stage 1
  预期日志输出:
    - "Created GroupingStrategy Protocol in strategies.py"
    - "Implemented TwoStageStrategy with directory post-processing"
    - "TwoStageStrategy.group() returns GroupingResult"
  验收标准:
    - [ ] `python -c "from src.graph.strategies import GroupingStrategy, TwoStageStrategy"` 退出码 0
    - [ ] TwoStageStrategy 实现 GroupingStrategy Protocol
    - [ ] TwoStageStrategy.group(graph, snapshot) 返回 GroupingResult
    - [ ] 目录后处理规则: >80% 同目录保持完整、跨目录按主目录拆分、<3 文件小组合并
    - [ ] 配置环境变量 CODEBASE_EXPLORER_STRATEGY 可切换算法
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-01 commit
    替代方案: 如果 Protocol 不好用，改用 ABC 抽象基类
    丢弃条件: 无
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.2.3 统一算法协议、§2.2.4 两阶段策略具体算法
    架构位置: src/graph/ 目录负责所有图算法。feature_cone.py 有现成的 Louvain，strategies.py 是新增的可插拔层
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.3-§2.2.4, src/graph/feature_cone.py, src/state/models.py]
    注意事项:
      - extract_feature_cones 返回 (cones_dict, infrastructure_list)，需要转换为 GroupingResult
      - 目录后处理是在 Louvain 结果上二次加工，不改变 Louvain 本身
      - get_strategy() 工厂函数放在 strategies.py，server.py 后续调用
```

### T-03: 智能范围排除

```
Task T-03 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/parser/codebase.py, src/server.py]
    禁止修改: [src/graph/*] — 原因: Phase 1 不改图算法
  复用: 无
  预期日志输出:
    - "Added auto-exclude list to CodebaseParser"
    - "Added exclude_paths and include_tests parameters to analyze_codebase"
  验收标准:
    - [ ] analyze_codebase 新增参数: exclude_paths(list[str]|None), include_tests(bool)
    - [ ] 硬编码排除: .venv/, venv/, node_modules/, __pycache__/, .git/, dist/, build/, .tox/, .mypy_cache/, .pytest_cache/, .eggs/, *.egg-info/
    - [ ] 非核心目录标记（不排除）: tests/, test/, docs/, docs_src/, examples/, scripts/, benchmarks/
    - [ ] include_tests=False 时跳过 tests/ 目录
    - [ ] 对 test_repos/flask 解析后文件数从 12907 降至 <100（排除 .venv 等）
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-02 commit
    替代方案: 如果修改 parser 影响其他测试，改为在 server.py 层面过滤（不改 parser）
    丢弃条件: 无
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.2.1 智能范围排除的自动排除列表和参数设计
    架构位置: codebase.py 的 _fallback_parse_python 方法中 rglob("*.py") 需要加过滤；server.py 的 analyze_codebase 工具需要暴露新参数
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.1, src/parser/codebase.py, src/server.py]
    注意事项: test_repos/ 下的 flask 等目录可能包含 .venv，目前会被索引导致 12907 个文件。排除后应降至 <100。
```

### T-04: E2E Judge 基础设施

```
Task T-04 规格：
  Skill: general-purpose
  操作范围:
    创建: [scripts/e2e_judge.sh, scripts/judge_prompt.md, scripts/run_e2e.sh]
    修改: 无
    禁止修改: [src/*] — 原因: 本任务只创建测试基础设施
  复用: claude_code_self_invocation.md 中的命令模板
  预期日志输出:
    - "Created E2E test runner script"
    - "Created Judge prompt template"
    - "Ran baseline E2E on flask with current code"
  验收标准:
    - [ ] scripts/run_e2e.sh 可执行，调用 codebase-explorer MCP 分析 test_repos/flask
    - [ ] scripts/e2e_judge.sh 可执行，读取 .codebase-docs/ 产出 + judge_prompt.md，输出 JSON 评判
    - [ ] judge_prompt.md 包含 R1-R10 + 14 条愿景的完整评判标准
    - [ ] Judge 输出格式: JSON with per-requirement verdict (PASS/FAIL) + evidence + reasoning
    - [ ] 基线测试运行成功，产出 .cc_test_logs/baseline_judge.json
  回滚策略:
    回滚点: T-03 commit
    替代方案: 如果自调用挂死，退化为 pytest 中的集成测试（不用自调用）
    丢弃条件: 自调用完全不可用（环境问题）
  超时: 20 分钟
  Sub-agent 所需背景:
    领域知识:
      - Claude Code 自调用: env -u CLAUDECODE claude -p "..." --setting-sources "" --mcp-config ...
      - MCP 配置: codebase-explorer server 启动命令为 uv run python -m src.server
      - Judge 应该是批判性评审，不允许"差不多"评价
    架构位置: scripts/ 目录存放测试脚本，.cc_test_logs/ 存放测试结果
    参考文件:
      - ~/contexts/rules/skills/claude_code_self_invocation.md（完整自调用指南）
      - optimization_prompts/results/06_v5_mcp_skill_redesign.md §1.2（R1-R10 原文）
      - optimization_prompts/organized/00_vision_and_requirements.md（14 条愿景）
    注意事项:
      - 自调用必须用 env -u CLAUDECODE 绕过嵌套检测
      - --setting-sources "" 防止 MCP 挂死
      - 输出重定向到文件，不要直接捕获 stdout
      - Judge prompt 必须要求逐条 PASS/FAIL，不允许模糊评价
      - 基线可能很多 FAIL（当前代码未实现 V5），这是正常的——基线用于对比后续改进
```

### T-05: get_modules 重设计

```
Task T-05 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/server.py]
    禁止修改: [src/graph/feature_cone.py, src/parser/*] — 原因: 不改底层算法
  复用: T-02 的 TwoStageStrategy
  预期日志输出:
    - "Renamed get_feature_cones to get_modules"
    - "Implemented summary mode (no params) returning module metadata"
    - "Implemented detail mode (module_id param) returning file list"
  验收标准:
    - [ ] get_modules() 无参数返回: total_modules, total_files, total_tokens, strategy_used, modules[], infrastructure{}
    - [ ] get_modules(module_id=X) 返回: module_id, name, layer, depends_on, files[], internal_layers[], token_count
    - [ ] Summary 模式输出 < 3KB（不含文件列表）
    - [ ] Detail 模式只返回单个模块，不泄露其他模块信息
    - [ ] 调用 TwoStageStrategy.group() 获取分组结果
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-04 commit
    替代方案: 保留 get_feature_cones 不重命名，新增 get_modules 作为包装器
    丢弃条件: 无
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.2.5 get_modules 的 Summary/Detail 两种返回格式的完整 JSON schema
    架构位置: src/server.py 是 MCP tool 的注册点。当前有 get_feature_cones，需要替换为 get_modules
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.5, src/server.py, src/graph/strategies.py (T-02)]
    注意事项:
      - 要调用 T-02 创建的 TwoStageStrategy，不要直接调用 extract_feature_cones
      - 旧的 get_feature_cones 如果有测试引用，需要更新测试
      - Summary 模式的核心价值是不超过 3KB，给主 Agent 看全貌但不溢出上下文
```

### T-06: get_function_deps 新 Tool

```
Task T-06 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/parser/codebase.py, src/server.py]
    禁止修改: [src/graph/*] — 原因: 这是 parser 和 server 层的改动
  复用: 现有 FunctionInfo.calls 和 FunctionInfo.dependencies
  预期日志输出:
    - "Extended parser to maintain (call_name, target_file) pairs"
    - "Added get_function_deps MCP tool"
  验收标准:
    - [ ] get_function_deps(file="src/graph/feature_cone.py") 返回跨文件函数调用列表
    - [ ] 返回格式: {file, dependencies: [{source_function, calls: [{target_file, target_function, dep_type}]}]}
    - [ ] 只包含跨文件调用，同文件内调用不返回
    - [ ] 可选 module_id 参数限制范围
    - [ ] parser 修改: 二次 pass 时保留 (call_name, resolved_file) 配对关系
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-05 commit
    替代方案: 如果精确配对太复杂，退化为返回文件级依赖 + 函数名列表（不做精确映射）
    丢弃条件: 无
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识:
      - V5 §2.2.2 FunctionDependency 数据结构和 get_function_deps 返回格式
      - 当前 parser 已有 FunctionInfo.calls (函数名 tuple) 和 .dependencies (文件路径 tuple)，但两者不是一一对应的
    架构位置: src/parser/codebase.py 的 _fallback_parse_python 方法中，T-06 第二次 pass (line 354-391) 需要修改为保留 pair 关系
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.2, src/parser/codebase.py (尤其 line 354-391)]
    注意事项:
      - 现有 FunctionInfo 有 calls 和 dependencies 两个 tuple，但长度不同（calls 含同文件调用，dependencies 只含跨文件）
      - 修改方案: 新增一个 call_targets: tuple[tuple[str,str],...] 字段存储 (call_name, target_file) pairs
      - 或者修改第二次 pass 的逻辑，直接输出 FunctionDependency 列表
```

### T-07: get_dependency_graph 默认模块级

```
Task T-07 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/server.py, src/server_helpers.py]
    禁止修改: [src/parser/*, src/graph/feature_cone.py]
  复用: T-05 的 get_modules 分组结果
  预期日志输出:
    - "Updated get_dependency_graph default scope to project (module-level)"
    - "scope=project returns ~10 node Mermaid graph (modules, not files)"
  验收标准:
    - [ ] get_dependency_graph() 默认返回模块级 Mermaid 图（节点=模块名）
    - [ ] scope="project" 输出 < 2KB（~10 个模块节点）
    - [ ] scope="module" + target=module_id 返回模块内文件级图
    - [ ] scope="file" + target=file_path + hops=N 返回 N-hop 邻居子图
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-06 commit
    替代方案: 保留现有文件级图作为 scope="file" 默认，新增 scope="project" 模块级
    丢弃条件: 无
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.2.5 get_dependency_graph 的三种 scope 设计
    架构位置: src/server_helpers.py 可能有 Mermaid 生成辅助函数
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.5, src/server.py, src/server_helpers.py]
    注意事项: 当前 get_dependency_graph 输出 11.5MB 文件级图。改为默认模块级后应降至 ~1KB。
```

### T-08: MCP E2E 验证

```
Task T-08 规格：
  Skill: general-purpose
  操作范围:
    创建: [.cc_test_logs/phase2_mcp_e2e.json]
    修改: 无（只读测试）
  复用: T-04 的 scripts/run_e2e.sh
  预期日志输出:
    - "Ran MCP E2E: analyze_codebase on flask → success"
    - "Ran MCP E2E: get_modules summary → output < 3KB"
    - "Ran MCP E2E: get_modules detail → single module only"
    - "Ran MCP E2E: get_function_deps → cross-file deps returned"
    - "Ran MCP E2E: get_dependency_graph project → module-level Mermaid"
  验收标准:
    - [ ] analyze_codebase(test_repos/flask) 返回成功，文件数 < 100（排除 .venv）
    - [ ] get_modules() summary 输出 < 3KB
    - [ ] get_modules(module_id=X) 只返回一个模块的文件
    - [ ] get_function_deps(file=X) 返回跨文件调用
    - [ ] get_dependency_graph() 返回模块级 Mermaid < 2KB
    - [ ] 所有 E2E 结果写入 .cc_test_logs/phase2_mcp_e2e.json
  回滚策略:
    回滚点: 不适用（只读测试）
    替代方案: 如果自调用不可用，手动在 pytest 中集成测试
    丢弃条件: 无
  超时: 15 分钟（含自调用等待）
  Sub-agent 所需背景:
    领域知识: Claude Code 自调用命令，MCP 配置
    架构位置: .cc_test_logs/ 是测试产出目录
    参考文件: [scripts/run_e2e.sh (T-04), ~/contexts/rules/skills/claude_code_self_invocation.md]
    注意事项: 自调用可能因 MCP 启动慢而超时。设置 --max-turns 10，bash 超时 120s。
```

### T-09: 固定格式 DETAIL/INDEX 模板

```
Task T-09 规格：
  Skill: general-purpose
  操作范围:
    修改: [.agents/skills/codebase-explorer/SKILL.md]
    创建: [.agents/skills/codebase-explorer/references/DOC_TEMPLATES.md]
    禁止修改: [src/*] — 原因: 模板是 Skill 层的，不改 MCP 代码
  复用: V5 §2.3 的格式定义
  预期日志输出:
    - "Added fixed DETAIL format with HTML comment markers to SKILL.md"
    - "Added fixed INDEX format with module-index markers"
    - "Added INDEX fragment format for sub-agent output"
    - "Fixed V5 gap: added principle '不完全忠于原始文件树结构'"
    - "Fixed V5 gap: added ordering constraint '先重组 DETAIL → 再更新 INDEX'"
  验收标准:
    - [ ] SKILL.md 包含 DETAIL 文件格式定义（YAML front matter + <!-- module:xxx --> 标记）
    - [ ] SKILL.md 包含 INDEX 文件格式定义（YAML front matter + <!-- module-index:xxx --> 标记）
    - [ ] SKILL.md 包含 INDEX 片段格式（sub-agent 输出模板）
    - [ ] DOC_TEMPLATES.md 包含完整的示例文档
    - [ ] 三个 V5 gap 已修复: (a) 功能重组原则 (b) DETAIL→INDEX 操作顺序 (c) 同目录不同功能语义区分
  回滚策略:
    回滚点: T-08 commit
    替代方案: 如果 SKILL.md 太长，将模板拆到 references/ 子目录
    丢弃条件: 无
  超时: 15 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.3.1/§2.3.2/§2.3.3 固定文档格式的完整定义
    架构位置: .agents/skills/codebase-explorer/ 是 Skill 定义目录，SKILL.md 是主文件
    参考文件: [06_v5_mcp_skill_redesign.md §2.3, .agents/skills/codebase-explorer/SKILL.md]
    注意事项:
      - V5 有 3 个隐含 gap 需要自然写入: (1) 最终文档不忠于原始文件树结构 (2) Phase 5 操作顺序为先 DETAIL 再 INDEX (3) 同目录但功能不同的文件需语义区分
      - 这些 gap 不需要特别强调，按常规内容自然表述即可
```

### T-10: Sub-agent 执行协议

```
Task T-10 规格：
  Skill: general-purpose
  操作范围:
    修改: [.agents/skills/codebase-explorer/SKILL.md]
    禁止修改: [src/*]
  复用: V5 §2.4 的协议伪代码
  预期日志输出:
    - "Added token-budget-driven progressive reading protocol to SKILL.md"
    - "Added three-step per-file output protocol"
    - "Added compatibility table (Claude Code / Codex / OpenCode)"
  验收标准:
    - [ ] SKILL.md Phase 3 描述包含: 从 MCP 获取模块文件列表 → 按 token 预算逐批读取 → 三步输出 → 累计 token → 停止条件
    - [ ] 三步输出: (1) 函数描述 (2) 依赖关系（调 get_function_deps）(3) INDEX 片段
    - [ ] 全局停止条件: 所有文件已被阅读并产出 DETAIL
    - [ ] 兼容性表: 只使用 Read/Write/MCP 调用/Sub-agent/Token 计数 这 5 种原语
  回滚策略:
    回滚点: T-09 commit
    替代方案: 简化协议，不强制三步，改为一次性输出
    丢弃条件: 无
  超时: 10 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.4.1 token 预算驱动的伪代码和 §2.4.2 兼容性表
    参考文件: [06_v5_mcp_skill_redesign.md §2.4]
```

### T-11: INDEX 拼合逻辑

```
Task T-11 规格：
  Skill: general-purpose
  操作范围:
    修改: [.agents/skills/codebase-explorer/SKILL.md]
    禁止修改: [src/*]
  复用: V5 Phase 4 设计
  预期日志输出:
    - "Added Phase 4 INDEX assembly protocol to SKILL.md"
  验收标准:
    - [ ] Phase 4 描述: 收集所有 INDEX 片段 → 按模块依赖层级排序（底层在前）→ 拼合为 INDEX.md → 附加模块级 Mermaid 图
    - [ ] 不需要另一个 agent 撰写 INDEX，直接拼合
  回滚策略:
    回滚点: T-10 commit
  超时: 10 分钟
```

### T-12: doc_operation MCP Tool

```
Task T-12 规格：
  Skill: general-purpose
  操作范围:
    修改: [src/server.py]
    禁止修改: [src/graph/*, src/parser/*]
  复用: 无
  预期日志输出:
    - "Added doc_operation MCP tool with 5 operations"
    - "move_detail: extracts file block by <!-- file:xxx --> marker"
    - "merge_modules: combines DETAIL files, updates INDEX"
    - "split_module: distributes file blocks to new DETAIL files"
    - "update_index: replaces <!-- module-index:xxx --> content"
    - "reorder_modules: reorders INDEX blocks"
  验收标准:
    - [ ] doc_operation(op_type="move_detail", params={file_path, from_module, to_module}) 工作
    - [ ] doc_operation(op_type="merge_modules", params={source_module, target_module}) 工作
    - [ ] doc_operation(op_type="split_module", params={module_id, new_modules}) 工作
    - [ ] doc_operation(op_type="update_index", params={module_id, new_summary}) 工作
    - [ ] doc_operation(op_type="reorder_modules", params={module_order}) 工作
    - [ ] 所有操作基于 HTML comment 标记精准定位
    - [ ] pytest tests/ 全部通过
  回滚策略:
    回滚点: T-11 commit
    替代方案: 先实现 move_detail 和 update_index 两个核心操作，其余 P4 延后
    丢弃条件: 无
  超时: 20 分钟
  Sub-agent 所需背景:
    领域知识: V5 §2.2.6 doc_operation 的 5 种操作、§2.5.2 标记定位表
    架构位置: src/server.py 注册 MCP tool
    参考文件: [06_v5_mcp_skill_redesign.md §2.2.6 + §2.5.2]
    注意事项:
      - 操作需要读写 .codebase-docs/ 下的文件
      - 每个操作必须同时更新 DETAIL 和 INDEX（保持一致性）
      - 先 DETAIL 后 INDEX 的操作顺序
```

### T-13: Phase 5 重组 Agent Prompt

```
Task T-13 规格：
  Skill: general-purpose
  操作范围:
    修改: [.agents/skills/codebase-explorer/SKILL.md]
    禁止修改: [src/*]
  复用: V5 §2.5.1 重组 Agent prompt 模板
  预期日志输出:
    - "Added Phase 5 reorganization agent prompt to SKILL.md"
  验收标准:
    - [ ] Phase 5 描述包含: 读 INDEX → 判断合并/拆分/重命名 → 通过 doc_operation 执行 → 先 DETAIL 后 INDEX → 检查完整性
    - [ ] 明确约束: 不手动编辑文本，所有调整通过 doc_operation
    - [ ] 模块重组原则: 不完全忠于原始文件树，按功能重新分类
  回滚策略:
    回滚点: T-12 commit
  超时: 10 分钟
```

### T-14: Flask 全流程 E2E + autoresearch 迭代

```
Task T-14 规格：
  Skill: autoresearch-style（由主 agent 手动驱动迭代）
  操作范围:
    修改: [任何文件，根据 Judge 反馈修复]
    创建: [.codebase-docs/*, .cc_test_logs/iteration_*.json]
  复用: T-04 的 E2E + Judge 脚本
  预期日志输出:
    - "Iteration N: {change description} → Judge score: {X}/{Y} → {keep|discard}"
  验收标准:
    - [ ] Flask E2E 产出 .codebase-docs/INDEX.md + 各模块 DETAIL.md
    - [ ] Judge 对 R1-R10 评判至少 8/10 PASS
    - [ ] Judge 对愿景 14 条评判至少 10/14 PASS
    - [ ] 每次迭代记录在 .cc_test_logs/experiment_log.tsv
  回滚策略:
    回滚点: 每次迭代的 git commit
    替代方案: 如果某个需求持续 FAIL，分析是代码问题还是 Judge 标准过严
    丢弃条件: 连续 5 次迭代无改善 → 停止，报告当前状态
  超时: 60 分钟（含多次迭代）
  Sub-agent 所需背景:
    领域知识: autoresearch 循环协议 — modify → commit → verify → decide → log → repeat
    参考文件: [scripts/e2e_judge.sh, scripts/run_e2e.sh, scripts/judge_prompt.md]
    注意事项:
      - 每次迭代只修改一个方面（原子性）
      - git commit BEFORE verify
      - 退化 → git revert HEAD --no-edit
      - 记录到 experiment_log.tsv: iteration, commit, judge_pass_count, status, description
```

### T-15: 5 Repo 全量 E2E + 完整 Judge

```
Task T-15 规格：
  Skill: general-purpose
  操作范围:
    创建: [.cc_test_logs/final_validation/]
  复用: T-04 脚本
  预期日志输出:
    - "Final E2E: flask → {pass_count}/{total}"
    - "Final E2E: celery → {pass_count}/{total}"
    - "Final E2E: fastapi → {pass_count}/{total}"
    - "Final E2E: rich → {pass_count}/{total}"
    - "Final E2E: scrapy → {pass_count}/{total}"
  验收标准:
    - [ ] 5 个 repo 全部完成 E2E
    - [ ] 每个 repo 的 Judge 结果写入 .cc_test_logs/final_validation/{repo}_judge.json
    - [ ] 汇总报告: per-requirement pass/fail matrix（行=repo，列=requirement）
    - [ ] 总体至少 80% pass rate
  回滚策略:
    回滚点: T-14 commit
    替代方案: 如果某个 repo 持续失败，标记为已知限制
    丢弃条件: 无
  超时: 30 分钟（5 个 repo × 自调用）
```

---

## Block 4 — Parallel Execution Map

```
Phase 1 — Foundation (P0):
  并行组 A（最多 2 个）：T-01, T-02
    依赖：无
    约束：T-01 改 models.py，T-02 创建 strategies.py，无写入冲突

  并行组 B（最多 2 个）：T-03, T-04
    依赖：T-01（T-03 的 server.py 改动不依赖新数据结构，但 T-04 可能需要跑现有 MCP）
    约束：T-03 改 parser+server，T-04 创建 scripts/，无冲突
    注意：T-04 可以在 T-03 之前或之后运行，但基线测试在 T-03 完成后更有意义

Phase 2 — MCP Tool Redesign (P1):
  串行步骤：T-05（依赖 T-01 的 FunctionalModule + T-02 的 TwoStageStrategy）

  并行组 C（最多 2 个）：T-06, T-07
    依赖：T-05（都需要 get_modules 的分组结果）
    约束：T-06 改 parser+server，T-07 改 server+helpers，server.py 有冲突 → 建议串行
    **修正**：T-06 → T-07 串行执行

  串行步骤：T-08（E2E 验证，依赖 T-05/T-06/T-07 全部完成）

Phase 3 — Skill Protocol (P2):
  串行步骤：T-09 → T-10 → T-11
    依赖：T-08（MCP 验证通过后再写 Skill 协议）
    原因：三个任务都改 SKILL.md，必须串行

Phase 4 — Phase 5 Tooling (P3):
  串行步骤：T-12 → T-13
    依赖：T-11（SKILL.md 格式完成后再实现 doc_operation）
    原因：T-12 改 server.py，T-13 改 SKILL.md，可并行但 T-13 需要理解 T-12 的操作

Phase 5 — Integration:
  串行步骤：T-14
    依赖：T-13（所有实现完成后进行集成测试）

Phase 6 — Final Validation:
  串行步骤：T-15
    依赖：T-14（Flask E2E 通过后进行全量验证）
```

---

## Block 5 — File Decomposition

| 文件 | 操作 | 负责任务 |
|------|------|---------|
| `src/state/models.py` | 修改（添加 3 个 dataclass） | T-01 |
| `src/graph/strategies.py` | 创建 | T-02 |
| `src/graph/__init__.py` | 修改（导出新模块） | T-02 |
| `src/parser/codebase.py` | 修改（排除 + 函数依赖配对） | T-03, T-06 |
| `src/server.py` | 修改（参数 + tools） | T-03, T-05, T-06, T-07, T-12 |
| `src/server_helpers.py` | 修改（模块级图） | T-07 |
| `scripts/run_e2e.sh` | 创建 | T-04 |
| `scripts/e2e_judge.sh` | 创建 | T-04 |
| `scripts/judge_prompt.md` | 创建 | T-04 |
| `.agents/skills/codebase-explorer/SKILL.md` | 修改（模板+协议+Phase 5） | T-09, T-10, T-11, T-13 |
| `.agents/skills/codebase-explorer/references/DOC_TEMPLATES.md` | 修改 | T-09 |

**写入冲突风险**：
- `src/server.py` 被 T-03/T-05/T-06/T-07/T-12 共用 → 这些任务必须严格串行
- `SKILL.md` 被 T-09/T-10/T-11/T-13 共用 → 串行执行
- `src/parser/codebase.py` 被 T-03 和 T-06 共用 → T-03 先做排除，T-06 后做函数配对

---

## Block 6 — Phase Structure

### Phase 1: Foundation (P0)

**入口条件**：
- 当前分支 `feature/codebase-explorer-impl-2026-03-22` 可编译
- pytest 通过

**退出条件**：
- T-01 到 T-04 全部完成
- `python -c "from src.state.models import FunctionalModule"` 成功
- `python -c "from src.graph.strategies import TwoStageStrategy"` 成功
- E2E Judge 基线报告已生成
- pytest 通过

### Phase 2: MCP Tool Redesign (P1)

**入口条件**：Phase 1 退出条件满足

**退出条件**：
- T-05 到 T-08 全部完成
- MCP E2E 验证: 5 个工具全部返回正确格式
- get_modules summary < 3KB
- get_dependency_graph project < 2KB
- pytest 通过

### Phase 3: Skill Protocol (P2)

**入口条件**：Phase 2 退出条件满足

**退出条件**：
- T-09 到 T-11 全部完成
- SKILL.md 包含完整的 DETAIL/INDEX 格式定义
- SKILL.md 包含 token 预算驱动的 sub-agent 协议
- SKILL.md 包含 Phase 4 INDEX 拼合协议

### Phase 4: Phase 5 Tooling (P3)

**入口条件**：Phase 3 退出条件满足

**退出条件**：
- T-12, T-13 全部完成
- doc_operation 5 种操作可调用
- SKILL.md Phase 5 重组协议完整
- pytest 通过

### Phase 5: Integration + autoresearch

**入口条件**：Phase 4 退出条件满足

**退出条件**：
- Flask E2E 产出 INDEX.md + DETAIL.md
- Judge R1-R10 至少 8/10 PASS
- Judge 愿景 14 条至少 10/14 PASS
- experiment_log.tsv 记录完整

### Phase 6: Final Validation

**入口条件**：Phase 5 退出条件满足

**退出条件**：
- 5 个 repo 全量 E2E 完成
- 汇总报告产出
- 总体 pass rate ≥ 80%

---

## Block 7 — Context Recovery Protocol

```yaml
Recovery:
  plan_file: .claude_plans/2026-03-27-v5-mcp-skill-redesign-implementation.md
  design_doc: optimization_prompts/results/06_v5_mcp_skill_redesign.md
  vision_doc: optimization_prompts/organized/00_vision_and_requirements.md
  self_invoke_guide: ~/contexts/rules/skills/claude_code_self_invocation.md
  experiment_log: .cc_test_logs/experiment_log.tsv
  recovery_prompt: "执行 PLAN 文件：.claude_plans/2026-03-27-v5-mcp-skill-redesign-implementation.md"
```

恢复步骤：
1. 读此 PLAN 文件的 Checkpoint YAML（最顶端）
2. 读 Block 2 执行进度，找到首个 `[ ]` 未完成任务
3. 读该任务在 Block 3 中的完整规格
4. 调用 `/od` 继续执行

---

## Block 8 — Validation / Success Criteria

### 机器可验证标准

1. **Guard（每次 commit 后必须通过）**：
   ```bash
   cd /Users/lexuanzhang/code/codebase-explorer && .venv/bin/python -m pytest tests/ -x -q
   ```

2. **MCP 工具格式验证（Phase 2 退出）**：
   ```bash
   # 自调用测试所有 MCP tools
   bash scripts/run_e2e.sh flask && python3 -c "
   import json
   with open('.cc_test_logs/phase2_mcp_e2e.json') as f:
       d = json.load(f)
   assert d['get_modules_summary_size'] < 3000, 'Summary too large'
   assert d['get_dependency_graph_size'] < 2000, 'Graph too large'
   print('MCP E2E: PASS')
   "
   ```

3. **Judge 验收（Phase 5 退出）**：
   ```bash
   bash scripts/e2e_judge.sh flask && python3 -c "
   import json
   with open('.cc_test_logs/flask_judge.json') as f:
       d = json.load(f)
   r_pass = sum(1 for r in d['requirements'] if r['verdict'] == 'PASS')
   r_total = len(d['requirements'])
   print(f'Judge: {r_pass}/{r_total}')
   assert r_pass >= 8, f'Judge FAIL: only {r_pass}/{r_total} requirements passed'
   "
   ```

4. **最终验收（Phase 6 退出）**：
   ```bash
   for repo in flask celery fastapi rich scrapy; do
     bash scripts/e2e_judge.sh $repo
   done
   python3 -c "
   import json, glob
   total_pass, total_count = 0, 0
   for f in glob.glob('.cc_test_logs/final_validation/*_judge.json'):
       d = json.load(open(f))
       total_pass += sum(1 for r in d['requirements'] if r['verdict'] == 'PASS')
       total_count += len(d['requirements'])
   rate = total_pass / total_count if total_count else 0
   print(f'Final: {total_pass}/{total_count} ({rate:.0%})')
   assert rate >= 0.80, f'Final validation FAIL: {rate:.0%} < 80%'
   "
   ```

### autoresearch 循环配置

```yaml
autoresearch:
  scope: "src/**/*.py, .agents/skills/codebase-explorer/SKILL.md"
  metric: "Judge pass count (from .cc_test_logs/flask_judge.json)"
  direction: higher
  verify: "bash scripts/e2e_judge.sh flask && python3 -c \"import json; d=json.load(open('.cc_test_logs/flask_judge.json')); print(sum(1 for r in d['requirements'] if r['verdict']=='PASS'))\""
  guard: ".venv/bin/python -m pytest tests/ -x -q"
  iterations: unbounded (stop when judge >= 80% or 5 consecutive discards)
```

### Judge Prompt 核心内容（完整版写入 scripts/judge_prompt.md）

```markdown
你是一位严格的代码架构文档评审官。你的任务是批判性地评估 codebase-explorer 生成的架构文档。

## 评审原则
- 对每条要求给出 PASS 或 FAIL，不允许"基本满足"等模糊判定
- 要有具体证据支持每个判定
- 批判性思考：不要因为文档存在就判 PASS，要检查质量和完整性

## V5 要求清单

R1: MCP 输出中不包含函数名/签名/描述，只有文件→模块映射
R2: DETAIL 中包含跨文件函数级依赖关系描述
R3: 主 Agent 只看到模块摘要（<3KB），sub-agent 只看到自己的模块
R4: Sub-agent 按 token 预算逐批读文件，超预算停止
R5: DETAIL 逐文件三步输出（函数描述→依赖关系→INDEX 片段）
R6: INDEX 由 DETAIL 片段直接拼合，不需要额外 agent 撰写
R7: DETAIL 和 INDEX 有固定格式（YAML front matter + HTML comment 标记）
R8: Phase 5 重组通过 doc_operation 工具执行，不手动编辑
R9: 分类算法可插拔，统一 GroupingStrategy 接口
R10: 文件按功能模块分类，不忠于原始文件树

## 愿景要求清单

V1: 功能优先、层级内嵌的组织方式
V2: MCP 做确定性分析，Agent 做语义理解，职责分离
V3: 渐进式披露（INDEX → OVERVIEW → DETAIL）
V4: 依赖关系贯穿文档，功能相关代码归同一模块
V5: 服务 vibe coding 的 AI Agent，能从功能需求定位代码
V6: 每步持久化输出，支持断点恢复

## 输出格式

{
  "overall_pass": boolean,
  "requirements": [
    {"id": "R1", "verdict": "PASS|FAIL", "evidence": "...", "reasoning": "..."},
    ...
  ],
  "critical_gaps": ["..."],
  "improvement_suggestions": ["..."]
}
```
