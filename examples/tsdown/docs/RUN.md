# Run notes

Where this run's facts come from and what was and was not checked.

## Generation basis

- CBE version: `2.2.0.dev0`
- Models: `group/glm-5.3-flash`
- Source: 43 files · SHA-256 `6211424a980e58ce57402128a3755fa54e4cc701bec5faece8c851386f3b90a6`
- Graph: SHA-256 `6690f936b2f6bf4a588286dc3c0d0ee0fc3346089a27245b02730b71f14e075c` · built by `joern` 4.0.654, `dependency-cruiser` 16.10.4 · edges call=1013, cfg=21516, dataflow=39253, import=532 · replaced no

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
