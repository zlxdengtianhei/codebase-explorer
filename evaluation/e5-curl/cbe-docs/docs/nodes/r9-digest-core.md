# Digest core (vauth/digest)

**Capability.** Parses Digest challenge directives, converts digests to ASCII, escapes quoted strings, and generates responses for HTTP Digest (MD5/SHA-256/SHA-512-256) and the DIGEST-MD5 SASL mechanism, plus full state cleanup.

Use this child to trace how challenge key=value pairs become a response message; the algorithm dispatch parameterizes one response builder over hash/format pairs. The HTTP Digest child consumes its decode/create/cleanup entry points.

**Depends on.**

- [Case-insensitive strings](r9-caseless-strings.md) · graph-confirmed · 9 edge(s)
- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 13 edge(s)
- [MD5 digest service](r12-md5-digest.md) · graph-only · 32 edge(s)
- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · graph-only · 31 edge(s)
- [string parsing primitives](r11-strparse-word-scanning.md) · graph-only · 30 edge(s)

**Depended on by.**

- [HTTP Digest](r9-digest-http.md) · graph-confirmed · 6 edge(s)

Parent: [HTTP/SOCKS authentication](r9-http-auth.md)

## Units (13)

<a id="u-e3cd8f61a7a9"></a>
### `Curl_auth_create_digest_http_message`

`CURLcode Curl_auth_create_digest_http_message(struct Curl_easy *data, struct Curl_cre…` · [lib/vauth/digest.c:L1000-L1031][f1]

Dispatches HTTP Digest response generation to auth_create_digest_http_message with the hash/format pair matching digest->algo: algorithms up to ALGO_MD5SESS use MD5 with auth_digest_md5_to_ascii, up to ALGO_SHA256SESS use SHA-256, and up to ALGO_SHA512_256SESS use SHA-512/256 when built with CURL_HAVE_SHA512_256.

An algo outside these ranges, or SHA-512/256 support compiled out, returns CURLE_BAD_CONTENT_ENCODING.

calls: [auth_create_digest_http_message](r9-digest-core.md#u-cfacb386af7b)

**Uncertainties.**

- The 'unreachable' fallback depends on the numeric ordering of the ALGO_* macros; the ordering is taken from the macro definitions in this file.

<a id="u-30b45fa12734"></a>
### `Curl_auth_create_digest_md5_message`

`CURLcode Curl_auth_create_digest_md5_message(struct Curl_easy *data, const struct buf…` · [lib/vauth/digest.c:L344-L513][f1]

Builds a DIGEST-MD5 (RFC 2831) SASL response from a challenge and credentials.

The service name comes from the credentials' SASL service when present, otherwise default_service. After decoding the challenge it rejects any algorithm other than 'md5-sess' and any qop set lacking 'auth' with CURLE_BAD_CONTENT_ENCODING. A 32-hex-char cnonce comes from Curl_rand_hex; its error propagates. It computes H(A1)=MD5(user:realm:passwd), the md5-sess A1=H(H(A1):nonce:cnonce), H(A2)=MD5(AUTHENTICATE:spn) with the SPN built by Curl_auth_build_spn from service and data->state.origin->hostname, and response=MD5(A1:nonce:nc:cnonce:qop:A2) with nc fixed at '00000001' and qop 'auth'. Realm, nonce, username, and spn are quoted-escaped before the final curl_maprintf; if any escape or the printf fails, temporaries are freed and CURLE_OUT_OF_MEMORY is returned. Curl_MD5_init failures likewise return CURLE_OUT_OF_MEMORY; spn is freed only in the later init-failure paths. On success the response is returned via Curl_bufref_set with curl_free as destructor.

calls: [auth_decode_digest_md5_message](r9-digest-core.md#u-4264823bccc7), [auth_digest_get_qop_values](r9-digest-core.md#u-8c689adca143), [auth_digest_string_quoted](r9-digest-core.md#u-fed5f9022a13), [Curl_rand_hex](r10-misc-utilities.md#u-a2eb969bfb7d), [Curl_MD5_init](r12-md5-digest.md#u-1c912a6f4b7b), [Curl_auth_build_spn](r8-auth-core.md#u-54b25784cc6d), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

**Uncertainties.**

- Curl_creds_* accessor behavior and whether data->state.origin can be NULL are not established from this source.

<a id="u-ad216e8b7263"></a>
### `Curl_auth_decode_digest_http_message`

`CURLcode Curl_auth_decode_digest_http_message(const char *chlg, struct digestdata *di…` · [lib/vauth/digest.c:L528-L671][f1]

Decodes an HTTP WWW-Authenticate Digest challenge into the digest state.

It first notes whether a nonce already existed, then resets all state via Curl_auth_digest_cleanup. It repeatedly parses key=value pairs with Curl_auth_digest_get_pair, stopping when parsing fails. Recognized keys: 'nonce', 'realm', and 'opaque' are strdup'ed into state (strdup failure returns CURLE_OUT_OF_MEMORY); 'stale' with content 'true' sets stale and resets nc to 1; 'qop' is tokenized on commas, selecting 'auth' first, then 'auth-int', otherwise none; 'algorithm' is strdup'ed and matched exactly (MD5-sess, MD5, SHA-256, SHA-256-SESS set the corresponding algo; SHA-512-256 and SHA-512-256-SESS require CURL_HAVE_SHA512_256 or return CURLE_NOT_BUILT_IN; anything else returns CURLE_BAD_CONTENT_ENCODING); 'userhash' with 'true' sets the userhash flag; unknown keys are ignored. Pairs are separated by an optional comma. After parsing, a second nonce without stale=true (bad credentials) returns CURLE_BAD_CONTENT_ENCODING, a missing nonce returns CURLE_BAD_CONTENT_ENCODING, and an algorithm with the SESSION_ALGO bit but no qop returns CURLE_BAD_CONTENT_ENCODING; otherwise CURLE_OK.

calls: [Curl_auth_digest_get_pair](r9-digest-core.md#u-ce3d49b7f7ce), [Curl_auth_digest_cleanup](r9-digest-core.md#u-c99d51194936), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

**Uncertainties.**

- The exact values of the ALGO_* constants (bit layout with SESSION_ALGO) come from macros in this file; their numeric ordering is inferred from the macro definitions.

<a id="u-c99d51194936"></a>
### `Curl_auth_digest_cleanup`

`void Curl_auth_digest_cleanup(struct digestdata *digest)` · [lib/vauth/digest.c:L1043-L1058][f1]

Releases and resets all Digest state: unlinks the stored origin and credentials peers, frees nonce, cnonce, realm, opaque, qop, and algorithm, then resets nc to 0, algo to ALGO_MD5, and stale/userhash to FALSE.

Safe to call on already-clean state because the frees null the pointers.

calls: [Curl_peer_unlink](r3-peer-identity.md#u-63430ed0e6c2), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

<a id="u-ce3d49b7f7ce"></a>
### `Curl_auth_digest_get_pair`

`bool Curl_auth_digest_get_pair(const char *str, struct Curl_str *value, char *content…` · [lib/vauth/digest.c:L60-L135][f1]

Parses one key=value pair from a Digest challenge string, handling quoted and escaped values.

Splits on '=' with curlx_str_until/curlx_str_single and returns FALSE on failure. If the value starts with a quote it must end with one. In the content loop: a backslash inside quotes starts an escape; a comma ends unquoted content; CR/LF ends unquoted content but returns FALSE inside quotes (no closing quote); a closing quote ends quoted content while an unquoted quote returns FALSE. If content_length reaches DIGEST_MAX_CONTENT_LENGTH - 1 it returns FALSE. A trailing escape with no following character also returns FALSE. On success content is NUL-terminated, *endptr is set past the consumed bytes, and it returns TRUE.

calls: [curlx_str_until](r11-strparse-word-scanning.md#u-ad9aa60680eb), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- Error-code semantics of curlx_str_until/curlx_str_single rest on strparse.c, not supplied here.

<a id="u-f7e818c075b5"></a>
### `Curl_auth_is_digest_supported`

`bool Curl_auth_is_digest_supported(void)` · [lib/vauth/digest.c:L322-L325][f1]

Always returns TRUE: DIGEST authentication is handled internally, so the capability probe never fails.

<a id="u-cfacb386af7b"></a>
### `auth_create_digest_http_message`

`static CURLcode auth_create_digest_http_message( struct Curl_easy *data, struct Curl_…` · [lib/vauth/digest.c:L692-L978][f1]

Generates an HTTP Digest Authorization header body, parameterized by a hash function and a digest-to-ASCII formatter so the same code serves MD5, SHA-256, and SHA-512/256.

It ensures nc defaults to 1 and generates a fresh 12-byte base64-encoded cnonce (stored in digest->cnonce) if absent; generation or encoding failure jumps to the oom cleanup. With userhash set, username:realm is hashed into userh first. A1 is H(user:realm:passwd); for session algorithms (SESSION_ALGO bit) A1 becomes H(A1:nonce:cnonce). A2 is H(request:uripath), extended to H(method:uri:H(empty body)) when qop is exactly 'auth-int' (the entity body is always hashed as empty, so PUT/POST bodies are not covered). The response is H(A1:nonce:nc:cnonce:qop:A2) when qop exists, otherwise H(A1:nonce:A2). Username (or userhash), realm (empty string if absent), nonce, and uri are quoted-escaped; opaque, algorithm, and userhash=true are appended when present. The qop variant includes nc=%08x and increments digest->nc for the next request. Every allocation or hash failure goes to the shared oom label, which frees all temporaries and releases the dynbuf on error; on success the dynbuf pointer/length are returned and the buffer is not freed.

calls: [auth_digest_string_quoted](r9-digest-core.md#u-fed5f9022a13), [Curl_rand_bytes](r10-misc-utilities.md#u-c3e86a9c4806), [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f), [curlx_dyn_addf](r3-dynbuf.md#u-063790a51674)

**Uncertainties.**

- The injected hash() and convert_to_ascii() callbacks come from callers; their exact failure contracts are outside this file.
- digest->nc's integer width is inferred from the %08x casts, not a supplied struct definition.

<a id="u-4264823bccc7"></a>
### `auth_decode_digest_md5_message`

`static CURLcode auth_decode_digest_md5_message(const struct bufref *chlgref, char *no…` · [lib/vauth/digest.c:L280-L311][f1]

Decodes a DIGEST-MD5 challenge buffer into nonce, realm, algorithm, and qop fields via auth_digest_get_key_value.

An empty challenge (bufref length 0) returns CURLE_BAD_CONTENT_ENCODING, as do missing 'nonce', 'algorithm', or 'qop' keys. A missing 'realm' is tolerated per RFC 2831: realm is set to the empty string. Each value is bounded by the caller-supplied buffer length.

calls: [auth_digest_get_key_value](r9-digest-core.md#u-a1036f964596), [bufref-c-accessors](r14-bufref-buffers.md#u-ac8cad6d65f5)

<a id="u-a1036f964596"></a>
### `auth_digest_get_key_value`

`static bool auth_digest_get_key_value(const char *chlg, const char *key, char *buf, s…` · [lib/vauth/digest.c:L189-L240][f1]

Finds a named directive in a comma-separated key=value challenge and copies its value.

Each iteration skips blanks, splits the key at '=' with curlx_str_until/curlx_str_single, and breaks (returning FALSE) on odd syntax. The value is read with curlx_str_quotedword; on STRE_BEGQUOTE it retries with curlx_str_until up to the next comma; any other failure returns FALSE. On key match (curlx_str_cmp), a value not fitting buflen returns FALSE; otherwise backslash escape pairs are collapsed (backslash dropped, next byte kept), the result is NUL-terminated, and TRUE is returned. On non-match a ',' is consumed with curlx_str_single; failing to find it ends the scan with FALSE.

calls: [curlx_str_quotedword](r11-strparse-word-scanning.md#u-832c085c6dd9), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- Whether curlx_str_quotedword already strips escapes is unclear; the code strips remaining backslashes manually.

<a id="u-8c689adca143"></a>
### `auth_digest_get_qop_values`

`static void auth_digest_get_qop_values(const char *options, int *value)` · [lib/vauth/digest.c:L242-L258][f1]

Converts a comma-separated qop-options list into a bitmask.

Tokens up to 32 chars are split on ',' with curlx_str_until and matched case-insensitively: 'auth', 'auth-int', or 'auth-conf' sets the corresponding DIGEST_QOP_VALUE bit; unknown tokens contribute nothing. *value is zeroed first. Failure to consume a ',' separator with curlx_str_single ends the loop, so unrecognized input leaves 0.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

<a id="u-83dba4d3cb96"></a>
### `auth_digest_md5_to_ascii`

`static void auth_digest_md5_to_ascii( const unsigned char *source, /* 16 bytes */ uns…` · [lib/vauth/digest.c:L139-L146][f1]

Formats a 16-byte MD5 digest as 32 hex characters into a 33-byte destination buffer, two lowercase hex digits per byte via curl_msnprintf.

calls: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

<a id="u-aa7c712d974c"></a>
### `auth_digest_sha256_to_ascii`

`static void auth_digest_sha256_to_ascii( const unsigned char *source, /* 32 bytes */ …` · [lib/vauth/digest.c:L149-L156][f1]

Formats a 32-byte SHA-256 or SHA-512/256 digest as 64 hex characters into a 65-byte destination buffer, two hex digits per byte via curl_msnprintf.

calls: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

<a id="u-fed5f9022a13"></a>
### `auth_digest_string_quoted`

`static char *auth_digest_string_quoted(const char *s)` · [lib/vauth/digest.c:L159-L184][f1]

Escapes a string for use inside a Digest quoted-string, returning allocated output built in a dynbuf capped at 2048 bytes.

Empty input returns a strdup of the empty string. '"' and '\\' are prefixed with a backslash; control bytes (< 0x20) and non-ASCII (> 0x7e) are emitted as %XX via Curl_hexbyte; other bytes are copied verbatim. Any dynbuf append failure returns NULL immediately, aborting the loop.

calls: [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [Curl_hexbyte](r7-string-escape-utils.md#u-dfd3e53b2fbc)

**Uncertainties.**

- Whether the 2048-byte dynbuf cap fails long inputs depends on dynbuf semantics not supplied.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/digest.c
