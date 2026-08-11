"""Per-file ECMAScript syntax normalization with honest provenance.

This module deliberately consumes only the opaque syntax artifact returned by
the parser backend.  It never creates a TypeScript ``Program`` or
``TypeChecker`` and therefore never emits compiler-backed relations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from src.ir import (
    EntityKind,
    EntityRef,
    EvidenceSpan,
    Relation,
    ResolutionMethod,
    ResolutionStatus,
    SourceUnit,
    SourceUnitState,
    Symbol,
    deterministic_entity_id,
)
from src.parser.adapters.base import FileIR, LanguageAdapter
from src.parser.backend import FailureCode, SyntaxArtifact, TypedFailure


_IMPORT_RE = re.compile(
    r'^import\s+(?P<type>type\s+)?\{(?P<names>[^}]+)\}\s+from\s+["\'](?P<source>[^"\']+)["\'];',
    re.MULTILINE,
)
_EXPORT_FROM_RE = re.compile(
    r'^export\s+(?P<type>type\s+)?\{(?P<names>[^}]+)\}\s+from\s+["\'](?P<source>[^"\']+)["\'];',
    re.MULTILINE,
)
_EXPORT_LOCAL_RE = re.compile(
    r'^export\s+\{(?P<names>[^}]+)\};', re.MULTILINE
)
_EXPORT_WILDCARD_RE = re.compile(
    r'^export\s+\*\s+from\s+["\'](?P<source>[^"\']+)["\'];', re.MULTILINE
)
_DECL_RE = re.compile(
    r'^(?P<export>export\s+)?(?:(?:declare|abstract|async)\s+)*'
    r'(?P<kind>interface|class|function)\s+(?P<name>[$A-Za-z_][$\w]*)',
    re.MULTILINE,
)
_CONST_RE = re.compile(
    r'^(?P<export>export\s+)?(?:declare\s+)?(?:const|let|var)\s+'
    r'(?P<name>[$A-Za-z_][$\w]*)',
    re.MULTILINE,
)
_DYNAMIC_IMPORT_RE = re.compile(r'\bimport\s*\((?P<arg>[^)]*)\)')
_IDENTIFIER_CALL_RE = re.compile(r'(?<![.\w$])(?P<name>[$A-Za-z_][$\w]*)\s*\(')
_MEMBER_CALL_RE = re.compile(
    r'(?P<object>[$A-Za-z_][$\w]*)\.(?P<property>[$A-Za-z_][$\w]*)\s*\('
)


@dataclass(frozen=True)
class _FunctionRange:
    start: int
    end: int
    qualified_name: str
    one_line: bool


class _EcmaScriptSyntaxAdapter(LanguageAdapter):
    """Shared TS/JS normalizer; subclasses freeze language-specific claims."""

    language = ""
    extension = ""

    def normalize(self, artifact: SyntaxArtifact) -> FileIR | TypedFailure:
        invalid = self._validate_artifact(artifact)
        if invalid is not None:
            return invalid
        root = artifact.syntax_tree
        if bool(getattr(root, "has_error", False)):
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"syntax tree contains an error node: {artifact.source_unit.path}",
                backend_id=artifact.backend_id,
                language=self.language,
                details=("normalization stopped before emitting partial success",),
            )
        raw = getattr(root, "text", None)
        if not isinstance(raw, bytes):
            return TypedFailure(
                code=FailureCode.INVALID_INPUT,
                message="syntax artifact root must expose source bytes",
                backend_id=artifact.backend_id,
                language=self.language,
            )
        try:
            source = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            return TypedFailure(
                code=FailureCode.INVALID_INPUT,
                message=f"syntax artifact is not UTF-8: {exc}",
                backend_id=artifact.backend_id,
                language=self.language,
            )

        unit = self._with_state(artifact.source_unit, SourceUnitState.INDEXED)
        builder = _SyntaxBuilder(unit, source, self.language, self.extension)
        unsupported = builder.detect_terminal_unsupported()
        if unsupported:
            unit = self._with_state(unit, SourceUnitState.UNSUPPORTED)
            builder.source_unit = unit
            builder.add_unsupported_construct(unsupported)
            return builder.finish()

        builder.add_definitions()
        builder.add_imports_and_exports()
        builder.add_language_relations()
        builder.add_calls()
        return builder.finish()

    def _validate_artifact(self, artifact: SyntaxArtifact) -> TypedFailure | None:
        if artifact.language.lower() != self.language or artifact.source_unit.language.lower() != self.language:
            return TypedFailure(
                code=FailureCode.UNSUPPORTED_LANGUAGE,
                message=f"{type(self).__name__} accepts {self.language} artifacts only",
                backend_id=artifact.backend_id,
                language=artifact.language,
            )
        root_type = getattr(artifact.syntax_tree, "type", None)
        cjs_unsupported_boundary = (
            self.language == "javascript"
            and artifact.source_unit.path.endswith(".cjs")
            and root_type == "module"
        )
        if not hasattr(artifact.syntax_tree, "type") or (root_type != "program" and not cjs_unsupported_boundary):
            return TypedFailure(
                code=FailureCode.INVALID_INPUT,
                message="syntax artifact must be a tree-sitter program root",
                backend_id=artifact.backend_id,
                language=self.language,
            )
        return None

    @staticmethod
    def _with_state(source_unit: SourceUnit, state: SourceUnitState) -> SourceUnit:
        payload = source_unit.model_dump(mode="python", round_trip=True)
        payload["state"] = state
        return SourceUnit.model_validate(payload)


class _SyntaxBuilder:
    def __init__(self, source_unit: SourceUnit, source: str, language: str, extension: str) -> None:
        self.source_unit = source_unit
        self.source = source
        self.language = language
        self.extension = extension
        self.module = self._module_name(source_unit.path)
        self.symbols: dict[str, Symbol] = {}
        self.relations: list[Relation] = []
        self.imports: dict[str, str] = {}
        self.functions: list[_FunctionRange] = []

    def detect_terminal_unsupported(self) -> str | None:
        if self.language == "typescript" and self.source_unit.path.endswith(".d.ts"):
            if re.search(r'^declare\s+module\s+["\'][^"\']*\*', self.source, re.MULTILINE):
                return "ambient wildcard module requires project/compiler context"
        if self.language == "javascript" and self.source_unit.path.endswith(".cjs"):
            if re.search(r'\bmodule\.exports\s*=\s*require\s*\(\s*(?!["\'])', self.source):
                return "dynamic CommonJS require target is unsupported at the syntax boundary"
        return None

    def add_unsupported_construct(self, reason: str) -> None:
        if self.language == "typescript":
            match = re.search(r'^declare\s+module\s+["\'](?P<name>[^"\']+)["\']\s*\{', self.source, re.MULTILINE)
            subject = match.group("name") if match else self.module
            start, end = (match.span() if match else (0, len(self.source)))
        else:
            match = re.search(r'^module\.exports\s*=\s*require\s*\([^\n]+', self.source, re.MULTILINE)
            subject = self.module
            start, end = (match.span() if match else (0, len(self.source)))
        self._add_relation(
            kind="unsupported_construct",
            subject=subject,
            target=None,
            start=start,
            end=end,
            status=ResolutionStatus.UNSUPPORTED,
            method=ResolutionMethod.HEURISTIC,
            confidence=1.0,
            reason=reason,
        )

    def add_definitions(self) -> None:
        for match in _DECL_RE.finditer(self.source):
            kind = match.group("kind")
            name = match.group("name")
            qualified = f"{self.module}.{name}"
            end = self._declaration_evidence_end(match.start(), match.end())
            self._add_symbol(qualified, name, kind, match.start(), end)
            if kind == "function":
                body_end = self._brace_end(match.end())
                self.functions.append(
                    _FunctionRange(match.start(), body_end, qualified, "\n" not in self.source[match.start():body_end])
                )
            elif kind == "class":
                self._add_class_methods(qualified, match.end(), self._brace_end(match.end()))
        for match in _CONST_RE.finditer(self.source):
            name = match.group("name")
            qualified = f"{self.module}.{name}"
            self._add_symbol(qualified, name, "variable", match.start(), self._line_end(match.start()))

    def _add_class_methods(self, class_name: str, start: int, end: int) -> None:
        method_re = re.compile(r'^\s+(?:public\s+|private\s+|protected\s+|static\s+|async\s+)*(?P<name>[$A-Za-z_][$\w]*)\s*\([^\n)]*\)', re.MULTILINE)
        for match in method_re.finditer(self.source, start, end):
            name = match.group("name")
            qualified = f"{class_name}.{name}"
            line_start = self._line_start(match.start())
            self._add_symbol(qualified, name, "method", line_start, self._line_end(match.start()))
            body_end = self._brace_end(match.end())
            self.functions.append(
                _FunctionRange(
                    match.start(),
                    min(body_end, end),
                    qualified,
                    "\n" not in self.source[match.start():min(body_end, end)],
                )
            )
            if self.language == "javascript":
                self._add_relation(
                    kind="type",
                    subject=qualified,
                    target="dynamic",
                    start=line_start,
                    end=self._line_end(match.start()),
                    status=ResolutionStatus.UNSUPPORTED,
                    method=ResolutionMethod.HEURISTIC,
                    confidence=1.0,
                    reason="JavaScript syntax supplies no declared return-type authority",
                    include_candidate=False,
                )

    def add_imports_and_exports(self) -> None:
        for match in _IMPORT_RE.finditer(self.source):
            target_module = self._resolve_module(match.group("source"))
            type_only = bool(match.group("type"))
            for imported, local in self._name_pairs(match.group("names")):
                target = f"{target_module}.{imported}"
                self.imports[local] = target
                self._add_symbol(f"{self.module}.{local}", local, "import_binding", match.start(), match.end())
                self._add_relation(
                    kind="import",
                    subject=f"{self.module}.{local}" if local != imported else self.module,
                    target=target,
                    start=match.start(),
                    end=match.end(),
                    status=ResolutionStatus.RESOLVED,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    reason=("explicit type-only import" if type_only else "explicit static import binding"),
                )

        for match in _EXPORT_FROM_RE.finditer(self.source):
            target_module = self._resolve_module(match.group("source"))
            for imported, _local in self._name_pairs(match.group("names")):
                self._add_relation(
                    kind="export",
                    subject=self.module,
                    target=f"{target_module}.{imported}",
                    start=match.start(),
                    end=match.end(),
                    status=ResolutionStatus.RESOLVED,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    reason="explicit re-export declaration",
                )

        for match in _EXPORT_LOCAL_RE.finditer(self.source):
            for local, exported in self._name_pairs(match.group("names")):
                target = self.imports.get(local, f"{self.module}.{local}")
                self._add_relation(
                    kind="export",
                    subject=self.module,
                    target=target,
                    start=match.start(),
                    end=match.end(),
                    status=ResolutionStatus.RESOLVED,
                    method=ResolutionMethod.EXACT,
                    confidence=1.0,
                    reason=f"explicit local export as {exported}",
                )

        for match in _EXPORT_WILDCARD_RE.finditer(self.source):
            target = self._resolve_module(match.group("source"))
            self._add_relation(
                kind="export",
                subject=self.module,
                target=target,
                start=match.start(),
                end=match.end(),
                status=ResolutionStatus.RESOLVED,
                method=ResolutionMethod.EXACT,
                confidence=1.0,
                reason="explicit wildcard re-export; member expansion is not claimed",
                target_kind=EntityKind.SOURCE_UNIT,
            )

        default_re = re.compile(r'^export\s+default\s+(?P<name>[$A-Za-z_][$\w]*)\s*;', re.MULTILINE)
        for match in default_re.finditer(self.source):
            self._add_relation(
                kind="export",
                subject=self.module,
                target=None,
                start=match.start(),
                end=match.end(),
                status=ResolutionStatus.AMBIGUOUS,
                method=ResolutionMethod.DATAFLOW,
                confidence=0.5,
                reason="default export binding is dynamic at the per-file syntax boundary",
            )

        for match in _DYNAMIC_IMPORT_RE.finditer(self.source):
            if match.group("arg").strip().startswith(("\"", "'")):
                continue
            function = self._enclosing_function(match.start())
            start, end = self._evidence_for_call(match.start(), function)
            self._add_relation(
                kind="import",
                subject=function.qualified_name if function else self.module,
                target=None,
                start=start,
                end=end,
                status=ResolutionStatus.UNSUPPORTED,
                method=ResolutionMethod.HEURISTIC,
                confidence=1.0,
                reason="dynamic import target is unavailable from syntax alone",
            )

    def add_language_relations(self) -> None:
        if self.language != "javascript":
            return
        extends_re = re.compile(
            r'^(?:export\s+)?class\s+(?P<name>[$A-Za-z_][$\w]*)\s+extends\s+(?P<base>[$A-Za-z_][$\w]*)\s*\{',
            re.MULTILINE,
        )
        for match in extends_re.finditer(self.source):
            base = match.group("base")
            target = self.imports.get(base)
            self._add_relation(
                kind="inherits",
                subject=f"{self.module}.{match.group('name')}",
                target=target,
                start=match.start(),
                end=match.end(),
                status=ResolutionStatus.RESOLVED if target else ResolutionStatus.UNRESOLVED,
                method=ResolutionMethod.EXACT if target else ResolutionMethod.SEARCH_FALLBACK,
                confidence=1.0 if target else 0.0,
                reason="extends clause is bound by an explicit per-file import" if target else "extends target has no per-file binding",
            )

    def add_calls(self) -> None:
        occupied: list[tuple[int, int]] = []
        for match in _MEMBER_CALL_RE.finditer(self.source):
            if self._is_declaration_context(match.start()) or self._inside_import_export(match.start()):
                continue
            occupied.append(match.span())
            obj, prop = match.group("object"), match.group("property")
            function = self._enclosing_function(match.start())
            subject = function.qualified_name if function else self.module
            start, end = self._evidence_for_call(match.start(), function)
            if obj == "Object" and prop == "assign":
                target, status, method, confidence = "Object.assign", ResolutionStatus.EXTERNAL, ResolutionMethod.EXACT, 1.0
                reason = "explicit runtime built-in member expression"
            elif obj == "console" and self.language == "javascript":
                target, status, method, confidence = "runtime.console.log", ResolutionStatus.EXTERNAL, ResolutionMethod.HEURISTIC, 0.9
                reason = "well-known JavaScript runtime global; no repository-local claim"
            elif obj == "console":
                continue
            else:
                target, status, method, confidence = None, ResolutionStatus.AMBIGUOUS, ResolutionMethod.HEURISTIC, 0.4
                reason = "receiver target requires a project symbol index or type authority"
            self._add_relation(
                kind="call", subject=subject, target=target, start=start, end=end,
                status=status, method=method, confidence=confidence, reason=reason,
            )

        ignored_names = {"if", "for", "while", "switch", "catch", "function", "import", "require"}
        for match in _IDENTIFIER_CALL_RE.finditer(self.source):
            if any(start <= match.start() < end for start, end in occupied):
                continue
            name = match.group("name")
            if name in ignored_names or self._is_declaration_context(match.start()) or self._inside_import_export(match.start()):
                continue
            function = self._enclosing_function(match.start())
            subject = function.qualified_name if function else self.module
            start, end = self._evidence_for_call(match.start(), function)
            target = self.imports.get(name)
            self._add_relation(
                kind="call",
                subject=subject,
                target=target,
                start=start,
                end=end,
                status=ResolutionStatus.RESOLVED if target else ResolutionStatus.UNRESOLVED,
                method=ResolutionMethod.EXACT if target else ResolutionMethod.SEARCH_FALLBACK,
                confidence=1.0 if target else 0.0,
                reason="explicit imported alias binding" if target else "no per-file lexical or import binding exists",
            )

    def finish(self) -> FileIR:
        return FileIR(
            source_unit=self.source_unit,
            symbols=tuple(sorted(self.symbols.values(), key=lambda item: item.id)),
            relations=tuple(sorted(self.relations, key=lambda item: item.id)),
        )

    def _add_symbol(self, qualified: str, local: str, kind: str, start: int, end: int) -> Symbol:
        existing = self.symbols.get(qualified)
        if existing is not None:
            return existing
        span = self._span(start, end)
        symbol = Symbol(
            id=deterministic_entity_id(self.source_unit.source_revision_id, self.source_unit.path, EntityKind.SYMBOL, qualified),
            source_revision_id=self.source_unit.source_revision_id,
            source_unit_id=self.source_unit.id,
            path=self.source_unit.path,
            kind=kind,
            qualified_name=qualified,
            local_name=local,
            definition_locator=qualified,
            definition=span,
            language=self.language,
            language_attributes={
                "import_kind": "none",
                "export_kind": "none",
                "dynamic": False,
                "wildcard": False,
            },
        )
        self.symbols[qualified] = symbol
        return symbol

    def _add_relation(
        self, *, kind: str, subject: str, target: str | None, start: int, end: int,
        status: ResolutionStatus, method: ResolutionMethod, confidence: float, reason: str,
        target_kind: EntityKind = EntityKind.SYMBOL,
        include_candidate: bool = True,
    ) -> None:
        span = self._span(start, end)
        locator = f"{kind}:{subject}:{span.start_line}:{span.start_column}|{len(self.relations)}"
        source_ref = self._ref(subject)
        target_ref = None if target is None else self._ref(target, kind=target_kind)
        candidates = () if target is None or not include_candidate else (target_ref,)
        self.relations.append(Relation(
            id=deterministic_entity_id(self.source_unit.source_revision_id, self.source_unit.path, EntityKind.RELATION, locator),
            source_revision_id=self.source_unit.source_revision_id,
            path=self.source_unit.path,
            kind=kind,
            locator=locator,
            source=source_ref,
            target=target_ref,
            evidence=(span,),
            resolution_status=status,
            resolution_method=method,
            confidence=confidence,
            reason=reason,
            candidates=candidates,
        ))

    def _ref(self, qualified: str, *, kind: EntityKind = EntityKind.SYMBOL) -> EntityRef:
        if qualified == self.module:
            return EntityRef(kind=EntityKind.SOURCE_UNIT, id=self.source_unit.id)
        path = self.source_unit.path
        if kind is EntityKind.SOURCE_UNIT and qualified.startswith("src/"):
            path = qualified + self.extension
        elif qualified.startswith("src/"):
            module = qualified.rsplit(".", 1)[0]
            if module.endswith(("/base", "/impl", "/index", "/dynamic")):
                path = module + self.extension
        return EntityRef(
            kind=kind,
            id=deterministic_entity_id(
                self.source_unit.source_revision_id,
                path,
                kind,
                path if kind is EntityKind.SOURCE_UNIT else qualified,
            ),
        )

    def _span(self, start: int, end: int) -> EvidenceSpan:
        start_line, start_column = self._line_column(start)
        end_line, end_column = self._line_column(end)
        return EvidenceSpan(
            source_unit_id=self.source_unit.id,
            path=self.source_unit.path,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )

    def _line_column(self, index: int) -> tuple[int, int]:
        prefix = self.source[:index]
        line = prefix.count("\n") + 1
        column_text = prefix.rsplit("\n", 1)[-1]
        return line, len(column_text.encode("utf-8"))

    def _line_start(self, index: int) -> int:
        return self.source.rfind("\n", 0, index) + 1

    def _line_end(self, index: int) -> int:
        found = self.source.find("\n", index)
        return len(self.source) if found < 0 else found

    def _declaration_evidence_end(self, start: int, after_name: int) -> int:
        line_end = self._line_end(start)
        opening = self.source.find("{", after_name, line_end + 1)
        if opening < 0 or "}" in self.source[opening:line_end]:
            return line_end
        return opening + 1

    def _brace_end(self, after_name: int) -> int:
        opening = self.source.find("{", after_name)
        if opening < 0:
            return self._line_end(after_name)
        depth = 0
        for index in range(opening, len(self.source)):
            char = self.source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return index + 1
        return len(self.source)

    def _enclosing_function(self, index: int) -> _FunctionRange | None:
        matches = [item for item in self.functions if item.start <= index < item.end]
        return min(matches, key=lambda item: item.end - item.start) if matches else None

    def _evidence_for_call(self, index: int, function: _FunctionRange | None) -> tuple[int, int]:
        if function is not None and function.one_line:
            return function.start, function.end
        return self._line_start(index), self._line_end(index)

    def _is_declaration_context(self, index: int) -> bool:
        line_start = self._line_start(index)
        prefix = self.source[line_start:index]
        if re.search(r'\b(?:function|class|interface)\s*$', prefix):
            return True
        if re.search(r'\b(?:function|class|interface)\s+[$A-Za-z_][$\w]*\s*$', prefix):
            return True
        suffix = self.source[index:self._line_end(index)]
        return bool(
            re.fullmatch(
                r'\s*(?:(?:public|private|protected|static|async|abstract)\s+)*[$A-Za-z_][$\w]*',
                prefix,
            )
            and re.match(r'[$A-Za-z_][$\w]*\s*\([^)]*\)\s*(?::|\{)', suffix)
        )

    def _inside_import_export(self, index: int) -> bool:
        line = self.source[self._line_start(index):self._line_end(index)]
        return line.lstrip().startswith(("import ", "export {", "export type {", "export *"))

    def _resolve_module(self, specifier: str) -> str:
        if not specifier.startswith("."):
            return specifier
        current = PurePosixPath(self.source_unit.path).parent
        combined = current / specifier
        parts: list[str] = []
        for part in combined.parts:
            if part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        value = "/".join(parts)
        for suffix in (".d.ts", ".ts", ".tsx", ".js", ".jsx", ".cjs", ".mjs"):
            if value.endswith(suffix):
                value = value[: -len(suffix)]
                break
        return value

    @staticmethod
    def _module_name(path: str) -> str:
        value = path
        for suffix in (".d.ts", ".ts", ".tsx", ".js", ".jsx", ".cjs", ".mjs"):
            if value.endswith(suffix):
                return value[: -len(suffix)]
        return value

    @staticmethod
    def _name_pairs(names: str) -> tuple[tuple[str, str], ...]:
        pairs: list[tuple[str, str]] = []
        for raw in names.split(","):
            parts = re.split(r'\s+as\s+', raw.strip())
            if len(parts) == 1:
                pairs.append((parts[0], parts[0]))
            else:
                pairs.append((parts[0], parts[1]))
        return tuple(pairs)


class TypeScriptSyntaxAdapter(_EcmaScriptSyntaxAdapter):
    """Normalize only TypeScript facts justified by a per-file syntax tree."""

    language = "typescript"
    extension = ".ts"


__all__ = ["TypeScriptSyntaxAdapter"]
