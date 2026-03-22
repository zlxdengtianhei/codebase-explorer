"""Parser package -- code parsing layer for codebase-explorer.

Encapsulates graph-sitter (codegen) and exposes a unified, immutable
interface for extracting files, functions, classes, and import
relationships from Python, TypeScript, and JavaScript codebases.
"""

from src.parser.codebase import (
    ClassInfo,
    CodebaseParser,
    CodebaseParseError,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
    GraphSitterError,
    UnsupportedLanguageError,
    parse_project,
)
from src.parser.language_detect import (
    LanguageProfile,
    detect_language,
    detect_languages,
    detect_project_language,
    is_supported_language,
)

__all__ = [
    # Core parser
    "CodebaseParser",
    "parse_project",
    # Data models
    "CodebaseSnapshot",
    "FileInfo",
    "FunctionInfo",
    "ClassInfo",
    "LanguageProfile",
    # Language detection
    "detect_language",
    "detect_languages",
    "detect_project_language",
    "is_supported_language",
    # Errors
    "GraphSitterError",
    "CodebaseParseError",
    "UnsupportedLanguageError",
]
