# Dynamic Header Array (dynhds)

**Capability.** Owns a growable array of name/value headers: allocation with inline name+value storage, limits and options, case-insensitive lookup, HTTP/1 line parse/serialize, nghttp2 nva export, and unit-test helpers.

Use this child for HTTP header storage needs outside a parsed request: adding, looking up, and emitting header sets. It is a self-contained utility with no external policy.

Parent: [curl Codebase](r10-curl-source.md)

## Units (17)

<a id="u-3ac0ab019cf8"></a>
### `dynhds-c-unittest-helpers`

`UNITTEST bool dynhds_contains(struct dynhds *dynhds, const char *name, size_t namelen)` · [lib/dynhds.c:L241-L245][f1]

Unit-test-only helpers (compiled under UNITTESTS) that wrap the public API for test 2602: dynhds_contains/dynhds_ccontains report whether any header matches a name case-insensitively (via Curl_dynhds_get, true as !!

of the entry pointer); dynhds_count_name/dynhds_ccount_name count entries with matching name length and case-insensitive text; dynhds_remove/dynhds_cremove free and compact out every matching entry, decrementing hds_len and strs_len per match and re-examining the same index after memmove of remaining entries, returning the removal count; dynhds_set removes all entries with the name then appends the new header at the end, returning the add result (add's limit/OOM errors propagate, removal errors cannot occur).

calls: [Curl_dynhds_get](r10-dynamic-headers.md#u-53ed8bade5a6), [Curl_dynhds_add](r10-dynamic-headers.md#u-d5f87d712974), [entry_free](r10-dynamic-headers.md#u-a069fd501043)

**Uncertainties.**

- These symbols exist only when UNITTESTS is defined; runtime exposure outside tests is unknown.

<a id="u-d5f87d712974"></a>
### `Curl_dynhds_add`

`CURLcode Curl_dynhds_add(struct dynhds *dynhds, const char *name, size_t namelen, con…` · [lib/dynhds.c:L134-L183][f1]

Appends a name/value header to the array, enforcing limits and managing growth.

Invalid arguments (NULL dynhds or name, zero namelen, NULL value with nonzero valuelen) return CURLE_BAD_FUNCTION_ARGUMENT after a debug assertion. Capacity check: adding fails with CURLE_OUT_OF_MEMORY if max_entries is set and reached, or if remaining max_strs_size budget cannot hold namelen plus valuelen. entry_new allocates and optionally lowercases; failure propagates as CURLE_OUT_OF_MEMORY. When hds_len+1 reaches hds_allc, the array is doubled (starting at 16), capped at max_entries if set, reallocated via calloc and copied; allocation failure frees the new entry and returns CURLE_OUT_OF_MEMORY. On success the entry pointer is stored, strs_len grows by namelen+valuelen, and CURLE_OK is returned; the out path frees the entry on any failure.

calls: [entry_new](r10-dynamic-headers.md#u-6c11e78131a9), [entry_free](r10-dynamic-headers.md#u-a069fd501043)

**Uncertainties.**

- Growth-cap arithmetic assumes hds_allc already reflects the max_entries cap; behavior when max_entries is lowered between calls is not provable here.

<a id="u-3bfbcb994cfc"></a>
### `Curl_dynhds_cadd`

`CURLcode Curl_dynhds_cadd(struct dynhds *dynhds, const char *name, const char *value)` · [lib/dynhds.c:L185-L192][f1]

Wrapper for null-terminated strings: rejects a NULL name with CURLE_BAD_FUNCTION_ARGUMENT, treats a NULL value as an empty value, and forwards lengths to Curl_dynhds_add.

calls: [Curl_dynhds_add](r10-dynamic-headers.md#u-d5f87d712974)

<a id="u-6dad57e59440"></a>
### `Curl_dynhds_cget`

`struct dynhds_entry *Curl_dynhds_cget(struct dynhds *dynhds, const char *name)` · [lib/dynhds.c:L129-L132][f1]

Convenience wrapper: looks up a null-terminated name by forwarding its strlen to Curl_dynhds_get.

calls: [Curl_dynhds_get](r10-dynamic-headers.md#u-53ed8bade5a6)

<a id="u-6cb59604037e"></a>
### `Curl_dynhds_count`

`size_t Curl_dynhds_count(struct dynhds *dynhds)` · [lib/dynhds.c:L100-L103][f1]

Returns the current number of stored entries.

<a id="u-a06ae9805ca8"></a>
### `Curl_dynhds_free`

`void Curl_dynhds_free(struct dynhds *dynhds)` · [lib/dynhds.c:L72-L84][f1]

Frees every entry then the entry array itself, zeroing lengths and allocation count.

Skips the per-entry loop when hds is NULL or hds_len is zero, so the array can be freed independently of entry cleanup.

calls: [entry_free](r10-dynamic-headers.md#u-a069fd501043)

<a id="u-53ed8bade5a6"></a>
### `Curl_dynhds_get`

`struct dynhds_entry *Curl_dynhds_get(struct dynhds *dynhds, const char *name, size_t …` · [lib/dynhds.c:L116-L127][f1]

Linear search for the first entry whose name length equals namelen and whose name matches case-insensitively via curl_strnequal; returns that entry or NULL.

Length check first means a same-text different-length name never matches.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-6ef10b70dc3f"></a>
### `Curl_dynhds_getn`

`struct dynhds_entry *Curl_dynhds_getn(struct dynhds *dynhds, size_t n)` · [lib/dynhds.c:L110-L114][f1]

Returns the entry at index n, or NULL when n is out of range; no copy, caller sees live storage.

<a id="u-6411eda4200d"></a>
### `Curl_dynhds_h1_add_line`

`CURLcode Curl_dynhds_h1_add_line(struct dynhds *dynhds, const char *line, size_t line…` · [lib/dynhds.c:L194-L226][f1]

Parses one HTTP/1 header line into name/value and stores it via Curl_dynhds_add.

Empty or NULL lines return CURLE_OK without effect. A missing colon, or a colon in the first byte, yields CURLE_BAD_FUNCTION_ARGUMENT. Name is everything before the colon; leading blanks after the colon are skipped to find the value start; the value is truncated at the first CR, else at the first LF, if either is present. The remainder (including limits) is delegated to Curl_dynhds_add, so its error codes propagate.

calls: [Curl_dynhds_add](r10-dynamic-headers.md#u-d5f87d712974)

**Uncertainties.**

- A line with colon but no value (e.g. 'Name:') stores an empty value; trailing spaces before CRLF are not trimmed beyond the blank-skip after the colon.

<a id="u-60ba07111db4"></a>
### `Curl_dynhds_h1_cadd_line`

`CURLcode Curl_dynhds_h1_cadd_line(struct dynhds *dynhds, const char *line)` · [lib/dynhds.c:L228-L231][f1]

Wrapper passing strlen(line) (or 0 for NULL) to Curl_dynhds_h1_add_line.

calls: [Curl_dynhds_h1_add_line](r10-dynamic-headers.md#u-6411eda4200d)

<a id="u-840ea3a562ff"></a>
### `Curl_dynhds_h1_dprint`

`CURLcode Curl_dynhds_h1_dprint(struct dynhds *dynhds, struct dynbuf *dbuf)` · [lib/dynhds.c:L352-L375][f1]

Serializes all headers in HTTP/1 wire form into a dynbuf: for each entry appends name, ": ", value, and CRLF, stopping at the first curlx_dyn_addn failure and returning that CURLcode.

An empty header set returns CURLE_OK immediately without touching dbuf. The dynbuf is not reset first, so content is appended to whatever is already there.

calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947)

<a id="u-f49c0f7102c7"></a>
### `Curl_dynhds_init`

`void Curl_dynhds_init(struct dynhds *dynhds, size_t max_entries, size_t max_strs_size)` · [lib/dynhds.c:L60-L70][f1]

Initializes a dynhds instance to empty state with caller-supplied entry and total-byte limits; opts start at 0.

Assertions on dynhds and max_strs_size are DEBUGASSERT-only, so in release builds a zero max_strs_size is accepted and would later make the capacity check in add behave as unlimited minus-wrap risk.

**Notes.**

- side_effect: Overwrites all dynhds fields without freeing any prior contents.

<a id="u-ae47b60beba5"></a>
### `Curl_dynhds_reset`

`void Curl_dynhds_reset(struct dynhds *dynhds)` · [lib/dynhds.c:L86-L98][f1]

Removes all entries but keeps the allocated array for reuse: each entry is freed and its slot NULLed, then hds_len and strs_len reset to 0.

hds and hds_allc are preserved.

calls: [entry_free](r10-dynamic-headers.md#u-a069fd501043)

<a id="u-019674c6c132"></a>
### `Curl_dynhds_set_opts`

`void Curl_dynhds_set_opts(struct dynhds *dynhds, int opts)` · [lib/dynhds.c:L105-L108][f1]

Replaces the option bitmask (e.g. DYNHDS_OPT_LOWERCASE) that later adds apply to new entries; existing entries are unchanged.

<a id="u-178bd5601bc6"></a>
### `Curl_dynhds_to_nva`

`nghttp2_nv *Curl_dynhds_to_nva(struct dynhds *dynhds, size_t *pcount)` · [lib/dynhds.c:L379-L399][f1]

Builds an nghttp2_nv array referencing the entries' name/value buffers in place (no copies), setting NGHTTP2_NV_FLAG_NONE per item.

On calloc failure returns NULL with *pcount set to 0; on success *pcount receives hds_len. Available only when USE_NGHTTP2 is defined.

**Uncertainties.**

- Lifetime of the returned array depends on the dynhds entries remaining valid; no ownership transfer is visible in this file.

<a id="u-a069fd501043"></a>
### `entry_free`

`static void entry_free(struct dynhds_entry *e)` · [lib/dynhds.c:L55-L58][f1]

Frees a single dynhds_entry allocation; both name and value live inside the same allocation, so one free suffices.

uses: [fwrite_xattr](r6-tool-xattr-metadata.md#u-3b151a738586)

<a id="u-6c11e78131a9"></a>
### `entry_new`

`static struct dynhds_entry *entry_new(const char *name, size_t namelen, const char *v…` · [lib/dynhds.c:L29-L53][f1]

Allocates one dynhds_entry with name and value stored inline in a single buffer.

Rejects allocation if namelen+valuelen plus struct and two NUL bytes would overflow SIZE_MAX; returns NULL on calloc failure. Name is copied, a NUL terminates it, value is copied only if valuelen is nonzero; when opts has DYNHDS_OPT_LOWERCASE the name is lowercased in place.

calls: [Curl_strntolower](r3-string-error-utils.md#u-ed93218a3450)

**Uncertainties.**

- Caller is documented by comment to have checked namelen+valuelen <= SIZE_MAX; that check is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/dynhds.c
