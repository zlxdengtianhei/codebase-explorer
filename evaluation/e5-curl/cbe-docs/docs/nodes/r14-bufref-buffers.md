# Bufref Utility

**Capability.** Owns the reference-counted-style buffer reference: init/free/set/memdup plus read-only accessors, so callers can hand out owned buffers with custom destructors.

Use this subtree when code needs to pass buffer ownership around without copying, as SASL message builders and handle duplication do. Curl_bufref_set is the central repointing operation that releases the previous buffer first.

**Depended on by.**

- [Easy Handle Lifecycle & Transfers](r14-core-easy-lifecycle.md) · graph-confirmed · 10 edge(s) · Easy-handle duplication clones buffer-held state through the bufref API.
- [SASL / Web Auth Message Builders](r14-sasl-auth.md) · graph-confirmed · 2 edge(s)
- [Legacy HTTP form \(multipart\) API](r7-httppost-form.md) · graph-only · 42 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (5)

<a id="u-ac8cad6d65f5"></a>
### `bufref-c-accessors`

`const unsigned char *Curl_bufref_uptr(const struct bufref *br)` · [lib/bufref.c:L87-L94][f1]

Three read-only accessors over an initialized bufref: Curl_bufref_uptr returns the referenced data as an unsigned-char pointer, Curl_bufref_ptr returns it as a char pointer (no NUL termination guaranteed), and Curl_bufref_len returns the byte length.

Each only debug-asserts a valid signature and the ptr-or-empty invariant, then returns the stored field; none allocate or mutate.

**Uncertainties.**

- Validity of the passed bufref is enforced only by DEBUGBUILD signature assertions.

<a id="u-2c7e087ba1d6"></a>
### `Curl_bufref_free`

`void Curl_bufref_free(struct bufref *br)` · [lib/bufref.c:L54-L66][f1]

Releases the referenced buffer and resets the bufref so it can be reused.

If a buffer is present and a destructor was installed, the destructor runs on the un-consted pointer; with a NULL destructor the reference is dropped without freeing, which is how non-owning references are released. dtor, ptr and len are cleared; the debug signature is deliberately left intact. Debug builds assert the signature and the ptr-or-empty invariant.

uses: [bufref](r5-easy-handle-api.md#u-3e1a47ea9d30)

**Uncertainties.**

- A non-NULL ptr with NULL dtor is allowed by the code; whether any caller does this is not visible.

<a id="u-724f379bbcfd"></a>
### `Curl_bufref_init`

`void Curl_bufref_init(struct bufref *br)` · [lib/bufref.c:L37-L47][f1]

Initializes a bufref to an empty state: null destructor, null pointer, zero length.

In DEBUGBUILD builds it also stamps a signature constant used by later API-misuse assertions; in release builds no signature exists.

uses: [bufref](r5-easy-handle-api.md#u-3e1a47ea9d30)

**Uncertainties.**

- DEBUGASSERT behavior on failure is defined outside this file.

<a id="u-e9e6c8b284a8"></a>
### `Curl_bufref_memdup0`

`CURLcode Curl_bufref_memdup0(struct bufref *br, const void *ptr, size_t len)` · [lib/bufref.c:L120-L138][f1]

Copies a buffer of given length into a fresh allocation and installs it as the bufref content.

When ptr is NULL the copy is skipped and the bufref is set to NULL/len 0 with curl_free as destructor. On allocation failure it returns CURLE_OUT_OF_MEMORY without modifying the bufref; on success it installs the copy via Curl_bufref_set and returns CURLE_OK. Debug asserts check the signature, ptr/len consistency, and CURL_MAX_INPUT_LENGTH.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

<a id="u-214d3ce6e368"></a>
### `Curl_bufref_set`

`void Curl_bufref_set(struct bufref *br, const void *ptr, size_t len, void (*dtor)(voi…` · [lib/bufref.c:L72-L82][f1]

Repoints a bufref at a new buffer with length and destructor.

It first frees the previously referenced buffer via Curl_bufref_free, so the old destructor runs before the new values are stored. Debug assertions require ptr set iff len is nonzero and len not exceeding CURL_MAX_INPUT_LENGTH; these are checks, not enforced fallbacks.

calls: [Curl_bufref_free](r14-bufref-buffers.md#u-2c7e087ba1d6)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/bufref.c
