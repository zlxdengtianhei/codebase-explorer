"""Unit boundaries: a function-valued object property is a unit of its own range, and
only declarations of one name in one scope are one explained symbol."""
from __future__ import annotations

from pathlib import Path

from cbe.source_context import build_context
from cbe.symbols import batch_table, inventory_from_context


def _table(tmp_path: Path, name: str, source: str) -> tuple[list[dict], dict]:
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
