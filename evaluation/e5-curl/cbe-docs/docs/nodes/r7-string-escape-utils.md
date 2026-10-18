# String escaping and encoding

**Capability.** Percent-encoding/decoding of URL data, hex encoding of binary, and the allocator-matching curl_free, plus endian byte-swap helpers.

Call these for URL-safe string conversion and for freeing strings returned by the library. Consumers include the SMTP parser and the CLI tool.

**Depended on by.**

- [SMTP protocol engine](r7-smtp-protocol.md) · graph-confirmed · 2 edge(s)
- [Transfer preparation](r7-tool-transfer-prep.md) · graph-confirmed · 3 edge(s)

Parent: [Shared infrastructure utilities](r7-shared-infra.md)

## Units (9)

<a id="u-dfd3e53b2fbc"></a>
### `Curl_hexbyte`

`void Curl_hexbyte(unsigned char *dest, /* must fit two bytes */ unsigned char val)` · [lib/escape.c:L372-L377][f1]

Writes one byte as exactly two uppercase hex characters into dest, using Curl_udigits for each nibble; dest must have room for two bytes and no terminator is added.

uses: [curl_printf.h module code (L1–L37)][f2]

<a id="u-9e7ae5f6fc46"></a>
### `Curl_hexencode`

`void Curl_hexencode(const unsigned char *src, size_t len, /* input length */ unsigned…` · [lib/escape.c:L350-L366][f1]

Encodes binary input as lowercase hex ASCII, null-terminated, writing at most as many whole byte-pairs as the output buffer allows.

In release builds a bad combination (NULL src, zero len, or olen < 3) leaves the caller's buffer untouched except that a nonzero olen gets a single terminating zero at out[0]; DEBUGASSERT would trap such misuse in debug builds. The loop emits two digits per input byte via Curl_ldigits, consuming three output bytes per iteration (two digits plus room for the terminator), and stops when either input is exhausted or fewer than three bytes of output space remain; it then null-terminates. Partial trailing bytes are truncated, not an error.

**Notes.**

- condition: If olen is too small for the whole input, output is silently truncated and still null-terminated.

uses: [curl_printf.h module code (L1–L37)][f2]

**Uncertainties.**

- The exact minimum olen guaranteeing full encoding of len bytes is implied by the loop (2*len+1) but not stated in the source.

<a id="u-0db7582a0fb5"></a>
### `Curl_urldecode`

`CURLcode Curl_urldecode(const char *string, size_t length, char **ostring, size_t *ol…` · [lib/escape.c:L223-L303][f1]

Internal percent-decoder producing a malloc'ed decoded string with its length; returns CURLE_OK or CURLE_URL_MALFORMAT/CURLE_OUT_OF_MEMORY.

A zero input length means strlen(string); DEBUGASSERT crashes debug builds on NULL string or a ctrl value of 0/1 (legacy TRUE/FALSE). The reject mode sets a limit byte: REJECT_CTRL rejects bytes below 0x20, REJECT_ZERO rejects decoded zero bytes, REJECT_NADA accepts all. The scan has two paths: on '%' with more than two bytes left, both following bytes must map through hextable as hex digits (high nibbles clear), yielding one decoded byte checked against the limit; otherwise the '%' is copied literally. Non-'%' runs are bulk-copied up to the next '%' via memchr, with rejection checks applied over the whole run (memchr for zero, a loop for control bytes) before copying. On any rejection the output buffer is freed, *ostring cleared via curlx_safefree, and CURLE_URL_MALFORMAT returned. On success the string is terminated and *olen (if non-NULL) receives the decoded length.

**Notes.**

- failure: Allocation failure returns CURLE_OUT_OF_MEMORY before *ostring is set, whereas rejection frees *ostring and returns CURLE_URL_MALFORMAT.
- contract: A truncated escape sequence like '%A' is copied literally rather than rejected.

**Uncertainties.**

- The branch condition `alloc > 2` means a trailing '%XY' at the very end with exactly two bytes remaining is treated as literal text; whether that is intentional for all callers is not stated in this file.

<a id="u-dc93e6e10bfa"></a>
### `curl_easy_escape`

`char *curl_easy_escape(CURL *curl, const char *string, int length)` · [lib/escape.c:L156-L205][f1]

Percent-encodes bytes not usable verbatim in a URL, returning a newly allocated encoded string; the curl parameter is ignored since 7.82.0.

Input semantics: NULL string or negative length returns NULL; a zero length means strlen(string), and an empty string yields an allocated empty string via curlx_strdup. Sizes above SIZE_MAX/16 are rejected with NULL to bound the (len*3)+1 worst-case allocation, which itself returns NULL on allocation failure. Encoding scans via the static hextable: when hextable[byte] has the high bit clear the byte is appended verbatim (hextable marks only non-hex-digit ASCII printable characters and '-'/'.' with _OK_, so alphanumerics, '%', and other special characters are encoded); bytes needing encoding are flushed from a pending run with memcpy and then written as '%XY' using the static hexpairs table. The result is always null-terminated.

**Notes.**

- side_effect: Allocates the returned buffer with curlx_malloc; the caller owns and must free it (e.g. via curl_free).

uses: [curl_printf.h module code (L1–L37)][f2]

**Uncertainties.**

- Whether hextable's exact accepted-verbatim character set matches any RFC rule is only inferable from the table contents, not from a stated specification in this file.

<a id="u-9edd19c848c9"></a>
### `curl_easy_unescape`

`char *curl_easy_unescape(CURL *curl, const char *string, int inlength, int *outlength)` · [lib/escape.c:L312-L334][f1]

Public unescape entry point that decodes a percent-escaped string and returns a newly allocated decoded string, with the handle ignored since 7.82.0.

NULL string or negative input length returns NULL without decoding; zero length means strlen(string). Decoding delegates to Curl_urldecode with REJECT_NADA, so no byte is rejected here; a decoder failure returns NULL. When outlength is non-NULL, a decoded length within INT_MAX is stored via curlx_uztosi, but if the decoded output exceeds INT_MAX the string is freed and NULL is returned because the length cannot be reported in an int.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

<a id="u-12bc348ba71a"></a>
### `curl_escape`

`char *curl_escape(const char *string, int length)` · [lib/escape.c:L36-L39][f1]

Legacy ABI wrapper that percent-encodes a string using the modern escape implementation.

It forwards the string and length directly to curl_easy_escape with a NULL handle, so input validation, allocation, and encoding behavior are entirely that callee's; it returns the callee's new allocated string or NULL on invalid input or allocation failure.

calls: [curl_easy_escape](r7-string-escape-utils.md#u-dc93e6e10bfa)

<a id="u-1328a1020607"></a>
### `curl_free`

`void curl_free(void *p)` · [lib/escape.c:L339-L342][f1]

Frees memory using the library's allocator so that pointers returned by this library (e.g. curl_easy_escape) can be released even when the application uses a different malloc/free system; it forwards to curlx_free and ignores NULL per that allocator's contract.

**Uncertainties.**

- Whether curlx_free accepts NULL is not shown in this file.

<a id="u-9a0ea393035d"></a>
### `curl_unescape`

`char *curl_unescape(const char *string, int length)` · [lib/escape.c:L42-L45][f1]

Legacy ABI wrapper that percent-decodes a string by forwarding to curl_easy_unescape with a NULL handle and NULL output-length pointer.

It therefore returns a newly allocated decoded string, or NULL on invalid input, malformed data, or allocation failure, and never reports the decoded length.

calls: [curl_easy_unescape](r7-string-escape-utils.md#u-9edd19c848c9)

<a id="u-63b0bdb77e38"></a>
### `curl_endian-c-byte-swap-helpers`

`unsigned short Curl_read16_le(const unsigned char *buf)` · [lib/curl_endian.c:L41-L45][f3]

Byte-order conversion helpers that assemble host-order integers from raw byte buffers.

Curl_read16_le returns buf[0] | buf[1]<<8; Curl_read32_le ORs four bytes with shifts 8/16/24; Curl_read16_be returns buf[0]<<8 | buf[1]. All operands are cast through unsigned short/unsigned int, so no sign extension occurs and results are the exact encoded values. Each is a single straight-line return: no branches, failure paths, or side effects. The buffer length is not checked; buf must point to at least 2 (16-bit) or 4 (32-bit) readable bytes or behavior is undefined.

contract: [curl_endian.h module code (L1–L36)][f4]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/escape.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_printf.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_endian.c
[f4]: ../../../../../../eval/curl-2c04412/lib/curl_endian.h
