# --libcurl Code Generation

**Capability.** Owns reproducing applied options as compilable C source: typed tool_setopt_* wrappers for long/enum/bitmask/offt/pointer/string/slist/mime/SSLVERSION options, NameValue lookup tables, C string escaping, and the recursive mime/slist generators.

Use this to understand --libcurl output. Each tool_setopt_* helper applies the option via curl_easy_setopt and, when code generation is active, emits a matching source line; libcurl_generate_mime recurses over mime parts.

**Depends on.**

- [Tool Operation Configuration](r1-tool-operation-config.md) · model-inferred · 0 edge(s)
- [Tool --libcurl source generation](r9-tool-easysrc.md) · graph-only · 39 edge(s)

**Depended on by.**

- [Tool Config to Easy Options](r13-tool-config-to-setopts.md) · graph-only · 213 edge(s)

Parent: [curl Command-Line Tool](r1-curl-tool.md)

## Units (15)

<a id="u-1ffc4858605d"></a>
### `c_escape`

`static char *c_escape(const char *str, curl_off_t len)` · [src/tool_setopt.c:L180-L234][f1]

c_escape converts a string into a C-escaped literal body, returning NULL on memory failure.

A zero-terminated length (-1) becomes strlen. Strings longer than 2000 characters are capped and a trailing '...' is appended. The loop splits the string at each character needing escape: ordinary printable characters not in the escape table are left inline; matched characters from tab, CR, LF, '?', '"', backslash become their two-character escape (the '?' escape prevents trigraphs); any other non-printable character is emitted as \%03o octal when the next byte is a hex digit (to avoid ambiguous hex escapes) or \x%02x otherwise. Accumulation uses a dynbuf capped at 4*2000+3 bytes; any dynbuf error aborts with NULL.

calls: [curlx_dyn_addf](r3-dynbuf.md#u-063790a51674)

**Uncertainties.**

- Behavior if the fully escaped output exceeds the dynbuf maximum is delegated to dynbuf error handling, which is outside this file.

<a id="u-1ee6d3cfa23e"></a>
### `libcurl_generate_mime`

`static CURLcode libcurl_generate_mime(CURL *curl, struct OperationConfig *config, str…` · [src/tool_setopt.c:L537-L565][f1]

Emits --libcurl code for a whole mime structure: it allocates a new mime number, emits the variable declaration, NULL initialization, curl_mime_init line, and cleanup lines curl_mime_free plus NULL reassignment, aborting at the first emit error.

If the mime has subparts and no error so far, it declares the corresponding part variable and recurses into libcurl_generate_mime_part for the subpart chain.

calls: [libcurl_generate_mime_part](r1-libcurl-codegen.md#u-dc9b2fa6da37), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-dc9b2fa6da37"></a>
### `libcurl_generate_mime_part`

`static CURLcode libcurl_generate_mime_part(CURL *curl, struct OperationConfig *config…` · [src/tool_setopt.c:L403-L534][f1]

Emits --libcurl code for one mime part, processing linked parts in reverse order via a recursive call on part->prev before emitting its own curl_mime_addpart line; it returns early on any error.

By part kind: TOOLMIME_PARTS recursively builds a sub-mime, emits curl_mime_subparts, and nulls the sub-mime variable so cleanup does not free it twice; TOOLMIME_DATA emits curl_mime_data with the escaped text; TOOLMIME_FILE and TOOLMIME_FILEDATA emit curl_mime_filedata, additionally emitting curl_mime_filename(part, NULL) for a FILEDATA part lacking a filename; TOOLMIME_STDIN defaults its filename to '-' and falls through, and TOOLMIME_STDINDATA emits a curl_mime_data_cb line wired to fread/fseek/stdin; other kinds emit nothing. After the switch it emits encoder, filename, name, and type lines when the corresponding fields are set, and finally generates a headers slist, emitting curl_mime_headers with takeover and nulling the slist variable. Each string is escaped, and escaping failure yields CURLE_OUT_OF_MEMORY.

calls: [libcurl_generate_mime](r1-libcurl-codegen.md#u-1ee6d3cfa23e), [libcurl_generate_slist](r1-libcurl-codegen.md#u-1fa0d1962c3a), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

**Uncertainties.**

- The FALLTHROUGH() macro's contract is not in this file; TOOLMIME_STDIN reaching TOOLMIME_STDINDATA code is inferred from control flow.

<a id="u-1fa0d1962c3a"></a>
### `libcurl_generate_slist`

`static CURLcode libcurl_generate_slist(struct curl_slist *slist, int *slistno)` · [src/tool_setopt.c:L366-L395][f1]

Generates --libcurl source for a curl_slist: it allocates a fresh slist number, emits a declaration, an initialization to NULL, and cleanup lines (curl_slist_free_all plus NULL reassignment).

If any of these emit steps fail it returns early. Then for each list node it C-escapes the data string, returning CURLE_OUT_OF_MEMORY immediately if escaping fails, and emits a curl_slist_append line; the last node's append uses the preceding variable so the chain reproduces the original order. The resulting error code is returned to the caller.

calls: [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-b8953deb0c04"></a>
### `tool_setopt_SSLVERSION`

`CURLcode tool_setopt_SSLVERSION(CURL *curl, const char *name, CURLoption tag, long lval)` · [src/tool_setopt.c:L275-L323][f1]

Sets CURLOPT_SSLVERSION-style options and reproduces them in --libcurl output by splitting the value into its low 16 bits (matched against setopt_nv_CURL_SSLVERSION) and the remaining high bits (matched against setopt_nv_CURL_SSLVERSION_MAX, whose NONE entry has an empty name).

If the base version has no table entry, the raw numeric value is emitted. If a max entry with a non-empty name matches, the emitted line ORs both names; otherwise only the base name is emitted. A zero value or setopt error suppresses code generation. Errors propagate; DEBUGBUILD additionally warns.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

**Uncertainties.**

- The MAX table is not scanned when the base name lookup fails, so an unlisted base always emits a plain numeric value even if max bits were set.

<a id="u-f8052c3df00a"></a>
### `tool_setopt_bitmask`

`CURLcode tool_setopt_bitmask(CURL *curl, const char *name, CURLoption tag, const stru…` · [src/tool_setopt.c:L326-L363][f1]

Sets an unsigned bitmask option and, for --libcurl with a nonzero value and successful setopt, decomposes it into ORed symbolic names.

It iterates the NameValueUnsigned list; whenever all bits of an entry are present in the remaining value, it emits 'name |' (or closes with ');' for the last chunk), clears those bits, and re-indents the preamble with spaces for continuation lines, stopping once all bits are handled or on error. Bits left over after the table produce a fallback line emitting the residual as an unsigned literal. Errors propagate.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-b3d07b185dbf"></a>
### `tool_setopt_enum`

`CURLcode tool_setopt_enum(CURL *curl, const char *name, CURLoption tag, const struct …` · [src/tool_setopt.c:L237-L272][f1]

Applies an enum-valued option via curl_easy_setopt and, when --libcurl is active and the value is nonzero and the setopt succeeded, records a source line reproducing the call.

It searches the supplied NameValue list for a matching value; if found it emits the symbolic name, otherwise it emits the raw numeric value (the fallback for values missing from the table). A zero value is skipped from code generation. Errors from curl_easy_setopt or easysrc_addf propagate; in DEBUGBUILD a warnf reports the error.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-87bb1e4c1fe4"></a>
### `tool_setopt_long`

`CURLcode tool_setopt_long(CURL *curl, const char *name, CURLoption tag, long lval)` · [src/tool_setopt.c:L609-L632][f1]

Sets a long option and, under --libcurl, emits a code line only when the value differs from the option's effective default.

The default is normally 0 but is looked up in the static setopt_nv_CURLNONZERODEFAULTS table by option name for options whose library default is nonzero (for example verification and nodelay flags). A DEBUGASSERT documents that the tag must be below CURLOPTTYPE_OBJECTPOINT. Errors from the library call or easysrc_addf propagate.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-8edc64b4072c"></a>
### `tool_setopt_long_force`

`CURLcode tool_setopt_long_force(CURL *curl, const char *name, CURLoption tag, long lval)` · [src/tool_setopt.c:L634-L642][f1]

Sets a long option and emits its code line more eagerly than tool_setopt_long: under --libcurl with a successful setopt, the line is emitted whenever it would not be the first generated statement (easysrc_is_first() false) or whenever the value is 0, ensuring later zero resets are not lost in the replay.

Errors propagate.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_is_first](r9-tool-easysrc.md#u-fce99ee7f1e9)

**Uncertainties.**

- Exact meaning of easysrc_is_first is defined in tool_easysrc.c, outside this file.

<a id="u-817baaaebddf"></a>
### `tool_setopt_mimepost`

`CURLcode tool_setopt_mimepost(CURL *curl, struct OperationConfig *config, const char …` · [src/tool_setopt.c:L568-L585][f1]

Applies CURLOPT_MIMEPOST via curl_easy_setopt and, only when that succeeds and --libcurl is active, generates the full mime structure source from config->mimeroot and emits the curl_easy_setopt line referencing the generated mime variable.

Errors from either the library call or the generation propagate to the caller.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [libcurl_generate_mime](r1-libcurl-codegen.md#u-1ee6d3cfa23e)

<a id="u-631743b60239"></a>
### `tool_setopt_offt`

`CURLcode tool_setopt_offt(CURL *curl, const char *name, CURLoption tag, curl_off_t lval)` · [src/tool_setopt.c:L645-L660][f1]

Sets a curl_off_t option; under --libcurl with a successful setopt and a nonzero value it emits a code line formatted with CURL_FORMAT_CURL_OFF_T.

Zero values are skipped from generation. A DEBUGASSERT restricts the tag range to CURLOPTTYPE_OFF_T..CURLOPTTYPE_BLOB, and errors propagate.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56)

<a id="u-f0fd295544bc"></a>
### `tool_setopt_ptr`

`CURLcode tool_setopt_ptr(CURL *curl, const char *name, CURLoption tag, ...)` · [src/tool_setopt.c:L663-L690][f1]

Sets an object or function pointer option taken from varargs.

DEBUGASSERTs document the expected tag ranges and that blob options are never set by the tool. It fetches one void * argument, calls curl_easy_setopt, and when --libcurl is active, the pointer is non-NULL and the setopt succeeded, it records a descriptive note in easysrc_toohard instead of generating real code, choosing 'object' or 'function' wording from the tag range (with the indefinite article adjusted). Errors propagate.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [easysrc_addf](r9-tool-easysrc.md#u-9e77edaffbe4)

<a id="u-c03e71944283"></a>
### `tool_setopt_slist`

`CURLcode tool_setopt_slist(CURL *curl, const char *name, CURLoption tag, struct curl_…` · [src/tool_setopt.c:L588-L606][f1]

Sets an slist-valued option via curl_easy_setopt; when --libcurl is active, the list is non-NULL, and the setopt succeeded, it generates the slist source and emits the curl_easy_setopt line referencing the generated slist variable.

A NULL list still reaches the library call but produces no generated code.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [libcurl_generate_slist](r1-libcurl-codegen.md#u-1fa0d1962c3a)

<a id="u-32fbd1f9673f"></a>
### `tool_setopt_str`

`CURLcode tool_setopt_str(CURL *curl, struct OperationConfig *config, const char *name…` · [src/tool_setopt.c:L693-L722][f1]

Sets a string option; under --libcurl with a non-NULL value and successful setopt, it C-escapes the string and emits the curl_easy_setopt line with the escaped literal.

For CURLOPT_POSTFIELDS the length passed to c_escape is the actual postdata dynbuf length rather than zero-terminated, so the generated literal matches the data sent even if it contains embedded content boundaries. Escaping failure (out of memory) becomes CURLE_OUT_OF_MEMORY. DEBUGASSERTs restrict the tag to object-pointers below the function-point range.

calls: [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56), [c_escape](r1-libcurl-codegen.md#u-1ffc4858605d)

**Uncertainties.**

- Whether a postdata length shorter than the string accurately reflects transmitted bytes depends on how config->postdata is filled elsewhere.

<a id="u-80c3ac86d782"></a>
### `tool_setopt.c module code (L1–L179)`

`module_region` · [src/tool_setopt.c:L1-L179][f1]

File header, includes, and the NameValue lookup tables used to map setopt values back to symbolic names for --libcurl output.

Combination values precede single bits in bitmask tables and NONE entries come last; setopt_nv_CURL_SSLVERSION_MAX has an empty-name entry for CURL_SSLVERSION_MAX_NONE, and the static setopt_nv_CURLNONZERODEFAULTS lists long options whose library default is 1 (or a nonzero flag), consulted by tool_setopt_long. NVEND entries terminate each table.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_setopt.c
