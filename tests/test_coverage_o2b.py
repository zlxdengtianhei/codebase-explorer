"""Structural edges must not inflate relationship resolution percentages."""
import re

from cbe import docs


def test_relation_percentages_exclude_structural_edges(tmp_path):
    graph = {
        "schema": "cbe-graph/1",
        "source_manifest": [{"path": "main.py", "language": "python"}],
        "nodes": [{"id": "a", "path": "main.py"}],
        "edges": [dict(id=f"cfg{i}", source="a", target="a", kind="cfg", status="resolved")
                  for i in range(100)]
                 + [dict(id=f"df{i}", source="a", target="a", kind="dataflow", status="resolved")
                    for i in range(100)]
                 + [dict(id=f"call{i}", source="a", target="a", kind="call",
                         status="resolved" if i == 0 else "unresolved") for i in range(4)]
                 + [dict(id=f"import{i}", source="a", target="a", kind="import", status=status)
                    for i, status in enumerate(["resolved", "external"])],
        "capabilities": [], "diagnostics": [],
    }
    docs.render(run_dir=tmp_path, source_root=tmp_path, inventory={}, units={}, dispositions={},
                tree={"nodes": []}, languages={}, graph=graph)
    index = (tmp_path / "docs/INDEX.md").read_text()
    assert "python import: resolved 1/2 (50%), external 1/2 (50%)" in index
    assert "python call: resolved 1/4 (25%), unresolved 3/4 (75%)" in index
    assert "cfg=100" in index and "dataflow=100" in index
    assert "structural edges; only their counts are shown, without status ratios" in index
    assert not re.search(r"\b(?:cfg|dataflow):\s*\w+\s+\d+/\d+", index)
    assert "/206" not in index and "Status ratios aggregated by language" not in index
