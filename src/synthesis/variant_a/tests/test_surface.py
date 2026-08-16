"""Public-surface resolution: B1 reexport chase, B2 import noise, T3 `from . import json`."""

from __future__ import annotations

import ast
from pathlib import Path

from src.semantic.models import SemanticSymbolKind
from src.synthesis.variant_a.surface import (
    INDEX_NOISE_NAMES,
    _resolve_relative_module,
    entry_bindings,
    extract_public_surface,
    index_noise_names,
    oracle_init_exports,
    resolve_name,
)
from src.synthesis.variant_a.tests.conftest import make_ledger, make_symbol


TRANSPORTS = (
    "ASGITransport",
    "AsyncBaseTransport",
    "WSGITransport",
    "AsyncHTTPTransport",
    "BaseTransport",
    "HTTPTransport",
    "MockTransport",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _httpx_like(tmp_path: Path) -> None:
    _write(
        tmp_path / "__init__.py",
        "from ._api import *\n"
        "from ._client import *\n"
        "from ._transports import *\n"
        "\n"
        "try:\n"
        "    from ._main import main\n"
        "except ImportError:\n"
        "    def main() -> None:\n"
        "        import sys\n"
        "        sys.exit(1)\n"
        "\n"
        "__all__ = ['ASGITransport', 'AsyncBaseTransport', 'WSGITransport', "
        "'AsyncHTTPTransport', 'BaseTransport', 'HTTPTransport', 'MockTransport', "
        "'Client', 'get']\n",
    )
    _write(tmp_path / "_api.py", "def get():\n    return 1\n")
    _write(tmp_path / "_client.py", "class Client:\n    def get(self):\n        pass\n")
    _write(tmp_path / "_main.py", "import sys\n\ndef main():\n    sys.exit(0)\n")
    _write(
        tmp_path / "_transports" / "__init__.py",
        "from .asgi import *\n"
        "from .base import *\n"
        "from .default import *\n"
        "from .mock import *\n"
        "from .wsgi import *\n"
        "\n"
        "__all__ = ['ASGITransport', 'AsyncBaseTransport', 'BaseTransport', "
        "'AsyncHTTPTransport', 'HTTPTransport', 'MockTransport', 'WSGITransport']\n",
    )
    _write(tmp_path / "_transports" / "asgi.py", "class ASGITransport:\n    pass\n")
    _write(tmp_path / "_transports" / "base.py", "class BaseTransport:\n    pass\n\nclass AsyncBaseTransport:\n    pass\n")
    _write(
        tmp_path / "_transports" / "default.py",
        "class HTTPTransport:\n    pass\n\nclass AsyncHTTPTransport:\n    pass\n",
    )
    _write(tmp_path / "_transports" / "mock.py", "class MockTransport:\n    pass\n")
    _write(tmp_path / "_transports" / "wsgi.py", "class WSGITransport:\n    pass\n")


def _httpx_ledger(tmp_path: Path):
    symbols = [
        make_symbol("_api.py", "get", kind=SemanticSymbolKind.FUNCTION),
        make_symbol("_client.py", "Client", kind=SemanticSymbolKind.CLASS),
        make_symbol("_client.py", "Client.get", kind=SemanticSymbolKind.METHOD),
        make_symbol("_transports/asgi.py", "ASGITransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/base.py", "BaseTransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/base.py", "AsyncBaseTransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/default.py", "HTTPTransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/default.py", "AsyncHTTPTransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/mock.py", "MockTransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_transports/wsgi.py", "WSGITransport", kind=SemanticSymbolKind.CLASS),
        make_symbol("_main.py", "main", kind=SemanticSymbolKind.FUNCTION),
    ]
    extra = [
        "__init__.py",
        "_transports/__init__.py",
    ]
    return make_ledger(tmp_path, symbols, extra_files=extra)


def _flask_like(tmp_path: Path) -> None:
    _write(
        tmp_path / "__init__.py",
        "from . import json as json\n"
        "from .app import Flask as Flask\n"
        "from .globals import current_app as current_app\n"
        "from .globals import request as request\n"
        "from .json import jsonify as jsonify\n",
    )
    _write(tmp_path / "app.py", "class Flask:\n    pass\n")
    _write(
        tmp_path / "globals.py",
        "import typing as t\n"
        "from contextvars import ContextVar\n"
        "from werkzeug.local import LocalProxy\n"
        "\n"
        "request = LocalProxy(lambda: None)\n"
        "current_app = LocalProxy(lambda: None)\n"
        "app_ctx = LocalProxy(lambda: None)\n",
    )
    _write(
        tmp_path / "json" / "__init__.py",
        "import typing as t\n"
        "from ..globals import current_app\n"
        "\n"
        "def dumps(obj):\n"
        "    return t.cast(str, obj)\n"
        "\n"
        "def jsonify(*args):\n"
        "    return dumps(args)\n",
    )
    _write(tmp_path / "typing.py", "class AppContext:\n    pass\n")


def _flask_ledger(tmp_path: Path):
    symbols = [
        make_symbol("app.py", "Flask", kind=SemanticSymbolKind.CLASS),
        make_symbol("json/__init__.py", "dumps", kind=SemanticSymbolKind.FUNCTION),
        make_symbol("json/__init__.py", "jsonify", kind=SemanticSymbolKind.FUNCTION),
        make_symbol("typing.py", "AppContext", kind=SemanticSymbolKind.CLASS),
    ]
    extra = ["__init__.py", "globals.py", "json/__init__.py"]
    return make_ledger(tmp_path, symbols, extra_files=extra)


def _root_binding(surface, name: str):
    return next(item for item in surface.bindings if item.path == "__init__.py" and item.name == name)


def _index_names(surface, repo: Path) -> list[str]:
    seen: list[str] = []
    have: set[str] = set()
    for item in entry_bindings(surface):
        if item.name in have:
            continue
        have.add(item.name)
        seen.append(item.name)
    for name, _path in oracle_init_exports(repo):
        if name in have:
            continue
        have.add(name)
        seen.append(name)
    return seen


def test_b1_star_reexport_second_hop_binds_classdef(tmp_path) -> None:
    _httpx_like(tmp_path)
    ledger = _httpx_ledger(tmp_path)
    surface = extract_public_surface(tmp_path, ledger)
    expected = {
        "ASGITransport": "_transports/asgi.py::ASGITransport",
        "AsyncBaseTransport": "_transports/base.py::AsyncBaseTransport",
        "WSGITransport": "_transports/wsgi.py::WSGITransport",
        "AsyncHTTPTransport": "_transports/default.py::AsyncHTTPTransport",
        "BaseTransport": "_transports/base.py::BaseTransport",
        "HTTPTransport": "_transports/default.py::HTTPTransport",
        "MockTransport": "_transports/mock.py::MockTransport",
    }
    for name, symbol_id in expected.items():
        hit = _root_binding(surface, name)
        assert hit.resolved_symbol_ids == (symbol_id,), (name, hit)
        assert hit.target_path == symbol_id.split("::", 1)[0]
        assert hit.target_path != "_api.py"
        assert "class " + name not in (tmp_path / "_api.py").read_text(encoding="utf-8")


def test_b1_first_hop_star_still_resolves_client_and_get(tmp_path) -> None:
    _httpx_like(tmp_path)
    ledger = _httpx_ledger(tmp_path)
    surface = extract_public_surface(tmp_path, ledger)
    client = _root_binding(surface, "Client")
    assert client.resolved_symbol_ids == ("_client.py::Client",)
    assert client.target_path == "_client.py"
    get = _root_binding(surface, "get")
    assert get.resolved_symbol_ids == ("_api.py::get",)
    assert get.target_path == "_api.py"


def test_b1_unresolved_uses_last_hop_not_first_star(tmp_path) -> None:
    _write(
        tmp_path / "__init__.py",
        "from ._api import *\nfrom ._later import *\n\n__all__ = ['Ghost']\n",
    )
    _write(tmp_path / "_api.py", "def get():\n    return 1\n")
    _write(tmp_path / "_later" / "__init__.py", "from .empty import *\n")
    _write(tmp_path / "_later" / "empty.py", "x = 1\n")
    ledger = make_ledger(
        tmp_path,
        [make_symbol("_api.py", "get", kind=SemanticSymbolKind.FUNCTION)],
        extra_files=["__init__.py", "_later/__init__.py", "_later/empty.py"],
    )
    surface = extract_public_surface(tmp_path, ledger)
    ghost = _root_binding(surface, "Ghost")
    assert ghost.resolved_symbol_ids == ()
    assert ghost.target_path != "_api.py"
    assert ghost.target_path == "_later/empty.py"
    assert "unresolved after reexport chase" in ghost.unresolved_reason


def test_b1_negative_control_old_first_star_would_be_red(tmp_path) -> None:
    """Frozen old algorithm on the same fixture is red; chase is green."""

    _httpx_like(tmp_path)
    ledger = _httpx_ledger(tmp_path)
    tree = ast.parse((tmp_path / "__init__.py").read_text(encoding="utf-8"))
    symbol_index: dict[tuple[str, str], list[str]] = {}
    for symbol_id, record in ledger.symbols.items():
        tail = record.qualified_name.rsplit(".", 1)[-1]
        symbol_index.setdefault((record.path, tail), []).append(symbol_id)

    star_files: list[str] = []
    star_hits: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            mod = node.module.lstrip(".") if node.module else ""
            for candidate in (f"{mod}.py", f"{mod}/__init__.py"):
                if (tmp_path / candidate).is_file():
                    star_files.append(candidate)
                    star_hits.extend(symbol_index.get((candidate, "ASGITransport"), []))
    old_target = star_files[0] if star_files else ""
    old_resolved = tuple(dict.fromkeys(star_hits))
    ledger_class = "_transports/asgi.py::ASGITransport"
    old_red = old_resolved == () and old_target == "_api.py" and ledger_class in ledger.symbols
    assert old_red is True

    new_ids, _reason, new_path = resolve_name(
        source_path="__init__.py",
        name="ASGITransport",
        tree=tree,
        repo_root=tmp_path,
        ledger=ledger,
        symbol_index=symbol_index,
    )
    assert new_ids == (ledger_class,)
    assert new_path == "_transports/asgi.py"


def test_b2_stdlib_and_thirdparty_imports_leave_index(tmp_path) -> None:
    _flask_like(tmp_path)
    ledger = _flask_ledger(tmp_path)
    surface = extract_public_surface(tmp_path, ledger)
    names = _index_names(surface, tmp_path)
    assert index_noise_names(names) == ()
    for noise in INDEX_NOISE_NAMES:
        assert noise not in names
    assert "request" in names
    assert "Flask" in names
    assert "jsonify" in names
    assert "current_app" in names


def test_b2_sys_from_nested_init_import_is_dropped(tmp_path) -> None:
    _httpx_like(tmp_path)
    ledger = _httpx_ledger(tmp_path)
    names = {n for n, _p in oracle_init_exports(tmp_path)}
    assert "sys" not in names
    assert "Client" in names or "ASGITransport" in names
    surface = extract_public_surface(tmp_path, ledger)
    index = _index_names(surface, tmp_path)
    assert "sys" not in index
    assert "get" in index
    assert "Client" in index


def test_b2_negative_control_reinjecting_sys_turns_gate_red() -> None:
    clean = {"Client", "get", "request"}
    assert index_noise_names(clean) == ()
    polluted = clean | {"sys"}
    assert index_noise_names(polluted) == ("sys",)


def test_t3_root_from_dot_import_json_resolves_to_package(tmp_path) -> None:
    _flask_like(tmp_path)
    ledger = _flask_ledger(tmp_path)
    # Old relative resolver: empty package → None.
    assert _resolve_relative_module("__init__.py", 1, None) == ""
    surface = extract_public_surface(tmp_path, ledger)
    hit = _root_binding(surface, "json")
    assert hit.target_path == "json/__init__.py"
    assert "cannot resolve" not in hit.unresolved_reason


def test_t3_negative_control_old_resolver_is_none() -> None:
    """The pre-fix empty-pkg_parts branch returned None; that is the red case."""

    # Replicated old predicate: empty parts + no module → fail.
    source_path = "__init__.py"
    level = 1
    module = None
    parts = Path(source_path).parts
    dir_parts = list(parts[:-1])
    pkg_parts = dir_parts
    climb = level - 1
    pkg_parts = pkg_parts[: len(pkg_parts) - climb] if climb else pkg_parts
    if module:
        pkg_parts = [*pkg_parts, *module.split(".")]
    old = None if not pkg_parts else "/".join(pkg_parts)
    assert old is None
    assert _resolve_relative_module(source_path, level, module) == ""


def test_t3_nested_relative_import_stays_in_repo(tmp_path) -> None:
    """``from ..json import dumps`` in json/tag.py must not be treated as stdlib json."""

    _flask_like(tmp_path)
    _write(tmp_path / "json" / "tag.py", "from ..json import dumps\n\nclass JSONTag:\n    pass\n")
    symbols = [
        make_symbol("app.py", "Flask", kind=SemanticSymbolKind.CLASS),
        make_symbol("json/__init__.py", "dumps", kind=SemanticSymbolKind.FUNCTION),
        make_symbol("json/__init__.py", "jsonify", kind=SemanticSymbolKind.FUNCTION),
        make_symbol("json/tag.py", "JSONTag", kind=SemanticSymbolKind.CLASS),
        make_symbol("typing.py", "AppContext", kind=SemanticSymbolKind.CLASS),
    ]
    ledger = make_ledger(
        tmp_path,
        symbols,
        extra_files=["__init__.py", "globals.py", "json/__init__.py", "json/tag.py"],
    )
    assert _resolve_relative_module("json/tag.py", 2, "json") == "json"
    surface = extract_public_surface(tmp_path, ledger)
    names = {(b.path, b.name) for b in surface.bindings}
    assert ("json/tag.py", "dumps") in names


def test_nested_star_module_path_stays_in_package() -> None:
    assert _resolve_relative_module("_transports/asgi.py", 1, "base") == "_transports/base"
    assert _resolve_relative_module("_transports/__init__.py", 1, "asgi") == "_transports/asgi"


def test_t3_named_in_repo_import_still_resolves_jsonify(tmp_path) -> None:
    _flask_like(tmp_path)
    ledger = _flask_ledger(tmp_path)
    surface = extract_public_surface(tmp_path, ledger)
    hit = _root_binding(surface, "jsonify")
    assert hit.resolved_symbol_ids == ("json/__init__.py::jsonify",)
    assert hit.target_path == "json/__init__.py"


def test_entry_bindings_keep_request_drop_contextvar(tmp_path) -> None:
    _flask_like(tmp_path)
    ledger = _flask_ledger(tmp_path)
    surface = extract_public_surface(tmp_path, ledger)
    names = [item.name for item in entry_bindings(surface)]
    assert "request" in names
    assert "ContextVar" not in names
    assert "LocalProxy" not in names
    assert "t" not in names
