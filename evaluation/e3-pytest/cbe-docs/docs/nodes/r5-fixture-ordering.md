# Item reordering for high-scope fixtures

**Capability.** Reorders collected items so tests sharing high-scoped parametrized fixtures run consecutively, minimizing repeated fixture setup/teardown.

Consult this to understand why item execution order may differ from collection order and how get_param_argkeys feeds the at-scope regrouping.

**Depends on.**

- [Fixture registry and requirement closure](r5-fixture-registry.md) · model-inferred · 0 edge(s)

Parent: [Fixture machinery](r5-fixture-machinery.md)

## Units (3)

<a id="u-ae43a2b63b8b"></a>
### `reorder_items`

`def reorder_items(items: Sequence[nodes.Item]) -> list[nodes.Item]:` · [src/_pytest/fixtures.py:L227-L245][f1]

Reorder collected items to minimize high-scope fixture setup/teardown churn.

For each scope in HIGH_SCOPES builds a map from item to its ParamArgKeys and an insertion-ordered map from ParamArgKey to the items sharing it; items without argkeys at a scope are absent from these maps. Then delegates to reorder_items_atscope starting at Session scope and returns the resulting item list.

calls: [get_param_argkeys](r5-fixture-ordering.md#u-ad4266dbad51), [reorder_items_atscope](r5-fixture-ordering.md#u-40809dce45a5)

<a id="u-40809dce45a5"></a>
### `reorder_items_atscope`

`def reorder_items_atscope( items: OrderedSet[nodes.Item], argkeys_by_item: Mapping[Sc…` · [src/_pytest/fixtures.py:L248-L310][f1]

Group items sharing a high-scoped param so same-parameter tests run consecutively.

Returns immediately if scope is Function or fewer than three items. Uses a deque of pending items, an ignore set of already-sliced ParamArgKeys, and a done set. For each item its non-ignored argkeys at the scope are computed; with none, the item goes to no_argkey_items. Otherwise one slicing argkey is chosen and all items sharing it that are still present are prepended (reversed, preserving encounter order) to the deque; the items_by_argkey ordering is then fixed by moving the item to the front, or on PyPy by rebuilding each dict to work around PyPy issue 5257. After the inner loop, no-argkey items are recursively reordered at scope.next_lower() and merged into done; the used slicing key is added to ignore so it is sliced once. Returns the done set.

**Notes.**

- side_effect: Mutates the shared items_by_argkey dictionaries while reordering (move_to_end or PyPy-specific rebuild).

calls: [reorder_items_atscope](r5-fixture-ordering.md#u-40809dce45a5)

**Uncertainties.**

- Recursion relies on Scope.next_lower(); its values are not defined in this file.

<a id="u-ad4266dbad51"></a>
### `get_param_argkeys`

`def get_param_argkeys(item: nodes.Item, scope: Scope) -> Iterator[ParamArgKey]:` · [src/_pytest/fixtures.py:L197-L224][f1]

Yield ParamArgKeys for the high-scoped parametrized arguments an item consumes at a given scope.

Asserts scope is not Function. Items lacking a callspec (AttributeError) yield nothing. The key's scoped_item_path/item_cls vary by scope: Session gives None/None, Package the item's parent directory, Module the item's file, Class the file plus item.cls; other scopes reach assert_never. Among callspec.indices only args whose _arg2scope equals the requested scope are yielded, keyed by their param index.

calls: [ParamArgKey][f1]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/fixtures.py
