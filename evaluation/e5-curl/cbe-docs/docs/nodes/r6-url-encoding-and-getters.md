# URL Encoding and Retrieval

**Capability.** Percent-encoding rules and part formatting/retrieval: encoding and hex-normalizing parts, allowed-character sets, assembling full URLs, part getters with transformations, IDN host encode/decode, and same-origin/port queries.

Use when producing or reading URL strings. curl_url_get routes through urlget_format/urlget_url; urlencode_str and url_encode_part define what gets escaped. Same-origin and default-port helpers serve redirect logic.

**Depends on.**

- [CURLU Handle Management and Setters](r6-url-handle-api.md) · model-inferred · 0 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 25 edge(s)

**Depended on by.**

- [URL Parse Pipeline](r6-url-parse-pipeline.md) · graph-confirmed · 6 edge(s)

Parent: [URL API \(urlapi\)](r6-url-api.md)

## Units (14)

<a id="u-e04ced770fa0"></a>
### `urlencode_str`

`UNITTEST CURLUcode urlencode_str(struct dynbuf *o, const char *url, size_t len, bool …` · [lib/urlapi.c:L127-L203][f1]

Copies a URL part into an output dynbuf while percent-encoding only bytes that must be encoded.

With relative=false it first copies everything before the host separator verbatim via find_host_sep and reduces len accordingly. Per byte: a space becomes '%20', or '+' when query==QUERY_YES; control bytes (<0x20) and bytes >=0x7f become %XX; a '%' followed by two hex digits containing lowercase letters is re-emitted uppercased. Any other run of bytes is copied verbatim, except that in QUERY_NOT_YET mode a '?' is copied once and the mode transitions to QUERY_YES for the remainder. CURLcode failures map through cc2cu to CURLUE_TOO_LARGE or CURLUE_OUT_OF_MEMORY.

calls: [find_host_sep](r6-url-encoding-and-getters.md#u-a46f7b5cba69)

**Uncertainties.**

- Exact QUERY_NO vs QUERY_NOT_YET semantics beyond the '?' transition are governed by the enum defined outside this file.

<a id="u-53fa22774617"></a>
### `url_encode_part`

`static CURLUcode url_encode_part(struct dynbuf *encp, const char *part, bool plusenco…` · [lib/urlapi.c:L1956-L1985][f1]

Percent-encodes a part string into a dynbuf byte by byte.

A space becomes '+' when plusencode. Unreserved bytes, path-allowed bytes in pathmode, and the first '=' when equalsencode are copied literally, with equalsencode cleared after the first '=' so later ones are encoded. Everything else becomes %XX via Curl_hexbyte. Dynbuf errors map through cc2cu.

calls: [allowed_in_path](r6-url-encoding-and-getters.md#u-8fcec1ee34b5)

<a id="u-4d5627625248"></a>
### `url_uppercasehex_part`

`static CURLUcode url_uppercasehex_part(struct dynbuf *encp, const char *part)` · [lib/urlapi.c:L1987-L2007][f1]

Copies a part into the dynbuf unchanged, then uppercases any lowercase hex digits in existing percent-escapes in place, advancing three bytes per escape.

Dynbuf append failure maps through cc2cu.

<a id="u-8fcec1ee34b5"></a>
### `allowed_in_path`

`static bool allowed_in_path(unsigned char x)` · [lib/urlapi.c:L1930-L1954][f1]

Returns TRUE for the fixed set of sub-delim and extra characters allowed unencoded in paths ('!$&\'(){}[]*+,;=:@/'), FALSE otherwise.

<a id="u-7593cf8fcbca"></a>
### `url_append_query`

`static CURLUcode url_append_query(CURLU *u, struct dynbuf *encp)` · [lib/urlapi.c:L2009-L2045][f1]

Appends an encoded query string to an existing query under CURLU_APPENDQUERY.

When an old query exists, a '&' is inserted only if the old query does not already end with '&', and the combined string replaces u->query; the incoming dynbuf is freed either way. With no existing query the incoming buffer is adopted directly after freeing the old value. Any dynbuf failure frees both buffers and returns the mapped OOM/too-large code.

<a id="u-a46f7b5cba69"></a>
### `find_host_sep`

`static const char *find_host_sep(const char *url)` · [lib/urlapi.c:L87-L101][f1]

Locates the character ending the hostname in a URL string.

It searches for '//'; if absent the hostname starts at the string start, otherwise two bytes past the marker. It then advances to the first '/', '?', or NUL and returns that pointer, so a URL like http://host?id=1 yields the '?' as the host separator.

<a id="u-770bb73cd6cf"></a>
### `curl_url_get`

`CURLUcode curl_url_get(const CURLU *u, CURLUPart what, char **part, unsigned int flags)` · [lib/urlapi.c:L1682-L1781][f1]

Public getter for individual URL parts.

NULL handle or part pointer give CURLUE_BAD_HANDLE / CURLUE_BAD_PARTPOINTER; *part starts NULL. Each part selects its field and a part-specific 'missing' error (CURLUE_NO_SCHEME, NO_USER, ...); CURLUPART_URL delegates to urlget_url. Scheme and port requests never URL-decode; for the scheme, CURLU_NO_GUESS_SCHEME with a guessed scheme reports CURLUE_NO_SCHEME. Port rendering matches urlget_url's default-port rules (suppress matching default under CURLU_NO_DEFAULT_PORT, emit scheme default under CURLU_DEFAULT_PORT). The path defaults to '/'. For queries, a stored empty query is treated as missing unless CURLU_GET_EMPTY, and URLDECODE enables plus-to-space conversion; for fragments, an empty-but-present fragment is returned as '' only with CURLU_GET_EMPTY. A found value is formatted by urlget_format; otherwise the part's ifmissing code is returned.

calls: [urlget_url](r6-url-encoding-and-getters.md#u-912e3f9fc3ae), [urlget_format](r6-url-encoding-and-getters.md#u-58bf5adffadb)

<a id="u-58bf5adffadb"></a>
### `urlget_format`

`static CURLUcode urlget_format(const CURLU *u, CURLUPart what, const char *ptr, char …` · [lib/urlapi.c:L1487-L1553][f1]

Formats a single stored URL part for retrieval, applying transformations in a fixed order on a copy of the input string.

plusdecode converts '+' to space (used for queries). CURLU_URLDECODE decodes with control bytes rejected, failing as CURLUE_URLDECODE. CURLU_URLENCODE re-encodes with urlencode_str in QUERY_YES mode only for the query part. For hosts, CURLU_PUNYCODE decodes a non-ASCII stored host to punycode and CURLU_PUNY2IDN converts an ASCII host to IDN, both via host_decode/host_encode (each frees the intermediate). The transformed string is returned through *partp; allocation failures are CURLUE_OUT_OF_MEMORY.

calls: [urlencode_str](r6-url-encoding-and-getters.md#u-e04ced770fa0), [host_decode](r6-url-encoding-and-getters.md#u-de51b2fed5fa), [host_encode](r6-url-encoding-and-getters.md#u-0d3ca678b39c)

**Uncertainties.**

- Curl_is_ASCII_name behavior is defined outside this file.

<a id="u-912e3f9fc3ae"></a>
### `urlget_url`

`static CURLUcode urlget_url(const CURLU *u, char **part, unsigned int flags)` · [lib/urlapi.c:L1569-L1680][f1]

Assembles the complete URL string for CURLUPART_URL retrieval.

file: schemes go to file_url; otherwise a missing host is CURLUE_NO_HOST. Scheme resolution uses u->scheme, the 'https' default under CURLU_DEFAULT_SCHEME, or fails with CURLUE_NO_SCHEME. Port handling: a stored port is rendered, suppressed when it equals the scheme default and CURLU_NO_DEFAULT_PORT is set, and the scheme's default port is emitted when CURLU_DEFAULT_PORT is set and none is stored; options are only included when the scheme handler sets PROTOPT_URLOPTIONS. A bracketed IPv6 host gets '%25'-joined zoneid; otherwise CURLU_URLENCODE, CURLU_PUNYCODE, or CURLU_PUNY2IDN transform the host. A guessed scheme is omitted from the output when CURLU_NO_GUESS_SCHEME is set. All pieces are joined with printf, defaulting the path to '/'; empty-present query/fragment produce separators when CURLU_GET_EMPTY is set.

calls: [file_url](r6-url-encoding-and-getters.md#u-bbd2c045d60e), [host_decode](r6-url-encoding-and-getters.md#u-de51b2fed5fa), [host_encode](r6-url-encoding-and-getters.md#u-0d3ca678b39c)

**Uncertainties.**

- curl_easy_escape with a NULL handle is used for host encoding; its behavior is external.

<a id="u-bbd2c045d60e"></a>
### `file_url`

`static CURLUcode file_url(const CURLU *u, char **part, const char *fragmentsep, const…` · [lib/urlapi.c:L1555-L1567][f1]

Builds a full file:// URL string with curl_maprintf from the path plus optional query and fragment, using caller-provided separators so empty-but-present parts emit '?' or '#'.

Allocation failure is CURLUE_OUT_OF_MEMORY.

<a id="u-0d3ca678b39c"></a>
### `host_encode`

`static CURLUcode host_encode(const char *host, char **allochost)` · [lib/urlapi.c:L1477-L1484][f1]

IDN build only: encodes a Unicode host to punycode via Curl_idn_encode with the same error mapping (OOM or CURLUE_BAD_HOSTNAME).

Without IDN support it is a macro returning CURLUE_LACKS_IDN.

**Uncertainties.**

- Whether this file is compiled with USE_IDN is a build-time decision.

<a id="u-de51b2fed5fa"></a>
### `host_decode`

`static CURLUcode host_decode(const char *host, char **allochost)` · [lib/urlapi.c:L1468-L1475][f1]

IDN build only: decodes a punycode/ASCII host to Unicode via Curl_idn_decode, mapping CURLE_OUT_OF_MEMORY to CURLUE_OUT_OF_MEMORY and any other error to CURLUE_BAD_HOSTNAME.

When IDN is disabled the symbol is a macro yielding CURLUE_LACKS_IDN.

**Uncertainties.**

- Whether this file is compiled with USE_IDN is a build-time decision.

<a id="u-8385213ff7aa"></a>
### `Curl_url_get_port`

`CURLUcode Curl_url_get_port(CURLU *u, uint16_t *pport)` · [lib/urlapi.c:L2233-L2248][f1]

Returns the handle's stored port, or the scheme's default port when none is stored but the scheme is known and has a default.

Otherwise *pport is zeroed and CURLUE_NO_PORT is returned. No NULL-check of the handle is performed here.

**Uncertainties.**

- Caller is expected to pass a valid handle; no guard exists in this function.

<a id="u-4dfe9cb05589"></a>
### `Curl_url_same_origin`

`bool Curl_url_same_origin(CURLU *base, CURLU *href)` · [lib/urlapi.c:L2198-L2231][f1]

Reports whether href is same-origin as base.

Base must have both scheme and host. A differing href scheme fails. With an href host, base and host must match case-insensitively; ports must then agree: when only one side stores a port, the scheme's default port must equal the stored one (an unknown scheme cannot match), when both or neither store ports the portnum values must be equal, and zoneids must match (empty when absent). An href without a host is same-origin only if it also has no port. Only base's scheme is looked up; href without its own scheme inherits base's.

uses: [Curl_url_get_port](r6-url-encoding-and-getters.md#u-8385213ff7aa)

**Uncertainties.**

- curl_strequal and Curl_get_scheme semantics are defined in other files.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/urlapi.c
