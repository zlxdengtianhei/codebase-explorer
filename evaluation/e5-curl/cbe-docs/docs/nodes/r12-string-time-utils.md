# String and time utilities

**Capability.** Safe copying, path basename extraction, thread-safe strerror (with a Winsock message table), SNPRINTF macro selection, and curltime structs with millisecond-difference and ceiling helpers.

Use for bounded string handling and time math; the timediff helpers expect the newer time first to avoid negative results.

**Depended on by.**

- [Progress meter](r12-progress-meter.md) · graph-confirmed · 1 edge(s)

Parent: [Portable utilities](r12-portable-utils.md)

## Units (6)

<a id="u-902a4ccc6a41"></a>
### `curlx_strcopy`

`void curlx_strcopy(char *dest, /* destination buffer */ size_t dsize, /* size of targ…` · [lib/curlx/strcopy.c:L38-L50][f1]

Safe strcpy replacement that copies slen bytes of src into dest when slen is strictly less than the destination size dsize, appending a null terminator.

When the source does not fit, no copy is made; if dsize is non-zero it stores an empty string at dest[0], leaving the rest untouched. A DEBUGASSERT flags slen >= dsize in debug builds but does not alter the release behavior. Returns nothing.

**Uncertainties.**

- Caller must supply slen matching src's actual string length; the function does not measure src

<a id="u-b0bcc29a7ca5"></a>
### `curlx_strerror`

`const char *curlx_strerror(int err, char *buf, size_t buflen)` · [lib/curlx/strerr.c:L248-L329][f2]

Thread-safe strerror replacement writing a message for err into buf.

It saves errno (and GetLastError on Windows), returns NULL immediately if buflen is 0, and clears buf[0]. On Windows the preference order is CRT, then Winsock, then Windows API: if strerror_s fails or yields "Unknown error", it tries get_winsock_error, then curlx_get_winapi_error; if all fail and space allows, it writes "Unknown error %d (%#x)" via SNPRINTF. On POSIX with POSIX strerror_r, a nonzero return triggers the "Unknown error %d" fallback when the buffer is large enough. With glibc strerror_r, which returns a pointer that may not point into the supplied buffer, the message is unconditionally copied via SNPRINTF when non-NULL. Without strerror_r it falls back to the non-reentrant strerror(). Finally, trailing '\n' is stripped if at least two characters precede it, and trailing '\r' if at least one precedes it; saved errno and Windows last-error values are restored so the call has no observable side effects on them. Returns buf.

calls: [get_winsock_error](r12-string-time-utils.md#u-d8c0b16bba3f); uses: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- curlx_get_winapi_error is not defined in this excerpt; its failure semantics are inferred from its position in the condition chain.

<a id="u-d8c0b16bba3f"></a>
### `get_winsock_error`

`static const char *get_winsock_error(int err, char *buf, size_t len)` · [lib/curlx/strerr.c:L44-L226][f2]

Static Winsock-only helper translating a Winsock error code into a fixed message string copied into the caller's buffer.

If len is 0 it returns NULL; otherwise it clears buf[0]. When CURLVERBOSE is not defined it returns NULL for every code (the err parameter is unused). Under CURLVERBOSE a large switch maps WSA error codes (including extended Winsock and getXbyY-style codes) to short messages, with WSAEINPROGRESS/WSAEALREADY sharing one message; unknown codes return NULL. On a match, curlx_strcopy copies the message into buf within len and returns buf.

uses: [curlx_strerror](r12-string-time-utils.md#u-b0bcc29a7ca5)

**Uncertainties.**

- Behavior without CURLVERBOSE is a compile-time null-returning stub; which macro configuration ships is not visible here.

<a id="u-c99e01e24310"></a>
### `curlx_basename`

`char *curlx_basename(char *path)` · [lib/curlx/basename.c:L52-L70][f3]

Returns a pointer to the final path component of a path, honoring both '/' and '\' separators.

It finds the last occurrence of each separator with strrchr; if both exist it takes whichever is later in the string, and in every match case returns the pointer one past that separator. If neither separator occurs, or the input is empty or NULL, the original pointer is returned unchanged. It never strips trailing separators, never returns "." for empty input, and never copies storage — a deliberate simplification of the POSIX basename semantics quoted above it. Compiled only when HAVE_BASENAME is undefined.

**Uncertainties.**

- POSIX corner cases (all-slash input, NULL/empty path) are documented in the comment but not implemented; actual return for those is the input pointer itself

<a id="u-91399d26aabc"></a>
### `timeval-h-time-interface`

`struct curltime` · [lib/curlx/timeval.h:L30-L33][f4]

Header for the curltime struct {time_t tv_sec; int tv_usec} and time helpers: curlx_now/curlx_pnow for current time, curlx_timediff_ms/ptimediff_ms, curlx_timediff_ceil_ms, curlx_us_to_ceil_ms, and the microsecond variants, all expecting the newer time as first argument to avoid negative differences; ceiling variants round up.

curlx_gmtime converts a time_t to struct tm returning CURLcode. On Windows, curlx_now_init must be called before curlx_now for tool/test builds. Only declarations and comments appear here.

**Uncertainties.**

- Exact rounding and overflow behavior of the diff functions is in the implementations, not this header

<a id="u-de6254b0f7f2"></a>
### `snprintf-h-snprintf-selection`

`module_region` · [lib/curlx/snprintf.h:L1-L45][f5]

Header selecting the SNPRINTF macro per build.

On Windows it declares the variadic curlx_win32_snprintf with printf-format checking (args 3,4). For test-server builds (WITHOUT_LIBCURL), SNPRINTF is curlx_win32_snprintf on Windows else the platform snprintf. Otherwise SNPRINTF is curl_msnprintf from curl/mprintf.h. Note the inventory reports a parse error near line 1 of this file, though coverage is preserved.

**Uncertainties.**

- Reported syntax error in this header's parse; declarations were read as written but the ERROR node may hide a detail

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/strcopy.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/strerr.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curlx/basename.c
[f4]: ../../../../../../eval/curl-2c04412/lib/curlx/timeval.h
[f5]: ../../../../../../eval/curl-2c04412/lib/curlx/snprintf.h
