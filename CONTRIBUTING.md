# Contributing to Codebase Explorer

Thanks for your interest in improving Codebase Explorer. This is a small project; keep contributions simple.

## How to contribute
- Bug reports and feature ideas: open an issue with a concrete repro or use case.
- Code changes: open a PR against `main`. Keep changes minimal and focused; match existing style.
- Semantic explanations are Python-only today (TS/JS is syntax-only). Don't claim multi-language support.

## Running tests
```
uv run --directory /path/to/codebase-explorer pytest
```

## Honest reporting
This project values honest evidence over polished claims. If a change adds a gate, check, or metric, first answer "can a simpler mechanism cover the same need?" in the PR description (project principle: lean deterministic layer, don't scatter agent attention over forced gates).

## License
By contributing you agree your contributions are licensed under the project's MIT License.
