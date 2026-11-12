"""`cbe query` and `cbe source` take the names the pages show, not only full IDs."""
import json

import pytest

from cbe import cli

GROUP = "grp:app.py-debug-property"
METHOD = "src/app.py::method::App.run::120"
OTHER_RUN = "src/cli.py::function::run::40"


@pytest.fixture
def published(tmp_path):
    """A published example: catalog only. Units carry the page's heading and anchor."""
    units = {
        GROUP: {"id": GROUP, "kind": "group", "explain": "The debug flag.", "anchor": "#u-aaaa11112222",
                "ranges": [{"path": "src/app.py", "lines": [[10, 20]]}]},
        METHOD: {"id": METHOD, "kind": "method", "explain": "Runs the app.", "anchor": "#u-bbbb33334444",
                 "ranges": [{"path": "src/app.py", "lines": [[120, 130]]}]},
    }
    symbols = {METHOD: {"kind": "method", "name": "run", "file": "src/app.py"},
               OTHER_RUN: {"kind": "function", "name": "run", "file": "src/cli.py"},
               "src/cli.py::function::main::90": {"kind": "function", "name": "main", "file": "src/cli.py"}}
    index = {sid: {"how": "unit", "unit": sid, "page": "nodes/app.md", "anchor": units[sid]["anchor"]}
             for sid in units}
    index[OTHER_RUN] = {"how": "index_only"}
    index["src/cli.py::function::main::90"] = {"how": "index_only"}
    (tmp_path / "catalog.json").write_text(json.dumps({
        "units": units, "symbols": symbols, "files": {"src/app.py": {}, "src/cli.py": {}},
        "nodes": {}, "edges": {}, "symbol_index": index,
        "short_names": {GROUP: "app.py-debug-property", METHOD: "App.run"},
    }), encoding="utf-8")
    return tmp_path


def query(run, name, capsys, *extra):
    code = cli.main(["query", "--run-dir", str(run), *extra, "--id", name])
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.mark.parametrize("name,expected", [
    ("app.py-debug-property", GROUP),           # group name as the heading shows it, no grp: prefix
    ("`app.py-debug-property`", GROUP),         # copied with the heading's backticks
    ("App.run", METHOD),                        # unit heading
    ("u-bbbb33334444", METHOD),                 # anchor
    ("#u-aaaa11112222", GROUP),                 # anchor with its hash
    ("main", "src/cli.py::function::main::90"),  # symbol name with one match
])
def test_page_names_resolve_and_say_so(published, capsys, name, expected):
    code, out, err = query(published, name, capsys)
    assert code == 0, err
    first, second = out.splitlines()[:2]
    assert first == f"resolved: {name} -> {expected}"
    assert second.endswith(f"  {expected}")


def test_json_output_records_the_resolution(published, capsys):
    code, out, _ = query(published, "App.run", capsys, "--json")
    assert code == 0
    record = json.loads(out)
    assert record["id"] == METHOD and record["resolved_from"] == "App.run"


def test_a_name_with_several_matches_lists_them_and_does_not_guess(published, capsys):
    code, out, err = query(published, "run", capsys)
    assert code == 2 and out == ""
    assert "run matches 2 IDs" in err
    assert METHOD in err and OTHER_RUN in err


def test_an_unknown_name_keeps_the_old_error(published, capsys):
    code, out, err = query(published, "no_such_thing", capsys)
    assert code == 2 and out == ""
    assert "unknown unit, symbol or file: no_such_thing" in err and "cbe find --run-dir" in err


def test_full_ids_are_unchanged(published, capsys):
    code, out, _ = query(published, METHOD, capsys)
    assert code == 0
    assert not out.startswith("resolved:")
    assert out.splitlines()[0] == f"App.run  {METHOD}"


def test_source_takes_a_page_name(published, capsys):
    import hashlib
    text = "".join(f"line {n}\n" for n in range(1, 140))
    (published / "context.json").write_text(json.dumps({"files": [
        {"path": "src/app.py", "source": text, "sha256": hashlib.sha256(text.encode()).hexdigest()}]}),
        encoding="utf-8")
    code = cli.main(["source", "--run-dir", str(published), "--id", "App.run"])
    out = capsys.readouterr().out
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == f"# resolved: App.run -> {METHOD}"
    assert lines[1] == "# src/app.py:L120-L130" and lines[2] == "120: line 120"
