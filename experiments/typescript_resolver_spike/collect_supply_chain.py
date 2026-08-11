from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path


def tree_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def main() -> int:
    experiment = Path(sys.argv[1]).resolve()
    lock = json.loads((experiment / "package-lock.json").read_text(encoding="utf-8"))
    npm_packages = []
    for relative, record in lock["packages"].items():
        if not relative.startswith("node_modules/"):
            continue
        package_root = experiment / relative
        npm_packages.append(
            {
                "package": relative.removeprefix("node_modules/"),
                "version": record["version"],
                "license": record.get("license"),
                "integrity": record.get("integrity"),
                "installed_bytes": tree_bytes(package_root),
            }
        )
    graph = importlib.metadata.distribution("graph-sitter")
    graph_root = Path(graph.locate_file("graph_sitter"))
    print(
        json.dumps(
            {
                "npm": {
                    "lockfile_version": lock["lockfileVersion"],
                    "external_package_count": len(npm_packages),
                    "packages": npm_packages,
                },
                "installed_graph_sitter": {
                    "version": graph.version,
                    "license": graph.metadata.get("License"),
                    "declared_dependency_count": len(graph.requires or []),
                    "package_bytes": tree_bytes(graph_root),
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
