# Quality Standards Reference

> Load this file when you need to verify documentation quality or understand
> the acceptance criteria for each phase.

## Table of Contents

1. [Coverage Standards](#1-coverage-standards)
2. [Link Validity Standards](#2-link-validity-standards)
3. [Token Budget Compliance](#3-token-budget-compliance)
4. [Dynamic Depth Validation](#4-dynamic-depth-validation)
5. [Content Quality Checklist](#5-content-quality-checklist)
6. [Phase Gate Criteria](#6-phase-gate-criteria)

---

## 1. Coverage Standards

### Threshold: >= 80% Module Coverage

Coverage measures the fraction of detected modules that have corresponding
documentation.

```
coverage = documented_modules / total_modules
```

| Coverage | Grade | Action |
|----------|-------|--------|
| >= 95% | Excellent | No action needed |
| 80-94% | Acceptable | Note uncovered modules in final report |
| 60-79% | Below standard | Must document critical modules before completion |
| < 60% | Unacceptable | Analysis is incomplete; continue or report blocker |

### What Counts as "Documented"

A module is considered documented if:

1. An analysis result has been submitted (via `submit_analysis`)
2. At least one document has been generated for it (OVERVIEW or DETAIL)
3. The document contains:
   - Module name and description
   - At least one public interface listed
   - At least one dependency relationship documented

### Modules That May Skip Documentation

- **Depth 0 modules**: Too small for standalone docs; merged into parent.
  These still count as "documented" if their parent's OVERVIEW includes
  a summary paragraph about them.
- **Auto-generated or vendor modules**: May be excluded from coverage
  calculation if the user confirms.

---

## 2. Link Validity Standards

### Threshold: 100% Link Validity

Every hyperlink in generated documentation must resolve:

| Link Type | Validation Rule |
|-----------|----------------|
| Internal doc links `[text](path)` | File must exist at the specified relative path |
| Anchor links `[text](#section)` | Header must exist in the target document |
| Cross-reference links | Target document must be in the doc tree |
| Parent links | Must point to an existing parent document |
| Child links | Must point to existing child documents |
| Source file links | Must match actual file paths in the repository |

### Validation Process

```
For each generated document:
  1. Extract all markdown links: [text](url)
  2. For relative paths:
     - Resolve against document's directory
     - Check file exists
  3. For anchor links (#section):
     - Parse target document headers
     - Verify anchor matches a header slug
  4. Report broken links with:
     - Source document path
     - Line number
     - Expected target
     - Suggested fix
```

### Common Link Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Missing parent link | Parent doc not generated yet | Generate in correct order (bottom-up) |
| Broken child link | Child merged into parent | Remove link, add inline summary |
| Wrong depth in path | Path calculation error | Verify `../` count matches level difference |
| Anchor not found | Header changed after linking | Regenerate linking document |

---

## 3. Token Budget Compliance

### Threshold: >= 90% of Documents Within Budget

A document is "within budget" if:

```
actual_tokens <= token_budget * 1.10  # Allow 10% overage
```

| Compliance | Grade | Action |
|------------|-------|--------|
| >= 95% | Excellent | No action |
| 90-94% | Acceptable | Note over-budget docs in report |
| 80-89% | Below standard | Regenerate over-budget documents with trimming |
| < 80% | Unacceptable | Review template configuration and budget allocation |

### Over-Budget Recovery

If a document exceeds its budget:

1. Identify which content sections are using the most tokens
2. Apply priority-based trimming (see DOC_TEMPLATES.md Section 5)
3. Trim in order: examples, internal helpers, edge cases,
   implementation notes, data flow diagrams
4. Regenerate with `generate_doc` and the same `token_budget`

### Under-Budget Evaluation

Documents significantly under budget (< 50% utilization) may indicate:

- Missing content sections
- Insufficient analysis depth
- Module simpler than expected (acceptable if depth was correctly assessed)

Check that under-budget documents still include all required sections
for their level.

---

## 4. Dynamic Depth Validation

### Depth Decision Reasonableness

After `plan_doc_structure`, verify that depth assignments are sensible:

| Module Characteristic | Expected Depth | Flag If |
|----------------------|----------------|---------|
| < 100 LOC, < 5 functions | 0 (merged) | Depth > 1 |
| 100-500 LOC | 1 | Depth > 2 |
| 500-2000 LOC | 1-2 | Depth > 3 |
| 2000-5000 LOC | 2-3 | Depth < 1 or > 4 |
| 5000+ LOC | 3-5 | Depth < 2 |
| Utility module (any size) | 0-2 | Depth > 2 |

### Split Strategy Validation

| Code Style | Expected Strategy | Flag If |
|-----------|-------------------|---------|
| 2+ balanced subpackages | SUBPACKAGE | CLASS or FILE chosen |
| OOP-heavy (3+ classes) | CLASS | FUNCTION_GROUP chosen |
| Functional (few classes) | FUNCTION_GROUP | CLASS chosen |
| Mixed content | HYBRID | -- |
| Flat structure | FILE | SUBPACKAGE chosen (no subpackages) |

### Minimum Documentable Unit Enforcement

Sub-documents should NOT be created for units below these thresholds:

| Metric | Minimum | Action If Below |
|--------|---------|----------------|
| Lines of code | 30 | Merge into parent as inline section |
| Functions | 2 | Merge into parent |
| Classes | 1 | Merge into parent (for class-split) |
| Estimated tokens | 200 | Merge into parent as summary line |

### Termination Condition Audit

Every leaf document in the tree should have a valid termination reason:

| Reason | Valid When |
|--------|-----------|
| `max_depth_reached` | Current depth equals configured max_depth |
| `below_min_lines` | LOC below configured threshold |
| `budget_exhausted` | Remaining budget below minimum |
| `no_meaningful_split` | Cannot create 2+ documentable sub-units |
| `utility_module_depth_limit` | Utility module at depth 2 |
| `single_unit_file` | Single file with 0-1 classes |

---

## 5. Content Quality Checklist

### Level 0 (INDEX.md)

- [ ] Project name and description present
- [ ] Technology stack listed
- [ ] Mermaid architecture diagram included
- [ ] All modules listed with descriptions
- [ ] Module links resolve to OVERVIEW documents
- [ ] Entry points documented
- [ ] Metrics table (files, functions, classes, LOC)
- [ ] doc-meta comment at top
- [ ] Token count within budget

### Level 1 (OVERVIEW.md)

- [ ] Module name and description
- [ ] Navigation: link to parent INDEX.md
- [ ] Navigation: links to child DETAIL documents
- [ ] Mermaid dependency diagram (who imports whom)
- [ ] Import dependencies listed with links
- [ ] Dependents listed with links
- [ ] Public interfaces with signatures
- [ ] Component table (if depth > 1)
- [ ] File list (truncated at 15 if necessary)
- [ ] Metrics (file_count, function_count, class_count, complexity)
- [ ] doc-meta comment at top
- [ ] Token count within budget

### Level 2+ (DETAIL.md)

- [ ] Component name and description
- [ ] Breadcrumb navigation chain (all levels back to INDEX)
- [ ] Mermaid internal structure diagram
- [ ] Classes with method tables (public methods)
- [ ] Functions with signatures and descriptions
- [ ] Call relationships (called_by, calls)
- [ ] Data flow diagram (optional at depth 4+)
- [ ] Sub-component table (if has children)
- [ ] Source files listed
- [ ] doc-meta comment at top
- [ ] Token count within budget

---

## 6. Phase Gate Criteria

### Phase 1 -> Phase 2 Gate

| Criterion | Required |
|-----------|----------|
| `index_codebase` returned `status: "success"` | Yes |
| `project_id` available | Yes |
| Summary stats reported to user | Yes |

### Phase 2 -> Phase 3 Gate

| Criterion | Required |
|-----------|----------|
| `get_modules` returned non-empty module list | Yes |
| User confirmed module grouping | Yes |
| `create_analysis_plan` created tasks | Yes |
| `plan_doc_structure` planned doc tree | Yes |

### Phase 3 -> Phase 4 Gate

| Criterion | Required |
|-----------|----------|
| All analysis tasks completed or skipped | Yes |
| `get_analysis_status` shows 0 pending tasks | Yes |
| At least 80% of modules have analysis results | Yes |

### Phase 4 -> Phase 5 Gate

| Criterion | Required |
|-----------|----------|
| All planned documents generated | Yes |
| `doc-index.json` created | Yes |
| Documents written to output directory | Yes |

### Phase 5 Completion

| Criterion | Required |
|-----------|----------|
| Link validity: 100% | Yes |
| Module coverage: >= 80% | Yes |
| Token compliance: >= 90% | Yes |
| Mermaid diagrams in every OVERVIEW | Yes |
| Final summary reported to user | Yes |
