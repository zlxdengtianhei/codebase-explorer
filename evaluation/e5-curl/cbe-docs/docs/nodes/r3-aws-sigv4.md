# AWS SigV4 Request Signing

**Capability.** Signs HTTP requests per AWS SigV4: parses the provider/region/service option string, canonicalizes path and query, builds canonical headers and request, hashes the payload (including S3 variants), constructs the string-to-sign, and derives and installs the Authorization header.

Read this subtree to follow signing from Curl_output_aws_sigv4 down through canonicalization, payload hashing, and key derivation. Many small helpers do single transformations on dynbufs or header lists.

**Depends on.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-confirmed · 59 edge(s)
- [SHA-256 & HMAC Primitives](r3-hash-primitives.md) · graph-confirmed · 7 edge(s)
- [String Helpers & Error Messages](r3-string-error-utils.md) · graph-confirmed · 7 edge(s)

Parent: [Crypto Primitives & HTTP Authentication](r3-crypto-auth.md)

## Units (22)

<a id="u-f012d93b6646"></a>
### `http_aws_sigv4-c-trivial-helpers`

`static void sha256_to_hex(char *dst, unsigned char *sha)` · [lib/http_aws_sigv4.c:L65-L69][f1]

Groups small file-local helpers in http_aws_sigv4.c whose behavior is a single call or a simple loop over dynbufs.

sha256_to_hex hex-encodes a CURL_SHA256_DIGEST_LENGTH digest into a caller buffer of SHA256_HEX_LENGTH bytes via Curl_hexencode. find_date_hdr returns the user header matching 'x-<provider>-date' if present, otherwise the generic 'Date' header; it returns a pointer into the user's header list or NULL. pair_array_free frees both dynbufs of each struct pair in an array; dyn_array_free frees each dynbuf in an array — both are safe on fully initialized entries only. is_reserved_char reports whether a byte is alphanumeric or RFC 3986 punctuation (ISURLPUNTCS), the set left unencoded in canonical paths and queries.

uses: [Curl_output_aws_sigv4](r3-aws-sigv4.md#u-1528904082ab), [canon_path](r3-aws-sigv4.md#u-a24afab56db8)

**Uncertainties.**

- find_date_hdr's returned pointer aliases Curl_checkheaders storage; its lifetime relative to the request is not visible here.

<a id="u-5110f264f5f0"></a>
### `trim_headers`

`static void trim_headers(struct curl_slist *head)` · [lib/http_aws_sigv4.c:L81-L116][f1]

Normalizes each header string of a curl_slist in place for canonical-header use.

The header name up to the first ':' is lowercased via Curl_strntolower. The value after the colon is rewritten in the same buffer: leading blanks are skipped, every run of consecutive blanks becomes a single space (a run at end of string emits nothing), and the result is null-terminated — so the stored string can only shrink. A header whose data ends at the colon is left with only its lowercased name.

<a id="u-f6f9b2ac6a14"></a>
### `split_to_dyn_array`

`static CURLcode split_to_dyn_array(const char *source, struct dynbuf db[MAX_QUERY_COM…` · [lib/http_aws_sigv4.c:L150-L195][f1]

Splits a query string on '&' into up to MAX_QUERY_COMPONENTS (128) initialized dynbufs.

Empty segments produced by leading, trailing, or consecutive '&' are skipped, since a segment only accumulates when it has non-zero length. Exceeding 128 components fails with CURLE_TOO_LARGE, and the final trailing segment is subject to the same limit. On any failure it stops early but always writes the partial count to *num_splits_out, so the caller must free the partially initialized entries with dyn_array_free.

<a id="u-92320c2e4ae4"></a>
### `uri_encode_path`

`static CURLcode uri_encode_path(struct Curl_str *original_path, struct dynbuf *new_path)` · [lib/http_aws_sigv4.c:L202-L221][f1]

Percent-encodes a path byte-by-byte into a dynbuf for canonical URI construction.

Bytes that are alphanumeric, RFC 3986 punctuation (per is_reserved_char), or '/' are copied verbatim; every other byte becomes %XX via curlx_dyn_addf. On the first dynbuf error it returns that CURLcode immediately, otherwise CURLE_OK.

<a id="u-1e9a11b0ccef"></a>
### `normalize_query`

`static CURLcode normalize_query(const char *string, size_t len, struct dynbuf *db)` · [lib/http_aws_sigv4.c:L225-L261][f1]

Rewrites a query key or value into canonical AWS SigV4 form in a dynbuf, decoding %XX escapes then re-encoding.

A valid '%HH' sequence (both following bytes are hex digits and at least two bytes remain) is decoded; if it decodes to '+' it is re-emitted as literal '%2B' so a decoded plus never becomes a space. A literal '+' in the input becomes '%20'. Unreserved RFC 3986 characters are copied raw; all other bytes, including stray '%' treated literally, become %XX. Returns the first dynbuf error, or CURLE_OK after consuming the whole input.

**Uncertainties.**

- Whether lowercase hex digits ('%2b') count as valid escapes depends on ISXDIGIT, defined outside this file.

<a id="u-4c12a1d0bb69"></a>
### `should_urlencode`

`static bool should_urlencode(struct Curl_str *service_name)` · [lib/http_aws_sigv4.c:L263-L278][f1]

Decides whether the canonical path needs additional URI encoding based on the AWS service name.

Returns FALSE for the S3 family — 's3', 's3express', 's3-outposts', 's3-object-lambda' — which use disableDoubleEncoding in the AWS endpoint rules and rely on the curl URL parser's normalization; any other service name returns TRUE.

<a id="u-d4f59e262249"></a>
### `compare_header_names`

`static int compare_header_names(const char *a, const char *b)` · [lib/http_aws_sigv4.c:L289-L316][f1]

Orders two header strings of form 'name:value' alphabetically by name for canonical sorting.

Only the bytes before the first ':' are compared with strncmp; on equal prefixes it returns the name-length difference so the shorter name sorts first. A DEBUGASSERT requires colons; in release builds a missing colon falls back to using the whole string as the name. Comparison is case-sensitive, so uppercase names sort before lowercase ones.

<a id="u-d718a2368ee3"></a>
### `merge_duplicate_headers`

`static CURLcode merge_duplicate_headers(struct curl_slist *head)` · [lib/http_aws_sigv4.c:L321-L367][f1]

Collapses adjacent headers with equal names into one entry by comma-joining their values, assuming the list is already alpha-sorted with 'name:value' strings.

For each adjacent equal pair it builds 'name:value1,value2' in a dynbuf, replaces curr->data with it, unlinks and frees the next node, and keeps scanning the same node so three or more duplicates merge fully; unequal pairs advance the cursor. On a dynbuf error it returns immediately without freeing the partially built dynbuf, and the list is left unmodified for that pair.

**Uncertainties.**

- The dynbuf 'buf' is not freed on the early-return error paths, which looks like a leak but is only provable with the dynbuf API's semantics.

<a id="u-719f49282175"></a>
### `make_headers`

`static CURLcode make_headers(struct Curl_easy *data, char *timestamp, const char *pro…` · [lib/http_aws_sigv4.c:L370-L536][f1]

Builds the canonical-headers list and signed-headers string for a SigV4 request.

It synthesizes the provider date header key 'X-<Provider>-Date' (provider lowercased, first letter uppercased) and the full lowercase 'x-<provider>-date:<timestamp>' form. When no user Host header exists and data->state.http_host is set, a Host header is prepended; a non-empty content_sha256_header is appended next. User headers are copied with SigV4 semantics: 'name:' with no value (internal-remove marker) is skipped; 'name;' with no value becomes 'name:' for an empty-value header; headers with whitespace-only values or no ':'/';' separator are skipped; any allocation failure jumps to fail. If the provider date header is absent from the user headers, the synthesized one is appended and *date_header receives a 'Key: timestamp\r\n' string for later emission; if present, its value is parsed — a value of exactly 16 alphanumeric bytes is copied into the caller's timestamp buffer (null-terminated), any other length blanks timestamp entirely. The list is then bubble-sorted case-sensitively by name via compare_header_names, duplicates comma-merged via merge_duplicate_headers, and each entry emitted into canonical_headers as 'name:value\n' and into signed_headers as ';'-joined names (colon truncated first). All paths free the list with curl_slist_free_all; success returns CURLE_OK, failure the first CURLcode encountered.

**Uncertainties.**

- When the user's date header has a bad timestamp length, timestamp is blanked; how the caller reacts to an empty timestamp is decided outside this function.

<a id="u-453ba250d988"></a>
### `parse_content_sha_hdr`

`static const char *parse_content_sha_hdr(struct Curl_easy *data, const char *provider…` · [lib/http_aws_sigv4.c:L543-L573][f1]

Looks for a user-provided 'x-<provider>-content-sha256' header and extracts its payload-hash value.

Returns NULL if the header is absent or contains no colon. Otherwise it skips blanks after the colon, strips trailing blanks from the counted length, and stores that length in *value_len. The returned pointer aliases the user's header data, so its lifetime follows that header list.

<a id="u-4ce0fa7acc6f"></a>
### `calc_payload_hash`

`static CURLcode calc_payload_hash(struct Curl_easy *data, unsigned char *sha_hash, ch…` · [lib/http_aws_sigv4.c:L575-L593][f1]

Computes the SHA-256 of the request payload held in data->set.postfields.

The length comes from postfieldsize when it is non-negative, otherwise strlen of the data; a NULL postfields hashes zero bytes. On Curl_sha256it success the digest is hex-encoded into sha_hex and CURLE_OK is returned; a hashing error is propagated and the hex buffer is left untouched.

<a id="u-02670386b3c7"></a>
### `calc_s3_payload_hash`

`static CURLcode calc_s3_payload_hash(struct Curl_easy *data, Curl_HttpReq httpreq, co…` · [lib/http_aws_sigv4.c:L597-L632][f1]

Produces the S3 x-<provider>-content-sha256 header value.

When the method is GET or HEAD, the filesize is zero, or it is a POST with an in-memory postfields body, it computes a real payload hash via calc_payload_hash and propagates its error; otherwise it copies the literal 'UNSIGNED-PAYLOAD' into sha_hex (guarded by a DEBUGASSERT that it fits). In both cases it formats 'x-<provider>-content-sha256: <value>' into the caller's header buffer and returns CURLE_OK — the initial CURLE_OUT_OF_MEMORY value is always overwritten on the success path.

<a id="u-fa24b670e1c2"></a>
### `compare_func`

`static int compare_func(const void *a, const void *b)` · [lib/http_aws_sigv4.c:L634-L668][f1]

qsort comparator for encoded query key/value pairs.

Keys are compared with strcmp; on a tie, values are compared with strcmp. An empty key sorts before any non-empty key (two empty keys are equal), and likewise an empty value sorts before a non-empty one. This yields the deterministic AWS canonical query ordering.

**Uncertainties.**

- If a dynbuf is empty, curlx_dyn_ptr may return NULL; the length checks before each strcmp are what make this safe, but dynbuf's exact pointer contract is outside this file.

<a id="u-a24afab56db8"></a>
### `canon_path`

`UNITTEST CURLcode canon_path(const char *q, size_t len, struct dynbuf *new_path, bool…` · [lib/http_aws_sigv4.c:L674-L696][f1]

Produces the canonical URI path from the request path.

It wraps q/len in a Curl_str, then either percent-encodes via uri_encode_path (when do_uri_encode is true) or copies the path verbatim with curlx_dyn_addn. If the resulting path is empty, a '/' is appended so the canonical URI is never empty. Returns the first error from the encoding or append steps, else CURLE_OK.

<a id="u-b65e3d0b3073"></a>
### `canon_query`

`UNITTEST CURLcode canon_query(const char *query, struct dynbuf *dq)` · [lib/http_aws_sigv4.c:L700-L805][f1]

Builds the canonical query string.

A NULL query returns immediately with an empty dynbuf. The query is split on '&' by split_to_dyn_array (failing with CURLE_TOO_LARGE beyond 128 components); each component is split at the first '=' into key and value, where a missing '=' or a trailing '=' yields an empty value. Key and value are normalized by normalize_query into a struct pair array, then qsorted with compare_func, and finally joined as 'key=value' with '&' separators — a component with an empty value is always emitted as 'key=' even when the original had none. On failure it jumps to fail, freeing the encoded pairs (only those counted so far) and the split array, returning the first error.

**Uncertainties.**

- The encoded_query_array entries are only counted/initialized inside the loop, so error timing determines which entries pair_array_free touches; the counted_query_components guard addresses this but relies on init-before-use ordering within each iteration.

<a id="u-14c62e531842"></a>
### `get_payload_hash`

`static CURLcode get_payload_hash(struct Curl_easy *data, Curl_HttpReq httpreq, struct…` · [lib/http_aws_sigv4.c:L861-L897][f1]

Determines the hashed-payload value for the request.

It first tries parse_content_sha_hdr; if a user-supplied content-sha256 header exists, its value and length are returned as-is. Otherwise, when provider0 case-insensitively equals 'aws' and service equals 's3', it computes the S3 content-sha256 header value via calc_s3_payload_hash; any other service falls back to calc_payload_hash over postfields. After either computation, the payload hash is sha_hex with its strlen as the length. Computation errors are propagated; success returns CURLE_OK.

**Uncertainties.**

- sign_as_s3 uses curlx_str_casecompare on both provider0 and service; whether compound providers like 'aws:s3' alternatives are intended is not decidable from this file.

<a id="u-728c9046e987"></a>
### `get_timestamp`

`static CURLcode get_timestamp(char *timestamp, size_t stampsize)` · [lib/http_aws_sigv4.c:L899-L924][f1]

Fills the timestamp buffer with the current UTC time formatted '%Y%m%dT%H%M%SZ' (16 characters plus NUL, TIMESTAMP_SIZE).

In DEBUGBUILD builds the CURL_FORCETIME environment variable forces clock=0, making the timestamp deterministic for tests; otherwise time(NULL) is used. curlx_gmtime failure is returned directly; if strftime produces nothing (buffer too small) CURLE_OUT_OF_MEMORY is returned.

**Uncertainties.**

- The DEBUGBUILD environment override is only compiled into debug builds; release behavior always uses time(NULL).

<a id="u-ffc458c43da3"></a>
### `make_canonical_request`

`static CURLcode make_canonical_request(struct Curl_easy *data, char *timestamp, struc…` · [lib/http_aws_sigv4.c:L926-L987][f1]

Assembles the AWS SigV4 canonical request string.

It delegates header collection to make_headers, then builds the canonical query via canon_query over data->state.up.query and the canonical path via canon_path over data->state.up.path, choosing additional URI encoding with should_urlencode(service). It formats method, path, query (an empty query pointer is substituted with ""), canonical headers, signed headers, and the payload hash into a curl_maprintf string with newline separators, stored in *canonical_request_out. Any step's failure or a printf allocation failure jumps to fail, which frees the two local dynbufs and propagates the error; success returns CURLE_OK.

**Uncertainties.**

- Whether a NULL canonical query pointer versus a non-NULL empty one changes the output beyond the shown ternary is visible only as the substitution itself.

<a id="u-32b719b28a8c"></a>
### `make_string_to_sign`

`static CURLcode make_string_to_sign(struct Curl_easy *data, struct Curl_str *provider…` · [lib/http_aws_sigv4.c:L989-L1066][f1]

Builds the SigV4 string-to-sign from the canonical request.

It formats '<provider0>4_request' as the request type (lowercased after formatting so the buffer can be written), then the credential scope '<date>/<region>/<service>/<request-type>'. The canonical request is SHA-256 hashed and hex-encoded, and str_to_sign is formatted as '<provider0>4-HMAC-SHA256\n<timestamp>\n<credential-scope>\n<sha-hex>'; the provider0 portion of the result is then uppercased. Each allocation or the hash computation failure frees all partially built strings and returns CURLE_OUT_OF_MEMORY. On success the three outputs are assigned and CURLE_OK returned after logging the string to sign via infof.

**Uncertainties.**

- Whether CURLE_OUT_OF_MEMORY is the semantically right code for a SHA-256 failure is a code choice visible here, not a general guarantee.

<a id="u-1946a9d0e957"></a>
### `parse_sigv4_params`

`static CURLcode parse_sigv4_params(struct Curl_easy *data, const char *hostname, stru…` · [lib/http_aws_sigv4.c:L807-L859][f1]

Parses the CURLOPT_AWS_SIGV4 string of form provider0[:provider1[:region[:service]]], each part at most MAX_SIGV4_LEN non-whitespace bytes, into Curl_str outputs.

When the option is unset or empty it defaults to 'aws:amz'. If provider0 is empty it fails with CURLE_BAD_FUNCTION_ARGUMENT via failf. If provider1 is missing or empty, provider1 is copied from provider0; missing region/service are left empty. When service is empty it is extracted from the hostname (first dot-delimited label), logging an info message, and if region is then also empty it is taken from the second label; failure to find a service or region label in the hostname fails with CURLE_URL_MALFORMAT. Success returns CURLE_OK.

**Uncertainties.**

- The intermediate else-if branch that parses region/service explicitly has an empty body by design (values remain empty); whether any case silently skips filling region when the third separator is absent depends on curlx_str_until semantics not shown here.

<a id="u-b218cd908e62"></a>
### `sign_and_set_auth_headers`

`static CURLcode sign_and_set_auth_headers(struct Curl_easy *data, struct Curl_str *pr…` · [lib/http_aws_sigv4.c:L1068-L1148][f1]

Derives the SigV4 signature key and installs the Authorization header.

The secret key is '<provider0>4<passwd>' (provider0 uppercased after formatting), where passwd and user come from the current credentials; user is percent-escaped via curl_escape and a NULL result aborts with CURLE_OUT_OF_MEMORY. Five chained HMAC-SHA256 operations (via the HMAC_SHA256 macro, any failure jumps to fail) derive the signing key through date, region, service, and request_type, then sign str_to_sign; the final digest is hex-encoded and logged. The Authorization header is formatted with Credential=<user>/<scope>, SignedHeaders, and Signature, appending date_header only when it was not user-specified and content_sha256_hdr plus a trailing CRLF only when non-empty; the provider0 portion is then uppercased. The result is stored in data->req.hd_auth (freeing any previous value), data->state.authhost.done is set TRUE, and both user and secret temporaries are freed on all paths.

**Uncertainties.**

- The exact ownership semantics of data->req.hd_auth (who frees it later) are not visible in this file.

<a id="u-1528904082ab"></a>
### `Curl_output_aws_sigv4`

`CURLcode Curl_output_aws_sigv4(struct Curl_easy *data)` · [lib/http_aws_sigv4.c:L1150-L1231][f1]

Public entry point that signs an HTTP request with AWS SigV4 and attaches the resulting auth headers.

It rejects data->set.path_as_is outright with CURLE_BAD_FUNCTION_ARGUMENT via failf, and returns CURLE_OK without doing anything when an Authorization header is already present. Otherwise it initializes the canonical-headers and signed-headers dynbufs, then runs the pipeline: parse_sigv4_params to resolve provider/region/service, Curl_http_method to get the method and request kind, get_payload_hash, get_timestamp, make_canonical_request, make_string_to_sign (the date portion is re-derived from the possibly updated timestamp), and finally sign_and_set_auth_headers. Every stage's result gates the next; the first failure short-circuits. All dynbufs and heap temporaries (canonical_request, request_type, credential_scope, str_to_sign, date_header) are freed before returning the final CURLcode.

**Uncertainties.**

- The initial result value CURLE_OUT_OF_MEMORY is only observable if parse_sigv4_params itself returns success through an unexpected path; normally the pipeline overwrites it before any return.
- Whether data->state.origin->hostname is guaranteed non-NULL here depends on the caller in lib/http.c, which is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_aws_sigv4.c
