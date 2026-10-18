# Cookie jar storage and lifecycle

**Capability.** Owns the CookieInfo jar: hash bucketing, insertion with replacement/expiry policy, host/path lookups, sorting, Netscape serialization, and file load/save under the cookie share lock.

Start at Curl_cookie_add, Curl_cookie_getlist, Curl_cookie_loadfiles, and Curl_flush_cookies; parsing and matching helpers live in the sibling node.

**Depends on.**

- [Doubly linked list \(llist\)](r9-linked-list.md) · graph-only · 37 edge(s)

Parent: [Cookie jar](r12-cookie-jar.md)

## Units (26)

<a id="u-1f55e4a70337"></a>
### `cookie.c-module-residuals`

`group` · [lib/cookie.c:L1-L52][f1]

Non-behavioral regions of lib/cookie.c: the license header, build guards (#if !CURL_DISABLE_HTTP && !CURL_DISABLE_COOKIES) wrapping the whole file, include list, and small constants/macros (COOKIES_MAXAGE, MAX_DATE_LENGTH, COOKIE_NAME/VALUE/DOMAIN/PATH/PIECES).

**Uncertainties.**

- Several residual regions fall inside function bodies in the line map (e.g. between parse functions); their content is not visible in the excerpt, so they are treated as non-behavioral separators.

<a id="u-111e5270b0e5"></a>
### `Curl_cookie_add`

`CURLcode Curl_cookie_add(struct Curl_easy *data, struct CookieInfo *ci, const char *l…` · [lib/cookie.c:L984-L1091][f1]

Adds one cookie line (header or Netscape format) to the jar, applying prefix, PSL, session and replacement policies.

**Notes.**

- condition: Silently ignores adds once data->req.setcookies reaches MAX_SET_COOKIE_AMOUNT.
- condition: __Secure- requires co->secure; __Host- requires secure, path '/' and no tailmatch; file loads under newsession drop session cookies (no expires).
- failure: Any parse, prefix, PSL, session, replacement, or OOM failure goes to fail: the partially filled stack struct's strings are freed and the stored result is returned.
- side_effect: On success the cookie is heap-cloned, appended to the bucket given by cookiehash(co->domain), numcookies increments when not replacing, next_expiration may lower, and setcookies counts up for header lines; ci->lastct assigns creationtime and livecookie mirrors ci->running.
- condition: remove_expired runs unless COOKIE_NOEXPIRE is set in flags.

<a id="u-7250284b8b00"></a>
### `Curl_cookie_cleanup`

`void Curl_cookie_cleanup(struct CookieInfo *ci)` · [lib/cookie.c:L1472-L1478][f1]

Frees all cookies in the jar and the jar struct itself; NULL is a no-op.

<a id="u-5cda38d4b3cb"></a>
### `Curl_cookie_clearall`

`void Curl_cookie_clearall(struct CookieInfo *ci)` · [lib/cookie.c:L1421-L1437][f1]

Removes and frees every cookie in the jar and resets numcookies to 0; NULL jar is a no-op.

<a id="u-885a7c3dd3d2"></a>
### `Curl_cookie_clearsess`

`void Curl_cookie_clearsess(struct CookieInfo *ci)` · [lib/cookie.c:L1444-L1465][f1]

Removes and frees all session cookies (those without an expiry), decrementing numcookies; NULL jar is a no-op.

<a id="u-8bbdec46e2ee"></a>
### `Curl_cookie_getlist`

`CURLcode Curl_cookie_getlist(struct Curl_easy *data, bool *okay, const char *host, st…` · [lib/cookie.c:L1314-L1414][f1]

Collects the cookies to send for a host/path into a caller-provided list, sorted longest-path first.

**Notes.**

- condition: Returns empty with *okay FALSE when no jar or no cookies in the host's hash bucket; expired cookies are pruned first.
- condition: A cookie matches when secure allows it (via Curl_secure_context), the domain matches (tailmatch or exact; IP hosts match by exact/IP rules), and the path matches; matching stops at MAX_COOKIE_SEND_AMOUNT.
- failure: On allocation failure the result list is destroyed and CURLE_OUT_OF_MEMORY returned; otherwise the matched list is rebuilt in cookie_sort order and *okay set TRUE.

<a id="u-8570927d82e9"></a>
### `Curl_cookie_init`

`struct CookieInfo *Curl_cookie_init(void)` · [lib/cookie.c:L1107-L1125][f1]

Allocates and initializes an empty CookieInfo jar with all hash lists and the expiration tracker; returns NULL on OOM.

<a id="u-edc8296dcb31"></a>
### `Curl_cookie_list`

`struct curl_slist *Curl_cookie_list(struct Curl_easy *data)` · [lib/cookie.c:L1658-L1665][f1]

Locks the cookie share, builds the cookie list, and unlocks; returns the list.

<a id="u-1e8d227a05b1"></a>
### `Curl_cookie_loadfiles`

`CURLcode Curl_cookie_loadfiles(struct Curl_easy *data, int flags)` · [lib/cookie.c:L1219-L1242][f1]

Loads every registered cookie file (CURLOPT_COOKIEFILE list) under the cookie share lock, creating the jar on first use.

**Notes.**

- failure: Returns CURLE_OUT_OF_MEMORY if the jar cannot be allocated, or the first cookie_load error otherwise; a NULL cookielist is a no-op returning CURLE_OK.

<a id="u-b6b48f4206b9"></a>
### `Curl_cookie_run`

`void Curl_cookie_run(struct Curl_easy *data)` · [lib/cookie.c:L1692-L1698][f1]

Under the cookie lock, marks the jar as running so later adds count as live cookies; no-op without a jar.

<a id="u-1736ce87dc1d"></a>
### `Curl_flush_cookies`

`void Curl_flush_cookies(struct Curl_easy *data, bool cleanup)` · [lib/cookie.c:L1667-L1690][f1]

Under the cookie lock, saves the jar to the configured cookiejar file and optionally destroys the jar.

**Notes.**

- condition: Saving happens only when a cookiejar string is set and data->cookies->running is TRUE (a transfer was started).
- failure: cookie_output failure logs a warning with the strerror text but does not propagate.
- side_effect: With cleanup set and the jar not shared, the jar is freed and data->cookies nulled.

<a id="u-65adaf6828ed"></a>
### `cookie_load`

`static CURLcode cookie_load(struct Curl_easy *data, const char *file, struct CookieIn…` · [lib/cookie.c:L1136-L1214][f1]

Reads cookies from a file (or stdin for '-'), feeding each line to Curl_cookie_add.

**Notes.**

- condition: ci->newsession is set from COOKIE_NOSESSION and ci->running cleared during load; 'Set-Cookie:'-prefixed lines are parsed as header lines after skipping blanks.
- condition: A directory filename is rejected with a warning; an unopenable file only warns.
- failure: Individual cookie errors are swallowed except CURLE_OUT_OF_MEMORY, which stops the loop and propagates.
- side_effect: After reading, remove_expired runs, the file is closed, state.cookie_engine set TRUE, and ci->running set TRUE.

<a id="u-e85141a043ea"></a>
### `cookie_output`

`static CURLcode cookie_output(struct Curl_easy *data, struct CookieInfo *ci, const ch…` · [lib/cookie.c:L1521-L1616][f1]

Writes the jar in Netscape format to a file (atomic temp+rename) or stdout for '-'.

**Notes.**

- condition: Expired cookies are pruned first; only cookies with a domain are written, sorted by creation time; a NULL jar is a no-op.
- failure: Curl_fopen failure, array/format allocation failure, or rename failure return the error; on error the temp file is unlinked and non-stdout handles closed.
- side_effect: For non-stdout targets the output is written to a temp file which is renamed onto the target only on success.

<a id="u-8d639e98b934"></a>
### `cookie_list`

`static struct curl_slist *cookie_list(const struct Curl_easy *data)` · [lib/cookie.c:L1618-L1656][f1]

Builds a curl_slist of Netscape-format lines for all domain-ful cookies, pruning expired ones first.

**Notes.**

- condition: Returns NULL when there is no jar, no cookies, or on any allocation failure (frees the partial list).

<a id="u-0ffe443a16a5"></a>
### `get_netscape_format`

`static char *get_netscape_format(const struct Cookie *co)` · [lib/cookie.c:L1487-L1511][f1]

Formats a cookie as a Netscape file line (no trailing newline); caller frees the result.

**Notes.**

- condition: Missing domain prints 'unknown', missing path '/', missing value empty; tailmatching domains get a leading dot; httponly cookies get the '#HttpOnly_' preamble.

<a id="u-f59568daaf9c"></a>
### `remove_expired`

`static void remove_expired(struct CookieInfo *ci)` · [lib/cookie.c:L274-L316][f1]

Removes expired cookies from all hash buckets, updating the jar's next-expiration tracker.

**Notes.**

- condition: Exits early without scanning when the recorded next_expiration is in the future (and not CURL_OFF_T_MAX); otherwise resets the tracker to CURL_OFF_T_MAX and lowers it to the earliest remaining expiry.
- side_effect: Each expired cookie is unlinked, fully freed, and ci->numcookies is decremented.

<a id="u-df09a668e04d"></a>
### `replace_existing`

`static bool replace_existing(struct Curl_easy *data, struct Cookie *co, const struct …` · [lib/cookie.c:L870-L974][f1]

Finds and removes an existing cookie superseded by the new one, enforcing secure-overlay rules and live-cookie preference.

**Notes.**

- condition: A replacement candidate matches name exactly, domains equal (or both absent), and paths equal (including both-path-or-both-none).
- condition: A non-secure new cookie is refused when it would path-overlay an existing secure cookie with the same name and matching domains (path-prefix check stops at the first '/' after the leading char).
- condition: A file-loaded (non-live) cookie never replaces a live (header-set) cookie.
- side_effect: On replacement the old node is unlinked and freed, and the new cookie inherits the old creationtime.

<a id="u-32b955896950"></a>
### `freecookie`

`static void freecookie(struct Cookie *co, bool maintoo)` · [lib/cookie.c:L64-L72][f1]

Frees a cookie's string fields, optionally the struct itself.

**Notes.**

- contract: The maintoo flag controls whether the Cookie struct itself is freed, so callers removing a stack-allocated cookie pass FALSE.

<a id="u-bff188ccae4a"></a>
### `storecookie`

`static CURLcode storecookie(struct Cookie *co, const struct Curl_str *cp, const char …` · [lib/cookie.c:L371-L413][f1]

Copies parsed name/value/path/domain pieces into a Cookie struct with default fallbacks.

**Notes.**

- condition: When no Path attribute exists, the default is the request path up to and including the last slash (or the whole path if none).
- condition: When no Domain attribute exists, the default domain parameter is copied; each allocation failure yields CURLE_OUT_OF_MEMORY.

<a id="u-a158f90811bc"></a>
### `strstore`

`static CURLcode strstore(char **str, const char *newstr, size_t len)` · [lib/cookie.c:L256-L263][f1]

Allocates a copy of a string into *str, returning CURLE_OUT_OF_MEMORY on allocation failure.

<a id="u-3a4d2639cdfe"></a>
### `cookiehash`

`static size_t cookiehash(const char * const domain)` · [lib/cookie.c:L212-L222][f1]

Hashes a cookie domain for jar bucketing; IP addresses and NULL map to bucket 0.

calls: [get_top_domain](r12-cookie-jar-core.md#u-7e821ef3cb8e), [cookie_hash_domain](r12-cookie-jar-core.md#u-377b4b1a5eb5)

<a id="u-377b4b1a5eb5"></a>
### `cookie_hash_domain`

`static size_t cookie_hash_domain(const char *domain, const size_t len)` · [lib/cookie.c:L191-L203][f1]

Case-insensitive djb2-style hash of a domain, reduced modulo COOKIE_HASH_SIZE.

<a id="u-7e821ef3cb8e"></a>
### `get_top_domain`

`static const char *get_top_domain(const char * const domain, size_t *outlen)` · [lib/cookie.c:L162-L181][f1]

Returns a pointer to the second-level domain label (start of top two labels) and its length via outlen.

**Notes.**

- contract: With fewer than two dots it returns the domain itself with full length; NULL domain yields len 0.

<a id="u-e0425250375c"></a>
### `cookie_sort`

`static int cookie_sort(const void *p1, const void *p2)` · [lib/cookie.c:L1252-L1281][f1]

qsort comparator ordering cookies by descending path length, then domain length, then name length, with creationtime as final tiebreaker.

**Uncertainties.**

- The comment claims creationtime is unique per cookie; the comparator cannot verify this.

<a id="u-7fa7e03d9e76"></a>
### `cookie_sort_ct`

`static int cookie_sort_ct(const void *p1, const void *p2)` · [lib/cookie.c:L1288-L1294][f1]

qsort comparator ordering cookies by creation time (newest first).

<a id="u-50a2655b5e8b"></a>
### `Curl_secure_context`

`bool Curl_secure_context(struct Curl_easy *data, const char *host)` · [lib/cookie.c:L1296-L1302][f1]

Returns TRUE when the transfer is secure or the host is localhost, 127.0.0.1, or ::1.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cookie.c
