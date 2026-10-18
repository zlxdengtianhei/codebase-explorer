# allocation and Windows text conversion

**Capability.** Heap allocation/zeroing helpers for buffers and strings plus Windows-only UTF-8/wchar conversion and a terminating snprintf wrapper.

Use these when duplicating or zeroing byte buffers and when bridging Windows wide-character APIs. They are platform-sensitive: most units compile only on Windows Unicode builds.

**Depended on by.**

- [flag dispatch and simple assignment](r11-arg-dispatch.md) · graph-confirmed · 1 edge(s)
- [RTSP protocol](r11-rtsp-protocol.md) · graph-confirmed · 1 edge(s)

Parent: [curlx shared utilities](r11-curlx-utilities.md)

## Units (4)

<a id="u-c74b7ad5f6c4"></a>
### `strdup.c-allocation-and-zeroing-helpers`

`wchar_t *curlx_wcsdup(const wchar_t *src)` · [lib/curlx/strdup.c:L43-L51][f1]

Allocation and zeroing helpers for byte buffers and strings.

curlx_wcsdup (Windows only) computes the wchar length, returns NULL if (length + 1) * sizeof(wchar_t) would overflow size_t, otherwise duplicates via curlx_memdup. curlx_memdup allocates length bytes with curlx_malloc, returns NULL if allocation fails, else memcpy's exactly length bytes with no terminator. curlx_memdup0 allocates length + 1, returning NULL when length == SIZE_MAX (overflow guard) or allocation fails; it copies length bytes when nonzero (asserting src is non-NULL in that case), always null-terminates, and returns the buffer. Under USE_CURLX_MEMZERO, curlx_memzero_low zeroes via a volatile function pointer to memset, a fallback for systems without a secure-zero function, skipping NULL; curlx_memzero adds a NULL check around it, and curlx_strzero zeroes strlen(buf) bytes of a null-terminated buffer, also skipping NULL. The volatile pointer split exists to keep compilers from eliding the zeroing.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4)

**Uncertainties.**

- Whether curlx_memzero_low is compiled at all depends on USE_CURLX_MEMZERO, which is defined elsewhere; outside that build the zeroing entry points are not visible in this file.

<a id="u-c71992718e87"></a>
### `curlx_convert_UTF8_to_wchar`

`wchar_t *curlx_convert_UTF8_to_wchar(const char *str_utf8)` · [lib/curlx/multibyte.c:L34-L54][f2]

Converts a UTF-8 string to a heap-allocated wide string on Windows Unicode builds.

A NULL input yields NULL. It first calls MultiByteToWideChar with MB_ERR_INVALID_CHARS to get the required length; a non-positive result (invalid UTF-8 or failure) returns NULL. On success it allocates with curlx_malloc and re-encodes; if the second call returns 0 it frees the buffer and returns NULL. Caller owns the returned buffer.

uses: [multibyte.h module code (L1–L51)][f3]

**Uncertainties.**

- Allocation failure path returns NULL via fall-through; curlx_malloc's exact failure semantics are defined elsewhere

<a id="u-63f640ace0d8"></a>
### `curlx_convert_wchar_to_UTF8`

`char *curlx_convert_wchar_to_UTF8(const wchar_t *str_w)` · [lib/curlx/multibyte.c:L56-L76][f2]

Converts a wide string to a heap-allocated UTF-8 string on Windows Unicode builds.

NULL input returns NULL. It sizes the output with WideCharToMultiByte; a non-positive result returns NULL. It then allocates with curlx_malloc and converts again; a zero return on the second call frees the buffer and returns NULL. Caller owns the result.

uses: [multibyte.h module code (L1–L51)][f3]

<a id="u-41f03093f2cd"></a>
### `curlx_win32_snprintf`

`void curlx_win32_snprintf(char *buf, size_t maxlen, const char *fmt, ...)` · [lib/curlx/snprintf.c:L31-L48][f4]

Windows-only variadic wrapper around vsnprintf that guarantees null-termination and discards the return length.

With maxlen equal to zero it returns immediately without touching the buffer. Otherwise it formats into buf and then unconditionally writes 0 at buf[maxlen-1], capping any unterminated output. Format-string warnings are suppressed when CURL_HAVE_DIAG is defined. Uses vsnprintf despite its ban status, annotated for the checker.

**Notes.**

- failure: Truncation is silent: no indication of clipped output is returned.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/strdup.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/multibyte.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curlx/multibyte.h
[f4]: ../../../../../../eval/curl-2c04412/lib/curlx/snprintf.c
