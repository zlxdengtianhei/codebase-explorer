# Container Types

**Capability.** Provides the generic chained hash table (elements with inline keys, pluggable destructors, iteration) and the curl_slist singly-linked list with append/take-ownership/duplicate/free operations.

Use this subtree for the two pervasive data structures in libcurl. The slist is the public-facing list used by the tool's header buffering; the hash underpins internal lookups.

**Depended on by.**

- [Tool Header Callback](r8-tool-header-callback.md) · graph-confirmed · 4 edge(s)

Parent: [Core Utilities and Portability](r8-core-utilities.md)

## Units (14)

<a id="u-1bb3a0849a4f"></a>
### `hash.h module code (L1–L33)`

`module_region` · [lib/hash.h:L1-L33][f1]

Include guard and curl_setup.h include.

<a id="u-40d081153a4c"></a>
### `lib/hash.h:<enum>`

`enum` · [lib/hash.h:L33-L37][f1]

Defines Curl_hash_type, selecting how hash keys are interpreted: raw bytes or a socket descriptor value.

<a id="u-4fb58631e6cd"></a>
### `hash.h module code (L37–L38)`

`module_region` · [lib/hash.h:L37-L38][f1]

Function-pointer typedefs for hash element destructors (plain and key-aware).

<a id="u-270a73a3904a"></a>
### `Curl_hash_element`

`struct Curl_hash_element` · [lib/hash.h:L39-L45][f1]

Chained hash element holding a next link, a generic value pointer, an optional per-element destructor, key length, and a key stored inline in memory allocated immediately after the struct.

**Notes.**

- field: key[1] is the head of allocated memory following the struct, so key bytes are stored inline.

<a id="u-691a9d9c68ec"></a>
### `Curl_hash`

`struct Curl_hash` · [lib/hash.h:L47-L57][f1]

Hash table descriptor: slot table of element chains, a general element destructor used unless an element carries its own, slot and element counts, and a uint8_t holding a Curl_hash_type; DEBUGBUILD adds an init guard.

uses: [Curl_hash_element](r8-container-types.md#u-270a73a3904a), [lib/hash.h:<enum>](r8-container-types.md#u-40d081153a4c)

<a id="u-c97aa22f694d"></a>
### `Curl_hash_iterator`

`struct Curl_hash_iterator` · [lib/hash.h:L59-L66][f1]

Iteration cursor over a Curl_hash: the hash being walked, the current slot index, and the current element within that slot; DEBUGBUILD init guard included.

uses: [Curl_hash](r8-container-types.md#u-691a9d9c68ec)

<a id="u-f948ccef9082"></a>
### `hash.h module code (L45–L46)`

`module_region` · [lib/hash.h:L45-L46][f1]

Separator line between declarations.

<a id="u-c582db627f19"></a>
### `hash.h module code (L57–L58)`

`module_region` · [lib/hash.h:L57-L58][f1]

Separator line between declarations.

<a id="u-01dd7904f6da"></a>
### `hash.h module code (L66–L95)`

`module_region` · [lib/hash.h:L66-L95][f1]

Public hash API prototypes: init, add/add2, delete, pick, destroy, count, clean, clean_with_criterium, iterate, and print.

<a id="u-7ee0f3196118"></a>
### `slist_get_last`

`static struct curl_slist *slist_get_last(struct curl_slist *list)` · [lib/slist.c:L29-L43][f2]

Returns the last node of a curl_slist, or NULL when the passed list is NULL; otherwise walks the next pointers to the final node.

Static helper, no allocation.

uses: [Curl_slist_append_nodup](r8-container-types.md#u-38f26493f1c4)

<a id="u-38f26493f1c4"></a>
### `Curl_slist_append_nodup`

`struct curl_slist *Curl_slist_append_nodup(struct curl_slist *list, const char *data)` · [lib/slist.c:L54-L76][f2]

Appends a string to a curl_slist, taking ownership of the (already allocated) string rather than copying it.

Allocates a node; allocation failure returns NULL and, per the contract, does not release the string. If the list was NULL the new node becomes the list; otherwise the node is linked after the tail found by slist_get_last. Always returns the first node's address.

calls: [slist_get_last](r8-container-types.md#u-7ee0f3196118); uses: [curl_slist_append](r8-container-types.md#u-851bb574d7cd)

<a id="u-851bb574d7cd"></a>
### `curl_slist_append`

`struct curl_slist *curl_slist_append(struct curl_slist *list, const char *data)` · [lib/slist.c:L85-L97][f2]

Appends a copy of the given string to a curl_slist.

The string is duplicated; strdup failure returns NULL. Delegates to Curl_slist_append_nodup, and if that fails the duplicate is freed before returning NULL. On success returns the first node's address, so it works both as initializer and appender.

calls: [Curl_slist_append_nodup](r8-container-types.md#u-38f26493f1c4)

<a id="u-098fac37e5cb"></a>
### `curl_slist_free_all`

`void curl_slist_free_all(struct curl_slist *list)` · [lib/slist.c:L125-L140][f2]

Frees every node of a curl_slist and the string each node owns, using curlx_safefree on the data; a NULL list returns immediately.

The loop stops after the node whose next was NULL, so the whole chain is released.

<a id="u-9baf85c9fa7a"></a>
### `Curl_slist_duplicate`

`struct curl_slist *Curl_slist_duplicate(struct curl_slist *inlist)` · [lib/slist.c:L104-L122][f2]

Deep-copies a curl_slist by repeatedly appending duplicates of each node's data, using a tail pointer so the list is built in order.

If any append fails, the partially built list is freed with curl_slist_free_all and NULL is returned; a NULL input also yields NULL.

calls: [curl_slist_append](r8-container-types.md#u-851bb574d7cd), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/hash.h
[f2]: ../../../../../../eval/curl-2c04412/lib/slist.c
