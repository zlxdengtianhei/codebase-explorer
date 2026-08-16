"""Symbol-level hop invariant: INDEX.md --≤3 resolvable links--> ledger symbol."""

from __future__ import annotations

from src.synthesis.variant_a.symbol_hops import measure_symbol_hops


def _block(symbol_id: str, title: str = "X") -> str:
    return (
        f"<!-- symbol:{symbol_id} -->\n"
        f"### `{title}`\n"
        f"body\n"
        f"<!-- end:symbol:{symbol_id} -->\n"
    )


def test_direct_index_link_is_one_hop() -> None:
    docs = {
        "INDEX.md": "# root\n\n[Flask](app/DETAIL.md#L10-L20)\n",
        "app/DETAIL.md": "# app\n\n" + _block("app.py::Flask", "Flask"),
    }
    out = measure_symbol_hops(docs, ["app.py::Flask"])
    assert out["distribution"] == {"0": 0, "1": 1, "2": 0, "3": 0, "4+": 0, "unreachable": 0}
    assert out["symbols"]["app.py::Flask"]["hops"] == 1
    assert out["rate_le_3"] == 1.0
    assert out["over_3"] == []
    assert out["unreachable"] == []


def test_cluster_index_then_part_is_two_hops() -> None:
    docs = {
        "INDEX.md": "# root\n\n[serve](serve/INDEX.md#L2-L10)\n",
        "serve/INDEX.md": "# serve\n\n[PART-1](PART-1.md#L2-L40)\n",
        "serve/PART-1.md": "# part\n\n" + _block("app.py::Flask", "Flask"),
    }
    out = measure_symbol_hops(docs, ["app.py::Flask"])
    assert out["symbols"]["app.py::Flask"]["hops"] == 2
    assert out["distribution"]["2"] == 1


def test_public_surface_shortcut_beats_cluster_path() -> None:
    docs = {
        "INDEX.md": (
            "# root\n\n"
            "[Flask](serve/PART-1.md#L10-L20)\n"
            "[serve](serve/INDEX.md#L2-L10)\n"
        ),
        "serve/INDEX.md": "# serve\n\n[PART-1](PART-1.md#L2-L40)\n",
        "serve/PART-1.md": "# part\n\n" + _block("app.py::Flask", "Flask"),
    }
    out = measure_symbol_hops(docs, ["app.py::Flask"])
    assert out["symbols"]["app.py::Flask"]["hops"] == 1


def test_four_hops_listed_in_over_3() -> None:
    docs = {
        "INDEX.md": "# r\n\n[a](a/INDEX.md)\n",
        "a/INDEX.md": "# a\n\n[b](../b/INDEX.md)\n",
        "b/INDEX.md": "# b\n\n[c](../c/INDEX.md)\n",
        "c/INDEX.md": "# c\n\n[d](../d/DETAIL.md)\n",
        "d/DETAIL.md": "# d\n\n" + _block("deep.py::fn", "fn"),
    }
    out = measure_symbol_hops(docs, ["deep.py::fn"])
    assert out["symbols"]["deep.py::fn"]["hops"] == 4
    assert out["distribution"]["4+"] == 1
    assert out["rate_le_3"] == 0.0
    assert len(out["over_3"]) == 1
    assert out["over_3"][0]["symbol_id"] == "deep.py::fn"
    assert out["over_3"][0]["hops"] == 4
    assert out["over_3"][0]["path"] == [
        "INDEX.md",
        "a/INDEX.md",
        "b/INDEX.md",
        "c/INDEX.md",
        "d/DETAIL.md",
    ]


def test_not_rendered_is_unreachable() -> None:
    docs = {
        "INDEX.md": "# r\n\n[x](x/DETAIL.md)\n",
        "x/DETAIL.md": "# x\n\nno symbol block\n",
    }
    out = measure_symbol_hops(docs, ["ghost.py::fn"])
    assert out["distribution"]["unreachable"] == 1
    assert out["unreachable"] == [
        {"symbol_id": "ghost.py::fn", "reason": "not_rendered", "pages": []}
    ]


def test_rendered_on_orphaned_page_is_unreachable() -> None:
    docs = {
        "INDEX.md": "# r\n\nno down links\n",
        "orphan/DETAIL.md": "# o\n\n" + _block("o.py::fn", "fn"),
    }
    out = measure_symbol_hops(docs, ["o.py::fn"])
    assert out["distribution"]["unreachable"] == 1
    row = out["unreachable"][0]
    assert row["symbol_id"] == "o.py::fn"
    assert row["reason"] == "page_unreachable"
    assert row["pages"] == ["orphan/DETAIL.md"]


def test_min_hops_across_duplicate_renders() -> None:
    docs = {
        "INDEX.md": "# r\n\n[near](near/DETAIL.md)\n[far](a/INDEX.md)\n",
        "near/DETAIL.md": "# n\n\n" + _block("dup.py::fn", "fn"),
        "a/INDEX.md": "# a\n\n[b](../b/DETAIL.md)\n",
        "b/DETAIL.md": "# b\n\n" + _block("dup.py::fn", "fn"),
    }
    out = measure_symbol_hops(docs, ["dup.py::fn"])
    assert out["symbols"]["dup.py::fn"]["hops"] == 1


def test_external_and_missing_links_do_not_count() -> None:
    docs = {
        "INDEX.md": (
            "# r\n\n"
            "[web](https://example.com/x.md)\n"
            "[gone](missing.md)\n"
            "[ok](ok/DETAIL.md)\n"
        ),
        "ok/DETAIL.md": "# ok\n\n" + _block("ok.py::fn", "fn"),
    }
    out = measure_symbol_hops(docs, ["ok.py::fn"])
    assert out["symbols"]["ok.py::fn"]["hops"] == 1
    assert out["distribution"]["unreachable"] == 0
