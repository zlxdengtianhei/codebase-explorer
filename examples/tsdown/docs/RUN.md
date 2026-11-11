# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 113 · semantic nodes: 15 · dispositioned inventory ids: 317
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
typescript import: resolved 142/532 (27%), unresolved 158/532 (30%), external 232/532 (44%) · typescript call: resolved 224/1013 (22%), ambiguous 12/1013 (1%), unresolved 350/1013 (35%), external 427/1013 (42%).
typescript structural edges: cfg=21516, dataflow=39253.
Incomplete capabilities: typescript/call partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.
