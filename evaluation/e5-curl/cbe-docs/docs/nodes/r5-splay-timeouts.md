# Splay Tree and Timeouts

**Capability.** Implements the top-down splay tree (splay/insert/remove/best-fit) and the timeout management layered on it, including the next-pending-timeout query.

Use when tracing deadline handling or the generic ordered-set primitive. The splay core is data-structure only; Curl_timeouts_next_ms is the timeout-oriented consumer of it.

Parent: [Event and Concurrency Infrastructure](r5-async-event-infrastructure.md)

## Units (6)

<a id="u-0fc50fc76810"></a>
### `Curl_timeouts_next_ms`

`int Curl_timeouts_next_ms(struct Curl_timeouts *timeouts, const struct curltime *pnow…` · [lib/splay.c:L64-L92][f1]

Reports the next pending timeout in milliseconds, updating the tree in place and writing side-channel outputs.

If the tree is non-empty it is splayed at TIMEDIFF_T_MIN so the earliest node becomes root. For that node: `pmid` receives the node id and `pexpire_offset_us` the absolute key (microseconds since the stored time base) when the corresponding pointers are non-NULL. The remaining time is node key minus elapsed microseconds computed by Curl_timeouts_offset_us against `pnow`; a positive delta is converted to milliseconds with curlx_us_to_ceil_ms and clamped to INT_MAX if it exceeds that, while a non-positive delta returns 0 (already expired). With an empty tree, `pmid` is set to UINT32_MAX, `pexpire_offset_us` to 0, and -1 is returned.

calls: [splay](r5-splay-timeouts.md#u-f575d83b4ae8), [splay.c-timeouts-and-splay-helpers](r5-splay-timeouts.md#u-4d5c1f91645f), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3)

**Uncertainties.**

- How callers treat an INT_MAX clamp is defined outside this file.

<a id="u-f575d83b4ae8"></a>
### `splay`

`struct Curl_tree *splay(timediff_t key, struct Curl_tree *root)` · [lib/splay.c:L102-L168][f1]

Restructures the splay tree so the node nearest `key` becomes the root, using the classic top-down splay algorithm.

An empty tree returns NULL. The loop walks from the root: if `key < root->key`, an empty smaller branch ends the search, otherwise a zig rotation is applied when the key is also below the left child's key, then the old root is hung on the right side of a temporary list tree and the walk continues left. The `key > root->key` side is symmetric. An exact key match breaks the loop. At the end the accumulated lists and the final root are reassembled so the returned root's smaller branch holds all keys less than `key` and its larger branch all keys greater; `root->key` may or may not equal `key`. Callers exploit this by splaying TIMEDIFF_T_MIN to bring the minimum node to the root. Mutates links in place; no allocation or error paths.

uses: [Curl_tree][f2]

<a id="u-35719c1d0891"></a>
### `splaygetbest`

`Curl_tree *splaygetbest(timediff_t key, struct Curl_tree *root, struct Curl_tree **re…` · [lib/splay.c:L241-L280][f1]

Finds and deletes the best-fit node — the smallest node unless its key exceeds `key` — returning the resulting tree and the removed node via `*removed`.

An empty tree sets *removed to NULL and returns NULL. The tree is splayed at TIMEDIFF_T_MIN so the minimum becomes root; if `key` is below even the minimum, *removed is NULL and the tree is returned unchanged. If the minimum has duplicates in its `same` list, the first duplicate is promoted to root (inheriting both subtrees), the removed node's `same` link is cleared, it is marked unregistered, and returned. Without duplicates, the removed root's `larger` subtree becomes the new tree. The removed node's `registered` flag is always set FALSE; no error paths.

calls: [splay](r5-splay-timeouts.md#u-f575d83b4ae8); uses: [Curl_tree][f2]

<a id="u-21feb1aa399a"></a>
### `splayinsert`

`Curl_tree *splayinsert(timediff_t key, struct Curl_tree *root, struct Curl_tree *node…` · [lib/splay.c:L179-L220][f1]

Inserts a node with the given key and id into the splay tree and returns the new root.

The node is initialized: key, id, empty `same` list, registered=TRUE; a NULL node triggers DEBUGASSERT. If a root exists the tree is splayed at `key`; when an equal key is already present, the new node is appended to the tail of the root's `same` duplicate list and the existing root is returned unchanged, so duplicates never occupy tree positions. Otherwise the new node becomes the new root: with no previous root both children are NULL; if `key < root->key` it adopts the old root's smaller subtree and the old root as its larger child (the old root's smaller link is cleared); the greater-key case is symmetric. The caller must pass a node not already in the tree.

calls: [splay](r5-splay-timeouts.md#u-f575d83b4ae8); uses: [Curl_tree][f2]

<a id="u-c6dcf459f999"></a>
### `splayremove`

`UNITTEST int splayremove(struct Curl_tree *root, struct Curl_tree *removenode, struct…` · [lib/splay.c:L313-L375][f1]

Deletes a specific node from the tree, storing the new root in `newroot` and returning 0 on success or non-zero without touching `newroot`.

Failure returns: 1 if the tree is empty; 2 if the target is unregistered; 2 if after splaying at the target key the root key differs (target not in the tree, DEBUGASSERT fires); 2 if the target is not found in the root's `same` duplicate list. A target found in the `same` list is unlinked from it, marked unregistered, and the existing root remains. If the target is the root: a `same` duplicate is promoted to root inheriting both subtrees; otherwise with no smaller subtree the larger subtree becomes the new root, else the smaller subtree is splayed at the key and its root gains the removed root's larger child. When the last node is removed, *newroot becomes NULL. The removed node is always marked unregistered.

calls: [splay](r5-splay-timeouts.md#u-f575d83b4ae8); uses: [Curl_tree][f2]

<a id="u-4d5c1f91645f"></a>
### `splay.c-timeouts-and-splay-helpers`

`uint32_t Curl_splayget(struct Curl_tree *node)` · [lib/splay.c:L33-L37][f1]

Wrapper helpers exposing the timeout splay structure and unit-test accessors.

Curl_timeouts_init empties the tree and records a time base in whole seconds, taking the seconds from the passed curltime or, when NULL, from curlx_now(). Curl_timeouts_has reports NULL-safely whether the easy handle's embedded splaynode carries registered=TRUE. Curl_timeouts_offset_us rebuilds a curltime from the stored base seconds (usec 0) and returns signed microseconds of `pts` relative to that base via curlx_ptimediff_us; the base can lag the real clock because only seconds are stored. Curl_timeouts_add asserts (debug only) that the handle's node is unregistered, then inserts it with the given microsecond offset and the handle's `mid` as id. Curl_timeouts_remove_expired removes via splaygetbest the best-fit node for elapsed time at `ts`, returning TRUE and the node id on removal, otherwise FALSE with *pmid=UINT32_MAX. Curl_timeouts_remove, when the handle's node is registered, removes it with splayreplace-tree in timeouts->tree and returns TRUE; on removal error it logs to stderr in DEBUGBUILD, and it returns FALSE when not registered. Curl_splayget (UNITTESTS only) debug-asserts non-NULL and returns the node id.

calls: [splayinsert](r5-splay-timeouts.md#u-21feb1aa399a), [splaygetbest](r5-splay-timeouts.md#u-35719c1d0891), [splayremove](r5-splay-timeouts.md#u-c6dcf459f999), [splay.c-timeouts-and-splay-helpers](r5-splay-timeouts.md#u-4d5c1f91645f), [curlx_now](r9-time-utils.md#u-1e54794baf3b), [timeval.c-timediff](r9-time-utils.md#u-d52230c213e3); uses: [splay.c-timeouts-and-splay-helpers](r5-splay-timeouts.md#u-4d5c1f91645f)

**Uncertainties.**

- Curl_timeouts_remove returns TRUE even when splayremove reports an error code; whether the node should be considered removed in that case is not resolved here.
- The truncated explain above is corrected: Curl_timeouts_remove stores the new tree directly into timeouts->tree via splayremove's newroot out-parameter.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/splay.c
[f2]: ../../../../../../eval/curl-2c04412/lib/splay.h
