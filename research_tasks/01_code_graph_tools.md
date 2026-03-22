# 研究任务 01：代码图谱/依赖分析工具深度调研

## 研究目标

找到能够**根据代码的函数间依赖关系、import 关系、类继承关系等，生成完整代码结构图谱**的所有成熟工具。对每个工具进行实际测试级别的深度分析（不只是看 README），最终给出明确的选型建议。

### 核心问题

1. 哪些工具能**跨文件**解析函数调用关系？（不仅仅是单文件 AST）
2. 哪些工具能输出**可编程的图数据结构**（如 NetworkX、JSON、GraphML）？
3. 各工具的**语言支持范围**和**精度**如何？
4. 在**本地运行**、**无需 Docker**、**开源免费**的约束下，最佳选择是什么？

## 搜索关键词

### 第一轮：广覆盖

- `code dependency graph generator tool open source 2025 2026`
- `cross-file function call graph static analysis tool`
- `codebase structure graph knowledge graph generator local`
- `代码依赖关系图 静态分析 开源工具`
- `code property graph CPG tools comparison`

### 第二轮：针对已知工具深入

- `graph-sitter codegen python API dependencies usages call_sites tutorial`
- `graph-sitter vs tree-sitter vs joern comparison`
- `Joern code property graph tutorial Python Java 2025`
- `SCIP sourcegraph code intelligence local index Python TypeScript`
- `PyCG static call graph Python accuracy limitations`
- `dependency-cruiser vs madge JavaScript module dependency`

### 第三轮：探索未知工具

- `code knowledge graph builder open source NOT neo4j NOT docker`
- `rust call graph analyzer local tool`
- `Go golang dependency graph static analysis tool`
- `multi-language code analysis unified graph output`
- `LSP language server protocol call hierarchy export`
- `stack-graphs GitHub code navigation incremental`

## 深入阅读方向

### 必须阅读的资源

1. **graph-sitter 完整文档**：https://graph-sitter.com/
   - 特别关注：`/building-with-graph-sitter/dependencies`
   - 特别关注：`/building-with-graph-sitter/traversing-the-call-graph`
   - 特别关注：`/building-with-graph-sitter/codebase-visualization`
   - 评估：实际 API 能力，是否能遍历整个 codebase 的所有依赖

2. **graph-sitter GitHub**：https://github.com/codegen-sh/graph-sitter
   - 查看：issue 和 limitations，实际用户反馈
   - 查看：最近的 release notes，活跃度

3. **Joern 文档**：https://docs.joern.io/
   - 评估：是否适合做架构分析（vs 安全分析）
   - 查看：Python/JS/Go 支持的成熟度
   - 评估：输出格式是否可编程

4. **SCIP 仓库**：https://github.com/sourcegraph/scip
   - 评估：`scip print --json` 的输出结构
   - 查看：各语言 indexer 的成熟度
   - 评估：是否能从 SCIP 索引构建依赖图

5. **PyCG 论文和代码**：https://github.com/vitsalis/PyCG
   - 注意：已归档 (archived)，评估是否仍可用
   - 评估精度数据：99.2% precision, 69.9% recall 的具体含义

6. **Pyan**：https://github.com/Technologicat/pyan
   - Python 调用图 + 模块依赖

7. **stack-graphs (GitHub)**：https://github.com/github/stack-graphs
   - GitHub 的增量式名称解析方案

### 可选深入

- `code2flow`：Python → 流程图
- `Understand (Scitools)`：商业工具，但了解其能力作为标杆
- `Sourcetrail`：已停止维护但设计优秀的代码探索工具

## 产出要求

### 保存位置

`results/01_code_graph_tools.md`

### 必须包含的内容

1. **工具矩阵表格**（至少 8 个工具）：

| 工具 | 语言支持 | 图谱类型 | 跨文件 | 输出格式 | 安装方式 | 活跃度 | 本地 | 开源 |
| ---- | -------- | -------- | ------ | -------- | -------- | ------ | ---- | ---- |

2. **每个主要工具的详细评价**（至少 5 个工具，每个 200+ 字）：
   - 实际能力描述（不是 README 复制）
   - 限制和缺点
   - 与其他工具的互补性
   - 适合/不适合什么场景

3. **最终选型建议**：
   - 主力工具推荐（含理由）
   - 备选方案
   - 不同语言的最佳组合

4. **关键代码示例**：
   - 展示主力工具如何遍历整个 codebase 并输出依赖图的完整代码

## 质量标准

- 所有引用必须有 URL
- 至少 3 个工具需要查看其 GitHub issue / 社区讨论（了解真实用户反馈）
- 如果声称某工具"支持 X 语言"，需要验证（而非仅看 README 声称）
- 对比必须包含至少一个**反面案例**（看起来好但实际有问题的工具）
