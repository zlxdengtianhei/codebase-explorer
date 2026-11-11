# AWS SigV4 Request Signing

**Capability.** Implements AWS Signature Version 4 request signing for the Bedrock provider, from canonical request construction to credential handling and header assembly.

Come here when Bedrock requests need to be authenticated or when SigV4 signing internals must be debugged or extended. It contains the full signing pipeline: canonical requests, string-to-sign computation, signing keys, credentials, and error types, exposed through a small facade.

**Depends on.**

- [Streaming and Provider Core](streaming-and-provider-core.md) · graph-confirmed · 1 edge(s) · SigV4 signing authenticates Bedrock requests issued through the provider core.
- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Units (23)

<a id="u-c73d285a37f3"></a>
### `bedrock.rb-bedrock-provider`

`class Bedrock < Provider` · [lib/ruby_llm/providers/bedrock.rb:L9-L17][f1]

AWS Bedrock provider that signs requests with SigV4-style credentials.

api_base interpolates the configured bedrock_region into the bedrock-runtime endpoint. `parse_error` returns nil for an empty body, otherwise JSON-parses it: a Hash yields its 'message', an Array joins each part's 'message' with '. ', anything else is returned raw. `sign_request` builds a request descriptor (connection, http_method, url defaulting to completion_url, JSON body with non-ASCII preserved) and signs it via a Signing::Signer created from configured access key, secret, session token, region, and service 'bedrock'. `build_headers` merges signature headers with JSON Content-Type and an Accept of the Amazon eventstream MIME when streaming, else JSON. Class methods expose Bedrock::Capabilities and require bedrock_api_key, bedrock_secret_key, bedrock_region.

<a id="u-1eee230d5d87"></a>
### `capabilities.rb-bedrock-provider-class`

`class Bedrock # Determines capabilities and pricing for AWS Bedrock models` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L5-L7][f2]

The AWS Bedrock provider class, reopened across files to mix in Capabilities, Chat, Media, Models, Signing, and Streaming modules that implement model metadata, request formatting, and SigV4-signed HTTP calls.

Each file contributes one concern; the class itself defines no behavior beyond these mixins.

<a id="u-498b78776ccc"></a>
### `signing.rb-canonicalrequest`

`class CanonicalRequest # Builds a canonical request for AWS signature # @param [Hash]…` · [lib/ruby_llm/providers/bedrock/signing.rb:L257-L260][f3]

Builds the SigV4 canonical request string.

to_s joins HTTP method, canonical path, an empty query line (query params unsupported), canonical headers plus a trailing newline, the signed-headers list, and the payload SHA-256. signed_headers and canonical_headers both skip headers listed in config.unsigned_headers, sort by name, and header values are collapsed whitespace and stripped. path defaults to '/' when empty and is percent-escaped per segment when config.uri_escape_path is true.

<a id="u-53740c8b5f24"></a>
### `signing.rb-canonicalrequestconfig`

`class CanonicalRequestConfig` · [lib/ruby_llm/providers/bedrock/signing.rb:L247-L250][f3]

CanonicalRequestConfig holds uri_escape_path (default true) and a Set of unsigned_headers (default empty); both feed CanonicalRequest's header filtering and path escaping.

<a id="u-00e1b9a487b4"></a>
### `signing.rb-credentialmanager`

`class CredentialManager` · [lib/ruby_llm/providers/bedrock/signing.rb:L490-L491][f3]

Fetches credentials from the provider and returns [credentials, expiration], where expiration is taken from the provider's expiration method when it responds to it, else nil.

Raises MissingCredentialsError ('unable to sign request without credentials set') when the key or secret is nil or empty.

<a id="u-2eff133ca061"></a>
### `signing.rb-credentials`

`class Credentials # @option options [required, String] :access_key_id # @option optio…` · [lib/ruby_llm/providers/bedrock/signing.rb:L134-L138][f3]

Credentials value object holding access_key_id, secret_access_key, and optional session_token.

The constructor raises ArgumentError unless both key options are present. set? is true only when both key and secret are non-nil and non-empty.

<a id="u-0ef618284eac"></a>
### `signing.rb-cryptoutils`

`def sha256_hexdigest(value)` · [lib/ruby_llm/providers/bedrock/signing.rb:L233-L235][f3]

Thin OpenSSL wrappers: SHA-256 hexdigest, HMAC-SHA256 binary digest, and HMAC-SHA256 hex digest, used for payload hashing and the SigV4 signing key chain.

<a id="u-d26ffa01597d"></a>
### `signing.rb-headerbuilder`

`class HeaderBuilder` · [lib/ruby_llm/providers/bedrock/signing.rb:L424-L425][f3]

Constructs the headers for a signed request.

build_sigv4_headers sets host (from the request's host header or derived from the URL) and x-amz-date, adds x-amz-security-token when the credentials carry a session token and omit_session_token is false, and adds x-amz-content-sha256 when apply_checksum_header is set. build_headers merges in an 'authorization' header assembled as algorithm Credential=..., SignedHeaders=..., Signature=...; when omit_session_token is true it re-adds the session token header if the credentials have one.

<a id="u-6f3c96758989"></a>
### `signing.rb-headerbuilder-2`

`class HeaderBuilder` · [lib/ruby_llm/providers/bedrock/signing.rb:L430-L436][f3]

Builds the HTTP headers attached to a signed SigV4 request.

build_sigv4_headers produces 'host' (from the request's host header or derived from the URL), 'x-amz-date' from the components' datetime, 'x-amz-security-token' when the credentials carry a session token and @omit_session_token is false, and 'x-amz-content-sha256' only when @apply_checksum_header is true. build_headers merges the sigv4 headers with an 'authorization' header assembled by build_authorization_header as 'ALGORITHM Credential=…, SignedHeaders=…, Signature=…'; when @omit_session_token is set it re-adds 'x-amz-security-token' from components[:creds] if that object has a session token. Note build_headers receives components but only uses them for the creds lookup.

<a id="u-45daf0fa8140"></a>
### `signing.rb-requestextractor`

`class RequestExtractor # Extract and process request components # @param [Hash] reque…` · [lib/ruby_llm/providers/bedrock/signing.rb:L359-L364][f3]

Class-level extraction of request components for signing.

extract_components pulls method/URL/downcased headers, optionally normalizes the URL path, takes datetime from the x-amz-date header or the current UTC time in SigV4 format, and computes content SHA-256 from the x-amz-content-sha256 header or hashes the body (empty string when nil). Raises ArgumentError when :http_method or :url is missing; headers default to an empty hash via to_hash on nil-safe handling.

<a id="u-c34b7cd01a86"></a>
### `signing.rb-signature`

`class Signature # @api private` · [lib/ruby_llm/providers/bedrock/signing.rb:L97-L99][f3]

Signature is a debugging-friendly result object: initialize dynamically defines setters for every key in the options hash (via send), so headers, canonical_request, string_to_sign, content_sha256, signature, and extra are all attr_accessors assigned from the constructor options rather than fixed logic.

<a id="u-ee89ab903f2e"></a>
### `signing.rb-signaturecomputation`

`class SignatureComputation` · [lib/ruby_llm/providers/bedrock/signing.rb:L320-L321][f3]

Computes SigV4 signing artifacts for a service/region.

string_to_sign joins algorithm, datetime, credential scope, and the SHA-256 of the canonical request; credential_scope is 'date/region/service/aws4_request'; credential prefixes the access key ID onto the scope. signature derives the signing key by chained HMACs ('AWS4'+secret, date, region, service, 'aws4_request') and returns the hex HMAC of the string-to-sign.

<a id="u-3c568cab871f"></a>
### `signing.rb-signaturegenerator`

`class SignatureGenerator` · [lib/ruby_llm/providers/bedrock/signing.rb:L547-L548][f3]

Core SigV4 computation.

Always uses sigv4 and 'AWS4-HMAC-SHA256' regardless of options. compute_signature merges the sigv4 headers into the request headers, builds a CanonicalRequest, derives the string-to-sign and signing key via SignatureComputation, and returns a result hash built by SignatureResultBuilder. Note build_signature_result recomputes the string-to-sign a second time for the debugging field, duplicating work but not changing the signature.

<a id="u-4a211bf8ace2"></a>
### `signing.rb-signatureresultbuilder`

`class SignatureResultBuilder` · [lib/ruby_llm/providers/bedrock/signing.rb:L516-L517][f3]

Assembles the signature result hash from request data: algorithm, credential (access key ID plus scope via SignatureComputation), signed headers from the canonical request, the signature hex, and the canonical request and string-to-sign strings for debugging.

<a id="u-849753b09f3c"></a>
### `signing.rb-signer`

`class Signer # Initialize a new signer with the provided options # @param [Hash] opti…` · [lib/ruby_llm/providers/bedrock/signing.rb:L728-L731][f3]

Facade for SigV4 request signing.

initialize builds all components via SignerInitializer and stores configuration plus service objects. sign_request fetches credentials (raising MissingCredentialsError when unset), extracts request components, builds sigv4 headers, computes the signature, and returns a Signature whose headers hash carries host, x-amz-date, optional security token and content SHA-256, and the authorization header. Class-level uri_escape_path, uri_escape, and normalize_path delegate to UriUtils.

<a id="u-9d8ac58f6445"></a>
### `signing.rb-signerinitializer`

`class SignerInitializer` · [lib/ruby_llm/providers/bedrock/signing.rb:L661-L662][f3]

Builds the Signer's dependency graph from options: validates service/region/credentials via SignerOptionExtractor, computes unsigned headers and config flags (uri_escape_path, apply_checksum_header, normalize_path default true; omit_session_token default false), then constructs SignatureGenerator, HeaderBuilder, and CredentialManager and returns the merged component hash.

Validation errors propagate from the extractors.

<a id="u-b61978bbedaf"></a>
### `signing.rb-signeroptionextractor`

`class SignerOptionExtractor` · [lib/ruby_llm/providers/bedrock/signing.rb:L628-L629][f3]

Validates and extracts signer options.

Raises ArgumentError for a missing :service, MissingRegionError for a missing :region, and MissingCredentialsError when no credentials_provider, :credentials, or :access_key_id is given; otherwise wraps static options in a StaticCredentialsProvider. initialize_unsigned_headers downcases the supplied list and always adds 'authorization', 'x-amzn-trace-id', and 'expect'.

<a id="u-e50bbf665702"></a>
### `signing.rb-signing-errors`

`class MissingCredentialsError < ArgumentError` · [lib/ruby_llm/providers/bedrock/signing.rb:L77-L78][f3]

ArgumentError subclasses for signer misconfiguration.

MissingCredentialsError renders a default message listing the accepted credential options (:access_key_id/:secret_access_key, :credentials, :credentials_provider) when none is given; MissingRegionError always raises with 'missing required option :region', ignoring any passed arguments.

<a id="u-527f817032d3"></a>
### `signing.rb-staticcredentialsprovider`

`class StaticCredentialsProvider # @option options [Credentials] :credentials # @optio…` · [lib/ruby_llm/providers/bedrock/signing.rb:L171-L176][f3]

Wraps either an existing Credentials object (from :credentials) or builds one from the remaining options; set?

is true only when a credentials object exists and reports itself set.

<a id="u-1bbf2a8f096d"></a>
### `signing.rb-uriutils`

`def uri_escape_path(path)` · [lib/ruby_llm/providers/bedrock/signing.rb:L195-L197][f3]

URI helpers for canonical signing.

uri_escape_path percent-escapes each path segment (preserving slashes); uri_escape CGI-escapes a UTF-8 string, converting '+' to '%20' and restoring '~', returning nil for nil. normalize_path cleans the URI path via Pathname (mapping '.' to ''), preserving a trailing slash. host returns just the host when the port equals the scheme default, otherwise 'host:port'.

<a id="u-bbb12959f94b"></a>
### `lib/ruby_llm/providers/bedrock/signing.rb:Credentials`

`class Credentials # @option options [required, String] :access_key_id # @option optio…` · [lib/ruby_llm/providers/bedrock/signing.rb:L147-L160][f3]

Holds AWS static credentials and validates presence at construction.

Raises ArgumentError unless both :access_key_id and :secret_access_key options are given; :session_token is optional. Exposes read-only accessors plus set?, which is true only when both key strings are non-nil and non-empty (session token irrelevant).

<a id="u-98f26b50204f"></a>
### `lib/ruby_llm/providers/bedrock/signing.rb:Signer`

`class Signer # Initialize a new signer with the provided options # @param [Hash] opti…` · [lib/ruby_llm/providers/bedrock/signing.rb:L735-L755][f3]

Facade that signs an AWS request with SigV4.

initialize delegates all wiring to SignerInitializer.create_components and stores the resulting configuration (service, region, credentials_provider, unsigned_headers, uri_escape_path, apply_checksum_header, signing_algorithm, normalize_path, omit_session_token) and service objects (signature_generator, header_builder, credential_manager). sign_request fetches credentials via CredentialManager (raising MissingCredentialsError if unset), extracts request components via RequestExtractor (normalizing the path per @normalize_path), builds sigv4 headers, computes the signature, and returns a Signature whose headers include authorization; the Signature also carries string_to_sign, canonical_request, content_sha256, and signature for debugging. Class-level uri_escape_path/uri_escape/normalize_path delegate to UriUtils.

<a id="u-366a4fcf413e"></a>
### `Signing`

`class for creating AWS signature version 4 signature. This class # provides a method …` · [lib/ruby_llm/providers/bedrock/signing.rb:L18-L75][f3]

Namespace module implementing AWS Signature Version 4 request signing, derived from the AWS SDK for Ruby (Apache 2.0).

It contains error classes, credential holders, URI/crypto utilities, canonical-request and signature-computation classes, and a Signer facade; the header comment documents configuration via service, region, and static or provider-based credentials.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/capabilities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/signing.rb
