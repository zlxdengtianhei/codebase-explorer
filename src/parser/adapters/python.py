"""Truthful Python ``ast`` normalization into canonical ``cbe-ir/2`` models."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.ir import (
    Availability,
    CapabilityCell,
    EntityKind,
    EntityRef,
    EvidenceSpan,
    Relation,
    ResolutionMethod,
    ResolutionStatus,
    SemanticTier,
    SourceUnit,
    SourceUnitState,
    Symbol,
    VerificationStatus,
    deterministic_entity_id,
)
from src.parser.adapters.base import FileIR, LanguageAdapter
from src.parser.backend import FailureCode, SyntaxArtifact, TypedFailure
_BUILTINS = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "globals",
    "int", "isinstance", "len", "list", "map", "max", "min", "next", "object",
    "open", "print", "range", "repr", "reversed", "set", "sorted", "str", "sum",
    "super", "tuple", "type", "zip",
})
@dataclass(frozen=True)
class _Definition:
    path: str
    kind: str
    qualified_name: str
    lexical_qualified_name: str
    lexical_kind: str
    local_name: str
    locator: str
    node: ast.AST
@dataclass(frozen=True)
class _ImportBinding:
    local_name: str
    target: str
    module: str
    aliased: bool
    wildcard: bool = False


@dataclass(frozen=True)
class _ModuleInfo:
    path: str
    name: str
    source: str
    tree: ast.Module
    definitions: tuple[_Definition, ...]
    imports: tuple[_ImportBinding, ...]


class PythonLanguageAdapter(LanguageAdapter):
    """Normalize verified Python AST artifacts using a repository-local index."""
    def __init__(
        self,
        root: str | Path,
        *,
        source_overrides: Mapping[str, str] | None = None,
    ) -> None:
        self._root = Path(root).resolve()
        self._source_overrides = dict(source_overrides or {})
        # path -> (source sha256, _ModuleInfo from ast.parse). Never stores
        # artifact.syntax_tree. Lives only on this adapter instance.
        self._parsed_module_cache: dict[str, tuple[str, _ModuleInfo]] = {}
        # One rglob + one full-repo parse per adapter lifetime. normalize() used
        # to rglob and re-read every *.py on every file; django paid that 908
        # times and died on the 15-minute wall. Fresh file after first walk
        # invalidates both caches once (see _scan_modules).
        self._repo_py_paths: frozenset[str] | None = None
        self._repo_modules: dict[str, _ModuleInfo] | None = None
        self._path_walks: int = 0

    def normalize(self, artifact: SyntaxArtifact) -> FileIR | TypedFailure:
        if artifact.language.lower() != "python":
            return self._failure(
                artifact,
                FailureCode.UNSUPPORTED_LANGUAGE,
                "Python adapter accepts Python artifacts only",
            )
        if not isinstance(artifact.syntax_tree, ast.Module):
            return self._failure(
                artifact,
                FailureCode.INVALID_INPUT,
                "Python adapter requires an ast.Module syntax tree",
            )
        source = self._read_source(artifact.source_unit.path)
        if isinstance(source, TypedFailure):
            return source
        actual_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if actual_hash != artifact.source_unit.content_hash:
            return self._failure(
                artifact,
                FailureCode.CONTENT_HASH_MISMATCH,
                f"content hash mismatch for {artifact.source_unit.path}",
                details=(f"expected={artifact.source_unit.content_hash}", f"actual={actual_hash}"),
            )

        modules = self._scan_modules(artifact)
        current = modules.get(artifact.source_unit.path)
        if current is None:
            current = self._module_info(
                artifact.source_unit.path, source, artifact.syntax_tree
            )
            modules[current.path] = current
        source_unit = artifact.source_unit.model_copy(
            update={
                "state": SourceUnitState.INDEXED,
                "backend_id": artifact.backend_id,
                "backend_version": artifact.backend_version,
                "diagnostics": tuple(artifact.diagnostics),
            }
        )
        definitions = {
            definition.qualified_name: definition
            for module in modules.values()
            for definition in module.definitions
        }
        symbols = tuple(
            sorted(
                (
                    self._symbol(source_unit, source, definition)
                    for definition in current.definitions
                ),
                key=lambda item: item.id,
            )
        )
        relations = self._relations(source_unit, current, modules, definitions)
        return FileIR(
            source_unit=source_unit,
            symbols=symbols,
            relations=tuple(sorted(relations, key=lambda item: item.id)),
        )

    @staticmethod
    def capability_cells(
        *,
        backend_id: str,
        backend_version: str,
        toolchain_conditions: tuple[str, ...],
        evidence_receipt_id: str,
    ) -> tuple[CapabilityCell, ...]:
        """Return the frozen Python capability axes without self-verifying them."""
        axes = {
            "syntax": (Availability.AVAILABLE, SemanticTier.RESOLVED),
            "imports": (Availability.AVAILABLE, SemanticTier.RESOLVED),
            "exports": (Availability.AVAILABLE, SemanticTier.RESOLVED),
            "names": (Availability.AVAILABLE, SemanticTier.RESOLVED),
            "calls": (Availability.AVAILABLE, SemanticTier.HEURISTIC),
            "types": (Availability.AVAILABLE, SemanticTier.HEURISTIC),
            "frameworks": (Availability.UNAVAILABLE, SemanticTier.SYNTAX_ONLY),
            "incremental": (Availability.UNAVAILABLE, SemanticTier.SYNTAX_ONLY),
        }
        limitations = {
            "calls": ("dynamic dispatch remains ambiguous or unresolved",),
            "types": ("annotations and inheritance only; no runtime/compiler claim",),
            "frameworks": ("no named framework rule is frozen",),
            "incremental": ("full rebuild only; no incremental claim",),
        }
        return tuple(
            CapabilityCell(
                language="python",
                capability=name,
                availability=availability,
                semantic_tier=tier,
                verification_status=(
                    VerificationStatus.UNVERIFIED
                    if availability is Availability.AVAILABLE
                    else VerificationStatus.CANNOT_JUDGE
                ),
                backend_id=backend_id,
                backend_version=backend_version,
                toolchain_conditions=toolchain_conditions,
                limitations=limitations.get(name, ("static Python AST evidence only",)),
                evidence_receipt_id=evidence_receipt_id,
            )
            for name, (availability, tier) in axes.items()
        )

    def _parsed_module(self, path: str, source: str) -> _ModuleInfo | None:
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        cached = self._parsed_module_cache.get(path)
        if cached is not None and cached[0] == digest:
            return cached[1]
        try:
            tree = ast.parse(source, filename=path)
        except (SyntaxError, ValueError):
            self._parsed_module_cache.pop(path, None)
            return None
        if not isinstance(tree, ast.Module):
            self._parsed_module_cache.pop(path, None)
            return None
        info = self._module_info(path, source, tree)
        self._parsed_module_cache[path] = (digest, info)
        return info

    def _list_repo_py_paths(self) -> frozenset[str]:
        if self._repo_py_paths is None:
            self._path_walks += 1
            paths = {path.relative_to(self._root).as_posix() for path in self._root.rglob("*.py")}
            paths.update(self._source_overrides)
            self._repo_py_paths = frozenset(paths)
        return self._repo_py_paths

    def _ensure_repo_modules(self) -> dict[str, _ModuleInfo]:
        if self._repo_modules is None:
            modules: dict[str, _ModuleInfo] = {}
            for path in sorted(self._list_repo_py_paths()):
                source = self._read_source(path)
                if isinstance(source, TypedFailure):
                    continue
                info = self._parsed_module(path, source)
                if info is not None:
                    modules[path] = info
            self._repo_modules = modules
        return self._repo_modules

    def _scan_modules(self, artifact: SyntaxArtifact) -> dict[str, _ModuleInfo]:
        current_path = artifact.source_unit.path
        known = self._repo_py_paths
        if known is not None and current_path not in known and current_path not in self._source_overrides:
            self._repo_py_paths = None
            self._repo_modules = None
        modules = dict(self._ensure_repo_modules())
        source = self._read_source(current_path)
        if isinstance(source, TypedFailure):
            return modules
        # Current file always uses the artifact tree, which may differ
        # from a fresh ast.parse of the same bytes. That tree is not
        # written into _parsed_module_cache.
        if isinstance(artifact.syntax_tree, ast.Module):
            modules[current_path] = self._module_info(
                current_path, source, artifact.syntax_tree
            )
        return modules

    def _module_info(self, path: str, source: str, tree: ast.Module) -> _ModuleInfo:
        module_name = self._module_name(path)
        definitions: list[_Definition] = []

        def walk(
            node: ast.AST,
            scope: tuple[str, ...] = (),
            enclosing_kind: str | None = None,
        ) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lexical = ".".join((*scope, child.name))
                    qualified = ".".join(part for part in (module_name, lexical) if part)
                    kind = "method" if enclosing_kind == "class" else "function"
                    definitions.append(
                        _Definition(
                            path=path,
                            kind=kind,
                            qualified_name=qualified,
                            lexical_qualified_name=lexical,
                            lexical_kind="method" if scope else "function",
                            local_name=child.name,
                            locator=self._definition_locator(kind, qualified, child),
                            node=child,
                        )
                    )
                    walk(child, (*scope, child.name), "function")
                elif isinstance(child, ast.ClassDef):
                    lexical = ".".join((*scope, child.name))
                    qualified = ".".join(part for part in (module_name, lexical) if part)
                    definitions.append(
                        _Definition(
                            path=path,
                            kind="class",
                            qualified_name=qualified,
                            lexical_qualified_name=lexical,
                            lexical_kind="class",
                            local_name=child.name,
                            locator=self._definition_locator("class", qualified, child),
                            node=child,
                        )
                    )
                    walk(child, (*scope, child.name), "class")
                else:
                    # Match ast-based independent enumeration: definitions in
                    # control-flow blocks remain visible without changing scope.
                    walk(child, scope, enclosing_kind)

        walk(tree)
        imports = tuple(self._import_bindings(path, tree))
        return _ModuleInfo(
            path=path,
            name=module_name,
            source=source,
            tree=tree,
            definitions=tuple(definitions),
            imports=imports,
        )

    def _import_bindings(
        self, path: str, tree: ast.Module
    ) -> list[_ImportBinding]:
        result: list[_ImportBinding] = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                module = self._absolute_import_module(path, node)
                for alias in node.names:
                    if alias.name == "*":
                        result.append(_ImportBinding("*", module, module, False, True))
                    else:
                        result.append(
                            _ImportBinding(
                                alias.asname or alias.name,
                                f"{module}.{alias.name}" if module else alias.name,
                                module,
                                alias.asname is not None,
                            )
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result.append(
                        _ImportBinding(
                            alias.asname or alias.name.split(".")[0],
                            alias.name,
                            alias.name,
                            alias.asname is not None,
                        )
                    )
        return result

    def _relations(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        modules: Mapping[str, _ModuleInfo],
        definitions: Mapping[str, _Definition],
    ) -> list[Relation]:
        result: list[Relation] = []
        bindings = {binding.local_name: binding for binding in module.imports}
        module_by_name = {item.name: item for item in modules.values()}
        source_ref = EntityRef(kind=EntityKind.SOURCE_UNIT, id=source_unit.id)

        for node in module.tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                result.extend(
                    self._import_relations(
                        source_unit, module, node, module_by_name, definitions, source_ref
                    )
                )
            if isinstance(node, ast.ClassDef):
                result.extend(
                    self._inheritance_relations(
                        source_unit, module, node, bindings, definitions
                    )
                )
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            ):
                result.extend(
                    self._export_relations(
                        source_unit, module, node, bindings, definitions, source_ref
                    )
                )

        parent: dict[ast.AST, ast.AST] = {}
        for candidate in ast.walk(module.tree):
            for child in ast.iter_child_nodes(candidate):
                parent[child] = candidate
        function_defs = {
            definition.node: definition
            for definition in module.definitions
            if definition.kind in {"function", "method"}
        }
        method_candidates: dict[str, list[str]] = {}
        for qualified, definition in definitions.items():
            if definition.kind == "method":
                method_candidates.setdefault(definition.local_name, []).append(qualified)
        call_locator_counts: dict[str, int] = {}

        for call in (node for node in ast.walk(module.tree) if isinstance(node, ast.Call)):
            owner = self._owner_function(call, parent, function_defs)
            if isinstance(call.func, ast.Name) and call.func.id == "exec":
                statement = self._statement(call, parent)
                locator = self._next_occurrence_locator(
                    self._relation_locator(
                        "unsupported_construct", statement, owner or module.name, None
                    ),
                    call_locator_counts,
                )
                result.append(
                    self._relation(
                        source_unit, module, "unsupported_construct",
                        locator,
                        owner or module.name, None, statement,
                        ResolutionStatus.UNSUPPORTED, ResolutionMethod.HEURISTIC, (),
                        "Dynamic exec cannot be normalized as static repository facts.",
                        definitions,
                        evidence_node=self._call_evidence_node(call, statement),
                    )
                )
                continue
            if isinstance(call.func, ast.Name) and call.func.id == "__import__":
                statement = self._statement(call, parent)
                locator = self._next_occurrence_locator(
                    self._relation_locator("import", statement, owner or module.name, None),
                    call_locator_counts,
                )
                result.append(
                    self._relation(
                        source_unit, module, "import",
                        locator,
                        owner or module.name, None, statement,
                        ResolutionStatus.UNSUPPORTED, ResolutionMethod.HEURISTIC, (),
                        "Dynamic import target is not statically known.", definitions,
                        evidence_node=self._call_evidence_node(call, statement),
                    )
                )
                continue
            if owner is None:
                continue
            relation = self._call_relation(
                source_unit, module, call, owner, parent, bindings,
                definitions, method_candidates, call_locator_counts
            )
            if relation is not None:
                result.append(relation)
        return result

    def _import_relations(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        node: ast.Import | ast.ImportFrom,
        module_by_name: Mapping[str, _ModuleInfo],
        definitions: Mapping[str, _Definition],
        source_ref: EntityRef,
    ) -> list[Relation]:
        bindings = self._import_bindings(module.path, ast.Module(body=[node], type_ignores=[]))
        relations: list[Relation] = []
        for binding in bindings:
            if binding.wildcard:
                candidates = tuple(
                    definition.qualified_name
                    for definition in module_by_name.get(
                        binding.module,
                        _ModuleInfo("", "", "", ast.Module(body=[], type_ignores=[]), (), ()),
                    ).definitions
                    if "." not in definition.qualified_name[len(binding.module) + 1 :]
                )
                locator = self._relation_locator("import", node, module.name, binding.module)
                relations.append(
                    self._relation(
                        source_unit, module, "import", locator, module.name,
                        binding.module, node, ResolutionStatus.AMBIGUOUS,
                        ResolutionMethod.HEURISTIC, candidates,
                        "Wildcard import exposes multiple possible bindings.", definitions,
                    )
                )
                continue
            internal = binding.target in definitions or binding.module in module_by_name
            status = ResolutionStatus.RESOLVED if internal else ResolutionStatus.EXTERNAL
            subject = f"{module.name}.{binding.local_name}" if binding.aliased else module.name
            locator = self._relation_locator("import", node, subject, binding.target)
            relations.append(
                self._relation(
                    source_unit, module, "import", locator, subject, binding.target, node,
                    status, ResolutionMethod.EXACT, (binding.target,),
                    "Static import target is lexically exact.", definitions,
                )
            )
        return relations

    def _inheritance_relations(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        node: ast.ClassDef,
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
    ) -> list[Relation]:
        subject = f"{module.name}.{node.name}"
        result: list[Relation] = []
        for base in node.bases:
            name = self._expr_name(base)
            binding = bindings.get(name)
            target = binding.target if binding is not None else f"{module.name}.{name}"
            external = target not in definitions
            status = (
                ResolutionStatus.RESOLVED
                if target == "typing.Protocol" or not external
                else ResolutionStatus.EXTERNAL
            )
            kind = "type" if target == "typing.Protocol" else "inherits"
            locator = self._relation_locator(kind, node, subject, target)
            result.append(
                self._relation(
                    source_unit, module, kind, locator, subject, target, node, status,
                    ResolutionMethod.EXACT, (target,),
                    "Inheritance target follows an exact lexical import.", definitions,
                )
            )
        return result

    def _export_relations(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        node: ast.Assign,
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
        source_ref: EntityRef,
    ) -> list[Relation]:
        if isinstance(node.value, (ast.List, ast.Tuple)) and all(
            isinstance(item, ast.Constant) and isinstance(item.value, str)
            for item in node.value.elts
        ):
            result: list[Relation] = []
            for item in node.value.elts:
                assert isinstance(item, ast.Constant) and isinstance(item.value, str)
                name = item.value
                target = bindings[name].target if name in bindings else f"{module.name}.{name}"
                locator = self._relation_locator("export", node, module.name, target)
                result.append(
                    self._relation(
                        source_unit, module, "export", locator, module.name, target, node,
                        ResolutionStatus.RESOLVED, ResolutionMethod.EXACT, (target,),
                        "Explicit __all__ names an exact exported binding.", definitions,
                    )
                )
            return result
        locator = self._relation_locator("export", node, module.name, None)
        return [
            self._relation(
                source_unit, module, "export", locator, module.name, None,
                node, ResolutionStatus.AMBIGUOUS, ResolutionMethod.HEURISTIC, (),
                "Computed __all__ cannot be enumerated statically.", definitions,
            )
        ]

    def _call_relation(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        call: ast.Call,
        owner: str,
        parent: Mapping[ast.AST, ast.AST],
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
        method_candidates: Mapping[str, list[str]],
        locator_counts: dict[str, int],
    ) -> Relation | None:
        target: str | None
        candidates: tuple[str, ...]
        if isinstance(call.func, ast.Name):
            name = call.func.id
            if name in bindings:
                target = bindings[name].target
                status = ResolutionStatus.RESOLVED
                method = ResolutionMethod.EXACT
                candidates = (target,)
            elif f"{module.name}.{name}" in definitions:
                target = f"{module.name}.{name}"
                status = ResolutionStatus.RESOLVED
                method = ResolutionMethod.EXACT
                candidates = (target,)
            elif name in _BUILTINS:
                target = f"builtins.{name}"
                status = ResolutionStatus.EXTERNAL
                method = ResolutionMethod.EXACT
                candidates = (target,)
            else:
                target = None
                status = ResolutionStatus.UNRESOLVED
                method = ResolutionMethod.SEARCH_FALLBACK
                candidates = ()
            statement = self._statement(call, parent)
            locator = self._next_occurrence_locator(
                self._relation_locator("call", statement, owner, target), locator_counts
            )
        elif isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            receiver = call.func.value.id
            attribute = call.func.attr
            annotation = self._parameter_annotation(owner, receiver, definitions)
            if annotation is not None:
                binding = bindings.get(annotation)
                base = binding.target if binding is not None else f"{module.name}.{annotation}"
                target = f"{base}.{attribute}"
                candidates = (target, *tuple(
                    item for item in sorted(method_candidates.get(attribute, ()))
                    if item != target and self._is_subclass_method(item, base, definitions, bindings)
                ))
                status = ResolutionStatus.RESOLVED
                method = ResolutionMethod.DATAFLOW
            else:
                target = None
                candidates = tuple(sorted(method_candidates.get(attribute, ())))
                status = ResolutionStatus.AMBIGUOUS
                method = ResolutionMethod.HEURISTIC
            statement = self._statement(call, parent)
            locator = self._next_occurrence_locator(
                self._relation_locator("call", statement, owner, target), locator_counts
            )
        else:
            return None
        reason = {
            ResolutionStatus.RESOLVED: "Lexical or annotation-bounded evidence resolves this call.",
            ResolutionStatus.EXTERNAL: "Built-in call is external to repository symbols.",
            ResolutionStatus.AMBIGUOUS: "Receiver evidence leaves multiple method candidates.",
            ResolutionStatus.UNRESOLVED: "No definition or import establishes a target.",
        }[status]
        return self._relation(
            source_unit, module, "call", locator, owner, target,
            statement, status, method, candidates, reason, definitions,
            evidence_node=self._call_evidence_node(call, statement),
        )

    def _relation(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        kind: str,
        locator: str,
        subject: str,
        target: str | None,
        node: ast.AST,
        status: ResolutionStatus,
        method: ResolutionMethod,
        candidates: tuple[str, ...],
        reason: str,
        definitions: Mapping[str, _Definition],
        *,
        evidence_node: ast.AST | None = None,
    ) -> Relation:
        source_ref = self._entity_ref(subject, source_unit, definitions, locator, "source")
        target_ref = (
            self._entity_ref(target, source_unit, definitions, locator, "target")
            if target is not None
            else None
        )
        candidate_refs = tuple(
            self._entity_ref(candidate, source_unit, definitions, locator, "candidate")
            for candidate in candidates
        )
        evidence = (
            self._node_span(source_unit, evidence_node)
            if evidence_node is not None
            else self._line_span(source_unit, module.source, node)
        )
        return Relation(
            id=deterministic_entity_id(
                source_unit.source_revision_id, source_unit.path,
                EntityKind.RELATION, locator
            ),
            source_revision_id=source_unit.source_revision_id,
            path=source_unit.path,
            kind=kind,
            locator=locator,
            source=source_ref,
            target=target_ref,
            evidence=(evidence,),
            resolution_status=status,
            resolution_method=method,
            confidence={
                ResolutionStatus.RESOLVED: 1.0,
                ResolutionStatus.EXTERNAL: 1.0,
                ResolutionStatus.AMBIGUOUS: 0.5,
                ResolutionStatus.UNRESOLVED: 0.0,
                ResolutionStatus.UNSUPPORTED: 0.0,
            }[status],
            reason=reason,
            candidates=candidate_refs,
        )

    def _entity_ref(
        self,
        qualified_name: str | None,
        source_unit: SourceUnit,
        definitions: Mapping[str, _Definition],
        relation_locator: str,
        role: str,
    ) -> EntityRef:
        definition = definitions.get(qualified_name or "")
        if definition is not None:
            return EntityRef(
                kind=EntityKind.SYMBOL,
                id=deterministic_entity_id(
                    source_unit.source_revision_id, definition.path,
                    EntityKind.SYMBOL, definition.locator
                ),
            )
        if qualified_name and qualified_name == self._module_name(source_unit.path):
            return EntityRef(kind=EntityKind.SOURCE_UNIT, id=source_unit.id)
        locator = (
            f"reference:{qualified_name}"
            if qualified_name is not None
            else f"{role}:{relation_locator}:none"
        )
        return EntityRef(
            kind=EntityKind.SYMBOL,
            id=deterministic_entity_id(
                source_unit.source_revision_id, source_unit.path,
                EntityKind.SYMBOL, locator
            ),
        )

    def _symbol(
        self, source_unit: SourceUnit, source: str, definition: _Definition
    ) -> Symbol:
        span = self._line_span(source_unit, source, definition.node)
        return Symbol(
            id=deterministic_entity_id(
                source_unit.source_revision_id, definition.path,
                EntityKind.SYMBOL, definition.locator
            ),
            source_revision_id=source_unit.source_revision_id,
            source_unit_id=source_unit.id,
            path=definition.path,
            kind=definition.kind,
            qualified_name=definition.qualified_name,
            local_name=definition.local_name,
            definition_locator=definition.locator,
            definition=span,
            language="python",
            language_attributes={
                "async": isinstance(definition.node, ast.AsyncFunctionDef),
                "lexical_qualified_name": definition.lexical_qualified_name,
                "lexical_kind": definition.lexical_kind,
                "definition_start_line": min(
                    [decorator.lineno for decorator in definition.node.decorator_list]
                    + [definition.node.lineno]
                ),
                "definition_start_column": definition.node.col_offset,
                "definition_end_line": definition.node.end_lineno or definition.node.lineno,
                "definition_end_column": (
                    definition.node.end_col_offset
                    if definition.node.end_col_offset is not None
                    else definition.node.col_offset
                ),
            },
        )

    def _read_source(self, path: str) -> str | TypedFailure:
        if path in self._source_overrides:
            return self._source_overrides[path]
        candidate = (self._root / path).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError:
            return TypedFailure(
                code=FailureCode.INVALID_INPUT,
                message=f"source unit escapes adapter root: {path}",
                backend_id="python_adapter",
                language="python",
            )
        try:
            return candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return TypedFailure(
                code=FailureCode.SOURCE_UNAVAILABLE,
                message=f"cannot read {path}: {exc}",
                backend_id="python_adapter",
                language="python",
            )

    @staticmethod
    def _failure(
        artifact: SyntaxArtifact,
        code: FailureCode,
        message: str,
        *,
        details: tuple[str, ...] = (),
    ) -> TypedFailure:
        return TypedFailure(
            code=code,
            message=message,
            backend_id=artifact.backend_id,
            language=artifact.language,
            details=details,
        )

    @staticmethod
    def _module_name(path: str) -> str:
        parts = Path(path).with_suffix("").parts
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    @classmethod
    def _absolute_import_module(cls, path: str, node: ast.ImportFrom) -> str:
        if not node.level:
            return node.module or ""
        package = cls._module_name(path).split(".")[:-1]
        up = node.level - 1
        if up:
            package = package[:-up] if up <= len(package) else []
        return ".".join((*package, *((node.module or "").split(".")))).strip(".")

    @staticmethod
    def _definition_locator(kind: str, qualified: str, node: ast.AST) -> str:
        return f"python:{kind}:{qualified}:{node.lineno}:{node.col_offset}"

    @staticmethod
    def _expr_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = PythonLanguageAdapter._expr_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ast.dump(node, include_attributes=False)

    @staticmethod
    def _statement(
        node: ast.AST, parent: Mapping[ast.AST, ast.AST]
    ) -> ast.AST:
        current = node
        while current in parent and not isinstance(current, ast.stmt):
            current = parent[current]
        return current

    @staticmethod
    def _owner_function(
        node: ast.AST,
        parent: Mapping[ast.AST, ast.AST],
        definitions: Mapping[ast.AST, _Definition],
    ) -> str | None:
        current = node
        while current in parent:
            current = parent[current]
            definition = definitions.get(current)
            if definition is not None:
                return definition.qualified_name
        return None

    @staticmethod
    def _parameter_annotation(
        owner: str,
        parameter: str,
        definitions: Mapping[str, _Definition],
    ) -> str | None:
        definition = definitions.get(owner)
        if definition is None or not isinstance(
            definition.node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            return None
        for argument in (*definition.node.args.posonlyargs, *definition.node.args.args):
            if argument.arg == parameter and argument.annotation is not None:
                return PythonLanguageAdapter._expr_name(argument.annotation)
        return None

    @staticmethod
    def _is_subclass_method(
        method: str,
        base: str,
        definitions: Mapping[str, _Definition],
        bindings: Mapping[str, _ImportBinding],
    ) -> bool:
        class_name = method.rsplit(".", 1)[0]
        class_def = definitions.get(class_name)
        if class_def is None or not isinstance(class_def.node, ast.ClassDef):
            return False
        for item in class_def.node.bases:
            name = PythonLanguageAdapter._expr_name(item)
            resolved = bindings[name].target if name in bindings else f"{class_name.rsplit('.', 1)[0]}.{name}"
            if resolved == base:
                return True
        return False

    @staticmethod
    def _line_span(source_unit: SourceUnit, source: str, node: ast.AST) -> EvidenceSpan:
        line = node.lineno
        raw_line = source.splitlines()[line - 1]
        return EvidenceSpan(
            source_unit_id=source_unit.id,
            path=source_unit.path,
            start_line=line,
            start_column=0,
            end_line=line,
            end_column=len(raw_line.encode("utf-8")),
        )

    @staticmethod
    def _node_span(source_unit: SourceUnit, node: ast.AST) -> EvidenceSpan:
        return EvidenceSpan(
            source_unit_id=source_unit.id,
            path=source_unit.path,
            start_line=node.lineno,
            start_column=node.col_offset,
            end_line=node.end_lineno or node.lineno,
            end_column=node.end_col_offset or node.col_offset,
        )

    @staticmethod
    def _call_evidence_node(call: ast.Call, statement: ast.AST) -> ast.AST | None:
        if (
            call.lineno == statement.lineno
            and call.end_lineno == statement.end_lineno == statement.lineno
        ):
            return None
        return call

    @staticmethod
    def _next_occurrence_locator(base: str, counts: dict[str, int]) -> str:
        occurrence = counts.get(base, 0) + 1
        counts[base] = occurrence
        return base if occurrence == 1 else f"{base}:occurrence:{occurrence}"

    @staticmethod
    def _relation_locator(
        kind: str,
        node: ast.AST,
        subject: str,
        target: str | None,
    ) -> str:
        return (
            f"python:{kind}:{node.lineno}:{node.col_offset}:"
            f"{subject}:{target or '?'}"
        )


PythonAdapter = PythonLanguageAdapter
__all__ = ["PythonAdapter", "PythonLanguageAdapter"]
