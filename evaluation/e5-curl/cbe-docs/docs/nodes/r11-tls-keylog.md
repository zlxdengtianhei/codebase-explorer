# TLS key logging

**Capability.** The SSLKEYLOGFILE feature: opening/closing the log file from the environment, appending formatted key lines, the OpenSSL keylog hook, and fallback stubs for builds without a supported TLS backend.

Use keylog.c functions to understand how key material reaches the file; openssl.c-keylog wires the OpenSSL backend into it. The stub group documents the no-backend case.

**Depended on by.**

- [OpenSSL connection lifecycle](r11-ossl-conn-lifecycle.md) · model-inferred · 0 edge(s)

Parent: [TLS backends \(OpenSSL-based\)](r11-tls-security.md)

## Units (6)

<a id="u-5a49afefe6bd"></a>
### `openssl.c-keylog`

`static void ossl_keylog_callback(const SSL *ssl, const char *line)` · [lib/vtls/openssl.c:L672-L677][f1]

TLS key material logging for the SSLKEYLOGFILE feature.

When the OpenSSL build offers the native keylog callback, ossl_keylog_callback simply forwards each line to Curl_tls_keylog_write_line. Without it, ossl_log_tls12_secret reconstructs the CLIENT_RANDOM for TLS 1.2-and-older handshakes: it marks the OpenSSL error stack, fetches the session, and returns early (popping to the mark) when there is no session or logging already happened. It copies the client random and master key, pops the error mark, and silently skips when the master key length is <= 0 (handshake not far enough, or a TLS 1.3 session under old headers); otherwise it sets *keylog_done and writes the secret via Curl_tls_keylog_write. Both are compiled only when key logging is not handled upstream.

<a id="u-f9ab5ea59d93"></a>
### `keylog.c-tls-backend-stubs`

`bool Curl_tls_keylog_enabled(void)` · [lib/vtls/keylog.c:L152-L155][f2]

Fallback definitions compiled when none of the supported TLS backends are built.

Curl_tls_keylog_enabled always returns FALSE and Curl_tls_keylog_file_name always returns NULL, so callers behave as if key logging was never enabled.

<a id="u-619a5e3dff81"></a>
### `Curl_tls_keylog_open`

`void Curl_tls_keylog_open(void)` · [lib/vtls/keylog.c:L38-L57][f2]

Opens the TLS key log file on first use: reads the SSLKEYLOGFILE environment variable and, if set, opens that path in append-text mode via curlx_fopen, storing the FILE* in a static.

On Windows an unbuffered stream is requested, elsewhere line buffering with a 4096-byte buffer; if setvbuf fails, the file is closed and the handle reset to NULL, leaving keylogging disabled. If already open, or the variable is unset, nothing happens. The file name is retained in a static for verbose logging.

**Notes.**

- side_effect: Sets statics keylog_file_fp and keylog_file_name; keylog_file_name stores the getenv pointer directly, not a copy.

**Uncertainties.**

- The stored name pointer's lifetime depends on the environment string; not provable from this file.

<a id="u-8de4deedf443"></a>
### `Curl_tls_keylog_close`

`void Curl_tls_keylog_close(void)` · [lib/vtls/keylog.c:L59-L65][f2]

Closes the open key log file if any, resetting the static FILE* to NULL so later writes fail; no-op otherwise.

<a id="u-c839af08b08d"></a>
### `Curl_tls_keylog_write`

`bool Curl_tls_keylog_write(const char *label, const unsigned char *client_random, siz…` · [lib/vtls/keylog.c:L105-L148][f2]

Formats and appends a standard keylog entry 'LABEL <hex client random> <hex secret>'.

Sanity checks each returning FALSE with no write: file not open, random_size below CLIENT_RANDOM_SIZE (also asserted), label longer than KEYLOG_LABEL_MAXLEN, or secretlen 0 or above SECRET_MAXLEN. Builds the line in a stack buffer sized for the maximum label, 32-byte client random, and 48-byte secret, hex-encodes each byte with Curl_hexbyte, separates fields with spaces, appends LF and NUL, and writes with fputs. Returns TRUE after the write.

uses: [keylog.h module code (L1–L75)][f3]

**Uncertainties.**

- DEBUGASSERT is the only guard on random_size; behavior of the non-debug build depends on the assert configuration.

<a id="u-3a0fb00fb725"></a>
### `Curl_tls_keylog_write_line`

`bool Curl_tls_keylog_write_line(const char *line)` · [lib/vtls/keylog.c:L77-L103][f2]

Appends one line to the open key log file.

Returns FALSE without writing when the file is not open, line is NULL, the line is empty, or its length exceeds 254 bytes (a 256-byte buffer must also hold an appended LF and NUL). Otherwise copies the line into a stack buffer, appends LF unless the line already ends with one, NUL-terminates, and writes via fputs — chosen over libcurl's fprintf replacement for thread safety. Returns TRUE after a completed write.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/openssl.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vtls/keylog.c
[f3]: ../../../../../../eval/curl-2c04412/lib/vtls/keylog.h
