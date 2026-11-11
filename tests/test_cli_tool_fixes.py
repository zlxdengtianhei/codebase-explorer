"""CLI compatibility and helpful invocation failures."""
import json

import pytest

from cbe import cli, docs


@pytest.fixture
def run(tmp_path):
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={},
                units={"grp:LIMIT": {"id": "grp:LIMIT", "kind": "group", "explain": "A limit."}},
                dispositions={}, tree={"nodes": [{"id": "root", "title": "Root", "unit_ids": ["grp:LIMIT"]}]},
                languages={})
    return tmp_path


@pytest.mark.parametrize("command,flag,value", [("find", "--term", "LIMIT"), ("query", "--id", "grp:LIMIT")])
@pytest.mark.parametrize("json_flag", [[], ["--json"]])
def test_positional_matches_flag_bytes(run, capsys, command, flag, value, json_flag):
    prefix = [command, "--run-dir", str(run), *json_flag]
    assert cli.main([*prefix, flag, value]) == 0
    expected = capsys.readouterr().out
    assert cli.main([*prefix, value]) == 0
    assert capsys.readouterr().out == expected
    assert cli.main([*prefix, flag, value, value]) == 0
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize("command,flag", [("find", "--term"), ("query", "--id")])
@pytest.mark.parametrize("values", [[], ["first", "FLAG", "second"]])
def test_missing_or_conflicting_argument_has_example(run, capsys, command, flag, values):
    with pytest.raises(SystemExit) as exc:
        cli.main([command, "--run-dir", str(run), *[flag if v == "FLAG" else v for v in values]])
    assert exc.value.code != 0
    error = capsys.readouterr().err
    assert error.startswith(f"usage: cbe {command} ")
    assert f"example: cbe {command} --run-dir" in error


@pytest.mark.parametrize("command", ["find", "query"])
@pytest.mark.parametrize("arguments", [["LIMIT"], ["--run-dir", "relative", "LIMIT"],
                                        ["--run-dir", "/absolute/run", "--typo", "LIMIT"]])
def test_parser_errors_also_show_example(capsys, command, arguments):
    with pytest.raises(SystemExit) as exc:
        cli.main([command, *arguments])
    assert exc.value.code != 0
    assert f"example: cbe {command} --run-dir" in capsys.readouterr().err


def test_version_uses_installed_command_name(capsys):
    from cbe import __version__
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out == f"cbe {__version__}\n"


def test_unknown_query_suggests_find(run, capsys):
    assert cli.main(["query", "--run-dir", str(run), "LIMIT"]) == 2
    assert "cbe find --run-dir" in capsys.readouterr().err


@pytest.fixture
def published_run(tmp_path):
    """A published example has docs and a catalog, but no frozen source."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "INDEX.md").write_text("# Example\n", encoding="utf-8")
    (tmp_path / "catalog.json").write_text(json.dumps({
        "units": {"unit:1": {"id": "unit:1", "name": "thing", "kind": "function",
                              "ranges": [{"path": "a.py", "lines": [[1, 1]]}]}},
        "symbols": {}, "files": {"a.py": {}}, "nodes": {}, "edges": {},
        "symbol_index": {"unit:1": {"how": "unit", "unit": "unit:1", "node": None,
                                     "page": None, "anchor": None}},
    }), encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("arguments,action", [
    (["source", "--id", "unit:1"], "source lines cannot be printed"),
    (["query", "--id", "unit:1", "--edges", "all"], "raw edges cannot be expanded"),
    (["host", "verify"], "host verification cannot run"),
    (["host", "render"], "host documents cannot be rendered"),
    (["host", "status"], "host run status cannot be read"),
    (["host", "cost"], "host run cost cannot be reported"),
])
def test_published_example_missing_context_has_actionable_error(published_run, capsys, arguments, action):
    command = [*arguments, "--run-dir", str(published_run)]
    assert cli.main(command) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"this directory has no frozen source snapshot (context.json), so {action}; "
        "published examples ship only docs and the catalog — run cbe on a checkout to get a full run directory\n"
    )
    assert "Errno" not in captured.err and "Traceback" not in captured.err


def test_published_example_find_and_query_do_not_need_context(published_run, capsys):
    for arguments in (["find", "thing"], ["query", "--id", "unit:1"]):
        assert cli.main([*arguments, "--run-dir", str(published_run)]) == 0
        captured = capsys.readouterr()
        assert "unit:1" in captured.out
        assert captured.err == ""


def test_host_commands_on_a_directory_that_is_not_a_run_keep_their_own_error(tmp_path, capsys):
    for command in ("status", "verify"):
        assert cli.main(["host", command, "--run-dir", str(tmp_path)]) != 0
        err = capsys.readouterr().err
        assert "published examples" not in err and "host plan" in err
