# Tool --libcurl source generation

**Capability.** Accumulates the equivalent libcurl program as source lines across five global lists (decl, data, code, toohard, clean) and dumps the generated sample program to a file or stdout.

Use this subtree to trace how tool operations are recorded as curl_easy_* calls. easysrc_free is the shared OOM bail-out; formatted lines go through easysrc_addf via the dynbuf formatter family.

**Depends on.**

- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 10 edge(s)

**Depended on by.**

- [--libcurl Code Generation](r1-libcurl-codegen.md) · graph-only · 39 edge(s)

Parent: [curl codebase](r9-curl-source.md)

## Units (8)

<a id="u-9200a0c7ed25"></a>
### `dumpeasysrc`

`void dumpeasysrc(void)` · [src/tool_easysrc.c:L202-L263][f1]

Writes the complete generated sample program to the file named by global->libcurl, or to stdout when that is "-".

If fopen of the target fails it warns and writes nothing; otherwise it prints srchead, then declaration, data, code (empty strings become blank lines), and clean-up list lines each indented two spaces, then srcend, closing the file only if it opened it. Finally it frees all generated lists via easysrc_free. Compilation of this file and its globals is guarded by !CURL_DISABLE_LIBCURL_OPTION.

calls: [easysrc_free](r9-tool-easysrc.md#u-080fdadacb3e), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

**Uncertainties.**

- fopened is set TRUE even when curlx_fopen fails; this only affects whether curlx_fclose is called, guarded by out being non-NULL.

<a id="u-078ffbf9f07d"></a>
### `easysrc_add`

`CURLcode easysrc_add(struct slist_wc **plist, const char *line)` · [src/tool_easysrc.c:L99-L118][f1]

Appends one literal source line to a target list.

If a perform has just been emitted (easysrc_pending_reset) and the target is easysrc_code, it first recursively inserts a curl_easy_reset(curl); line, clearing the flag before the recursion so it happens once; a reset-insertion failure aborts with that code. The line is appended with slist_wc_append; on allocation failure all generated source is freed (easysrc_free) and CURLE_OUT_OF_MEMORY is returned, otherwise *plist is updated to the new list head.

**Notes.**

- side_effect: May consume the pending-reset flag and inject an extra reset statement before the requested line.

calls: [slist_wc_append](r1-curl-tool.md#u-afa002f0f87c), [easysrc_free](r9-tool-easysrc.md#u-080fdadacb3e)

**Uncertainties.**

- Behavior depends on the caller passing &easysrc_code to trigger the reset insertion; other list targets never see it.

<a id="u-9e77edaffbe4"></a>
### `easysrc_addf`

`CURLcode easysrc_addf(struct slist_wc **plist, const char *fmt, ...)` · [src/tool_easysrc.c:L120-L136][f1]

Formatted variant of easysrc_add: renders fmt with varargs via curl_mvaprintf; a rendering failure returns CURLE_OUT_OF_MEMORY without side effects.

On success it delegates the line to easysrc_add (inheriting its reset-injection and free-on-failure behavior), then frees the temporary buffer with curl_free regardless.

calls: [easysrc_add](r9-tool-easysrc.md#u-078ffbf9f07d)

<a id="u-8ea7642d1e52"></a>
### `easysrc_cleanup`

`CURLcode easysrc_cleanup(void)` · [src/tool_easysrc.c:L190-L200][f1]

Emits the handle cleanup statements.

It clears easysrc_pending_reset first (nothing follows cleanup, so no reset is needed), then appends 'curl_easy_cleanup(curl);' and 'curl = NULL;'; the second append only happens if the first succeeded. Returns the first failing CURLcode.

calls: [easysrc_add](r9-tool-easysrc.md#u-078ffbf9f07d)

<a id="u-080fdadacb3e"></a>
### `easysrc_free`

`static void easysrc_free(void)` · [src/tool_easysrc.c:L84-L96][f1]

Frees all five global code-generation lists (decl, data, code, toohard, clean) via slist_wc_free_all and resets each global pointer to NULL; used as the out-of-memory bail-out for source generation.

calls: [slist_wc_free_all](r1-curl-tool.md#u-85a2af6b99ef)

<a id="u-33dcb0d3060d"></a>
### `easysrc_init`

`CURLcode easysrc_init(void)` · [src/tool_easysrc.c:L138-L142][f1]

Resets easysrc_performed to FALSE and emits the curl_easy_init statement into the code list; returns whatever easysrc_add returns, including CURLE_OUT_OF_MEMORY after freeing all generated source.

calls: [easysrc_add](r9-tool-easysrc.md#u-078ffbf9f07d)

<a id="u-fce99ee7f1e9"></a>
### `easysrc_is_first`

`bool easysrc_is_first(void)` · [src/tool_easysrc.c:L144-L147][f1]

Returns TRUE while no easysrc_perform has completed, i.e. the generated handle is still fresh.

<a id="u-3dffc1807bd5"></a>
### `easysrc_perform`

`CURLcode easysrc_perform(void)` · [src/tool_easysrc.c:L149-L188][f1]

Emits the perform statement and finalizes per-operation code.

If easysrc_toohard is non-empty, it appends a blank line, the srchard preamble comment lines, each unconverted option line, another blank line, and the comment terminator '*/', then frees and clears easysrc_toohard; any easysrc_add failure stops that sequence early with its error code. When no failure has occurred, it appends blank line, 'result = curl_easy_perform(curl);', blank line, sets easysrc_performed to TRUE, and arms easysrc_pending_reset so the next code-list insertion injects a reset first. Returns the first error encountered, or CURLE_OK.

**Notes.**

- failure: Every append is guarded by !result, so the first out-of-memory skips all subsequent emissions and leaves easysrc_toohard already freed only if the toohard block ran to its free (which is unconditional once entered).
- side_effect: Sets easysrc_pending_reset only on full success.

calls: [easysrc_add](r9-tool-easysrc.md#u-078ffbf9f07d)

**Uncertainties.**

- If an easysrc_add inside the toohard block fails, slist_wc_free_all(easysrc_toohard) still runs, discarding remaining unconverted options.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_easysrc.c
