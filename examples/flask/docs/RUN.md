# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 293 · semantic nodes: 31 · dispositioned inventory ids: 483
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
python import: resolved 95/307 (31%), external 212/307 (69%) · python call: resolved 231/1360 (17%), ambiguous 51/1360 (4%), unresolved 437/1360 (32%), external 641/1360 (47%).
python structural edges: cfg=22975, dataflow=44873.
Incomplete capabilities: python/call partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.
