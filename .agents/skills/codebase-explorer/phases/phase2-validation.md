# Phase 2: Auto-Validation (No LLM Required)

> **When to read this file:** Phase 1 analysis is complete and you need to validate the MCP output before spawning documentation agents.
>
> **Entry conditions:** `analyze_codebase` has completed successfully. `03_feature_cones.json` and `06_function_deps.json` exist.

---

**Purpose:** Rule-based sanity checks on MCP output. No LLM needed — these are
deterministic checks. The goal is to catch problems early before spending agent
context on documentation generation.

**Input:** `get_modules()` summary response

**Time:** < 30 seconds (reading one API response)

---

## Validation Checks

Run all checks against `get_modules()` output. No tool calls beyond that are needed.

### Check 1: Module Size Warning (token_count > 50k)

```
For each module in get_modules().modules:
  if module.token_count > 50000:
    WARN: "Module {module_id} has {token_count} tokens — may cause context overflow in Phase 3"
    Recommendation: Document in two passes (first N/2 files, then remaining files)
```

Hard limit: A single DETAIL agent should not receive more than 80,000 tokens of source to read.

### Check 2: Single-File Module Flag

```
For each module in get_modules().modules:
  if module.file_count == 1:
    NOTE: "Module {module_id} has only 1 file"
    If token_count < 2000: consider documenting together with a neighboring module
```

Single-file modules are valid — this is only a flag, not an error.

### Check 3: Coverage (All Files Assigned)

```
total_files_in_modules = sum(m.file_count for m in modules)
infrastructure_files = get_modules().infrastructure.file_count
total_accounted = total_files_in_modules + infrastructure_files

If total_accounted < get_modules().total_files:
  WARN: "{unaccounted} source files are not assigned to any module"
  Action: These files will not be documented — acceptable if they are auto-generated
```

### Check 4: Field Completeness

```
For each module in get_modules().modules:
  Required fields: module_id, name, file_count, token_count, layer
  If any field is missing or 0:
    WARN: "Module {module_id} missing field {field_name}"
    Action: Re-run analyze_codebase(force_reindex=true)
```

---

## Validation Report Format

After running all checks, produce a brief summary:

```
Phase 2 Validation:
- Total modules: {N}
- Total files: {N}
- Total tokens: {N}
- PASS: All modules have required fields
- PASS: Source file coverage: {N}/{N} files assigned
- WARN: Module "large_module" has 75,000 tokens (split into two passes)
- NOTE: 3 single-file modules found (acceptable)

Proceeding to Phase 3.
```

---

## Exit Condition

Phase 2 is complete when all checks have been run and findings have been noted.
Warnings do not block Phase 3 — they inform how Phase 3 should be executed.

**Next step:** Proceed to [Phase 3: DETAIL Generation](./phase3-detail.md).
