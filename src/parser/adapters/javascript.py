"""JavaScript syntax adapter sharing the ECMAScript normalization core."""

from __future__ import annotations

from src.parser.adapters.typescript import _EcmaScriptSyntaxAdapter


class JavaScriptSyntaxAdapter(_EcmaScriptSyntaxAdapter):
    """Normalize static JS syntax and explicitly bounded heuristic calls."""

    language = "javascript"
    extension = ".js"


__all__ = ["JavaScriptSyntaxAdapter"]
