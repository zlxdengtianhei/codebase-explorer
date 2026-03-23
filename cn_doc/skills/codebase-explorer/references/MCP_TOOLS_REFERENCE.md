# MCP 工具参考文档

> 当需要完整参数规范和返回值说明时，请加载本文件。

## 目录

1. [索引与分析工具](#1-索引与分析工具)
2. [预算与分块工具](#2-预算与分块工具)
3. [任务管理工具](#3-任务管理工具)
4. [检查点与交叉引用工具](#4-检查点与交叉引用工具)
5. [文档生成工具](#5-文档生成工具)
6. [错误代码](#6-错误代码)

---

## 1. 索引与分析工具

### index_codebase

解析代码库，构建依赖图，运行 Louvain 社区检测。

**参数**：

| 参数        | 类型                                                 | 必填 | 默认值 | 描述                          |
| ----------- | ---------------------------------------------------- | ---- | ------ | ----------------------------- |
| `path`      | `str`                                                | 是   | --     | 代码库根目录的绝对路径        |
| `languages` | `list["python"\|"typescript"\|"javascript"] \| null` | 否   | `null` | 要分析的语言，null = 自动检测 |

**返回值**：

```json
{
  "status": "success",
  "summary": "已索引 42 个文件，156 个函数，28 个类",
  "data": {
    "project_id": "proj_abc123",
    "file_count": 42,
    "function_count": 156,
    "class_count": 28,
    "languages": ["python"],
    "module_count": 6
  }
}
```

**注意**：幂等操作。超时时间：120 秒。必须在其他工具之前调用。

**示例**：

```
index_codebase(path="/home/user/flask", languages=["python"])
```

---

### get_modules

获取 Louvain 分组后的模块列表。

**参数**：

| 参数         | 类型                                         | 必填 | 默认值   | 描述                              |
| ------------ | -------------------------------------------- | ---- | -------- | --------------------------------- |
| `project_id` | `str \| null`                                | 否   | `null`   | 项目 ID，null = 使用最新项目      |
| `sort_by`    | `"name"\|"size"\|"complexity"\|"dependency"` | 否   | `"name"` | 排序方式，"dependency" = 拓扑顺序 |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "project_id": "proj_abc123",
    "modules": [
      {
        "name": "core",
        "file_count": 8,
        "line_count": 2400,
        "function_count": 45,
        "class_count": 12,
        "is_utility": false
      }
    ],
    "total_modules": 6
  }
}
```

**前置条件**：必须已调用 `index_codebase`。

---

### get_module_detail

获取特定模块的详细信息。

**参数**：

| 参数          | 类型          | 必填 | 默认值 | 描述                     |
| ------------- | ------------- | ---- | ------ | ------------------------ |
| `module_name` | `str`         | 是   | --     | 要查询的模块名称         |
| `project_id`  | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目 |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "name": "core",
    "files": ["src/core/app.py", "src/core/models.py"],
    "functions": [
      {
        "name": "create_app",
        "params": "(config: Config)",
        "file": "src/core/app.py"
      }
    ],
    "classes": [
      {
        "name": "Flask",
        "methods": ["run", "route"],
        "file": "src/core/app.py"
      }
    ],
    "dependencies": ["utils", "config"],
    "dependents": ["api", "cli"],
    "metrics": { "line_count": 2400, "complexity": 3.2 },
    "mermaid_graph": "graph TD\n  core --> utils\n  core --> config"
  }
}
```

---

### get_dependency_graph

以 Mermaid 格式获取依赖图。

**参数**：

| 参数         | 类型                  | 必填 | 默认值      | 描述                              |
| ------------ | --------------------- | ---- | ----------- | --------------------------------- |
| `scope`      | `"project"\|"module"` | 否   | `"project"` | 图范围                            |
| `target`     | `str \| null`         | 否   | `null`      | 模块名称（scope="module" 时必填） |
| `project_id` | `str \| null`         | 否   | `null`      | 项目 ID，null = 最新项目          |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "nodes": [{ "name": "core", "type": "module" }],
    "edges": [{ "from": "api", "to": "core", "weight": 5 }],
    "circular_deps": [["models", "schemas"]],
    "mermaid_graph": "graph TD\n  api --> core\n  core --> utils"
  }
}
```

---

## 2. 预算与分块工具

### estimate_module_tokens

使用字符/行数启发式方法估算模块的 Token 数量。

**参数**：

| 参数          | 类型          | 必填 | 默认值 | 描述                          |
| ------------- | ------------- | ---- | ------ | ----------------------------- |
| `module_name` | `str \| null` | 否   | `null` | 模块名称，null = 估算所有模块 |
| `project_id`  | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目      |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "estimates": [
      {
        "module": "core",
        "estimated_tokens": 28800,
        "line_count": 2400,
        "file_count": 8,
        "language": "python"
      }
    ],
    "total_tokens": 92000
  }
}
```

**启发式规则**：Python 约 4.2 字符/Token，TypeScript/JavaScript 约 3.8 字符/Token。

---

### create_analysis_plan

生成带有 DAG 拓扑排序的分块分析计划。

**参数**：

| 参数                   | 类型          | 必填 | 默认值  | 描述                                |
| ---------------------- | ------------- | ---- | ------- | ----------------------------------- |
| `project_id`           | `str \| null` | 否   | `null`  | 项目 ID，null = 最新项目            |
| `max_tokens_per_batch` | `int`         | 否   | `60000` | 每批的最大 Token 数（10000-200000） |

**返回值**：

```json
{
  "status": "success",
  "summary": "已创建 8 个分析任务，共 4 个层级",
  "data": {
    "tasks": [
      {
        "batch": 0,
        "modules": ["utils", "config"],
        "estimated_tokens": 12000,
        "reason": "leaf_modules"
      },
      {
        "batch": 1,
        "modules": ["models"],
        "estimated_tokens": 18000,
        "reason": "layer_1"
      }
    ],
    "total_batches": 4,
    "total_modules": 8
  }
}
```

**注意**：幂等操作。叶子模块（无依赖）优先批处理。

---

### check_budget_status

检查 Agent 是否应停止并保存进度。

**参数**：

| 参数                 | 类型    | 必填 | 默认值 | 描述                        |
| -------------------- | ------- | ---- | ------ | --------------------------- |
| `used_tokens`        | `int`   | 是   | --     | 到目前为止已消耗的 Token 数 |
| `modules_completed`  | `int`   | 否   | `0`    | 本次会话已分析的模块数      |
| `pending_cross_refs` | `int`   | 否   | `0`    | 未解决的交叉引用数          |
| `elapsed_minutes`    | `float` | 否   | `0.0`  | 会话开始以来经过的分钟数    |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "total_budget": 129000,
    "used_tokens": 85000,
    "remaining_tokens": 44000,
    "usage_percent": 65.9,
    "should_stop": false,
    "stop_reason": ""
  }
}
```

**停止条件**：

1. Token 使用量 > 预算的 85%
2. 未解决的交叉引用 > 3 个未分析模块
3. 经过时间 > 15 分钟

---

## 3. 任务管理工具

### get_next_batch

获取下一批待分析的模块。

**参数**：

| 参数         | 类型          | 必填 | 默认值 | 描述                     |
| ------------ | ------------- | ---- | ------ | ------------------------ |
| `project_id` | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目 |
| `batch_size` | `int`         | 否   | `3`    | 每批的最大模块数（1-10） |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "batch_index": 2,
    "modules": [
      {
        "name": "services",
        "files": ["src/services/auth.py"],
        "estimated_tokens": 24000,
        "dependency_summaries": "# 模块：utils\n描述：..."
      }
    ],
    "remaining_batches": 2,
    "total_progress_percent": 50.0
  }
}
```

**前置条件**：必须已调用 `create_analysis_plan`。

---

### submit_analysis

提交模块的分析结果。

**参数**：

| 参数                  | 类型          | 必填 | 默认值 | 描述                     |
| --------------------- | ------------- | ---- | ------ | ------------------------ |
| `module_name`         | `str`         | 是   | --     | 模块名称                 |
| `description`         | `str`         | 是   | --     | 一行描述                 |
| `public_interfaces`   | `list[str]`   | 是   | --     | 公共函数/类签名列表      |
| `key_data_structures` | `list[str]`   | 是   | --     | 重要数据结构             |
| `dependencies`        | `list[str]`   | 是   | --     | 模块依赖关系             |
| `patterns_identified` | `list[str]`   | 是   | --     | 发现的设计模式           |
| `detailed_analysis`   | `str \| null` | 否   | `null` | 完整 Markdown 格式分析   |
| `mermaid_diagram`     | `str \| null` | 否   | `null` | 内部结构图               |
| `token_count`         | `int`         | 否   | `0`    | 本次分析消耗的 Token 数  |
| `project_id`          | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目 |

**返回值**：

```json
{
  "status": "success",
  "summary": "'services' 的分析已保存。6/8 个模块已完成。",
  "data": {
    "result_id": "res_abc",
    "modules_completed": 6,
    "modules_remaining": 2,
    "progress_percent": 75.0
  }
}
```

---

### get_analysis_status

获取整体分析进度和任务状态。

**参数**：

| 参数         | 类型          | 必填 | 默认值 | 描述                     |
| ------------ | ------------- | ---- | ------ | ------------------------ |
| `project_id` | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目 |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "total_tasks": 8,
    "pending": 2,
    "in_progress": 0,
    "completed": 6,
    "failed": 0,
    "completed_modules": ["utils", "config", "models"],
    "errors": [],
    "progress_percent": 75.0
  }
}
```

---

## 4. 检查点与交叉引用工具

### save_checkpoint

保存分析检查点以便会话恢复。

**参数**：

| 参数               | 类型                                                                 | 必填 | 默认值          | 描述                     |
| ------------------ | -------------------------------------------------------------------- | ---- | --------------- | ------------------------ |
| `phase`            | `"indexing"\|"module_analysis"\|"cross_reference"\|"doc_generation"` | 是   | --              | 当前阶段                 |
| `status`           | `"in_progress"\|"completed"\|"interrupted"`                          | 否   | `"in_progress"` | 状态                     |
| `tokens_processed` | `int`                                                                | 否   | `0`             | 已处理的总 Token 数      |
| `project_id`       | `str \| null`                                                        | 否   | `null`          | 项目 ID，null = 最新项目 |

**返回值**：

```json
{
  "status": "success",
  "summary": "检查点已保存：6/8 个模块已分析",
  "data": {
    "checkpoint_id": "ckpt_abc",
    "analyzed_modules": ["utils", "config"],
    "pending_modules": ["api", "cli"],
    "progress_percent": 75.0
  }
}
```

---

### load_checkpoint

加载分析检查点以恢复上一次会话。

**参数**：

| 参数            | 类型          | 必填 | 默认值 | 描述                             |
| --------------- | ------------- | ---- | ------ | -------------------------------- |
| `checkpoint_id` | `str \| null` | 否   | `null` | 检查点 ID，null = 加载最新检查点 |
| `project_id`    | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目         |

**返回值**：

```json
{
  "status": "success",
  "summary": "已恢复检查点：6/8 个模块已分析",
  "data": {
    "checkpoint_id": "ckpt_abc",
    "phase": "module_analysis",
    "analyzed_modules": ["utils", "config"],
    "pending_modules": ["api", "cli"],
    "module_summaries": {
      "utils": {
        "description": "共享工具函数",
        "public_interfaces": ["sanitize()"]
      }
    },
    "progress_percent": 75.0,
    "tokens_processed": 45000
  }
}
```

---

### get_cross_ref_context

从依赖摘要构建交叉引用上下文。

**参数**：

| 参数          | 类型          | 必填 | 默认值  | 描述                             |
| ------------- | ------------- | ---- | ------- | -------------------------------- |
| `module_name` | `str`         | 是   | --      | 正在分析的模块                   |
| `max_tokens`  | `int`         | 否   | `16000` | 上下文最大 Token 数（500-30000） |
| `project_id`  | `str \| null` | 否   | `null`  | 项目 ID，null = 最新项目         |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "target_module": "services",
    "context": "# 模块：utils\n描述：共享工具函数...\n---\n# 模块：models\n...",
    "dependencies_resolved": 3,
    "dependencies_pending": 1,
    "context_tokens": 8500
  }
}
```

**注意**：返回依赖关系的摘要（而非源代码），按引用权重排序。
未分析的依赖关系显示文件列表和"待处理"状态。

---

## 5. 文档生成工具

### plan_doc_structure

使用动态深度决策规划完整的文档树。

**参数**：

| 参数         | 类型          | 必填 | 默认值 | 描述                     |
| ------------ | ------------- | ---- | ------ | ------------------------ |
| `project_id` | `str \| null` | 否   | `null` | 项目 ID，null = 最新项目 |

**返回值**：

```json
{
  "status": "success",
  "summary": "已规划 12 个文档，共 3 个深度层级",
  "data": {
    "doc_tree": [
      {
        "path": "INDEX.md",
        "level": 0,
        "target": "root",
        "token_budget": 1200,
        "parent": null,
        "children": ["core/OVERVIEW.md", "utils/OVERVIEW.md"]
      },
      {
        "path": "core/OVERVIEW.md",
        "level": 1,
        "target": "core",
        "token_budget": 2000,
        "parent": "INDEX.md",
        "children": ["core/app/DETAIL.md"]
      }
    ],
    "total_docs": 12,
    "max_depth": 3,
    "depth_decisions": {
      "core": {
        "depth": 2,
        "reason": "1453 行，28 个组件",
        "split_strategy": "subpackage"
      },
      "utils": {
        "depth": 1,
        "reason": "工具模块，200 行",
        "split_strategy": "file"
      }
    }
  }
}
```

**前置条件**：所有模块必须已完成分析（`submit_analysis` 已全部提交）。

---

### generate_doc

使用 Jinja2 模板生成单个文档。

**参数**：

| 参数           | 类型                | 必填 | 默认值 | 描述                                  |
| -------------- | ------------------- | ---- | ------ | ------------------------------------- |
| `target`       | `str`               | 是   | --     | 模块名称，或 INDEX 用 "root"          |
| `level`        | `int`               | 是   | --     | 0=INDEX, 1=OVERVIEW, 2+=DETAIL（0-5） |
| `token_budget` | `int`               | 是   | --     | 本文档的 Token 预算（>= 200）         |
| `parent_path`  | `str \| null`       | 否   | `null` | 父文档路径（用于反向链接）            |
| `children`     | `list[str] \| null` | 否   | `null` | 子文档路径列表（用于前向链接）        |
| `project_id`   | `str \| null`       | 否   | `null` | 项目 ID，null = 最新项目              |

**返回值**：

```json
{
  "status": "success",
  "data": {
    "path": "core/OVERVIEW.md",
    "content": "# Core 模块\n\n> ...",
    "actual_tokens": 1850,
    "level": 1,
    "target": "core"
  }
}
```

**模板选择**：

- 层级 0：`index.md.j2`
- 层级 1：`overview.md.j2`
- 层级 2+：`detail.md.j2`（通用，适用于任意深度）

---

## 6. 错误代码

| 错误                   | 相关工具                               | 描述                      | 恢复方法                          |
| ---------------------- | -------------------------------------- | ------------------------- | --------------------------------- |
| `PROJECT_NOT_FOUND`    | 除 `index_codebase` 外的所有工具       | 尚未索引任何项目          | 先调用 `index_codebase`           |
| `MODULE_NOT_FOUND`     | `get_module_detail`, `submit_analysis` | 无效的模块名称            | 通过 `get_modules` 检查有效名称   |
| `PLAN_NOT_CREATED`     | `get_next_batch`, `generate_doc`       | 分析计划不存在            | 调用 `create_analysis_plan`       |
| `ANALYSIS_INCOMPLETE`  | `plan_doc_structure`                   | 并非所有模块都已分析      | 完成待处理的分析                  |
| `INVALID_PATH`         | `index_codebase`                       | 路径不存在                | 提供有效的绝对路径                |
| `BUDGET_EXCEEDED`      | `generate_doc`                         | 内容超出 Token 预算       | 缩减范围或增加预算                |
| `CHECKPOINT_NOT_FOUND` | `load_checkpoint`                      | 不存在检查点              | 从阶段一重新开始                  |
| `TASK_CLAIMED`         | `get_next_batch`                       | 模块已被另一个 Agent 锁定 | 跳到批次中的下一个模块            |
| `UNSUPPORTED_LANGUAGE` | `index_codebase`                       | 不支持该语言              | 使用 python/typescript/javascript |
| `TIMEOUT`              | `index_codebase`                       | 索引超过 120 秒           | 索引更小的目录                    |
