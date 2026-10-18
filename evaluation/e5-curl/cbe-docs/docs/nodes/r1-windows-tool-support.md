# Windows/DOS Tool Support

**Capability.** Owns the platform-specific tool behaviors: DOS-safe filename sanitizing, CA-bundle lookup via SearchPath, VT terminal setup/restore with a signal-safe once-flag, and the stdin relay that replaces redirected stdin with a background-thread-fed socket pair.

Read this for Windows-only tool mechanics. sanitize_file_name composes msdosify and rename_if_reserved_dos; win32_stdin_read_thread plus win_stdin_thread_func implement the stdin relay with its cleanup and read helpers.

**Depends on.**

- [Tool Operation Configuration](r1-tool-operation-config.md) · model-inferred · 0 edge(s)

Parent: [curl Command-Line Tool](r1-curl-tool.md)

## Units (17)

<a id="u-5b92e9e3e094"></a>
### `FindWin32CACert`

`CURLcode FindWin32CACert(struct OperationConfig *config, const TCHAR *bundle_file)` · [src/tool_doswin.c:L585-L604][f1]

Searches the Windows SearchPath order (application dir, CWD, system dirs, %PATH%) for a CA bundle and stores its UTF-8 path in config->cacert, freeing any previous value.

If SearchPath finds nothing, config->cacert is untouched and CURLE_OK is returned; converting the found TCHAR path to UTF-8 failing yields CURLE_OUT_OF_MEMORY. Intended to be skipped when Schannel is the SSL backend and the user set an explicit CA location.

contract: [tool_doswin.h module code (L1–L58)][f2]

**Uncertainties.**

- Whether callers guarantee config is non-NULL is not visible here

<a id="u-dd9a0b321d72"></a>
### `GetLoadedModulePaths`

`struct curl_slist *GetLoadedModulePaths(void)` · [src/tool_doswin.c:L610-L660][f1]

Returns a curl_slist of full paths of all modules loaded in the current process, or NULL on error.

Builds a toolhelp32 module snapshot, retrying CreateToolhelp32Snapshot while it fails with ERROR_BAD_LENGTH. Iterates Module32First/Module32Next, converting wide paths to multibyte under UNICODE, appending each via curl_slist_append. Any snapshot, iteration, conversion, or append failure frees the accumulated list, closes the handle, and returns NULL; on success the snapshot handle is still closed. Under CURL_WINDOWS_UWP the function returns NULL unconditionally.

contract: [tool_doswin.h module code (L1–L58)][f2]

**Uncertainties.**

- Whether curl_slist_append failure can leave a partially appended node is not established from this source

<a id="u-793b73f20f9f"></a>
### `__crt0_glob_function`

`char **__crt0_glob_function(char *arg)` · [src/tool_doswin.c:L65-L69][f1]

Disables DJGPP's default argument globbing by returning a NULL glob result for any argument.

<a id="u-7192a509550b"></a>
### `cleanup_tdata_sync`

`static void cleanup_tdata_sync(void)` · [src/tool_doswin.c:L747-L760][f1]

Under the stdin-relay critical section, closes the duplicated original stdin handle and the relay write socket, nulling/bad-ing both so repeated calls are safe.

Used both by the stdin thread at exit and via atexit on the success path of win32_stdin_read_thread.

uses: [win32_stdin_read_thread](r1-windows-tool-support.md#u-e809306d7d74); calls: [win_stdin_thread_func](r1-windows-tool-support.md#u-7f8cadf8d267)

<a id="u-9ebdd8054bb2"></a>
### `init_terminal`

`static void init_terminal(void)` · [src/tool_doswin.c:L693-L730][f1]

Enables virtual-terminal (VT) output processing on stdout and records whether ANSI bold is available in the global tool_term_has_bold.

It returns early, changing nothing, if the stdout handle is invalid, GetConsoleMode fails, or the OS is older than Windows 10 build 16299. If VT processing is already enabled it only sets tool_term_has_bold. Otherwise it marks the settings valid, installs signal_handler first (so an interrupt during the mode change is caught), then attempts SetConsoleMode with ENABLE_VIRTUAL_TERMINAL_PROCESSING: on success tool_term_has_bold is set and restore_terminal is registered via atexit; on failure the handler is removed and the valid flag reset.

**Notes.**

- side_effect: Sets globals TerminalSettings and tool_term_has_bold; installs an atexit hook and a console control handler.

calls: [signal_handler](r1-windows-tool-support.md#u-f80d24e06562), [restore_terminal](r1-windows-tool-support.md#u-aae13d4a8d90)

<a id="u-9d7a1c1db9c7"></a>
### `msdosify`

`static SANITIZEcode msdosify(char ** const sanitized, const char *file_name, int flags)` · [src/tool_doswin.c:L142-L272][f1]

Rewrites a filename into an MS-DOS-legal form, replacing illegal characters with underscores; a supporting helper for sanitize_file_name.

On failure *sanitized is NULL; on success it points to a heap copy. Returns SANITIZE_ERR_BAD_ARGUMENT for NULL sanitized or file_name, SANITIZE_ERR_INVALID_PATH when the name exceeds PATH_MAX-1. When long filenames are available (CURL_USE_LFN), only the Windows 95 illegal set applies. A leading drive letter is kept, with the colon replaced by '_' unless SANITIZE_ALLOW_PATH. Colons and separators pass through verbatim under SANITIZE_ALLOW_PATH; leading './' and '../' are copied verbatim; a leading dot becomes '_', a second dot either replaces the first (heuristic when the first dot is before index 5) or becomes '-'; trailing '++' after an extension becomes 'xx', otherwise '++' becomes 'plus' (or 'xx' near the buffer limit). If the buffer overflows, truncation is validated via truncate_dryrun and no residual separator/colon may remain, else SANITIZE_ERR_INVALID_PATH. Final allocation failure yields SANITIZE_ERR_OUT_OF_MEMORY.

**Notes.**

- side_effect: Allocates the returned string with curlx_strdup; the caller owns it.

calls: [truncate_dryrun](r1-windows-tool-support.md#u-d0460edd2842); contract: [tool_doswin.h module code (L1–L58)][f2]

**Uncertainties.**

- The dot heuristic (dot_idx < 5) behavior for pathological inputs relies on the in-code comment, not on tests

<a id="u-1bff0f2d7adc"></a>
### `prefix_reserved`

`static int prefix_reserved(const char *p)` · [src/tool_doswin.c:L276-L307][f1]

Returns the byte length of a reserved DOS device-name prefix at the start of p, or zero if none.

COM/LPT followed by digit 1-9 count 4 bytes; COM/LPT followed by a UTF-8 or ISO-8859-1 superscript 1/2/3 counts the prefix plus the superscript encoding (3 bytes for ISO-8859-1, 4 when a 0xc2 UTF-8 lead byte precedes); other COM/LPT forms return 0. CON, PRN, AUX, NUL return 3; CLOCK$ returns 6.

**Notes.**

- condition: A zero return means the name is not treated as reserved; it does not mean p is empty.

uses: [rename_if_reserved_dos](r1-windows-tool-support.md#u-d5c32df798ca)

<a id="u-55b791eb15c9"></a>
### `read_auth_val`

`static int read_auth_val(curl_socket_t sock, uint64_t* auth_val_ptr)` · [src/tool_doswin.c:L853-L872][f1]

Reads a full 64-bit authentication value from a socket in a loop over partial reads.

A zero read (peer disconnect) or a negative read (socket error) logs the respective message and returns -1; otherwise it fills *auth_val_ptr and returns 0.

calls: [win32_stdin_read_thread](r1-windows-tool-support.md#u-e809306d7d74)

<a id="u-d5c32df798ca"></a>
### `rename_if_reserved_dos`

`static SANITIZEcode rename_if_reserved_dos(char ** const sanitized, const char *file_…` · [src/tool_doswin.c:L322-L435][f1]

Renames a path whose components are reserved DOS device names by prepending an underscore; a supporting helper for sanitize_file_name.

Returns SANITIZE_ERR_BAD_ARGUMENT for NULL arguments and SANITIZE_ERR_OUT_OF_MEMORY on allocation failure; *sanitized is NULL on failure. Under SANITIZE_ALLOW_PATH, '\\'-prefixed paths are passed through unchanged (non-MSDOS builds only). The name is copied into a buffer with two spare bytes; curlx_basename locates the basename. The loop inspects the full path and then the basename, using prefix_reserved: a reserved prefix followed by spaces then '.' replaces the dot with '_'; a ':' replaces it with '_' unless SANITIZE_ALLOW_PATH (then the colon is kept and scanning continues into the ADS suffix); any other non-terminator character ends that candidate. For a bare reserved name, an '_' is prepended with memmove and the basename pointer is recomputed since the path expanded. On MSDOS only, if the basename stats as a character device, an '_' is likewise prepended, returning SANITIZE_ERR_INVALID_PATH if the buffer lacks room.

**Notes.**

- failure: The two spare buffer bytes exist specifically to absorb one prepended underscore; overflow is only handled on the MSDOS stat path.

calls: [prefix_reserved](r1-windows-tool-support.md#u-1bff0f2d7adc); contract: [tool_doswin.h module code (L1–L58)][f2]

**Uncertainties.**

- The stat-based device check is compiled only under MSDOS; its behavior on Windows builds is not observable here

<a id="u-aae13d4a8d90"></a>
### `restore_terminal`

`static void restore_terminal(void)` · [src/tool_doswin.c:L677-L681][f1]

Restores the saved console output mode exactly once, using an interlocked flag exchange so concurrent callers (e.g. signal handler and atexit) cannot restore twice.

uses: [init_terminal](r1-windows-tool-support.md#u-9ebdd8054bb2)

<a id="u-3a896b768061"></a>
### `sanitize_file_name`

`SANITIZEcode sanitize_file_name(char ** const sanitized, const char *file_name, int f…` · [src/tool_doswin.c:L466-L560][f1]

Sanitizes a file or path name for DOS/Windows filesystems, returning a heap copy via *sanitized.

NULL arguments give SANITIZE_ERR_BAD_ARGUMENT; allocation failure SANITIZE_ERR_OUT_OF_MEMORY; *sanitized is NULL on any failure. Control characters (1-31), and—unless SANITIZE_ALLOW_PATH—colons and path separators become '_'; the banned set |<>"?* always becomes '_'. Without SANITIZE_ALLOW_PATH, trailing spaces and periods are clipped to the first non-space/non-period character. On MSDOS, msdosify then applies legacy DOS rules; unless SANITIZE_ALLOW_RESERVED, rename_if_reserved_dos prepends underscores to reserved device names (a '\\?\' literal prefix is skipped from character replacement when paths are allowed). Each stage frees the previous buffer and propagates its error code. In DEBUGBUILD, the environment variables CURL_FN_SANITIZE_BAD and CURL_FN_SANITIZE_OOM force the corresponding error returns for testing.

**Notes.**

- condition: Fully blocking reserved device names requires passing neither flag; \\?\-prefixed and \\ prefixed paths still admit reserved names under SANITIZE_ALLOW_PATH.

calls: [msdosify](r1-windows-tool-support.md#u-9d7a1c1db9c7), [rename_if_reserved_dos](r1-windows-tool-support.md#u-d5c32df798ca)

**Uncertainties.**

- Ordering of trailing-period clipping versus msdosify on MSDOS may interact, but no combined-case behavior is provable from this file alone

<a id="u-f80d24e06562"></a>
### `signal_handler`

`static BOOL WINAPI signal_handler(DWORD type)` · [src/tool_doswin.c:L686-L691][f1]

Console control handler invoked by the system in a separate thread: restores the terminal on CTRL_C_EVENT or CTRL_BREAK_EVENT and always returns FALSE so default processing continues.

calls: [restore_terminal](r1-windows-tool-support.md#u-aae13d4a8d90)

<a id="u-ea70eb0930bd"></a>
### `swrite_blocking_on_nonblock`

`static int swrite_blocking_on_nonblock(curl_socket_t nonblock_sock, const unsigned ch…` · [src/tool_doswin.c:L806-L851][f1]

Writes nbytes to a non-blocking socket, blocking until completion via select.

Each iteration selects on writability and exception; select returning <= 0 logs a select error and returns -1; an exception set reports the SO_ERROR connect failure and returns -1; swrite returning <= 0 continues on EAGAIN-style errors, otherwise logs and returns -1. Partial writes are accumulated until all bytes are sent, then 0 is returned.

<a id="u-d0460edd2842"></a>
### `truncate_dryrun`

`static SANITIZEcode truncate_dryrun(const char *path, const size_t truncate_pos)` · [src/tool_doswin.c:L97-L127][f1]

Checks whether truncating a path at a byte position leaves a usable filename, without modifying anything.

Returns SANITIZE_ERR_BAD_ARGUMENT when path is NULL or truncate_pos exceeds the length; SANITIZE_ERR_INVALID_PATH when the path is empty, the position is zero, the remainder starting at truncate_pos-1 contains a path separator or colon, or a colon exists earlier in the last path segment (alternate data streams like C:\foo:ads cannot be truncated). Only SANITIZE_ERR_OK means truncation is safe.

**Notes.**

- contract: Any result other than SANITIZE_ERR_OK or SANITIZE_ERR_INVALID_PATH signals an error, per the documented return convention.

<a id="u-7746e4263c70"></a>
### `win32_init`

`CURLcode win32_init(void)` · [src/tool_doswin.c:L1043-L1052][f1]

One-time Windows tool initialization: initializes Windows-version and time helpers, then enables VT terminal handling on non-UWP builds.

Always returns CURLE_OK.

calls: [init_terminal](r1-windows-tool-support.md#u-9ebdd8054bb2)

<a id="u-e809306d7d74"></a>
### `win32_stdin_read_thread`

`curl_socket_t win32_stdin_read_thread(void)` · [src/tool_doswin.c:L875-L1038][f1]

Replaces the process stdin with a loopback socket pair fed by a background thread, returning the readable end (or CURL_SOCKET_BAD on any failure).

Idempotent: a static socket_r is returned if already set. The setup sequence creates a critical section, a loopback TCP listener bound to any port, a non-blocking connector socket, and accepts the writer end used by the thread; the listener is closed after accept. The peers authenticate by exchanging a random 64-bit value (sent with swrite_blocking_on_nonblock, verified with read_auth_val); mismatch, random-generation, DuplicateHandle, SetStdHandle, or CreateThread failure aborts setup. On success, stdin is redirected to the socket, the original stdin duplicated into tdata, the thread is started and its handle released, and cleanup_tdata_sync is registered via atexit. On any earlier failure, stdin is restored if already switched, all sockets and tdata are torn down, the critical section is deleted, and CURL_SOCKET_BAD is returned; this path relies on the thread not yet running to avoid TOCTOU races.

**Notes.**

- side_effect: After success, all reads from stdin or fd 0 come from the socket; global tdata and static socket_r persist for process lifetime.
- failure: Failure cleanup restores the original stdin handle when it was already redirected.

calls: [swrite_blocking_on_nonblock](r1-windows-tool-support.md#u-ea70eb0930bd), [read_auth_val](r1-windows-tool-support.md#u-55b791eb15c9), [win_stdin_thread_func](r1-windows-tool-support.md#u-7f8cadf8d267), [cleanup_tdata_sync](r1-windows-tool-support.md#u-7192a509550b); uses: [win_thread_data][f1]

**Uncertainties.**

- Behavior if connect() returns EAGAIN (in-progress) is tolerated rather than completed explicitly; completion is assumed before accept

<a id="u-7f8cadf8d267"></a>
### `win_stdin_thread_func`

`static DWORD WINAPI win_stdin_thread_func(void *thread_data)` · [src/tool_doswin.c:L762-L804][f1]

Background thread body that pumps the true (pre-redirection) stdin handle into the relay socket.

It loops reading BUFSIZ chunks with ReadFile and stops on read failure (e.g. ERROR_BROKEN_PIPE on a closed pipe), a zero-byte read (mingw end-of-data), a swrite failure, or a partial write. It then shuts the write side down so a FIN is sent after all data is acknowledged, and drains the socket with sread until close or error (the peer may take up to ~2 minutes to answer the FIN) before cleaning up tdata under its critical section.

**Notes.**

- failure: The thread exits on end-of-input or any write/read anomaly; there is no restart mechanism.

calls: [cleanup_tdata_sync](r1-windows-tool-support.md#u-7192a509550b); uses: [win_thread_data][f1]

**Uncertainties.**

- Exact shutdown/recv interplay timing on different shells is described only via code comments

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_doswin.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_doswin.h
