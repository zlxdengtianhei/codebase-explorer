"""Public-surface overlay. Bindings stay out of the symbol denominator."""

from __future__ import annotations

import ast
import hashlib
import sys
import __future__
from collections.abc import Iterable, Mapping
from pathlib import Path

from pydantic import Field

from src.semantic.inventory import enumerate_python_files
from src.semantic.models import SemanticLedger, SemanticModel


SURFACE_SCHEMA = "cbe-public-surface-1"
# n7d §4.2: chase ImportFrom / star a bounded depth; cycle via seen set.
REEEXPORT_MAX_DEPTH = 3
# Historical n7fix T2 dropped names. Not the B2 gate predicate — the gate is
# ``index_noise_names`` (same in-repo criterion as ``_is_repo_local_import``).
INDEX_NOISE_NAMES = frozenset({"t", "sys", "ContextVar", "LocalProxy"})
_STDLIB_EXPORT_HOMES = (
    "typing",
    "types",
    "contextvars",
    "collections.abc",
    "dataclasses",
    "enum",
    "abc",
    "functools",
    "collections",
)
_STDLIB_CAPWORD_EXPORTS: frozenset[str] | None = None


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def surface_id(path: str, name: str) -> str:
    return f"surface:{path}:{name}"


class SurfaceBinding(SemanticModel):
    surface_id: str
    name: str
    path: str
    resolved_symbol_ids: tuple[str, ...] = ()
    unresolved_reason: str = ""
    target_path: str = ""

    @property
    def resolved(self) -> bool:
        return bool(self.resolved_symbol_ids)


class PublicSurface(SemanticModel):
    schema_id: str = Field(default=SURFACE_SCHEMA, alias="schema", serialization_alias="schema")
    repo_root: str
    source_revision: str
    bindings: tuple[SurfaceBinding, ...]
    overlay_file_hashes: dict[str, str] = Field(default_factory=dict)

    @property
    def schema(self) -> str:
        return self.schema_id

    @property
    def by_id(self) -> dict[str, SurfaceBinding]:
        return {item.surface_id: item for item in self.bindings}

    @property
    def by_name(self) -> dict[str, tuple[SurfaceBinding, ...]]:
        grouped: dict[str, list[SurfaceBinding]] = {}
        for item in self.bindings:
            grouped.setdefault(item.name, []).append(item)
        return {name: tuple(items) for name, items in grouped.items()}

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.name for item in self.bindings if not item.name.startswith("_")))

    @property
    def alias_edges(self) -> set[tuple[str, str]]:
        edges: set[tuple[str, str]] = set()
        for item in self.bindings:
            for symbol_id in item.resolved_symbol_ids:
                edges.add((item.surface_id, symbol_id))
        return edges


def _star_import_modules(tree: ast.Module) -> tuple[tuple[int, str | None], ...]:
    found: list[tuple[int, str | None]] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            found.append((node.level, node.module))
    return tuple(found)


def _import_bindings(tree: ast.Module) -> dict[str, tuple[int, str | None, str]]:
    bound: dict[str, tuple[int, str | None, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                bound[local] = (node.level, node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                bound[local] = (0, alias.name, alias.name.split(".")[-1])
    return bound


def _resolve_relative_module(source_path: str, level: int, module: str | None) -> str | None:
    parts = Path(source_path).parts
    if not parts:
        return None
    # Directory of the file is the current package for both ``__init__.py`` and
    # sibling modules. Extra dots climb parents: ``from ..json import dumps``
    # in ``json/tag.py`` is level=2 → climb 1 out of ``json/`` then append json.
    dir_parts = list(parts[:-1])
    pkg_parts = dir_parts
    if level:
        climb = level - 1
        if climb > len(pkg_parts):
            return None
        pkg_parts = pkg_parts[: len(pkg_parts) - climb] if climb else pkg_parts
    if module:
        pkg_parts = [*pkg_parts, *module.split(".")]
    if not pkg_parts:
        # `from . import json` at a repo-root package: current package is "".
        return "" if level else None
    return "/".join(pkg_parts)


def _join_mod(package: str, child: str) -> str:
    child_path = child.replace(".", "/")
    if not package:
        return child_path
    return f"{package}/{child_path}"


def _imported_module_path(
    source_path: str,
    level: int,
    module: str | None,
    imported: str,
) -> str | None:
    """Slash-separated module path, including ``from . import json`` → current pkg + json."""

    base = _resolve_relative_module(source_path, level, module)
    if module is None and level > 0:
        if base is None:
            return None
        return _join_mod(base, imported)
    return base


def _candidate_files(repo_root: Path, module_path: str) -> tuple[str, ...]:
    if not module_path or module_path.startswith("/") or module_path.endswith("/"):
        return ()
    py_file = f"{module_path}.py"
    init_file = f"{module_path}/__init__.py"
    found: list[str] = []
    if (repo_root / py_file).is_file():
        found.append(py_file)
    if (repo_root / init_file).is_file():
        found.append(init_file)
    return tuple(found)


def _stdlib_top_level(module: str | None) -> bool:
    if not module:
        return False
    top = module.lstrip(".").split(".")[0]
    return top in sys.stdlib_module_names


def _is_repo_local_import(
    repo_root: Path,
    source_path: str,
    level: int,
    module: str | None,
    imported: str,
) -> bool:
    """True iff this import binds a name from a module that exists in the repo.

    Absolute stdlib imports (``import typing as t``, ``from contextvars import ContextVar``)
    are never in-repo, even when the package has a colliding filename such as ``typing.py``.
    Relative imports (``from .typing import X``) are in-repo when the file exists.
    Third-party absolute imports (``from werkzeug.local import LocalProxy``) are not.
    """

    if level == 0 and _stdlib_top_level(module):
        return False
    target = _imported_module_path(source_path, level, module, imported)
    if not target:
        return False
    return bool(_candidate_files(repo_root, target))


def _keep_import_name(
    repo_root: Path,
    source_path: str,
    level: int,
    module: str | None,
    imported: str,
) -> bool:
    return _is_repo_local_import(repo_root, source_path, level, module, imported)


def _top_level_exported_names(
    tree: ast.Module,
    *,
    repo_root: Path,
    source_path: str,
) -> list[str]:
    all_names: list[str] | None = None
    collected: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        all_names = [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
                elif isinstance(target, ast.Name) and not target.id.startswith("_"):
                    collected.append(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if not node.target.id.startswith("_"):
                collected.append(node.target.id)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    continue
                if not _keep_import_name(repo_root, source_path, node.level, node.module, alias.name):
                    continue
                collected.append(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not _keep_import_name(
                    repo_root, source_path, 0, alias.name, alias.name.split(".")[-1]
                ):
                    continue
                collected.append(alias.asname or alias.name.split(".")[0])
    if all_names is not None:
        return list(dict.fromkeys(n for n in all_names if not n.startswith("_")))
    return list(dict.fromkeys(n for n in collected if not n.startswith("_")))


def _index_symbols(ledger: SemanticLedger) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        tail = record.qualified_name.rsplit(".", 1)[-1]
        index.setdefault((record.path, tail), []).append(symbol_id)
        index.setdefault((record.path, record.qualified_name), []).append(symbol_id)
    return index


def _module_level_ids(
    symbol_index: Mapping[tuple[str, str], list[str]],
    path: str,
    name: str,
) -> list[str]:
    """Hits whose unqualified qualified_name is exactly ``name`` (not ``Client.get``)."""

    hits = symbol_index.get((path, name), [])
    return [sid for sid in dict.fromkeys(hits) if sid.split("::", 1)[-1] == name]


def _load_tree(
    repo_root: Path,
    relative: str,
    cache: dict[str, ast.Module | None],
) -> ast.Module | None:
    if relative in cache:
        return cache[relative]
    path = repo_root / relative
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=relative)
    except (OSError, SyntaxError):
        cache[relative] = None
        return None
    if not isinstance(tree, ast.Module):
        cache[relative] = None
        return None
    cache[relative] = tree
    return tree


def _chase_definition(
    *,
    start_files: tuple[str, ...],
    name: str,
    repo_root: Path,
    ledger: SemanticLedger,
    symbol_index: Mapping[tuple[str, str], list[str]],
    ast_cache: dict[str, ast.Module | None],
    max_depth: int = REEEXPORT_MAX_DEPTH,
) -> tuple[tuple[str, ...], str, str]:
    """Follow ImportFrom / star until a module-level ledger symbol, or the last hop."""

    seen: set[tuple[str, str]] = set()
    last_path = start_files[0] if start_files else ""

    def visit(path: str, lookup: str, depth: int) -> tuple[str, ...]:
        nonlocal last_path
        if not path or depth > max_depth or (path, lookup) in seen:
            return ()
        seen.add((path, lookup))
        last_path = path
        hits = tuple(_module_level_ids(symbol_index, path, lookup))
        if hits:
            return hits
        tree = _load_tree(repo_root, path, ast_cache)
        if tree is None:
            return ()
        local = _import_bindings(tree).get(lookup)
        if local is not None:
            level, module, imported = local
            target = _imported_module_path(path, level, module, imported)
            if target is None:
                return ()
            files = _candidate_files(repo_root, target)
            for nxt in files:
                found = visit(nxt, imported, depth + 1)
                if found:
                    return found
            return ()
        for level, module in _star_import_modules(tree):
            target = _resolve_relative_module(path, level, module)
            if target is None:
                continue
            files = _candidate_files(repo_root, target)
            for nxt in files:
                found = visit(nxt, lookup, depth + 1)
                if found:
                    return found
        return ()

    found: tuple[str, ...] = ()
    for start in start_files:
        found = visit(start, name, 0)
        if found:
            break
    if found:
        def_path = ledger.symbols[found[0]].path if found[0] in ledger.symbols else last_path
        return found, "", def_path
    if not start_files:
        return (), f"module-level name {name} is not a FunctionDef/ClassDef", ""
    if last_path and last_path in start_files and _path_is_imported_module(last_path, name):
        reason = f"import target is a package/module with no ledger symbol; last hop {last_path}"
    elif last_path:
        reason = f"reexport chase failed; last hop {last_path}"
    else:
        reason = f"module-level name {name} is not a FunctionDef/ClassDef"
    return (), reason, last_path


def resolve_name(
    *,
    source_path: str,
    name: str,
    tree: ast.Module,
    repo_root: Path,
    ledger: SemanticLedger,
    symbol_index: Mapping[tuple[str, str], list[str]],
    ast_cache: dict[str, ast.Module | None] | None = None,
) -> tuple[tuple[str, ...], str, str]:
    cache = ast_cache if ast_cache is not None else {}
    cache.setdefault(source_path, tree)

    local = _import_bindings(tree).get(name)
    if local is not None:
        level, module, imported = local
        target_mod = _imported_module_path(source_path, level, module, imported)
        if target_mod is None:
            return (), f"cannot resolve import module for {name}", ""
        files = _candidate_files(repo_root, target_mod)
        if not files:
            return (), f"import {name} resolved to {target_mod} with no lexical symbol", ""
        return _chase_definition(
            start_files=files,
            name=imported,
            repo_root=repo_root,
            ledger=ledger,
            symbol_index=symbol_index,
            ast_cache=cache,
        )

    same_file = tuple(_module_level_ids(symbol_index, source_path, name))
    if same_file:
        return same_file, "", source_path

    star_files: list[str] = []
    for level, module in _star_import_modules(tree):
        target_mod = _resolve_relative_module(source_path, level, module)
        if target_mod is None:
            continue
        star_files.extend(_candidate_files(repo_root, target_mod))
    unique_files = tuple(dict.fromkeys(star_files))
    if not unique_files:
        return (), f"module-level name {name} is not a FunctionDef/ClassDef", ""
    return _chase_definition(
        start_files=unique_files,
        name=name,
        repo_root=repo_root,
        ledger=ledger,
        symbol_index=symbol_index,
        ast_cache=cache,
    )


def extract_public_surface(
    repo_root: str | Path,
    ledger: SemanticLedger,
) -> PublicSurface:
    root = Path(repo_root).expanduser().resolve()
    symbol_index = _index_symbols(ledger)
    bindings: list[SurfaceBinding] = []
    file_hashes: dict[str, str] = {}
    seen: set[str] = set()
    ast_cache: dict[str, ast.Module | None] = {}

    for path in enumerate_python_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=relative)
        except (OSError, SyntaxError):
            continue
        if not isinstance(tree, ast.Module):
            continue
        ast_cache[relative] = tree
        names = _top_level_exported_names(tree, repo_root=root, source_path=relative)
        if not names:
            continue
        file_hashes[relative] = _file_digest(path)
        for name in names:
            sid = surface_id(relative, name)
            if sid in seen:
                continue
            seen.add(sid)
            resolved, reason, target_path = resolve_name(
                source_path=relative,
                name=name,
                tree=tree,
                repo_root=root,
                ledger=ledger,
                symbol_index=symbol_index,
                ast_cache=ast_cache,
            )
            bindings.append(
                SurfaceBinding(
                    surface_id=sid,
                    name=name,
                    path=relative,
                    resolved_symbol_ids=resolved,
                    unresolved_reason=reason,
                    target_path=target_path,
                )
            )

    bindings.sort(key=lambda item: (item.path, item.name))
    return PublicSurface(
        schema=SURFACE_SCHEMA,
        repo_root=root.as_posix(),
        source_revision=ledger.source_revision,
        bindings=tuple(bindings),
        overlay_file_hashes=dict(sorted(file_hashes.items())),
    )


def coerce_surface(value: PublicSurface | Mapping[str, object] | None) -> PublicSurface | None:
    if value is None:
        return None
    if isinstance(value, PublicSurface):
        return value
    return PublicSurface.model_validate(value)


def oracle_init_exports(repo_root: str | Path) -> tuple[tuple[str, str], ...]:
    """Names the frozen N1 oracle will look for (any ``__init__.py``).

    Import bindings enter the denominator only when the imported module is in
    this repo. Stdlib aliases (``sys``, ``import typing as t``) and third-party
    re-exports (``from contextvars import ContextVar``) stay out. ``__all__``
    strings and assignments remain, so a name explicitly published still counts.
    """

    root = Path(repo_root)
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for init in sorted(root.rglob("__init__.py")):
        if any(part in {".venv", "node_modules", ".git", ".codebase-docs", ".codebase-analysis"} for part in init.parts):
            continue
        try:
            tree = ast.parse(init.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        rel = init.relative_to(root).as_posix()
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if not _keep_import_name(root, rel, node.level, node.module, alias.name):
                        continue
                    names.append(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if not _keep_import_name(root, rel, 0, alias.name, alias.name.split(".")[-1]):
                        continue
                    names.append(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, (ast.List, ast.Tuple)):
                            names.extend(
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            )
                    elif isinstance(target, ast.Name) and not target.id.startswith("_"):
                        names.append(target.id)
        for name in names:
            if name.startswith("_") or name in seen:
                continue
            seen.add(name)
            found.append((name, rel))
    return tuple(found)


def _path_is_imported_module(path: str, name: str) -> bool:
    """True iff ``path`` is the file that implements module ``name``."""

    if not path or not name:
        return False
    parts = Path(path)
    if parts.name == "__init__.py":
        return parts.parent.name == name
    return parts.stem == name


def _stdlib_capword_exports() -> frozenset[str]:
    """Public CapWords / ALL_CAPS names from stdlib modules typically ``from X import``-ed."""

    global _STDLIB_CAPWORD_EXPORTS
    if _STDLIB_CAPWORD_EXPORTS is not None:
        return _STDLIB_CAPWORD_EXPORTS
    found: set[str] = set()
    for mod_name in _STDLIB_EXPORT_HOMES:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except ImportError:
            continue
        exported = getattr(mod, "__all__", None)
        names = exported if exported is not None else (item for item in dir(mod) if not item.startswith("_"))
        for item in names:
            if not item or item.startswith("_"):
                continue
            if item.isupper() or (item[0].isupper() and item.isidentifier()):
                found.add(item)
    _STDLIB_CAPWORD_EXPORTS = frozenset(found)
    return _STDLIB_CAPWORD_EXPORTS


def _is_external_unqualified_name(name: str) -> bool:
    """Names-only half of the B2 gate: provably not a repo symbol without a tree.

    A name is external if it is a stdlib top-level module, a ``__future__``
    feature, or a CapWords/ALL_CAPS export of a stdlib typing-like module.
    Application names (``Flask``, ``request``, ``jsonify``) stay off this list.
    """

    if not name or name.startswith("_"):
        return False
    if _stdlib_top_level(name):
        return True
    if name in __future__.all_feature_names:
        return True
    return name in _stdlib_capword_exports()


def _repo_local_surface_names(
    repo_root: Path,
    ledger: SemanticLedger | None = None,
) -> set[str]:
    """Names production would treat as in-repo (same criterion as ``_is_repo_local_import``).

    Local = module-level def / assignment / ``__all__`` publication, or an
    import ``_keep_import_name`` would keep. Stdlib aliases (``import typing as t``)
    and third-party imports (``from werkzeug.local import LocalProxy``) stay out
    even when a colliding filename exists.
    """

    repo_root = Path(repo_root).expanduser().resolve()
    local: set[str] = set()
    if ledger is not None:
        for record in ledger.symbols.values():
            tail = record.qualified_name.rsplit(".", 1)[-1]
            if tail and not tail.startswith("_"):
                local.add(tail)
    for path in enumerate_python_files(repo_root):
        relative = path.relative_to(repo_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=relative)
        except (OSError, SyntaxError):
            continue
        if not isinstance(tree, ast.Module):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith("_"):
                    local.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id == "__all__" and isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                if elt.value and not elt.value.startswith("_"):
                                    local.add(elt.value)
                    elif target.id != "__all__" and not target.id.startswith("_"):
                        local.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if not node.target.id.startswith("_"):
                    local.add(node.target.id)
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    if not _keep_import_name(repo_root, relative, node.level, node.module, alias.name):
                        continue
                    kept = alias.asname or alias.name
                    if kept and not kept.startswith("_"):
                        local.add(kept)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if not _keep_import_name(
                        repo_root, relative, 0, alias.name, alias.name.split(".")[-1]
                    ):
                        continue
                    kept = alias.asname or alias.name.split(".")[0]
                    if kept and not kept.startswith("_"):
                        local.add(kept)
    return local


def index_noise_names(
    names: set[str] | tuple[str, ...] | list[str] | Iterable[str],
    *,
    repo_root: str | Path | None = None,
    ledger: SemanticLedger | None = None,
) -> tuple[str, ...]:
    """B2 gate: INDEX names that are not repo-local symbols.

    Same criterion as production ``_is_repo_local_import``, not a four-name
    denylist. With ``repo_root``, a name is noise iff it is absent from the
    in-repo surface (defs, assignments, ``__all__``, kept imports). Without a
    repo, a name is noise iff it is a stdlib module, ``__future__`` feature, or
    stdlib CapWords export — so injecting ``os`` / ``TYPE_CHECKING`` turns red
    even when those strings were never enumerated.
    """

    pending = {name for name in names if name and not str(name).startswith("_")}
    if repo_root is not None:
        local = _repo_local_surface_names(Path(repo_root).expanduser().resolve(), ledger)
        return tuple(sorted(name for name in pending if name not in local))
    return tuple(sorted(name for name in pending if _is_external_unqualified_name(name)))


def entry_bindings(surface: PublicSurface) -> tuple[SurfaceBinding, ...]:
    """Names the oracle's N1 first-screen check will look for.

    The oracle enumerates ``__init__.py`` exports. We project the shallowest
    ``__init__.py`` plus ``globals.py`` so ``request`` / ``g`` still appear.
    Stdlib / third-party import bindings are already dropped by
    ``extract_public_surface``; this function does not re-add them.
    """

    inits = [item.path for item in surface.bindings if Path(item.path).name == "__init__.py"]
    root_dir = ""
    if inits:
        root_init = min(inits, key=lambda path: (path.count("/"), path))
        parent = Path(root_init).parent.as_posix()
        root_dir = "" if parent in {".", ""} else parent
    globals_path = "globals.py" if not root_dir else f"{root_dir}/globals.py"
    seen: set[str] = set()
    ordered: list[SurfaceBinding] = []
    for item in surface.bindings:
        if item.name.startswith("_") or item.name in seen:
            continue
        if Path(item.path).name == "__init__.py":
            seen.add(item.name)
            ordered.append(item)
    for item in surface.bindings:
        if item.name.startswith("_") or item.name in seen:
            continue
        if item.path == globals_path:
            seen.add(item.name)
            ordered.append(item)
    if not ordered:
        return tuple(item for item in surface.bindings if not item.name.startswith("_"))
    return tuple(ordered)
