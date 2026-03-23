# 职责分离

> 主题：MCP Server、Skill、Agent 三层职责边界，工具精简，任务分配与上下文管理。

---

## 1. 三层架构

```
MCP Server（确定性，零 LLM）→ 代码解析、图计算、Token 估算、任务分配
Skill（编排层）             → 定义工作流、Prompt 模板、调度策略
Agent（LLM 智能层）         → 阅读代码并理解语义，撰写文档
```

| 判断标准           | MCP      | Agent      |
| ------------------ | -------- | ---------- |
| 需要 LLM 判断？    | ❌ → MCP | ✅ → Agent |
| 结果确定性？       | ✅ → MCP | ❌ → Agent |
| 涉及代码语义理解？ | ❌ → MCP | ✅ → Agent |
| 涉及文档撰写？     | ❌ → MCP | ✅ → Agent |

---

## 2. MCP Server 职责

### A. 代码结构解析

- `index_codebase(path, languages)` → 解析代码，建图，Louvain 分组
- `get_module_detail(module_name)` → 文件列表、函数签名、类定义、导入关系
- `get_dependency_graph(scope, target)` → Mermaid 依赖图

### B. 深度规划 + Token 估算

- `estimate_module_tokens(module_name)` → 每个模块/文件的 token 数（**新功能**）
- `plan_depth(module_name?)` → 深度建议（**注意：是"建议"，最终由 Agent 决策**）
- `create_analysis_plan(max_tokens_per_batch)` → DAG 排序的任务队列

### C. 进度追踪（大幅简化）

- `get_next_batch(batch_size)` → 下一批待分析模块
- `submit_analysis(module_name, content)` → 存储分析结果
- `check_budget_status()` → 预算状态

### 新增

- ✅ `get_file_content(file_path)` — 返回源码（供 Agent 阅读）
- ✅ `estimate_module_tokens()` 增强 — 文件级 token 明细

---

## 3. 工具精简：15 → 6

| 新工具                 | 功能                        |
| ---------------------- | --------------------------- |
| `analyze_codebase`     | 全流水线：解析→图→锥体→任务 |
| `get_structure`        | 查询文件/函数/类详情        |
| `get_feature_cones`    | 查询功能分组                |
| `get_dependency_graph` | Mermaid 依赖图              |
| `get_progress`         | 任务完成状态                |
| `get_file_tokens`      | 每文件 token 估算           |

### 砍掉的工具

| 工具                          | 原因                           |
| ----------------------------- | ------------------------------ |
| `generate_doc()`              | 文档由 LLM Agent 写，非 Jinja2 |
| `plan_doc_structure()` 树构建 | 改为只返回建议                 |
| `save/load_checkpoint`        | 简化为 JSON status             |
| `get_cross_ref_context()`     | Agent 自拼上下文               |

### 存储简化

- 旧：SQLite WAL + 5 表 + checkpoint → 新：JSON 文件（`{project_id}.json`）

---

## 4. Skill 的 5 个 Phase

| Phase | 名称     | 角色       | 关键动作                          |
| ----- | -------- | ---------- | --------------------------------- |
| 1     | Index    | MCP        | 运行 `analyze_codebase()`         |
| 2     | Validate | 审查 Agent | 判断分组/深度语义合理性           |
| 3     | DETAIL   | 并行 Agent | 读源码，写 DETAIL + SNIPPET       |
| 4     | INDEX    | 整理 Agent | 组合 SNIPPET 写 INDEX（不读源码） |
| 5     | Validate | 自动       | 链接/覆盖率/Token 检查            |

---

## 5. Agent 角色定义

### DETAIL Agent

- **输入**: 源代码文件 + `feature_cones.json` 中本功能结构
- **输出**: DETAIL.md + SNIPPET.md
- **做**: 读源码、理解功能、撰写文档
- **不做**: 了解完整架构、描述其他功能

### INDEX Agent

- **输入**: `feature_cones.json` + 所有 SNIPPET
- **输出**: INDEX.md + OVERVIEW.md + doc-index.json
- **做**: 组合架构数据和 SNIPPET
- **不做**: 读任何一行源代码

### Validator Agent

- **输入**: 深度建议 + 模块列表 + 依赖图
- **输出**: 审查结果（调整建议）

---

## 6. 任务分配策略

### 三种情况

| 类型   | Token 范围 | 策略                         |
| ------ | ---------- | ---------------------------- |
| 小功能 | < 30k      | 合并到一个 batch，一个 Agent |
| 中功能 | 30k~100k   | 独立分配，一个 Agent         |
| 大功能 | > 100k     | 按内部层级拆分，多个 Agent   |

### 装箱算法

按 token 数降序排列，贪心装入 batch，每个 batch < CONTEXT_BUDGET (100k)。

### task_manifest.json 核心字段

```json
{
  "tasks": [
    {
      "task_id": "task_001",
      "type": "batch|single|split",
      "features": [
        {
          "cone_id": "cone_0",
          "files": ["views.py", "ctx.py"],
          "tokens": 4500,
          "layers": [{ "depth": 0, "files": ["views.py"] }],
          "shared_deps": ["app.py"]
        }
      ]
    }
  ],
  "final_tasks": [
    {
      "task_id": "index_assembly",
      "depends_on": ["task_001"],
      "input": "all SNIPPET.md files"
    }
  ]
}
```

---

## 7. 信息流

```
MCP（代码层）              Skill（Agent 调度层）
─────────────             ──────────────────
01_structure.json ──┐
02_dag.json ────────┤
03_feature_cones.json ──┤──→ DETAIL Agent A → DETAIL_A + SNIPPET_A
04_file_tokens.json ────┤──→ DETAIL Agent B → DETAIL_B + SNIPPET_B
05_task_manifest.json ──┘──→ INDEX Agent   → INDEX.md + OVERVIEW.md
                              (不读源码，用 cones + SNIPPET)
```

---

## 8. 关键设计优势

1. **确定性分配**: MCP 算任务，Agent 不需决定"该读哪些文件"
2. **Token 安全**: 每个任务 token 已验证 < 100k
3. **小项目零浪费**: Flask 16k → 一个 Agent 搞定
4. **大项目可扩展**: 200k+ 自动拆分并行
5. **统一 Prompt**: 所有 Agent 同一套 Skill，输入数据不同
6. **断点恢复**: 每步有文件输出
7. **架构完整性**: 架构信息是代码分析预算的常量，不因任务拆分丢失
