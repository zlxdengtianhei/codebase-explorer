"""Page assembly: which tree nodes share one published page, under a token budget.

The page boundary is a publishing decision, not a generation decision. The tree
and its unit explanations stay frozen; this module only decides how many nodes
one page prints, so re-rendering an existing run needs no model call.

Two modes:

``group``   one page per tree node (the rule before 3.2)
``budget``  walk the tree from the top: a node whose whole subtree fits the
            budget becomes one page and prints its descendants as sections; when
            it does not fit, its children's pages are packed in tree order as long
            as they still fit together, and the rest stay pages of their own

A page prints its root and a list of further tree nodes (``members``). A node's
own unit explanations are never split, so the groups stay whole. Every node is
printed on exactly one page: the plan raises rather than writing a unit twice or
dropping one.

A page that cannot meet the budget is reported with a reason instead of being
silently oversized: either the node has no children to split into, or its own
unit explanations alone are larger than the budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

PAGE_MODES = ("group", "budget")
DEFAULT_PAGE_MODE = "budget"
DEFAULT_PAGE_BUDGET = 2500

Cost = Callable[[str, tuple[str, ...]], int]

UNSPLITTABLE_LEAF = "leaf_over_budget"
OWN_CONTENT_OVER_BUDGET = "own_content_over_budget"


@dataclass(frozen=True)
class Page:
    """One published page: the node it is rooted at, the nodes it also prints, its size."""

    root: str
    members: tuple[str, ...]
    tokens: int
    over_budget: str | None = None

    @property
    def nodes(self) -> tuple[str, ...]:
        return (self.root,) + self.members


@dataclass
class PagePlan:
    mode: str
    budget: int
    pages: list[Page]
    root_of: dict[str, str]

    def page_of(self, nid: str) -> str:
        """The page root that prints this node; an unknown id stands for itself."""
        return self.root_of.get(nid, nid)

    @property
    def over_budget(self) -> list[Page]:
        return [page for page in self.pages if page.over_budget]

    def report(self) -> dict:
        """What the catalog and RUN.md record about this plan."""
        return {"mode": self.mode, "budget": self.budget, "page_count": len(self.pages),
                "pages": [{"root": page.root, "members": list(page.members), "tokens": page.tokens,
                           **({"over_budget": page.over_budget} if page.over_budget else {})}
                          for page in self.pages],
                "root_of": dict(sorted(self.root_of.items()))}


def descendants(children: Mapping[str, Sequence[str]], nid: str) -> tuple[str, ...]:
    """Every node below ``nid`` in pre-order."""
    order: list[str] = []

    def walk(current: str) -> None:
        for kid in children.get(current) or []:
            order.append(kid)
            walk(kid)

    walk(nid)
    return tuple(order)


def plan_pages(*, nodes: Mapping[str, dict], children: Mapping[str, Sequence[str]],
               roots: Sequence[str], cost: Cost, budget: int = DEFAULT_PAGE_BUDGET,
               mode: str = DEFAULT_PAGE_MODE) -> PagePlan:
    """Cut the tree into pages. See the module docstring for the two modes.

    ``cost(root, members)`` returns the token count of the page that would be
    written for that root and those members; the renderer owns it, so this module
    never guesses what a page will weigh.
    """
    if mode not in PAGE_MODES:
        raise ValueError(f"unknown page mode {mode!r}; expected one of {', '.join(PAGE_MODES)}")
    if budget < 1:
        raise ValueError("page budget must be at least 1 token")
    below = {nid: descendants(children, nid) for nid in nodes}
    if mode == "group":
        pages = [Page(root=nid, members=(), tokens=cost(nid, ())) for nid in nodes]
        return PagePlan(mode=mode, budget=budget, pages=pages, root_of={nid: nid for nid in nodes})

    measured: dict[tuple[str, tuple[str, ...]], int] = {}

    def measure(root: str, members: tuple[str, ...]) -> int:
        key = (root, members)
        if key not in measured:
            measured[key] = cost(root, members)
        return measured[key]

    def plan_subtree(nid: str) -> list[Page]:
        """Pages covering this node's subtree, in tree order. The first has ``nid`` as root."""
        kids = list(children.get(nid) or [])
        whole = measure(nid, below[nid])
        if whole <= budget:
            return [Page(root=nid, members=below[nid], tokens=whole)]
        if not kids:
            return [Page(root=nid, members=(), tokens=whole, over_budget=UNSPLITTABLE_LEAF)]
        subs = [page for kid in kids for page in plan_subtree(kid)]
        packs: list[list[Page]] = [[]]
        for candidate in subs:
            trial = [nid for page in packs[-1] for nid in page.nodes] + list(candidate.nodes)
            if measure(nid, tuple(trial)) <= budget:
                packs[-1].append(candidate)
            else:
                packs.append([candidate])
        if not packs[0]:
            # The node's own content plus any child page is over the budget: its
            # own units, with links to the child pages, stand alone.
            own = measure(nid, ())
            first = Page(root=nid, members=(), tokens=own,
                         over_budget=OWN_CONTENT_OVER_BUDGET if own > budget else None)
            return [first] + [page for pack in packs[1:] for page in pack]
        members = tuple(nid for page in packs[0] for nid in page.nodes)
        first = Page(root=nid, members=members, tokens=measure(nid, members))
        return [first] + [page for pack in packs[1:] for page in pack]

    pages: list[Page] = []
    for root in roots:
        if root in nodes:
            pages.extend(plan_subtree(root))

    root_of: dict[str, str] = {}
    for page in pages:
        for nid in page.nodes:
            if nid in root_of:
                raise ValueError(f"node {nid!r} would be printed on two pages: "
                                 f"{root_of[nid]!r} and {page.root!r}")
            root_of[nid] = page.root
    missing = sorted(set(nodes) - set(root_of))
    if missing:
        raise ValueError(f"{len(missing)} node(s) belong to no page: {missing[:5]}")
    return PagePlan(mode=mode, budget=budget, pages=pages, root_of=root_of)
