> **Context 恢复协议**：如果你在 Context 压缩后读到此文件，
> 1. 查看"执行进度"区块，确认当前进度（[x] 已完成，[ ] 待执行）
> 2. **调用 `/od` skill** 继续执行此计划
> 3. `/od` 会从首个 [ ] 任务继续，按其 workflow 自主执行
>
> **恢复后必须调用 `/od` skill，不要自己直接开始工作。**

# Plan: feature-cone-algorithm-optimization

**Date**: 2026-03-25
**Project**: codebase-explorer `/Users/lexuanzhang/code/codebase-explorer`
**Plan file**: `/Users/lexuanzhang/code/codebase-explorer/.claude_plans/2026-03-25-feature-cone-algorithm-optimization.md`

---

## Vision Constraint（愿景约束）【Block 0 — 传递给每个 Sub-agent】

> 以下内容从用户原始需求中提取，是整个执行链的不可变约束。
> /od 在构建每个 Sub-agent prompt 时，必须将此区块完整复制到 `## Vision` 中。

```yaml
Vision:
  original_prompt: |
    去根据网络上或者大家综合评价很好的一个代码库，它的代码量肯定要比 Flask 多很多，
    但也不至于多到太夸张，是一个相对比较大的项目。最重要的是，这个项目要有一个清晰的
    架构体系，就是你完全能了解到它的架构具体是怎么设计的。然后在这种代码库中，请你把
    它作为 Test Repo 去跑一下"通过边来进行分类"的这个功能。去检查一下效果：它分类
    出来的结果和模块，跟架构本身的模块是否一致、是否类似。

    最终目标是要贴合原有的代码架构，并尽量符合语义化的模块分类。但因为代码本身可能
    缺乏语义，不能强求完全准确。对于无法分类的地方，让每个 Agent 总结其分类情况和
    结果。最终再启动一个 Agent，让它根据所有结果进行思考，评估当前算法继续优化的
    可能性，从而给出更好的分类效果。

    在具体优化的时候，检测函数之间的依赖关系，那个东西应该是一个开源的实现。我希望
    你做的，就是尽量完整、最大化地利用这些现有的资源。如果现有的开源项目已经有一些
    成熟的实现，请你直接使用它们，而不是重新不断地造轮子去尝试。
  hard_constraints:
    - MCP Server 保持纯确定性（零 LLM 调用），不得在 MCP 层引入任何 AI 模型
    - 676 个现有测试不得被破坏（uv run python -m pytest tests/ 全部通过）
    - 不得修改 MCP 工具的对外接口签名（7 个 @mcp.tool 保持不变）
    - 优先使用现有开源工具，不重复造轮子
    - 每步改动后必须跑测试验证，不得积累未验证的代码
    - Python >=3.10 兼容性
  done_from_user_perspective: |
    用户在 Rich/FastAPI/Scrapy/Celery 四个测试项目上运行 analyze_codebase，
    得到的 Feature Cone 分组结果与各项目的真实架构模块高度匹配：
    - 均分从当前 48.5 提升至 72+
    - 核心模块（如 Scrapy 的 Engine/Downloader/Spider/Middleware）被正确识别为独立 Cone
    - Infrastructure 文件检测准确（不过度提升功能模块，不遗漏核心 hub）
    - 不再出现 206 cone / 161 file 的超碎片化现象
    - Cone 命名有语义意义（不再出现 cli-1..9, api-1..4, __init__-1..4）
```

---

## Context（背景）

### 为何存在

Feature Cone 算法在四个真实项目上的实测评分不理想（均分 48.5/100），暴露了 7 个跨项目根因。本计划旨在系统性修复这些问题，将算法准确率提升至纯静态分析的理论天花板（~78 分）附近。

### 前置工作

1. **四项目实测**：Rich (65)、FastAPI (34)、Scrapy (60)、Celery (35)
2. **综合分析**：Opus Agent 产出的 7 个根因 + 三阶段路线图 + 参数调优建议
3. **算法代码深度分析**：feature_cone.py 943 行、所有函数/参数/行号
4. **开源工具调研**：17 个工具评估（pyan3、grimp、astroid 等）
5. **专项研究**：`__init__.py` facade 检测、pytest 测试发现模式、动态 import AST 检测

### 开源工具实用性评估

| 工具 | 评估结论 | 使用方式 |
|------|---------|---------|
| **pyan3** | 有 call graph 提取 + MRO 继承解析，但自称"superficial"，且 Python >=3.10 only | **参考其 AST 遍历思路**，自建简化版 call graph 提取（我们只需函数名→文件映射，不需 MRO） |
| **grimp** | 最佳 import graph API（Rust 核心），但要求包可被 import（不适合分析任意 repo） | **不使用**——我们已有 import 解析（含 relative import 修复），grimp 的约束不符合场景 |
| **astroid** | 最强 AST 推理引擎（pylint 底层），但依赖重、部分推理需执行代码 | **不使用**——太重，我们要纯静态分析。参考其 ClassDef.bases 遍历模式 |
| **NetworkX PageRank/betweenness** | 已是项目依赖，一行代码即可用 | **直接使用**——hub 检测用 `nx.pagerank()` 和 `nx.in_degree_centrality()` |
| **leidenalg** | 比 Louvain 更好（保证连通社区），但需额外依赖 igraph | **不引入**——现有 Louvain fallback 足够，优先优化主算法而非 fallback |

### 约束

- 每个 Phase 结束后：`uv run python -m pytest tests/ -x -q` 必须全部通过
- 不引入新的 pip 依赖（仅使用 stdlib ast + 已有的 networkx）
- 改动不得影响 MCP 工具的 JSON 输出格式

### 执行预算

```
执行预算:
  预估总任务数: 14
  预估每任务耗时: 15 分钟
  预估总耗时: 210 分钟 (~3.5 小时)
  Context 窗口评估: 需要 /clear 中断，按 Phase 分段执行
```

---

## Execution Progress（执行进度）

### Phase 1 — Quick Wins（参数调优 + 前置过滤 + 合并策略）
- [x] T-01: 测试文件前置过滤 → agent: tdd-guide → 产出物: `feature_cone.py` 修改 + 新测试
- [x] T-02: shared_threshold 公式改为次线性 → agent: tdd-guide → 产出物: `feature_cone.py` 修改 + 新测试
- [x] T-03: `__init__.py` facade 检测与降权 → agent: tdd-guide → 产出物: `semantic_hints.py` + `feature_cone.py` 修改
- [x] T-04: Package 层级 orphan 合并 → agent: tdd-guide → 产出物: `feature_cone.py` `_merge_orphan_cones()` 重构
- [x] T-05: Phase 1 四项目回归验证 → agent: e2e-runner → 产出物: 验证报告

### Phase 2 — 核心增强（Call Graph + 自适应参数）
- [x] T-06: AST Call Graph 提取（参考 pyan3 思路） → agent: tdd-guide → 产出物: `codebase.py` 修改
- [x] T-07: AST 跨文件继承边提取 → agent: tdd-guide → 产出物: `codebase.py` 修改
- [x] T-08: 动态 import 启发式检测 → agent: tdd-guide → 产出物: `codebase.py` 修改
- [x] T-09: 自适应 Affinity 参数（基于图特征） → agent: tdd-guide → 产出物: `feature_cone.py` 修改
- [x] T-10: Phase 2 四项目回归验证 → agent: e2e-runner → 产出物: 验证报告

### Phase 3 — Hub 检测 + Cone 命名优化
- [x] T-11: Hub 节点预标记（in-degree centrality） → agent: tdd-guide → 产出物: `feature_cone.py` 修改
- [x] T-12: Cone 命名改进（消除 cli-1..9、__init__-1..4 模式） → agent: tdd-guide → 产出物: `feature_cone.py` 修改

### Phase 4 — 验证 + 审查
- [x] T-13: 全量测试 + 四项目最终评分 → agent: e2e-runner → 产出物: 最终评分报告
- [x] T-14: 代码审查 → agent: code-reviewer → 产出物: 审查报告（1 CRITICAL fix applied: empty exclusive_files guard）

---

## Agent Responsibility Matrix（Agent 职责矩阵）

| Task ID | 描述 | Skill / Agent | 输入 | 输出产物 |
|---------|------|---------------|------|---------|
| T-01 | 测试文件前置过滤 | tdd-guide | feature_cone.py, semantic_hints.py | 修改后的 feature_cone.py + tests |
| T-02 | shared_threshold 次线性公式 | tdd-guide | feature_cone.py | 修改后的 feature_cone.py + tests |
| T-03 | __init__.py facade 检测降权 | tdd-guide | semantic_hints.py, feature_cone.py | 两文件修改 + tests |
| T-04 | Package 层级 orphan 合并 | tdd-guide | feature_cone.py | _merge_orphan_cones 重构 + tests |
| T-05 | Phase 1 四项目验证 | e2e-runner | test_repos/{rich,fastapi,scrapy,celery} | 评分报告 |
| T-06 | AST Call Graph 提取 | tdd-guide | codebase.py, pyan3 参考 | 修改后的 codebase.py + tests |
| T-07 | AST 跨文件继承边 | tdd-guide | codebase.py | 修改后的 codebase.py + tests |
| T-08 | 动态 import 检测 | tdd-guide | codebase.py | 修改后的 codebase.py + tests |
| T-09 | 自适应 Affinity 参数 | tdd-guide | feature_cone.py, weighted_graph.py | 修改后的 feature_cone.py + tests |
| T-10 | Phase 2 四项目验证 | e2e-runner | test_repos/* | 评分报告 |
| T-11 | Hub 节点预标记 | tdd-guide | feature_cone.py | 修改后的 feature_cone.py + tests |
| T-12 | Cone 命名改进 | tdd-guide | feature_cone.py | 修改后的 feature_cone.py + tests |
| T-13 | 最终全量验证 | e2e-runner | 全部源码 + test_repos/* | 最终评分报告 |
| T-14 | 代码审查 | code-reviewer | Phase 1-3 所有修改文件 | 审查报告 |

---

### 任务规格

#### T-01 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`extract_feature_cones()` 函数，约第 325 行后）
  - 修改: `tests/test_feature_cone.py`（新增测试用例）
  - 禁止修改: `src/server.py`（属全局集成，不在此任务范围）
- **预期日志**: 测试中可验证：给定含测试文件的 DAG，过滤后 root 数减少且 shared_threshold 降低
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 新测试覆盖：含 test 文件的 DAG 过滤后 root 数 < 过滤前
  - [ ] 过滤逻辑使用 `classify_file()` 的 "testing" 分类
  - [ ] 过滤仅影响 root 发现和 threshold 计算，不删除测试文件的 DAG 节点
- **回滚策略**:
  - 回滚点: Phase 1 入口 (`git stash`)
  - 替代方案: 用目录模式匹配 (`tests/`, `test/`, `t/`) 替代 `classify_file()`
  - 丢弃条件: 过滤导致非测试文件误删
- **超时**: 10 分钟
- **Sub-agent 所需背景**:
  本项目是一个 MCP Server，通过静态分析将代码库按功能分组为 "Feature Cone"。核心算法在 `src/graph/feature_cone.py`。

  **当前问题**：`find_feature_roots()` (第 110-138 行) 将所有 in-degree=0 的节点标记为 feature root，包括测试文件。Celery 有 255 个测试文件作为 root，导致 `compute_shared_threshold()` (第 60-69 行) 计算出 threshold=77（`max(2, round(255*0.3))`），几乎没有文件能达到此阈值被标记为 infrastructure。

  **修复方案**：在 `extract_feature_cones()` 第 325 行的 `roots = find_feature_roots(dag)` 之后，调用 `classify_file()` 过滤掉 testing 类 root，再计算 threshold。注意：
  1. 只过滤 root 列表，不从 DAG 中删除测试节点（测试文件仍参与 BFS）
  2. 如果过滤后 root 为空，回退到未过滤的 root（防止全 test 项目）
  3. pytest 标准模式：`test_*.py`, `*_test.py`, 目录 `tests/`, `test/`, `t/`, 文件 `conftest.py`

  **参考文件**：
  - `src/graph/feature_cone.py` 第 60-69 行 (`compute_shared_threshold`)
  - `src/graph/feature_cone.py` 第 110-138 行 (`find_feature_roots`)
  - `src/graph/feature_cone.py` 第 293-397 行 (`extract_feature_cones` 主流程)
  - `src/graph/semantic_hints.py` 第 102-138 行 (`classify_file` — 已有 "testing" 分类)

---

#### T-02 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`compute_shared_threshold()` 函数，第 60-69 行）
  - 修改: `tests/test_feature_cone.py`
  - 禁止修改: `src/server.py`
- **预期日志**: 测试验证：sqrt-based threshold 对不同 root 数的输出符合预期
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 新公式：`max(2, round(math.sqrt(n_roots) * 1.2))` — 50 roots → threshold=9（而非 15）
  - [ ] 参数化测试覆盖 n_roots = 5, 10, 20, 50, 100, 200
- **回滚策略**:
  - 回滚点: T-01 完成后
  - 替代方案: `max(2, round(math.log2(n_roots) * 2))`
  - 丢弃条件: 新公式导致 Rich 的 infrastructure 检测崩溃
- **超时**: 8 分钟
- **Sub-agent 所需背景**:
  `compute_shared_threshold()` 在 `src/graph/feature_cone.py` 第 60-69 行。当前公式 `max(2, round(n_roots * 0.3))` 是线性的，大项目上 threshold 过高（200 roots → threshold=60）。一个文件被 12 个 cone 共享已足以认定为 infrastructure，不需要 60 个。

  **改为次线性公式**：`max(2, round(math.sqrt(n_roots) * 1.2))`

  验证值：5→3, 10→4, 20→6, 50→9, 100→12, 200→17

  **参考文件**: `src/graph/feature_cone.py` 第 60-69 行

---

#### T-03 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/semantic_hints.py`（新增 `is_reexport_facade()` 函数）
  - 修改: `src/graph/feature_cone.py`（`_affinity_bfs()` 第 146-187 行，添加 facade 降权）
  - 修改: `tests/test_semantic_hints.py`, `tests/test_feature_cone.py`
  - 禁止修改: `src/parser/codebase.py`（属 T-06/T-07/T-08）
- **预期日志**: 测试验证：facade `__init__.py` 的出边 affinity 被惩罚 0.3x
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] `is_reexport_facade(filepath, root_path)` 函数存在且有单元测试
  - [ ] facade 判定标准：relative_imports / (relative_imports + definitions) > 0.8
  - [ ] `_affinity_bfs()` 中 facade 节点的出边 affinity 额外乘以 0.3
  - [ ] 非 facade 的 `__init__.py`（如含大量 def/class）不受影响
- **回滚策略**:
  - 回滚点: T-02 完成后
  - 替代方案: 简化版——所有 `__init__.py` 统一降权 0.5x（不检测 facade）
  - 丢弃条件: facade 检测误判率 > 20%
- **超时**: 15 分钟
- **Sub-agent 所需背景**:
  FastAPI 的 `fastapi/__init__.py` 是典型的 re-export facade——它只做 `from .applications import FastAPI`、`from .routing import APIRouter` 等 re-export，没有实际逻辑。当前 BFS 从 root 经过这种 facade 时，会一跳到达所有被 re-export 的模块，制造 mega-cone。

  **facade 检测逻辑**（参考 ruff F401 和 mypy --no-implicit-reexport）：
  ```python
  def is_reexport_facade(filepath: str, root_path: str) -> bool:
      if not filepath.endswith("__init__.py"):
          return False
      source = Path(root_path, filepath).read_text()
      tree = ast.parse(source)
      relative_imports = sum(1 for n in ast.walk(tree)
          if isinstance(n, ast.ImportFrom) and n.level and n.level > 0)
      definitions = sum(1 for n in ast.walk(tree)
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
      total = relative_imports + definitions
      return total > 0 and (relative_imports / total) > 0.8
  ```

  **BFS 降权**：在 `_affinity_bfs()` 第 170 行附近，检查当前节点是否为 facade，如果是则 edge_affinity *= 0.3。

  **参考文件**:
  - `src/graph/semantic_hints.py`（新增函数放这里）
  - `src/graph/feature_cone.py` 第 146-187 行 (`_affinity_bfs`)
  - FastAPI 的 `test_repos/fastapi/fastapi/__init__.py`（测试用例）

---

#### T-04 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`_merge_orphan_cones()` 第 624-685 行）
  - 修改: `tests/test_feature_cone.py`
  - 禁止修改: `src/graph/semantic_hints.py`（属 T-03）
- **预期日志**: 测试验证：同一 Python package 下的小 cone（≤2 文件）被合并
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 合并范围从 parent directory 扩展到 Python package（含 `__init__.py` 的目录）
  - [ ] 不仅合并单文件 cone，也合并 ≤2 文件的小 cone
  - [ ] 合并后单个 cone 不超过 15 个文件（防止过度合并）
  - [ ] 测试用例覆盖：同 package 多个小 cone 合并、跨 package 不合并、上限限制
- **回滚策略**:
  - 回滚点: T-03 完成后
  - 替代方案: 仅扩展合并到 ≤2 文件 cone，不改变 package 层级
  - 丢弃条件: 合并导致功能不同的模块被强行合并
- **超时**: 12 分钟
- **Sub-agent 所需背景**:
  当前 `_merge_orphan_cones()` 只合并**同一 parent directory 下的单文件 cone**。这导致 Scrapy 的 `commands/` 目录产生 9 个独立的 cli cone（cli-1 到 cli-9），Celery 的 `backends/` 产生 22 个独立 cone。

  **改进方案**：
  1. 合并粒度：从 parent directory 扩展到 Python package（向上查找到包含 `__init__.py` 的最近目录）
  2. 合并门槛：不仅合并单文件 cone，也合并 ≤2 文件的小 cone（`SMALL_CONE_THRESHOLD = 2`）
  3. 上限保护：合并后单 cone 不超过 `MAX_MERGED_CONE_SIZE = 15` 个文件

  **参考文件**:
  - `src/graph/feature_cone.py` 第 624-685 行 (`_merge_orphan_cones`)
  - `src/graph/semantic_hints.py` 第 141-189 行 (`directory_affinity_score` — 可参考但不强制使用)

---

#### T-05 规格
- **Skill**: agent: e2e-runner
- **操作范围**:
  - 读取: `test_repos/{rich,fastapi,scrapy,celery}`, 全部 `src/` 源码
  - 创建: 无（仅输出报告）
  - 禁止修改: 任何源码文件
- **预期日志**: 四个项目的评分报告
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0（现有测试无回归）
  - [ ] 四项目均成功运行 analyze pipeline（无异常）
  - [ ] 输出对比表：每个项目的 cone 数、infrastructure 数、单文件 cone 比例、与真实架构匹配度
  - [ ] Phase 1 目标：均分从 48.5 提升至 ≥58
- **回滚策略**:
  - 回滚点: Phase 1 入口
  - 替代方案: N/A（验证任务）
  - 丢弃条件: N/A
- **超时**: 15 分钟
- **Sub-agent 所需背景**:
  本任务是 Phase 1 的验证步骤。T-01 到 T-04 已完成了四项优化（测试过滤、threshold 公式、facade 降权、package 合并）。现在需要在四个测试项目上运行完整的分析管道，验证改进效果。

  **运行方式**：对每个 repo 运行以下 Python 代码（以 Scrapy 为例）：
  ```python
  import sys; sys.path.insert(0, '/Users/lexuanzhang/code/codebase-explorer')
  from src.parser.codebase import CodebaseParser
  from src.graph.dependency import DependencyGraphBuilder
  from src.graph.feature_cone import FeatureConeExtractor
  repo = 'test_repos/scrapy'
  parser = CodebaseParser(repo)
  files, funcs, classes, total_lines = parser.parse()
  source_files = [f for f in files if f.filepath.startswith('scrapy/')]
  builder = DependencyGraphBuilder()
  graph = builder.build(source_files, funcs, classes)
  extractor = FeatureConeExtractor(graph)
  cones = extractor.extract()
  # 统计 cone 数、infrastructure 数、单文件 cone 比例
  ```

  **评分维度**（每个项目）：
  1. Infrastructure 检测准确率
  2. 核心模块分组准确率（与已知架构对比）
  3. 碎片化程度（cone 数 / 文件数比率）
  4. catch-all cone 大小

  **对比基线**：Rich=65, FastAPI=34, Scrapy=60, Celery=35（均分 48.5）

  **已知的各项目真实架构模块**：
  - Rich: console(hub), text, style, segment, progress, theme, tree, layout, markdown
  - FastAPI: routing, applications, dependencies, security, openapi, middleware, cli, params, encoders
  - Scrapy: engine, scheduler, downloader, spiders, spider_middlewares, downloader_middlewares, extensions, pipelines, selectors, commands, http, settings
  - Celery: app, worker, backends, concurrency, beat, canvas, result, security, events, bin, loaders

---

#### T-06 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/parser/codebase.py`（`_fallback_parse_python` 和 `_ast_extract_function`）
  - 修改: `tests/test_parser.py`
  - 禁止修改: `src/graph/feature_cone.py`（属 T-09/T-11/T-12）
  - 禁止修改: `src/graph/weighted_graph.py`（此任务只改 parser，weighted_graph 自动拾取新数据）
- **预期日志**: 测试验证：解析后 FunctionInfo.calls 非空，weighted_graph 产生 call 边 (weight=2)
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] `_ast_extract_function()` 返回的 `calls` 字段包含被调用的函数名列表
  - [ ] `_fallback_parse_python()` 构建 `func_name_to_file` 映射并用于解析 call targets
  - [ ] FunctionInfo.dependencies 字段包含被调用函数所在的文件路径
  - [ ] 测试用例：跨文件函数调用被正确解析为 dependency 边
- **回滚策略**:
  - 回滚点: Phase 2 入口
  - 替代方案: 集成 pyan3 作为可选依赖（`try: import pyan3; except: fallback`）
  - 丢弃条件: call graph 提取导致解析时间增加 > 5x
- **超时**: 20 分钟
- **Sub-agent 所需背景**:
  当前 AST fallback parser 的 `_ast_extract_function()` (第 375-393 行) 返回 `calls=()` 和 `dependencies=()`——完全为空。这导致 `weighted_graph.py` 无法生成 call 边 (weight=2)，所有边都是 import 边 (weight=1)。import 边的 affinity 只有 0.3，导致 BFS 在 2 跳后被剪枝。

  **实现方案**（参考 pyan3 的 AST 遍历思路，但简化版）：

  1. 在 `_fallback_parse_python()` 中构建 `func_name_to_file: dict[str, str]` 映射：
     - 遍历所有已解析的函数，记录 `{func_name: filepath}`
     - 对于重名函数，标记为 ambiguous 并跳过（与 weighted_graph.py 现有策略一致）

  2. 在 `_ast_extract_function()` 中提取函数调用：
     - 遍历函数体 AST，收集所有 `ast.Call` 节点
     - 对于 `ast.Name` 类型的调用（如 `foo()`），记录函数名
     - 对于 `ast.Attribute` 类型的调用（如 `self.foo()`），记录属性名
     - 不需要解析 `self.obj.method()` 这种链式调用（太复杂，收益有限）

  3. 在 `_fallback_parse_python()` 的第二遍中，用 `func_name_to_file` 解析 calls → dependencies：
     - 第一遍：收集所有函数定义 → 建立映射
     - 第二遍：重新遍历所有函数体，用映射解析 call targets → 填充 dependencies

  **注意**：不需要做类型推理或 MRO 解析——简单的函数名匹配已经能捕获大部分 call 关系。pyan3 的 MRO 解析太复杂，我们不需要。

  **参考文件**:
  - `src/parser/codebase.py` 第 375-393 行 (`_ast_extract_function`)
  - `src/parser/codebase.py` 第 232-327 行 (`_fallback_parse_python` 主流程)
  - `src/graph/weighted_graph.py` 第 139-146 行（call 边生成——已实现，只需 parser 提供数据）
  - pyan3 的 AST 遍历思路参考：`https://github.com/Technologicat/pyan` — 它遍历函数体内的 `ast.Call` 并通过名称解析到定义文件

---

#### T-07 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/parser/codebase.py`（`_ast_extract_class` 和 `_fallback_parse_python`）
  - 修改: `tests/test_parser.py`
  - 禁止修改: `src/graph/weighted_graph.py`（自动拾取新数据）
- **预期日志**: 测试验证：ClassInfo.base_classes 正确解析，weighted_graph 产生 inherit 边 (weight=3)
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 跨文件继承关系被正确解析（如 `class MySpider(Spider)` → dependency on spider.py）
  - [ ] 解析使用 `class_name_to_file` 映射，歧义类名被跳过
  - [ ] 测试用例：跨文件继承产生 weight=3 的边
- **回滚策略**:
  - 回滚点: T-06 完成后
  - 替代方案: 仅依赖 T-06 的 call graph，不实现继承边
  - 丢弃条件: 继承解析导致大量误报（>30% 错误边）
- **超时**: 12 分钟
- **Sub-agent 所需背景**:
  `_ast_extract_class()` (第 396-418 行) 已经提取了 `base_classes`，但 `_fallback_parse_python()` 没有用这些信息建立跨文件继承关系。

  **实现方案**：
  1. 在 `_fallback_parse_python()` 的第一遍中构建 `class_name_to_file` 映射（与 T-06 类似）
  2. 第二遍中，遍历每个 ClassInfo 的 base_classes，通过映射解析到文件路径
  3. 将继承关系添加到 FileInfo 的 import_sources 中（或创建新的 inheritance_sources 字段）

  **注意**：`weighted_graph.py` 第 97-115 行和 148-156 行已有继承边处理逻辑——它使用 `class_name_to_file` 查表生成 weight=3 边。所以 parser 只需确保 `ClassInfo.base_classes` 中的类名能在项目内部找到对应文件即可。当前问题是很多类名（如 `BaseModel`、`Exception`）是外部类，映射中找不到就被跳过了——这是正确行为。

  **参考文件**:
  - `src/parser/codebase.py` 第 396-418 行 (`_ast_extract_class`)
  - `src/graph/weighted_graph.py` 第 97-115 行（class_name_to_file 构建）
  - `src/graph/weighted_graph.py` 第 148-156 行（继承边生成）

---

#### T-08 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/parser/codebase.py`（`_fallback_parse_python` 内添加动态 import 检测）
  - 修改: `tests/test_parser.py`
  - 禁止修改: `src/graph/` 下任何文件
- **预期日志**: 测试验证：`importlib.import_module("celery.backends.redis")` 被解析为 import 边
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 检测 `importlib.import_module("string_literal")` 模式
  - [ ] 检测 `__import__("string_literal")` 模式
  - [ ] 非字符串字面量参数被安全忽略
  - [ ] 检测到的动态 import 被添加到 FileInfo.import_sources
- **回滚策略**:
  - 回滚点: T-07 完成后
  - 替代方案: 仅检测 `import_module`，不检测 `__import__`
  - 丢弃条件: 动态 import 检测产生大量误报
- **超时**: 10 分钟
- **Sub-agent 所需背景**:
  Scrapy 和 Celery 大量使用 `importlib.import_module()` 加载 backend、middleware、extension。这些运行时动态导入在 AST 层面不可见，导致依赖图缺失大量边。

  **实现方案**（已有现成 AST 代码）：
  ```python
  # 在 _fallback_parse_python() 的 per-file AST 遍历中添加
  for node in ast.walk(tree):
      if not isinstance(node, ast.Call):
          continue
      func = node.func
      # importlib.import_module("module.path")
      if (isinstance(func, ast.Attribute) and func.attr == "import_module"
          and isinstance(func.value, ast.Name) and func.value.id in ("importlib",)):
          if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
              resolved = module_map.get(node.args[0].value)
              if resolved:
                  import_sources.append(resolved)
      # __import__("module.path")
      elif isinstance(func, ast.Name) and func.id == "__import__":
          if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
              resolved = module_map.get(node.args[0].value)
              if resolved:
                  import_sources.append(resolved)
  ```

  **参考文件**: `src/parser/codebase.py` 第 262-311 行（现有 import 提取逻辑——动态 import 追加到同一个 import_sources 列表）

---

#### T-09 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`_affinity_bfs` 和新增 `_compute_adaptive_params` 函数）
  - 修改: `tests/test_feature_cone.py`
  - 禁止修改: `src/parser/codebase.py`（属 T-06/T-07/T-08）
- **预期日志**: 测试验证：AST fallback 模式（call 边 <10%）自动提升 import affinity
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 新增 `_compute_adaptive_params(dag)` 函数
  - [ ] 当 call+inherit 边占比 < 10% 时，import affinity 从 0.3 提升到 0.5
  - [ ] 当图密度 < 0.02 时，AFFINITY_CUTOFF 从 0.08 降至 0.05
  - [ ] 原始常量保留为默认值，自适应仅在特定条件下覆盖
  - [ ] 测试覆盖：稀疏图、密集图、混合边类型
- **回滚策略**:
  - 回滚点: Phase 2 入口
  - 替代方案: 固定参数调优（直接改常量值）而非自适应
  - 丢弃条件: 自适应参数导致某项目评分下降 > 5 分
- **超时**: 15 分钟
- **Sub-agent 所需背景**:
  当前 `EDGE_AFFINITY`、`AFFINITY_CUTOFF` 等参数是硬编码常量（第 39-57 行），对所有项目使用相同值。但不同项目的图特征差异很大：
  - FastAPI: 48 节点、95 边（全部 import）、密度 0.04
  - Celery: 161 节点、稀疏
  - Rich: 76 节点、星形拓扑

  **自适应规则**：
  ```python
  def _compute_adaptive_params(dag: nx.DiGraph) -> dict:
      edges = list(dag.edges(data=True))
      total = len(edges)
      if total == 0:
          return {"edge_affinity": EDGE_AFFINITY, "cutoff": AFFINITY_CUTOFF}

      call_inherit_count = sum(1 for _, _, d in edges if d.get("weight", 1) >= 2)
      call_ratio = call_inherit_count / total

      density = nx.density(dag)

      adaptive_affinity = dict(EDGE_AFFINITY)
      adaptive_cutoff = AFFINITY_CUTOFF

      if call_ratio < 0.1:  # AST fallback mode
          adaptive_affinity[1] = 0.5  # 提升 import 权重
      if density < 0.02:  # 稀疏图
          adaptive_cutoff = 0.05

      return {"edge_affinity": adaptive_affinity, "cutoff": adaptive_cutoff}
  ```

  **参考文件**:
  - `src/graph/feature_cone.py` 第 39-57 行（当前参数定义）
  - `src/graph/feature_cone.py` 第 146-187 行 (`_affinity_bfs` — 需要接受参数而非读全局常量)

---

#### T-10 规格
- **Skill**: agent: e2e-runner
- **操作范围**: 读取全部源码和 test_repos，输出报告，不修改文件
- **验收标准**:
  - [ ] 现有测试全部通过
  - [ ] 四项目评分输出
  - [ ] Phase 2 目标：均分 ≥ 66
- **超时**: 15 分钟
- **Sub-agent 所需背景**: 同 T-05，但对比基线改为 Phase 1 的评分结果。

---

#### T-11 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`extract_feature_cones` 中添加 PageRank 预标记）
  - 修改: `tests/test_feature_cone.py`
  - 禁止修改: `src/parser/codebase.py`, `src/graph/weighted_graph.py`
- **预期日志**: 测试验证：高 PageRank 节点被预标记为 infrastructure
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] 使用 `nx.pagerank(dag)` + `nx.in_degree_centrality(dag)` 计算 hub 分数
  - [ ] Top N 节点（N 由图大小决定，如 `max(3, int(len(dag) * 0.05))`）预标记为 infrastructure
  - [ ] 预标记在 BFS 之前执行，预标记节点不参与 cone 归属
  - [ ] 测试覆盖：星形图中心节点被正确识别为 hub
- **回滚策略**:
  - 回滚点: Phase 3 入口
  - 替代方案: 仅用 in-degree > 2x median 作为 hub 标准（已有类似逻辑）
  - 丢弃条件: PageRank 预标记导致功能模块核心文件被误提升为 infra
- **超时**: 12 分钟
- **Sub-agent 所需背景**:
  当前 infrastructure 检测发生在 BFS 之后（第 342-344 行 shared_threshold + 第 369-371 行 high fan-in promotion），但对于 FastAPI 这类小项目，BFS 到达的节点太少，shared_threshold 机制失效。

  **改进**：在 BFS 之前使用 NetworkX 的 PageRank 和 in-degree centrality 预标记 hub 节点。
  ```python
  pagerank = nx.pagerank(dag)
  in_degree_cent = nx.in_degree_centrality(dag)
  # 综合得分
  hub_score = {n: pagerank[n] * 0.5 + in_degree_cent[n] * 0.5 for n in dag}
  # Top N 预标记
  n_hubs = max(3, int(len(dag) * 0.05))
  sorted_hubs = sorted(hub_score.items(), key=lambda x: x[1], reverse=True)
  pre_infra = {n for n, _ in sorted_hubs[:n_hubs]}
  ```

  **注意**：预标记的节点从 DAG 中保留（其他节点仍能引用它们），但在 cone 归属阶段排除——它们直接进入 infrastructure_nodes 集合。

  **参考文件**:
  - `src/graph/feature_cone.py` 第 293-397 行 (`extract_feature_cones` 主流程)
  - `src/graph/feature_cone.py` 第 195-286 行 (`_promote_high_fanin_to_infrastructure`)
  - NetworkX 文档：`nx.pagerank()`, `nx.in_degree_centrality()`

---

#### T-12 规格
- **Skill**: agent: tdd-guide
- **操作范围**:
  - 修改: `src/graph/feature_cone.py`（`_generate_cone_name` 第 751-793 行）
  - 修改: `src/graph/semantic_hints.py`（扩展 `classify_file` 的分类 categories）
  - 修改: `tests/test_feature_cone.py`, `tests/test_semantic_hints.py`
  - 禁止修改: `src/parser/codebase.py`
- **预期日志**: 测试验证：cone 名称不再出现 `__init__-N` 或 `cli-N` 模式
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0
  - [ ] `classify_file` 新增 categories：middleware, security, utils/helpers, exceptions
  - [ ] `_generate_cone_name` 优先使用最深公共目录名而非 `__init__` 文件名
  - [ ] 同目录多 cone 使用语义后缀（如 `security-auth`, `security-base`）而非数字后缀
  - [ ] 测试用例：`__init__.py` 开头的文件不再产生 `__init__-N` 名称
- **回滚策略**:
  - 回滚点: T-11 完成后
  - 替代方案: 仅修改命名逻辑，不扩展 classify_file categories
  - 丢弃条件: 命名改变导致下游 Skill 的 DETAIL/INDEX 生成出错
- **超时**: 12 分钟
- **Sub-agent 所需背景**:
  当前 `_generate_cone_name()` (第 751-793 行) 使用 `classify_file()` 查找主导分类，fallback 使用公共目录前缀或第一个文件 stem。问题：
  1. `classify_file` 只有 5 个 category（testing, models, api, cli, config），88% 文件分类为 "unknown"
  2. 当 cone 的入口文件是 `__init__.py` 时，名称变成 `__init__`，多个同名产生 `__init__-1..4`

  **改进**：
  1. 在 `semantic_hints.py` 中扩展 categories（注意保持 `classify_file` 的 first-match-wins 逻辑）：
     - "middleware": stem patterns `middleware`, `middlewares`; dir patterns `middleware/`, `middlewares/`
     - "security": stem patterns `security`, `auth`, `permissions`; dir patterns `security/`, `auth/`
     - "utils": stem patterns `utils`, `helpers`, `common`, `shared`, `lib`; dir patterns `utils/`, `helpers/`
     - "exceptions": stem patterns `exceptions`, `errors`
  2. 在 `_generate_cone_name()` 中，如果最佳名称是 `__init__`，替换为其 parent directory 名称

  **参考文件**:
  - `src/graph/feature_cone.py` 第 751-793 行 (`_generate_cone_name`)
  - `src/graph/semantic_hints.py` 第 14-88 行（现有 category 定义）

---

#### T-13 规格
- **Skill**: agent: e2e-runner
- **操作范围**: 读取全部源码和 test_repos，输出最终报告
- **验收标准**:
  - [ ] `uv run python -m pytest tests/ -x -q` 退出码 0，676+ 测试全部通过
  - [ ] 四项目最终评分均 ≥ 60
  - [ ] 四项目均分 ≥ 72
  - [ ] 无 catch-all cone 超过总文件数的 40%
  - [ ] 无项目出现 cone 数 > 文件数的超碎片化
- **超时**: 15 分钟
- **Sub-agent 所需背景**: 同 T-05/T-10，但这是最终验证。对比基线是原始评分（48.5）和各阶段中间结果。

---

#### T-14 规格
- **Skill**: agent: code-reviewer
- **操作范围**: 读取 Phase 1-3 修改的所有文件
- **验收标准**:
  - [ ] 0 个 CRITICAL 级别问题
  - [ ] 0 个 HIGH 级别问题
  - [ ] MEDIUM 级别问题 ≤ 5 个
- **超时**: 10 分钟
- **Sub-agent 所需背景**:
  本轮修改涉及 Feature Cone 算法优化，主要改动文件：
  - `src/graph/feature_cone.py` — 核心算法（测试过滤、threshold 公式、facade 降权、package 合并、自适应参数、hub 预标记、命名改进）
  - `src/graph/semantic_hints.py` — 语义分类（facade 检测、新 categories）
  - `src/parser/codebase.py` — AST parser（call graph、继承边、动态 import）

  **审查重点**：
  1. 不可变模式（coding-style.md 要求）：确保所有新函数返回新对象而非修改输入
  2. 函数长度 < 50 行
  3. 参数边界验证（空图、空 root 列表）
  4. 测试覆盖 ≥ 80%

---

## Parallel Execution Map（并行执行图）

```
并行组 A（同时启动，最多 2 个）：T-01, T-02
  依赖：无
  约束：T-01 修改 extract_feature_cones 函数，T-02 修改 compute_shared_threshold 函数
        两者在 feature_cone.py 中的修改位置不重叠
  最大并行数：2

串行步骤：T-03
  依赖：T-01 + T-02（因为 T-03 修改 _affinity_bfs，需要先确认 root 过滤和 threshold 正常工作）
  原因：T-03 的 facade 降权逻辑在 _affinity_bfs 中，需确保 T-01 的过滤不影响 facade 判定

串行步骤：T-04
  依赖：T-03（T-04 修改 _merge_orphan_cones，与 T-03 同在 feature_cone.py，需串行防止冲突）
  原因：两者都修改 feature_cone.py 的不同函数，但需要稳定基线

串行步骤：T-05
  依赖：T-04（验证 Phase 1 全部改动的综合效果）
  原因：必须观测 T-01~T-04 的全部效果

---

并行组 B（同时启动，最多 2 个）：T-06, T-07
  依赖：T-05（Phase 1 验证通过后才开始 Phase 2）
  约束：两者都修改 codebase.py 但 T-06 改 _ast_extract_function，T-07 改 _ast_extract_class
        修改位置不重叠
  最大并行数：2

串行步骤：T-08
  依赖：T-06 + T-07（T-08 的动态 import 检测在同一文件的 import 提取循环中）
  原因：需要 T-06/T-07 的代码稳定后再在同一文件追加改动

串行步骤：T-09
  依赖：T-08（自适应参数需要新的 edge type 分布数据来验证规则）
  原因：T-09 的自适应逻辑依赖 call/inherit 边的存在来判断 AST fallback 模式

串行步骤：T-10
  依赖：T-09（验证 Phase 2 全部改动）
  原因：必须观测 T-06~T-09 的综合效果

---

并行组 C（同时启动，最多 2 个）：T-11, T-12
  依赖：T-10（Phase 2 验证通过后才开始 Phase 3）
  约束：T-11 修改 extract_feature_cones 的 BFS 前逻辑
        T-12 修改 _generate_cone_name 和 semantic_hints
        修改位置不重叠
  最大并行数：2

串行步骤：T-13
  依赖：T-11 + T-12（最终全量验证）
  原因：必须观测全部改动效果

串行步骤：T-14
  依赖：T-13（代码审查在验证通过后）
  原因：审查需要观测最终代码状态
```

---

## File Decomposition（文件拆解）

| 文件路径 | 操作 | 所属任务 | 负责 Agent |
|---------|------|---------|-----------|
| `src/graph/feature_cone.py` | MODIFY | T-01, T-02, T-04, T-09, T-11, T-12 | tdd-guide |
| `src/graph/semantic_hints.py` | MODIFY | T-03, T-12 | tdd-guide |
| `src/parser/codebase.py` | MODIFY | T-06, T-07, T-08 | tdd-guide |
| `tests/test_feature_cone.py` | MODIFY | T-01, T-02, T-03, T-04, T-09, T-11, T-12 | tdd-guide |
| `tests/test_semantic_hints.py` | MODIFY | T-03, T-12 | tdd-guide |
| `tests/test_parser.py` | MODIFY | T-06, T-07, T-08 | tdd-guide |

**受保护文件（不得修改）：**
- `src/server.py` — 原因: MCP 工具接口不得变更，集成层不在本优化范围
- `src/server_helpers.py` — 原因: 输出格式不得变更
- `src/graph/weighted_graph.py` — 原因: 已正确处理 call/inherit 边，只需 parser 提供数据
- `src/graph/dependency.py` — 原因: 基础 graph builder 不需改动
- `src/state/` — 原因: 状态管理不在本优化范围
- `src/doc/` — 原因: 文档生成不在本优化范围
- `src/budget/` — 原因: Token 预算不在本优化范围

---

## Phase Structure（阶段结构）

### Phase 1 — Quick Wins（参数调优 + 前置过滤 + 合并策略）
**入口条件**: 计划已获用户确认
**任务**: T-01 + T-02（并行），T-03（串行），T-04（串行），T-05（验证）
**退出条件**: T-05 验证通过，四项目均分 ≥ 58，现有 676 测试全部通过

### Phase 2 — 核心增强（Call Graph + 自适应参数）
**入口条件**: Phase 1 完成
**任务**: T-06 + T-07（并行），T-08（串行），T-09（串行），T-10（验证）
**退出条件**: T-10 验证通过，四项目均分 ≥ 66

### Phase 3 — Hub 检测 + Cone 命名优化
**入口条件**: Phase 2 完成
**任务**: T-11 + T-12（并行），T-13（最终验证）
**退出条件**: T-13 验证通过，四项目均分 ≥ 72

### Phase 4 — 审查
**入口条件**: Phase 3 完成
**任务**: T-14（代码审查）
**退出条件**: 0 个 CRITICAL/HIGH 问题

---

## Checkpoint（检查点）

```yaml
phase: 1
current_task: T-01
status: ready
last_updated: 2026-03-25T00:00:00Z
completed: []
pending: [T-01, T-02, T-03, T-04, T-05, T-06, T-07, T-08, T-09, T-10, T-11, T-12, T-13, T-14]
blocked: []
fix_loop_count: 0
current_fix_target: null
escalated: []
```

---

## Experiment Log（实验日志）

| Task | Attempt | Commit | 方案 | 关键指标 | Status | 描述 |
|------|---------|--------|------|---------|--------|------|

> **由 /od 在执行过程中填写。/op 初始化时此表为空。**

---

## Validation / Success Criteria（成功标准）

满足以下**全部**条件时，任务才算完成：

- [ ] `uv run python -m pytest tests/ -x -q` 退出码 0，676+ 测试全部通过
- [ ] Rich 评分 ≥ 65（不低于基线）
- [ ] FastAPI 评分 ≥ 60（从 34 大幅提升）
- [ ] Scrapy 评分 ≥ 72（从 60 提升）
- [ ] Celery 评分 ≥ 55（从 35 大幅提升）
- [ ] 四项目均分 ≥ 72
- [ ] 代码审查 0 个 CRITICAL/HIGH 问题
- [ ] 无新增 pip 依赖
- [ ] MCP 工具对外接口签名未变
- [ ] 执行进度中的所有任务已标记为 [x]
