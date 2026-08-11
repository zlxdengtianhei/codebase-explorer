"""Legacy snapshot compatibility boundary over the parser backend registry.

Provides immutable data structures and a unified interface for parsing
Python, TypeScript, and JavaScript codebases.

When graph-sitter is unavailable or incompatible, a lightweight fallback
parser based on Python's built-in ``ast`` module is selected explicitly.
The fallback supports Python files only and provides best-effort import
resolution, function/class extraction, and character counts.
"""
from __future__ import annotations

import ast
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.ir import EntityKind, SourceUnit, SourceUnitState, deterministic_entity_id
from src.parser.adapters.registry import (
    BackendRegistry,
    BackendSelection,
    default_backend_registry,
)
from src.parser.backend import (
    BackendHealth,
    FailureCode,
    PythonAstBackend,
    SyntaxArtifact,
    TypedFailure,
)
from src.parser.language_detect import detect_language, detect_languages, is_supported_language

if TYPE_CHECKING:
    from src.capabilities import CapabilityHandshake

logger = logging.getLogger(__name__)


# -- Error hierarchy --------------------------------------------------------

class GraphSitterError(Exception):
    """Base error for graph-sitter operations."""

class CodebaseParseError(GraphSitterError):
    """Raised when graph-sitter fails to parse the codebase."""

    def __init__(
        self,
        message: str,
        failures: tuple[TypedFailure, ...] = (),
        handshake: CapabilityHandshake | None = None,
    ) -> None:
        self.failures = failures
        self.handshake = handshake
        super().__init__(message)

class UnsupportedLanguageError(GraphSitterError):
    """Raised when an unsupported language is requested."""


class RequestedLanguageUnavailableError(CodebaseParseError):
    """Raised when an explicit language request cannot be fulfilled."""

    def __init__(
        self,
        failures: tuple[TypedFailure, ...],
        handshake: CapabilityHandshake,
    ) -> None:
        self.failures = failures
        self.handshake = handshake
        reasons = "; ".join(
            f"{failure.language} ({failure.code.value}: {failure.message})"
            for failure in failures
        )
        super().__init__(f"Requested languages unavailable: {reasons}", failures, handshake)


# -- Immutable data models --------------------------------------------------

@dataclass(frozen=True)
class FileInfo:
    """Immutable representation of a parsed source file."""
    filepath: str
    language: str
    line_count: int
    function_names: tuple[str, ...]
    class_names: tuple[str, ...]
    import_sources: tuple[str, ...]  # resolved import target paths
    char_count: int = 0

@dataclass(frozen=True)
class FunctionInfo:
    """Immutable representation of a parsed function."""
    name: str
    filepath: str
    start_line: int
    end_line: int
    parameters: tuple[str, ...]
    return_type: str | None
    calls: tuple[str, ...]        # callee function names
    dependencies: tuple[str, ...]  # dependency file paths

@dataclass(frozen=True)
class ClassInfo:
    """Immutable representation of a parsed class."""
    name: str
    filepath: str
    start_line: int
    end_line: int
    methods: tuple[str, ...]
    base_classes: tuple[str, ...]
    subclasses: tuple[str, ...]

@dataclass(frozen=True)
class CodebaseSnapshot:
    """Immutable snapshot of a fully parsed codebase."""
    root_path: str
    files: tuple[FileInfo, ...]
    functions: tuple[FunctionInfo, ...]
    classes: tuple[ClassInfo, ...]
    languages_detected: tuple[str, ...]
    total_lines: int
    requested_languages: tuple[str, ...] = ()
    successfully_parsed_languages: tuple[str, ...] = ()
    failures: tuple[TypedFailure, ...] = ()
    handshake: CapabilityHandshake | None = None


# -- Sentinel for AST fallback ----------------------------------------------

_USE_FALLBACK = object()
"""Test-only token that routes an injected initializer result to the registry."""

_EXCLUDED_DIRS = frozenset({
    ".venv", "venv", "node_modules", "__pycache__", ".git",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", ".eggs",
})
"""Directory names to exclude from file discovery during parsing."""


# -- Parser -----------------------------------------------------------------

class CodebaseParser:
    """Wraps graph-sitter Codebase API for code analysis."""

    def __init__(self, *, registry: BackendRegistry | None = None) -> None:
        self._registry = registry or default_backend_registry()

    def parse(self, path: str, languages: list[str] | None = None) -> CodebaseSnapshot:
        """Parse a codebase and return an immutable snapshot.

        Args:
            path: Absolute path to the codebase root directory.
            languages: Languages to analyse. Auto-detects when None.

        Raises:
            CodebaseParseError: If the path is invalid or parsing fails.
            UnsupportedLanguageError: If an unsupported language is requested.
        """
        root = Path(path).resolve()
        if not root.exists():
            raise CodebaseParseError(f"Path does not exist: {path}")
        if not root.is_dir():
            raise CodebaseParseError(f"Path is not a directory: {path}")

        profile = detect_languages(str(root))
        detected = tuple(sorted(profile.languages.keys()))
        if languages is None:
            if profile.primary_language == "unsupported":
                raise UnsupportedLanguageError(
                    f"No supported language files found in {root}"
                )
            resolved = list(detected)
        else:
            resolved = list(dict.fromkeys(self._resolve_languages(str(root), languages)))
        explicit_request = languages is not None
        requested = tuple(dict.fromkeys(resolved)) if explicit_request else ()
        all_files: list[FileInfo] = []
        all_funcs: list[FunctionInfo] = []
        all_cls: list[ClassInfo] = []
        total_lines = 0
        parsed: list[str] = []
        failures: list[TypedFailure] = []

        for lang in resolved:
            logger.info("Parsing %s files in %s", lang, root)
            selection = self._init_codebase(str(root), lang)
            if selection is _USE_FALLBACK:
                selection = self._registry.select_with_health(
                    lang, root=root, semantic_tier="heuristic"
                )
            if selection is None:
                failures.append(self._unavailable_failure(str(root), lang))
                continue
            if not isinstance(selection, BackendSelection):
                failures.append(TypedFailure(
                    code=FailureCode.BACKEND_ERROR,
                    message=f"registry returned an invalid selection for {lang}",
                    backend_id="none",
                    language=lang,
                ))
                continue
            files, funcs, classes, lines, language_failures = (
                self._parse_backend_language(root, lang, selection)
            )
            all_files.extend(files)
            all_funcs.extend(funcs)
            all_cls.extend(classes)
            total_lines += lines
            failures.extend(language_failures)
            if files and not language_failures:
                parsed.append(lang)

        from src.capabilities import build_capability_handshake

        failure_tuple = tuple(failures)
        handshake = build_capability_handshake(
            registry=self._registry,
            root=root,
            requested_languages=requested,
            detected_languages=detected,
            successfully_parsed_languages=tuple(parsed),
            failures=failure_tuple,
            receipt_id="runtime-unverified",
        )
        if explicit_request and failures:
            raise RequestedLanguageUnavailableError(failure_tuple, handshake)
        residual_codes = {
            FailureCode.BACKEND_UNAVAILABLE,
            FailureCode.INCOMPATIBLE_API,
            FailureCode.UNSUPPORTED_LANGUAGE,
        }
        if failures and (
            not parsed or any(failure.code not in residual_codes for failure in failures)
        ):
            raise CodebaseParseError(
                "; ".join(failure.message for failure in failures),
                failure_tuple,
                handshake,
            )

        return CodebaseSnapshot(
            root_path=str(root),
            files=tuple(all_files),
            functions=tuple(all_funcs),
            classes=tuple(all_cls),
            languages_detected=detected,
            total_lines=total_lines,
            requested_languages=requested,
            successfully_parsed_languages=tuple(parsed),
            failures=failure_tuple,
            handshake=handshake,
        )

    def get_file_content(self, filepath: str) -> str:
        """Read the content of a source file."""
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        return p.read_text(encoding="utf-8")

    # -- Private helpers ----------------------------------------------------

    def _resolve_languages(self, root: str, languages: list[str] | None) -> list[str]:
        if languages is not None:
            for lang in languages:
                if not is_supported_language(lang):
                    raise UnsupportedLanguageError(
                        f"Unsupported language: {lang}. "
                        f"Supported: python, typescript, javascript"
                    )
            return [lang.lower() for lang in languages]
        profile = detect_languages(root)
        if profile.primary_language == "unsupported":
            raise UnsupportedLanguageError(
                f"No supported language files found in {root}"
            )
        return list(profile.languages.keys())

    def _init_codebase(self, root: str, language: str) -> BackendSelection | None:
        """Select the project backend exclusively through the registry."""
        return self._registry.select_with_health(language, root=root)

    def _parse_backend_language(
        self,
        root: Path,
        language: str,
        selection: BackendSelection,
    ) -> tuple[
        list[FileInfo],
        list[FunctionInfo],
        list[ClassInfo],
        int,
        list[TypedFailure],
    ]:
        """Run the selected backend for every eligible source before conversion."""
        backend = selection.backend
        health = selection.health
        paths = self._eligible_source_paths(root, language)
        if not paths:
            return [], [], [], 0, [TypedFailure(
                code=FailureCode.SOURCE_UNAVAILABLE,
                message=f"no eligible {language} source files under {root}",
                backend_id=health.backend_id,
                language=language,
            )]

        units, failures = self._source_units(root, language, health, paths)
        artifacts: list[SyntaxArtifact] = []
        for unit in units:
            try:
                result = backend.parse(unit)
            except Exception as exc:  # backend contract boundary
                failures.append(TypedFailure(
                    code=FailureCode.BACKEND_ERROR,
                    message=(
                        f"{health.backend_id} raised while parsing "
                        f"{unit.path}: {exc}"
                    ),
                    backend_id=health.backend_id,
                    language=language,
                ))
                continue
            if isinstance(result, TypedFailure):
                failures.append(result)
            elif (
                isinstance(result, SyntaxArtifact)
                and result.source_unit == unit
                and result.language == unit.language
            ):
                artifacts.append(result)
            else:
                mismatch = (
                    isinstance(result, SyntaxArtifact)
                    and result.language != unit.language
                )
                failures.append(TypedFailure(
                    code=FailureCode.BACKEND_ERROR,
                    message=(
                        f"backend returned artifact/source language mismatch for {unit.path}"
                        if mismatch
                        else f"backend returned an invalid parse result for {unit.path}"
                    ),
                    backend_id=health.backend_id,
                    language=language,
                ))

        if isinstance(backend, PythonAstBackend):
            included = frozenset(artifact.source_unit.path for artifact in artifacts)
            files, funcs, classes, lines = self._fallback_parse_python(
                str(root), included_paths=included
            )
            return files, funcs, classes, lines, failures

        files: list[FileInfo] = []
        for artifact in artifacts:
            path = root / artifact.source_unit.path
            try:
                source = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                failures.append(TypedFailure(
                    code=FailureCode.SOURCE_UNAVAILABLE,
                    message=f"cannot convert {artifact.source_unit.path}: {exc}",
                    backend_id=artifact.backend_id,
                    language=language,
                ))
                continue
            files.append(FileInfo(
                filepath=artifact.source_unit.path,
                language=language,
                line_count=source.count("\n") + 1 if source else 0,
                function_names=(),
                class_names=(),
                import_sources=(),
                char_count=len(source),
            ))
        return files, [], [], sum(item.line_count for item in files), failures

    def _eligible_source_paths(self, root: Path, language: str) -> tuple[Path, ...]:
        return tuple(sorted(
            path
            for path in root.rglob("*")
            if path.is_file()
            and detect_language(str(path)) == language
            and not any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts)
        ))

    def _source_units(
        self,
        root: Path,
        language: str,
        health: BackendHealth,
        paths: tuple[Path, ...],
    ) -> tuple[list[SourceUnit], list[TypedFailure]]:
        readable: list[tuple[str, str]] = []
        failures: list[TypedFailure] = []
        for path in paths:
            relative = path.relative_to(root).as_posix()
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                failures.append(TypedFailure(
                    code=FailureCode.SOURCE_UNAVAILABLE,
                    message=f"cannot read {relative}: {exc}",
                    backend_id=health.backend_id,
                    language=language,
                ))
                continue
            readable.append((relative, hashlib.sha256(content.encode("utf-8")).hexdigest()))

        manifest = "\n".join(f"{path}:{digest}" for path, digest in readable)
        revision = "rev_" + hashlib.sha256(manifest.encode("utf-8")).hexdigest()
        units = [
            SourceUnit(
                id=deterministic_entity_id(revision, path, EntityKind.SOURCE_UNIT, path),
                source_revision_id=revision,
                path=path,
                language=language,
                content_hash=digest,
                state=SourceUnitState.DISCOVERED,
                backend_id=health.backend_id,
                backend_version=health.backend_version,
            )
            for path, digest in readable
        ]
        return units, failures

    def _unavailable_failure(self, root: str, language: str) -> TypedFailure:
        health = self._registry.health(root=root)
        incompatible = tuple(item for item in health if item.status == "incompatible")
        if incompatible:
            item = incompatible[0]
            return TypedFailure(
                code=FailureCode.INCOMPATIBLE_API,
                message=item.limitations[0],
                backend_id=item.backend_id,
                language=language,
                details=item.limitations,
            )
        errors = tuple(item for item in health if item.status == "error")
        if errors:
            item = errors[0]
            return TypedFailure(
                code=FailureCode.BACKEND_ERROR,
                message=item.limitations[0],
                backend_id=item.backend_id,
                language=language,
                details=item.limitations,
            )
        return TypedFailure(
            code=FailureCode.BACKEND_UNAVAILABLE,
            message=f"no healthy registered backend for {language}",
            backend_id="none",
            language=language,
            details=tuple(
                limitation
                for item in health
                for limitation in item.limitations
            ),
        )

    # -- AST fallback parser --------------------------------------------------

    def _fallback_parse_python(
        self,
        root: str,
        *,
        included_paths: frozenset[str] | None = None,
    ) -> tuple[list[FileInfo], list[FunctionInfo], list[ClassInfo], int]:
        """Parse Python files using the built-in ``ast`` module.

        Walks the directory tree under *root*, parses each ``.py`` file,
        and extracts file info, top-level functions, and classes.  Import
        resolution is best-effort: ``import foo`` resolves to ``foo.py``
        if that file exists under *root*.

        Returns:
            (files, functions, classes, total_lines) tuple.
        """
        root_path = Path(root).resolve()
        py_files = sorted(
            f for f in root_path.rglob("*.py")
            if not any(part in _EXCLUDED_DIRS for part in f.relative_to(root_path).parts)
            and (
                included_paths is None
                or f.relative_to(root_path).as_posix() in included_paths
            )
        )

        # Build a module-name → filepath lookup for import resolution
        module_map: dict[str, str] = {}
        for pf in py_files:
            rel = pf.relative_to(root_path)
            # "models.py" → "models", "pkg/utils.py" → "pkg.utils"
            module_name = str(rel.with_suffix("")).replace(os.sep, ".")
            # Store relative posix path as the canonical filepath
            module_map[module_name] = str(rel)

        files: list[FileInfo] = []
        funcs: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        total_lines = 0

        for pf in py_files:
            rel_path = str(pf.relative_to(root_path))
            try:
                source = pf.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                logger.warning("Failed to read %s; skipping", pf)
                continue

            line_count = source.count("\n") + 1 if source else 0
            char_count = len(source)

            try:
                tree = ast.parse(source, filename=str(pf))
            except SyntaxError:
                logger.warning("SyntaxError parsing %s; recording as empty", pf)
                files.append(FileInfo(
                    filepath=rel_path, language="python",
                    line_count=line_count, function_names=(),
                    class_names=(), import_sources=(),
                    char_count=char_count,
                ))
                total_lines += line_count
                continue

            func_names: list[str] = []
            class_names: list[str] = []
            import_sources: list[str] = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    func_names.append(node.name)
                    fi = self._ast_extract_function(node, rel_path, source)
                    if fi is not None:
                        funcs.append(fi)
                elif isinstance(node, ast.ClassDef):
                    class_names.append(node.name)
                    ci = self._ast_extract_class(node, rel_path)
                    if ci is not None:
                        classes.append(ci)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        resolved = module_map.get(alias.name)
                        if resolved is not None:
                            import_sources.append(resolved)
                elif isinstance(node, ast.ImportFrom):
                    abs_module = self._resolve_import_from(
                        node, rel_path, module_map,
                    )
                    if abs_module is not None:
                        import_sources.append(abs_module)

            # T-08: Detect dynamic imports (importlib.import_module / __import__)
            for dyn_node in ast.walk(tree):
                if not isinstance(dyn_node, ast.Call):
                    continue
                func = dyn_node.func
                # importlib.import_module("module.path")
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "import_module"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "importlib"
                ):
                    if (
                        dyn_node.args
                        and isinstance(dyn_node.args[0], ast.Constant)
                        and isinstance(dyn_node.args[0].value, str)
                    ):
                        resolved = module_map.get(dyn_node.args[0].value)
                        if resolved is not None:
                            import_sources.append(resolved)
                # __import__("module.path")
                elif isinstance(func, ast.Name) and func.id == "__import__":
                    if (
                        dyn_node.args
                        and isinstance(dyn_node.args[0], ast.Constant)
                        and isinstance(dyn_node.args[0].value, str)
                    ):
                        resolved = module_map.get(dyn_node.args[0].value)
                        if resolved is not None:
                            import_sources.append(resolved)

            files.append(FileInfo(
                filepath=rel_path, language="python",
                line_count=line_count,
                function_names=tuple(func_names),
                class_names=tuple(class_names),
                import_sources=tuple(dict.fromkeys(import_sources)),
                char_count=char_count,
            ))
            total_lines += line_count

        # T-06: Second pass — resolve function calls to file-level dependencies.
        # Build func_name → filepath mapping (skip ambiguous names).
        func_name_count: dict[str, int] = {}
        for fn in funcs:
            func_name_count[fn.name] = func_name_count.get(fn.name, 0) + 1

        func_name_to_file: dict[str, str] = {
            fn.name: fn.filepath
            for fn in funcs
            if func_name_count.get(fn.name, 0) == 1
        }

        # T-07: Also build class_name → filepath for inheritance edges.
        class_name_count: dict[str, int] = {}
        for ci in classes:
            class_name_count[ci.name] = class_name_count.get(ci.name, 0) + 1

        class_name_to_file: dict[str, str] = {
            ci.name: ci.filepath
            for ci in classes
            if class_name_count.get(ci.name, 0) == 1
        }

        # Resolve call targets to dependency file paths for each function.
        updated_funcs: list[FunctionInfo] = []
        for fn in funcs:
            dep_files: list[str] = []
            for call_name in fn.calls:
                target_file = func_name_to_file.get(call_name)
                if target_file and target_file != fn.filepath:
                    dep_files.append(target_file)
            updated_funcs.append(FunctionInfo(
                name=fn.name, filepath=fn.filepath,
                start_line=fn.start_line, end_line=fn.end_line,
                parameters=fn.parameters, return_type=fn.return_type,
                calls=fn.calls,
                dependencies=tuple(dict.fromkeys(dep_files)),
            ))
        funcs = updated_funcs

        # T-07: Enrich FileInfo.import_sources with inheritance-based edges.
        # For each class, if its base class resolves to a different file,
        # add that file as an import source (weighted_graph.py will create
        # inherit edges from ClassInfo.base_classes → class_name_to_file).
        # No FileInfo changes needed since weighted_graph.py already handles
        # inheritance via ClassInfo.base_classes + its own class_name_to_file.
        # The ClassInfo.base_classes are already correctly populated by
        # _ast_extract_class, so weighted_graph.py will produce weight=3 edges.

        logger.info(
            "AST fallback parsed %d Python files (%d lines) in %s",
            len(files), total_lines, root,
        )
        return files, funcs, classes, total_lines

    @staticmethod
    def _resolve_import_from(
        node: ast.ImportFrom,
        current_file: str,
        module_map: dict[str, str],
    ) -> str | None:
        """Resolve an ``ast.ImportFrom`` node to a file path.

        Handles both absolute imports (``from foo.bar import X``) and
        relative imports (``from .bar import X``, ``from ..baz import Y``).
        """
        level = node.level or 0
        module = node.module or ""

        if level == 0:
            # Absolute import: direct lookup
            return module_map.get(module)

        # Relative import: compute base package from current file path
        parts = current_file.replace(os.sep, "/").split("/")
        # Remove the filename to get the package directory parts
        pkg_parts = parts[:-1]

        # Go up (level - 1) directories (level=1 means current package)
        up = level - 1
        if up > len(pkg_parts):
            return None
        if up > 0:
            pkg_parts = pkg_parts[:-up]

        # Build the absolute module name
        if module:
            abs_parts = pkg_parts + module.split(".")
        else:
            abs_parts = pkg_parts

        abs_module = ".".join(abs_parts)

        # Try exact match, then __init__ for package imports
        resolved = module_map.get(abs_module)
        if resolved is not None:
            return resolved
        init_module = abs_module + ".__init__"
        return module_map.get(init_module)

    @staticmethod
    def _ast_extract_function(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        filepath: str,
        source: str,
    ) -> FunctionInfo | None:
        """Extract a FunctionInfo from an AST FunctionDef node.

        Extracts function calls from the body (``ast.Call`` nodes) to
        populate the ``calls`` field.  Only simple calls (``foo()`` and
        ``self.foo()``) are captured; chained attribute calls are skipped.
        """
        try:
            params = tuple(
                arg.arg for arg in node.args.args if arg.arg != "self"
            )
            rt = ast.get_source_segment(source, node.returns) if node.returns else None

            # T-06: Extract function call names from the body
            call_names: list[str] = []
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                if isinstance(func, ast.Name):
                    call_names.append(func.id)
                elif isinstance(func, ast.Attribute):
                    call_names.append(func.attr)

            return FunctionInfo(
                name=node.name, filepath=filepath,
                start_line=node.lineno, end_line=node.end_lineno or node.lineno,
                parameters=params, return_type=str(rt) if rt else None,
                calls=tuple(dict.fromkeys(call_names)),
                dependencies=(),  # filled in second pass
            )
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _ast_extract_class(
        node: ast.ClassDef, filepath: str,
    ) -> ClassInfo | None:
        """Extract a ClassInfo from an AST ClassDef node."""
        try:
            methods = tuple(
                n.name for n in node.body
                if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            )
            bases: list[str] = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            return ClassInfo(
                name=node.name, filepath=filepath,
                start_line=node.lineno, end_line=node.end_lineno or node.lineno,
                methods=methods, base_classes=tuple(bases),
                subclasses=(),
            )
        except Exception:  # noqa: BLE001
            return None

# -- Convenience function ---------------------------------------------------

def parse_project(path: str, languages: list[str] | None = None) -> CodebaseSnapshot:
    """Parse a project directory and return an immutable snapshot."""
    return CodebaseParser().parse(path, languages=languages)
