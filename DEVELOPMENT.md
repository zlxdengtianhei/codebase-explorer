# Development

The repository lock file is the developer environment source of truth. From this directory, install the locked runtime and development dependencies, then run the complete active test suite:

```sh
uv sync --frozen --group dev
uv run pytest -q
```

`--frozen` is intentional: it makes a stale `uv.lock` fail instead of silently changing the lock during setup. The `dev` group includes `pytest`, `pytest-asyncio`, and `pytest-cov`; async tests therefore collect without adding packages on the command line.

Virtual environments are path-bound caches and must not be copied between checkouts. If this checkout already contains a copied or otherwise suspect `.venv`, preserve it for rollback and rebuild before using the canonical commands:

```sh
CBE_OLD_VENV="$(mktemp -d)/previous-venv"
[ ! -d .venv ] || mv .venv "$CBE_OLD_VENV"
uv sync --frozen --group dev
uv run pytest -q
```

## Clean-environment verification

Use a temporary virtual environment to verify the lock without deleting or reusing the repository `.venv`:

```sh
CBE_DEV_VENV="$(mktemp -d)/.venv"
UV_PROJECT_ENVIRONMENT="$CBE_DEV_VENV" uv sync --frozen --group dev
UV_PROJECT_ENVIRONMENT="$CBE_DEV_VENV" uv run pytest -q
```

When dependency declarations intentionally change, regenerate the lock only with `uv lock`, review the resulting `uv.lock` diff, and rerun the frozen clean-environment commands above. Do not hand-edit `uv.lock`.

## Parser backend status

The pinned environment installs `graph-sitter`, whose import name is `graph_sitter`. The current parser implementation instead attempts `from codegen import Codebase`. In a fresh locked environment, `import graph_sitter` succeeds while `import codegen` raises `ModuleNotFoundError`. The GraphSitter path is therefore unreachable through the current parser contract, and parsing uses the Python AST fallback where supported.

This is a known backend negative, not a setup failure and not evidence of TypeScript or JavaScript parser support. Packet P2 owns the explicit backend registry, health reporting, and truthful unavailable states; P0 does not add an unrelated runtime package to mask the mismatch.
