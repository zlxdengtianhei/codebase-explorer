#!/usr/bin/env bash
# build_judge_input.sh — Construct judge input with full evidence
# Usage: bash scripts/build_judge_input.sh [test_repo_path] > /tmp/judge_input.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_PATH="${1:-test_repos/flask}"
REPO_ABS="$(cd "$PROJECT_DIR/$REPO_PATH" 2>/dev/null && pwd)" || REPO_ABS="$PROJECT_DIR/$REPO_PATH"
ANALYSIS_DIR="$REPO_ABS/.codebase-analysis"
DOCS_DIR="$REPO_ABS/.codebase-docs"

cat <<'JUDGE_HEADER'
# Codebase-Explorer V5 Judge Evaluation

You are evaluating whether the codebase-explorer system satisfies all V5 requirements.
Read the evaluation framework below, then examine the evidence appendices.
Output STRICTLY as JSON matching the format in the framework.

JUDGE_HEADER

# Evaluation framework
cat "$PROJECT_DIR/scripts/judge_prompt.md"

# --- Appendix A: MCP Tool Response Evidence ---
echo -e "\n---\n# Appendix A: MCP Tool Response Evidence\n"

echo "## get_modules(summary) — actual response shape"
echo "The get_modules summary mode returns ONLY this structure (NO file paths, NO function names):"
echo '```json'
echo '{
  "status": "success",
  "total_modules": N,
  "total_files": N,
  "total_tokens": N,
  "grouping": {
    "strategy_used": "feature_cone",
    "available_strategies": ["feature_cone"],
    "interface": "GroupingStrategy protocol",
    "config": "Set CODEBASE_EXPLORER_STRATEGY env var to switch algorithm"
  },
  "token_budget": { "total_project_tokens": N, "budget_limit": 100000, ... },
  "modules": [
    {"module_id": "X", "name": "...", "file_count": N, "token_count": N, "layer": N, "depends_on": [...], "directory_hint": "..."}
  ],
  "infrastructure": {"file_count": N, "token_count": N}
}'
echo '```'
echo "Note: modules array contains NO file path lists, NO function names. Only metadata."
echo ""

echo "## get_modules(module_id=X) — actual response shape"
echo "The detail mode includes per-file token_count:"
echo '```json'
echo '{
  "status": "success",
  "module_id": "X",
  "files": [{"filepath": "...", "token_count": N}, ...],
  "internal_layers": [[...], ...],
  "token_count": N
}'
echo '```'
echo ""

echo "## GroupingStrategy Protocol evidence"
echo "File: src/graph/strategies.py defines:"
echo "- GroupingStrategy Protocol class with name property and group() method"
echo "- FeatureConeStrategy implementation (default)"
echo "- get_strategy(name) function for switching algorithms"
echo "- CODEBASE_EXPLORER_STRATEGY env var for configuration"
echo ""

# --- Appendix C: Generated docs ---
echo -e "---\n# Appendix C: Generated Documentation Evidence\n"

echo "## INDEX.md"
cat "$DOCS_DIR/INDEX.md" 2>/dev/null || echo "(not found)"

for f in $(find "$DOCS_DIR" -name "DETAIL.md" 2>/dev/null | sort); do
  echo -e "\n## $f"
  cat "$f"
done

# --- Appendix D: MCP Output Data ---
echo -e "\n---\n# Appendix D: MCP Output Data\n"
echo "## 03_feature_cones.json (first 200 lines)"
head -200 "$ANALYSIS_DIR/03_feature_cones.json" 2>/dev/null || echo "(not found)"
echo -e "\n## 06_function_deps.json (first 100 lines)"
head -100 "$ANALYSIS_DIR/06_function_deps.json" 2>/dev/null || echo "(not found)"

# --- Appendix E: E2E Log ---
echo -e "\n---\n# Appendix E: E2E Execution Log\n"
python3 -c "
import json
d = json.load(open('$PROJECT_DIR/.cc_test_logs/real_e2e_result.json'))
print(f'Status: {d.get(\"subtype\")}')
print(f'Turns: {d.get(\"num_turns\")}')
print(f'Cost: \${d.get(\"total_cost_usd\", 0):.4f}')
result = d.get('result', '')
if isinstance(result, list):
    for item in result:
        if isinstance(item, dict) and item.get('type') == 'text':
            result = item.get('text', '')
            break
if isinstance(result, str):
    print(f'Result preview: {result[:3000]}')
" 2>/dev/null || echo "(log not available)"

# --- Appendix F: doc_operation tool capabilities ---
echo -e "\n---\n# Appendix F: doc_operation Tool Capabilities\n"
echo "The doc_operation MCP tool supports these operations:"
echo "- get_template: Returns DETAIL.md format template"
echo "- get_protocol: Returns 3-step documentation protocol"
echo "- update_index: Scans all DETAIL.md for index-fragment blocks, assembles INDEX.md"
echo "- move_detail: Block-level move of file sections between modules"
echo "- list_module_files (alias: split_module): Lists files in a module"
echo "- merge_modules: Merge two modules"
echo "- reorder_modules: Change module order in INDEX"
