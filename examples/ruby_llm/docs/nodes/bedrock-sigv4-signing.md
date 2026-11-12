# Bedrock SigV4 Signing

**Capability.** Implements AWS SigV4 request signing components, credentials, canonicalization, signatures, and signer facade.

Observed units show Bedrock request signing internals. They include canonical requests, credential handling, signature computation, and signer option validation.

Parent: [RubyLLM Multi-Provider Library](rubyllm-multi-provider-library.md)

## Units (17)

<a id="u-8a1ab21f0ed0"></a>
### `signing.rb-canonical-request`

`class CanonicalRequest # Builds a canonical request for AWS signature # @param [Hash]…` · [lib/ruby_llm/providers/bedrock/signing.rb:L257-L260][f1]

CanonicalRequest builds the SigV4 canonical request string from method, URL, headers, content hash, and config.

to_s joins method, path, an empty query line, canonical headers plus newline, signed headers, and content hash with newlines. signed_headers filters out configured unsigned headers, sorts, and joins with ';'. path uses the URL path, substitutes '/' for empty, and escapes it only when config.uri_escape_path is true. canonical_headers filters unsigned headers, sorts by header name, and formats each as name:value with whitespace collapsed to single spaces and stripped. canonical_header_value performs that whitespace normalization.

<a id="u-2da6e67f943e"></a>
### `signing.rb-canonical-request-config`

`class CanonicalRequestConfig` · [lib/ruby_llm/providers/bedrock/signing.rb:L247-L250][f1]

CanonicalRequestConfig stores path-escaping and unsigned-header settings.

uri_escape_path is options[:uri_escape_path] || true, so a supplied false is replaced by true; unsigned_headers is the supplied value or a new Set. Both are exposed by readers.

<a id="u-20d41855e27b"></a>
### `signing.rb-credential-manager`

`class CredentialManager` · [lib/ruby_llm/providers/bedrock/signing.rb:L490-L491][f1]

CredentialManager fetches credentials from a provider and validates them.

fetch_credentials calls provider.credentials; if credentials_set? is true it returns [credentials, expiration], taking expiration from provider.expiration only when the provider responds to it; otherwise it raises MissingCredentialsError with a message. credentials_set? requires non-nil, non-empty access_key_id and secret_access_key.

<a id="u-2eff133ca061"></a>
### `signing.rb-credentials`

`class Credentials # @option options [required, String] :access_key_id # @option optio…` · [lib/ruby_llm/providers/bedrock/signing.rb:L134-L138][f1]

Credentials stores an access key, secret key, and optional session token.

Initialization requires both access_key_id and secret_access_key to be truthy, otherwise it raises ArgumentError; empty strings are truthy and pass this check. set? returns true only when both access key and secret key are non-nil and non-empty.

<a id="u-cfb485c8a2bf"></a>
### `signing.rb-crypto-helpers`

`def sha256_hexdigest(value)` · [lib/ruby_llm/providers/bedrock/signing.rb:L233-L235][f1]

These module functions provide SHA-256 hexdigest, binary HMAC-SHA256, and hex HMAC-SHA256 using OpenSSL.

<a id="u-2b0064504f93"></a>
### `signing.rb-header-builder`

`class HeaderBuilder` · [lib/ruby_llm/providers/bedrock/signing.rb:L424-L425][f1]

HeaderBuilder assembles SigV4 headers and authorization.

build_sigv4_headers starts with host from existing headers or the URL and x-amz-date from components; it adds x-amz-security-token when credentials have a session token and omit_session_token is false, and adds x-amz-content-sha256 only when apply_checksum_header is true. build_headers merges an authorization header built from algorithm, credential, signed headers, and signature; when omit_session_token is true it then calls add_omitted_session_token with components[:creds], which adds x-amz-security-token only if that value has a session token, otherwise adds nothing. build_authorization_header joins the three authorization fields with comma-space.

<a id="u-072a5fef3e70"></a>
### `signing.rb-request-component-extraction`

`class RequestExtractor # Extract and process request components # @param [Hash] reque…` · [lib/ruby_llm/providers/bedrock/signing.rb:L359-L364][f1]

RequestExtractor normalizes a request hash into signing components.

extract_components optionally normalizes the URL path (default true), extracts method, URL, and downcased headers, takes datetime from x-amz-date or current UTC time, takes content SHA-256 from x-amz-content-sha256 or hashes the body or empty string, and returns a hash with method, URL, headers, datetime, date (first eight datetime characters), and content hash. Missing http_method or url raises ArgumentError. extract_http_method upcases the supplied method; extract_url parses the supplied URL string; downcase_headers converts a hash-like headers value to string keys and downcases them, treating nil as empty.

<a id="u-03568ae11830"></a>
### `signing.rb-signature-computation`

`class SignatureComputation` · [lib/ruby_llm/providers/bedrock/signing.rb:L320-L321][f1]

SignatureComputation derives SigV4 strings and signatures for a service and region.

string_to_sign joins the supplied algorithm, datetime, credential scope for the first eight date characters, and SHA-256 hexdigest of the canonical request. credential_scope joins date, region, service, and 'aws4_request'. credential joins the access key ID with that scope. signature derives HMAC-SHA256 keys in order from 'AWS4'+secret, date, region, service, and 'aws4_request', then returns the hex HMAC of the string to sign.

<a id="u-ab59ef86e94a"></a>
### `signing.rb-signature-generator`

`class SignatureGenerator` · [lib/ruby_llm/providers/bedrock/signing.rb:L547-L548][f1]

SignatureGenerator computes SigV4 signatures and result data.

Initialization always uses sigv4, sets uri_escape_path to options[:uri_escape_path] || true (so false becomes true), defaults unsigned_headers to a Set, stores service and region, and creates SignatureComputation and SignatureResultBuilder. sts_algorithm returns 'AWS4-HMAC-SHA256'. compute_signature merges component headers with sigv4 headers, creates a canonical request, computes the signature, and builds the result. Private helpers build the canonical request string and string-to-sign, delegate string-to-sign and signature generation to SignatureComputation, create CanonicalRequestConfig from the stored escaping and unsigned-header settings, and pass algorithm, credentials, date, signature, canonical request, and string-to-sign into the result builder.

<a id="u-51b72a859e08"></a>
### `signing.rb-signature-result-builder`

`class SignatureResultBuilder` · [lib/ruby_llm/providers/bedrock/signing.rb:L516-L517][f1]

SignatureResultBuilder turns signature computation data into a result hash.

build_result returns algorithm, credential from the signature computation using credentials and date, signed_headers from the canonical request, signature, canonical_request (creq), and string_to_sign (sts). It performs no validation.

<a id="u-0ee0afe4edc1"></a>
### `signing.rb-signature-value-object`

`class Signature # @api private` · [lib/ruby_llm/providers/bedrock/signing.rb:L97-L99][f1]

Signature is a mutable value object holding signed request headers and debugging fields.

Its initializer iterates option pairs and calls existing attr_accessor setters via send; unknown option keys therefore raise NoMethodError rather than being stored. The accessors cover headers, canonical_request, string_to_sign, content_sha256, signature, and extra; no validation is performed.

<a id="u-849753b09f3c"></a>
### `signing.rb-signer`

`class Signer # Initialize a new signer with the provided options # @param [Hash] opti…` · [lib/ruby_llm/providers/bedrock/signing.rb:L728-L731][f1]

Signer is the public SigV4 request-signing facade.

Initialization builds components through SignerInitializer, stores configuration, and stores signature generator, header builder, and credential manager. sign_request fetches credentials first (raising if missing), extracts request components, builds SigV4 headers, computes the signature, and returns a Signature containing headers, string_to_sign, canonical_request, content_sha256, and signature. Private setup assigns configuration and service components; extract_request_components passes normalize_path; build_sigv4_headers and compute_signature delegate to the stored collaborators; build_signature_response calls header_builder.build_headers and constructs the Signature. Class-level uri_escape_path, uri_escape, and normalize_path delegate to UriUtils.

<a id="u-bdb2bf38b214"></a>
### `signing.rb-signer-initializer`

`class SignerInitializer` · [lib/ruby_llm/providers/bedrock/signing.rb:L661-L662][f1]

SignerInitializer assembles the signer's configuration and service objects.

create_components extracts service, region, credentials provider, unsigned headers, and config options, merges them, and creates service components. extract_config_options defaults uri_escape_path, apply_checksum_header, and normalize_path to true and omit_session_token to false. create_service_components builds SignatureGenerator, HeaderBuilder, and CredentialManager and merges them into the component hash. create_signature_generator passes signing_algorithm, uri_escape_path, unsigned_headers, service, and region; create_header_builder passes signing_algorithm, apply_checksum_header, omit_session_token, and region.

<a id="u-d98fbf0864a3"></a>
### `signing.rb-signer-option-extraction`

`class SignerOptionExtractor` · [lib/ruby_llm/providers/bedrock/signing.rb:L628-L629][f1]

SignerOptionExtractor validates and normalizes signer options.

extract_service returns the service or raises ArgumentError; extract_region raises MissingRegionError unless region is present; extract_credentials_provider returns a supplied provider, otherwise builds StaticCredentialsProvider when credentials or access_key_id keys exist, otherwise raises MissingCredentialsError. initialize_unsigned_headers downcases supplied unsigned_headers (default empty) and merges authorization, x-amzn-trace-id, and expect.

<a id="u-e50bbf665702"></a>
### `signing.rb-signing-errors`

`class MissingCredentialsError < ArgumentError` · [lib/ruby_llm/providers/bedrock/signing.rb:L77-L78][f1]

These ArgumentError subclasses report missing AWS signing configuration.

MissingCredentialsError uses the supplied message or a default listing accepted credential options. MissingRegionError ignores all arguments and always raises with 'missing required option :region'.

<a id="u-3edf1545f286"></a>
### `signing.rb-static-credentials-provider`

`class StaticCredentialsProvider # @option options [Credentials] :credentials # @optio…` · [lib/ruby_llm/providers/bedrock/signing.rb:L171-L176][f1]

StaticCredentialsProvider wraps a Credentials object for the signer.

Initialization uses options[:credentials] when present, otherwise constructs Credentials from the same options. set? returns true only when the wrapped credentials exist and report set?.

<a id="u-6f90b7ece134"></a>
### `signing.rb-uri-utilities`

`def uri_escape_path(path)` · [lib/ruby_llm/providers/bedrock/signing.rb:L195-L197][f1]

These module functions escape and normalize request URLs for signing.

uri_escape_path escapes each non-slash path segment with uri_escape. uri_escape returns nil for nil, otherwise CGI-escapes the UTF-8 string, converts '+' to '%20', and restores '~'. normalize_path cleans the URI path with Pathname, turns '.' into an empty string, and appends a trailing slash when the original path ended with one and the cleaned path does not; it mutates uri.path. host returns the host when the URI port equals the default port, otherwise host:port.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/signing.rb
