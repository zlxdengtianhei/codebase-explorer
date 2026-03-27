#!/bin/bash
# E2E 验证脚本：运行 codebase-explorer MCP 分析 + LLM Judge 评判
# 用于 autoresearch 循环的 Verify 步骤
set -e
cd /Users/lexuanzhang/code/codebase-explorer
mkdir -p .cc_test_logs

# Step 1: 跑 codebase-explorer MCP 分析 scrapy
env -u CLAUDECODE claude \
  -p "CRITICAL: You MUST output the FULL raw JSON from each tool call. DO NOT summarize. DO NOT create tables. Copy-paste the EXACT JSON.

Execute these steps and output the raw JSON return value for each:
1. analyze_codebase(path='test_repos/scrapy', force_reindex=true)
2. get_modules() (no args — summary mode)
3. Pick the module with highest file_count (exclude IDs containing testing/docs/scrapydocs) → get_modules(module_id=that_id)
4. From that module's files, pick the .py with highest token_count (exclude __init__.py) → get_function_deps(file=that_path)
5. get_dependency_graph() — for this one, output ONLY node_count, edge_count, and first 5 edges (skip full mermaid)
6. doc_operation(operation='get_template')
7. doc_operation(operation='get_protocol')
8. doc_operation(operation='merge_modules', source_module=step3_module, target_module=pick_another_from_summary)

FORMAT: For each step write STEP N then paste the COMPLETE JSON. Separate with ---. NO summaries." \
  --dangerously-skip-permissions \
  --max-turns 20 \
  --output-format json \
  --no-session-persistence \
  --model haiku \
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
