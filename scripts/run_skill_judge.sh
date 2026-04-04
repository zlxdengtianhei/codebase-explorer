#!/usr/bin/env bash
# run_skill_judge.sh — Skill-Driven E2E + Automated Judge Evaluation
#
# Unlike run_real_e2e.sh which uses a hardcoded prompt, this script tests the
# actual Skill documentation by having a child Claude read and follow it.
#
# Usage:
#   bash scripts/run_skill_judge.sh [test_repo_path]
#   bash scripts/run_skill_judge.sh test_repos/flask --skip-execute
#   bash scripts/run_skill_judge.sh test_repos/celery --execute-model sonnet --judge-model sonnet
#
# Options:
#   --skip-execute         Skip pipeline execution, judge existing artifacts only
#   --execute-model MODEL  Model for pipeline execution (default: sonnet)
#   --judge-model MODEL    Model for judge evaluation (default: sonnet)
#   --skill-dir DIR        Skill directory (default: .agents/skills/codebase-explorer)
#   --max-turns N          Max turns for execution phase (default: 80)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Parse arguments ---
REPO_PATH=""
SKIP_EXECUTE=false
EXECUTE_MODEL="sonnet"
JUDGE_MODEL="sonnet"
SKILL_DIR="$PROJECT_DIR/.agents/skills/codebase-explorer"
MAX_TURNS=80

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      echo "Usage: bash scripts/run_skill_judge.sh [repo_path] [options]"
      echo ""
      echo "Options:"
      echo "  --skip-execute         Skip pipeline execution, judge existing artifacts"
      echo "  --execute-model MODEL  Model for execution (default: sonnet)"
      echo "  --judge-model MODEL    Model for judge (default: sonnet)"
      echo "  --skill-dir DIR        Skill directory (default: .agents/skills/codebase-explorer)"
      echo "  --max-turns N          Max turns for execution (default: 80)"
      echo ""
      echo "Examples:"
      echo "  bash scripts/run_skill_judge.sh                           # Flask, full run"
      echo "  bash scripts/run_skill_judge.sh test_repos/celery         # Celery, full run"
      echo "  bash scripts/run_skill_judge.sh --skip-execute            # Judge existing artifacts"
      exit 0 ;;
    --skip-execute)     SKIP_EXECUTE=true; shift ;;
    --execute-model)    EXECUTE_MODEL="$2"; shift 2 ;;
    --judge-model)      JUDGE_MODEL="$2"; shift 2 ;;
    --skill-dir)        SKILL_DIR="$2"; shift 2 ;;
    --max-turns)        MAX_TURNS="$2"; shift 2 ;;
    -*)                 echo "Unknown option: $1"; exit 1 ;;
    *)                  REPO_PATH="$1"; shift ;;
  esac
done

REPO_PATH="${REPO_PATH:-test_repos/flask}"
REPO_ABS="$(cd "$PROJECT_DIR/$REPO_PATH" 2>/dev/null && pwd)" || REPO_ABS="$PROJECT_DIR/$REPO_PATH"

LOG_DIR="$PROJECT_DIR/.cc_test_logs"
JUDGE_DIR="$LOG_DIR/judge"
mkdir -p "$JUDGE_DIR"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPO_NAME="$(basename "$REPO_ABS")"

echo "=== Codebase Explorer V5 — Skill Judge Pipeline ==="
echo "Target:  $REPO_ABS"
echo "Skill:   $SKILL_DIR"
echo "Models:  execute=$EXECUTE_MODEL  judge=$JUDGE_MODEL"
echo "Timestamp: $TIMESTAMP"
echo ""

# --- Validate Skill directory ---
if [[ ! -f "$SKILL_DIR/SKILL.md" ]]; then
  echo "ERROR: Skill file not found at $SKILL_DIR/SKILL.md"
  exit 1
fi

###############################################################################
# PHASE 1: EXECUTE — Run Skill-driven pipeline
###############################################################################

if [[ "$SKIP_EXECUTE" == "true" ]]; then
  echo "--- Phase 1: SKIPPED (--skip-execute) ---"
  echo ""
else
  echo "--- Phase 1: Execute Skill Pipeline ---"

  # Clean old artifacts
  rm -rf "$REPO_ABS/.codebase-analysis" "$REPO_ABS/.codebase-docs"
  echo "Cleaned old artifacts."

  # Build MCP config
  MCP_CONFIG_FILE="$LOG_DIR/mcp_config.json"
  cat > "$MCP_CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "codebase-explorer": {
      "command": "uv",
      "args": ["run", "--directory", "$PROJECT_DIR", "python", "-m", "src.server"],
      "transport": "stdio"
    }
  }
}
EOF

  # Build Skill-driven prompt
  # Key difference from run_real_e2e.sh: child Claude reads and follows the
  # actual Skill documentation instead of a hardcoded prompt.
  PROMPT_FILE="$LOG_DIR/skill_e2e_prompt.txt"
  cat > "$PROMPT_FILE" <<PROMPT_EOF
You are a Claude Code agent executing a codebase documentation pipeline.
Your ONLY source of instructions is the Skill documentation files listed below.
Do NOT use any prior knowledge about codebase-explorer. Follow ONLY the Skill docs.

TARGET REPO: $REPO_ABS
OUTPUT DIR:  $REPO_ABS/.codebase-docs

## Your Task

1. Read the Skill documentation files in this exact order:
   - Main skill: $SKILL_DIR/SKILL.md
   - Phase 1: $SKILL_DIR/phases/phase1-analysis.md
   - Phase 2: $SKILL_DIR/phases/phase2-validation.md
   - Phase 3: $SKILL_DIR/phases/phase3-detail.md
   - Phase 4: $SKILL_DIR/phases/phase4-index.md
   - Templates: $SKILL_DIR/references/DOC_TEMPLATES.md

2. Execute the complete 4-phase pipeline as described in SKILL.md.

3. For Phase 3, if the Skill says to spawn sub-agents, you may process modules
   sequentially instead (sub-agent spawning is optional in test mode).

4. After completing all phases, write a brief execution summary to stdout.

## Critical Rules

- Follow the Skill documentation EXACTLY as written.
- Do not skip any phase or step described in the Skill.
- This is a test of the Skill documentation quality — ambiguities or errors
  in the Skill will be evaluated as part of the judge process.
- Use the codebase-explorer MCP tools as instructed by the Skill.
- Write real documentation based on actual source code analysis.
PROMPT_EOF

  echo "Spawning child Claude (model=$EXECUTE_MODEL, max_turns=$MAX_TURNS)..."
  EXEC_START="$(date +%s)"

  E2E_PROMPT="$(cat "$PROMPT_FILE")"

  # Allow execution to fail — we still want to judge whatever was produced
  env -u CLAUDECODE claude -p "$E2E_PROMPT" \
    --dangerously-skip-permissions \
    --max-turns "$MAX_TURNS" \
    --output-format json \
    --no-session-persistence \
    --model "$EXECUTE_MODEL" \
    --setting-sources "project" \
    --mcp-config "$MCP_CONFIG_FILE" \
    --allowedTools "Read,Write,Edit,Bash,Glob,Grep,Skill,Agent,mcp__codebase-explorer" \
    > "$LOG_DIR/skill_e2e_result.json" \
    2> "$LOG_DIR/skill_e2e_debug.log" \
    || true

  EXEC_END="$(date +%s)"
  EXEC_DURATION=$((EXEC_END - EXEC_START))

  echo "Child Claude completed in ${EXEC_DURATION}s."

  # Parse execution result
  uv run python -c "
import json, sys
with open('$LOG_DIR/skill_e2e_result.json') as f:
    d = json.load(f)
status = 'PASS' if d.get('subtype') == 'success' and not d.get('is_error') else 'FAIL'
print(f'  Status: {status}')
print(f'  Turns:  {d.get(\"num_turns\")}')
print(f'  Cost:   \${d.get(\"total_cost_usd\", 0):.4f}')
if d.get('subtype') == 'error_max_turns':
    print('  WARNING: Hit max turns limit!')
" || echo "  (result parsing failed)"
  echo ""
fi

###############################################################################
# PHASE 2: VERIFY — Run filesystem verification
###############################################################################

echo "--- Phase 2: Verify Artifacts ---"
# Allow verify to fail without aborting — failures are captured for the judge
bash "$SCRIPT_DIR/verify_real_e2e.sh" "$REPO_ABS" 2>&1 | tee "$JUDGE_DIR/verify_${REPO_NAME}_${TIMESTAMP}.txt" || true
echo ""

###############################################################################
# PHASE 3: BUILD JUDGE INPUT — Collect all evidence + Skill docs
###############################################################################

echo "--- Phase 3: Build Judge Input ---"

JUDGE_INPUT="$JUDGE_DIR/judge_input_${REPO_NAME}_${TIMESTAMP}.md"
ANALYSIS_DIR="$REPO_ABS/.codebase-analysis"
DOCS_DIR="$REPO_ABS/.codebase-docs"

{
  # Header
  cat <<'JUDGE_HEADER'
# Codebase-Explorer V5 Skill Judge Evaluation

You are evaluating whether the codebase-explorer Skill documentation correctly
guided an Agent to produce architecture documentation that satisfies all V5
requirements. This is a Skill quality test — failures may indicate problems
in the Skill docs, not just the Agent.

Read the evaluation framework, examine the evidence appendices, then output
STRICTLY as JSON matching the format in the framework.

JUDGE_HEADER

  # Evaluation framework
  cat "$SCRIPT_DIR/skill_judge_prompt.md"

  # --- Appendix A: MCP Tool Response Evidence ---
  echo -e "\n---\n# Appendix A: MCP Tool Response Evidence\n"
  echo "## get_modules(summary) — expected response shape"
  echo '```json'
  echo '{
  "status": "success",
  "total_modules": N,
  "total_files": N,
  "total_tokens": N,
  "grouping": {"strategy_used": "feature_cone", "available_strategies": ["feature_cone"]},
  "token_budget": {"total_project_tokens": N, "budget_limit": 100000},
  "modules": [{"module_id": "X", "name": "...", "file_count": N, "token_count": N, "layer": N, "depends_on": [...]}]
}'
  echo '```'
  echo "Note: modules array contains NO file path lists, NO function names. Only metadata."
  echo ""

  echo "## GroupingStrategy Protocol evidence"
  echo "File: src/graph/strategies.py defines GroupingStrategy Protocol + FeatureConeStrategy."
  echo ""

  # --- Appendix B: Generated Documentation ---
  echo -e "---\n# Appendix B: Generated Documentation\n"
  echo "## INDEX.md"
  if [[ -f "$DOCS_DIR/INDEX.md" ]]; then
    cat "$DOCS_DIR/INDEX.md"
  else
    echo "(INDEX.md not found — CRITICAL FAILURE)"
  fi

  for f in $(find "$DOCS_DIR" -name "DETAIL.md" 2>/dev/null | sort); do
    echo -e "\n## $f"
    cat "$f"
  done

  # --- Appendix C: MCP Output Data ---
  echo -e "\n---\n# Appendix C: MCP Output Data\n"
  echo "## 03_feature_cones.json (first 200 lines)"
  head -200 "$ANALYSIS_DIR/03_feature_cones.json" 2>/dev/null || echo "(not found)"
  echo -e "\n## 06_function_deps.json (first 100 lines)"
  head -100 "$ANALYSIS_DIR/06_function_deps.json" 2>/dev/null || echo "(not found)"
  echo -e "\n## state.json"
  cat "$ANALYSIS_DIR/state.json" 2>/dev/null || echo "(not found)"

  # --- Appendix D: Execution Log ---
  echo -e "\n---\n# Appendix D: Execution Log\n"
  E2E_LOG="$LOG_DIR/skill_e2e_result.json"
  if [[ -f "$E2E_LOG" ]]; then
    python3 -c "
import json
d = json.load(open('$E2E_LOG'))
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
    print(f'Result preview (first 3000 chars):\n{result[:3000]}')
" 2>/dev/null || echo "(log parsing failed)"
  else
    echo "(no execution log — using --skip-execute?)"
  fi

  # --- Appendix E: Verification Results ---
  echo -e "\n---\n# Appendix E: Verification Results\n"
  VERIFY_LOG="$JUDGE_DIR/verify_${REPO_NAME}_${TIMESTAMP}.txt"
  if [[ -f "$VERIFY_LOG" ]]; then
    cat "$VERIFY_LOG"
  else
    echo "(no verify log)"
  fi

  # --- Appendix F: Skill Documentation (for Skill-specific evaluation) ---
  echo -e "\n---\n# Appendix F: Skill Documentation\n"
  echo "## SKILL.md (master)"
  cat "$SKILL_DIR/SKILL.md"
  echo -e "\n## phase3-detail.md"
  cat "$SKILL_DIR/phases/phase3-detail.md"
  echo -e "\n## phase4-index.md"
  cat "$SKILL_DIR/phases/phase4-index.md"
  echo -e "\n## DOC_TEMPLATES.md"
  cat "$SKILL_DIR/references/DOC_TEMPLATES.md"
  echo -e "\n## QUALITY_STANDARDS.md"
  cat "$SKILL_DIR/references/QUALITY_STANDARDS.md"

  # --- Appendix G: Full-Quantity Section Verification ---
  echo -e "\n---\n# Appendix G: Full-Quantity Section Verification\n"
  echo "Automated count of section headers in every DETAIL.md file block."
  echo "This data is AUTHORITATIVE — use it for R5, R5b, P3, S2, S5 evaluation."
  echo ""
  uv run python "$SCRIPT_DIR/count_sections.py" "$REPO_ABS" 2>/dev/null || echo "(count_sections.py failed)"
  echo ""
  echo "## Machine-readable summary"
  uv run python "$SCRIPT_DIR/count_sections.py" "$REPO_ABS" --json 2>/dev/null || echo "{}"

} > "$JUDGE_INPUT"

JUDGE_SIZE=$(wc -c < "$JUDGE_INPUT" | tr -d ' ')
echo "Judge input built: $JUDGE_INPUT ($JUDGE_SIZE bytes)"
echo ""

###############################################################################
# PHASE 4: JUDGE — Run LLM judge evaluation
###############################################################################

echo "--- Phase 4: Run Judge Evaluation ---"

JUDGE_OUTPUT="$JUDGE_DIR/judge_result_${REPO_NAME}_${TIMESTAMP}.json"

echo "Spawning judge Claude (model=$JUDGE_MODEL)..."
JUDGE_START="$(date +%s)"

JUDGE_PROMPT="$(cat "$JUDGE_INPUT")"

env -u CLAUDECODE claude -p "$JUDGE_PROMPT" \
  --dangerously-skip-permissions \
  --max-turns 5 \
  --output-format json \
  --no-session-persistence \
  --model "$JUDGE_MODEL" \
  --setting-sources "project" \
  > "$JUDGE_DIR/judge_raw_${REPO_NAME}_${TIMESTAMP}.json" \
  2> "$JUDGE_DIR/judge_debug_${REPO_NAME}_${TIMESTAMP}.log"

JUDGE_END="$(date +%s)"
JUDGE_DURATION=$((JUDGE_END - JUDGE_START))
echo "Judge completed in ${JUDGE_DURATION}s."

# Extract the judge JSON from Claude's response
uv run python -c "
import json, re, sys

with open('$JUDGE_DIR/judge_raw_${REPO_NAME}_${TIMESTAMP}.json') as f:
    raw = json.load(f)

result = raw.get('result', '')
if isinstance(result, list):
    for item in result:
        if isinstance(item, dict) and item.get('type') == 'text':
            result = item.get('text', '')
            break

# Extract JSON from markdown code blocks or raw text
json_match = re.search(r'\`\`\`(?:json)?\s*(\{.*?\})\s*\`\`\`', result, re.DOTALL)
if json_match:
    judge_json = json.loads(json_match.group(1))
else:
    # Try parsing the entire result as JSON
    judge_json = json.loads(result)

with open('$JUDGE_OUTPUT', 'w') as f:
    json.dump(judge_json, f, indent=2, ensure_ascii=False)
print(f'Judge result saved: $JUDGE_OUTPUT')
" || {
  echo "ERROR: Failed to extract judge JSON. Raw output saved at:"
  echo "  $JUDGE_DIR/judge_raw_${REPO_NAME}_${TIMESTAMP}.json"
  echo "You can inspect the raw response and manually extract the JSON."
  exit 1
}

echo ""

###############################################################################
# PHASE 5: REPORT — Parse and display results
###############################################################################

echo "--- Phase 5: Results Report ---"
echo ""

uv run python "$SCRIPT_DIR/parse_judge_result.py" "$JUDGE_OUTPUT"

EXIT_CODE=$?

# Save a copy with latest symlink for convenience
cp "$JUDGE_OUTPUT" "$JUDGE_DIR/judge_result_${REPO_NAME}_latest.json"

echo ""
echo "=== Artifacts ==="
echo "  Execution log:  $LOG_DIR/skill_e2e_result.json"
echo "  Verify log:     $JUDGE_DIR/verify_${REPO_NAME}_${TIMESTAMP}.txt"
echo "  Judge input:    $JUDGE_INPUT"
echo "  Judge result:   $JUDGE_OUTPUT"
echo "  Latest symlink: $JUDGE_DIR/judge_result_${REPO_NAME}_latest.json"

exit $EXIT_CODE
