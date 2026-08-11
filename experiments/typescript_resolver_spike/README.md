# TypeScript resolver decision spike

This directory is an isolated, non-production experiment. It reconstructs the
frozen TypeScript oracle fixture from its content-addressed contract, probes a
project-aware TypeScript `Program`, probes SCIP generation, and records the
installed GraphSitter compatibility boundary. It does not alter production
dependencies, adapters, fixtures, locks, or contracts.

Run `bash run.sh`, then `bash run_nest.sh`. Generated dependencies and
repository checkouts stay under ignored `.work/`; result JSON stays under
`results/`. Recompute the verdict with:

```bash
../../.venv/bin/python validate_results.py . ../../tests/oracles/contracts/typescript/expected_ir.json
```

The timing files and online install/audit observations are environment- and
date-specific; the oracle, package lock, repository lock, and validator provide
the deterministic comparison anchors.
