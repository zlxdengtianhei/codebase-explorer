#!/bin/bash
# E2E 验证脚本：运行 codebase-explorer MCP 分析 + LLM Judge 评判
# 用于 autoresearch 循环的 Verify 步骤
set -e
cd /Users/lexuanzhang/code/codebase-explorer
mkdir -p .cc_test_logs

# Step 1: 跑 codebase-explorer MCP 分析 scrapy
env -u CLAUDECODE claude \
  -p "你是 codebase-explorer 的 E2E 测试器。请依次执行以下操作并汇总所有结果：
1. 调用 analyze_codebase(path='test_repos/scrapy', force_reindex=true)
2. 调用 get_modules()（无参数，获取 summary）。注意观察 grouping 和 token_budget 字段。
3. 从 summary 的 modules 列表中，选 file_count 最大且 module_id 不含 testing/docs/scrapydocs 的模块，调用 get_modules(module_id=该模块ID)
4. 从该模块详情的 files 列表中，选 token_count 最大的 .py 文件（排除 __init__.py），调用 get_function_deps(file=该文件)
5. 调用 get_dependency_graph()（默认 scope=project）
6. 调用 doc_operation(operation='get_template') 获取 DETAIL/INDEX 格式模板
7. 调用 doc_operation(operation='get_protocol') 获取三步协议
将每一步的完整返回结果原样输出，用 --- 分隔。" \
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
