# Tool platform support

**Capability.** Platform-specific file sizing (VMS), default CA bundle discovery (Windows), PKCS#11 URI detection, and environment CA path setup.

These helpers adjust behavior for VMS and Windows and fill in CA locations when the user did not specify them; invoked from transfer preparation and operate().

**Depended on by.**

- [Transfer preparation](r7-tool-transfer-prep.md) · graph-confirmed · 5 edge(s)

Parent: [Command-line tool](r7-tool-cli.md)

## Units (6)

<a id="u-53b42f2e5751"></a>
### `src/tool_operate.c:VmsSpecialSize`

`static curl_off_t VmsSpecialSize(const char *name, const curlx_struct_stat *stat_buf)` · [src/tool_operate.c:L174-L184][f1]

VMS-only: for variable-record formats (FAB$C_VAR/VFC) whose st_size is unreliable it returns vms_realfilesize(name); otherwise the stat st_size.

calls: [vms_realfilesize](r7-tool-platform-support.md#u-af23344f7ec4)

<a id="u-af23344f7ec4"></a>
### `vms_realfilesize`

`static curl_off_t vms_realfilesize(const char *name, const curlx_struct_stat *stat_buf)` · [src/tool_operate.c:L143-L166][f1]

VMS-only helper that reads the whole named file in 8KB chunks to count its real byte size; returns 0 when fopen fails.

<a id="u-cdc643484f0d"></a>
### `win32_setup_certs`

`static CURLcode win32_setup_certs(struct OperationConfig *config)` · [src/tool_operate.c:L2225-L2244][f1]

Windows-only default CA setup when neither --capath nor --cacert is given: with CURL_CA_SEARCH_SAFE it locates curl-ca-bundle.crt beside the executable and copies the path (OOM on strdup failure); otherwise on desktop Windows without CA search disabled it delegates to FindWin32CACert (error propagates).

Non-Windows builds compile to a no-op returning CURLE_OK.

<a id="u-5220dac745d0"></a>
### `win32_using_schannel`

`static bool win32_using_schannel(CURLcode *resultp)` · [src/tool_operate.c:L2198-L2223][f1]

Windows-only, caches whether the TLS backend is Schannel in a static (-1 unchecked, 0 no, 1 yes).

On first call it creates a temporary easy handle, reads CURLINFO_TLS_SSL_PTR, and records the backend; OOM or getinfo failure passes the error back via *resultp and returns TRUE. Later calls just report the cached answer.

<a id="u-8a03c4717849"></a>
### `src/tool_operate.c:is_pkcs11_uri`

`static bool is_pkcs11_uri(const char *string)` · [src/tool_operate.c:L122-L130][f1]

Returns TRUE when the string starts with the case-insensitive prefix "pkcs11:", otherwise FALSE.

<a id="u-96c65cb76881"></a>
### `cacertpaths`

`static CURLcode cacertpaths(struct OperationConfig *config)` · [src/tool_operate.c:L2261-L2306][f1]

Fills CA locations from the environment, skipping when SSL is absent, the user set cacert/capath, or peer verification is fully disabled (insecure_ok with no DoH URL or DoH also insecure).

On Windows, Schannel backs out since CA location is only honored via explicit --cacert. CURL_CA_BUNDLE sets cacert; otherwise SSL_CERT_DIR sets capath and, if that succeeded, SSL_CERT_FILE sets cacert; strdup failures return CURLE_OUT_OF_MEMORY. Finally win32_setup_certs may supply the default bundle; on any failure both capath and cacert are cleared.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_operate.c
