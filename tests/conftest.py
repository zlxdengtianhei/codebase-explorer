"""Shared pytest fixtures for codebase-explorer tests."""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from src.parser.codebase import (
    ClassInfo,
    CodebaseSnapshot,
    FileInfo,
    FunctionInfo,
)
# from src.state.database import Database  # TEMPORARY: Removed in Phase 1, will be updated in TEST-01


# @pytest_asyncio.fixture
# async def db():
#     """In-memory async SQLite database for testing."""
#     database = Database(Path(":memory:"))
#     await database.initialize()
#     yield database
#     await database.close()


@pytest.fixture
def sample_file_info_app() -> FileInfo:
    """FileInfo representing app.py with imports to utils."""
    return FileInfo(
        filepath="app.py",
        language="python",
        line_count=100,
        function_names=("main", "run_app"),
        class_names=("App",),
        import_sources=("utils.py",),
    )


@pytest.fixture
def sample_file_info_utils() -> FileInfo:
    """FileInfo representing utils.py (no imports)."""
    return FileInfo(
        filepath="utils.py",
        language="python",
        line_count=50,
        function_names=("helper",),
        class_names=(),
        import_sources=(),
    )


@pytest.fixture
def sample_file_info_models() -> FileInfo:
    """FileInfo representing models.py with imports to utils."""
    return FileInfo(
        filepath="models.py",
        language="python",
        line_count=80,
        function_names=("create_model",),
        class_names=("UserModel", "BaseModel"),
        import_sources=("utils.py",),
    )


@pytest.fixture
def sample_function_info() -> FunctionInfo:
    """FunctionInfo for the main() function in app.py."""
    return FunctionInfo(
        name="main",
        filepath="app.py",
        start_line=10,
        end_line=30,
        parameters=("args",),
        return_type="None",
        calls=("helper",),
        dependencies=("utils.py",),
    )


@pytest.fixture
def sample_class_info() -> ClassInfo:
    """ClassInfo for the App class in app.py."""
    return ClassInfo(
        name="App",
        filepath="app.py",
        start_line=35,
        end_line=80,
        methods=("__init__", "run"),
        base_classes=(),
        subclasses=(),
    )


@pytest.fixture
def sample_snapshot(
    sample_file_info_app: FileInfo,
    sample_file_info_utils: FileInfo,
    sample_file_info_models: FileInfo,
    sample_function_info: FunctionInfo,
    sample_class_info: ClassInfo,
) -> CodebaseSnapshot:
    """Create a CodebaseSnapshot for testing with 3 files.

    Dependency structure:
        app.py -> utils.py
        models.py -> utils.py
    """
    return CodebaseSnapshot(
        root_path="/fake/project",
        files=(
            sample_file_info_app,
            sample_file_info_utils,
            sample_file_info_models,
        ),
        functions=(sample_function_info,),
        classes=(sample_class_info,),
        languages_detected=("python",),
        total_lines=230,
    )


@pytest.fixture
def empty_snapshot() -> CodebaseSnapshot:
    """CodebaseSnapshot with no files."""
    return CodebaseSnapshot(
        root_path="/fake/empty",
        files=(),
        functions=(),
        classes=(),
        languages_detected=(),
        total_lines=0,
    )
