# Portable utilities and platform shims

**Capability.** Small self-contained helpers shared across the library: codec and address formatting, Windows API error/random helpers, warning-suppressing conversions, ASCII classification, line reading, and a macOS proxy-init shim.

Treat this subtree as a utility belt: nothing here knows about transfer state. Children cover the larger helpers; the remaining headers are thin, dependency-free conveniences.

**Children.**

- [Base64 codec](r4-base64-codec.md) `r4-base64-codec` · 5 unit(s)
- [Address to text formatting](r4-address-formatting.md) `r4-address-formatting` · 3 unit(s)
- [Windows API helpers](r4-windows-helpers.md) `r4-windows-helpers` · 3 unit(s)

Parent: [curl source tree](r4-curl.md)

## Units (6)

<a id="u-f4727a9d0d02"></a>
### `warnless-h-conversion-helpers`

`module_region` · [lib/curlx/warnless.h:L1-L74][f1]

Header of warning-suppressing numeric conversion helpers plus a function-cast macro.

Most functions (curlx_ultouc, curlx_uztosi, curlx_uztoul, curlx_uztoui, curlx_sltosi, curlx_sltoui, curlx_sltous, curlx_uztosz, curlx_sotouz, curlx_sztosi, curlx_uitous, curlx_sitouz, curlx_uitouz) convert between signed/unsigned and width variants by value. Range-checked variants differ: curlx_sotouz_range clamps to [uzmin, uzmax]; curlx_uztoso returns CURL_OFF_T_MAX on overflow; curlx_sztouz, curlx_sotouz_fits, and curlx_sltouz return bool FALSE on negative/oversized input and store 0 through the out pointer on failure. CURLX_FUNCTION_CAST casts a function pointer through void(*)(void) to a target type.

**Uncertainties.**

- Exact clamping vs truncation semantics of the non-annotated conversions are defined in implementations not supplied

<a id="u-6da5d72c8482"></a>
### `curl_ctype.h module code (L1–L50)`

`module_region` · [lib/curl_ctype.h:L1-L50][f2]

Header-only ASCII character-classification macros for curl's C sources.

Each macro takes a character argument and returns a nonzero/true value if it falls in the named ASCII class, else 0: ISLOWHEXALPHA/ISUPHEXALPHA test lowercase/uppercase hex letters a-f and A-F; ISLOWCNTRL casts to unsigned char and tests <= 0x1f; IS7F tests 0x7f; ISPRINT/ISGRAPH test the printable and visible ranges 0x20-0x7e and 0x21-0x7e; ISCNTRL combines ISLOWCNTRL or IS7F; ISALPHA/ISALNUM combine ISLOWER/ISUPPER and digit tests; ISXDIGIT combines digit and both hex-letter tests; ISODIGIT tests 0-7; ISBLANK is space or tab; ISSPACE is blank plus 0xa-0x0d; ISURLPUNTCS is '-', '.', '_', '~'; ISUNRESERVED is alnum plus those; ISNEWLINE is '\n' or '\r'. All comparisons are plain ASCII range checks with no locale dependence; behavior with values outside unsigned-char range is undefined except for ISLOWCNTRL, which truncates via the cast. Non-ASCII (>0x7f) inputs are false everywhere, since no macro range reaches them. Composed macros like ISXDIGIT depend on sibling macros such as ISDIGIT being in scope, which the header's include-guard-protected definitions guarantee.

**Notes.**

- contract: Macros evaluate their argument more than once, so arguments with side effects are unsafe.
- condition: Only ISLOWCNTRL applies an unsigned char cast; other macros rely on the caller passing an in-range value.

**Uncertainties.**

- Behavior when callers pass values outside 0-255 is not constrained by these macros; results depend on C integer comparison semantics at the call site.

<a id="u-fc9d0cdbcdfa"></a>
### `Curl_get_line`

`CURLcode Curl_get_line(struct dynbuf *buf, FILE *input, bool *eof)` · [lib/curl_get_line.c:L35-L67][f3]

Reads a FILE into a dynbuf and returns only whole lines terminated by a newline.

It resets the buffer, then loops: each iteration fgets()es up to 128 bytes; if fgets returns NULL and ferror() is set it returns CURLE_READ_ERROR. After each read it sets *eof from feof(input). Non-empty chunks are appended via curlx_dyn_addn; an append failure (over-long line or out of memory) propagates that CURLcode. If the accumulated buffer ends with '\n' it returns CURLE_OK. If *eof is set without a trailing newline it appends one newline and returns that append's CURLcode; otherwise it loops for more input. Callers use *eof to know the last line was consumed.

calls: [curlx_dyn_reset](r3-dynbuf.md#u-76d5fbff65c6), [curlx_dyn_addn](r3-dynbuf.md#u-f1c899173947), [dynbuf.c-accessors](r3-dynbuf.md#u-5e7007dbb9e6)

**Uncertainties.**

- If fgets returns NULL at EOF with no content read, *eof is set and a bare newline is appended, returning OK with a one-byte buffer; caller handling of that case is not visible here.

<a id="u-912fda6daed9"></a>
### `curl_get_line.c module code (L1–L34)`

`module_region` · [lib/curl_get_line.c:L1-L34][f3]

License header, curl_setup.h include, and the feature guard: the file compiles only when cookies, altsvc, HSTS or netrc support is not disabled.

<a id="u-4c9f7e5ae4a0"></a>
### `curl_get_line.c module code (L67–L69)`

`module_region` · [lib/curl_get_line.c:L67-L69][f3]

Closing #endif of the feature guard.

<a id="u-784f4e079613"></a>
### `Curl_macos_init`

`CURLcode Curl_macos_init(void)` · [lib/macos.c:L32-L48][f4]

Triggers the macOS SystemConfiguration proxy lookup so later IPv4-to-IPv6 literal conversion works.

It calls SCDynamicStoreCopyProxies(NULL) purely for its system side effect: the comment states that automagic conversion from IPv4 literals to IPv6 literals only works after this system function has run. The returned dictionary is discarded — if non-NULL it is released via CFRelease, otherwise nothing happens — and the function always returns CURLE_OK. No proxy value is used because curl does not support system-wide HTTP proxies.

**Notes.**

- side_effect: The call exists for the system-level side effect of SCDynamicStoreCopyProxies; its returned dictionary is released and ignored.
- failure: No failure path is implemented: a NULL result from SCDynamicStoreCopyProxies is silently skipped and the return value is always CURLE_OK.

uses: [macos.h module code (L1–L34)][f5]

**Uncertainties.**

- Whether SCDynamicStoreCopyProxies can return NULL on failure is not shown here; the code only guards CFRelease against a NULL dict.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/warnless.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_ctype.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_get_line.c
[f4]: ../../../../../../eval/curl-2c04412/lib/macos.c
[f5]: ../../../../../../eval/curl-2c04412/lib/macos.h
