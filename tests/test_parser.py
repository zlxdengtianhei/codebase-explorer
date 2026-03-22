"""Tests for src.parser.language_detect and src.parser.codebase modules."""
from __future__ import annotations

import dataclasses
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.parser.codebase import (
    ClassInfo,
    CodebaseParseError,
    CodebaseParser,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
    UnsupportedLanguageError,
)
from src.parser.language_detect import (
    LanguageProfile,
    detect_language,
    detect_languages,
    detect_project_language,
    is_supported_language,
)


# ===================================================================
# Language Detection Tests
# ===================================================================


class TestDetectLanguage:
    """Tests for detect_language() single-file language detection."""

    def test_detect_python(self) -> None:
        assert detect_language("main.py") == "python"
        assert detect_language("/some/path/module.py") == "python"

    def test_detect_typescript(self) -> None:
        assert detect_language("component.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"
        assert detect_language("/src/index.ts") == "typescript"
        assert detect_language("/src/App.tsx") == "typescript"

    def test_detect_javascript(self) -> None:
        assert detect_language("index.js") == "javascript"
        assert detect_language("index.jsx") == "javascript"
        assert detect_language("/lib/utils.js") == "javascript"
        assert detect_language("/components/Button.jsx") == "javascript"

    def test_detect_unsupported(self) -> None:
        assert detect_language("main.go") == "unsupported"
        assert detect_language("lib.rs") == "unsupported"
        assert detect_language("App.java") == "unsupported"
        assert detect_language("style.css") == "unsupported"
        assert detect_language("data.json") == "unsupported"

    def test_detect_no_extension(self) -> None:
        assert detect_language("Makefile") == "unsupported"
        assert detect_language("Dockerfile") == "unsupported"
        assert detect_language("/path/to/noext") == "unsupported"

    def test_detect_case_insensitive_extension(self) -> None:
        """Extensions are lowercased before lookup."""
        assert detect_language("main.PY") == "python"
        assert detect_language("index.JS") == "javascript"
        assert detect_language("app.TS") == "typescript"


class TestIsSupportedLanguage:
    """Tests for is_supported_language() check."""

    def test_supported_lowercase(self) -> None:
        assert is_supported_language("python") is True
        assert is_supported_language("typescript") is True
        assert is_supported_language("javascript") is True

    def test_supported_case_insensitive(self) -> None:
        assert is_supported_language("Python") is True
        assert is_supported_language("TYPESCRIPT") is True
        assert is_supported_language("JavaScript") is True

    def test_unsupported(self) -> None:
        assert is_supported_language("go") is False
        assert is_supported_language("rust") is False
        assert is_supported_language("java") is False
        assert is_supported_language("") is False


class TestDetectProjectLanguage:
    """Tests for detect_project_language() directory scanning."""

    def test_detect_project_language_python_dominant(self) -> None:
        """Directory with more .py files should detect 'python'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 3 Python files and 1 JS file
            Path(tmpdir, "app.py").write_text("# python")
            Path(tmpdir, "utils.py").write_text("# python")
            Path(tmpdir, "models.py").write_text("# python")
            Path(tmpdir, "script.js").write_text("// js")

            result = detect_project_language(tmpdir)
            assert result == "python"

    def test_detect_project_language_typescript_dominant(self) -> None:
        """Directory with more .ts files should detect 'typescript'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "index.ts").write_text("// ts")
            Path(tmpdir, "App.tsx").write_text("// tsx")
            Path(tmpdir, "utils.ts").write_text("// ts")
            Path(tmpdir, "helper.py").write_text("# py")

            result = detect_project_language(tmpdir)
            assert result == "typescript"

    def test_detect_project_language_empty_dir(self) -> None:
        """Empty directory returns 'unsupported'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = detect_project_language(tmpdir)
            assert result == "unsupported"

    def test_detect_project_language_no_supported_files(self) -> None:
        """Directory with only unsupported files returns 'unsupported'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "main.go").write_text("package main")
            Path(tmpdir, "Cargo.toml").write_text("[package]")

            result = detect_project_language(tmpdir)
            assert result == "unsupported"

    def test_detect_project_language_nonexistent_dir(self) -> None:
        """Non-existent directory raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            detect_project_language("/nonexistent/path/abc123")

    def test_detect_project_language_file_not_dir(self) -> None:
        """Path pointing to a file raises NotADirectoryError."""
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            with pytest.raises(NotADirectoryError):
                detect_project_language(f.name)


class TestDetectLanguages:
    """Tests for detect_languages() returning a LanguageProfile."""

    def test_detect_languages_mixed(self) -> None:
        """Mixed project returns proper LanguageProfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.py").write_text("")
            Path(tmpdir, "b.py").write_text("")
            Path(tmpdir, "c.ts").write_text("")

            profile = detect_languages(tmpdir)

            assert isinstance(profile, LanguageProfile)
            assert profile.primary_language == "python"
            assert profile.total_files == 3
            assert profile.languages["python"] == 2
            assert profile.languages["typescript"] == 1

    def test_detect_languages_recursive(self) -> None:
        """Recursively detects files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = Path(tmpdir, "src")
            sub.mkdir()
            Path(sub, "index.js").write_text("")
            Path(sub, "utils.js").write_text("")
            Path(tmpdir, "setup.py").write_text("")

            profile = detect_languages(tmpdir)

            assert profile.total_files == 3
            assert "javascript" in profile.languages
            assert "python" in profile.languages

    def test_language_profile_is_frozen(self) -> None:
        """LanguageProfile is a frozen dataclass."""
        profile = LanguageProfile(
            languages={"python": 5},
            primary_language="python",
            total_files=5,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.primary_language = "javascript"  # type: ignore[misc]


# ===================================================================
# CodebaseParser Tests
# ===================================================================


class TestFileInfo:
    """Tests for the FileInfo frozen dataclass."""

    def test_file_info_fields(
        self, sample_file_info_app: FileInfo
    ) -> None:
        """Verify FileInfo has all required fields."""
        assert sample_file_info_app.filepath == "app.py"
        assert sample_file_info_app.language == "python"
        assert sample_file_info_app.line_count == 100
        assert isinstance(sample_file_info_app.function_names, tuple)
        assert isinstance(sample_file_info_app.class_names, tuple)
        assert isinstance(sample_file_info_app.import_sources, tuple)

    def test_file_info_immutable(self) -> None:
        """FileInfo should be frozen (immutable)."""
        fi = FileInfo(
            filepath="test.py",
            language="python",
            line_count=10,
            function_names=(),
            class_names=(),
            import_sources=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fi.filepath = "other.py"  # type: ignore[misc]


class TestFunctionInfo:
    """Tests for the FunctionInfo frozen dataclass."""

    def test_function_info_fields(
        self, sample_function_info: FunctionInfo
    ) -> None:
        assert sample_function_info.name == "main"
        assert sample_function_info.filepath == "app.py"
        assert sample_function_info.start_line == 10
        assert sample_function_info.end_line == 30
        assert sample_function_info.parameters == ("args",)
        assert sample_function_info.return_type == "None"
        assert sample_function_info.calls == ("helper",)
        assert sample_function_info.dependencies == ("utils.py",)

    def test_function_info_immutable(self) -> None:
        fi = FunctionInfo(
            name="f",
            filepath="x.py",
            start_line=1,
            end_line=5,
            parameters=(),
            return_type=None,
            calls=(),
            dependencies=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fi.name = "g"  # type: ignore[misc]


class TestClassInfo:
    """Tests for the ClassInfo frozen dataclass."""

    def test_class_info_fields(
        self, sample_class_info: ClassInfo
    ) -> None:
        assert sample_class_info.name == "App"
        assert sample_class_info.filepath == "app.py"
        assert sample_class_info.methods == ("__init__", "run")
        assert sample_class_info.base_classes == ()
        assert sample_class_info.subclasses == ()

    def test_class_info_immutable(self) -> None:
        ci = ClassInfo(
            name="C",
            filepath="c.py",
            start_line=1,
            end_line=10,
            methods=(),
            base_classes=(),
            subclasses=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ci.name = "D"  # type: ignore[misc]


class TestCodebaseSnapshot:
    """Tests for the CodebaseSnapshot frozen dataclass."""

    def test_codebase_snapshot_immutable(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        """CodebaseSnapshot is a frozen dataclass and cannot be mutated."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            sample_snapshot.root_path = "/other"  # type: ignore[misc]

    def test_codebase_snapshot_fields(
        self, sample_snapshot: CodebaseSnapshot
    ) -> None:
        assert sample_snapshot.root_path == "/fake/project"
        assert len(sample_snapshot.files) == 3
        assert len(sample_snapshot.functions) == 1
        assert len(sample_snapshot.classes) == 1
        assert sample_snapshot.languages_detected == ("python",)
        assert sample_snapshot.total_lines == 230


class TestCodebaseParser:
    """Tests for the CodebaseParser class."""

    def test_parse_invalid_path(self) -> None:
        """Parsing a non-existent path raises CodebaseParseError."""
        parser = CodebaseParser()
        with pytest.raises(CodebaseParseError, match="Path does not exist"):
            parser.parse("/nonexistent/path/xyz123")

    def test_parse_file_not_directory(self) -> None:
        """Parsing a file path (not dir) raises CodebaseParseError."""
        parser = CodebaseParser()
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            with pytest.raises(
                CodebaseParseError, match="Path is not a directory"
            ):
                parser.parse(f.name)

    def test_parse_unsupported_language_explicit(self) -> None:
        """Explicitly requesting an unsupported language raises error."""
        parser = CodebaseParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(UnsupportedLanguageError, match="Unsupported language"):
                parser.parse(tmpdir, languages=["rust"])

    def test_parse_empty_directory_no_supported_files(self) -> None:
        """Empty dir with auto-detect raises UnsupportedLanguageError."""
        parser = CodebaseParser()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(
                UnsupportedLanguageError,
                match="No supported language files found",
            ):
                parser.parse(tmpdir)

    def test_parse_project_basic_with_mock(self) -> None:
        """Parse a small project using a mocked codegen.Codebase.

        Mocks the graph-sitter (codegen) import so that the test does
        not require the actual codegen package to be installed.
        """
        parser = CodebaseParser()

        # Build mock source file objects
        mock_file = MagicMock()
        mock_file.filepath = "app.py"
        mock_file.source = "line1\nline2\nline3"
        mock_file.functions = []
        mock_file.classes = []
        mock_file.imports = []

        mock_fn = MagicMock()
        mock_fn.name = "main"
        mock_fn.filepath = "app.py"
        mock_fn.start_point = (1, 0)
        mock_fn.end_point = (3, 0)
        mock_fn.parameters = []
        mock_fn.return_type = None
        mock_fn.function_calls = []
        mock_fn.dependencies = []

        mock_codebase = MagicMock()
        mock_codebase.files = [mock_file]
        mock_codebase.functions = [mock_fn]
        mock_codebase.classes = []

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real .py file so language detection works
            Path(tmpdir, "app.py").write_text("line1\nline2\nline3")

            with patch.object(
                parser,
                "_init_codebase",
                return_value=mock_codebase,
            ):
                snapshot = parser.parse(tmpdir)

        assert isinstance(snapshot, CodebaseSnapshot)
        assert len(snapshot.files) == 1
        assert snapshot.files[0].filepath == "app.py"
        assert snapshot.files[0].line_count == 3
        assert len(snapshot.functions) == 1
        assert snapshot.functions[0].name == "main"
        assert snapshot.total_lines == 3

    def test_parse_returns_empty_when_codebase_init_fails(self) -> None:
        """When _init_codebase returns None, parse returns empty snapshot."""
        parser = CodebaseParser()

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1")

            with patch.object(
                parser,
                "_init_codebase",
                return_value=None,
            ):
                snapshot = parser.parse(tmpdir)

        assert isinstance(snapshot, CodebaseSnapshot)
        assert len(snapshot.files) == 0
        assert snapshot.total_lines == 0

    def test_get_file_content(self) -> None:
        """get_file_content reads real file content."""
        parser = CodebaseParser()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write("hello = 'world'\n")
            f.flush()
            try:
                content = parser.get_file_content(f.name)
                assert content == "hello = 'world'\n"
            finally:
                os.unlink(f.name)

    def test_get_file_content_missing(self) -> None:
        """get_file_content raises FileNotFoundError for missing files."""
        parser = CodebaseParser()
        with pytest.raises(FileNotFoundError):
            parser.get_file_content("/nonexistent/file.py")

    def test_resolve_languages_explicit_valid(self) -> None:
        """Explicit language list is returned lowercased."""
        parser = CodebaseParser()
        result = parser._resolve_languages("/some/dir", ["Python", "TypeScript"])
        assert result == ["python", "typescript"]

    def test_resolve_languages_explicit_invalid(self) -> None:
        """Invalid explicit language raises UnsupportedLanguageError."""
        parser = CodebaseParser()
        with pytest.raises(UnsupportedLanguageError):
            parser._resolve_languages("/some/dir", ["rust"])
