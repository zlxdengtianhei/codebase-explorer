# complex option value parsers

**Capability.** Parsing option values with nontrivial syntax: cert/passphrase splitting, size units, rate intervals, ranges, ports, headers/quotes, ECH, time conditions, upload flags, URL/continue-at/write-out handling, and URL-encoded POST data.

Each parse_*/set_* helper owns one option's syntax and is invoked from the dispatch family (mostly opt_string/opt_bool/opt_file). Read the specific helper for the option you care about; add_url/parse_output/parse_upload_file/parse_remote_name manage per-URL node pairing.

**Depends on.**

- [string parsing primitives](r11-strparse-word-scanning.md) · graph-confirmed · 8 edge(s)

**Depended on by.**

- [flag dispatch and simple assignment](r11-arg-dispatch.md) · graph-confirmed · 27 edge(s) · Flag dispatch hands complex option values (URLs, ranges, headers, sizes) to the dedicated value parsers.

Parent: [command-line option processing](r11-cli-options.md)

## Units (25)

<a id="u-773e8c0d30f0"></a>
### `parse_cert_parameter`

`UNITTEST ParameterError parse_cert_parameter(const char *cert_parameter, char **certn…` · [src/tool_getparam.c:L389-L493][f1]

Splits a --cert/-E argument into certificate name and optional passphrase separated by the first unescaped colon, honoring backslash escapes for ':' and '\'.

Empty input returns PARAM_BLANK_STRING. A 'pkcs11:' prefix or absence of ':' or '\' yields the whole string as certname with NULL passphrase. Otherwise an output buffer is filled scanning the input: a backslash copies the escaped character literally, and a trailing lone backslash copies a backslash; on Windows a colon at position 1 followed by a slash and a leading letter is kept as a drive-letter colon. The first other colon ends certname and the remainder becomes passphrase (NULL if empty). On PARAM_NO_MEM the partial certname is freed and the error propagates.

uses: [GetFileAndPassword](r11-option-value-parsers.md#u-8eab6908a176)

**Uncertainties.**

- Colons inside a pkcs11: URI are never separators because the prefix check returns early.

<a id="u-8eab6908a176"></a>
### `GetFileAndPassword`

`static ParameterError GetFileAndPassword(const char *nextarg, char **file, char **pas…` · [src/tool_getparam.c:L523-L539][f1]

Applies parse_cert_parameter to an option argument and stores the resulting cert name and passphrase into the given file/password slots.

On success it always frees and replaces *file, and replaces *password only when a passphrase was parsed; any parse or allocation error is returned with both slots untouched.

calls: [parse_cert_parameter](r11-option-value-parsers.md#u-773e8c0d30f0)

<a id="u-dfd21691ba24"></a>
### `replace_url_encoded_space_by_plus`

`static size_t replace_url_encoded_space_by_plus(char *url)` · [src/tool_getparam.c:L496-L521][f1]

Rewrites a string in place, converting each literal '%20' three-byte sequence into '+' and compacting the remainder, then NUL-terminates and returns the new length.

Only the exact three-byte pattern matches; partial sequences like '%2' pass through unchanged.

<a id="u-49aef9d46a35"></a>
### `existingfile`

`static ParameterError existingfile(char **store, const struct LongShort *a, const cha…` · [src/tool_getparam.c:L2241-L2252][f1]

Validates that filename exists via curlx_stat; failure errors 'The file ...

does not exist' naming the option and returns PARAM_BAD_USE, otherwise stores the path via getstr rejecting blanks.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-8d7cf60ca943"></a>
### `getunit`

`static const struct sizeunit *getunit(char unit)` · [src/tool_getparam.c:L547-L562][f1]

Looks up a size-suffix character (p, t, g, m, k) case-insensitively by OR-ing 0x20, returning a pointer to a static sizeunit entry holding the multiplier and its decimal digit count, or NULL for unknown suffixes.

<a id="u-6b39a7a01969"></a>
### `GetSizeParameter`

`UNITTEST ParameterError GetSizeParameter(const char *arg, curl_off_t *out)` · [src/tool_getparam.c:L569-L629][f1]

Parses a size argument such as '10M' or '1.5g' for --limit-rate/--max-filesize into a byte count.

Integer parse overflow returns PARAM_NUMBER_TOO_LARGE, other parse errors PARAM_BAD_NUMERIC. An optional '.' starts a fraction. A suffix longer than one character is PARAM_BAD_USE; empty or 'b' suffix means plain bytes, and fractional digits with byte units are rejected. Otherwise getunit resolves K/M/G/T/P; a fraction is scaled to the unit, trimming precision digits beyond the multiplier's decimal length, with an overflow guard choosing the multiplication order. A final overflow check returns PARAM_NUMBER_TOO_LARGE; otherwise *out gets value*mul+add and PARAM_OK.

calls: [getunit](r11-option-value-parsers.md#u-8d7cf60ca943)

<a id="u-74de1cb1417e"></a>
### `data_urlencode`

`static ParameterError data_urlencode(const char *nextarg, char **postp, size_t *lenp)` · [src/tool_getparam.c:L650-L753][f1]

Builds URL-encoded POST data for --data-urlencode.

The argument may be 'name=content', 'name@filename', bare content, or a bare filename after '@': the first '=' splits name/content, else the first '@' splits name/filename, else the whole string is content. The '@' form reads the file ('-' means stdin in binary mode); open failure logs and returns PARAM_READ_ERROR, read errors propagate. Otherwise getstr copies content with blanks allowed. Empty file data becomes an empty string so a POST is still sent. Content is curl_easy_escape'd and '%20' becomes '+'. With a name part, 'name='+encoded is assembled into a dynbuf capped at 500MB, any add failure returning PARAM_NO_MEM; without a name the encoded copy alone is returned. On success *postp/*lenp receive buffer and length.

calls: [replace_url_encoded_space_by_plus](r11-option-value-parsers.md#u-dfd21691ba24), [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

**Uncertainties.**

- Any dynbuf add failure, including the size cap, is uniformly reported as PARAM_NO_MEM.

<a id="u-e912e7aba48d"></a>
### `set_data`

`static ParameterError set_data(cmdline_t cmd, const char *nextarg, struct OperationCo…` · [src/tool_getparam.c:L940-L1016][f1]

Accumulates POST body data for the --data* family and --json into config->postdata.

--data-urlencode delegates to data_urlencode. Otherwise a leading '@' (except --data-raw) reads a file or stdin ('-'; binary mode forced for --data-binary and --json), using file2memory for binary and file2string otherwise, with open failure returning PARAM_READ_ERROR and empty files yielding an empty string. Other content is copied via getstr with blanks allowed. --json sets config->jsoned. An '&' separator is appended between chunks unless this is --json; any dynbuf append failure maps to PARAM_NO_MEM. Finally postfields points at the dynbuf buffer and the temporary postdata is freed.

calls: [data_urlencode](r11-option-value-parsers.md#u-74de1cb1417e), [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-1f514b09fdd0"></a>
### `set_rate`

`static ParameterError set_rate(const char *nextarg)` · [src/tool_getparam.c:L1018-L1081][f1]

Parses --rate as a number with optional '/s', '/m', '/h' (default), or '/d' unit and stores the per-transfer millisecond interval in global->ms_per_transfer.

Non-numeric value returns PARAM_BAD_NUMERIC; a value below 1 returns PARAM_BAD_USE; an unknown unit errors and returns PARAM_BAD_USE. An optional count after the slash multiplies the interval, with overflow returning PARAM_NUMBER_TOO_LARGE; a failed count parse defaults the count to 1. A denominator above the interval also returns PARAM_NUMBER_TOO_LARGE; otherwise ms_per_transfer gets numerator/denominator.

<a id="u-a6cc902db078"></a>
### `url_query`

`static ParameterError url_query(const char *nextarg, struct OperationConfig *config)` · [src/tool_getparam.c:L905-L938][f1]

Appends to config->query for --url-query.

A leading '+' takes the rest verbatim; otherwise the argument is encoded via data_urlencode. If a query already exists, old and new are joined with '&' into a dynbuf capped at 100000 bytes and the old query freed; otherwise the new query is stored directly. Allocation failures map to PARAM_NO_MEM.

calls: [data_urlencode](r11-option-value-parsers.md#u-74de1cb1417e)

<a id="u-7522e9ca3f81"></a>
### `add_url`

`static ParameterError add_url(struct OperationConfig *config, const char *thisurl, bo…` · [src/tool_getparam.c:L1092-L1133][f1]

Adds a URL to config's url_list, reusing the first node whose urlset is FALSE or appending a new node via new_getout (PARAM_NO_MEM if allocation fails).

Fills url->url with getstr rejecting blanks, sets urlset TRUE, and when remote_noglob sets useremote and noglob. After incrementing num_urls, more than one URL combined with an etag save/compare option errors 'The etag options only work on a single URL' and returns PARAM_BAD_USE.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-e01a2793a02e"></a>
### `parse_url`

`static ParameterError parse_url(struct OperationConfig *config, const char *nextarg)` · [src/tool_getparam.c:L1135-L1169][f1]

Handles --url.

An argument starting with '@' reads URLs line by line from a file ('@-' means stdin), calling add_url for each with remote_noglob TRUE; the file is opened read-text, open failure returning PARAM_READ_ERROR, and any read error or add_url error surfaces as PARAM_READ_ERROR. A plain argument is added directly via add_url with remote_noglob FALSE.

calls: [add_url](r11-option-value-parsers.md#u-7522e9ca3f81)

<a id="u-caad03eefa61"></a>
### `parse_localport`

`static ParameterError parse_localport(struct OperationConfig *config, const char *nex…` · [src/tool_getparam.c:L1171-L1205][f1]

Parses --local-port as 'start' or 'start - end'.

Leading digits form the start port; anything after must begin (after optional blanks) with '-' or the argument is PARAM_BAD_USE. The start is parsed with str2unummax capped at 65535 (failure PARAM_BAD_USE). Without a range part, localportrange defaults to 1; with one, the end is parsed the same way, range becomes end-(start-1), and a result below 1 returns PARAM_BAD_USE.

<a id="u-6914c70bdba8"></a>
### `parse_continue_at`

`static ParameterError parse_continue_at(struct OperationConfig *config, const char *n…` · [src/tool_getparam.c:L1207-L1234][f1]

Handles --continue-at.

Rejects use with --range, --remove-on-error, or --no-clobber, each with an errorf and PARAM_BAD_USE. An argument other than '-' parses a byte offset into resume_from via str2offset with resume_from_current FALSE; '-' sets resume_from_current TRUE and resume_from 0. Either way use_resume becomes TRUE and str2offset errors propagate.

<a id="u-f521bd50622b"></a>
### `parse_ech`

`static ParameterError parse_ech(struct OperationConfig *config, const char *nextarg)` · [src/tool_getparam.c:L1236-L1291][f1]

Handles --ech.

Without ECH support returns PARAM_LIBCURL_DOESNT_SUPPORT. 'pn:<...>' sets ech_public, 'ecl:<...>' sets ech_config, both via getstr rejecting blanks; anything else sets ech. For 'ecl:@file' (or @- for stdin) the file is read with file2string, an unopenable file warned and returning PARAM_BAD_USE; the content is rewrapped as 'ecl:<content>' via curl_maprintf and stored, with allocation failures returning PARAM_NO_MEM.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-5f1e12c5251d"></a>
### `parse_header`

`static ParameterError parse_header(struct OperationConfig *config, cmdline_t cmd, con…` · [src/tool_getparam.c:L1293-L1338][f1]

Handles --header/--proxy-header.

An '@'-prefixed argument reads headers line by line from a file or stdin, adding each to proxyheaders or headers via add2list; open failure errors and returns PARAM_READ_ERROR, and read errors also surface as PARAM_READ_ERROR. A direct argument lacking both ':' and ';' draws a warning that it does not look like a header but is still added to the list selected by the command.

uses: [parse_quote](r11-option-value-parsers.md#u-5bc00069212f)

<a id="u-e04e12df2a2b"></a>
### `parse_output`

`static ParameterError parse_output(struct OperationConfig *config, const char *nextarg)` · [src/tool_getparam.c:L1340-L1378][f1]

Assigns an output file to the first url_list node whose outset is FALSE, or creates a new node (PARAM_NO_MEM on failure).

With an argument, url->outfile is set via getstr rejecting blanks; with NULL (from --out-null), outfile is NULL and out_null TRUE. useremote is switched off and outset set TRUE in both cases.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-14d63c1674e4"></a>
### `parse_remote_name`

`static ParameterError parse_remote_name(struct OperationConfig *config, bool toggle)` · [src/tool_getparam.c:L1380-L1417][f1]

Handles --remote-name/-O and --remote-name-all.

A FALSE toggle with remote_name_all unset does nothing. Otherwise it picks or creates the first url_out node without outset (PARAM_NO_MEM on failure), clears outfile, sets useremote to the toggle, outset TRUE, and out_null FALSE.

<a id="u-5bc00069212f"></a>
### `parse_quote`

`static ParameterError parse_quote(struct OperationConfig *config, const char *nextarg)` · [src/tool_getparam.c:L1419-L1441][f1]

Routes a QUOTE command by leading character: '-' strips the dash and appends to postquote, '+' strips and appends to prequote, anything else appends to quote; add2list results propagate.

<a id="u-e4f8dfd2e7e3"></a>
### `parse_range`

`static ParameterError parse_range(struct OperationConfig *config, const char *nextarg)` · [src/tool_getparam.c:L1443-L1485][f1]

Handles --range.

If --continue-at is active (use_resume), errors and returns PARAM_BAD_USE. If the argument parses as a bare number with no dash, warns that a dash is required and rewrites the range as '<number>-' (PARAM_NO_MEM if the copy fails). Otherwise the range is scanned for characters outside digits, '-', and ','; a bad character triggers a warning that the server response is uncertain and the scan stops. The original argument is stored into config->range via getstr rejecting blanks.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-9074450b3894"></a>
### `parse_upload_file`

`static ParameterError parse_upload_file(struct OperationConfig *config, const char *n…` · [src/tool_getparam.c:L1487-L1523][f1]

Handles -T/--upload-file by finding or creating the first url_ul node without uploadset (PARAM_NO_MEM on failure), marking uploadset TRUE.

An empty argument sets noupload TRUE; otherwise the filename (which may be '-' for stdin, kept as the literal string) is stored via getstr rejecting blanks.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-03e09adf4306"></a>
### `parse_writeout`

`static ParameterError parse_writeout(struct OperationConfig *config, const char *next…` · [src/tool_getparam.c:L1583-L1620][f1]

Handles --write-out.

An '@'-prefixed argument reads the format from a file or stdin ('-' becomes the fname '<stdin>'), freeing any previous writeout; open failure errors and returns PARAM_READ_ERROR, read errors propagate, and an empty result draws a warning but succeeds. Otherwise the argument is stored via getstr allowing blanks.

calls: [getstr](r11-arg-dispatch.md#u-7d7347e28a1d)

<a id="u-fa5f7d316680"></a>
### `parse_time_cond`

`static ParameterError parse_time_cond(struct OperationConfig *config, const char *nex…` · [src/tool_getparam.c:L1622-L1663][f1]

Handles -z/--time-cond.

A leading '+' (or none) selects If-Modified-Since, '-' selects If-Unmodified-Since, '=' selects Last-Modified, each dash/equals form skipping the prefix character. The remaining text is parsed with curl_getdate into condtime; a -1 result falls back to getfiletime on the same text, and if that also fails, timecond is reset to CURL_TIMECOND_NONE with a warning, disabling the condition. Other errors always return PARAM_OK.

<a id="u-f8c560c36885"></a>
### `parse_upload_flags`

`static ParameterError parse_upload_flags(struct OperationConfig *config, const char *…` · [src/tool_getparam.c:L1680-L1723][f1]

Handles --upload-flags as a comma-separated list of IMAP flags (answered, deleted, draft, flagged, seen).

A leading '-' negates, clearing the flag bit from config->upload_flags; otherwise the bit is set. An unrecognized token stops processing and returns PARAM_OPTION_UNKNOWN; note tokens before the bad one have already been applied.

<a id="u-a127791a6e5d"></a>
### `find_tos`

`static int find_tos(const void *a, const void *b)` · [src/tool_getparam.c:L897-L902][f1]

strcmp comparison callback over TOSEntry name fields for bsearch in opt_string's --ip-tos lookup.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_getparam.c
