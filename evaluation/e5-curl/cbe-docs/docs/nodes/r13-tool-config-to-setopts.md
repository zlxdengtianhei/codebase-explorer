# Tool Config to Easy Options

**Capability.** Owns the curl tool's conversion of parsed OperationConfig into libcurl easy-handle options. A top-level converter fans out into grouped setters (transfer, DNS/network, proxy, credentials/headers, protocol-specific including HTTP/FTP/SSH/TLS, mail/SASL, cookies, misc), each reporting failures through a shared lethal/ignorable classifier.

Use this subtree to see which command-line setting maps to which CURLOPT and where conversion errors abort. Scheme-filtered groups return CURLE_OK silently for unrelated protocols.

**Depends on.**

- [curl Library Responsibilities](r13-curl-library-core.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r13-tool-config-to-setopts ` → ` r13-curl-library-core `)
- [--libcurl Code Generation](r1-libcurl-codegen.md) · graph-only · 213 edge(s)

Parent: [curl Library Responsibilities](r13-curl-library-core.md)

## Units (27)

<a id="u-9e44a8e94dc1"></a>
### `buffersize`

`static void buffersize(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L932-L949][f1]

Chooses CURLOPT_BUFFERSIZE.

In debug builds the CURL_BUFFERSIZE environment variable overrides everything: a parseable number (capped at LONG_MAX) is set and the function returns even if parsing failed (no option set then). In normal operation, when a receive speed limit below 102400 is configured, the buffer is shrunk to that rate for better sleeps; otherwise the fixed BUFFER_SIZE is used.

**Notes.**

- condition: An unparseable CURL_BUFFERSIZE in debug builds leaves the buffer size unset entirely (early return).

**Uncertainties.**

- curlx_str_number is an external helper; its failure semantics for this parse are not visible here.

<a id="u-c9a6f04849d0"></a>
### `check_post_resume`

`static CURLcode check_post_resume(struct OperationConfig *config)` · [src/config2setopts.c:L890-L900][f1]

Rejects resume combined with HTTP POST bodies.

When use_resume is set together with resume_from or resume_from_current, errorf reports the error, sets config->synthetic_error, and returns CURLE_BAD_FUNCTION_ARGUMENT; otherwise CURLE_OK.

<a id="u-8a09fc9f6181"></a>
### `config2setopts`

`CURLcode config2setopts(struct OperationConfig *config, struct per_transfer *per, CUR…` · [src/config2setopts.c:L1204-L1259][f1]

Top-level converter from the curl tool's OperationConfig into libcurl easy-handle options, called once per transfer.

First rewrites/validates the URL via url_proto_and_rewrite, then attaches the share handle with plain curl_easy_setopt (excluded from --libcurl output). In debug builds, CURL_QUICK_EXIT enables CURLOPT_QUICK_EXIT (detached threads); note the guarded if with the block means without the env var the block still executes in non-debug builds only. Then, in order: trace callbacks, buffer size, URL, NOPROGRESS from noprogress/silent, generic I/O callbacks (which may override NOPROGRESS for stdin uploads), proxy_setopts (aborting on lethal error or synthetic_error), and finally credentials/headers, transfer, protocol, DNS/network, mail/SASL, and misc groups, each chained only when the previous result is not lethal per setopt_bad. If everything succeeded but config->synthetic_error was set along the way, returns CURLE_FAILED_INIT instead of OK.

**Notes.**

- condition: setopt_bad tolerance means CURLE_NOT_BUILT_IN/UNKNOWN_OPTION from feature groups never abort the whole transfer.

calls: [url_proto_and_rewrite](r13-tool-config-to-setopts.md#u-c685f47d6639), [proxy_setopts](r13-tool-config-to-setopts.md#u-44db1e49f249), [transfer_setopts](r13-tool-config-to-setopts.md#u-feaf8ee0621c), [protocol_setopts](r13-tool-config-to-setopts.md#u-395e4ae480aa), [dns_and_network_setopts](r13-tool-config-to-setopts.md#u-1f02eef69459), [mail_and_sasl_setopts](r13-tool-config-to-setopts.md#u-a036e8d6b41d), [misc_setopts](r13-tool-config-to-setopts.md#u-ed07ab95700e), [gen_trace_setopts](r13-tool-config-to-setopts.md#u-0872ee901354), [gen_cb_setopts](r13-tool-config-to-setopts.md#u-45b13de0ad07), [buffersize](r13-tool-config-to-setopts.md#u-9e44a8e94dc1), [setopt_bad](r13-tool-config-to-setopts.md#u-55c795c3f3d4), [curl_easy_setopt](r2-setopt-core.md#u-86c13b752f56)

**Uncertainties.**

- The #ifdef DEBUGBUILD if(getenv(...)) followed by an unguarded brace block means QUICK_EXIT is set unconditionally in non-debug builds; whether that is intended is ambiguous from syntax alone.

<a id="u-95ad8291ebe3"></a>
### `cookie_setopts`

`static CURLcode cookie_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L537-L580][f1]

Configures cookies.

When config->cookies exists, it joins cookie strings with ';' into a dynbuf capped at 8200 bytes; each element after the first is prefixed with a space unless it already starts with a blank. Exceeding the cap warns 'skipped provided cookie' and returns the dynbuf error immediately without freeing the dynbuf. Otherwise the joined header is set via CURLOPT_COOKIE and the buffer freed; a set failure returns after freeing. Cookie files are each set as CURLOPT_COOKIEFILE, cookiejar as CURLOPT_COOKIEJAR, and COOKIESESSION follows config->cookiesession.

**Notes.**

- failure: When the 8200-byte cap is hit, the dynbuf is returned unfreed (memory retained until process cleanup is not shown).

calls: [curlx_dyn_add](r3-dynbuf.md#u-b4e3d05d4a72)

<a id="u-7956d61be2a5"></a>
### `credentials_and_headers_setopts`

`static CURLcode credentials_and_headers_setopts(struct OperationConfig *config, CURL …` · [src/config2setopts.c:L951-L981][f1]

Sets authentication and header options.

Netrc mode is three-way: netrc_opt gives CURL_NETRC_OPTIONAL; netrc or netrc_file gives REQUIRED; otherwise IGNORED. Sets the netrc file, login options, userpwd, XOAUTH2 bearer token, key password, and the user header slist as CURLOPT_HTTPHEADER. When the HTTP or RTSP protocol is compiled in, also sets referer and user agent, defaulting the agent to the curl name/version string. Errors from string setters propagate via the macro; the function returns CURLE_OK otherwise.

**Uncertainties.**

- The proto_http/proto_rtsp guard tests compiled-in protocol availability, not the transfer's scheme; user agent/referer may be set for non-HTTP transfers in such builds.

<a id="u-1f02eef69459"></a>
### `dns_and_network_setopts`

`static CURLcode dns_and_network_setopts(struct OperationConfig *config, struct per_tr…` · [src/config2setopts.c:L1074-L1117][f1]

Applies DNS, interface, and connection-layer options: network interface, progress-bar initialization on per->progressbar, DNS servers/interface/local IPs, telnet options, connect timeout, DoH URL, FTP missing-dir creation mode, max file size, IP resolve version, SOCKS5 GSSAPI NEC and auth mask, service name, ignore-content-length, and local port/range when a port is given.

--raw disables both HTTP content and transfer decoding. Delegates TCP keepalive/nodelay/fastopen to tcp_setopts and sets the TFTP blocksize only when a blocksize is configured and TFTP is compiled in.

calls: [tcp_setopts](r13-tool-config-to-setopts.md#u-2f2cae36ddd2), [progressbarinit](r5-tool-callbacks.md#u-72debdef66bb)

<a id="u-b75db34d3ff6"></a>
### `ftp_setopts`

`static CURLcode ftp_setopts(struct OperationConfig *config, CURL *curl, const char *u…` · [src/config2setopts.c:L757-L788][f1]

Applies FTP/FTPS options; returns CURLE_OK for any other scheme.

Sets FTPPORT, disables EPSV/EPRT per flags, sets the FTP SSL CCC mode when ftp_ssl_ccc is on, the FTP account, skip-PASV-IP, file method, alternative-to-user string, and PRET support. Errors from MY_SETOPT_STR propagate through the returned result; note result is returned without being initialized to CURLE_OK beyond the macro assignments.

**Uncertainties.**

- CURLcode result is returned but never explicitly initialized before MY_SETOPT_STR; if the macros do not assign on success, the return value's content for the non-string paths is unproven from this file.

<a id="u-45b13de0ad07"></a>
### `gen_cb_setopts`

`static void gen_cb_setopts(struct OperationConfig *config, struct per_transfer *per, …` · [src/config2setopts.c:L799-L838][f1]

Installs the transfer I/O callbacks.

Writes and reads both use the per-transfer struct as data (WRITEDATA/READDATA/SEEKDATA/HEADERDATA) with tool_write_cb, tool_read_cb, tool_seek_cb, and tool_header_cb. Progress handling has two exclusive cases: with the bar progress mode, not noprogress, and not silent, tool_progress_cb is installed; otherwise, when uploading from stdin ('.'), NOPROGRESS is cleared and tool_readbusy_cb is installed so the progress slot can unpause busy reads. Header callback/data are always set.

**Notes.**

- condition: config is explicitly unused ((void)config) — all inputs come from per and global.

imports: [src/tool_cb_wrt.h][f2]

<a id="u-0872ee901354"></a>
### `gen_trace_setopts`

`static void gen_trace_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L790-L797][f1]

Installs the debug callback when trace output is enabled: when global->tracetype is not TRACE_NONE, sets CURLOPT_DEBUGFUNCTION to tool_debug_cb, DEBUGDATA to config, and VERBOSE to 1.

<a id="u-0a8c1fd5ccb0"></a>
### `get_address_family`

`static int get_address_family(curl_socket_t sockfd)` · [src/config2setopts.c:L59-L67][f1]

Returns the address family of a socket by querying getsockname into a zeroed sockaddr.

On success returns sa_family; on failure returns AF_UNSPEC. Guarded by #ifdef IP_TOS, so absent in builds without that option.

**Uncertainties.**

- Whether AF_UNSPEC callers distinguish error from a genuinely unspecified family is not shown here.

<a id="u-70559d7067ab"></a>
### `http_setopts`

`static CURLcode http_setopts(struct OperationConfig *config, CURL *curl, const char *…` · [src/config2setopts.c:L666-L730][f1]

Applies HTTP-only options; returns CURLE_OK immediately unless the negotiated scheme is http or https.

Sets follow-location, unrestricted auth, AWS SigV4 (unless disabled), autoreferer, proxy headers slist, max redirects, HTTP version when configured, the POST-redirection mask from post301/302/303 flags, Accept-Encoding ('' when --compressed), transfer encoding, HTTP/0.9 allowance, altsvc and hsts files, and Expect: 100 timeout when positive. Then chains cookie_setopts and propagates its error. When a proxy or proxy headers are in use together with https or proxytunnel, sets CURLOPT_HEADEROPT to CURLHEADER_SEPARATE so --header content does not leak into CONNECT requests.

calls: [cookie_setopts](r13-tool-config-to-setopts.md#u-95ad8291ebe3), [httpsig_setopts](r13-tool-config-to-setopts.md#u-4c19fd5e424a)

<a id="u-4c19fd5e424a"></a>
### `httpsig_setopts`

`static CURLcode httpsig_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L584-L660][f1]

Configures HTTP message signatures when any --httpsig-* option is given; compiles to a no-op returning CURLE_OK when the feature is disabled.

--httpsig-key and --httpsig-keyid are mandatory (errorf + CURLE_FAILED_INIT otherwise). The algorithm defaults to ed25519; 'ed25519' and 'hmac-sha256' are accepted, anything else errors with CURLE_FAILED_INIT. Sets the algorithm, headers, and keyid options. A key starting with '@' is read from the named file via file2string: PARAM_NO_MEM yields CURLE_OUT_OF_MEMORY, PARAM_READ_ERROR yields CURLE_READ_ERROR, and an empty file yields CURLE_BAD_FUNCTION_ARGUMENT, each after freeing the buffer and reporting via errorf; an unopenable file also gives CURLE_READ_ERROR. The hexdata is set with my_setopt_str (not the macro, since it must be freed first), and only a lethal error per setopt_bad() aborts. A non-'@' key must be non-empty or CURLE_BAD_FUNCTION_ARGUMENT is returned.

**Notes.**

- failure: Lethal classification via setopt_bad lets NOT_BUILT_IN/UNKNOWN_OPTION from CURLOPT_HTTPSIG_KEY pass as success.

calls: [file2string](r9-tool-paramhlp.md#u-0f6d92519149), [setopt_bad](r13-tool-config-to-setopts.md#u-55c795c3f3d4)

<a id="u-a036e8d6b41d"></a>
### `mail_and_sasl_setopts`

`static CURLcode mail_and_sasl_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L1119-L1136][f1]

Sets mail and SASL options: MAIL_FROM, the recipient slist, recipient allow-fails, MAIL_AUTH, SASL authzid, and SASL initial response; also sets NEW_FILE_PERMS when create_file_mode is nonzero.

<a id="u-ed07ab95700e"></a>
### `misc_setopts`

`static CURLcode misc_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L1138-L1202][f1]

Applies remaining assorted options: stderr redirect, RESOLVE and CONNECT_TO slists, GSSAPI delegation (set twice — once near the top and again after the protocol-string options), protocol and redirect-protocol strings when present, mail/SASL options duplicated from mail_and_sasl_setopts, unix socket path as abstract or regular, default protocol, TFTP no-options (only true when TFTP is available), happy-eyeballs timeout unless default, and disallow-username-in-url.

When IP TOS or VLAN priority is configured: on platforms with any of IP_TOS/IPV6_TCLASS/SO_PRIORITY it installs sockopt_callback with config as data; otherwise it errors per feature and returns CURLE_NOT_BUILT_IN. CURLOPT_UPLOAD_FLAGS is set only when no error occurred so far.

**Notes.**

- side_effect: CURLOPT_GSSAPI_DELEGATION and MAIL_AUTH/SASL options are set redundantly; later sets overwrite with the same values.

uses: [sockopt_callback](r13-tool-config-to-setopts.md#u-a7d42bfb2959)

<a id="u-395e4ae480aa"></a>
### `protocol_setopts`

`static CURLcode protocol_setopts(struct OperationConfig *config, struct per_transfer …` · [src/config2setopts.c:L1037-L1072][f1]

Orchestrates protocol-specific option groups in order: http_setopts, ftp_setopts (both scheme-filtered, errors abort), ssh_setopts (only lethal errors abort via setopt_bad), then, when the SSL feature is present, ssl_ca_setopts followed by ssl_setopts with the same lethality filter.

In debug builds, when per->urlnum is 0 and CURL_DBG_NO_USE_SSL_ON_FIRST is set, forces CURLUSESSL_NONE. Returns the last non-lethal or first lethal result; per is unused outside debug builds.

calls: [http_setopts](r13-tool-config-to-setopts.md#u-70559d7067ab), [ftp_setopts](r13-tool-config-to-setopts.md#u-b75db34d3ff6), [ssh_setopts](r13-tool-config-to-setopts.md#u-e7c38717a410), [ssl_ca_setopts](r13-tool-config-to-setopts.md#u-02b453e9eccb), [setopt_bad](r13-tool-config-to-setopts.md#u-55c795c3f3d4)

<a id="u-44db1e49f249"></a>
### `proxy_setopts`

`static CURLcode proxy_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L840-L888][f1]

Applies proxy configuration.

Setting CURLOPT_PROXY first: if that fails, errorf reports disabled proxy support, sets config->synthetic_error, and returns CURLE_NOT_BUILT_IN. With a proxy configured, the proxy type follows config->proxyver. Then sets proxyuserpwd, HTTP-proxy tunneling, pre-proxy, noproxy, suppress-connect-headers, proxy service name, HAProxy protocol and client IP, and proxy key password unconditionally or per flags. Proxy authentication is a priority chain: anyauth, negotiate, ntlm, digest, basic — first matching flag sets CURLOPT_PROXYAUTH via bitmask; none set leaves the default.

**Notes.**

- failure: The early NOT_BUILT_IN path also flags config->synthetic_error, which config2setopts checks to abort.

<a id="u-55c795c3f3d4"></a>
### `setopt_bad`

`static bool setopt_bad(CURLcode result)` · [src/config2setopts.c:L51-L56][f1]

Classifies a curl_easy_setopt failure as lethal or ignorable for the option-conversion pipeline.

Returns TRUE only when result is nonzero and neither CURLE_NOT_BUILT_IN nor CURLE_UNKNOWN_OPTION; those two mean libcurl lacks the feature/option and callers continue setting other options. A zero result is not bad.

<a id="u-a51c221b8d81"></a>
### `setopt_post`

`static CURLcode setopt_post(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L902-L930][f1]

Finalizes POST body options based on config->httpreq.

For SIMPLEPOST, resume is first rejected via check_post_resume; then CURLOPT_POSTFIELDS points into config->postdata's dynbuf with POSTFIELDSIZE_LARGE from its length. For MIMEPOST, any previous mimepost is freed and cleared, resume is rejected, and on success tool2curlmime builds the form and my_setopt_mimepost attaches it. Other request types do nothing. First failure propagates and skips the rest of the case.

calls: [tool2curlmime](r3-form-parsing.md#u-b90bfb405303), [check_post_resume](r13-tool-config-to-setopts.md#u-c9a6f04849d0)

**Uncertainties.**

- For SIMPLEPOST the easy handle retains a pointer into config->postdata; lifetime beyond this call is not shown.

<a id="u-a7d42bfb2959"></a>
### `sockopt_callback`

`static int sockopt_callback(void *clientp, curl_socket_t curlfd, curlsocktype purpose)` · [src/config2setopts.c:L75-L121][f1]

Socket-option callback applying configured IP TOS and VLAN priority to freshly created connection sockets.

It ignores any purpose other than CURLSOCKTYPE_IPCXN. For AF_INET sockets it sets IP_TOS, for AF_INET6 it sets IPV6_TCLASS (when compiled in); for SO_PRIORITY it sets the VLAN priority on SOL_SOCKET. Each setsockopt failure only produces a warnf message with errno and strerror text; the callback always returns CURL_SOCKOPT_OK, so failures never abort the connection. Both features are conditionally compiled with IP_TOS/IPV6_TCLASS/SO_PRIORITY; the whole callback exists only when at least one is defined.

**Notes.**

- side_effect: Emits warning messages on setsockopt failure but never changes the callback return value.

calls: [get_address_family](r13-tool-config-to-setopts.md#u-0a8c1fd5ccb0)

<a id="u-e7c38717a410"></a>
### `ssh_setopts`

`static CURLcode ssh_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L205-L269][f1]

Sets SSH-related options on the easy handle; returns CURLE_OK immediately when neither SCP nor SFTP protocol is available.

Sets private/public key files and host-public-key MD5/SHA256 strings from config. If --insecure-ok is not set, it resolves a known-hosts path: config->knownhosts if present, else findfile('.ssh/known_hosts'), else, when no MD5/SHA256 pin exists, synthesizes '$HOME/.ssh/known_hosts' via a dynbuf (empty HOME string if getenv fails). The found path is set with my_setopt_str and cached in config->knownhosts; on set failure it clears config->knownhosts, frees the string, and propagates the error. Duplication from findfile allocation failure returns CURLE_OUT_OF_MEMORY.

**Notes.**

- side_effect: Caches the resolved known-hosts path in config->knownhosts to skip repeated lookup.

calls: [findfile](r7-tool-support.md#u-6b92e249f0be)

<a id="u-e0384a86b9b5"></a>
### `ssl_backend`

`static char *ssl_backend(void)` · [src/config2setopts.c:L125-L137][f1]

Returns the name of the SSL backend in use, cached in a static buffer.

On first call it reads curl_version_info's ssl_version, copies up to the first space (chopping multi-SSL suffixes) into an 80-byte static via curl_msnprintf, and marks it cached; subsequent calls return the cached string. If ssl_version is NULL the buffer keeps its initial 'no ssl' text.

**Uncertainties.**

- Not thread-safe: the static 'already' flag and buffer are unsynchronized.

<a id="u-02b453e9eccb"></a>
### `ssl_ca_setopts`

`static CURLcode ssl_ca_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L319-L375][f1]

Sets CA trust material on the easy handle; only called when libcurl supports TLS.

Sets CAINFO, PROXY_CAINFO, and CAPATH when configured. PROXY_CAPATH falls back to capath when proxy_capath is unset; if that set returns NOT_BUILT_IN or UNKNOWN_OPTION it warns via ssl_backend() and resets to CURLE_OK. When CURL_CA_EMBED is compiled in and no cacert/capath (or proxy equivalents) are configured, it sets the embedded CA bundle via CURLOPT_CAINFO_BLOB / CURLOPT_PROXY_CAINFO_BLOB with a notef, again downgrading unsupported-option errors to OK with a warning. Other errors propagate and abort further setting.

calls: [ssl_backend](r13-tool-config-to-setopts.md#u-e0384a86b9b5)

**Uncertainties.**

- result is checked against NOT_BUILT_IN/UNKNOWN_OPTION right after the MY_SETOPT_STR macro for PROXY_CAPATH; whether the macro assigns result on failure is not visible in this file.

<a id="u-9272a8dc4b6b"></a>
### `ssl_setopts`

`static CURLcode ssl_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L378-L535][f1]

Applies all remaining TLS options; only called when libcurl supports TLS, and always returns CURLE_OK at the end.

Sets CRL files (proxy CRL defaults to crlfile), pinned public keys, EC curves, signature algorithms, and certificate/key pairs and types for both direct and proxy connections. Forces SSL_VERIFYPEER/VERIFYHOST to 0 when --insecure-ok, else 1, so each transfer resets values left by earlier --next transfers; DoH and proxy variants are relaxed separately when configured. Computes SSL options bitmasks (allow beast, early data, no revoke, best-effort revoke, native CA, auto client cert) for direct and proxy and sets them only when nonzero. Cipher lists and TLS 1.3 cipher lists warn and continue when unsupported. Sets CURLOPT_SSLVERSION from tlsversion(), proxy SSL version when a proxy is configured, USE_SSL (ALL/TRY/CONTROL by the strongest of ftp_ssl_reqd/ftp_ssl/ftp_ssl_control), session-cache disabling, ECH strings only when feature_ech, engine, and disables ALPN when noalpn. Unsupported pinned keys and ciphers only warn; MY_SETOPT_STR failures propagate immediately but are never returned.

**Notes.**

- failure: Despite MY_SETOPT_STR error propagation, the function unconditionally returns CURLE_OK, so TLS option failures never abort the transfer.

calls: [tlsversion](r13-tool-config-to-setopts.md#u-68b9869609bf), [ssl_backend](r13-tool-config-to-setopts.md#u-e0384a86b9b5)

**Uncertainties.**

- ech_public, ech_config, and ech all set the same CURLOPT_ECH option sequentially, so the last configured one wins; intent is not stated in code.

<a id="u-2f2cae36ddd2"></a>
### `tcp_setopts`

`static void tcp_setopts(struct OperationConfig *config, CURL *curl)` · [src/config2setopts.c:L732-L755][f1]

Sets TCP connection options.

Disables TCP_NODELAY only when tcp_nodelay is off, enables TCP_FASTOPEN when configured, and swaps in the MPTCP open-socket callback for --mptcp. When keepalive is not disabled it enables TCP_KEEPALIVE, uses alivetime for both KEEPIDLE and KEEPINTVL when set, and KEEPCNT when alivecnt is set; otherwise it explicitly disables keepalive.

imports: [src/tool_cb_soc.h][f3]

<a id="u-68b9869609bf"></a>
### `tlsversion`

`static long tlsversion(unsigned char mintls, unsigned char maxtls)` · [src/config2setopts.c:L271-L316][f1]

Maps the --tlsv1 min/max version codes to a CURLOPT_SSLVERSION value.

If the minimum is default (0) and the maximum is set below 3, the minimum is raised to the maximum so the default floor does not exceed the ceiling. The minimum maps 1→TLSv1_0, 2→TLSv1_1, 0/3→TLSv1_2 (so default min is 1.2), 4 and any other value→TLSv1_3. The maximum is ORed in: 0 leaves the max bits unset; 1–4 map to the corresponding MAX_* constants, with any value above 4 treated as TLSv1_3.

**Uncertainties.**

- Values above 4 silently map to TLSv1_3 for both min and max; caller validation is not visible.

<a id="u-feaf8ee0621c"></a>
### `transfer_setopts`

`static CURLcode transfer_setopts(struct OperationConfig *config, struct per_transfer …` · [src/config2setopts.c:L983-L1035][f1]

Applies generic transfer options: nobody, fail-on-error (when fail equals FAIL_WO_BODY), request target, upload (from per->uploadfile), dirlistonly, append, ASCII mode, range, error buffer, timeout, MIME options, low-speed limits, send/receive speed caps, resume offset (resume_from when use_resume else 0), path-as-is, FILETIME for no-body or remote-time, CRLF, quote/postquote/prequote slists, time condition and value, and custom request (also recorded via customrequest_helper).

Calls setopt_post in the middle and returns immediately on its error.

calls: [setopt_post](r13-tool-config-to-setopts.md#u-a51c221b8d81), [customrequest_helper](r5-tool-messaging.md#u-3b5d3cb6ab00)

<a id="u-c685f47d6639"></a>
### `url_proto_and_rewrite`

`static CURLcode url_proto_and_rewrite(char **url, struct OperationConfig *config, con…` · [src/config2setopts.c:L143-L203][f1]

Parses the transfer URL, determines its scheme token, and rewrites IPFS/IPNS URLs in place.

Builds a CURLU handle with scheme guessing and non-support schemes allowed. If a proto_default is configured, the scheme is fetched with CURLU_NO_GUESS_SCHEME; when the URL has no scheme, the default's protocol token becomes the scheme. Otherwise the scheme is fetched with CURLU_DEFAULT_SCHEME. When the scheme is ipfs or ipns (unless IPFS is disabled), ipfs_url_rewrite rewrites *url and sets config->synthetic_error on rewrite failure. CURLUE_OUT_OF_MEMORY at either stage becomes CURLE_OUT_OF_MEMORY; curl_url() failure also yields that error. *scheme is set to the token, or '?' so later proto comparisons never match when unknown. Returns CURLE_OK or the mapped error; the CURLU handle is always cleaned up.

**Notes.**

- failure: Any URL parse error other than OUT_OF_MEMORY or NO_SCHEME handling leaves result CURLE_OK; the '?' scheme makes protocol-specific setopts skip.

calls: [ipfs_url_rewrite](r6-tool-ipfs-rewrite.md#u-1576b15ada23), [proto_token](r7-tool-support.md#u-cf1321e4e28c)

**Uncertainties.**

- When proto_default's token lookup fails, proto stays NULL and *scheme becomes '?'; whether that should be an error is not decided here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/config2setopts.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_cb_wrt.h
[f3]: ../../../../../../eval/curl-2c04412/src/tool_cb_soc.h
