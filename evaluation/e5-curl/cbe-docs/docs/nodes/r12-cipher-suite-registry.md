# Cipher-suite name registry

**Capability.** Compile-time compressed table mapping cipher-suite names (OpenSSL and IANA spellings) to 16-bit IANA ids, with forward and reverse lookups and list-token walking for backends lacking native name support.

Use via Curl_cipher_suite_lookup_id and Curl_cipher_suite_get_str. cs_str_to_zip/cs_zip_to_str encode against the compressed table.

Parent: [TLS infrastructure](r12-tls-infrastructure.md)

## Units (7)

<a id="u-ef3ee1bd7f3e"></a>
### `cipher_suite.c-compressed-table`

`enum` · [lib/vtls/cipher_suite.c:L92-L132][f1]

Provides a compile-time compressed table mapping cipher-suite names (OpenSSL and IANA spellings) to IANA 16-bit ids, for SSL backends lacking native name support.

cs_txt is a NUL-separated string pool of known name parts; the enum assigns an index (<64) to each part and must stay in sync with the pool. CS_ZIP_IDX/CS_ENTRY macros pack eight part indexes into 6 bytes (6-bit fields, 48 bits) next to the id, forming struct cs_entry. cs_list holds TLS 1.3 suites unconditionally; the larger TLS 1.2 and non-standard (ARIA/CAMELLIA/PSK/CCM etc.) entries compile only under USE_MBEDTLS. Most ids appear twice — once with the 'TLS...WITH...' RFC form and once with the short OpenSSL form — both zipping to the same id. Empty trailing slots zip as index 0, which is also the empty-string sentinel.

uses: [cs_str_to_zip](r12-cipher-suite-registry.md#u-082266582543), [cs_zip_to_str](r12-cipher-suite-registry.md#u-60d9df51b9bb)

**Uncertainties.**

- Exact ordering guarantees of cs_list are inferred from the literal order; no sorting invariant is stated in code

<a id="u-8f8beb417a19"></a>
### `Curl_cipher_suite_get_str`

`int Curl_cipher_suite_get_str(uint16_t id, char *buf, size_t buf_size, bool prefer_rfc)` · [lib/vtls/cipher_suite.c:L676-L700][f1]

Public reverse lookup: writes the name for id into buf and returns 0, or -1 after writing a 'TLS_UNKNOWN_0x%04x' placeholder.

It scans cs_list for matching ids. Selection rule: when the entry's first part is TLS-prefixed XOR not prefer_rfc — i.e. it matches the caller's preferred naming style — it is chosen immediately; otherwise the first matching entry of the other style is remembered as fallback. If no matching id exists, j stays CS_LIST_LEN and r stays -1, triggering the unknown placeholder. Decompression via cs_zip_to_str can also fail (-1 on bad index or formatting), falling back to the same placeholder even for a tabled id.

**Notes.**

- failure: A formatting failure from cs_zip_to_str is indistinguishable from an unknown id in the return value (-1), though buf still receives the unknown placeholder

calls: [cs_zip_to_str](r12-cipher-suite-registry.md#u-60d9df51b9bb); uses: [cipher_suite.c-compressed-table](r12-cipher-suite-registry.md#u-ef3ee1bd7f3e)

**Uncertainties.**

- The XOR condition (zip[0]>>2 != TLS_IDX) == !prefer_rfc is taken at face value; its intended RFC-vs-OpenSSL preference semantics were not independently verified against cs_zip_to_str output

<a id="u-b79ade9a6a08"></a>
### `Curl_cipher_suite_lookup_id`

`uint16_t Curl_cipher_suite_lookup_id(const char *cs_str, size_t cs_len)` · [lib/vtls/cipher_suite.c:L635-L648][f1]

Public lookup: returns the IANA id for a cipher-suite name, or 0 when unknown.

If cs_len is 0 it returns 0 without touching cs_str; otherwise it compresses the name with cs_str_to_zip and linearly scans cs_list comparing the 6-byte zip with memcmp. The first byte-identical entry's id wins, which means the OpenSSL-short and RFC forms resolve to the same id because both were tabled under it. An empty-string part mismatch inside cs_str_to_zip also yields 0 via the -1 path.

calls: [cs_str_to_zip](r12-cipher-suite-registry.md#u-082266582543); uses: [cipher_suite.c-compressed-table](r12-cipher-suite-registry.md#u-ef3ee1bd7f3e)

<a id="u-4dda6463f29f"></a>
### `Curl_cipher_suite_walk_str`

`uint16_t Curl_cipher_suite_walk_str(const char **str, const char **end)` · [lib/vtls/cipher_suite.c:L663-L674][f1]

Extracts the next cipher-suite token from a separator-delimited list and returns its id.

Using cs_is_separator (space, tab, ':', ',', ';'), it first skips leading separators, then sets *end to the next separator or NUL terminator, and looks up the token in place via Curl_cipher_suite_lookup_id. Unknown tokens yield 0; pointers *str and *end still delimit the consumed token so callers can continue. Nothing is copied or mutated in the input string.

calls: [cs_is_separator](r12-cipher-suite-registry.md#u-95c02bb39258), [Curl_cipher_suite_lookup_id](r12-cipher-suite-registry.md#u-b79ade9a6a08)

<a id="u-95c02bb39258"></a>
### `cs_is_separator`

`static bool cs_is_separator(char c)` · [lib/vtls/cipher_suite.c:L650-L661][f1]

Returns TRUE only for ' ', '\t', ':', ',', ';'; FALSE for all other characters including NUL.

<a id="u-082266582543"></a>
### `cs_str_to_zip`

`static int cs_str_to_zip(const char *cs_str, size_t cs_len, uint8_t zip[6])` · [lib/vtls/cipher_suite.c:L542-L588][f1]

Converts a cipher-suite name substring to its 6-byte compressed form, returning 0 on success and -1 on any mismatch.

Splitting is by '-' by default, but if the name starts with 'TLS' (case-insensitive) the separator becomes '_', matching RFC 'TLS_..._WITH_...' spellings. It walks up to 8 parts; if a ninth part exists, or a part is not found in cs_txt (first, empty entry skipped), it returns -1 immediately. Parts are matched case-insensitively against the pool via curl_strnequal. Unused trailing indexes stay 0, and the eight indexes are packed into zip[6] exactly like the CS_ZIP_IDX macro so memcmp against cs_list entries works. No allocation or global state.

uses: [cipher_suite.c-compressed-table](r12-cipher-suite-registry.md#u-ef3ee1bd7f3e)

<a id="u-60d9df51b9bb"></a>
### `cs_zip_to_str`

`static int cs_zip_to_str(const uint8_t zip[6], char *buf, size_t buf_size)` · [lib/vtls/cipher_suite.c:L590-L633][f1]

Renders a compressed 6-byte cipher entry back into a name in buf, returning 0, or -1 on invalid data.

It unpacks the eight 6-bit indexes; if the first index is the TLS part the join separator is '_', otherwise '-'. The loop stops at the first zero index (padding) or when buf_size is reached, so only meaningful parts are printed. If any index is >= CS_TXT_LEN (corrupt or foreign zipped data) it returns -1. Each part is appended with curl_msnprintf; a negative return aborts with -1. Buffer may therefore hold a truncated name without error when buf_size is small.

uses: [cipher_suite.c-compressed-table](r12-cipher-suite-registry.md#u-ef3ee1bd7f3e)

**Uncertainties.**

- Whether len can exceed buf_size between iterations depends on curl_msnprintf's truncation return value, which is not visible here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/cipher_suite.c
