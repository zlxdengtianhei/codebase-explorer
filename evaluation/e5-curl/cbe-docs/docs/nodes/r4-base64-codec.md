# Base64 codec

**Capability.** Encodes and decodes base64 with standard and URL-safe alphabets, sharing one static core encoder that takes the alphabet table and pad byte as parameters.

Use curlx_base64_encode for RFC 4648 output and curlx_base64url_encode for the unpadded URL/filename-safe variant; decode allocates a new buffer and returns a CURLcode.

Parent: [Portable utilities and platform shims](r4-portable-utils.md)

## Units (5)

<a id="u-5a5d1f7c650e"></a>
### `base64-h-interfaces`

`module_region` · [lib/curlx/base64.h:L1-L40][f1]

Header declaring base64 encoding/decoding entry points: curlx_base64_encode, curlx_base64url_encode (URL-safe alphabet), and curlx_base64_decode, each taking an input buffer and returning a CURLcode with outputs via out pointer and length.

Also exposes the shared alphabet table curlx_base64encdec and CURL_MAX_BASE64_INPUT (16,000,000), an input-length cap meant to catch misuse of the encoder. Only declarations are present in this file; behavior lives elsewhere.

**Uncertainties.**

- Return codes for invalid input or allocation failure are defined in the implementation, not this header

<a id="u-41326e685d75"></a>
### `base64_encode`

`static CURLcode base64_encode(const char *table64, uint8_t padbyte, const uint8_t *in…` · [lib/curlx/base64.c:L185-L251][f2]

Static core encoder shared by the public base64 and base64url wrappers; maps input bytes through a caller-supplied 64-char table with an optional pad byte.

On insize==0 it returns CURLE_OK with *outptr NULL and *outlen 0. If insize exceeds CURL_MAX_BASE64_INPUT it returns CURLE_TOO_LARGE (a DEBUGASSERT also guards this in debug builds). It allocates ((insize+2)/3*4)+1 bytes; allocation failure returns CURLE_OUT_OF_MEMORY. Full 3-byte groups are packed into a 32-bit value and emitted as four table lookups. A 1-byte remainder emits two characters plus two pad bytes when padbyte is nonzero; a 2-byte remainder emits three characters plus one pad byte. With padbyte 0 (URL-safe mode) no padding characters are emitted, so the output length is 2 or 3 for such remainders. The result is null-terminated and its length returned via *outlen.

uses: [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f), [curlx_base64url_encode](r4-base64-codec.md#u-d51c529eeabe)

<a id="u-153cda566bc5"></a>
### `curlx_base64_decode`

`CURLcode curlx_base64_decode(const char *src, uint8_t **outptr, size_t *outlen)` · [lib/curlx/base64.c:L88-L183][f2]

Decodes a null-terminated base64 string into a newly allocated buffer.

It first zeroes *outptr and *outlen, computes strlen, and rejects inputs that are empty or whose length is not a multiple of 4 with CURLE_BAD_CONTENT_ENCODING. It then counts trailing '=' padding, allowing at most two; a third immediately fails. Decoded size is quantums*3 minus padding. After allocating rawlen+1 bytes via curlx_malloc (failure returns CURLE_OUT_OF_MEMORY), it decodes full 4-char quantums using the static decodetable; if any of the four table values has the high bit set (0xff, invalid symbol) it jumps to the failure path, which frees the buffer and returns CURLE_BAD_CONTENT_ENCODING. The final partial quantum with padding is decoded specially: '=' shifts in zeros and increments padc, which must not exceed the earlier padding count; non-'=' characters must map to a value other than 0xff. Note 0xff is also the decoded value for '+', so a '+' in the final quantum is treated as invalid. With one padding byte the middle decoded byte is written, then pos advances by 3-padding. The buffer is null-terminated, and only on CURLE_OK are *outptr and *outlen populated.

uses: [base64.c module code (L1–L87)][f2]

**Uncertainties.**

- The graph links this function to fwrite_xattr, but the source shows no such call; that edge is not supported by this excerpt.
- Failure of curlx_malloc mid-decode leaves *outptr NULL, per the early assignment.

<a id="u-6cff14e8366f"></a>
### `curlx_base64_encode`

`CURLcode curlx_base64_encode(const uint8_t *inputbuff, size_t insize, char **outptr, …` · [lib/curlx/base64.c:L266-L271][f2]

Public wrapper that encodes input with the standard RFC 4648 base64 alphabet and '=' padding, delegating entirely to the static core encoder, which sets the documented empty-input, oversize-input, and allocation-failure behaviors.

calls: [base64_encode](r4-base64-codec.md#u-41326e685d75)

<a id="u-d51c529eeabe"></a>
### `curlx_base64url_encode`

`CURLcode curlx_base64url_encode(const uint8_t *inputbuff, size_t insize, char **outpt…` · [lib/curlx/base64.c:L288-L292][f2]

Public wrapper that encodes input with the RFC 4648 section 5 URL/filename-safe alphabet ('-' and '_') and no padding, delegating to the static core encoder with padbyte 0; output is therefore unpadded for 1- or 2-byte remainders.

calls: [base64_encode](r4-base64-codec.md#u-41326e685d75)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/base64.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/base64.c
