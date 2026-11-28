"""Unit boundaries: a function-valued object property is a unit of its own range, and
only declarations of one name in one scope are one explained symbol."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from cbe.grammars import _grammar_for_suffix
from cbe.source_context import build_context
from cbe.symbols import batch_table, inventory_from_context


def _table(tmp_path: Path, name: str, source: str) -> tuple[list[dict], dict]:
    spec = _grammar_for_suffix(Path(name).suffix)
    if spec is not None and importlib.util.find_spec(spec.module) is None:
        pytest.skip(f"grammar package {spec.module} not installed")
    (tmp_path / name).write_text(source, encoding="utf-8")
    context = build_context(tmp_path, [name])
    return batch_table([name], inventory_from_context(context, [name])), context


def _rows(table: list[dict]) -> dict[str, dict]:
    return {row["name"]: row for row in table if row["kind"] != "module_residual"}


def _span(row: dict) -> tuple[int, int]:
    return min(a for a, _ in row["lines"]), max(b for _, b in row["lines"])


OBJECT_LITERAL = """\
const x = 1;

export default {
  id: 'p',
  defaults: { a: 1 },
  before: (chart, args) => {
    const a = 1;
    return a;
  },
  other: function (z) {
    return z;
  },
  destroy(chart) {
    return chart;
  },
  late: async (q) => q,
};
"""


def test_a_function_valued_object_property_is_a_unit_with_its_own_range(tmp_path: Path) -> None:
    table, _ = _table(tmp_path, "plugin.js", OBJECT_LITERAL)
    rows = _rows(table)
    # The arrow, function-expression and async-arrow properties are units, like the shorthand method.
    assert {"before", "other", "destroy", "late"} <= set(rows)
    assert all(rows[name]["kind"] == "method" for name in ("before", "other", "destroy", "late"))
    # Each one ends where it ends: the shorthand method no longer takes the whole literal.
    assert _span(rows["before"]) == (6, 9)
    assert _span(rows["other"]) == (10, 12)
    assert _span(rows["destroy"]) == (13, 15)
    assert _span(rows["late"]) == (16, 16)
    # The literal's own lines (head, plain values, closing) stay with the file's module code.
    residual = [row for row in table if row["kind"] == "module_residual"]
    assert len(residual) == 1 and any(a <= 3 <= b and a <= 5 <= b for a, b in residual[0]["lines"])


def test_the_same_property_name_in_two_object_literals_is_two_units(tmp_path: Path) -> None:
    source = ("const a = {\n  go: () => 1,\n};\n\nconst b = {\n  go: () => 2,\n  stop() {\n    return 3;\n  },\n};\n")
    table, _ = _table(tmp_path, "two.js", source)
    go = [row for row in table if row["name"] == "go"]
    assert [_span(row) for row in go] == [(2, 2), (6, 6)]


def test_a_nested_object_literal_property_is_a_unit(tmp_path: Path) -> None:
    source = "export const config = {\n  hooks: {\n    onDone: () => {\n      return 1;\n    },\n  },\n};\n"
    table, _ = _table(tmp_path, "nested.ts", source)
    assert _span(_rows(table)["onDone"]) == (3, 5)


def test_methods_of_different_classes_with_one_name_are_separate_units(tmp_path: Path) -> None:
    source = '''\
class Base:
    def open(self, app):
        """Abstract hook."""
        raise NotImplementedError

    def close(self):
        pass


class Impl(Base):
    def open(self, app):
        return app

    def close(self):
        return None


def open(path):
    return path
'''
    table, _ = _table(tmp_path, "sessions.py", source)
    opens = [row for row in table if row["name"] == "open"]
    assert sorted((row["kind"], _span(row)) for row in opens) == [
        ("function", (18, 19)), ("method", (2, 4)), ("method", (11, 12))]
    assert all(len(row["ids"]) == 1 for row in opens)
    closes = [row for row in table if row["name"] == "close"]
    assert len(closes) == 2 and all(len(row["ids"]) == 1 for row in closes)


def test_the_same_nested_name_under_different_functions_is_separate_units(tmp_path: Path) -> None:
    source = '''\
def one(f):
    def wrapper(*a):
        return f(*a)
    return wrapper


def two(f):
    def wrapper(*a):
        return f(*a, 1)
    return wrapper
'''
    table, _ = _table(tmp_path, "wrap.py", source)
    assert sorted(_span(row) for row in table if row["name"] == "wrapper") == [(2, 3), (8, 9)]


def test_overloads_and_their_implementation_are_still_one_unit(tmp_path: Path) -> None:
    """What the fold is for: the signatures of one function and its body are one symbol."""
    source = '''\
function pick(a: string): string;
function pick(a: number): number;
function pick(a: any): any {
  return a;
}

class Box {
  get(a: string): string;
  get(a: number): number;
  get(a: any): any {
    return a;
  }
}

class Other {
  get(a: string): string {
    return a;
  }
}
'''
    table, _ = _table(tmp_path, "over.ts", source)
    pick = [row for row in table if row["name"] == "pick"]
    assert len(pick) == 1 and len(pick[0]["ids"]) == 3 and _span(pick[0]) == (1, 5)
    gets = sorted((_span(row), len(row["ids"])) for row in table if row["name"] == "get")
    assert gets == [((8, 12), 3), ((16, 18), 1)]  # Box.get is one row of three; Other.get is its own


def test_python_property_setter_stays_with_its_getter(tmp_path: Path) -> None:
    source = '''\
class A:
    @property
    def size(self):
        return 1

    @size.setter
    def size(self, value):
        pass


class B:
    @property
    def size(self):
        return 2
'''
    table, _ = _table(tmp_path, "prop.py", source)
    sizes = sorted((_span(row), len(row["ids"])) for row in table if row["name"] == "size")
    assert sizes == [((2, 8), 2), ((12, 14), 1)]


def test_a_context_frozen_without_scope_fields_still_merges_by_name() -> None:
    chunk = {"path": "a.py", "start_line": 1, "end_line": 2, "text": "x", "kind": "function"}
    context = {"chunks": [{**chunk, "id": "a.py::function::f::0", "name": "f"},
                          {**chunk, "id": "a.py::function::f::9", "name": "f", "start_line": 5, "end_line": 6}],
               "files": [{"path": "a.py", "sha256": "0"}]}
    table = batch_table(["a.py"], inventory_from_context(context, ["a.py"]))
    assert len(table) == 1 and len(table[0]["ids"]) == 2


# One scope rule for every grammar: a declaration is named under what holds it (a class, an interface,
# a namespace, a module, an object literal, an anonymous class, a Go receiver type, the ``A::`` of a
# C++ definition, the type an impl is for). Each case holds two scopes that each declare ``name``.
SCOPES = {
    "python": ("a.py", "class A:\n    def run(self):\n        return 1\n\nclass B:\n    def run(self):\n        return 2\n", "run"),
    "javascript": ("a.js", "class A {\n  run() { return 1; }\n}\nclass B {\n  run() { return 2; }\n}\n", "run"),
    "typescript": ("a.ts", "class A {\n  run(): number { return 1; }\n}\nclass B {\n  run(): number { return 2; }\n}\n", "run"),
    "tsx": ("a.tsx", "class A {\n  run() { return <i/>; }\n}\nclass B {\n  run() { return <b/>; }\n}\n", "run"),
    "java": ("A.java", "class A {\n  void run() {}\n}\nclass B {\n  void run() {}\n}\n", "run"),
    "go": ("a.go", "package p\n\ntype A struct{}\ntype B struct{}\n\nfunc (a *A) Run() int { return 1 }\nfunc (b B) Run() int { return 2 }\n", "Run"),
    "go generic receiver": ("g.go", "package p\n\ntype A[T any] struct{}\ntype B[T any] struct{}\n\nfunc (a *A[T]) Run() {}\nfunc (b *B[T]) Run() {}\n", "Run"),
    "ruby": ("a.rb", "class A\n  def run\n    1\n  end\nend\nmodule B\n  def run\n    2\n  end\nend\n", "run"),
    "ruby blocks": ("a_spec.rb", "describe 'a' do\n  def helper\n    1\n  end\nend\ndescribe 'b' do\n  def helper\n    2\n  end\nend\n", "helper"),
    "c++ class": ("a.cpp", "class A {\npublic:\n  int run() { return 1; }\n};\nclass B {\npublic:\n  int run() { return 2; }\n};\n", "run"),
    "c++ namespace": ("n.cpp", "namespace N1 { int run() { return 1; } }\nnamespace N2 { int run() { return 2; } }\n", "run"),
    "c++ out of class": ("o.cpp", "class A { public: int run(); };\nclass B { public: int run(); };\nint A::run() { return 1; }\nint B::run() { return 2; }\n", "run"),
    "c#": ("a.cs", "class A { void Run() {} }\nclass B { void Run() {} }\n", "Run"),
    "c# namespace": ("n.cs", "namespace P {\n  class A { class In { void Run() {} } }\n  class B { class In { void Run() {} } }\n}\n", "Run"),
    "rust impl": ("a.rs", "struct A;\nstruct B;\nimpl A { fn go(&self) {} }\nimpl B { fn go(&self) {} }\n", "go"),
    "rust trait impl": ("t.rs", "struct A;\nstruct B;\ntrait T { fn f(&self); }\nimpl T for A { fn f(&self) {} }\nimpl T for B { fn f(&self) {} }\n", "f"),
    "rust mod": ("m.rs", "mod m1 { pub fn f() {} }\nmod m2 { pub fn f() {} }\n", "f"),
    "php": ("a.php", "<?php\nclass A { function run() { return 1; } }\nclass B { function run() { return 2; } }\n", "run"),
    "php namespace": ("n.php", "<?php\nnamespace N1 { function f() {} }\nnamespace N2 { function f() {} }\n", "f"),
    "php anonymous class": ("an.php", "<?php\nfunction make() {\n  $a = new class { function run() { return 1; } };\n  $b = new class { function run() { return 2; } };\n}\n", "run"),
    "java anonymous class": ("An.java", "class W {\n  void make() {\n    Runnable a = new Runnable() {\n      public void run() { one(); }\n    };\n    Runnable b = new Runnable() {\n      public void run() { two(); }\n    };\n  }\n}\n", "run"),
    "typescript namespace": ("ns.ts", "namespace N1 { export function f() {} }\nnamespace N2 { export function f() {} }\n", "f"),
    "typescript nested namespace": ("nn.ts", "namespace A.B { export function f() {} }\nnamespace C.B { export function f() {} }\n", "f"),
    "typescript module": ("mod.ts", "module M1 { export function f() {} }\nmodule M2 { export function f() {} }\n", "f"),
    "typescript ambient module": ("d.ts", 'declare module "x" { function f(): void; }\ndeclare module "y" { function f(): void; }\n', "f"),
    "typescript class expression": ("ce.ts", "const A = class {\n  run() { return 1; }\n};\nconst B = class {\n  run() { return 2; }\n};\n", "run"),
    "javascript class expression": ("ce.js", "const A = class {\n  run() { return 1; }\n};\nconst B = class {\n  run() { return 2; }\n};\n", "run"),
    "javascript object literals": ("o.js", "const a = { run() { return 1; } };\nconst b = { run() { return 2; } };\n", "run"),
    "javascript nested function": ("nf.js", "const a = {\n  go() {\n    function inner() { return 1; }\n    return inner();\n  },\n};\nconst b = {\n  go() {\n    function inner() { return 2; }\n    return inner();\n  },\n};\n", "inner"),
    "typescript type literals": ("lit.ts", "function a(x: { f(): void }, y: { f(): void }) {}\n", "f"),
    "java enum constant bodies": ("E.java", "enum E {\n  X { void f() {} },\n  Y { void f() {} };\n}\n", "f"),
    "kotlin enum entry bodies": ("e.kt", "enum class E {\n    X {\n        override fun f() {\n        }\n    },\n    Y {\n        override fun f() {\n        }\n    };\n}\n", "f"),
    "kotlin": ("a.kt", "class A {\n    fun run() {\n    }\n}\nclass B {\n    fun run() {\n    }\n}\n", "run"),
    "kotlin object expression": ("o.kt", "fun make() {\n    val a = object : Runnable {\n        override fun run() {\n        }\n    }\n    val b = object : Runnable {\n        override fun run() {\n        }\n    }\n}\n", "run"),
    "swift": ("a.swift", "class A {\n    func run() {\n    }\n}\nclass B {\n    func run() {\n    }\n}\n", "run"),
}


@pytest.mark.parametrize("language", sorted(SCOPES))
def test_one_name_in_two_scopes_is_two_units_in_every_grammar(tmp_path: Path, language: str) -> None:
    filename, source, name = SCOPES[language]
    table, _ = _table(tmp_path, filename, source)
    rows = [row for row in table if row["name"] == name and row["kind"] in {"function", "method"}]
    assert len(rows) == 2 and all(len(row["ids"]) == 1 for row in rows), rows


def test_a_go_receiver_names_its_method_and_a_plain_function_stays_apart(tmp_path: Path) -> None:
    source = "package p\n\ntype A struct{}\n\nfunc (a *A) Run() int { return 1 }\nfunc Run() int { return 3 }\n"
    table, context = _table(tmp_path, "a.go", source)
    assert sorted((row["kind"], row["name"]) for row in table if row["name"] == "Run") == [("function", "Run"), ("method", "Run")]
    assert {chunk["qualified_name"] for chunk in context["chunks"] if chunk["name"] == "Run"} == {"A.Run", "Run"}


def test_cpp_definitions_of_one_class_are_named_by_the_function_not_the_class(tmp_path: Path) -> None:
    source = "class A { public: int run(); int stop(); };\nint A::run() { return 1; }\nint A::stop() { return 2; }\nvoid f(int) {}\nvoid f(double) {}\n"
    table, context = _table(tmp_path, "o.cpp", source)
    assert sorted(row["name"] for row in table if row["kind"] == "function") == ["f", "run", "stop"]
    assert {chunk["qualified_name"] for chunk in context["chunks"] if chunk["kind"] == "function"} == {"A.run", "A.stop", "f"}
    assert [len(row["ids"]) for row in table if row["name"] == "f"] == [2]  # overloads of one scope are one unit


def test_a_rust_impl_is_named_by_its_trait_and_its_type(tmp_path: Path) -> None:
    source = "struct A;\ntrait T { fn f(&self); }\ntrait U { fn f(&self); }\nimpl A { fn f(&self) {} }\nimpl T for A { fn f(&self) {} }\nimpl U for A { fn f(&self) {} }\n"
    table, _ = _table(tmp_path, "t.rs", source)
    assert sorted(_span(row) for row in table if row["name"] == "f" and row["kind"] == "method") == [(4, 4), (5, 5), (6, 6)]


def test_a_php_namespace_statement_is_no_scope_and_no_unit(tmp_path: Path) -> None:
    table, context = _table(tmp_path, "s.php", "<?php\nnamespace App\\Models;\nclass A { function run() {} }\n")
    assert not [chunk for chunk in context["chunks"] if chunk["kind"] == "namespace"]
    assert [row["name"] for row in table if row["kind"] == "method"] == ["run"]


def test_a_declaration_nested_in_a_function_valued_property_keeps_its_object_literal(tmp_path: Path) -> None:
    source = "const a = {\n  go: () => {\n    const inner = () => 1;\n    return inner();\n  },\n};\nconst b = {\n  go: () => {\n    const inner = () => 2;\n    return inner();\n  },\n};\n"
    table, _ = _table(tmp_path, "np.js", source)
    assert sorted(_span(row) for row in table if row["name"] == "inner") == [(3, 3), (9, 9)]


def test_folds_stay_inside_a_namespace_an_object_literal_and_an_unnamed_class(tmp_path: Path) -> None:
    ns = ("namespace N {\n  export function pick(a: string): string;\n  export function pick(a: number): number;\n"
          "  export function pick(a: any): any { return a; }\n}\n"
          "namespace M {\n  export function pick(a: any): any { return a; }\n}\n")
    table, _ = _table(tmp_path, "ns.ts", ns)
    assert sorted((_span(row), len(row["ids"])) for row in table if row["name"] == "pick") == [((2, 4), 3), ((7, 7), 1)]
    accessors = "const o = {\n  get size() { return 1; },\n  set size(v) {},\n};\nconst p = {\n  get size() { return 2; },\n};\n"
    table, _ = _table(tmp_path, "acc.js", accessors)
    assert sorted((_span(row), len(row["ids"])) for row in table if row["name"] == "size") == [((2, 3), 2), ((6, 6), 1)]
    klass = "export default class {\n  get v() { return 1; }\n  set v(x) {}\n}\n"
    table, _ = _table(tmp_path, "dc.js", klass)
    assert [(_span(row), len(row["ids"])) for row in table if row["name"] == "v"] == [((2, 3), 2)]


def test_the_parts_of_one_long_declaration_in_a_scope_stay_one_unit(tmp_path: Path) -> None:
    body = "".join(f"        x{i} = {i}\n" for i in range(60))
    source = f"class A:\n    def long(self):\n{body}\nclass B:\n    def long(self):\n        return 1\n"
    (tmp_path / "long.py").write_text(source, encoding="utf-8")
    context = build_context(tmp_path, ["long.py"], max_segment_bytes=120)
    assert any("::s1" in chunk["id"] for chunk in context["chunks"])
    longs = [row for row in batch_table(["long.py"], inventory_from_context(context, ["long.py"])) if row["name"] == "long"]
    assert sorted(len(row["ids"]) > 1 for row in longs) == [False, True]


def test_a_context_frozen_with_receiver_less_go_names_still_merges_by_that_name() -> None:
    """A run frozen before the receiver type entered the qualified name keeps its units."""
    chunk = {"path": "a.go", "start_line": 1, "end_line": 2, "text": "x", "kind": "method", "name": "Run",
             "qualified_name": "Run"}
    context = {"chunks": [{**chunk, "id": "a.go::method::Run::1"},
                          {**chunk, "id": "a.go::method::Run::9", "start_line": 5, "end_line": 6}],
               "files": [{"path": "a.go", "sha256": "0"}]}
    assert len(batch_table(["a.go"], inventory_from_context(context, ["a.go"]))) == 1


def test_a_rust_impl_name_has_no_path_separator_in_its_id(tmp_path: Path) -> None:
    table, context = _table(tmp_path, "p.rs", "struct A;\nimpl std::fmt::Display for A { fn fmt(&self) {} }\n")
    assert all("::" not in chunk["qualified_name"] for chunk in context["chunks"]), context["chunks"]
    assert [row["name"] for row in table if row["kind"] == "method"] == ["fmt"]
