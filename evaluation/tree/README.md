# Module-tree scales (A, B1, B2, C)

Measures how well a division of a repo's code units into modules ("a tree") works. Not part of the installed package.
Design: the owner's `DESIGN_tree.md`, section 5. Inputs: the five `catalog.json.gz` files and the cloned git histories.

The scales' T0 ("the published tree") means the old `catalog.json.gz` files in `examples/` and `evaluation/e2-flask/` as of commit `67a99ee`. The examples were regenerated later, so to reproduce T0 take those files from that commit (`git show 67a99ee:examples/<name>/catalog.json.gz`).

```sh
export PYTHONPATH=<worktree>/src:<worktree>/evaluation/tree
PY=python   # an environment with codebase-explorer installed
export CBE_EVAL_CLONES=<dir with full-history clones: ruby_llm, gson, tsdown, fmt, flask>
export CBE_EVAL_LAB=<scratch dir for raw answers and caches>
$PY run.py all                        # commits (if missing) + T0 and T1 rows for the five repos + results/table_T0_T1.md
$PY run.py row ruby_llm T0            # one JSON line: A, B1, B2 at leaf/up1/top, C at up1/top
$PY run.py row gson path/to/T3-gson.json --out rows.jsonl     # a tree file from the skeleton work
$PY run.py row gson T1 --match path/to/T3-gson.json           # directories cut at the depth whose module count matches
$PY run.py table rows.jsonl [...]     # Markdown tables
$PY controls.py [--model-free|--repeat|--table]               # checks on the scales themselves
$PY commits.py                        # re-draw the 30 commits per repo (seeded; files in commits/)
```

Tree file: `{"name": "T2-gson", "nodes": [{"id", "parent", "title", "capability", "summary", "unit_ids"}]}`; the root has `parent: null`.

Files: `common.py` (loading, cuts, soft file membership), `measures.py` (A, B1, B2), `commits.py` (commit choice),
`locate.py` (C: page, prompt, gateway calls, scoring), `run.py` (commands, tables), `controls.py` (checks).
Raw model answers and caches go to `$CBE_EVAL_LAB` (not in git) and are reused on rerun. The model endpoint is an OpenAI-compatible gateway; see `locate.py`.

In the repository: the scripts and three tables in `results/` (`table_all.md`, `compare.md`, `controls.md`). Not in the repository: the per-repo commit lists (`commits/`, re-drawn deterministically by `run.py commits` from the pinned snapshots with the seed in `commits.py`), the raw rows (`results/*.jsonl`) and the raw model answers. Read `controls.md` before trusting any number in the tables: it shows how each scale can mislead.
