# Formatter API families

**Capability.** The three public entry-point families built on the engine: bounded-buffer snprintf-style functions, dynbuf-backed append formatters with a 512-byte staging buffer, and unbounded buffer/stdio formatters.

Callers across the codebase (auth header generation, progress meter, telnet, the tool) use these families. The nsprintf family also serves as the bounded sink used by the engine's own double formatting.

**Depended on by.**

- [Tool Help, Version & Debug Output](r14-tool-help-debug.md) · graph-only · 26 edge(s)

Parent: [printf engine \(mprintf\)](r9-mprintf.md)

## Units (3)

<a id="u-780e9db0224b"></a>
### `lib-mprintf-c-buffer-stdio-family`

`static int storebuffer(unsigned char outc, void *f)` · [lib/mprintf.c:L1427-L1433][f1]

Covers the unbounded-buffer and stdio formatters.

storebuffer/storerun write bytes straight through a char* cursor with no bound check and always accept everything. curl_msprintf formats into the caller's buffer through formatf and then null-terminates; curl_mvsprintf is its va_list core doing the same. fputc_wrapper writes one byte with fputc and records i->error when EOF returns; fwrite_wrapper writes runs with fwrite and flags an error when fewer than len bytes are written. curl_mvfprintf runs formatf with these sinks and returns -1 if the sink flagged an error, else the formatted count; curl_mfprintf and curl_mprintf are vararg wrappers (the latter targeting stdout), and curl_mvprintf forwards to curl_mvfprintf(stdout,...). None of these functions bounds-check the destination buffer; callers must size it themselves.

calls: [formatf](r9-mprintf-format-engine.md#u-7022ea537fbf), [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

**Uncertainties.**

- Partial fwrite results set the error flag but the stream position after a short write is not restored; the returned count reflects formatted, not necessarily written, bytes.

<a id="u-ce09737881fa"></a>
### `lib-mprintf-c-dynbuf-alloc-family`

`static int alloc_flush(void *f)` · [lib/mprintf.c:L1284-L1296][f1]

Implements the dynbuf-backed append formatters using a 512-byte staging buffer so the dynbuf append overhead is paid per chunk, not per byte.

alloc_flush commits staged bytes via curlx_dyn_addn, resetting nstage and mapping CURLE_TOO_LARGE to MERR_TOO_LARGE, other errors to MERR_MEM, returning 1 on failure. alloc_addn appends directly with the same error mapping. alloc_fits predicts whether 'more' bytes still fit the dynbuf's toobig limit counting staged bytes and the reserved terminator byte. alloc_addbyter stages single bytes; when the stage is full it flushes, and when the next byte would exceed the limit it flushes and appends that byte alone so the size limit is reported at exactly that byte (which %n's count depends on), returning 1 on failure. alloc_addrun stages runs, flushing when the stage is full; when a run crosses the limit it stages what fits, flushes, and appends the first non-fitting byte individually, returning the accepted count so partial acceptance aborts formatting. curlx_dyn_vprintf drives formatf with these callbacks plus alloc_flush, does a final flush when no error occurred, and on error frees the dynbuf and returns the MERR code. curl_mvaprintf does the same into a fresh dynbuf capped at DYN_APRINTF, freeing and returning NULL on error, returning the buffer pointer when non-empty and curlx_strdup("") for an empty result. curl_maprintf is the vararg wrapper.

calls: [formatf](r9-mprintf-format-engine.md#u-7022ea537fbf), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a), [curlx_dyn_init](r3-dynbuf.md#u-dba8ba103985), [dynbuf.c-accessors](r3-dynbuf.md#u-5e7007dbb9e6)

**Uncertainties.**

- alloc_fits reads the dynbuf struct fields 'leng' and 'toobig' directly, assuming the layout documented only in dynbuf internals; the fit formula mirrors curlx_dyn_addn's rejection rule as noted in the comment.
- The numeric values of the MERR_* codes are defined outside this file.

<a id="u-e17299de2a1f"></a>
### `lib-mprintf-c-nsprintf-family`

`static int addbyter(unsigned char outc, void *f)` · [lib/mprintf.c:L1220-L1230][f1]

Implements the bounded-buffer snprintf family.

addbyter is the byte callback: while fewer than max bytes are stored it appends to the buffer and returns 0, otherwise returns 1 (aborting formatting). addrun is the block callback: it copies min(len, remaining) bytes and returns that count, so overlong output stops formatting at the buffer limit. curl_mvsnprintf drives formatf with these sinks and then null-terminates: if maxlength is zero nothing is written or terminated; if the output exactly filled the buffer the last byte is replaced with NUL and the return count is decremented so the NUL is not counted, otherwise a NUL is appended after the output. curl_msnprintf is the vararg wrapper forwarding to curl_mvsnprintf. The return value is the untruncated character count, like standard snprintf.

calls: [formatf](r9-mprintf-format-engine.md#u-7022ea537fbf)

**Uncertainties.**

- Exact truncation semantics rely on formatf returning the would-be full count; that holds because addbyter/addrun aborts propagate the running count.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mprintf.c
