# Version & Feature Reporting

**Capability.** Reports libcurl's version and build capabilities: static protocol/feature tables, third-party library version formatters feeding curl_version's combined string, compile-time feature-presence predicates, and curl_version_info which refreshes and returns the static version_info struct (the requested CURLversion stamp is ignored).

Use this subtree to learn what a build supports and which third-party libraries it embeds. curl_version gives a one-line string; curl_version_info gives structured protocol names and the feature bitmask.

Parent: [curl Codebase](r3-curl-codebase.md)

## Units (5)

<a id="u-e59bb6f46d91"></a>
### `version-c-third-party-version-helpers`

`static void brotli_version(char *buf, size_t bufsz)` · [lib/version.c:L78-L85][f1]

This region gathers the small static helpers that format third-party library versions into caller-provided buffers for inclusion in curl's version strings, plus the USE_IDN feature macro.

Each helper is compiled only when its library is enabled. brotli_version decodes BrotliDecoderVersion()'s packed number: major is the top 8 bits, minor bits 12-23, patch the low 12 bits, formatted as 'brotli/major.minor.patch'. zstd_version divides ZSTD_versionNumber() decimal-style (major = v/10000, minor = remainder/100, patch = final remainder) as 'zstd/major.minor.patch'. psl_version prefers the numeric API: when PSL_VERSION_MAJOR exists and is at least 0.11, it queries psl_check_version_number(0) and prints major>>16, (num>>8)&0xff, num&0xff; otherwise it prints psl_get_version(). idn_version prints 'libidn2/<idn2_check_version(NULL)>', or the fixed strings 'WinIDN' or 'AppleIDN' depending on which IDN backend macro is defined. All formatting goes through curl_msnprintf, so output is truncated to the buffer size.

calls: [curl_version](r3-version-info.md#u-c6d444fd09bd), [curl_version_info](r3-version-info.md#u-a10e1e8ea546)

**Uncertainties.**

- Whether psl_check_version_number exists at compile time depends on the PSL_VERSION_MAJOR comparison, not visible here.
- curl_msnprintf's exact truncation semantics live outside this file.

<a id="u-c6d444fd09bd"></a>
### `curl_version`

`char *curl_version(void)` · [lib/version.c:L140-L283][f1]

Builds a space-separated string of the libcurl version and every enabled third-party library version, returned from a function-local static buffer of 300 bytes.

Each component is formatted into a small local buffer (or produced by Curl_ssl_version/Curl_ssh_version/Curl_http2_ver/Curl_quic_ver/Curl_ldap_version) and its pointer is appended to a src[] array capped at VERSION_PARTS (16) entries; a DEBUGASSERT checks the cap. In DEBUGBUILD builds, if the environment variable CURL_DEBUG_VERSION is set, the function prints it into the output and returns immediately, bypassing all library detection. The enabled components are: libcurl itself, TLS backend, zlib, brotli, zstd, c-ares, IDN, libpsl, SSH, HTTP/2 (nghttp2, only if HTTP not disabled), HTTP/3, gsasl, GSS-API (variant-dependent: AppleGSS, libgss with GSS_VERSION, mit-krb5 with CURL_KRB5_VERSION, or plain mit-krb5), and LDAP (unless disabled). The concatenation loop copies each part preceded by a space (except the first) while outlen exceeds n+2; if the next part would not fit, it breaks, silently truncating the remainder. The result is always NUL-terminated. Thread safety relies on every invocation producing the identical string, so concurrent writes never store temporary data like zeros into the static buffer.

calls: [version-c-third-party-version-helpers](r3-version-info.md#u-e59bb6f46d91), [Curl_ldap_version](r11-ldap-protocol.md#u-c335792179a7)

**Uncertainties.**

- The buffer is 300 bytes and VERSION_PARTS is 16; whether any real configuration can exceed either is not provable from this file.
- Behavior of Curl_ssl_version, Curl_ssh_version, Curl_http2_ver, Curl_quic_ver, Curl_ldap_version, and DEBUGASSERT outside this file is unverified.
- getenv thread safety during concurrent first calls is not addressed in the source.

<a id="u-c5df8dc6ec6a"></a>
### `version-c-protocol-and-feature-tables`

`struct feat` · [lib/version.c:L419-L423][f1]

This region defines the compile-time data curl_version_info serves.

supported_protocols is a NULL-terminated array of protocol name strings, each entry guarded by its disable/enable macros: 'dict', 'file', 'ftp'/'ftps', 'gopher'/'gophers', 'http'/'https', 'imap'/'imaps', 'ldap' plus 'ldaps' only when LDAPS is enabled and the LDAP library supports SSL (OpenLDAP with USE_SSL, or non-OpenLDAP with HAVE_LDAP_SSL), 'mqtt'/'mqtts', 'pop3'/'pop3s', 'rtsp', 'scp' and 'sftp' under USE_SSH, 'smtp'/'smtps', 'telnet', 'tftp', and 'ws'/'wss' when WebSockets (and HTTP) are enabled. The FEATURE macro and struct feat define a table of {name, present-check function, bitmask} entries, alphabetically sorted, for every optional feature; most have a NULL present check (always present when compiled in), while ECH, HTTPS-proxy, and IDN route through runtime check functions. Two conditions are compile-enforced: enabling ECH without USE_HTTPSRR is a #error, and the AppleSecTrust vs NativeCA feature is exclusive per USE_SSL. The static feature_names array (one slot per table entry) and the version_info struct are initialized with fixed libcurl metadata (CURLVERSION_NOW, LIBCURL_VERSION/NUM, CURL_OS), NULL version pointers, and the protocols array; the features bitmask starts at 0 and pointers are filled at runtime. A comment requires these runtime-check results to stay constant between curl_global_init and curl_global_cleanup.

uses: [version-c-feature-presence-checks](r3-version-info.md#u-71c011495b07), [curl_version_info](r3-version-info.md#u-a10e1e8ea546)

**Uncertainties.**

- CURL_ARRAYSIZE and the exact curl_version_info_data field order are defined outside this file.
- Whether the protocols list ordering matches the documented alphabetical guarantee beyond source inspection is assumed from the layout.

<a id="u-71c011495b07"></a>
### `version-c-feature-presence-checks`

`static int idn_present(curl_version_info_data *info)` · [lib/version.c:L382-L390][f1]

Three small compile-time-conditional predicates used by the features table.

idn_present, compiled when any IDN backend is enabled, returns TRUE unconditionally for Win32 or Apple IDN (ignoring info), otherwise reports !!info->libidn for libidn2 — so with libidn2 the feature reflects whether idn2_check_version(IDN2_VERSION) yielded a string earlier. https_proxy_present, compiled when SSL, proxy, and HTTP are all enabled, returns Curl_ssl_supports(NULL, SSLSUPP_HTTPS_PROXY). ech_present, compiled when SSL and ECH are enabled, returns Curl_ssl_supports(NULL, SSLSUPP_ECH). Each ignores its info parameter where the answer is static.

calls: [curl_version_info](r3-version-info.md#u-a10e1e8ea546)

**Uncertainties.**

- Curl_ssl_supports semantics (which backends support these flags) are defined in vtls and not visible here.
- Whether info->libidn was populated by a prior curl_version_info call is a cross-call contract not provable in this file.

<a id="u-a10e1e8ea546"></a>
### `curl_version_info`

`curl_version_info_data *curl_version_info(CURLversion stamp)` · [lib/version.c:L574-L676][f1]

Returns a pointer to the static version_info struct, refreshing its library-version fields and rebuilding the feature bitmask and names array on each call; the requested CURLversion stamp is ignored ((void)stamp), so every caller receives CURLVERSION_NOW-shaped data regardless of argument.

First it fills version pointers into static buffers (ssh_buf sized 80, ssl_buffer 200 under multi-SSL else 80, brotli/zstd/quic buffers 80): the TLS version via Curl_ssl_version, zlib via zlibVersion(), c-ares via ares_version (also storing ares_num), libidn via idn2_check_version(IDN2_VERSION) which yields NULL when the linked libidn2 is older than the compiled-against version, SSH via Curl_ssh_version, brotli via BrotliDecoderVersion plus brotli_version formatting, zstd similarly, nghttp2 via nghttp2_version(0), QUIC via Curl_quic_ver, and gsasl via gsasl_check_version(NULL). Then it walks features_table: for each entry with a NULL present check or a truthy present(&version_info), it ORs the entry's bitmask into features and appends the name to feature_names; NULL-present entries are unconditional for the build, conditional ones can report absent at runtime. In DEBUGBUILD builds CURL_VERSION_CURLDEBUG is force-added for compatibility. The names array is NULL-terminated at slot n and the accumulated mask stored in version_info.features. No error paths exist; the same static struct is returned to all callers.

uses: [version-c-protocol-and-feature-tables](r3-version-info.md#u-c5df8dc6ec6a); calls: [version-c-feature-presence-checks](r3-version-info.md#u-71c011495b07), [version-c-third-party-version-helpers](r3-version-info.md#u-e59bb6f46d91)

**Uncertainties.**

- Concurrent calls share the static buffers and struct; the source gives no locking here, so thread safety relies on results being identical across calls.
- The ignored stamp parameter means callers asking for an older CURLversion receive current-layout data; how the header accommodates that is outside this file.
- Behavior of Curl_ssl_supports and the external version functions is defined elsewhere.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/version.c
