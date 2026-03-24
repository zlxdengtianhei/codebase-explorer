# Agent Prompt Field Consistency Audit Report

> **Generated**: 2026-03-24
> **Scope**: All 3 Agent Prompts in `.agents/skills/codebase-explorer/SKILL.md`
> **Authority Sources**:
>   - `02a_code_analysis_v2.md` Section 4 (JSON Schema definitions -- authoritative field names)
>   - `02b_skill_design_v2.md` Sections 3/4/5 (Agent Prompt templates -- design intent)
>   - `02c_responsibility_v2.md` Section 6 (submit_analysis V2 final signature)
>   - `03_final_progressive_scheme.md` Check 5 ruling (field name authority decision)

---

## 1. Per-Agent Prompt Audit Table

### 1.1 Validator Agent Prompt (Phase 2)

**Location in SKILL.md**: Lines 117-200 (Validator Agent Prompt Template)

| # | Field in SKILL.md Prompt | Authoritative Field (02a Section 4.3) | Match? | Severity | Notes |
|---|--------------------------|---------------------------------------|--------|----------|-------|
| 1 | `cone_name` (output schema line 179) | `name` | MISMATCH | HIGH | 03 Check 5 ruling: use `name` |
| 2 | `files` (output schema line 186) | `exclusive_files` | MISMATCH | HIGH | 03 Check 5 ruling: use `exclusive_files` |
| 3 | `layers` (output schema line 187) | `layers_within_cone` | MISMATCH | HIGH | 03 Check 5 ruling: use `layers_within_cone` |
| 4 | `cone_token_estimate` (output schema line 189) | `exclusive_total_tokens` | MISMATCH | HIGH | 03 Check 5 ruling: use `exclusive_total_tokens` |
| 5 | `dependency_edges` (output schema line 188) | N/A (not a per-cone field in 02a) | MISMATCH | MEDIUM | In 02a, weighted edges are at top-level `weighted_edges` in `01_structure.json`, not inside each cone object |
| 6 | `cone_id` (output schema line 178) | `cone_id` | MATCH | -- | Consistent |
| 7 | `action` (output schema line 180) | N/A (Validator-added field) | OK | -- | Not in 02a schema; added by Validator, per 03 Check 5 |
| 8 | `confidence` (output schema line 183) | N/A (Validator-added field) | OK | -- | Not in 02a schema; added by Validator, per 03 Check 5 |
| 9 | `reasoning` (output schema line 184) | N/A (Validator-added field) | OK | -- | Not in 02a schema; added by Validator |
| 10 | `validation_notes` (output schema line 185) | N/A (Validator-added field) | OK | -- | Not in 02a schema; added by Validator |
| 11 | Size check uses `cone_token_estimate > 30000` (line 155) | Should reference `exclusive_total_tokens` | MISMATCH | MEDIUM | Field name in validation criteria text |
| 12 | Preserve instruction says `files`, `layers`, `dependency_edges` (line 168/252-253) | Should say `exclusive_files`, `layers_within_cone`; `dependency_edges` does not exist in cone | MISMATCH | HIGH | Preservation instruction references wrong field names |

**Summary**: 5 MISMATCH items (4 HIGH, 1 MEDIUM) in the Validator Agent Prompt.

---

### 1.2 DETAIL Agent Prompt (Phase 3)

**Location in SKILL.md**: Lines 220-397 (DETAIL Agent Prompt Template)

| # | Variable/Field in SKILL.md Prompt | Authoritative Source | Match? | Severity | Notes |
|---|-----------------------------------|----------------------|--------|----------|-------|
| 1 | `{{files_in_cone}}` (line 253) | `exclusive_files` in 03_feature_cones.json | OK (injection variable) | -- | Injection variable name; actual data sourced from `exclusive_files`. Variable name is a Skill-layer alias, acceptable. |
| 2 | `{{cone_name}}` (line 247) | `name` in 03_feature_cones.json | OK (injection variable) | -- | Maps to `name` field at injection time |
| 3 | `{{dag_layer}}` (line 248) | `dag_layer` in 03_feature_cones.json | MATCH | -- | Consistent |
| 4 | `{{dependency_snippets}}` (lines 262-267) | Snippet files from `.codebase-analysis/snippets/` | OK (injection variable) | -- | Content injection, not a JSON field |
| 5 | `{{dependent_cone_names}}` (lines 277-279) | Derived from DAG reverse edges | OK (injection variable) | -- | Computed at Skill layer |
| 6 | `{{detail_token_budget}}` (line 283) | Derived from task_manifest | OK (injection variable) | -- | Computed at Skill layer |
| 7 | `{{task_id}}` (line 226) | `task_id` in 05_task_manifest.json | MATCH | -- | Consistent |
| 8 | `{{task_type}}` (line 227) | `type` in 05_task_manifest.json | NOTE | LOW | SKILL.md uses `task_type` injection variable but 05_task_manifest.json field is `type`. Acceptable as injection alias. |
| 9 | `{{feature_name}}` (line 228) | Derived from `name` in 03_feature_cones.json | OK (injection variable) | -- | Acceptable alias |
| 10 | SNIPPET path: `.codebase-analysis/snippets/{{cone_id}}.md` (line 326) | 03 scheme Section 2.3 snippet path | MATCH | -- | Consistent with `03_final_progressive_scheme.md` Section 2.3 |
| 11 | `@unit` marker format (not present in SKILL.md DETAIL prompt) | Required by 02b Section 4 | MISSING | HIGH | SKILL.md DETAIL prompt does NOT include the `@unit` marker rules from 02b. This is critical for Phase 5 Semantic Reorganization. |

**Summary**: 1 MISSING item (HIGH severity). The `@unit` marker rules from 02b Section 4 (lines 409-462) are entirely absent from the SKILL.md DETAIL Agent Prompt. This is a critical gap because Phase 5 depends on these markers for split operations.

---

### 1.3 INDEX Agent Prompt (Phase 4)

**Location in SKILL.md**: Lines 416-528 (INDEX Agent Prompt Template)

| # | Field/Reference in SKILL.md Prompt | Authoritative Source | Match? | Severity | Notes |
|---|-------------------------------------|----------------------|--------|----------|-------|
| 1 | `Input 3: Document Plan` uses `{{doc_plan_json}}` (line 446) | 02b Section 5 uses `04_doc_plan.json` | NOTE | MEDIUM | 02a/02c authority names file `04_file_tokens.json`, not `04_doc_plan.json`. See Section 7 of this report. |
| 2 | References `04_doc_plan.json` (line 406) | 02a/02c authority: `04_file_tokens.json` | MISMATCH | HIGH | SKILL.md Phase 4 input says `04_doc_plan.json` but the authoritative file name is `04_file_tokens.json` per 03 Check 2 ruling |
| 3 | `dependency_map` (lines 462, 616-617) | 02a does not define `dependency_map` as a field in `03_feature_cones.json` | NOTE | MEDIUM | 02a uses `shared_deps` per cone + top-level `weighted_edges` in 01_structure.json. `dependency_map` is not defined in any authoritative schema. |
| 4 | `needs_overview` in `doc_plan` (line 474, 631-632) | Not in 02a schema | NOTE | LOW | This is a doc_plan concept from 02b, acceptable if the Skill generates this field |
| 5 | `cone_name` in style constraints (line 722) | Authority: `name` (02a) | MISMATCH | MEDIUM | Should reference `name` field per 02a authority |
| 6 | Link Path Rules table (lines 730-735) | 02b Section 5 link path rules table | MATCH | -- | Consistent with 02b. The 4-row table is correctly reproduced. |
| 7 | `doc-index.json` schema (lines 501-519) references `cone_name` | Authority: `name` (02a) | MISMATCH | MEDIUM | Should be `name` per 02a, but this is the doc-index output schema (INDEX Agent generates), so `cone_name` is an INDEX-authored display field, not a direct 02a field. Still, for consistency with upstream data, should align. |
| 8 | `status: "complete" | "pending"` in doc-index.json (line 511) | 02c Section 4: `pending/in_progress/complete/failed` | NOTE | LOW | doc-index.json is a different file from state.json; its status values are subset but consistent |
| 9 | Missing `doc-manifest.json` output reference | 02b Section 6.5: Phase 4 initializes `doc-manifest.json` | MISSING | MEDIUM | SKILL.md Phase 4 does not mention `doc-manifest.json` initialization as an output |

**Summary**: 2 MISMATCH (1 HIGH, 1 MEDIUM), 1 MISSING (MEDIUM), several NOTES.

---

## 2. Corrected Validator Agent Prompt (using authoritative field names)

The following is the corrected output schema section of the Validator Agent Prompt. Changes are marked with `[FIXED]` comments.

```
## Output Format

Output the COMPLETE updated `03_feature_cones.json` with your changes applied.

Use this schema for each cone:

```json
{
  "cone_id": "cone_0",
  "name": "request-handling",               // [FIXED] was "cone_name" -> "name" per 02a
  "action": "keep",                          // keep | merge | split | rename
  "merge_target": null,                      // if action=merge, target cone_id
  "split_into": null,                        // if action=split, list of new groupings
  "confidence": "high",                      // high | medium | low
  "reasoning": "These files collectively implement the request/response cycle...",
  "validation_notes": "Algorithm placed ctx.py and wrappers.py together correctly.",
  "exclusive_files": ["flask/views.py", "flask/ctx.py", "flask/wrappers.py"],  // [FIXED] was "files"
  "layers_within_cone": {{...preserve algorithm output...}},  // [FIXED] was "layers"
  "exclusive_total_tokens": 8400             // [FIXED] was "cone_token_estimate"
}
```

## Validation Criteria (corrected field references)

### 3. Size Appropriateness
- Cones with `exclusive_total_tokens > 30000`: Flag as "too large" (split candidate)
  // [FIXED] was "cone_token_estimate > 30000"
- Cones with `exclusive_total_tokens < 500` AND `exclusive_file_count == 1`: Flag as "too small" (merge candidate)
  // [FIXED] was "cone_token_estimate < 500"
- Algorithm constraint: Do NOT suggest merging two cones whose combined `exclusive_total_tokens` exceeds 30000

## What You MUST Do (corrected)

5. Preserve all fields that the algorithm set (especially `exclusive_files`,
   `layers_within_cone`, `exclusive_total_tokens`, `shared_deps`, `dag_layer`,
   `cohesion_score`) -- only update `name`, `action`, `validation_notes`,
   and `confidence`
   // [FIXED] was "files, layers, dependency_edges, cone_token_estimate"
```

**Full corrected Validator Prompt** (copy-paste ready, showing only the diff sections):

The instruction `"Preserve all fields that the algorithm set (especially files, layers, dependency_edges, cone_token_estimate)"` should be replaced with:

```
Preserve all fields that the algorithm set (especially `exclusive_files`,
`layers_within_cone`, `exclusive_total_tokens`, `shared_deps`, `dag_layer`,
`cohesion_score`, `entry_point`) — only update `name`, `action`,
`validation_notes`, `confidence`, and `reasoning`
```

The `dependency_edges` reference in the preservation instruction should be removed entirely since this field does not exist in the per-cone object of `03_feature_cones.json`. Dependency edge data lives at the top level of the file or in `01_structure.json`.

---

## 3. DETAIL Agent Prompt Field Verification

### Injection Variables vs JSON Schema Mapping

| Injection Variable | Source JSON File | Source Field | Correct Mapping? |
|--------------------|-----------------|--------------|-------------------|
| `{{task_id}}` | 05_task_manifest.json | `tasks[].task_id` | YES |
| `{{task_type}}` | 05_task_manifest.json | `tasks[].type` | YES (alias) |
| `{{feature_name}}` | 03_feature_cones.json | `feature_cones[].name` | YES |
| `{{cone_name}}` | 03_feature_cones.json | `feature_cones[].name` | YES (alias of `name`) |
| `{{dag_layer}}` | 03_feature_cones.json | `feature_cones[].dag_layer` | YES |
| `{{total_dag_layers}}` | 02_dag.json | `max_layer` | YES |
| `{{file_count}}` | 03_feature_cones.json | `feature_cones[].exclusive_file_count` | YES |
| `{{files_in_cone}}` | 03_feature_cones.json | `feature_cones[].exclusive_files` | YES (data from `exclusive_files`) |
| `{{filepath}}` | 01_structure.json | `files[].path` or `files[].relative_path` | YES |
| `{{line_count}}` | 01_structure.json | `files[].line_count` | YES |
| `{{estimated_tokens}}` | 04_file_tokens.json | `files[].estimated_tokens` | YES |
| `{{dependency_snippets}}` | Disk files | `.codebase-analysis/snippets/*.md` | YES |
| `{{dep_cone_name}}` | 03_feature_cones.json | `feature_cones[].name` of dependency cone | YES |
| `{{dep_snippet_content}}` | Disk files | Content of snippet .md file | YES |
| `{{dependent_cone_names}}` | 03_feature_cones.json + DAG reverse | Computed from cone dependencies | YES |
| `{{detail_token_budget}}` | 05_task_manifest.json | Derived from `remaining_budget` | YES |
| `{{budget_ratio}}` | Skill computation | Not a stored field | YES |
| `{{source_token_estimate}}` | 04_file_tokens.json | Sum of `estimated_tokens` for cone files | YES |

### Critical Missing Element: `@unit` Marker Rules

The SKILL.md DETAIL Agent Prompt is **missing** the `@unit` marker rules defined in 02b Section 4 (lines 409-462). This is a Phase 5 prerequisite.

**Required addition** (from 02b, to be inserted after the DETAIL.md structure template):

```
### @unit Markup (MANDATORY for multi-file cones)

When `file_count > 1`, your DETAIL.md MUST wrap each source file's content
section with `@unit` fence markers:

<!-- @unit: {filepath} | tokens: {estimated_tokens} -->
### {filename} -- brief description

...documentation content for this file...

<!-- @/unit: {filepath} -->

Rules:
- `tokens` value is the approximate token count for this section (written chars / 4)
- The **功能概述** and **设计决策** sections go OUTSIDE all @unit markers
  (at the top and bottom of the document)
- Single-file cones (file_count == 1) do NOT need @unit markers
- @unit markers are the foundation for Phase 5 Semantic Reorganization split operations
```

---

## 4. INDEX Agent Prompt Field Verification

### Link Path Rules Table Correctness

The link path rules table in SKILL.md (lines 730-735) matches 02b Section 5 exactly:

| From document | To INDEX.md | To {cone}/OVERVIEW.md | To {cone}/DETAIL.md |
|---------------|-------------|----------------------|---------------------|
| INDEX.md (depth 0) | self | `{cone}/OVERVIEW.md` | `{cone}/DETAIL.md` |
| OVERVIEW.md (depth 1) | `../INDEX.md` | `../{cone}/OVERVIEW.md` | `DETAIL.md` (same dir) |
| DETAIL.md (depth 1) | `../INDEX.md` | `OVERVIEW.md` (same dir) | sibling DETAIL: `./OTHER.md` |
| DETAIL.md (depth 2) | `../../INDEX.md` | `../OVERVIEW.md` | sibling: `./OTHER.md` |

**Verdict**: CORRECT. Table is consistent between SKILL.md and 02b Section 5.

### Issues Found

1. **`04_doc_plan.json` reference** (line 406): SKILL.md Phase 4 input says `04_doc_plan.json` but per 03 Check 2 ruling, the authoritative name is `04_file_tokens.json`. The "doc plan" concept from 02b was resolved to be covered by `04_file_tokens.json` (token estimates) + `05_task_manifest.json` (task structure). INDEX Agent should receive `04_file_tokens.json` for token budget info and `05_task_manifest.json` for document tree structure, not a non-existent `04_doc_plan.json`.

2. **`dependency_map` reference** (lines 462, 616-617): The `dependency_map` field is referenced in the Pre-Flight Validation Check 2 and Mermaid generation instructions, but this field does not exist in the authoritative 02a `03_feature_cones.json` schema. The actual dependency information is:
   - Per-cone: `shared_deps` array in each cone object
   - Global: `weighted_edges` array in `01_structure.json`
   - DAG-level: `edges` array in `02_dag.json`

   The INDEX Agent should use `02_dag.json` edges (cone-level) for the Mermaid diagram, not a non-existent `dependency_map` field.

3. **Missing `doc-manifest.json` output**: Per 02b Section 6.5, Phase 4 should initialize `doc-manifest.json` as a flat structure. SKILL.md does not mention this output.

---

## 5. submit_analysis() Parameter Comparison: SKILL.md vs 02c Section 6

### 02c Section 6 Authoritative V2 Final Signature

```python
async def submit_analysis(
    task_id: str,                              # from 05_task_manifest.json
    detail_paths: list[str],                   # DETAIL.md absolute paths written to disk
    snippet_paths: list[str],                  # SNIPPET.md absolute paths written to disk
    tokens_used: int,                          # Agent self-reported token consumption
    source_files_covered: list[str] | None = None,  # source files documented
    project_id: str | None = None,             # None = most recent analyze_codebase result
) -> dict:
    """Returns: { status, task_id, tasks_remaining, progress_percent, source_file_coverage_percent }"""
```

### SKILL.md Signature (Line 624)

```
submit_analysis(task_id, detail_paths, snippet_paths, tokens_used, source_files_covered)
```

### Comparison

| Parameter | 02c Section 6 | SKILL.md | Match? |
|-----------|---------------|----------|--------|
| `task_id: str` | Required | Present | MATCH |
| `detail_paths: list[str]` | Required | Present | MATCH |
| `snippet_paths: list[str]` | Required | Present | MATCH |
| `tokens_used: int` | Required | Present | MATCH |
| `source_files_covered: list[str] \| None` | Optional (default None) | Present | MATCH |
| `project_id: str \| None` | Optional (default None) | **MISSING** | MISMATCH |

### Return Value Comparison

| Return Field | 02c Section 6 | SKILL.md (lines 631-636) | Match? |
|--------------|---------------|--------------------------|--------|
| `status` | `"success"` | Not shown | MISSING (minor) |
| `task_id` | str | `"task_abc"` | MATCH |
| `tasks_remaining` | int | `5` | MATCH |
| `progress_percent` | float | `66.67` | MATCH |
| `source_file_coverage_percent` | float | `78.5` | MATCH |

### V2.1 Extensions (from 02c Section 8.5 ruling)

02c Section 8.5 V2.1 ruling adds:
- `detail_paths` semantics generalized to accept all doc types (DETAIL, OVERVIEW, INDEX)
- New optional parameter: `manifest_path: str | None = None`

SKILL.md does **not** reflect these V2.1 extensions.

**Verdict**: SKILL.md is missing `project_id` optional parameter and the V2.1 `manifest_path` extension. The core 5-parameter signature matches.

---

## 6. state.json Task Status Value Unification Check

### Authoritative Status Values (02c Section 4 + 03 Check 6 ruling)

```
"pending" | "in_progress" | "complete" | "failed"
```

### Locations Checked

| Location | Status Values Used | Consistent? |
|----------|-------------------|-------------|
| 02c Section 4 `state.json` schema | `pending`, `in_progress`, `complete`, `failed` | YES (authority) |
| 03 Section 2.5 `state.json` schema | `pending`, `in_progress`, `complete`, `failed` | YES |
| SKILL.md `get_progress()` return (lines 600-615) | `pending`, `in_progress`, `complete`, `failed` | YES |
| SKILL.md Phase 4 INDEX prompt `doc-index.json` `status` field (line 511) | `"complete"`, implicit `"pending"` | YES (subset) |
| 02b `doc-index.json` `documents[].status` (line 1275) | `complete`, `pending`, `failed` | YES (subset, no `in_progress` -- acceptable for doc-index since docs are either done or not) |
| 02c Section 5 recovery algorithm | `pending`, `in_progress`, `complete`, `failed` | YES |
| SKILL.md workflow text (lines 683-684) | "pending/in_progress" | YES |
| 03 Section 2.5 output_files[].status | `pending`, `complete` | YES (subset for file-level tracking) |

**Verdict**: CONSISTENT. All locations use the same 4-value set `{pending, in_progress, complete, failed}` or a valid subset thereof. The `doc-index.json` uses a 3-value subset (`pending`, `complete`, `failed`) which is acceptable since documents do not have an "in_progress" state in that context.

---

## 7. 02b `doc-plan.json` vs `doc-manifest.json` Naming Unification

### The Naming Discrepancy

02b uses two different file names in different contexts:

| Context in 02b | File Name Used | Purpose |
|----------------|---------------|---------|
| Phase 1 output list (Section 2, line 76) | `04_doc_plan.json` | Per-cone doc budget + split strategy |
| Phase 4 output (Section 2, line 125) | `doc-manifest.json` | Document organization state (SSOT) |
| Phase 5 operations (Section 6.5) | `doc-manifest.json` | Reorganization state tracking |
| INDEX Agent Input 3 (Section 5, line 559) | `04_doc_plan.json` | Document tree structure |

### Authoritative Resolution (03 Check 2 ruling)

The 03 Check 2 ruling is definitive:

> **Authoritative naming (per 02a and 02c):**
> 1. `01_structure.json`
> 2. `02_dag.json`
> 3. `03_feature_cones.json`
> 4. `04_file_tokens.json`
> 5. `05_task_manifest.json`

There is **no** `04_doc_plan.json` in the authoritative 5-file set. The 02b name `04_doc_plan.json` was a semantic alias that maps to:

- **Token/budget information** --> `04_file_tokens.json` (the authoritative file #4)
- **Document tree/task structure** --> `05_task_manifest.json` (the authoritative file #5)
- **Document organization state** --> `doc-manifest.json` (a separate Phase 4/5 artifact, NOT one of the 5 analysis files)

### Impact on SKILL.md

SKILL.md has the following issues related to this naming:

1. **Phase 4 input** (line 406): References `04_doc_plan.json` -- should reference `04_file_tokens.json` and `05_task_manifest.json` instead
2. **INDEX Agent Input 3** (line 446): Uses `{{doc_plan_json}}` -- should be `{{task_manifest_json}}` or split into file-tokens + task-manifest inputs
3. **Phase 4 output**: Does not mention `doc-manifest.json` initialization

### Naming Summary Table

| 02b Name | Authoritative Name | Status |
|----------|-------------------|--------|
| `02_dependency_graph.json` | `02_dag.json` | 02b is non-authoritative; use `02_dag.json` |
| `04_doc_plan.json` | `04_file_tokens.json` | 02b is non-authoritative; use `04_file_tokens.json` for token data |
| `doc-manifest.json` | `doc-manifest.json` | This is a separate artifact (not one of the 5 analysis files). Name is correct and consistent across 02b. |

---

## 8. Comprehensive Discrepancy Summary

### All Discrepancies Found (sorted by severity)

| # | Location | Issue | Severity | Fix |
|---|----------|-------|----------|-----|
| D1 | Validator Prompt: output schema `cone_name` | Should be `name` | HIGH | Replace `"cone_name"` with `"name"` in Validator output schema |
| D2 | Validator Prompt: output schema `files` | Should be `exclusive_files` | HIGH | Replace `"files"` with `"exclusive_files"` |
| D3 | Validator Prompt: output schema `layers` | Should be `layers_within_cone` | HIGH | Replace `"layers"` with `"layers_within_cone"` |
| D4 | Validator Prompt: output schema `cone_token_estimate` | Should be `exclusive_total_tokens` | HIGH | Replace `"cone_token_estimate"` with `"exclusive_total_tokens"` |
| D5 | Validator Prompt: preservation instruction | References `files`, `layers`, `dependency_edges` | HIGH | Replace with `exclusive_files`, `layers_within_cone`; remove `dependency_edges` |
| D6 | DETAIL Prompt: missing `@unit` marker rules | Required by 02b Section 4 for Phase 5 | HIGH | Add @unit marker rules section |
| D7 | INDEX Prompt: `04_doc_plan.json` reference | Authoritative name is `04_file_tokens.json` | HIGH | Replace with `04_file_tokens.json` + `05_task_manifest.json` |
| D8 | Validator Prompt: `dependency_edges` field | Does not exist in per-cone 02a schema | MEDIUM | Remove from output schema |
| D9 | INDEX Prompt: `dependency_map` field | Not in any authoritative schema | MEDIUM | Replace with `02_dag.json` edges reference |
| D10 | INDEX Prompt: `cone_name` in style constraints | Authority says `name` | MEDIUM | Replace with `name` (or clarify as display label) |
| D11 | INDEX Prompt: missing `doc-manifest.json` output | Required by 02b Phase 4 | MEDIUM | Add doc-manifest.json initialization as Phase 4 output |
| D12 | submit_analysis: missing `project_id` param | Present in 02c Section 6 | MEDIUM | Add optional `project_id` parameter |
| D13 | submit_analysis: missing V2.1 `manifest_path` param | 02c Section 8.5 ruling | MEDIUM | Add optional `manifest_path` parameter |
| D14 | Validator Prompt: size check field name | Uses `cone_token_estimate` in criteria text | MEDIUM | Replace with `exclusive_total_tokens` |
| D15 | SKILL.md Phase count | Title says "5-Phase" (line 59) | LOW | 02b defines 6 phases; SKILL.md Phase 5 is "Validate" but 02b has Phase 5 as "Semantic Reorganization" and Phase 6 as "Validate". Update to 6-Phase. |

### Statistics

| Severity | Count |
|----------|-------|
| HIGH | 7 |
| MEDIUM | 7 |
| LOW | 1 |
| **Total** | **15** |

---

## 9. Acceptance Criteria Checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Audit table covers all 3 existing Agent Prompts (Validator, DETAIL, INDEX) | **PASS** | Sections 1.1, 1.2, 1.3 |
| Each discrepancy annotates "02a authoritative value" and "current SKILL.md value" | **PASS** | All items in Section 1 tables include both values |
| Corrected Prompt fragments provided (copy-paste ready) | **PASS** | Section 2 (Validator), Section 3 (DETAIL @unit addition) |
| submit_analysis() V2 signature matches 02c Section 6 | **PASS** | Section 5 -- core 5 params match; `project_id` and `manifest_path` noted as missing optional params |
| state.json task status values unified | **PASS** | Section 6 -- all 4 values consistent across all documents |
| 02b doc-plan.json vs doc-manifest.json naming unified | **PASS** | Section 7 -- resolution provided with authoritative mapping |

---

## Appendix A: Authoritative 03_feature_cones.json Cone Object Schema (02a Section 4.3)

For reference, the complete authoritative field set for a cone object in `03_feature_cones.json`:

```json
{
  "cone_id": "feature_request_handling",
  "name": "request-handling",
  "entry_point": "/abs/path/to/views.py",
  "entry_point_relative": "src/flask/views.py",
  "exclusive_files": [
    "/abs/path/to/views.py",
    "/abs/path/to/wrappers.py"
  ],
  "exclusive_file_count": 2,
  "exclusive_total_tokens": 5880,
  "layers_within_cone": {
    "0": ["/abs/path/to/wrappers.py"],
    "1": ["/abs/path/to/views.py"]
  },
  "shared_deps": [
    "/abs/path/to/scc_0",
    "/abs/path/to/sansio/app.py"
  ],
  "dag_layer": 3,
  "cohesion_score": 0.78,
  "review_flagged": false
}
```

Fields added by Validator Agent (Phase 2):

```json
{
  "action": "keep | merge | split | rename",
  "confidence": "high | medium | low",
  "reasoning": "...",
  "validation_notes": "...",
  "merge_target": null,
  "split_into": null
}
```

## Appendix B: Authoritative submit_analysis() V2.1 Full Signature (02c Section 6 + 8.5)

```python
async def submit_analysis(
    task_id: str,
    detail_paths: list[str],           # Generalized: accepts DETAIL/OVERVIEW/INDEX paths
    snippet_paths: list[str],
    tokens_used: int,
    source_files_covered: list[str] | None = None,
    project_id: str | None = None,
    manifest_path: str | None = None,  # V2.1: doc-manifest.json path for Phase 4/5
) -> dict:
    """
    Returns:
    {
        "status": "success",
        "task_id": str,
        "tasks_remaining": int,
        "progress_percent": float,
        "source_file_coverage_percent": float
    }
    """
```
