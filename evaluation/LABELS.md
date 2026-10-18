# Question and document-presence labels

These labels describe question wording, the understanding needed to answer, and catalog membership. They are subgroup labels, not quality scores. In particular, `in_docs` does not establish that a published document explains the cited behavior.

## Question types and understanding layers

The SWE-QA question types describe the form of the question. The four layers describe the depth of the requested understanding; a question beginning with “Where” can require tracing behavior or explaining design.

| Type | What it asks |
|---|---|
| What | Identify a concept, responsibility, property, result or behavior. |
| Why | Explain a reason, constraint, choice or consequence. |
| Where | Locate an implementation, definition or responsibility, sometimes with its wider context. |
| How | Explain an algorithm, mechanism, sequence of operations or interaction. |

| Layer | Name | What it requires |
|---|---|---|
| 1 | locate | Find a definition, implementation or responsible code location. |
| 2 | unit behavior | Explain a local method, parameter, state change or algorithm. |
| 3 | cross-module flow | Trace calls, data, context, registration or state across units. |
| 4 | impact and design | Explain an architectural choice, tradeoff, coupling, or the effects of a change. |

Layer precedence is design/impact > cross-unit flow > unit behavior > definition location. The highest applicable demand takes precedence. “Cross-module” includes interactions between units in the same file. Borderline decisions remain subjective; per-question reasons are part of the published labels.

The evaluation plan called for annotation by an agent that did not answer the questions, using the question text. Flask's labels record manual semantic annotation from questions only; their `method` does not identify an individual annotator, so it cannot by itself establish role independence. The same flask labels are carried in E1, E2 and E2b; E2b's label file still contains the full question set, not just its answered subset. Pytest was annotated by the separate reference-checking agent `cbe-r12`, from question texts only, before its reference-answer source check. E5's independent labeler `cbe-l13` read only question texts and build assumptions, without candidate answers or source.

### Recorded methods (verbatim)

The following are the complete `method` fields, not revised descriptions of how annotation should have been done.

[e1-flask-pilot/questions/labels.json](e1-flask-pilot/questions/labels.json):

> Manual semantic annotation from original questions only. Layer precedence: design/impact > cross-unit flow > unit behavior > definition location; Where does not automatically mean layer 1. Zero-based qid is original JSONL row.

[e2-flask/questions/labels.json](e2-flask/questions/labels.json):

> Manual semantic annotation from original questions only. Layer precedence: design/impact > cross-unit flow > unit behavior > definition location; Where does not automatically mean layer 1. Zero-based qid is original JSONL row.

[e2b-flask-25steps/questions/labels.json](e2b-flask-25steps/questions/labels.json):

> Manual semantic annotation from original questions only. Layer precedence: design/impact > cross-unit flow > unit behavior > definition location; Where does not automatically mean layer 1. Zero-based qid is original JSONL row.

[e3-pytest/questions/labels.json](e3-pytest/questions/labels.json):

> Manual semantic annotation from the 48 question texts only (answers and source not read when labeling). swe_type follows the opening wording of the question (What/How/Why/Where); for qids 3, 12, 23, 25 this differs from the file-position block (0-11/12-23/24-35/36-47). Layer precedence: design/impact (4) > cross-unit flow (3) > unit behavior (2) > definition location (1); Where does not automatically mean layer 1. Zero-based qid is the original JSONL row.

[e5-curl/question-pipeline/label/labels.json](e5-curl/question-pipeline/label/labels.json):

> Manual semantic annotation by cbe-l13 from the 56 question texts and build_assumptions in questions_only.jsonl only (candidates, answers and source not read when labeling). swe_type follows the opening wording of each question (What, How, Why, Where). Layer precedence: design/impact (4) > cross-unit flow (3) > unit behavior (2) > definition location (1); Where does not automatically mean layer 1, and a question that asks for a unit's behavior plus its callers or users, or a value or state traced across functions, is labeled 3. A Why question is labeled 4 when its reason concerns interaction with, or impact on, other components, and 2 when the reason is local to one function. Borderline calls are named in the reason.

## E5 independent annotation and selection

The independent label file covers 56 candidate questions. After rubric checking, one candidate was dropped; 40 were selected from the remaining 55 using these labels. The frozen set has 10 What, 10 Why, 10 Where and 10 How questions; layers 1–4 contain 3/8/18/11 questions. These counts are for the frozen set, not the whole independent label file. See [selection.json](e5-curl/freeze/selection.json) and [questions_frozen.jsonl](e5-curl/freeze/questions_frozen.jsonl). The layer allocation departed from the proposed 4/8/14/14 quota; it is disclosed in the evaluation README.

Question writers read Joern subgraph cards; those cards share an origin with CBE's dependency lines and query output. Independent labeling does not remove that shared origin. The function-pointer-dispatch subgroup is reported separately for this reason.

## E5 catalog-presence labels

The main evaluation session produced [freeze/doc_presence.json](e5-curl/freeze/doc_presence.json) after CBE generation and before E5 answering. It used the core rubric items' `source` fields and the frozen catalog, rather than searching the document prose. Its recorded rule is reproducible with [doc_presence.py](e5-curl/freeze/doc_presence.py).

For each core rubric item, split the source on semicolons. An entry `path: name1, name2` yields file/name pairs; a file-only entry is recorded but does not affect the label. Normalize names by dropping leading `struct`, `union` or `enum`, trailing `()`, and a trailing `comment`. Match each name and file against catalog symbols. If any matching symbol owns a unit, the pair is `unit`; otherwise it is `grouped` if it belongs to a group unit, `index_only` if only indexed, or `missing` if there is no match.

- `in_docs`: every named pair is either `unit` or `grouped`. This is the frozen subgroup label: “a same-named unit is present in the catalog,” including group members. Group membership does not prove that prose explains each member.
- `own_unit`: every named pair is `unit`, requiring an independent unit for each pair. The frozen file calls this informational; the strict subgroup supplement was subsequently recomputed by the main session and appears in [SUBGROUPS.md](SUBGROUPS.md).

The aggregate fields below are copied from `doc_presence.json`.

| Recorded field | Count |
|---|---:|
| `counts`: present / absent / unjudgeable questions | 30 / 10 / 0 |
| `own_unit_count`: questions whose pairs all have own units | 15 |
| `pair_status.unit` | 125 |
| `pair_status.grouped` | 35 |
| `pair_status.missing` | 13 |
| `pair_status.index_only` | 2 |

The `pair_status` fields count entries in the per-rubric pair lists: a (file, name) pair cited by two rubric items counts twice, so these are not counts of distinct symbols. Of the 175 entries, 160 are present (`unit` or `grouped`), and 35 of those are `grouped`; the 15 entries labelled "not present" are the 13 `missing` and 2 `index_only` entries. The evaluation README uses the same reading.

The publication conditions in the evaluation README further limit interpretation: 10 of the 15 absent file/name entries have names that appear in some published page's text. The absent entries include macros, variables, a typedef, a bit-field, a header declaration, enum constants, and two indexed struct definitions without units. The 10 absent questions are all What or Why and cite 5.9 names on average, compared with 3.9 for the 30 present questions. Presence is therefore mixed with question type and citation count. Subgroup differences cannot be read as the effect of whether prose explains a function.

The question-type and layer definitions follow the evaluation plan, section 3. All reported subgroup intervals, including the additional `own_unit` reading, are in [SUBGROUPS.md](SUBGROUPS.md); the complete conditions remain in [the evaluation README](README.md#q-a-curl-e5).
