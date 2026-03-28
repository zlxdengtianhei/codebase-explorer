"""Tests for src/parser/codebase.py and src/parser/language_detect.py.

Covers all public data classes, the CodebaseParser (including AST fallback),
the convenience ``parse_project`` function, and all language detection
functions.
"""
from __future__ import annotations

import dataclasses
import os
import textwrap
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
    GraphSitterError,
    UnsupportedLanguageError,
    _USE_FALLBACK,
    parse_project,
)
from src.parser.language_detect import (
    SUPPORTED_LANGUAGES,
    LanguageProfile,
    _EXTENSION_MAP,
    detect_language,
    detect_languages,
    detect_project_language,
    is_supported_language,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    """Write content to a file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ===========================================================================
# Data model tests
# ===========================================================================


class TestFileInfo:
    """Tests for the FileInfo frozen dataclass."""

    def test_creation_with_required_fields(self) -> None:
        fi = FileInfo(
            filepath="app.py",
            language="python",
            line_count=42,
            function_names=("main",),
            class_names=("App",),
            import_sources=("utils.py",),
        )
        assert fi.filepath == "app.py"
        assert fi.language == "python"
        assert fi.line_count == 42
        assert fi.function_names == ("main",)
        assert fi.class_names == ("App",)
        assert fi.import_sources == ("utils.py",)
        assert fi.char_count == 0  # default

    def test_creation_with_char_count(self) -> None:
        fi = FileInfo(
            filepath="a.py", language="python", line_count=1,
            function_names=(), class_names=(), import_sources=(),
            char_count=999,
        )
        assert fi.char_count == 999

    def test_frozen_immutability(self) -> None:
        fi = FileInfo(
            filepath="a.py", language="python", line_count=1,
            function_names=(), class_names=(), import_sources=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fi.filepath = "changed.py"  # type: ignore[misc]

    def test_equality(self) -> None:
        kwargs = dict(
            filepath="a.py", language="python", line_count=1,
            function_names=(), class_names=(), import_sources=(),
        )
        assert FileInfo(**kwargs) == FileInfo(**kwargs)

    def test_inequality_different_values(self) -> None:
        base = dict(
            filepath="a.py", language="python", line_count=1,
            function_names=(), class_names=(), import_sources=(),
        )
        fi1 = FileInfo(**base)
        fi2 = FileInfo(**{**base, "line_count": 99})
        assert fi1 != fi2


class TestFunctionInfo:
    """Tests for the FunctionInfo frozen dataclass."""

    def test_creation(self) -> None:
        fi = FunctionInfo(
            name="do_stuff", filepath="x.py",
            start_line=1, end_line=10,
            parameters=("a", "b"), return_type="int",
            calls=("helper",), dependencies=("util.py",),
        )
        assert fi.name == "do_stuff"
        assert fi.parameters == ("a", "b")
        assert fi.return_type == "int"
        assert fi.calls == ("helper",)

    def test_none_return_type(self) -> None:
        fi = FunctionInfo(
            name="f", filepath="x.py",
            start_line=1, end_line=1,
            parameters=(), return_type=None,
            calls=(), dependencies=(),
        )
        assert fi.return_type is None

    def test_frozen_immutability(self) -> None:
        fi = FunctionInfo(
            name="f", filepath="x.py",
            start_line=1, end_line=1,
            parameters=(), return_type=None,
            calls=(), dependencies=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fi.name = "other"  # type: ignore[misc]


class TestClassInfo:
    """Tests for the ClassInfo frozen dataclass."""

    def test_creation(self) -> None:
        ci = ClassInfo(
            name="MyClass", filepath="m.py",
            start_line=5, end_line=50,
            methods=("__init__", "run"),
            base_classes=("Base",),
            subclasses=("Child",),
        )
        assert ci.name == "MyClass"
        assert ci.methods == ("__init__", "run")
        assert ci.base_classes == ("Base",)
        assert ci.subclasses == ("Child",)

    def test_frozen_immutability(self) -> None:
        ci = ClassInfo(
            name="C", filepath="c.py",
            start_line=1, end_line=2,
            methods=(), base_classes=(), subclasses=(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            ci.name = "Other"  # type: ignore[misc]


class TestCodebaseSnapshot:
    """Tests for the CodebaseSnapshot frozen dataclass."""

    def test_creation(self, sample_snapshot: CodebaseSnapshot) -> None:
        assert sample_snapshot.root_path == "/fake/project"
        assert len(sample_snapshot.files) == 3
        assert sample_snapshot.total_lines == 230
        assert sample_snapshot.languages_detected == ("python",)

    def test_empty_snapshot(self, empty_snapshot: CodebaseSnapshot) -> None:
        assert empty_snapshot.files == ()
        assert empty_snapshot.functions == ()
        assert empty_snapshot.classes == ()
        assert empty_snapshot.total_lines == 0

    def test_frozen_immutability(self, empty_snapshot: CodebaseSnapshot) -> None:
        with pytest.raises(dataclasses.FrozenInstanceError):
            empty_snapshot.root_path = "/changed"  # type: ignore[misc]


class TestErrorHierarchy:
    """Tests for the custom exception hierarchy."""

    def test_graph_sitter_error_is_exception(self) -> None:
        assert issubclass(GraphSitterError, Exception)

    def test_codebase_parse_error_inherits(self) -> None:
        assert issubclass(CodebaseParseError, GraphSitterError)

    def test_unsupported_language_error_inherits(self) -> None:
        assert issubclass(UnsupportedLanguageError, GraphSitterError)

    def test_errors_carry_messages(self) -> None:
        err = CodebaseParseError("bad path")
        assert str(err) == "bad path"


# ===========================================================================
# Language detection tests
# ===========================================================================


class TestDetectLanguage:
    """Tests for detect_language (single file path -> language)."""

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("app.py", "python"),
            ("module.ts", "typescript"),
            ("component.tsx", "typescript"),
            ("script.js", "javascript"),
            ("component.jsx", "javascript"),
            ("/absolute/path/to/file.py", "python"),
            ("relative/path/file.ts", "typescript"),
        ],
    )
    def test_supported_extensions(self, path: str, expected: str) -> None:
        assert detect_language(path) == expected

    @pytest.mark.parametrize(
        "path",
        [
            "readme.md",
            "Makefile",
            "style.css",
            "data.json",
            "image.png",
            "code.rs",
            "main.go",
            "lib.rb",
            "noext",
        ],
    )
    def test_unsupported_extensions(self, path: str) -> None:
        assert detect_language(path) == "unsupported"

    def test_case_insensitive_extension(self) -> None:
        assert detect_language("FILE.PY") == "python"
        assert detect_language("app.Ts") == "typescript"

    def test_extension_map_completeness(self) -> None:
        """Every value in _EXTENSION_MAP is a SUPPORTED_LANGUAGES member."""
        for lang in _EXTENSION_MAP.values():
            assert lang in SUPPORTED_LANGUAGES


class TestIsSupportedLanguage:
    """Tests for is_supported_language."""

    @pytest.mark.parametrize("lang", ["python", "typescript", "javascript"])
    def test_supported(self, lang: str) -> None:
        assert is_supported_language(lang) is True

    @pytest.mark.parametrize("lang", ["Python", "TYPESCRIPT", "JavaScript"])
    def test_case_insensitive(self, lang: str) -> None:
        assert is_supported_language(lang) is True

    @pytest.mark.parametrize("lang", ["rust", "go", "ruby", "java", ""])
    def test_unsupported(self, lang: str) -> None:
        assert is_supported_language(lang) is False


class TestLanguageProfile:
    """Tests for the LanguageProfile frozen dataclass."""

    def test_creation(self) -> None:
        lp = LanguageProfile(
            languages={"python": 10, "typescript": 3},
            primary_language="python",
            total_files=13,
        )
        assert lp.primary_language == "python"
        assert lp.total_files == 13
        assert lp.languages["typescript"] == 3

    def test_frozen_immutability(self) -> None:
        lp = LanguageProfile(languages={}, primary_language="python", total_files=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            lp.primary_language = "rust"  # type: ignore[misc]


class TestDetectLanguages:
    """Tests for detect_languages (directory-level scanning)."""

    def test_python_only_project(self, tmp_path: Path) -> None:
        _write(tmp_path / "app.py", "print('hello')\n")
        _write(tmp_path / "utils.py", "x = 1\n")
        profile = detect_languages(str(tmp_path))
        assert profile.primary_language == "python"
        assert profile.languages == {"python": 2}
        assert profile.total_files == 2

    def test_mixed_languages(self, tmp_path: Path) -> None:
        _write(tmp_path / "app.py", "pass\n")
        _write(tmp_path / "index.ts", "const x = 1;\n")
        _write(tmp_path / "script.js", "var y = 2;\n")
        profile = detect_languages(str(tmp_path))
        assert set(profile.languages.keys()) == {"python", "typescript", "javascript"}
        assert profile.total_files == 3

    def test_empty_directory(self, tmp_path: Path) -> None:
        profile = detect_languages(str(tmp_path))
        assert profile.primary_language == "unsupported"
        assert profile.languages == {}
        assert profile.total_files == 0

    def test_only_unsupported_files(self, tmp_path: Path) -> None:
        _write(tmp_path / "readme.md", "# hi\n")
        _write(tmp_path / "data.json", "{}\n")
        profile = detect_languages(str(tmp_path))
        assert profile.primary_language == "unsupported"
        assert profile.total_files == 0

    def test_nested_directories(self, tmp_path: Path) -> None:
        _write(tmp_path / "src" / "a.py", "pass\n")
        _write(tmp_path / "src" / "lib" / "b.py", "pass\n")
        _write(tmp_path / "src" / "lib" / "c.ts", "1;\n")
        profile = detect_languages(str(tmp_path))
        assert profile.languages["python"] == 2
        assert profile.languages["typescript"] == 1
        assert profile.primary_language == "python"

    def test_nonexistent_directory_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            detect_languages("/nonexistent/path/xyz")

    def test_file_instead_of_directory_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hi", encoding="utf-8")
        with pytest.raises(NotADirectoryError):
            detect_languages(str(f))


class TestDetectProjectLanguage:
    """Tests for detect_project_language convenience function."""

    def test_returns_primary_language(self, tmp_path: Path) -> None:
        _write(tmp_path / "a.py", "pass\n")
        _write(tmp_path / "b.py", "pass\n")
        _write(tmp_path / "c.ts", "1;\n")
        assert detect_project_language(str(tmp_path)) == "python"

    def test_empty_returns_unsupported(self, tmp_path: Path) -> None:
        assert detect_project_language(str(tmp_path)) == "unsupported"


# ===========================================================================
# CodebaseParser tests
# ===========================================================================


class TestCodebaseParser:
    """Tests for CodebaseParser.parse() and helpers."""

    def test_parse_nonexistent_path_raises(self) -> None:
        parser = CodebaseParser()
        with pytest.raises(CodebaseParseError, match="does not exist"):
            parser.parse("/absolutely/no/such/path")

    def test_parse_file_not_directory_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "file.py"
        f.write_text("pass", encoding="utf-8")
        parser = CodebaseParser()
        with pytest.raises(CodebaseParseError, match="not a directory"):
            parser.parse(str(f))

    def test_parse_unsupported_language_explicit(self, tmp_path: Path) -> None:
        parser = CodebaseParser()
        with pytest.raises(UnsupportedLanguageError, match="rust"):
            parser.parse(str(tmp_path), languages=["rust"])

    def test_parse_empty_dir_unsupported_language(self, tmp_path: Path) -> None:
        """Empty directory with no language files yields UnsupportedLanguageError."""
        parser = CodebaseParser()
        with pytest.raises(UnsupportedLanguageError, match="No supported language"):
            parser.parse(str(tmp_path))

    def test_parse_dir_with_only_unsupported_files(self, tmp_path: Path) -> None:
        _write(tmp_path / "readme.md", "# hello\n")
        parser = CodebaseParser()
        with pytest.raises(UnsupportedLanguageError, match="No supported language"):
            parser.parse(str(tmp_path))

    def test_resolve_languages_auto_detect(self, tmp_path: Path) -> None:
        _write(tmp_path / "a.py", "pass\n")
        parser = CodebaseParser()
        resolved = parser._resolve_languages(str(tmp_path), None)
        assert "python" in resolved

    def test_resolve_languages_explicit(self, tmp_path: Path) -> None:
        parser = CodebaseParser()
        resolved = parser._resolve_languages(str(tmp_path), ["Python"])
        assert resolved == ["python"]

    def test_resolve_languages_unsupported_raises(self, tmp_path: Path) -> None:
        parser = CodebaseParser()
        with pytest.raises(UnsupportedLanguageError):
            parser._resolve_languages(str(tmp_path), ["cobol"])


class TestCodebaseParserASTFallback:
    """Tests exercising the AST fallback path (codegen not importable)."""

    def _make_python_project(self, tmp_path: Path) -> Path:
        """Create a small Python project under tmp_path and return root."""
        _write(tmp_path / "main.py", """\
            import utils

            def main(arg: str) -> int:
                return utils.helper(arg)

            class App:
                def run(self):
                    pass
        """)
        _write(tmp_path / "utils.py", """\
            def helper(x):
                return x
        """)
        return tmp_path

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_produces_snapshot(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        parser = CodebaseParser()
        snap = parser.parse(str(root), languages=["python"])

        assert isinstance(snap, CodebaseSnapshot)
        assert snap.languages_detected == ("python",)
        assert len(snap.files) == 2
        assert snap.total_lines > 0

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_extracts_functions(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        snap = CodebaseParser().parse(str(root), languages=["python"])

        func_names = {f.name for f in snap.functions}
        assert "main" in func_names
        assert "helper" in func_names

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_extracts_classes(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        snap = CodebaseParser().parse(str(root), languages=["python"])

        class_names = {c.name for c in snap.classes}
        assert "App" in class_names

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_extracts_class_methods(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        snap = CodebaseParser().parse(str(root), languages=["python"])

        app_cls = [c for c in snap.classes if c.name == "App"][0]
        assert "run" in app_cls.methods

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_resolves_imports(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        snap = CodebaseParser().parse(str(root), languages=["python"])

        main_file = [f for f in snap.files if "main" in f.filepath][0]
        assert "utils.py" in main_file.import_sources

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_char_count(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        root = self._make_python_project(tmp_path)
        snap = CodebaseParser().parse(str(root), languages=["python"])

        for fi in snap.files:
            assert fi.char_count > 0

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_syntax_error_file(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        """A file with a SyntaxError is still recorded (but with empty names)."""
        _write(tmp_path / "bad.py", "def broken(\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])

        assert len(snap.files) == 1
        assert snap.files[0].function_names == ()
        assert snap.files[0].class_names == ()
        assert snap.files[0].line_count > 0

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_skips_non_python_language(
        self, _mock_init: MagicMock, tmp_path: Path,
    ) -> None:
        """Non-python language with fallback should produce an empty snapshot."""
        _write(tmp_path / "app.ts", "const x = 1;\n")
        parser = CodebaseParser()
        snap = parser.parse(str(tmp_path), languages=["typescript"])

        assert len(snap.files) == 0
        assert snap.total_lines == 0

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_function_parameters(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        _write(tmp_path / "funcs.py", """\
            def greet(name: str, greeting: str) -> str:
                return f"{greeting}, {name}"
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        fn = snap.functions[0]
        assert fn.name == "greet"
        assert "name" in fn.parameters
        assert "greeting" in fn.parameters

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_function_line_numbers(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        _write(tmp_path / "f.py", """\
            def a():
                pass

            def b():
                pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        assert len(snap.functions) == 2
        for fn in snap.functions:
            assert fn.start_line >= 1
            assert fn.end_line >= fn.start_line

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_async_function(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        _write(tmp_path / "async_mod.py", """\
            async def fetch(url: str) -> str:
                return url
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        assert len(snap.functions) == 1
        assert snap.functions[0].name == "fetch"

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_class_with_bases(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        _write(tmp_path / "models.py", """\
            class Base:
                pass

            class Child(Base):
                def method(self):
                    pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        child = [c for c in snap.classes if c.name == "Child"][0]
        assert "Base" in child.base_classes
        assert "method" in child.methods

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_from_import_resolution(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        """``from utils import helper`` should resolve to utils.py."""
        _write(tmp_path / "utils.py", "def helper(): pass\n")
        _write(tmp_path / "consumer.py", "from utils import helper\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        consumer = [f for f in snap.files if "consumer" in f.filepath][0]
        assert "utils.py" in consumer.import_sources

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_unresolved_import_omitted(
        self, _mock_init: MagicMock, tmp_path: Path,
    ) -> None:
        """Imports that can't be resolved to local files are omitted."""
        _write(tmp_path / "app.py", "import os\nimport sys\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        app = snap.files[0]
        assert app.import_sources == ()

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_nested_package(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        """Files in nested packages resolve module paths correctly."""
        _write(tmp_path / "pkg" / "__init__.py", "")
        _write(tmp_path / "pkg" / "core.py", "x = 1\n")
        _write(tmp_path / "main.py", "import pkg.core\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        main = [f for f in snap.files if "main" in f.filepath][0]
        expected_import = os.path.join("pkg", "core.py")
        assert expected_import in main.import_sources

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_fallback_self_param_excluded(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        """``self`` should not appear in extracted function parameters."""
        _write(tmp_path / "cls.py", """\
            class Foo:
                def method(self, x):
                    pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        method = [f for f in snap.functions if f.name == "method"][0]
        assert "self" not in method.parameters
        assert "x" in method.parameters


class TestCallGraphExtraction:
    """T-06: Tests for AST call graph extraction in fallback parser."""

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_function_calls_extracted(self, _mock, tmp_path):
        """Function call names are extracted into FunctionInfo.calls."""
        _write(tmp_path / "caller.py", """\
            def caller():
                result = helper()
                return result
        """)
        _write(tmp_path / "helper.py", """\
            def helper():
                return 42
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        caller_fn = [f for f in snap.functions if f.name == "caller"][0]
        assert "helper" in caller_fn.calls

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_cross_file_call_creates_dependency(self, _mock, tmp_path):
        """Cross-file function calls resolve to dependency file paths."""
        _write(tmp_path / "main.py", """\
            def main():
                do_work()
        """)
        _write(tmp_path / "worker.py", """\
            def do_work():
                pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        main_fn = [f for f in snap.functions if f.name == "main"][0]
        assert "worker.py" in main_fn.dependencies

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_self_call_not_cross_file_dep(self, _mock, tmp_path):
        """Calls to functions in the same file don't create dependencies."""
        _write(tmp_path / "mod.py", """\
            def a():
                b()
            def b():
                pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        a_fn = [f for f in snap.functions if f.name == "a"][0]
        # b() is in the same file, so no cross-file dependency
        assert "mod.py" not in a_fn.dependencies

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_attribute_call_extracted(self, _mock, tmp_path):
        """self.method() and obj.func() attribute calls are captured."""
        _write(tmp_path / "cls.py", """\
            class Foo:
                def run(self):
                    self.process()
                def process(self):
                    pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        run_fn = [f for f in snap.functions if f.name == "run"][0]
        assert "process" in run_fn.calls


class TestInheritanceEdges:
    """T-07: Tests for cross-file inheritance detection."""

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_base_classes_extracted(self, _mock, tmp_path):
        """ClassInfo.base_classes are correctly populated for cross-file use."""
        _write(tmp_path / "base.py", """\
            class Animal:
                pass
        """)
        _write(tmp_path / "dog.py", """\
            from base import Animal
            class Dog(Animal):
                def bark(self):
                    pass
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        dog_cls = [c for c in snap.classes if c.name == "Dog"][0]
        assert "Animal" in dog_cls.base_classes


class TestDynamicImportDetection:
    """T-08: Tests for dynamic import detection."""

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_importlib_import_module_detected(self, _mock, tmp_path):
        """importlib.import_module('pkg.mod') is detected as import edge."""
        _write(tmp_path / "pkg" / "__init__.py", "")
        _write(tmp_path / "pkg" / "mod.py", "x = 1\n")
        _write(tmp_path / "loader.py", """\
            import importlib
            m = importlib.import_module("pkg.mod")
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        loader = [f for f in snap.files if "loader" in f.filepath][0]
        import os
        expected = os.path.join("pkg", "mod.py")
        assert expected in loader.import_sources

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_dunder_import_detected(self, _mock, tmp_path):
        """__import__('mod') is detected as import edge."""
        _write(tmp_path / "mod.py", "x = 1\n")
        _write(tmp_path / "dyn.py", """\
            m = __import__("mod")
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        dyn = [f for f in snap.files if "dyn" in f.filepath][0]
        assert "mod.py" in dyn.import_sources

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_non_string_arg_safely_ignored(self, _mock, tmp_path):
        """Dynamic import with non-string arg (variable) is safely skipped."""
        _write(tmp_path / "dyn.py", """\
            import importlib
            name = "mod"
            m = importlib.import_module(name)
        """)
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        dyn = [f for f in snap.files if "dyn" in f.filepath][0]
        # name is a variable, not a string literal; should not resolve
        assert len(dyn.import_sources) == 0


class TestParserExcludesVenv:
    """Tests for _EXCLUDED_DIRS path exclusion in fallback parser."""

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_venv_files_excluded(self, _mock, tmp_path):
        """Files inside .venv should not appear in the snapshot."""
        _write(tmp_path / "app.py", "x = 1\n")
        _write(tmp_path / ".venv" / "lib" / "junk.py", "y = 2\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        filepaths = [f.filepath for f in snap.files]
        assert "app.py" in filepaths
        assert not any(".venv" in fp for fp in filepaths)

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_node_modules_excluded(self, _mock, tmp_path):
        """Files inside node_modules should not appear in the snapshot."""
        _write(tmp_path / "main.py", "pass\n")
        _write(tmp_path / "node_modules" / "pkg" / "mod.py", "z = 3\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        filepaths = [f.filepath for f in snap.files]
        assert not any("node_modules" in fp for fp in filepaths)

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_pycache_excluded(self, _mock, tmp_path):
        """Files inside __pycache__ should not appear in the snapshot."""
        _write(tmp_path / "app.py", "pass\n")
        _write(tmp_path / "__pycache__" / "app.cpython-313.pyc.py", "pass\n")
        # Note: __pycache__ usually has .pyc but we test .py for simplicity
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        filepaths = [f.filepath for f in snap.files]
        assert not any("__pycache__" in fp for fp in filepaths)

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_normal_dirs_not_excluded(self, _mock, tmp_path):
        """Non-excluded directories should still be parsed normally."""
        _write(tmp_path / "src" / "core.py", "x = 1\n")
        _write(tmp_path / "tests" / "test_core.py", "y = 2\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        filepaths = [f.filepath for f in snap.files]
        assert len(filepaths) == 2

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_multiple_excluded_dirs(self, _mock, tmp_path):
        """Multiple excluded directories should all be filtered out."""
        _write(tmp_path / "app.py", "pass\n")
        _write(tmp_path / ".venv" / "a.py", "pass\n")
        _write(tmp_path / "venv" / "b.py", "pass\n")
        _write(tmp_path / ".git" / "c.py", "pass\n")
        _write(tmp_path / "dist" / "d.py", "pass\n")
        snap = CodebaseParser().parse(str(tmp_path), languages=["python"])
        assert len(snap.files) == 1
        assert snap.files[0].filepath == "app.py"


class TestCodebaseParserGetFileContent:
    """Tests for CodebaseParser.get_file_content."""

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.py"
        f.write_text("print('hi')\n", encoding="utf-8")
        parser = CodebaseParser()
        content = parser.get_file_content(str(f))
        assert "print('hi')" in content

    def test_nonexistent_file_raises(self) -> None:
        parser = CodebaseParser()
        with pytest.raises(FileNotFoundError):
            parser.get_file_content("/no/such/file.py")


class TestParseProjectConvenience:
    """Tests for the module-level parse_project function."""

    @patch("src.parser.codebase.CodebaseParser._init_codebase", return_value=_USE_FALLBACK)
    def test_returns_snapshot(self, _mock_init: MagicMock, tmp_path: Path) -> None:
        _write(tmp_path / "app.py", "x = 1\n")
        snap = parse_project(str(tmp_path), languages=["python"])
        assert isinstance(snap, CodebaseSnapshot)
        assert len(snap.files) == 1

    def test_raises_on_invalid_path(self) -> None:
        with pytest.raises(CodebaseParseError):
            parse_project("/no/such/path")


class TestCodebaseParserInitCodebase:
    """Tests for _init_codebase handling of codegen import."""

    def test_fallback_sentinel_returned_when_codegen_missing(self) -> None:
        """When codegen is not importable, _init_codebase returns _USE_FALLBACK."""
        parser = CodebaseParser()
        with patch.dict("sys.modules", {"codegen": None}):
            # Force ImportError by making the import fail
            with patch(
                "builtins.__import__",
                side_effect=_make_import_error_for("codegen"),
            ):
                result = parser._init_codebase("/some/path", "python")
                assert result is _USE_FALLBACK

    def test_returns_none_on_generic_exception(self) -> None:
        """When codegen exists but init raises, _init_codebase returns None."""
        mock_codebase_cls = MagicMock(side_effect=RuntimeError("init failed"))
        mock_codegen = MagicMock()
        mock_codegen.Codebase = mock_codebase_cls

        parser = CodebaseParser()
        with patch.dict("sys.modules", {"codegen": mock_codegen}):
            result = parser._init_codebase("/some/path", "python")
            assert result is None


# ===========================================================================
# Helper for patching imports
# ===========================================================================

_real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__


def _make_import_error_for(module_name: str):
    """Return an __import__ replacement that raises ImportError for one module."""
    def _custom_import(name, *args, **kwargs):
        if name == module_name:
            raise ImportError(f"No module named '{module_name}'")
        return _real_import(name, *args, **kwargs)
    return _custom_import
