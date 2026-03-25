"""Tests for semantic classification and directory affinity scoring."""

from __future__ import annotations

import pytest

from src.graph.semantic_hints import classify_file, directory_affinity_score


# ---------------------------------------------------------------------------
# classify_file
# ---------------------------------------------------------------------------


class TestClassifyFileTesting:
    """Test classification of testing-related files."""

    def test_test_prefix(self):
        assert classify_file("test_login.py") == "testing"

    def test_test_prefix_nested(self):
        assert classify_file("src/auth/test_oauth.py") == "testing"

    def test_test_suffix(self):
        assert classify_file("login_test.py") == "testing"

    def test_conftest(self):
        assert classify_file("tests/conftest.py") == "testing"

    def test_fixtures_file(self):
        assert classify_file("fixtures.py") == "testing"

    def test_tests_directory(self):
        assert classify_file("tests/helpers.py") == "testing"

    def test_test_directory_singular(self):
        assert classify_file("test/integration/check.py") == "testing"


class TestClassifyFileModels:
    """Test classification of model/schema files."""

    def test_models_file(self):
        assert classify_file("models.py") == "models"

    def test_model_suffix(self):
        assert classify_file("user_model.py") == "models"

    def test_schemas(self):
        assert classify_file("schemas.py") == "models"

    def test_schema_singular(self):
        assert classify_file("schema.py") == "models"

    def test_types_file(self):
        assert classify_file("types.py") == "models"

    def test_models_directory(self):
        assert classify_file("models/user.py") == "models"

    def test_nested_models(self):
        assert classify_file("src/models/account.py") == "models"

    def test_entities(self):
        assert classify_file("entities.py") == "models"


class TestClassifyFileApi:
    """Test classification of API-related files."""

    def test_routes(self):
        assert classify_file("routes.py") == "api"

    def test_views(self):
        assert classify_file("views.py") == "api"

    def test_endpoints(self):
        assert classify_file("endpoints.py") == "api"

    def test_handlers(self):
        assert classify_file("handlers.py") == "api"

    def test_api_directory(self):
        assert classify_file("api/users.py") == "api"

    def test_nested_api(self):
        assert classify_file("src/api/v2/health.py") == "api"

    def test_controllers(self):
        assert classify_file("controllers.py") == "api"


class TestClassifyFileCli:
    """Test classification of CLI-related files."""

    def test_cli_file(self):
        assert classify_file("cli.py") == "cli"

    def test_main_module(self):
        assert classify_file("__main__.py") == "cli"

    def test_commands(self):
        assert classify_file("commands.py") == "cli"

    def test_console(self):
        assert classify_file("console.py") == "cli"

    def test_cli_directory(self):
        assert classify_file("cli/run.py") == "cli"

    def test_main_file(self):
        assert classify_file("main.py") == "cli"


class TestClassifyFileConfig:
    """Test classification of configuration files."""

    def test_config(self):
        assert classify_file("config.py") == "config"

    def test_settings(self):
        assert classify_file("settings.py") == "config"

    def test_constants(self):
        assert classify_file("constants.py") == "config"

    def test_defaults(self):
        assert classify_file("defaults.py") == "config"

    def test_env(self):
        assert classify_file("env.py") == "config"

    def test_config_directory(self):
        assert classify_file("config/production.py") == "config"


class TestClassifyFileUnknown:
    """Test that non-matching files return 'unknown'."""

    def test_generic_module(self):
        assert classify_file("utils.py") == "unknown"

    def test_nested_generic(self):
        assert classify_file("src/auth/login.py") == "unknown"

    def test_init_file(self):
        assert classify_file("__init__.py") == "unknown"

    def test_deeply_nested(self):
        assert classify_file("a/b/c/d/helper.py") == "unknown"


class TestClassifyFileEdgeCases:
    """Test edge cases for file classification."""

    def test_backslash_path(self):
        """Windows-style paths should still work."""
        assert classify_file("tests\\conftest.py") == "testing"

    def test_case_insensitive_stem(self):
        """Classification should be case-insensitive."""
        assert classify_file("Models.py") == "models"

    def test_ambiguous_testing_in_models_dir(self):
        """A test file inside a models directory should match testing first."""
        # testing patterns are checked before models in the ordered dict
        assert classify_file("models/test_user.py") == "testing"

    def test_no_extension(self):
        """File without extension should still classify by stem."""
        assert classify_file("config") == "config"


# ---------------------------------------------------------------------------
# directory_affinity_score
# ---------------------------------------------------------------------------


class TestDirectoryAffinityScoreSameDir:
    """Test affinity for files in the same directory."""

    def test_same_directory(self):
        score = directory_affinity_score("src/auth/login.py", "src/auth/utils.py")
        assert score == 1.0

    def test_root_level(self):
        score = directory_affinity_score("app.py", "utils.py")
        assert score == 1.0

    def test_same_deep_directory(self):
        score = directory_affinity_score("a/b/c/d/x.py", "a/b/c/d/y.py")
        assert score == 1.0


class TestDirectoryAffinityScoreParentChild:
    """Test affinity for parent-child directory relationships."""

    def test_parent_child(self):
        score = directory_affinity_score("src/auth.py", "src/auth/login.py")
        assert score == 0.7

    def test_child_parent(self):
        """Order should not matter."""
        score = directory_affinity_score("src/auth/login.py", "src/auth.py")
        assert score == 0.7

    def test_root_to_one_level(self):
        """Root file vs file one directory deep."""
        score = directory_affinity_score("app.py", "src/main.py")
        assert score == 0.7


class TestDirectoryAffinityScoreSiblings:
    """Test affinity for sibling directories."""

    def test_sibling_dirs(self):
        score = directory_affinity_score("src/auth/login.py", "src/db/models.py")
        assert score == 0.4

    def test_sibling_dirs_symmetric(self):
        a = directory_affinity_score("src/auth/login.py", "src/db/models.py")
        b = directory_affinity_score("src/db/models.py", "src/auth/login.py")
        assert a == b


class TestDirectoryAffinityScoreUnrelated:
    """Test affinity for unrelated directories."""

    def test_different_toplevel(self):
        score = directory_affinity_score("frontend/app.js", "backend/server.py")
        assert score == 0.0

    def test_deep_vs_shallow_unrelated(self):
        score = directory_affinity_score("a/b/c/d.py", "x/y.py")
        assert score == 0.0


class TestDirectoryAffinityScoreBoundary:
    """Test that scores always fall in [0.0, 1.0]."""

    @pytest.mark.parametrize(
        "a, b",
        [
            ("a.py", "b.py"),
            ("x/a.py", "x/b.py"),
            ("x/y/a.py", "x/z/b.py"),
            ("foo/bar/a.py", "baz/qux/b.py"),
            ("a.py", "x/y/z/b.py"),
            ("x/a.py", "y/b.py"),
        ],
    )
    def test_score_in_valid_range(self, a: str, b: str):
        score = directory_affinity_score(a, b)
        assert 0.0 <= score <= 1.0

    @pytest.mark.parametrize(
        "a, b",
        [
            ("a.py", "b.py"),
            ("x/a.py", "x/b.py"),
        ],
    )
    def test_symmetry(self, a: str, b: str):
        assert directory_affinity_score(a, b) == directory_affinity_score(b, a)
