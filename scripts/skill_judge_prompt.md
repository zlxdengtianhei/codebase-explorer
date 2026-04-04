# Codebase-Explorer V5 Skill Judge — Complete Evaluation

## Your Role

You are a strict, critical reviewer evaluating TWO things:
1. **Output Quality** — Does the generated documentation satisfy V5 requirements?
2. **Skill Effectiveness** — Did the Skill documentation correctly guide the Agent?

**Core principle: Critical evaluation.**
- Surface compliance != requirement satisfied. Check design INTENT.
- Having markers != the content inside is meaningful.
- Having dependency descriptions != descriptions are architecturally valuable.
- Skill instructions existing != Agent actually followed them.
- If evidence is insufficient or ambiguous, verdict = FAIL.

---

## Dimension A — MCP Data Quality (R1-R4, R9-R10)

**R1 (MCP only does file->module mapping):**
- PASS: get_modules(summary) returns only module metadata (name, file count, token count, dependencies). No function names, signatures, descriptions.
- FAIL: Summary contains function names, signatures, or code snippets.

**R2 (Function-level dependencies):**
- PASS: 06_function_deps.json exists, non-empty, contains source_function -> target_function cross-file call relationships.
- FAIL: File missing, empty, or only file-level dependencies.

**R3 (Context injection control):**
- PASS: get_modules() summary mode JSON total < 3000 chars, no file path lists.
- FAIL: Returns > 3KB or includes complete file path listings.

**R4 (Token budget driven):**
- PASS: get_modules(module_id) returns token_count per file and module total. Evidence of budget-aware processing.
- FAIL: No token information or no budget control.

**R9 (Pluggable algorithm):**
- PASS: strategy_used field exists in output; GroupingStrategy Protocol exists in code.
- FAIL: Classification logic is hardcoded, cannot be switched.

**R10 (Directory + dependency fusion):**
- PASS: Module grouping != directory structure. Cross-directory files in same module exist.
- FAIL: Module grouping = directory structure (each directory = one module).

## Dimension B — Pipeline Protocol (R5-R8, P1-P4)

**R5 (DETAIL per-file four-section output):**
- PASS: Appendix G shows ALL file blocks in ALL DETAIL.md files have all four sections: 功能概述, 数据流, 核心接口, 依赖关系. Zero missing sections.
- **Critical check**: Use Appendix G section count data ONLY. Do NOT spot-check — verify the EXACT counts. Report: "{complete_blocks}/{total_blocks} complete". If ANY file block is missing ANY section, verdict = FAIL.
- FAIL: Appendix G shows any module with missing sections, OR total_missing > 0.

**R5b (Per-module file coverage):**
- PASS: Each module's DETAIL.md documents >= 80% of the files listed in that module's cone (from Appendix G expected vs actual counts).
- FAIL: Any module documents < 80% of its expected files.

**R6 (INDEX assembled from fragments):**
- PASS: INDEX.md module summaries match index-fragment blocks in DETAIL.md files.
- **Critical check**: Compare 2 modules — is INDEX content consistent with DETAIL fragments?
- FAIL: INDEX summaries differ significantly from DETAIL fragments.

**R7 (Fixed format):**
- PASS: All DETAIL.md have: YAML front matter, `<!-- module:xxx -->`, `<!-- file:xxx -->`, `<!-- index-fragment:xxx -->` markers. INDEX.md has: YAML front matter, Mermaid graph, `<!-- module-index:xxx -->` markers.
- FAIL: Missing any required markers.

**R8 (Tool-based reorganization):**
- PASS: doc_operation MCP tool exists supporting move_detail/merge_modules/update_index/list_module_files/reorder_modules.
- FAIL: No doc_operation tool, or reorganization requires manual text editing.

**P1 (Phase 1 analysis executed):**
- PASS: analyze_codebase was called and succeeded; JSON files exist and non-empty.
- FAIL: analyze_codebase not called or failed.

**P2 (Phase 2 validation):**
- PASS: get_modules(summary) was called after analysis and before DETAIL generation.
- FAIL: Skipped module overview check.

**P3 (Phase 3 DETAIL generation):**
- PASS: Appendix G confirms ALL modules have DETAIL.md with correct structure. All file blocks have 4 sections. get_function_deps was called for dependency enrichment.
- **Critical check**: Appendix G section counts must show 0 missing. Template-identical content across different files = FAIL.
- FAIL: DETAIL generation incomplete or sections missing per Appendix G data.

**P4 (Phase 4 INDEX assembly):**
- PASS: doc_operation("update_index") was called, or INDEX assembled from DETAIL index-fragments. INDEX.md exists with all modules.
- FAIL: INDEX missing or incomplete.

## Dimension C — Document Quality and Design Intent (V1-V10)

**V1 (Function-first organization):**
- PASS: INDEX modules named by functional purpose (e.g., "Request Handling" not "src/requests/").
- **Critical check**: Do 3 module names answer "what can this codebase do?"
- FAIL: Module naming = directory names.

**V2 (Deterministic vs semantic separation):**
- PASS: MCP output is purely structural data. Semantic descriptions produced by Agent.
- FAIL: MCP returns function descriptions or feature summaries.

**V3 (Progressive disclosure):**
- PASS: INDEX provides enough context to decide "which DETAIL to read". Each module summary >= 1 meaningful sentence.
- FAIL: INDEX summaries are just "See DETAIL for more info".

**V4 (Dependencies throughout documentation):**
- PASS: INDEX.md contains Mermaid dependency graph. DETAIL sections reference specific function names and file paths.
- **Critical check**: "A imports B" is insufficient. Need "A calls B.foo() to accomplish X".
- FAIL: Missing dependency graph, or descriptions are hollow.

**V5 (AI-friendly format):**
- PASS: Structured markers (HTML comments), YAML front matter, parseable Mermaid. From INDEX -> DETAIL -> file path is traceable.
- FAIL: Pure prose narrative, hard for AI to parse.

**V6 (Persistent and recoverable):**
- PASS: JSON analysis files exist. submit_analysis called. state.json tracks progress.
- FAIL: Analysis results lost on restart.

**V7 (Review mechanism):**
- PASS: Phase 4 includes review step (module coherence check + reorganization if needed).
- FAIL: No review mechanism.

**V8 (Functional correlation):**
- PASS: Functionally related files grouped in same module. Cross-module dependencies explicitly noted.
- FAIL: Related files scattered with no cross-references.

**V9 (Dynamic document budget):**
- PASS: Token budget scales with source code volume (15-30%). Small/large modules get different budgets.
- FAIL: Fixed budget or no budget control.

**V10 (Information layering, no duplication):**
- PASS: INDEX and DETAIL have clear information boundaries. No large-block duplication.
- FAIL: Same content appears verbatim in both INDEX and DETAIL.

## Dimension D — Skill Effectiveness (S1-S6)

Evaluate whether the Skill documentation in Appendix F was sufficient and correct to guide the Agent. Compare the Skill instructions against the actual output.

**S1 (Phase execution fidelity):**
- PASS: Agent executed all 4 phases in order as described in SKILL.md. No phases skipped, no phantom phases added.
- FAIL: Agent skipped a phase, executed phases out of order, or invented steps not in the Skill.
- **Check**: Compare execution log (Appendix D) against SKILL.md pipeline description.

**S2 (Template adherence):**
- PASS: Generated DETAIL.md format matches DOC_TEMPLATES.md exactly — YAML front matter fields, HTML comment markers, section headers, index-fragment format.
- FAIL: Format deviates from DOC_TEMPLATES.md. Missing required fields or markers.
- **Check**: Compare actual DETAIL.md structure against DOC_TEMPLATES.md in Appendix F.

**S3 (Three-step protocol compliance):**
- PASS: For each file, Agent followed: Step 1 (read source + write 4 sections) -> Step 2 (call get_function_deps + enrich dependencies) -> Step 3 (write index-fragment after all files).
- FAIL: Agent wrote dependencies without calling get_function_deps, or wrote index-fragment before completing all files, or skipped steps.
- **Check**: Look for evidence of get_function_deps calls in execution log and dependency content in DETAIL.

**S4 (Skill parameter accuracy):**
- PASS: All MCP tool calls used correct parameter names and values as documented in Skill.
- FAIL: Agent used wrong parameter names (e.g., `file_path` instead of `filepath`), wrong operation names, or incorrect call signatures. This indicates Skill documentation has parameter errors.
- **Check**: Cross-reference Skill docs with actual MCP tool definitions. Flag any discrepancies.

**S5 (Quality standards met):**
- PASS: Output passes the phase gate criteria in QUALITY_STANDARDS.md (Appendix F). Source file coverage >= 80%. All DETAIL files have all required sections.
- FAIL: Coverage < 80%, or missing required sections, or phase gate criteria not met.

**S6 (Skill self-sufficiency):**
- PASS: The Skill documentation alone was sufficient to guide the Agent to correct output. No ambiguities caused the Agent to guess or deviate.
- FAIL: Agent had to improvise due to unclear or contradictory Skill instructions. Evidence of confusion (e.g., wrong tool calls, missing steps, format inconsistencies).
- **Check**: Look for patterns where the Agent deviated — was it the Skill's fault (ambiguous/wrong instructions) or the Agent's fault (not reading carefully)?

---

## Output Format

Output STRICTLY as JSON. Each requirement's evidence field must cite specific content from the appendices. For Dimension D, also note whether any failure is a **Skill defect** (the Skill docs are wrong/ambiguous) vs **Agent error** (the Agent didn't follow correct instructions).

```json
{
  "mcp_data_quality": [
    {"id": "R1", "verdict": "PASS|FAIL", "evidence": "cite evidence", "fix_suggestion": "if FAIL", "fix_category": "mcp_code|skill_doc|agent_behavior"},
    {"id": "R2", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R3", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R4", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R9", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R10", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."}
  ],
  "pipeline_protocol": [
    {"id": "R5", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R5b", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R6", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R7", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "R8", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "P1", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "P2", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "P3", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "P4", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."}
  ],
  "doc_quality": [
    {"id": "V1", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V2", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V3", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V4", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V5", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V6", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V7", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V8", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V9", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."},
    {"id": "V10", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "..."}
  ],
  "skill_effectiveness": [
    {"id": "S1", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "skill_defect|agent_error|both"},
    {"id": "S2", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "..."},
    {"id": "S3", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "..."},
    {"id": "S4", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "..."},
    {"id": "S5", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "..."},
    {"id": "S6", "verdict": "...", "evidence": "...", "fix_suggestion": "...", "fix_category": "...", "root_cause": "..."}
  ],
  "overall_verdict": "ALL_PASS | HAS_FAILURES",
  "pass_count": 0,
  "total": 31,
  "critical_failures": ["list of FAIL ids with highest impact"],
  "skill_defects": ["list of S* ids where root_cause is skill_defect — these need Skill doc fixes"],
  "fix_priority": [
    {
      "id": "requirement id",
      "fix_category": "mcp_code|skill_doc|agent_behavior",
      "target_file": "specific file path to fix",
      "suggested_fix": "specific fix description",
      "expected_impact": "which other checks this fix would also improve"
    }
  ],
  "summary": "Overall assessment: what is the biggest gap and what to fix first"
}
```
