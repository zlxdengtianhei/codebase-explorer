> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（哪些 [x] 已完成，哪些 [ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

---

## Block 1 — Context（背景）

### 任务概述

本计划实现 codebase-explorer v2 优化，基于 `optimization_prompts/results/` 目录中的完整分析文档。核心目标是修正 V1 中三大架构违规：

1. **违规一**：MCP Server 承担了 Jinja2 文档生成（无 LLM 能力的模块不应撰写文档）
2. **违规二**：Agent 没有读取源码的工具，`submit_analysis()` 传入空数据
3. **违规三**：Phase 3（分析）和 Phase 4（生成）之间的数据管道断裂

V1 E2E 测试结果：文件覆盖率 0%、链接有效率 14.8%、Token 使用率仅 5-29%。

### 参考文档

| 文档 | 用途 |
|------|------|
| `optimization_prompts/results/03_final_progressive_scheme.md` | 最终权威规范（L2 实现指引 + P0/P1/P2 矩阵）|
| `optimization_prompts/results/02c_responsibility_v2.md` | 7 个工具 API 签名（Section 2）+ 文件去留决策（Section 7）|
| `optimization_prompts/results/01_current_architecture.md` | 当前架构详解（理解现有代码）|
| `optimization_prompts/results/02a_code_analysis_v2.md` | 算法设计（加权图 + Feature Cone + 装箱算法）|
| `optimization_prompts/results/02b_skill_design_v2.md` | Skill 工作流 + Agent Prompt 模板（5-Phase）|

### 核心变更概述

**删除**（8 个文件）：`src/doc/generator.py`、`src/doc/templates.py`、`src/doc/_context.py`、`src/doc/_tree_builder.py`（替换）、`src/state/database.py`、`src/state/checkpoint.py`、`src/state/_schema.py`、`src/budget/controller.py`、`src/templates/*.j2`（3 个）

**新建**（4 个文件）：`src/state/json_store.py`、`src/graph/feature_cone.py`、`src/graph/weighted_graph.py`、`src/analysis/__init__.py`（可选辅助）

**修改**（6 个文件）：`src/graph/dependency.py`、`src/graph/grouper.py`、`src/budget/estimator.py`、`src/state/models.py`、`src/doc/depth_planner.py`、`src/server.py`（重建）

**重写 Skill**：`.agents/skills/codebase-explorer/SKILL.md`（新 5-Phase 工作流 + 3 个 Agent Prompt 模板）

### 约束

- 不破坏现有测试（`tests/e2e_test.py` 中与新 API 冲突的测试需更新到 TEST-01 任务中处理）
- 每个任务操作一个文件或一组紧密相关文件
- 每个 Phase 结束后做一次 git commit
- 禁止直接修改 `src/parser/codebase.py`、`src/graph/ordering.py`、`src/doc/mermaid.py`（这些文件 V2 保留不变）

### 执行预算

```
预估总任务数: 20 个任务（DEL-01~DEL-08 + NEW-01~NEW-03 + MOD-01~MOD-07 + TEST-01 + INIT-01）
预估每任务耗时: 8-15 分钟（删除任务 3 分钟，新建/修改任务 10-20 分钟）
预估总耗时: 约 200 分钟（3-4 小时）
Context 窗口评估: 需要 /clear 中断，建议在 Phase 3 和 Phase 4 之间各清理一次。
  Phase 1+2（8+3=11 任务）约 80 分钟，Phase 3（5 任务）约 70 分钟，Phase 4+5 约 50 分钟
```

---

## Block 2 — Execution Progress（执行进度）

### Phase 0: 前置准备

- [ ] INIT-01: 修改 src/__init__.py 和各子模块 __init__.py 确保导出一致（为后续删除做准备） → agent tdd-guide → (import 清理完成)

### Phase 1: 删除废弃文件（P0）

- [ ] DEL-01: 删除 src/doc/generator.py（Jinja2 文档生成器）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-02: 删除 src/doc/templates.py（Jinja2 模板渲染器）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-03: 删除 src/doc/_context.py（链接生成和索引构建，V1 链接断裂根因）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-04: 删除 src/templates/ 目录内全部 .j2 文件（index.md.j2, overview.md.j2, detail.md.j2）→ agent refactor-cleaner → (3 个模板文件已删除)
- [ ] DEL-05: 删除 src/state/checkpoint.py（CheckpointManager，由 state.json task status 替代）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-06: 删除 src/budget/controller.py（AnalysisBudgetController + 5 条停止规则）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-07: 删除 src/state/_schema.py（SQLite DDL 建表脚本）→ agent refactor-cleaner → (文件已删除)
- [ ] DEL-08: 删除 src/doc/_tree_builder.py（DocPlanNode 逻辑，后续 MOD-05 会重建 task_manifest 版本）→ agent refactor-cleaner → (文件已删除)

### Phase 2: 创建新基础文件（P0）

- [ ] NEW-01: 创建 src/state/json_store.py（JSON 原子读写，替代 database.py）→ agent tdd-guide → (文件已创建且测试通过)
- [ ] NEW-02: 创建 src/graph/feature_cone.py（Feature Cone 提取算法：SCC + DAG + BFS）→ agent tdd-guide → (文件已创建且测试通过)
- [ ] NEW-03: 创建 src/graph/weighted_graph.py（加权多关系图构建器：import/call/inherit）→ agent tdd-guide → (文件已创建且测试通过)

### Phase 3: 修改现有文件（P1）

- [ ] MOD-01: 修改 src/graph/dependency.py（集成加权图构建和文件级子图查询）→ agent tdd-guide → (文件已修改，测试通过)
- [ ] MOD-02: 修改 src/graph/grouper.py（Feature Cone 作主力 + Louvain 降为 fallback）→ agent tdd-guide → (文件已修改，测试通过)
- [ ] MOD-03: 修改 src/budget/estimator.py（新增 chars÷4 主力函数，旧方法标记 deprecated）→ agent tdd-guide → (文件已修改，测试通过)
- [ ] MOD-04: 修改 src/state/models.py（删除 SQLite dataclass，新增 JSON-compatible frozen dataclass）→ agent tdd-guide → (文件已修改，测试通过)
- [ ] MOD-05: 修改 src/doc/depth_planner.py（替换三维阈值表为 DAG 分层深度计算）→ agent tdd-guide → (文件已修改，测试通过)

### Phase 4: 重建核心文件（P1）

- [ ] MOD-06: 重建 src/server.py（7 个新工具，移除 SQLite/Jinja2，添加 JSON 文件读写）→ agent tdd-guide → (server.py 重建完成，7 个工具可正常调用)
- [ ] MOD-07: 重写 .agents/skills/codebase-explorer/SKILL.md（5-Phase 工作流 + Validator/DETAIL/INDEX Agent Prompt 模板）→ agent doc-updater → (SKILL.md 重写完成)

### Phase 5: 更新测试（P2）

- [ ] TEST-01: 更新 tests/e2e_test.py（适配新 7 工具 API，移除对旧 15 工具的引用）→ agent tdd-guide → (测试全部通过)

---

## Block 3 — Agent 职责矩阵（Agent Responsibility Matrix）

---

### INIT-01: 修改 __init__.py 文件（为删除做准备）

**Skill**: agent tdd-guide
**目标**: 清理各模块的 `__init__.py` 导出，移除对待删除文件的引用，防止后续删除操作触发 ImportError。

**操作范围**:
```
创建: []
修改: [
  src/budget/__init__.py,
  src/state/__init__.py,
  src/doc/__init__.py
]
禁止修改: [
  src/server.py,
  src/graph/__init__.py,
  src/parser/__init__.py,
  src/__init__.py
]
```

**复用**: 无

**预期日志输出**:
- `[INIT-01] budget/__init__.py: removed controller export`
- `[INIT-01] state/__init__.py: removed Database, CheckpointManager exports`
- `[INIT-01] doc/__init__.py: removed DocumentGenerator, TemplateRenderer exports`

**验收标准**:
- [ ] `python -c "from src.budget import estimator"` 退出码 0
- [ ] `python -c "from src.state import models"` 退出码 0
- [ ] `python -c "from src.doc import depth_planner"` 退出码 0
- [ ] `grep -r "from src.budget.controller" src/ | grep -v test` 无输出

**回滚策略**:
```
回滚点: git stash 或 git checkout -- src/budget/__init__.py src/state/__init__.py src/doc/__init__.py
替代方案: 在删除文件时同步修改 __init__.py，而非提前修改
丢弃条件: 若修改 __init__.py 导致当前测试失败，则先跳过此任务，在 DEL 任务中同步处理
```

**超时**: 10 分钟

---

### DEL-01: 删除 src/doc/generator.py

**Skill**: agent refactor-cleaner
**目标**: 删除 Jinja2 文档生成器，消除"MCP 做文档生成"的架构违规。

**操作范围**:
```
创建: []
修改: [src/doc/__init__.py]
删除: [src/doc/generator.py]
禁止修改: [
  src/server.py,
  src/doc/depth_planner.py,
  src/doc/mermaid.py,
  tests/
]
```

**复用**: 无

**预期日志输出**:
- `[DEL-01] Deleted src/doc/generator.py`
- `[DEL-01] Removed DocumentGenerator import from src/doc/__init__.py`

**验收标准**:
- [ ] `ls src/doc/generator.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "from src.doc.generator\|from src.doc import.*DocumentGenerator\|import.*generator" src/ | grep -v "#"` 无输出
- [ ] `python -c "import src.doc"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/doc/generator.py src/doc/__init__.py
替代方案: 将 generator.py 内容清空（保留空模块）而非删除，避免 ImportError
丢弃条件: 如果 generator.py 被 server.py 之外超过 3 个文件直接 import（需先处理这些文件）
```

**超时**: 5 分钟

---

### DEL-02: 删除 src/doc/templates.py

**Skill**: agent refactor-cleaner
**目标**: 删除 TemplateRenderer 和所有 Jinja2 模板引用，完全移除 Jinja2 依赖。

**操作范围**:
```
创建: []
修改: [src/doc/__init__.py]
删除: [src/doc/templates.py]
禁止修改: [
  src/server.py,
  src/doc/generator.py,  # 已被 DEL-01 删除
  tests/
]
```

**复用**: 无

**预期日志输出**:
- `[DEL-02] Deleted src/doc/templates.py`
- `[DEL-02] Removed TemplateRenderer import from src/doc/__init__.py`

**验收标准**:
- [ ] `ls src/doc/templates.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "from src.doc.templates\|TemplateRenderer\|Jinja2\|jinja2" src/ | grep -v test | grep -v ".pyc"` 无输出
- [ ] `python -c "import src.doc"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/doc/templates.py src/doc/__init__.py
替代方案: 将 templates.py 内容清空（保留空模块）
丢弃条件: 如果 Jinja2 仍被其他未处理文件依赖
```

**超时**: 5 分钟

---

### DEL-03: 删除 src/doc/_context.py

**Skill**: agent refactor-cleaner
**目标**: 删除 `make_relative_link()` 和 `build_doc_index()`（V1 链接断裂根因）。V2 中 Agent 负责生成正确相对路径，`doc-index.json` 由 INDEX Agent 生成。

**操作范围**:
```
创建: []
修改: [src/doc/__init__.py]
删除: [src/doc/_context.py]
禁止修改: [
  src/server.py,
  tests/
]
```

**复用**: 无（此文件是 V1 链接断裂根因，不复用任何逻辑）

**预期日志输出**:
- `[DEL-03] Deleted src/doc/_context.py`
- `[DEL-03] Removed make_relative_link, build_doc_index imports from src/doc/__init__.py`

**验收标准**:
- [ ] `ls src/doc/_context.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "make_relative_link\|build_doc_index\|_context" src/ | grep -v test | grep -v "#"` 无输出
- [ ] `python -c "import src.doc"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/doc/_context.py src/doc/__init__.py
替代方案: 保留文件但将函数体替换为 NotImplementedError（标记为废弃）
丢弃条件: 无（此文件是需要删除的根因代码）
```

**超时**: 5 分钟

---

### DEL-04: 删除 src/templates/ 目录内 .j2 模板文件

**Skill**: agent refactor-cleaner
**目标**: 删除所有 Jinja2 模板文件（index.md.j2、overview.md.j2、detail.md.j2），V2 文档由 LLM Agent 直接撰写。

**操作范围**:
```
创建: []
修改: []
删除: [
  src/templates/index.md.j2,
  src/templates/overview.md.j2,
  src/templates/detail.md.j2
]
禁止修改: [src/templates/ 目录本身（保留目录以防其他用途）]
```

**复用**: 无

**预期日志输出**:
- `[DEL-04] Deleted src/templates/index.md.j2`
- `[DEL-04] Deleted src/templates/overview.md.j2`
- `[DEL-04] Deleted src/templates/detail.md.j2`

**验收标准**:
- [ ] `ls src/templates/*.j2 2>&1 | grep "No such file"` 返回非空（或目录为空）
- [ ] `find src/templates/ -name "*.j2" | wc -l | tr -d ' '` 输出 `0`

**回滚策略**:
```
回滚点: git checkout -- src/templates/
替代方案: 将 .j2 文件内容清空但保留文件（空模板）
丢弃条件: 无（模板是纯删除，无复杂依赖）
```

**超时**: 3 分钟

---

### DEL-05: 删除 src/state/checkpoint.py

**Skill**: agent refactor-cleaner
**目标**: 删除 `CheckpointManager`，断点恢复改由 `state.json` task status + 恢复算法实现（见 NEW-01）。

**操作范围**:
```
创建: []
修改: [src/state/__init__.py]
删除: [src/state/checkpoint.py]
禁止修改: [
  src/server.py,
  src/state/database.py,  # 将被 DEL-07 删除，此时不修改
  tests/
]
```

**复用**: 无

**预期日志输出**:
- `[DEL-05] Deleted src/state/checkpoint.py`
- `[DEL-05] Removed CheckpointManager export from src/state/__init__.py`

**验收标准**:
- [ ] `ls src/state/checkpoint.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "CheckpointManager\|from src.state.checkpoint" src/ | grep -v test | grep -v "#"` 无输出
- [ ] `python -c "import src.state"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/state/checkpoint.py src/state/__init__.py
替代方案: 保留文件但标记为废弃（deprecated），在 NEW-01 json_store.py 中实现断点恢复
丢弃条件: 如果 checkpoint.py 被 server.py 之外超过 2 个文件直接依赖
```

**超时**: 5 分钟

---

### DEL-06: 删除 src/budget/controller.py

**Skill**: agent refactor-cleaner
**目标**: 删除 `AnalysisBudgetController` 和 5 条停止规则，Token 预算验证移入 `analyze_codebase` 内部装箱算法（NEW-02/MOD-06 实现）。

**操作范围**:
```
创建: []
修改: [src/budget/__init__.py]
删除: [src/budget/controller.py]
禁止修改: [
  src/budget/estimator.py,
  src/server.py,
  tests/
]
```

**复用**: 无

**预期日志输出**:
- `[DEL-06] Deleted src/budget/controller.py`
- `[DEL-06] Removed AnalysisBudgetController export from src/budget/__init__.py`

**验收标准**:
- [ ] `ls src/budget/controller.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "AnalysisBudgetController\|from src.budget.controller\|budget_controller" src/ | grep -v test | grep -v "#"` 无输出
- [ ] `python -c "import src.budget"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/budget/controller.py src/budget/__init__.py
替代方案: 保留文件但标记为废弃
丢弃条件: 无
```

**超时**: 5 分钟

---

### DEL-07: 删除 src/state/_schema.py

**Skill**: agent refactor-cleaner
**目标**: 删除 SQLite 建表 DDL 脚本，V2 不使用任何 SQLite。

**操作范围**:
```
创建: []
修改: [src/state/__init__.py]
删除: [src/state/_schema.py]
禁止修改: [
  src/state/database.py,  # 将被后续删除，此时不修改
  src/server.py,
  tests/
]
```

**复用**: 无

**预期日志输出**:
- `[DEL-07] Deleted src/state/_schema.py`

**验收标准**:
- [ ] `ls src/state/_schema.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "from src.state._schema\|_schema\|CREATE TABLE" src/ | grep -v test | grep -v "#"` 无输出（CREATE TABLE 检查排除注释）
- [ ] `python -c "import src.state"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/state/_schema.py
替代方案: 保留文件但内容清空
丢弃条件: 无（纯删除）
```

**超时**: 3 分钟

---

### DEL-08: 删除 src/doc/_tree_builder.py

**Skill**: agent refactor-cleaner
**目标**: 删除 DocPlanNode 文档树构建逻辑。注意：`_tree_builder.py` 在 V2 中会被重建为 `build_task_manifest()` 函数，但重建逻辑属于 MOD-05 任务（修改 depth_planner.py 时同步处理）。此处先删除旧版本。

**操作范围**:
```
创建: []
修改: [src/doc/__init__.py]
删除: [src/doc/_tree_builder.py]
禁止修改: [
  src/doc/depth_planner.py,
  src/server.py,
  tests/
]
```

**复用**: 无（新版 task_manifest 构建器逻辑将在 MOD-05 中创建）

**预期日志输出**:
- `[DEL-08] Deleted src/doc/_tree_builder.py`
- `[DEL-08] Removed DocPlanNode, build_doc_tree exports from src/doc/__init__.py`

**验收标准**:
- [ ] `ls src/doc/_tree_builder.py 2>&1 | grep "No such file"` 返回非空
- [ ] `grep -r "DocPlanNode\|_tree_builder\|build_doc_tree" src/ | grep -v test | grep -v "#"` 无输出
- [ ] `python -c "import src.doc"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/doc/_tree_builder.py src/doc/__init__.py
替代方案: 保留文件但标记为废弃
丢弃条件: 如果 depth_planner.py 直接 import _tree_builder（需先解耦）
```

**超时**: 5 分钟

---

### NEW-01: 创建 src/state/json_store.py

**Skill**: agent tdd-guide
**目标**: 实现 JSON 文件原子读写，替代 `database.py`。提供 `atomic_write_state()`、`read_state()`、`update_task_status()`、`resume_from_state()` 四个核心函数。

**操作范围**:
```
创建: [
  src/state/json_store.py,
  tests/test_json_store.py
]
修改: [src/state/__init__.py]
禁止修改: [
  src/state/models.py,  # 将在 MOD-04 修改，此时不改
  src/server.py,
  src/state/database.py  # 尚未删除，不修改
]
```

**复用**: `02c_responsibility_v2.md` Section 4（state.json Schema）+ Section 5（断点恢复算法伪代码）

**预期日志输出**:
- `[json_store] Atomic write to state.json completed`
- `[json_store] Resuming from state: N tasks pending, M in_progress reset to pending`
- `[json_store] State file not found, returning empty state`

**验收标准**:
- [ ] `python -m pytest tests/test_json_store.py -x -q` 退出码 0
- [ ] `ls src/state/json_store.py` 文件存在
- [ ] `python -c "from src.state.json_store import atomic_write_state, read_state, update_task_status, resume_from_state"` 退出码 0
- [ ] 测试覆盖原子写入（先写 .tmp 再 os.replace）、断点恢复（in_progress → pending 重置）、文件完整性检查（size > 200 bytes + 结束标记）

**回滚策略**:
```
回滚点: git stash 或删除 src/state/json_store.py 和 tests/test_json_store.py
替代方案: 使用简化版（只实现 atomic_write_state 和 read_state，不含 resume 逻辑）
丢弃条件: 如果 json_store.py 的 resume 逻辑与 models.py 的数据结构发生冲突（等 MOD-04 完成后再重试）
```

**超时**: 20 分钟

**实现要点**（来自 `02c_responsibility_v2.md` Section 4-5）:

```python
# 核心函数签名：
def atomic_write_state(state_path: Path, state: dict) -> None:
    """先写 .tmp 再 os.replace()，POSIX 原子操作。"""
    tmp_path = state_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    os.replace(tmp_path, state_path)

def read_state(state_path: Path) -> dict | None:
    """读取 state.json，文件不存在返回 None。"""

def update_task_status(
    state_path: Path,
    task_id: str,
    status: Literal["pending", "in_progress", "complete", "failed"],
    output_files: list[dict] | None = None,
) -> dict:
    """原子更新指定任务的状态。"""

def resume_from_state(project_root: Path) -> list[str]:
    """
    处理 in_progress 任务（崩溃遗留）：
    - 所有输出文件存在 + size > 200B + 含结束标记 → 标记为 complete
    - 否则 → 重置为 pending
    返回有序的 pending task ID 列表
    """
```

---

### NEW-02: 创建 src/graph/feature_cone.py

**Skill**: agent tdd-guide
**目标**: 实现 Feature Cone 提取算法（SCC + DAG 分层 + BFS），作为 V2 的核心模块分组主力算法，替代 Louvain。

**操作范围**:
```
创建: [
  src/graph/feature_cone.py,
  tests/test_feature_cone.py
]
修改: [src/graph/__init__.py]
禁止修改: [
  src/graph/grouper.py,   # 将在 MOD-02 修改
  src/graph/dependency.py,  # 将在 MOD-01 修改
  src/graph/ordering.py,  # KEEP 不修改
  src/server.py
]
```

**复用**: `03_final_progressive_scheme.md` Section 2.6（功能锥体提取流程图）+ `02a_code_analysis_v2.md` Section 3.2-3.4（SCC/DAG/Feature Cone 算法伪代码）

**预期日志输出**:
- `[feature_cone] Found N SCC groups, condensed to DAG with M nodes`
- `[feature_cone] Identified K feature roots (in-degree=0 nodes)`
- `[feature_cone] Extracted N feature cones, J infrastructure nodes (shared_threshold=2)`
- `[feature_cone] Cone 'cone_cli' → 3 files, layer=2, tokens=4200`

**验收标准**:
- [ ] `python -m pytest tests/test_feature_cone.py -x -q` 退出码 0
- [ ] `ls src/graph/feature_cone.py` 文件存在
- [ ] `python -c "from src.graph.feature_cone import extract_feature_cones, find_feature_roots, assign_scc_to_cone"` 退出码 0
- [ ] 测试包含：(a) 简单 DAG（无 SCC）的 cone 提取；(b) 含 SCC 的循环依赖场景；(c) infrastructure 识别（shared_threshold=2）；(d) 扁平目录触发 Louvain fallback 的条件

**回滚策略**:
```
回滚点: git stash 或删除 src/graph/feature_cone.py 和 tests/test_feature_cone.py
替代方案: 将 Feature Cone 算法直接内嵌到 grouper.py（MOD-02）而不单独成文件
丢弃条件: 如果 graph-sitter 提供的 FunctionInfo.dependencies 字段在测试代码库中为空，导致 call 边无法构建（退化到仅 import 边的场景也可接受）
```

**超时**: 25 分钟

**实现要点**（来自 `02a_code_analysis_v2.md` Section 3.2-3.4）:

```python
# 核心函数：
SHARED_THRESHOLD = 2

def find_feature_roots(dag: nx.DiGraph) -> list[str]:
    """找到 in-degree=0 的节点作为 Feature Root。
    fallback: 若所有节点 in-degree > 0（库代码），取 in-degree <= min+1 的节点集。"""

def extract_feature_cones(
    dag: nx.DiGraph,
    snapshot: CodebaseSnapshot,
    shared_threshold: int = SHARED_THRESHOLD,
) -> tuple[dict[str, FeatureCone], frozenset[str]]:
    """BFS 追踪每个 Feature Root 的依赖锥体。
    返回 (cone_dict, infrastructure_nodes)。
    infrastructure_nodes: 被 >= shared_threshold 个 cone 共享的节点。"""

def assign_scc_to_cone(
    scc_members: list[str],
    cone_assignments: dict[str, str],
) -> str | None:
    """SCC 归属决策：哪个 cone 包含最多 SCC 成员 → SCC 归属该 cone。
    平局 → 归入 infrastructure。"""
```

---

### NEW-03: 创建 src/graph/weighted_graph.py

**Skill**: agent tdd-guide
**目标**: 实现加权多关系图构建器，合并 import/call/inherit 三类边并分配权重（1/2/3），替代当前 `build_dependency_graph()` 中仅使用 import 边的做法。

**操作范围**:
```
创建: [
  src/graph/weighted_graph.py,
  tests/test_weighted_graph.py
]
修改: [src/graph/__init__.py]
禁止修改: [
  src/graph/dependency.py,   # 将在 MOD-01 修改（集成本模块）
  src/graph/grouper.py,
  src/server.py
]
```

**复用**: `03_final_progressive_scheme.md` Section 2.6 + `02a_code_analysis_v2.md` Section 3.1（完整伪代码）

**预期日志输出**:
- `[weighted_graph] Added N import edges (weight=1), M call edges (weight=2), K inherit edges (weight=3)`
- `[weighted_graph] Built weighted graph: P nodes, Q edges (total weight sum: R)`
- `[weighted_graph] Warning: function 'foo' appears in multiple files, skipping call edge (conservative strategy)`

**验收标准**:
- [ ] `python -m pytest tests/test_weighted_graph.py -x -q` 退出码 0
- [ ] `ls src/graph/weighted_graph.py` 文件存在
- [ ] `python -c "from src.graph.weighted_graph import build_weighted_dependency_graph, WeightedGraphResult"` 退出码 0
- [ ] 测试包含：(a) import 边权重 1；(b) 同一对文件有 import+call → 权重累加为 3；(c) 函数名重名时保守跳过（不建错误边）；(d) 继承边权重 3 的构建

**回滚策略**:
```
回滚点: git stash 或删除 src/graph/weighted_graph.py 和 tests/test_weighted_graph.py
替代方案: 将加权图逻辑直接内嵌到 dependency.py（MOD-01）而不单独成文件
丢弃条件: 如果 graph-sitter 的 ClassInfo.base_classes 字段只返回字符串而非路径，导致继承边无法构建（可以跳过继承边，只用 import+call 边）
```

**超时**: 20 分钟

**实现要点**（来自 `02a_code_analysis_v2.md` Section 3.1）:

```python
EDGE_WEIGHTS = {
    "import": 1,
    "call": 2,
    "inherit": 3,
}

def build_weighted_dependency_graph(snapshot: CodebaseSnapshot) -> WeightedGraphResult:
    """
    构建加权多关系图:
    1. 构建 class_name_to_file 查找表 (class_name → file_path)
    2. 构建 func_name_to_file 查找表 (func_name → file_path)
       注意：同名函数存在于多个文件时，不建 call 边（保守策略）
    3. import 边: file.import_sources → weight += 1
    4. call 边: func.dependencies → weight += 2（按文件路径，非函数名）
    5. inherit 边: class.base_classes 查表 → weight += 3
    6. 同一对文件的多种关系 → 权重累加
    """
```

---

### MOD-01: 修改 src/graph/dependency.py

**Skill**: agent tdd-guide
**目标**: 集成加权图构建（复用 NEW-03 的 `build_weighted_dependency_graph()`），新增 `get_file_dependency_subgraph()` 支持 `scope="file"`。保留原 `build_dependency_graph()` 向后兼容。

**操作范围**:
```
创建: []
修改: [src/graph/dependency.py]
禁止修改: [
  src/graph/weighted_graph.py,  # 已由 NEW-03 创建，只复用
  src/graph/grouper.py,
  src/graph/ordering.py,
  src/server.py,
  tests/test_dependency.py  # 如果存在，不修改（保证向后兼容）
]
```

**复用**: `src/graph/weighted_graph.py` 中的 `build_weighted_dependency_graph()`（NEW-03 产出）

**预期日志输出**:
- `[dependency] build_weighted_dependency_graph: N files, M weighted edges`
- `[dependency] get_file_dependency_subgraph: file=X, hops=1, subgraph has P nodes`

**验收标准**:
- [ ] `python -c "from src.graph.dependency import build_dependency_graph, build_weighted_dependency_graph, get_file_dependency_subgraph"` 退出码 0
- [ ] `python -m pytest tests/ -k "dependency" -x -q` 退出码 0（原有 dependency 测试通过）
- [ ] `python -c "from src.graph.dependency import build_weighted_dependency_graph; help(build_weighted_dependency_graph)"` 显示函数签名

**回滚策略**:
```
回滚点: git checkout -- src/graph/dependency.py
替代方案: 不修改 dependency.py，将加权图作为独立函数只在 server.py 中直接调用 weighted_graph.py
丢弃条件: 如果 build_weighted_dependency_graph 与原 build_dependency_graph 的返回类型不兼容（需先修改调用者）
```

**超时**: 15 分钟

---

### MOD-02: 修改 src/graph/grouper.py

**Skill**: agent tdd-guide
**目标**: 新增 `extract_feature_cones()` 作为主力分组算法（复用 NEW-02），原 `group_modules()` Louvain 降为辅助（7 种触发条件之一：扁平目录场景）。新增 `get_cone_metrics()` 函数。

**操作范围**:
```
创建: []
修改: [src/graph/grouper.py]
禁止修改: [
  src/graph/feature_cone.py,  # 只复用，不修改
  src/graph/weighted_graph.py,
  src/graph/ordering.py,
  src/server.py
]
```

**复用**: `src/graph/feature_cone.py` 中的 `extract_feature_cones()`（NEW-02 产出）

**预期日志输出**:
- `[grouper] Feature Cone mode: extracted N cones from DAG`
- `[grouper] Louvain fallback triggered: flat directory structure detected (0 subdirectories)`
- `[grouper] get_cone_metrics: cone 'cone_cli' metrics computed`

**验收标准**:
- [ ] `python -c "from src.graph.grouper import group_modules, extract_feature_cones, get_cone_metrics"` 退出码 0
- [ ] `python -m pytest tests/ -k "grouper" -x -q` 退出码 0
- [ ] `python -c "from src.graph.grouper import group_modules; print('Louvain backward compat OK')"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/graph/grouper.py
替代方案: 保留原 grouper.py 不变，在 server.py 中直接调用 feature_cone.py（跳过 grouper.py 的集成）
丢弃条件: 如果 Feature Cone 提取结果与 Louvain 结果差异过大导致测试失败（检查测试断言是否过于依赖 Louvain 的输出格式）
```

**超时**: 20 分钟

---

### MOD-03: 修改 src/budget/estimator.py

**Skill**: agent tdd-guide
**目标**: 新增主力函数 `estimate_tokens_from_chars(char_count, language)` 使用 `CHARS_PER_TOKEN = {"python": 3.5, "typescript": 4.0, "javascript": 3.8}`。新增 `estimate_file_tokens(file_path)` 直接读文件返回估算结果。原 `estimate_tokens_from_lines()` 保留但标记为 deprecated。

**操作范围**:
```
创建: []
修改: [src/budget/estimator.py]
禁止修改: [
  src/budget/controller.py,  # 已被 DEL-06 删除
  src/server.py,
  tests/
]
```

**复用**: `02c_responsibility_v2.md` Section 2 Tool 6（`get_file_tokens` 设计说明）+ `03_final_progressive_scheme.md` 附录决策表（token 估算方法）

**预期日志输出**:
- `[estimator] estimate_tokens_from_chars: 12040 chars / 3.5 = 3440 tokens (python)`
- `[estimator] estimate_tokens_from_lines deprecated, use estimate_tokens_from_chars`

**验收标准**:
- [ ] `python -c "from src.budget.estimator import estimate_tokens_from_chars, estimate_file_tokens"` 退出码 0
- [ ] `python -c "from src.budget.estimator import estimate_tokens_from_chars; assert estimate_tokens_from_chars(3500, 'python') == 1000"` 退出码 0
- [ ] `python -m pytest tests/ -k "estimator" -x -q` 退出码 0（若有 estimator 测试）

**回滚策略**:
```
回滚点: git checkout -- src/budget/estimator.py
替代方案: 只新增 estimate_tokens_from_chars，不添加 estimate_file_tokens（后者在 server.py 中实现为内联函数）
丢弃条件: 无（此修改是纯新增，不破坏现有接口）
```

**超时**: 10 分钟

---

### MOD-04: 修改 src/state/models.py

**Skill**: agent tdd-guide
**目标**: 删除 SQLite 对应的 dataclass（`ProjectRecord`、`ModuleRecord`、`AnalysisTask`、`AnalysisResult`、`DocNode`），新增 JSON Schema 对应的 frozen dataclass（`StateFile`、`ProjectMeta`、`TaskRecord`、`OutputFileRecord`、`DocumentationMeta`）。

**操作范围**:
```
创建: []
修改: [src/state/models.py]
禁止修改: [
  src/state/database.py,  # 依赖旧 models 的旧文件，将被整体删除（先不管）
  src/state/json_store.py,  # 已由 NEW-01 创建，需保持兼容
  src/server.py,
  tests/
]
```

**复用**: `02c_responsibility_v2.md` Section 4（state.json Schema）→ 对应的 Python dataclass 定义

**预期日志输出**:
- `[models] StateFile dataclass initialized with schema_version='2.0'`
- `[models] TaskRecord: task_001 status=complete`

**验收标准**:
- [ ] `python -c "from src.state.models import StateFile, ProjectMeta, TaskRecord, OutputFileRecord, DocumentationMeta"` 退出码 0
- [ ] `python -c "from src.state.models import ProjectRecord"` 应产生 ImportError（旧类已删除）
- [ ] 所有新 dataclass 使用 `frozen=True`（不可变对象）
- [ ] `python -m pytest tests/ -k "models" -x -q 2>/dev/null || echo "no model tests, OK"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/state/models.py
替代方案: 保留旧 dataclass 不删除，新旧并存（在 server.py 中只使用新 dataclass）
丢弃条件: 如果 json_store.py（NEW-01）的 resume_from_state() 函数与新 models 不兼容（需同步修改 json_store.py）
```

**超时**: 15 分钟

---

### MOD-05: 修改 src/doc/depth_planner.py

**Skill**: agent tdd-guide
**目标**: 替换三维阈值表（`_STRUCTURAL_THRESHOLDS`、`_COMPLEXITY_THRESHOLDS`、`_TOKEN_THRESHOLDS`）为基于 DAG 分层数量的深度计算：`calculate_feature_cone_depth(cone, dag)` → 深度 = 锥体内 DAG 层数，受 token 预算约束。同时在此文件中添加 `build_task_manifest()` 函数（替代已删除的 `_tree_builder.py`）。

**操作范围**:
```
创建: []
修改: [src/doc/depth_planner.py]
禁止修改: [
  src/doc/mermaid.py,
  src/graph/feature_cone.py,
  src/server.py,
  tests/
]
```

**复用**: `02c_responsibility_v2.md` Section 7（depth_planner.py REPLACE 决策）+ `02a_code_analysis_v2.md` Section 5（装箱算法 FFD 伪代码）

**预期日志输出**:
- `[depth_planner] cone 'cone_cli' depth=2 (3 DAG layers, token_budget=6000)`
- `[depth_planner] small module constraint: cone 'cone_utils' has 8 components → depth capped to 1`
- `[depth_planner] build_task_manifest: N tasks (batch=A, single=B, split=C)`

**验收标准**:
- [ ] `python -c "from src.doc.depth_planner import calculate_feature_cone_depth, build_task_manifest"` 退出码 0
- [ ] `python -c "from src.doc.depth_planner import plan_doc_structure"` 退出码 0（如果原函数保留）或 ImportError（如果已删除）——记录实际结果
- [ ] 深度计算：小模块约束保留（总组件 < 10 且行数 < 200 → 强制 depth=1）
- [ ] `build_task_manifest()` 输出包含 `batch`、`single`、`split` 三种任务类型
- [ ] `python -m pytest tests/ -k "depth_planner or planner" -x -q 2>/dev/null || echo "no planner tests"` 退出码 0

**回滚策略**:
```
回滚点: git checkout -- src/doc/depth_planner.py
替代方案: 只添加 build_task_manifest()，保留原三维阈值表不删除（两种方法并存）
丢弃条件: 如果 calculate_feature_cone_depth 需要 feature_cone.py 的数据结构但 NEW-02 尚未完成
```

**超时**: 20 分钟

---

### MOD-06: 重建 src/server.py

**Skill**: agent tdd-guide
**目标**: 重建 server.py，实现 7 个新 MCP 工具，移除所有旧工具（15 个）、SQLite/Jinja2 相关 import 和 `_lifespan` 中的旧初始化逻辑。这是 Phase 4 最核心的任务。

**操作范围**:
```
创建: []
修改: [src/server.py]
禁止修改: [
  src/graph/feature_cone.py,
  src/graph/weighted_graph.py,
  src/state/json_store.py,
  src/state/models.py,
  src/budget/estimator.py,
  tests/  # TEST-01 任务处理测试更新
]
```

**复用**:
- `02c_responsibility_v2.md` Section 2（7 个工具完整 API 签名）
- `02c_responsibility_v2.md` Section 4（state.json Schema）
- `03_final_progressive_scheme.md` Section 2.2（工具迁移最终对照表）
- `src/graph/feature_cone.py`（NEW-02）
- `src/graph/weighted_graph.py`（NEW-03）
- `src/state/json_store.py`（NEW-01）
- `src/budget/estimator.py`（MOD-03）
- `src/doc/depth_planner.py`（MOD-05，用于 build_task_manifest）

**预期日志输出**:
- `[server] analyze_codebase: parsing /path/to/repo...`
- `[server] analyze_codebase: 24 files, 7 feature cones, 12 tasks generated`
- `[server] analyze_codebase: wrote 5 JSON files + state.json to .codebase-analysis/`
- `[server] get_structure: returning summary (N files, M functions)`
- `[server] get_feature_cones: returning all cones from 03_feature_cones.json`
- `[server] submit_analysis: task_001 marked complete, 3 files verified on disk`
- `[server] get_progress: 4/12 tasks complete (33.3%), coverage=16.7%`

**验收标准**:
- [ ] `grep -c "^@mcp.tool" src/server.py` 输出 `7`
- [ ] `python -c "import src.server"` 退出码 0
- [ ] `grep -c "aiosqlite\|Database\|CheckpointManager\|DocumentGenerator\|TemplateRenderer\|Jinja2" src/server.py` 输出 `0`
- [ ] `grep "analyze_codebase\|get_structure\|get_feature_cones\|get_dependency_graph\|get_progress\|get_file_tokens\|submit_analysis" src/server.py | wc -l` 大于 7
- [ ] server.py 文件行数 < 800（高内聚低耦合原则）

**回滚策略**:
```
回滚点: git stash 或 git checkout -- src/server.py
替代方案: 分两步重建：先注释掉旧工具（保留文件结构），再逐步添加新工具
丢弃条件: 如果依赖的 NEW-01/NEW-02/NEW-03/MOD-01~05 任务有任何一个失败，则暂停此任务
```

**超时**: 40 分钟

**7 个工具简要实现指南**:

```
1. analyze_codebase(path, languages, output_dir, force_reindex):
   CodebaseParser.parse() → build_weighted_dependency_graph() → nx.condensation() →
   extract_feature_cones() → estimate_tokens_from_chars() → build_task_manifest() →
   写出 5 个 JSON + state.json → 返回 analyze_codebase 响应 Schema

2. get_structure(module, file, function):
   读 01_structure.json → 按 query_type 返回对应 Schema

3. get_feature_cones(cone_id):
   读 03_feature_cones.json → 返回全量列表或单个锥体详情

4. get_dependency_graph(scope, target, include_weights):
   读 02_dag.json → MermaidGenerator 生成图 → 返回 mermaid_graph + 元数据

5. get_progress(project_id):
   读 state.json → 统计 pending/complete/failed 任务数 → 计算覆盖率

6. get_file_tokens(file, module):
   读 04_file_tokens.json → 按 file 或 module(cone_id) 过滤返回

7. submit_analysis(task_id, detail_paths, snippet_paths, tokens_used, source_files_covered):
   验证文件存在 → atomic_write_state() 更新 state.json → 返回进度摘要
```

---

### MOD-07: 重写 .agents/skills/codebase-explorer/SKILL.md

**Skill**: agent doc-updater
**目标**: 完全重写 Skill 工作流文档，从 V1 的 15 工具 5-Phase（基于 Jinja2）改为 V2 的 7 工具 5-Phase（基于 Feature Cone + Agent 撰写文档），包含三个完整的 Agent Prompt 模板（Validator、DETAIL、INDEX）。

**操作范围**:
```
创建: []
修改: [.agents/skills/codebase-explorer/SKILL.md]
禁止修改: [
  .agents/skills/codebase-explorer/assets/,
  .agents/skills/codebase-explorer/references/,
  src/server.py,
  tests/
]
```

**复用**:
- `02b_skill_design_v2.md` Section 2（精化的 5-Phase 工作流）
- `02b_skill_design_v2.md` Section 3（Validator Agent 完整 Prompt 模板）
- `02b_skill_design_v2.md` Section 4（DETAIL Agent 完整 Prompt 模板，含 split 任务说明）
- `02b_skill_design_v2.md` Section 5（INDEX Agent 完整 Prompt 模板，含链接路径规则表）
- `02b_skill_design_v2.md` Section 8（样式约束节，所有 Agent Prompt 共用）
- `03_final_progressive_scheme.md` Section 2.1（完整数据流 Mermaid 图）
- `03_final_progressive_scheme.md` Section 2.4（Agent 角色边界表）

**预期日志输出**:
- `[doc-updater] SKILL.md: updated tools_count from 15 to 7`
- `[doc-updater] SKILL.md: added Phase 2 Validator Agent prompt template`
- `[doc-updater] SKILL.md: added Phase 3 DETAIL Agent prompt template with split task handling`
- `[doc-updater] SKILL.md: added Phase 4 INDEX Agent prompt template with link path rules`

**验收标准**:
- [ ] `grep -c "Phase [1-5]" .agents/skills/codebase-explorer/SKILL.md` 输出 >= 5
- [ ] `grep "tools_count: 7" .agents/skills/codebase-explorer/SKILL.md` 返回匹配
- [ ] `grep "analyze_codebase\|get_feature_cones\|submit_analysis" .agents/skills/codebase-explorer/SKILL.md | wc -l` > 3
- [ ] `grep "Validator Agent\|DETAIL Agent\|INDEX Agent" .agents/skills/codebase-explorer/SKILL.md | wc -l` >= 3
- [ ] `grep -c "index_codebase\|generate_doc\|save_checkpoint" .agents/skills/codebase-explorer/SKILL.md` 输出 `0`（旧工具已全部移除）

**回滚策略**:
```
回滚点: git checkout -- .agents/skills/codebase-explorer/SKILL.md
替代方案: 保留原 SKILL.md，新建 SKILL_V2.md 作为临时过渡
丢弃条件: 无（此任务是纯文档更新，不影响代码）
```

**超时**: 20 分钟

---

### TEST-01: 更新 tests/e2e_test.py

**Skill**: agent tdd-guide
**目标**: 更新 E2E 测试以适配新的 7 工具 API，移除对已删除的旧 15 工具的引用，添加新工具的基础验证测试。

**操作范围**:
```
创建: []
修改: [tests/e2e_test.py]
禁止修改: [
  src/server.py,  # 此时已完成，不再修改
  src/graph/,
  src/state/,
  src/budget/,
  src/doc/
]
```

**复用**: 新 API 签名来自 MOD-06 完成的 server.py 和 `02c_responsibility_v2.md` Section 2

**预期日志输出**:
- `[TEST-01] test_analyze_codebase: PASS (flask test repo indexed, 7 cones found)`
- `[TEST-01] test_get_feature_cones: PASS`
- `[TEST-01] test_submit_analysis: PASS`
- `[TEST-01] test_get_progress: PASS`

**验收标准**:
- [ ] `python -m pytest tests/e2e_test.py -x -q` 退出码 0
- [ ] `grep -c "index_codebase\|generate_doc\|save_checkpoint\|load_checkpoint\|check_budget" tests/e2e_test.py` 输出 `0`（旧工具引用已清除）
- [ ] `grep -c "analyze_codebase\|get_feature_cones\|get_progress" tests/e2e_test.py` 输出 > 0

**回滚策略**:
```
回滚点: git checkout -- tests/e2e_test.py
替代方案: 新建 tests/test_v2_tools.py 而不修改原 e2e_test.py（保留旧测试作参考）
丢弃条件: 如果 Flask 测试代码库不存在（test_repos/flask/），则跳过 E2E 测试，只做单元测试
```

**超时**: 20 分钟

---

## Block 4 — Parallel Execution Map（并行执行图）

### Phase 0 (前置准备)

```
串行步骤: INIT-01
  依赖：无
  原因：为后续所有删除操作清理导出，防止 ImportError 级联
  最大并行数：1（单步）
```

### Phase 1 (Delete obsolete files)

```
批次 1-A (并行): DEL-01, DEL-02
  依赖：INIT-01 完成（__init__.py 已预先清理导出）
  约束：DEL-01 修改 doc/__init__.py，DEL-02 也修改 doc/__init__.py → 潜在写冲突
  解决：按顺序 DEL-01 先，DEL-02 后，间隔 2 分钟
  实际执行：串行（同一文件的修改需要串行）

批次 1-B (并行): DEL-03, DEL-04
  依赖：DEL-01 + DEL-02 完成
  约束：DEL-03 修改 doc/__init__.py，DEL-04 只删文件（不改 __init__.py）→ 可以并行
  最大并行数：2

批次 1-C (并行): DEL-05, DEL-06
  依赖：DEL-03 + DEL-04 完成
  约束：DEL-05 改 state/__init__.py，DEL-06 改 budget/__init__.py → 不同文件，可并行
  最大并行数：2

批次 1-D (并行): DEL-07, DEL-08
  依赖：DEL-05 + DEL-06 完成
  约束：DEL-07 改 state/__init__.py，DEL-08 改 doc/__init__.py → 不同文件，可并行
  最大并行数：2

Phase 1 结束后：git commit "feat(v2): delete obsolete V1 files"
```

### Phase 2 (New foundation files)

```
串行步骤: NEW-01
  依赖：Phase 1 完成（确保 state/__init__.py 已清理）
  原因：NEW-01 修改 state/__init__.py，需要 DEL-07 已完成

批次 2-A (并行): NEW-02, NEW-03
  依赖：NEW-01 完成
  约束：NEW-02 修改 graph/__init__.py，NEW-03 也修改 graph/__init__.py → 潜在写冲突
  解决：NEW-02 先完成（约 25 分钟），NEW-03 后（约 20 分钟），不实际并行
  实际执行：NEW-02 先，NEW-03 后（同一文件修改）

Phase 2 结束后：git commit "feat(v2): create new foundation files"
```

### Phase 3 (Modify existing files)

```
批次 3-A (并行): MOD-01, MOD-03
  依赖：NEW-02 + NEW-03 完成
  约束：MOD-01 修改 dependency.py，MOD-03 修改 estimator.py → 不同文件，可并行
  最大并行数：2

批次 3-B (并行): MOD-02, MOD-04
  依赖：MOD-01 + MOD-03 完成
  约束：MOD-02 修改 grouper.py（依赖 MOD-01 已集成 weighted_graph），MOD-04 修改 models.py → 不同文件，可并行
  最大并行数：2

串行步骤: MOD-05
  依赖：MOD-02 完成（Feature Cone 数据结构需要 grouper.py 的集成）
  原因：depth_planner.py 中的 build_task_manifest() 依赖 FeatureCone 数据结构

Phase 3 结束后：git commit "feat(v2): modify core analysis modules"
```

### Phase 4 (Rebuild core)

```
串行步骤: MOD-06
  依赖：所有 Phase 3 任务（MOD-01~05）完成
  原因：server.py 从所有已修改/创建的模块 import，必须等所有依赖就绪

串行步骤: MOD-07
  依赖：MOD-06 完成
  原因：SKILL.md 中引用的工具名称、返回 Schema 必须与 server.py 实现一致

Phase 4 结束后：git commit "feat(v2): rebuild server with 7 tools and update SKILL"
```

### Phase 5 (Tests)

```
串行步骤: TEST-01
  依赖：Phase 4 全部完成（MOD-06 + MOD-07）
  原因：E2E 测试需要完整的 server.py 和可运行的 MCP 服务器

Phase 5 结束后：git commit "test(v2): update e2e tests for new 7-tool API"
```

---

## Block 5 — File Decomposition（文件拆解）

### 删除的文件

| 文件 | 任务 | 处置 |
|------|------|------|
| `src/doc/generator.py` | DEL-01 | DELETE（Jinja2 生成器，V2 移交 Agent）|
| `src/doc/templates.py` | DEL-02 | DELETE（Jinja2 模板渲染器）|
| `src/doc/_context.py` | DEL-03 | DELETE（make_relative_link V1 根因）|
| `src/templates/index.md.j2` | DEL-04 | DELETE（Jinja2 模板）|
| `src/templates/overview.md.j2` | DEL-04 | DELETE（Jinja2 模板）|
| `src/templates/detail.md.j2` | DEL-04 | DELETE（Jinja2 模板）|
| `src/state/checkpoint.py` | DEL-05 | DELETE（CheckpointManager）|
| `src/budget/controller.py` | DEL-06 | DELETE（AnalysisBudgetController）|
| `src/state/_schema.py` | DEL-07 | DELETE（SQLite DDL）|
| `src/doc/_tree_builder.py` | DEL-08 | DELETE（DocPlanNode，由 MOD-05 重建为 build_task_manifest）|

### 新建的文件

| 文件 | 任务 | 用途 |
|------|------|------|
| `src/state/json_store.py` | NEW-01 | JSON 原子读写，替代 database.py |
| `src/graph/feature_cone.py` | NEW-02 | Feature Cone 提取（SCC+DAG+BFS）|
| `src/graph/weighted_graph.py` | NEW-03 | 加权多关系图（import+call+inherit）|
| `tests/test_json_store.py` | NEW-01 | json_store.py 单元测试 |
| `tests/test_feature_cone.py` | NEW-02 | feature_cone.py 单元测试 |
| `tests/test_weighted_graph.py` | NEW-03 | weighted_graph.py 单元测试 |

### 修改的文件

| 文件 | 任务 | 主要变更 |
|------|------|---------|
| `src/budget/__init__.py` | INIT-01/DEL-06 | 移除 controller 导出 |
| `src/state/__init__.py` | INIT-01/DEL-05/DEL-07/NEW-01 | 移除旧导出，新增 JsonStore |
| `src/doc/__init__.py` | INIT-01/DEL-01/DEL-02/DEL-03/DEL-08 | 移除所有废弃导出 |
| `src/graph/__init__.py` | NEW-02/NEW-03 | 新增 feature_cone, weighted_graph 导出 |
| `src/graph/dependency.py` | MOD-01 | 集成加权图，新增 get_file_dependency_subgraph |
| `src/graph/grouper.py` | MOD-02 | Feature Cone 主力 + Louvain fallback |
| `src/budget/estimator.py` | MOD-03 | 新增 chars÷4 方法，deprecated 标记旧方法 |
| `src/state/models.py` | MOD-04 | 删除 SQLite dataclass，新增 JSON dataclass |
| `src/doc/depth_planner.py` | MOD-05 | 替换阈值表，新增 build_task_manifest |
| `src/server.py` | MOD-06 | 重建：7 工具，移除 SQLite/Jinja2 |
| `.agents/skills/codebase-explorer/SKILL.md` | MOD-07 | V2 工作流 + 3 个 Agent Prompt 模板 |
| `tests/e2e_test.py` | TEST-01 | 适配 7 工具 API |

### 保留不变的文件（绝对不修改）

| 文件 | 原因 |
|------|------|
| `src/parser/codebase.py` | 核心解析能力不变（V2 保留）|
| `src/parser/language_detect.py` | 语言检测不变 |
| `src/parser/__init__.py` | 无变更 |
| `src/graph/ordering.py` | DAG 拓扑排序正确，继续使用 |
| `src/doc/mermaid.py` | Mermaid 图生成正确，继续使用 |
| `src/__init__.py` | 无变更 |

---

## Block 6 — Phase Structure（阶段结构）

### Phase 0: 前置准备
**入口条件**: 已读完所有优化文档，代码库处于 feature/codebase-explorer-impl-2026-03-22 分支
**任务**: INIT-01
**退出条件**: 所有 `__init__.py` 已清理旧导出，`python -c "import src"` 退出码 0

### Phase 1: 删除废弃文件
**入口条件**: Phase 0 完成
**任务**: DEL-01 至 DEL-08（8 个任务，按批次执行）
**退出条件**: 8 个文件全部删除，`grep -r "Jinja2\|DocumentGenerator\|CheckpointManager" src/ | grep -v test | grep -v pyc` 无输出；git commit 完成

### Phase 2: 创建新基础文件
**入口条件**: Phase 1 完成（确保旧文件已清除，不产生命名冲突）
**任务**: NEW-01，然后 NEW-02，然后 NEW-03
**退出条件**: 3 个新文件存在且对应测试通过；git commit 完成

### Phase 3: 修改现有文件
**入口条件**: Phase 2 完成（NEW-01/02/03 已就绪，可被 import）
**任务**: MOD-01 至 MOD-05（5 个任务，按批次执行）
**退出条件**: 5 个修改完成，`python -m pytest tests/ -x -q --ignore=tests/e2e_test.py` 退出码 0（跳过 E2E）；git commit 完成

### Phase 4: 重建核心文件
**入口条件**: Phase 3 完成（所有依赖模块就绪）
**任务**: MOD-06，然后 MOD-07
**退出条件**: `grep -c "^@mcp.tool" src/server.py` 输出 `7`；SKILL.md 包含 V2 工作流；git commit 完成

### Phase 5: 更新测试
**入口条件**: Phase 4 完成（server.py 可运行）
**任务**: TEST-01
**退出条件**: `python -m pytest tests/ -x -q` 退出码 0；git commit 完成

---

## Block 7 — Context Recovery Protocol（Context 恢复协议）

### 恢复头部

此文件顶端已放置恢复协议头部（见文件第一行）。

### 任务级恢复表

| 恢复场景 | 检查命令 | 操作 |
|---------|---------|------|
| DEL 任务失败 | `ls src/doc/generator.py 2>&1` | git checkout -- [文件] 然后重试 |
| NEW-01 失败 | `python -m pytest tests/test_json_store.py` | 检查 state.json schema 兼容性 |
| NEW-02 失败 | `python -m pytest tests/test_feature_cone.py` | 检查 nx.condensation 调用方式 |
| MOD-06 部分完成 | `grep -c "^@mcp.tool" src/server.py` | 期望 7，否则继续添加剩余工具 |
| tests 失败 | `python -m pytest tests/ -v` | 查看具体失败原因，对应回滚策略 |

### 状态检查快捷命令

```bash
# 检查整体进度
grep -c "^@mcp.tool" /Users/lexuanzhang/code/codebase-explorer/src/server.py 2>/dev/null || echo "server.py not rebuilt yet"

# 检查 Phase 1 完成度
for f in src/doc/generator.py src/doc/templates.py src/doc/_context.py src/state/checkpoint.py src/budget/controller.py src/state/_schema.py; do
  [ -f "/Users/lexuanzhang/code/codebase-explorer/$f" ] && echo "STILL EXISTS: $f" || echo "DELETED: $f"
done

# 检查 Phase 2 完成度
for f in src/state/json_store.py src/graph/feature_cone.py src/graph/weighted_graph.py; do
  [ -f "/Users/lexuanzhang/code/codebase-explorer/$f" ] && echo "EXISTS: $f" || echo "MISSING: $f"
done

# 运行测试
cd /Users/lexuanzhang/code/codebase-explorer && python -m pytest tests/ -x -q 2>&1 | tail -10
```

---

## Block 8 — Validation / Success Criteria（成功标准）

以下所有命令从 `/Users/lexuanzhang/code/codebase-explorer` 执行：

```bash
# === 验证 Phase 1: 旧文件已全部删除 ===

# 验证 generator.py 已删除
ls src/doc/generator.py 2>&1
# Expected: "No such file or directory"

# 验证 templates.py 已删除
ls src/doc/templates.py 2>&1
# Expected: "No such file or directory"

# 验证 _context.py 已删除
ls src/doc/_context.py 2>&1
# Expected: "No such file or directory"

# 验证 Jinja2 模板已删除
find src/templates/ -name "*.j2" | wc -l
# Expected: 0

# 验证 checkpoint.py 已删除
ls src/state/checkpoint.py 2>&1
# Expected: "No such file or directory"

# 验证 controller.py 已删除
ls src/budget/controller.py 2>&1
# Expected: "No such file or directory"

# 验证无 Jinja2 import
grep -r "import jinja2\|from jinja2\|Jinja2" src/ | grep -v test | grep -v ".pyc"
# Expected: no output

# === 验证 Phase 2: 新文件已创建 ===

# 验证 json_store.py 存在
ls src/state/json_store.py
# Expected: file exists

# 验证 feature_cone.py 存在
ls src/graph/feature_cone.py
# Expected: file exists

# 验证 weighted_graph.py 存在
ls src/graph/weighted_graph.py
# Expected: file exists

# 验证新文件可 import
python -c "from src.state.json_store import atomic_write_state, read_state; print('json_store OK')"
# Expected: "json_store OK"

python -c "from src.graph.feature_cone import extract_feature_cones, find_feature_roots; print('feature_cone OK')"
# Expected: "feature_cone OK"

python -c "from src.graph.weighted_graph import build_weighted_dependency_graph; print('weighted_graph OK')"
# Expected: "weighted_graph OK"

# === 验证 Phase 4: server.py 重建完成 ===

# 验证 server.py 有恰好 7 个工具
grep -c "^@mcp.tool" src/server.py
# Expected: 7

# 验证 server.py 无旧工具
grep "def index_codebase\|def generate_doc\|def save_checkpoint\|def load_checkpoint\|def check_budget_status\|def get_next_batch" src/server.py
# Expected: no output

# 验证 server.py 无 SQLite/Jinja2 import
grep "aiosqlite\|Database\|CheckpointManager\|DocumentGenerator\|TemplateRenderer" src/server.py
# Expected: no output

# 验证 server.py 可 import
python -c "import src.server; print('server.py OK')"
# Expected: "server.py OK"

# === 验证 Phase 4: SKILL.md 重写完成 ===

# 验证 SKILL.md 包含新工具数
grep "tools_count: 7" .agents/skills/codebase-explorer/SKILL.md
# Expected: match found

# 验证 SKILL.md 包含 5 个 Phase
grep -c "Phase [1-5]" .agents/skills/codebase-explorer/SKILL.md
# Expected: >= 5

# 验证 SKILL.md 不包含旧工具
grep "index_codebase\|generate_doc\|save_checkpoint" .agents/skills/codebase-explorer/SKILL.md
# Expected: no output

# 验证 SKILL.md 包含 3 个 Agent
grep -c "Validator Agent\|DETAIL Agent\|INDEX Agent" .agents/skills/codebase-explorer/SKILL.md
# Expected: >= 3

# === 验证 Phase 5: 测试全部通过 ===

# 运行所有测试
python -m pytest tests/ -x -q 2>&1 | tail -5
# Expected: no FAILED tests（允许 SKIP）

# 运行新增单元测试
python -m pytest tests/test_json_store.py tests/test_feature_cone.py tests/test_weighted_graph.py -v
# Expected: all PASSED

# === 最终完整验证 ===

# 验证 Python 包可正常 import
python -c "
import src.server
from src.state.json_store import atomic_write_state
from src.graph.feature_cone import extract_feature_cones
from src.graph.weighted_graph import build_weighted_dependency_graph
from src.budget.estimator import estimate_tokens_from_chars
from src.doc.depth_planner import calculate_feature_cone_depth, build_task_manifest
print('ALL IMPORTS OK')
"
# Expected: "ALL IMPORTS OK"
```

---

## Checkpoint YAML

```yaml
checkpoint:
  phase: 0
  status: ready
  current_task: INIT-01
  completed_tasks: []
  failed_tasks: []
  last_updated: "2026-03-23"
  git:
    branch: feature/codebase-explorer-impl-2026-03-22
    last_commit: ""
  notes: >
    计划已创建。Phase 0 从 INIT-01 开始，修改 __init__.py 为后续删除做准备。
    Phase 1 的 DEL 任务中注意 doc/__init__.py 和 state/__init__.py 被多个任务修改，
    需要串行执行相关任务（DEL-01 和 DEL-02 串行；DEL-05 和 DEL-07 串行）。
    Phase 2 中 NEW-02 和 NEW-03 都修改 graph/__init__.py，也需要串行。
```
