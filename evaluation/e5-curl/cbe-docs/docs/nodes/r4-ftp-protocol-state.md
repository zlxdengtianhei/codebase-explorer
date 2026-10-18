# FTP state and wildcard interface

**Capability.** Declares FTP's easy-scoped and connection-scoped state records and the FTP directory-listing parser and wildcard-download interface, including the wildcard lifecycle enum and WildcardData record.

Read these headers to understand how FTP state is attached via connection/easy metadata and how wildcard downloads track pattern, matched files and lifecycle state.

Parent: [Protocol module interfaces](r4-protocol-interfaces.md)

## Units (7)

<a id="u-832049bb4d14"></a>
### `ftplistparser-h-ftp-parser-and-wildcard-interface`

`enum` · [lib/ftplistparser.h:L46-L57][f1]

Declares the FTP directory-listing parser and wildcard-download interface.

When FTP is enabled it exposes four functions: Curl_ftp_listmode reports whether a transfer is in wildcard listing mode; Curl_ftp_parselist is the WRITEFUNCTION callback that consumes LIST response bytes and has external linkage but an implementation not visible here; Curl_ftp_parselist_geterror converts parser state into a CURLcode; and data_alloc/data_free manage the opaque struct ftp_parselist_data, which is defined only in the .c file, so callers hold it solely by pointer. The wildcard_states enum enumerates the wildcard process lifecycle from CURLWC_CLEAR/INIT through MATCHING, DOWNLOADING, CLEAN, SKIP, ERROR, to DONE, where DONE ends the wildcard loop; these states feed the unsigned char state field of WildcardData. WildcardData itself aggregates the match directory path, the pattern, a Curl_llist filelist of Curl_fileinfo entries, an ftpwc pointer to FTP-specific wildcard data, and a wildcard_dtor function-pointer for releasing custom payloads; Curl_wildcard_init and Curl_wildcard_dtor construct and tear down that struct, the latter taking a double pointer so it can clear the caller's handle. When CURL_DISABLE_FTP is defined the whole surface collapses to macros: Curl_ftp_listmode expands to FALSE, Curl_ftp_parselist to ZERO_NULL, and Curl_wildcard_dtor to nothing, letting call sites compile without the FTP machinery; notably Curl_ftp_parselist_geterror and the alloc/free functions have no disabled-mode replacements, so their use under the disable flag is unguarded here.

group: [lib/ftplistparser.h:<enum>](r4-ftp-protocol-state.md#u-f97497d2af73), [WildcardData](r4-ftp-protocol-state.md#u-0a1d5b6fa44c)

**Uncertainties.**

- Behavior of Curl_ftp_parselist and Curl_ftp_parselist_geterror is declared here only; their implementations are not in the supplied source, so error-conversion semantics are inferred from naming alone.
- Why no disabled-mode stubs exist for Curl_ftp_parselist_getfile/data_alloc/data_free is unexplained by the visible #else block.

<a id="u-135378d3ef0a"></a>
### `FTP`

`struct FTP` · [lib/ftp-int.h:L88-L96][f2]

Easy-handle-scoped FTP data stored under the CURL_META_FTP_EASY meta key.

It is deliberately separated from struct ftp_conn because the Curl_easy may change between uses of a connection. It holds the request path (path pointing into urlpieces, or pathalloc when an allocated copy is needed), the transfer mode as a curl_pp_transfer enum (BODY/INFO/NONE) so debuggers show symbols, and downloadsize.

<a id="u-deb42011ad32"></a>
### `ftp_conn`

`struct ftp_conn` · [lib/ftp-int.h:L106-L146][f2]

Connection-scoped FTP state embedded in the connection via connection metadata (key CURL_META_FTP_CONN).

It embeds the pingpong struct, protocol strings (account, alternative_to_user, entrypath, rawpath, prevpath, server_os), a dirs array of pathcomp entries with dirdepth/cwdcount bounds (< FTP_MAX_DIR_DEPTH), general-purpose counters count1..3 used by the state machine, and flags controlling behavior: dont_check skips the final size/226-250 check, ctl_valid gates QUIT, cwddone/cwdfail govern current-directory caching, wait_data_conn and shutdown track data-connection and QUIT phases. state holds an ftpstate enum value; the comment requires changes only through ftp.c's state() helper. transfertype feeds Curl_client_write. All of this is pure data; behavior lives in ftp.c and pingpong.c.

**Uncertainties.**

- FTP_MAX_DIR_DEPTH and the state() accessor are defined outside this header, so their exact enforcement is not visible here.

<a id="u-f97497d2af73"></a>
### `lib/ftplistparser.h:<enum>`

`enum` · [lib/ftplistparser.h:L46-L57][f1]

The wildcard_states enum listing the wildcard process lifecycle; values are consumed by WildcardData.state.

<a id="u-02bab5654d0b"></a>
### `ftplistparser.h module code (L1–L46)`

`module_region` · [lib/ftplistparser.h:L1-L46][f1]

Header guard and license block for the FTP LIST/WILDCARD parser interface; includes curl_setup.h and declares nothing beyond what later regions hold.

<a id="u-f65a8d940afc"></a>
### `ftplistparser.h module code (L69–L82)`

`module_region` · [lib/ftplistparser.h:L69-L82][f1]

Closing include guard plus the CURL_DISABLE_FTP macro fallbacks; behavioral only as preprocessor substitutions.

<a id="u-0a1d5b6fa44c"></a>
### `WildcardData`

`struct WildcardData` · [lib/ftplistparser.h:L62-L69][f1]

struct WildcardData keeps information about a wildcard download process: path, pattern, a linked list of matched files, FTP-specific data, a destructor callback, and the current lifecycle state.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ftplistparser.h
[f2]: ../../../../../../eval/curl-2c04412/lib/ftp-int.h
