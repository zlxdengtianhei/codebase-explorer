# CBE evaluation

This page reports six evaluation rounds (E1–E6) run on Codebase Explorer (CBE) 2.2.0.dev0 in October 2026. They ask three questions: does CBE documentation change an agent's score on code-understanding questions (Q-A), how much of a published rubric do CBE documents cover compared with CodeWiki (Q-B), and what does generation cost compared with CodeWiki (Q-C). A showcase on six small repositories was generated but not scored.

Short answer: on flask and pytest, no difference was detected between an agent that had CBE documents and commands and one that read only the source. On curl, in this exploratory reading, that agent's rubric score was 5.60 points higher than the source-only agent's, interval [+0.90, +10.82]; it is a single exploratory secondary result, and its conditions must travel with it ([Q-A: curl](#q-a-curl-e5)). On svelte, CBE and CodeWiki documents got identical coverage verdicts. With the same svelte input and model id, CBE used 13.3%–18.0% of CodeWiki's gateway requests and 8.4%–11.4% of its prompt tokens, with each tool on its own settings. Every result holds only under its conditions: one answering model, one judge model family, one documentation generation per repository, and a 10-step agent limit that nearly every answer reached.

**How to read the numbers**

- Token counts use tiktoken's `o200k_base` encoding. Each repository's input scope (which directories were kept) is listed in [Repositories and inputs](#repositories-and-inputs).
- Intervals are 95% percentile bootstrap intervals. Q-A resamples questions in pairs, 10,000 times; Q-B pairs rubric leaves.
- When an interval contains 0, we write "no difference detected". This does not mean the arms are equal.
- "We infer" marks a judgment, not a measurement, and says who made it. The *coordinator* is the agent session that ran the evaluation; a *checker* is a separate agent that did not run the stage and recomputed it from raw files.
- Costs are the `cost_usd` that the Magpie gateway records per request. The gateway computes it from its own price table (the *gateway price table*), not from a provider's public price list. Request and token counts do not depend on prices.

## What we measured

| Question | What it asks | Compared |
|---|---|---|
| Q-A question answering | Does giving an answering agent CBE's `docs/` (and the `cbe find` / `cbe query` commands) change its score on code-understanding questions, compared with reading only the source? | Arms S, C0, C (and W on flask), defined in [Setup](#arms) |
| Q-B coverage | In svelte, what share of the CodeWikiBench rubric do the documents cover, under one judge and one rubric? | CBE and CodeWiki documents |
| Q-C cost and size | With the same input and the same model id, how many gateway requests, prompt tokens, gateway cost and published-document tokens does each tool use? | CBE and CodeWiki generation runs |
| Showcase | Do six small repositories in different languages generate end to end and pass `cbe host verify`? | Not scored |

The primary metric was fixed before the runs: the C − S paired difference in total score on the 48 flask questions. pytest, curl, the five dimensions, layers and difficulty bands are secondary: we report their intervals and draw no multiple-comparison conclusions from them.

## Headline results

| Question | Result | Conditions that go with it |
|---|---|---|
| Q-A flask (E2) | 48 questions, 10-step limit: C − S −0.46 [−3.08, +2.10], no difference detected. Pre-specified 25-step comparison (24 questions): +1.88 [−2.50, +7.17], no difference detected; the same 24 questions at 10 steps gave −0.17, the opposite sign; both intervals contain 0, so this is a difference between point estimates, and both are reported. | 97.9%–100% of answers hit the 10-step limit, so the result holds only at that limit. The C arm issued `find`/`query` in only 7 of 48 questions, so C behaved close to C0; this is not evidence that the commands do not help. One answering model, one judge model family, one CBE generation. CBE commit `9c6499e` (E3–E6 used `a87674d`; E2 was not rerun at it). 10 of the 48 questions reuse pilot answers. Some subgroup intervals exclude 0 and are reported in the section. SWE-QA questions may be known to the model. |
| Q-A pytest (E3) | 48 questions, 10-step limit: C − S −0.06 [−3.12, +3.15], no difference detected. | 95.8%–100% hit the limit. C executed `find`/`query` in 2 questions, so C behaved close to C0. For C's last 15 questions the shared Python environment had been replaced and `cbe` could not run. One repository, generation, answering model and judge family. Of 10 reference answers checked, 5 right, 4 partly right, 1 wrong. 2 of 24 subgroup intervals exclude 0; no conclusion. No 25-step run. |
| Q-A curl (E5) | 40 self-authored questions, 10-step limit. In this exploratory reading, arm C's rubric score was 5.60 points higher than arm S's, interval [+0.90, +10.82]. | Secondary metric, single exploratory reading. The lower end, +0.90, is close to 0: the scoring of a single answer can pull it below 0 (with the rescorer's verdicts on 10 spot-checked answers: +4.70 [−0.29, +9.94]). Five-dimension score: no difference detected. At 25 steps the rubric point estimate had the opposite sign; both intervals contain 0. The subgraph cards used to write the questions share an origin with the dependency lines in CBE's documents (not tested). 15 of 96 subgroup intervals exclude 0; no conclusion. Full list of conditions in [Q-A: curl](#q-a-curl-e5). |
| Q-B coverage (svelte) | Identical leaf verdicts: 94/96 each, weighted 95.8476% each; no difference detected, both close to the maximum. | One judge, one verdict per leaf, one generation per side, one repository. The judge can recognize CBE's program labels. The rubric checks "mentions and explains", not correctness. "The rubric is at its ceiling and cannot separate the two" is an inference, not a result. The input had no `.svelte` files, so this says nothing about CBE handling `.svelte`. |
| Q-C cost and size (svelte) | Same input, same model id. CBE ÷ CodeWiki: gateway requests 13.3%–18.0%, prompt tokens 8.4%–11.4%, gateway cost 33.8%–45.3%, output tokens 70.1%–93.8%, published documents 54.8%–63.8% (CBE counts `docs/**/*.md` with its `[fN]:` reference lines; CodeWiki counts the top-level `*.md`). | CBE 3 runs, CodeWiki 2: observed ranges, not confidence intervals. One repository, one model. All five first passes were incomplete; the figures include one resume each. Each tool used its own settings: reasoning tokens were 9.8%–11.0% of CBE's output and 47.9%/48.1% of CodeWiki's, so output and cost ratios include a settings difference. Costs use the gateway price table. Fewer document tokens do not mean less coverage. Wall clock is recorded only. |
| Showcase (E6) | 5 of 6 repositories complete and pass verify; fmt stayed partial after two resumes. Total 1.352381 USD (gateway price table). | fmt's `format.h` and `core.h` have no published unit (39.663% of its source). The polyglot example is the rerun under Python 3.12; its source is only 1,708 tokens. cJSON, fmt and gson ran under Python 3.13. Verify passing does not mean the explanations are correct. Examples carry the upstream license files. |

## Setup

The six rounds: E1, a 10-question pilot on flask (its readings are not conclusions); E2, flask Q-A; E3, pytest Q-A; E4, svelte Q-B and Q-C; E5, curl Q-A; E6, the showcase.

### Repositories and inputs

Each repository was exported at a fixed commit without `.git` into a *pruned copy* that keeps only the listed directories; this is the input scope of every measurement on that repository. CBE, CodeWiki and the answering agents all read the same pruned copy. Within it, CBE's default source discovery decides which files become documentation input; the counts are in the table. The file lists of the pruned copies are in `evaluation/inputs/`. All token counts are `o200k_base`.

| Repository | Commit | Kept | Size of the pruned copy | Used in |
|---|---|---|---|---|
| flask | `85c5d93` | `src/`, `tests/` | 87 files; CBE read 65 `.py` files, 125,125 o200k tokens | E1 pilot, E2 |
| pytest | `5989efe` | `src/`, `testing/` | 249 files, 752,827 o200k tokens; CBE froze 225 `.py` files | E3 |
| curl | `2c04412d8` | `lib/`, `src/`, `include/` | 506 files, 1,741,311 o200k tokens; CBE's default discovery took 485 source files (1,714,019 tokens) and skipped 21 non-source files | E5 |
| svelte | `be645b4` | JS/TS sources without tests, `documentation/` or `*.md` | 440 files (396 `.js`, 44 `.ts`, no `.svelte`), 531,705 o200k tokens | E4 |
| Showcase | see [Showcase](#showcase-e6) | per repository, listed in the Showcase table | 1,708 to 185,053 tokens per repository | E6 |

### Questions

- **flask and pytest:** all 48 SWE-QA questions for each repository (SWE-QA is Apache-2.0). On flask, 10 of the 48 are the E1 pilot questions; their 10-step answers and scores were reused.
- **curl:** 40 questions written for this evaluation, each with an atomic rubric. Two Claude Opus subagents read the pruned copy and program-generated *subgraph cards* (excerpts of the Joern code graph) and wrote 56 candidates. `codex/gpt-6.1-sol` checked 531 rubric items: 501 hold, 28 partly hold, 2 do not hold; 1 question was dropped, leaving 55. A Sonnet subagent spot-checked 8 questions and found 0 substantive errors. A closed-book filter had GLM-5.3-Flash answer each candidate without tools; questions scoring 70 or more would be removed, and 0 of 55 were (highest score 55.56). 40 questions were selected by independent labels: layers 1–4 = 3/8/18/11 (layers 3 and 4 make up 72.5%), 10 per question type (What, Why, Where, How). The four layers, in order, are: locate, unit behavior, cross-module flow, and impact and design. Two rubric adjudications were applied before answering (in B16, two items moved from core to supporting; in B11, item r1 accepts the formula or the value 100).
- **Frozen before answering (curl):** questions, rubrics and report rules were committed 3 hours 18 minutes before the first answer; document-presence labels were committed before the first answer. The spot-check list was committed after the first answer had started; the coordinator states it was written before reading any answer or score, which file times cannot confirm. The 25-step stopping threshold was also set after the first answer had started.

### Arms

- **S:** source only.
- **C0:** S plus CBE's generated `docs/`; no commands.
- **C:** C0 plus `cbe find` and `cbe query`.
- **W:** S plus CodeWiki's documents (flask only).

C0 − S isolates the documents, C − C0 the commands, C0 − W the difference between the two document sets.

### Answering agent

- Harness: SWE-QA-Bench `SWE-agent_QA` at commit `c13deac`, with tools `bash`, `read_file`, `grep` and `ls`.
- Our changes to the harness (published as a patch): (1) the arm prompt is added in `_build_instance_prompt` and the output keeps the original question; (2) one observation is cut at 20,000 characters; (3) a step limit; (4) the tool subprocess `PATH` and the absolute path of `cbe`; (5) for arm C only, `bash` is allowed for commands that start with the absolute `cbe` path and whitespace and contain none of ``; & | ` $ > <`` or a newline. Answering and judge requests time out after 240 seconds, with SDK retries off.
- Model: `zai/glm-5.3-flash` through the Magpie gateway, at most 4 answers in parallel. An attempt without an answer is rerun in full up to 2 times; after that it is NA, scored 1 per dimension, 5 in total.
- Isolation: each arm has its own pruned copy without `.git`. Tool subprocesses run under macOS `sandbox-exec` with no network and read access only to that arm's copy, documents and run directory.

### Judges

- **Five-dimension judge (all Q-A):** the SWE-QA judge prompt, five dimensions of 1–20 points each, total 100; `codex/gpt-6.1-sol`; 3 draws per answer, median per dimension, then summed. It sees the question, the reference answer and the answer.
- **Rubric judge (curl, primary):** `codex/gpt-6.1-sol` decides each rubric item. It does not see the reference answer text or the source. Each "satisfied" verdict must quote the answer, and a program checks that the quote is a substring of the answer. Majority of 3. NA scores 0.
- **Coverage judge (Q-B):** CodeWikiBench with its svelte rubric (96 leaves, 8 top-level topics), `codex/gpt-6.1-sol` with `--use-tools`, one verdict per leaf, same parameters for both sides.

The answering model (GLM) and the judges (GPT) are from different model families.

### CBE commits

flask (E1, E2) used CBE `9c6499e`; pytest, curl, svelte and the showcase (E3–E6) used `a87674d`. E2 was not rerun at `a87674d`: it stays at `9c6499e` because the frozen flask source is byte-identical under both commits, which five separate checks confirmed.

## Results by question

### Q-A: flask (E2)

**Primary, 10 steps, 48 questions**

| Arm | Mean score (NA = 5) | Valid answers | Hit the 10-step limit |
|---|---:|---:|---:|
| S | 77.71 | 48/48 | 97.9% |
| C0 | 77.90 | 48/48 | 97.9% |
| C | 77.25 | 48/48 | 100.0% |
| W | 75.38 | 48/48 | 100.0% |

| Pair | Mean difference [95% interval] | Reading |
|---|---|---|
| C − S (primary) | −0.46 [−3.08, +2.10] | no difference detected |
| C0 − S | +0.19 [−2.56, +3.08] | no difference detected |
| C − C0 | −0.65 [−3.42, +2.04] | no difference detected |
| C0 − W | +2.52 [−0.15, +5.29] | no difference detected |
| C − W | +1.88 [−1.02, +5.10] | no difference detected |

A checker recomputed every pair from the per-question judge draws; all matched, with interval end points within 0.17.

**Pre-specified secondary comparison, 25 steps, 24 questions**

| Arm | Mean score | Hit the 25-step limit |
|---|---:|---:|
| S | 76.21 | 79.2% |
| C0 | 74.08 | 75.0% |
| C | 78.08 | 83.3% |
| W | 77.38 | 75.0% |

| Pair | 25 steps | Same 24 questions at 10 steps |
|---|---|---|
| C − S | +1.88 [−2.50, +7.17] | −0.17 [−2.75, +2.29], point estimate of opposite sign |
| C0 − S | −2.12 [−7.83, +3.17] | — |
| C − C0 | +4.00 [−0.42, +9.29] | — |
| C0 − W | −3.29 [−8.58, +1.21] | +1.62 [−1.92, +5.12], point estimate of opposite sign |
| C − W | +0.71 [−2.58, +4.46] | — |

All these intervals contain 0, so the opposite signs are differences between point estimates. The rules fixed before E2 say: when the two step limits disagree in direction, report both and prefer neither.

**What the C arm actually ran.** At 10 steps: 11 `find`/`query` requests, 10 executed, 8 succeeded, 1 blocked (a query with a pipe and a redirect, from a reused pilot answer). Only 7 questions issued `find`/`query`, and 6 of them had at least one success; `--help` ran 7 more times. At 25 steps: 28 requested, 28 executed (12 `find`, 16 `query`), 21 succeeded, 0 blocked, in 8 questions; a checker found one more `cbe source … || cbe find …` command that the tool layer blocked and the original audit did not count. So at 10 steps the C arm behaved close to C0, and C − C0 cannot be read as "the commands do not help".

**Sensitivity (C − S)**

| Subset | Why | 10 steps | 25 steps |
|---|---|---|---|
| Without the 10 pilot questions | not independent samples | −0.47 [−3.68, +2.76], n=38 | +0.14 [−3.86, +5.21], n=14 |
| Without q32 | its premise and reference answer have no support in the source | −0.47 [−3.11, +2.21], n=47 | +2.22 [−2.39, +7.74], n=23 |
| Without q4, q11, q47 | reference answers partly wrong or weak premise | −0.67 [−3.38, +2.13], n=45 | +1.00 [−3.52, +6.52], n=21 |
| Valid answers only | — | −0.46 [−3.08, +2.17], n=48 | same as all |

All contain 0. One sign changed: at 25 steps, C0 − W is −3.29 on all 24 questions and +1.21 [−1.93, +5.14] without the pilot questions (n=14). We infer (checker) that the negative sign at 25 steps comes mainly from the reused pilot questions.

**Subgroups (reported, not conclusions).** Of the 35 question-type and layer intervals at 10 steps, 1 excludes 0; about 1.75 would by chance. The difficulty-band and 25-step subgroup intervals were computed separately and have not been counted together. These subgroup intervals exclude 0:

| Reading | Mean difference [interval] | n |
|---|---|---:|
| 10 steps, high direct-answer band, C − S | −3.17 [−6.96, −0.08] | 24 |
| 10 steps, high band, C0 − S (checker) | −2.58 [−5.12, −0.04] | 24 |
| 10 steps, low band, C0 − W (checker) | +3.96 [+0.92, +7.08] | 24 |
| 10 steps, question type What, C − C0 | interval only: [+0.75, +11.00] | 12 |
| W arm, 25 steps minus 10 steps | +5.17 [+0.12, +11.13]; lower end +0.08 to +0.12 depending on seed | 24 |
| 25 steps, low band, C0 − W | −7.75 [−16.75, −0.58] | 12 |
| Same questions at 10 steps, low band, C0 − W | +7.17 [+3.58, +11.17] | 12 |
| Same questions at 10 steps, high band, C0 − W | −3.92 [−8.50, −0.17] | 12 |

Difficulty bands split the 48 questions at the median score of a direct answer without tools, 68.5; the high band holds the questions the model answered well without tools. The direct-answer prompt asks for short answers and the judge penalizes short answers, so the bands describe difficulty only under that prompt and judge.

**Citation check (auxiliary).** 97.0%–98.3% of the `.py` paths named in answers exist; answers contained no checkable explicit line numbers. A path that exists does not show that it supports the claim.

**Conditions for every flask reading**

1. 97.9%–100% of answers hit the 10-step limit, so the result holds only at this limit; at 25 steps 75.0%–83.3% still hit it.
2. One answering model (`zai/glm-5.3-flash`), one judge model family (`codex/gpt-6.1-sol`).
3. C and C0 read one CBE generation (`9c6499e`); the intervals do not include variation between generations.
4. 10 of the 48 questions reuse E1 pilot answers and are not independent repeats; the 24 questions at 25 steps include them too.
5. The size of the 25-step subset was derived from the 147 answers E2a had finished, not the planned 152 (a recorded deviation).
6. The C arm issued commands in only 7 of 48 questions.
7. Subgroup intervals that exclude 0 are reported with the primary reading, labelled as subgroup readings.
8. The reporting rules were committed before E2's answers, but the 10 pilot scores had been seen; "fixed before seeing the data" holds for the 38 new questions only.
9. CBE commit `9c6499e`; E2 was not rerun at `a87674d`.
10. SWE-QA is public, so the answering model may have seen these questions. Questions with defective reference answers are scored as they are, with the sensitivity analyses above.

### Q-A: pytest (E3)

| Arm | Mean score | Valid answers | Hit the 10-step limit |
|---|---:|---:|---:|
| S | 71.25 | 48/48 | 97.9% |
| C0 | 72.46 | 48/48 | 100.0% |
| C | 71.19 | 48/48 | 95.8% |

| Pair | Mean difference [95% interval] | Reading |
|---|---|---|
| C − S (primary for this repository) | −0.06 [−3.12, +3.15] | no difference detected |
| C0 − S | +1.21 [−1.00, +3.54] | no difference detected |
| C − C0 | −1.27 [−3.90, +1.54] | no difference detected |

A checker recomputed from the 144 judgments; end points differed by at most 0.17. pytest has no CodeWiki arm and no 25-step run.

**What the C arm actually ran.** 3 `find`/`query` requests, 3 executed, 3 succeeded (q8: one `find`, one `query`; q30: one `find`). `--help` ran 7 times; the q39 call crashed with return code −6 because the sandbox blocked `libpython`. 18 more `find`/`query` calls were written but never executed (q16 3, q34 2, q35 2, q36 2, q47 9): the harness executes only the first tool call in each reply, and these came later in the same reply. 7 questions wrote a non-help `find`/`query`. `bash` was blocked in every arm: in 47/48 questions for S, 46/48 for C0 and 48/48 for C (52, 58 and 69 times); replies with several tool calls made up S 10.7%, C0 20.5%, C 27.6%. We infer (checker; adopted by the coordinator) that these effects also apply to S and C0, so C − S and C − C0 carry no one-sided bias from them; they do make C behave close to C0.

**Environment change during the run.** For C's questions q33–q47 (15 questions), another session had replaced the shared Python environment, and `cbe` could not run.

**Sensitivity (all intervals contain 0)**

| Subset | Reading |
|---|---|
| Without q22 (reference answer wrong) | C − S +0.02 [−3.09, +3.23], n=47 |
| Without q3, q4, q7, q34 (reference answers partly right) | C − S +0.84 [−2.02, +4.07], n=44 |
| Valid answers only | C − S −0.06 [−3.10, +3.19], n=48 |
| Only q0–q32 (before the environment change) | C − S +0.64 [−2.94, +4.70]; C − C0 −0.61 [−3.39, +2.97]; C0 − S +1.24 [−1.36, +3.88]; n=33 |
| Only q33–q47 | C − S −1.60 [−7.67, +3.33], n=15 |

**Subgroups.** Of 24 question-type and layer intervals, 2 exclude 0, about 1.2 expected by chance: Why C − S [−13.08, −0.17] (point estimate −5.92, computed by the checker) and Why C − C0 [−12.50, −1.00], 12 questions each. No conclusion.

**Citation check (auxiliary).** Paths named in answers that exist: S 530/589, C0 469/518, C 407/439. Explicit line numbers: S 1 (0 checkable), C0 1 (exists), C 12 (all exist).

**Conditions for every pytest reading**

1. One repository, one documentation generation, one answering model, one judge model family.
2. 95.8%–100% of answers hit the 10-step limit; the result holds only at this limit.
3. The C arm executed commands in 2 questions; C behaved close to C0, so C − C0 cannot be read as "the commands do not help".
4. For q33–q47 the C arm could not run `cbe`.
5. 10 reference answers were checked against the source: 5 right, 4 partly right, 1 wrong. 6 reference answers carry a leftover `start_of_answer` marker that was passed to the judge as is and may affect scores.
6. Difficulty bands split at the median direct-answer score, 61.5, and describe difficulty only under that short-answer prompt.
7. 2 of 24 subgroup intervals exclude 0; no conclusion.
8. No 25-step run. SWE-QA is public, so leakage is possible.

### Q-A: curl (E5)

**What can be said.** In this exploratory reading, arm C's rubric score was 5.60 points higher than arm S's, interval [+0.90, +10.82] (40 questions, 10 steps). Rubric C0 − S was +6.64 [+1.50, +11.74], which also excludes 0, and C − C0 was −1.04 [−6.98, +5.26], which contains 0. S and C rubric means were 25.17 and 30.77, so neither the ceiling rule (both ≥85) nor the floor rule (both ≤15) applied.

**Conditions that must be quoted with this result.** This list is the full set of publication conditions for curl. Quote the result only together with it.

1. curl is a secondary metric of this evaluation. The result is a single exploratory reading, and no multiple-comparison conclusion is drawn from it.
2. The lower end, +0.90, is close to 0; the scoring of a single answer can pull it below 0. Across 30 bootstrap seeds the lower end stayed between +0.70 and +0.99. In the judge spot check below, the rubric judge and an independent rescorer disagreed on 10 of 103 items, all with the judge marking "not met"; 4 of the 5 disagreements in arm S are in one answer, B20, which the judge scored 18.18 and the rescorer 81.82. Giving all 10 spot-checked answers the rescorer's verdicts changes C − S to +4.70 [−0.29, +9.94], an illustration computed by a checker, not a pre-specified analysis. That change comes almost entirely from B20: swapping B20 alone lowers the C − S mean by about 1.59, while swapping the other nine together raises it by about 0.70 (means computed by a second checker; the interval with only B20 swapped was not computed). This does not show that the judge is stricter overall or stricter for arm S: there are only 3–4 spot-checked answers per arm, one rescorer, and the coordinator re-checked only 2 answers.
3. The five-dimension score, reported alongside, shows C − S −0.93 [−5.58, +3.40], no difference detected. The two scores disagree in direction; the frozen rules report both and prefer neither.
4. The pre-specified 25-step comparison completed 17 of 20 planned questions. Rubric C − S was −1.61 [−10.88, +7.77] and five-dimension C − S +2.29 [−2.06, +6.71]; both show no difference detected. The same 17 questions at 10 steps gave rubric C − S +4.85 [−0.48, +10.98]. The rubric point estimate at 25 steps has the opposite sign to the primary result, but both of these intervals contain 0, so the difference in direction is between point estimates only.
5. The subgraph cards share an origin with the dependency lines in CBE's documents; part of the difference may come from this (not tested). The question writers read the pruned source and subgraph cards built from the Joern graph; the same graph also produces the output of `cbe query`. For this reason the questions anchored at function-pointer dispatch are reported separately (table below).
6. "The difference comes from the documents" is an inference (coordinator), and only under the rubric score: rubric C0 − S excludes 0 while C − C0 contains 0, but five-dimension C0 − S is +0.53 [−2.65, +3.70], no difference detected. The C arm ran `find`/`query` in only 9 of 40 questions (20 executed, 15 succeeded), so these data cannot measure what the commands do.
7. 15 of 96 subgroup intervals exclude 0 (rubric 11, five-dimension 4); about 4.8 would by chance. The subgroups overlap; no conclusion.
8. One repository, one documentation generation, one answering model, one judge model family. All valid answers hit the 10-step limit, so the result holds only at this limit.
9. The judge is strict: 28 of 40 questions scored 0 closed-book, and rubric means of 25–32 should be read as scores under this judge. The result holds only for questions that passed the closed-book filter. That filter deviated from "one answer per question": one successful answer was lost before it was saved and the question was answered again; the affected questions (A02, A06–A10) are inferred.
10. Per question, C scored higher on 13, S on 9, and 18 tied (mostly 0 against 0); the median difference is 0, and the 5 largest differences make up 82% of the total (checker's count). +5.60 is not a uniform shift.
11. Question selection deviated from the proposal's layer quota (4/8/14/14). "Not enough candidates" was true; "adding questions needs another round" is a cost reason. This is disclosed as a deviation from the proposal, not as "more questions were impossible".
12. The label "unit present in the catalog" is not "the documents mention it". Of the 15 (file, name) pairs labelled "not present", 10 names appear somewhere in a published page's text. 13 of these pairs (12 distinct names) have no matching unit: macros 5, file-level static variable 1, typedef 1, bit-field member 1, header declaration 1, non-static global 1, enum constants used as `case` labels 2; the other 2 are struct definitions indexed without a unit. The 10 "not present" questions are all What or Why and cite 5.9 names on average, against 3.9 for "present", so the label is mixed with question type and citation count. "Present" includes members of grouped units: of the 175 (file, name) entries in the core rubric items (a name cited by two items counts twice), 160 are present, and 35 of those are members of grouped units rather than units of their own. Subgroups are reported on the frozen label (`in_docs`); the strict reading (`own_unit`, units of their own only) is reported in addition.
13. 8 questions were spot-checked before selection, and 6 of them are among the 40; 0 errors in 8 has a 95% upper bound of about 3/8, so errors in the other questions are not excluded.
14. The spot-check list was committed after the first answer had started; the coordinator states it was written before reading any answer or score, which file times cannot confirm. The 25-step stopping threshold was also set after the first answer had started.
15. The C arm ran `cbe` in a private Python 3.12 environment with 9 runtime dependencies at the versions in `pyproject.toml` and tiktoken pinned to 0.14.0 (the frozen commit has no lock file); smoke test 19/19. Whether it matches E3's shared environment package by package cannot be shown. Against the restored shared environment, all 20 executed commands gave byte-identical output (20/20).
16. In the documentation generation (E5a), 153 of the 485 source files (31.5%) reported a Tree-sitter `syntax_error`, and the reused graph hit the 50,000-edge cap for reaching definitions once (486,150 edges omitted). Complete and verified does not prove the documents are semantically correct.
17. E5a's first pass started under Python 3.12; the shared environment was rebuilt as 3.13 during it (2026-10-17 23:56:36Z), and the two resumes and verify ran under 3.13. The effect on the first pass was not checked.

**Primary reading**

| Arm | Valid answers | Rubric mean | Five-dimension mean | All core items met | Hit the 10-step limit |
|---|---:|---:|---:|---:|---:|
| S | 40/40 | 25.17 | 65.20 | 10.0% | 100.0% |
| C0 | 40/40 | 31.81 | 65.72 | 17.5% | 100.0% |
| C | 39/40 (A04: no valid answer in three attempts, NA) | 30.77 | 64.28 | 20.0% | 100.0% of the 39 valid |

| Score | C − S | C0 − S | C − C0 |
|---|---|---|---|
| Rubric, all 40 (NA = 0), primary | +5.60 [+0.90, +10.82] | +6.64 [+1.50, +11.74] | −1.04 [−6.98, +5.26] |
| Rubric, valid only | +5.74 [+0.90, +11.03] (n=39) | +6.64 [+1.50, +11.74] (n=40) | −0.50 [−6.46, +5.90] (n=39) |
| Five-dimension (NA = 5) | −0.93 [−5.58, +3.40] | +0.53 [−2.65, +3.70] | −1.45 [−6.17, +3.10] |
| Five-dimension, valid only | +0.38 [−3.26, +4.28] (n=39) | +0.53 [−2.65, +3.70] | −0.28 [−4.46, +3.97] (n=39) |

Seed 20261018 for every pair. The coordinator recomputed from the raw judge replies (re-parsed each rubric reply, re-checked each quote, re-took the majority; re-took the five-dimension medians): every vote and every per-question score matched. With other seeds, C0 − S and C − C0 gave [+1.66, +11.71] and [−7.04, +5.25]; whether they contain 0 did not change.

**Judge spot check.** A Sonnet subagent that neither answered nor judged, and could not see arms or judge votes, rescored 10 answers (S 3, C0 3, C 4) item by item against the source: 103 items. It agreed with the rubric judge on 93/103 (90.3%), Cohen's kappa 0.789. In all 10 disagreements the judge marked "not met" and the rescorer "met"; there was no disagreement in the other direction. Disagreements by arm: S 5, C0 2, C 3; as rates, S 16.1% (5/31), C0 6.1% (2/33), C 7.7% (3/39). 4 of the 5 in arm S are in one answer, B20 (judge 18.18, rescorer 81.82). On these 10 answers the judge's mean was 35.64 and the rescorer's 50.02. The coordinator re-checked 2 of the 10 against the source: it agreed with the rescorer on every item and differed from the judge on 1. The rescorer found no wrong rubric item, and noted that 5 answers named functions that do not exist in this source tree. In the same illustration, C0 − S becomes +5.21 [−1.33, +11.25] and C − C0 −0.51 [−6.83, +6.27]. These 10 answers are 8% of the 120, and there was one rescorer; we do not judge who is more accurate. With 3–4 answers per arm, these data cannot show whether the judge is stricter for one arm.

**25-step secondary comparison**

| Item | Reading |
|---|---|
| Gate | It started only if primary answering used at most 12,000,000 input tokens; measured 11,887,507. |
| Coverage | 20 questions planned; answering stopped at its threshold of 15 million input tokens (15,409,608 used) after 17 complete pairs, all valid; B23, B26, B28 did not start. |
| Rubric | S 47.79, C 46.18; C − S −1.61 [−10.88, +7.77], n=17 |
| Five-dimension | S 72.18, C 74.47; C − S +2.29 [−2.06, +6.71], n=17 |
| Step limit | S and C each 16/17 hit the 25-step limit |

Coverage is short of the plan, so no conclusion is drawn about the 20-question comparison.

**What the C arm actually ran.** 23 `find`/`query` calls written, 20 reached the tool handler and were executed, 15 succeeded, 0 blocked, 3 written but not executed; `--help` ran 19 times. 9 questions executed a non-help `find`/`query`. The 5 failures all returned 2: 4 passed the search term or unit id as a positional argument instead of `--term`/`--id`, and 1 `query --id` named an unknown unit. At 25 steps: 42 written, 38 executed, 33 succeeded, 4 written but not executed.

**Process counts (all three arms)**

| | S | C0 | C |
|---|---:|---:|---:|
| Replies with several tool calls | 15.3% | 11.5% | 12.4% |
| Tool calls written but not executed | 188 | 140 | 80 |
| `bash` blocked | 53 | 50 | 53 |
| `grep` calls containing an unescaped `a\|b` | 36.1% | 36.1% | 34.3% |

**Subgroups and sensitivity (intervals only, no conclusions)**

| Subset | Rubric reading |
|---|---|
| Same 17 questions as the 25-step run, at 10 steps | C − S +4.85 [−0.48, +10.98] |
| Unit present in the catalog (`in_docs`, 30 questions) | C − S [−1.50, +8.39]; C − C0 [−10.30, +2.05] |
| Not present (10 questions) | C − S [+1.67, +25.12]; C − C0 [−6.15, +23.86] |
| Strict reading, own unit (`own_unit`, 15 questions) | C − S [+0.40, +15.22]; C0 − S [−0.71, +14.02]; C − C0 [−8.03, +10.05] |
| Strict reading, no own unit (25 questions) | C − S [−1.58, +11.39]; C0 − S [+0.06, +13.46], lower end crosses 0 for 10 of 30 seeds; C − C0 [−10.11, +6.33] |
| Function-pointer dispatch anchors (14) / others (26) | C − C0 [−12.94, +10.10] / [−7.73, +6.72]; C − S [−4.07, +8.84] / [+1.14, +14.42] |
| Closed-book score 0 (28) / above 0 (12) | C − S [+0.34, +13.34] / [−2.04, +9.52] |

No question was found to have a wrong reference answer or rubric after freezing, so the planned drop-wrong-questions analysis was not needed. All 96 subgroup intervals are in the published metrics.

**Direct answers (difficulty calibration, five-dimension).** 29 of 40 valid; 11 NA after three timeouts under the 240-second limit. Mean 40.12 over 40 questions with each NA scored 5; 53.45 over the 29 valid. E2 and E3 report the median direct-answer score (68.5 and 61.5); the two are not directly comparable.

**Cost (gateway price table).** 8 sessions, 3,482 requests, 8.318145 USD; 64 HTTP 499 responses carried no usage and were not estimated. Primary answering: 1,494 requests, 0.997613 USD; 25-step answering: 907 requests, 0.769247 USD; rubric judge for the primary comparison: 3.004433 USD. For every request the gateway served the requested model. Primary answering took 11,058.7 seconds of wall-clock time.

### Q-B: coverage (E4q)

Under one judge and one rubric, CBE (run r1) and CodeWiki (run 1) received identical verdicts on all 96 leaves; no difference detected, and both are close to the maximum. A checker recomputed from the 2×96 raw verdicts; all matched.

| Reading | CBE r1 | CodeWiki 1 |
|---|---|---|
| Weighted score | 95.8476% | 95.8476% |
| Leaves passed | 94/96 (97.9167%), NA 0 | 94/96 (97.9167%), NA 0 |
| Paired difference (unweighted) | +0.0000 pp [0.0000, 0.0000]; 0 leaves differ | |
| Leaves failed by both | 1.1.2 and 2.0.0 | |
| Top-level topics | Fine-Grained Reactivity Engine 83.9286%, Component System and Architecture 89.7727%, the other 6 at 100%; same on both sides | |
| 47 `.svelte`-related leaves / other 49 | 47/47, 47/49 | 47/47, 47/49 |
| Weighted score without the 47 leaves | 91.9017% | 91.9017% |
| Judge tokens, requests, gateway cost | 11,451,940 tokens, 311 requests, 8.228079 USD | 14,018,641 tokens, 303 requests, 10.120151 USD |
| `docs_tree` sent to the judge | 27,807 tokens (121,471 bytes), 169 nodes | 35,927 tokens (158,861 bytes), 133 nodes |

The two runs judged were chosen before scoring as the lowest-numbered complete run of each tool, not by quality. A second round was not judged: the first round used 25,470,581 tokens, above the 20 million limit set in advance. The interval [0.0000, 0.0000] comes from all-zero paired differences, which make the bootstrap degenerate. It excludes the judge's own bias, repeat-judging noise and variation between generations, so it is not evidence of equivalence.

**Conditions**

1. One judge, one verdict per leaf.
2. One generation per side; variation between generations was not measured. CodeWiki run 1 has 6 top-level overview pages that hold only an opening sentence (81–106 bytes); run 2 does not. They were judged as they are.
3. The judge can recognize CBE's program-written labels in its pages.
4. One repository.
5. The rubric checks whether a point is mentioned and explained, not whether it is correct. A read-only check of six passed leaves found one (6.0.1) where the judge merged different subsystems to pass it; failed leaves were not checked.
6. We infer (coordinator) that this rubric is at its ceiling under this judge and cannot separate the two tools. That is stronger than "no difference detected", and the data do not exclude that the coverage is in fact similar.
7. The input contained no `.svelte` files, so "all `.svelte`-related leaves passed on both sides" follows from the input, not from CBE handling `.svelte`. The `.svelte` labelling was broad: the 47 leaves are 49% of the rubric.
8. CBE's `docs_tree` is smaller than CodeWiki's; only its node count is larger.
9. Each CodeWiki output has a `docs/` subdirectory with 3 or 4 pages written to the wrong place in the first pass; the parser reads only top-level `.md`, so the judge never saw them.

**Public scores (background only, not comparable with this experiment).** The CodeWikiBench paper (Table 1) reports, for svelte, CodeWiki 71.96 ±3.73 (coverage 80/96) and DeepWiki 68.51 ±3.31, generated with Claude Sonnet 4 and judged by Gemini 2.5 Flash, GPT OSS 120B and Kimi K2 Instruct. CodeWiki's README reports a later rerun: DeepWiki 69.83, CodeWiki 1.0 73.21, CodeWiki 2.0 80.09, without naming the judge.

### Q-C: cost and size (E4b, E4c)

Same svelte input (440 files, 531,705 o200k tokens) and same model id `zai/glm-5.3-flash`. Ratios take the two extreme pairings: CBE's smallest ÷ CodeWiki's largest to CBE's largest ÷ CodeWiki's smallest. A checker recomputed every row and both ends of each ratio from the gateway records and the published documents.

| Measure (sum including resumes) | CBE r1 / r2 / r3 | CodeWiki 1 / 2 | CBE ÷ CodeWiki |
|---|---|---|---|
| Gateway requests | 128 / 136 / 144 | 961 / 800 | 13.3%–18.0% |
| Non-cached input tokens | 1,860,598 / 1,129,904 / 2,091,458 | 6,236,066 / 5,889,363 | 18.1%–35.5% |
| Cache-read tokens | 805,952 / 1,738,432 / 1,061,376 | 25,488,064 / 21,654,528 | 3.2%–8.0% |
| Prompt tokens (non-cached + cache read) | 2,666,550 / 2,868,336 / 3,152,834 | 31,724,130 / 27,543,891 | 8.4%–11.4% |
| Output tokens | 1,050,007 / 1,243,809 / 1,346,155 | 1,498,452 / 1,435,134 | 70.1%–93.8% |
| Reasoning tokens (part of output) | 102,592 / 133,826 / 148,010 | 718,407 / 689,624 | 14.3%–21.5% |
| Gateway `cost_usd` (gateway price table) | 0.828 / 0.844 / 1.019 | 2.449 / 2.251 | 33.8%–45.3% |
| Published document tokens (o200k) | 349,480 / 336,124 / 327,275 | 596,992 / 547,814 | 54.8%–63.8% |
| Published documents ÷ source | 65.73% / 63.22% / 61.55% | 112.28% / 103.03% | — |
| Pages | 170 / 146 / 155 | 134 / 124 | — |
| Wall clock (recorded only) | 2.32 / 2.69 / 3.18 hours | 7.75 / 7.39 hours | 30.0%–43.1% |

**First passes only (without resumes):** CBE 114 / 119 / 130 requests and 0.706 / 0.708 / 0.895 USD; CodeWiki 921 / 727 requests and 2.361 / 2.045 USD; ratios 12.4%–17.9% for requests and 29.9%–43.8% for cost. None of the five first passes was complete: CBE lost 1–3 module tasks per run, CodeWiki missed 2–3 pages per run.

A failed CBE svelte generation before a fix (CBE `9c6499e`) cost another 0.77 USD over 116 model calls (gateway price table); it is not in the ratios.

**Conditions**

1. CBE 3 runs, CodeWiki 2: the table shows observed ranges, not confidence intervals.
2. One repository, one model. With another model or repository the ratios may differ.
3. All five first passes were incomplete, so the figures include one resume per run. The resume limit was 1 for CBE and 2 for CodeWiki; every run completed within one resume.
4. Different settings. CBE used settings tuned for this model id (reasoning effort low, JSON mode, output limit 49,152, batch size 8,000/10,000); CodeWiki used its defaults (no reasoning effort sent, `--max-tokens 32768`, `--no-prompt-caching`, `--flat`, `--no-artifacts`). Reasoning tokens were 9.8% / 10.8% / 11.0% of CBE's output and 47.9% / 48.1% of CodeWiki's, so the output-token and cost ratios include a settings difference, not only a method difference.
5. Costs use the gateway price table, not a public price list.
6. Accounting uses the gateway: CodeWiki's own `metadata.json` recorded 652 / 563 fewer requests (nested sub-agent usage was not merged into the parent module).
7. Document tokens: CBE counts `docs/**/*.md`, including its `[fN]:` source-reference lines (without them: 337,315 / 324,201 / 315,477). CodeWiki counts the top-level `*.md` of its output directory, which is what the judge read; including its `docs/` subdirectory gives 612,294 / 571,845 and a ratio of 53.5%–61.1%.
8. Not in the ratios: CBE's query layer (`context.json` about 250 MB, `catalog.json` about 27 MB) and the frozen graph (181 MB; building the Joern graph makes no model calls, and the three runs reused one graph).
9. CodeWiki run 1 has 6 top-level pages under 600 bytes, still counted in its 134 pages. Fewer document tokens do not mean less or more coverage; see Q-B.
10. Wall clock: both tools ran at the same time on one heavily loaded Mac through a shared gateway; recorded only.
11. CodeWiki's README states 21.48 USD and 2 hours 46 minutes for svelte without naming the model; not comparable with this table.

### Showcase (E6)

Each repository was generated once at CBE `a87674d` and not scored. Gateway total: 139 requests, 1.324365 USD; with the polyglot rerun (13 requests, 0.028016 USD), 1.352381 USD (gateway price table).

| Repository | Language, commit, scope | Complete | Verify | Notes |
|---|---|---|---|---|
| tsdown | TypeScript, `2b1be7e`, `src/` without `*.test.ts` | yes | pass | |
| ruby_llm | Ruby, `1e315ab`, `lib/` | yes | pass | The import graph is empty (0 resolved; 46 imports without a path). Reaching definitions hit the 50,000-edge cap; 38,310 edges omitted. |
| cJSON | C, `6d9f244`, the 4 core files at the root | yes | pass | `internal_malloc` and `internal_realloc` were registered as `function::CJSON_CDECL` (the calling-convention macro, not the function name); 3 files reported `syntax_error`. |
| fmt | C++, `b4ffa39`, `include/` and `src/`, with `--header-language cpp` | no: partial after two resumes | fail | `format.h` and `core.h` have no published unit (73,397 tokens, 39.663% of the source). Both resumes exited 2 with the task still leased; the root cause was not located. After the resumes, 28 node pages lost their dependency notes, and `summary.json` under-counts 6 requests. The first-pass response for `format.h` was cut at the 49,152-token output limit; the empty macro `FMT_END_EXPORT` was registered as a function covering lines 928–1755; 19 files reported `syntax_error`. |
| gson | Java, `e2292f9`, `gson/src/main/java` | yes | pass | 35 synthetic `<clinit>` methods have no path and are recorded as nodes outside the inventory (no real file was missed). |
| polyglot | Synthetic fixture, 23 files (CBE reads 22), fixed by manifest hash `6b19d76603fb65d1` | yes | pass | The published run is the rerun under Python 3.12: with the optional grammars present, whole-file fallbacks fell from 7 to 1 (`src/q.sql`; CBE has no SQL grammar). Its source is only 1,708 tokens, so its ratios are not comparable. |

cJSON, fmt, gson and the first polyglot run ran under the replaced Python 3.13 environment; their C, C++ and Java grammar versions match those under 3.12. Verify checks structure, coverage, source references and catalogue navigation; passing it does not mean the explanations are correct.

### Generation runs

Generation runs used in this evaluation (all `zai/glm-5.3-flash` through `--host api`; gateway price table):

| Repository (round) | Source tokens | Gateway requests | `cost_usd` | Model-written text ÷ source | Published Markdown ÷ source | First pass complete | Resumes |
|---|---:|---:|---:|---:|---:|---|---:|
| flask (E1, `9c6499e`) | 125,125 | 33 | 0.250453 | 34.28% | 91.68% | yes | 0 |
| svelte r1 / r2 / r3 (E4) | 531,705 | 128 / 136 / 144 | 0.828273 / 0.843545 / 1.018638 | 28.275% / 27.361% / 26.763% | 65.728% / 63.216% / 61.552% | no / no / no | 1 / 1 / 1 |
| pytest (E3) | 752,827 | 194 | 1.660272 | 30.0% | 70.8% | no | 2 |
| curl (E5) | 1,741,311 | 341 (1 HTTP 429) | 2.116713 | 26.008% | 56.374% | no (stopped by HTTP 429) | 2 |
| tsdown (E6) | 38,670 | 21 | 0.094858 | 34.419% | 105.808% | yes | 0 |
| ruby_llm (E6) | 74,885 | 29 | 0.292913 | 54.174% | 141.219% | yes | 0 |
| cJSON (E6) | 34,364 | 13 | 0.084977 | 29.182% | 86.401% | yes | 0 |
| fmt (E6) | 185,053 | 30 | 0.544564 | 17.060% | 39.363% | no (still partial) | 2 |
| gson (E6) | 159,691 | 36 | 0.295048 | 24.926% | 65.173% | yes | 0 |
| polyglot (E6 rerun under 3.12) | 1,708 | 13 | 0.028016 | not recorded | 800.8% | yes | 0 |

Notes: Incomplete first passes came mostly from GLM-5.3-Flash producing malformed module answers (`schema_error` in 46 / 52 / 57 of 128 / 136 / 144 calls on svelte, 78 of 194 on pytest, 112 of 341 on curl). Resumes used the same settings, with no code change and no manual repair. The published-Markdown ratio moves by about 0.7–0.9 points with the run directory's location, because `[fN]:` lines hold relative paths. The query layer (`context.json`, `catalog.json`) and graphs are reported in bytes only and are not in the ratios.

## Limitations

1. **Most answers hit the step limit.** 97.9%–100% on flask and 95.8%–100% on pytest at 10 steps; 100% of valid curl answers. At 25 steps, 75.0%–83.3% on flask and 16/17 on curl. The Q-A results hold only at the limits tested. The coordinator suggests that a next round try 50 steps or a stronger answering model (which needs a judge from yet another family).
2. **The harness executes only the first tool call in a reply.** On pytest, replies with several calls were S 10.7%, C0 20.5%, C 27.6% (one reply had 113 calls); 18 `find`/`query` calls of arm C were never executed. E2 was not checked for this. On curl the shares were S 15.3%, C0 11.5%, C 12.4%.
3. **`grep` with `a|b` returns nothing.** The upstream `grep` tool uses basic regular expressions, where `|` is literal. In E1, 179 of 508 `grep` calls (about 35%) returned nothing for this reason. Unescaped `|` appeared in 37.7%–40.8% of executed `grep` calls in E2 at 10 steps, 30.9%–39.9% at 25 steps, 24.5%–30.1% in E3 and 34.3%–36.1% in E5. It affects all arms similarly but uses steps.
4. **`bash` is open only for clean `cbe` commands in arm C.** The upstream blocklist blocks `bash` by tool name for every arm; some agents then stopped trying `bash`, and in arm C also stopped trying `cbe`. The `ls`, `grep` and `find` tools do not escape their arguments, so every arm could start a second command through them; the sandbox blocks reads and writes outside the arm, and none of the 1,041 E1 commands did this. Do not describe S, C0 or W as "having no shell".
5. **One answering model and one judge family.** All answers come from `zai/glm-5.3-flash`; the five-dimension judge, the rubric judge and the coverage judge are all `codex/gpt-6.1-sol`. Documents may help stronger models differently. The five-dimension judge was checked against the source by an independent rescorer only on 10 E1 pilot answers from arms S and C0: mean absolute difference 4.1 points, correlation 0.96; the rescorer had seen the judge's scores first, which may have anchored it.
6. **Possible leakage.** SWE-QA is public; the answering model may have seen flask and pytest. curl used a closed-book filter, which removed 0 of 55.
7. **Reference answers have defects.** flask: of 10 checked, 7 right, 3 partly right, 0 wrong; pytest: 5 right, 4 partly right, 1 wrong, plus 6 with a leftover marker. The five-dimension judge scores against the reference answer, so answers that accept a wrong premise can gain. Main results keep all questions; sensitivity analyses drop the defective ones.
8. **One documentation generation per repository.** Q-A intervals exclude variation between CBE generations; Q-B judged one generation per side.
9. **Costs use the gateway price table.** Re-price with a dated public price list before comparing with other reports; request and token counts are unaffected.
10. **The shared Python environment was replaced during the runs.** At 2026-10-17 23:56:36Z another session rebuilt the shared environment from Python 3.12.13 to 3.13.11 without all optional grammar packages. Effects: in E3, `cbe` was unavailable to arm C for q33–q47; in E6, cJSON, fmt, gson and the first polyglot run ran under 3.13 (polyglot had 7 whole-file fallbacks and was rerun under 3.12); in E5a, the resumes and verify ran under 3.13. The environment was later restored to 3.12.13, and E5's arm C used a private 3.12 environment. CBE has no lock file (`uv.lock` was removed earlier), and the shared environment's package versions during E3 and E5a were not recorded, so the runtime environment cannot be rebuilt exactly from the commit.
11. **Two frozen CBE commits.** E1 and E2 used `9c6499e`, E3–E6 `a87674d`; this departs from the plan's "no changes after freezing". E2 stays at `9c6499e` on the condition that the frozen flask source is byte-identical.
12. **Wall clock is recorded only.** The machine was heavily loaded and the gateway shared.

## Reproduce

Paths below are repository-relative. Each experiment directory holds a `scripts/` folder with the driver, reduce, judge and audit scripts used. The scripts are published as they ran; paths and gateway settings in them refer to the original machine and must be adapted.

| What | Where | How to rerun |
|---|---|---|
| Harness changes | `evaluation/harness/swe-qa-agent.patch` | Check out SWE-QA-Bench at `c13deac` and apply the patch. |
| Input scope | `evaluation/inputs/` | File lists of the pruned copies (flask, pytest, curl, svelte with SHA-256 for curl) and the showcase inputs. |
| Questions and labels | `evaluation/<round>/questions/`; curl: `evaluation/e5-curl/freeze/` | flask and pytest questions are SWE-QA's; reference answers are not included (see below). curl questions, rubrics, reference answers, selection, adjudications, labels and report rules are in `freeze/` with a SHA-256 manifest. |
| curl question pipeline | `evaluation/e5-curl/question-pipeline/` | Candidates, rubric verification verdicts, independent labels, seed templates, subgraph cards and closed-book filter records. |
| Answers (full trajectories) | `evaluation/<round>/answers.tar.gz` | One JSON per question and arm, with all attempts, message history and command receipts. Run the patched harness with `zai/glm-5.3-flash`, the arm's documents and the step limit. |
| Judgments | `evaluation/<round>/judge/`; curl rubric judgments: `evaluation/e5-curl/rubric-judge.tar.gz` | Five-dimension: 3 draws per answer with `codex/gpt-6.1-sol`. Rubric: 3 votes per item, quotes checked by program. |
| Metrics and intervals | `evaluation/<round>/metrics.json`; `evaluation/e5-curl/spotcheck-and-recompute/recompute_e5qa.py` | Paired bootstrap, 10,000 resamples, 95% percentile; curl seed 20261018. |
| Judge spot check (curl) | `evaluation/e5-curl/spotcheck-and-recompute/` | Selection script and list, rescorer inputs and verdicts, agreement computation. |
| Generated documents | `evaluation/e2-flask/cbe-docs/`, `evaluation/e3-pytest/cbe-docs/`, `evaluation/e5-curl/cbe-docs/`, `evaluation/e4-svelte/cbe-docs-r1-r3.tar.gz`, `examples/<repo>/` | `cbe graph build` with Joern, then `cbe generate <pruned copy> --host api --model zai/glm-5.3-flash --graph … --run-dir …` at the CBE commit of that round; resume with `--resume` and unchanged settings when the first pass stops. |
| CodeWiki outputs | `evaluation/e2-flask/codewiki-docs.tar.gz`, `evaluation/e4-svelte/codewiki-docs-1-2.tar.gz` | CodeWiki `5b95c84` with `zai/glm-5.3-flash` for all model roles and the flags listed in Q-C. |
| Coverage verdicts | `evaluation/e4-svelte/qb/` | Leaf ids and verdicts for both sides, the aggregation script and the CBE-to-CodeWikiBench conversion script. The rubric itself is not included. |
| Costs and tokens | `evaluation/costs/` | Per-request gateway rows (time, model requested and served, token counts, `cost_usd`, status), one file per run. |

Not in this repository:

- **SWE-QA reference answers and the full harness:** get SWE-QA-Bench at `c13deac` (`Benchmark/flask.jsonl`, `Benchmark/pytest.jsonl`).
- **CodeWikiBench rubric for svelte:** download it from CodeWikiBench's Hugging Face dataset; we do not redistribute it.
- **Source copies:** rebuild each pruned copy with `git archive <commit>` and the kept directories listed in [Repositories and inputs](#repositories-and-inputs).
- **Query layers and graphs** (`catalog.json`, `context.json`, `graph.json`) for flask, pytest, svelte and curl: too large for the repository; regenerate them with the commands above. The showcase examples include the compressed catalogue (`catalog.json.gz`).

## Data and licenses

- CBE's code is under the MIT license (`LICENSE` at the repository root).
- Data we produced (curl questions, rubrics and reference answers, answers, judgments, labels, generated documents): released under the repository's MIT license (see `LICENSE`); third-party parts carry their own licenses, listed below.
- SWE-QA (Apache-2.0): the question text appears in our answer and judgment records for E1–E3 and is redistributed under Apache-2.0 with attribution to SWE-QA-Bench (`c13deac`); the question files themselves are not included. SWE-QA reference answers are not included in either case.
- Our harness patch modifies SWE-QA-Bench (Apache-2.0, `c13deac`); the patch file states which files were changed.
- The license of the CodeWikiBench rubric data is unclear to us (the CodeWikiBench repository has no LICENSE file), so we publish only leaf ids and verdicts and say how to obtain the rubric.
- RepoProbe (CC BY 4.0): the tsdown and ruby_llm commits were taken from RepoProbe; its questions were not used.
- CodeWiki outputs were generated by CodeWiki `5b95c84` (MIT; Copyright (c) 2025 FSoft-AI4Code) with `zai/glm-5.3-flash`.
- Language. This page, the per-repository pages and the four check tables (`e1-flask-pilot/r10-reference-check.csv`, `e1-flask-pilot/j10-judge-check.csv`, `e3-pytest/r12-reference-check.csv`, `e5-curl/s13-question-spotcheck.csv`) are in English. Some raw records were written in Chinese during the runs and are published unchanged, so that their hashes still match: verifier notes in the E5 question pipeline (for example the `verify_notes` field), comments and report labels in helper scripts, and a few working notes. No number on this page depends on reading them.
- Generated documents, questions, rubrics and answer trajectories quote upstream source code. Each directory that contains such quotes includes the upstream license file from the pinned commit:

| Repository | Commit | License file | License and copyright line |
|---|---|---|---|
| flask | `85c5d93` | `LICENSE.txt` | BSD 3-clause text; Copyright 2010 Pallets |
| pytest | `5989efe` | `LICENSE` | MIT; Copyright (c) 2004 Holger Krekel and others |
| curl | `2c04412d8` | `COPYING` | curl license; Copyright (c) 1996 - 2026, Daniel Stenberg and many contributors |
| svelte | `be645b4` | `LICENSE.md` | MIT text; Copyright (c) 2016-2025 Svelte Contributors |
| tsdown | `2b1be7e` | `LICENSE` | MIT; Copyright (c) 2025-present VoidZero Inc. & Contributors; Copyright (c) 2024 Kevin Deng |
| ruby_llm | `1e315ab` | `LICENSE`, `NOTICE`, `LICENSES/APACHE-2.0.txt` | MIT; Copyright (c) 2025 Carmine Paolino; NOTICE for code from aws-sdk-ruby (Apache-2.0) |
| cJSON | `6d9f244` | `LICENSE` | MIT text; Copyright (c) 2009-2017 Dave Gamble and cJSON contributors |
| fmt | `b4ffa39` | `LICENSE` (and `doc/LICENSE-exception`) | MIT text; Copyright (c) 2012 - present, Victor Zverovich and {fmt} contributors |
| gson | `e2292f9` | `LICENSE` | Apache-2.0 |

In `evaluation/`, each round directory carries the upstream file under a name with the repository added, so that several can sit side by side: `e1-flask-pilot/`, `e2-flask/` and `e2b-flask-25steps/` have `LICENSE-flask.txt`, `e3-pytest/` has `LICENSE-pytest`, `e4-svelte/` has `LICENSE-svelte.md`, and `e5-curl/` has `COPYING-curl`. In `examples/`, each directory carries the file under its original name.

The polyglot fixture was written for this evaluation; its license statement is in `examples/polyglot/`.
