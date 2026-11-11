# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 352 · semantic nodes: 35 · dispositioned inventory ids: 2037
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
ruby import: resolved 9/45 (20%), external 36/45 (80%) · ruby call: resolved 856/2776 (31%), ambiguous 316/2776 (11%), unresolved 1173/2776 (42%), external 431/2776 (16%).
ruby structural edges: cfg=53285, dataflow=50000.
Incomplete capabilities: ruby/call partial; ruby/dataflow partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.
