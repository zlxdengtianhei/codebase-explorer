# AmigaOS support

**Capability.** Opens and releases the Amiga bsdsocket library, provides an AmiSSL-aware select wrapper that re-raises SIGINT, and replaces the generic IPv4 resolver on AmigaOS 4.

Read for Amiga startup/teardown and resolver behavior; the resolver override interacts bidirectionally with the sync IPv4 resolver in the name-resolution branch.

**Depends on.**

- [Synchronous IPv4 resolver](r12-sync-ipv4-resolver.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Synchronous IPv4 resolver](r12-sync-ipv4-resolver.md) · graph-confirmed · 1 edge(s)

Parent: [Platform adaptation](r12-platform-adaptation.md)

## Units (4)

<a id="u-3534f60386c8"></a>
### `amigaos-c-curl-amiga-init`

`CURLcode Curl_amiga_init(void)` · [lib/amigaos.c:L72-L100][f1]

Opens the Amiga bsdsocket library and prepares the socket interface used by the rest of the module, returning CURLE_OK on success and CURLE_FAILED_INIT on any failure.

Two compile-time variants exist. AmigaOS 4: OpenLibrary("bsdsocket.library",4); if the library opens but GetInterface("main") fails, the library is closed before failing. On success it queries SocketBaseTags for the GETHOSTADDR_R API, setting the static SocketFeatures flag HAVE_BSDSOCKET_GETHOSTBYNAME_R when enabled, stores the interface in the static __CurlISocket, registers Curl_amiga_cleanup via atexit, and returns CURLE_OK. AmigaOS 3: opens the library only if the static SocketBase is not already set; failure prints 'No TCP/IP Stack running!' via __request (libnix) or Printf (otherwise) and returns CURLE_FAILED_INIT; a non-zero SocketBaseTags result (errno/log pointers setup) prints 'SocketBaseTags ERROR' and also fails. On success it registers atexit cleanup except under __libnix__, where ADD2EXIT(Curl_amiga_cleanup,-50) is used instead. Non-Amiga or non-bsdsocket builds see a header macro reducing the call to CURLE_OK.

uses: [amigaos-c-curl-amiga-cleanup](r12-amigaos-support.md#u-3b6b68fe2e6e), [Curl_ipv4_resolve_r](r12-amigaos-support.md#u-2d70defb7e47)

**Uncertainties.**

- Whether SocketBaseTags actually enables the R API depends on the running TCP/IP stack, not visible here.
- Exact effect of ADD2EXIT priority -50 under libnix is platform convention not verifiable from this file.

<a id="u-3b6b68fe2e6e"></a>
### `amigaos-c-curl-amiga-cleanup`

`void Curl_amiga_cleanup(void)` · [lib/amigaos.c:L102-L110][f1]

Releases the bsdsocket library resources acquired by Curl_amiga_init, with separate AmigaOS 4 and AmigaOS 3 implementations.

OS 4: if the static __CurlISocket is set, it extracts the underlying Library base from the interface's Data.LibBase, drops the interface, closes the library, and nulls the static pointer, so repeated calls are no-ops. OS 3: if static SocketBase is set, it closes the library and nulls it. It is invoked at process exit via atexit (or ADD2EXIT under libnix, OS 3 only). Non-Amiga builds compile it away via the header macro Curl_nop_stmt.

uses: [amigaos-c-curl-amiga-init](r12-amigaos-support.md#u-3534f60386c8)

<a id="u-3433c06e5b0a"></a>
### `Curl_amiga_select`

`int Curl_amiga_select(int nfds, fd_set *readfds, fd_set *writefds, fd_set *errorfds, …` · [lib/amigaos.c:L175-L183][f1]

AmiSSL-only wrapper around WaitSelect that re-raises SIGINT so Ctrl-C is actioned.

It forwards nfds and the fd_sets and timeout to WaitSelect and returns its value unchanged. Only when WaitSelect returns -1 and SOCKERRNO equals SOCKEINTR does it call raise(SIGINT) before returning; all other results return as-is.

**Uncertainties.**

- Whether raise(SIGINT) reaching a handler affects the return value is outside this file.

<a id="u-2d70defb7e47"></a>
### `Curl_ipv4_resolve_r`

`struct Curl_addrinfo *Curl_ipv4_resolve_r(const char *hostname, uint16_t port)` · [lib/amigaos.c:L121-L170][f1]

Replaces the generic IPv4 resolver on AmigaOS 4, returning a Curl_addrinfo list for hostname:port or NULL on any failure.

Compiled only with CURLRES_AMIGA. When SocketFeatures has HAVE_BSDSOCKET_GETHOSTBYNAME_R (set by Curl_amiga_init), it allocates a zeroed CURL_HOSTENT_SIZE buffer; if allocation succeeds it calls gethostbyname_r, converts a non-NULL result via Curl_he2ai(h, port), and always frees the buffer; allocation failure or resolution failure yields NULL. Otherwise two paths: with USE_RESOLV_THREADED, gethostbyname is not thread-safe, so it reopens bsdsocket.library and gets the 'main' interface on the calling thread's context, resolves, converts on success, then drops the interface and closes the library; if either reopen step fails, ai stays NULL. Without the threaded resolver it uses gethostbyname directly and converts a non-NULL result. Callers such as Curl_sync_getaddrinfo depend on this as the synchronous getaddrinfo backend on this platform. Assumes malloc/calloc/free are thread-safe because Curl_he2ai allocates.

uses: [amigaos-c-curl-amiga-init](r12-amigaos-support.md#u-3534f60386c8), [Curl_sync_getaddrinfo](r12-sync-ipv4-resolver.md#u-ed1ad49f786c)

**Uncertainties.**

- h_errnop is set but never inspected; error detail is discarded.
- Behavior when __CurlISocket is NULL but the R-API flag is set is untested by visible code (gethostbyname_r would use the stale global interface).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/amigaos.c
