"""JS/TS import declarations that Joern reports by their first line only.

Joern's code for a multi-line ``import {`` / ``import type {`` declaration stops at the
line break, so the module specifier is not in the expression. Real counts before this
change (CBE 3.0.0rc2, Joern 4.0.654): tsdown 86 of 390 import edges unresolved for this
reason, Chart.js 40 of 298.
"""
from cbe.graph_backends.resolution import resolve_declarations


def _edge(path, line, expression):
    return dict(id=f"{path}:{line}", kind="import", backend="joern", path=path, line=line,
                source=f"file:{path}", expression=expression)


def test_a_multi_line_import_is_read_to_its_specifier(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text(
        "import {\n  one,\n  two,\n} from './b.js'\nimport type {\n  T,\n} from \"./c\";\n"
        "import {\n  x }\nfrom '../outside.js'\n", encoding="utf-8")
    files = {"src/a.ts", "src/b.ts", "src/c.ts"}
    _, edges = resolve_declarations(tmp_path, [], [
        _edge("src/a.ts", 1, "import {"), _edge("src/a.ts", 5, "import type {"),
        _edge("src/a.ts", 8, "import {")], files=files)
    by_line = {edge["line"]: edge for edge in edges}
    assert by_line[1]["status"] == "resolved" and by_line[1]["target"] == "file:src/b.ts"
    assert by_line[5]["status"] == "resolved" and by_line[5]["target"] == "file:src/c.ts"
    assert by_line[8]["status"] == "unresolved"  # a relative path outside the repository stays unresolved
    assert all(edge["expression"].startswith("import") for edge in edges)


def test_a_js_specifier_resolves_to_its_declaration_file(tmp_path):
    files = {"src/core.ts", "src/types/basic.d.ts"}
    _, edges = resolve_declarations(tmp_path, [], [
        _edge("src/core.ts", 1, "import type {AnyObject} from './types/basic.js'")], files=files)
    assert edges[0]["status"] == "resolved" and edges[0]["target"] == "file:src/types/basic.d.ts"


def test_an_unreadable_file_leaves_the_edge_unresolved(tmp_path):
    _, edges = resolve_declarations(tmp_path, [], [_edge("src/gone.js", 3, "import {")],
                                    files={"src/gone.js"})
    assert edges[0]["status"] == "unresolved"
