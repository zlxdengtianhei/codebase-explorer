"""Deterministic public-surface overlay. Bindings are not ledger symbols.

Ported from r003 variant_B.patch `src/semantic/surface.py`, plus source line
spans so unresolved names (request / signals) still get a document target.
"""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from src.semantic.inventory import enumerate_python_files
from src.semantic.models import SemanticLedger


SURFACE_SCHEMA = "cbe-public-surface-1"


@dataclass(frozen=True)
class SurfaceBinding:
    name: str
    path: str
    kind: str
    origin_path: str | None = None
    origin_name: str | None = None
    resolved_symbol_ids: tuple[str, ...] = ()
    residual: str | None = None
    lineno: int | None = None
    end_lineno: int | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "name": self.name,
            "origin_name": self.origin_name,
            "origin_path": self.origin_path,
            "path": self.path,
            "residual": self.residual,
            "resolved_symbol_ids": list(self.resolved_symbol_ids),
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
        }


@dataclass(frozen=True)
class PublicSurface:
    repo_root: str
    source_revision: str | None
    bindings: tuple[SurfaceBinding, ...]
    file_hashes: Mapping[str, str] = field(default_factory=dict)

    @property
    def exported_names(self) -> tuple[str, ...]:
        names = {
            item.name
            for item in self.bindings
            if item.path.endswith("__init__.py") and not item.name.startswith("_")
        }
        return tuple(sorted(names))

    @property
    def resolved_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.name
                    for item in self.bindings
                    if item.resolved_symbol_ids and not item.name.startswith("_")
                }
            )
        )

    @property
    def unresolved_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.exported_names) - set(self.resolved_names)))

    def bindings_for(self, path: str) -> tuple[SurfaceBinding, ...]:
        return tuple(item for item in self.bindings if item.path == path)

    def index_rows(self) -> list[SurfaceBinding]:
        """One binding per public __init__ name; prefer resolved + shorter path."""

        chosen: dict[str, SurfaceBinding] = {}
        for item in self.bindings:
            if item.name.startswith("_") or item.name == "*":
                continue
            if not item.path.endswith("__init__.py"):
                continue
            previous = chosen.get(item.name)
            if previous is None:
                chosen[item.name] = item
                continue
            if item.resolved_symbol_ids and not previous.resolved_symbol_ids:
                chosen[item.name] = item
            elif len(item.path) < len(previous.path):
                chosen[item.name] = item
        return [chosen[name] for name in sorted(chosen)]

    def to_json(self) -> dict[str, object]:
        return {
            "schema": SURFACE_SCHEMA,
            "repo_root": self.repo_root,
            "source_revision": self.source_revision,
            "file_hashes": dict(sorted(self.file_hashes.items())),
            "exported_names": list(self.exported_names),
            "resolved_names": list(self.resolved_names),
            "unresolved_names": list(self.unresolved_names),
            "n_exported": len(self.exported_names),
            "n_resolved": len(self.resolved_names),
            "n_unresolved": len(self.unresolved_names),
            "bindings": [item.to_json() for item in self.bindings],
        }


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _literal_all(node: ast.AST) -> tuple[str, ...] | None:
    if not isinstance(node, ast.Assign):
        return None
    if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
        return None
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return None
    names: list[str] = []
    for item in node.value.elts:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            names.append(item.value)
        else:
            return None
    return tuple(names)


def _ann_target(node: ast.AnnAssign) -> str | None:
    if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
        return node.target.id
    return None


def _assign_targets(node: ast.Assign) -> tuple[str, ...]:
    names: list[str] = []
    for target in node.targets:
        if isinstance(target, ast.Name) and not target.id.startswith("_") and target.id != "__all__":
            names.append(target.id)
    return tuple(names)


def _package_dir(relative: str) -> tuple[str, ...]:
    return tuple(relative.split("/")[:-1])


def _resolve_imported_module(
    from_path: str,
    module: str | None,
    level: int,
    files: set[str],
) -> str | None:
    package = list(_package_dir(from_path))
    if level:
        drop = level - 1
        if drop > len(package):
            return None
        if drop:
            package = package[: len(package) - drop]
    suffix = [part for part in (module or "").split(".") if part]
    base = "/".join([*package, *suffix])
    if not base:
        return None
    as_file = f"{base}.py"
    as_init = f"{base}/__init__.py"
    if as_file in files:
        return as_file
    if as_init in files:
        return as_init
    return None


def _rhs_name(value: ast.AST | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
    if isinstance(value, ast.Attribute):
        return value.attr
    return None


def _annotation_name(node: ast.AnnAssign) -> str | None:
    annotation = node.annotation
    if isinstance(annotation, ast.Name):
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        return annotation.attr
    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        return annotation.value.id
    return None


def _node_span(node: ast.AST) -> tuple[int | None, int | None]:
    lineno = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None) or lineno
    return lineno, end


def _lookup_symbol(
    ledger: SemanticLedger | None,
    path: str | None,
    name: str,
) -> tuple[str, ...]:
    if ledger is None or not path:
        return ()
    by_qual = {
        record.qualified_name: symbol_id
        for symbol_id, record in ledger.symbols.items()
        if record.path == path
    }
    if name in by_qual:
        return (by_qual[name],)
    return tuple(
        sorted(
            symbol_id
            for symbol_id, record in ledger.symbols.items()
            if record.path == path and record.qualified_name.rsplit(".", 1)[-1] == name
        )
    )


def extract_public_surface(
    repo_root: str | Path,
    ledger: SemanticLedger | None = None,
) -> PublicSurface:
    root = Path(repo_root).expanduser().resolve()
    files = enumerate_python_files(root)
    file_set = {_relative_posix(path, root) for path in files}
    bindings: list[SurfaceBinding] = []
    hashes: dict[str, str] = {}

    for path in files:
        relative = _relative_posix(path, root)
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        hashes[relative] = _file_digest(raw)
        source = raw.decode("utf-8", errors="replace")
        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError:
            continue
        bindings.extend(_bindings_from_module(relative, tree, file_set, ledger))

    bindings.sort(key=lambda item: (item.path, item.name, item.kind))
    return PublicSurface(
        repo_root=root.as_posix(),
        source_revision=None if ledger is None else ledger.source_revision,
        bindings=tuple(bindings),
        file_hashes=hashes,
    )


def _import_origin(
    relative: str,
    node: ast.ImportFrom,
    alias: ast.alias,
    files: set[str],
) -> tuple[str | None, str]:
    origin_name = alias.name.split(".")[-1]
    if alias.name == "*":
        return None, origin_name
    module = node.module if node.module else alias.name
    origin_path = _resolve_imported_module(relative, module, node.level, files)
    return origin_path, origin_name


def _bindings_from_module(
    relative: str,
    tree: ast.Module,
    files: set[str],
    ledger: SemanticLedger | None,
) -> list[SurfaceBinding]:
    is_init = Path(relative).name == "__init__.py"
    explicit_all: tuple[str, ...] | None = None
    for node in tree.body:
        found = _literal_all(node)
        if found is not None:
            explicit_all = found
            break

    result: list[SurfaceBinding] = []
    if is_init and explicit_all is not None:
        origins: dict[str, tuple[str | None, str, ast.AST]] = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module != "__future__":
                for alias in node.names:
                    local = alias.asname or alias.name
                    origin_path, origin_name = _import_origin(relative, node, alias, files)
                    origins[local] = (origin_path, origin_name, node)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    origins[local] = (None, local, node)
        for name in explicit_all:
            if name.startswith("_"):
                continue
            origin_path, origin_name, src_node = origins.get(name, (relative, name, tree))
            resolved = _lookup_symbol(ledger, origin_path, origin_name)
            if not resolved:
                resolved = _lookup_symbol(ledger, relative, name)
            lineno, end_lineno = _node_span(src_node)
            result.append(
                SurfaceBinding(
                    name=name,
                    path=relative,
                    kind="all",
                    origin_path=origin_path,
                    origin_name=origin_name,
                    resolved_symbol_ids=resolved,
                    residual=None if resolved else "export name did not resolve to a ledger symbol",
                    lineno=lineno,
                    end_lineno=end_lineno,
                )
            )
        seen = {item.name for item in result}
        for node in tree.body:
            if not isinstance(node, ast.Import):
                continue
            lineno, end_lineno = _node_span(node)
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if local.startswith("_") or local in seen:
                    continue
                result.append(
                    SurfaceBinding(
                        name=local,
                        path=relative,
                        kind="reexport",
                        origin_path=None,
                        origin_name=local,
                        residual="import name is not in __all__ but the N1 probe counts it",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
                seen.add(local)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [(alias.asname or alias.name.split(".")[0]) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and getattr(node, "module", None) != "__future__":
                names = [
                    (alias.asname or alias.name)
                    for alias in node.names
                    if alias.name != "*"
                ]
            lineno, end_lineno = _node_span(node)
            for local in names:
                if not local or local.startswith("_") or local in seen:
                    continue
                result.append(
                    SurfaceBinding(
                        name=local,
                        path=relative,
                        kind="reexport",
                        residual="nested import counted by N1 probe, not a public export",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
                seen.add(local)
        return result

    for node in tree.body:
        lineno, end_lineno = _node_span(node)
        if is_init and isinstance(node, ast.ImportFrom) and node.module != "__future__":
            for alias in node.names:
                if alias.name == "*":
                    result.append(
                        SurfaceBinding(
                            name="*",
                            path=relative,
                            kind="reexport",
                            residual="wildcard import is not a public name",
                            lineno=lineno,
                            end_lineno=end_lineno,
                        )
                    )
                    continue
                local = alias.asname or alias.name
                if local.startswith("_"):
                    continue
                origin_path, origin_name = _import_origin(relative, node, alias, files)
                resolved = _lookup_symbol(ledger, origin_path, origin_name)
                result.append(
                    SurfaceBinding(
                        name=local,
                        path=relative,
                        kind="reexport",
                        origin_path=origin_path,
                        origin_name=origin_name,
                        resolved_symbol_ids=resolved,
                        residual=None if resolved else "re-export did not resolve to a ledger symbol",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
        elif is_init and isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if local.startswith("_"):
                    continue
                origin_path = _resolve_imported_module(relative, alias.name, 0, files)
                resolved = _lookup_symbol(ledger, origin_path, local)
                result.append(
                    SurfaceBinding(
                        name=local,
                        path=relative,
                        kind="reexport",
                        origin_path=origin_path,
                        origin_name=local,
                        resolved_symbol_ids=resolved,
                        residual=None if resolved else "imported module is not a ledger symbol",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
        elif isinstance(node, ast.Assign):
            rhs = _rhs_name(node.value)
            for name in _assign_targets(node):
                resolved = _lookup_symbol(ledger, relative, name)
                if not resolved and rhs:
                    resolved = _lookup_symbol(ledger, relative, rhs)
                result.append(
                    SurfaceBinding(
                        name=name,
                        path=relative,
                        kind="assign",
                        origin_path=relative,
                        origin_name=rhs,
                        resolved_symbol_ids=resolved,
                        residual=None if resolved else "module-level binding is not a ledger symbol",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
        elif isinstance(node, ast.AnnAssign):
            name = _ann_target(node)
            if name is None:
                continue
            rhs = _rhs_name(node.value)
            annotation = _annotation_name(node)
            resolved = _lookup_symbol(ledger, relative, name)
            if not resolved and rhs:
                resolved = _lookup_symbol(ledger, relative, rhs)
            result.append(
                SurfaceBinding(
                    name=name,
                    path=relative,
                    kind="assign",
                    origin_path=relative,
                    origin_name=rhs or annotation,
                    resolved_symbol_ids=resolved,
                    residual=None if resolved else "module-level binding is not a ledger symbol",
                    lineno=lineno,
                    end_lineno=end_lineno,
                )
            )
    if is_init:
        seen = {item.name for item in result}
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [(alias.asname or alias.name.split(".")[0]) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
                names = [
                    (alias.asname or alias.name)
                    for alias in node.names
                    if alias.name != "*"
                ]
            lineno, end_lineno = _node_span(node)
            for local in names:
                if not local or local.startswith("_") or local in seen:
                    continue
                result.append(
                    SurfaceBinding(
                        name=local,
                        path=relative,
                        kind="reexport",
                        residual="nested import counted by N1 probe, not a public export",
                        lineno=lineno,
                        end_lineno=end_lineno,
                    )
                )
                seen.add(local)
    return result
