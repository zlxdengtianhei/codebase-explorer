"""``cbe host verify`` asks that every source file with a printed unit is named on a page.

A page's ``Files:`` line is the reader's only path from a page to a file. The first
budget-page draft cut that line to five names; with several groups on a page the
files it left out were named nowhere, and no test noticed.
"""
from __future__ import annotations

import json
from pathlib import Path

from cbe import docs, source_context
from cbe.symbols import inventory_from_context

FILES = 8


def _render_and_verify(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    for index in range(FILES):
        (repo / "pkg" / f"mod{index}.py").write_text(
            f"def work{index}(value):\n    return value + {index}\n", encoding="utf-8")
    context = source_context.build_context(repo)
    inventory = inventory_from_context(context)
    units, dispositions = {}, {}
    for path, entry in inventory.items():
        for row in entry["symbols"]:
            units[row["id"]] = {"id": row["id"], "kind": row["kind"], "explain": f"{row['name']} adds.",
                                "extras": [], "relations": [], "uncertainties": []}
            dispositions[row["id"]] = {"how": "unit", "unit": row["id"], "reason": "behavior"}
    ids = list(units)
    tree = {"nodes": [{"id": "root", "parent": None, "title": "Root", "capability": "One root.",
                       "summary": "Start here.", "unit_ids": ids}], "depends_on": []}
    run = tmp_path / "run"
    run.mkdir()
    (run / "context.json").write_text(json.dumps(context))
    docs.render(run_dir=run, source_root=repo, inventory=inventory, units=units,
                dispositions=dispositions, tree=tree,
                languages={path: "python" for path in inventory}, context=context)
    checks = docs.verify(run, inventory, units, dispositions, tree)
    return next(check for check in checks if check["check"] == "source_files_named_on_a_page")


def test_every_file_with_a_printed_unit_is_named_on_a_page(tmp_path: Path) -> None:
    check = _render_and_verify(tmp_path)
    assert check["ok"] and check["detail"]["files"] == FILES


def test_a_files_line_cut_to_five_names_turns_the_check_red(tmp_path: Path, monkeypatch) -> None:
    real = docs.files_line
    monkeypatch.setattr(docs, "files_line", lambda counts, shown=None: real(counts, shown=5))
    check = _render_and_verify(tmp_path)
    assert not check["ok"]
    assert len(check["detail"]["unnamed"]) == FILES - 5
