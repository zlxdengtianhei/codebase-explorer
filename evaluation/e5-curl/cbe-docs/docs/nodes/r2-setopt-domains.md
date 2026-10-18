# Setopt Domain Handlers

**Capability.** Per-protocol and per-domain option semantics: HTTP/MQTT, proxy, TLS/SSH, FTP, network, protocol masks, cookies, credentials and MIME POST installation.

Use to find the exact handling of a specific option group, including build-disabled stubs and special cases like cookie engine control, ECH parsing, and installing a curl_mime as POST body.

**Depends on.**

- [MIME Assembly API](r2-mime-api.md) · graph-confirmed · 3 edge(s)
- [Setopt Dispatch & Storage](r2-setopt-core.md) · graph-confirmed · 73 edge(s)

Parent: [Easy Handle Option Setting](r2-easy-setopt.md)

## Units (29)

<a id="u-fae53546d861"></a>
### `cookiefile`

`static CURLcode cookiefile(struct Curl_easy *data, const char *ptr)` · [lib/setopt.c:L1548-L1583][f1]

Manages the list of cookie filenames to read later, and clears the cookie engine when given NULL.

**Notes.**

- failure: A filename over CURL_MAX_INPUT_LENGTH returns CURLE_BAD_FUNCTION_ARGUMENT; if appending to the list fails with an allocation error, the whole accumulated list is freed and CURLE_OUT_OF_MEMORY returned.
- side_effect: With NULL: the filename list is freed; cookies are cleared and the engine disabled (data->cookies NULL) unless the cookie container is shared with data->share.

calls: [curl_slist_append](r8-container-types.md#u-851bb574d7cd), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb), [Curl_cookie_clearall](r12-cookie-jar-core.md#u-5cda38d4b3cb), [Curl_cookie_cleanup](r12-cookie-jar-core.md#u-7250284b8b00)

<a id="u-834964123ef2"></a>
### `cookielist`

`static CURLcode cookielist(struct Curl_easy *data, const char *ptr)` · [lib/setopt.c:L1488-L1546][f1]

Implements CURLOPT_COOKIELIST: clears, flushes, reloads, or adds individual cookie lines.

**Notes.**

- condition: "ALL" clears all cookies, "SESS" clears session cookies (both under the cookie share lock); "FLUSH" writes cookies to file; "RELOAD" reloads from the configured file list, honoring cookiesession via COOKIE_NOSESSION. NULL returns CURLE_OK without action.
- failure: If the cookie engine is not running it is created with Curl_cookie_init; failure there returns CURLE_OUT_OF_MEMORY. Lines over CURL_MAX_INPUT_LENGTH return CURLE_BAD_FUNCTION_ARGUMENT. "Set-Cookie:"-prefixed lines are parsed as HTTP header lines with COOKIE_HTTPHEADER; otherwise as Netscape format; both add with COOKIE_SECURE and COOKIE_NOPSL, and Curl_cookie_add's result propagates.

calls: [Curl_cookie_clearall](r12-cookie-jar-core.md#u-5cda38d4b3cb), [Curl_cookie_clearsess](r12-cookie-jar-core.md#u-885a7c3dd3d2), [Curl_flush_cookies](r12-cookie-jar-core.md#u-1736ce87dc1d), [Curl_cookie_loadfiles](r12-cookie-jar-core.md#u-1e8d227a05b1), [Curl_cookie_init](r12-cookie-jar-core.md#u-8570927d82e9), [Curl_cookie_add](r12-cookie-jar-core.md#u-111e5270b0e5)

<a id="u-9402e1405a40"></a>
### `protocol2num`

`static CURLcode protocol2num(const char *str, curl_prot_t *val)` · [lib/setopt.c:L176-L212][f1]

Converts a comma-separated protocol name list into a bitmask, starting from all protocols disabled.

**Notes.**

- condition: The token "all" sets every bit; empty tokens between commas are skipped.
- failure: NULL input or an all-empty list yielding zero bits returns CURLE_BAD_FUNCTION_ARGUMENT; an unknown scheme or one with h->run false returns CURLE_UNSUPPORTED_PROTOCOL immediately, leaving earlier OR'ed bits discarded with *val already set.

calls: [Curl_getn_scheme](r11-protocol-registry.md#u-cf475df7f08a), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-48dd489d3522"></a>
### `setproxy`

`static CURLcode setproxy(struct Curl_easy *data, const char *proxy)` · [lib/setopt.c:L1587-L1597][f1]

Stores the proxy string, skipping state invalidation when the proxy is unchanged.

**Notes.**

- condition: If a proxy was already set and the new string compares equal with strcmp, returns CURLE_OK without side effects; otherwise changeproxy clears proxy auth state and the new value is stored via Curl_setstropt, so NULL clears it.

calls: [changeproxy](r2-setopt-domains.md#u-c2986536a7e0), [Curl_setstropt](r2-setopt-core.md#u-82b62740d48c)

<a id="u-c2986536a7e0"></a>
### `changeproxy`

`static void changeproxy(struct Curl_easy *data)` · [lib/setopt.c:L949-L953][f1]

Invalidates proxy authentication state by clearing the proxy digest and authproxy structs.

**Notes.**

- side_effect: Cleans data->state.proxydigest via Curl_auth_digest_cleanup and memsets data->state.authproxy to zero.

calls: [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936)

<a id="u-8949805d7091"></a>
### `setstropt_userpwd`

`static CURLcode setstropt_userpwd(const char *option, char **userp, char **passwdp)` · [lib/setopt.c:L123-L153][f1]

Parses a user:password option string into separate user and password outputs, replacing prior values.

**Notes.**

- failure: Input over CURL_MAX_INPUT_LENGTH or a parse error from Curl_parse_login_details propagates before any stored value is modified.
- side_effect: The old password is zeroed via curlx_strzero before free; a NULL option clears both outputs.

calls: [Curl_parse_login_details](r7-url-and-credentials.md#u-f6421ec70808)

<a id="u-ec374970a45d"></a>
### `setstropt_interface`

`static CURLcode setstropt_interface(struct Curl_easy *data, char *option)` · [lib/setopt.c:L155-L169][f1]

Validates and stores the network interface option, treating an empty string as a clear.

**Notes.**

- failure: Curl_parse_interface is used as a syntax check; a parse error propagates without storing. NULL or "" clears STRING_INTERFACE_OPT.

calls: [Curl_parse_interface](r13-socket-filters.md#u-152d101cbfc1)

<a id="u-4af25aff5c3e"></a>
### `httpauth`

`static CURLcode httpauth(struct Curl_easy *data, bool proxy, unsigned long auth)` · [lib/setopt.c:L215-L250][f1]

Validates an HTTP or proxy authentication bitmask and stores it in data->set.

**Notes.**

- condition: CURLAUTH_DIGEST_IE is rewritten to CURLAUTH_DIGEST; NTLM and NEGOTIATE bits are dropped when not built in.
- failure: A mask other than CURLAUTH_NONE with no supported bit below CURLAUTH_ONLY returns CURLE_NOT_BUILT_IN and stores nothing.

<a id="u-56af31555a67"></a>
### `setopt_HTTP_VERSION`

`static CURLcode setopt_HTTP_VERSION(struct Curl_easy *data, long arg)` · [lib/setopt.c:L254-L289][f1]

Validates a requested HTTP version and stores it in data->set.httpwant.

**Notes.**

- condition: HTTP/2 and HTTP/3 versions are accepted only under USE_HTTP2 / USE_HTTP3 compile flags.
- failure: Unknown versions: below CURL_HTTP_VERSION_NONE returns CURLE_BAD_FUNCTION_ARGUMENT, otherwise CURLE_UNSUPPORTED_PROTOCOL.

<a id="u-2eb74d652b47"></a>
### `setopt_RTSP_REQUEST`

`static CURLcode setopt_RTSP_REQUEST(struct Curl_easy *data, long arg)` · [lib/setopt.c:L330-L341][f1]

Validates an RTSP request method value and stores it in data->set.rtspreq.

**Notes.**

- failure: Values at or below CURL_RTSPREQ_NONE or at or above CURL_RTSPREQ_LAST return CURLE_BAD_FUNCTION_ARGUMENT.

<a id="u-22660d906fcf"></a>
### `setopt_copypostfields`

`static CURLcode setopt_copypostfields(const char *ptr, struct UserDefined *s)` · [lib/setopt.c:L1788-L1824][f1]

Copies POST data into handle-owned memory, using either strlen or the pre-set postfieldsize.

**Notes.**

- condition: If postfieldsize is -1 or ptr is NULL, the string is duplicated with strlen semantics; otherwise exactly postfieldsize bytes are duplicated via curlx_memdup0, allocating even for size 0 so later pointer compares detect COPYPOSTFIELDS mode.
- failure: postfieldsize < -1 or a ptr over CURL_MAX_INPUT_LENGTH returns CURLE_BAD_FUNCTION_ARGUMENT; allocation failures return CURLE_OUT_OF_MEMORY with the old copy already freed in the strlen branch.
- side_effect: On success s->postfields points at the new copy and s->method becomes HTTPREQ_POST.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4)

<a id="u-caee2f8eac17"></a>
### `setopt_ech`

`static CURLcode setopt_ech(struct Curl_easy *data, const char *ptr)` · [lib/setopt.c:L1828-L1861][f1]

Parses the ECH option string into an ECH mode, optionally storing ECH config or public name material.

**Notes.**

- condition: NULL or "false" disables ECH; "grease", "true", and "hard" select the matching mode; "ecl:<config>" and "pn:<name>" store the payload and default the mode to CURLECH_HARD if none was set.
- failure: Strings over CURL_MAX_INPUT_LENGTH or unrecognized values return CURLE_BAD_FUNCTION_ARGUMENT; storage failures from Curl_setstropt propagate.

<a id="u-8fe9ace0aa8c"></a>
### `setopt_mimepost`

`static CURLcode setopt_mimepost(struct Curl_easy *data, curl_mime *mimep)` · [lib/setopt.c:L1382-L1407][f1]

Installs a curl_mime as the POST body, switching the request method to MIME POST.

**Notes.**

- failure: Allocating the internal mimepart can fail with CURLE_OUT_OF_MEMORY; Curl_mime_set_subparts' result propagates, and on failure the method is not changed.
- side_effect: On success the legacy httppost form data is cleaned and freed (data->state.formp released, data->state.mimepost NULLed) and opt_no_body is cleared.

calls: [Curl_mime_set_subparts](r2-mime-api.md#u-a58bc4c6839f), [Curl_mime_initpart](r2-mime-api.md#u-c25b72491d98), [Curl_mime_cleanpart](r2-mime-api.md#u-358147b42434)

<a id="u-532041b3fbad"></a>
### `setopt_share`

`static CURLcode setopt_share(struct Curl_easy *data, struct Curl_share *set)` · [lib/setopt.c:L1411-L1429][f1]

Links or relinks the easy handle to a share object, refusing while a connection is attached.

**Notes.**

- failure: With data->conn set, it logs via infof and returns CURLE_BAD_FUNCTION_ARGUMENT without changing shares; otherwise it unlinks from the old share first, and only on success links to a valid new share (GOOD_SHARE_HANDLE). The unlink result propagates when linking is skipped.

calls: [Curl_share_easy_unlink](r6-share-api.md#u-8cd7b4636d92), [Curl_share_easy_link](r6-share-api.md#u-45aa6f6d595e)

<a id="u-c7018faa9f8d"></a>
### `setopt_cptr_ftp`

`static CURLcode setopt_cptr_ftp(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L2195-L2227][f1]

Applies FTP and wildcard-related string options.

**Notes.**

- condition: FTPPORT stores the string and sets ftp_use_port to whether a non-empty FTPPORT string is stored. KRBLEVEL always returns CURLE_NOT_BUILT_IN (removed in 8.17.0). CHUNK_DATA and FNMATCH_DATA store raw user pointers for the wildcard callbacks.

<a id="u-fb810e915f8d"></a>
### `setopt_cptr_http_mqtt`

`static CURLcode setopt_cptr_http_mqtt(struct Curl_easy *data, CURLoption option, char…` · [lib/setopt.c:L2010-L2137][f1]

Applies HTTP and MQTT string options: POST data variants, encoding, cookies, referer, and user agent.

**Notes.**

- condition: POSTFIELDS stores the caller pointer and frees any prior copy; method becomes HTTPREQ_POST. ACCEPT_ENCODING with "" stores a generated all-encodings header string, NULL stores nothing. COOKIEJAR activates the cookie engine if not running. REFERER stores the new string first, then frees the old bufref, so self-referencing input is safe.
- failure: ACCEPT_ENCODING "" returns CURLE_OUT_OF_MEMORY if the encoding list cannot be built; COOKIEJAR activation failure returns CURLE_OUT_OF_MEMORY; COPYPOSTFIELDS delegates to setopt_copypostfields; other results propagate.

calls: [setopt_copypostfields](r2-setopt-domains.md#u-22660d906fcf), [cookielist](r2-setopt-domains.md#u-834964123ef2), [cookiefile](r2-setopt-domains.md#u-fae53546d861), [Curl_get_content_encodings](r4-content-encoding-decode.md#u-c041af0423b9), [Curl_cookie_init](r12-cookie-jar-core.md#u-8570927d82e9), [Curl_bufref_free](r14-bufref-buffers.md#u-2c7e087ba1d6)

<a id="u-f09d229fdd80"></a>
### `setopt_cptr_misc`

`static CURLcode setopt_cptr_misc(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L2276-L2490][f1]

Applies the bulk of string and data-pointer options: URL, credentials, callbacks' user data, protocol masks, HSTS, and alt-svc.

**Notes.**

- condition: URL stores the string and mirrors it into state.url via Curl_bufref_set. USERPWD parses and stores username/password, freeing temporaries only after successful stores. PROTOCOLS_STR/REDIR_PROTOCOLS_STR parse a comma list via protocol2num; NULL resets to defaults (CURLPROTO_64ALL / CURLPROTO_REDIR). CUSTOMREQUEST changes only the request keyword, not the method.
- failure: HSTS initializes the cache lazily (CURLE_OUT_OF_MEMORY on failure) and appends the filename to state.hstslist, freeing the whole list on append failure; NULL clears the list and frees the private cache unless shared. ALTSVC initializes data->asi and loads the file via Curl_altsvc_load on success. TLSAUTH options always return CURLE_NOT_BUILT_IN. RTSP_SESSION_ID unlinks the prior session origin before storing.
- side_effect: Numerous *DATA options store raw caller pointers into s (write/read/debug/progress/seek/ioctl/sockopt/opensocket/resolver/closesocket/prereq/errorbuffer/writeheader/private_data/rtp_out/hsts read/write).

calls: [setstropt_userpwd](r2-setopt-domains.md#u-8949805d7091), [protocol2num](r2-setopt-domains.md#u-9402e1405a40), [setopt_ech](r2-setopt-domains.md#u-caee2f8eac17), [Curl_hsts_init](r10-hsts-cache.md#u-85f212dd39be), [Curl_hsts_cleanup](r10-hsts-cache.md#u-08a59bb64394), [Curl_altsvc_init](r11-alt-svc-cache.md#u-49ff500998f4), [Curl_altsvc_load](r11-alt-svc-cache.md#u-6c9d17b7c86c), [curl_slist_append](r8-container-types.md#u-851bb574d7cd), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368), [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2)

<a id="u-0639344d37a2"></a>
### `setopt_cptr_net`

`static CURLcode setopt_cptr_net(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L2230-L2274][f1]

Applies network-binding string options: interface, DNS overrides, Unix sockets, and DoH URL.

**Notes.**

- condition: INTERFACE delegates to setstropt_interface (empty string clears). UNIX_SOCKET_PATH sets abstract_unix_socket FALSE, ABSTRACT_UNIX_SOCKET sets it TRUE, both storing the same string slot. DOH_URL sets data->set.doh to whether a DOH string is stored.
- failure: DNS_SERVERS/INTERFACE/LOCAL_IP4/LOCAL_IP6 are handled only under USE_RESOLV_ARES; otherwise they fall to default and return CURLE_UNKNOWN_OPTION. setstropt_interface's parse failure propagates.

calls: [setstropt_interface](r2-setopt-domains.md#u-ec374970a45d)

<a id="u-45438112f531"></a>
### `setopt_cptr_proxy`

`static CURLcode setopt_cptr_proxy(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L1599-L1779][f1]

Applies proxy-related string options: proxy credentials, proxy URL, TLS material, and HAProxy settings.

**Notes.**

- condition: PROXYUSERPWD parses user:password then URL-decodes each component into STRING_PROXYUSERNAME/STRING_PROXYPASSWORD with REJECT_ZERO. HAPROXY_CLIENT_IP sets haproxyprotocol to whether a client IP string is stored. PROXY_CAINFO and PROXY_CAPATH set proxy_ssl.custom_cafile/custom_capath on success. PROXY and PRE_PROXY store the strings; an empty PROXY means explicitly no proxy, NULL defers to environment.
- failure: Ciphers, CRL, issuer cert, CA path, and pinned key options return CURLE_NOT_BUILT_IN when the SSL backend lacks the matching support; unknown options return CURLE_UNKNOWN_OPTION; decode or store failures propagate and partially stored credentials may remain cleared.

calls: [setstropt_userpwd](r2-setopt-domains.md#u-8949805d7091), [setproxy](r2-setopt-domains.md#u-48dd489d3522), [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

**Uncertainties.**

- After a failed PROXYUSERPWD decode, whether the cleared proxy username/password strings are restored is not visible here; the code clears both strings before decoding and frees temporaries unconditionally.

<a id="u-05a8edfab35f"></a>
### `setopt_cptr_ssh`

`static CURLcode setopt_cptr_ssh(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L2141-L2191][f1]

Applies SSH string options: key files, host key fingerprints, knownhosts file, and callback user data.

**Notes.**

- side_effect: SSH_KEYDATA sets ssh_keyfunc_userp; SSH_HOSTKEYDATA (libssh2 only) sets ssh_hostkeyfunc_userp; the file-name options store via Curl_setstropt.

<a id="u-9f7d5d3ea02f"></a>
### `setopt_cptr_ssl`

`static CURLcode setopt_cptr_ssl(struct Curl_easy *data, CURLoption option, char *ptr)` · [lib/setopt.c:L1868-L2006][f1]

Applies TLS and SSH shared string options: certificates, keys, CA material, engines, and ECH.

**Notes.**

- condition: CURLOPT_KEYPASSWD works for both TLS and SSH. CAINFO stores the file and sets ssl.custom_cafile on success. RANDOM_FILE and EGDSOCKET are accepted and ignored. SSLENGINE stores the string and then loads the engine via Curl_ssl_set_engine when non-empty.
- failure: CAPATH, CRLFILE, cipher lists, TLS 1.3 ciphers, issuer cert, EC curves, signature algorithms, pinned key, SSL_CTX data each return CURLE_NOT_BUILT_IN without the matching SSLSUPP capability; unknown options return CURLE_UNKNOWN_OPTION; ECH delegates to setopt_ech.

calls: [Curl_setstropt](r2-setopt-core.md#u-82b62740d48c), [setopt_ech](r2-setopt-domains.md#u-caee2f8eac17)

**Uncertainties.**

- The effect of Curl_ssl_set_engine failure on the already-stored engine string is decided inside the SSL backend, not here.

<a id="u-27930137a17a"></a>
### `setopt_long_bool`

`static CURLcode setopt_long_bool(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L344-L750][f1]

Applies all boolean-style long options into per-feature flags in the easy handle's UserDefined set.

**Notes.**

- condition: enabled is !!arg. NOBODY sets HTTPREQ_HEAD and clearing it reverts HEAD to GET; UPLOAD/PUT enabled set HTTPREQ_PUT and clear opt_no_body, disabled set HTTPREQ_GET; POST enabled sets HTTPREQ_POST, disabled HTTPREQ_GET; HTTPGET enabled sets HTTPREQ_GET only. HTTP_TRANSFER/CONTENT_DECODING store the inverted value.
- failure: Unknown options return CURLE_UNKNOWN_OPTION; VERIFYSTATUS and DOH_SSL_VERIFYSTATUS return CURLE_NOT_BUILT_IN when certificate-status is unsupported; CERTINFO returns CURLE_NOT_BUILT_IN when SSL lacks SSLSUPP_CERTINFO; TCP_FASTOPEN returns CURLE_NOT_BUILT_IN when no fast-open mechanism is compiled.
- side_effect: SSL/proxy verify peer/host options also call Curl_ssl_conn_config_update; VERIFYHOST treats 1 and 2 identically and sets ok=2; args above the per-option bound or negative produce only an infof warning, never an error.

calls: [Curl_ssl_conn_config_update](r1-tls-configuration.md#u-69e1eda38557), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

**Uncertainties.**

- Which cases compile depends on feature macros (HTTP, proxy, GSSAPI, SSH, TFTP, etc.); under a disabled feature the same option reaches default and returns CURLE_UNKNOWN_OPTION.

<a id="u-6bdcb1ce02dd"></a>
### `setopt_long_http`

`static CURLcode setopt_long_http(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L1005-L1077][f1]

Applies HTTP-related long options, or returns CURLE_UNKNOWN_OPTION for all when HTTP is disabled.

**Notes.**

- condition: FOLLOWLOCATION accepts 0-3; HEADEROPT sets sep_headers from CURLHEADER_SEPARATE; STREAM_WEIGHT accepts 1-256 only with HTTP/2 or HTTP/3, otherwise CURLE_NOT_BUILT_IN.
- failure: MAXREDIRS clamps via value_range(-1..0x7fff); POSTREDIR below CURL_REDIR_GET_ALL returns bad argument; HTTPSIG_ALGORITHM rejects unknown algorithm values.
- side_effect: HTTPSIG_ALGORITHM adds or removes the CURLAUTH_HTTPSIG bit in s->httpauth depending on a nonzero argument.

calls: [httpauth](r2-setopt-domains.md#u-4af25aff5c3e), [setopt_HTTP_VERSION](r2-setopt-domains.md#u-56af31555a67)

<a id="u-d3e2ed69328a"></a>
### `setopt_long_misc`

`static CURLcode setopt_long_misc(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L1180-L1256][f1]

Applies remaining long options: time conditions, sizes, resume, MIME flags, HSTS control, and alt-svc.

**Notes.**

- failure: POSTFIELDSIZE, INFILESIZE, RESUME_FROM reject values below -1; TIMECONDITION rejects values outside [CURL_TIMECOND_NONE, CURL_TIMECOND_LAST); HSTS enable failing Curl_hsts_init returns CURLE_OUT_OF_MEMORY; ALTSVC_CTRL delegates fully to Curl_altsvc_ctrl.
- side_effect: Setting POSTFIELDSIZE larger than the current size frees s->str_copypostfields and NULLs s->postfields, invalidating a prior COPYPOSTFIELDS. HSTS_CTRL enable lazily creates the HSTS cache; disable frees the private cache and the hstslist unless shared with data->share, in which case it only detaches.

calls: [Curl_hsts_init](r10-hsts-cache.md#u-85f212dd39be), [Curl_hsts_cleanup](r10-hsts-cache.md#u-08a59bb64394), [curl_slist_free_all](r8-container-types.md#u-098fac37e5cb), [Curl_altsvc_ctrl](r11-alt-svc-cache.md#u-a466d0e058ea)

<a id="u-f332e153df94"></a>
### `setopt_long_net`

`static CURLcode setopt_long_net(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L763-L890][f1]

Applies network-related long options: timeouts, ports, buffer sizes, keepalive, and address settings.

**Notes.**

- condition: DNS_CACHE_TIMEOUT of -1 stores -1 (never expire); any other value goes through setopt_set_timeout_sec. MAXCONNECTS of 0 after clamping stores DEFAULT_CONNCACHE_SIZE. CONNECT_ONLY accepts 0-2, with 2 also setting connect_only_ws.
- failure: PORT/LOCALPORT/LOCALPORTRANGE outside 0-65535 return CURLE_BAD_FUNCTION_ARGUMENT; LOW_SPEED_LIMIT and MAXFILESIZE reject negatives; other options clamp via value_range (buffer sizes to READBUFFER/UPLOADBUFFER bounds, LOW_SPEED_TIME to USHRT_MAX); unknown options return CURLE_UNKNOWN_OPTION.

calls: [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706), [setopt_set_timeout_sec](r2-setopt-core.md#u-d1d1066db815), [setopt_set_timeout_ms](r2-setopt-core.md#u-b878e4fd8733)

<a id="u-f0f4322fbdc5"></a>
### `setopt_long_proto`

`static CURLcode setopt_long_proto(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L1079-L1178][f1]

Applies protocol-specific long options for TFTP, netrc, FTP, RTSP, SSH, WebSocket, and protocol masks.

**Notes.**

- failure: Enum-style options (NETRC, FTP_FILEMETHOD, FTP_SSL_CCC, FTPSSLAUTH, FTP_CREATE_MISSING_DIRS) reject out-of-range values; NEW_FILE_PERMS and NEW_DIRECTORY_PERMS accept only 0-0777; RTSP CSeq options clamp via value_range(0..INT_MAX); TFTP_BLKSIZE clamps to its min/max.
- condition: PROTOCOLS and REDIR_PROTOCOLS store the raw long as a bitmask without validation; WS_OPTIONS extracts two bit flags; SSH_AUTH_TYPES stores the raw value.

calls: [setopt_RTSP_REQUEST](r2-setopt-domains.md#u-2eb74d652b47)

<a id="u-08ef844a2c87"></a>
### `setopt_long_proxy`

`static CURLcode setopt_long_proxy(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L955-L993][f1]

Applies proxy-related long options: port, auth bitmask, proxy type, and SOCKS5 auth.

**Notes.**

- failure: PROXYPORT outside 0-UINT16_MAX returns CURLE_BAD_FUNCTION_ARGUMENT; PROXYTYPE outside [CURLPROXY_HTTP, CURLPROXY_HTTPS3] returns bad argument, and CURLPROXY_HTTPS3 returns CURLE_NOT_BUILT_IN without HTTP/3 proxy support; SOCKS5_AUTH with bits beyond BASIC|GSSAPI|ONLY returns CURLE_NOT_BUILT_IN, and ONLY without BASIC or GSSAPI returns bad argument.
- side_effect: Changing PROXYPORT to a different value triggers changeproxy, discarding cached proxy auth state.

calls: [changeproxy](r2-setopt-domains.md#u-c2986536a7e0), [httpauth](r2-setopt-domains.md#u-4af25aff5c3e)

<a id="u-e6716615b75e"></a>
### `lib/setopt.c:setopt_long_proxy`

`static CURLcode setopt_long_proxy(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L995-L1002][f1]

No-op stub used when proxy support is disabled: ignores all arguments and returns CURLE_UNKNOWN_OPTION.

<a id="u-1149805f64c0"></a>
### `setopt_long_ssl`

`static CURLcode setopt_long_ssl(struct Curl_easy *data, CURLoption option, long arg)` · [lib/setopt.c:L892-L946][f1]

Applies SSL-related long options, or returns CURLE_UNKNOWN_OPTION for all when SSL is not built in.

**Notes.**

- failure: CA_CACHE_TIMEOUT returns CURLE_NOT_BUILT_IN when the backend lacks SSLSUPP_CA_CACHE; SSL_FALSESTART always returns CURLE_NOT_BUILT_IN; USE_SSL rejects values outside [CURLUSESSL_NONE, CURLUSESSL_LAST); SSLENGINE_DEFAULT clears STRING_SSL_ENGINE then calls Curl_ssl_set_engine_default, propagating its result.
- condition: SSL_OPTIONS and PROXY_SSL_OPTIONS store only the low byte; SSL_ENABLE_NPN is accepted and ignored.

calls: [Curl_setopt_SSLVERSION](r2-setopt-core.md#u-ceb2158e7388)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/setopt.c
