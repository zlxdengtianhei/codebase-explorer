# How the published evaluation files were prepared

This record lists how the files in `evaluation/` and `examples/` were copied from the original run directories and what was changed before publishing (local paths, account columns, key handling in scripts, licenses, source links). Numbers in the evaluation come from the original runs; the published copies change only what is listed here.


This directory stages the manifest-approved evaluation artifacts and six generated examples. It was built from 4,008 source files across 52 publishable groups; symbolic links were dereferenced. Original run, evidence, repository, and source files were left unchanged. No Git operation or model API request was made.

## Copy scope and exclusions

SWE-QA question text remains embedded in answer and judge records under Apache-2.0. Five standalone question JSONL files are excluded; reference answers, the full SWE-QA harness, CodeWikiBench rubric text, window exports, source copies, virtual environments, and the voided first C arm are excluded. E5 project-authored questions and references are included. Labels and sampling records remain in questions/; E5 adjudications.json is one level above freeze/.

| Group | Copied files |
|---|---:|
| H1 | 1 |
| SCRIPTS | 146 |
| INPUTS | 5 |
| E1-q | 4 |
| E1-ans | 111 |
| E1-judge | 90 |
| E1-misc | 4 |
| E1-cost | 2 |
| E1-cbe-docs | 79 |
| E1-cw-docs | 44 |
| E2-q | 3 |
| E2-ans | 196 |
| E2-judge | 192 |
| E2-direct | 97 |
| E2-metrics | 4 |
| E2-cost | 2 |
| E2b-q | 3 |
| E2b-ans | 96 |
| E2b-judge | 96 |
| E2b-metrics | 4 |
| E2b-cost | 2 |
| E3-q | 3 |
| E3-ans | 147 |
| E3-judge | 144 |
| E3-direct | 97 |
| E3-metrics | 4 |
| E3-cost | 3 |
| E3-cbe-docs | 306 |
| E4-cbe-docs | 477 |
| E4-cw-docs | 271 |
| E4-qb | 4 |
| E4-qb-cost | 2 |
| E4-qc-cost | 8 |
| E5-freeze | 11 |
| E5-qgen | 108 |
| E5-qgen-big | 18 |
| E5-qgen-cost | 2 |
| E5-ans | 194 |
| E5-rubric | 154 |
| E5-judge | 194 |
| E5-metrics | 15 |
| E5-spot | 9 |
| E5-cost | 2 |
| E5-cbe-docs | 403 |
| E6-tsdown-docs | 24 |
| E6-ruby_llm-docs | 75 |
| E6-cjson-docs | 17 |
| E6-fmt-docs | 51 |
| E6-gson-docs | 52 |
| E6-polyglot-docs | 13 |
| E6-catalog | 6 |
| E6-metrics | 13 |

## Step 2: paths and user names

The initial normalization changed 836 source files (including compressed-group contents): working-root paths became `$WORK`, other home paths became `$HOME`, and private temporary paths use `$TMP`. User names became `owner`; the captured owner/group pair uses `owner group`. A follow-up pass changed 109 of those files, removing 174 truncated or misspelled home-path fragments and six remaining user-name fragments. Fabricated and truncated paths in failed tool calls are still recognizable as failed calls, but their home prefixes are now generic. Archive headers use numeric owner/group 0 and generic `owner`/`group` names, with modification times zeroed.

Affected patterns: evaluation/*/{metrics,*audit*,*manifest*}.json, answer and rubric archive members, historical scripts, generated summary.json, inputs.json, and CodeWiki output. evaluation/PROVENANCE.md explains that numeric evaluation results refer to original runs and recorded byte counts can differ after redaction.

## Step 3: cost CSV allowlist

Applied the manifest allowlist to 22 gateway CSV files (16,646 rows); added a separate 13-row e6-polyglot-r2.csv filtered from the R2 window by its exact session tag. Earlier polyglot costs remain separately named, preserving the Python 3.13 versus 3.12 distinction. Retained only time, session, requested/served model, swapped, status, token counters, cost, and duration. Removed account/key identities, provider/host/routing fields, request/response identifiers, error text, agent and other columns outside the allowlist.

| File | Rows | Removed columns |
|---|---:|---|
| evaluation/costs/e1-cbe-flask-gateway-requests.csv | 33 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e1-codewiki-attributed-requests.csv | 225 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e2-gateway-window-model-requests.csv | 3066 | agent, model, request_id, response_id |
| evaluation/costs/e2b-gateway-window-model-requests.csv | 2435 | agent, model, request_id, response_id |
| evaluation/costs/e3-cbe-pytest-gateway-requests.csv | 194 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e3-gateway-window-model-requests.csv | 3544 | agent, model, request_id, response_id |
| evaluation/costs/e4-cbe-svelte-r1-gateway-requests.csv | 128 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-cbe-svelte-r2-gateway-requests.csv | 136 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-cbe-svelte-r3-gateway-requests.csv | 144 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-cwb-cbe-r1-requests.csv | 315 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-cwb-codewiki-1-requests.csv | 303 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-e4c-run1-gateway-requests.csv | 961 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e4-e4c-run2-gateway-requests.csv | 800 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e5-cbe-curl-gateway-requests.csv | 341 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e5-qa-gateway-requests.csv | 3482 | agent, model, request_id, response_id |
| evaluation/costs/e5q-judge-gateway_window.csv | 400 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-cjson.csv | 13 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-fmt.csv | 30 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-gson.csv | 36 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-polyglot.csv | 10 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-ruby_llm.csv | 29 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |
| evaluation/costs/e6-tsdown.csv | 21 | agent, provider, host, model, effort, ttft_ms, error, kind, provider_key_id, provider_key_name, provider_account, route_id, request_id, endpoint, error_message, error_type, source, rejected, session_provider, session_account, session_official_login, caller_key_id, caller_key_name, response_id, upstream, tries, handed_on, tier_asked, tier_sent, tier_served, upstream_stop |

## Step 4: historical scripts

Changed 90 Python scripts. The 31 originals mentioning a local credential configuration comprise 27 executable credential reads and four reports describing that practice. All 27 executable reads now use the `MAGPIE_API_KEY` environment variable; generation scripts pass that value into the existing child-process environment. The four report strings now describe environment credentials. No credential value was read. Sandbox negative-control commands now target a generic denied-secret fixture. Existing credential-scan test selectors are public syntax strings and remain.

Absolute path literals now expand environment variables. `WORK` defaults to `CBE_WORK_ROOT` or the current directory; `TMP` defaults to `TMPDIR` or /tmp, and HOME follows the process environment. Set WORK to a reconstructed experiment workspace before using historical scripts. They still require original inputs and optional tools; compilation does not establish end-to-end reproducibility. Subdirectories are retained under scripts/ to avoid filename collisions; the E6 scripts/ source directory is flattened to a single scripts/ level.

All 165 Python files, including auxiliary scripts and compressed-group scripts, compiled successfully with python3 and with the private Python 3.12 interpreter. Bytecode outputs are outside this publication directory.

| Changed script | Credential reads replaced | Path literals parameterized |
|---|---:|---:|
| evaluation/e1-flask-pilot/scripts/attribution_probe.py | 1 | 1 |
| evaluation/e1-flask-pilot/scripts/checkpoint.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/checkpoint_b2.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/codewiki_audit_cli.py | 0 | 2 |
| evaluation/e1-flask-pilot/scripts/export_final_usage.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/finalize_artifacts.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/finish_b2.py | 1 | 1 |
| evaluation/e1-flask-pilot/scripts/generate_cbe.py | 1 | 1 |
| evaluation/e1-flask-pilot/scripts/guess_arms.py | 1 | 0 |
| evaluation/e1-flask-pilot/scripts/judge_pilot.py | 1 | 0 |
| evaluation/e1-flask-pilot/scripts/prepare.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/reconcile_usage.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/render_b2.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/render_report.py | 0 | 1 |
| evaluation/e1-flask-pilot/scripts/run_codewiki.py | 1 | 1 |
| evaluation/e1-flask-pilot/scripts/run_pilot.py | 1 | 0 |
| evaluation/e1-flask-pilot/scripts/verify_b2.py | 1 | 1 |
| evaluation/e1-flask-pilot/scripts/verify_final.py | 1 | 2 |
| evaluation/e2-flask/scripts/render.py | 0 | 1 |
| evaluation/e2-flask/scripts/run_direct.py | 1 | 0 |
| evaluation/e2-flask/scripts/secret_scan.py | 1 | 0 |
| evaluation/e2-flask/scripts/setup.py | 0 | 1 |
| evaluation/e2-flask/scripts/tool_layer_smoke.py | 0 | 2 |
| evaluation/e2-flask/scripts/verify.py | 1 | 0 |
| evaluation/e2-flask/scripts/verify_patch_sha.py | 0 | 1 |
| evaluation/e2b-flask-25steps/scripts/render.py | 0 | 1 |
| evaluation/e2b-flask-25steps/scripts/setup.py | 0 | 1 |
| evaluation/e2b-flask-25steps/scripts/tool_layer_smoke.py | 0 | 2 |
| evaluation/e2b-flask-25steps/scripts/verify.py | 0 | 1 |
| evaluation/e2b-flask-25steps/scripts/verify_patch_sha.py | 0 | 1 |
| evaluation/e3-pytest/scripts/artifact_scope_d67.py | 0 | 1 |
| evaluation/e3-pytest/scripts/extend_generation_d67.py | 1 | 1 |
| evaluation/e3-pytest/scripts/failure_verify.py | 1 | 1 |
| evaluation/e3-pytest/scripts/finalize.py | 0 | 1 |
| evaluation/e3-pytest/scripts/finalize_d67.py | 0 | 1 |
| evaluation/e3-pytest/scripts/generate.py | 1 | 1 |
| evaluation/e3-pytest/scripts/generation_metrics.py | 0 | 1 |
| evaluation/e3-pytest/scripts/pipeline.py | 0 | 1 |
| evaluation/e3-pytest/scripts/pipeline_d67.py | 0 | 1 |
| evaluation/e3-pytest/scripts/prepare_calibration.py | 0 | 1 |
| evaluation/e3-pytest/scripts/prepare_limitations.py | 0 | 1 |
| evaluation/e3-pytest/scripts/render.py | 0 | 1 |
| evaluation/e3-pytest/scripts/run_direct.py | 1 | 0 |
| evaluation/e3-pytest/scripts/secret_scan.py | 1 | 0 |
| evaluation/e3-pytest/scripts/setup.py | 0 | 2 |
| evaluation/e3-pytest/scripts/tool_layer_smoke.py | 0 | 2 |
| evaluation/e4-svelte/scripts/cwb/prepare_docs.py | 0 | 1 |
| evaluation/e4-svelte/scripts/cwb/prepare_labels.py | 0 | 1 |
| evaluation/e4-svelte/scripts/cwb/report.py | 0 | 1 |
| evaluation/e4-svelte/scripts/cwb/run_judge.py | 1 | 0 |
| evaluation/e4-svelte/scripts/cwb/verify.py | 1 | 0 |
| evaluation/e4-svelte/scripts/cwb/wait_e4c.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/analyze.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/compress.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/execute.py | 1 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/finalize.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/heartbeat.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/report.py | 0 | 2 |
| evaluation/e4-svelte/scripts/e4b-scripts/schedule.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/snapshot.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/status.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4b-scripts/verify_measurements.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4c/cleanup.py | 1 | 0 |
| evaluation/e4-svelte/scripts/e4c/codewiki_audit_cli.py | 0 | 1 |
| evaluation/e4-svelte/scripts/e4c/probe.py | 1 | 0 |
| evaluation/e4-svelte/scripts/e4c/run_codewiki.py | 1 | 1 |
| evaluation/e5-curl/question-pipeline/verify/A/build_review.py | 0 | 1 |
| evaluation/e5-curl/question-pipeline/verify/A/source_extract.py | 0 | 2 |
| evaluation/e5-curl/scripts/e5a-scripts/analyze.py | 0 | 1 |
| evaluation/e5-curl/scripts/e5a-scripts/diagnostics.py | 0 | 2 |
| evaluation/e5-curl/scripts/e5a-scripts/execute.py | 1 | 2 |
| evaluation/e5-curl/scripts/e5a-scripts/finalize.py | 0 | 1 |
| evaluation/e5-curl/scripts/e5a-scripts/preflight.py | 0 | 1 |
| evaluation/e5-curl/scripts/e5a-scripts/report.py | 0 | 2 |
| evaluation/e5-curl/scripts/e5a-scripts/verify_measurements.py | 0 | 1 |
| evaluation/e5-curl/scripts/e5a-scripts/watch.py | 0 | 1 |
| evaluation/e5-curl/scripts/qa/finalize.py | 1 | 0 |
| evaluation/e5-curl/scripts/qa/render.py | 0 | 1 |
| evaluation/e5-curl/scripts/qa/setup.py | 0 | 1 |
| evaluation/e6-showcase/scripts/analyze-e4b-reference.py | 0 | 1 |
| evaluation/e6-showcase/scripts/analyze.py | 0 | 1 |
| evaluation/e6-showcase/scripts/excerpts.py | 0 | 1 |
| evaluation/e6-showcase/scripts/execute.py | 1 | 1 |
| evaluation/e6-showcase/scripts/prepare.py | 0 | 3 |
| evaluation/e6-showcase/scripts/report.py | 0 | 2 |
| evaluation/e6-showcase/scripts/snapshot_fmt.py | 0 | 1 |
| evaluation/e6-showcase/scripts/status.py | 0 | 1 |
| evaluation/e6-showcase/scripts/verify_measurements.py | 0 | 1 |
| archive-work/E5-qgen-big/evaluation/e5-curl/question-pipeline/judge/rubric_judge.py | 1 | 0 |
| archive-work/E5-qgen-big/evaluation/e5-curl/question-pipeline/judge/write_report.py | 0 | 1 |

## Step 5: licenses and provenance

Copied 15 upstream files byte-for-byte: flask licenses to E1/E2/E2b; pytest to E3; curl COPYING to E5; svelte to E4; SWE-QA-Bench Apache-2.0 to harness/; LICENSE to tsdown, ruby_llm, cjson, fmt and gson; ruby_llm NOTICE and LICENSES/APACHE-2.0.txt; fmt doc/LICENSE-exception. Added a polyglot declaration that the project-owned synthetic fixture follows the repository MIT license. evaluation/LICENSE-DATA.md states the MIT license for project-authored data and preserves third-party licensing.

CodeWiki provenance accompanies both experiment directories and both compressed output groups: tool FSoft-AI4Code/CodeWiki, commit 5b95c84, model zai/glm-5.3-flash, software MIT copyright FSoft-AI4Code; flask/svelte licenses are also inside the corresponding archives. Local paths in those outputs use placeholders.

The harness patch now has relative a/ and b/ file headers and the manifest-specified Apache-2.0 modification notice naming all five modified files. Patch content still records the historical changes and environment configuration. The eight short CodeWikiBench topic titles in aggregate.json are retained; rubric requirement text is not included.

## Step 6: example source links

Changed 401 `[fN]:` definitions to upstream GitHub /blob/<full-commit>/ links. Counts: tsdown 41, ruby_llm 113, cjson 14, fmt 48, gson 85. Repositories were taken from local remote configuration; commits were taken from E6 inputs.json. Evaluation document source-link targets remain as recorded, apart from path redaction.

Polyglot has no upstream repository commit: its recorded 64-character identifier is a fixture content digest. Its 35 source-reference definitions remain unchanged; no commit or URL was guessed. The fixture was later published with the example; see the follow-up section below. Affected references:

- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.go` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rb` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.php` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.swift` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.kt` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/closure-functional-patterns.md` → `../../../../../../eval/polyglot-6b19d76/js_case.js` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/Sample.cs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/Sample.java` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.kt` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.php` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rb` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.swift` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.ts` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.js` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/greeting-shape-contracts.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.kt` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rb` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.cpp` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.js` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/shared-helpers.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.ts` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/python-worker.md` → `../../../../../../eval/polyglot-6b19d76/python_case.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/fixtures-and-edgecases.md` → `../../../../../../eval/polyglot-6b19d76/src/crlf.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/fixtures-and-edgecases.md` → `../../../../../../eval/polyglot-6b19d76/src/unicode.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/fixtures-and-edgecases.md` → `../../../../../../eval/polyglot-6b19d76/src/broken.c` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/fixtures-and-edgecases.md` → `../../../../../../eval/polyglot-6b19d76/tests/test_x.py` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/value-type-methods.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.go` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/value-type-methods.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/job-queue.md` → `../../../../../../eval/polyglot-6b19d76/ts_case.ts` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/entrypoint-demos.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.c` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/entrypoint-demos.md` → `../../../../../../eval/polyglot-6b19d76/src/Sample.cs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/entrypoint-demos.md` → `../../../../../../eval/polyglot-6b19d76/src/sample.rs` (fixture content digest, no pinned upstream git commit).
- `examples/polyglot/docs/nodes/java-main-and-nested.md` → `../../../../../../eval/polyglot-6b19d76/src/Sample.java` (fixture content digest, no pinned upstream git commit).

## E5 frozen files

In freeze/doc_presence.json, only the single line containing a local path changed, replacing its root with `$WORK`. The original MANIFEST.sha256 is preserved exactly as MANIFEST.original.sha256. The current MANIFEST.sha256 changes only the doc_presence.json digest; every listed file now verifies, including ../adjudications.json.

## English table derivatives

Translated only the original per-question summary tables: e1-flask-pilot/r10-reference-check.csv (10 rows), e3-pytest/r12-reference-check.csv (10), e1-flask-pilot/j10-judge-check.csv (10), e5-curl/s13-question-spotcheck.csv (8). Each row has question_id, conclusion, reason_en. The j10 conclusion preserves arm, checker score, judge score, and difference rather than inventing a categorical judgment. No new adjudication was added; source-table caveats and even the B02 table wording were retained as given.

## Step 7: compressed groups

Ten groups are tar.gz archives; the E6-catalog group is six separate catalog.json.gz files. Archives contain regular files only, with links dereferenced.

| Group | Archive | Members | Uncompressed bytes | Compressed bytes |
|---|---|---:|---:|---:|
| E1-ans | evaluation/e1-flask-pilot/answers.tar.gz | 111 | 6057089 | 1293189 |
| E1-cw-docs | evaluation/e2-flask/codewiki-docs.tar.gz | 46 | 849783 | 232124 |
| E2-ans | evaluation/e2-flask/answers.tar.gz | 196 | 10841374 | 2227384 |
| E2b-ans | evaluation/e2b-flask-25steps/answers.tar.gz | 96 | 10032568 | 2082933 |
| E3-ans | evaluation/e3-pytest/answers.tar.gz | 147 | 8705475 | 1760327 |
| E4-cbe-docs | evaluation/e4-svelte/cbe-docs-r1-r3.tar.gz | 477 | 4707455 | 1270219 |
| E4-cw-docs | evaluation/e4-svelte/codewiki-docs-1-2.tar.gz | 273 | 5533878 | 1586120 |
| E5-qgen-big | evaluation/e5-curl/question-pipeline.tar.gz | 18 | 12826899 | 2650212 |
| E5-ans | evaluation/e5-curl/answers.tar.gz | 194 | 12745787 | 2351756 |
| E5-rubric | evaluation/e5-curl/rubric-judge.tar.gz | 154 | 3991370 | 445690 |

## Query-layout experiment and remaining decisions

The private Python 3.12 environment uses the nine requested runtime packages, including tiktoken 0.14.0 and all eight tree-sitter package versions pinned in pyproject.toml. Every example was tested with one real find term and one real query ID from its catalog. With the publication layout (docs plus catalog.json.gz), all 12 commands exit 2 because this CBE version opens catalog.json directly. With catalog.json decompressed in a separate trial directory, all 12 commands exit 0 and return nonempty JSON. No context file is needed for those tested queries; this does not establish every optional query mode.

Keep compressed catalogs in the repository and instruct readers to run `gzip -dk examples/<repo>/catalog.json.gz` locally before find/query. Publishing plain catalogs instead would add about 29.5 MB before removing the compressed copies. No CBE code or publication layout was changed to hide this failure. The coordinator owns the final evaluation README and per-repository example pages; neither was written here.

## Final checks

The copied scanner is adapted outside this directory to enumerate final staged files and each final tar archive member. Original matching patterns and 96 SWE-QA / 59 rubric probes are retained; scan outputs, exact commands, interpreter version, dependency freeze, copy/redaction ledgers, and integrity results were kept with the private working files and are not published.

## Follow-up before publishing

- polyglot: the fixture has no upstream repository; it is this project's own test fixture (MIT, see examples/polyglot/LICENSE). Its 23 source files were copied from the pruned copy `polyglot-6b19d76` into `examples/polyglot/source/`, and the 35 `[fN]:` reference lines in 9 pages were rewritten to relative paths into `source/`; every rewritten link resolves.
- E6 catalogs stay compressed (`catalog.json.gz`, 2.2 MB for six repos instead of about 30 MB); each example page tells readers to run `gzip -dk examples/<repo>/catalog.json.gz` before `cbe find` or `cbe query`.
- A later independent scan found 9 truncated user-name fragments in `ls -l` output inside `evaluation/e3-pytest/answers.tar.gz` (2 members) and `evaluation/e5-curl/answers.tar.gz` (7 members). They were replaced with `owner`, and both archives were rebuilt with the same member order and normalized headers.
- The private task-directory prefix in 21 historical scripts and records, and in 2 members of `evaluation/e5-curl/question-pipeline.tar.gz`, was replaced with `$TASK_DIR`.
- Added after the first publication: `evaluation/e2-flask/cbe-docs/catalog.json.gz` (715 KB; SHA-256 `2133b476842fe01ca86d1c0bf7a8dbb20d43f799f8f50c9c2c5bb8e0b3833713`). It is `gzip -9 -n` of the `catalog.json` from the same CBE run as the published Flask docs (run `7b9409`, see `STATUS.md` in that folder), so readers can run `cbe find` and `cbe query` on the Flask docs after `gzip -dk evaluation/e2-flask/cbe-docs/catalog.json.gz`. It was scanned for local paths, user names, e-mail addresses and key-like strings before publication (none found; the `@` matches are Python decorators such as `@app.route`).
