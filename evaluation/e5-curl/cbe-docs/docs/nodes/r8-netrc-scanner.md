# netrc Scanner and File Loading

**Capability.** Implements the netrc grammar on top of the lexer: scanner lifecycle, entry-level parsing that yields credentials for a host/user, file loading with comment skipping and caching, store init/cleanup, public lookup entry point, and error strings.

Use this subtree to trace a credential lookup end to end: file selection and buffering, tokenization, entry matching, and result/error reporting.

**Depends on.**

- [netrc Credentials](r8-netrc-credentials.md) · containment · → 2 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r8-netrc-scanner ` → ` r8-netrc-credentials `)
- [netrc Lexer](r8-netrc-lexer.md) · graph-confirmed · 8 edge(s)

Parent: [netrc Credentials](r8-netrc-credentials.md)

## Units (14)

<a id="u-8e9ca673aced"></a>
### `netrc.c-scanner-support`

`struct netrc_scanner` · [lib/netrc.c:L322-L331][f1]

Scanner state and lifecycle.

struct netrc_scanner embeds the lexer plus the lookup inputs hostname (non-NULL) and user (normalized to NULL when empty), the accumulated login/passwd strings, the resulting Curl_creds, and the matches_host/found flags. netrc_scan_init() zeroes the struct, initializes the lexer, and applies netrc_scan_reset(). netrc_scan_reset() frees login and passwd and clears matches_host; it is called between entries and at cleanup, so per-entry state never leaks into the next machine/default entry. netrc_scan_cleanup() resets, nulls hostname/user, releases the creds via Curl_creds_unlink, and cleans the lexer. All are void and cannot fail except through the frees they perform.

calls: [netrc.c-lexer-support](r8-netrc-lexer.md#u-dbed5d3def58), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

<a id="u-8e5afdcc7b7b"></a>
### `netrc.c module code (L1–L87)`

`module_region` · [lib/netrc.c:L1-L87][f1]

License, includes (pwd.h under HAVE_PWD_H with AmigaOS net-api toggles), the netrc grammar comment, size limits MAX_NETRC_LINE (16384), MAX_NETRC_FILE (128 KiB), MAX_NETRC_TOKEN (4096), and the curl2netrc macro mapping CURLcode to NETRCcode: OK when no error, OUT_OF_MEMORY for CURLE_OUT_OF_MEMORY, otherwise SYNTAX_ERROR.

<a id="u-8260c4982201"></a>
### `netrc.c module code (L571–L578)`

`module_region` · [lib/netrc.c:L571-L578][f1]

Comment block marking Curl_netrc_scan as unittest 1304 and documenting that *loginp/*passwordp must be pre-allocated when non-NULL (legacy comment; current API outputs creds).

<a id="u-549c11b7d010"></a>
### `netrc.c module code (L657–L667)`

`module_region` · [lib/netrc.c:L657-L667][f1]

Tail of Curl_netrc_scan's out path and the file's closing guard: on a non-OK result the output creds are unlinked before returning; residual scope only.

<a id="u-1827b7f9d490"></a>
### `netrc.c module code (L696–L698)`

`module_region` · [lib/netrc.c:L696-L698][f1]

Closing #endif of the CURL_DISABLE_NETRC guard.

<a id="u-0d1a64180b7c"></a>
### `file2memory`

`static NETRCcode file2memory(const char *filename, struct dynbuf *filebuf)` · [lib/netrc.c:L503-L540][f1]

Loads a netrc file into a dynbuf, skipping '#' comment lines.

It returns NETRC_FILE_MISSING if curlx_fopen fails. After resetting the buffer, if the fstat fails or the file is not a directory, it reads lines with Curl_get_line (each ends with a newline), skips lines whose first non-blank char is '#', and appends the rest via curlx_dyn_add. Any read or append error frees the accumulated buffer and returns the mapped NETRCcode, stopping the loop. When the file cannot be opened the buffer is left reset and NETRC_FILE_MISSING is returned; a directory passes the fstat check but yields no content via reads, leaving an effectively empty result.

calls: [Curl_get_line](r4-portable-utils.md#u-fc9d0cdbcdfa), [curlx_dyn_add](r3-dynbuf.md#u-b4e3d05d4a72), [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- The condition '(fstat == -1) || !S_ISDIR' means a successful fstat on a directory proceeds into reading anyway; resulting behavior relies on read failures not visible here.

<a id="u-0bfa4c544c21"></a>
### `netrc_scan`

`static NETRCcode netrc_scan(struct Curl_easy *data, const char *content, const char *…` · [lib/netrc.c:L423-L501][f1]

Tokenizes netrc content and extracts credentials for a hostname and optional user.

It first unlinks *pcreds and initializes the scanner. The main loop reads tokens with want_literal=FALSE until an error or a match: EOF, MACHINE, DEFAULT, or MACDEF each end the previous entry via netrc_scan_end_entry (returning early on error or match). Then, per token: EOF exits the loop; MACHINE reads the next token as a literal and sets matches_host from a strict curl_strequal against the hostname, pushing the token back if it is not a literal; DEFAULT sets matches_host TRUE; ACCOUNT is skipped; LOGIN and PASSWD capture literals into sc.login/sc.passwd; MACDEF skips to the next empty line; stray literals/junk are ignored. On success, the accumulated creds are linked into *pcreds, otherwise (no creds) the result is NETRC_NO_MATCH. Always cleans up the scanner.

calls: [netrc_scan_end_entry](r8-netrc-scanner.md#u-036a2869fb18), [netrc_scan_literal](r8-netrc-scanner.md#u-e9642af12efd), [Curl_creds_link](r7-credential-store.md#u-ed4d022e2a5a), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- Whether curl_strequal handles a NULL hostname depends on strequal.c, not visible; the scanner comment says hostname is non-NULL.

<a id="u-036a2869fb18"></a>
### `netrc_scan_end_entry`

`static NETRCcode netrc_scan_end_entry(struct netrc_scanner *sc)` · [lib/netrc.c:L381-L421][f1]

Finalizes the current netrc entry and decides whether it yields credentials.

Only entries whose machine matched (or a default) are considered. If a login was seen: with a requested user, entry matches only when Curl_timestrcmp says the logins are equal, and then found is set only if a password exists; without a requested user, found is set unconditionally. If no login but a password was seen, found is set (password applies to any user). Otherwise the entry is ignored. When found, Curl_creds_create builds CREDS_NETRC credentials from the requested user or the entry login plus the password; failure maps to NETRC_OUT_OF_MEMORY. Always resets per-entry state and returns the error code.

calls: [Curl_timestrcmp](r3-string-error-utils.md#u-7ed1fd4e44dd), [Curl_creds_create](r7-credential-store.md#u-ca1cf603180d)

**Uncertainties.**

- Arguments to Curl_creds_create beyond user/password (three NULLs and CREDS_NETRC) have effects defined in creds.c, not visible here.

<a id="u-2986cd9cfe4e"></a>
### `netrc_scan_file`

`static NETRCcode netrc_scan_file(struct Curl_easy *data, struct store_netrc *store, c…` · [lib/netrc.c:L542-L571][f1]

Scans one netrc file, using the store's cached content when possible.

If the store is not loaded or the path differs from the cached filename, it marks the store unloaded, loads the file via file2memory into store->filebuf, and on failure logs and returns that error. Otherwise it replaces store->filename with a strdup of the path (resetting the buffer and returning NETRC_OUT_OF_MEMORY if the strdup fails) and marks it loaded. An empty buffer yields NETRC_NO_MATCH; otherwise it runs netrc_scan over the cached content.

calls: [file2memory](r8-netrc-scanner.md#u-0d1a64180b7c), [netrc_scan](r8-netrc-scanner.md#u-0bfa4c544c21), [dynbuf.c-accessors](r3-dynbuf.md#u-5e7007dbb9e6)

<a id="u-e9642af12efd"></a>
### `netrc_scan_literal`

`static NETRCcode netrc_scan_literal(struct netrc_scanner *sc, char **pdest)` · [lib/netrc.c:L362-L379][f1]

Fetches the next token expecting a literal, by calling netrc_lexer_next with want_literal=TRUE.

On success with a NETRC_TOK_LITERAL, when a destination pointer is given and the current entry matches the host, it frees the old *pdest and stores a strdup of the literal, setting NETRC_OUT_OF_MEMORY if the strdup fails. If the token is not a literal, it pushes the token back so the caller's next next() sees it again, and returns OK without consuming. Errors from the lexer propagate unchanged. Used for login, password (stored), and account (pdest NULL, ignored).

calls: [netrc_lexer_next](r8-netrc-lexer.md#u-85c17edbdca4), [netrc.c-lexer-support](r8-netrc-lexer.md#u-dbed5d3def58)

<a id="u-3dc3931d3868"></a>
### `Curl_netrc_scan`

`NETRCcode Curl_netrc_scan(struct Curl_easy *data, struct store_netrc *store, const ch…` · [lib/netrc.c:L579-L657][f1]

Public netrc lookup: finds credentials for a host and optional user from a given file or the default location.

It unlinks *pcreds and logs the scan. If netrcfile is NULL it resolves the file: $NETRC first; else $HOME; on systems with getpwuid support it falls back to the effective uid's passwd entry, and on Windows to %USERPROFILE%. With no home directory it returns NETRC_FILE_MISSING (also covering allocation failure there). Otherwise it builds '<home>/<DIR_CHAR>.netrc' via curl_maprintf (NETRC_OUT_OF_MEMORY on failure) and scans it; on Windows, if that returns NETRC_FILE_MISSING it retries with '_netrc'. If netrcfile was given, only that file is scanned. On any error return, *pcreds is unlinked again at out.

calls: [netrc_scan_file](r8-netrc-scanner.md#u-2986cd9cfe4e), [curl_getenv](r8-netrc-credentials.md#u-88fda3b63c5f), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

**Uncertainties.**

- Which home fallback branches compile depends on HAVE_GETPWUID_R/HAVE_GETPWUID/HAVE_GETEUID/_WIN32; only one of those paths exists per build.
- The Windows _netrc fallback reuses `home`, which is only assigned inside the netrcfile==NULL branch — consistent there, but its value is undefined if reached otherwise; that path is Windows-only inside the same branch.

<a id="u-bf823372230b"></a>
### `Curl_netrc_init`

`void Curl_netrc_init(struct store_netrc *store)` · [lib/netrc.c:L668-L673][f1]

Initializes a store_netrc: initializes filebuf with the MAX_NETRC_FILE cap, clears loaded, and nulls filename.

<a id="u-3eac491fff75"></a>
### `Curl_netrc_cleanup`

`void Curl_netrc_cleanup(struct store_netrc *store)` · [lib/netrc.c:L674-L679][f1]

Releases a store_netrc: frees filebuf, frees filename, and clears loaded.

<a id="u-de4282be9d1d"></a>
### `Curl_netrc_strerror`

`const char *Curl_netrc_strerror(NETRCcode ret)` · [lib/netrc.c:L681-L696][f1]

Maps a NETRCcode to a static description string: FILE_MISSING 'no such file', NO_MATCH 'no matching entry', OUT_OF_MEMORY 'out of memory', SYNTAX_ERROR 'syntax error'; any other value, including NETRC_OK, returns an empty string.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/netrc.c
