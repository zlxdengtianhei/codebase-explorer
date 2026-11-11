# Run notes

Where this run's facts come from and what was and was not checked.

## Generation basis

- CBE version: `2.2.0.dev0`
- Models: none recorded
- Source: 24 files · SHA-256 `818601e2a710c47c9bd1fd7bf8d62ee306dfce524d39a862018d36a7a47f2387`
- Graph: SHA-256 `c11c3532ee88640e200d7608f29e9030fef5543706d909ee01d4d516bae3c4ae` · built by `joern` 4.0.654, `grimp` 3.17 · edges call=1360, cfg=22975, dataflow=44873, import=307 · replaced no

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
