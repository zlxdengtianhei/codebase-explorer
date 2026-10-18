# Alt-Svc cache

**Capability.** Parsing, storing, looking up, flushing and persisting HTTP Alternative Services: cache lifecycle with default protocol flags, header-line parsing, origin matching, entry eviction and file load/save.

Curl_altsvc_parse ingests Alt-Svc headers best-effort into the cache; Curl_altsvc_lookup finds alternatives via hostcompare; save/load serialize to the line format parsed by altsvc_add. ctrl/init/cleanup manage cache ownership and flags; debugtime supports reproducible expiry in tests.

**Depends on.**

- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 51 edge(s) · Alt-Svc header and cache-file parsing uses the cursor-based word/number scanning primitives.

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (20)

<a id="u-df37eb31c241"></a>
### `Curl_alpnid2str`

`const char *Curl_alpnid2str(enum alpnid id)` · [lib/altsvc.c:L67-L79][f1]

Maps an ALPN id enum to its name string: h1, h2, or the h3 version constant; any other id returns an empty string, which callers treat as a bad id.

<a id="u-43c129e1b31a"></a>
### `Curl_str2alpnid`

`static enum alpnid Curl_str2alpnid(const struct Curl_str *cstr)` · [lib/altsvc.c:L81-L85][f1]

Converts a parsed string token to an ALPN id by forwarding the token bytes and length to Curl_alpn2alpnid.

calls: [Curl_alpn2alpnid](r6-connection-management.md#u-1f4c563864bf)

<a id="u-8a149f12e568"></a>
### `altsvc_debugtime`

`static time_t altsvc_debugtime(void *unused)` · [lib/altsvc.c:L51-L61][f1]

Debug/unittest time() replacement: reads CURL_TIME from the environment and, when set, returns that value parsed as a capped number; otherwise returns the current time.

Active only in DEBUGBUILD or UNITTESTS builds, where the file #undefs time and redefines time(x) to this function, restoring the macro at file end.

**Notes.**

- side_effect: The time(x) macro redefinition changes every time(NULL) call in this file during debug builds, enabling deterministic expiry tests.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-612717d161e1"></a>
### `altsvc_createid`

`static struct altsvc *altsvc_createid(const char *srchost, size_t hlen, const char *d…` · [lib/altsvc.c:L89-L134][f1]

Allocates one alt-svc record with both host strings inline in the same allocation, after normalization: a source host starting with '[' loses its brackets (length minus 2), a source host ending in '.' loses the dot, and a destination host starting with '[' loses its brackets.

If either host becomes empty, NULL is returned. The calloc covers the struct plus (hlen+1) and (dlen+1) bytes; hosts are copied and already null-terminated by the zeroed allocation, then ALPN ids are stored and ports truncated to unsigned short. Returns NULL on allocation failure.

**Notes.**

- condition: Only the source host gets trailing-dot stripping; the destination keeps any trailing dot.

<a id="u-ec8957de1c44"></a>
### `altsvc_create`

`static struct altsvc *altsvc_create(struct Curl_str *srchost, struct Curl_str *dsthos…` · [lib/altsvc.c:L136-L151][f1]

Builds an alt-svc record from parsed string tokens: resolves both ALPN name tokens via Curl_str2alpnid and returns NULL if either is unknown (zero), otherwise delegates to altsvc_createid with the host bytes and lengths.

calls: [Curl_str2alpnid](r11-alt-svc-cache.md#u-43c129e1b31a), [altsvc_createid](r11-alt-svc-cache.md#u-612717d161e1)

<a id="u-f54d0b1a09b7"></a>
### `altsvc_append`

`static void altsvc_append(struct altsvcinfo *asi, struct altsvc *as)` · [lib/altsvc.c:L155-L165][f1]

Appends an entry to the cache list tail, evicting the oldest (head) entries, freeing each via altsvc_free, while the list holds MAX_ALTSVC_ENTRIES or more.

calls: [Curl_llist_append](r9-linked-list.md#u-5e8651140cc1)

<a id="u-b09fcedc4d26"></a>
### `altsvc_add`

`static CURLcode altsvc_add(struct altsvcinfo *asi, const char *line)` · [lib/altsvc.c:L168-L227][f1]

Parses one cache-file line shaped like 'srcalpn srchost srcport dstalpn dsthost dstport "date" persist prio' using strictly ordered curlx_str steps bounded by the MAX_ALTSVC_* limits; if any step fails the line is silently dropped and CURLE_OK is returned.

On a successful parse, the quoted date is copied into a null-terminated buffer, the expiry comes from Curl_getdate_capped, and the entry is created and appended only when now is earlier than the expiry; stale lines are discarded silently. The only propagated error is CURLE_OUT_OF_MEMORY when entry creation fails.

**Notes.**

- contract: The trailing prio is parsed with max 0, so any nonzero prio invalidates the whole line and the entry is ignored.

calls: [Curl_getdate_capped](r10-parsedate.md#u-c19bb098429e), [altsvc_create](r11-alt-svc-cache.md#u-ec8957de1c44), [altsvc_append](r11-alt-svc-cache.md#u-f54d0b1a09b7)

<a id="u-4d65e4835c2f"></a>
### `altsvc_load`

`static CURLcode altsvc_load(struct altsvcinfo *asi, const char *file)` · [lib/altsvc.c:L237-L270][f1]

Stores a private strdup copy of the cache filename (returning CURLE_OUT_OF_MEMORY if allocation fails), then opens the file read-text.

When open succeeds and fstat does not fail and the file is not a directory, lines are read via Curl_get_line into a dynbuf capped at MAX_ALTSVC_LINE; blank lines and '#' comment lines are skipped and each remaining line is passed to altsvc_add, which ignores per-line syntax errors. The dynbuf is freed after the loop, the file is closed, and the last Curl_get_line result is returned, so only read-level failures propagate.

calls: [Curl_get_line](r4-portable-utils.md#u-fc9d0cdbcdfa), [altsvc_add](r11-alt-svc-cache.md#u-b09fcedc4d26)

<a id="u-1e16b0874240"></a>
### `altsvc_out`

`static CURLcode altsvc_out(struct altsvc *as, FILE *fp)` · [lib/altsvc.c:L275-L316][f1]

Serializes one alt-svc record as a cache-file line: converts the expiry via curlx_gmtime and returns its CURLcode on failure; under USE_IPV6, src/dst hosts parsing as IPv6 are wrapped in brackets; then fprintf writes both alpn/host/port pairs, the quoted date components, the persist flag, and a constant priority 0.

calls: [Curl_alpnid2str](r11-alt-svc-cache.md#u-df37eb31c241), [curlx_gmtime](r9-time-utils.md#u-18914244ccd6)

<a id="u-49ff500998f4"></a>
### `Curl_altsvc_init`

`struct altsvcinfo *Curl_altsvc_init(void)` · [lib/altsvc.c:L324-L341][f1]

Allocates an empty altsvcinfo cache, initializes its linked list, and sets default protocol flags: CURLALTSVC_H1 always, plus the H2 bit under USE_HTTP2 and the H3 bit under USE_HTTP3.

Returns NULL on allocation failure.

calls: [Curl_llist_init](r9-linked-list.md#u-a99250aef25e)

<a id="u-a466d0e058ea"></a>
### `Curl_altsvc_ctrl`

`CURLcode Curl_altsvc_ctrl(struct Curl_easy *data, const long ctrl)` · [lib/altsvc.c:L355-L368][f1]

Applies the user's alt-svc bitmask: a zero ctrl value returns CURLE_BAD_FUNCTION_ARGUMENT.

If the easy handle has no cache, one is created via Curl_altsvc_init, with allocation failure returning CURLE_OUT_OF_MEMORY; then the cache flags are overwritten with ctrl and CURLE_OK is returned.

calls: [Curl_altsvc_init](r11-alt-svc-cache.md#u-49ff500998f4)

<a id="u-6c9d17b7c86c"></a>
### `Curl_altsvc_load`

`CURLcode Curl_altsvc_load(struct altsvcinfo *asi, const char *file)` · [lib/altsvc.c:L346-L350][f1]

Public wrapper asserting a non-null cache and forwarding to altsvc_load for the given file.

calls: [altsvc_load](r11-alt-svc-cache.md#u-4d65e4835c2f)

<a id="u-96bb3528612e"></a>
### `Curl_altsvc_cleanup`

`void Curl_altsvc_cleanup(struct altsvcinfo **asi)` · [lib/altsvc.c:L374-L389][f1]

Frees the whole cache when *asi is non-null: walks the entry list freeing each altsvc, frees the stored filename and the cache struct, and sets the caller's pointer to NULL; no-op otherwise.

calls: [Curl_llist_head](r9-linked-list.md#u-21d32d21e74e)

<a id="u-af7f3b50871e"></a>
### `Curl_altsvc_save`

`CURLcode Curl_altsvc_save(struct Curl_easy *data, struct altsvcinfo *asi, const char …` · [lib/altsvc.c:L394-L436][f1]

Writes the cache to a file, returning CURLE_OK without writing when the cache is NULL, when no filename exists (otherwise falling back to the filename stored at load time), when flags include CURLALTSVC_READONLYFILE, or when the name is empty.

Otherwise opens the target via Curl_fopen, writes two comment header lines, then serializes each list entry with altsvc_out, stopping on the first error and closing the file. If writing succeeded and a tempstore name exists, the temp file is renamed onto the target, a rename failure producing CURLE_WRITE_ERROR; on any error the temp file is unlinked and tempstore freed either way.

calls: [Curl_fopen](r15-file-protocol.md#u-c83e623c02f2), [altsvc_out](r11-alt-svc-cache.md#u-1e16b0874240)

<a id="u-19fd71ad8e9e"></a>
### `hostcompare`

`static bool hostcompare(const char *host, const char *check)` · [lib/altsvc.c:L441-L452][f1]

Case-insensitive host match: a trailing dot on the first host is ignored, lengths must then be equal, and the comparison itself uses curl_strnequal over the host length.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-c896a15f39c6"></a>
### `altsvc_flush`

`static void altsvc_flush(struct altsvcinfo *asi, struct Curl_peer *origin, enum alpni…` · [lib/altsvc.c:L456-L472][f1]

Removes and frees every cache entry whose source ALPN id, port, and host (via hostcompare) match the given origin, iterating safely over the linked list while removing nodes.

calls: [hostcompare](r11-alt-svc-cache.md#u-19fd71ad8e9e)

<a id="u-0f3b65ea1010"></a>
### `altsvc_parse_params`

`static void altsvc_parse_params(const char **pp, time_t *pmaxage, bool *ppersist)` · [lib/altsvc.c:L476-L529][f1]

Parses ';name=value' parameter chains after an alt-svc destination.

If the next character is not ';' it returns immediately. In each iteration a name up to '=' and its value (quoted word, or run up to ',;\r\n') are extracted with whitespace trimmed; names 'ma' and 'persist' (case-insensitive) are recognized, and only when the value is entirely a number within TIME_T_MAX is it applied: 'ma' sets *pmaxage, 'persist' with value 1 sets *ppersist. Any parse failure breaks out of further parameters without error; the loop ends when no ';' follows a parameter.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-c7b1a704e491"></a>
### `altsvc_parse_dest`

`static bool altsvc_parse_dest(const char **pp, struct Curl_easy *data, struct Curl_pe…` · [lib/altsvc.c:L531-L573][f1]

Parses the quoted 'hostname:port' destination of an alt-svc entry, updating *pdstport and *dsthost on success.

After the opening quote: if the content does not start with ':', it is a host — a '[' immediately after means an IPv6 literal parsed up to ']' (bounded by MAX_IPADR_LEN, failure logs a bad-IPv6 infof and returns FALSE), otherwise a DNS/IPv4 name up to ':' (bounded by MAX_ALTSVC_HOSTLEN; failure logs a bad-hostname infof and returns FALSE); a missing ':' after the host also returns FALSE. If the content starts with ':', the destination host is taken from the origin's hostname. The port is then parsed (max 0xffff), with a parse failure logging an infof and returning FALSE; finally the closing quote is required or FALSE is returned.

calls: [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

<a id="u-e85ef1329f6c"></a>
### `Curl_altsvc_parse`

`CURLcode Curl_altsvc_parse(struct Curl_easy *data, struct altsvcinfo *asi, const char…` · [lib/altsvc.c:L586-L675][f1]

Parses an incoming Alt-Svc header value into the cache, best-effort: invalid entries are rejected locally and never produce an error return.

A value whose first token (up to ';', newline, or CR) trims to 'clear' flushes all cached alternatives for the source origin and returns CURLE_OK. Otherwise each entry is 'alpn="host:port";params': the ALPN token is read up to '=', the destination via altsvc_parse_dest (stopping the loop on failure), and parameters via altsvc_parse_params with maxage defaulting to 24 hours. For a known destination ALPN id, the first entry of the line first flushes old alternatives for the origin; an entry is then created from the origin as source, expires computed as now + maxage capped at TIME_T_MAX, persist set from params, appended, and logged via infof. Entry-creation failure returns CURLE_OUT_OF_MEMORY — the only error this function propagates. A following ',' continues to the next entry; anything else ends parsing with CURLE_OK.

calls: [altsvc_flush](r11-alt-svc-cache.md#u-c896a15f39c6), [altsvc_parse_dest](r11-alt-svc-cache.md#u-c7b1a704e491), [altsvc_parse_params](r11-alt-svc-cache.md#u-0f3b65ea1010), [altsvc_createid](r11-alt-svc-cache.md#u-612717d161e1), [altsvc_append](r11-alt-svc-cache.md#u-f54d0b1a09b7)

<a id="u-3e76f794185f"></a>
### `Curl_altsvc_lookup`

`bool Curl_altsvc_lookup(struct altsvcinfo *asi, struct Curl_peer *origin, enum alpnid…` · [lib/altsvc.c:L680-L720][f1]

Finds a usable alternative for an origin.

If the cache is empty it returns FALSE immediately. Walking the list, expired entries (expires < now) are removed and freed as encountered. A match requires equal source ALPN id, the destination ALPN id present in the versions bitmask, equal source port, and a source-host match via hostcompare; on match the entry is written to *dstentry, *psame_destination is set when the destination equals the origin's host and port, and TRUE is returned. No match yields FALSE with *psame_destination FALSE either way.

calls: [hostcompare](r11-alt-svc-cache.md#u-19fd71ad8e9e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/altsvc.c
