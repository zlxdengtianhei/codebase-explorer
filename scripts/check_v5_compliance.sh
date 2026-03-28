#!/usr/bin/env bash
# check_v5_compliance.sh — Check V5 vision compliance (gaps from audit)
# Returns: X/8 score (higher = better)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0
TOTAL=8

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

# Robust grep count: returns 0 on no match, actual count on match
gcount() {
    grep -cE "$1" "$2" 2>/dev/null || true
}

echo "=== V5 Vision Compliance Check ==="
echo ""

PHASE3="$PROJECT_DIR/.agents/skills/codebase-explorer/phases/phase3-detail.md"

# C1: phase3-detail.md uses per-file format (### 函数与类 + ### 依赖关系), NOT V2 sections
c1="false"
if [ -f "$PHASE3" ]; then
    has_functions=$(gcount '### 函数与类' "$PHASE3")
    has_deps=$(gcount '### 依赖关系' "$PHASE3")
    v2_count=$(gcount '^## (功能概述|核心接口|内部逻辑|设计决策|在系统中的位置)' "$PHASE3")
    if [ "$has_functions" -gt 0 ] && [ "$has_deps" -gt 0 ] && [ "$v2_count" -eq 0 ]; then
        c1="true"
    fi
fi
check "C1" "phase3-detail.md uses V5 per-file format (no V2 sections)" "$c1"

# C2: phase3-detail.md template has <!-- file:xxx --> and <!-- module:xxx --> markers in the template
c2="false"
if [ -f "$PHASE3" ]; then
    has_file_marker=$(gcount '<!-- file:' "$PHASE3")
    has_module_marker=$(gcount '<!-- module:' "$PHASE3")
    has_end_file=$(gcount '<!-- end:file:' "$PHASE3")
    has_end_module=$(gcount '<!-- end:module:' "$PHASE3")
    if [ "$has_file_marker" -ge 2 ] && [ "$has_module_marker" -ge 2 ] && \
       [ "$has_end_file" -ge 2 ] && [ "$has_end_module" -ge 2 ]; then
        c2="true"
    fi
fi
check "C2" "phase3-detail.md template includes file/module marker examples" "$c2"

# C3: Three-step protocol in phase3-detail.md
c3="false"
if [ -f "$PHASE3" ]; then
    has_step1=$(gcount 'Step 1' "$PHASE3")
    has_step2=$(gcount 'Step 2' "$PHASE3")
    has_step3=$(gcount 'Step 3' "$PHASE3")
    has_func_deps=$(gcount 'get_function_deps' "$PHASE3")
    if [ "$has_step1" -gt 0 ] && [ "$has_step2" -gt 0 ] && [ "$has_step3" -gt 0 ] && [ "$has_func_deps" -gt 0 ]; then
        c3="true"
    fi
fi
check "C3" "Three-step protocol in phase3-detail.md (read->deps->INDEX)" "$c3"

# C4: get_modules summary includes depends_on list (not just dep_count)
c4="false"
c4=$(cd "$PROJECT_DIR" && uv run python -c "
with open('src/server.py') as f:
    source = f.read()
in_summary = False
found = False
for line in source.split('\n'):
    if 'Summary mode' in line or 'no module_id' in line:
        in_summary = True
    if in_summary and 'Detail mode' in line:
        in_summary = False
    if in_summary and '\"depends_on\"' in line:
        found = True
        break
print('true' if found else 'false')
" 2>/dev/null || echo "false")
check "C4" "get_modules summary includes depends_on list per module" "$c4"

# C5: get_modules summary includes directory_hint per module
c5="false"
c5=$(cd "$PROJECT_DIR" && uv run python -c "
with open('src/server.py') as f:
    source = f.read()
in_summary = False
found = False
for line in source.split('\n'):
    if 'Summary mode' in line or 'no module_id' in line:
        in_summary = True
    if in_summary and 'Detail mode' in line:
        in_summary = False
    if in_summary and '\"directory_hint\"' in line:
        found = True
        break
print('true' if found else 'false')
" 2>/dev/null || echo "false")
check "C5" "get_modules summary includes directory_hint per module" "$c5"

# C6: INDEX fragment format specified in phase3-detail.md
c6="false"
if [ -f "$PHASE3" ]; then
    has_index_frag=$(gcount 'index-fragment' "$PHASE3")
    has_module_index=$(gcount 'module-index' "$PHASE3")
    if [ "$has_index_frag" -gt 0 ] && [ "$has_module_index" -gt 0 ]; then
        c6="true"
    fi
fi
check "C6" "INDEX fragment format specified in phase3 prompt" "$c6"

# C7: All existing tests pass
c7="false"
if cd "$PROJECT_DIR" && uv run python -m pytest tests/ -x -q --tb=no 2>/dev/null | tail -1 | grep -q 'passed'; then
    c7="true"
fi
check "C7" "All existing tests pass" "$c7"

# C8: phase3-detail.md does NOT have V2 SNIPPET.md instructions (V5 uses index-fragment instead)
c8="false"
if [ -f "$PHASE3" ]; then
    has_snippet_output=$(gcount 'Output 2: SNIPPET.md|Write to.*snippets/' "$PHASE3")
    has_index_frag=$(gcount 'index-fragment' "$PHASE3")
    if [ "$has_snippet_output" -eq 0 ] && [ "$has_index_frag" -gt 0 ]; then
        c8="true"
    fi
fi
check "C8" "No V2 SNIPPET.md instructions (uses index-fragment instead)" "$c8"

echo ""
echo "=== Result: $PASS/$TOTAL ==="
echo ""
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
