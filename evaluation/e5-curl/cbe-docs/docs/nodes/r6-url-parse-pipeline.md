# URL Parse Pipeline

**Capability.** Core parsing of a URL string into a Curl_URL: scheme detection and legacy guessing, authority split, path/query/fragment handling, file: URLs, and dot-segment removal.

Use to follow how a raw string becomes structured parts. parseurl orchestrates scheme, authority and component handlers; set_url and redirect_url implement the CURLUPART_URL set path including relative references.

**Depends on.**

- [URL Encoding and Retrieval](r6-url-encoding-and-getters.md) · graph-confirmed · 6 edge(s)
- [Authority and Host Handling](r6-url-host-authority.md) · graph-confirmed · 4 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 25 edge(s)

**Depended on by.**

- [CURLU Handle Management and Setters](r6-url-handle-api.md) · graph-confirmed · 1 edge(s)

Parent: [URL API \(urlapi\)](r6-url-api.md)

## Units (14)

<a id="u-00c4b188e415"></a>
### `parseurl`

`static CURLUcode parseurl(const char *url, CURLU *u, unsigned int flags)` · [lib/urlapi.c:L1224-L1312][f1]

Core URL parser filling a Curl_URL from a string.

Input longer than CURL_MAX_INPUT_LENGTH is CURLUE_MALFORMED_INPUT. The scheme is detected with Curl_is_absolute_url using guessing flags. A 'file' scheme delegates entirely to parse_file. Otherwise parse_scheme establishes the scheme and host start; the host ends at the first '/', '?' or '#'. A non-empty host goes through parse_authority, then guess_scheme applies a hostname-based scheme when guessing was requested and none was set; an empty host is tolerated only with CURLU_NO_AUTHORITY (else CURLUE_NO_HOST). The remaining tail is split in order into fragment (handle_fragment), query (handle_query), and path (handle_path), each only if prior steps succeeded. On full success u->host takes the dynbuf buffer; any failure frees the dynbuf and all handle fields via free_urlhandle.

calls: [parse_file](r6-url-parse-pipeline.md#u-eee2350cd486), [parse_scheme](r6-url-parse-pipeline.md#u-b1865dc1f2ff), [parse_authority](r6-url-host-authority.md#u-eed9a82d861f), [guess_scheme](r6-url-parse-pipeline.md#u-34f0ac02073e), [handle_fragment](r6-url-parse-pipeline.md#u-aba23c156e2a), [handle_query](r6-url-parse-pipeline.md#u-e62c9bfbd521), [handle_path](r6-url-parse-pipeline.md#u-76a73a573143), [free_urlhandle](r6-url-handle-api.md#u-a36f88ccce10)

<a id="u-1747cc202a9f"></a>
### `parseurl_and_replace`

`static CURLUcode parseurl_and_replace(const char *url, CURLU *u, unsigned int flags)` · [lib/urlapi.c:L1317-L1329][f1]

Parses a URL into a temporary zeroed Curl_URL and, only on success, frees the target handle's fields and copies the temporary over it by value; on failure the target is untouched.

calls: [parseurl](r6-url-parse-pipeline.md#u-00c4b188e415), [free_urlhandle](r6-url-handle-api.md#u-a36f88ccce10)

<a id="u-b1865dc1f2ff"></a>
### `parse_scheme`

`static CURLUcode parse_scheme(const char *url, CURLU *u, char *schemebuf, size_t sche…` · [lib/urlapi.c:L1034-L1090][f1]

Determines the scheme and where the authority starts during URL parsing.

With a scheme present, an unknown scheme fails with CURLUE_UNSUPPORTED_SCHEME unless CURLU_NON_SUPPORT_SCHEME is set; fewer than one slash gives CURLUE_BAD_SLASHES. Slash counting accepts up to 2 with CURLU_NO_AUTHORITY, otherwise up to 3 (4+ slashes are CURLUE_BAD_SLASHES); *hostpp points after the slashes. Without a scheme, both CURLU_DEFAULT_SCHEME and CURLU_GUESS_SCHEME being unset yields CURLUE_BAD_SCHEME; DEFAULT_SCHEME selects 'https' and the whole URL becomes the host start. A chosen scheme is strdup'd into u->scheme (OOM propagated).

**Uncertainties.**

- Curl_getn_scheme behavior for unknown schemes is external.

<a id="u-34f0ac02073e"></a>
### `guess_scheme`

`static CURLUcode guess_scheme(CURLU *u, struct dynbuf *host)` · [lib/urlapi.c:L1092-L1118][f1]

Legacy curl-style scheme guessing from the hostname prefix: ftp., dict., ldap., imap., smtp., pop3.

map to their schemes, everything else to http. The scheme is strdup'd (CURLUE_OUT_OF_MEMORY on failure) and u->guessed_scheme is set TRUE so later getters can hide the guessed value.

<a id="u-a006636e95c1"></a>
### `Curl_is_absolute_url`

`size_t Curl_is_absolute_url(const char *url, char *buf, size_t buflen, bool guess_sch…` · [lib/urlapi.c:L213-L253][f1]

Tests whether a URL string starts with an absolute scheme and returns the scheme-name length, 0 if relative.

It lowercases up to MAX_SCHEME_LEN leading ALPHA/ALNUM/'+'-/'-'/'. characters into buf when buf is non-NULL, always leaving buf defined (empty when not absolute). The URL is absolute when at least one leading char matched and url[i]==':' followed by '/' — or by anything when guess_scheme is false (so data: URLs count). On _WIN32 with guessing, a drive-letter prefix like c: is rejected first.

**Uncertainties.**

- buf is treated as write-only scratch; buflen is only asserted in debug builds.

<a id="u-eee2350cd486"></a>
### `parse_file`

`UNITTEST CURLUcode parse_file(const char *url, size_t urllen, CURLU *u, const char **…` · [lib/urlapi.c:L944-L1032][f1]

Parses file: URLs into a scheme and a path pointer, rejecting malformed ones with CURLUE_BAD_FILE_URL.

Requires more than 'file:/' and a path starting with '/'. For 'file://' forms, an authority must be empty, a Windows drive prefix, 'localhost', or '127.0.0.1' (the latter two skipped over); anything else is a bad file URL. On non-Windows platforms Windows drive letters (file:/c: or file:c:) are rejected; on Windows builds a leading slash before the drive letter is dropped by advancing the path. On success u->scheme is strdup'd as 'file' (OOM possible) and the path pointer/length are returned via out-params.

**Uncertainties.**

- checkprefix is defined elsewhere; exact prefix matching semantics assumed case-insensitive per curl convention.

<a id="u-76a73a573143"></a>
### `handle_path`

`static CURLUcode handle_path(CURLU *u, const char *path, size_t pathlen, unsigned int…` · [lib/urlapi.c:L1179-L1222][f1]

Stores and cleans the path component.

With CURLU_URLENCODE and a non-empty path the path is percent-encoded first (spaces as %20) and pathlen/path point into the encoding buffer. Non-trivial paths are rejected by badoctets (CURLUE_BAD_PATH). The path is copied into u->path unless the encoded buffer is already stored, in which case it is NUL-terminated at pathlen since encoding may cover more than the path. Unless CURLU_PATH_AS_IS is set, dedotdotify removes dot segments, replacing u->path; its nonzero return maps to CURLUE_OUT_OF_MEMORY. file: URLs accept one-byte paths, others require two.

calls: [urlencode_str](r6-url-encoding-and-getters.md#u-e04ced770fa0), [dedotdotify](r6-url-parse-pipeline.md#u-ff32dfffc847)

<a id="u-e62c9bfbd521"></a>
### `handle_query`

`static CURLUcode handle_query(CURLU *u, const char *query, size_t qlen, unsigned int …` · [lib/urlapi.c:L1146-L1177][f1]

Stores the query part, marking query_present first.

With CURLU_URLENCODE the text after '?' is encoded with urlencode_str in QUERY_YES mode (spaces become '+'); otherwise badoctets may reject with CURLUE_BAD_QUERY and the text is memdup'd. A query consisting of only '?' stores an empty string (OOM if strdup fails).

calls: [urlencode_str](r6-url-encoding-and-getters.md#u-e04ced770fa0)

<a id="u-aba23c156e2a"></a>
### `handle_fragment`

`static CURLUcode handle_fragment(CURLU *u, const char *fragment, size_t fraglen, unsi…` · [lib/urlapi.c:L1120-L1144][f1]

Stores the fragment part of a URL, first marking fragment_present even when empty.

With more than the '#' alone: under CURLU_URLENCODE the text after '#' is encoded with urlencode_str (QUERY_NO, so spaces become %20); otherwise badoctets rejects control bytes with CURLUE_BAD_FRAGMENT and the text is memdup'd (OOM on allocation failure).

calls: [urlencode_str](r6-url-encoding-and-getters.md#u-e04ced770fa0)

<a id="u-ff32dfffc847"></a>
### `dedotdotify`

`UNITTEST int dedotdotify(const char *input, size_t clen, char **outp)` · [lib/urlapi.c:L835-L937][f1]

Removes '.' and '..' segments from a null-terminated path per RFC 3986 section 5.2.4, writing the result into a dynbuf.

needs_dedotdot short-circuits clean paths, leaving *outp NULL (meaning 'nothing to do'). Leading './', '../', and bare '.'/'..' prefixes are stripped first, with a path consisting only of dots jumping straight to output. In the main loop, a '/' followed by a lone dot yields a trailing '/' and stops; '/./' is skipped; '/../' removes the last output segment by trimming the buffer at its final '/' (via memrchr) and continues, or emits '/' if at the end. Any other byte is copied one at a time. Success returns 0 with *outp set to the dynbuf contents, or an empty strdup when the output is empty (strdup failure returns 1). Any dynbuf error returns 1.

calls: [needs_dedotdot](r6-url-parse-pipeline.md#u-f054a9ae963e), [is_dot](r6-url-parse-pipeline.md#u-fa45e36fa5a7)

**Uncertainties.**

- On a dynbuf failure the allocated output dynbuf may not be freed; no cleanup is visible in this scope.

<a id="u-f054a9ae963e"></a>
### `needs_dedotdot`

`static bool needs_dedotdot(const char *p, size_t pn)` · [lib/urlapi.c:L794-L816][f1]

Cheap prescan deciding whether a path needs RFC 3986 dot-segment removal.

Strings shorter than 2 bytes or without any '.' or '%' return FALSE. It scans for a dot segment followed by end-of-string or '/', or a dotdot segment so followed, returning TRUE in those cases; otherwise FALSE.

calls: [is_dot](r6-url-parse-pipeline.md#u-fa45e36fa5a7)

<a id="u-fa45e36fa5a7"></a>
### `is_dot`

`static bool is_dot(const char **str, size_t *clen)` · [lib/urlapi.c:L774-L789][f1]

Consumes one dot segment from a string: a literal '.' or the percent-encoded '%2e'/'%2E' (case-insensitive via |0x20).

On match it advances *str past the segment, decrements *clen, and returns TRUE; otherwise FALSE with no change.

<a id="u-d22ad9a37b74"></a>
### `set_url`

`static CURLUcode set_url(CURLU *u, const char *url, size_t part_size, unsigned int fl…` · [lib/urlapi.c:L1828-L1880][f1]

Implements setting CURLUPART_URL, handling blank and relative inputs.

An empty string is valid only when a complete URL already exists: success keeps everything but clears the fragment (RFC 3986 5.2.2); failure is MALFORMED_INPUT unless it was OOM. An absolute new URL (per Curl_is_absolute_url with the guessing flags) replaces everything via parseurl_and_replace. Otherwise the current URL is fetched with CURLU_GET_EMPTY and without CURLU_NO_GUESS_SCHEME so empty separators are preserved for correct splicing; OOM aborts, any other fetch failure replaces wholesale, and success splices via redirect_url. The old URL string is always freed.

calls: [curl_url_get](r6-url-encoding-and-getters.md#u-770bb73cd6cf), [parseurl_and_replace](r6-url-parse-pipeline.md#u-1747cc202a9f), [redirect_url](r6-url-parse-pipeline.md#u-9850a67069c7)

<a id="u-9850a67069c7"></a>
### `redirect_url`

`static CURLUcode redirect_url(const char *base, const char *relurl, CURLU *u, unsigne…` · [lib/urlapi.c:L1334-L1408][f1]

Builds an absolute URL by splicing a relative reference onto a base URL string.

The base's scheme prefix is assumed present (u->scheme or 'https' default); a NULL base is CURLUE_MALFORMED_INPUT. The relative form decides the cutoff: '//' keeps the scheme and switches host (host_changed); '/path' cuts at the first '/' after the authority; '#frag' cuts at an existing '#' only if fragment_present; other forms cut an existing '?' when query_present, else a '#', and for non-'?'-led references cut after the last '/'. The kept base prefix plus the urlencoded remainder (QUERY_NOT_YET) form the new URL, which is applied with parseurl_and_replace after clearing CURLU_PATH_AS_IS from the flags. Dynbuf failures are CURLUE_OUT_OF_MEMORY.

calls: [urlencode_str](r6-url-encoding-and-getters.md#u-e04ced770fa0), [parseurl_and_replace](r6-url-parse-pipeline.md#u-1747cc202a9f)

**Uncertainties.**

- The scheme-prefix arithmetic assumes the base string literally starts with '<scheme>://'; no re-validation of that shape occurs here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/urlapi.c
