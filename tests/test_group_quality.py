"""The group-quality check over the published example runs (evaluation/group_quality.py)."""

from __future__ import annotations

import gzip
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "evaluation/group_quality.py"
spec = importlib.util.spec_from_file_location("group_quality", SCRIPT)
group_quality = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(group_quality)


def copy_examples(tmp_path: Path) -> Path:
    for example in (ROOT / "examples").iterdir():
        if (example / "catalog.json.gz").is_file():
            (tmp_path / example.name).mkdir()
            shutil.copy(example / "catalog.json.gz", tmp_path / example.name)
            shutil.copy(example / "summary.json", tmp_path / example.name)
    return tmp_path


def load_catalog(example: Path) -> dict:
    return json.loads(gzip.decompress((example / "catalog.json.gz").read_bytes()))


def save_catalog(example: Path, catalog: dict) -> None:
    (example / "catalog.json.gz").write_bytes(gzip.compress(json.dumps(catalog).encode()))


def set_tree_leaves(example: Path, leaves: int) -> None:
    summary_path = example / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["tree"]["leaves"] = leaves
    summary_path.write_text(json.dumps(summary), encoding="utf-8")


def test_published_examples_pass_the_group_quality_check() -> None:
    assert group_quality.main(["--check", "--examples", str(ROOT / "examples")]) == 0


def test_check_fails_when_summary_leaves_disagree_with_the_catalog(tmp_path: Path) -> None:
    copy_examples(tmp_path)
    summary_path = tmp_path / "cjson/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    del summary["tree"]["leaves"]
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    assert group_quality.main(["--check", "--examples", str(tmp_path)]) == 1


def test_check_fails_when_a_leaf_group_is_split_into_a_single_member_group(
        tmp_path: Path) -> None:
    copy_examples(tmp_path)
    example = tmp_path / "flask"
    catalog = load_catalog(example)
    nodes = catalog["nodes"]
    node = nodes["wsgi-entry-and-request-contexts"]
    parent = node["parent"]
    moved = node["unit_ids"].pop()  # src/flask/app.py::method::Flask.wsgi_app::59470
    nodes[parent]["children"].append("wsgi-entry-point")
    nodes["wsgi-entry-point"] = {
        "title": "WSGI Entry Point",
        "parent": parent,
        "children": [],
        "unit_ids": [moved],
    }
    save_catalog(example, catalog)
    set_tree_leaves(example, 23)
    assert group_quality.main(["--check", "--examples", str(tmp_path)]) == 1


def test_check_fails_when_merged_groups_keep_a_title_the_members_do_not_carry(
        tmp_path: Path) -> None:
    copy_examples(tmp_path)
    example = tmp_path / "cjson"
    catalog = load_catalog(example)
    nodes = catalog["nodes"]
    root = "cjson-json-library"
    # The failure this gate exists for: leaf groups were turned into single-member groups
    # and merged program-style into a few groups that kept an old title whose words the
    # members do not carry. Only one extra low-cover group: the old gate's overall
    # low_cover_groups <= 3 allowance still passed, the per-example baseline gate does not.
    removed = ["core-json-parse-and-print", "item-creation-and-lifecycle",
               "public-header-types-and-macros"]
    pools = {node_id: nodes.pop(node_id)["unit_ids"] for node_id in removed}
    merged = {
        "merged-public-header-types-and-macros":
            ("Public Header Types and Macros", pools["core-json-parse-and-print"]),
        "merged-item-creation-and-lifecycle":
            ("Item Creation and Lifecycle",
             pools["item-creation-and-lifecycle"]
             + pools["public-header-types-and-macros"]),
    }
    for node_id in removed:
        nodes[root]["children"].remove(node_id)
    for node_id, (title, unit_ids) in merged.items():
        nodes[node_id] = {"title": title, "parent": root, "children": [],
                          "unit_ids": unit_ids}
        nodes[root]["children"].append(node_id)
    save_catalog(example, catalog)
    set_tree_leaves(example, 4)
    assert group_quality.main(["--check", "--examples", str(tmp_path)]) == 1
