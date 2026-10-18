# SHA-256 & HMAC Primitives

**Capability.** Provides the SHA-256 one-shot digest (Curl_sha256it) over selectable backends (OpenSSL EVP, wolfSSL, nettle, mbedTLS PSA, CommonCrypto, WinCrypt, or a pure-C LibTomCrypt fallback) and a generic RFC2104 HMAC init/update/final plus a one-shot Curl_hmacit wrapper.

Read this subtree to see how hashing is isolated behind backend macros. Callers use only Curl_sha256it or Curl_hmacit with a hash-parameter table; hmac.c compiles only for NTLM/AWS/DIGEST/SSL builds.

**Depended on by.**

- [AWS SigV4 Request Signing](r3-aws-sigv4.md) · graph-confirmed · 7 edge(s)

Parent: [Crypto Primitives & HTTP Authentication](r3-crypto-auth.md)

## Units (13)

<a id="u-c70725335377"></a>
### `sha256-c-openssl-backend`

`static CURLcode my_sha256_init(void *in)` · [lib/sha256.c:L61-L73][f1]

Implements the SHA-256 init/update/final interface using OpenSSL's EVP API.

my_sha256_init allocates an EVP_MD_CTX; allocation failure returns CURLE_OUT_OF_MEMORY, and EVP_DigestInit_ex failure frees the context and returns CURLE_FAILED_INIT. my_sha256_update forwards data to EVP_DigestUpdate and my_sha256_final writes the 32-byte digest via EVP_DigestFinal_ex then frees the context, so final must be called exactly once per successful init. Update and final report no status; backend errors after init are silently ignored.

uses: [sha256-c-openssl-backend](r3-hash-primitives.md#u-c70725335377)

**Uncertainties.**

- Return values of EVP_DigestUpdate and EVP_DigestFinal_ex are ignored, so digest correctness depends on the backend succeeding
- Context storage is caller-provided (struct holding one pointer); a prior init failure leaves the context unusable

<a id="u-1f1ea364edbb"></a>
### `sha256-c-wolfssl-backend`

`static CURLcode my_sha256_init(void *in)` · [lib/sha256.c:L96-L101][f1]

Implements the SHA-256 interface using wolfSSL's wc_Sha256 type directly as the context.

my_sha256_init returns CURLE_FAILED_INIT if wc_InitSha256 fails, otherwise CURLE_OK; my_sha256_update casts the length to word32 and calls wc_Sha256Update; my_sha256_final calls wc_Sha256Final to produce the digest. All wc_ return codes other than init's are cast to void, so update/final failures produce no error signal.

**Uncertainties.**

- wc_Sha256Update and wc_Sha256Final results are discarded, so backend failures are unobservable here

<a id="u-c3be81d9bb41"></a>
### `sha256-c-gnutls-backend`

`static CURLcode my_sha256_init(void *ctx)` · [lib/sha256.c:L121-L125][f1]

Implements the SHA-256 interface using libnettle's sha256_ctx.

my_sha256_init calls sha256_init and always returns CURLE_OK; my_sha256_update forwards to sha256_update with the length first. my_sha256_final is version-dependent: on nettle 4 or later it calls sha256_digest(ctx, digest), while older nettle needs the explicit SHA256_DIGEST_SIZE argument. No error path exists in this branch.

<a id="u-98350160c593"></a>
### `sha256-c-mbedtls-backend`

`static CURLcode my_sha256_init(void *ctx)` · [lib/sha256.c:L149-L156][f1]

Implements the SHA-256 interface via the mbedTLS PSA crypto API, compiled only when PSA_WANT_ALG_SHA_256 is enabled.

my_sha256_init resets the psa_hash_operation_t and returns CURLE_OUT_OF_MEMORY if psa_hash_setup with PSA_ALG_SHA_256 does not return PSA_SUCCESS (the code maps any setup failure to out-of-memory). my_sha256_update calls psa_hash_update and my_sha256_final calls psa_hash_finish bounded by CURL_SHA256_DIGEST_LENGTH, discarding both status codes and the actual output length.

**Uncertainties.**

- Any psa_hash_setup failure, not only memory shortage, is reported as CURLE_OUT_OF_MEMORY
- psa_hash_update and psa_hash_finish failures are silently ignored

<a id="u-67148db0516a"></a>
### `sha256-c-commoncrypto-backend`

`static CURLcode my_sha256_init(void *ctx)` · [lib/sha256.c:L180-L184][f1]

Implements the SHA-256 interface using Apple's CommonCrypto (selected by macOS/iOS version macros).

my_sha256_init calls CC_SHA256_Init, which the comment says always returns 1, and always returns CURLE_OK; my_sha256_update and my_sha256_final delegate to CC_SHA256_Update and CC_SHA256_Final with results ignored. There is no failure path in this branch.

<a id="u-d63dc229d870"></a>
### `sha256-c-win32-backend`

`static CURLcode my_sha256_init(void *in)` · [lib/sha256.c:L207-L221][f1]

Implements the SHA-256 interface with the legacy Windows CryptoAPI (wincrypt).

my_sha256_init acquires a PROV_RSA_AES context with CRYPT_VERIFYCONTEXT|CRYPT_SILENT; acquisition failure returns CURLE_OUT_OF_MEMORY. CryptCreateHash failure with CALG_SHA_256 releases the context, zeroes hCryptProv, and returns CURLE_FAILED_INIT. my_sha256_update feeds data with CryptHashData. my_sha256_final first queries HP_HASHVAL size, copies the digest only when it equals CURL_SHA256_DIGEST_LENGTH, then destroys the hash and releases the provider, so the context cannot be reused after final.

**Uncertainties.**

- Both CryptGetHashParam calls' return codes are ignored; on size mismatch the output buffer is left untouched
- CryptAcquireContext failure is reported as CURLE_OUT_OF_MEMORY regardless of the underlying cause

<a id="u-2f6f5bb830c8"></a>
### `Curl_sha256it`

`CURLcode Curl_sha256it(unsigned char *output, const unsigned char *input, size_t len)` · [lib/sha256.c:L484-L501][f1]

Computes the SHA-256 digest of an arbitrarily long input buffer into a caller-provided 32-byte output, returning CURLE_OK or the failure code from the backend's init.

It stacks a my_sha256_ctx, calls my_sha256_init, and only if init succeeded loops: each iteration feeds CURLMIN(len, UINT_MAX) bytes through my_sha256_update (adapting the size_t length to the unsigned int the update functions take), advancing input and shrinking len until exhausted, then calls my_sha256_final once. If init fails, output is not written and the code is returned directly; update and final have no status output, so later backend failures are invisible here.

calls: [sha256-c-openssl-backend](r3-hash-primitives.md#u-c70725335377), [sha256-c-libtomcrypt-fallback](r3-hash-primitives.md#u-2345bfe62ec3)

**Uncertainties.**

- Whether Curl_sha256it is safe to call with len 0 (update skipped, final of an empty message) follows the backend's behavior, not this file

<a id="u-2345bfe62ec3"></a>
### `sha256-c-libtomcrypt-fallback`

`static int sha256_compress(struct sha256_state *md, const unsigned char *buf)` · [lib/sha256.c:L319-L365][f1]

Public-domain LibTomCrypt-derived pure-C SHA-256 used when no crypto backend macro matches.

my_sha256_init loads the standard SHA-256 initial state and always returns CURLE_OK. sha256_compress transforms one 64-byte block: it loads big-endian words, expands W[16..63] via Gamma0/Gamma1, runs the 64-round RND schedule over S[0..7], and adds the result back into md->state, always returning 0. my_sha256_update returns immediately (without error) if md->curlen exceeds sizeof(md->buf); it compresses full aligned blocks directly from input when curlen is 0 and at least 64 bytes remain, otherwise buffers bytes until 64 accumulate, aborting silently if compression fails. my_sha256_final likewise returns early if curlen exceeds 63; it appends 0x80, pads: if curlen exceeds 56 it zero-fills to 64, compresses, and resets curlen, then pads to 56, stores the 64-bit big-endian bit length, compresses, and writes the eight state words big-endian to out.

**Notes.**

- failure: sha256_compress always returns 0, so the update-side <0 checks are currently dead; the guard curlen > sizeof(buf) silently drops data rather than reporting an error
- side_effect: my_sha256_final mutates md->length and md->buf, so the state cannot be reused after final

calls: [sha256-c-libtomcrypt-fallback](r3-hash-primitives.md#u-2345bfe62ec3)

**Uncertainties.**

- The curlen > sizeof(md->buf) guards compare against 64 including equality at the final boundary, leaving one-byte margin behavior unproven
- md->length is only incremented by compressed full blocks during update and by curlen*8 in final; interleaving update after final would corrupt the digest

<a id="u-c8c591ff2b10"></a>
### `hmac-c-module`

`module_region` · [lib/hmac.c:L1-L44][f2]

Non-behavioral residue of lib/hmac.c: the license header, conditional compilation guards limiting the file to NTLM-without-SSPI, AWS, DIGEST, or SSL builds, the curl_hmac.h include, the module comment describing the generic RFC2104 HMAC algorithm, the static pad constants hmac_ipad (0x36) and hmac_opad (0x5C), and the closing #endif.

The pad constants are only meaningful as inputs to Curl_HMAC_init.

<a id="u-3496b0bc2abc"></a>
### `Curl_HMAC_init`

`struct HMAC_context *Curl_HMAC_init(const struct HMAC_params *hashparams, const unsig…` · [lib/hmac.c:L45-L99][f2]

Allocates and primes an HMAC context from a hash-parameter table, key, and key length per RFC2104.

It mallocs one block holding the context plus two hash sub-contexts plus scratch space; on allocation failure it returns NULL. If keylen exceeds hashparams->maxkeylen, the key is replaced by its digest: hinit/hupdate/hfinal write the digest into scratch after hashctxt2, and key/keylen are switched to that digest and resultlen. Both sub-contexts are then initialized; if either hinit fails, control jumps to fail, freeing the context and returning NULL. Otherwise each key byte XORed with hmac_ipad feeds hashctxt1 and the same byte XORed with hmac_opad feeds hashctxt2, one byte at a time; when keylen is shorter than maxkeylen, the remaining iterations feed raw hmac_ipad/hmac_opad padding bytes. Returns the context pointer for later updates.

**Notes.**

- side_effect: The returned context owns a single allocation containing both hash sub-contexts; only Curl_HMAC_final frees it.
- failure: hinit failure at any point frees the context and returns NULL; hupdate/hfinal failures are not checked here.

uses: [Curl_HMAC_final](r3-hash-primitives.md#u-333e5a23ac24)

**Uncertainties.**

- The failure return values of hashparams->hupdate and hashparams->hfinal are ignored in this function; their actual error semantics are defined outside this file.

<a id="u-33eccf51f0ed"></a>
### `Curl_HMAC_update`

`void Curl_HMAC_update(struct HMAC_context *ctxt, const unsigned char *data, unsigned …` · [lib/hmac.c:L101-L107][f2]

Feeds data into the first (inner) hash sub-context of an existing HMAC context by invoking the hash table's hupdate callback.

Returns void; no length or NULL validation is visible, and the outer sub-context is untouched at this stage.

**Uncertainties.**

- No visible handling of a NULL ctxt or a failing hupdate callback; caller must supply a context from Curl_HMAC_init.

<a id="u-333e5a23ac24"></a>
### `Curl_HMAC_final`

`int Curl_HMAC_final(struct HMAC_context *ctxt, unsigned char *output)` · [lib/hmac.c:L109-L124][f2]

Completes the HMAC computation and releases the context.

If output is NULL, the digest is written to scratch space behind hashctxt2 instead of a caller buffer. It finalizes the inner hash into output, feeds those resultlen bytes into the outer sub-context, finalizes the outer hash into the same output location, frees the context with curlx_free, and always returns 0. Passing a NULL output therefore means the caller can only read the result through the context's internal buffer before it is freed here, so the digest is effectively lost unless the scratch layout is used deliberately.

contract: [Curl_HMAC_init](r3-hash-primitives.md#u-3496b0bc2abc)

**Uncertainties.**

- The comment says a null output parameter means 'only release storage', but the code still computes both hash finals into the internal scratch before freeing; whether that buffer remains readable afterwards is not provable from this file.

<a id="u-fae3d6daf635"></a>
### `Curl_hmacit`

`CURLcode Curl_hmacit(const struct HMAC_params *hashparams, const unsigned char *key, …` · [lib/hmac.c:L143-L168][f2]

One-shot convenience wrapper that produces an HMAC digest for arbitrary data using a given hash table and key.

It rejects keylen larger than UINT_MAX with CURLE_BAD_FUNCTION_ARGUMENT, otherwise narrows the length via curlx_uztoui and delegates setup to Curl_HMAC_init, returning CURLE_OUT_OF_MEMORY if that fails. Data is consumed in a do/while loop: each pass computes ilen as CURLMIN(datalen, UINT_MAX), calls Curl_HMAC_update with that chunk, then advances data and shrinks datalen by ilen, repeating until datalen reaches zero. Curl_HMAC_final then writes the digest into output and frees the context; the function returns CURLE_OK. Because the loop is do/while, one update occurs even when datalen is zero.

calls: [Curl_HMAC_init](r3-hash-primitives.md#u-3496b0bc2abc), [Curl_HMAC_update](r3-hash-primitives.md#u-33eccf51f0ed), [Curl_HMAC_final](r3-hash-primitives.md#u-333e5a23ac24), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

**Uncertainties.**

- Behavior of curlx_uztoui for sizes above UINT_MAX is untested here, but the preceding keylen guard ensures the key length stays in range; datalen is only clamped, not guarded.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/sha256.c
[f2]: ../../../../../../eval/curl-2c04412/lib/hmac.c
