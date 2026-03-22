# 研究任务 06：Agent Skill (SKILL.md) 设计

## ⚠️ 前置依赖

**在开始本任务之前，请先阅读以下前置研究结果**（如果存在）：

1. `results/01_code_graph_tools.md` — Skill 需要知道用什么工具做图谱分析
2. `results/02_auto_module_grouping.md` — Skill 的分析流程需要按模块分组进行
3. `results/03_docagent_architecture.md` — Skill 的多步骤工作流参考 DocAgent 的模式
4. `results/04_progressive_doc_standards.md` — Skill 需要指导 Agent 按什么标准写文档
5. `results/05_mcp_server_patterns.md` — Skill 需要知道有哪些 MCP 工具可调用

**本任务是整合性任务**：Skill 是"胶水层"，它将前面所有研究的结果编排成一个完整的工作流。因此，前置结果对本任务**非常重要**。

如果前置结果不全，可以先调研 Skill 格式和设计模式，但「我们的 Skill 设计草案」部分必须等前置结果齐全后再填写完整版。

## 研究目标

设计一个**跨工具兼容**的 Agent Skill（SKILL.md），用于指导 AI Agent 如何编排多轮代码库分析流程、调用 MCP 工具、以及生成渐进式文档。

### 核心问题

1. SKILL.md 的**标准格式**是什么？各工具（Claude Code, Gemini CLI, OpenCode）的具体要求有何差异？
2. 如何在 Skill 中编码**多步骤工作流**，让 Agent 能自主完成而不需要人工干预？
3. 如何在 Skill 中嵌入**质量控制规则**（如"分析完 N 个模块后必须提交中间结果"）？
4. Skill 的**渐进式加载**如何工作？可以有子文件吗？
5. 有哪些**优秀的现有 Skill 实现**可以参考？

## 搜索关键词

### 第一轮：SKILL.md 标准

- `agent skills SKILL.md format specification standard 2025 2026`
- `SKILL.md yaml frontmatter markdown body structure`
- `agent skills directory standard open format`
- `claude code custom skills SKILL.md tutorial`
- `gemini CLI skills folder structure`

### 第二轮：Skill 设计模式

- `AI agent skill design patterns multi-step workflow`
- `SKILL.md complex workflow encoding example`
- `agent skill progressive disclosure sub-files scripts references`
- `AI coding agent skill best practices token efficiency`
- `skill design workflow automation agent`

### 第三轮：现有优秀 Skill 示例

- `github SKILL.md examples awesome agent skills`
- `skillsdirectory.com best skills coding analysis`
- `agent skills marketplace popular skills code analysis`
- `claude code built-in skills implementation reference`
- `opencode skills directory structure examples`

### 第四轮：跨工具兼容

- `SKILL.md compatibility Claude Gemini OpenCode Cursor Copilot`
- `agent skill portability cross-platform testing`
- `skill discovery mechanism AI IDE comparison`
- `SKILL.md location convention .claude .gemini .agents`

## 深入阅读方向

### 必须阅读的资源

1. **Agent Skills 官方规范**：
   - https://agentskills.io/ （如果存在）
   - https://skillsdirectory.com/
   - 完整了解标准规范

2. **Claude Code Skills 文档**：
   - https://docs.anthropic.com/en/docs/claude-code/skills
   - Skill 加载机制、目录位置、格式要求

3. **Gemini CLI Skills 文档**：
   - https://geminicli.com/ 的 Skills 章节
   - 与 Claude Code 的差异

4. **OpenCode Skills 支持**：
   - https://opencode.ai/ 的文档
   - 支持的 Skill 目录路径

5. **优秀 Skill 实现示例**（在 GitHub 搜索）：
   - 搜索 `path:SKILL.md` 在 GitHub 上
   - 找到至少 5 个高质量的 Skill 实现

6. **Agent Skills 媒体文章**：
   - Strapi, Medium 等平台上关于 Agent Skills 的教程文章
   - 关注实际使用经验和坑

### 可选深入

- Cursor Rules (.cursorrules) 与 SKILL.md 的对比
- GitHub Copilot Instructions 与 SKILL.md 的兼容性
- 如何测试 Skill 在不同 Agent 中的行为一致性

## 产出要求

### 保存位置

`results/06_agent_skill_design.md`

### 必须包含的内容

1. **SKILL.md 格式规范总结**：
   - YAML frontmatter 必需字段和可选字段
   - Markdown body 推荐结构
   - 子文件类型（scripts/, references/, assets/）
   - 文件大小/token 限制建议

2. **各工具的 Skill 发现路径对比**：

| 工具        | Workspace 路径    | Global 路径                | 优先级 |
| ----------- | ----------------- | -------------------------- | ------ |
| Claude Code | .claude/skills/   | ~/.claude/skills/          | ?      |
| Gemini CLI  | .gemini/skills/   | ~/.gemini/skills/          | ?      |
| OpenCode    | .opencode/skills/ | ~/.config/opencode/skills/ | ?      |
| 通用        | .agents/skills/   | ~/.agents/skills/          | ?      |

3. **我们的 Skill 设计草案**：
   - 完整的 SKILL.md 初稿（包含 frontmatter + body）
   - 多步骤工作流的编码方式
   - 质量控制规则的嵌入方式
   - 与 MCP 工具的配合说明

4. **5个优秀 Skill 的分析**：
   - 名称和来源
   - 设计亮点
   - 值得借鉴的地方
   - 渐进式加载示例

5. **兼容性建议**：
   - 如何确保一个 Skill 在所有支持的工具中都能工作
   - 需要避免的工具特定语法
   - 推荐的目录布局

6. **测试 Checklist**：
   - 如何验证 Skill 是否被正确加载
   - 如何验证 Skill 在不同工具中的行为一致性

## 质量标准

- 必须查阅至少 3 个不同 AI 工具的 Skill 文档
- Skill 设计草案必须是完整的（不是片段）
- 兼容性路径必须经过验证或引用官方文档
- 优秀 Skill 示例必须来自真实项目（有 URL）
