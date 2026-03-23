# 优化文档索引

本目录整理自 `optimization_v1.md` 中与 Agent 的深度交流内容。按照不同维度将优化方案拆分为以下文档：

## 文档结构

| 文件                                                                 | 主题                   | 说明                                                                                              |
| -------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------- |
| [00_vision_and_requirements.md](00_vision_and_requirements.md)       | **需求愿景与设计思想** | 原始需求提取（14 个需求点）、需求全景图、6 条核心设计思想、一句话总结                             |
| [01_code_analysis_architecture.md](01_code_analysis_architecture.md) | 代码获取与架构优化     | 图算法改进（加权多关系图、SCC、DAG分层、功能锥体提取）、Louvain重新定位、目录树与依赖图的融合策略 |
| [02_skill_design.md](02_skill_design.md)                             | Skill 细节配置         | SKILL.md 重写方案、Prompt 模板设计（DETAIL Agent / INDEX Agent）、文档预算动态计算、信息分层规则  |
| [03_responsibility_separation.md](03_responsibility_separation.md)   | 职责分离               | MCP Server vs Skill vs Agent 的三层职责划分、工具精简（15→6）、任务分配与上下文管理               |
| [04_current_issues_diagnosis.md](04_current_issues_diagnosis.md)     | 当前问题诊断           | 现有实现的 E2E 测试结果、过度工程问题分析、流程错误分析、可保留部分                               |

## 核心设计理念

1. **MCP = 数据层**：确定性计算（代码解析、图算法、Token 估算），零 LLM
2. **Skill = 编排层**：定义 Agent 工作流、Prompt 模板、调度策略
3. **Agent = 智能层**：真正阅读代码并理解语义，撰写文档内容

## 关键改进方向

- **功能优先**：以"功能锥体"（Feature Cone）而非文件树或纯图社区来组织文档
- **层级内嵌**：每个功能内部保持从入口到实现的依赖链层级
- **共享代码独立**：被多功能共享的代码独立为基础设施节，附带反向索引
- **动态预算**：文档 Token 预算按源码量的 15-30% 动态分配
