# Public libcurl API Header

**Capability.** Owns the include/curl/curl.h contract: portable linkage preamble, CURLcode/CURLoption enums and option-value constants, callback typedefs, socket and transfer callback infrastructure, MIME/form and global-init API, runtime introspection and share interface, TLS/proxy/auth option constants, HSTS and protocol masks, and the CURL_NO_OLDIES compatibility aliases.

Read this subtree to understand the API surface applications program against. The preamble and enums define calling conventions; later regions declare options, callbacks, and interfaces. Compatibility aliases keep legacy names compiling unless CURL_NO_OLDIES is defined.

Parent: [curl Codebase](r3-curl-codebase.md)

## Units (13)

<a id="u-1df90ddf7b9a"></a>
### `curlh-portability-preamble`

`group` · [include/curl/curl.h:L1-L153][f1]

Defines the portability and linkage preamble of the public libcurl header.

It opens an include guard, defines CURL_DEPRECATED/CURL_IGNORE_DEPRECATION as GCC/clang/IAR deprecation attributes unless building libcurl itself or CURL_DISABLE_DEPRECATION is set (expanding to nothing otherwise), includes curlver.h, system.h, stdio.h, limits.h and platform headers gated on _WIN32, BSD variants, and a listed set of OSes for sys/select.h, then typedefs CURL and CURLSH as opaque void, computes CURL_EXTERN (empty for CURL_STATICLIB, dllexport/dllimport on Windows or when declspec attributes are supported, CURL_EXTERN_SYMBOL when building with CURL_HIDDEN_SYMBOLS), and defines curl_socket_t as SOCKET with CURL_SOCKET_BAD INVALID_SOCKET on Windows (excluding lwIP) or int with CURL_SOCKET_BAD (-1) elsewhere, guarded by curl_socket_typedef. All content is wrapped in extern "C" for C++.

group: [curlh-sslbackend-and-httppost](r3-public-curl-api.md#u-b0d635537051)

**Uncertainties.**

- Actual effect of CURL_EXTERN_SYMBOL is defined in system.h, which is not supplied here.

<a id="u-b0d635537051"></a>
### `curlh-sslbackend-and-httppost`

`enum` · [include/curl/curl.h:L153-L169][f1]

Declares the curl_sslbackend enum identifying supported TLS backends (several members marked deprecated via CURL_DEPRECATED), alias macros mapping AWS-LC/BoringSSL/LibreSSL forks and old names onto existing backend values, the CURLFOLLOW_* bit values for CURLOPT_FOLLOWLOCATION redirect behavior, and the curl_httppost linked-list struct used by the deprecated multipart formpost API.

The struct carries the part list linkage, name/contents/buffer pointers with lengths, per-part content type and extra headers, a 'more' list for multiple files under one field name, and a flags field whose CURL_HTTPPOST_* bits switch how the part data is sourced: filename, read-file, non-owned pointer name/contents, buffer, pointer buffer, read-callback with custom pointer, or curl_off_t contentlen when CURL_HTTPPOST_LARGE is set (added 7.46.0). showfilename overrides the reported filename; userp carries the callback custom pointer.

**Uncertainties.**

- Backend availability at runtime is not determined by this header; only identifiers are declared.

<a id="u-54a324ecf333"></a>
### `curlh-transfer-callbacks-and-fileinfo`

`enum` · [include/curl/curl.h:L295-L306][f1]

Declares the transfer-time callback typedefs and their result-code conventions.

curl_progress_callback (deprecated, doubles) and curl_xferinfo_callback (curl_off_t) report progress; returning CURL_PROGRESSFUNC_CONTINUE (0x10000001) makes libcurl run its default progress function. Buffer limits CURL_MAX_READ_SIZE (10 MiB), CURL_MAX_WRITE_SIZE (16384) and CURL_MAX_HTTP_HEADER (100 KiB) are overridable via build definitions; the header comment gives 16K as an upload-buffer sweet spot on Windows. Write-callback magic returns: CURL_WRITEFUNC_PAUSE pauses receiving, CURL_WRITEFUNC_ERROR signals callback error. Declared prototypes cover write, resolver-start, chunk-bgn/chunk-end (long returns with CURL_CHUNK_*_FUNC_OK/FAIL and SKIP for bgn; the end callback must be invoked for every chunk even skipped ones), fnmatch (MATCH/NOMATCH/FAIL codes), seek (OK, FAIL aborts the transfer, CANTSEEK lets libcurl try alternatives), read (CURL_READFUNC_ABORT stops the transfer immediately, CURL_READFUNC_PAUSE pauses sending), and trailer (OK/ABORT). It also defines curlfiletype and the CURLFINFOFLAG_KNOWN_* bits filling struct curl_fileinfo, whose b_data/b_size/b_used fields are documented as private to libcurl and must not be touched.

**Uncertainties.**

- Exact libcurl handling of out-of-range return values from these callbacks is not defined in this header.

<a id="u-65ce1a29cbaf"></a>
### `curlh-socket-and-io-callbacks`

`enum` · [include/curl/curl.h:L412-L416][f1]

Declares socket-level and I/O callback infrastructure.

struct curl_sockaddr exposes family, socktype, protocol, addrlen (changed from socklen_t in 7.18.0) and the sockaddr; curl_opensocket_callback receives it and may replace the address or refuse the connection by returning CURL_SOCKET_BAD, while curl_closesocket_callback replaces close(2). curlsocktype distinguishes IPCXN from ACCEPT-created sockets. The sockopt callback returns CURL_SOCKOPT_OK, CURL_SOCKOPT_ERROR (libcurl aborts with CURLE_ABORTED_BY_CALLBACK), or CURL_SOCKOPT_ALREADY_CONNECTED. curlioerr/curliocmd define the deprecated ioctl callback: CURLIOCMD_RESTARTREAD restarts the read stream and the callback may report CURLIOE_FAILRESTART or CURLIOE_UNKNOWNCMD. It also defines the pluggable malloc/free/realloc/strdup/calloc typedefs for curl_global_init_mem (guarded by CURL_DID_MEMORY_FUNC_TYPEDEFS), curl_infotype categories passed to the debug callback, the pre-request callback prototype with CURL_PREREQFUNC_OK/ABORT return codes, and the curl_conv_callback prototype.

<a id="u-2b2722da2e6a"></a>
### `curlh-curlcode-enum`

`enum` · [include/curl/curl.h:L520-L650][f1]

Declares CURLcode, the error-code enum returned by most libcurl functions.

The header mandates stability: new codes are appended, none removed; obsolete slots (20, 24, 29, 32, 34, 40, 41, 44, 46, 50, 51, 57, 62, 75, 76) are retained unused, and several slots were reused for new meanings (4, 10, 12, 16) as commented. Codes span protocol failures (CURLE_COULDNT_RESOLVE_HOST, CURLE_OPERATION_TIMEDOUT, CURLE_SSL_CONNECT_ERROR...), HTTP/2, HTTP/3, QUIC and SSH layer errors, CURLE_ABORTED_BY_CALLBACK reached from callback failures, CURLE_AGAIN for not-ready sockets, and end at CURLE_ECH_REQUIRED (101) plus CURL_LAST, which is a marker never to be used. A companion comment ties CURLE_PROXY to CURLINFO_PROXY_ERROR detail codes.

<a id="u-14a1052ff02b"></a>
### `curlh-obsolete-error-compat`

`enum` · [include/curl/curl.h:L744-L780][f1]

Provides the CURL_NO_OLDIES-guarded compatibility layer for retired CURLcode names and old option names: alias macros map old identifiers (e.g. CURLE_SSL_CACERT, CURLE_OBSOLETE16, CURLE_FTP_ACCESS_DENIED, CURLOPT_FILE, CURLOPT_WRITEINFO) onto their current equivalents or unused obsolete slots, so existing programs keep compiling; defining CURL_NO_OLDIES removes the block.

It then declares CURLproxycode, the detailed result enum surfaced via CURLINFO_PROXY_ERROR when a transfer fails with CURLE_PROXY, covering address/version/auth errors, send/recv failures at each proxy handshake stage, server reply codes (refused, unreachable, TTL expired, command not supported), and CURLPX_UNKNOWN_FAIL/CURLPX_UNKNOWN_MODE fallbacks.

<a id="u-d918715cdc0e"></a>
### `curlh-proxy-auth-ssh-ssl-options`

`enum` · [include/curl/curl.h:L810-L812][f1]

Declares the proxy-type, authentication, SSH and TLS option constants.

CURLPROXY_* long values select HTTP, HTTP/1.0, HTTPS, HTTPS2, HTTPS3 and SOCKS4/4A/5/5-hostname proxy flavors, with curl_proxytype only supplying CURLPROXY_LAST. CURLAUTH_* bitmasks choose HTTP auth methods; CURLAUTH_ANY excludes DIGEST_IE and HTTPSIG, CURLAUTH_ANYSAFE additionally excludes BASIC, CURLAUTH_ONLY (bit 31) must be ORed with one other type, and NTLM_WB exists only when CURL_NO_OLDIES is undefined. CURLSSH_AUTH_* masks pick SSH methods (default: any), CURLGSSAPI_DELEGATION_* controls credential delegation, and CURLHTTPSIG_* selects RFC 9421 algorithms. The SSH host-key section defines curl_khtype, curl_khkey (key is base64 text when len is zero, else raw data), the callback's return enum curl_khstat (FINE_ADD_TO_FILE, FINE, REJECT, DEFER, FINE_REPLACE; DEFER yields CURLE_PEER_FAILED_VERIFICATION while keeping the connection) and input status curl_khmatch, plus curl_sshkeycallback and the simpler curl_sshhostkeycallback returning CURLE_OK to accept. CURLUSESSL_*, CURLSSLOPT_* bits (BEAST, revocation modes, partial chain, native CA, auto client cert, early data), CURL_HET_DEFAULT 200 ms and CURL_UPKEEP_INTERVAL_DEFAULT 60000 ms follow, then FTP-related value sets: CURLFTPSSL_CCC_*, CURLFTPAUTH_*, CURLFTP_CREATE_DIR_* (RETRY re-CWDs even if MKD fails; only FTP), CURLFTPMETHOD_*, CURLHEADER_UNIFIED/SEPARATE, CURLALTSVC_* bits and CURLULFLAG_* IMAP upload flags. Legacy CURLFTPSSL names alias curl_usessl under CURL_NO_OLDIES.

**Uncertainties.**

- Which CURLSSLOPT_* bits each TLS backend honors is decided in the library, not this header.

<a id="u-0628685b50cd"></a>
### `curlh-hsts-and-protocol-masks`

`struct curl_hstsentry` · [include/curl/curl.h:L1056-L1061][f1]

Declares HSTS support and the deprecated protocol masks.

struct curl_hstsentry carries the host name with length, an includeSubDomains bit and an 18-byte expire field formatted 'YYYYMMDD HH:MM:SS' null-terminated; struct curl_index reports the entry index and total count for saving. The hsts read/write callbacks return CURLSTS_OK to continue, CURLSTS_DONE to stop, or CURLSTS_FAIL on error. CURLHSTS_ENABLE and CURLHSTS_READONLYFILE are the CURLOPT_HSTS_CTRL bits. The CURLPROTO_* block is explicitly marked for the deprecated CURLOPT_*PROTOCOLS options: one bit per supported protocol from HTTP through GOPHERS, plus CURLPROTO_ALL as 0xffffffff.

<a id="u-5b45d0e2dfd6"></a>
### `curlh-curloption-enum`

`enum` · [include/curl/curl.h:L1154-L1935][f1]

Defines the CURLOPT_* option numbering system and the full CURLoption enum.

Option values are built by the CURLOPT(name, type, number) macro as type-base + number, where CURLOPTTYPE_LONG=0, OBJECTPOINT=10000, FUNCTIONPOINT=20000, OFF_T=30000, BLOB=40000; STRINGPOINT, SLISTPOINT, CBPOINT and VALUES are aliases so tools can classify options, and CURLOPTDEPRECATED attaches a deprecation attribute. The enum assigns every option its documented number (WRITEDATA=1 through SSL signature/HTTPSIG options in the 320s), skipping obsolete numbers with comments, marking deprecated entries (HTTPPOST, PUT, PROGRESSFUNCTION, KRBLEVEL, TLSAUTH trio, PROTOCOLS/REDIR_PROTOCOLS long forms, STREAM_DEPENDS...) with versions and replacement advice, and ending at CURL_LASTENTRY. A following CURL_NO_OLDIES block aliases old option names (CURLOPT_POST301, CURLOPT_SSLKEYPASSWD, CURLOPT_FTP_RESPONSE_TIMEOUT, MAIL_RCPT_ALLLOWFAILS typo-compat) and undefines CURLOPT_DNS_USE_GLOBAL_CACHE when oldies are disabled.

**Uncertainties.**

- Runtime validation of values passed to each option happens in the library; the header only fixes numeric identities.

<a id="u-38fdf260f584"></a>
### `curlh-option-value-constants`

`enum CURL_NETRC_OPTION` · [include/curl/curl.h:L2388-L2392][f1]

Declares the value sets consumed by VALUE-type options.

CURL_IPRESOLVE_* forces any/V4/V6. CURL_HTTP_VERSION_* picks HTTP versions, where 2TLS uses HTTP/2 for HTTPS and 1.1 otherwise, 3 falls back to HTTP/2 or 1.1 (HTTPS only; error on HTTP), 3ONLY removes the fallback, and CURL_HTTP_VERSION_2 aliases 2_0 for naming compatibility. CURL_RTSPREQ_* enumerate RTSP methods. CURL_NETRC_IGNORED/OPTIONAL/REQUIRED carry the netrc behavior with the enum CURL_NETRC_OPTION only holding CURL_NETRC_LAST so the values stay L-suffixed constants; CURL_TLSAUTH does the same for NONE/SRP. CURL_SSLVERSION_* selects minimum TLS/SSL versions with MAX_* variants (version shifted left 16 bits) controlling the maximum allowed protocol. CURL_REDIR_POST_301/302/303 are OR-able for CURLOPT_POSTREDIR with POST_ALL as their union; GET_ALL is 0. CURL_TIMECOND_* selects conditional request semantics, with curl_TimeCond again a marker-only typedef. CURL_ZERO_TERMINATED is the size_t sentinel meaning a null-terminated string.

<a id="u-bf54ff3f23bb"></a>
### `curlh-mime-form-global-api`

`enum` · [include/curl/curl.h:L2584-L2613][f1]

Declares the public string, MIME/form and global-init API surface.

curl_strequal/curl_strnequal are marked for future removal. The curl_mime/curl_mimepart opaque handles come with setters: curl_mime_init/free lifecycle tied to an easy handle, addpart, name, filename, type, encoder, data (memory), filedata, data_cb (read/seek/free callbacks with size and arg), subparts and headers (take_ownership decides who frees the slist). The deprecated CURLFORM_* enum, curl_forms array element struct, CURLFORMcode results (documented causes: memory failure, option twice, null char pointer, unknown option, incomplete form, illegal array, disabled build) and curl_formadd/formget/formfree form the legacy multipart API, all CURL_DEPRECATED(7.56.0) pointing at the mime API; curl_formget serializes a built form through a callback returning the passed length on success, curl_formfree releases a curl_httppost chain. Global lifecycle: curl_global_init (exactly once, before other calls; thread-safe only if CURL_VERSION_THREADSAFE is set in version info), curl_global_init_mem installing custom allocator callbacks, curl_global_cleanup, and curl_global_trace configuring per-component tracing. Helpers cover curl_getenv (result must be curl_free()d), curl_version, easy_escape/easy_unescape (newly allocated strings, unescape reports outlength and converts %XX per host encoding on non-ASCII platforms), curl_free, struct curl_slist with curl_slist_append/append-creates/ free_all, curl_global_sslset (callable once, before global_init; by id or name with id winning, CURLSSLSET_OK/UNKNOWN_BACKEND with avail list/TOO_LATE/NO_BACKENDS results), and curl_getdate parsing an HTTP date to seconds since epoch (second parameter unused, pass NULL).

**Uncertainties.**

- Return values and lifetimes are documented in comments; implementations live outside this header.

<a id="u-8fdef957a356"></a>
### `curlh-runtime-info-and-share`

`struct curl_certinfo` · [include/curl/curl.h:L2903-L2909][f1]

Declares runtime introspection and the share interface.

struct curl_certinfo holds num_of_certs and an array of per-certificate slists of 'name:content' lines, filled when CURLOPT_CERTINFO is set. curl_tlssessioninfo pairs a curl_sslbackend id with the backend's internal handle for CURLINFO_TLS_SSL_PTR. CURLINFO_* type masks (STRING/LONG/DOUBLE/SLIST/PTR/SOCKET/OFF_T with MASK and TYPEMASK) prefix the CURLINFO enum whose members encode type+number; deprecated double-based size/speed entries are paralleled by _T off_t versions, ending at CURLINFO_LASTONE=71, with CURLINFO_HTTP_CODE aliasing RESPONSE_CODE. curl_closepolicy is a legacy enum. CURL_GLOBAL_* flags feed curl_global_init (ALL = SSL|WINSOCK, DEFAULT = ALL; SSL bit has no purpose since 7.57.0). The share API defines curl_lock_data categories (cookie, DNS, SSL session, connect, PSL, HSTS...), curl_lock_access shared/single, lock/unlock callback typedefs, CURLSHcode results (BAD_OPTION, IN_USE, INVALID, NOMEM, NOT_BUILT_IN) and CURLSHopt options, with curl_share_init/setopt/cleanup prototypes. The version block defines CURLversion FIRST..TWELFTH with CURLVERSION_NOW=TWELFTH and struct curl_version_info_data whose 'age' field tells how many later fields are valid, adding version/host/features/ssl/protocols plus ares, libidn, iconv, libssh, brotli, nghttp2/quic, cainfo/capath, zstd, hyper, gsasl, feature_names and rtmp_version entries per version step; CURL_VERSION_* feature bits (through THREADSAFE bit 30) describe the build; curl_version_info(stamp) returns a static struct.

**Uncertainties.**

- Which features a given build reports depends on the compiled library, not this header.

<a id="u-f6e3eefb18ba"></a>
### `curlh-error-strings-pause-ssls-and-tail`

`group` · [include/curl/curl.h:L3200-L3374][f1]

Closes the header with the remaining API and include tail.

curl_easy_strerror and curl_share_strerror map CURLcode/CURLSHcode to static human-readable strings. curl_easy_pause pauses or resumes a transfer via the CURLPAUSE_* bitmask (RECV/SEND bits, *_CONT zero values, ALL/CONT composites). curl_easy_ssls_import inserts an exported SSL session (key, optional HMAC, data and lengths) into the easy handle's or its share's session cache; curl_easy_ssls_export iterates stored sessions invoking a curl_ssls_export_cb that receives key, shmac, data, validity, TLS id, ALPN and earlydata_max and returns CURLcode. After closing extern "C", it includes easy.h, multi.h, urlapi.h, options.h, header.h, websockets.h and mprintf.h (noting curl.h must expose option/info constants first), then sets up the GCC/clang typechecker include when compiling C with CURL_DISABLE_TYPECHECK undefined, otherwise — for STDC compilers — defines curl_easy_setopt/getinfo, curl_share_setopt and curl_multi_setopt as two-stage macros that enforce exactly three call arguments while tolerating C++ method-name usage.

**Uncertainties.**

- Behavior of the included sub-headers (easy.h, multi.h, ...) is not in this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/curl.h
