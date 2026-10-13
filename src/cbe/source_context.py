"""Multi-language source chunking and the unified graph + source context.

This module is the source-context half of the public ``cbe-context/1``
contract consumed by the generation pipeline: byte-exact source chunks plus
an optional standard ``cbe-graph/1`` analysis graph.  It turns a repository
into a byte-exact, non-overlapping partition of source chunks (functions,
classes, methods, types, module residue) and combines those chunks with a
standard graph object.

Design rules that the implementation follows:

* Chunks partition the original UTF-8 bytes exactly once.  Concatenating the
  chunks of one file in ``start_byte`` order reproduces the decoded source
  byte-for-byte.  A nested declaration is its own chunk, so a class chunk
  never repeats its method bodies; ancestor names, signatures and the full
  syntactic range stay in metadata.
* Oversized exclusive regions are split at grammar child boundaries only.
  A segment boundary is always a real syntax-tree boundary, never a character
  prefix cut.
* Unknown languages, a missing grammar package, a UTF-8 decode failure and a
  parse error are all distinguishable from "success with empty source".  A
  parse error still yields a full-coverage partition plus a diagnostic.
* Only tree-sitter grammars do the parsing.  The glue here maps grammar node
  kinds to chunk kinds and maps byte/char/line coordinates; it does not
  re-implement any language analysis.
* Graphs are consumed, never built.  A graph whose ``source_manifest`` drifts
  from the current source is rejected with a locatable error.
"""

from __future__ import annotations

import bisect
import json
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from cbe.ir import OffsetMap, canonical_symbol_id, line_starts, sha256_bytes, sha256_text

SCHEMA_CONTEXT = "cbe-context/1"
SCHEMA_GRAPH = "cbe-graph/1"

#: Default target for a single chunk segment.  A segment never exceeds this
#: value unless one indivisible grammar token is larger.
DEFAULT_MAX_SEGMENT_BYTES = 32 * 1024

#: Files larger than this are skipped during discovery (not during an explicit
#: ``paths`` request) and reported with ``file_too_large``.
MAX_FILE_BYTES = 8 * 1024 * 1024

#: Reused from ``cbe.inventory`` so discovery keeps the project's own proof of
#: which directories are caches or environments.
from cbe.inventory import DEFAULT_EXCLUDE_DIR_NAMES  # noqa: E402  (after constants)

_IDENTIFIER_TYPES = frozenset(
    {
        "identifier",
        "type_identifier",
        "field_identifier",
        "property_identifier",
        "private_property_identifier",
        "namespace_identifier",
        "package_identifier",
        "constant",
        "operator_name",
        "destructor_name",
        "scoped_identifier",
        "simple_identifier",
    }
)

_SIGNATURE_LIMIT = 400

#: Suffixes that are valid in more than one registered grammar.  The first
#: candidate is the default; a real diagnostic states the chosen parse so a C
#: header is never silently documented as the wrong language.
AMBIGUOUS_SUFFIXES: dict[str, tuple[str, ...]] = {".h": ("c", "cpp")}


# ---------------------------------------------------------------------------
# Grammar registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GrammarSpec:
    """A tree-sitter grammar plus the node kinds that mean "chunk boundary"."""

    name: str
    suffixes: tuple[str, ...]
    module: str
    attr: str
    #: node type -> cbe chunk kind for function-like declarations
    function_kinds: dict[str, str]
    #: node type -> cbe chunk kind for class-like declarations
    class_kinds: dict[str, str]
    #: transparent wrappers whose span extends the declaration they contain
    wrappers: frozenset[str]
    #: expression node types that become a declaration when bound to a name
    value_function_kinds: frozenset[str]
    #: node types that bind a value to a name (``const f = () =>``)
    binding_kinds: frozenset[str] = frozenset()
    #: grammar provenance: ``official`` (tree-sitter org) or ``community``
    provenance: str = "official"
    #: Joern native frontends that already provide this language in the graph
    #: backend, so the source interface covers the same set without a plugin.
    joern_frontends: tuple[str, ...] = ()


#: Frontend coverage for the languages already registered above.
_JOERN_FRONTENDS: dict[str, tuple[str, ...]] = {
    "c": ("c2cpg",),
    "cpp": ("c2cpg",),
    "python": ("pysrc2cpg",),
    "javascript": ("jssrc2cpg",),
    "typescript": ("jssrc2cpg",),
    "tsx": ("jssrc2cpg",),
    "java": ("javasrc2cpg",),
    "go": ("gosrc2cpg",),
}


_VARIABLE_FUNCTION_VALUES = frozenset(
    {"arrow_function", "function_expression", "generator_function", "function"}
)

GRAMMARS: tuple[GrammarSpec, ...] = (
    GrammarSpec(
        name="c",
        suffixes=(".c", ".h"),
        module="tree_sitter_c",
        attr="language",
        function_kinds={"function_definition": "function"},
        class_kinds={
            "struct_specifier": "struct",
            "union_specifier": "union",
            "enum_specifier": "enum",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
    ),
    GrammarSpec(
        name="cpp",
        suffixes=(".cc", ".cpp", ".cxx", ".c++", ".hh", ".hpp", ".hxx", ".h++", ".inl"),
        module="tree_sitter_cpp",
        attr="language",
        function_kinds={"function_definition": "function"},
        class_kinds={
            "class_specifier": "class",
            "struct_specifier": "struct",
            "union_specifier": "union",
            "enum_specifier": "enum",
            "namespace_definition": "namespace",
        },
        wrappers=frozenset({"template_declaration"}),
        value_function_kinds=frozenset(),
        binding_kinds=frozenset(),
    ),
    GrammarSpec(
        name="python",
        suffixes=(".py",),
        module="tree_sitter_python",
        attr="language",
        function_kinds={"function_definition": "function"},
        class_kinds={"class_definition": "class"},
        wrappers=frozenset({"decorated_definition"}),
        value_function_kinds=frozenset(),
    ),
    GrammarSpec(
        name="javascript",
        suffixes=(".js", ".jsx", ".mjs", ".cjs"),
        module="tree_sitter_javascript",
        attr="language",
        function_kinds={
            "function_declaration": "function",
            "generator_function_declaration": "function",
            "method_definition": "method",
        },
        class_kinds={"class_declaration": "class", "class": "class"},
        wrappers=frozenset(
            {"export_statement", "ambient_declaration", "lexical_declaration", "variable_declaration"}
        ),
        value_function_kinds=_VARIABLE_FUNCTION_VALUES,
        binding_kinds=frozenset({"variable_declarator"}),
    ),
    GrammarSpec(
        name="typescript",
        suffixes=(".ts", ".mts", ".cts"),
        module="tree_sitter_typescript",
        attr="language_typescript",
        function_kinds={
            "function_declaration": "function",
            "generator_function_declaration": "function",
            "function_signature": "function",
            "method_signature": "method",
            "method_definition": "method",
        },
        class_kinds={
            "class_declaration": "class",
            "abstract_class_declaration": "class",
            "interface_declaration": "interface",
            "enum_declaration": "enum",
            "type_alias_declaration": "type_alias",
        },
        wrappers=frozenset(
            {"export_statement", "ambient_declaration", "lexical_declaration", "variable_declaration", "declare_statement"}
        ),
        value_function_kinds=_VARIABLE_FUNCTION_VALUES,
        binding_kinds=frozenset({"variable_declarator"}),
    ),
    GrammarSpec(
        name="java",
        suffixes=(".java",),
        module="tree_sitter_java",
        attr="language",
        function_kinds={
            "method_declaration": "method",
            "constructor_declaration": "constructor",
        },
        class_kinds={
            "class_declaration": "class",
            "interface_declaration": "interface",
            "enum_declaration": "enum",
            "annotation_type_declaration": "annotation",
            "record_declaration": "record",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
    ),
    GrammarSpec(
        name="go",
        suffixes=(".go",),
        module="tree_sitter_go",
        attr="language",
        function_kinds={
            "function_declaration": "function",
            "method_declaration": "method",
        },
        class_kinds={"type_declaration": "type"},
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
    ),
    # --- Joern extra native frontends, wired with mature tree-sitter grammars ---
    GrammarSpec(
        name="ruby",
        suffixes=(".rb", ".rake", ".gemspec", ".ru"),
        module="tree_sitter_ruby",
        attr="language",
        function_kinds={"method": "function", "singleton_method": "method"},
        class_kinds={"class": "class", "module": "module", "singleton_class": "class"},
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        joern_frontends=("rubysrc2cpg",),
    ),
    GrammarSpec(
        name="rust",
        suffixes=(".rs",),
        module="tree_sitter_rust",
        attr="language",
        function_kinds={"function_item": "function"},
        class_kinds={
            "struct_item": "struct",
            "enum_item": "enum",
            "union_item": "union",
            "impl_item": "impl",
            "trait_item": "trait",
            "mod_item": "module",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        joern_frontends=("rust2cpg",),
    ),
    GrammarSpec(
        name="php",
        suffixes=(".php", ".phtml"),
        module="tree_sitter_php",
        attr="language_php",
        function_kinds={"function_definition": "function", "method_declaration": "method"},
        class_kinds={
            "class_declaration": "class",
            "interface_declaration": "interface",
            "trait_declaration": "trait",
            "enum_declaration": "enum",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        joern_frontends=("php2cpg",),
    ),
    GrammarSpec(
        name="c_sharp",
        suffixes=(".cs",),
        module="tree_sitter_c_sharp",
        attr="language",
        function_kinds={
            "method_declaration": "method",
            "constructor_declaration": "constructor",
            "destructor_declaration": "destructor",
            "local_function_statement": "function",
            "operator_declaration": "method",
        },
        class_kinds={
            "class_declaration": "class",
            "interface_declaration": "interface",
            "struct_declaration": "struct",
            "enum_declaration": "enum",
            "record_declaration": "record",
            "namespace_declaration": "namespace",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        joern_frontends=("csharpsrc2cpg",),
    ),
    GrammarSpec(
        name="kotlin",
        suffixes=(".kt", ".kts"),
        module="tree_sitter_kotlin",
        attr="language",
        function_kinds={"function_declaration": "function", "secondary_constructor": "constructor"},
        class_kinds={"class_declaration": "class", "object_declaration": "object", "companion_object": "object"},
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        provenance="community",
        joern_frontends=("kotlin2cpg",),
    ),
    GrammarSpec(
        name="swift",
        suffixes=(".swift",),
        module="tree_sitter_swift",
        attr="language",
        function_kinds={
            "function_declaration": "function",
            "init_declaration": "constructor",
            "deinit_declaration": "destructor",
            "protocol_function_declaration": "method",
        },
        class_kinds={
            "class_declaration": "class",
            "protocol_declaration": "protocol",
            "extension_declaration": "extension",
            "enum_declaration": "enum",
        },
        wrappers=frozenset(),
        value_function_kinds=frozenset(),
        provenance="community",
        joern_frontends=("swiftsrc2cpg",),
    ),
)

# TSX shares the TypeScript package but a different language function.
_TSX_SPEC = GrammarSpec(
    name="tsx",
    suffixes=(".tsx",),
    module="tree_sitter_typescript",
    attr="language_tsx",
    function_kinds=GRAMMARS[4].function_kinds,
    class_kinds=GRAMMARS[4].class_kinds,
    wrappers=GRAMMARS[4].wrappers,
    value_function_kinds=_VARIABLE_FUNCTION_VALUES,
    binding_kinds=frozenset({"variable_declarator"}),
)

#: Extra specs added at runtime by ``register_language`` or a ``cbe.languages``
#: entry point.  This is the unified extension seam: a grammar pack makes a
#: natively supported extra language visible without editing this module.
_EXTRA_SPECS: dict[str, GrammarSpec] = {}
_PLUGIN_ERRORS: list[dict[str, Any]] = []
_PLUGINS_LOADED = False


def register_language(spec: GrammarSpec) -> None:
    """Register or replace a grammar spec for the shared chunking path.

    A grammar pack can call this directly, or publish a ``cbe.languages``
    entry point whose target is a ``GrammarSpec`` or a zero-argument factory.
    Registering a suffix that a built-in already owns replaces it, so a project
    can say ``.h`` means C++ without forking the product module.
    """

    if not isinstance(spec, GrammarSpec):
        raise TypeError("register_language expects a GrammarSpec")
    _EXTRA_SPECS[spec.name] = spec


def _ensure_plugins() -> None:
    global _PLUGINS_LOADED
    if _PLUGINS_LOADED:
        return
    _PLUGINS_LOADED = True
    try:
        from importlib.metadata import entry_points

        try:
            selected = entry_points(group="cbe.languages")
        except TypeError:  # pragma: no cover - old importlib API
            selected = entry_points().get("cbe.languages", [])  # type: ignore[attr-defined]
    except Exception:
        return
    for entry in selected:
        try:
            loaded = entry.load()
            spec = loaded() if callable(loaded) else loaded
            if isinstance(spec, GrammarSpec):
                register_language(spec)
            else:
                _PLUGIN_ERRORS.append(
                    {
                        "entry_point": getattr(entry, "name", str(entry)),
                        "error": f"expected a GrammarSpec, got {type(spec).__name__}",
                    }
                )
        except Exception as exc:
            _PLUGIN_ERRORS.append(
                {
                    "entry_point": getattr(entry, "name", str(entry)),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue


def _all_specs() -> tuple[GrammarSpec, ...]:
    _ensure_plugins()
    ordered: dict[str, GrammarSpec] = {}
    for spec in (*GRAMMARS, _TSX_SPEC, *_EXTRA_SPECS.values()):
        ordered[spec.name] = spec
    return tuple(ordered.values())


def _grammar_for_suffix(suffix: str) -> GrammarSpec | None:
    suffix = suffix.lower()
    _ensure_plugins()
    # Registered/plugin specs win over built-ins so a project can remap an
    # ambiguous suffix (for example ``.h`` to C++) without editing this module.
    for spec in (*_EXTRA_SPECS.values(), *GRAMMARS, _TSX_SPEC):
        if suffix in spec.suffixes:
            return spec
    return None


def language_for_path(path: str | os.PathLike[str]) -> str | None:
    """Return the CBE language name for a path, or ``None`` if unsupported."""

    suffix = PurePosixPath(str(path)).suffix
    spec = _grammar_for_suffix(suffix)
    return spec.name if spec is not None else None


_LOADED_LANGUAGES: dict[tuple[str, str, str], Any] = {}


def _load_language(spec: GrammarSpec) -> Any:
    # Cache by grammar identity, not by name: replacing a registered spec with
    # a different module must actually select the new grammar.
    key = (spec.name, spec.module, spec.attr)
    cached = _LOADED_LANGUAGES.get(key)
    if cached is not None:
        return cached
    # Import here so a missing grammar package is a per-language diagnostic,
    # not a module import failure.
    import importlib

    from tree_sitter import Language

    module = importlib.import_module(spec.module)
    capsule = getattr(module, spec.attr)
    payload = capsule() if callable(capsule) else capsule
    try:
        language = Language(payload)
    except TypeError:  # tree-sitter < 0.25 needs the name as a second argument
        language = Language(payload, spec.name)
    _LOADED_LANGUAGES[key] = language
    return language


def _make_parser(spec: GrammarSpec) -> Any:
    from tree_sitter import Parser

    language = _load_language(spec)
    try:
        return Parser(language)
    except TypeError:
        parser = Parser()
        setter = getattr(parser, "set_language", None)
        if setter is None:
            raise
        setter(language)
        return parser


def _grammar_version(spec: GrammarSpec) -> str:
    try:
        import importlib

        module = importlib.import_module(spec.module)
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version(spec.module.replace("_", "-"))
        except PackageNotFoundError:
            return str(getattr(module, "__version__", "unknown"))
    except Exception:
        return "unknown"


def available_languages() -> dict[str, Any]:
    """Capability discovery for product consumers.

    Returns every registered language, its suffixes, grammar package and
    whether that grammar is importable in the current environment.  Consumers
    must not hard-code the priority list: languages added to the registry show
    up here and flow through the same chunking path.
    """

    languages: list[dict[str, Any]] = []
    for spec in _all_specs():
        entry: dict[str, Any] = {
            "name": spec.name,
            "suffixes": list(spec.suffixes),
            "grammar_module": spec.module,
            "grammar_version": _grammar_version(spec),
            "provenance": spec.provenance,
            "joern_frontends": list(spec.joern_frontends or _JOERN_FRONTENDS.get(spec.name, ())),
            "available": False,
            "error": None,
        }
        try:
            _make_parser(spec)
            entry["available"] = True
        except Exception as exc:  # pragma: no cover - depends on environment
            entry["error"] = f"{type(exc).__name__}: {exc}"
        languages.append(entry)
    return {"schema": SCHEMA_CONTEXT, "languages": languages, "plugin_errors": [dict(item) for item in _PLUGIN_ERRORS]}


def supported_languages() -> dict[str, Any]:
    """Discovery alias for consumers that ask for supported languages.

    Returns the same registry as :func:`available_languages`; it is the single
    authoritative discovery path for the generation driver so no Python-only
    file scan can hide the extra languages.
    """

    return available_languages()


# ---------------------------------------------------------------------------
# Errors and diagnostics
# ---------------------------------------------------------------------------


class ContextError(Exception):
    """A locatable, structured failure that a consumer can catch and report."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.details}


class GraphSourceMismatch(ContextError):
    """A graph's source manifest does not match the current source tree."""

    def __init__(self, path: str, expected: str | None, actual: str | None, reason: str) -> None:
        super().__init__(
            "graph_source_mismatch",
            f"graph/source drift on {path}: {reason}",
            path=path,
            expected=expected,
            actual=actual,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


def _validate_relative(repo: Path, raw: str) -> str:
    """Normalise a repo-relative POSIX path and reject escapes.

    Rejects absolute paths, ``..`` components, and any path that resolves
    (through symlinks) outside the repository root.
    """

    if not isinstance(raw, str) or not raw:
        raise ContextError("invalid_path", f"path must be a non-empty string, got {raw!r}", path=raw)
    candidate = PurePosixPath(raw)
    if candidate.is_absolute():
        raise ContextError("invalid_path", f"absolute path is not allowed: {raw}", path=raw)
    if ".." in candidate.parts:
        raise ContextError("invalid_path", f"path escapes the repository: {raw}", path=raw)
    normalized = candidate.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in ("", "."):
        raise ContextError("invalid_path", f"path does not name a file: {raw}", path=raw)

    repo_real = Path(os.path.realpath(repo))
    target = repo / PurePosixPath(normalized)
    target_real = Path(os.path.realpath(target))
    try:
        target_real.relative_to(repo_real)
    except ValueError:
        raise ContextError(
            "invalid_path",
            f"path resolves outside the repository (symlink escape): {raw}",
            path=raw,
            resolved=str(target_real),
        ) from None
    return normalized


def _iter_source_files(repo: Path, paths: list[str] | None) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (relative paths, diagnostics) for a build request."""

    diagnostics: list[dict[str, Any]] = []
    if paths is not None:
        selected: list[str] = []
        for raw in paths:
            selected.append(_validate_relative(repo, raw))
        return selected, diagnostics

    discovered: list[str] = []
    for root, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(name for name in dirnames if name not in DEFAULT_EXCLUDE_DIR_NAMES)
        rel_root = os.path.relpath(root, repo)
        for filename in sorted(filenames):
            rel = filename if rel_root == "." else f"{rel_root}/{filename}"
            rel = rel.replace(os.sep, "/")
            if _grammar_for_suffix(PurePosixPath(rel).suffix) is None:
                continue
            try:
                # Discovery applies the same escape/symlink validation as
                # explicit ``paths``; a discovered external symlink is skipped
                # with a diagnostic instead of silently read.
                rel = _validate_relative(repo, rel)
            except ContextError as exc:
                diagnostics.append({"path": rel, "code": exc.code, "message": exc.message})
                continue
            full = repo / rel
            try:
                size = full.stat().st_size
            except OSError as exc:
                diagnostics.append({"path": rel, "code": "source_unavailable", "message": str(exc)})
                continue
            if size > MAX_FILE_BYTES:
                diagnostics.append(
                    {
                        "path": rel,
                        "code": "file_too_large",
                        "message": f"{size} bytes exceeds MAX_FILE_BYTES={MAX_FILE_BYTES}",
                    }
                )
                continue
            discovered.append(rel)
    return discovered, diagnostics


# ---------------------------------------------------------------------------
# Tree walking
# ---------------------------------------------------------------------------


@dataclass
class _Declaration:
    node: Any
    kind: str
    name: str
    qualified_name: str
    parent_id: str | None
    symbol_id: str
    start_byte: int
    end_byte: int
    body_start_byte: int
    children: list["_Declaration"] = field(default_factory=list)
    ancestors: tuple[str, ...] = ()
    signature: str = ""


def _text(offsets: OffsetMap, start_byte: int, end_byte: int) -> str:
    return offsets.raw[start_byte:end_byte].decode("utf-8", errors="replace")


def _node_name(offsets: OffsetMap, node: Any) -> str:
    # Field lookup first: most grammars expose the declared name as ``name``.
    name_node = node.child_by_field_name("name") if hasattr(node, "child_by_field_name") else None
    if name_node is not None:
        return _text(offsets, name_node.start_byte, name_node.end_byte)
    # C/C++ function declarators carry the name, not a ``name`` field.  This
    # must run before scanning children, otherwise the return type is picked.
    declarator = node.child_by_field_name("declarator") if hasattr(node, "child_by_field_name") else None
    if declarator is not None:
        found = _first_identifier(offsets, declarator)
        if found:
            return found
    for child in node.named_children:
        if child.type in _IDENTIFIER_TYPES:
            return _text(offsets, child.start_byte, child.end_byte)
    # Go grouped ``type`` declarations nest the name in ``type_spec``.
    for child in node.named_children:
        if child.type in {"type_spec", "function_declarator", "init_declarator"}:
            found = _node_name(offsets, child)
            if found:
                return found
    return ""


def _first_identifier(offsets: OffsetMap, node: Any) -> str:
    for child in node.named_children:
        if child.type in _IDENTIFIER_TYPES or child.type in {"operator_name", "destructor_name"}:
            return _text(offsets, child.start_byte, child.end_byte)
        found = _first_identifier(offsets, child)
        if found:
            return found
    return ""


def _body_start(offsets: OffsetMap, node: Any) -> int:
    if hasattr(node, "child_by_field_name"):
        body = node.child_by_field_name("body")
        if body is not None:
            return body.start_byte
    return -1


def _extract_declarations(spec: GrammarSpec, offsets: OffsetMap, root: Any, path: str) -> list[_Declaration]:
    declarations: list[_Declaration] = []

    def visit(
        node: Any,
        parent: _Declaration | None,
        scope: str | None,
        prefix: list[int | None],
    ) -> None:
        ntype = node.type
        if ntype in spec.wrappers:
            # A wrapper prefix (decorators, ``export``, ``template`` ...) belongs
            # to the first declaration the wrapper contains.  Only that first
            # declaration consumes it, so sibling declarators in a multi-binding
            # statement never copy the wrapper start and never overlap.
            start = prefix[0] if prefix[0] is not None else node.start_byte
            holder: list[int | None] = [start]
            for child in node.named_children:
                visit(child, parent, scope, holder)
            return

        if ntype in spec.class_kinds:
            if not _is_type_definition(spec, node):
                # C/C++ type reference or forward declaration: not a chunk
                # boundary, but still descend in case of nested definitions.
                for child in node.named_children:
                    visit(child, parent, scope, prefix)
                return
            decl = _make_declaration(spec, offsets, node, path, parent, spec.class_kinds[ntype], prefix[0])
            prefix[0] = None
            declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)
            child_scope = scope if decl.kind in {"namespace", "module"} else "class"
            for child in node.named_children:
                visit(child, decl, child_scope, [None])
            return

        if ntype in spec.function_kinds:
            declared = spec.function_kinds[ntype]
            kind = "method" if declared == "function" and scope == "class" else declared
            decl = _make_declaration(spec, offsets, node, path, parent, kind, prefix[0])
            prefix[0] = None
            declarations.append(decl)
            if parent is not None:
                parent.children.append(decl)
            for child in node.named_children:
                visit(child, decl, "function", [None])
            return

        if ntype in spec.binding_kinds:
            value = node.child_by_field_name("value") if hasattr(node, "child_by_field_name") else None
            if value is not None and value.type in spec.value_function_kinds:
                kind = "method" if scope == "class" else "function"
                decl = _make_declaration(spec, offsets, node, path, parent, kind, prefix[0])
                prefix[0] = None
                declarations.append(decl)
                if parent is not None:
                    parent.children.append(decl)
                visit(value, decl, "function", [None])
                return
            # fall through: a plain variable declaration is not a chunk boundary
        for child in node.named_children:
            visit(child, parent, scope, prefix)

    visit(root, None, None, [None])
    return declarations


def _is_type_definition(spec: GrammarSpec, node: Any) -> bool:
    """True when a C/C++ type node actually defines a body.

    ``struct Point p = {...}`` and ``class Foo;`` carry a type node without a
    body and must not split the enclosing function or introduce a chunk.
    Other grammars only emit type declaration nodes for real definitions.
    """

    if spec.name not in {"c", "cpp"}:
        return True
    if hasattr(node, "child_by_field_name") and node.child_by_field_name("body") is not None:
        return True
    return False


def _make_declaration(
    spec: GrammarSpec,
    offsets: OffsetMap,
    node: Any,
    path: str,
    parent: _Declaration | None,
    kind: str,
    extend_start: int | None,
) -> _Declaration:
    start_byte = node.start_byte
    if extend_start is not None:
        start_byte = min(start_byte, extend_start)
    end_byte = node.end_byte
    name = _node_name(offsets, node)
    scope = parent.qualified_name if parent is not None else ""
    qualified = f"{parent.qualified_name}.{name}" if parent is not None and name else (name or scope)
    symbol_id = canonical_symbol_id(path, kind, qualified or name, start_byte)
    ancestors = (parent.ancestors + (parent.qualified_name,)) if parent is not None else ()
    body_start = _body_start(offsets, node)
    if body_start < 0:
        body_start = start_byte
    signature = offsets.raw[start_byte:body_start].decode("utf-8", errors="replace").strip()
    if len(signature) > _SIGNATURE_LIMIT:
        signature = signature[:_SIGNATURE_LIMIT]
    return _Declaration(
        node=node,
        kind=kind,
        name=name or f"<{kind}>",
        qualified_name=qualified or name or f"<{kind}>",
        parent_id=parent.symbol_id if parent is not None else None,
        symbol_id=symbol_id,
        start_byte=start_byte,
        end_byte=end_byte,
        body_start_byte=body_start,
        ancestors=ancestors,
        signature=signature,
    )


# ---------------------------------------------------------------------------
# Chunk construction
# ---------------------------------------------------------------------------


_BODY_CONTAINERS = frozenset(
    {
        "block",
        "statement_block",
        "compound_statement",
        "statement_list",
        "class_body",
        "declaration_list",
        "field_declaration_list",
        "constructor_body",
        "interface_body",
        "enum_body",
        "interface_body",
        "module",
        "program",
        "translation_unit",
        "source_file",
        "body_statement",
        "function_body",
        "protocol_body",
        "statements",
        "compilation_unit",
    }
)


def _collect_named_boundaries(root: Any) -> tuple[list[int], list[int]]:
    """Return (all named-node boundaries, statement-level boundaries).

    Statement-level boundaries are the starts/ends of nodes that sit directly
    in a body/block, so an oversized declaration prefers to cut between
    statements instead of inside an expression.  Both lists are token
    boundaries; splitting on either never cuts inside a lexeme.
    """

    all_boundaries: list[int] = [root.start_byte, root.end_byte]
    statement_boundaries: list[int] = []
    stack = [root]
    while stack:
        node = stack.pop()
        all_boundaries.append(node.start_byte)
        all_boundaries.append(node.end_byte)
        if node.type in _BODY_CONTAINERS:
            for child in node.named_children:
                statement_boundaries.append(child.start_byte)
                statement_boundaries.append(child.end_byte)
        stack.extend(node.named_children)
    return sorted(set(all_boundaries)), sorted(set(statement_boundaries))


def _subtract_ranges(start: int, end: int, holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    kept = [(start, end)]
    for hole_start, hole_end in sorted(holes):
        next_kept: list[tuple[int, int]] = []
        for seg_start, seg_end in kept:
            if hole_end <= seg_start or hole_start >= seg_end:
                next_kept.append((seg_start, seg_end))
                continue
            if seg_start < hole_start:
                next_kept.append((seg_start, hole_start))
            if hole_end < seg_end:
                next_kept.append((hole_end, seg_end))
        kept = next_kept
    return [(seg_start, seg_end) for seg_start, seg_end in kept if seg_end > seg_start]


def _leftover_ranges(total_bytes: int, covered: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if total_bytes <= 0:
        return []
    return _subtract_ranges(0, total_bytes, covered)


def _split_byte_span(
    start: int,
    end: int,
    all_boundaries: list[int],
    statement_boundaries: list[int],
    max_bytes: int,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Split a byte span at grammar boundaries, never inside a token.

    Everything here is in bytes, matching tree-sitter and the chunk contract.
    Returns ``(segments, oversized)``; ``oversized`` holds segments that had
    to exceed ``max_bytes`` because one indivisible grammar token does not
    fit.  The caller turns those into an explicit diagnostic instead of a
    silently over-budget chunk.
    """

    if max_bytes <= 0 or end - start <= max_bytes:
        return [(start, end)], []
    segments: list[tuple[int, int]] = []
    oversized: list[tuple[int, int]] = []
    current = start

    def choose(boundaries: list[int], limit: int) -> int | None:
        lo = bisect.bisect_left(boundaries, start)
        hi = bisect.bisect_right(boundaries, end)
        window = boundaries[lo:hi]
        index = bisect.bisect_right(window, limit) - 1
        while index >= 0:
            candidate = window[index]
            if candidate > current:
                return candidate
            index -= 1
        return None

    while current < end:
        limit = current + max_bytes
        nxt = choose(statement_boundaries, limit)
        if nxt is None:
            nxt = choose(all_boundaries, limit)
        if nxt is None:
            after = bisect.bisect_right(all_boundaries, current)
            nxt = all_boundaries[after] if after < len(all_boundaries) else end
        seg_end = min(nxt, end)
        if seg_end - current > max_bytes:
            oversized.append((current, seg_end))
        segments.append((current, seg_end))
        if seg_end >= end:
            break
        current = seg_end
    return segments, oversized


def _line_of(starts: tuple[int, ...], char_index: int) -> int:
    return bisect.bisect_right(starts, char_index)


@dataclass
class _ChunkPlan:
    path: str
    language: str
    kind: str
    name: str
    qualified_name: str
    symbol_id: str
    parent_id: str | None
    signature: str
    ancestors: tuple[str, ...]
    start_byte: int
    end_byte: int
    full_start_byte: int
    full_end_byte: int
    segment_index: int
    segment_count: int


def _plan_chunks(
    spec: GrammarSpec,
    offsets: OffsetMap,
    declarations: list[_Declaration],
    root: Any,
    path: str,
    language: str,
    max_segment_bytes: int,
) -> tuple[list[_ChunkPlan], list[dict[str, Any]]]:
    total_bytes = len(offsets.raw)
    by_parent: dict[str | None, list[_Declaration]] = {}
    for decl in declarations:
        by_parent.setdefault(decl.parent_id, []).append(decl)

    # Exclusive byte ranges: full span minus the spans of direct child
    # declarations.  Union over all declarations equals the union of the
    # top-level declaration spans (no duplication).
    exclusive: dict[str, list[tuple[int, int]]] = {}
    for decl in declarations:
        holes = [(child.start_byte, child.end_byte) for child in by_parent.get(decl.symbol_id, ())]
        exclusive[decl.symbol_id] = _subtract_ranges(decl.start_byte, decl.end_byte, holes)

    covered = [(decl.start_byte, decl.end_byte) for decl in declarations if decl.parent_id is None]
    residual = _leftover_ranges(total_bytes, covered)

    boundaries, statement_boundaries = _collect_named_boundaries(root)
    max_bytes = max(1, int(max_segment_bytes))
    plans: list[_ChunkPlan] = []
    diagnostics: list[dict[str, Any]] = []

    def record_oversized(ranges: list[tuple[int, int]]) -> None:
        for seg_start, seg_end in ranges:
            diagnostics.append(
                {
                    "path": path,
                    "code": "oversized_token",
                    "message": (
                        f"segment [{seg_start},{seg_end}) is {seg_end - seg_start} bytes, above the "
                        f"{max_bytes}-byte target: one grammar token does not fit and no safe boundary exists"
                    ),
                }
            )

    def add_plan(decl: _Declaration, seg_start: int, seg_end: int, index: int, count: int) -> None:
        plans.append(
            _ChunkPlan(
                path=path,
                language=language,
                kind=decl.kind,
                name=decl.name,
                qualified_name=decl.qualified_name,
                symbol_id=decl.symbol_id,
                parent_id=decl.parent_id,
                signature=decl.signature,
                ancestors=decl.ancestors,
                start_byte=seg_start,
                end_byte=seg_end,
                full_start_byte=decl.start_byte,
                full_end_byte=decl.end_byte,
                segment_index=index,
                segment_count=count,
            )
        )

    for decl in declarations:
        segments: list[tuple[int, int]] = []
        oversized: list[tuple[int, int]] = []
        for rng_start, rng_end in exclusive.get(decl.symbol_id, []):
            part, over = _split_byte_span(rng_start, rng_end, boundaries, statement_boundaries, max_bytes)
            segments.extend(part)
            oversized.extend(over)
        record_oversized(oversized)
        count = len(segments)
        for index, (seg_start, seg_end) in enumerate(segments):
            add_plan(decl, seg_start, seg_end, index, count)

    for rng_start, rng_end in residual:
        segments, oversized = _split_byte_span(rng_start, rng_end, boundaries, statement_boundaries, max_bytes)
        record_oversized(oversized)
        count = len(segments)
        residual_id = canonical_symbol_id(path, "module_residual", "", rng_start)
        for index, (seg_start, seg_end) in enumerate(segments):
            plans.append(
                _ChunkPlan(
                    path=path,
                    language=language,
                    kind="module_residual",
                    name=PurePosixPath(path).name,
                    qualified_name="",
                    symbol_id=residual_id,
                    parent_id=None,
                    signature="",
                    ancestors=(),
                    start_byte=seg_start,
                    end_byte=seg_end,
                    full_start_byte=rng_start,
                    full_end_byte=rng_end,
                    segment_index=index,
                    segment_count=count,
                )
            )

    plans.sort(key=lambda item: (item.start_byte, item.end_byte))
    return plans, diagnostics


def _chunk_from_plan(plan: _ChunkPlan, offsets: OffsetMap, starts: tuple[int, ...]) -> dict[str, Any]:
    text = offsets.raw[plan.start_byte:plan.end_byte].decode("utf-8")
    char_start = offsets.char_of_byte(plan.start_byte)
    char_end = offsets.char_of_byte(plan.end_byte)
    chunk_id = plan.symbol_id
    if plan.segment_count > 1:
        chunk_id = f"{chunk_id}::s{plan.segment_index}"
    return {
        "id": chunk_id,
        "path": plan.path,
        "language": plan.language,
        "kind": plan.kind,
        "name": plan.name,
        "start_line": _line_of(starts, char_start),
        "end_line": _line_of(starts, max(char_start, char_end - 1)),
        "start_byte": plan.start_byte,
        "end_byte": plan.end_byte,
        "text": text,
        "sha256": sha256_text(text),
        # --- additive metadata (DESIGN allows it; required fields keep meaning)
        "symbol_id": plan.symbol_id,
        "parent_id": plan.parent_id,
        "qualified_name": plan.qualified_name,
        "signature": plan.signature,
        "ancestors": list(plan.ancestors),
        "segment_index": plan.segment_index,
        "segment_count": plan.segment_count,
        "full_start_byte": plan.full_start_byte,
        "full_end_byte": plan.full_end_byte,
    }


# ---------------------------------------------------------------------------
# build_context
# ---------------------------------------------------------------------------


def build_context(
    repo: Path | str,
    paths: list[str] | None = None,
    *,
    graph_path: Path | str | None = None,
    max_segment_bytes: int = DEFAULT_MAX_SEGMENT_BYTES,
) -> dict[str, Any]:
    """Freeze one source snapshot and (optionally) a matching standard graph.

    ``paths`` must be repo-relative POSIX paths.  They are validated so they
    can neither escape the repository nor follow an external symlink.
    ``graph_path`` is read and its ``source_manifest`` is checked against the
    current bytes; a mismatch raises :class:`GraphSourceMismatch`.
    """

    repo_path = Path(repo)
    if not repo_path.is_dir():
        raise ContextError("invalid_repo", f"not a directory: {repo_path}", repo=str(repo_path))

    selected, diagnostics = _iter_source_files(repo_path, paths)

    files: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}

    for relative in selected:
        full = repo_path / PurePosixPath(relative)
        try:
            raw = full.read_bytes()
        except OSError as exc:
            diagnostics.append({"path": relative, "code": "source_unavailable", "message": str(exc)})
            continue

        digest = sha256_bytes(raw)
        source_hashes[relative] = digest
        spec = _grammar_for_suffix(PurePosixPath(relative).suffix)
        language = spec.name if spec is not None else _language_from_suffix(relative)

        if spec is None:
            diagnostics.append(
                {
                    "path": relative,
                    "code": "unsupported_language",
                    "message": f"no grammar registered for suffix {PurePosixPath(relative).suffix!r}",
                }
            )
            files.append({"path": relative, "language": language, "sha256": digest})
            continue

        if PurePosixPath(relative).suffix.lower() in AMBIGUOUS_SUFFIXES:
            candidates = AMBIGUOUS_SUFFIXES[PurePosixPath(relative).suffix.lower()]
            explicitly_mapped = any(".h" in extra.suffixes for extra in _EXTRA_SPECS.values())
            if spec.name == candidates[0] and not explicitly_mapped:
                diagnostics.append(
                    {
                        "path": relative,
                        "code": "ambiguous_language",
                        "message": (
                            f"{PurePosixPath(relative).suffix!r} is valid in {', '.join(candidates)}; "
                            f"parsed with {spec.name}. Register a mapping or use a unique extension "
                            "to remove the ambiguity."
                        ),
                    }
                )

        if len(raw) > MAX_FILE_BYTES:
            diagnostics.append(
                {
                    "path": relative,
                    "code": "file_too_large",
                    "message": f"{len(raw)} bytes exceeds MAX_FILE_BYTES={MAX_FILE_BYTES}",
                }
            )
            files.append({"path": relative, "language": language, "sha256": digest})
            continue

        files.append({"path": relative, "language": language, "sha256": digest})

        try:
            offsets = OffsetMap.from_bytes(raw)
        except UnicodeDecodeError as exc:
            diagnostics.append(
                {
                    "path": relative,
                    "code": "decode_error",
                    "message": f"UTF-8 decode failed: {exc}",
                }
            )
            continue

        try:
            parser = _make_parser(spec)
        except Exception as exc:
            diagnostics.append(
                {
                    "path": relative,
                    "code": "grammar_unavailable",
                    "message": f"grammar {spec.module} is not importable: {exc}",
                }
            )
            continue

        try:
            tree = parser.parse(raw)
        except Exception as exc:  # pragma: no cover - grammar-level failure
            diagnostics.append(
                {"path": relative, "code": "parse_error", "message": f"{type(exc).__name__}: {exc}"}
            )
            continue

        root = tree.root_node
        if getattr(root, "has_error", False):
            line = root.start_point[0] + 1
            diagnostics.append(
                {
                    "path": relative,
                    "code": "syntax_error",
                    "message": f"tree contains an ERROR node near line {line}; chunk coverage is preserved",
                }
            )

        declarations = _extract_declarations(spec, offsets, root, relative)
        plans, plan_diagnostics = _plan_chunks(
            spec, offsets, declarations, root, relative, spec.name, max_segment_bytes
        )
        diagnostics.extend(plan_diagnostics)
        starts = line_starts(offsets.text)
        chunks.extend(_chunk_from_plan(plan, offsets, starts) for plan in plans)

    graph: dict[str, Any] | None = None
    graph_status = "not_provided"
    if graph_path is not None:
        graph = _load_graph(Path(graph_path), repo_path, source_hashes)
        graph_status = "provided"

    return {
        "schema": SCHEMA_CONTEXT,
        "files": files,
        "chunks": chunks,
        "graph": graph,
        "graph_status": graph_status,
        "diagnostics": diagnostics,
    }


def _language_from_suffix(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lstrip(".").lower()
    return suffix or "unknown"


# ---------------------------------------------------------------------------
# Graph loading and pruning
# ---------------------------------------------------------------------------


def _graph_source_anchors(payload: dict[str, Any]):
    """Yield every node/edge object that could anchor repo source."""

    for key in ("nodes", "edges"):
        for item in payload.get(key) or []:
            if isinstance(item, dict):
                yield item


def _load_graph(graph_path: Path, repo: Path, frozen_hashes: dict[str, str]) -> dict[str, Any]:
    if not graph_path.exists():
        raise ContextError("graph_missing", f"graph file does not exist: {graph_path}", path=str(graph_path))
    try:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextError("graph_unreadable", f"cannot read graph {graph_path}: {exc}", path=str(graph_path)) from exc
    if not isinstance(payload, dict):
        raise ContextError("graph_schema_unsupported", "graph payload is not an object", path=str(graph_path))
    if payload.get("schema") != SCHEMA_GRAPH:
        raise ContextError(
            "graph_schema_unsupported",
            f"expected schema {SCHEMA_GRAPH!r}, got {payload.get('schema')!r}",
            path=str(graph_path),
        )
    from cbe.graph import GraphError, validate_graph_provenance

    try:
        validate_graph_provenance(repo, payload)
    except (GraphError, OSError) as exc:
        raise ContextError("graph_provenance_mismatch", str(exc), path=str(graph_path)) from exc
    manifest = payload.get("source_manifest")
    if not isinstance(manifest, list):
        raise ContextError(
            "graph_manifest_missing",
            "graph has no source_manifest; cannot prove it matches the source",
            path=str(graph_path),
        )
    manifested: set[str] = set()
    for entry in manifest:
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            raise ContextError(
                "graph_manifest_missing",
                f"malformed source_manifest entry: {entry!r}",
                path=str(graph_path),
            )
        raw_rel = str(entry["path"])
        try:
            rel = _validate_relative(repo, raw_rel)
        except ContextError as exc:
            raise ContextError(
                "graph_source_mismatch",
                f"graph manifest path is not a valid repo path: {raw_rel}: {exc.message}",
                path=raw_rel,
                reason="invalid_path",
            ) from exc
        manifested.add(rel)
        expected = str(entry["sha256"])
        if rel in frozen_hashes:
            # Authority is the hash of the bytes the chunks were built from, so
            # a file changed between the two reads cannot make a stale chunk
            # set look consistent with a matching second read.
            actual = frozen_hashes[rel]
        else:
            target = repo / PurePosixPath(rel)
            try:
                raw = target.read_bytes()
            except OSError:
                raise GraphSourceMismatch(
                    rel, expected, None, "file present in graph manifest is missing on disk"
                ) from None
            actual = sha256_bytes(raw)
        if actual != expected:
            raise GraphSourceMismatch(rel, expected, actual, "content hash differs from current source")

    # A node or edge that anchors real repo source must be covered by the
    # manifest, or the graph mixes snapshots.  Nodes without a repo path (or
    # with a path that is not an existing repo file) stay explicitly
    # external/unknown and are not rejected; a valid empty graph stays valid.
    unmanifested: set[str] = set()
    for anchor in _graph_source_anchors(payload):
        raw_path = anchor.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        try:
            rel = _validate_relative(repo, raw_path)
        except ContextError:
            continue
        if rel in manifested:
            continue
        if (repo / rel).exists():
            unmanifested.add(rel)
    if unmanifested:
        listed = ", ".join(sorted(unmanifested)[:10])
        raise ContextError(
            "graph_unmanifested_source",
            f"graph anchors repo source not covered by source_manifest: {listed}",
            paths=sorted(unmanifested),
        )
    return payload


def _prune_graph(graph: dict[str, Any] | None, selected: set[str]) -> dict[str, Any] | None:
    if graph is None:
        return None
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    by_id = {node.get("id"): node for node in nodes}

    kept_ids: set[str] = {node.get("id") for node in nodes if node.get("path") in selected}
    kept_edges: list[dict[str, Any]] = []
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        source_node = by_id.get(source)
        target_node = by_id.get(target)
        touches = (
            (source_node is not None and source_node.get("path") in selected)
            or (target_node is not None and target_node.get("path") in selected)
        )
        if touches:
            kept_edges.append(edge)
            if source is not None:
                kept_ids.add(source)
            if target is not None:
                kept_ids.add(target)

    kept_nodes = [node for node in nodes if node.get("id") in kept_ids]
    pruned: dict[str, Any] = {
        key: value for key, value in graph.items() if key not in {"nodes", "edges", "source_manifest"}
    }
    pruned["nodes"] = kept_nodes
    pruned["edges"] = kept_edges
    # Keep the full analysis manifest.  A local slice may reference files
    # outside the selection because their nodes are boundary endpoints; a
    # trimmed manifest would misrepresent the provenance of the whole graph.
    pruned["source_manifest"] = list(graph.get("source_manifest", []))
    pruned["scope"] = {
        "paths": sorted(selected),
        "partial": True,
        "edge_filter": "incident_to_selected",
        "note": "Boundary/external nodes kept; relationships outside the selection are not shown.",
    }
    return pruned


# ---------------------------------------------------------------------------
# context_for_paths
# ---------------------------------------------------------------------------


def context_for_paths(context: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    """Select a local slice from a frozen context.  Never reads the repository.

    The slice keeps the chunks and files for the requested paths, prunes the
    graph to edges incident to those paths plus their boundary/external
    endpoints, and marks the result as partial so a consumer cannot mistake it
    for a complete relationship set.
    """

    if not isinstance(context, dict) or context.get("schema") != SCHEMA_CONTEXT:
        raise ContextError(
            "invalid_context",
            f"expected a {SCHEMA_CONTEXT!r} context object",
        )
    selected: set[str] = set()
    for raw in paths:
        candidate = PurePosixPath(str(raw))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ContextError("invalid_path", f"path escapes the context scope: {raw}", path=str(raw))
        selected.add(candidate.as_posix())

    chunks = [chunk for chunk in context.get("chunks", []) if chunk.get("path") in selected]
    files = [item for item in context.get("files", []) if item.get("path") in selected]
    diagnostics = [item for item in context.get("diagnostics", []) if item.get("path") in selected]

    return {
        "schema": SCHEMA_CONTEXT,
        "files": files,
        "chunks": chunks,
        "graph": _prune_graph(context.get("graph"), selected),
        "graph_status": context.get("graph_status", "not_provided"),
        "diagnostics": diagnostics,
        "scope": {"paths": sorted(selected), "partial": True},
    }
