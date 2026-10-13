"""Backend registry for the public ``cbe-graph/1`` graph analyzer.

Each backend wraps one upstream open-source analyzer and returns a fragment in
the standard node/edge shape.  ``cbe.graph`` merges fragments, owns the schema
and never re-implements language analysis.
"""

from __future__ import annotations

from ._paths import canonical_repo_path
from .imports import (
    DEPCRUISE_LANGUAGES,
    build_with_depcruise,
    build_with_grimp,
    find_depcruise,
)
from .joern import (
    FRONTEND_NAME,
    JOERN_BYTECODE_FRONTENDS,
    JOERN_LANGUAGE_FLAGS,
    JoernError,
    build_with_joern,
    find_joern,
    joern_version,
)

__all__ = [
    "DEPCRUISE_LANGUAGES",
    "FRONTEND_NAME",
    "JOERN_BYTECODE_FRONTENDS",
    "JOERN_LANGUAGE_FLAGS",
    "JoernError",
    "build_with_depcruise",
    "build_with_grimp",
    "build_with_joern",
    "canonical_repo_path",
    "find_depcruise",
    "find_joern",
    "joern_version",
]
