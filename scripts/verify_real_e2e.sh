#!/usr/bin/env bash
# verify_real_e2e.sh — V5 file-system-level verification for codebase-explorer E2E
# Usage: bash scripts/verify_real_e2e.sh [test_repo_path]
# Returns: X/18 score + exit code (0 = all pass, 1 = some fail)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_PATH="${1:-test_repos/flask}"
REPO_PATH="$(cd "$REPO_PATH" 2>/dev/null && pwd)" || { echo "FAIL: Repo path not found: $1"; exit 1; }

ANALYSIS_DIR="$REPO_PATH/.codebase-analysis"
DOCS_DIR="$REPO_PATH/.codebase-docs"

PASS=0
FAIL=0
TOTAL=18

check() {
    local id="$1" desc="$2" result="$3"
    if [ "$result" = "true" ]; then
        echo "  PASS  $id: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $id: $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Codebase Explorer V5 E2E Verification ==="
echo "Repo: $REPO_PATH"
echo ""

# R1: .codebase-analysis/ exists with 7 JSON files (6 analysis + state.json)
r1="false"
if [ -d "$ANALYSIS_DIR" ]; then
    count=0
    for f in 01_structure.json 02_dag.json 03_feature_cones.json 04_file_tokens.json 05_task_manifest.json 06_function_deps.json state.json; do
        [ -f "$ANALYSIS_DIR/$f" ] && count=$((count + 1))
    done
    [ "$count" -ge 7 ] && r1="true"
fi
check "R1" ".codebase-analysis/ exists with 7 JSON files (incl. 06_function_deps.json)" "$r1"

# R2: .codebase-docs/INDEX.md exists and >500 bytes
r2="false"
if [ -f "$DOCS_DIR/INDEX.md" ]; then
    size=$(wc -c < "$DOCS_DIR/INDEX.md")
    [ "$size" -gt 500 ] && r2="true"
fi
check "R2" "INDEX.md exists and >500 bytes ($([ -f "$DOCS_DIR/INDEX.md" ] && wc -c < "$DOCS_DIR/INDEX.md" || echo 0) bytes)" "$r2"

# R3: At least 3 DETAIL.md files with index-fragment blocks (V5: replaces OVERVIEW check)
r3="false"
frag_count=0
if [ -d "$DOCS_DIR" ]; then
    while IFS= read -r -d '' f; do
        grep -q '<!-- index-fragment:' "$f" && frag_count=$((frag_count + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$frag_count" -ge 3 ] && r3="true"
fi
check "R3" "At least 3 DETAIL.md with index-fragment blocks ($frag_count found)" "$r3"

# R4: At least 3 DETAIL.md files, each >200 bytes
r4="false"
detail_count=0
if [ -d "$DOCS_DIR" ]; then
    while IFS= read -r -d '' f; do
        size=$(wc -c < "$f")
        [ "$size" -gt 200 ] && detail_count=$((detail_count + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$detail_count" -ge 3 ] && r4="true"
fi
check "R4" "At least 3 DETAIL.md files >200 bytes ($detail_count found)" "$r4"

# R5: All DETAIL.md contain end marker
r5="false"
if [ "$detail_count" -gt 0 ]; then
    total_details=0
    marked_details=0
    while IFS= read -r -d '' f; do
        total_details=$((total_details + 1))
        grep -q "codebase-explorer: end" "$f" && marked_details=$((marked_details + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$total_details" -gt 0 ] && [ "$total_details" -eq "$marked_details" ] && r5="true"
fi
check "R5" "All DETAIL.md have end marker ($marked_details/${total_details:-0})" "$r5"

# R6: state.json has >=50% tasks complete
r6="false"
if [ -f "$ANALYSIS_DIR/state.json" ]; then
    r6=$(uv run python -c "
import json
state = json.load(open('$ANALYSIS_DIR/state.json'))
tasks = state.get('tasks', {})
if not tasks:
    print('false')
else:
    complete = sum(1 for t in tasks.values() if t.get('status') == 'complete')
    pct = complete / len(tasks) * 100
    print('true' if pct >= 50 else 'false')
" 2>/dev/null || echo "false")
fi
check "R6" "state.json >=50% tasks complete" "$r6"

# R7: INDEX.md contains Mermaid block
r7="false"
if [ -f "$DOCS_DIR/INDEX.md" ]; then
    grep -q '```mermaid' "$DOCS_DIR/INDEX.md" && r7="true"
fi
check "R7" "INDEX.md contains Mermaid diagram" "$r7"

# R8: Inter-module dep_count sum > 0
r8="false"
if [ -f "$ANALYSIS_DIR/02_dag.json" ] && [ -f "$ANALYSIS_DIR/03_feature_cones.json" ]; then
    r8=$(cd "$(cd "$(dirname "$0")/.." && pwd)" && uv run python -c "
import json, sys
from src.server_helpers import compute_inter_module_deps_from_dag

cones = json.load(open('$ANALYSIS_DIR/03_feature_cones.json')).get('cones', {})
edges = json.load(open('$ANALYSIS_DIR/02_dag.json')).get('edges', [])
deps = compute_inter_module_deps_from_dag(cones, edges)
total = sum(len(v) for v in deps.values())
print('true' if total > 0 else 'false')
" 2>/dev/null || echo "false")
fi
check "R8" "Inter-module dep_count sum > 0" "$r8"

# R9: Module-level graph node_count < 50
r9="false"
if [ -f "$ANALYSIS_DIR/03_feature_cones.json" ]; then
    r9=$(uv run python -c "
import json
cones = json.load(open('$ANALYSIS_DIR/03_feature_cones.json')).get('cones', {})
print('true' if 0 < len(cones) < 50 else 'false')
" 2>/dev/null || echo "false")
fi
check "R9" "Module-level graph has <50 nodes" "$r9"

# R10: All DETAIL.md contain <!-- file:{filepath} --> markers
r10="false"
if [ "${detail_count:-0}" -gt 0 ]; then
    file_marked=0
    while IFS= read -r -d '' f; do
        grep -q '<!-- file:' "$f" && file_marked=$((file_marked + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$file_marked" -gt 0 ] && [ "$file_marked" -eq "${total_details:-0}" ] && r10="true"
fi
check "R10" "All DETAIL.md have <!-- file:xxx --> markers (${file_marked:-0}/${total_details:-0})" "$r10"

# R11: All DETAIL.md contain <!-- module:{module_id} --> markers
r11="false"
if [ "${detail_count:-0}" -gt 0 ]; then
    mod_marked=0
    while IFS= read -r -d '' f; do
        grep -q '<!-- module:' "$f" && mod_marked=$((mod_marked + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$mod_marked" -gt 0 ] && [ "$mod_marked" -eq "${total_details:-0}" ] && r11="true"
fi
check "R11" "All DETAIL.md have <!-- module:xxx --> markers (${mod_marked:-0}/${total_details:-0})" "$r11"

# R12: INDEX.md contains >= 3 <!-- module-index:{id} --> markers
r12="false"
if [ -f "$DOCS_DIR/INDEX.md" ]; then
    mi_count=$(grep -c '<!-- module-index:' "$DOCS_DIR/INDEX.md" 2>/dev/null || true)
    mi_count=${mi_count:-0}
    [ "$mi_count" -ge 3 ] && r12="true"
fi
check "R12" "INDEX.md has >=3 module-index markers (${mi_count:-0} found)" "$r12"

# R13: Parser excludes .venv/node_modules/__pycache__/.git
r13="false"
if grep -q '_EXCLUDED_DIRS' "$SCRIPT_DIR/../src/parser/codebase.py" 2>/dev/null; then
    r13="true"
fi
check "R13" "Parser has _EXCLUDED_DIRS path exclusion" "$r13"

# R14: run_real_e2e.sh does NOT contain --setting-sources ""
r14="false"
if ! grep -q 'setting-sources ""' "$SCRIPT_DIR/run_real_e2e.sh" 2>/dev/null; then
    r14="true"
fi
check "R14" "run_real_e2e.sh loads Skill (no --setting-sources \"\")" "$r14"

# R15: >= 10 unit tests covering key functions
r15="false"
test_count=0
for tf in "$SCRIPT_DIR/../tests/test_server_helpers.py" "$SCRIPT_DIR/../tests/test_doc_operation.py" "$SCRIPT_DIR/../tests/test_parser.py"; do
    if [ -f "$tf" ]; then
        tc=$(grep -c 'def test_' "$tf" 2>/dev/null || true)
        tc=${tc:-0}
        test_count=$((test_count + tc))
    fi
done
[ "$test_count" -ge 10 ] && r15="true"
check "R15" ">=10 unit tests in key test files ($test_count found)" "$r15"

# R16: All DETAIL.md have YAML front matter
r16="false"
if [ "${detail_count:-0}" -gt 0 ]; then
    yaml_count=0
    while IFS= read -r -d '' f; do
        head -1 "$f" | grep -q '^---' && yaml_count=$((yaml_count + 1))
    done < <(find "$DOCS_DIR" -name "DETAIL.md" -print0 2>/dev/null)
    [ "$yaml_count" -gt 0 ] && [ "$yaml_count" -eq "${total_details:-0}" ] && r16="true"
fi
check "R16" "All DETAIL.md have YAML front matter (${yaml_count:-0}/${total_details:-0})" "$r16"

# R17: 06_function_deps.json exists and non-empty
r17="false"
if [ -f "$ANALYSIS_DIR/06_function_deps.json" ]; then
    size=$(wc -c < "$ANALYSIS_DIR/06_function_deps.json")
    [ "$size" -gt 50 ] && r17="true"
fi
check "R17" "06_function_deps.json exists and non-empty" "$r17"

# R18: All file blocks in DETAIL.md have all 4 section headers
r18="false"
total_blocks=0
complete_blocks=0
for f in $(find "$DOCS_DIR" -name "DETAIL.md" 2>/dev/null); do
    blocks=$(grep -c '<!-- file:' "$f" 2>/dev/null || echo 0)
    purpose=$(grep -c '#### 功能概述' "$f" 2>/dev/null || echo 0)
    dataflow=$(grep -c '#### 数据流' "$f" 2>/dev/null || echo 0)
    interfaces=$(grep -c '#### 核心接口' "$f" 2>/dev/null || echo 0)
    deps=$(grep -c '#### 依赖关系' "$f" 2>/dev/null || echo 0)
    total_blocks=$((total_blocks + blocks))
    min_sec=$purpose
    [ $dataflow -lt $min_sec ] && min_sec=$dataflow
    [ $interfaces -lt $min_sec ] && min_sec=$interfaces
    [ $deps -lt $min_sec ] && min_sec=$deps
    complete_blocks=$((complete_blocks + min_sec))
done
[ "$total_blocks" -gt 0 ] && [ "$total_blocks" -eq "$complete_blocks" ] && r18="true"
check "R18" "All file blocks have 4 sections ($complete_blocks/$total_blocks complete)" "$r18"

echo ""
echo "=== Result: $PASS/$TOTAL ==="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
