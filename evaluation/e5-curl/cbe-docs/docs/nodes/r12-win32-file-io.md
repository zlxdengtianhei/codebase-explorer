# Windows file IO wrappers

**Capability.** UTF-8-aware Windows replacements for fopen/freopen/open/mkdir/rename/stat/seek and CreateFile/FindFirstFile, including extended-length path rewriting for paths beyond MAX_PATH.

Use these instead of raw CRT/Win32 calls so Unicode builds and long paths work. fix_excessive_path and the UTF-8-to-wide conversion are the shared foundations.

Parent: [Portable utilities](r12-portable-utils.md)

## Units (11)

<a id="u-d5970565ae02"></a>
### `curlx_CreateFile`

`HANDLE curlx_CreateFile(const char *filename, DWORD dwDesiredAccess, DWORD dwShareMod…` · [lib/curlx/win32-fopen.c:L255-L294][f1]

UTF-8-friendly CreateFile wrapper (excluded from UWP builds).

In Unicode builds it converts the filename via curlx_convert_UTF8_to_wchar and bails out returning INVALID_HANDLE_VALUE if conversion fails; in ANSI builds it uses the name directly. It passes the fix_excessive_path result if successful, otherwise the original name, to CreateFile, then frees the converted and fixed buffers. Returns the handle or INVALID_HANDLE_VALUE on any earlier failure; CreateFile's own error reporting is via GetLastError, not altered here.

calls: [fix_excessive_path](r12-win32-file-io.md#u-758a3070d85d)

<a id="u-e941bba731df"></a>
### `curlx_FindFirstFile`

`HANDLE curlx_FindFirstFile(const char *filename, WIN32_FIND_DATA *find_data)` · [lib/curlx/win32-fopen.c:L296-L325][f1]

UTF-8-friendly FindFirstFile wrapper (excluded from UWP builds) with the same pattern as curlx_CreateFile: convert the filename in Unicode builds (INVALID_HANDLE_VALUE on conversion failure), use fix_excessive_path output when available, call FindFirstFile, then free temporaries.

Find results are written to the caller's WIN32_FIND_DATA.

calls: [fix_excessive_path](r12-win32-file-io.md#u-758a3070d85d)

<a id="u-a8816ce2c01a"></a>
### `curlx_fseek`

`int curlx_fseek(void *stream, curl_off_t offset, int whence)` · [lib/curlx/win32-fopen.c:L28-L39][f1]

Portable 64-bit seek wrapper over an opaque stream.

On Windows it maps to _fseeki64; on systems with fseeko declared it maps to fseeko with an off_t cast; otherwise it rejects offsets above LONG_MAX with -1 and uses fseek with a long cast. Return and whence semantics follow the underlying function.

**Uncertainties.**

- The void* stream is cast implicitly by the platform functions; type checking happens at those call sites.

<a id="u-4567484075db"></a>
### `curlx_win32_fopen`

`FILE *curlx_win32_fopen(const char *filename, const char *mode)` · [lib/curlx/win32-fopen.c:L369-L400][f1]

_fsopen wrapper opening a file with _SH_DENYNO sharing.

Unicode builds convert both filename and mode via fn_convert_UTF8_to_wchar; if either conversion fails, errno is set to EINVAL and file stays NULL; otherwise _wfsopen opens the extended-length-capable path. ANSI builds use _fsopen directly. Temporaries are freed and the FILE* (or NULL) returned.

calls: [fn_convert_UTF8_to_wchar](r12-win32-file-io.md#u-76a6f8a4b4e8)

<a id="u-d0e0eacf3746"></a>
### `curlx_win32_freopen`

`FILE *curlx_win32_freopen(const char *filename, const char *mode, FILE *fp)` · [lib/curlx/win32-fopen.c:L407-L438][f1]

freopen wrapper reassociating an existing FILE* with a new path.

Unicode builds convert filename and mode, set errno EINVAL and return NULL if either conversion fails, and otherwise call _wfreopen_s, which reports through errno and the out FILE*. ANSI builds use freopen_s (with a declaration shim for old mingw-w64). Extended-length paths are applied via fix_excessive_path; all temporaries are freed and the FILE* result returned.

<a id="u-194f7521c9ee"></a>
### `curlx_win32_mkdir`

`int curlx_win32_mkdir(const char *path)` · [lib/curlx/win32-fopen.c:L471-L500][f1]

mkdir wrapper creating a single directory.

Unicode builds convert the path via curlx_convert_UTF8_to_wchar and set errno EINVAL / res -1 on conversion failure; otherwise _wmkdir (or _mkdir in ANSI builds) creates the extended-length-capable path. Returns 0 on success, -1 on failure, freeing the fixed path buffer either way.

<a id="u-eb13f6787f1a"></a>
### `curlx_win32_open`

`int curlx_win32_open(const char *filename, int oflag, ...)` · [lib/curlx/win32-fopen.c:L328-L367][f1]

_sopen_s wrapper accepting an optional pmode variadic argument: pmode is read from varargs only when oflag includes O_CREAT.

In Unicode builds the filename is converted with fn_convert_UTF8_to_wchar; conversion failure sets errno to EINVAL and leaves res at -1, otherwise _wsopen_s opens the (possibly extended-length) path with _SH_DENYNO and errno carries its result. ANSI builds use _sopen_s directly. The fixed path buffer is always freed and res is returned (-1 on failure).

calls: [fix_excessive_path](r12-win32-file-io.md#u-758a3070d85d)

**Uncertainties.**

- No validation that the caller actually passed pmode when O_CREAT is set; a missing argument would read garbage from varargs.

<a id="u-c2ee7fccfba4"></a>
### `curlx_win32_rename`

`int curlx_win32_rename(const char *oldpath, const char *newpath)` · [lib/curlx/win32-fopen.c:L507-L565][f1]

Renaming wrapper (compiled when HTTP, cookies, or alt-svc support is enabled) that overwrites existing targets, unlike Windows rename().

In Unicode builds both paths are converted via curlx_convert_UTF8_to_wchar; if either conversion fails the function returns -1 without attempting the move. Each path is passed through fix_excessive_path, then MoveFileEx with MOVEFILE_REPLACE_EXISTING is retried in a loop: on success res becomes 0 and the loop exits; on failure the loop retries with Sleep(1) until 1000 ms elapse or the elapsed time computes negative, then breaks with res -1. The retry tolerates transient failures when the target file has open handles. Fixed and converted buffers are freed in all paths.

calls: [fix_excessive_path](r12-win32-file-io.md#u-758a3070d85d)

**Uncertainties.**

- Whether the 1000 ms budget is wall-clock bounded under clock changes is not determinable; curlx_now is not shown.

<a id="u-2d89b0f6de4d"></a>
### `curlx_win32_stat`

`int curlx_win32_stat(const char *path, curlx_struct_stat *buffer)` · [lib/curlx/win32-fopen.c:L440-L469][f1]

stat wrapper returning _wstati64/_stati64 results for the given path.

In Unicode builds the path is converted via curlx_convert_UTF8_to_wchar, with conversion failure setting errno EINVAL and res -1; in ANSI builds the path is used directly. fix_excessive_path supplies the target path when a rewrite applies; stat output goes into the caller's buffer, res is 0 on success or -1, and temporaries are freed.

<a id="u-758a3070d85d"></a>
### `fix_excessive_path`

`static bool fix_excessive_path(const TCHAR *in, TCHAR **out)` · [lib/curlx/win32-fopen.c:L108-L252][f1]

Windows helper that rewrites paths longer than MAX_PATH into extended-length form.

It sets *out NULL and returns false if the input already starts with the \\?\ prefix. In non-Unicode builds the multibyte input is first converted to wide via mbstowcs_s; any conversion mismatch, zero length, or length at/above the 32767 approximate limit aborts via the cleanup path. GetFullPathNameW is first called with size 0 to measure the normalized full path (which collapses '..' and forward slashes); if the measured path is not longer than MAX_PATH, no rewrite is needed and the function returns false. Otherwise the full path is materialized and prefixed: existing \\?\ is kept, \\.\ becomes \\?\, a \\. or \\? prefix that is not the expected form aborts, UNC paths (\\server\...) become \\?\UNC\<path minus leading \\>, and ordinary drive paths get \\?\ prepended; intermediate size overflows above 32767 or wide-string copy failures free temporaries and abort. In non-Unicode builds the result is converted back to multibyte (failing if characters are not representable in the current codepage); on success *out owns the buffer and true is returned, otherwise false with all temporaries freed.

uses: [curlx_CreateFile](r12-win32-file-io.md#u-d5970565ae02)

**Uncertainties.**

- Which Windows APIs can return the unexpected '\\\\.' or '\\\\?' prefixes is undocumented here; that branch unconditionally fails.

<a id="u-76a6f8a4b4e8"></a>
### `fn_convert_UTF8_to_wchar`

`static wchar_t *fn_convert_UTF8_to_wchar(const char *str_utf8)` · [lib/curlx/win32-fopen.c:L62-L81][f1]

Unicode-build helper converting a UTF-8 string to a heap-allocated wide string.

Returns NULL for a NULL input, when MultiByteToWideChar's size query fails or returns non-positive, when the sized allocation fails, or when the second conversion call returns 0 (invalid UTF-8, due to MB_ERR_INVALID_CHARS), freeing the buffer in that case. Allocation uses malloc/free under CURL_MEMDEBUG to avoid recursion in the memory tracker, otherwise curlx_malloc/curlx_free.

**Uncertainties.**

- Defined only under _UNICODE; behavior in ANSI builds is not applicable.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/win32-fopen.c
