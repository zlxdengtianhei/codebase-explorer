from __future__ import annotations

from src.synthesis.variant_a.anchors import page_anchor, symbol_anchor
from src.synthesis.variant_a.line_ranges import apply_line_ranges, audit_tree


def test_rewrite_turns_symbol_fragments_into_line_ranges() -> None:
    sid = "app.py::Flask"
    frag = symbol_anchor(sid)
    docs = {
        "INDEX.md": (
            f'<a id="{page_anchor("root")}"></a>\n'
            f"# root\n\n"
            f"[`Flask`](mod/DETAIL.md#{frag})\n"
        ),
        "mod/DETAIL.md": (
            f'<a id="{page_anchor("d")}"></a>\n'
            f"# detail\n\n"
            f"<!-- symbol:{sid} -->\n"
            f'<a id="{frag}"></a>\n'
            f"### `Flask`\n\n"
            f"body\n\n"
            f"<!-- end:symbol:{sid} -->\n"
        ),
    }
    rewritten = apply_line_ranges(docs)
    index = rewritten["INDEX.md"]
    assert "#L" in index
    assert "DETAIL.md#L" in index
    audit = audit_tree(rewritten)
    assert audit["rate_with_line_range"] == 1.0
    assert audit["failed"] == 0


def test_unparseable_link_counts_as_failure() -> None:
    docs = {
        "INDEX.md": "# x\n\n[bad](missing.md)\n",
    }
    audit = audit_tree(docs)
    assert audit["failed"] == 1
    assert audit["rate_with_line_range"] == 0.0
