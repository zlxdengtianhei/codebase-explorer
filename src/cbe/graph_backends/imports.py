"""File/module import backends: dependency-cruiser (JS/TS/TSX) and Grimp (Python).

Joern exposes import *declarations*; these two tools resolve them to concrete
files/modules and are the source of truth for the ``import`` graph kind where
they apply.  Both are optional: a missing binary becomes a diagnostic, not a
crash, and a run that succeeds with no dependencies reports ``empty`` rather
than an unexplained absence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

from ._paths import canonical_repo_path
from .identity import repository_files, file_id, external_id

DEPCRUISE_LANGUAGES = frozenset({"javascript", "typescript", "tsx"})
_JS_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".mts", ".cts", ".tsx")


def find_depcruise(depcruise_bin=None):
    if depcruise_bin is not None:
        candidate = os.path.expanduser(str(depcruise_bin))
        if os.path.isfile(candidate):
            return candidate
    env = os.environ.get("CBE_DEPCRUISE_BIN")
    if env and os.path.isfile(env):
        return env
    which = shutil.which("depcruise")
    return which or None


def build_with_depcruise(repo, run_dir, depcruise_bin, timeout: int, languages: list[str]) -> dict:
    os.makedirs(str(run_dir), exist_ok=True)
    try:
        completed = subprocess.run(
            [str(depcruise_bin), "--no-config", "--output-type", "json", "."],
            cwd=str(repo), check=False, capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return _result([], [], [{"path": None, "code": "backend_timeout",
                                 "message": f"dependency-cruiser timed out after {timeout}s"}],
                       languages, status="failed")
    except OSError as exc:
        return _result([], [], [{"path": None, "code": "backend_error",
                                 "message": f"cannot run dependency-cruiser: {exc}"}],
                       languages, status="failed")
    if completed.returncode != 0:
        return _result([], [], [{"path": None, "code": "backend_error",
                                 "message": f"dependency-cruiser failed (exit {completed.returncode})"}],
                       languages, status="failed")
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        return _result([], [], [{"path": None, "code": "backend_error",
                                 "message": f"dependency-cruiser output unreadable: {exc}"}],
                       languages, status="failed")

    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    counter = 0
    files = repository_files(repo)

    def add_file(rel: str) -> str | None:
        node_id = file_id(rel, files)
        if node_id is None:
            return None
        if node_id not in seen:
            seen.add(node_id)
            nodes.append({"id": node_id, "kind": "file", "path": rel,
                          "start_line": None, "end_line": None, "name": rel,
                          "backend": "dependency-cruiser"})
        return node_id

    for module in payload.get("modules", []):
        source = canonical_repo_path(module.get("source", ""))
        if not source or not source.endswith(_JS_EXTENSIONS):
            continue
        source_id = add_file(source)
        if source_id is None:
            continue
        for dep in module.get("dependencies", []):
            resolved = dep.get("resolved")
            expression = dep.get("module", "")
            counter += 1
            if dep.get("couldNotResolve"):
                target_id = None
                status = "unresolved"
            elif resolved and not dep.get("coreModule"):
                target_rel = canonical_repo_path(resolved)
                target_id = add_file(target_rel) if target_rel else None
                status = "resolved" if target_id else "unresolved"
            elif dep.get("coreModule"):
                target_rel = canonical_repo_path(str(expression))
                target_id = external_id(target_rel or expression)
                if target_id not in seen:
                    seen.add(target_id)
                    nodes.append({"id": target_id, "kind": "external", "path": None,
                                  "start_line": None, "end_line": None, "name": expression,
                                  "external": True, "backend": "dependency-cruiser"})
                status = "external"
            else:
                target_id = None
                status = "unresolved"
            edges.append({
                "id": f"dc/import/{counter}",
                "source": source_id,
                "target": target_id,
                "kind": "import",
                "status": status,
                "path": source,
                "expression": expression,
                "analyzer_id": None,
                "backend": "dependency-cruiser",
            })
    return _result(nodes, edges, [], languages, status="resolved" if edges else "empty")


def build_with_grimp(repo, languages: list[str]) -> dict:
    if "python" not in languages:
        return {"nodes": [], "edges": [], "diagnostics": [], "capabilities": []}
    try:
        import grimp  # noqa: PLC0415
    except ImportError:
        return {"nodes": [], "edges": [], "diagnostics": [
            {"path": None, "code": "backend_unavailable",
             "message": "grimp is not installed; Python import graph skipped (install the 'graphs' extra)"}],
            "capabilities": []}
    from ._imports import ImportResolver

    resolver = ImportResolver(repo)
    packages = _top_level_python_packages(repo)
    if not packages:
        return _result([], [], [{"path": None, "code": "no_python_packages",
                                 "message": "no importable top-level Python package was found"}],
                       None, status="empty", language="python")
    diagnostics: list[dict] = []
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    built = 0
    hard_failures = 0
    not_packages = 0
    inserted = str(repo)
    sys.path.insert(0, inserted)
    try:
        for package in packages:
            try:
                graph = grimp.build_graph(package)
            except Exception as exc:  # grimp has several failure modes for arbitrary trees
                kind = type(exc).__name__
                if kind.startswith("NotATopLevel"):
                    not_packages += 1
                    diagnostics.append({"path": None, "code": "not_a_package",
                                        "message": f"grimp treats {package!r} as a top-level module, not a package"})
                else:
                    hard_failures += 1
                    diagnostics.append({"path": None, "code": "backend_error",
                                        "message": f"grimp could not build {package}: {kind}"})
                continue
            built += 1
            for module in graph.modules:
                source_path = resolver.python_file(module)
                if source_path is None:
                    diagnostics.append({"path": None, "code": "module_file_missing",
                                        "message": f"grimp module {module!r} has no repository file"})
                    continue
                module_id = _add_module(nodes, seen, module, source_path, resolver.files)
                for imported in graph.find_modules_directly_imported_by(module):
                    target_path = resolver.python_file(imported)
                    status = "resolved" if target_path else ("unresolved" if resolver.python_local(imported) else "external")
                    target_id = _add_module(nodes, seen, imported, target_path, resolver.files) if status != "unresolved" else None
                    edges.append({
                        "id": f"grimp/import/{module}->{imported}",
                        "source": module_id,
                        "target": target_id,
                        "kind": "import",
                        "status": status,
                        "path": source_path,
                        "expression": imported,
                        "analyzer_id": None,
                        "backend": "grimp",
                    })
    finally:
        try:
            sys.path.remove(inserted)
        except ValueError:
            pass
    if edges:
        status = "resolved"
    elif built:
        status = "empty"
    elif hard_failures:
        status = "failed"
    elif not_packages:
        status = "unsupported"
    else:
        status = "empty"
    return _result(nodes, edges, diagnostics, None, status=status, language="python")


def _add_module(nodes: list[dict], seen: set[str], module: str, path: str | None, files) -> str:
    module_id = file_id(path, files) if path else external_id(module)
    if module_id not in seen:
        seen.add(module_id)
        nodes.append({"id": module_id, "kind": "file" if path else "external",
                      "path": path,
                      "start_line": None, "end_line": None, "name": module,
                      "backend": "grimp", **({"external": True} if path is None else {})})
    return module_id


def _result(nodes, edges, diagnostics, languages, *, status, language=None) -> dict:
    if language is not None:
        capabilities = [{"language": language, "graph": "import", "backend": "grimp",
                         "status": status,
                         "limitations": "module-level imports only"}]
    else:
        capabilities = [{"language": lang, "graph": "import", "backend": "dependency-cruiser",
                         "status": status, "limitations": None} for lang in (languages or [])]
    return {"nodes": nodes, "edges": edges, "diagnostics": diagnostics, "capabilities": capabilities}


def _top_level_python_packages(repo) -> list[str]:
    packages: list[str] = []
    try:
        import pathlib

        entries = sorted(pathlib.Path(repo).iterdir())
    except OSError:
        return packages
    for entry in entries:
        name = entry.name
        if name.startswith((".", "_")):
            continue
        if entry.is_dir() and (entry / "__init__.py").is_file():
            packages.append(name)
        elif entry.is_file() and entry.suffix == ".py" and name != "setup.py":
            packages.append(entry.stem)
    return packages
