# Polyglot Sample Corpus

**Capability.** Owns the whole documented sample codebase: a multi-language collection of small programs, class libraries, functional-closure demos, fixtures, and tests. It groups language-specific implementations under responsibility-level capabilities rather than directory structure, so readers find behavior by what code does, not where it lives.

Start here to navigate the corpus. Each child capability groups implementations across languages that share a responsibility. Language identity is retained at the leaf/unit level.

**Children.**

- [Entry-Point Demos](entrypoint-demos.md) `entrypoint-demos` · 5 unit(s)
- [Greeters and Shape Contracts](greeting-shape-contracts.md) `greeting-shape-contracts` · 13 unit(s)
- [Closures and Functional Patterns](closure-functional-patterns.md) `closure-functional-patterns` · 12 unit(s)
- [Shared Helper Utilities](shared-helpers.md) `shared-helpers` · 9 unit(s)
- [Value Types with Sum Methods](value-type-methods.md) `value-type-methods` · 2 unit(s)
- [Job Queue and Job Mapping](job-queue.md) `job-queue` · 4 unit(s)
- [Python Worker and Helper](python-worker.md) `python-worker` · 3 unit(s)
- [Encoding and Parser Fixtures](fixtures-and-edgecases.md) `fixtures-and-edgecases` · 6 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
