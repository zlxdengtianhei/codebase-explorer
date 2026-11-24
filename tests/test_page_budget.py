"""The page plan: which tree nodes share a page under a token budget.

These tests pin the guarantees the renderer relies on: every node lands on
exactly one page, a page never grows past its budget unless the tree gives it
nothing to split into, and ``group`` keeps the older one-page-per-node rule.
"""
from __future__ import annotations

import pytest

from cbe import page_budget


TREE = {"top": None, "a": "top", "b": "top", "a1": "a", "a2": "a", "b1": "b", "b2": "b"}


def _views(tree: dict[str, str | None]) -> tuple[dict, dict[str, list[str]], list[str]]:
    from collections import defaultdict

    nodes = {nid: {"id": nid, "parent": parent} for nid, parent in tree.items()}
    children: dict[str, list[str]] = defaultdict(list)
    for nid, node in nodes.items():
        if node["parent"] in nodes:
            children[node["parent"]].append(nid)
    roots = [nid for nid, node in nodes.items() if node["parent"] not in nodes]
    return nodes, children, roots


def _cost(sizes: dict[str, int], overhead: int = 0):
    """A page costs its root's size plus the sizes of the subtrees it covers, plus ``overhead``."""

    def cost(root: str, covers: tuple[str, ...]) -> int:
        return sizes[root] + sum(sizes[cover] for cover in covers) + overhead * (1 + len(covers))

    return cost


def test_group_mode_keeps_one_page_per_node() -> None:
    nodes, children, roots = _views(TREE)
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost({nid: 10 for nid in TREE}), mode="group")
    assert [page.root for page in plan.pages] == list(TREE)
    assert plan.root_of == {nid: nid for nid in TREE}


def test_a_subtree_that_fits_becomes_one_page_with_its_children_as_sections() -> None:
    nodes, children, roots = _views(TREE)
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost({nid: 10 for nid in TREE}), budget=100)
    assert [(page.root, page.members) for page in plan.pages] == [
        ("top", ("a", "a1", "a2", "b", "b1", "b2"))]
    assert plan.root_of == {nid: "top" for nid in TREE}
    assert plan.pages[0].nodes == ("top", "a", "a1", "a2", "b", "b1", "b2")


def test_children_pages_pack_in_tree_order_while_they_fit() -> None:
    nodes, children, roots = _views(TREE)
    sizes = {"top": 10, "a": 20, "a1": 10, "a2": 10, "b": 20, "b1": 10, "b2": 10}
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost(sizes), budget=50)
    # The whole tree costs 90 > 50: split. Each child's subtree fits (40), and the
    # first child's page joins the root's page (50) while the second no longer fits
    # beside it (90), so it keeps its own page.
    assert [(page.root, page.members) for page in plan.pages] == [
        ("top", ("a", "a1", "a2")), ("b", ("b1", "b2"))]
    assert plan.root_of == {"top": "top", "a": "top", "a1": "top", "a2": "top",
                            "b": "b", "b1": "b", "b2": "b"}


def test_every_node_lands_on_exactly_one_page_and_none_is_lost() -> None:
    nodes, children, roots = _views(TREE)
    for budget in (1, 20, 45, 60, 100, 1000):
        plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                      cost=_cost({nid: 10 for nid in TREE}), budget=budget)
        printed = [nid for page in plan.pages for nid in page.nodes]
        assert sorted(printed) == sorted(TREE), budget
        assert len(printed) == len(set(printed)), budget


def test_a_page_that_cannot_split_is_reported_instead_of_silently_growing() -> None:
    nodes, children, roots = _views({"top": None, "big": "top"})
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost({"top": 10, "big": 500}), budget=100)
    over = plan.over_budget
    assert [(page.root, page.over_budget) for page in over] == [("big", page_budget.UNSPLITTABLE_LEAF)]
    assert over[0].tokens == 500


def test_a_node_whose_own_content_overflows_stands_alone() -> None:
    nodes, children, roots = _views({"top": None, "kid": "top"})
    sizes = {"top": 90, "kid": 60}
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost(sizes, overhead=1), budget=100)
    # top + kid costs 152 > 100, so top prints on its own page and links to kid's page.
    assert [(page.root, page.members) for page in plan.pages] == [("top", ()), ("kid", ())]
    assert plan.root_of == {"top": "top", "kid": "kid"}
    assert not plan.over_budget


def test_an_own_page_that_cannot_fit_its_own_content_is_flagged() -> None:
    nodes, children, roots = _views({"top": None, "kid": "top"})
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost({"top": 500, "kid": 10}), budget=100)
    assert [(page.root, page.over_budget) for page in plan.pages] == [
        ("top", page_budget.OWN_CONTENT_OVER_BUDGET), ("kid", None)]


def test_a_page_over_budget_is_only_allowed_where_the_tree_offers_no_split() -> None:
    nodes, children, roots = _views(TREE)
    sizes = {"top": 10, "a": 40, "a1": 90, "a2": 10, "b": 40, "b1": 10, "b2": 300}
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost(sizes), budget=60)
    assert plan.over_budget, "this tree has leaves no page can fit"
    for page in plan.pages:
        if page.tokens > 60:
            assert page.over_budget, f"{page.root} is over budget without a reason"
            assert not children[page.root], f"{page.root} could have been split"


def test_unknown_mode_and_empty_budget_are_rejected() -> None:
    nodes, children, roots = _views(TREE)
    cost = _cost({nid: 10 for nid in TREE})
    with pytest.raises(ValueError):
        page_budget.plan_pages(nodes=nodes, children=children, roots=roots, cost=cost, mode="pages")
    with pytest.raises(ValueError):
        page_budget.plan_pages(nodes=nodes, children=children, roots=roots, cost=cost, budget=0)


def test_the_report_carries_the_budget_and_the_page_roots() -> None:
    nodes, children, roots = _views(TREE)
    plan = page_budget.plan_pages(nodes=nodes, children=children, roots=roots,
                                  cost=_cost({nid: 10 for nid in TREE}), budget=100)
    report = plan.report()
    assert report["mode"] == "budget" and report["budget"] == 100
    assert report["page_count"] == 1
    assert report["pages"][0] == {"root": "top", "members": ["a", "a1", "a2", "b", "b1", "b2"],
                                  "tokens": 70}
    assert report["root_of"]["a2"] == "top"
