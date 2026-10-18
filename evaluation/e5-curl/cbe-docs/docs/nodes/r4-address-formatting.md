# Address to text formatting

**Capability.** Converts network-format IPv4 and IPv6 addresses into presentation text, compressing the longest zero run in IPv6 with '::', returning CURLcode results.

Call curlx_inet_ntop with the address family; it dispatches to inet_ntop4 or inet_ntop6. Useful wherever presentation-form addresses are logged or built without platform inet_ntop.

Parent: [Portable utilities and platform shims](r4-portable-utils.md)

## Units (3)

<a id="u-4a1e424cecdf"></a>
### `curlx_inet_ntop`

`CURLcode curlx_inet_ntop(int af, const void *src, char *buf, size_t size)` · [lib/curlx/inet_ntop.c:L189-L199][f1]

Converts a network-format address to presentation text by address family: AF_INET forwards to inet_ntop4, AF_INET6 to inet_ntop6, returning that function's CURLcode unchanged.

Any other family returns CURLE_UNSUPPORTED_PROTOCOL without touching buf. When USE_IPV6 is disabled and AF_INET6 is undefined, the file defines AF_INET6 as AF_INET+1 so IPv6 conversion still works.

calls: [inet_ntop4](r4-address-formatting.md#u-f6560981a783), [lib/curlx/inet_ntop.c:inet_ntop6](r4-address-formatting.md#u-bdd0421ebe54)

<a id="u-f6560981a783"></a>
### `inet_ntop4`

`static CURLcode inet_ntop4(const unsigned char *src, char *dst, size_t size)` · [lib/curlx/inet_ntop.c:L56-L75][f1]

Formats a 4-byte network-order IPv4 address as dotted-decimal text.

It renders into a local temp buffer sized for '255.255.255.255' using SNPRINTF (stated not to overflow), asserts size >= 16, then rejects the result if its length is zero or not smaller than size, returning CURLE_TOO_LARGE. Otherwise it copies via curlx_strcopy and returns CURLE_OK; dst is written only on success.

calls: [curlx_strcopy](r12-string-time-utils.md#u-902a4ccc6a41), [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- Behavior of DEBUGASSERT on failure depends on build configuration not shown.

<a id="u-bdd0421ebe54"></a>
### `lib/curlx/inet_ntop.c:inet_ntop6`

`static CURLcode inet_ntop6(const unsigned char *src, char *dst, size_t size)` · [lib/curlx/inet_ntop.c:L94-L182][f1]

Converts a 16-byte IPv6 address to RFC-style presentation text, compressing the longest zero run of at least two 16-bit words with '::'.

Byte pairs are packed into words; a scan finds the best zero run (runs shorter than 2 are discarded). Formatting emits lowercase hex per word with leading zeroes omitted, skipping the chosen run and writing ':' at its start; a trailing ':' is appended when the run reaches the last word. If the run starts at word 0 and the address is an encapsulated IPv4 (best.len 6, or 5 with words[5]==0xffff), words 12-15 are formatted by inet_ntop4 into the remaining temp space and its error CURLcode is propagated. Output is built in a local tmp buffer; if the produced length is >= size it returns CURLE_TOO_LARGE without touching dst, otherwise curlx_strcopy copies it and CURLE_OK is returned.

calls: [inet_ntop4](r4-address-formatting.md#u-f6560981a783), [curlx_strcopy](r12-string-time-utils.md#u-902a4ccc6a41)

**Uncertainties.**

- The formatting loop relies on tmp being large enough for the longest form; no explicit inner bounds guard is visible, so safety rests on that size arithmetic.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/inet_ntop.c
