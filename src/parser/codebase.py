"""Codebase parsing layer wrapping graph-sitter (codegen) API.

Provides immutable data structures and a unified interface for parsing
Python, TypeScript, and JavaScript codebases.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from src.parser.language_detect import detect_languages, is_supported_language

logger = logging.getLogger(__name__)


# -- Error hierarchy --------------------------------------------------------

class GraphSitterError(Exception):
    """Base error for graph-sitter operations."""

class CodebaseParseError(GraphSitterError):
    """Raised when graph-sitter fails to parse the codebase."""

class UnsupportedLanguageError(GraphSitterError):
    """Raised when an unsupported language is requested."""


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


# -- Parser -----------------------------------------------------------------

class CodebaseParser:
    """Wraps graph-sitter Codebase API for code analysis."""

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

        resolved = self._resolve_languages(str(root), languages)
        all_files: list[FileInfo] = []
        all_funcs: list[FunctionInfo] = []
        all_cls: list[ClassInfo] = []
        total_lines = 0

        for lang in resolved:
            logger.info("Parsing %s files in %s", lang, root)
            codebase = self._init_codebase(str(root), lang)
            if codebase is None:
                continue
            files, funcs, classes, lines = self._extract(codebase, lang)
            all_files.extend(files)
            all_funcs.extend(funcs)
            all_cls.extend(classes)
            total_lines += lines

        return CodebaseSnapshot(
            root_path=str(root),
            files=tuple(all_files),
            functions=tuple(all_funcs),
            classes=tuple(all_cls),
            languages_detected=tuple(resolved),
            total_lines=total_lines,
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

    def _init_codebase(self, root: str, language: str) -> object | None:
        """Initialise a graph-sitter Codebase; returns None on failure."""
        try:
            from codegen import Codebase  # graph-sitter package
        except ImportError as exc:
            raise CodebaseParseError(
                "graph-sitter (codegen) is not installed. "
                "Run: pip install graph-sitter"
            ) from exc
        try:
            return Codebase(root, language=language)
        except RecursionError:
            logger.warning("RecursionError for %s; raising limit and retrying", language)
            original = sys.getrecursionlimit()
            sys.setrecursionlimit(max(original, 5000))
            try:
                return Codebase(root, language=language)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to parse %s after retry: %s", language, exc)
                return None
            finally:
                sys.setrecursionlimit(original)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to init codebase for %s: %s", language, exc)
            return None

    def _extract(
        self, codebase: object, language: str,
    ) -> tuple[list[FileInfo], list[FunctionInfo], list[ClassInfo], int]:
        files: list[FileInfo] = []
        funcs: list[FunctionInfo] = []
        classes: list[ClassInfo] = []
        total_lines = 0
        for sf in codebase.files:  # type: ignore[attr-defined]
            fi = self._extract_file(sf, language)
            if fi is not None:
                files.append(fi)
                total_lines += fi.line_count
        for fn in codebase.functions:  # type: ignore[attr-defined]
            fi = self._extract_function(fn)
            if fi is not None:
                funcs.append(fi)
        for cl in codebase.classes:  # type: ignore[attr-defined]
            ci = self._extract_class(cl)
            if ci is not None:
                classes.append(ci)
        return files, funcs, classes, total_lines

    def _extract_file(self, sf: object, language: str) -> FileInfo | None:
        try:
            filepath = str(sf.filepath)  # type: ignore[attr-defined]
            content = sf.source  # type: ignore[attr-defined]
            line_count = content.count("\n") + 1 if content else 0
            func_names = tuple(f.name for f in getattr(sf, "functions", []))
            class_names = tuple(c.name for c in getattr(sf, "classes", []))
            import_sources: list[str] = []
            for imp in getattr(sf, "imports", []):
                resolved = getattr(imp, "resolved_symbol", None)
                if resolved is not None:
                    rf = getattr(resolved, "file", None)
                    if rf is not None:
                        import_sources.append(str(rf.filepath))
            return FileInfo(
                filepath=filepath, language=language, line_count=line_count,
                function_names=func_names, class_names=class_names,
                import_sources=tuple(import_sources),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to extract file info; skipping", exc_info=True)
            return None

    def _extract_function(self, fn: object) -> FunctionInfo | None:
        try:
            name = fn.name  # type: ignore[attr-defined]
            filepath = str(fn.filepath)  # type: ignore[attr-defined]
            start_line = getattr(fn, "start_point", (0,))[0]
            end_line = getattr(fn, "end_point", (0,))[0]
            params = tuple(p.name for p in getattr(fn, "parameters", []))
            rt = getattr(fn, "return_type", None)
            return_type = str(rt) if rt is not None else None
            calls: list[str] = []
            for call in getattr(fn, "function_calls", []):
                fd = getattr(call, "function_definition", None)
                if fd is not None:
                    calls.append(fd.name)
            deps: list[str] = []
            for dep in getattr(fn, "dependencies", []):
                dp = getattr(dep, "filepath", None)
                if dp is not None:
                    deps.append(str(dp))
            return FunctionInfo(
                name=name, filepath=filepath,
                start_line=start_line, end_line=end_line,
                parameters=params, return_type=return_type,
                calls=tuple(calls), dependencies=tuple(deps),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to extract function info; skipping", exc_info=True)
            return None

    def _extract_class(self, cl: object) -> ClassInfo | None:
        try:
            name = cl.name  # type: ignore[attr-defined]
            filepath = str(cl.filepath)  # type: ignore[attr-defined]
            start_line = getattr(cl, "start_point", (0,))[0]
            end_line = getattr(cl, "end_point", (0,))[0]
            methods = tuple(m.name for m in getattr(cl, "methods", []))
            supers = getattr(cl, "superclasses", None)
            base_classes = tuple(b.name for b in supers) if supers is not None else ()
            subclasses = tuple(s.name for s in getattr(cl, "subclasses", []))
            return ClassInfo(
                name=name, filepath=filepath,
                start_line=start_line, end_line=end_line,
                methods=methods, base_classes=base_classes,
                subclasses=subclasses,
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to extract class info; skipping", exc_info=True)
            return None


# -- Convenience function ---------------------------------------------------

def parse_project(path: str, languages: list[str] | None = None) -> CodebaseSnapshot:
    """Parse a project directory and return an immutable snapshot."""
    return CodebaseParser().parse(path, languages=languages)
