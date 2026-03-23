# Workflow Detail Reference

> Load this file when you need expanded step-by-step procedures for each phase.

## Table of Contents

1. [Phase 1: Index](#phase-1-index)
2. [Phase 2: Plan](#phase-2-plan)
3. [Phase 3: Analyze](#phase-3-analyze)
4. [Phase 4: Generate](#phase-4-generate)
5. [Phase 5: Validate](#phase-5-validate)
6. [Error Recovery Strategies](#error-recovery-strategies)
7. [Checkpoint and Resume Flow](#checkpoint-and-resume-flow)

---

## Phase 1: Index

### Step-by-Step

```
1. Determine the target path
   - Use the user's provided path, or detect from CWD
   - Path MUST be absolute

2. Call index_codebase
   tool: index_codebase
   params:
     path: "/absolute/path/to/repo"
     languages: null  # auto-detect, or ["python"] to filter

3. Poll for completion
   tool: get_analysis_status
   params:
     project_id: <from step 2 response>
   Repeat until status is "success" or "failed"

4. Report to user
   - File count, function count, class count
   - Languages detected
   - Module count (from Louvain grouping)
```

### MCP Call Example

```json
// Request
{"tool": "index_codebase", "params": {"path": "/home/user/my-project"}}

// Response
{
  "status": "success",
  "summary": "Indexed 42 files, 156 functions, 28 classes",
  "data": {
    "project_id": "proj_abc123",
    "file_count": 42,
    "function_count": 156,
    "class_count": 28,
    "languages": ["python"],
    "module_count": 6
  }
}
```

### Error Recovery

| Error | Cause | Fix |
|-------|-------|-----|
| `InvalidPathError` | Path does not exist | Ask user for correct path |
| `UnsupportedLanguageError` | No supported files found | Try with explicit `languages` param |
| Timeout (120s) | Very large codebase | Split analysis by subdirectory |

---

## Phase 2: Plan

### Step-by-Step

```
1. Get module list
   tool: get_modules
   params:
     sort_by: "dependency"  # topological order
     project_id: <project_id>

2. Present modules to user
   Show: name, file_count, line_count, is_utility
   Ask: "Does this grouping look correct?"

3. Create analysis plan
   tool: create_analysis_plan
   params:
     project_id: <project_id>
     max_tokens_per_batch: 60000

4. Plan doc structure
   tool: plan_doc_structure
   params:
     project_id: <project_id>

5. Review depth decisions
   The response includes depth_decisions for each module.
   Report notable decisions to the user:
   - Which modules get deep documentation
   - Which modules are merged into parents
   - The split strategies chosen
```

### MCP Call Example: plan_doc_structure

```json
// Response
{
  "status": "success",
  "data": {
    "doc_tree": [
      {"path": "INDEX.md", "level": 0, "target": "root",
       "token_budget": 1200, "parent": null,
       "children": ["core/OVERVIEW.md", "utils/OVERVIEW.md"]},
      {"path": "core/OVERVIEW.md", "level": 1, "target": "core",
       "token_budget": 2000, "parent": "INDEX.md",
       "children": ["core/app/DETAIL.md"]}
    ],
    "depth_decisions": {
      "core": {"depth": 2, "reason": "1453 lines, 28 components",
               "split_strategy": "subpackage"},
      "utils": {"depth": 1, "reason": "utility module, 200 lines",
                "split_strategy": "file"}
    }
  }
}
```

### Dynamic Depth Decision Process

For each module, the planner:

1. Collects metrics: file_count, function_count, class_count, line_count,
   estimated_tokens, subpackage_count, cyclomatic_complexity
2. Computes three independent depth scores:
   - structural_depth from subpackage_count
   - complexity_depth from weighted score formula
   - token_depth from estimated source tokens
3. Takes `max(structural, complexity, token)` as the raw depth
4. Applies constraints:
   - Utility modules capped at depth 2
   - Very small modules (< 100 LOC, < 5 functions) forced to depth 0
   - Maximum cap at 5
5. Selects split strategy: SUBPACKAGE > CLASS > FUNCTION_GROUP > FILE

---

## Phase 3: Analyze

### Step-by-Step

```
LOOP:
  1. Get next batch
     tool: get_next_batch
     params:
       batch_size: 3

  2. For each module in batch:
     a. Get cross-reference context
        tool: get_cross_ref_context
        params:
          module_name: <name>
          max_tokens: 16000

     b. Read source files for the module
        Use standard file reading tools

     c. Analyze and submit
        tool: submit_analysis
        params:
          module_name: <name>
          description: "One-line description"
          public_interfaces: ["func_a(x: int) -> str", ...]
          key_data_structures: ["UserModel", ...]
          dependencies: ["utils", "config"]
          patterns_identified: ["Repository Pattern", ...]
          detailed_analysis: "Full markdown analysis..."
          mermaid_diagram: "graph TD\n  A --> B"
          token_count: 3500

  3. Check budget
     tool: check_budget_status
     params:
       used_tokens: <cumulative>
       modules_completed: <count>
       elapsed_minutes: <time>

  4. If should_stop:
     tool: save_checkpoint
     params:
       phase: "module_analysis"
       tokens_processed: <total>

  5. If NOT should_stop and remaining_batches > 0:
     Continue loop

  6. If remaining_batches == 0:
     Exit loop, proceed to Phase 4
```

### Checkpoint Every 3 Modules

After completing each batch of 3 modules:

1. Save all generated results to disk
2. Report progress: "X of Y modules complete"
3. Call `save_checkpoint` for safety
4. Validate that submitted results are retrievable

### Resume from Checkpoint

```
1. Load checkpoint
   tool: load_checkpoint

2. Review state
   - analyzed_modules: already done, skip these
   - pending_modules: pick up from here
   - module_summaries: available as cross-ref context

3. Continue from get_next_batch
   The batch skips already-completed modules automatically
```

---

## Phase 4: Generate

### Step-by-Step

```
1. Get the doc tree from plan_doc_structure response

2. Sort doc nodes: generate leaves first, then parents
   - Level 2+ DETAIL docs first
   - Level 1 OVERVIEW docs next
   - Level 0 INDEX.md last

3. For each doc node (bottom-up):
   tool: generate_doc
   params:
     target: <module_name or "root">
     level: <0, 1, 2, ...>
     token_budget: <from doc tree>
     parent_path: <from doc tree>
     children: <from doc tree>
     project_id: <project_id>

4. Verify output:
   - actual_tokens <= token_budget (allow 10% overage)
   - Content includes required sections for its level
   - Navigation links are correct

5. Write content to output_dir/<path>

6. Generate doc-index.json
   Aggregate all doc entries with paths, levels, token counts
```

### Generation Order Example

For a project with modules: core (depth 2), utils (depth 1), api (depth 2):

```
Step 1: generate_doc(target="core.app", level=2, ...)       # DETAIL
Step 2: generate_doc(target="core.models", level=2, ...)    # DETAIL
Step 3: generate_doc(target="api.routes", level=2, ...)     # DETAIL
Step 4: generate_doc(target="core", level=1, ...)           # OVERVIEW
Step 5: generate_doc(target="utils", level=1, ...)          # OVERVIEW
Step 6: generate_doc(target="api", level=1, ...)            # OVERVIEW
Step 7: generate_doc(target="root", level=0, ...)           # INDEX
```

Bottom-up generation ensures parent documents can reference child
document summaries for navigation links.

---

## Phase 5: Validate

### Step-by-Step

```
1. Confirm completion
   tool: get_analysis_status
   Verify all tasks are "completed"

2. Link validation
   For each document, check every [text](path) link:
   - Internal links resolve to existing doc files
   - Anchor links point to valid headers
   - No broken cross-references

3. Token budget compliance
   For each document:
   - actual_tokens should be within token_budget
   - Flag documents exceeding budget by > 10%

4. Coverage check
   coverage = documented_modules / total_modules
   Target: >= 80%

5. Mermaid diagram check
   - Every OVERVIEW.md must contain a Mermaid dependency diagram
   - Every DETAIL.md must contain a Mermaid structure diagram

6. Report to user
   - Total documents: N
   - Coverage: X%
   - Token usage: Y total
   - Max depth used: Z
   - Issues found: [list]
```

---

## Error Recovery Strategies

### Index Failure

```
IF index_codebase returns error:
  1. Check path exists and is absolute
  2. Try with explicit languages filter
  3. If repo is very large (> 10000 files), suggest indexing subdirectories
  4. Report error message to user
```

### Analysis Session Timeout

```
IF context window approaching limit OR elapsed > 15 minutes:
  1. save_checkpoint(phase="module_analysis", status="interrupted")
  2. Report progress to user
  3. User can resume with: load_checkpoint()
```

### Document Generation Failure

```
IF generate_doc returns error for a specific target:
  1. Check that analysis result exists for the target
  2. Verify parent/children paths are correct
  3. Try regenerating with reduced token_budget
  4. If persistent, skip and note in final report
```

### Budget Exhaustion

```
IF check_budget_status returns should_stop: true:
  1. Complete the current module's analysis (do not leave partial)
  2. save_checkpoint immediately
  3. Report: "Budget reached. X modules analyzed, Y remaining."
  4. User restarts with load_checkpoint to continue
```

---

## Checkpoint and Resume Flow

### Checkpoint Data Structure

A checkpoint captures:
- `phase`: Current workflow phase
- `analyzed_modules`: List of completed module names
- `pending_modules`: List of remaining module names
- `tokens_processed`: Cumulative token count
- `status`: "in_progress", "completed", or "interrupted"

### Resume Protocol

```
1. Agent starts new session
2. Call load_checkpoint()
3. If checkpoint exists:
   a. Skip Phase 1 (index already done)
   b. Skip Phase 2 (plan already created)
   c. Resume Phase 3 from pending_modules
   d. Cross-ref context available from module_summaries
4. If no checkpoint:
   a. Start from Phase 1
```

### Multi-Session Workflow

```
Session 1:
  Phase 1: Index (5 min)
  Phase 2: Plan (2 min)
  Phase 3: Analyze 6/10 modules (15 min)
  -> save_checkpoint (budget exhausted)

Session 2:
  load_checkpoint -> resume Phase 3
  Phase 3: Analyze 4/10 remaining (10 min)
  Phase 4: Generate docs (5 min)
  Phase 5: Validate (2 min)
  -> complete
```
