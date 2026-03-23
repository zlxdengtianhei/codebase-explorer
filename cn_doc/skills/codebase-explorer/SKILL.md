---
name: codebase-explorer
description: >-
  分析代码库结构，并使用 MCP 工具生成渐进式披露架构文档。自动索引代码库，
  通过 Louvain 社区检测对模块进行分组，并生成动态 N 层文档
  （INDEX、OVERVIEW、DETAIL），其深度根据模块复杂度自适应调整。
  当用户希望了解代码库架构、生成文档、探索模块依赖关系或可视化代码结构时使用。
  也可通过以下关键词触发："架构文档"、"模块概览"、"代码地图"、"依赖图"、
  "代码库分析"或"生成文档"。
version: 1.0.0
license: MIT
compatibility:
  - claude-code
  - codex
  - opencode
  - gemini-cli
mcp_server: codebase-explorer
tools_count: 15
---

# Codebase Explorer（代码库探索器）

分析代码结构并生成渐进式架构文档。
生成动态 N 层文档——从单页项目索引到组件级内部细节——
其深度根据每个模块的复杂度自动调整。小型工具模块只需一个概览；
大型子系统则需要 4-5 层详细说明。

## 使用场景

在以下情况使用本 Skill：

- 用户希望了解陌生代码库的结构
- 用户要求提供架构文档或模块概览
- 用户需要可视化模块之间的依赖关系
- 用户提到"代码地图"、"依赖图"、"架构文档"
- 新团队成员需要入职文档
- 在大型重构之前，需要了解影响范围

**不应使用**的情况：

- 用户只想查看或编辑单个文件（使用常规工具即可）
- 用户想要某个库的 API 参考文档（使用官方文档）
- 代码库只是一个文件或脚本（< 100 行）

## 前置条件

codebase-explorer MCP 服务器必须正在运行。通过调用
`get_analysis_status` 来验证——如果调用失败，请告知用户启动服务器：

```
uv run python -m codebase_explorer.server
```

## 快速开始

1. **安装**：`uv add codebase-explorer` 或在 `.mcp.json` 中配置
2. **配置**：将 `assets/doc-config.yaml` 复制到项目根目录（可选）
3. **运行**：告诉 Agent "分析这个代码库"，或使用 `/codebase-explorer`

## 工作流程

整个工作流程分为 5 个阶段。每个阶段产生具体的输出，作为下一阶段的输入。
请按顺序执行这些阶段。

### 阶段一：索引

**目标**：从源文件构建代码图谱。

1. 调用 `index_codebase(path=<repo_path>)`
2. 通过 `get_analysis_status` 检查进度，直到 `status: "success"`
3. 记录 `project_id`，供所有后续调用使用
4. 向用户报告摘要统计信息（文件数、函数数、类数、语言）

**质量门控**：继续前须确认 `status: "success"`。

### 阶段二：规划

**目标**：发现模块，创建分析计划，并规划文档结构。

1. 调用 `get_modules(sort_by="dependency")` 获取 Louvain 分组的模块
2. 向用户展示模块列表；确认分组是否可接受
3. 调用 `create_analysis_plan()` 按拓扑依赖顺序生成分块分析任务
4. 调用 `plan_doc_structure()` 构建文档树

文档结构规划器使用**动态深度引擎**来决定每个模块的文档深度。
这不是固定的 3 层——深度由三个因素决定：

```
depth = max(structural_depth, complexity_depth, token_depth)
```

- **结构深度**：基于子包数量（0 = 平铺，5 = 20+ 子包）
- **复杂度深度**：基于函数/类数量和圈复杂度
- **Token 深度**：基于估计的源码 Token 数量

结果：小型模块获得深度 0-1（合并或单一概览），复杂子系统获得
深度 3-5，带有递归的 DETAIL 文档。

**质量门控**：用户确认模块分组。分析计划已创建。

### 阶段三：分析

**目标**：分析每个模块并提交结构化结果。

循环执行，直到所有模块分析完成：

1. 调用 `get_next_batch(batch_size=3)` 获取下一批模块
2. 对批次中每个模块：
   a. 调用 `get_cross_ref_context(module_name)` 获取依赖摘要
   b. 读取源文件并分析模块
   c. 调用 `submit_analysis(module_name, description, public_interfaces,
   key_data_structures, dependencies, patterns_identified, ...)`
3. 调用 `check_budget_status(used_tokens, modules_completed)` 决定
   是继续还是保存检查点
4. 如果 `should_stop: true`，调用 `save_checkpoint(phase="module_analysis")`，
   之后通过 `load_checkpoint()` 恢复

**检查点规则**：每分析 3 个模块，保存进度并验证中间结果。
长时间会话有上下文窗口溢出的风险——频繁保存可防止丢失工作。

**质量门控**：所有模块均已提交分析结果。

### 阶段四：生成

**目标**：按照规划的树形结构生成文档。

按 `plan_doc_structure()` 返回的文档树处理文档，
从叶节点到根节点自底向上生成：

1. 对每个文档节点（按层级自底向上）：
   a. 调用 `generate_doc(target, level, token_budget, parent_path, children)`
   b. 验证返回的 `actual_tokens` 是否在 `token_budget` 范围内
   c. 将内容写入输出目录下的指定路径
2. 生成 `doc-index.json`，对所有文档进行汇总

**Token 预算强制执行**——当内容超出预算时，按以下顺序裁剪：

| 优先级    | 内容类型            | 操作     |
| --------- | ------------------- | -------- |
| 1（保留） | 名称、签名、描述    | 始终包含 |
| 2         | 依赖关系、架构图    | 高优先级 |
| 3         | 类/函数详情、数据流 | 中优先级 |
| 4         | 实现说明、示例      | 优先裁剪 |

**质量门控**：所有规划文档均在 Token 预算内生成完毕。

### 阶段五：验证

**目标**：验证文档质量。

1. 调用 `get_analysis_status()` 确认所有任务已完成
2. 验证链接完整性：每个 `[文本](路径)` 链接均可解析
3. 验证 Token 预算：每个文档均在其分配的预算内
4. 检查覆盖率：文档化模块数 / 总模块数 >= 80%
5. 向用户展示最终摘要：
   - 生成的文档总数
   - 覆盖率百分比
   - 总 Token 数
   - 使用的最大深度
   - 任何差距或问题

**质量标准**（参见 [QUALITY_STANDARDS.md](references/QUALITY_STANDARDS.md)）：

| 指标               | 阈值                   |
| ------------------ | ---------------------- |
| 模块覆盖率         | >= 80%                 |
| 链接有效性         | 100%                   |
| Token 预算合规率   | >= 90% 的文档在预算内  |
| Mermaid 图表存在性 | 每个 OVERVIEW 都有一个 |

## 动态深度功能

文档深度**不是固定的**。深度规划器独立评估每个模块，
并根据其指标分配深度 0-5：

| 深度 | 含义              | 适用场景                             |
| ---- | ----------------- | ------------------------------------ |
| 0    | 仅摘要            | 合并到父文档（< 100 行，< 5 个函数） |
| 1    | 仅 OVERVIEW       | 小型模块（< 500 行）                 |
| 2    | OVERVIEW + DETAIL | 中型模块（500-2000 行）              |
| 3    | 三层嵌套          | 复杂模块（2000+ 行，有子包）         |
| 4    | 四层嵌套          | 大型子系统（5000+ 行）               |
| 5    | 最大深度          | 框架级模块（10000+ 行）              |

更深层级的拆分策略：

- **SUBPACKAGE（子包）**：按子目录拆分（当有 2+ 个均衡子包时首选）
- **CLASS（类）**：按类拆分（适用于 OOP 风格，有 3+ 个类）
- **FUNCTION_GROUP（函数组）**：按函数簇拆分（函数式风格）
- **FILE（文件）**：按单个文件拆分（兜底方案）

低于最小可文档化阈值的单元（30 行、2 个函数、200 Token）
将合并到父文档，而非单独生成文件。

## MCP 工具快速参考

详细参数请参见 [MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md)。

| #   | 工具                     | 用途                                      |
| --- | ------------------------ | ----------------------------------------- |
| 1   | `index_codebase`         | 解析代码库，构建依赖图，运行 Louvain 分组 |
| 2   | `get_modules`            | 列出自动检测到的模块及其指标              |
| 3   | `get_module_detail`      | 获取单个模块的文件、接口、依赖关系        |
| 4   | `get_dependency_graph`   | 获取 Mermaid 依赖关系图（项目或模块范围） |
| 5   | `estimate_module_tokens` | 估算模块的 Token 数量                     |
| 6   | `create_analysis_plan`   | 按 DAG 顺序生成分块分析任务               |
| 7   | `check_budget_status`    | 检查 Agent 是否应停止并保存进度           |
| 8   | `get_next_batch`         | 获取下一批待分析模块                      |
| 9   | `submit_analysis`        | 提交模块的结构化分析结果                  |
| 10  | `get_analysis_status`    | 获取整体进度和任务状态                    |
| 11  | `save_checkpoint`        | 保存分析检查点以便会话恢复                |
| 12  | `load_checkpoint`        | 恢复检查点以继续上一次会话                |
| 13  | `get_cross_ref_context`  | 从依赖摘要构建交叉引用上下文              |
| 14  | `plan_doc_structure`     | 使用动态深度决策规划文档树                |
| 15  | `generate_doc`           | 使用 Jinja2 模板生成单个文档              |

## 配置

默认配置位于 [assets/doc-config.yaml](assets/doc-config.yaml)。
复制到项目根目录可覆盖默认值：

```yaml
output_dir: .codebase-docs
max_depth: 5
budget:
  total_tokens: 50000
  max_per_module: 10000
depth:
  min_lines_for_split: 200
  min_components_for_split: 15
  decay_factor: 0.6
```

## 错误恢复

**索引失败**：检查路径是否为绝对路径且目录存在。
尝试使用明确的 `languages` 过滤参数。

**Token 预算超出**：以缩减范围重新调用 `generate_doc`。
遵循基于优先级的裁剪原则（保留接口，裁剪示例）。

**检查点恢复**：调用 `load_checkpoint()` 以恢复。检查点包含
已分析模块和待处理队列——不会重复工作。

**任务声明冲突**：另一个 Agent 已锁定该模块。
跳过批次中的其他模块。

## 参考文件

仅在需要详细规范时加载这些文件：

- [WORKFLOW_DETAIL.md](references/WORKFLOW_DETAIL.md) — 带有 MCP 调用示例的扩展步骤说明
- [MCP_TOOLS_REFERENCE.md](references/MCP_TOOLS_REFERENCE.md) — 所有 15 个工具的完整参数和返回值规范
- [DOC_TEMPLATES.md](references/DOC_TEMPLATES.md) — Jinja2 模板变量列表、输出示例、Token 预算指南
- [QUALITY_STANDARDS.md](references/QUALITY_STANDARDS.md) — 覆盖率、链接有效性、Token 合规性和深度验证标准
