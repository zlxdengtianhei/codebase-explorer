# Tool parameter helpers

**Capability.** Parses and validates curl command-line parameter values: numeric and seconds parsers, keyword-to-enum selectors, protocol list/sets handling, password prompting, file-to-memory reading, slist helpers, and per-operation argument fixups.

Use this subtree for how option strings become typed config values. Protocol parsing builds sorted comma-joined strings over interned protocol sets; comparisons use the caseless-string utilities.

**Depends on.**

- [Case-insensitive strings](r9-caseless-strings.md) · graph-confirmed · 10 edge(s)
- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 3 edge(s)

Parent: [curl codebase](r9-curl-source.md)

## Units (15)

<a id="u-9c237590e8c4"></a>
### `tool-paramhlp-enum-selectors`

`long ftpfilemethod(const char *str)` · [src/tool_paramhlp.c:L612-L624][f1]

Keyword-to-enum selectors used for FTP and GSS options, each comparing case-insensitively with curl_strequal and warning on no match.

ftpfilemethod maps 'singlecwd', 'nocwd', 'multicwd' to their CURLFTPMETHOD_* values, otherwise warns 'unrecognized ftp file method' and defaults to CURLFTPMETHOD_MULTICWD. ftpcccmethod maps 'passive'/'active' to CURLFTPSSL_CCC_PASSIVE/ACTIVE, otherwise warns and defaults to PASSIVE. delegation maps 'none', 'policy', 'always' to the CURLGSSAPI_DELEGATION_* values, otherwise warns and defaults to NONE.

<a id="u-60bd880c7bef"></a>
### `tool-paramhlp-file2memory-range`

`ParameterError file2memory_range(char **bufp, size_t *size, FILE *file, curl_off_t st…` · [src/tool_paramhlp.c:L119-L190][f1]

Reads a byte range [starto, endo] from a stream into a dynbuf and reports pointer and length.

For seekable files (anything but stdin) starto positions via curlx_fseek, failing with PARAM_READ_ERROR; for stdin the first starto bytes are read and discarded incrementally. Data is read in 4096-byte chunks until feof. A read error frees the dynbuf, zeroes *size and *bufp and returns PARAM_READ_ERROR; an append failure returns PARAM_NO_MEM without a visible free. When accumulated offset plus pending bytes would pass endo, n_add is clamped so the copy ends exactly at endo. A NULL file yields *size 0 and *bufp NULL, and returns PARAM_OK. The wrapper file2memory reads the whole stream by delegating with starto 0 and endo CURL_OFF_T_MAX.

calls: [tool-paramhlp-file2memory-range](r9-tool-paramhlp.md#u-60bd880c7bef)

**Uncertainties.**

- Dynbuf cleanup on the PARAM_NO_MEM path depends on dynbuf internals not shown.

<a id="u-21b0edbd27a7"></a>
### `tool-paramhlp-numeric-parsers`

`ParameterError str2num(long *val, const char *str)` · [src/tool_paramhlp.c:L205-L220][f1]

Numeric command-line argument parsers built on curlx_str_number/curlx_str_octal plus a terminating curlx_str_single check; each returns a ParameterError and never writes *val on failure.

str2num parses an optionally '-'-signed decimal long (failure: PARAM_BAD_NUMERIC) and negates on sign. str2unum wraps str2num and returns PARAM_NEGATIVE_NUMERIC for negative results. str2unummax further returns PARAM_NUMBER_TOO_LARGE when the value exceeds max. oct2nummax parses octal up to max, mapping STRE_OVERFLOW to PARAM_NUMBER_TOO_LARGE, other octal errors and trailing garbage to PARAM_BAD_NUMERIC, and negative results to PARAM_NEGATIVE_NUMERIC. str2offset parses a non-negative curl_off_t offset up to CURL_OFF_T_MAX, failing with PARAM_BAD_NUMERIC on parse error or trailing characters.

**Uncertainties.**

- NULL-string behavior beyond DEBUGASSERT depends on the curlx_str_* helpers, which are not in this batch.

<a id="u-1532207f43d4"></a>
### `tool-paramhlp-proto2num`

`ParameterError proto2num(const char * const *val, char **ostr, const char *str)` · [src/tool_paramhlp.c:L394-L419][f1]

Parses a comma-separated protocol list into an allocated, comma-joined, alphabetically sorted protocol string stored in *ostr, seeded from the default protocols in val.

If proto_count exceeds MAX_PROTOS (34) it returns PARAM_NO_MEM immediately. Empty tokens (str == next) are skipped. Each token may carry a leading modifier: '=' sets the set to that token, '-' denies it, '+' (or none) allows it. The token 'all' with deny empties the set; with allow or set it copies built_in_protos. Otherwise the token is interned via proto_token: unknown protocols report 'unrecognized protocol' via errorf and return PARAM_BAD_USE, and for a set action the set is emptied first as if nothing is allowed. Known tokens are added/cleared in the set via protoset_set/protoset_clear; a set action clears the set before adding. Finally the set is sorted with struplocompare4sort, joined with commas via curlx_dyn_addf (failure: PARAM_NO_MEM); an empty result frees the buffer and returns PARAM_BAD_USE, otherwise *ostr is replaced with the new allocation after freeing the old. The local e_action enum defines the allow/deny/set action values used by this switch.

calls: [tool-paramhlp-protoset](r9-tool-paramhlp.md#u-0408a4230b0a); uses: [tool_libinfo.h module code (L1–L69)][f2]

**Uncertainties.**

- Behavior when the output string would exceed MAX_PROTOSTRING (dynbuf cap) is PARAM_NO_MEM by construction but the truncation path relies on dynbuf semantics not shown.

<a id="u-0408a4230b0a"></a>
### `tool-paramhlp-protoset`

`static size_t protoset_index(const char * const *protoset, const char *proto)` · [src/tool_paramhlp.c:L338-L348][f1]

Protocol sets implemented as NUL-terminated arrays of interned protocol-name pointers whose slots are indexed by position in the built-in protocol table.

protoset_index returns the slot holding proto, or the member count when proto is NULL; it debug-asserts pointer identity with proto_token, so matching is by token, not string. protoset_set adds a token only if absent, asserting the set never exceeds proto_count. protoset_clear removes a token by swapping the last member into its slot and nulling that slot, so member order is not stable across removals. All three ignore a NULL proto.

uses: [tool_libinfo.h module code (L1–L69)][f2]

<a id="u-156887e3e0ca"></a>
### `tool-paramhlp-str2tls-max`

`ParameterError str2tls_max(unsigned char *val, const char *str)` · [src/tool_paramhlp.c:L710-L712][f1]

Maps a --tls-max version string to a library enum value via a static table pairing 'default' with 0 and '1.0'..'1.3' with 1..4.

A NULL string returns PARAM_REQUIRES_PARAMETER; a table hit stores the value in *val and returns PARAM_OK; any other string returns PARAM_BAD_USE after scanning the whole table. The nested s_tls_max struct defines the table row layout.

<a id="u-e7021dd163e9"></a>
### `add2list`

`ParameterError add2list(struct curl_slist **list, const char *ptr)` · [src/tool_paramhlp.c:L601-L610][f1]

Appends ptr to a curl_slist via curl_slist_append; on success *list is updated to the new head and PARAM_OK returned, on allocation failure PARAM_NO_MEM is returned and *list is unchanged.

uses: [get_args](r9-tool-paramhlp.md#u-6d8cb922f66b)

<a id="u-68525b067b9d"></a>
### `check_protocol`

`ParameterError check_protocol(const char *str)` · [src/tool_paramhlp.c:L521-L529][f1]

Checks whether a protocol name is supported by libcurl.

A NULL string returns PARAM_REQUIRES_PARAMETER; otherwise proto_token resolves the name and PARAM_OK or PARAM_LIBCURL_UNSUPPORTED_PROTOCOL is returned.

uses: [tool_libinfo.h module code (L1–L69)][f2]

<a id="u-af7a3454243a"></a>
### `checkpasswd`

`static CURLcode checkpasswd(const char *kind, /* for what purpose */ const size_t i, …` · [src/tool_paramhlp.c:L548-L599][f1]

Prompts interactively for a missing password and rewrites a user[:password][;options] string in place.

It returns CURLE_OK immediately when *userpwd is empty. If a ':' separator exists or the string starts with ';', no prompt occurs and the string is left as-is. Otherwise, any ';options' suffix is temporarily terminated, a prompt is built naming the kind and user — with a plain form for the first operation when it is the last (i==0 && last) and a 'URL #<i+1>' form otherwise — the password is read with getpass_r into a 2048-byte buffer, the ';' is restored, and a new 'user:password' string is formatted into a dynbuf capped at MAX_USERPWDLENGTH. dynbuf formatting failure returns CURLE_OUT_OF_MEMORY leaving *userpwd as the unprefixed user string; success frees the old string and installs the dynbuf pointer.

calls: [tool_getpass.h module code (L1–L38)][f3]

**Uncertainties.**

- getpass_r failure semantics (NULL return aborting the operation per its header) are not handled visibly in this function.

<a id="u-0f6d92519149"></a>
### `file2string`

`ParameterError file2string(char **bufp, FILE *file)` · [src/tool_paramhlp.c:L85-L117][f1]

Reads a whole file into a dynbuf of capacity MAX_FILE2STRING, skipping CR, LF and NUL bytes, and returns the buffer through bufp.

Reading proceeds in 4096-byte chunks until feof; each chunk is split by memcrlf into non-delimiter runs to append and delimiter runs to skip. A read error frees the dynbuf, sets *bufp to NULL and returns PARAM_READ_ERROR; a dynbuf append failure returns PARAM_NO_MEM on that path without a visible curlx_dyn_free call. A NULL file yields the empty dynbuf contents. Returns PARAM_OK otherwise.

calls: [memcrlf](r9-tool-paramhlp.md#u-c12d978660fa)

**Uncertainties.**

- Whether the dynbuf is reclaimed on the PARAM_NO_MEM path depends on dynbuf semantics not shown here.

<a id="u-6d8cb922f66b"></a>
### `get_args`

`CURLcode get_args(struct OperationConfig *config, const size_t i)` · [src/tool_paramhlp.c:L673-L699][f1]

Applies per-operation argument fixups before transfer i.

When config->jsoned, it adds 'Content-Type: application/json' and 'Accept: application/json' headers unless already present (inlist check); an add2list failure aborts with CURLE_OUT_OF_MEMORY. Then, if userpwd is set and oauth_bearer is not, it prompts for a missing host password via checkpasswd; if that succeeded and proxyuserpwd is set, it does the same for the proxy credentials. Returns the resulting CURLcode. The 'last' flag passed to checkpasswd is true only when config->next is NULL.

calls: [add2list](r9-tool-paramhlp.md#u-e7021dd163e9), [checkpasswd](r9-tool-paramhlp.md#u-af7a3454243a), [inlist](r9-tool-paramhlp.md#u-db6998dfe1a5)

<a id="u-db6998dfe1a5"></a>
### `inlist`

`static bool inlist(const struct curl_slist *head, const char *checkfor)` · [src/tool_paramhlp.c:L658-L671][f1]

Returns TRUE if the header list contains an entry whose first thislen bytes match checkfor case-insensitively (curl_strnequal) and whose byte at that position is a header separator ':' or ';'; otherwise FALSE.

checkfor must be non-empty and not end in ':' (debug-asserted).

<a id="u-c12d978660fa"></a>
### `memcrlf`

`static size_t memcrlf(char *orig, bool countcrlf, /* TRUE if we count CRLF, FALSE if …` · [src/tool_paramhlp.c:L68-L81][f1]

Scans up to max bytes from orig, treating CR, LF and NUL as delimiters per ISCRLF.

With countcrlf FALSE it returns the count of leading non-delimiter bytes; with countcrlf TRUE it returns the count of leading delimiter bytes. If the whole region is homogeneous it returns max.

**Notes.**

- contract: NUL counts as a delimiter, so embedded NULs end the non-CRLF scan.

<a id="u-89c718db735e"></a>
### `new_getout`

`struct getout *new_getout(struct OperationConfig *config)` · [src/tool_paramhlp.c:L35-L55][f1]

Allocates a getout node and appends it to the operation config's URL list.

On allocation success it links the node after config->url_last (or becomes config->url_list when the list is empty), moves url_last, copies config->remote_name_all into node->useremote, and stores a monotonically increasing static counter in node->num. On allocation failure it returns NULL and leaves the list untouched.

**Uncertainties.**

- How callers handle the NULL return is not visible in this file.

<a id="u-89a453fe85db"></a>
### `secs2ms`

`ParameterError secs2ms(long *val, const char *str)` · [src/tool_paramhlp.c:L296-L330][f1]

Converts a seconds value with optional '.' fractional part into milliseconds stored in *val, positive input only.

A NULL string or seconds parse exceeding LONG_MAX/1000 - 1 returns PARAM_BAD_NUMERIC. If a '.' follows, the fraction is parsed (failure: PARAM_NUMBER_TOO_LARGE) and reduced by dividing by 10 while its digit count exceeds the 9-entry digs table or the value exceeds LONG_MAX/100, then scaled as fracs*100/digs[len-1]; result is secs*1000 plus that millisecond part. The digs[len-1] index would be invalid if the fraction length ever dropped to 0, which is only possible if curlx_str_number accepts zero digits.

**Uncertainties.**

- Whether curlx_str_number can consume an empty fractional part (digs[-1] indexing) is not visible here.
- Sign handling relies on curlx_str_number, not visible.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_paramhlp.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_libinfo.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_getpass.h
