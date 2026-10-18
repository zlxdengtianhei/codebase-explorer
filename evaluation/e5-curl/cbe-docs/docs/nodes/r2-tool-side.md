# Tool-Side Diagnostics & Config

**Capability.** Command-line tool support: build-time feature reporting, terminal width detection, socket-callback declarations, clobber-retry constants, and converting tool config into libcurl options.

Use this subtree for the curl tool executable's small standalone helpers and its bridge to libcurl option setting. These are separate from the library core and depend on it, not vice versa.

**Depends on.**

- [Setopt Dispatch & Storage](r2-setopt-core.md) · model-inferred · 0 edge(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Units (6)

<a id="u-e9686c7384df"></a>
### `config2setopts.h module code (L1–L32)`

`module_region` · [src/config2setopts.h:L1-L32][f1]

Header guard and declaration of config2setopts, which converts parsed OperationConfig state into libcurl options on a per-transfer handle given the easy handle and share object.

Implementation is outside this file.

<a id="u-7f3ae59d17c5"></a>
### `main`

`int main(void)` · [src/curlinfo.c:L281-L289][f2]

Prints each entry of the compile-time feature table, one per line, and returns 0.

Loops over the static `disabled` array with puts(), so output goes to stdout and each label is followed by a newline. No arguments are read and no failure path exists in the visible code; the function always returns 0 after printing all entries.

uses: [curlinfo.c module code (L1–L280)](r2-tool-side.md#u-ed58b0d9347e)

<a id="u-ed58b0d9347e"></a>
### `curlinfo.c module code (L1–L280)`

`module_region` · [src/curlinfo.c:L1-L280][f2]

Builds a compile-time table reporting which optional curl features are enabled or disabled at build time, for a diagnostic tool run as its own executable.

The static array `disabled` holds one labeled string per feature; each label is assembled by preprocessor conditionals so that the string literal is "OFF" when the disabling macro (e.g. CURL_DISABLE_COOKIES, USE_RESOLV_THREADED, ENABLE_WAKEUP, SIZEOF_TIME_T < 5) is in effect and "ON" otherwise. A few entries invert the polarity: "override-dns", "ssl-sessions", "cert-status", and "getrlimit" print "ON" when their enabling macros (CURL_MEMDEBUG plus an alternate resolver, USE_SSLS_EXPORT, GnuTLS or OpenSSL without OPENSSL_NO_OCSP, HAVE_GETRLIMIT) are defined. The win32 CA entries depend on _WIN32 and CURL_CA_SEARCH_SAFE/CURL_WINDOWS_UWP combinations. The file comment notes this exists because disabled protocols are already visible via curl_version_info(); these features are not.

**Uncertainties.**

- The tree has a syntax ERROR near line 1, so the exact spellability of every conditional literal is not machine-verified, though the source text is readable.

<a id="u-2a27008140f3"></a>
### `get_terminal_columns`

`unsigned int get_terminal_columns(void)` · [src/terminal.c:L42-L90][f3]

Returns the width in columns of the current terminal, falling back to 79 when the width cannot be determined.

It first reads the COLUMNS environment variable via curl_getenv; if present, curlx_str_number parses it with a 10000 cap, and the value is accepted only when parsing succeeds and the number exceeds 20, otherwise width stays 0. The environment string is always freed with curl_free in that branch. If width is still 0, platform probes run: with TIOCGSIZE a single ioctl on stdin fills a ttysize; with TIOCGWINSZ ioctls try stdin, then stdout, then stderr in order, taking the first success; on non-UWP Windows, GetStdHandle(STD_ERROR_HANDLE) plus GetConsoleScreenBufferInfo yields the window width without the +1 that would cause wrapping. Any probe result in [0,10000) becomes the width; note that a successful probe reporting 0 columns is discarded. If everything fails, width defaults to 79. A single return value covers all paths; allocation failure or ioctl errors are silently absorbed into the fallback.

**Notes.**

- failure: All detection failures (missing COLUMNS, unparseable value, ioctl errors, missing console handle) degrade silently to 79 with no error reporting.
- condition: The environment value is accepted only if it parses as a number under the 10000 cap and is greater than 20; the ioctl path accepts 0..9999, so 0..20 from the environment is rejected while 0 from ioctl is rejected only by the cols >= 0 test passing (0 is accepted).

calls: [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16), [curl_free](r7-string-escape-utils.md#u-1328a1020607); uses: [update_width](r5-tool-callbacks.md#u-dc6786ac6e98)

**Uncertainties.**

- Behavior when COLUMNS parses to a value above the 10000 cap depends on curlx_str_number semantics (error vs truncation), which is outside this file.
- Whether struct ttysize/winsize ioctls can succeed on non-tty descriptors is not established here.

<a id="u-e3df7316b763"></a>
### `tool_cb_soc-h-declarations`

`module_region` · [src/tool_cb_soc.h:L1-L35][f4]

Header for tool_cb_soc.c: include guard, license, and the prototype for tool_socket_open_mptcp_cb; declarations only, no behavior.

<a id="u-f1b2ccfbaa0f"></a>
### `tool_cb_wrt-c-module`

`module_region`

Module-level definitions of tool_cb_wrt.c: Windows/non-Windows OPENMODE file-permission macros and MAX_CLOBBER_ATTEMPTS (9999) limiting the CLOBBER_NEVER retry loop; also includes tool_cb_wrt.h declarations already covered by their definitions.

**Notes.**

- field: OPENMODE grants user/group/other read+write on POSIX and _S_IREAD|_S_IWRITE on Windows; used only by the O_EXCL open path.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/config2setopts.h
[f2]: ../../../../../../eval/curl-2c04412/src/curlinfo.c
[f3]: ../../../../../../eval/curl-2c04412/src/terminal.c
[f4]: ../../../../../../eval/curl-2c04412/src/tool_cb_soc.h
