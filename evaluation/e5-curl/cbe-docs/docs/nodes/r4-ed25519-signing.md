# Ed25519 signing

**Capability.** Signs messages with Ed25519 (RFC 8032) via exactly one compiled backend variant: OpenSSL, wolfSSL, GnuTLS/nettle, or a CURLE_NOT_BUILT_IN stub.

Read when signature support matters (e.g. SSH or websocket-related crypto): the four Curl_ed25519_sign variants are mutually exclusive per build and share one signature contract.

Parent: [Authentication and crypto primitives](r4-auth-crypto.md)

## Units (5)

<a id="u-a7335a5890e7"></a>
### `curl-ed25519-gnutls`

`CURLcode Curl_ed25519_sign(const unsigned char *key, size_t keylen, const unsigned ch…` · [lib/curl_ed25519.c:L141-L156][f1]

GnuTLS/nettle variant.

keylen != ED25519_KEY_SIZE returns CURLE_BAD_FUNCTION_ARGUMENT. The public key is derived with nettle_ed25519_sha512_public_key and the message signed with nettle_ed25519_sha512_sign; *siglen is set to CURL_ED25519_SIGLEN and CURLE_OK is always returned, since the nettle calls here report no failure.

group: [curl_ed25519-c-sign](r4-ed25519-signing.md#u-7d8ddbea6cfa)

**Uncertainties.**

- The nettle Ed25519 calls return void, so no signing failure can be detected or reported after the size check.

<a id="u-434ecbffa412"></a>
### `curl-ed25519-openssl`

`CURLcode Curl_ed25519_sign(const unsigned char *key, size_t keylen, const unsigned ch…` · [lib/curl_ed25519.c:L46-L86][f1]

OpenSSL variant of Curl_ed25519_sign.

A keylen other than CURL_ED25519_KEYLEN returns CURLE_BAD_FUNCTION_ARGUMENT. EVP_PKEY_new_raw_private_key failure returns CURLE_AUTH_ERROR; EVP_MD_CTX_new failure frees the key and returns CURLE_OUT_OF_MEMORY; EVP_DigestSignInit returning anything but 1 frees context and key and returns CURLE_AUTH_ERROR. EVP_DigestSign is called with slen preset to CURL_ED25519_SIGLEN; context and key are always freed, rc != 1 yields CURLE_AUTH_ERROR, otherwise *siglen is set to slen and CURLE_OK returned.

**Notes.**

- side_effect: The EVP_PKEY and EVP_MD_CTX are freed on every exit path.

group: [curl_ed25519-c-sign](r4-ed25519-signing.md#u-7d8ddbea6cfa)

<a id="u-6987be180897"></a>
### `curl-ed25519-stub`

`CURLcode Curl_ed25519_sign(const unsigned char *key, size_t keylen, const unsigned ch…` · [lib/curl_ed25519.c:L160-L171][f1]

No-backend fallback: all parameters are explicitly ignored and CURLE_NOT_BUILT_IN is returned without touching sig or siglen.

group: [curl_ed25519-c-sign](r4-ed25519-signing.md#u-7d8ddbea6cfa)

<a id="u-3616cb6e6116"></a>
### `curl-ed25519-wolfssl`

`CURLcode Curl_ed25519_sign(const unsigned char *key, size_t keylen, const unsigned ch…` · [lib/curl_ed25519.c:L95-L136][f1]

wolfSSL variant, compiled when the Ed25519 import/sign feature macros are defined.

keylen != ED25519_KEY_SIZE returns CURLE_BAD_FUNCTION_ARGUMENT; wc_ed25519_init failure returns CURLE_AUTH_ERROR. The seed is imported private-only, the public key is derived with wc_ed25519_make_public, and the full key is re-imported; any failure jumps to a fail label that frees the key object and returns CURLE_AUTH_ERROR. On successful wc_ed25519_sign_msg the key is freed, *siglen is set from outlen, and CURLE_OK is returned.

group: [curl_ed25519-c-sign](r4-ed25519-signing.md#u-7d8ddbea6cfa)

<a id="u-7d8ddbea6cfa"></a>
### `curl_ed25519-c-sign`

`CURLcode Curl_ed25519_sign(const unsigned char *key, size_t keylen, const unsigned ch…` · [lib/curl_ed25519.c:L46-L86][f1]

Signs a message with Ed25519 (RFC 8032) using whichever crypto backend is compiled in; exactly one of the four Curl_ed25519_sign variants exists per build.

All variants take a raw private seed, message, and output buffer, and write the actual signature length through siglen. Common input rule: a keylen not matching the backend's expected size (32 bytes everywhere) returns CURLE_BAD_FUNCTION_ARGUMENT with no side effects.

uses: [httpsig_sign_base](r5-http-message-signatures.md#u-17d45fd2fb99), [curl_ed25519.h module code (L1–L44)][f2]

**Uncertainties.**

- Selection among the four variants is by preprocessor conditionals, so only one variant's runtime behavior is observable per build.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_ed25519.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_ed25519.h
