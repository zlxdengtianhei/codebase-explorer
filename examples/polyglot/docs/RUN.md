# Run notes

Where this run's facts come from and what was and was not checked.

## Reading stats

- units: 54 · semantic nodes: 14 · dispositioned inventory ids: 159
- source ranges are program-derived from the inventory, never model-written

## Graph coverage

Source: static analysis graph. Resolved relations are graph-confirmed; this does not guarantee semantic correctness. External targets are outside the repository; ambiguous targets have multiple candidates. Unresolved or unsupported relations, and languages or relation kinds without coverage, rely on model inference and may be inaccurate.
Import and call status ratios use the edge count of each kind. CFG and dataflow are structural edges; only their counts are shown, without status ratios.
c import: external 1/1 (100%) · c call: resolved 1/2 (50%), external 1/2 (50%).
c structural edges: cfg=19, dataflow=42.
c_sharp import: external 1/1 (100%) · c_sharp call: resolved 1/3 (33%), unresolved 1/3 (33%), external 1/3 (33%).
c_sharp structural edges: cfg=12, dataflow=38.
cpp import: external 1/1 (100%) · cpp call: no edges.
cpp structural edges: cfg=13, dataflow=38.
go import: external 1/1 (100%) · go call: resolved 1/2 (50%), external 1/2 (50%).
go structural edges: cfg=15, dataflow=33.
java import: external 1/1 (100%) · java call: no edges.
java structural edges: cfg=9, dataflow=38.
javascript import: unresolved 2/2 (100%) · javascript call: resolved 1/3 (33%), unresolved 1/3 (33%), external 1/3 (33%).
javascript structural edges: cfg=103, dataflow=208.
kotlin import: no edges · kotlin call: external 1/1 (100%).
kotlin structural edges: cfg=21, dataflow=51.
php import: no edges · php call: no edges.
php structural edges: cfg=0, dataflow=0.
python import: external 3/3 (100%) · python call: resolved 6/11 (55%), external 5/11 (45%).
python structural edges: cfg=288, dataflow=571.
ruby import: external 1/1 (100%) · ruby call: resolved 1/3 (33%), unresolved 1/3 (33%), external 1/3 (33%).
ruby structural edges: cfg=69, dataflow=143.
rust import: no edges · rust call: no edges.
rust structural edges: cfg=0, dataflow=0.
swift import: external 1/1 (100%) · swift call: resolved 1/1 (100%).
swift structural edges: cfg=18, dataflow=56.
typescript import: no edges · typescript call: unresolved 1/4 (25%), external 3/4 (75%).
typescript structural edges: cfg=95, dataflow=188.
Incomplete capabilities: c_sharp/call partial; javascript/call partial; kotlin/call partial; php/call failed; php/cfg failed; php/dataflow failed; php/import failed; ruby/call partial; rust/call failed; rust/cfg failed; rust/dataflow failed; rust/import failed; typescript/call partial.
Program checks: dangling edges 0; nodes outside manifest 0; nodes with missing files 0; frontend failed; see graph diagnostics.

## Generation notes

- Known-empty files (no source text, no inventory id, no unit, no model call): src/empty.py.

## Checks

- Cohesion: 4 of 4 modules with edges have at least as many resolved edges inside as outside.
- Granularity: 5 of 11 modules hold 5 to 30 units.
- Introduction length: the longest module introduction is 0.91 times the explanations under it; 0 module(s) above 1.
- Program diagnostics only; they do not prove semantic correctness. All readings: `summary.json`.
