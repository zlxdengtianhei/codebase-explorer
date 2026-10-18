# HTTP Message Signatures (RFC 9421)

**Capability.** Produces Signature/Signature-Input headers: covered-component parsing and resolution, signature-params serialization with RFC 8941 quoting/byte-sequence encoding, signature-base construction, key decoding, and algorithm-specific signing.

Enter at Curl_output_httpsig, which orchestrates all helpers. Component resolution and base building feed the signer; alg/id mapping functions translate user options to wire names.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 56 edge(s)

Parent: [Protocol and Filter Implementations](r5-protocol-implementations.md)

## Units (13)

<a id="u-2a0767884055"></a>
### `Curl_output_httpsig`

`CURLcode Curl_output_httpsig(struct Curl_easy *data)` · [lib/http_httpsig.c:L529-L687][f1]

Produces the RFC 9421 Signature and Signature-Input headers for an outgoing request, storing them in data->req.hd_auth and marking host auth done.

Required options are validated first: an unknown algorithm, empty CURLOPT_HTTPSIG_KEY, or empty CURLOPT_HTTPSIG_KEYID each return CURLE_BAD_FUNCTION_ARGUMENT with a logged message before any allocation. If the user already supplies Signature or Signature-Input headers, the function jumps to the done path, clearing its work and reporting success without adding headers. Otherwise it decodes the hex key, rejects a non-32-byte key for Ed25519, gathers method/path/query/authority (path defaults to "/" when absent; @query is always prefixed with '?', using just "?" when there is no query), parses the component list, computes the created timestamp, builds the signature params, logs them, builds and logs the signature base, signs it, and formats "sig1=<byte-seq>" and "sig1=<params>" into the two headers via curl_maprintf (allocation failure falls to the fail path with the initial CURLE_OUT_OF_MEMORY). Memory initialization failure at dyn_init is not individually checked; the first append on an unallocated dynbuf yields the propagated error. On any failure the fail path zeroes and frees the decoded key, zeroes the raw signature buffer, frees the headers copy and all dynbufs, and returns the error. The done path frees any previous hd_auth and installs the new headers, always returning CURLE_OK.

**Notes.**

- side_effect: Sets data->state.authhost.done = TRUE and replaces data->req.hd_auth even when user-supplied Signature headers make signing unnecessary.
- failure: Key material and the raw signature are memset to zero before free/return on every exit.

calls: [decode_hex_key](r5-http-message-signatures.md#u-250f51a93798), [httpsig_authority](r5-http-message-signatures.md#u-3f59f14c4221), [parse_components](r5-http-message-signatures.md#u-2deaa21067a5), [build_sig_params](r5-http-message-signatures.md#u-0adef74918d0), [build_sig_base](r5-http-message-signatures.md#u-51ac2257ef39), [httpsig_sign_base](r5-http-message-signatures.md#u-17d45fd2fb99), [sf_encode_byte_seq](r5-http-message-signatures.md#u-52964c86b5d9), [httpsig_get_created](r5-http-message-signatures.md#u-5e1e11551866), [id_to_alg](r5-http-message-signatures.md#u-68704301ae9b); uses: [alg_to_str](r5-http-message-signatures.md#u-a270db87cf2c)

**Uncertainties.**

- Whether data->conn and data->state.up are always populated at this point is established by the HTTP caller, not this file.
- Result codes from curlx_dyn_init calls are void here; failure surfaces only through subsequent dynbuf operations.

<a id="u-a270db87cf2c"></a>
### `alg_to_str`

`static const char *alg_to_str(enum httpsig_alg alg)` · [lib/http_httpsig.c:L56-L67][f1]

Maps an httpsig_alg value to its wire name: HTTPSIG_ALG_ED25519 to "ed25519", HTTPSIG_ALG_HMAC_SHA256 to "hmac-sha256", any other value (including HTTPSIG_ALG_UNKNOWN) to NULL.

Pure lookup, no allocation or failure path.

<a id="u-51ac2257ef39"></a>
### `build_sig_base`

`static CURLcode build_sig_base(struct dynbuf *base, const char **components, size_t c…` · [lib/http_httpsig.c:L335-L371][f1]

Builds the RFC 9421 signature base into a dynbuf: for each component, resolve_component produces its value, which is written as "\"name\": value\n"; afterwards the final line "\"@signature-params\": <sig_params>" is appended.

A scratch dynbuf for combined header values is initialized on entry; on any resolution or append failure it is freed and the error (or CURLE_BAD_FUNCTION_ARGUMENT when a component resolves to NULL) is returned. On success the scratch buffer is freed before the final append, whose result code is returned.

calls: [resolve_component](r5-http-message-signatures.md#u-c49d2dcce7e8)

<a id="u-0adef74918d0"></a>
### `build_sig_params`

`static CURLcode build_sig_params(struct dynbuf *params, const char **components, size…` · [lib/http_httpsig.c:L209-L251][f1]

Serializes the RFC 9421 signature-params string into a dynbuf: '(' followed by the component identifiers, each SF-quoted via sf_append_quoted and space-separated, then ')', then ";created=<unix-time>", then ";keyid=" plus the quoted keyid only when keyid is non-empty, and finally ";alg=\"<name>\"" using alg_to_str.

The first dynbuf or quoting error is returned immediately; for HTTPSIG_ALG_UNKNOWN the alg field would serialize a NULL string, but callers reject that algorithm before this point.

calls: [sf_append_quoted](r5-http-message-signatures.md#u-fcc0da67130b), [alg_to_str](r5-http-message-signatures.md#u-a270db87cf2c)

<a id="u-250f51a93798"></a>
### `decode_hex_key`

`static CURLcode decode_hex_key(struct Curl_easy *data, const char *hexstr, unsigned c…` · [lib/http_httpsig.c:L82-L125][f1]

Decodes a hex string into a freshly allocated byte buffer; *keyout and *keylen are zeroed on entry.

Trailing newline characters are stripped before validation. An empty or odd trimmed length fails with CURLE_BAD_FUNCTION_ARGUMENT and a logged message; a length above CURL_MAX_INPUT_LENGTH fails likewise. curlx_malloc failure returns CURLE_OUT_OF_MEMORY. Each byte pair must both be hex digits; the first offending pair is reported by position, the buffer freed, and CURLE_BAD_FUNCTION_ARGUMENT returned. On success *keyout owns len/2 bytes and *keylen is len/2.

uses: [Curl_output_httpsig](r5-http-message-signatures.md#u-2a0767884055)

<a id="u-3f59f14c4221"></a>
### `httpsig_authority`

`static CURLcode httpsig_authority(struct Curl_easy *data, struct connectdata *conn, s…` · [lib/http_httpsig.c:L129-L164][f1]

Computes the RFC 9421 @authority value into the caller's dynbuf.

If data->state.http_host exists and begins with "host:", blanks after the colon are skipped; a non-empty remaining value is trimmed of trailing newline/blank characters and appended verbatim, returning CURLE_OK or the dynbuf error. Otherwise the fallback uses conn->origin: a nonzero port differing from the scheme's default port produces "hostname:port" via curlx_dyn_addf, otherwise only the hostname. An empty or blank-only Host value falls through to the connection-based authority.

uses: [Curl_output_httpsig](r5-http-message-signatures.md#u-2a0767884055)

<a id="u-5e1e11551866"></a>
### `httpsig_get_created`

`static time_t httpsig_get_created(void)` · [lib/http_httpsig.c:L474-L490][f1]

Returns the 'created' timestamp for the signature parameters.

In DEBUGBUILD, if CURL_FORCETIME is set to a non-empty value, the timestamp is taken from CURL_HTTPSIG_CREATED when it parses as a number, otherwise 0; this makes signatures reproducible in tests. Outside debug builds, or when CURL_FORCETIME is unset, the current wall-clock time(NULL) is returned.

**Uncertainties.**

- curlx_str_number's failure contract is assumed to be zero-result-on-error; the return-0 path on a malformed CURL_HTTPSIG_CREATED depends on it.

<a id="u-17d45fd2fb99"></a>
### `httpsig_sign_base`

`static CURLcode httpsig_sign_base(struct Curl_easy *data, enum httpsig_alg alg, const…` · [lib/http_httpsig.c:L492-L527][f1]

Signs the signature base with the configured algorithm.

For HTTPSIG_ALG_ED25519 it calls Curl_ed25519_sign over the dynbuf bytes, storing the length in *raw_sig_len. For HTTPSIG_ALG_HMAC_SHA256 it calls Curl_hmacit with the SHA-256 HMAC and, on success, sets *raw_sig_len to CURL_SHA256_DIGEST_LENGTH. An unknown algorithm returns CURLE_BAD_FUNCTION_ARGUMENT without signing. When the result is CURLE_NOT_BUILT_IN, a message naming the unsupported algorithm is logged and the error propagates.

calls: [curl_ed25519-c-sign](r4-ed25519-signing.md#u-7d8ddbea6cfa); uses: [Curl_output_httpsig](r5-http-message-signatures.md#u-2a0767884055)

**Uncertainties.**

- For the HMAC case, raw_sig must be at least CURL_SHA256_DIGEST_LENGTH bytes; sizing is the caller's responsibility.

<a id="u-68704301ae9b"></a>
### `id_to_alg`

`static enum httpsig_alg id_to_alg(uint8_t val)` · [lib/http_httpsig.c:L69-L80][f1]

Converts the user-set algorithm option value to the internal enum: CURLHTTPSIG_ED25519 to HTTPSIG_ALG_ED25519, CURLHTTPSIG_HMAC_SHA256 to HTTPSIG_ALG_HMAC_SHA256, anything else to HTTPSIG_ALG_UNKNOWN, which callers treat as invalid configuration.

Pure lookup.

<a id="u-2deaa21067a5"></a>
### `parse_components`

`static CURLcode parse_components(struct Curl_easy *data, const char *query, const cha…` · [lib/http_httpsig.c:L373-L472][f1]

Determines the covered-component list from the HTTPSIG headers option, or a default set.

When the option is set, it is duplicated into *hdrs_copy_out and split on blanks; quote and backslash characters in a token fail with CURLE_BAD_FUNCTION_ARGUMENT. A token ending in ':' is a header field: the colon is dropped, the name lowercased, and an empty name rejected. Otherwise the lowercased token must be one of method/authority/path/query and is mapped to its '@'-prefixed constant; unknown names fail. Parsing stops at HTTPSIG_MAX_COMPONENTS entries; zero components fails, and leftover unparsed input fails with a 'too many components' message. Duplicate components (case differences removed) are rejected per RFC 9421. When the option is unset or empty, the defaults are @method, @authority, @path, plus @query only when a query string exists. On success *ncomp_out is set; note the caller-supplied components array must hold at least HTTPSIG_MAX_COMPONENTS entries.

uses: [Curl_output_httpsig](r5-http-message-signatures.md#u-2a0767884055)

**Uncertainties.**

- When the option is set but consists only of blanks, the token loop breaks with ncomp==0 and the 'no signature components' error is returned rather than the defaults.

<a id="u-c49d2dcce7e8"></a>
### `resolve_component`

`static CURLcode resolve_component(const char *name, const char *method, const char *a…` · [lib/http_httpsig.c:L264-L333][f1]

Resolves one covered component identifier to its value for the signature base.

Names starting with '@' are matched case-sensitively against @method, @authority, @path and @query and returned directly; an unknown derived component, or a known one with no value, fails with CURLE_BAD_FUNCTION_ARGUMENT and a logged message. Any other name is treated as a header field: the buffer is reset, all user headers whose name matches case-insensitively (name length match followed by a header separator) are collected, each value is taken after the colon and trimmed of OWS, and duplicates are combined with ", ". If no header matched, CURLE_BAD_FUNCTION_ARGUMENT is returned. On success *out points either to the passed-in string or to the dynbuf contents.

uses: [build_sig_base](r5-http-message-signatures.md#u-51ac2257ef39)

**Uncertainties.**

- Header name matching requires an exact-length case-insensitive prefix, so header parameters or extra characters in the field name are not matched.

<a id="u-fcc0da67130b"></a>
### `sf_append_quoted`

`static CURLcode sf_append_quoted(struct dynbuf *buf, const char *str)` · [lib/http_httpsig.c:L166-L185][f1]

Appends an RFC 8941 quoted string to a dynbuf: opening quote, per-character copy with backslash-escaping of '\' and '"', closing quote.

Any control character aborts with CURLE_BAD_FUNCTION_ARGUMENT, leaving the partially built buffer as-is; dynbuf append errors propagate immediately.

uses: [build_sig_params](r5-http-message-signatures.md#u-0adef74918d0)

<a id="u-52964c86b5d9"></a>
### `sf_encode_byte_seq`

`static CURLcode sf_encode_byte_seq(const unsigned char *raw, size_t rawlen, struct dy…` · [lib/http_httpsig.c:L188-L207][f1]

Encodes raw bytes as an RFC 8941 byte sequence: curlx_base64_encode produces the base64 text, then ':' + base64 + ':' is appended to the dynbuf, stopping at the first append error.

The base64 buffer is always freed; the last recorded error code is returned.

uses: [Curl_output_httpsig](r5-http-message-signatures.md#u-2a0767884055)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_httpsig.c
