#!/usr/bin/env bash
# run_real_e2e.sh — Run full codebase-explorer V5 workflow via Claude Code self-invocation
# Usage: bash scripts/run_real_e2e.sh [test_repo_path]
#
# This script:
# 1. Cleans old analysis/docs for the target repo
# 2. Spawns a child Claude Code instance with codebase-explorer MCP + Skill
# 3. The child executes the full 4-Phase V5 workflow
# 4. Runs verify_real_e2e.sh to check results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_PATH="${1:-test_repos/flask}"
REPO_ABS="$(cd "$PROJECT_DIR/$REPO_PATH" 2>/dev/null && pwd)" || REPO_ABS="$PROJECT_DIR/$REPO_PATH"

LOG_DIR="$PROJECT_DIR/.cc_test_logs"
mkdir -p "$LOG_DIR"

echo "=== Codebase Explorer V5 Real E2E Test ==="
echo "Project: $PROJECT_DIR"
echo "Target:  $REPO_ABS"
echo ""

# 1. Clean old artifacts
echo "--- Step 1: Cleaning old artifacts ---"
rm -rf "$REPO_ABS/.codebase-analysis" "$REPO_ABS/.codebase-docs"
echo "Cleaned: .codebase-analysis/ and .codebase-docs/"

# 2. Build MCP config file
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

# 3. Build the V5 E2E prompt file
PROMPT_FILE="$LOG_DIR/e2e_prompt.txt"
cat > "$PROMPT_FILE" <<PROMPT_EOF
You are running a codebase-explorer V5 E2E test. Execute the FULL 4-phase documentation pipeline on the target repo. Do NOT skip any steps.

TARGET_REPO: $REPO_ABS
DOCS_DIR: $REPO_ABS/.codebase-docs

## Phase 1: Analyze
Call analyze_codebase(path="$REPO_ABS", force_reindex=true).
Wait for it to complete. Note the module count and feature cones found.

## Phase 2: Validate + Plan
Call get_modules() in summary mode to see all modules.
Check: Are there modules with > 50k tokens? Are all files assigned?
This is a quick validation — no LLM reasoning needed.

## Phase 3: Generate DETAIL for EACH module
For each module from Phase 2:

a) Call get_modules(module_id=X) to get the file list with token_count per file
b) Call doc_operation(operation="get_template") to get the DETAIL format
c) Call doc_operation(operation="get_protocol") to get the three-step protocol
d) For each file in the module:
   - Read the source code using the Read tool
   - Write the four sections:
     - 功能概述 (Purpose): What this file does and why
     - 数据流 (Data Flow): How data enters, transforms, exits
     - 核心接口 (Key Interfaces): Important functions/classes with signatures
     - 依赖关系 (Dependencies): Cross-file dependencies with specific function names
   - Call get_function_deps(file=filepath) to get cross-file function dependencies
   - Integrate dependency info into the 依赖关系 section
e) At the END of each DETAIL.md, write an index-fragment block:
   <!-- index-fragment:{module_id} -->
   **{Module Name}** (N files, N tokens) — 2-3 sentence summary of module purpose.
   Key entry points: function_name(), ClassName.
   <!-- end:index-fragment:{module_id} -->
f) Write the complete DETAIL.md to $REPO_ABS/.codebase-docs/{module_id}/DETAIL.md
   Format: YAML front matter + <!-- module:{module_id} --> + per-file sections + index-fragment + <!-- end:{module_id} --> + <!-- codebase-explorer: end -->
g) After writing docs, call submit_analysis(task_id=..., status="complete", output_files=[...])

## Phase 4: Assemble INDEX + Review & Reorganize
1. Call doc_operation(operation="update_index") to assemble INDEX.md from all DETAIL index-fragment blocks.
2. Read the generated INDEX.md. MANDATORY REVIEW:
   a) For each module, call doc_operation(operation="list_module_files", module_id=X) to see its files.
   b) Evaluate: Do the files in each module belong together functionally? Is the module name accurate?
   c) Check: Are there modules mixing framework infrastructure (typing, logging, signals) with application code?
   d) Document your review findings explicitly (e.g., "Module X looks coherent because..." or "Module Y mixes concerns because...").
3. If any module has poor cohesion or misleading name:
   - Use doc_operation("move_detail", source_module=..., target_module=..., filepath=...) to relocate misplaced files
   - Use doc_operation("merge_modules", source=..., target=...) if two modules should be combined
   - Re-run doc_operation(operation="update_index") after reorganization
4. Call submit_analysis(task_id="index_assembly", status="complete", output_files=["INDEX.md"]) to persist checkpoint.
The INDEX should have: YAML front matter + Mermaid module dependency graph + per-module summaries.

## CRITICAL RULES:
- TWO-DOCUMENT MODEL: Only INDEX.md and DETAIL.md. Do NOT create OVERVIEW.md or SNIPPET.md.
- Every DETAIL.md MUST have YAML front matter (--- ... ---)
- Every DETAIL.md MUST have <!-- module:{module_id} --> and <!-- end:{module_id} --> markers
- Every DETAIL.md MUST have <!-- file:{filepath} --> and <!-- end:file:{filepath} --> markers for EACH file
- Every DETAIL.md MUST contain <!-- index-fragment:{module_id} --> block at the end
- Every DETAIL.md MUST end with: <!-- codebase-explorer: end -->
- DETAIL per-file sections MUST include: 功能概述, 数据流, 核心接口, 依赖关系
- Use doc_operation("update_index") to assemble INDEX.md — do NOT write it manually
- INDEX.md MUST contain a mermaid code block
- Call submit_analysis for EVERY completed task
- Write real documentation based on actual source code — not placeholders
- Process ALL modules from get_modules(). Do NOT skip any.
- Generate at least 3 DETAIL.md files
- Module names in docs should be FUNCTIONAL (e.g., "Application Core", "JSON Serialization"), NOT directory names (e.g., "src/flask/")
- Call submit_analysis after completing EACH task to enable checkpoint recovery
- Token budget: check token_count per file from get_modules(module_id=X). Scale doc depth proportionally.
- Phase 4 REVIEW IS MANDATORY: You MUST call list_module_files for each module and document your review of module coherence before finalizing INDEX.
PROMPT_EOF

echo "--- Step 2: Running E2E via Claude Code self-invocation ---"
echo "This may take several minutes..."

# 4. Read prompt from file and pass to claude
E2E_PROMPT="$(cat "$PROMPT_FILE")"

env -u CLAUDECODE claude -p "$E2E_PROMPT" \
  --dangerously-skip-permissions \
  --max-turns 80 \
  --output-format json \
  --no-session-persistence \
  --model sonnet \
  --setting-sources "project" \
  --mcp-config "$MCP_CONFIG_FILE" \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep,Skill,mcp__codebase-explorer" \
  > "$LOG_DIR/real_e2e_result.json" \
  2> "$LOG_DIR/real_e2e_debug.log"

echo "Child Claude completed."

# 5. Parse result
echo ""
echo "--- Step 3: Parsing result ---"
uv run python -c "
import json
with open('$LOG_DIR/real_e2e_result.json') as f:
    d = json.load(f)
status = 'PASS' if d.get('subtype') == 'success' and not d.get('is_error') else 'FAIL'
print(f'Child Claude status: {status}')
print(f'Turns: {d.get(\"num_turns\")} | Cost: \${d.get(\"total_cost_usd\", 0):.4f}')
print(f'Duration: {d.get(\"duration_ms\", 0) / 1000:.1f}s')
if d.get('permission_denials'):
    print(f'Permission denials: {d[\"permission_denials\"]}')
if d.get('subtype') == 'error_max_turns':
    print('WARNING: Hit max turns limit. May need more turns.')
"

# 6. Run verification
echo ""
echo "--- Step 4: Verifying results ---"
bash "$SCRIPT_DIR/verify_real_e2e.sh" "$REPO_ABS"
