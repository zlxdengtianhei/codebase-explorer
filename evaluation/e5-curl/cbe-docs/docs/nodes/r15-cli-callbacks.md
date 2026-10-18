# Tool libcurl callbacks

**Capability.** CURLOPT_SEEKFUNCTION and CURLOPT_OPENSOCKETFUNCTION implementations (with Linux MPTCP socket rewriting) plus the read-callback declarations header and module include residues.

These callbacks adapt tool-side file descriptors and sockets to libcurl's option interface. tool_seek_cb returns only CURL_SEEKFUNC_* codes; the MPTCP callback refuses non-rewritable opens.

Parent: [Command-line tool support](r15-tool-cli.md)

## Units (5)

<a id="u-ed2f9beb227f"></a>
### `tool-cb-see-c-module`

`group` · [src/tool_cb_see.c:L1-L35][f1]

License header and includes of tool_cb_see.c; no behavior.

<a id="u-525e929accf4"></a>
### `tool_seek_cb`

`int tool_seek_cb(void *userdata, curl_off_t offset, int whence)` · [src/tool_cb_see.c:L36-L85][f1]

CURLOPT_SEEKFUNCTION callback seeking per->infd and returning CURL_SEEKFUNC_* codes only, never the resulting offset.

On platforms where curl_off_t exceeds off_t and not Windows, offsets above the 32-bit ceiling are handled by rewinding to start and stepping forward with long-sized lseek calls (SEEK_SET only); any lseek error there returns CURL_SEEKFUNC_FAIL. Otherwise a single curl_lseek is attempted: failure returns CURL_SEEKFUNC_CANTSEEK (libcurl may try alternatives), success CURL_SEEKFUNC_OK. The errno from failure is deliberately not reported.

**Notes.**

- failure: The >32-bit path distinguishes FAIL (could not complete a supported seek) from CANTSEEK in the ordinary path, letting libcurl pick a fallback only in the latter case.

<a id="u-5f2d4fefcc1b"></a>
### `tool_cb_rea-h-declarations`

`module_region` · [src/tool_cb_rea.h:L1-L40][f2]

Header for tool_cb_rea.c: include guard, license, and prototypes for tool_read_cb (CURLOPT_READFUNCTION) and tool_readbusy_cb (progress callback); declarations only, no behavior.

<a id="u-514947ba25ef"></a>
### `tool_cb_soc-c-module-region`

`module_region` · [src/tool_cb_soc.c:L1-L36][f3]

License header, conditional netinet/in.h include for IPPROTO_TCP, and include of tool_cb_soc.h; non-behavioral.

<a id="u-5a482875bbcb"></a>
### `tool_socket_open_mptcp_cb`

`curl_socket_t tool_socket_open_mptcp_cb(void *clientp, curlsocktype purpose, struct c…` · [src/tool_cb_soc.c:L37-L57][f3]

CURLOPT_OPENSOCKETFUNCTION callback that rewrites IPPROTO_TCP sockets to MPTCP on Linux and otherwise refuses.

**Notes.**

- condition: If addr->protocol is IPPROTO_TCP: on __linux__ it substitutes IPPROTO_MPTCP (defined as 262 if missing); on other platforms it returns CURL_SOCKET_BAD so the open fails.
- side_effect: Ignores clientp and purpose; otherwise creates the socket with the address's family, socktype, and (possibly rewritten) protocol.

**Uncertainties.**

- Comment states only Linux is supported; non-Linux behavior for non-TCP protocols (pass-through to CURL_SOCKET) is code-visible but untested here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_cb_see.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_cb_rea.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_cb_soc.c
