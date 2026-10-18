# Windows API helpers

**Capability.** Windows-only helpers: rendering API error codes into message buffers while preserving GetLastError/errno, and filling a buffer with CNG random bytes.

Use these when reporting Win32 errors or needing entropy on Windows; both are isolated from the rest of the library.

Parent: [Portable utilities and platform shims](r4-portable-utils.md)

## Units (3)

<a id="u-00f29fa5f988"></a>
### `curlx_get_winapi_error`

`const char *curlx_get_winapi_error(DWORD err, char *buf, size_t buflen)` · [lib/curlx/winapi.c:L39-L66][f1]

Converts a Windows API error code (GetLastError-style) into a message in a caller buffer, returning the buffer pointer or NULL when no message exists.

A zero buflen returns NULL immediately. It calls FormatMessageA with FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS and LANG_NEUTRAL, producing local-codepage text suitable for terminal output; on failure it writes '\0' at buf and returns NULL. On success it truncates the message at the first newline, removing a preceding '\r' if present, then returns buf if non-empty, else NULL.

**Uncertainties.**

- FormatMessageA failure conditions beyond a zero-length result follow the Windows API, not this source.

<a id="u-af95bbff470d"></a>
### `curlx_win32_random`

`CURLcode curlx_win32_random(unsigned char *entropy, size_t length)` · [lib/curlx/winapi.c:L114-L123][f1]

Fills entropy with length random bytes using the Windows CNG API.

It first memsets the buffer to zero, then calls BCryptGenRandom with BCRYPT_USE_SYSTEM_PREFERRED_RNG; any status other than STATUS_SUCCESS returns CURLE_FAILED_INIT, otherwise CURLE_OK. Available only when built for Windows and not WITHOUT_LIBCURL.

**Uncertainties.**

- Whether BCryptGenRandom can leave the buffer partially written on failure is a property of the Windows API, not shown here; the function itself leaves the zeroed content in that case.

<a id="u-8a9de7ec9ae8"></a>
### `curlx_winapi_strerror`

`const char *curlx_winapi_strerror(DWORD err, char *buf, size_t buflen)` · [lib/curlx/winapi.c:L68-L105][f1]

Produces an error string for a Windows API error code in buf, preserving the caller's GetLastError and errno values.

With zero buflen it returns NULL without touching buf; otherwise it clears buf first. Under CURLVERBOSE it fills buf via curlx_get_winapi_error, falling back to SNPRINTF 'Unknown error %lu (0x%08lx)' when that returns NULL (with a GCC format-truncation warning suppressed around the fallback). Without CURLVERBOSE it writes only 'No error' for ERROR_SUCCESS and 'Error' otherwise via curlx_strcopy. It then restores errno if a call changed it and SetLastError if the saved last error changed, and always returns buf (never NULL except for the buflen==0 case).

calls: [curlx_get_winapi_error](r4-windows-helpers.md#u-00f29fa5f988)

**Uncertainties.**

- The exact message content differs between CURLVERBOSE and non-CURLVERBOSE builds; which is compiled is decided outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/winapi.c
