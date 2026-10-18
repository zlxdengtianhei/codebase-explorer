# Dynamic Buffer (dynbuf)

**Capability.** Implements a growable, NUL-terminated byte buffer with init/reset/free lifecycle, append of strings/chunks/formatted output via a core nappend routine that grows on demand, and tail-trimming accessors.

Read this subtree for the canonical way curl builds strings and byte blobs. Init with a max size, append via add/addn/addf, inspect via accessors, and release with free (reset keeps the allocation).

**Depended on by.**

- [AWS SigV4 Request Signing](r3-aws-sigv4.md) · graph-confirmed · 59 edge(s)
- [DNS-over-HTTPS Resolver](r3-doh-resolver.md) · graph-confirmed · 5 edge(s)
- [Form/Multipart Argument Parsing](r3-form-parsing.md) · graph-confirmed · 10 edge(s)
- [HTTP/1 CONNECT Proxy Filter](r3-h1-proxy-tunnel.md) · graph-confirmed · 21 edge(s)
- [Transfer Output Writing](r3-output-writing.md) · graph-confirmed · 6 edge(s)
- [ASN.1 / X.509 Parsing](r3-x509-parsing.md) · model-inferred · 0 edge(s)
- [HTTP Message Signatures \(RFC 9421\)](r5-http-message-signatures.md) · graph-only · 56 edge(s)
- [Request Construction and Send](r6-http-request-build.md) · graph-only · 50 edge(s)
- [Authority and Host Handling](r6-url-host-authority.md) · graph-only · 36 edge(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) · graph-only · 29 edge(s)
- [MQTT Protocol Handler](r14-mqtt-protocol.md) · graph-only · 27 edge(s)
- [Tool Variable Store and Expansion](r6-tool-variable-store.md) · graph-only · 26 edge(s)
- [URL Globbing](r10-tool-urlglob.md) · graph-only · 25 edge(s)
- [RTSP protocol](r11-rtsp-protocol.md) · graph-only · 25 edge(s)
- [FTP Wildcard LIST Parsing](r6-ftp-list-parsing.md) · graph-only · 25 edge(s)
- [URL Encoding and Retrieval](r6-url-encoding-and-getters.md) · graph-only · 25 edge(s)
- [URL Parse Pipeline](r6-url-parse-pipeline.md) · graph-only · 25 edge(s)

Parent: [Shared Core Utilities](r3-core-utilities.md)

## Units (10)

<a id="u-dba8ba103985"></a>
### `curlx_dyn_init`

`void curlx_dyn_init(struct dynbuf *s, size_t toobig)` · [lib/curlx/dynbuf.c:L38-L50][f1]

Initializes a dynbuf struct to an empty state with a caller-supplied maximum size limit.

**Notes.**

- field: In DEBUGBUILD builds a magic pattern is stored in s->init; later calls assert it. The field does not exist in non-debug builds.

<a id="u-21f694d1bd8a"></a>
### `curlx_dyn_free`

`void curlx_dyn_free(struct dynbuf *s)` · [lib/curlx/dynbuf.c:L56-L62][f1]

Releases the dynbuf's heap buffer and zeroes length and allocation, leaving the struct reusable for further appends.

uses: [dyn_nappend](r3-dynbuf.md#u-e0f530e6b2b9)

<a id="u-e0f530e6b2b9"></a>
### `dyn_nappend`

`static CURLcode dyn_nappend(struct dynbuf *s, const unsigned char *mem, size_t len)` · [lib/curlx/dynbuf.c:L67-L119][f1]

Core append routine: grows the buffer as needed, copies len bytes, and keeps the result NUL-terminated.

**Notes.**

- failure: If fit (len + leng + 1) exceeds s->toobig, or realloc fails, the whole buffer is freed and CURLE_TOO_LARGE / CURLE_OUT_OF_MEMORY is returned, leaving the dynbuf empty.
- side_effect: First allocation is MIN_FIRST_ALLOC (or toobig/fit when smaller); growth doubles allocation, clamped to s->toobig.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

**Uncertainties.**

- Behavior of curlx_realloc/curlx_safefree is defined outside this file

<a id="u-76d5fbff65c6"></a>
### `curlx_dyn_reset`

`void curlx_dyn_reset(struct dynbuf *s)` · [lib/curlx/dynbuf.c:L125-L133][f1]

Clears the string by zeroing length while keeping the existing allocation; safe on already-freed buffers.

<a id="u-3a3e5b30ff85"></a>
### `curlx_dyn_tail`

`CURLcode curlx_dyn_tail(struct dynbuf *s, size_t trail)` · [lib/curlx/dynbuf.c:L139-L157][f1]

Keeps only the last trail bytes of the buffer, dropping everything before them.

**Notes.**

- failure: trail > leng returns CURLE_BAD_FUNCTION_ARGUMENT unchanged; trail == leng is a no-op; otherwise the tail is memmoved to offset 0, length set to trail, and the buffer re-terminated.

calls: [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6)

<a id="u-f1c899173947"></a>
### `curlx_dyn_addn`

`CURLcode curlx_dyn_addn(struct dynbuf *s, const void *mem, size_t len)` · [lib/curlx/dynbuf.c:L162-L168][f1]

Appends an arbitrary memory chunk of the given length by delegating to the internal append routine.

calls: [dyn_nappend](r3-dynbuf.md#u-e0f530e6b2b9)

<a id="u-b4e3d05d4a72"></a>
### `curlx_dyn_add`

`CURLcode curlx_dyn_add(struct dynbuf *s, const char *str)` · [lib/curlx/dynbuf.c:L173-L182][f1]

Appends a NUL-terminated string, measuring its length with strlen before the internal append.

calls: [dyn_nappend](r3-dynbuf.md#u-e0f530e6b2b9)

<a id="u-e48d243dc15d"></a>
### `curlx_dyn_vaddf`

`CURLcode curlx_dyn_vaddf(struct dynbuf *s, const char *fmt, va_list ap)` · [lib/curlx/dynbuf.c:L187-L215][f1]

Appends printf-formatted output from a va_list, with two compile-time implementations selected by BUILDING_LIBCURL.

**Notes.**

- failure: libcurl build maps MERR_TOO_LARGE to CURLE_TOO_LARGE and any other nonzero result to CURLE_OUT_OF_MEMORY; the other build formats via curl_mvaprintf and, on format failure, frees the whole buffer and returns CURLE_OUT_OF_MEMORY.

calls: [dyn_nappend](r3-dynbuf.md#u-e0f530e6b2b9)

**Uncertainties.**

- The BUILDING_LIBCURL branch relies on curlx_dyn_vprintf and MERR_TOO_LARGE, defined outside this file

<a id="u-063790a51674"></a>
### `curlx_dyn_addf`

`CURLcode curlx_dyn_addf(struct dynbuf *s, const char *fmt, ...)` · [lib/curlx/dynbuf.c:L220-L232][f1]

Variadic wrapper that formats its arguments and forwards to the va_list append implementation.

**Notes.**

- contract: A debug assert rejects a bare "%s" format, steering callers to curlx_dyn_add.

calls: [curlx_dyn_vaddf](r3-dynbuf.md#u-e48d243dc15d)

<a id="u-5e7007dbb9e6"></a>
### `dynbuf.c-accessors`

`char *curlx_dyn_ptr(const struct dynbuf *s)` · [lib/curlx/dynbuf.c:L237-L243][f1]

Small dynbuf accessor and ownership functions.

curlx_dyn_ptr and curlx_dyn_uptr return the buffer pointer as char* / unsigned char* (possibly NULL when empty); curlx_dyn_len returns the current byte length. curlx_dyn_take transfers ownership: it sets *plen to the length and resets bufr/leng/allc, after which only init or append calls make the struct usable again. curlx_dyn_setlen shrinks the string and re-terminates with NUL, returning CURLE_BAD_FUNCTION_ARGUMENT with no change if the requested length exceeds the current one. All assert the debug init pattern.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/dynbuf.c
