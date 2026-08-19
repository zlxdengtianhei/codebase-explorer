"""Truthful Python ``ast`` normalization into canonical ``cbe-ir/3`` models."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from src.ir import (
    Availability,
    CallOutcome,
    CallResolution,
    CallSiteAnchor,
    CallSiteInventory,
    CapabilityCell,
    EntityKind,
    EntityRef,
    EvidenceSpan,
    ExternalEcosystem,
    ExternalTargetEvidence,
    Provenance,
    ProvenanceBasis,
    ReceiverGap,
    ReceiverGapReason,
    ReceiverShape,
    Relation,
    RepositoryEntityIdentity,
    ResolutionMethod,
    ResolutionStatus,
    SemanticTier,
    SourceUnit,
    SourceUnitState,
    Symbol,
    TargetEvidence,
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
    owner_class: str | None = None
    decorator_names: tuple[str, ...] = ()
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
        parent = self._parent_map(current.tree)
        function_defs = {
            definition.node: definition
            for definition in current.definitions
            if definition.kind in {"function", "method"}
        }
        call_site_inventory = self._call_site_inventory(
            source_unit, current, parent, function_defs
        )
        relations = self._relations(source_unit, current, modules, definitions)
        return FileIR(
            source_unit=source_unit,
            symbols=symbols,
            relations=tuple(sorted(relations, key=lambda item: item.id)),
            call_site_inventory=call_site_inventory,
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
        imports = tuple(self._import_bindings(path, tree))
        decorator_bindings = {binding.local_name: binding for binding in imports}

        def walk(
            node: ast.AST,
            scope: tuple[str, ...] = (),
            enclosing_kind: str | None = None,
            enclosing_class: str | None = None,
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
                            owner_class=enclosing_class,
                            decorator_names=self._canonical_decorator_names(
                                child.decorator_list, decorator_bindings
                            ),
                        )
                    )
                    walk(child, (*scope, child.name), "function", enclosing_class)
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
                            owner_class=None,
                            decorator_names=self._canonical_decorator_names(
                                child.decorator_list, decorator_bindings
                            ),
                        )
                    )
                    walk(child, (*scope, child.name), "class", qualified)
                else:
                    # Match ast-based independent enumeration: definitions in
                    # control-flow blocks remain visible without changing scope.
                    walk(child, scope, enclosing_kind, enclosing_class)

        walk(tree)
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

    @staticmethod
    def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
        parent: dict[ast.AST, ast.AST] = {}
        for candidate in ast.walk(tree):
            for child in ast.iter_child_nodes(candidate):
                parent[child] = candidate
        return parent

    @staticmethod
    def _span_key(span: EvidenceSpan) -> tuple[int, int, int, int, str]:
        return (
            span.start_line,
            span.start_column,
            span.end_line,
            span.end_column,
            span.source_unit_id,
        )

    @classmethod
    def _caller_canonical_id(
        cls, path: str, module_name: str, owner: str | None
    ) -> str:
        if owner is None:
            return f"{path}::<module>"
        prefix = f"{module_name}." if module_name else ""
        lexical = owner[len(prefix) :] if prefix and owner.startswith(prefix) else owner
        return f"{path}::{lexical}"

    @staticmethod
    def _call_locator(span: EvidenceSpan, caller_id: str) -> str:
        return (
            f"python:call:{span.start_line}:{span.start_column}:"
            f"{span.end_line}:{span.end_column}:{caller_id}"
        )

    def _call_site_inventory(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        parent: Mapping[ast.AST, ast.AST],
        function_defs: Mapping[ast.AST, _Definition],
    ) -> CallSiteInventory:
        anchors: list[CallSiteAnchor] = []
        for call in (node for node in ast.walk(module.tree) if isinstance(node, ast.Call)):
            span = self._node_span(source_unit, call)
            owner = self._owner_function(call, parent, function_defs)
            caller_id = self._caller_canonical_id(module.path, module.name, owner)
            locator = self._call_locator(span, caller_id)
            call_id = deterministic_entity_id(
                source_unit.source_revision_id,
                source_unit.path,
                EntityKind.RELATION,
                locator,
            )
            anchors.append(
                CallSiteAnchor(
                    call_site_id=call_id,
                    caller_canonical_id=caller_id,
                    span=span,
                )
            )
        anchors.sort(key=lambda item: (*self._span_key(item.span), item.call_site_id))
        return CallSiteInventory(
            source_revision_id=source_unit.source_revision_id,
            source_unit_id=source_unit.id,
            path=source_unit.path,
            language="python",
            ast_backend_id=source_unit.backend_id,
            ast_backend_version=source_unit.backend_version,
            call_sites=tuple(anchors),
        )

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

        parent = self._parent_map(module.tree)
        function_defs = {
            definition.node: definition
            for definition in module.definitions
            if definition.kind in {"function", "method"}
        }
        method_candidates: dict[str, list[str]] = {}
        for qualified, definition in definitions.items():
            if definition.kind == "method":
                method_candidates.setdefault(definition.local_name, []).append(qualified)
        for call in (node for node in ast.walk(module.tree) if isinstance(node, ast.Call)):
            owner = self._owner_function(call, parent, function_defs)
            relation = self._call_relation(
                source_unit, module, call, owner, parent, bindings,
                definitions, method_candidates, modules
            )
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
        owner: str | None,
        parent: Mapping[ast.AST, ast.AST],
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
        method_candidates: Mapping[str, list[str]],
        modules: Mapping[str, _ModuleInfo],
    ) -> Relation:
        span = self._node_span(source_unit, call)
        caller_id = self._caller_canonical_id(module.path, module.name, owner)
        locator = self._call_locator(span, caller_id)
        module_by_name = {item.name: item for item in modules.values()}
        resolution, status, method, reason = self._classify_call(
            source_unit,
            module,
            call,
            owner,
            bindings,
            definitions,
            method_candidates,
            module_by_name,
            modules,
        )
        return self._relation(
            source_unit,
            module,
            "call",
            locator,
            owner or module.name,
            None,
            call,
            status,
            method,
            (),
            reason,
            definitions,
            evidence_node=call,
            call_resolution=resolution,
        )

    @staticmethod
    def _function_local_bindings(definition: _Definition) -> set[str]:
        """Return names bound by one function body, excluding nested scopes."""

        node = definition.node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return set()
        bound: set[str] = {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }
        if node.args.vararg is not None:
            bound.add(node.args.vararg.arg)
        if node.args.kwarg is not None:
            bound.add(node.args.kwarg.arg)
        assigned: set[str] = set()
        imported: set[str] = set()
        global_names: set[str] = set()
        nonlocal_names: set[str] = set()

        def visit(current: ast.AST) -> None:
            for child in ast.iter_child_nodes(current):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    # A nested definition is handled as a direct lexical
                    # binding by _direct_local_binding; its body is another
                    # scope and cannot contribute assignments here.
                    continue
                if isinstance(child, ast.Global):
                    global_names.update(child.names)
                    continue
                if isinstance(child, ast.Nonlocal):
                    nonlocal_names.update(child.names)
                    continue
                if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
                    assigned.add(child.id)
                elif isinstance(child, ast.alias):
                    imported.add(child.asname or child.name.split(".", 1)[0])
                elif isinstance(child, ast.ExceptHandler) and child.name:
                    imported.add(child.name)
                visit(child)

        for statement in node.body:
            visit(statement)
        return (bound | assigned | imported | nonlocal_names) - global_names

    @classmethod
    def _direct_local_binding(
        cls,
        name: str,
        owner: str | None,
        definitions: Mapping[str, _Definition],
    ) -> tuple[str | None, bool]:
        """Resolve only a unique direct local definition, never a closure.

        The old resolver searched module definitions before accounting for
        Python's lexical bindings.  A parameter or assignment therefore
        promoted an unrelated same-name module symbol to ``runtime_exact``.
        This helper makes such scopes visible gaps while accepting one direct
        nested function/class definition.  Enclosing function bindings are
        deliberately treated as unresolved closure state.
        """

        if owner is None:
            return None, False

        def scope_state(scope: str) -> tuple[set[str], tuple[str, ...]]:
            definition = definitions.get(scope)
            if definition is None or definition.kind not in {"function", "method"}:
                return set(), ()
            prefix = f"{scope}."
            direct = tuple(
                sorted(
                    qualified
                    for qualified, candidate in definitions.items()
                    if qualified.startswith(prefix)
                    and "." not in qualified[len(prefix) :]
                    and candidate.local_name == name
                )
            )
            return cls._function_local_bindings(definition), direct

        local_names, direct_definitions = scope_state(owner)
        if name in local_names:
            return None, True
        if len(direct_definitions) == 1:
            return direct_definitions[0], False
        if direct_definitions:
            return None, True

        # A binding in an enclosing function is a closure.  No target identity
        # is proven by this bounded resolver, even when a single definition is
        # visible there; the caller must remain a visible non-exact gap.
        ancestor = owner
        while "." in ancestor:
            ancestor = ancestor.rsplit(".", 1)[0]
            definition = definitions.get(ancestor)
            if definition is None or definition.kind not in {"function", "method"}:
                continue
            ancestor_names, ancestor_direct = scope_state(ancestor)
            if name in ancestor_names or ancestor_direct:
                return None, True
        return None, False

    def _classify_call(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        call: ast.Call,
        owner: str | None,
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
        method_candidates: Mapping[str, list[str]],
        module_by_name: Mapping[str, _ModuleInfo],
        modules: Mapping[str, _ModuleInfo],
    ) -> tuple[CallResolution, ResolutionStatus, ResolutionMethod, str]:
        call_span = self._node_span(source_unit, call)

        def gap(reason: ReceiverGapReason, shape: ReceiverShape, text: str) -> tuple[CallResolution, ResolutionStatus, ResolutionMethod, str]:
            return (
                CallResolution(
                    outcome=CallOutcome.UNRESOLVED_OR_DEEP,
                    receiver_shape=shape,
                    unresolved_or_deep_receiver=ReceiverGap(
                        reason=reason,
                        receiver_text=text,
                        evidence=(call_span,),
                    ),
                ),
                ResolutionStatus.UNRESOLVED,
                ResolutionMethod.HEURISTIC,
                f"Static resolution gap: {reason.value}.",
            )

        if isinstance(call.func, ast.Name):
            name = call.func.id
            if name == "exec":
                return gap(ReceiverGapReason.EXEC, ReceiverShape.BARE_NAME, name)
            if name == "__import__":
                return gap(ReceiverGapReason.DYNAMIC_IMPORT, ReceiverShape.BARE_NAME, name)
            if name == "getattr":
                return gap(ReceiverGapReason.DYNAMIC_ATTRIBUTE, ReceiverShape.DYNAMIC_ATTRIBUTE, name)
            target_name, shadowed = self._direct_local_binding(name, owner, definitions)
            if shadowed:
                return gap(ReceiverGapReason.UNKNOWN_NAME, ReceiverShape.BARE_NAME, name)
            basis = ProvenanceBasis.DIRECT_LOCAL_BINDING
            if target_name is not None:
                pass
            elif name in bindings:
                target_name = bindings[name].target
                basis = ProvenanceBasis.IMPORT_BINDING
            elif f"{module.name}.{name}" in definitions:
                target_name = f"{module.name}.{name}"
            elif name in _BUILTINS:
                external = self._external_target(
                    source_unit,
                    ExternalEcosystem.PYTHON_BUILTIN,
                    f"builtins.{name}",
                    call_span,
                )
                return (
                    CallResolution(
                        outcome=CallOutcome.EXTERNAL,
                        receiver_shape=ReceiverShape.BARE_NAME,
                        external_target=external,
                    ),
                    ResolutionStatus.EXTERNAL,
                    ResolutionMethod.EXACT,
                    "Built-in call is external to repository symbols.",
                )
            else:
                return gap(ReceiverGapReason.UNKNOWN_NAME, ReceiverShape.BARE_NAME, name)
            definition = definitions.get(target_name or "")
            if definition is None:
                external = self._external_target(
                    source_unit,
                    ExternalEcosystem.PYTHON_MODULE,
                    target_name or name,
                    call_span,
                )
                return (
                    CallResolution(
                        outcome=CallOutcome.EXTERNAL,
                        receiver_shape=ReceiverShape.BARE_NAME,
                        external_target=external,
                    ),
                    ResolutionStatus.EXTERNAL,
                    ResolutionMethod.EXACT,
                    "Imported target is outside the repository symbol index.",
                )
            if self._unsupported_decorator(definition):
                return gap(
                    ReceiverGapReason.DECORATED_CALLABLE,
                    ReceiverShape.BARE_NAME,
                    name,
                )
            target = self._target_evidence(
                source_unit,
                definition,
                basis,
                modules,
            )
            return (
                CallResolution(
                    outcome=CallOutcome.RUNTIME_EXACT,
                    receiver_shape=ReceiverShape.BARE_NAME,
                    runtime_exact_target=target,
                ),
                ResolutionStatus.RESOLVED,
                ResolutionMethod.EXACT,
                "A single repository binding proves the runtime target.",
            )

        if isinstance(call.func, ast.Attribute):
            attribute = call.func.attr
            receiver = call.func.value
            if isinstance(receiver, ast.Name):
                receiver_name = receiver.id
                if receiver_name in {"self", "cls"}:
                    owner_definition = definitions.get(owner or "")
                    base = owner_definition.owner_class if owner_definition else None
                    if base is None:
                        return gap(
                            ReceiverGapReason.UNTYPED_RECEIVER,
                            ReceiverShape.SELF if receiver_name == "self" else ReceiverShape.CLS,
                            receiver_name,
                        )
                    return self._virtual_call(
                        source_unit,
                        module,
                        base,
                        attribute,
                        ReceiverShape.SELF if receiver_name == "self" else ReceiverShape.CLS,
                        definitions,
                        method_candidates,
                        module_by_name,
                        modules,
                        call_span,
                        final_owner=owner,
                    )
                annotation, unsupported_union = self._parameter_annotation_info(
                    owner, receiver_name, definitions
                )
                if unsupported_union:
                    return gap(
                        ReceiverGapReason.UNSUPPORTED_UNION_RECEIVER,
                        ReceiverShape.ANNOTATED_NAME,
                        receiver_name,
                    )
                if annotation is not None:
                    base = self._resolve_class_name(
                        annotation, module, bindings, definitions, module_by_name
                    )
                    if base is None:
                        return gap(
                            ReceiverGapReason.AMBIGUOUS_MRO,
                            ReceiverShape.ANNOTATED_NAME,
                            receiver_name,
                        )
                    return self._virtual_call(
                        source_unit,
                        module,
                        base,
                        attribute,
                        ReceiverShape.ANNOTATED_NAME,
                        definitions,
                        method_candidates,
                        module_by_name,
                        modules,
                        call_span,
                    )
                binding = bindings.get(receiver_name)
                if binding is not None and binding.target in module_by_name:
                    target_name = f"{binding.target}.{attribute}"
                    definition = definitions.get(target_name)
                    if definition is not None and not self._unsupported_decorator(definition):
                        return (
                            CallResolution(
                                outcome=CallOutcome.RUNTIME_EXACT,
                                receiver_shape=ReceiverShape.MODULE_ATTRIBUTE,
                                runtime_exact_target=self._target_evidence(
                                    source_unit,
                                    definition,
                                    ProvenanceBasis.MODULE_BINDING,
                                    modules,
                                ),
                            ),
                            ResolutionStatus.RESOLVED,
                            ResolutionMethod.EXACT,
                            "A module alias and one repository member prove the target.",
                        )
                    if definition is not None:
                        return gap(
                            ReceiverGapReason.DECORATED_CALLABLE,
                            ReceiverShape.MODULE_ATTRIBUTE,
                            f"{receiver_name}.{attribute}",
                        )
                if binding is not None and binding.target not in definitions:
                    return (
                        CallResolution(
                            outcome=CallOutcome.EXTERNAL,
                            receiver_shape=ReceiverShape.MODULE_ATTRIBUTE,
                            external_target=self._external_target(
                                source_unit,
                                ExternalEcosystem.PYTHON_MODULE,
                                f"{binding.target}.{attribute}",
                                call_span,
                            ),
                        ),
                        ResolutionStatus.EXTERNAL,
                        ResolutionMethod.EXACT,
                        "Module attribute is external to the repository index.",
                    )
                return gap(
                    ReceiverGapReason.UNTYPED_RECEIVER,
                    ReceiverShape.OTHER,
                    f"{receiver_name}.{attribute}",
                )
            if isinstance(receiver, ast.Attribute):
                return gap(
                    ReceiverGapReason.ATTRIBUTE_CHAIN,
                    ReceiverShape.ATTRIBUTE_CHAIN,
                    self._expr_name(receiver),
                )
            if isinstance(receiver, ast.Call):
                return gap(
                    ReceiverGapReason.FACTORY_RESULT,
                    ReceiverShape.CALL_RESULT,
                    ast.get_source_segment(module.source, receiver) or "call()",
                )
            if isinstance(receiver, ast.Subscript):
                return gap(
                    ReceiverGapReason.SUBSCRIPT_RECEIVER,
                    ReceiverShape.SUBSCRIPT,
                    ast.get_source_segment(module.source, receiver) or "subscript",
                )
            return gap(
                ReceiverGapReason.UNSUPPORTED_SYNTAX,
                ReceiverShape.OTHER,
                ast.get_source_segment(module.source, receiver) or "receiver",
            )

        if isinstance(call.func, ast.Call):
            if (
                isinstance(call.func.func, ast.Name)
                and call.func.func.id == "getattr"
            ):
                return gap(
                    ReceiverGapReason.DYNAMIC_ATTRIBUTE,
                    ReceiverShape.DYNAMIC_ATTRIBUTE,
                    ast.get_source_segment(module.source, call.func) or "getattr()",
                )
            return gap(
                ReceiverGapReason.FACTORY_RESULT,
                ReceiverShape.CALL_RESULT,
                ast.get_source_segment(module.source, call.func) or "call()",
            )
        if isinstance(call.func, ast.Subscript):
            return gap(
                ReceiverGapReason.SUBSCRIPT_RECEIVER,
                ReceiverShape.SUBSCRIPT,
                ast.get_source_segment(module.source, call.func) or "subscript",
            )
        return gap(
            ReceiverGapReason.UNSUPPORTED_SYNTAX,
            ReceiverShape.OTHER,
            ast.get_source_segment(module.source, call.func) or "callable",
        )

    def _virtual_call(
        self,
        source_unit: SourceUnit,
        module: _ModuleInfo,
        base: str,
        attribute: str,
        receiver_shape: ReceiverShape,
        definitions: Mapping[str, _Definition],
        method_candidates: Mapping[str, list[str]],
        module_by_name: Mapping[str, _ModuleInfo],
        modules: Mapping[str, _ModuleInfo],
        call_span: EvidenceSpan,
        *,
        final_owner: str | None = None,
    ) -> tuple[CallResolution, ResolutionStatus, ResolutionMethod, str]:
        mro = self._c3_mro(base, definitions, module_by_name, modules)
        if mro is None:
            return self._gap_result(
                source_unit,
                call_span,
                ReceiverGapReason.AMBIGUOUS_MRO,
                receiver_shape,
                base,
            )
        lexical_definition = next(
            (
                definitions.get(f"{class_name}.{attribute}")
                for class_name in mro
                if definitions.get(f"{class_name}.{attribute}") is not None
            ),
            None,
        )
        if lexical_definition is None:
            return self._gap_result(
                source_unit,
                call_span,
                ReceiverGapReason.MISSING_LEXICAL_MEMBER,
                receiver_shape,
                f"{base}.{attribute}",
            )
        if self._unsupported_decorator(lexical_definition):
            return self._gap_result(
                source_unit,
                call_span,
                ReceiverGapReason.DECORATED_CALLABLE,
                receiver_shape,
                f"{base}.{attribute}",
            )
        exact = (
            self._is_final_class(base, definitions)
            or self._is_final_definition(lexical_definition)
            or (
                final_owner is not None
                and self._is_final_class(final_owner, definitions)
            )
        )
        lexical_basis = (
            ProvenanceBasis.FINAL_CLASS_OR_METHOD
            if exact
            else (
                ProvenanceBasis.ENCLOSING_CLASS
                if receiver_shape in {ReceiverShape.SELF, ReceiverShape.CLS}
                else ProvenanceBasis.RECEIVER_ANNOTATION
            )
        )
        lexical = self._target_evidence(
            source_unit,
            lexical_definition,
            lexical_basis,
            modules,
        )
        overrides: list[TargetEvidence] = []
        for candidate in sorted(method_candidates.get(attribute, ())):
            candidate_definition = definitions.get(candidate)
            if candidate_definition is None or candidate_definition is lexical_definition:
                continue
            candidate_class = candidate.rsplit(".", 1)[0]
            candidate_mro = self._c3_mro(candidate_class, definitions, module_by_name, modules)
            if candidate_mro is None or base not in candidate_mro:
                continue
            if self._unsupported_decorator(candidate_definition):
                continue
            overrides.append(
                self._target_evidence(
                    source_unit,
                    candidate_definition,
                    ProvenanceBasis.CLASS_HIERARCHY,
                    modules,
                )
            )
        if exact:
            return (
                CallResolution(
                    outcome=CallOutcome.RUNTIME_EXACT,
                    receiver_shape=receiver_shape,
                    runtime_exact_target=lexical,
                ),
                ResolutionStatus.RESOLVED,
                ResolutionMethod.EXACT,
                "Final class or method evidence closes virtual dispatch.",
            )
        overrides.sort(key=lambda item: self._target_key(item))
        return (
            CallResolution(
                outcome=CallOutcome.VIRTUAL_DISPATCH,
                receiver_shape=receiver_shape,
                lexical_base_target=lexical,
                override_candidates=tuple(overrides),
            ),
            ResolutionStatus.AMBIGUOUS,
            ResolutionMethod.DATAFLOW,
            "Receiver evidence identifies a lexical base but leaves virtual dispatch open.",
        )

    def _gap_result(
        self,
        source_unit: SourceUnit,
        span: EvidenceSpan,
        reason: ReceiverGapReason,
        shape: ReceiverShape,
        text: str,
    ) -> tuple[CallResolution, ResolutionStatus, ResolutionMethod, str]:
        return (
            CallResolution(
                outcome=CallOutcome.UNRESOLVED_OR_DEEP,
                receiver_shape=shape,
                unresolved_or_deep_receiver=ReceiverGap(
                    reason=reason,
                    receiver_text=text,
                    evidence=(span,),
                ),
            ),
            ResolutionStatus.UNRESOLVED,
            ResolutionMethod.HEURISTIC,
            f"Static resolution gap: {reason.value}.",
        )

    @staticmethod
    def _target_key(target: Any) -> tuple[Any, ...]:
        identity = target.target
        return (
            identity.ref.id,
            identity.source_revision_id,
            identity.path,
            identity.definition_locator,
            tuple(
                (
                    provenance.basis.value,
                    provenance.source_revision_id,
                    tuple(
                        (
                            span.path,
                            span.start_line,
                            span.start_column,
                            span.end_line,
                            span.end_column,
                            span.source_unit_id,
                        )
                        for span in provenance.evidence
                    ),
                )
                for provenance in target.provenance
            ),
        )

    def _target_evidence(
        self,
        source_unit: SourceUnit,
        definition: _Definition,
        basis: ProvenanceBasis,
        modules: Mapping[str, _ModuleInfo],
    ) -> TargetEvidence:
        target = self._repository_identity(source_unit.source_revision_id, definition)
        definition_span = self._definition_evidence(source_unit.source_revision_id, definition)
        provenance = Provenance(
            basis=basis,
            evidence=(definition_span,),
            source_revision_id=source_unit.source_revision_id,
            source_entity=target,
        )
        return TargetEvidence(target=target, provenance=(provenance,))

    @staticmethod
    def _repository_identity(source_revision_id: str, definition: _Definition) -> RepositoryEntityIdentity:
        ref = EntityRef(
            kind=EntityKind.SYMBOL,
            id=deterministic_entity_id(
                source_revision_id,
                definition.path,
                EntityKind.SYMBOL,
                definition.locator,
            ),
        )
        return RepositoryEntityIdentity(
            ref=ref,
            source_revision_id=source_revision_id,
            path=definition.path,
            definition_locator=definition.locator,
        )

    @staticmethod
    def _definition_evidence(source_revision_id: str, definition: _Definition) -> EvidenceSpan:
        node = definition.node
        return EvidenceSpan(
            source_unit_id=deterministic_entity_id(
                source_revision_id,
                definition.path,
                EntityKind.SOURCE_UNIT,
                definition.path,
            ),
            path=definition.path,
            start_line=min(
                [decorator.lineno for decorator in getattr(node, "decorator_list", ())]
                + [node.lineno]
            ),
            start_column=node.col_offset,
            end_line=getattr(node, "end_lineno", None) or node.lineno,
            end_column=getattr(node, "end_col_offset", None) or node.col_offset,
        )

    def _external_target(
        self,
        source_unit: SourceUnit,
        ecosystem: ExternalEcosystem,
        qualified_name: str,
        call_span: EvidenceSpan,
    ) -> ExternalTargetEvidence:
        from src.ir.models import _external_identity

        normalized = ".".join(part.strip() for part in qualified_name.strip().split("."))
        external_id = _external_identity(ecosystem, normalized, None)
        return ExternalTargetEvidence(
            external_id=external_id,
            ecosystem=ecosystem,
            qualified_name=normalized,
            distribution=None,
            provenance=(
                Provenance(
                    basis=ProvenanceBasis.DIRECT_LOCAL_BINDING,
                    evidence=(call_span,),
                    source_revision_id=source_unit.source_revision_id,
                ),
            ),
        )

    @classmethod
    def _canonical_decorator_name(
        cls, node: ast.AST, bindings: Mapping[str, _ImportBinding]
    ) -> str:
        callable_head = node.func if isinstance(node, ast.Call) else node
        raw = cls._expr_name(callable_head)
        head, separator, tail = raw.partition(".")
        binding = bindings.get(head)
        if binding is None:
            return raw
        return f"{binding.target}.{tail}" if separator else binding.target

    @classmethod
    def _canonical_decorator_names(
        cls,
        nodes: tuple[ast.expr, ...] | list[ast.expr],
        bindings: Mapping[str, _ImportBinding],
    ) -> tuple[str, ...]:
        return tuple(
            sorted({cls._canonical_decorator_name(node, bindings) for node in nodes})
        )

    @classmethod
    def _definition_decorators(cls, definition: _Definition) -> tuple[str, ...]:
        if definition.decorator_names:
            return definition.decorator_names
        return cls._canonical_decorator_names(
            tuple(getattr(definition.node, "decorator_list", ())), {}
        )

    @staticmethod
    def _decorator_name(node: ast.AST) -> str:
        return PythonLanguageAdapter._expr_name(node)

    @classmethod
    def _unsupported_decorator(cls, definition: _Definition) -> bool:
        allowed = {
            "staticmethod",
            "classmethod",
            "final",
            "typing.final",
            "typing_extensions.final",
        }
        decorators = cls._definition_decorators(definition)
        return any(item not in allowed for item in decorators)

    @classmethod
    def _is_final_definition(cls, definition: _Definition) -> bool:
        final_names = {"final", "typing.final", "typing_extensions.final"}
        decorators = cls._definition_decorators(definition)
        return any(item in final_names for item in decorators)

    @classmethod
    def _is_final_class(cls, class_name: str, definitions: Mapping[str, _Definition]) -> bool:
        definition = definitions.get(class_name)
        return definition is not None and cls._is_final_definition(definition)

    def _resolve_class_name(
        self,
        annotation: str,
        module: _ModuleInfo,
        bindings: Mapping[str, _ImportBinding],
        definitions: Mapping[str, _Definition],
        module_by_name: Mapping[str, _ModuleInfo],
    ) -> str | None:
        binding = bindings.get(annotation)
        candidate = binding.target if binding is not None else (
            annotation if annotation in definitions else f"{module.name}.{annotation}"
        )
        if candidate in definitions and definitions[candidate].kind == "class":
            return candidate
        if candidate in module_by_name:
            return candidate
        return None

    def _class_direct_bases(
        self,
        class_name: str,
        definitions: Mapping[str, _Definition],
        module_by_name: Mapping[str, _ModuleInfo],
    ) -> tuple[str, ...] | None:
        definition = definitions.get(class_name)
        if definition is None or not isinstance(definition.node, ast.ClassDef):
            return None
        module = next((item for item in module_by_name.values() if item.path == definition.path), None)
        if module is None:
            return None
        bindings = {binding.local_name: binding for binding in module.imports}
        bases: list[str] = []
        for base_node in definition.node.bases:
            name = self._expr_name(base_node)
            binding = bindings.get(name)
            candidate = binding.target if binding is not None else (
                name if name in definitions else f"{module.name}.{name}"
            )
            if candidate not in definitions or definitions[candidate].kind != "class":
                return None
            bases.append(candidate)
        return tuple(bases)

    def _c3_mro(
        self,
        class_name: str,
        definitions: Mapping[str, _Definition],
        module_by_name: Mapping[str, _ModuleInfo],
        modules: Mapping[str, _ModuleInfo],
        _memo: dict[str, tuple[str, ...] | None] | None = None,
        _stack: tuple[str, ...] = (),
    ) -> tuple[str, ...] | None:
        memo = _memo if _memo is not None else {}
        if class_name in memo:
            return memo[class_name]
        if class_name in _stack:
            memo[class_name] = None
            return None
        direct = self._class_direct_bases(class_name, definitions, module_by_name)
        if direct is None:
            memo[class_name] = None
            return None
        if not direct:
            memo[class_name] = (class_name,)
            return memo[class_name]
        sequences: list[list[str]] = []
        for base in direct:
            base_mro = self._c3_mro(base, definitions, module_by_name, modules, memo, (*_stack, class_name))
            if base_mro is None:
                memo[class_name] = None
                return None
            sequences.append(list(base_mro))
        sequences.append(list(direct))
        result = [class_name]
        while any(sequences):
            candidate = next(
                (
                    sequence[0]
                    for sequence in sequences
                    if sequence
                    and all(sequence[0] not in other[1:] for other in sequences if other)
                ),
                None,
            )
            if candidate is None:
                memo[class_name] = None
                return None
            result.append(candidate)
            for sequence in sequences:
                if sequence and sequence[0] == candidate:
                    sequence.pop(0)
        memo[class_name] = tuple(result)
        return memo[class_name]

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
        call_resolution: CallResolution | None = None,
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
            call_resolution=call_resolution,
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
            decorators=definition.decorator_names,
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
        owner: str | None,
        parameter: str,
        definitions: Mapping[str, _Definition],
    ) -> str | None:
        annotation, unsupported_union = PythonLanguageAdapter._parameter_annotation_info(
            owner, parameter, definitions
        )
        return None if unsupported_union else annotation

    @staticmethod
    def _annotation_expression(annotation: ast.AST) -> ast.AST | None:
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            try:
                expression = ast.parse(annotation.value.strip(), mode="eval").body
            except (SyntaxError, ValueError):
                return None
            return expression if isinstance(expression, ast.AST) else None
        return annotation

    @classmethod
    def _annotation_arm_names(cls, annotation: ast.AST) -> list[str]:
        expression = cls._annotation_expression(annotation)
        if expression is None:
            return []
        if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
            return [
                *cls._annotation_arm_names(expression.left),
                *cls._annotation_arm_names(expression.right),
            ]
        if isinstance(expression, ast.Tuple):
            names: list[str] = []
            for item in expression.elts:
                names.extend(cls._annotation_arm_names(item))
            return names
        if isinstance(expression, ast.Constant) and expression.value is None:
            return ["None"]
        if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
            return [expression.value]
        return [cls._expr_name(expression)]

    @staticmethod
    def _parameter_annotation_info(
        owner: str | None,
        parameter: str,
        definitions: Mapping[str, _Definition],
    ) -> tuple[str | None, bool]:
        if owner is None:
            return None, False
        definition = definitions.get(owner)
        if definition is None or not isinstance(
            definition.node, (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            return None, False
        arguments = [
            *definition.node.args.posonlyargs,
            *definition.node.args.args,
            *definition.node.args.kwonlyargs,
        ]
        if definition.node.args.vararg is not None:
            arguments.append(definition.node.args.vararg)
        if definition.node.args.kwarg is not None:
            arguments.append(definition.node.args.kwarg)
        for argument in arguments:
            if argument.arg == parameter and argument.annotation is not None:
                annotation = argument.annotation
                expression = PythonLanguageAdapter._annotation_expression(annotation)
                if expression is None:
                    return None, True
                if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
                    names = PythonLanguageAdapter._annotation_arm_names(expression)
                    non_none = [
                        item
                        for item in names
                        if item not in {"None", "NoneType", "types.NoneType"}
                    ]
                    return (non_none[0], False) if len(non_none) == 1 else (None, True)
                if isinstance(expression, ast.Subscript) and PythonLanguageAdapter._expr_name(
                    expression.value
                ) in {"Optional", "typing.Optional"}:
                    names = PythonLanguageAdapter._annotation_arm_names(expression.slice)
                    non_none = [
                        item
                        for item in names
                        if item not in {"None", "NoneType", "types.NoneType"}
                    ]
                    return (non_none[0], False) if len(non_none) == 1 else (None, True)
                return PythonLanguageAdapter._expr_name(expression), False
        return None, False

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
