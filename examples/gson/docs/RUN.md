# Run notes

Where this run's facts come from and what was and was not checked.

## Generation basis

- CBE version: `2.2.0.dev0`
- Models: `group/glm-5.3-flash`
- Source: 86 files · SHA-256 `80f18b6036a56de1c009471badcabb6e234a7228b3ebf954fa5a5d79e96552f9`
- Graph: SHA-256 `689e9d86a1b5464f2c3fc2f6239fa8bdd3ba092539a00c61edb8a52308854250` · built by `joern` 4.0.654 · edges call=3227, cfg=27509, dataflow=50000, import=685 · replaced no

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
