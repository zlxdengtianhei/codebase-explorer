# MD4 digest backends

**Capability.** Computes MD4 digests through whichever crypto backend the build configures (OpenSSL, wolfSSL, GnuTLS/nettle, CommonCrypto, Win32 CryptoAPI) or a self-contained RFC 1320 fallback, behind the single Curl_md4it entry point.

Use this node when a digest is needed (e.g. NTLM-family auth): Curl_md4it hides the backend; my_md4_body is the fallback block compressor. Each backend region is exclusive per build.

Parent: [Authentication and crypto primitives](r4-auth-crypto.md)

## Units (8)

<a id="u-3e2e4d27e9c6"></a>
### `md4-commoncrypto-backend`

`static int my_md4_init(my_md4_ctx *ctx)` · [lib/md4.c:L114-L117][f1]

CommonCrypto-backed MD4 primitives for Apple builds matching the macOS or iOS version ranges in the surrounding preprocessor condition.

my_md4_init returns CC_MD4_Init's result (commented as always 1); my_md4_update casts the length to CC_LONG and calls CC_MD4_Update, ignoring the return; my_md4_final calls CC_MD4_Final, also ignoring its return. The CC_LONG cast means inputs longer than CC_LONG's width would truncate, though CC_LONG is 32-bit unsigned on these platforms.

**Uncertainties.**

- Actual CC_MD4_* return values on failure are not defined in this source

<a id="u-1d01b3c2b237"></a>
### `md4-fallback-implementation`

`struct md4_ctx` · [lib/md4.c:L233-L238][f1]

Self-contained RFC 1320 MD4 implementation used when no configured crypto library provides MD4.

The md4_ctx struct holds byte counters lo/hi, state words a-d, a 64-byte buffer, and a 16-word block. The MD4_F/G/H macros and MD4_STEP implement the three rounds; on i386/x86_64/vax MD4_SET reads words directly (little-endian unaligned access), otherwise it assembles words byte-by-byte into ctx->block, which also stores them for MD4_GET in later rounds. my_md4_init sets the standard IV 0x67452301/0xefcdab89/0x98badcfe/0x10325476 with lo=hi=0 and returns 1. my_md4_update maintains the bit counter (lo wraps modulo 2^29 with carry into hi plus len>>29), fills any partial buffered block, processes whole 64-byte blocks through my_md4_body, and buffers the remainder; a len under 64 with a partially filled buffer just accumulates and returns. my_md4_final appends 0x80 padding, zero-fills, adds an extra block when fewer than 8 bytes remain, writes the little-endian 64-bit bit length via curlx_ultouc, runs one final block, serializes a-d little-endian into the 16-byte digest, and zeroes the context. It never reports failure.

calls: [my_md4_body](r4-md4-digest.md#u-807821d29f15)

**Uncertainties.**

- The do/while(size -= 64) loop in my_md4_body relies on size being a nonzero multiple of 64; passing a size that is a multiple of 64 is guaranteed only by the callers' masking in this file.
- The length arithmetic caps lo at 29 bits; behavior for inputs near or beyond 2^61 bits follows the hi-counter logic but is not exercised by any visible test.

<a id="u-c226d23d4ebf"></a>
### `md4-gnutls-backend`

`static int my_md4_init(my_md4_ctx *ctx)` · [lib/md4.c:L184-L188][f1]

Nettle-backed MD4 primitives for USE_GNUTLS builds.

my_md4_init wraps md4_init and always returns 1; my_md4_update forwards to md4_update with the length first; my_md4_final calls md4_digest with an explicit MD4_DIGEST_SIZE argument on nettle major version below 4 and without it on version 4 or newer, reflecting the nettle API change. No error propagation exists in this backend.

<a id="u-723aa25c154b"></a>
### `md4-openssl-backend`

`static int my_md4_init(my_md4_ctx *ctx)` · [lib/md4.c:L50-L61][f1]

Provides the OpenSSL-backed MD4 primitives selected when USE_OPENSSL is defined and MD4 is not disabled.

my_md4_init allocates an EVP_MD_CTX and initializes it for MD4, returning 0 on allocation or EVP_DigestInit_ex failure and freeing the context on the latter; it returns 1 on success. my_md4_update feeds input via EVP_DigestUpdate, discarding its result, so update failures are not surfaced. my_md4_final writes the digest via EVP_DigestFinal_ex (result ignored) and frees the context, making final one-shot and non-repeatable.

uses: [Curl_md4it](r4-md4-digest.md#u-fa8fd828b273)

**Uncertainties.**

- EVP_DigestUpdate/EVP_DigestFinal_ex return values are deliberately ignored, so failure behavior of this backend is unobservable to callers

<a id="u-fb68f063c9f4"></a>
### `md4-win32-crypto-backend`

`struct md4_ctx` · [lib/md4.c:L133-L136][f1]

Windows CryptoAPI-backed MD4 primitives for USE_WIN32_CRYPTO builds.

The local md4_ctx struct holds an HCRYPTPROV and an HCRYPTHASH. my_md4_init zeroes both handles, acquires a PROV_RSA_FULL context with CRYPT_VERIFYCONTEXT|CRYPT_SILENT (returning 0 on failure), and creates a CALG_MD4 hash; if CryptCreateHash fails it releases the provider, resets the handle, and returns 0. my_md4_update hashes data via CryptHashData without checking its result. my_md4_final queries HP_HASHVAL for its length and copies the digest only if the length equals MD4_DIGEST_LENGTH, otherwise leaving the output buffer untouched; it always destroys the hash and releases the provider when the handles are nonzero.

**Notes.**

- failure: If CryptGetHashParam reports a length other than MD4_DIGEST_LENGTH, the digest buffer is left uninitialized and no error is signaled.

**Uncertainties.**

- Whether the caller can detect the wrong-length case is not visible here; my_md4_final returns void.

<a id="u-2e5af83176ef"></a>
### `md4-wolfssl-backend`

`static int my_md4_init(my_md4_ctx *ctx)` · [lib/md4.c:L85-L89][f1]

WolfSSL-backed MD4 primitives compiled when USE_WOLFSSL and !NO_MD4 are defined.

The context type is wc_Md4 for wolfSSL 5.7.6+ (LIBWOLFSSL_VERSION_HEX >= 0x05007006) and the legacy Md4 type otherwise. my_md4_init wraps wc_InitMd4 and always returns 1; my_md4_update wraps wc_Md4Update after truncating the length to word32; my_md4_final wraps wc_Md4Final to write the digest. No error paths are propagated to callers.

**Uncertainties.**

- Whether wc_InitMd4/wc_Md4Update can fail and with what effect is not visible from this file

<a id="u-fa8fd828b273"></a>
### `Curl_md4it`

`CURLcode Curl_md4it(unsigned char *output, const unsigned char *input, const size_t len)` · [lib/md4.c:L474-L483][f1]

Computes the 16-byte MD4 digest of input into output in one call, hiding the backend differences.

It declares a my_md4_ctx, returns CURLE_FAILED_INIT if my_md4_init fails (only possible on the OpenSSL and Win32 backends), then calls my_md4_update with the length narrowed by curlx_uztoui — a size_t larger than UINT_MAX would truncate — and my_md4_final, returning CURLE_OK. Update errors, if any, are silently ignored by the backend wrappers, so the only reported failure is initialization.

calls: [md4-openssl-backend](r4-md4-digest.md#u-723aa25c154b); uses: [md4-fallback-implementation](r4-md4-digest.md#u-1d01b3c2b237)

**Uncertainties.**

- Which backend my_md4_* resolve to depends on preprocessor configuration not decidable from this file alone.
- Behavior when curlx_uztoui truncates len is not defined beyond the numeric narrowing.

<a id="u-807821d29f15"></a>
### `my_md4_body`

`static const void *my_md4_body(my_md4_ctx *ctx, const void *input, unsigned long size)` · [lib/md4.c:L281-L370][f1]

Compresses one or more 64-byte blocks into the MD4 state without touching the bit counters.

It saves a-d from the context, then for each block performs the 16 F-steps, 16 G-steps (adding 0x5a827999) and 16 H-steps (adding 0x6ed9eba1) via MD4_STEP macros, adds the saved values back, and advances the input pointer 64 bytes. The do/while continues while (size -= 64) is nonzero, so size must be a positive multiple of 64; it never terminates early. On return it stores the updated state back into the context and returns the pointer past the consumed blocks so callers can resume with leftover bytes.

uses: [md4-fallback-implementation](r4-md4-digest.md#u-1d01b3c2b237)

**Uncertainties.**

- A size of 0 would run one loop iteration because the do-while tests after the body; callers in this file never pass 0.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/md4.c
