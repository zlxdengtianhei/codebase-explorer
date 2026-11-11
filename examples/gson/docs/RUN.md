# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 460 · semantic nodes: 49 · dispositioned inventory ids: 1894
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
java import: resolved 304/685 (44%), external 381/685 (56%) · java call: resolved 1111/3118 (36%), ambiguous 515/3118 (17%), unresolved 43/3118 (1%), external 1449/3118 (46%).
java structural edges: cfg=27509, dataflow=50000.
unknown call: resolved 92/109 (84%), unresolved 10/109 (9%), external 7/109 (6%).
Incomplete capabilities: java/call partial; java/dataflow partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.

## Generation notes

- Accepted with repairs or gaps (see each task's flags in host/state.json): module_5.

## Checks

- Cohesion: 19 of 32 modules with edges have at least as many resolved edges inside as outside.
- Granularity: 26 of 32 modules hold 5 to 30 units.
- Program diagnostics only; they do not prove semantic correctness. All readings: `summary.json`.
