# HSTS Cache

**Capability.** Owns the HSTS cache: entry creation/match/eviction, Strict-Transport-Security header parsing, file and callback load/save, cache cloning, and expiry pruning.

Use this child to trace how HSTS entries enter the cache (header, file, callback), how they match a peer host, and how they are persisted. Date parsing of expiry stamps is delegated to parsedate.

**Depends on.**

- [Date Parsing](r10-parsedate.md) · graph-confirmed · 1 edge(s) · HSTS entry creation parses expiry stamps using the capped date parser.
- [Doubly linked list \(llist\)](r9-linked-list.md) · graph-only · 24 edge(s)

**Depended on by.**

- [Transfer Loop and Lifecycle](r10-transfer-loop.md) · graph-confirmed · 2 edge(s)

Parent: [HTTP Domain Policy Caches](r10-url-policy.md)

## Units (19)

<a id="u-a29314c17796"></a>
### `Curl_hsts_applies`

`bool Curl_hsts_applies(struct hsts *h, const struct Curl_peer *dest)` · [lib/hsts.c:L638-L641][f1]

Returns true when the peer's hostname matches an HSTS entry, enabling subdomain matching via hsts_check; the pointer is normalized with !!.

calls: [hsts_check](r10-hsts-cache.md#u-97720bdcb018)

<a id="u-08a59bb64394"></a>
### `Curl_hsts_cleanup`

`void Curl_hsts_cleanup(struct hsts **hp)` · [lib/hsts.c:L79-L94][f1]

Frees an entire HSTS cache.

If *hp is non-NULL it walks the entry list freeing each stsentry, then frees h->filename and the struct, and nulls *hp. No list-node destructor is registered, so node unlinking is implicit in freeing the whole struct.

calls: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e), [Curl_node_elem](r9-linked-list.md#u-640782ef2dbe), [Curl_node_next](r9-linked-list.md#u-0089ba08aa64)

<a id="u-adc22c015815"></a>
### `Curl_hsts_copy`

`CURLcode Curl_hsts_copy(struct hsts *dst, struct hsts *src)` · [lib/hsts.c:L138-L152][f1]

Clones all still-live entries from src into dst, used by easy-handle duplication.

For each src entry whose expiry is in the future it calls hsts_create on dst with host length, subdomain flag and expiry; the first error (e.g. out of memory) is propagated. Expired entries are skipped and src is not modified.

calls: [hsts_create](r10-hsts-cache.md#u-a73fa7ef3f8d)

**Uncertainties.**

- If the copy exceeds MAX_HSTS_ENTRIES, hsts_append evicts earlier entries silently.

<a id="u-85f212dd39be"></a>
### `Curl_hsts_init`

`struct hsts *Curl_hsts_init(void)` · [lib/hsts.c:L68-L75][f1]

Allocates a zeroed struct hsts with curlx_calloc and, on success, initializes its entry list with Curl_llist_init(NULL destructor); returns the struct or NULL on allocation failure.

calls: [Curl_llist_init](r9-linked-list.md#u-a99250aef25e)

<a id="u-d415407fc208"></a>
### `Curl_hsts_loadcb`

`CURLcode Curl_hsts_loadcb(struct Curl_easy *data, struct hsts *h)` · [lib/hsts.c:L613-L618][f1]

Returns CURLE_OK when h is NULL; otherwise delegates to hsts_pull to load entries from the read callback.

calls: [hsts_pull](r10-hsts-cache.md#u-622ec8736771)

<a id="u-c734d27c2d4f"></a>
### `Curl_hsts_loadfile`

`CURLcode Curl_hsts_loadfile(struct Curl_easy *data, struct hsts *h, const char *file)` · [lib/hsts.c:L602-L608][f1]

Thin wrapper asserting h is non-NULL, ignoring data, and delegating to hsts_load.

calls: [hsts_load](r10-hsts-cache.md#u-c11702ec500e)

<a id="u-f807f9357170"></a>
### `Curl_hsts_loadfiles`

`CURLcode Curl_hsts_loadfiles(struct Curl_easy *data)` · [lib/hsts.c:L620-L636][f1]

Loads every file named in data->state.hstslist under the HSTS share lock: takes CURL_LOCK_DATA_HSTS exclusively, calls Curl_hsts_loadfile for each list node into data->hsts, stopping and propagating the first error, then unlocks.

Returns CURLE_OK when the list is empty.

calls: [Curl_hsts_loadfile](r10-hsts-cache.md#u-c734d27c2d4f), [Curl_share_lock_share](r6-share-api.md#u-6146ca450d97), [Curl_share_unlock_share](r6-share-api.md#u-552c57d51f96)

<a id="u-0611c2c7240b"></a>
### `Curl_hsts_parse`

`CURLcode Curl_hsts_parse(struct hsts *h, const char *hostname, const char *header)` · [lib/hsts.c:L210-L310][f1]

Parses a Strict-Transport-Security header value and updates the cache for the hostname.

Returns CURLE_OK immediately for numeric IP hosts (RFC 6797 exclusion). The loop tokenizes ';'-separated directives: blanks and semicolons are skipped, a word is read up to ';', '=', CR/LF, space or tab; if followed by '=', the value is a quoted word or a run up to comma, space or line end. A duplicate max-age or duplicate includesubdomains returns CURLE_BAD_FUNCTION_ARGUMENT. max-age is parsed as a number capped at CAP_HSTS_MAX_AGE: overflow clamps to the cap, other parse errors return CURLE_BAD_FUNCTION_ARGUMENT. A missing max-age is an error. max-age=0 removes the exact-host entry if present and returns OK. Otherwise the relative age is added to now, clamped to CURL_OFF_T_MAX on overflow; an existing exact-host entry is updated in place with the new expiry and subdomain flag; otherwise a new entry is created via hsts_create.

calls: [hsts_check](r10-hsts-cache.md#u-97720bdcb018), [hsts_create](r10-hsts-cache.md#u-a73fa7ef3f8d), [Curl_host_is_ipnum](r5-dns-resolver.md#u-5cc77a1b33a7)

**Uncertainties.**

- Unknown directives are silently ignored; only max-age value and duplicates produce errors.

<a id="u-f3aa4e97ddaf"></a>
### `Curl_hsts_save`

`CURLcode Curl_hsts_save(struct Curl_easy *data, struct hsts *h, const char *file)` · [lib/hsts.c:L369-L425][f1]

Writes the HSTS cache to a file and/or the hsts_write callback.

Returns CURLE_OK immediately if h is NULL. With no explicit file it falls back to h->filename stored at load time; skips the file write entirely when the cache is marked CURLHSTS_READONLYFILE, or the filename is NULL or empty. Otherwise opens via Curl_fopen (tempstore mechanism), writes a comment header and one line per entry via hsts_out, closes, and renames tempstore over the target; a failed rename yields CURLE_WRITE_ERROR and the tempstore is unlinked on any failure. After the skip or save, if an hsts_write callback is set, every entry is pushed via hsts_push with an index counter; the loop stops on error or when the callback requests stop, and that error (or the earlier save error) is returned.

calls: [hsts_out](r10-hsts-cache.md#u-614139678aaa), [hsts_push](r10-hsts-cache.md#u-edb7a2410116), [Curl_fopen](r15-file-protocol.md#u-c83e623c02f2)

**Uncertainties.**

- The file-write result is overwritten by later callback results only when result was OK; if save failed the callback loop still runs and its result replaces the returned error only if it errors—exact interplay on combined failures is not fully determined.

<a id="u-90df197d35e5"></a>
### `hsts_add`

`static CURLcode hsts_add(struct hsts *h, const char *line)` · [lib/hsts.c:L483-L504][f1]

Parses one cache-file line of the form host "YYYYMMDD HH:MM:SS" (optionally leading dot on host) into word, single-space, quoted-date, and newline parts; if all parts parse it delegates to hsts_add_host_expire with subdomain FALSE.

Any malformed line returns CURLE_OK without adding anything, so syntactic errors are ignored.

calls: [hsts_add_host_expire](r10-hsts-cache.md#u-749a43e5aed4)

<a id="u-749a43e5aed4"></a>
### `hsts_add_host_expire`

`static CURLcode hsts_add_host_expire(struct hsts *h, const char *host, size_t hostlen…` · [lib/hsts.c:L428-L480][f1]

Adds or updates one entry from a host plus date-string pair; only serious errors are returned.

Dates longer than MAX_HSTS_DATELEN are rejected with CURLE_BAD_FUNCTION_ARGUMENT; the date is null-terminated into a stack buffer, 'unlimited' maps to TIME_T_MAX, otherwise Curl_getdate_capped parses it. Expired entries (expiry <= now) are silently dropped with CURLE_OK. A leading dot on the host enables subdomains and is stripped; a trailing dot is stripped; an empty remaining host adds nothing. If no matching entry exists it is created; if the exact host already exists, the larger expiry wins and includeSubDomains is only ever turned on, never off.

calls: [hsts_check](r10-hsts-cache.md#u-97720bdcb018), [hsts_create](r10-hsts-cache.md#u-a73fa7ef3f8d), [Curl_getdate_capped](r10-parsedate.md#u-c19bb098429e)

**Uncertainties.**

- If Curl_getdate_capped fails to parse, expires stays 0 and the entry is dropped as expired; the return value of Curl_getdate_capped is not checked.

<a id="u-71723d865d86"></a>
### `hsts_append`

`static void hsts_append(struct hsts *h, struct stsentry *sts)` · [lib/hsts.c:L98-L108][f1]

Inserts an entry at the list tail, evicting the oldest entry first when the list already holds MAX_HSTS_ENTRIES items: the head node is removed and its stsentry freed before Curl_llist_append adds the new one.

calls: [Curl_llist_append](r9-linked-list.md#u-5e8651140cc1), [Curl_llist_count](r9-linked-list.md#u-d824c41827d3), [Curl_node_remove](r9-linked-list.md#u-e7f506f6b8c9)

**Uncertainties.**

- If the list were empty while count equals MAX_HSTS_ENTRIES, Curl_llist_head would be NULL; assumes MAX_HSTS_ENTRIES > 0.

<a id="u-97720bdcb018"></a>
### `hsts_check`

`stsentry *hsts_check(struct hsts *h, const char *hostname, size_t hlen, bool subdomain)` · [lib/hsts.c:L165-L208][f1]

Finds the HSTS entry matching a host, lazily pruning expired entries.

Returns NULL immediately if h is NULL or the host span is empty or longer than MAX_HSTS_HOSTLEN; strips a trailing dot. While walking the list it frees any entry whose expiry has passed. For live entries it tries subdomain matching only when the caller enables it, the entry has includeSubDomains, and the entry host is a strict dot-suffix of the input; the longest such tail is kept as bestsub. An exact length-and-content match (curl_strnequal over hlen, because hostname is not null-terminated) returns that entry immediately. Otherwise the longest subdomain match, or NULL, is returned.

**Notes.**

- side_effect: Expired entries encountered during the scan are removed and freed.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167), [Curl_node_remove](r9-linked-list.md#u-e7f506f6b8c9)

**Uncertainties.**

- An exact-match early return skips pruning of later entries.

<a id="u-a73fa7ef3f8d"></a>
### `hsts_create`

`static CURLcode hsts_create(struct hsts *h, const char *hostname, size_t hlen, bool s…` · [lib/hsts.c:L110-L133][f1]

Allocates and inserts one HSTS entry.

Asserts h and hostname, strips a trailing dot from the host span, and if bytes remain allocates a stsentry with a host tail of hlen bytes (terminator already zeroed), copies the host, stores expiry and includeSubDomains, and appends it. Returns CURLE_OUT_OF_MEMORY on allocation failure, otherwise CURLE_OK; an empty host after dot-strip silently adds nothing.

calls: [hsts_append](r10-hsts-cache.md#u-71723d865d86)

<a id="u-4a4f5335dff5"></a>
### `hsts_debugtime`

`static time_t hsts_debugtime(void *unused)` · [lib/hsts.c:L52-L63][f1]

Under DEBUGBUILD or UNITTESTS builds, substitutes time(): reads CURL_TIME from the environment; if set, parses it as a number up to TIME_T_MAX, adds the global deltatime adjustment, and returns that as time_t; otherwise returns real time(NULL).

The file redefines time(x) to call this and undefines it at end.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- deltatime is defined here but only set externally (test hook).

<a id="u-c11702ec500e"></a>
### `hsts_load`

`static CURLcode hsts_load(struct hsts *h, const char *file)` · [lib/hsts.c:L558-L597][f1]

Loads the text cache file line by line.

First replaces h->filename with a private strdup of file (out of memory returns CURLE_OUT_OF_MEMORY). Opens the file read-text; only when fstat succeeds and the path is not a directory does it iterate with Curl_get_line up to MAX_HSTS_LINE, skipping comment lines and lines of length <= 1 (blank), and parsing each remaining line with hsts_add, ignoring its per-line errors. Returns the first Curl_get_line error or CURLE_OK; unreadable files simply yield an empty result.

calls: [hsts_add](r10-hsts-cache.md#u-90df197d35e5), [Curl_get_line](r4-portable-utils.md#u-fc9d0cdbcdfa)

**Uncertainties.**

- A directory or unstatable file is skipped silently (CURLE_OK), matching the docstring that only major errors are returned.

<a id="u-614139678aaa"></a>
### `hsts_out`

`static void hsts_out(struct stsentry *sts, FILE *fp)` · [lib/hsts.c:L349-L364][f1]

Writes one entry as a file line: hosts with includeSubDomains are prefixed with a dot.

Entries with TIME_T_MAX expiry print 'unlimited'; others format the date via curlx_gmtime, and if gmtime fails the entry is silently skipped (no line written).

calls: [curlx_gmtime](r9-time-utils.md#u-18914244ccd6)

<a id="u-622ec8736771"></a>
### `hsts_pull`

`static CURLcode hsts_pull(struct Curl_easy *data, struct hsts *h)` · [lib/hsts.c:L510-L548][f1]

Loads HSTS entries from the user's hsts_read callback, if set.

Each round fills a stack-backed curl_hstsentry (empty name, empty expire) and calls the callback: CURLSTS_OK continues after validating the entry—if the name is empty or either null-terminator slot was overwritten it returns CURLE_BAD_FUNCTION_ARGUMENT; an empty expire is treated as 'unlimited', then hsts_add_host_expire is called and any error is propagated. CURLSTS_FAIL returns CURLE_ABORTED_BY_CALLBACK. Any other CURLSTScode ends the loop with CURLE_OK.

**Notes.**

- failure: Callback-supplied names longer than MAX_HSTS_HOSTLEN cannot fit and are caught by the terminator check.

calls: [hsts_add_host_expire](r10-hsts-cache.md#u-749a43e5aed4)

<a id="u-edb7a2410116"></a>
### `hsts_push`

`static CURLcode hsts_push(struct Curl_easy *data, struct curl_index *i, struct stsent…` · [lib/hsts.c:L315-L344][f1]

Sends one HSTS entry to the user's hsts_write callback.

Fills a curl_hstsentry with the host and subdomain flag; if the expiry equals TIME_T_MAX the expire string is 'unlimited', otherwise it is formatted from curlx_gmtime, and a gmtime failure is propagated. The callback result sets *stop to true unless CURLSTS_OK; CURLSTS_FAIL maps to CURLE_BAD_FUNCTION_ARGUMENT, other non-OK codes return CURLE_OK with stop set.

calls: [curlx_gmtime](r9-time-utils.md#u-18914244ccd6)

**Uncertainties.**

- Behavior for CURLSTScodes other than OK/FAIL is only 'stop', never an error.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/hsts.c
