# 研究任务 03：DocAgent 多Agent架构深度分析

## 研究目标

深入分析 Facebook Research 的 DocAgent 项目的**完整架构**，提取其中**可复用的设计模式**，特别是：

- Navigator 模块（AST → DAG → 拓扑排序）的具体实现
- 多 Agent 协作模式（Orchestrator/Reader/Searcher/Writer/Verifier）的通信和协调机制
- 如何适配和扩展为我们的"渐进式架构文档生成"系统

### 核心问题

1. DocAgent 的 Navigator 是如何构建依赖 DAG 的？具体分析哪些依赖类型？
2. 5 个 Agent 之间的通信协议是什么？是管道式还是图式？
3. Orchestrator 是如何决定何时停止迭代的？
4. Verifier 的质量评估标准是什么？可以复用吗？
5. DocAgent 的设计有哪些**局限性**是我们需要避开的？

## 搜索关键词

### 第一轮：DocAgent 本身

- `DocAgent facebook research multi-agent documentation generation architecture`
- `DocAgent arxiv 2504.08725 paper analysis`
- `facebookresearch DocAgent github source code analysis`
- `DocAgent navigator module AST dependency DAG topological sort`

### 第二轮：类似的多Agent代码分析系统

- `multi-agent code analysis system architecture paper 2024 2025`
- `agentic code documentation generation hierarchical processing`
- `LLM agent code understanding orchestrator pattern`
- `multi-agent software engineering system survey 2025`

### 第三轮：可替代的设计模式

- `reader writer verifier agent pattern software`
- `topological sort code processing order dependency DAG`
- `hierarchical code documentation generation incremental context`
- `iterative refinement agent loop stop condition`

## 深入阅读方向

### 必须阅读的资源

1. **DocAgent 论文**：https://arxiv.org/abs/2504.08725
   - 完整阅读，重点关注 Section 3 (Methodology)
   - 提取算法伪代码

2. **DocAgent 源代码**：https://github.com/facebookresearch/DocAgent
   - `src/agent/` 目录 — Agent 框架核心
   - `src/agent/README.md` — Agent 组件详细说明
   - `src/navigator/` 或类似模块 — DAG 构建逻辑
   - `config/example_config.yaml` — 配置结构
   - `generate_docstrings.py` — 入口文件，理解主流程

3. **DocAgent Agent Component README**：
   - https://github.com/facebookresearch/DocAgent/blob/main/src/agent/README.md
   - 这个文件详细描述了 Agent 间的协作机制

4. **RepoAgent (OpenBMB)** 作为对比：
   - https://github.com/OpenBMB/RepoAgent
   - 与 DocAgent 的设计差异是什么？

5. **MASLab (Multi-Agent System Lab)**：
   - 搜索 "MASLab multi-agent code analysis benchmark"
   - 了解学术界对多Agent代码分析的基准评估

### 可选深入

- HyperAgent (FPT Software) 的 4-Agent 设计
- SWE-Agent 的任务分解模式
- Devin / OpenHands 的 Agent 协作机制

## 产出要求

### 保存位置

`results/03_docagent_architecture.md`

### 必须包含的内容

1. **DocAgent 完整架构图**（文字/Mermaid）
   - 所有组件及其关系
   - 数据流动方向
   - 控制流描述

2. **Navigator 模块详细分析**：
   - 输入：什么
   - 处理：如何构建 DAG？用了哪些 AST 节点类型？
   - 输出：什么格式？
   - 排序策略：具体的拓扑排序方式

3. **Agent 协作模式提取**：
   - 各 Agent 的输入/输出接口
   - 迭代终止条件
   - 错误恢复机制
   - Agent 间的信息传递格式

4. **可复用的设计模式清单**：
   - 模式名称
   - 适用场景
   - 在我们系统中如何应用
   - 代码草案（Python 伪代码级别）

5. **DocAgent 局限性分析**：
   - 仅支持 Python 的根本原因
   - 仅生成 docstring 的设计限制
   - 对我们"渐进式多级文档"需求的差距

6. **与 RepoAgent 的对比**：
   - 设计理念差异
   - 哪个设计更适合我们的需求
   - 可以互相借鉴什么

## 质量标准

- 必须阅读 DocAgent 源代码（不仅是论文和 README）
- 架构图必须基于源代码验证（不是从论文描述推断）
- 设计模式清单必须包含具体的代码映射建议
- Agent 协作描述必须够具体，能直接指导实现
