# Run notes

Where this run's facts come from and what was and was not checked.

## Generation basis

- CBE version: `2.2.0.dev0`
- Models: `group/glm-5.3-flash`
- Source: 4 files · SHA-256 `b0dfc1363d65cbbf276a1e83d0ba19f4882693307fb416df493616138f747024`
- Graph: SHA-256 `1e048baa6fb44286ee804b9a9c9672cb2828abd2222109a3b0bf57b694056482` · built by `joern` 4.0.654 · edges call=431, cfg=10630, dataflow=21773, import=20 · replaced no

## Reading stats

- units: 107 · semantic nodes: 15 · dispositioned inventory ids: 290
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
c import: resolved 3/20 (15%), external 17/20 (85%) · c call: resolved 350/431 (81%), external 81/431 (19%).
c structural edges: cfg=10630, dataflow=21773.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.
