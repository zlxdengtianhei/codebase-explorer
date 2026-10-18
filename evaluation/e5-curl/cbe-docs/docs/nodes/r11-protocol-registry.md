# scheme registry and lookup

**Capability.** The static table of known URI schemes plus length-partitioned, case-insensitive lookup of a scheme name to its descriptor.

Use Curl_get_scheme/Curl_getn_scheme as the entry points; the per-length helpers implement fast matching against the static scheme table, returning NULL for unknown schemes.

Parent: [protocol implementations](r11-protocol-layer.md)

## Units (9)

<a id="u-c09f27daaf85"></a>
### `protocol-c-scheme-table`

`group` · [lib/protocol.c:L1-L437][f1]

Defines the static table of all URI schemes libcurl knows, each as a const struct Curl_scheme with name, protocol handler pointer, protocol/family bits, PROTOPT_* flags, and default port.

Each entry guards its ->run handler with the corresponding CURL_DISABLE_* / USE_SSL / USE_SSH / HAVE_LDAP_SSL build condition, setting ZERO_NULL or NULL when the implementation is compiled out — so a matched scheme can exist without an implementation; callers must check ->run. TLS variants (ftps, https, imaps, ldaps, mqtts, pop3s, smtps, wss, gophers) additionally require USE_SSL and share the plain protocol's handler with the non-TLS family bit. The five socks* entries always have a NULL handler and PROTOPT_NO_TRANSFER, marking them as proxy-only, non-transfer schemes. ws/wss require WebSocket support plus HTTP, default to the HTTP port, and use the HTTP family.

uses: [Curl_protocol](r7-connection-metadata.md#u-db0cbc6d24eb), [Curl_scheme](r7-connection-metadata.md#u-f7b877efa786)

**Uncertainties.**

- The exact set of active schemes depends on build configuration macros not resolved in this excerpt.

<a id="u-9cb6018a95a0"></a>
### `Curl_get_scheme`

`const struct Curl_scheme *Curl_get_scheme(const char *scheme)` · [lib/protocol.c:L626-L629][f1]

Convenience wrapper that resolves a NUL-terminated scheme string by delegating to Curl_getn_scheme with strlen(scheme) as the length, so its length bounds and NULL-for-unknown behavior apply unchanged.

No state and no error reporting beyond the returned NULL.

calls: [Curl_getn_scheme](r11-protocol-registry.md#u-cf475df7f08a)

**Uncertainties.**

- Behavior depends on the input being NUL-terminated, guaranteed only by the caller.

<a id="u-cf475df7f08a"></a>
### `Curl_getn_scheme`

`const struct Curl_scheme *Curl_getn_scheme(const char *scheme, size_t len)` · [lib/protocol.c:L608-L624][f1]

Resolves a scheme name of explicit length to its scheme descriptor, or NULL.

It rejects lengths below 2 or above 7 with NULL, then dispatches through a static function table indexed by (len - 2), so two-letter names go to two_letter_scheme and so on up to seven letters. The length precondition is what makes the per-letter functions' direct indexing safe; this function itself performs no character validation. The returned entry's ->run field may be NULL when the protocol is disabled at build time, per the accompanying comment.

calls: [two_letter_scheme](r11-protocol-registry.md#u-6ac772497b0a), [three_letter_scheme](r11-protocol-registry.md#u-4e23c866177f), [four_letter_scheme](r11-protocol-registry.md#u-d9cb8ca02a29), [five_letter_scheme](r11-protocol-registry.md#u-5dbd6f62414d), [six_letter_scheme](r11-protocol-registry.md#u-384485206eb4), [seven_letter_scheme](r11-protocol-registry.md#u-dd8929a99faa); contract: [Curl_scheme](r7-connection-metadata.md#u-f7b877efa786)

**Uncertainties.**

- Whether the input needs NUL termination is not provable here since the letter functions index by position within the stated length.

<a id="u-6ac772497b0a"></a>
### `two_letter_scheme`

`static const struct Curl_scheme *two_letter_scheme(const char *scheme)` · [lib/protocol.c:L438-L444][f1]

Returns the ws scheme entry when the two input characters are 'w' and 's' case-insensitively, compared via Curl_raw_tolower on each byte; otherwise returns NULL.

Reads scheme[0] and scheme[1] directly, so the caller must guarantee at least two characters, which Curl_getn_scheme does via its length check.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

<a id="u-4e23c866177f"></a>
### `three_letter_scheme`

`static const struct Curl_scheme *three_letter_scheme(const char *scheme)` · [lib/protocol.c:L446-L464][f1]

Matches case-insensitively length-3 scheme names, lowercasing each of the three bytes up front.

On first letter 'f' it accepts 'ftp'; on 'w' it accepts 'wss'; on 's' it accepts 'scp'. Any other combination, including a correct pair after a different leading letter, returns NULL. Requires the caller to have validated the length.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

<a id="u-d9cb8ca02a29"></a>
### `four_letter_scheme`

`static const struct Curl_scheme *four_letter_scheme(const char *scheme)` · [lib/protocol.c:L466-L519][f1]

Matches case-insensitively length-4 schemes, lowercasing all four bytes.

When the last byte is 'p' it dispatches on the first: 'h'->http, 'i'->imap, 'l'->ldap, 'r'->rtsp, 't'->tftp, and 's'->sftp ('sf..') or smtp ('sm..'), each confirmed by two further exact lowered characters. When the last byte is not 'p': 'f' prefixes accept 'ftps' and 'file', 'm' accepts 'mqtt', 'p' accepts 'pop3', 'd' accepts 'dict'. Any unmatched shape returns NULL. Note that within the 's'-prefix/'p'-suffix arm, sftp is tried before smtp; both require distinct middle characters so they cannot collide. The caller must supply at least four valid bytes.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

<a id="u-5dbd6f62414d"></a>
### `five_letter_scheme`

`static const struct Curl_scheme *five_letter_scheme(const char *scheme)` · [lib/protocol.c:L521-L565][f1]

Matches case-insensitively length-5 schemes.

It first lowercases the fifth byte and returns NULL immediately unless it is 's'. Only then does it lowercase the first four bytes. With the fourth byte 'p' it switches on the first: 'h'->https, 'l'->ldaps, 'i'->imaps, 's'->smtps, each requiring 'tt', 'da', 'ma', or 'mt' as bytes two-three respectively; other first letters fall through to NULL. With a non-'p' fourth byte: 'p'->pop3s ('op3'), 'm'->mqtts ('qtt'), 's'->socks ('ock'). All other inputs return NULL. Requires at least five readable bytes.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408)

<a id="u-384485206eb4"></a>
### `six_letter_scheme`

`static const struct Curl_scheme *six_letter_scheme(const char *scheme)` · [lib/protocol.c:L567-L587][f1]

Matches case-insensitively length-6 schemes by switching on the lowercased first byte: 's' compares the next five characters against "ocks4" then "ocks5" via curl_strnequal, returning socks4 or socks5; 'g' compares against "opher" returning gopher; 't' compares against "elnet" returning telnet.

Any other first byte or failed comparison returns NULL. curl_strnequal performs the case-insensitive fixed-length comparison for the remaining bytes, so this function itself only lowercases byte zero.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

<a id="u-dd8929a99faa"></a>
### `seven_letter_scheme`

`static const struct Curl_scheme *seven_letter_scheme(const char *scheme)` · [lib/protocol.c:L589-L603][f1]

Matches case-insensitively length-7 schemes by the lowercased first byte: 's' compares the next six characters against "ocks4a" then "ocks5h" with curl_strnequal, returning socks4a or socks5h; 'g' compares against "ophers", returning gophers.

Any other first byte or failed comparison returns NULL. The caller must guarantee seven readable bytes.

uses: [protocol-c-scheme-table](r11-protocol-registry.md#u-c09f27daaf85); calls: [Curl_raw_tolower](r9-caseless-strings.md#u-e32e0b0ff408), [strequal-c-comparisons](r9-caseless-strings.md#u-ce4b12776167)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/protocol.c
