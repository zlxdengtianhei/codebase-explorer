#!/bin/bash
# E2E 验证脚本：运行 codebase-explorer MCP 分析 + LLM Judge 评判
# 用于 autoresearch 循环的 Verify 步骤
set -e
cd "$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p .cc_test_logs

# Step 1: 跑 codebase-explorer MCP 分析 scrapy
env -u CLAUDECODE claude \
  -p "你是 E2E 测试器。依次调用以下 8 个工具，收集所有返回值，最后一次性输出。

调用顺序：
1. analyze_codebase(path='test_repos/scrapy', force_reindex=true)
2. get_modules()
3. 选 file_count 最大且 module_id 不含 testing/docs/scrapydocs 的模块 → get_modules(module_id=该ID)
4. 选 token_count 最大的 .py（排除 __init__.py）→ get_function_deps(file=该路径)
5. get_dependency_graph()
6. doc_operation(operation='get_template')
7. doc_operation(operation='get_protocol')
8. doc_operation(operation='merge_modules', source_module=步骤3的模块ID, target_module=从步骤2选另一个模块)

【关键】你的最终输出必须包含每个步骤的完整 JSON 返回值。格式：每步写 STEP N，然后贴完整 JSON。对于步骤5，只贴 node_count、edge_count 和前5条边（跳过完整 mermaid 图）。不要用表格总结，必须贴原始 JSON。" \
  --dangerously-skip-permissions \
  --max-turns 20 \
  --output-format json \
  --no-session-persistence \
  --model haiku \
  --setting-sources "" \
  --mcp-config '{"mcpServers":{"codebase-explorer":{"command":".venv/bin/python","args":["-m","src.server"],"cwd":"'"$PWD"'"}}}' \
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
  --max-turns 5 \
  --output-format json \
  --no-session-persistence \
  --model haiku \
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
