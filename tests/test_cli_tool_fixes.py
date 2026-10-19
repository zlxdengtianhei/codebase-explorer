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
    assert f"example: cbe {command} --run-dir" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["find", "query"])
@pytest.mark.parametrize("arguments", [["LIMIT"], ["--run-dir", "relative", "LIMIT"],
                                        ["--run-dir", "/absolute/run", "--typo", "LIMIT"]])
def test_parser_errors_also_show_example(capsys, command, arguments):
    with pytest.raises(SystemExit) as exc:
        cli.main([command, *arguments])
    assert exc.value.code != 0
    assert f"example: cbe {command} --run-dir" in capsys.readouterr().err


def test_unknown_query_suggests_find(run, capsys):
    assert cli.main(["query", "--run-dir", str(run), "LIMIT"]) == 2
    assert "cbe find --run-dir" in capsys.readouterr().err
