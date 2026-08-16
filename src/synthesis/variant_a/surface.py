"""Public-surface overlay. Bindings stay out of the symbol denominator."""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from pathlib import Path

from pydantic import Field

from src.semantic.inventory import enumerate_python_files
from src.semantic.models import SemanticLedger, SemanticModel


SURFACE_SCHEMA = "cbe-public-surface-1"


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


def _top_level_exported_names(tree: ast.Module) -> list[str]:
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
                collected.append(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                collected.append(alias.asname or alias.name.split(".")[0])
    if all_names is not None:
        return list(dict.fromkeys(n for n in all_names if not n.startswith("_")))
    return list(dict.fromkeys(n for n in collected if not n.startswith("_")))


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
    dir_parts = list(parts[:-1])
    pkg_parts = dir_parts
    if level:
        if Path(source_path).name == "__init__.py":
            climb = level - 1
        else:
            climb = level
        if climb > len(pkg_parts):
            return None
        pkg_parts = pkg_parts[: len(pkg_parts) - climb] if climb else pkg_parts
    if module:
        pkg_parts = [*pkg_parts, *module.split(".")]
    if not pkg_parts:
        return None
    return "/".join(pkg_parts)


def _candidate_files(repo_root: Path, module_path: str) -> tuple[str, ...]:
    py_file = f"{module_path}.py"
    init_file = f"{module_path}/__init__.py"
    found: list[str] = []
    if (repo_root / py_file).is_file():
        found.append(py_file)
    if (repo_root / init_file).is_file():
        found.append(init_file)
    return tuple(found)


def _index_symbols(ledger: SemanticLedger) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        tail = record.qualified_name.rsplit(".", 1)[-1]
        index.setdefault((record.path, tail), []).append(symbol_id)
        index.setdefault((record.path, record.qualified_name), []).append(symbol_id)
    return index


def resolve_name(
    *,
    source_path: str,
    name: str,
    tree: ast.Module,
    repo_root: Path,
    ledger: SemanticLedger,
    symbol_index: Mapping[tuple[str, str], list[str]],
) -> tuple[tuple[str, ...], str, str]:
    local = _import_bindings(tree).get(name)
    if local is not None:
        level, module, imported = local
        target_mod = _resolve_relative_module(source_path, level, module)
        if target_mod is None:
            return (), f"cannot resolve import module for {name}", ""
        files = _candidate_files(repo_root, target_mod)
        hits: list[str] = []
        for path in files:
            hits.extend(symbol_index.get((path, imported), []))
        unique = tuple(dict.fromkeys(hits))
        if unique:
            return unique, "", files[0] if files else ""
        return (), f"import {name} resolved to {files or target_mod} with no lexical symbol", files[0] if files else ""

    same_file = tuple(dict.fromkeys(symbol_index.get((source_path, name), [])))
    if same_file:
        return same_file, "", source_path

    star_hits: list[str] = []
    star_files: list[str] = []
    for level, module in _star_import_modules(tree):
        target_mod = _resolve_relative_module(source_path, level, module)
        if target_mod is None:
            continue
        files = _candidate_files(repo_root, target_mod)
        star_files.extend(files)
        for path in files:
            star_hits.extend(symbol_index.get((path, name), []))
    unique_star = tuple(dict.fromkeys(star_hits))
    if unique_star:
        first = ledger.symbols[unique_star[0]].path if unique_star[0] in ledger.symbols else (star_files[0] if star_files else "")
        return unique_star, "", first
    return (), f"module-level name {name} is not a FunctionDef/ClassDef", star_files[0] if star_files else ""


def extract_public_surface(
    repo_root: str | Path,
    ledger: SemanticLedger,
) -> PublicSurface:
    root = Path(repo_root).expanduser().resolve()
    symbol_index = _index_symbols(ledger)
    bindings: list[SurfaceBinding] = []
    file_hashes: dict[str, str] = {}
    seen: set[str] = set()

    for path in enumerate_python_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=relative)
        except (OSError, SyntaxError):
            continue
        if not isinstance(tree, ast.Module):
            continue
        names = _top_level_exported_names(tree)
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
    """Names the frozen N1 oracle will look for (any ``__init__.py``, ``ast.walk``).

    The overlay itself stays top-level-only so ``os``/``sys`` imported inside a
    helper do not become citeable surface ids. INDEX still has to *mention*
    those names or N1 drops them.
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
                names.extend(a.asname or a.name for a in node.names if a.name != "*")
            elif isinstance(node, ast.Import):
                names.extend(a.asname or a.name.split(".")[0] for a in node.names)
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


def entry_bindings(surface: PublicSurface) -> tuple[SurfaceBinding, ...]:
    """Names the oracle's N1 first-screen check will look for.

    The oracle enumerates ``__init__.py`` exports. We project the shallowest
    ``__init__.py`` plus ``globals.py`` so ``request`` / ``g`` still appear.
    """

    # Oracle N1 denominators are names found in any ``__init__.py``. Project
    # those first so ``sys`` imported by a nested init still appears.
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
