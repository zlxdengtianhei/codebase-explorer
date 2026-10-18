# MD5 digest service

**Capability.** Backend-pluggable MD5: one-shot and incremental digest API dispatching to OpenSSL, Nettle, wolfSSL, mbedTLS PSA, CommonCrypto, Win32 Crypto, or the built-in RFC 1321 fallback, with the constant backend table exposed to callers.

Call Curl_md5it for one-shot digests or Curl_MD5_init/update/final for streaming. APOP authentication is a known consumer.

**Depends on.**

- [Socket, buffer, and integer utilities](r12-socket-and-buffer-utils.md) · graph-confirmed · 24 edge(s)

**Depended on by.**

- [POP3 authentication](r12-pop3-authentication.md) · graph-confirmed · 4 edge(s) · POP3 APOP authentication computes its timestamp-plus-password digest with the MD5 service.
- [POP3 state machine and transfer](r12-pop3-state-machine.md) · model-inferred · 0 edge(s)
- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-only · 32 edge(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Units (12)

<a id="u-1008c6c0d928"></a>
### `md5-c-builtin-backend`

`struct md5_ctx` · [lib/md5.c:L269-L274][f1]

Public-domain fallback MD5 implementation (RFC 1321, Openwall style) compiled when no crypto library backend applies.

It defines struct md5_ctx with bit counters (lo/hi), state words (a-d), a 64-byte buffer, and a 16-word block, plus the MD5_F/G/H/H2/I round functions and the MD5_STEP macro. my_md5_body processes whole 64-byte blocks through four rounds without updating bit counters and returns the advanced pointer; on i386/x86_64/vax it reads words directly from the input (unaligned little-endian load), otherwise it assembles little-endian words into ctx->block. my_md5_init sets the standard IV and zeroes the counters, returning CURLE_OK. my_md5_update buffers partial blocks: it extends the 29-bit low counter with carry into hi, fills the tail of the buffer, processes whole blocks via my_md5_body when enough data accumulates, and memcpy's the remainder. my_md5_final appends 0x80 padding, zero-fills, adds another padded block when fewer than 8 bytes remain, writes the little-endian 64-bit bit length into the last 8 bytes, runs one final block, emits the 16-byte digest from a-d via curlx_ultouc, and memsets the context to zero.

calls: [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706); contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

**Uncertainties.**

- MD5_STEP's masking relies on 32-bit wraparound of uint32_t arithmetic; behavior on exotic widths is untested here.
- The final update's my_md5_body calls are internal to this group; the graph shows no exported exits.

<a id="u-53bbeeb18b01"></a>
### `md5-c-commoncrypto-backend`

`static CURLcode my_md5_init(void *ctx)` · [lib/md5.c:L178-L182][f1]

Apple CommonCrypto MD5 backend, chosen for macOS targets from Tiger up to below 10.15 and iOS 2.0 to below 13.0 per the version-macro condition.

my_md5_ctx is CC_MD5_CTX. my_md5_init wraps CC_MD5_Init (a comment asserts it always returns 1) and always returns CURLE_OK; my_md5_update calls CC_MD5_Update; my_md5_final calls CC_MD5_Final to write the digest. This backend has no error paths.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

<a id="u-5063bb1f0e4c"></a>
### `md5-c-mbedtls-psa-backend`

`static CURLcode my_md5_init(void *ctx)` · [lib/md5.c:L139-L146][f1]

mbedTLS PSA crypto MD5 backend, compiled only when USE_MBEDTLS and PSA_WANT_ALG_MD5 are both set; the include block rejects mbedTLS older than 3.2.0 with #error.

my_md5_ctx is a psa_hash_operation_t. my_md5_init resets the operation via psa_hash_operation_init and starts MD5 with psa_hash_setup; any status other than PSA_SUCCESS yields CURLE_OUT_OF_MEMORY, otherwise CURLE_OK. my_md5_update forwards to psa_hash_update; my_md5_final calls psa_hash_finish writing up to MD5_DIGEST_LEN bytes and ignores both the status and the actual output length, so a short or failed finish is undetectable by callers.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

**Uncertainties.**

- psa_hash_finish status and actual_length are discarded; digest correctness on failure cannot be guaranteed from this source.

<a id="u-522d7ff14091"></a>
### `md5-c-nettle-backend`

`static CURLcode my_md5_init(void *ctx)` · [lib/md5.c:L54-L58][f1]

GNUTLS/Nettle MD5 backend, selected when USE_GNUTLS is defined; it aliases my_md5_ctx to Nettle's md5_ctx and adapts md5_init/md5_update/md5_digest to curl's callback signatures.

my_md5_init calls md5_init and always returns CURLE_OK; my_md5_update forwards the byte count and buffer to md5_update; my_md5_final produces the digest via md5_digest, with an arity change for Nettle 4.x (digest pointer only) versus earlier versions (explicit MD5_DIGEST_LEN length). No error paths exist.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

**Uncertainties.**

- Whether Nettle's md5_init or md5_update can fail is not visible; the adapters assume success.

<a id="u-b457d92ea2c7"></a>
### `md5-c-openssl-backend`

`static CURLcode my_md5_init(void *in)` · [lib/md5.c:L80-L93][f1]

OpenSSL MD5 backend, compiled when USE_OPENSSL is set and MD5 is not disabled.

my_md5_ctx is an EVP_MD_CTX pointer, and the void* callback parameter points to such a pointer. my_md5_init allocates a context with EVP_MD_CTX_new and initializes MD5 via EVP_DigestInit_ex: allocation failure returns CURLE_OUT_OF_MEMORY, init failure frees the context, nulls the slot, and returns CURLE_FAILED_INIT, otherwise CURLE_OK. my_md5_update forwards to EVP_DigestUpdate and ignores its result. my_md5_final finalizes with EVP_DigestFinal_ex (result ignored), frees the context, and nulls the slot, so the context is consumed by final.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

**Uncertainties.**

- Here sizeof(my_md5_ctx) is a pointer size, so the table's ctxtsize is the size of the EVP_MD_CTX* slot rather than the EVP_MD_CTX itself; callers must pass a pointer to that slot, which cannot be verified from this file alone.

<a id="u-89f0e26997d1"></a>
### `md5-c-parameter-tables`

`group` · [lib/md5.c:L531-L555][f1]

Constant backend tables exposed to the rest of curl.

Curl_HMAC_MD5 fills an HMAC_params with the selected my_md5_init/update/final callbacks, sizeof(my_md5_ctx) as the context size, a 64-byte maximum key length, and MD5_DIGEST_LEN (16) as the result size. Curl_DIGEST_MD5 fills the MD5_params variant with the same callbacks, the same context size, and MD5_DIGEST_LEN; it has no maxkeylen field.

uses: [md5-c-builtin-backend](r12-md5-digest.md#u-1008c6c0d928)

<a id="u-8b2c04e31e68"></a>
### `md5-c-win32-crypto-backend`

`static CURLcode my_md5_init(void *in)` · [lib/md5.c:L204-L218][f1]

Windows CryptoAPI MD5 backend, selected when USE_WIN32_CRYPTO is defined; its local struct md5_ctx holds an HCRYPTPROV and an HCRYPTHASH.

my_md5_init acquires a verified, silent PROV_RSA_FULL context (returning CURLE_OUT_OF_MEMORY if CryptAcquireContext fails), then creates a CALG_MD5 hash; if CryptCreateHash fails it releases the provider, clears the handle, and returns CURLE_FAILED_INIT. my_md5_update hashes data with CryptHashData. my_md5_final first queries HP_HASHVAL for its length, copies the digest only when the length equals MD5_DIGEST_LEN, then always destroys the hash and releases the provider; on a length mismatch the digest buffer is left untouched and no error is reported.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

**Uncertainties.**

- If the queried hash length differs from MD5_DIGEST_LEN, the digest is silently not written and the failure is not propagated.

<a id="u-023f3f1d49fc"></a>
### `md5-c-wolfssl-backend`

`static CURLcode my_md5_init(void *ctx)` · [lib/md5.c:L115-L120][f1]

wolfSSL MD5 backend, selected when USE_WOLFSSL is set and NO_MD5 is not; my_md5_ctx is a wc_Md5 used by value.

my_md5_init calls wc_InitMd5 and returns CURLE_OUT_OF_MEMORY if it reports failure, otherwise CURLE_OK. my_md5_update forwards to wc_Md5Update casting the length to word32; my_md5_final calls wc_Md5Final to emit the 16-byte digest. Update and final return values are discarded.

contract: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

<a id="u-fabda254dcb3"></a>
### `Curl_MD5_final`

`CURLcode Curl_MD5_final(struct MD5_context *context, unsigned char *result)` · [lib/md5.c:L611-L619][f1]

Finalizes an incremental MD5 computation: it invokes the backend's md5_final_func to write the digest into the caller's result buffer, then frees both the backend hash context and the MD5_context wrapper with curlx_free, always returning CURLE_OK.

The context is consumed and must not be reused.

uses: [MD5_context](r15-protocol-support-headers.md#u-0473e7fd6415)

<a id="u-1c912a6f4b7b"></a>
### `Curl_MD5_init`

`struct MD5_context *Curl_MD5_init(const struct MD5_params *md5params)` · [lib/md5.c:L575-L601][f1]

Allocates an incremental MD5 context for the given MD5_params backend.

It mallocs the MD5_context wrapper, returning NULL on failure; then mallocs md5_ctxtsize bytes for the backend context, freeing the wrapper and returning NULL if that fails. It stores the params pointer and invokes md5_init_func on the backend context; a nonzero (failed) return frees both allocations and returns NULL, otherwise the initialized context is returned.

uses: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb), [md5-c-parameter-tables](r12-md5-digest.md#u-89f0e26997d1)

**Uncertainties.**

- The init-failure check treats any nonzero CURLcode from the callback as failure; for backends whose init returns void this branch is unreachable by construction.

<a id="u-c4fa1e912419"></a>
### `Curl_MD5_update`

`CURLcode Curl_MD5_update(struct MD5_context *context, const unsigned char *input, uns…` · [lib/md5.c:L603-L609][f1]

Feeds len input bytes into an in-progress MD5 computation by dispatching to the backend's md5_update_func with the stored hash context.

It performs no error checking and always returns CURLE_OK.

uses: [MD5_context](r15-protocol-support-headers.md#u-0473e7fd6415)

<a id="u-489a346c4d18"></a>
### `Curl_md5it`

`CURLcode Curl_md5it(unsigned char *output, const unsigned char *input, size_t len)` · [lib/md5.c:L556-L573][f1]

Computes the MD5 digest of an arbitrary-length buffer in one call using the selected backend.

It stack-allocates a my_md5_ctx, runs my_md5_init, and only if init succeeded loops: each iteration updates with CURLMIN(len, UINT_MAX) bytes (splitting inputs larger than UINT_MAX into multiple updates), advances the input, and repeats until len is zero; then it calls my_md5_final to write the 16-byte output. If init fails, its CURLcode is returned and no digest is produced.

calls: [md5-c-builtin-backend](r12-md5-digest.md#u-1008c6c0d928)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/md5.c
