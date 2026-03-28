"""Tests for src/graph/semantic_hints.py — semantic classification & directory affinity.

Covers:
- classify_file for all 5 categories (testing, models, api, cli, config) + unknown
- directory_affinity_score (same dir, parent-child, sibling, unrelated)
- Uses pytest.mark.parametrize extensively
"""

from __future__ import annotations

import pytest

from src.graph.semantic_hints import classify_file, directory_affinity_score, is_reexport_facade


# ---------------------------------------------------------------------------
# is_reexport_facade (T-03)
# ---------------------------------------------------------------------------


class TestIsReexportFacade:
    """Tests for is_reexport_facade."""

    def test_facade_init_detected(self, tmp_path):
        """An __init__.py that only re-exports via relative imports is a facade."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "from .core import App\nfrom .utils import helper\n",
            encoding="utf-8",
        )
        assert is_reexport_facade("mypkg/__init__.py", str(tmp_path)) is True

    def test_non_facade_init(self, tmp_path):
        """An __init__.py with many definitions is NOT a facade."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "def foo(): pass\ndef bar(): pass\nclass Baz: pass\n",
            encoding="utf-8",
        )
        assert is_reexport_facade("mypkg/__init__.py", str(tmp_path)) is False

    def test_non_init_file(self, tmp_path):
        """Non-__init__.py files always return False."""
        (tmp_path / "app.py").write_text("from .core import x\n", encoding="utf-8")
        assert is_reexport_facade("app.py", str(tmp_path)) is False

    def test_empty_init(self, tmp_path):
        """Empty __init__.py returns False (no imports, no defs)."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        assert is_reexport_facade("pkg/__init__.py", str(tmp_path)) is False

    def test_mixed_init_below_threshold(self, tmp_path):
        """Init with 50% imports / 50% defs is below 0.8 threshold."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(
            "from .a import x\ndef foo(): pass\n",
            encoding="utf-8",
        )
        # 1 import, 1 def => 0.5 < 0.8 => not facade
        assert is_reexport_facade("pkg/__init__.py", str(tmp_path)) is False

    def test_nonexistent_file(self, tmp_path):
        """Nonexistent file returns False (no crash)."""
        assert is_reexport_facade("nope/__init__.py", str(tmp_path)) is False


# ---------------------------------------------------------------------------
# classify_file — testing category
# ---------------------------------------------------------------------------


class TestClassifyFileTesting:
    """classify_file returns 'testing' for testing-related files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "test_login.py",
            "tests/test_auth.py",
            "src/tests/test_utils.py",
            "login_test.py",
            "auth/login_test.py",
            "tests.py",
            "testing.py",
            "conftest.py",
            "tests/conftest.py",
            "fixtures.py",
            "tests/fixtures.py",
            "factories.py",
            "test/helpers.py",           # test/ directory pattern
            "__tests__/something.py",    # __tests__/ directory pattern
            "fixtures/data.py",          # fixtures/ directory pattern
        ],
    )
    def test_testing_category(self, filepath: str):
        assert classify_file(filepath) == "testing"


# ---------------------------------------------------------------------------
# classify_file — models category
# ---------------------------------------------------------------------------


class TestClassifyFileModels:
    """classify_file returns 'models' for model/schema files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "models.py",
            "src/models.py",
            "user_model.py",
            "auth/user_model.py",
            "schema.py",
            "schemas.py",
            "types.py",
            "dataclasses.py",
            "entities.py",
            "models/user.py",      # models/ directory
            "schemas/auth.py",     # schemas/ directory
            "entities/product.py", # entities/ directory
        ],
    )
    def test_models_category(self, filepath: str):
        assert classify_file(filepath) == "models"


# ---------------------------------------------------------------------------
# classify_file — api category
# ---------------------------------------------------------------------------


class TestClassifyFileApi:
    """classify_file returns 'api' for API-related files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "routes.py",
            "views.py",
            "endpoints.py",
            "handlers.py",
            "controllers.py",
            "api.py",
            "api/auth.py",           # api/ directory
            "routes/users.py",       # routes/ directory
            "views/admin.py",        # views/ directory
            "endpoints/health.py",   # endpoints/ directory
            "handlers/webhook.py",   # handlers/ directory
        ],
    )
    def test_api_category(self, filepath: str):
        assert classify_file(filepath) == "api"


# ---------------------------------------------------------------------------
# classify_file — cli category
# ---------------------------------------------------------------------------


class TestClassifyFileCli:
    """classify_file returns 'cli' for CLI/entrypoint files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "cli.py",
            "src/cli.py",
            "__main__.py",
            "src/__main__.py",
            "commands.py",
            "console.py",
            "main.py",
            "cli/deploy.py",      # cli/ directory
            "commands/build.py",  # commands/ directory
        ],
    )
    def test_cli_category(self, filepath: str):
        assert classify_file(filepath) == "cli"


# ---------------------------------------------------------------------------
# classify_file — config category
# ---------------------------------------------------------------------------


class TestClassifyFileConfig:
    """classify_file returns 'config' for configuration files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "config.py",
            "settings.py",
            "constants.py",
            "defaults.py",
            "env.py",
            "conf.py",
            "config/database.py",     # config/ directory
            "settings/production.py", # settings/ directory
        ],
    )
    def test_config_category(self, filepath: str):
        assert classify_file(filepath) == "config"


# ---------------------------------------------------------------------------
# classify_file — unknown category
# ---------------------------------------------------------------------------


class TestClassifyFileMiddleware:
    """classify_file returns 'middleware' for middleware files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "middleware.py",
            "middlewares.py",
            "middleware/auth.py",
            "middlewares/cache.py",
        ],
    )
    def test_middleware_category(self, filepath: str):
        assert classify_file(filepath) == "middleware"


class TestClassifyFileSecurity:
    """classify_file returns 'security' for security files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "security.py",
            "auth.py",
            "permissions.py",
            "security/oauth.py",
            "auth/jwt.py",
        ],
    )
    def test_security_category(self, filepath: str):
        assert classify_file(filepath) == "security"


class TestClassifyFileUtils:
    """classify_file returns 'utils' for utility files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "utils.py",
            "helpers.py",
            "common.py",
            "shared.py",
            "lib.py",
            "utils/text.py",
            "helpers/math.py",
        ],
    )
    def test_utils_category(self, filepath: str):
        assert classify_file(filepath) == "utils"


class TestClassifyFileExceptions:
    """classify_file returns 'exceptions' for exception files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "exceptions.py",
            "errors.py",
        ],
    )
    def test_exceptions_category(self, filepath: str):
        assert classify_file(filepath) == "exceptions"


class TestClassifyFileUnknown:
    """classify_file returns 'unknown' for unrecognised files."""

    @pytest.mark.parametrize(
        "filepath",
        [
            "app.py",
            "src/core/engine.py",
            "foo/bar/baz.py",
            "setup.py",
            "README.md",
        ],
    )
    def test_unknown_category(self, filepath: str):
        assert classify_file(filepath) == "unknown"


# ---------------------------------------------------------------------------
# classify_file — edge cases & normalization
# ---------------------------------------------------------------------------


class TestClassifyFileEdgeCases:
    """Edge cases for classify_file."""

    def test_backslash_normalized(self):
        """Windows-style backslashes are normalised to forward slashes."""
        assert classify_file("tests\\test_auth.py") == "testing"

    def test_case_insensitive_stem(self):
        """Stem matching is case-insensitive."""
        assert classify_file("Test_Login.py") == "testing"
        assert classify_file("MODELS.py") == "models"
        assert classify_file("CLI.py") == "cli"

    def test_case_insensitive_directory(self):
        """Directory matching is case-insensitive."""
        assert classify_file("Tests/helper.py") == "testing"
        assert classify_file("API/router.py") == "api"

    def test_deeply_nested_directory_match(self):
        """Category is detected even in deeply nested paths."""
        assert classify_file("a/b/c/tests/d/helper.py") == "testing"
        assert classify_file("a/b/models/user.py") == "models"

    def test_priority_testing_over_models(self):
        """Testing category is checked first, so test_model.py => testing."""
        assert classify_file("test_model.py") == "testing"

    def test_no_extension(self):
        """File without extension: stem is the entire basename."""
        # "models" stem matches models category
        assert classify_file("src/models") == "models"

    def test_empty_path(self):
        """Empty string returns unknown (no crash)."""
        assert classify_file("") == "unknown"


# ---------------------------------------------------------------------------
# directory_affinity_score — same directory
# ---------------------------------------------------------------------------


class TestDirectoryAffinitySameDir:
    """directory_affinity_score returns 1.0 for same-directory files."""

    @pytest.mark.parametrize(
        "file_a, file_b",
        [
            ("src/auth/login.py", "src/auth/utils.py"),
            ("a.py", "b.py"),                             # both at root
            ("deep/nested/dir/x.py", "deep/nested/dir/y.py"),
        ],
    )
    def test_same_dir_score_1_0(self, file_a: str, file_b: str):
        assert directory_affinity_score(file_a, file_b) == 1.0


# ---------------------------------------------------------------------------
# directory_affinity_score — parent-child
# ---------------------------------------------------------------------------


class TestDirectoryAffinityParentChild:
    """directory_affinity_score returns 0.7 for parent-child directories."""

    @pytest.mark.parametrize(
        "file_a, file_b",
        [
            ("src/auth/login.py", "src/utils.py"),          # auth is child of src
            ("src/utils.py", "src/auth/login.py"),          # symmetric
            ("pkg/mod.py", "mod.py"),                       # pkg vs root
            ("mod.py", "pkg/mod.py"),                       # root vs pkg (symmetric)
        ],
    )
    def test_parent_child_score_0_7(self, file_a: str, file_b: str):
        assert directory_affinity_score(file_a, file_b) == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# directory_affinity_score — sibling directories
# ---------------------------------------------------------------------------


class TestDirectoryAffinitySibling:
    """directory_affinity_score returns 0.4 for sibling directories."""

    @pytest.mark.parametrize(
        "file_a, file_b",
        [
            ("src/auth/login.py", "src/users/profile.py"),  # auth & users under src
            ("pkg/sub1/a.py", "pkg/sub2/b.py"),              # sub1 & sub2 under pkg
        ],
    )
    def test_sibling_score_0_4(self, file_a: str, file_b: str):
        assert directory_affinity_score(file_a, file_b) == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# directory_affinity_score — unrelated (different top-level)
# ---------------------------------------------------------------------------


class TestDirectoryAffinityUnrelated:
    """directory_affinity_score returns 0.0 for unrelated directories."""

    @pytest.mark.parametrize(
        "file_a, file_b",
        [
            ("frontend/app.js", "backend/server.py"),  # different top-level
            ("src/a.py", "lib/b.py"),                   # different top-level
            ("alpha/beta/a.py", "gamma/delta/b.py"),    # deeply separate
        ],
    )
    def test_unrelated_score_0_0(self, file_a: str, file_b: str):
        assert directory_affinity_score(file_a, file_b) == 0.0

    def test_top_level_dirs_not_siblings(self):
        """Two top-level directories are NOT considered siblings (grandparent='')."""
        score = directory_affinity_score("frontend/a.py", "backend/b.py")
        assert score == 0.0


# ---------------------------------------------------------------------------
# directory_affinity_score — edge cases
# ---------------------------------------------------------------------------


class TestDirectoryAffinityEdgeCases:
    """Edge cases for directory_affinity_score."""

    def test_identical_files(self):
        """Same file => same directory => 1.0."""
        assert directory_affinity_score("src/app.py", "src/app.py") == 1.0

    def test_backslash_normalized(self):
        """Windows backslashes are normalised."""
        assert directory_affinity_score(
            "src\\auth\\login.py", "src\\auth\\utils.py"
        ) == 1.0

    def test_root_level_both(self):
        """Both at root => same directory => 1.0."""
        assert directory_affinity_score("a.py", "b.py") == 1.0

    def test_symmetry(self):
        """Affinity is symmetric: score(a, b) == score(b, a)."""
        pairs = [
            ("src/auth/a.py", "src/users/b.py"),
            ("pkg/mod.py", "mod.py"),
            ("src/a.py", "lib/b.py"),
        ]
        for a, b in pairs:
            assert directory_affinity_score(a, b) == directory_affinity_score(b, a)
