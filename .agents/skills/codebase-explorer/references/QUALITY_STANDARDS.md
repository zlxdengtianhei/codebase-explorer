# Quality and Evidence Standards

## Separate Pipeline Evidence from Product Evidence

The real E2E pytest may use generated fixture explanations. It proves:

- MCP transport and tool discovery work;
- analysis, claim, submit, render, and review calls connect;
- a rejected submission preserves the prior ledger/docs snapshot;
- a saved packet can be submitted after an MCP client reconnect.

It cannot prove that explanations understand the repository. Do not cite that
test as semantic-quality acceptance.

## Coverage Gate

The semantic denominator is the inventory returned by
`get_semantic_progress`, not a producer-maintained list.

Required terminal state:

```text
coverage_percent == 100.0
uncovered_symbols == []
stale_symbols == []
```

A residual keeps its symbol uncovered and must be reported as an explicit gap.

## Explanation Review Criteria

For every sampled symbol, the independent reviewer evaluates:

1. function: what the symbol does;
2. role: why it exists in this repository;
3. input/output and side effects: data, mutation, I/O, failures;
4. dependencies: calls, callers, cited callees, and cycles that affect meaning.

Source-grounded explanations name concrete behavior. Restating a name, signature,
or import list is insufficient.

## Progressive-Disclosure Projection

- INDEX gives the project/module map and Mermaid dependency graph.
- Module DETAIL documents group files by functional ownership.
- File sections summarize their symbol inventory and uncovered residue.
- Symbol blocks carry stable source IDs and semantic explanations.

The generated docs are projections. Repair them from the ledger with
`render_semantic_docs`; do not patch them into a second truth.

## Completion Evidence

Completion evidence consists of:

- fresh 100% progress recomputed after production;
- successful render paths;
- an accepted, fingerprint-bound independent review;
- readable INDEX/DETAIL files with dependency graph and symbol anchors.
