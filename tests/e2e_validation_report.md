# E2E Validation Report

## Test Target
- Repository: pallets/flask
- Source: test_repos/flask/src/flask/
- Docs: test_repos/flask/.codebase-docs/
- Generated: 2026-03-22T16:05:38 UTC
- Generator: codebase-explorer v0.1.0

## Results Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| File discovery rate | 0% (0/24) | >= 90% | **FAIL** |
| Module coverage | 66.7% (2/3) | >= 80% | **FAIL** |
| Link validity | 14.8% (9/61) | 100% | **FAIL** |
| Token budget compliance | 100% (22/22) | >= 90% | **PASS** |
| Dynamic depth (max) | 2 | >= 2 | **PASS** |
| Dynamic depth (min) | 1 | = 1 | **FAIL** |
| Parent-child consistency | true (vacuous) | true | **PASS** (with caveats) |
| Orphaned docs | 16 | 0 | **FAIL** |
| Total docs generated | 22 | - | INFO |

## Document Tree

```
test_repos/flask/.codebase-docs/
├── INDEX.md                         (level 0, root)
├── doc-index.json
├── _utilities/
│   ├── OVERVIEW.md                  (level 1, 268 fn, 32 cls)
│   ├── sub_0/
│   │   └── DETAIL.md               (level 2)
│   └── sub_1/
│       └── DETAIL.md               (level 2)
├── json/
│   ├── OVERVIEW.md                  (level 1, 34 fn, 10 cls)
│   └── file_0/
│       └── DETAIL.md               (level 2)
├── module_0/
│   ├── OVERVIEW.md                  (level 1, 14 fn, 2 cls)
│   ├── group_0/
│   │   └── DETAIL.md               (level 2)
│   └── group_1/
│       └── DETAIL.md               (level 2)
├── module_6/
│   ├── OVERVIEW.md                  (level 1, 12 fn, 3 cls)
│   └── file_0/
│       └── DETAIL.md               (level 2)
├── module_7/
│   ├── OVERVIEW.md                  (level 1, 6 fn, 2 cls)
│   └── group_0/
│       └── DETAIL.md               (level 2)
└── sansio/
    ├── OVERVIEW.md                  (level 1, 40 fn, 2 cls)
    ├── group_0/DETAIL.md            (level 2)
    ├── group_1/DETAIL.md            (level 2)
    ├── group_2/DETAIL.md            (level 2)
    ├── group_3/DETAIL.md            (level 2)
    ├── group_4/DETAIL.md            (level 2)
    ├── group_5/DETAIL.md            (level 2)
    ├── group_6/DETAIL.md            (level 2)
    └── group_7/DETAIL.md           (level 2)
```

**Total: 22 documents** (1 INDEX + 6 OVERVIEW + 15 DETAIL)

## Depth Decisions

| Module | Max Depth | Children (level 2) | Rationale |
|--------|-----------|---------------------|-----------|
| _utilities | 2 | 2 sub-groups | Large module (268 fn, 32 cls) - correctly split |
| json | 2 | 1 file group | Medium module (34 fn, 10 cls) - split into 1 detail |
| module_0 | 2 | 2 groups | Medium module (14 fn, 2 cls) - split into 2 groups |
| module_6 | 2 | 1 file group | Small module (12 fn, 3 cls) - split into 1 detail |
| module_7 | 2 | 1 group | Small module (6 fn, 2 cls) - split into 1 group |
| sansio | 2 | 8 groups | Large module (40 fn, 2 cls) - correctly split into many groups |

**Issue: All modules have depth = 2.** No module has depth = 1 only, meaning the dynamic depth planner did not keep any small module flat. Even `module_7` (6 functions, 2 classes) was split to depth 2 when it likely should have remained at depth 1.

## Token Budget Compliance

All 22 documents are within their token budgets (100% compliance rate).

| Document | Token Count | Token Budget | Usage % |
|----------|------------|--------------|---------|
| INDEX.md | 157 | 415 | 38% |
| module_0/OVERVIEW.md | 276 | 532 | 52% |
| json/OVERVIEW.md | 302 | 442 | 68% |
| sansio/OVERVIEW.md | 363 | 720 | 50% |
| module_6/OVERVIEW.md | 259 | 403 | 64% |
| module_7/OVERVIEW.md | 254 | 259 | 98% |
| _utilities/OVERVIEW.md | 460 | 6036 | 8% |
| module_0/group_0/DETAIL.md | 194 | 887 | 22% |
| module_0/group_1/DETAIL.md | 194 | 887 | 22% |
| json/file_0/DETAIL.md | 180 | 738 | 24% |
| sansio/group_0..7/DETAIL.md | 188 each | 1201 each | 16% each |
| module_6/file_0/DETAIL.md | 192 | 672 | 29% |
| module_7/group_0/DETAIL.md | 194 | 432 | 45% |
| _utilities/sub_0/DETAIL.md | 196 | 3621 | 5% |
| _utilities/sub_1/DETAIL.md | 196 | 3621 | 5% |

**Observation:** While all documents are under budget, most DETAIL files use very little of their budget (5-29%). This suggests the DETAIL template generates mostly structural boilerplate without meaningful content about the actual source code. The `_utilities` module has the largest budget (6036 tokens) but its sub-documents only use 5% each.

## Validation Script Results

### Link Validation (`validate_doc_links.py`)

```json
{
  "total_docs": 22,
  "total_links": 61,
  "valid_links": 9,
  "broken_links": 52,
  "orphaned_docs": 16,
  "parent_child_consistency": true,
  "parent_child_errors": [],
  "status": "FAIL"
}
```

### Coverage Check (`check_coverage.py`)

```json
{
  "source_files": 24,
  "documented_files": 0,
  "file_discovery_rate": 0.0,
  "total_modules": 3,
  "documented_modules": 2,
  "module_coverage": 0.667,
  "token_budget_compliance": {
    "total_docs": 22,
    "compliant": 22,
    "rate": 1.0
  },
  "depth_analysis": {
    "max_depth": 2,
    "modules_with_depth_gte_2": 6,
    "modules_with_depth_eq_1": 0,
    "dynamic_depth_working": true
  },
  "status": "FAIL"
}
```

## Issues Found

### CRITICAL: Broken Links (52 of 61 links broken)

**Root cause:** The document generator uses paths relative to the docs root directory, but Markdown links must be relative to the current file's location.

Examples:
- In `module_0/OVERVIEW.md`: link `[Project Overview](INDEX.md)` should be `[Project Overview](../INDEX.md)` because the file is inside `module_0/`.
- In `sansio/group_0/DETAIL.md`: link `[Project](INDEX.md)` should be `[Project](../../INDEX.md)` because the file is two levels deep.
- In `sansio/group_0/DETAIL.md`: link `[sansio](sansio/OVERVIEW.md)` should be `[sansio](../OVERVIEW.md)`.

The 9 valid links are the inter-module references in OVERVIEW files (e.g., `[_utilities](../_utilities/OVERVIEW.md)`) which happen to use correct relative `../` prefixes.

**Fix required in:** The `DocWriter` or template generation code that constructs navigation links in OVERVIEW.md and DETAIL.md files.

### CRITICAL: File Discovery Rate = 0%

**Root cause:** The `doc-index.json` entries do not populate the `source_files` field. The coverage script checks `entry.get("source_files", [])` to determine which source files are documented, but this field is missing from all 22 entries.

Flask has 24 source files (18 root `.py` files + 3 `json/` files + 3 `sansio/` files), but the documentation system does not track which specific source files each document covers.

**Fix required in:** The doc-index.json generation code must populate the `source_files` field for each document entry.

### HIGH: Module Coverage = 66.7%

**Root cause:** Flask has 3 source "modules" as detected by the coverage script: `json`, `sansio`, and `__root__` (the 18 standalone `.py` files at the package root). The documented targets use names `module_0`, `module_6`, `module_7`, `_utilities` for the root files, but none of these match the `__root__` pseudo-module name used by the coverage script.

The doc generator correctly groups root files into logical modules (`module_0` = config, `module_6` = testing, `module_7` = views, `_utilities` = app/helpers/etc.), but this naming convention is incompatible with the coverage script's `__root__` convention.

**Fix options:**
1. The doc generator should include a `__root__` module or use a naming convention the coverage script recognizes.
2. The coverage script should match documented modules by content (checking which source files they cover) rather than by name.

### HIGH: Dynamic Depth Not Differentiating (all modules depth=2)

All 6 content modules reached depth 2. No module stayed at depth 1, even though `module_7` (6 functions, 2 classes) is small enough to document at a single level. The depth planner should keep small modules flat.

**Note:** The coverage script's `dynamic_depth_working` reports `true` because its logic only checks `modules_with_depth_gte_2 > 0` and `len(distinct_depths) > 1 or len(module_depths) <= 1`. Since all modules have depth 2, `distinct_depths = {2}` has length 1, but there are 6 modules so the second condition fails. However, the actual result is `true` -- this seems to be because the `root` target at level 0 is counted as a distinct depth, making `distinct_depths = {0, 2}` which has length > 1.

### MEDIUM: Orphaned Documents (16 of 22)

16 documents are orphaned (not referenced by any link or doc-meta from other documents):
- All 15 DETAIL.md files
- `module_7/OVERVIEW.md`

**Root cause:** OVERVIEW files do not include `children` in their doc-meta blocks (only doc-index.json has this data). The OVERVIEW files also do not contain Markdown links pointing to their DETAIL children. The validation script cannot verify the hierarchy from the `.md` files alone.

### MEDIUM: Generic Module Names

Modules are named `module_0`, `module_6`, `module_7`, `_utilities` instead of meaningful names derived from the source code (e.g., `config`, `testing`, `views`, `core`). This reduces documentation usability.

### LOW: INDEX.md Shows Empty Metrics

The INDEX.md shows 0 files, 0 functions, 0 classes, and 0 lines of code. The module table is empty. The architecture diagram shows "No modules detected". These are placeholder values not populated from actual analysis.

### LOW: DETAIL Files Lack Source Content

All DETAIL files show "No source files associated" and "No dependencies". They contain only structural boilerplate (breadcrumb navigation, empty mermaid diagrams) without any actual documentation of the code they represent.

### LOW: Duplicate Public Interface Names

Several OVERVIEW files list duplicate function names in their Public Interfaces section (e.g., `sansio/OVERVIEW.md` lists `app_template_filter` three times). These likely represent overloaded methods or similarly-named methods across different classes, but the interface listing does not disambiguate them.

## Overall Verdict: **FAIL**

### Summary of Pass/Fail

| Check | Result |
|-------|--------|
| Documents generated (22 files) | PASS |
| doc-index.json exists | PASS |
| INDEX.md exists | PASS |
| Token budget compliance (100%) | PASS |
| Parent-child consistency (vacuous) | PASS (with caveats) |
| File discovery rate (0%) | FAIL |
| Module coverage (66.7%) | FAIL |
| Link validity (14.8%) | FAIL |
| Dynamic depth min=1 | FAIL |
| Orphaned docs (16) | FAIL |

### Priority Fixes for Next Iteration

1. **P0 - Link paths:** Fix relative link generation in templates to use proper `../` prefixes based on document depth.
2. **P0 - source_files field:** Populate `source_files` in doc-index.json entries to enable file discovery tracking.
3. **P1 - Module naming:** Either use `__root__` for root-level files or update the coverage script to match by content.
4. **P1 - OVERVIEW children links:** Add Markdown links from OVERVIEW to DETAIL children, or include `children` in doc-meta blocks.
5. **P2 - Dynamic depth:** Adjust depth planner to keep small modules (< 10 functions) at depth 1.
6. **P2 - Content richness:** Populate DETAIL files with actual source code documentation instead of structural boilerplate only.
7. **P3 - INDEX.md metrics:** Populate aggregate metrics from analysis data.
8. **P3 - Module names:** Use descriptive names derived from source file names.
