# Write-out output

**Capability.** Implements --write-out: the variable id enum and name/id/writefunc mapping, and JSON emission that escapes strings and invokes each mapping's write function with use_json=TRUE.

Read when adding or changing a write-out variable. The enum ordering (URL* before URLE*, VAR_INPUT_URLESCHEME) is relied on by urlpart comparisons.

**Depends on.**

- [Socket, buffer, and integer utilities](r12-socket-and-buffer-utils.md) · model-inferred · 0 edge(s)

Parent: [Command-line tool](r12-cli-tool.md)

## Units (10)

<a id="u-35a2e89a5a73"></a>
### `src/tool_writeout.h:<enum>`

`enum` · [src/tool_writeout.h:L30-L106][f1]

Defines writeoutid, the enum of all --write-out variable ids from VAR_NONE through VAR_NUM_OF_VARS, with the URL* (request URL) ids listed before the URLE* (effective URL) ids; VAR_INPUT_URLESCHEME is documented as the first URLE* entry, which urlpart relies on for its >= comparison.

**Notes.**

- contract: urlpart treats any id >= VAR_INPUT_URLESCHEME as an effective-URL variable, so the enum ordering is load-bearing.

<a id="u-97f37d17e28a"></a>
### `tool_writeout.h module code (L1–L30)`

`module_region` · [src/tool_writeout.h:L1-L30][f1]

Header guard and includes for tool_writeout.h; non-behavioral.

<a id="u-950ef8917291"></a>
### `tool_writeout.h module code (L106–L107)`

`module_region` · [src/tool_writeout.h:L106-L107][f1]

Single-line residual between the enum and the struct; non-behavioral.

<a id="u-c499fd1c3e02"></a>
### `tool_writeout.h module code (L115–L120)`

`module_region` · [src/tool_writeout.h:L115-L120][f1]

Declaration of ourWriteOut and header close; the declaration itself carries no behavior.

<a id="u-0b25a58c31f7"></a>
### `writeoutvar`

`struct writeoutvar` · [src/tool_writeout.h:L108-L115][f1]

Defines struct writeoutvar { name, id, ci, writefunc } binding a variable name to its enum id, optional CURLINFO handle, and a write function of uniform signature taking (FILE*, wovar, per_transfer, CURLcode, use_json).

<a id="u-44ea371c2203"></a>
### `headerJSON`

`void headerJSON(FILE *stream, struct per_transfer *per)` · [src/tool_writeout_json.c:L118-L162][f2]

Emits response headers as a JSON object.

Iterates all CURLH_HEADER entries of the last request via curl_easy_nextheader (reqno -1). A header with amount > 1 is grouped: on its index-0 entry the name is printed (lowercased) followed by a '[' list of all its values fetched by curl_easy_header by index, comma-separated; non-zero-index entries of already-grouped headers are skipped. Single-instance headers are emitted as "name":["value"] with a leading comma-newline when not first. Values are JSON-escaped; header names are lowercased. Always terminates with a newline and '}'.

**Uncertainties.**

- Grouped-header iteration breaks out of the value loop if a curl_easy_header lookup for an intermediate index fails, potentially emitting a truncated list.
- Only CURLH_HEADER (plain) headers are included; other header kinds are excluded by the API arguments.

<a id="u-4dfb834ada22"></a>
### `jsonWriteString`

`void jsonWriteString(FILE *stream, const char *in, bool lowercase)` · [src/tool_writeout_json.c:L83-L95][f2]

Prints `in` to stream as a quoted JSON string: initializes a dynbuf capped at MAX_JSON_STRING, runs jsonquoted over strlen(in), and on success writes opening quote, escaped content (empty string prints nothing between quotes), closing quote.

On jsonquoted failure nothing at all is written. The dynbuf is always freed.

**Uncertainties.**

- If the escaped content exceeded the 100000-byte dynbuf cap, jsonquoted fails and the string is silently dropped.

<a id="u-f48962618bda"></a>
### `jsonquoted`

`int jsonquoted(const char *in, size_t len, struct dynbuf *out, bool lowercase)` · [src/tool_writeout_json.c:L36-L81][f2]

Appends the JSON-escaped form of len bytes of `in` to the caller-provided dynbuf (not initialized here), without outer quotes.

Escapes backslash, quote, and the standard control characters (\b, \f, \n, \r, \t); other bytes below 32 become \u00xx; printable bytes pass through, ASCII letters lowercased when `lowercase` is set (via bit-or, not locale-dependent tolower). Returns 0 on success, or the CURLcode from the first failing dynbuf append (stopping the scan).

**Notes.**

- contract: The output dynbuf must be initialized by the caller; this function only appends.

uses: [varfunc](r6-tool-variable-store.md#u-b1c8c0248ffd)

**Uncertainties.**

- Multibyte UTF-8 bytes pass through unvalidated; malformed input yields invalid JSON escapes-free bytes.

<a id="u-3aa9887a5845"></a>
### `ourWriteOutJSON`

`void ourWriteOutJSON(FILE *stream, const struct writeoutvar mappings[], size_t nentri…` · [src/tool_writeout_json.c:L97-L116][f2]

Emits a JSON object of all write-out variables: opens '{', invokes each mapping's writefunc with use_json=TRUE (which emits "name":value or "name":null), emitting a comma after each that returned 1, then appends "curl_version": as a JSON string and closes with '}'.

Relies on the mappings being alphabetically sorted; curl_version is appended last as a non --write-out entry.

uses: [ourWriteOut](r8-tool-writeout.md#u-e0b2a7c6de1b)

**Uncertainties.**

- Because every writefunc returns constant 1, a comma is emitted after every entry including the last one before "curl_version", producing trailing commas in the JSON output as written by this code.

<a id="u-46f2b43048ba"></a>
### `tool_writeout_json.c module code (L1–L35)`

`module_region` · [src/tool_writeout_json.c:L1-L35][f2]

Include prelude of tool_writeout_json.c and the MAX_JSON_STRING 100000 cap used for JSON string buffers; non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_writeout.h
[f2]: ../../../../../../eval/curl-2c04412/src/tool_writeout_json.c
