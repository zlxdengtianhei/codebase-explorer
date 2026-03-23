# 工作流程详细参考文档

> 当需要每个阶段的详细步骤说明时，请加载本文件。

## 目录

1. [阶段一：索引](#阶段一索引)
2. [阶段二：规划](#阶段二规划)
3. [阶段三：分析](#阶段三分析)
4. [阶段四：生成](#阶段四生成)
5. [阶段五：验证](#阶段五验证)
6. [错误恢复策略](#错误恢复策略)
7. [检查点与恢复流程](#检查点与恢复流程)

---

## 阶段一：索引

### 步骤说明

```
1. 确定目标路径
   - 使用用户提供的路径，或从当前工作目录检测
   - 路径必须是绝对路径

2. 调用 index_codebase
   工具：index_codebase
   参数：
     path: "/absolute/path/to/repo"
     languages: null  # 自动检测，或使用 ["python"] 过滤

3. 轮询完成状态
   工具：get_analysis_status
   参数：
     project_id: <步骤 2 响应中获取>
   重复直到 status 为 "success" 或 "failed"

4. 向用户报告
   - 文件数、函数数、类数
   - 检测到的语言
   - 模块数（来自 Louvain 分组）
```

### MCP 调用示例

```json
// 请求
{"tool": "index_codebase", "params": {"path": "/home/user/my-project"}}

// 响应
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

### 错误恢复

| 错误                       | 原因             | 修复方法                        |
| -------------------------- | ---------------- | ------------------------------- |
| `InvalidPathError`         | 路径不存在       | 向用户询问正确路径              |
| `UnsupportedLanguageError` | 未找到支持的文件 | 尝试使用明确的 `languages` 参数 |
| 超时（120 秒）             | 代码库非常大     | 按子目录拆分分析                |

---

## 阶段二：规划

### 步骤说明

```
1. 获取模块列表
   工具：get_modules
   参数：
     sort_by: "dependency"  # 拓扑顺序
     project_id: <project_id>

2. 向用户展示模块
   显示：name, file_count, line_count, is_utility
   询问："这个分组看起来正确吗？"

3. 创建分析计划
   工具：create_analysis_plan
   参数：
     project_id: <project_id>
     max_tokens_per_batch: 60000

4. 规划文档结构
   工具：plan_doc_structure
   参数：
     project_id: <project_id>

5. 回顾深度决策
   响应中包含每个模块的 depth_decisions。
   向用户报告重要决策：
   - 哪些模块获得了深层文档
   - 哪些模块被合并到父文档中
   - 选择的拆分策略
```

### MCP 调用示例：plan_doc_structure

```json
// 响应
{
  "status": "success",
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

### 动态深度决策过程

对于每个模块，规划器：

1. 收集指标：file_count, function_count, class_count, line_count,
   estimated_tokens, subpackage_count, cyclomatic_complexity
2. 计算三个独立的深度分数：
   - 来自 subpackage_count 的 structural_depth
   - 来自加权分数公式的 complexity_depth
   - 来自估算源码 Token 数的 token_depth
3. 取 `max(structural, complexity, token)` 作为原始深度
4. 应用约束：
   - 工具模块最大深度为 2
   - 非常小的模块（< 100 行，< 5 个函数）强制为深度 0
   - 最大上限为 5
5. 选择拆分策略：SUBPACKAGE > CLASS > FUNCTION_GROUP > FILE

---

## 阶段三：分析

### 步骤说明

```
循环：
  1. 获取下一批
     工具：get_next_batch
     参数：
       batch_size: 3

  2. 对批次中每个模块：
     a. 获取交叉引用上下文
        工具：get_cross_ref_context
        参数：
          module_name: <名称>
          max_tokens: 16000

     b. 读取模块的源文件
        使用标准文件读取工具

     c. 分析并提交
        工具：submit_analysis
        参数：
          module_name: <名称>
          description: "一行描述"
          public_interfaces: ["func_a(x: int) -> str", ...]
          key_data_structures: ["UserModel", ...]
          dependencies: ["utils", "config"]
          patterns_identified: ["仓储模式", ...]
          detailed_analysis: "完整 Markdown 格式分析..."
          mermaid_diagram: "graph TD\n  A --> B"
          token_count: 3500

  3. 检查预算
     工具：check_budget_status
     参数：
       used_tokens: <累计值>
       modules_completed: <数量>
       elapsed_minutes: <时间>

  4. 如果 should_stop 为 true：
     工具：save_checkpoint
     参数：
       phase: "module_analysis"
       tokens_processed: <总计>

  5. 如果 should_stop 为 false 且 remaining_batches > 0：
     继续循环

  6. 如果 remaining_batches == 0：
     退出循环，进入阶段四
```

### 每 3 个模块保存检查点

完成每批 3 个模块后：

1. 将所有生成的结果保存到磁盘
2. 报告进度："Y 个模块中的 X 个已完成"
3. 调用 `save_checkpoint` 以确保安全
4. 验证提交的结果是否可检索

### 从检查点恢复

```
1. 加载检查点
   工具：load_checkpoint

2. 回顾状态
   - analyzed_modules：已完成，跳过这些
   - pending_modules：从这里继续
   - module_summaries：可作为交叉引用上下文

3. 从 get_next_batch 继续
   批次会自动跳过已完成的模块
```

---

## 阶段四：生成

### 步骤说明

```
1. 获取来自 plan_doc_structure 响应的文档树

2. 对文档节点排序：先生成叶节点，再生成父节点
   - 层级 2+ 的 DETAIL 文档优先
   - 层级 1 的 OVERVIEW 文档其次
   - 层级 0 的 INDEX.md 最后

3. 对每个文档节点（自底向上）：
   工具：generate_doc
   参数：
     target: <模块名或 "root">
     level: <0, 1, 2, ...>
     token_budget: <来自文档树>
     parent_path: <来自文档树>
     children: <来自文档树>
     project_id: <project_id>

4. 验证输出：
   - actual_tokens <= token_budget（允许 10% 超出）
   - 内容包含其层级所需的部分
   - 导航链接正确

5. 将内容写入 output_dir/<path>

6. 生成 doc-index.json
   汇总所有文档条目，包含路径、层级、Token 数
```

### 生成顺序示例

对于包含模块 core（深度 2）、utils（深度 1）、api（深度 2）的项目：

```
步骤 1：generate_doc(target="core.app", level=2, ...)       # DETAIL
步骤 2：generate_doc(target="core.models", level=2, ...)    # DETAIL
步骤 3：generate_doc(target="api.routes", level=2, ...)     # DETAIL
步骤 4：generate_doc(target="core", level=1, ...)           # OVERVIEW
步骤 5：generate_doc(target="utils", level=1, ...)          # OVERVIEW
步骤 6：generate_doc(target="api", level=1, ...)            # OVERVIEW
步骤 7：generate_doc(target="root", level=0, ...)           # INDEX
```

自底向上生成确保父文档可以引用子文档的摘要以生成导航链接。

---

## 阶段五：验证

### 步骤说明

```
1. 确认完成
   工具：get_analysis_status
   验证所有任务均为 "completed"

2. 链接验证
   对每个文档，检查每个 [文本](路径) 链接：
   - 内部链接可解析到已存在的文档文件
   - 锚点链接指向有效的标题
   - 无断开的交叉引用

3. Token 预算合规性
   对每个文档：
   - actual_tokens 应在 token_budget 内
   - 标记超出预算 > 10% 的文档

4. 覆盖率检查
   coverage = documented_modules / total_modules
   目标：>= 80%

5. Mermaid 图表检查
   - 每个 OVERVIEW.md 必须包含 Mermaid 依赖图
   - 每个 DETAIL.md 必须包含 Mermaid 结构图

6. 向用户报告
   - 文档总数：N 个
   - 覆盖率：X%
   - Token 用量：Y 总计
   - 使用的最大深度：Z
   - 发现的问题：[列表]
```

---

## 错误恢复策略

### 索引失败

```
如果 index_codebase 返回错误：
  1. 检查路径是否存在且为绝对路径
  2. 尝试使用明确的 languages 过滤器
  3. 如果代码库非常大（> 10000 个文件），建议对子目录分别索引
  4. 向用户报告错误信息
```

### 分析会话超时

```
如果上下文窗口接近限制 OR 已过 15 分钟：
  1. save_checkpoint(phase="module_analysis", status="interrupted")
  2. 向用户报告进度
  3. 用户可以继续：load_checkpoint()
```

### 文档生成失败

```
如果 generate_doc 对特定目标返回错误：
  1. 检查该目标的分析结果是否存在
  2. 验证 parent/children 路径是否正确
  3. 尝试以较小的 token_budget 重新生成
  4. 如果持续失败，跳过并在最终报告中注明
```

### 预算耗尽

```
如果 check_budget_status 返回 should_stop: true：
  1. 完成当前模块的分析（不要留下部分结果）
  2. 立即 save_checkpoint
  3. 报告："预算已达上限。X 个模块已分析，Y 个待处理。"
  4. 用户重新开始并使用 load_checkpoint 继续
```

---

## 检查点与恢复流程

### 检查点数据结构

检查点记录以下内容：

- `phase`：当前工作流程阶段
- `analyzed_modules`：已完成模块的名称列表
- `pending_modules`：待处理模块的名称列表
- `tokens_processed`：累计 Token 数量
- `status`："in_progress"、"completed" 或 "interrupted"

### 恢复协议

```
1. Agent 开始新会话
2. 调用 load_checkpoint()
3. 如果检查点存在：
   a. 跳过阶段一（索引已完成）
   b. 跳过阶段二（计划已创建）
   c. 从 pending_modules 恢复阶段三
   d. 交叉引用上下文可从 module_summaries 获取
4. 如果不存在检查点：
   a. 从阶段一开始
```

### 多会话工作流

```
会话 1：
  阶段一：索引（5 分钟）
  阶段二：规划（2 分钟）
  阶段三：分析 10 个模块中的 6 个（15 分钟）
  -> 保存检查点（预算耗尽）

会话 2：
  load_checkpoint -> 恢复阶段三
  阶段三：分析剩余 4 个模块（10 分钟）
  阶段四：生成文档（5 分钟）
  阶段五：验证（2 分钟）
  -> 完成
```
