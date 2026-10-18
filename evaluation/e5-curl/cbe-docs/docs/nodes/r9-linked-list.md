# Doubly linked list (llist)

**Capability.** A generic doubly linked list with a stored destructor callback, core insertion/removal internals, take-without-destroy unlinking, and debug-asserted accessors for head/tail/next/prev/elem/count.

Use this subtree for list storage needs; nodes may be detached via Curl_node_take_elem without destroying payloads. Destruction drains via node_uremove so the configured destructor runs per element.

**Depended on by.**

- [Cookie jar storage and lifecycle](r12-cookie-jar-core.md) · graph-only · 37 edge(s)
- [HTTP Headers Store and API](r8-http-headers-api.md) · graph-only · 25 edge(s)
- [HSTS Cache](r10-hsts-cache.md) · graph-only · 24 edge(s)

Parent: [Shared core infrastructure](r9-core-infra.md)

## Units (14)

<a id="u-5e8651140cc1"></a>
### `Curl_llist_append`

`void Curl_llist_append(struct Curl_llist *list, const void *p, struct Curl_llist_node…` · [lib/llist.c:L120-L127][f1]

Appends a payload node at the list tail by delegating to llist_insert_next with the current tail as anchor; the size==0 branch inside insertion handles empty lists.

Debug asserts require an initialized list and non-NULL node.

calls: [llist_insert_next](r9-linked-list.md#u-cfc18389f7ca)

<a id="u-d824c41827d3"></a>
### `Curl_llist_count`

`size_t Curl_llist_count(const struct Curl_llist *list)` · [lib/llist.c:L228-L233][f1]

Returns the maintained node count; asserts list validity and debug init pattern.

The count is only as accurate as insert/remove bookkeeping.

<a id="u-3fbee724f1c9"></a>
### `Curl_llist_destroy`

`void Curl_llist_destroy(struct Curl_llist *list, void *user)` · [lib/llist.c:L195-L202][f1]

Drains the list by repeatedly removing the tail node through node_uremove until _size reaches zero, passing the supplied user pointer to each destructor call.

NULL list is ignored; a list without a dtor simply detaches nodes without freeing payloads.

calls: [node_uremove](r9-linked-list.md#u-fe550f0c6aa3)

**Uncertainties.**

- Termination relies on each popped tail being attached (non-NULL _list) so _size decrements; the source guards this only via node_uremove's _list check, so a corrupted list could loop forever.

<a id="u-21d32d21e74e"></a>
### `Curl_llist_head`

`struct Curl_llist_node *Curl_llist_head(const struct Curl_llist *list)` · [lib/llist.c:L206-L211][f1]

Returns the list's first node, which is NULL for an empty list; asserts the list pointer and its debug init pattern.

In debug builds the result passes through verifynode, which re-checks the node's init pattern.

uses: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e)

<a id="u-a99250aef25e"></a>
### `Curl_llist_init`

`void Curl_llist_init(struct Curl_llist *l, Curl_llist_dtor dtor)` · [lib/llist.c:L45-L54][f1]

Initializes a caller-allocated doubly linked list: size 0, stored destructor callback, NULL head and tail.

Debug builds also stamp an _init pattern later checked by DEBUGASSERT; a NULL dtor means removal will not free payloads.

**Uncertainties.**

- Non-NULL list argument is only enforced via DEBUGASSERT, which compiles out in release builds.

<a id="u-640782ef2dbe"></a>
### `Curl_node_elem`

`void *Curl_node_elem(const struct Curl_llist_node *n)` · [lib/llist.c:L236-L241][f1]

Returns the payload pointer stored in a node; asserts node validity and debug init pattern.

<a id="u-1dcbb170a9f8"></a>
### `Curl_node_llist`

`struct Curl_llist *Curl_node_llist(const struct Curl_llist_node *n)` · [lib/llist.c:L268-L273][f1]

Returns the owning-list back-pointer of a node, NULL when the node is detached; debug assert checks the init pattern only when a list is present.

<a id="u-0089ba08aa64"></a>
### `Curl_node_next`

`struct Curl_llist_node *Curl_node_next(const struct Curl_llist_node *n)` · [lib/llist.c:L245-L250][f1]

Returns the node's _next pointer, NULL at the end of the list; asserts node validity and debug init pattern, and in debug builds the result is re-verified via verifynode.

uses: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e)

<a id="u-e7f506f6b8c9"></a>
### `Curl_node_remove`

`void Curl_node_remove(struct Curl_llist_node *e)` · [lib/llist.c:L190-L193][f1]

Public removal entry: unlinks the node and runs the list destructor with a NULL user pointer via node_uremove; no-op for NULL nodes or detached nodes.

calls: [node_uremove](r9-linked-list.md#u-fe550f0c6aa3)

<a id="u-7f394eddbd90"></a>
### `Curl_node_take_elem`

`void *Curl_node_take_elem(struct Curl_llist_node *e)` · [lib/llist.c:L129-L172][f1]

Unlinks a node from its list without destroying the payload and returns the stored pointer; NULL input returns NULL.

Head removal advances head, NULLing tail if the list empties, else fixing the new head's _prev; non-head removal splices via neighbors, moving tail to _prev when the node was last. Size decrements only when e->_list is set. Afterwards _list, _ptr, _prev, _next are cleared (debug: _init stamped with a removal pattern), so reuse requires reinsertion.

**Uncertainties.**

- Behavior when e->_list is NULL: all unlinking is skipped, but _ptr is still read and returned after the guard, so the return value for detached nodes is whatever _ptr holds rather than a guaranteed NULL.

<a id="u-cfc18389f7ca"></a>
### `llist_insert_next`

`UNITTEST void llist_insert_next(struct Curl_llist *list, struct Curl_llist_node *e, /…` · [lib/llist.c:L70-L109][f1]

Core insertion: links node 'ne' carrying payload 'p' into 'list' after node 'e'.

Empty-list case makes 'ne' the sole head and tail with both links NULL. Non-empty: if 'e' is NULL the node is prepended (old head's _prev updated, head moves to 'ne'); if 'e' has a successor, that successor's _prev points back at 'ne'; otherwise 'ne' becomes the new tail. Only when 'e' is non-NULL is e->_next updated, so prepending keeps the old head's forward link intact. Size always increments. Debug builds stamp ne->_init and assert list/ne validity.

**Notes.**

- side_effect: Mutates list head/tail/size and neighboring nodes' links; 'ne' storage is supplied by the caller.

**Uncertainties.**

- Passing 'e' from a different list is unguarded; no runtime check exists in this source.

<a id="u-322e71c8059d"></a>
### `llist_node_prev`

`Curl_llist_node *llist_node_prev( const struct Curl_llist_node *n)` · [lib/llist.c:L259-L265][f1]

Unit-test-only accessor returning the node's _prev pointer, NULL at the list start; asserts node validity and debug init pattern, and re-verifies the neighbor pattern via verifynode in debug builds.

uses: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e)

<a id="u-cb24aa8799de"></a>
### `llist_tail`

`Curl_llist_node *llist_tail(const struct Curl_llist *list)` · [lib/llist.c:L219-L224][f1]

Unit-test-only accessor returning the list's last node, NULL when empty; asserts list pointer and debug init pattern, and re-verifies the node pattern via verifynode in debug builds.

uses: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e)

<a id="u-fe550f0c6aa3"></a>
### `node_uremove`

`static void node_uremove(struct Curl_llist_node *e, void *user)` · [lib/llist.c:L174-L188][f1]

Removes a node from its list and invokes the list destructor with the user pointer and detached payload when one is configured.

NULL node returns immediately; a NULL _list back-pointer skips both unlink and destructor. Destruction policy lives with the list's dtor, not the node.

calls: [Curl_node_take_elem](r9-linked-list.md#u-7f394eddbd90)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/llist.c
