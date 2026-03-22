# 研究任务 04：渐进式披露文档设计标准

## ⚠️ 前置依赖

**在开始本任务之前，请先阅读以下前置研究结果**（如果存在）：

1. `results/01_code_graph_tools.md` — 了解我们选定的图谱工具能输出什么数据结构，文档层级需要基于这些数据
2. `results/02_auto_module_grouping.md` — 了解模块是如何被自动分组的，文档层级直接对应分组层级
3. `results/03_docagent_architecture.md` — 了解 DocAgent 的层级处理模式，可能影响文档设计

如果这些文件不存在，可以独立执行本任务，但在"推荐的文档层级"部分需要标注"待与前置任务结果对齐"。

## 研究目标

定义**渐进式披露（Progressive Disclosure）架构文档**的完整规范：包括文档层级结构、每层的内容标准、层间索引连接方式、以及自动生成这些文档的模板。

### 核心问题

1. 业界有哪些**成熟的代码架构文档标准**？（如 arc42, C4 Model, 4+1 View）
2. 这些标准中哪些适合用"渐进式披露"方式呈现？
3. 每一层文档应该包含**多少信息**？如何控制信息密度？
4. 层间的**索引/链接**应该采用什么格式？
5. 有没有现成的**文档模板生成工具**可以参考？

## 搜索关键词

### 第一轮：架构文档标准

- `software architecture documentation standard template 2025`
- `arc42 architecture documentation template structure`
- `C4 model code documentation levels context container component code`
- `4+1 architectural view model documentation`
- `technical documentation hierarchy best practices`

### 第二轮：渐进式披露在文档中的应用

- `progressive disclosure documentation design pattern`
- `hierarchical technical documentation structure`
- `multi-level code documentation index linking`
- `documentation information density optimization`
- `code documentation for LLM context efficiency`

### 第三轮：自动化文档生成

- `automatic architecture documentation generation from code`
- `code to architecture document generator tool`
- `markdown documentation template engine Jinja2 code architecture`
- `architecture decision record ADR template`
- `diátaxis documentation framework technical`

### 第四轮：针对 AI/LLM 优化的文档

- `AI-friendly codebase documentation format`
- `LLM context window optimized documentation structure`
- `token-efficient architecture documentation`
- `Claude SKILL.md documentation structure progressive disclosure`
- `code documentation for AI agent consumption`

## 深入阅读方向

### 必须阅读的资源

1. **C4 Model**：https://c4model.com/
   - 这是最接近渐进式披露的架构文档模型
   - 4 个层级：System Context → Container → Component → Code
   - 评估如何把 C4 的层级映射到我们的文件结构

2. **arc42**：https://arc42.org/
   - 德国标准的架构文档模板
   - 评估其 12 个章节中哪些适合我们自动生成

3. **Diátaxis 框架**：https://diataxis.fr/
   - 技术文档的四象限模型：Tutorial, How-to, Explanation, Reference
   - 评估与我们的层级结构是否互补

4. **Agent Skills 的 Progressive Disclosure 模式**：
   - Claude/Gemini 的 Skill 系统如何做渐进式加载
   - 这给我们的文档层级设计提供了直接参考

5. **aider repomap 的信息压缩策略**：
   - 如何在有限 token 内呈现最大信息量
   - PageRank 排序与 token 预算裁剪

6. **现有大型开源项目的文档结构**：
   - Linux Kernel: `Documentation/` 目录结构
   - Kubernetes: `docs/` 目录结构
   - Rust 编译器: `compiler/` 下的 README 结构
   - 评估哪些做得好，哪些可以改进

### 可选深入

- `Sphinx` 文档生成器的层级组织方式
- `MkDocs` 的 navigation 配置
- `Docusaurus` 的侧边栏层级设计

## 产出要求

### 保存位置

`results/04_progressive_doc_standards.md`

### 必须包含的内容

1. **文档层级定义**（核心产出）：

```
Level 0: INDEX.md (项目总览)
├── 项目名称和一句话描述
├── 核心功能模块列表（带简述）
├── 架构概览图（Mermaid）
├── 技术栈摘要
└── → 链接到各 Level 1 文档

Level 1: module/OVERVIEW.md (模块概述)
├── 模块职责和边界
├── 与其他模块的依赖关系
├── 关键对外接口
├── 复杂度指标
└── → 链接到各 Level 2 文档

Level 2: module/component/ARCHITECTURE.md (组件详情)
├── 组件内部结构
├── 核心类/函数说明
├── 数据流描述
├── 关键设计决策
└── → (如果需要) 链接到更深层
```

2. **每层的信息密度标准**：
   - Level 0: 不超过 X 行 / Y tokens
   - Level 1: 不超过 X 行 / Y tokens
   - Level 2: 不超过 X 行 / Y tokens
   - 给出这些数字的依据

3. **索引链接规范**：
   - 如何在 Markdown 中实现层间导航
   - 元数据注释格式（parent, children, coverage, last_updated）
   - 自动校验链接完整性的方法

4. **文档模板**：
   - Level 0 的 Jinja2/Markdown 模板
   - Level 1 的 Jinja2/Markdown 模板
   - Level 2 的 Jinja2/Markdown 模板
   - 每个模板中的变量说明

5. **与 C4 Model 的映射关系**：
   - 我们的 Level 0/1/2 如何对应 C4 的 Context/Container/Component/Code

6. **AI/LLM 消费优化建议**：
   - 如何让生成的文档既适合人类阅读，又适合 LLM 快速理解
   - 结构化元数据的作用

## 质量标准

- 必须参考至少 3 个主流架构文档标准（C4, arc42, Diátaxis 或其他）
- 必须分析至少 2 个真实大型开源项目的文档结构
- 文档模板必须可以直接使用（不是草案）
- 信息密度标准需要有量化依据（不是拍脑袋）
