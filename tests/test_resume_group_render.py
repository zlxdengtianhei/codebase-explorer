"""Resumed detail can arrive before the responsibility tree is rebuilt."""
from cbe import cli, docs


def test_render_flow_with_new_group_not_owned_by_old_tree(tmp_path):
    units = {uid: {"id": uid, "kind": "group", "explain": "A useful explanation."}
             for uid in ("grp:existing", "grp:format-h-dragon")}
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={}, units=units,
                dispositions={}, languages={},
                tree={"nodes": [{"id": "root", "title": "Root", "unit_ids": ["grp:existing"]}]},
                system={"overview": "Overview", "maintenance_navigation": "Open Root.",
                        "key_flows": [{"name": "Float conversion",
                        "description": "Convert a floating point value.",
                        "steps": ["grp:existing", "grp:format-h-dragon"]}]})
    index = (tmp_path / "docs/INDEX.md").read_text()
    assert "Convert a floating point value." in index
    assert "[existing](nodes/root.md#" in index
    assert "[format-h-dragon](../catalog.json) (not assigned to a node)" in index
    assert docs.query(tmp_path, "grp:format-h-dragon")["page"] is None


def test_cli_labels_unhandled_keyerror(tmp_path, capsys, monkeypatch):
    def missing(*args, **kwargs):
        raise KeyError("grp:format-h-dragon")
    monkeypatch.setattr(docs, "query", missing)
    assert cli.main(["query", "--run-dir", str(tmp_path), "grp:format-h-dragon"]) == 2
    assert capsys.readouterr().err == "内部错误：缺少键 grp:format-h-dragon\n"
