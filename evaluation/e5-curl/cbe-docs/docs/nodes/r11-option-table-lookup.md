# option table lookup

**Capability.** Resolving option names and single letters to their table entries: tool long/short lookup via binary search, and libcurl easy-option lookup by name, id, and iteration.

findlongopt/findshortopt serve the tool's getparameter; the easygetopt units expose curl_easy_option_by_name/by_id/next over the static easy-opts table, all backed by one runtime search. Use these when mapping user-facing names to option descriptors.

**Depended on by.**

- [flag dispatch and simple assignment](r11-arg-dispatch.md) · graph-confirmed · 3 edge(s)

Parent: [command-line option processing](r11-cli-options.md)

## Units (7)

<a id="u-a9fb8ac977e2"></a>
### `easygetopt-c-lookup`

`static const struct curl_easyoption *lookup(const char *name, CURLoption id)` · [lib/easygetopt.c:L31-L51][f1]

Searches the static Curl_easyopts table at runtime for an easy setopt option by case-insensitive name or by option id, returning the matching entry or NULL.

If both name and id are NULL (when asserts are disabled), it returns NULL without scanning. With a name, it compares each entry's name with curl_strequal, which is case-insensitive, and returns the first match, including alias entries. With only an id, it returns the first entry whose id matches and whose CURLOT_FLAG_ALIAS flag is clear, so aliases never satisfy id lookups. Iteration is a do/while starting at Curl_easyopts[0] and advancing while o->name is non-NULL, so the terminating { NULL, CURLOPT_LASTENTRY, ... } sentinel entry stops the scan. DEBUGASSERT invocations (asserting an argument is present and Curl_easyopts_check() is zero) are active only in debug builds, where a table out of sync with curl/curl.h aborts the build; in release builds they are no-ops. On no match it returns NULL.

**Notes.**

- contract: Curl_easyopts_check() being zero is a debug-build invariant verifying the generated table matches curl/curl.h; a nonzero result trips the assert.

calls: [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167), [Curl_easyopts_check](r7-public-api-contracts.md#u-5075f40c6484); uses: [easyoptions-c-table](r7-public-api-contracts.md#u-23e79766a9b0)

**Uncertainties.**

- Whether DEBUGASSERT aborts or merely logs depends on the curl_setup.h assert definition, not shown here.
- curl_strequal's exact semantics are taken from its name and this call site; its implementation is outside the supplied source.

<a id="u-58b4428ecd2c"></a>
### `easygetopt-c-curl-easy-option-by-name`

`const struct curl_easyoption *curl_easy_option_by_name(const char *name)` · [lib/easygetopt.c:L53-L57][f1]

Public name-based lookup of a curl_easyoption entry, provided by two conditional variants.

In the normal build (CURL_DISABLE_GETOPTIONS undefined) it delegates to lookup(name, CURLOPT_LASTENTRY); lookup then ignores the id argument entirely and matches by case-insensitive name, including CURLOT_FLAG_ALIAS entries such as ENCODING, so an alias name resolves to its entry. When getoptions support is disabled, the stub ignores its argument and always returns NULL. No allocation or mutation occurs; the returned pointer points into the static Curl_easyopts table.

calls: [easygetopt-c-lookup](r11-option-table-lookup.md#u-a9fb8ac977e2)

**Uncertainties.**

- NULL name input is only guarded by lookup's DEBUGASSERT; behavior with a NULL name in release builds depends on curl_strequal(NULL, NULL) handling not shown here.

<a id="u-f54eba44690a"></a>
### `easygetopt-c-curl-easy-option-by-id`

`const struct curl_easyoption *curl_easy_option_by_id(CURLoption id)` · [lib/easygetopt.c:L59-L62][f1]

Public id-based lookup of a curl_easyoption entry, in two conditional variants.

In the normal build it calls lookup(NULL, id); because name is NULL, lookup matches entries by numeric id and skips entries carrying CURLOT_FLAG_ALIAS, so only the canonical entry for an id is returned even when aliases share it. If no non-alias entry has that id, or the sentinel is reached, the result is NULL. In the CURL_DISABLE_GETOPTIONS build the stub ignores its argument and returns NULL.

calls: [easygetopt-c-lookup](r11-option-table-lookup.md#u-a9fb8ac977e2)

<a id="u-e0f756bf4eb5"></a>
### `easygetopt-c-curl-easy-option-next`

`const struct curl_easyoption *curl_easy_option_next( const struct curl_easyoption *prev)` · [lib/easygetopt.c:L65-L76][f1]

Iterates over the Curl_easyopts table in its stored (alphabetical) order, in two conditional variants.

In the normal build: passing NULL returns a pointer to the first entry, &Curl_easyopts[0], starting iteration. Passing a valid previous entry returns the immediately following entry, since the table is a dense array terminated by the { NULL, CURLOPT_LASTENTRY, ... } sentinel. Passing a pointer whose ->name is NULL (the sentinel, or an end-of-table result) returns NULL, ending iteration, so callers loop while curl_easy_option_next(prev) is non-NULL. In the CURL_DISABLE_GETOPTIONS build the stub ignores its argument and always returns NULL.

**Uncertainties.**

- A prev pointer that points outside the Curl_easyopts array is never validated; behavior in that case is undefined and cannot be established from this source.

<a id="u-ec9cb6546467"></a>
### `findarg`

`static int findarg(const void *a, const void *b)` · [src/tool_getparam.c:L831-L836][f2]

strcmp comparison callback over LongShort lname fields, used by bsearch in findlongopt.

<a id="u-fe1c2a85b62d"></a>
### `findlongopt`

`const struct LongShort *findlongopt(const char *opt)` · [src/tool_getparam.c:L1083-L1090][f2]

Binary-searches the alphasorted aliases table for a long-option name using findarg as the comparator, returning the matching LongShort entry or NULL.

calls: [findarg](r11-option-table-lookup.md#u-ec9cb6546467)

<a id="u-6c947bb2d16d"></a>
### `findshortopt`

`const struct LongShort *findshortopt(char letter)` · [src/tool_getparam.c:L838-L856][f2]

Resolves a single-letter option to its LongShort entry.

Letters <= ' ' or >= 127 return NULL. On first use a static table indexed by letter is populated from the aliases array (a later duplicate letter overwrites the earlier) and marked done, so subsequent calls are a direct lookup.

**Uncertainties.**

- Which alias wins for a duplicated short letter depends on the full aliases order.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/easygetopt.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_getparam.c
