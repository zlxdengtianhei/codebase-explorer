# Detail producer

Read this when writing or importing function/module Detail.

Source is in the prompt once, under `source`. The `symbols` array carries names, kinds, spans, parent/structural ids, and slice indexes only. Do not expect signatures or exclusive bodies there; repeating them would count as extra source presentation. Produce the JSON details and write the specified result file. Do not Read the packet file or the source directory again. The CLI still loads skills; that is not a license to skip tools that the host requires, and it is not a claim that no tools exist. Accounting counts the packet injection mechanically at claim time; your result carries a `report` object stating what you actually read, and the program checks it against the assignment. If the interval is missing bytes or the frozen hash no longer matches, stop and return residual `source_conflict` instead of guessing an empty body.

Accurate field types and the output contract are in the current initial task (`models.detail_production_contract`). This file keeps the writing SOP; do not hand-copy a second type table. Related fields may be empty lists only when that aspect is genuinely absent. Do not invent IDs.

Write execution cause and effect: what it does, inputs/outputs and key conditions, state/IO/external effects, error/cancel/retry, locally evidenced dependencies, unknowns. Shortest sufficient language; no fixed word count. "Processes data" is not an explanation of a branching function.

Methods and classes are separate records. A class record explains initialization and class contract and links method Details. It does not paste method bodies. Module residual records cover top-level imports, registration, decorators, and side effects that are not a function.

Tests: state the fixture, the asserted behavior, and what failure means.

A symbol whose exclusive spans all sit in one packet writes the canonical symbol id. A symbol that intersects N packets writes N fragment ids `{parent}::frag::{identity}` plus a source-0 merge that only reads those fragment Details in file order. Mixed packets carry per-symbol fragment meta and inline source once; they do not fake a single `parent_symbol_id`. Merge consumes `fragment_ids` (also stored as `slice_ids` for older callers).

Native Astra review with source uses `delivery=packet_read` on the main SKILL: claim `--include-source` reserves a packet path (initial L=0), root only forwards that path, and a tool read of the reserved packet settles the reservation. See the Native Astra review section of `.dsh/skills/codebase-explorer/SKILL.md`. Do not treat a returned packet path as an initial source presentation.
