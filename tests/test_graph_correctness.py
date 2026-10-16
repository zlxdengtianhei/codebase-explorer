"""Regression cases for graph correctness, independent of analyzer installations."""
from pathlib import Path

from cbe.graph import _prefer_resolved_imports
from cbe.graph_backends._imports import ImportResolver, import_token, resolve_declarations


def test_python_declarations_resolve_namespace_packages_and_dependencies(tmp_path):
    for path in ("pkg/__init__.py", "pkg/main.py", "pkg/ns/util.py"):
        full = tmp_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.touch()
    resolver = ImportResolver(tmp_path)
    assert resolver.resolve("pkg/main.py", "from .ns.util import helper") == [("resolved", "pkg/ns/util.py")]
    assert resolver.resolve("pkg/main.py", "from .ns import util") == [("resolved", "pkg/ns/util.py")]
    assert resolver.resolve("pkg/main.py", "from pkg import main as m") == [("resolved", "pkg/main.py")]
    assert resolver.resolve("pkg/main.py", "import os, third_party") == [("external", "os"), ("external", "third_party")]
    assert resolver.resolve("pkg/main.py", "from .missing import x") == [("unresolved", None)]
    assert resolver.resolve("pkg/main.py", "import pkg.missing") == [("unresolved", None)]
    assert import_token("from .ns.util import helper", ".py") == ".ns.util"
    assert import_token('import x from "./util"', ".js") == "./util"


def test_language_tokens_and_non_python_file_resolution(tmp_path):
    declarations = [(".java", "import java.util.List;", "java.util.List"),
                    (".kt", "import sample.Helper as H", "sample.Helper"),
                    (".cs", "using System.Text;", "System.Text"),
                    (".rb", 'require_relative "helper"', "helper"),
                    (".rs", "use crate::helper::run;", "crate::helper::run"),
                    (".go", 'import alias "fmt"', "fmt"),
                    (".php", r"use Sample\Helper;", r"Sample\Helper"),
                    (".swift", "import Foundation", "Foundation")]
    for suffix, declaration, expected in declarations:
        assert import_token(declaration, suffix) == expected
    for path in ("src/sample/Helper.java", "lib/helper.rb", "src/helper.rs"):
        full = tmp_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.touch()
    resolver = ImportResolver(tmp_path)
    assert resolver.resolve("src/Main.java", "import sample.Helper;") == [("resolved", "src/sample/Helper.java")]
    assert resolver.resolve("src/Main.java", "import java.util.List;") == [("external", "java.util.List")]
    assert resolver.resolve("lib/main.rb", 'require_relative "helper"') == [("resolved", "lib/helper.rb")]
    assert resolver.resolve("lib/main.rb", 'require_relative "missing"') == [("unresolved", None)]
    assert resolver.resolve("src/main.rs", "use crate::helper::run;") == [("resolved", "src/helper.rs")]
    assert resolver.resolve("main.go", 'import "fmt"') == [("external", "fmt")]


def test_include_resolution_is_local_then_unique_and_angle_is_external(tmp_path):
    for path in ("a/local.h", "b/shared.h", "a/duplicate.h", "b/duplicate.h"):
        full = tmp_path / path
        full.parent.mkdir(exist_ok=True)
        full.touch()
    resolver = ImportResolver(tmp_path)
    assert resolver.resolve("a/main.c", '#include "local.h"') == [("resolved", "a/local.h")]
    assert resolver.resolve("a/main.c", '#include "shared.h"') == [("resolved", "b/shared.h")]
    assert resolver.resolve("main.c", '#include "duplicate.h"') == [("unresolved", None)]
    assert resolver.resolve("a/main.c", '#include <local.h>') == [("external", "local.h")]
    assert resolver.resolve("a/main.c", '#include "missing.h"') == [("unresolved", None)]


def test_import_merge_uses_real_target_and_preserves_unresolved_expression(tmp_path):
    (tmp_path / "util.py").touch()
    edges = [dict(id="j", kind="import", backend="joern", path="main.py", source="file:main.py",
                  expression="from util import helper", status="unresolved", target=None),
             dict(id="g", kind="import", backend="grimp", path="main.py", source="file:main.py",
                  expression="util", status="resolved", target="file:util.py"),
             dict(id="missing", kind="import", backend="joern", path="main.py", source="file:main.py",
                  expression="from .missing import x", status="unresolved", target=None)]
    nodes, edges = resolve_declarations(tmp_path, [], edges)
    kept = _prefer_resolved_imports(edges)
    assert {e["id"] for e in kept} == {"g", "missing/0"}
    assert kept[-1]["expression"] == "from .missing import x"
    assert {n["id"] for n in nodes} == {"file:util.py"}


def test_grimp_uses_real_package_paths_and_never_fabricates_files(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from cbe.graph_backends.imports import build_with_grimp

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/__init__.py").touch()
    (tmp_path / "pkg/main.py").touch()
    graph = SimpleNamespace(modules={"pkg", "pkg.main"},
                            find_modules_directly_imported_by=lambda module: {"pkg.main", "pkg.missing", "thirdparty"} if module == "pkg" else set())
    monkeypatch.setitem(sys.modules, "grimp", SimpleNamespace(build_graph=lambda name: graph))
    result = build_with_grimp(tmp_path, ["python"])
    edges = {e["expression"]: e for e in result["edges"]}
    assert edges["pkg.main"]["source"] == "file:pkg/__init__.py"
    assert edges["pkg.main"]["target"] == "file:pkg/main.py"
    assert edges["pkg.main"]["path"] == "pkg/__init__.py"
    assert edges["pkg.missing"]["status"] == "unresolved"
    assert edges["pkg.missing"]["target"] is None
    assert edges["thirdparty"]["target"] == "ext:thirdparty"
    assert edges["thirdparty"]["status"] == "external"
    assert all(not n["id"].startswith("module:") for n in result["nodes"])
    assert all((tmp_path / n["path"]).is_file() for n in result["nodes"] if n.get("path"))
