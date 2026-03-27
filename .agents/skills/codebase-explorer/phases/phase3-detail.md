# Phase 3: DETAIL Generation (Parallel Sub-Agents)

> **When to read this file:** Phase 2 validation is complete and you are ready to generate detailed documentation for each module.
>
> **Entry conditions:** `get_modules()` returns a non-empty module list. Phase 2 validation findings have been reviewed.

---

**Input:** Module list from `get_modules()` summary

**Processing:** Spawn one sub-agent per module (or two passes for large modules)

**Agent Outputs:**
- `.codebase-docs/{module_id}/DETAIL.md` — per-module documentation

---

## Three-Step Per-File Protocol

For each file in the module, the DETAIL agent executes three steps in order.
Complete Steps 1 + 2 for one file before moving to the next file.

**Step 1 — Read source + write four sections:**
Read the source file, then write four sections for it:
- `#### 功能概述 (Purpose)` — What this file does, why it exists, its role in the module
- `#### 数据流 (Data Flow)` — How data enters, what transforms occur, where results go
- `#### 核心接口 (Key Interfaces)` — Important functions and classes with signatures
- `#### 依赖关系 (Dependencies)` — Placeholder; will be enriched in Step 2

**Step 2 — Call get_function_deps + enrich 依赖关系:**
Call `get_function_deps(file="{filepath}")` via MCP. Use the returned cross-file
call relationships to replace the placeholder with specific dependency entries:
- "Calls `other_module/file.function_name()` to accomplish X"
- "Class Y inherits from `base/file.BaseClass`"
- "Called by `consumer/file.py` which needs Z"

Close the file block with `<!-- end:file:{filepath} -->`.

**Step 3 — Write INDEX fragment (after ALL files are done):**
After documenting all files in the module, write a summary block:
```
<!-- index-fragment:{module_id} -->
**{Module Name}** ({N} files, {N} tokens) — 2-3 sentences describing the module's
primary responsibility and how it relates to other modules.
Key entry points: `main_function()`, `ImportantClass`.
<!-- end:index-fragment:{module_id} -->
```

---

## DETAIL Agent Prompt Template

```
# Code Documentation Task

## Your Role

You are a technical documentation writer. Your job is to read each source file
in module "{module_id}" and produce one document: DETAIL.md.

MCP provides structural data only (file lists, token counts, dependency graphs).
YOU must read the source code files and understand what they actually do.

## Module Context

- Module ID: {module_id}
- Module name: {module_name}
- DAG layer: {layer} (0 = foundational, higher = more user-facing)
- Files in this module: {file_count} files, {token_count} tokens total

## Files You Must Read and Document

{for each file}
- {filepath}  ({token_count} tokens)
{/for}

## Token Budget

- DETAIL.md: max {budget} tokens
- Before reading each file, check: accumulated_tokens + file_token_count <= budget
- If the next file would exceed budget, STOP. Write the INDEX fragment for files
  completed so far. Do not read the remaining files.
- Track accumulated_tokens as a running sum of token_count for each file read.

## Three-Step Per-File Protocol

For EACH file, execute Steps 1 + 2 in order, then proceed to the next file.
Write Step 3 only after ALL files are documented.

### Step 1: Read source and write four sections

1. Read the source file using the Read tool
2. Open a file block: `<!-- file:{filepath} -->`
3. Write four sections:

#### 功能概述 (Purpose)
What this file does, why it exists, and its role in the module.
(NOT implementation details; NOT a line-by-line walkthrough)

#### 数据流 (Data Flow)
How data enters this file, what transformations occur, and where results go.
(Input types → transformation steps → output types)

#### 核心接口 (Key Interfaces)
Important functions and classes with signatures:
- `function_name(param: Type) -> ReturnType`: Brief description
- `ClassName`: What it represents and its key methods

#### 依赖关系 (Dependencies)
[Write placeholder: "Querying cross-file dependencies..."]

### Step 2: Call get_function_deps and enrich 依赖关系

1. Call `get_function_deps(file="{filepath}")` via MCP
2. Replace the placeholder with specific dependency entries:
   - Calls `other_file.function_name()` to accomplish X
   - Uses `ClassName` from `module/file.py` for Y
   - Imported by `consumer.py` which needs Z
3. Close the file block: `<!-- end:file:{filepath} -->`

### Step 3: Write INDEX fragment (after ALL files)

After all files are documented:

<!-- index-fragment:{module_id} -->
**{Module Name}** ({N} files, {N} tokens) — 2-3 sentence summary of what this
module does, its primary responsibility, and how it relates to other modules.
Key entry points: `main_function()`, `ImportantClass`.
<!-- end:index-fragment:{module_id} -->

## Output: DETAIL.md

Write to: `.codebase-docs/{module_id}/DETAIL.md`

Use EXACTLY this structure:

---
module_id: {module_id}
module_name: {module_name}
file_count: {file_count}
generated_at: {timestamp}
token_budget: {budget}
---

# {module_name}

<!-- module:{module_id} -->

### {filename_1}
<!-- file:{filepath_1} -->

#### 功能概述 (Purpose)
...

#### 数据流 (Data Flow)
...

#### 核心接口 (Key Interfaces)
...

#### 依赖关系 (Dependencies)
...

<!-- end:file:{filepath_1} -->

(repeat for each file)

<!-- index-fragment:{module_id} -->
...
<!-- end:index-fragment:{module_id} -->

<!-- end:{module_id} -->
<!-- codebase-explorer: end -->

## After Writing DETAIL.md

Call submit_analysis to record completion:

submit_analysis(
  task_id="{task_id}",
  detail_paths=[".codebase-docs/{module_id}/DETAIL.md"],
  snippet_paths=[],
  tokens_used={your_estimate},
  source_files_covered=[...list of files you documented...]
)
```

---

## Style Constraints

1. **Language:** English for all section content. Keep Chinese names in section headers (功能概述, 数据流, 核心接口, 依赖关系) exactly as written.
2. **Headers:** `###` for file-level, `####` for four sections. No `#####` or deeper.
3. **Lists:** `-` for unordered lists.
4. **Perspective:** Write for an AI Agent reading docs before modifying code. Focus on "what does this do and what can I call."
5. **No opinions:** Do not write "elegant", "well-designed", "unfortunately". Describe facts.
6. **Specific dependencies:** In 依赖关系, always name the specific function/class called, not just the module imported.

---

## Exit Condition

Phase 3 is complete when:
- All modules have a `DETAIL.md` in `.codebase-docs/{module_id}/`
- Each `DETAIL.md` has an `<!-- index-fragment -->` block
- `get_progress()` shows all tasks as `"complete"` or `progress_percent == 100`

**Next step:** Proceed to [Phase 4: INDEX Assembly](./phase4-index.md).
