"""Grammar registration, source discovery, and source coordinates."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_CONTEXT = "cbe-context/1"
SCHEMA_GRAPH = "cbe-graph/1"

#: Default target for a single chunk segment.  A segment never exceeds this
#: value unless one indivisible grammar token is larger.
DEFAULT_MAX_SEGMENT_BYTES = 32 * 1024

#: Files larger than this are skipped during discovery (not during an explicit
#: ``paths`` request) and reported with ``file_too_large``.
MAX_FILE_BYTES = 8 * 1024 * 1024

#: Version-control metadata, dependency caches and tool output: never own source.
#: Folder names such as build/dist/vendor and other dot-directories are *not*
#: proof of third-party or generated code, so they stay enrolled.
DEFAULT_EXCLUDE_DIR_NAMES = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", ".codebase-analysis",
})


#: Suffixes that are valid in more than one registered grammar.  The first
#: candidate is the default; a real diagnostic states the chosen parse so a C
#: header is never silently documented as the wrong language.
AMBIGUOUS_SUFFIXES: dict[str, tuple[str, ...]] = {".h": ("c", "cpp")}



def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    return sha256_bytes(payload.encode("utf-8"))


@dataclass(frozen=True)
class OffsetMap:
    """Byte offset (parser) to character offset for one UTF-8 file; CRLF stays two characters."""

    raw: bytes
    text: str
    byte_to_char: tuple[int, ...]

    @classmethod
    def from_bytes(cls, raw: bytes) -> "OffsetMap":
        text = raw.decode("utf-8")
        byte_to_char: list[int] = [0] * (len(raw) + 1)
        byte_index = 0
        for char_index, char in enumerate(text):
            for _ in char.encode("utf-8"):
                byte_to_char[byte_index] = char_index
                byte_index += 1
        byte_to_char[len(raw)] = len(text)
        return cls(raw=raw, text=text, byte_to_char=tuple(byte_to_char))

    def char_of_byte(self, byte_index: int) -> int:
        if byte_index < 0 or byte_index > len(self.raw):
            raise ValueError(f"byte offset {byte_index} out of range")
        return self.byte_to_char[byte_index]


def line_starts(text: str) -> tuple[int, ...]:
    """Character offsets of each 1-indexed line, keeping CRLF as two characters."""

    starts = [0]
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\r" and index + 1 < length and text[index + 1] == "\n":
            index += 2
            starts.append(index)
        elif char in "\n\r":
            index += 1
            starts.append(index)
        else:
            index += 1
    return tuple(starts)


def canonical_symbol_id(path: str, kind: str, scope: str, anchor: int) -> str:
    """Stable id: path + kind + lexical scope + declaration byte anchor (lines are not identities)."""

    return f"{path}::{kind}::{scope}::{anchor}"



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
    #: node types published as ordinary module-region declarations
    ordinary_declaration_kinds: frozenset[str] = frozenset()
    #: name extraction strategy for ordinary declarations
    ordinary_name_style: str = "node_names"
    #: whether ordinary declarations may be owned by a class scope
    ordinary_in_class_scope: bool = False
    #: C-family scope, error recovery, and declarator rules
    c_declaration_rules: bool = False
    #: recovered declared types that must not become ordinary declarations
    recovery_type_keywords: frozenset[str] = frozenset()
    #: grouped type declarations need one declaration per type spec
    grouped_type_declarations: bool = False
    #: type declarations retain the surrounding scope for their children
    preserve_type_scope: bool = False


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

#: What running Joern 4.0.654 on a real small repository of each language gave.
#: A language that is not listed has not been tried.
_JOERN_TESTED = "Joern 4.0.654"
_CALL_GRAPH: dict[str, dict[str, str]] = {
    **{name: {"status": "works"} for name in ("c", "cpp", "python", "javascript", "typescript", "java", "go", "ruby")},
    "c_sharp": {"status": "known_failure",
                "note": f"{_JOERN_TESTED}: failed on a real 55-file repository (the export script hit a null "
                        "pointer error); a two-file test fixture works"},
    "kotlin": {"status": "known_failure",
               "note": f"{_JOERN_TESTED}: failed on a real 146-file repository (joern-parse: key not found: "
                       "MethodRef); a two-file test fixture works"},
    "php": {"status": "needs_tool", "note": "needs `php` on PATH"},
    "rust": {"status": "needs_tool", "note": "needs `cargo` on PATH and a Cargo project layout"},
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
        ordinary_declaration_kinds=frozenset(
            {"preproc_def", "preproc_function_def", "declaration", "type_definition"}
        ),
        c_declaration_rules=True,
        recovery_type_keywords=frozenset({"class"}),
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
        ordinary_declaration_kinds=frozenset(
            {"preproc_def", "preproc_function_def", "declaration", "type_definition", "alias_declaration"}
        ),
        c_declaration_rules=True,
        recovery_type_keywords=frozenset({"import", "module"}),
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
        ordinary_declaration_kinds=frozenset({"assignment"}),
        ordinary_name_style="python",
        ordinary_in_class_scope=True,
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
        ordinary_declaration_kinds=frozenset({"variable_declarator"}),
        ordinary_name_style="bindings",
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
        ordinary_declaration_kinds=frozenset({"variable_declarator"}),
        ordinary_name_style="bindings",
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
        ordinary_declaration_kinds=frozenset({"field_declaration", "constant_declaration"}),
        ordinary_name_style="fields",
        ordinary_in_class_scope=True,
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
        ordinary_declaration_kinds=frozenset({"var_declaration", "const_declaration"}),
        ordinary_name_style="grouped_names",
        grouped_type_declarations=True,
        preserve_type_scope=True,
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
        ordinary_declaration_kinds=frozenset({"assignment"}),
        ordinary_name_style="constants",
        ordinary_in_class_scope=True,
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
    ordinary_declaration_kinds=GRAMMARS[4].ordinary_declaration_kinds,
    ordinary_name_style=GRAMMARS[4].ordinary_name_style,
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

        selected = entry_points(group="cbe.languages")
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


def _lookup_specs() -> tuple[GrammarSpec, ...]:
    """Specs in suffix-lookup order: registered/plugin specs win over built-ins,
    so a project can remap an ambiguous suffix (for example ``.h`` to C++)
    without editing this module. A built-in replaced by name still answers for
    the suffixes the replacement does not claim."""

    _ensure_plugins()
    return (*_EXTRA_SPECS.values(), *GRAMMARS, _TSX_SPEC)


def _grammar_for_suffix(suffix: str) -> GrammarSpec | None:
    suffix = suffix.lower()
    for spec in _lookup_specs():
        if any(suffix == declared.lower() for declared in spec.suffixes):
            return spec
    return None


def language_name(path: str) -> str:
    """The language CBE records for a path: the grammar's name, else the bare suffix."""

    spec = _grammar_for_suffix(PurePosixPath(path).suffix)
    return spec.name if spec is not None else _language_from_suffix(path)


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
    language = Language(payload)
    _LOADED_LANGUAGES[key] = language
    return language


def _make_parser(spec: GrammarSpec) -> Any:
    from tree_sitter import Parser

    return Parser(_load_language(spec))


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
            "call_graph": dict(_CALL_GRAPH.get(spec.name, {"status": "untested"})),
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


#: Suffixes documented without a grammar: each file becomes one whole-file region.
FALLBACK_SUFFIXES = frozenset({".sql"})


def suffix_languages() -> dict[str, str]:
    """Suffix -> language for every suffix ``_grammar_for_suffix`` recognises.

    Enumerating the lookup's own specs and asking the lookup keeps one rule for
    which suffixes count and which spec wins, for one path and for a whole tree."""

    suffixes = {suffix.lower() for spec in _lookup_specs() for suffix in spec.suffixes}
    return {suffix: _grammar_for_suffix(suffix).name for suffix in sorted(suffixes)}


def registered_suffixes() -> frozenset[str]:
    """Every suffix a registered grammar (built-in or plugin) claims."""

    return frozenset(suffix_languages())


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



def _language_from_suffix(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lstrip(".").lower()
    return suffix or "unknown"


