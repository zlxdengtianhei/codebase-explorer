# CURLU Handle Management and Setters

**Capability.** Lifecycle of the URL handle and the public setter surface: allocation, deep copy, cleanup, part clearing, scheme/port validation and storage.

Use for the public curl_url_* entry points. curl_url_set dispatches to the set_url/scheme/port/host implementations; dup and cleanup manage whole-handle lifetime.

**Depends on.**

- [URL Parse Pipeline](r6-url-parse-pipeline.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Request Construction and Send](r6-http-request-build.md) · graph-confirmed · 14 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-confirmed · 16 edge(s)
- [IPFS URL Rewriting](r6-tool-ipfs-rewrite.md) · graph-confirmed · 8 edge(s)
- [Tool URL and Operation Helpers](r6-tool-operation-helpers.md) · graph-confirmed · 8 edge(s)
- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · model-inferred · 0 edge(s)
- [URL Encoding and Retrieval](r6-url-encoding-and-getters.md) · model-inferred · 0 edge(s)

Parent: [URL API \(urlapi\)](r6-url-api.md)

## Units (8)

<a id="u-c69ca9bdf3f3"></a>
### `curl_url`

`CURLU *curl_url(void)` · [lib/urlapi.c:L1412-L1415][f1]

Allocates a zeroed Curl_URL handle; NULL on allocation failure.

<a id="u-9d451bd158e3"></a>
### `curl_url_cleanup`

`void curl_url_cleanup(CURLU *u)` · [lib/urlapi.c:L1417-L1423][f1]

Frees all fields of a URL handle and the handle itself; a NULL pointer is ignored.

calls: [free_urlhandle](r6-url-handle-api.md#u-a36f88ccce10)

<a id="u-3dae878c835b"></a>
### `curl_url_dup`

`CURLU *curl_url_dup(const CURLU *in)` · [lib/urlapi.c:L1434-L1462][f1]

Deep-copies a URL handle into a fresh zeroed struct, strdup'ing each present string field (scheme, user, password, options, host, path, query, fragment, zoneid) via the DUP macro, which jumps to fail on allocation failure.

Port and present/guessed flags are copied by value. A NULL input returns NULL; on failure the partial copy is cleaned up and NULL returned.

calls: [curl_url_cleanup](r6-url-handle-api.md#u-9d451bd158e3)

<a id="u-a36f88ccce10"></a>
### `free_urlhandle`

`static void free_urlhandle(struct Curl_URL *u)` · [lib/urlapi.c:L69-L81][f1]

Releases all heap-allocated fields of a Curl_URL handle and zeroes the password buffer before freeing it.

<a id="u-d733644547e8"></a>
### `urlset_clear`

`static CURLUcode urlset_clear(CURLU *u, CURLUPart what)` · [lib/urlapi.c:L1882-L1928][f1]

Clears one URL part when it is set to NULL.

CURLUPART_URL resets the entire handle (freeing all fields and zeroing); others free their field, and scheme/query/fragment/port additionally reset guessed_scheme/query_present/fragment_present/port_present. Unknown parts return CURLUE_UNKNOWN_PART.

calls: [free_urlhandle](r6-url-handle-api.md#u-a36f88ccce10)

<a id="u-68d6b32905a9"></a>
### `curl_url_set`

`CURLUcode curl_url_set(CURLU *u, CURLUPart what, const char *part, unsigned int flags)` · [lib/urlapi.c:L2090-L2196][f1]

Public setter for URL parts.

A NULL handle is CURLUE_BAD_HANDLE and a NULL part value clears via urlset_clear. Inputs over CURL_MAX_INPUT_LENGTH are CURLUE_MALFORMED_INPUT. Each part configures encoding behavior: scheme never encodes and is validated by set_url_scheme; port delegates to set_url_port; URL delegates to set_url; setting the host clears any zoneid; query sets plusencode, APPENDQUERY behavior and equalsencode and marks query_present; fragment marks fragment_present. Otherwise the value is encoded into a dynbuf (sized 3x+1 for hosts, at least 16) with an enforced leading '/' for paths, using url_encode_part when CURLU_URLENCODE, else url_uppercasehex_part. APPENDQUERY routes to url_append_query; hosts go through url_sethost. On success the old value is zero-wiped (passwords) and freed, and the encoded buffer is stored.

calls: [set_url_scheme](r6-url-handle-api.md#u-5c0f97bfd745), [set_url_port](r6-url-handle-api.md#u-882a9ac12474), [set_url](r6-url-parse-pipeline.md#u-d22ad9a37b74), [urlset_clear](r6-url-handle-api.md#u-d733644547e8), [url_encode_part](r6-url-encoding-and-getters.md#u-53fa22774617), [url_uppercasehex_part](r6-url-encoding-and-getters.md#u-4d5627625248), [url_append_query](r6-url-encoding-and-getters.md#u-7593cf8fcbca), [url_sethost](r6-url-host-authority.md#u-1748b7a86cdd)

**Uncertainties.**

- The CURLMAX sizing macro and CURL_UNCONST are defined in headers outside this file.

<a id="u-5c0f97bfd745"></a>
### `set_url_scheme`

`static CURLUcode set_url_scheme(CURLU *u, const char *scheme, unsigned int flags)` · [lib/urlapi.c:L1783-L1812][f1]

Validates a scheme string before storing it: length must be 1..MAX_SCHEME_LEN (else CURLUE_BAD_SCHEME).

Known schemes are accepted unless they lack a run handler and CURLU_NON_SUPPORT_SCHEME is unset (CURLUE_UNSUPPORTED_SCHEME). For unknown schemes the syntax ALPHA *(ALNUM/'+'/'-'/'.') is enforced manually, else CURLUE_BAD_SCHEME. On success u->guessed_scheme resets to FALSE.

**Uncertainties.**

- h->run semantics live in the scheme table definition outside this file.

<a id="u-882a9ac12474"></a>
### `set_url_port`

`static CURLUcode set_url_port(CURLU *u, const char *provided_port)` · [lib/urlapi.c:L1814-L1826][f1]

Parses and stores a port number: the first byte must be a digit, then curlx_str_number must consume the whole string with a 0xffff cap; any deviation returns CURLUE_BAD_PORT_NUMBER.

Success stores the value and sets port_present.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/urlapi.c
