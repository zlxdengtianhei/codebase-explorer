# codebase-explorer 当前架构说明

> 本文档由 T-01 任务产出，供 T-02a / T-02b / T-02c / T-03 / T-04 只读参考。
> 禁止修改本文件。

---

## Chapter 1: 系统三层架构总览

codebase-explorer 项目实现了一个三层架构，用于生成渐进式披露的代码库架构文档。

### Layer 1: MCP Server（`src/server.py`）

当前设计让 MCP Server 同时承担三件事（过度职责）：

**正确的职责（应保留）：**
- `index_codebase()`：解析源代码、构建依赖图、运行 Louvain 分组、存储 SQLite
- `get_modules()`、`get_module_detail()`：查询模块元数据
- `estimate_module_tokens()`：估算 Token 数量
- `get_dependency_graph()`：生成 Mermaid 依赖图

**错误的职责（应迁移给 Agent）：**
- `generate_doc()`：直接调用 Jinja2 模板生成文档——**这是 LLM Agent 该做的事**
- Jinja2 模板渲染完全不涉及任何 LLM 调用，不读取源码，输出空骨架
- SQLite + 5表 + Checkpoint 系统对单 Agent 顺序流程过度复杂

### Layer 2: Skill（`.agents/skills/codebase-explorer/SKILL.md`）

定义了5个 Phase 的工作流：
- Phase 1: Index → Phase 2: Plan → Phase 3: Analyze → Phase 4: Generate → Phase 5: Validate

**Skill 假设 Phase 3 会真正阅读代码**，但实际上：
- 没有 MCP 工具支持 Agent 读取源码内容
- `submit_analysis()` 在实践中从未被正确调用（调用时传入空数据）

### Layer 3: Agent 执行层

**Skill 期望 Agent 做：**
1. 阅读源码 → 理解功能 → 调用 `submit_analysis()` 提交结构化分析
2. 根据分析结果调用 `generate_doc()` 生成有意义的文档

**实际发生的：**
- Agent 没有读取源码的工具
- `submit_analysis()` 接收空数据存入数据库
- `generate_doc()` 从数据库取空数据 → Jinja2 渲染空模板 → 输出骨架

### 核心架构违规点

**第一违规**：把"应由 LLM 做的事"（文档撰写）硬编码进了 MCP（Jinja2 模板）

**第二违规**：没有"让 Agent 读源码的工具"（缺少 `get_file_content()` 或类似工具）

**第三违规**：Phase 3（分析）和 Phase 4（生成）之间的数据管道断裂——Phase 3 的 `submit_analysis()` 存的是空数据，Phase 4 用这空数据渲染出空文档

---

## Chapter 2: MCP Server 工具清单（全部15个工具）

### 分类 A：代码库分析（5个工具）

| 工具 | 参数 | 返回 | 作用 |
|------|------|------|------|
| `index_codebase` | `path: str`, `languages: list[str] \| None` | `{project_id, file_count, function_count, class_count, module_count}` | 解析源码、构建依赖图（仅 import 边）、Louvain 分组、存入 SQLite |
| `get_modules` | `project_id?: str`, `sort_by: "name"\|"size"\|"complexity"\|"dependency"` | `{modules: list, total_modules}` | 返回所有模块的指标列表（file_count, line_count, function_count, class_count, is_utility）|
| `get_module_detail` | `module_name: str`, `project_id?: str` | `{name, files, file_count, line_count, function_count, class_count, is_utility, description, analysis}` | 返回模块记录 + 文件列表 + 如有则返回 AnalysisResult |
| `get_dependency_graph` | `scope: "project"\|"module"`, `target?: str`, `project_id?: str` | `{mermaid_graph, node_count, edge_count, circular_deps}` | 生成 Mermaid 依赖图，可以是全项目或单模块子图 |
| `estimate_module_tokens` | `module_name?: str`, `project_id?: str` | `{estimates: list, total_tokens}` | 按语言比例估算 Token（Python: 12 tokens/行，TypeScript: 15 tokens/行）|

### 分类 B：分析计划与编排（6个工具）

| 工具 | 参数 | 返回 | 作用 |
|------|------|------|------|
| `create_analysis_plan` | `project_id?: str`, `max_tokens_per_batch: int = 60000` | `{tasks: list, total_batches, total_modules}` | 按 DAG 拓扑顺序创建 AnalysisTask 记录 |
| `get_next_batch` | `project_id?: str`, `batch_size: int = 3` | `{modules: list, batch_count, progress_percent}` | 原子性地取出下一批待分析任务并标记 in_progress |
| `submit_analysis` | `module_name: str`, `description: str`, `public_interfaces: list[str]`, `key_data_structures: list[str]`, `dependencies: list[str]`, `patterns_identified: list[str]`, `detailed_analysis?: str`, `mermaid_diagram?: str`, `token_count: int`, `project_id?: str` | `{result_id, modules_completed, modules_remaining, progress_percent}` | 存储模块的结构化分析结果到 analysis_results 表 |
| `get_analysis_status` | `project_id?: str` | `{total_tasks, pending, in_progress, completed, failed, progress_percent}` | 返回任务状态汇总 |
| `check_budget_status` | `project_id?: str` | `{total_budget, used_tokens, remaining_tokens, usage_percent, should_stop, stop_reason}` | 检查是否触发了5条停止规则之一 |
| `save_checkpoint` | `phase: str`, `status: str`, `tokens_processed: int`, `metadata?: dict`, `project_id?: str` | `{checkpoint_id, analyzed_modules, pending_modules, progress_percent}` | 保存检查点供断点恢复 |

### 分类 C：上下文与交叉引用（2个工具）

| 工具 | 参数 | 返回 | 作用 |
|------|------|------|------|
| `load_checkpoint` | `checkpoint_id?: str`, `project_id?: str` | `{checkpoint_id, phase, analyzed_modules, pending_modules, module_summaries, tokens_processed}` | 恢复已保存的检查点 |
| `get_cross_ref_context` | `module_name: str`, `max_tokens: int = 2000`, `project_id?: str` | `{target_module, context: str, dependencies_resolved, context_tokens}` | 构建交叉引用上下文字符串（依赖模块的描述汇总，裁剪到 token 预算内）|

### 分类 D：文档规划与生成（2个工具）

| 工具 | 参数 | 返回 | 作用 |
|------|------|------|------|
| `plan_doc_structure` | `project_id?: str` | `{doc_tree: list[DocNode], total_docs, max_depth, depth_decisions}` | 调用三维深度规划器构建文档树，将 DocNode 记录存入 SQLite |
| `generate_doc` | `target: str`, `level: int`, `token_budget: int`, `parent_path?: str`, `children?: list[str]`, `project_id?: str` | `{path, content, actual_tokens, level, target}` | 从数据库取分析结果，填充 Jinja2 模板，裁剪到 token 预算，返回生成的文档 |

---

## Chapter 3: 代码分析层实现

### 3.1 解析层：`src/parser/codebase.py`

**`CodebaseParser.parse()` 返回 `CodebaseSnapshot`：**

```python
@dataclass(frozen=True)
class CodebaseSnapshot:
    root_path: str
    languages_detected: frozenset[str]  # {"python", "typescript", ...}
    files: tuple[FileInfo, ...]
    functions: tuple[FunctionInfo, ...]
    classes: tuple[ClassInfo, ...]
    total_lines: int
```

**`FileInfo` 关键字段：**
- `filepath`: 绝对路径
- `language`: "python" | "typescript" | "javascript"
- `line_count`: 文件行数
- `function_names`: 函数名列表
- `class_names`: 类名列表
- `import_sources`: **已解析的文件路径**列表（该文件 import 了哪些文件）

**`FunctionInfo` 关键字段：**
- `filepath`: 所在文件
- `name`: 函数名
- `dependencies`: 该函数调用的其他文件路径列表（graph-sitter 调用图分析）

### 3.2 依赖图：`src/graph/dependency.py`

**`build_dependency_graph()` 构建 NetworkX DiGraph：**
- **节点**：源文件路径（每个文件一个节点）
- **边（来源1）**：`file.import_sources` 中的 import 关系（权重 1）
- **边（来源2）**：跨文件的 `func.dependencies` 函数调用（部分使用）

**⚠️ 关键遗漏（当前实现只用 import 边）：**
- ❌ 未使用继承关系（`class.base_classes`）
- ❌ 未使用跨文件函数调用图
- ❌ 未区分 import 权重、调用权重、继承权重

### 3.3 模块分组：`src/graph/grouper.py`

**Louvain 社区检测流程：**
1. 识别高入度节点（入度 > 10% × 总节点数）→ 标记为 utility
2. 将有向图转为无向图（**丢失方向信息**）
3. 运行 Louvain → `{file_path: community_id}` 映射
4. 按社区 ID 分组文件 → 模块
5. 命名：取目录前缀或 PageRank 最高文件名（当前实现可能命名为 `module_0`）

**⚠️ 问题：**
- 高入度节点被粗暴移除而不是保留为"共享组件"
- 有向图转无向图丢失了依赖方向
- 命名不反映语义（`module_0`、`module_7`）

### 3.4 模块排序：`src/graph/ordering.py`

**拓扑排序用于确定分析顺序：**
1. 构建模块级 DAG（节点=模块，边=跨模块依赖）
2. `nx.condensation()` 压缩强连通分量（SCC）处理循环依赖
3. 计算 PageRank → 层内优先级排序
4. Kahn 算法生成分层列表：`[[layer0_modules], [layer1], ...]`

### 3.5 Token 估算：`src/budget/estimator.py`

**两种估算方法：**

```python
# 方法1：行数乘以系数（模块级，误差较大 ±50%）
TOKENS_PER_LINE = {"python": 12, "typescript": 15, "javascript": 15}
estimated_tokens = line_count * TOKENS_PER_LINE[language]

# 方法2：字符数除以系数（文件级，更准确）
CHARS_PER_TOKEN = {"python": 3.5, "typescript": 4.0, "javascript": 3.8}
estimated_tokens = char_count / CHARS_PER_TOKEN[language]
```

### 3.6 预算控制：`src/budget/controller.py`

**5条停止规则：**
1. 总预算 >= 95% 耗尽 → `budget_exhausted`
2. 单个模块超过每模块上限（默认 10K tokens）→ `module_over_limit`
3. 运行时间超过限制（默认 15 分钟）→ `time_limit_exceeded`
4. 连续失败次数超过阈值（默认 3 次）→ `consecutive_failures`
5. 所有模块已完成 → `all_modules_completed`

---

## Chapter 4: 文档生成层实现

### 4.1 动态深度规划器：`src/doc/depth_planner.py`

**三维深度引擎：最终深度 = max(三个维度)**

#### 维度1：结构深度（基于子包数量）

```python
_STRUCTURAL_THRESHOLDS = [
    (0, 0),   # 0 个子包 → depth 0
    (2, 1),   # ≤2 → depth 1
    (5, 2),   # ≤5 → depth 2
    (10, 3),  # ≤10 → depth 3
    (20, 4),  # ≤20 → depth 4
    # >20 → depth 5
]
```

#### 维度2：复杂度深度（函数/类/行数加权）

```python
score = function_count * 1.0 + class_count * 3.0 + line_count / 100.0 + cyclomatic * 2.0
_COMPLEXITY_THRESHOLDS = [
    (10.0, 0),   # score < 10 → depth 0
    (30.0, 1),   # score < 30 → depth 1
    (100.0, 2),  # score < 100 → depth 2
    (300.0, 3),  # score < 300 → depth 3
    (600.0, 4),  # score < 600 → depth 4
    # >= 600 → depth 5
]
```

#### 维度3：Token 深度（基于估算 Token 数）

```python
_TOKEN_THRESHOLDS = [
    (500, 0),       # < 500 → depth 0
    (2_000, 1),     # < 2K → depth 1
    (8_000, 2),     # < 8K → depth 2
    (32_000, 3),    # < 32K → depth 3
    (128_000, 4),   # < 128K → depth 4
    # >= 128K → depth 5
]
```

#### 最终深度计算与约束

```python
raw_depth = max(structural_depth, complexity_depth, token_depth)

# 约束1：utility 模块最多 depth 2
if module_name.startswith("_utilities"):
    raw_depth = min(raw_depth, 2)

# 约束2：极小模块强制 depth 0（合并到父节点）
if line_count < 100 and function_count < 5:
    raw_depth = 0

# 约束3：小模块约束（< 10 组件 AND < 200 行 → depth ≤ 1）
total_components = function_count + class_count
if raw_depth >= 2 and total_components < 10 and line_count < 200:
    raw_depth = 1

return min(raw_depth, MAX_DEPTH)  # MAX_DEPTH = 5
```

### 4.2 文档树构建：`src/doc/_tree_builder.py`

**从模块计划构建 DocPlanNode 扁平列表：**

1. 过滤出活跃模块（`plan.should_merge_parent == False`）
2. 创建 Level 0 INDEX 节点：`{path: "INDEX.md", level: 0, children: [所有 OVERVIEW 路径]}`
3. 对每个活跃模块创建 Level 1 OVERVIEW 节点
4. 根据分割策略创建 Level 2 DETAIL 节点：
   - SUBPACKAGE → `{module}/sub_0/DETAIL.md`, `sub_1/DETAIL.md`, ...
   - CLASS → `{module}/class_0/DETAIL.md`, ...
   - FUNCTION_GROUP → `{module}/group_0/DETAIL.md`, ...
   - FILE（fallback）→ `{module}/file_0/DETAIL.md`, ...

### 4.3 文档生成器：`src/doc/generator.py`

**`generate_doc()` 是纯 Jinja2 模板渲染器：**

```python
def generate_doc(node, analysis_result, cross_ref_context, children_summaries):
    # 1. 从数据库取 AnalysisResult（通常是空数据）
    # 2. 构建 Jinja2 上下文（以 analysis_result 的字段填充）
    # 3. 选模板：level=0 → index.md.j2，level=1 → overview.md.j2，level≥2 → detail.md.j2
    # 4. 渲染 → 裁剪到 token_budget → 返回 GeneratedDocument
```

**⚠️ 关键事实：这个函数：**
- ❌ 不调用任何 LLM
- ❌ 不读取任何源码文件
- ❌ 不使用 `submit_analysis()` 传入的分析数据（因为数据是空的）
- ✓ 只是把数据库中的（空）结构填入 Jinja2 模板

### 4.4 SQLite 数据库：`src/state/database.py`

**5张数据库表：**

| 表名 | 主要字段 | 用途 |
|------|---------|------|
| `projects` | id, path, created_at, status, languages, file_count, total_lines | 项目元数据 |
| `modules` | id, project_id, name, files(JSON), file_count, line_count, is_utility | Louvain 分组结果 |
| `analysis_tasks` | id, project_id, module_name, status, batch_index, created_at | 分析任务队列 |
| `analysis_results` | id, task_id, project_id, module_name, description, public_interfaces(JSON), key_data_structures(JSON), dependencies(JSON), detailed_analysis, mermaid_diagram, token_count | 分析结果（通常为空）|
| `doc_nodes` | id, project_id, path, level, target, token_budget, parent_path, children_paths(JSON), content, actual_tokens, status | 文档树节点 |

---

## Chapter 5: Skill 工作流（5-Phase）

### Phase 1: Index

**调用链：**
```
index_codebase(path)
  → CodebaseParser.parse()         [graph-sitter 解析]
  → build_dependency_graph()       [只用 import 边，DiGraph]
  → group_modules(Louvain)         [有向图→无向图→社区检测]
  → INSERT projects, modules       [存入 SQLite]
  → 返回 project_id
```

### Phase 2: Plan

**调用链：**
```
get_modules(project_id)            [列出模块]
create_analysis_plan(project_id)   [拓扑排序 → AnalysisTask 队列]
plan_doc_structure(project_id)     [三维深度 → DocPlanNode 列表 → doc_nodes 表]
```

### Phase 3: Analyze（设计 vs 现实）

**Skill 期望：**
```
循环直到完成：
  get_next_batch(batch_size=3)     → 获取待分析模块
  [Agent 读取源码 — 无 MCP 工具！]
  get_cross_ref_context()          → 获取依赖模块描述
  submit_analysis(module_name, description, interfaces, ...)  → 存分析结果
  check_budget_status()            → 检查是否停止
```

**⚠️ 实际发生：**
- 没有 MCP 工具支持 Agent 读取源码内容
- `submit_analysis()` 被调用但传入空数据
- 数据库中存储空的 `AnalysisResult`

### Phase 4: Generate（接收空数据）

```
对每个 doc_node（按层级从下到上）：
  generate_doc(target, level, token_budget)
    → SELECT * FROM analysis_results  [取到空数据]
    → BUILD Jinja2 context            [上下文全为空字符串/空列表]
    → RENDER 模板                     [输出空骨架]
    → TRIM to budget
    → 写入 .codebase-docs/
```

### Phase 5: Validate

实际验证结果（来自 e2e_validation_report.md）：

| 指标 | 实际值 | 阈值 | 状态 |
|------|--------|------|------|
| 文件覆盖率 | 0% (0/24) | ≥90% | ❌ FAIL |
| 模块覆盖率 | 66.7% (2/3) | ≥80% | ❌ FAIL |
| 链接有效率 | 14.8% (9/61) | 100% | ❌ FAIL |
| Token 预算合规 | 100% | ≥90% | ✅ PASS |
| 动态深度最大值 | 2 | ≥2 | ✅ PASS |
| 动态深度最小值 | 1（全部=2，无=1）| 有模块保持1 | ❌ FAIL |
| 孤立文档 | 16/22 | 0 | ❌ FAIL |

---

## Chapter 6: 完整数据流

```
用户请求
    ↓
Phase 1: INDEX
  index_codebase(path)
    → CodebaseSnapshot: {files: [FileInfo], functions: [FunctionInfo], classes: [ClassInfo]}
    → DependencyGraphResult: nx.DiGraph（仅 import 边）
    → GroupingResult: {modules: {"core": ("a.py","b.py"), ...}, modularity_score}
    → SQLite: INSERT projects (project_id), INSERT modules × N
    ↓
Phase 2: PLAN
  create_analysis_plan()
    → topological_order(): [["layer0_modules"], ["layer1"], ...]
    → SQLite: INSERT analysis_tasks × N (status="pending")
  plan_doc_structure()
    → ModuleMetrics × N
    → DocumentPlan × N: {depth, split_strategy, doc_budget_per_level}
    → [DocPlanNode × M]: INDEX.md + OVERVIEW.md × k + DETAIL.md × j
    → SQLite: INSERT doc_nodes × M (status="planned")
    ↓
Phase 3: ANALYZE（断裂处）
  get_next_batch() → [module_name × 3]
  submit_analysis(module_name, description="", public_interfaces=[], ...)   ← 空数据！
    → SQLite: INSERT analysis_results (description="", ...)
    → UPDATE analysis_tasks SET status="completed"
    ↓
Phase 4: GENERATE（接收空数据）
  generate_doc(target="core", level=1, token_budget=1200)
    → SELECT analysis_results WHERE module_name="core"  ← 取到空记录
    → Jinja2 context: {module: {description: "", interfaces: []}}  ← 全空
    → render overview.md.j2  ← 输出空骨架
    → trim_to_budget()
    → 写入 core/OVERVIEW.md  ← Token 使用率仅 5-29%
    ↓
Phase 5: VALIDATE
  → 链接断裂：52/61（相对路径生成错误，缺少 ../）
  → 覆盖率 0%：doc-index.json 的 source_files 字段未填充
  → 内容空洞：analysis_results 全为空数据
  → 总体：FAIL
```

---

## Chapter 7: E2E 失败问题清单

### 失败1：链接断裂（52/61 = 85%）

**症状：** 生成文档中的 Markdown 链接使用了错误的相对路径。

**示例：**
```markdown
# 错误：
[Project Overview](INDEX.md)       # 在 module_0/OVERVIEW.md 中
# 正确应该是：
[Project Overview](../INDEX.md)    # 需要向上一级
```

**根因：** `src/doc/_context.py` 中的 `make_relative_link()` 函数没有根据文档所在目录深度正确计算 `../` 前缀数量。

### 失败2：文件覆盖率 0%

**症状：** `doc-index.json` 中 `source_files` 字段为空。

**根因：** `src/doc/_context.py` 中的 `build_doc_index()` 函数没有将 `source_files` 列表写入 JSON 输出。`generator.py` 中虽然有 `source_files = module_files.get(doc_node.target, [])` 的代码，但这个值没有被传递到 `build_doc_index()`。

### 失败3：深度动态性不足（所有模块 depth=2，无 depth=1）

**症状：** `module_7`（6函数 + 2类 = 8个组件）应触发小模块约束保持 depth=1，但实际生成了 `group_0/DETAIL.md`（depth=2）。

**根因：** `depth_planner.py` 的小模块约束条件（`total_components < 10 AND line_count < 200`）在代码中逻辑正确，但可能 `module_7` 的实际行数 >= 200，或约束在 `_tree_builder.py` 构建文档树时没有被正确传递（`calculate_depth()` 的结果被传入但 `_tree_builder.py` 忽略了 depth=1 的决策，仍然创建了 DETAIL 子节点）。

### 失败4：内容空洞（Token 使用率仅 5-29%）

**症状：** DETAIL.md 只有结构骨架，无实际代码说明内容。

**根因（两部分）：**

1. **Phase 3 从未真正分析代码：** 没有工具让 Agent 读取源码内容，`submit_analysis()` 传入空数据，数据库中存储空 `AnalysisResult`

2. **Jinja2 模板不含任何 LLM 调用：** `generate_doc()` 只是用空数据填模板，无法产生代码语义理解内容

**核心问题一句话：**
> `generate_doc()` 是纯 Jinja2 渲染，不是 LLM 文档生成。真正的文档撰写责任在 Agent 层，但 Agent 没有读取源码的工具，导致整个生成流水线产出空骨架。

---

## 可保留的组件清单

| 组件 | 文件 | 状态 | 说明 |
|------|------|------|------|
| graph-sitter 解析层 | `parser/` | ✅ 保留 | 核心解析能力不变 |
| Louvain 分组算法 | `graph/grouper.py` | ✅ 保留，改角色 | 从主力变为辅助（处理扁平目录）|
| DAG 拓扑排序 | `graph/ordering.py` | ✅ 保留 | 分析顺序计算正确 |
| Token 估算 | `budget/estimator.py` | ✅ 保留，改算法 | 改用字符数/4 |
| Mermaid 图生成 | `doc/mermaid.py` | ✅ 保留 | |
| 三维深度算法核心逻辑 | `doc/depth_planner.py` | ⚠️ 改造 | 替换为 DAG 分层 + Token 预算 |
| Jinja2 文档生成 | `doc/generator.py` | ❌ 删除 | 文档由 Agent 撰写 |
| SQLite 状态管理 | `state/` | ❌ 大幅精简 | 改为 JSON 文件 |
| Checkpoint 系统 | `state/checkpoint.py` | ❌ 删除 | 每步输出文件即为断点 |
| generate_doc 工具 | `server.py` | ❌ 删除 | 文档生成是 Agent 的事 |
