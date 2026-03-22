"""Language detection for source code files and projects.

Detects programming languages based on file extensions and provides
project-level language distribution analysis. Only languages supported
by graph-sitter (codegen) are recognized.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = ("python", "typescript", "javascript")

_EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}


@dataclass(frozen=True)
class LanguageProfile:
    """Immutable language distribution for a directory.

    Attributes:
        languages: Mapping from language name to file count.
        primary_language: The most common supported language.
        total_files: Total number of supported-language files found.
    """

    languages: dict[str, int]
    primary_language: str
    total_files: int


def detect_language(file_path: str) -> str:
    """Detect the programming language of a single file by extension.

    Args:
        file_path: Path to the source file (absolute or relative).

    Returns:
        Language name (e.g. "python", "typescript", "javascript")
        or "unsupported" if the extension is not recognized.
    """
    suffix = Path(file_path).suffix.lower()
    return _EXTENSION_MAP.get(suffix, "unsupported")


def detect_project_language(dir_path: str) -> str:
    """Detect the primary programming language of a project directory.

    Scans all files recursively, counts supported-language files,
    and returns the language with the highest count.

    Args:
        dir_path: Path to the project root directory.

    Returns:
        The primary language name, or "unsupported" if no supported
        files are found.

    Raises:
        FileNotFoundError: If dir_path does not exist.
        NotADirectoryError: If dir_path is not a directory.
    """
    profile = detect_languages(dir_path)
    return profile.primary_language


def detect_languages(dir_path: str) -> LanguageProfile:
    """Detect all programming languages present in a directory.

    Scans file extensions recursively to determine language distribution.
    Only counts files whose extensions map to SUPPORTED_LANGUAGES.

    Args:
        dir_path: Directory path to scan.

    Returns:
        LanguageProfile with language distribution and primary language.

    Raises:
        FileNotFoundError: If dir_path does not exist.
        NotADirectoryError: If dir_path is not a directory.
    """
    path = Path(dir_path)

    if not path.exists():
        raise FileNotFoundError(f"Directory does not exist: {dir_path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {dir_path}")

    counter: Counter[str] = Counter()

    for child in path.rglob("*"):
        if not child.is_file():
            continue
        lang = detect_language(str(child))
        if lang != "unsupported":
            counter[lang] += 1

    total = sum(counter.values())

    if total == 0:
        logger.warning("No supported language files found in %s", dir_path)
        return LanguageProfile(
            languages={},
            primary_language="unsupported",
            total_files=0,
        )

    primary = counter.most_common(1)[0][0]

    return LanguageProfile(
        languages=dict(counter),
        primary_language=primary,
        total_files=total,
    )


def is_supported_language(language: str) -> bool:
    """Check if a language is supported by graph-sitter.

    Args:
        language: Language name to check (case-insensitive).

    Returns:
        True if the language is supported, False otherwise.
    """
    return language.lower() in SUPPORTED_LANGUAGES
