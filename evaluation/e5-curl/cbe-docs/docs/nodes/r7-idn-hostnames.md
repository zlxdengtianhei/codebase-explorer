# Internationalized domain names

**Capability.** Conversion of hostnames between Unicode and ASCII punycode (A-labels), with per-platform backends and ASCII-detection helpers.

Curl_idnconvert_hostname is the main consumer entry point used during connection setup; the wrappers dispatch to macOS, Windows, or library backends. Consult when hostname conversion fails or behaves differently per platform.

**Depended on by.**

- [SMTP protocol engine](r7-smtp-protocol.md) · graph-confirmed · 8 edge(s)

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (13)

<a id="u-aea0f67ab7d1"></a>
### `Curl_idn_decode`

`CURLcode Curl_idn_decode(const char *input, char **output)` · [lib/idn.c:L314-L337][f1]

Public wrapper decoding an A-label hostname to Unicode, returning an allocated string or NULL on error.

Calls idn_decode; with libidn2, on success it strdups the idn2-allocated buffer, frees the original with idn2_free, and maps strdup failure to CURLE_OUT_OF_MEMORY (this normalizes allocation so callers can use a single free). A zero-length decoded result is rejected as CURLE_URL_MALFORMAT and freed, leaving *output unset. Otherwise *output gets the string. Non-libidn2 backends skip the re-allocation since their helpers already use the standard allocator.

calls: [idn_decode](r7-idn-hostnames.md#u-e9d9b530ff77)

**Uncertainties.**

- On failure after idn_decode succeeded but strdup failed, d was already freed, so the function must not leak, but *output is never set in any error path — callers relying on *output on error would see stale values.

<a id="u-7b908912625d"></a>
### `Curl_idn_encode`

`CURLcode Curl_idn_encode(const char *puny, char **output)` · [lib/idn.c:L339-L356][f1]

Public wrapper converting a punycode label to Unicode, mirroring Curl_idn_decode's structure.

Calls idn_encode; under libidn2 it strdups the result, frees the original with idn2_free, and sets CURLE_OUT_OF_MEMORY if the strdup fails. On overall success *output receives the allocation; there is no zero-length rejection here, unlike the decode wrapper.

calls: [idn_encode](r7-idn-hostnames.md#u-7d4dd765d4e5)

**Uncertainties.**

- Unlike Curl_idn_decode, an empty result string is accepted; whether that is intentional is not evident from this file.

<a id="u-50af72aa294f"></a>
### `Curl_idnconvert_hostname`

`CURLcode Curl_idnconvert_hostname(struct hostname *host)` · [lib/idn.c:L371-L388][f1]

Performs IDN conversion of a connection hostname in place.

It first aliases host->dispname to the original host->name. Compiled only under USE_IDN: when the name contains non-ASCII bytes it decodes it via Curl_idn_decode and, on any error, propagates that CURLcode immediately (dispname still pointing at the original name). On success it stores the decoded allocation in both host->name and host->encalloc, so the original name string is replaced by the heap copy; the caller later frees encalloc via Curl_free_idnconverted_hostname. Pure-ASCII names and non-IDN builds return CURLE_OK with no allocation.

calls: [Curl_is_ASCII_name](r7-idn-hostnames.md#u-03214be67f22), [Curl_idn_decode](r7-idn-hostnames.md#u-aea0f67ab7d1)

**Uncertainties.**

- Because host->name is replaced by the decoded allocation, the caller's original name pointer is retained only via dispname; lifetime of the caller's original string relative to encalloc is governed by code outside this file.

<a id="u-03214be67f22"></a>
### `Curl_is_ASCII_name`

`bool Curl_is_ASCII_name(const char *hostname)` · [lib/idn.c:L226-L235][f1]

Reports whether a NUL-terminated hostname contains only ASCII bytes.

A NULL hostname returns TRUE. Otherwise it wraps the string in a struct Curl_str with strlen length and delegates to Curl_is_ASCII_str, which returns FALSE on any byte with the high bit set.

calls: [Curl_is_ASCII_str](r7-idn-hostnames.md#u-d4c1854cf16b)

<a id="u-d4c1854cf16b"></a>
### `Curl_is_ASCII_str`

`bool Curl_is_ASCII_str(struct Curl_str *s)` · [lib/idn.c:L237-L248][f1]

Scans a counted string and returns FALSE if any byte has the high bit set (non-ASCII), TRUE otherwise.

A NULL pointer or zero length yields TRUE without scanning. It relies on s->str/s->len being consistent; it does not stop at embedded NULs within len.

<a id="u-cb38c4c963e7"></a>
### `iconv_to_utf8`

`static CURLcode iconv_to_utf8(const char *in, size_t inlen, char **out, size_t *outlen)` · [lib/idn.c:L53-L82][f1]

Converts a byte buffer to UTF-8 via iconv using the locale's codeset, returning a CURLcode.

On iconv_open failure it maps errno ENOMEM to CURLE_OUT_OF_MEMORY, otherwise CURLE_FAILED_INIT. After a successful open it converts in place into the caller's *out buffer, adjusts *outlen by the unconsumed remainder, closes the descriptor, and maps iconv failure to CURLE_OUT_OF_MEMORY (ENOMEM) or CURLE_URL_MALFORMAT; success returns CURLE_OK. Note *outlen is reduced by the remaining output space, i.e. it ends up holding bytes written only on success paths where iconv consumed input.

**Notes.**

- side_effect: Advances *out and shrinks *outlen; on conversion error the caller's pointer state reflects partial conversion.

uses: [mac_idn_to_ascii](r7-idn-hostnames.md#u-1d3d6a41f12f)

<a id="u-c5d7c1157636"></a>
### `idn_curlx_convert_wchar_to_UTF8`

`static char *idn_curlx_convert_wchar_to_UTF8(const wchar_t *str_w, int chars)` · [lib/idn.c:L149-L165][f1]

Converts a UTF-16 wchar string to heap-allocated UTF-8 on Windows.

First sizing WideCharToMultiByte call returns the needed byte count; bytes <= 0 yields NULL. Allocation failure also yields NULL. If the second conversion call returns 0 the buffer is freed and NULL is returned. Otherwise the malloc'ed, NUL-terminated UTF-8 string is returned.

**Uncertainties.**

- Allocation failure and conversion failure are indistinguishable to callers (both NULL), so callers cannot report CURLE_OUT_OF_MEMORY versus conversion error separately on NULL.

<a id="u-e9d9b530ff77"></a>
### `idn_decode`

`static CURLcode idn_decode(const char *input, char **output)` · [lib/idn.c:L259-L292][f1]

Backend-dispatching IDN A-label decode helper, compiled per build configuration.

With libidn2 it first verifies the library version (too-old yields CURLE_NOT_BUILT_IN), then looks up with NFC_INPUT plus NONTRANSITIONAL flags when the IDN2 version is >= 0.1.4; a failed lookup retries once with IDN2_TRANSITIONAL for IDNA2003 compatibility, and a second failure maps to CURLE_URL_MALFORMAT. With Windows it delegates to win32_idn_to_ascii, with Apple to mac_idn_to_ascii. Only when result is CURLE_OK is *output set to the decoded allocation. With no IDN backend compiled in, decoded stays NULL and CURLE_OK is returned, leaving *output untouched (guarding callers use USE_IDN).

uses: [win32_idn_to_ascii](r7-idn-hostnames.md#u-c4b06c35bc3b), [mac_idn_to_ascii](r7-idn-hostnames.md#u-1d3d6a41f12f), [Curl_idn_decode](r7-idn-hostnames.md#u-aea0f67ab7d1)

**Uncertainties.**

- Exactly one backend branch compiles per configuration; which one is active depends on build flags not visible here.

<a id="u-7d4dd765d4e5"></a>
### `idn_encode`

`static CURLcode idn_encode(const char *puny, char **output)` · [lib/idn.c:L294-L312][f1]

Backend-dispatching A-label-to-Unicode (encode to IDN) helper.

libidn2 path uses idn2_to_unicode_8z8z with flags 0, returning CURLE_OUT_OF_MEMORY on IDNA_MALLOC_ERROR and CURLE_URL_MALFORMAT on any other failure. Windows delegates to win32_ascii_to_idn, Apple to mac_ascii_to_idn, propagating their CURLcode directly. On success *output receives the allocation and CURLE_OK is returned; as in idn_decode, an unconfigured build returns CURLE_OK without setting *output.

uses: [win32_ascii_to_idn](r7-idn-hostnames.md#u-ae3c8eb21b2e), [mac_ascii_to_idn](r7-idn-hostnames.md#u-268a0add387a), [Curl_idn_encode](r7-idn-hostnames.md#u-7b908912625d)

**Uncertainties.**

- The libidn2 success check compares rc against IDNA_SUCCESS (an IDNA2003 constant) rather than an IDN2_* code; behavior on other non-error IDNA rc values is unclear from this source.

<a id="u-268a0add387a"></a>
### `mac_ascii_to_idn`

`static CURLcode mac_ascii_to_idn(const char *in, char **out)` · [lib/idn.c:L118-L141][f1]

On Apple platforms converts a punycode (ASCII) label back to Unicode via ICU.

Inputs of length >= MAX_HOST_LENGTH (512) return CURLE_URL_MALFORMAT. It opens UTS46 with BIDI-check and non-transitional-to-UNICODE flags; open failure or a failed uidna_nameToUnicodeUTF8 call results in CURLE_URL_MALFORMAT (the function's only fallthrough return). On success *out is a strdup of the Unicode UTF-8 buffer, with NULL allocation mapped to CURLE_OUT_OF_MEMORY. Unlike mac_idn_to_ascii, only U_FAILURE(err) is checked; info.errors is ignored.

**Uncertainties.**

- info.errors from uidna_nameToUnicodeUTF8 is not consulted, so labels ICU flags as erroneous may still be accepted.

<a id="u-1d3d6a41f12f"></a>
### `mac_idn_to_ascii`

`static CURLcode mac_idn_to_ascii(const char *in, char **out)` · [lib/idn.c:L84-L116][f1]

On Apple platforms converts an IDN hostname to ASCII punycode.

Input longer than or equal to MAX_HOST_LENGTH (512) is rejected with CURLE_URL_MALFORMAT without touching *out. Otherwise the input is iconv-converted to UTF-8 into a stack buffer; if iconv_to_utf8 fails its code is propagated directly. On success uidna_openUTS46 is opened with BIDI-check and non-transitional-to-ASCII flags; a U_FAILURE at open skips conversion and falls through to CURLE_URL_MALFORMAT. uidna_nameToASCII_UTF8 result is intentionally ignored; conversion succeeds only when err is not a failure and info.errors is zero, in which case *out is a strdup of the ASCII buffer (NULL strdup yields CURLE_OUT_OF_MEMORY). Any ICU error or reported info.errors also ends as CURLE_URL_MALFORMAT.

calls: [iconv_to_utf8](r7-idn-hostnames.md#u-cb38c4c963e7)

**Uncertainties.**

- The uidna_nameToASCII_UTF8 return code is discarded ((void) cast); success is judged only by UErrorCode and info.errors, so partial-error semantics of ICU are not distinguishable here.

<a id="u-ae3c8eb21b2e"></a>
### `win32_ascii_to_idn`

`static CURLcode win32_ascii_to_idn(const char *in, char **out)` · [lib/idn.c:L194-L219][f1]

Windows ASCII/punycode-to-Unicode conversion using IdnToUnicode, mirroring win32_idn_to_ascii.

*out starts NULL. MultiByteToWideChar with MB_ERR_INVALID_CHARS failure (zero return) returns CURLE_URL_MALFORMAT. IdnToUnicode returning <= 0 also returns CURLE_URL_MALFORMAT. On success the UTF-16 result goes through idn_curlx_convert_wchar_to_UTF8; NULL yields CURLE_OUT_OF_MEMORY, otherwise CURLE_OK and *out holds the UTF-8 Unicode name. The terminator from the wide conversion is preserved through to *out.

calls: [idn_curlx_convert_wchar_to_UTF8](r7-idn-hostnames.md#u-c5d7c1157636)

<a id="u-c4b06c35bc3b"></a>
### `win32_idn_to_ascii`

`static CURLcode win32_idn_to_ascii(const char *in, char **out)` · [lib/idn.c:L167-L192][f1]

Windows IDN-to-ASCII conversion using IdnToAscii.

Sets *out to NULL first. The input UTF-8 string is converted to UTF-16 with MB_ERR_INVALID_CHARS; a zero return (invalid input or buffer overflow at IDN_MAX_LENGTH=255) returns CURLE_URL_MALFORMAT. IdnToAscii returning <= 0 likewise returns CURLE_URL_MALFORMAT. On success the punycode is converted back to UTF-8 via idn_curlx_convert_wchar_to_UTF8; NULL there propagates CURLE_OUT_OF_MEMORY, otherwise CURLE_OK with the punycode in *out. Per the in-code comment, the NUL terminator from MultiByteToWideChar is preserved so the returned buffer is terminated.

calls: [idn_curlx_convert_wchar_to_UTF8](r7-idn-hostnames.md#u-c5d7c1157636)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/idn.c
