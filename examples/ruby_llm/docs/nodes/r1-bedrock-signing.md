# SigV4 Signing

**Capability.** A self-contained AWS SigV4 implementation: URI/crypto utilities, canonical request construction, signature math and credentials value objects, request preparation/header assembly, the public Signer, and configuration-error types.

Read the Signer first; it wires the pipeline (request prep, canonical request, signature core) over shared stateless helpers. Errors signal missing SigV4 configuration.

**Depended on by.**

- [Bedrock Models & Capabilities](r1-bedrock-models-capabilities.md) · model-inferred · 0 edge(s)

Parent: [Bedrock Adapter](r1-bedrock-adapter.md)

## Units (7)

<a id="u-ef4167d839ba"></a>
### `signing-rb-signer`

`class SignerOptionExtractor` · [lib/ruby_llm/providers/bedrock/signing.rb:L628-L629][f1]

Wires and operates the public SigV4 Signer.

SignerOptionExtractor validates options: missing :service raises ArgumentError('missing required option :service'); missing :region raises Errors::MissingRegionError; :credentials_provider wins, else static credentials are built when :credentials or :access_key_id is present, else Errors::MissingCredentialsError is raised; unsigned_headers are downcased and always joined by 'authorization', 'x-amzn-trace-id', and 'expect'. SignerInitializer.create_components merges those with defaults (uri_escape_path, apply_checksum_header, normalize_path true; omit_session_token false) and instantiates SignatureGenerator, HeaderBuilder, and CredentialManager. Signer#initialize runs this pipeline and caches all components; sign_request then fetches credentials (raising MissingCredentialsError when unset), extracts request components, builds SigV4 headers, computes the signature, and returns a Signature whose headers include authorization plus any omitted-session-token handling. The singleton-method block at the end re-exports UriUtils.uri_escape_path/uri_escape/normalize_path as Signer class methods.

**Uncertainties.**

- SignerInitializer passes components[:signing_algorithm] (never set by extract_config_options) into the generator and header builder, so HeaderBuilder's @signing_algorithm is nil; HeaderBuilder does not read it, so the effect appears nil, but any future use would see nil.

<a id="u-fc75b3de872c"></a>
### `signing-rb-request-pipeline`

`class RequestExtractor # Extract and process request components # @param [Hash] reque…` · [lib/ruby_llm/providers/bedrock/signing.rb:L359-L364][f1]

Prepares raw requests for signing and assembles signing headers.

RequestExtractor.extract_components (normalize_path default true) pulls method/url/headers, optionally normalizes the URL path in place, derives datetime from the 'x-amz-date' header or the current UTC time, and computes content_sha256 from 'x-amz-content-sha256' or SHA-256 of the body (empty string when body is nil). Missing :http_method raises ArgumentError('missing required option :http_method'); missing :url raises the analogous :url error; headers are downcased via to_hash.transform_keys, treating nil as {}. CredentialManager.fetch_credentials calls the provider's #credentials and, when credentials_set? fails, raises Errors::MissingCredentialsError; on success it returns [credentials, expiration], reading expiration only when the provider responds to it. HeaderBuilder.build_sigv4_headers emits host (from the headers or UriUtils.host of the URL) and x-amz-date, adds x-amz-security-token only when a session token exists and @omit_session_token is false, and adds x-amz-content-sha256 only when @apply_checksum_header is set. build_headers merges the authorization header and, only when @omit_session_token is true, re-adds x-amz-security-token from components[:creds] if present.

**Notes.**

- failure: Unsigned or incomplete credentials surface as Errors::MissingCredentialsError from CredentialManager#fetch_credentials, before any signature math runs.

**Uncertainties.**

- HeaderBuilder.build_headers reads components[:creds], a key RequestExtractor never sets; when @omit_session_token is true this key is presumably injected by a caller, otherwise the token is silently skipped (creds&.session_token on nil).

<a id="u-b2d5cf07e769"></a>
### `signing-rb-signature-core`

`class SignatureComputation` · [lib/ruby_llm/providers/bedrock/signing.rb:L320-L321][f1]

Performs the SigV4 math and result assembly.

SignatureComputation holds service/region/algorithm: string_to_sign joins the algorithm, datetime, credential scope (date/region/service/'aws4_request'), and the SHA-256 hex of the canonical request; credential prefixes the access key id to the scope; signature derives the key chain AWS4<secret> → date → region → service → 'aws4_request' via raw HMACs and returns CryptoUtils.hexhmac of the string-to-sign. SignatureGenerator always uses :sigv4 and 'AWS4-HMAC-SHA256'; compute_signature merges request headers with the SigV4 headers, builds the CanonicalRequest, computes the signature, and delegates to SignatureResultBuilder, whose result hash exposes algorithm, credential, signed_headers (from the CanonicalRequest), signature, canonical_request, and string_to_sign. Note build_signature_result recomputes generate_string_to_sign on the canonical request text, so sts is computed twice per signature.

**Uncertainties.**

- CanonicalRequestConfig is created in create_canonical_request_config without the unsigned_headers set passed to SignatureGenerator's constructor, so generator-level unsigned headers may not influence canonicalization; behavior depends on CanonicalRequestConfig defaults.

<a id="u-bd5146ad8074"></a>
### `signing-rb-canonical-request`

`class CanonicalRequestConfig` · [lib/ruby_llm/providers/bedrock/signing.rb:L247-L250][f1]

Builds the AWS SigV4 canonical request string.

CanonicalRequestConfig stores uri_escape_path (default true) and the unsigned-headers Set (default empty). CanonicalRequest is initialized from http_method, url, headers, content_sha256, and an optional config. to_s joins: method, canonical path, an empty line in place of a query string (query parameters are deliberately not supported), the canonical headers block, the signed header list, and the payload hash. signed_headers lists every header not in unsigned_headers, sorted, joined by ';'. canonical_headers sorts unsigned-out entries by key and emits 'key:value' lines where each value is collapsed (\s+ to single space) and stripped. path uses '/' for an empty path and conditionally applies UriUtils.uri_escape_path.

**Uncertainties.**

- Requests with query strings will not sign correctly because to_s always inserts an empty query component; this is an intentional simplification visible only in the comment.

<a id="u-815e5577a125"></a>
### `signing-rb-signature-credentials`

`class Signature # @api private` · [lib/ruby_llm/providers/bedrock/signing.rb:L97-L99][f1]

Value objects underpinning signatures and credentials.

Signature is initialized from a hash whose keys are applied verbatim via send("#{attr_name}=") — unknown keys raise NoMethodError — and exposes attr_accessors for headers, canonical_request, string_to_sign, content_sha256, signature, and extra. Credentials requires both :access_key_id and :secret_access_key, raising ArgumentError with a fixed message when either is missing, and exposes readers plus set? (true only when both key values are non-nil and non-empty). StaticCredentialsProvider wraps an existing :credentials object or builds Credentials from the options, and its set? is true only when credentials exist and Credentials#set? passes. ParamComponent is a plain Struct(name, value, offset).

<a id="u-01d82e5fd819"></a>
### `signing-rb-uri-crypto-utils`

`module UriUtils` · [lib/ruby_llm/providers/bedrock/signing.rb:L192-L195][f1]

Stateless helpers shared by the signing pipeline.

UriUtils.uri_escape_path escapes each path segment between slashes individually; uri_escape returns nil for nil, otherwise CGI-escapes a UTF-8 encoded string, restores '+' to '%20' and '%7E' to '~' (AWS SigV4 unreserved-character rules). normalize_path cleans the URI path via Pathname#cleanpath, maps a '.' result to '', re-appends a trailing slash when the original path had one, and writes the result back onto uri.path. host returns uri.host alone when the URI uses its default port, otherwise 'host:port'. CryptoUtils wraps OpenSSL: sha256_hexdigest returns a hex digest, hmac returns raw SHA-256 HMAC bytes, hexhmac returns the hex form.

**Notes.**

- side_effect: UriUtils.normalize_path mutates the URI object passed to it in place.

<a id="u-5b87177b6aa5"></a>
### `signing-rb-errors`

`class MissingCredentialsError < ArgumentError` · [lib/ruby_llm/providers/bedrock/signing.rb:L77-L78][f1]

Two ArgumentError subclasses for SigV4 configuration failures.

MissingCredentialsError#initialize uses its msg argument when given, otherwise emits a multi-line hint listing the :access_key_id/:secret_access_key, :credentials, and :credentials_provider options; the message is stripped of heredoc indentation. MissingRegionError#initialize ignores all positional arguments and always raises with 'missing required option :region'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/signing.rb