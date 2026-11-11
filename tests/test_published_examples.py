"""Checks for the self-contained examples shipped in this repository."""

from __future__ import annotations

import gzip
import importlib.util
import json
import re
from pathlib import Path
from types import SimpleNamespace

from cbe.docs import prose_for_links


ROOT = Path(__file__).resolve().parents[1]
PUBLISH_SCRIPT = ROOT / "evaluation/e6-showcase/scripts/publish_example.py"
spec = importlib.util.spec_from_file_location("publish_example", PUBLISH_SCRIPT)
publish_example = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(publish_example)


def test_publish_rewrites_node_catalog_links_to_compressed_catalog(tmp_path: Path) -> None:
    run = tmp_path / "run"
    source = tmp_path / "source"
    example = tmp_path / "example"
    (run / "docs/nodes").mkdir(parents=True)
    source.mkdir()
    page = ("# Node\n\n[external](../../catalog.json)\n"
            "[already compressed](../../catalog.json.gz)\n")
    (run / "docs/nodes/page.md").write_text(page, encoding="utf-8")
    (run / "catalog.json").write_text(json.dumps({"files": {}}), encoding="utf-8")
    (run / "summary.json").write_text("{}\n", encoding="utf-8")

    args = SimpleNamespace(run_dir=run, source=source, example_dir=example, replace=None,
                           source_url_base="https://example.invalid/repository/blob/commit",
                           source_local_dir=None)
    assert publish_example.publish(args) == 0
    assert (example / "docs/nodes/page.md").read_text(encoding="utf-8") == page.replace(
        "](../../catalog.json)", "](../../catalog.json.gz)")
    assert json.loads(gzip.decompress((example / "catalog.json.gz").read_bytes())) == {"files": {}}


def test_example_markdown_relative_links_resolve() -> None:
    broken = []
    for document in (ROOT / "examples").rglob("*.md"):
        text = prose_for_links(document.read_text(encoding="utf-8"))
        references = re.findall(r"^\[[^\]\n]+\]:\s*(\S+)\s*$", text, re.MULTILINE)
        targets = re.findall(r"\]\(([^)\s]+)\)", text) + references
        for target in targets:
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            file_part = target.partition("#")[0]
            if not file_part or Path(file_part).is_absolute():
                continue
            if not (document.parent / file_part).exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not broken, "broken published-example links:\n" + "\n".join(broken)
