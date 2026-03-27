# Phase 4: INDEX Assembly + Semantic Reorganization

> **When to read this file:** All Phase 3 DETAIL tasks are complete and you need to assemble the project-level INDEX and review module organization.
>
> **Entry conditions:** All modules have `DETAIL.md` files in `.codebase-docs/`. `get_progress()` shows all tasks complete.

---

**Purpose:** Assemble INDEX.md from DETAIL fragments, then review module organization
for semantic coherence. Reorganize if needed, then re-assemble.

**Inputs:**
- All `.codebase-docs/{module_id}/DETAIL.md` files (via `update_index` automatic extraction)
- `02_dag.json` (for Mermaid graph generation — done automatically by `update_index`)

**Outputs:**
- `.codebase-docs/INDEX.md` — project-level entry point

**Key Constraint:** The INDEX assembly agent does NOT need to read source code files.
It reviews DETAIL content and module names only.

---

## Step 1: Initial INDEX Assembly

Call `doc_operation("update_index")`. This:
1. Scans all `.codebase-docs/{module_id}/DETAIL.md` files
2. Extracts each `<!-- index-fragment:{module_id} -->` block
3. Builds a module-level Mermaid graph from `02_dag.json`
4. Writes `.codebase-docs/INDEX.md` with YAML front matter + Mermaid + module sections

```
doc_operation(operation="update_index")
```

Returns:
```json
{
  "status": "success",
  "index_path": "/path/.codebase-docs/INDEX.md",
  "module_count": 9,
  "message": "INDEX.md regenerated with 9 sections."
}
```

---

## Step 2: Review Module Organization

Read the generated INDEX.md. Evaluate:

### 2a. Are module names functional?

Good module names describe what the code does, not where it lives:
- Good: `request-handling`, `authentication`, `data-validation`
- Acceptable: `routing`, `sessions`, `cli`
- Poor (directory-based): `src_utils`, `lib_core`, `pkg_models`

If module names are poor, they can be noted but cannot be changed via MCP
(module IDs come from `03_feature_cones.json`).

### 2b. Are there obvious misplacements?

A module is misplaced if its `index-fragment` summary describes functionality
that clearly belongs to a different module's domain.

Example: A module named "auth" that contains fragments about "URL routing" suggests
some files ended up in the wrong module during cone extraction.

If misplacement is found: use `doc_operation("move_detail")` (Step 3).

### 2c. Is the module listing order sensible?

Consider reordering modules so that:
- Foundational modules (layer 0) appear first
- User-facing / entry-point modules appear last
- Related modules are adjacent

If reordering is desired: use `doc_operation("reorder_modules")` (Step 3).

---

## Step 3: Reorganize (If Needed)

Apply reorganization operations as needed. Each operation type:

### move_detail — Move a DETAIL file to a different module

Use when: A module's DETAIL file contains documentation that belongs to another module.

```
doc_operation(
  operation="move_detail",
  source_module="misplaced_module",
  target_module="correct_module",
  file_path="DETAIL.md"
)
```

### merge_modules — Merge one module into another

Use when: Two modules are very small (< 2000 tokens combined) and cover the same domain.

```
doc_operation(
  operation="merge_modules",
  source_module="tiny_module",
  target_module="related_module"
)
```

Note: After merging, the DETAIL files from `tiny_module` are moved to `related_module/`.
The merged DETAIL files retain their original content — no automatic content rewriting occurs.
If you want a unified INDEX fragment, manually edit the DETAIL file and add a new
`<!-- index-fragment -->` block.

### reorder_modules — Change display order in INDEX

```
doc_operation(
  operation="reorder_modules",
  new_order=["globals", "exceptions", "routing", "sessions", "app", "blueprints", "cli"]
)
```

### split_module — Inspect a large module (read-only listing)

Use when: You want to see what files are in a module before deciding how to reorganize.

```
doc_operation(operation="split_module", source_module="large_module")
```

Returns the list of files. Then use `move_detail` to reassign specific files.

---

## Step 4: Re-assemble INDEX

After any reorganization operations, re-run `update_index` to regenerate INDEX.md
with the updated module structure:

```
doc_operation(operation="update_index")
```

Repeat Steps 2-4 until the INDEX is semantically coherent.

---

## Step 5: Final Quality Check

Verify:
- [ ] INDEX.md exists and has a Mermaid graph
- [ ] Every module has a `<!-- module-index:{id} -->` block in INDEX.md
- [ ] All links to DETAIL files resolve (files exist at the paths)
- [ ] Module names are meaningful (not just `cone_0`, `cone_1`)
- [ ] Source file coverage >= 80% (from `get_progress()`)

---

## Exit Condition

Phase 4 is complete when:
- `.codebase-docs/INDEX.md` exists with Mermaid graph + module sections
- All DETAIL links in INDEX.md resolve to existing files
- Module organization is semantically coherent
- Source file coverage >= 80%

**Next step:** Proceed to [Phase 5: Quality Verification](./phase5-verify.md).
