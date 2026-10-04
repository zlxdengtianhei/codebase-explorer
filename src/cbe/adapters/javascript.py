"""Tree-sitter JavaScript/JSX adapter sharing the ECMA walker."""

from __future__ import annotations

from cbe.adapters.typescript import normalize_ecma
from cbe.ir import FailureCode, FileIR, OffsetMap, TypedFailure


def _load_js_language():
    try:
        import tree_sitter_javascript as tsjavascript
        from tree_sitter import Language
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(f"tree-sitter javascript is not importable: {exc}") from exc
    return Language(tsjavascript.language())


def make_js_parser():
    from tree_sitter import Parser

    language = _load_js_language()
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        parser.set_language(language)
        return parser


class JavaScriptAdapter:
    language = "javascript"
    backend_id = "tree_sitter_javascript"

    def __init__(self) -> None:
        self._parser = None

    def parser_version(self) -> str:
        try:
            import tree_sitter_javascript as tsjavascript

            return str(getattr(tsjavascript, "__version__", "unknown"))
        except Exception:
            return "unknown"

    def parse(
        self,
        path: str,
        offsets: OffsetMap,
        content_hash: str,
        *,
        language: str | None = None,
    ) -> FileIR | TypedFailure:
        declared = language or self.language
        suffix = path.rsplit(".", 1)[-1].lower() if "." in path else "js"
        if suffix == "jsx":
            from cbe.adapters.typescript import TypeScriptAdapter

            return TypeScriptAdapter().parse(path, offsets, content_hash, language=declared)
        try:
            if self._parser is None:
                self._parser = make_js_parser()
            tree = self._parser.parse(offsets.raw)
        except Exception as exc:
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"tree-sitter failed to parse {path}: {exc}",
                backend_id=self.backend_id,
                language=declared,
            )
        root = tree.root_node
        if getattr(root, "has_error", False):
            return TypedFailure(
                code=FailureCode.PARSE_ERROR,
                message=f"syntax tree contains an error node: {path}",
                backend_id=self.backend_id,
                language=declared,
                details=("normalization stopped before emitting partial success",),
            )
        return normalize_ecma(
            path=path,
            offsets=offsets,
            content_hash=content_hash,
            root=root,
            language=declared,
            backend_id=self.backend_id,
            backend_version=self.parser_version(),
        )
