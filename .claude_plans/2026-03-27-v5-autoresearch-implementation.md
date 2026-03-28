# V5 实施计划 — autoresearch 驱动

> **Context 恢复协议**（Context 压缩后的新 Agent 必读）：
>
> 1. 读此文件的 **Checkpoint** 区块，了解当前状态
> 2. 读 `.cc_test_logs/experiment_log.tsv` 了解历史迭代（哪些 keep、哪些 discard）
> 3. 读 `.cc_test_logs/judge_result.json` 了解上次 Judge 的具体 FAIL 项
> 4. 调用 **`/autoresearch`** skill，传入以下预填配置：
>    - **Goal**: "实施 V5 MCP Skill Redesign，使 LLM Judge 评分达到 13/16"
>    - **Scope**: `src/**/*.py, .agents/skills/codebase-explorer/SKILL.md`
>    - **Metric**: Judge pass count（从 `.cc_test_logs/judge_result.json` 提取）
>    - **Direction**: higher
>    - **Verify**: 见下方"Verify 命令"区块（E2E 自调用 + Judge 自调用）
>    - **Guard**: `.venv/bin/python -m pytest tests/ -x -q`
>    - **Iterations**: unbounded（stop 条件见下方）
> 5. `/autoresearch` 的 setup gate 会问这些问题——用上述值直接回答，不需要问用户
> 6. 循环从 Checkpoint 的 `iteration` 编号继续，不从 0 开始
>
> **关键文件位置**：
> - 设计文档: `optimization_prompts/results/06_v5_mcp_skill_redesign.md`
> - 愿景文档: `optimization_prompts/organized/00_vision_and_requirements.md`
> - Judge prompt: `scripts/judge_prompt.md`
> - 实验日志: `.cc_test_logs/experiment_log.tsv`
> - 自调用指南: `~/contexts/rules/skills/claude_code_self_invocation.md`

---

## Checkpoint

```yaml
phase: 1
status: iterating
iteration: 3
best_judge_score: 9/16
last_commit: 08053d2
consecutive_discards: 0
last_fail_items: [R2, R4, R5, R6, R7, R8, R9]
```

> **Checkpoint 更新规则**：每次 autoresearch 迭代结束后，agent 必须用 Edit 工具更新此区块。
> 这是跨 session 恢复的唯一依据。Context 压缩后新 agent 读此区块即可恢复。

---

## 目标

将 V5 设计文档（`optimization_prompts/results/06_v5_mcp_skill_redesign.md`）落地实施，使 codebase-explorer 生成的架构文档满足用户愿景。

## 核心引用

- 设计文档: `optimization_prompts/results/06_v5_mcp_skill_redesign.md`
- 愿景文档: `optimization_prompts/organized/00_vision_and_requirements.md`
- 自调用指南: `~/contexts/rules/skills/claude_code_self_invocation.md`

---

## autoresearch 配置

> 以下配置直接对应 `/autoresearch` setup gate 的 6 个字段。
> 恢复 session 时，用这些值回答 setup gate 的提问。

```yaml
Goal: "实施 V5 MCP Skill Redesign，使 LLM Judge 评分从 0/16 提升到 13/16 (80%)"
Scope: "src/**/*.py, .agents/skills/codebase-explorer/SKILL.md, .agents/skills/codebase-explorer/references/*"
Metric: "Judge pass count（0-16 整数，从 .cc_test_logs/judge_result.json 提取）"
Direction: higher
Guard: ".venv/bin/python -m pytest tests/ -x -q"
Stop: "Judge >= 13/16 (80%) OR 连续 5 次 discard"
```

### Verify 命令

```bash
#!/bin/bash
# 此脚本应保存为 scripts/verify_e2e.sh 并 chmod +x
set -e
cd /Users/lexuanzhang/code/codebase-explorer
mkdir -p .cc_test_logs

# Step 1: 跑 codebase-explorer MCP 分析 scrapy
env -u CLAUDECODE claude \
  -p "你是 codebase-explorer 的 E2E 测试器。请依次执行以下操作并汇总所有结果：
1. 调用 analyze_codebase(path='test_repos/scrapy')
2. 调用 get_modules()（无参数，获取 summary）
3. 从 summary 中选第一个模块，调用 get_modules(module_id=该模块ID)
4. 从该模块的文件列表中选第一个 .py 文件，调用 get_function_deps(file=该文件)
5. 调用 get_dependency_graph()（默认 scope=project）
将每一步的完整返回结果原样输出，用 --- 分隔。" \
  --dangerously-skip-permissions \
  --max-turns 12 \
  --output-format json \
  --no-session-persistence \
  --model sonnet \
  --setting-sources "" \
  --mcp-config '{"mcpServers":{"codebase-explorer":{"command":".venv/bin/python","args":["-m","src.server"],"cwd":"/Users/lexuanzhang/code/codebase-explorer"}}}' \
  --allowedTools "mcp__codebase-explorer" \
  > .cc_test_logs/e2e_result.json 2> .cc_test_logs/e2e_debug.log

# Step 2: 提取 E2E 结果文本
E2E_OUTPUT=$(python3 -c "
import json
with open('.cc_test_logs/e2e_result.json') as f:
    d = json.load(f)
print(d.get('result', 'ERROR: no result'))
")

# Step 3: Judge 评判
env -u CLAUDECODE claude \
  -p "$(cat scripts/judge_prompt.md)

---

## 被评审的 codebase-explorer 输出

${E2E_OUTPUT}" \
  --dangerously-skip-permissions \
  --max-turns 3 \
  --output-format json \
  --no-session-persistence \
  --model sonnet \
  --setting-sources "" \
  > .cc_test_logs/judge_result.json 2> .cc_test_logs/judge_debug.log

# Step 4: 提取并输出 pass count
python3 -c "
import json, re
with open('.cc_test_logs/judge_result.json') as f:
    d = json.load(f)
result_text = d.get('result', '')
# 尝试从 JSON 输出中提取 pass count
pass_count = result_text.count('\"verdict\": \"PASS\"') + result_text.count('\"verdict\":\"PASS\"')
# fallback: 搜索 PASS 关键词
if pass_count == 0:
    pass_count = len(re.findall(r'\bPASS\b', result_text))
total = 16
print(f'{pass_count}')
"
```

### Verify 命令（简化版，用于 autoresearch 的 Verify 字段）

```
bash scripts/verify_e2e.sh
```

> **注意**：首次运行前必须先创建 `scripts/judge_prompt.md`（见本文件底部"Judge 评判标准"区块）和 `scripts/verify_e2e.sh`（上方脚本）。

---

## 优化方向（不是具体步骤）

autoresearch 循环中，agent 按以下优先级方向进行改进。每次迭代只做一个原子改动。

### Phase 1: MCP 输出治理（让 Judge 的 R1, R3, R9, R10 通过）

**方向**：MCP 输出从"全量 dump"转变为"分级过滤"。

- 智能排除 .venv/ 等非代码目录（当前索引 12907 文件 → 应降至 ~400）
- 实现可插拔的分类算法接口（GroupingStrategy Protocol）
- get_feature_cones → get_modules，支持 summary/detail 两种模式
- Summary 模式只返回模块元信息（<3KB），不返回文件列表
- Detail 模式只返回单个模块的文件，不泄露其他模块
- get_dependency_graph 默认返回模块级图（~10 节点），非文件级（~1000 节点）

**参考**: V5 §2.2.1-§2.2.5

### Phase 2: 函数级依赖 + 文档格式（让 R2, R5, R7 通过）

**方向**：MCP 提供函数级依赖数据，Skill 定义固定文档格式。

- 新增 get_function_deps 工具（现有 parser 已提取函数调用关系，只需暴露为 MCP tool）
- 修复 parser 中 calls↔dependencies 的配对关系
- DETAIL 文件使用固定格式（YAML front matter + HTML comment 标记）
- INDEX 文件使用固定格式（模块级 Mermaid 图 + 模块摘要块）
- Sub-agent 逐文件三步输出：函数描述 → 依赖关系 → INDEX 片段

**参考**: V5 §2.2.2, §2.3, §2.4

### Phase 3: Skill 执行协议 + Phase 5 工具化（让 R4, R6, R8 通过）

**方向**：Sub-agent 按 token 预算渐进读码，Phase 5 通过工具重组文档。

- Token 预算驱动的 sub-agent 协议写入 SKILL.md
- INDEX 由 DETAIL 片段直接拼合（Phase 4）
- doc_operation MCP tool（move_detail, merge_modules, split_module, update_index, reorder_modules）
- Phase 5 重组 agent 通过 doc_operation 操作，不手动编辑文本
- 操作顺序：先 DETAIL 后 INDEX

**参考**: V5 §2.4, §2.5, §2.2.6

### Phase 4: 愿景对齐（让 V1-V6 通过）

**方向**：确保最终产出满足愿景的 6 大设计原则。

- 功能优先、层级内嵌（不忠于原始文件树）
- MCP 确定性分析 vs Agent 语义理解，职责分离
- 渐进式披露（INDEX → DETAIL）
- 依赖关系贯穿文档
- 服务 vibe coding 的 AI Agent
- 每步持久化，断点可恢复

**参考**: 00_vision §三

---

## 循环协议

> 此协议与 `/autoresearch` skill 的 Phase 1-8 完全对齐。
> 当你调用 `/autoresearch` 时，它会自动执行此循环。
> 此处显式写出是为了 Context 恢复时的参考——如果 `/autoresearch` 因某种原因不可用，
> 可以手动按此协议执行。

### 前置（首次执行，只做一次）

```bash
mkdir -p .cc_test_logs scripts
# 创建 scripts/judge_prompt.md（内容见本文件底部"Judge 评判标准"区块）
# 创建 scripts/verify_e2e.sh（内容见上方"Verify 命令"区块）
chmod +x scripts/verify_e2e.sh
```

### 循环（/autoresearch 自动驱动）

```
Phase 1 — Review（每次迭代开头）:
  - git log --oneline -20                    ← 看最近改了什么，哪些 keep 哪些 revert
  - git diff HEAD~1                          ← 看上一个 keep 的改动是什么
  - cat .cc_test_logs/judge_result.json      ← 上次 Judge 的具体 FAIL 项
  - cat .cc_test_logs/experiment_log.tsv     ← 历史记录，避免重复已 discard 的方向

Phase 2 — Ideate:
  - 从 Judge 的 FAIL 项中选一个最容易改善的
  - 参考对应的优化方向（Phase 1-4）和 V5 设计文档
  - 确定一个原子改动（一句话能说清楚）
  - 优先级: fix crash > 利用上次 keep 的动量 > 探索新方向 > 组合

Phase 3 — Modify:
  - 实现改动（一个文件或少数紧密相关的文件）
  - 如果描述需要"和"，拆成两次迭代

Phase 4 — Commit（验证前提交）:
  - git add <specific files>（永远不用 git add -A）
  - git commit -m "experiment(v5): <一句话描述>"

Phase 5 — Guard:
  - .venv/bin/python -m pytest tests/ -x -q
  - FAIL → 修复（最多 3 次尝试），修不好 → git revert HEAD --no-edit → 进 Phase 2

Phase 6 — Verify:
  - bash scripts/verify_e2e.sh
  - 提取 pass count（0-16 整数）

Phase 7 — Decide:
  - pass count 增加 → keep
  - pass count 持平但修复了 Judge 指出的关键 gap → keep
  - pass count 下降 → git revert HEAD --no-edit → log "discard"
  - crash / 无法 verify → 修复（最多 3 次），修不好 → revert → log "crash"

Phase 8 — Log + Update:
  - 追加到 .cc_test_logs/experiment_log.tsv:
    iteration | commit_hash | pass_count | status(keep/discard/crash) | description
  - Edit 本文件的 Checkpoint 区块:
    - iteration += 1
    - best_judge_score = max(current, previous)
    - last_commit = HEAD hash
    - consecutive_discards = 0 (if keep) or += 1 (if discard)
    - last_fail_items = [Judge 本次 FAIL 的 requirement IDs]
  - 继续 Phase 1

停止条件:
  - pass count >= 13/16 (80%) → 退出循环，进入最终验收
  - consecutive_discards >= 5 → 停止，向用户报告当前状态和建议
  - 用户主动中断
```

### Context 耗尽时的自动保存

当 agent 检测到 Context 接近上限（系统警告、token > 80%、对话 > 20 轮）：

1. **立即更新 Checkpoint**（Edit 本文件的 Checkpoint 区块）
2. **确保 experiment_log.tsv 已写入最新迭代**
3. **输出恢复指令**：
   ```
   Context 即将耗尽。当前状态已保存到 Checkpoint。
   恢复方法：/clear 后执行以下 prompt——

   "读取计划文件 .claude_plans/2026-03-27-v5-autoresearch-implementation.md，
   按其 Context 恢复协议继续执行。调用 /autoresearch 继续迭代循环。"
   ```
4. 停止当前执行

---

## 最终验收

当 Scrapy 上的 Judge 达到 80% 后，对全部 5 个 repo 进行验证：

```bash
for repo in flask rich celery scrapy fastapi; do
  # 替换 Verify 中的 scrapy 为 $repo
  # 运行 E2E + Judge
  # 产出 .cc_test_logs/final/${repo}_judge.json
done
```

输出：per-requirement × per-repo 的 pass/fail 矩阵。

验收标准：总体 pass rate ≥ 80%。

---

## Judge 评判标准（写入 scripts/judge_prompt.md）

16 条评判项，每条 PASS 或 FAIL：

**MCP 输出 (R1-R10)**:
- R1: MCP 输出只有文件→模块映射，无函数名/签名/描述
- R2: 可获取跨文件函数级依赖关系
- R3: 主 Agent 收到的模块摘要 < 3KB，不包含文件列表
- R4: 有 token 预算机制，sub-agent 不会上下文溢出
- R5: DETAIL 逐文件三步输出（函数描述→依赖→INDEX 片段）
- R6: INDEX 由片段直接拼合
- R7: DETAIL/INDEX 有固定格式（YAML front matter + HTML comment 标记）
- R8: Phase 5 通过 doc_operation 工具操作，不手动编辑
- R9: 分类算法可插拔（GroupingStrategy 接口）
- R10: 文件按功能模块分类，不完全忠于原始文件树

**愿景对齐 (V1-V6)**:
- V1: 功能优先、层级内嵌
- V2: 确定性分析 vs 语义理解，职责分离
- V3: 渐进式披露结构
- V4: 依赖关系贯穿文档
- V5: 服务 vibe coding AI Agent
- V6: 每步持久化，断点可恢复
