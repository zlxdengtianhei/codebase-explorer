# 研究任务 07：上下文预算与代码分片策略

## ⚠️ 前置依赖

**在开始本任务之前，请先阅读以下前置研究结果**（如果存在）：

1. `results/01_code_graph_tools.md` — 了解图谱工具输出的数据规模，影响分片策略
2. `results/02_auto_module_grouping.md` — 了解模块分组结果，分片应以模块为单位
3. `results/05_mcp_server_patterns.md` — 了解 MCP 工具设计，分片策略需要通过工具实现

如果这些文件不存在，可以独立执行本任务，但在"推荐的分析分片策略"部分需要标注"待与前置任务结果对齐"。

## 研究目标

研究如何**控制每次 Agent 分析的代码量**，确保不会超出 LLM 的 context window，同时保证每次分析的**信息完整性和有用性**。

### 核心问题

1. 现有工具（aider, Plandex, Continue.dev 等）是如何**管理代码上下文大小**的？
2. 代码应该按什么方式**分片**？（文件级 vs 模块级 vs 函数级）
3. 如何量化"一段代码需要多少 LLM token"？
4. **上下文预算**应该设多大？多少代码量后应该让 Agent 停下来？
5. 如何在分析远处需要交叉引用的代码时，不超出预算？(即agent在该分析多少代码后暂停，以保证一定不会超出context window，并且以一个中间结果的形式去记录目前进度)

## 搜索关键词

### 第一轮：现有工具的上下文管理策略

- `aider repomap token budget context management strategy`
- `Plandex context management 2M tokens strategy`
- `Continue.dev code context window management`
- `cursor IDE context window code selection strategy`
- `LLM coding assistant context budget management`

### 第二轮：代码分片方法

- `code chunking strategy LLM context window optimization`
- `intelligent code splitting semantic chunking`
- `code context selection algorithm relevance ranking`
- `token counting source code estimator tool`
- `tree-sitter code splitting semantic boundaries`

### 第三轮：Token 估算

- `source code token count estimation heuristic`
- `characters to tokens ratio programming language`
- `tiktoken code tokenizer Python`
- `LLM token estimation without tokenizer fast`
- `code lines to tokens approximate conversion`

### 第四轮：中间状态保存

- `incremental code analysis checkpoint resume strategy`
- `agent analysis progress intermediate result format`
- `partial code understanding accumulation merging`
- `code exploration breadth-first depth-first strategy LLM`

## 深入阅读方向

### 必须阅读的资源

1. **aider 的 RepoMap 策略**：https://aider.chat/docs/repomap.html
   - 如何用 PageRank 选择最重要的符号
   - `--map-tokens` 参数的实现逻辑
   - 动态调整 map 大小的策略

2. **Plandex 的上下文管理**：
   - 搜索 Plandex 如何处理 20M+ tokens 的项目
   - 智能上下文窗口管理策略

3. **aider 的 token 计数实现**：
   - https://github.com/Aider-AI/aider 源代码中的 token 计数逻辑
   - 它用什么方法估算代码 token？

4. **tiktoken (OpenAI)**：https://github.com/openai/tiktoken
   - 不同模型的 tokenizer 差异
   - 代码 token 化的特点（比自然语言更多 token）

5. **Continue.dev 的上下文策略**：
   - https://github.com/continuedev/continue
   - 如何选择发送给模型的代码上下文

6. **代码 token 比例研究**：
   - 不同语言的字符/token 比例
   - 代码行数 vs token 数的经验公式

### 可选深入

- OpenAI / Anthropic / Google 最新模型的 context window 大小
- RAG (Retrieval Augmented Generation) 在代码上下文中的应用
- 长上下文模型（如 Gemini 2M tokens）是否改变了分片策略
- 代码摘要（code summarization）作为上下文压缩手段

## 产出要求

### 保存位置

`results/07_context_budget_strategies.md`

### 必须包含的内容

1. **现有工具上下文策略对比**：

| 工具 | 策略名称 | 选择算法 | 预算控制 | 增量/全量 |
| ---- | -------- | -------- | -------- | --------- |

2. **代码量-Token 估算公式**：
   - 不同语言的经验公式
   - 快速估算方法（不需要完整 tokenizer）
   - 推荐使用的估算工具/库

3. **推荐的分析分片策略**：
   - 分片单位（文件 vs 模块 vs 函数组）
   - 每片的推荐大小
   - 如何处理跨片依赖
   - 分片排序策略（与依赖 DAG 的结合）

4. **预算阈值建议**：
   - 不同模型的建议预算
   - "何时停下来"的具体规则
   - 中间结果格式定义

5. **中间状态保存方案**：
   - Agent 应该以什么格式保存分析中间结果？
   - 如何让下一个 Agent（或下一轮会话）继续？
   - SQL schema 或 JSON 格式建议

6. **跨引用处理策略**：
   - 当分析模块 A 需要理解模块 B 时怎么办？
   - "先分析依赖 → 再分析依赖者" 的 DAG 拓扑策略
   - 提供模块摘要作为上下文替代（而非完整代码）

## 质量标准

- 必须分析至少 3 个现有工具的实际上下文管理实现
- Token 估算公式必须有实际数据支持（不是推测）
- 预算建议必须考虑不同模型的 context window 差异
- 中间结果格式必须够具体，能直接用作 MCP 工具的输入
