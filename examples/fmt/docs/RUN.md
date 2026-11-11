# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 474 · semantic nodes: 53 · dispositioned inventory ids: 3334
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
cpp import: resolved 38/183 (21%), external 145/183 (79%) · cpp call: resolved 464/3074 (15%), unresolved 2588/3074 (84%), external 22/3074 (1%).
cpp structural edges: cfg=32409, dataflow=50000.
Incomplete capabilities: cpp/call partial; cpp/dataflow partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.

## Generation notes

- 1 module title(s) are program-made (frequent words and main directory) because no usable model name was accepted for them.
- Accepted with repairs or gaps (see each task's flags in host/state.json): module_1, tree_top.

## Checks

- Cohesion: 11 of 29 modules with edges have at least as many resolved edges inside as outside.
- Granularity: 32 of 41 modules hold 5 to 30 units.
- Program diagnostics only; they do not prove semantic correctness. All readings: `summary.json`.
