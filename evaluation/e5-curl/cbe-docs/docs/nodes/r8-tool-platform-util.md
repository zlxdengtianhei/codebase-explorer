# Tool Platform Utilities

**Capability.** Small platform-dependent tool helpers: real wall-clock time (Windows vs POSIX), file truncation variants (Win32, DJGPP), executable-relative resource lookup on Windows, and NULL-tolerant case-insensitive comparison with a qsort adapter.

Consult this subtree when adjusting platform-specific tool behavior for time, truncation, or resource files.

Parent: [Command-Line Tool Output](r8-tooling.md)

## Units (7)

<a id="u-5c50ce1c44a3"></a>
### `tvrealnow`

`struct timeval tvrealnow(void)` · [src/tool_util.c:L30-L47][f1]

Windows implementation returning the real wall-clock time as a struct timeval.

It converts the 1601-epoch FILETIME to Unix-epoch seconds (dividing 100ns ticks by 10,000,000 after subtracting the epoch constant) and derives microseconds from SYSTEMTIME's millisecond field.

uses: [tool_debug_cb](r14-tool-help-debug.md#u-49b6875acbdc)

**Uncertainties.**

- Sub-second precision is limited to milliseconds because it comes from wMilliseconds

<a id="u-7b70dad74fc0"></a>
### `src/tool_util.c:tvrealnow`

`struct timeval tvrealnow(void)` · [src/tool_util.c:L51-L61][f1]

Non-Windows implementation returning the real wall-clock time as a struct timeval via gettimeofday when available, otherwise seconds from time(NULL) with tv_usec zero.

<a id="u-9be3d6473308"></a>
### `toolx_ftruncate_win32`

`int toolx_ftruncate_win32(int fd, curl_off_t where)` · [src/tool_util.c:L85-L96][f1]

Truncates a file descriptor at a 64-bit offset on Windows (non-MinGW): seeks to the position and calls SetEndOfFile on the descriptor's OS handle.

Returns -1 if the seek fails or SetEndOfFile fails, 0 on success.

<a id="u-5b9ef93bea11"></a>
### `toolx_ftruncate_djgpp`

`int toolx_ftruncate_djgpp(int fd, curl_off_t where)` · [src/tool_util.c:L101-L107][f1]

DJGPP truncation limited to 32-bit sizes: returns -1 when the requested offset exceeds INT_MAX, otherwise delegates to ftruncate with an off_t cast.

<a id="u-d378156bcc98"></a>
### `tool_execpath`

`FILE *tool_execpath(const char *filename, char **pathp)` · [src/tool_util.c:L111-L156][f1]

Locates a resource file next to the running executable on Windows, returning an open read handle and setting *pathp to the built path.

It fetches the executable path via GetModuleFileName into a static 512-byte buffer (converting to UTF-8 under UNICODE, failing if the converted name does not fit), truncates at the last directory separator, and if the requested filename fits in the remaining space, appends DIR_CHAR plus the filename and opens it with curlx_fopen. It returns NULL when the executable path is unavailable or too long, no separator exists, the filename does not fit, or conversion fails.

**Notes.**

- side_effect: *pathp points into a static buffer, so the path is invalidated by subsequent calls.

**Uncertainties.**

- The exact required slack (strlen(filename) < remaining - 1) leaves the last byte unused; off-by-one intent is not documented

<a id="u-39e2c0a242e2"></a>
### `struplocompare`

`int struplocompare(const char *p1, const char *p2)` · [src/tool_util.c:L66-L73][f1]

Case-insensitive string comparison that accepts NULL pointers: a NULL first argument sorts before a non-NULL second (-1) and equals NULL (0); a non-NULL first against NULL second returns 1; otherwise CURL_STRICMP compares the strings.

uses: [struplocompare4sort](r8-tool-platform-util.md#u-cfd6cc504a98)

<a id="u-cfd6cc504a98"></a>
### `struplocompare4sort`

`int struplocompare4sort(const void *p1, const void *p2)` · [src/tool_util.c:L76-L79][f1]

qsort adapter that dereferences two char* pointers and applies struplocompare to them.

calls: [struplocompare](r8-tool-platform-util.md#u-39e2c0a242e2)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_util.c
