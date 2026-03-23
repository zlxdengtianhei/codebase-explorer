# 当前问题诊断

> 主题：现有实现的 E2E 测试结果分析、过度工程诊断、流程错误和可保留部分。

---

## 1. E2E 测试结果分析

测试输出位于 `test_repos/flask/.codebase-docs/`，包含 22 个文档。

### 文档结构

```
test_repos/flask/.codebase-docs/
├── INDEX.md                          # L0: 项目概览
├── doc-index.json                    # 全局索引（339行，22个记录）
├── _utilities/ → OVERVIEW + DETAIL
├── json/ → OVERVIEW + DETAIL
├── module_0/ → OVERVIEW + DETAIL
├── module_6/ → OVERVIEW + DETAIL
├── module_7/ → OVERVIEW（无DETAIL，小模块）
└── sansio/ → OVERVIEW + 8个 DETAIL
```

### 4 类系统性问题

| 问题                     | 严重度 | 原因                                                                |
| ------------------------ | ------ | ------------------------------------------------------------------- |
| 链接断裂（52/61 broken） | 🔴 P0  | 文档生成器用绝对路径而非相对路径                                    |
| 文件覆盖率 0%            | 🔴 P0  | `doc-index.json` 的 `source_files` 未被正确读取匹配                 |
| 深度动态性不足           | 🟡 P1  | `module_7`（6函数2类）应 depth=1 但实际 depth=2；小模块约束未被触发 |
| 内容空洞                 | 🟡 P1  | DETAIL 只有结构骨架，无真实代码内容（token 使用率仅 5-29%）         |

### 深度问题详解

- `module_7` 有 6函数+2类=8 components，符合 `< 10` 的小模块约束
- `depth_planner.py` 代码逻辑**应该**将其限制为 depth=1
- 但实际输出中 `module_7` 有 `group_0/DETAIL.md`（depth=2）
- 说明 `calculate_depth()` 的结果未被正确传递到文档树构建

---

## 2. 过度工程诊断

### 🔴 架构层：三件事混在一个 MCP Server

```
当前设计（一个 Server 做三件事）：
MCP Server
├── 代码解析层 (graph-sitter → NetworkX)
├── 任务调度层 (SQLite WAL + 互斥 + checkpoint)
└── 文档生成层 (depth_planner + Jinja2 + generate_doc)

正确拆法：
MCP Server（纯数据）→ Skill/Agent（做决策）
```

### 🔴 状态管理过度

- SQLite WAL + 5 个表 + checkpoint 系统
- 实际上 Skill 是顺序调用 MCP 工具的单 Agent 流程
- **一个简单的 JSON 文件就够了**

### 🟡 预算控制过度包装

- `AnalysisBudgetController` + 5 条停止规则
- 本质上是"一个数字和几个 if 语句"

### 🟡 15 个工具冗余

- `get_module_detail` 和 `get_cross_ref_context` 本质上都是"查已分析结果"，可合并

---

## 3. 流程错误：跳过了 LLM 分析

### 实际发生的流程

```
index_codebase() ← graph-sitter 解析 Flask
      ↓
plan_doc_structure() ← depth_planner 决定深度
      ↓
generate_doc() ← Jinja2 直接生成文档      ⚠️ submit_analysis() 被跳过！
      ↓
写入 .codebase-docs/
```

### 问题

1. graph-sitter 的解析结果存入了数据库
2. 但**没有任何 Agent 真正读源码并理解它**
3. `generate_doc()` 直接用模板生成骨架
4. → DETAIL 文件 token 使用率只有 5-29%，全是结构骨架无实际内容

### 正确的流程

```
MCP Server 职责（确定性，无 LLM）：
─ index_codebase() → 文件列表、函数/类列表、依赖图
─ get_modules() → Louvain 分组结果
─ get_dependency_graph() → Mermaid 依赖关系图

Skill/Agent 职责（LLM 决策）：
─ 读取 graph-sitter 的原始输出
─ 真正阅读源码，理解模块功能
─ 调用 submit_analysis() 提交理解结果
─ 根据 plan_doc_structure() 生成有意义的文档
```

---

## 4. depth_planner.py 的算法问题

### 当前做法

```python
depth = max(
    threshold_table(subpackage_count),          # 结构深度
    threshold_table(函数*1 + 类*3 + 行数/100),  # 复杂度深度
    threshold_table(estimated_tokens),           # Token深度
)
```

用三张查表来"猜"深度——而代码本身已经有答案了。

### 问题对比

| 维度         | 当前 depth_planner   | 正确做法                         |
| ------------ | -------------------- | -------------------------------- |
| 深度来源     | 三张阈值表（人工猜） | 依赖方向天然产生                 |
| 主要聚类     | 仅 Louvain           | 目录树 + Louvain 混合            |
| 图信息利用   | 只统计边数           | SCC + 继承链 + 凝聚度 + PageRank |
| Token 估算   | 行数 × 15（±50%）    | 字符数 ÷ 4（更准确）             |
| utility 节点 | 移除                 | 保留，标记为"共享组件"           |
| 结果命名     | module_0             | PageRank 最高文件名或目录名      |

---

## 5. 可保留部分

| 组件                                    | 状态            | 说明                           |
| --------------------------------------- | --------------- | ------------------------------ |
| graph-sitter 解析层（`parser/`）        | ✅ 保留         | 核心解析能力不变               |
| Louvain 分组算法（`graph/`）            | ✅ 保留但改角色 | 从主力变为辅助（处理扁平目录） |
| 三维深度计算（`depth_planner.py` 核心） | ❌ 替换         | 用 DAG 分层 + Token 预算替代   |
| Token 估算（`budget/estimator.py`）     | ✅ 保留但改算法 | 改用字符数/4                   |
| DAG 拓扑排序（`graph/ordering.py`）     | ✅ 保留         |                                |
| Mermaid 图生成（`doc/mermaid.py`）      | ✅ 保留         |                                |
| Jinja2 文档生成（`doc/generator.py`）   | ❌ 删除         | 文档由 Agent 写                |
| SQLite 状态管理                         | ❌ 删除         | 改为 JSON                      |
| Checkpoint 系统                         | ❌ 删除         | 每步输出文件即为断点           |

---

## 6. 一句话总结

> 实现是完整的（全部 18 个任务 ✅），代码架构也是正确的，但存在多个运行时串联 bug：
> 相对路径生成错误 + depth planner 输出未被正确尊重 + 实际代码内容未注入到文档模板中。
>
> 更根本的问题是职责边界画错了：把"应该由 LLM Agent 做的事"硬编码进了 MCP Server（Jinja2 模板生成），
> 同时把"应该由 MCP Server 提供的纯数据"做得不够（缺少 token 估算、缺少文件内容读取接口）。
