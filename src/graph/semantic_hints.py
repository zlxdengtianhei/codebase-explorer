"""Semantic classification and directory affinity scoring for codebase files.

Provides classify_file (5 semantic categories) and directory_affinity_score
(0.0-1.0 structural relatedness). Used by the feature-cone rebalancer.
"""

from __future__ import annotations

import posixpath
import re

# Each category maps to (stem_patterns, directory_patterns)
_CATEGORY_PATTERNS: dict[str, tuple[list[str], list[str]]] = {
    "testing": (
        [
            r"^test_",        # test_foo.py
            r"_test$",        # foo_test.py
            r"^tests$",       # tests.py
            r"^testing$",     # testing.py (test utilities / test client)
            r"^conftest$",    # conftest.py
            r"^fixtures$",    # fixtures.py
            r"^factories$",   # factories.py
        ],
        [
            r"^tests?$",      # tests/ or test/
            r"^fixtures$",    # fixtures/
            r"^__tests__$",   # __tests__/
        ],
    ),
    "models": (
        [
            r"^models$",      # models.py
            r"_model$",       # user_model.py
            r"^schemas?$",    # schema.py, schemas.py
            r"^types$",       # types.py
            r"^dataclasses$", # dataclasses.py
            r"^entities$",    # entities.py
        ],
        [
            r"^models$",      # models/
            r"^schemas$",     # schemas/
            r"^entities$",    # entities/
        ],
    ),
    "api": (
        [
            r"^routes$",      # routes.py
            r"^views$",       # views.py
            r"^endpoints$",   # endpoints.py
            r"^handlers$",    # handlers.py
            r"^controllers$", # controllers.py
            r"^api$",         # api.py
        ],
        [
            r"^api$",         # api/
            r"^routes$",      # routes/
            r"^views$",       # views/
            r"^endpoints$",   # endpoints/
            r"^handlers$",    # handlers/
        ],
    ),
    "cli": (
        [
            r"^cli$",         # cli.py
            r"^__main__$",    # __main__.py
            r"^commands$",    # commands.py
            r"^console$",     # console.py
            r"^main$",        # main.py
        ],
        [
            r"^cli$",         # cli/
            r"^commands$",    # commands/
        ],
    ),
    "config": (
        [
            r"^config$",      # config.py
            r"^settings$",    # settings.py
            r"^constants$",   # constants.py
            r"^defaults$",    # defaults.py
            r"^env$",         # env.py
            r"^conf$",        # conf.py
        ],
        [
            r"^config$",      # config/
            r"^settings$",    # settings/
        ],
    ),
}

# Pre-compile patterns for performance
_COMPILED_PATTERNS: dict[str, tuple[list[re.Pattern[str]], list[re.Pattern[str]]]] = {
    category: (
        [re.compile(p, re.IGNORECASE) for p in stem_pats],
        [re.compile(p, re.IGNORECASE) for p in dir_pats],
    )
    for category, (stem_pats, dir_pats) in _CATEGORY_PATTERNS.items()
}



def classify_file(filepath: str) -> str:
    """Classify a file into a semantic category based on naming patterns.

    Examines both the file stem (basename without extension) and every
    directory component in the path.  The first matching category wins
    (checked in deterministic order: testing, models, api, cli, config).

    Args:
        filepath: Relative file path using forward slashes
                  (e.g. ``"src/auth/test_login.py"``).

    Returns:
        One of ``"testing"``, ``"models"``, ``"api"``, ``"cli"``,
        ``"config"``, or ``"unknown"`` when no pattern matches.
    """
    # Normalise to posix path
    normalised = filepath.replace("\\", "/")

    # Extract stem (basename without extension) and directory parts
    basename = posixpath.basename(normalised)
    stem = posixpath.splitext(basename)[0]
    parts = normalised.split("/")
    dir_parts = parts[:-1]  # all components except the filename

    for category, (stem_regexes, dir_regexes) in _COMPILED_PATTERNS.items():
        # Check stem patterns
        for regex in stem_regexes:
            if regex.search(stem):
                return category

        # Check directory patterns
        for part in dir_parts:
            for regex in dir_regexes:
                if regex.search(part):
                    return category

    return "unknown"


def directory_affinity_score(file_a: str, file_b: str) -> float:
    """Score how related two files are by directory structure.

    Returns a float in ``[0.0, 1.0]``:

    - **1.0** -- same directory
    - **0.7** -- parent-child (one directory level apart)
    - **0.4** -- sibling directories (share the same grandparent)
    - **0.0** -- different top-level directories (no structural affinity)

    Uses ``posixpath`` for cross-platform path handling.

    Args:
        file_a: Relative file path (e.g. ``"src/auth/login.py"``).
        file_b: Relative file path (e.g. ``"src/auth/utils.py"``).

    Returns:
        Affinity score between 0.0 and 1.0.
    """
    dir_a = posixpath.dirname(file_a.replace("\\", "/"))
    dir_b = posixpath.dirname(file_b.replace("\\", "/"))

    # Same directory
    if dir_a == dir_b:
        return 1.0

    # Parent-child: one directory is the direct parent of the other
    if dir_a and dir_b:
        if posixpath.dirname(dir_a) == dir_b or posixpath.dirname(dir_b) == dir_a:
            return 0.7
    elif dir_a and not dir_b:
        # file_b is at root, dir_a could be one level deep
        if posixpath.dirname(dir_a) == dir_b:  # dir_b is "" (root)
            return 0.7
    elif dir_b and not dir_a:
        if posixpath.dirname(dir_b) == dir_a:  # dir_a is "" (root)
            return 0.7

    # Sibling directories: share the same grandparent (must be non-root).
    # Two top-level directories (grandparent == "") are NOT siblings -- they
    # are separate top-level concerns (e.g. frontend/ vs backend/).
    grandparent_a = posixpath.dirname(dir_a) if dir_a else ""
    grandparent_b = posixpath.dirname(dir_b) if dir_b else ""

    if dir_a and dir_b and grandparent_a == grandparent_b and grandparent_a:
        return 0.4

    # Different top-level directories
    return 0.0
