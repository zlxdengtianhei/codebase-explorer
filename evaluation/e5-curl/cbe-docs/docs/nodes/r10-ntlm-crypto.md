# NTLM Core Crypto

**Capability.** Owns NTLM message cryptography: DES primitives abstracted per crypto backend (key setup, odd parity, block encryption), LM/NT hash computation, Unicode conversion helpers, and LMv2/NTLMv2 response construction including FILETIME timestamps.

Use this child to trace NTLM credential computation. Backend selection is compile-time via the #if ladder; the response builders compose the DES and HMAC-based pieces.

Parent: [curl Codebase](r10-curl-source.md)

## Units (15)

<a id="u-f8dfaced64b5"></a>
### `lib-curl-ntlm-core-c-des-backend-abstraction`

`static void curl_des_set_odd_parity(unsigned char *bytes, size_t len)` · [lib/curl_ntlm_core.c:L120-L136][f1]

Groups the backend-conditioned DES primitives of curl_ntlm_core.c: odd-parity fixing, 56-to-64-bit key expansion, per-backend key scheduling, and per-backend single-block encryption, all static within this file.

**Notes.**

- contract: The file comment mandates keeping the backend #if branch order (OpenSSL, wolfSSL, GnuTLS, mbedTLS, OS400, Win32) so exactly one backend is selected even when several are enabled; if none is available compilation fails with #error.

uses: [Curl_ntlm_core_lm_resp](r10-ntlm-crypto.md#u-8a8459da9e03), [Curl_ntlm_core_mk_lm_hash](r10-ntlm-crypto.md#u-42a11fdcb66e)

**Uncertainties.**

- The mbedTLS branch errors out at compile time below 3.2.0, so unsupported backends are a build failure, not a runtime fallback

<a id="u-36a820c0577b"></a>
### `lib-curl-ntlm-core-c-encrypt-des`

`static bool encrypt_des(const unsigned char *in, unsigned char *out, const unsigned c…` · [lib/curl_ntlm_core.c:L201-L217][f1]

The three encrypt_des variants (mbedTLS, OS400, Win32) encrypt one 8-byte DES block under a 56-bit key and return a bool.

mbedTLS sets key parity via the library, initializes a context, sets the encryption key, and returns whether mbedtls_des_crypt_ecb succeeded. OS400 fills a cipher control structure with ENCRYPT_ONLY, applies curl_des_set_odd_parity, invokes _CIPHER, and unconditionally returns TRUE. Win32 acquires a provider with CRYPT_VERIFYCONTEXT|CRYPT_SILENT (failure returns FALSE); failed CryptImportKey releases the context and returns FALSE; otherwise it copies the 8 input bytes to out, calls CryptEncrypt, destroys key and context, and returns the CryptEncrypt result.

group: [lib-curl-ntlm-core-c-des-backend-abstraction](r10-ntlm-crypto.md#u-f8dfaced64b5)

**Uncertainties.**

- The OS400 variant always returns TRUE regardless of whether _CIPHER succeeded, so callers cannot detect OS400 encryption failure

<a id="u-cc5a18a7b380"></a>
### `lib-curl-ntlm-core-c-module-residual`

`group` · [lib/curl_ntlm_core.c:L1-L119][f1]

Non-behavioral regions of curl_ntlm_core.c: the license banner, curl_setup include, NTLM reference links, the backend-selection #if ladder with its includes, version-gated macros (USE_OPENSSL_DES, USE_WOLFSSL_DES, USE_GNUTLS_DES with nettle <4 gate, USE_MBEDTLS_DES requiring mbedTLS >= 3.2.0, USE_OS400CRYPTO, USE_WIN32_CRYPTO), the AWS-LC DES_set_key_unchecked compatibility macro, the NTLMv2 blob signature/length macros, and include directives.

The ladder's #else raises a compile-time #error when no DES-capable backend is present.

**Uncertainties.**

- The parser reported a syntax ERROR node near line 1, so some residual boundaries may be slightly misaligned even though chunk coverage is preserved

<a id="u-9d3218d359a1"></a>
### `lib-curl-ntlm-core-c-setup-des-key`

`static void setup_des_key(const unsigned char *key_56, DES_key_schedule *ks)` · [lib/curl_ntlm_core.c:L159-L171][f1]

The three setup_des_key variants (OpenSSL, wolfSSL, GnuTLS) expand a 56-bit key to 64 bits via extend_key_56_to_64, apply odd parity where the backend lacks it (GnuTLS uses curl_des_set_odd_parity; OpenSSL uses DES_set_odd_parity), and install the key schedule.

Variant selection is by the USE_*_DES macro; each writes only the caller-provided schedule and cannot fail. On AWS-LC builds DES_set_key_unchecked is macro-mapped to (void)DES_set_key.

group: [lib-curl-ntlm-core-c-des-backend-abstraction](r10-ntlm-crypto.md#u-f8dfaced64b5)

<a id="u-d6a2d6bd0fa0"></a>
### `lib-curl-ntlm-core-c-time2filetime`

`static void time2filetime(struct ms_filetime *ft, time_t t)` · [lib/curl_ntlm_core.c:L446-L487][f1]

time2filetime converts a time_t to a Windows FILETIME (tenths of a microsecond since 1601-01-01) in a caller-provided struct ms_filetime.

With 64-bit time_t it adds the 11644473600-second bias, multiplies by 10,000,000, and splits into low/high words. With 32-bit time_t it works word-by-word: it sign-extends when time_t is signed and the low word's top bit is set, adds the 0x2B6109100 bias with a carry that adds 3 or 2 to the high word, then performs the ×10,000,000 scaling with a digit-by-digit loop to avoid width overflow. No failure path; pure computation.

uses: [lib-curl-ntlm-core-c-time2filetime](r10-ntlm-crypto.md#u-d6a2d6bd0fa0)

**Uncertainties.**

- Exact 32-bit-time_t carry arithmetic is intricate (split shifts, per-digit multiply); the observed structure matches the documented bias and scaling but overflow edge cases at time_t extremes are not provable from this excerpt alone

<a id="u-8a8459da9e03"></a>
### `Curl_ntlm_core_lm_resp`

`void Curl_ntlm_core_lm_resp(const unsigned char *keys, const unsigned char *plaintext…` · [lib/curl_ntlm_core.c:L299-L343][f1]

Builds a 24-byte LM response: treats the 21-byte keys buffer as three consecutive 56-bit DES keys and encrypts the 8-byte plaintext under each, writing the three 8-byte blocks to results, results+8, results+16.

Backend branch OpenSSL/wolfSSL/GnuTLS sets up a fresh key schedule per block and calls the backend ECB encrypt; mbedTLS/OS400/Win32 calls encrypt_des three times. A residual #else discards the arguments and writes nothing, reachable only if no backend macro is set, which the backend-selection #error otherwise prevents.

calls: [lib-curl-ntlm-core-c-setup-des-key](r10-ntlm-crypto.md#u-9d3218d359a1), [lib-curl-ntlm-core-c-encrypt-des](r10-ntlm-crypto.md#u-36a820c0577b)

<a id="u-42a11fdcb66e"></a>
### `Curl_ntlm_core_mk_lm_hash`

`CURLcode Curl_ntlm_core_mk_lm_hash(const char *password, unsigned char *lmbuffer /* 2…` · [lib/curl_ntlm_core.c:L348-L394][f1]

Computes the LAN Manager hash of a password into a 21-byte lmbuffer.

It truncates the password to at most 14 bytes (CURLMIN with strlen), uppercases it into a local 14-byte buffer with Curl_strntoupper, and zero-pads the remainder. The 8-byte magic 'KGS!@#$%' is DES-encrypted under the first and second 7-byte key halves using the backend primitives, filling lmbuffer[0..15]; bytes 16..20 are then zeroed. Always returns CURLE_OK; the password is read, not modified.

calls: [lib-curl-ntlm-core-c-setup-des-key](r10-ntlm-crypto.md#u-9d3218d359a1), [lib-curl-ntlm-core-c-encrypt-des](r10-ntlm-crypto.md#u-36a820c0577b)

**Uncertainties.**

- Passwords longer than 14 characters are silently truncated, per the LM algorithm; multi-byte characters are treated as single bytes

<a id="u-235dd9395ec6"></a>
### `Curl_ntlm_core_mk_lmv2_resp`

`CURLcode Curl_ntlm_core_mk_lmv2_resp(const unsigned char *ntlmv2hash, const unsigned …` · [lib/curl_ntlm_core.c:L641-L663][f1]

Builds the 24-byte LMv2 response: HMAC-MD5 keyed by the 16-byte NTLMv2 hash over the 8-byte server challenge followed by the 8-byte client challenge; on HMAC failure the error is returned with lmresp untouched.

Otherwise lmresp receives the 16-byte HMAC output followed by a copy of the 8-byte client nonce. Always CURLE_OK on success; no allocation.

<a id="u-4714b29b2d43"></a>
### `Curl_ntlm_core_mk_nt_hash`

`CURLcode Curl_ntlm_core_mk_nt_hash(const char *password, unsigned char *ntbuffer /* 2…` · [lib/curl_ntlm_core.c:L410-L432][f1]

Computes the NT hash of a password into a 21-byte ntbuffer.

It rejects passwords longer than SIZE_MAX/2 with CURLE_OUT_OF_MEMORY to prevent overflow, allocates 2*len bytes (or strdups the empty string when len is 0), converts the password to UTF-16LE via ascii_to_unicode_le, and MD4-hashes the result with Curl_md4it. On Curl_md4it success it zeroes ntbuffer[16..20]; the MD4 error code is propagated and the scratch buffer is freed in both cases.

uses: [curl_md4.h module code (L1–L37)][f2]; calls: [ascii_to_unicode_le](r10-ntlm-crypto.md#u-b5a4be590c7f)

<a id="u-90409f0b3384"></a>
### `Curl_ntlm_core_mk_ntlmv2_hash`

`CURLcode Curl_ntlm_core_mk_ntlmv2_hash(const char *user, size_t userlen, const char *…` · [lib/curl_ntlm_core.c:L502-L529][f1]

Creates the NTLMv2 hash: HMAC-MD5 of the uppercased-Unicode user concatenated with plain-Unicode domain, keyed by the 16-byte NTLM hash.

Rejects userlen or domlen above CURL_MAX_INPUT_LENGTH with CURLE_OUT_OF_MEMORY; allocates (userlen+domlen)*2+1 bytes and returns CURLE_OUT_OF_MEMORY on allocation failure. Fills the identity with ascii_uppercase_to_unicode_le for the user and ascii_to_unicode_le for the domain, runs Curl_hmacit with Curl_HMAC_MD5, frees the scratch buffer, and propagates the HMAC result.

calls: [ascii_uppercase_to_unicode_le](r10-ntlm-crypto.md#u-1b24d15ca1a0), [ascii_to_unicode_le](r10-ntlm-crypto.md#u-b5a4be590c7f)

**Uncertainties.**

- (userlen + domlen) is not overflow-checked itself, but each component is capped at CURL_MAX_INPUT_LENGTH, so the sum fits within practical limits under that cap

<a id="u-1c9a8defd0af"></a>
### `Curl_ntlm_core_mk_ntlmv2_resp`

`CURLcode Curl_ntlm_core_mk_ntlmv2_resp(const unsigned char *ntlmv2hash, const unsigne…` · [lib/curl_ntlm_core.c:L548-L625][f1]

Builds the NTLMv2 response for a type-3 message: a 16-byte HMAC-MD5 over a blob containing signature 0x01010000, reserved zero, a 1601-based FILETIME timestamp, the 8-byte client nonce, and the type-2 message's target info.

In DEBUGBUILD, setting the CURL_FORCETIME environment variable forces timestamp zero; otherwise time(NULL) is converted via time2filetime. The response length is HMAC_MD5_LENGTH + NTLMv2_BLOB_LEN (blob depends on ntlm->target_info_len); the buffer is calloc'd and returns CURLE_OUT_OF_MEMORY on failure. The blob is formatted with curl_msnprintf, the client nonce copied at offset 32, and target info copied at offset 44 only when target_info_len is nonzero. The 8-byte server nonce is copied to ptr+8, HMAC-MD5 is computed over ptr+8 for NTLMv2_BLOB_LEN+8 bytes; on HMAC failure the buffer is freed and the error returned. Otherwise the HMAC output overwrites ptr[0..15] and *ntresp/*ntresp_len are set.

calls: [lib-curl-ntlm-core-c-time2filetime](r10-ntlm-crypto.md#u-d6a2d6bd0fa0)

**Uncertainties.**

- Correctness depends on ntlm->target_info/target_info_len/nonce fields being valid, set elsewhere (type-2 decoding); those invariants are outside this excerpt
- The blob is built via a printf-style %c format into binary data; embedded NUL bytes from LONGQUARTET are written literally by the format, but behavior relies on curl_msnprintf not truncating at NTLMv2_BLOB_LEN

<a id="u-b5a4be590c7f"></a>
### `ascii_to_unicode_le`

`static void ascii_to_unicode_le(unsigned char *dest, const char *src, size_t srclen)` · [lib/curl_ntlm_core.c:L396-L404][f1]

Converts srclen ASCII bytes to UTF-16LE in the caller's buffer: each source byte becomes a low byte followed by a zero high byte, writing 2*srclen bytes to dest.

No bounds checking and no allocation; the caller must size dest accordingly.

<a id="u-1b24d15ca1a0"></a>
### `ascii_uppercase_to_unicode_le`

`static void ascii_uppercase_to_unicode_le(unsigned char *dest, const char *src, size_…` · [lib/curl_ntlm_core.c:L489-L497][f1]

Converts srclen ASCII bytes to uppercased UTF-16LE in the caller's buffer: each byte is uppercased with Curl_raw_toupper, written as the low byte with a zero high byte, producing 2*srclen output bytes.

No bounds checking; the caller sizes dest.

uses: [lib-curl-ntlm-core-c-time2filetime](r10-ntlm-crypto.md#u-d6a2d6bd0fa0)

<a id="u-949f9166992e"></a>
### `curl_des_set_odd_parity`

`static void curl_des_set_odd_parity(unsigned char *bytes, size_t len)` · [lib/curl_ntlm_core.c:L120-L136][f1]

Adjusts each byte of the given buffer to have odd parity, for crypto backends lacking their own parity routine.

For each byte it folds bits 1..7 of the shifted value; if their parity is even it sets the low bit, otherwise it clears it. The buffer is modified in place; no return value and no failure path.

<a id="u-c5d9fd09b564"></a>
### `extend_key_56_to_64`

`static void extend_key_56_to_64(const unsigned char *key_56, char *key)` · [lib/curl_ntlm_core.c:L142-L152][f1]

Expands a 7-byte 56-bit DES key into the 8-byte 64-bit form by shifting and OR-ing successive input bytes, masking each result to 8 bits.

Pure byte arithmetic: writes exactly 8 output bytes, no error handling; the final output byte is the last input byte shifted left by one, leaving the low bit zero until parity is fixed.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_ntlm_core.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_md4.h
