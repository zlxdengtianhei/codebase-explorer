# Run notes

Where this run's facts come from and what was and was not checked.

## Generation basis

- CBE version: `2.2.0.dev0`
- Models: `group/deepseek`, `group/glm-5.3-flash`
- Source: 115 files · SHA-256 `ed4bf8f0ee4b242de5181081f554dbb61829401545baa8fccfa718ca2cd82904`
- Graph: SHA-256 `4fff42c47772955e94fac0ab64b1b89a18894f4ee896883cf7c44321fa3693b1` · built by `joern` 4.0.654 · edges call=2776, cfg=53285, dataflow=50000, import=45 · replaced no

## Reading stats

- units: 295 · semantic nodes: 27 · dispositioned inventory ids: 2037
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
ruby import: resolved 9/45 (20%), external 36/45 (80%) · ruby call: resolved 856/2776 (31%), ambiguous 316/2776 (11%), unresolved 1173/2776 (42%), external 431/2776 (16%).
ruby structural edges: cfg=53285, dataflow=50000.
Incomplete capabilities: ruby/call partial; ruby/dataflow partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0.

## Generation notes

- Review: the sampled batch (review_3) reported 1 issue(s), so every batch was reviewed: 12 of 12 reviewed, 36 issue(s) in total.
