from __future__ import annotations

import importlib
import inspect
import json
import resource
import sys
import time
from importlib import metadata
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    result: dict[str, object] = {
        "candidate": "installed_graph_sitter_adaptation",
        "root": str(root),
        "versions": {},
        "facts": {
            "ts.call.worker.run": {"observed": False},
            "ts.implements.worker": {"observed": False},
            "ts.type.runner.run": {"observed": False},
        },
    }
    for package in ("graph-sitter", "mini-racer", "tree-sitter", "tree-sitter-typescript"):
        try:
            result["versions"][package] = metadata.version(package)  # type: ignore[index]
        except metadata.PackageNotFoundError:
            result["versions"][package] = "not-installed"  # type: ignore[index]

    started = time.perf_counter()
    try:
        importlib.import_module("graph_sitter.typescript.external.ts_analyzer_engine")
        result["unmodified_import"] = "ok"
    except Exception as exc:
        result["unmodified_import"] = {
            "status": "incompatible",
            "exception": type(exc).__name__,
            "message": str(exc),
        }

    try:
        import py_mini_racer
        import py_mini_racer._types as legacy_types

        legacy_types.JSEvalException = py_mini_racer.JSEvalException
        engine_module = importlib.import_module("graph_sitter.typescript.external.ts_analyzer_engine")
        graph_sitter = importlib.import_module("graph_sitter")
        analyzer_path = Path(engine_module.__file__).parent / "typescript_analyzer"
        result["shim_import"] = "ok"
        result["codebase_signature"] = str(inspect.signature(graph_sitter.Codebase))
        result["analyzer_dist_present"] = (analyzer_path / "dist" / "index.js").is_file()
        result["analyzer_source_present"] = (analyzer_path / "src" / "run_full.ts").is_file()
        result["public_typescript_engine_methods"] = sorted(
            name for name, value in inspect.getmembers(engine_module.NodeTypescriptEngine, inspect.isfunction)
            if not name.startswith("_")
        )
        result["semantic_support_assessment"] = (
            "public installed engine exposes function return-type lookup only; "
            "no call-target or implements-resolution result surface"
        )
    except Exception as exc:
        result["shim_import"] = {
            "status": "failed",
            "exception": type(exc).__name__,
            "message": str(exc),
        }

    result["elapsed_ms"] = (time.perf_counter() - started) * 1000
    result["peak_rss_platform_units"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

