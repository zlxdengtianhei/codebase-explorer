# Core provider infrastructure

**Capability.** Provides the abstract Provider base class, Faraday connection management, error hierarchy and middleware, and the model registry with lookup and refresh.

The backbone of the gem: Provider defines request/parse templates for chat, embeddings, moderation, images, and transcription, plus the class-level provider registry. Connection configures Faraday with retries and debug filtering; Error maps HTTP failures; Models merges registry and Parsera-sourced model specs.

**Depended on by.**

- [Bedrock AWS integration](bedrock-aws-integration.md) · graph-confirmed · 1 edge(s) · Bedrock integration builds on the abstract provider base and connection management.
- [Streaming and result objects](streaming-and-result-objects.md) · graph-confirmed · 2 edge(s)
- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 2 edge(s)
- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-only · 1 edge(s)
- [AWS SigV4 Request Signing](aws-sigv4-request-signing.md) · graph-only · 1 edge(s)
- [Bedrock model capabilities](bedrock-model-capabilities.md) · graph-only · 1 edge(s)
- [Embeddings and Mistral support](embeddings-and-mistral-support.md) · graph-only · 1 edge(s)
- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-only · 1 edge(s)
- [Provider class composition](provider-class-composition.md) · graph-only · 1 edge(s)

Parent: [Streaming and Provider Core](streaming-and-provider-core.md)

## Units (27)

<a id="u-74d02b4f9b1f"></a>
### `connection.rb-connection-setup`

`class Connection` · [lib/ruby_llm/connection.rb:L5-L8][f1]

Manages Faraday connections to providers.

basic builds a bare Faraday connection with debug logging (no bodies/response/headers) and raise_error, yielding for extra config. initialize verifies the provider is configured (raising ConfigurationError via ensure_configured! otherwise) and builds the cached connection with timeout, verbose logging with redaction filters, retry, middleware, and optional proxy setup.

<a id="u-f3755d4b007b"></a>
### `connection.rb-faraday-setup-helpers`

`def setup_timeout(faraday)` · [lib/ruby_llm/connection.rb:L56-L58][f1]

Configure the connection: timeout from config.request_timeout; debug logging with bodies/response/errors and filters masking long base64 and embedding arrays; retry with configured max/interval/randomness/backoff on retry_exceptions (timeout, connection failures, and RubyLLM rate-limit/server/overloaded errors) and statuses 429, 500, 502, 503, 504, 529; multipart+json request and json response middleware, net_http adapter, and the llm_errors middleware bound to the provider; an optional HTTP proxy from config.

<a id="u-74415f2cb06c"></a>
### `connection.rb-http-verbs`

`def post(url, payload, &)` · [lib/ruby_llm/connection.rb:L36-L41][f1]

post/get issue requests through the Faraday connection, merging the provider's headers when the provider responds to headers, and yielding the request for per-call customization (e.g., streaming on_data).

Errors and retries are handled by the configured middleware.

<a id="u-ad9c6ddfe44e"></a>
### `error.rb-error-base`

`class Error < StandardError` · [lib/ruby_llm/error.rb:L6-L9][f2]

StandardError subclass wrapping a provider response; initialize stores the response and uses the explicit message or the response body as the exception message (nil-safe via &.).

<a id="u-c6343f8430e9"></a>
### `error.rb-error-middleware`

`class ErrorMiddleware < Faraday::Middleware` · [lib/ruby_llm/error.rb:L32-L33][f2]

Faraday middleware (registered as :llm_errors) that, on response completion, calls the class-level parse_error with the provider.

parse_error first asks the provider for a message via parse_error, then switches on status: 200..399 returns the message without raising; 400/401/402/403/429/500 raise the corresponding typed error with the provider message or a fixed fallback; 502..503 raise ServiceUnavailableError; 529 raises OverloadedError; any other status raises generic Error. The raised errors wrap the response.

<a id="u-c2f1b49ff598"></a>
### `error.rb-error-taxonomy`

`class ConfigurationError < StandardError; end` · [lib/ruby_llm/error.rb:L16-L16][f2]

Non-HTTP errors (ConfigurationError, InvalidRoleError, ModelNotFoundError, UnsupportedAttachmentError) subclass StandardError directly; HTTP-mapped errors (BadRequest, Unauthorized, PaymentRequired, Forbidden, RateLimit, Server, ServiceUnavailable, Overloaded) subclass RubyLLM::Error and therefore carry the response.

<a id="u-75a1d5d16f1d"></a>
### `models.rb-model-lookup`

`def find_with_provider(model_id, provider)` · [lib/ruby_llm/models.rb:L218-L223][f3]

find_with_provider matches by exact id and provider string, then by the Aliases-resolved id, else raises ModelNotFoundError naming model and provider.

find_without_provider matches by id, then by alias, else raises ModelNotFoundError naming the id.

<a id="u-8a9b19088e15"></a>
### `models.rb-model-merging`

`def merge_models(provider_models, parsera_models)` · [lib/ruby_llm/models.rb:L106-L126][f3]

merge_models unions provider and Parsera models keyed by "provider:id": when both exist, the Parsera model wins with provider metadata merged in (provider metadata as base, Parsera metadata overriding); when only one exists it is kept; results are sorted by provider then id.

find_parsera_model additionally maps vertexai keys to the matching gemini Parsera entry, rebuilding it with provider 'vertexai'. add_provider_metadata merges metadata hashes; index_by_key builds the key hash.

<a id="u-1e44a7770ab3"></a>
### `models.rb-model-registry-loading`

`class << self` · [lib/ruby_llm/models.rb:L8-L9][f3]

Class-level registry access: instance is a memoized Models; schema_file locates models_schema.json next to the source file; load_models/read_from_json parse the registry JSON file (defaulting to config.model_registry_file) into Model::Info objects, treating a missing file as empty and rescuing JSON::ParserError to return [].

<a id="u-9499653dd8d9"></a>
### `models.rb-registry-instance-api`

`def initialize(models = nil)` · [lib/ruby_llm/models.rb:L156-L158][f3]

Instance wraps a model array (loaded from JSON when not injected).

load_from_json! replaces the models from a file; save_to_json pretty-prints all models to the registry file; all/each expose the array (Enumerable); find delegates to provider-aware or provider-less lookup; chat/embedding/audio/image_models return new filtered instances by type or output modality; by_family/by_provider filter by string comparison; refresh! and resolve delegate to the class-level equivalents.

<a id="u-dd0d83896efb"></a>
### `models.rb-registry-refresh`

`def refresh!(remote_only: false)` · [lib/ruby_llm/models.rb:L28-L33][f3]

refresh!

rebuilds the singleton instance by fetching models from providers (configured remote providers when remote_only, else all configured providers, instantiating each with the global config and flat-mapping list_models) plus Parsera, merging them via merge_models. fetch_from_providers logs the provider names first; provider fetch errors propagate.

<a id="u-97e4b6758150"></a>
### `models.rb-singleton-delegation`

`def method_missing(method, ...)` · [lib/ruby_llm/models.rb:L82-L88][f3]

method_missing forwards unknown class-level calls to the memoized instance when it responds, else super; respond_to_missing?

mirrors that so the delegation is introspectable.

<a id="u-e1fe0c83259f"></a>
### `moderation.rb-moderation`

`def moderation_url` · [lib/ruby_llm/providers/openai/moderation.rb:L10-L12][f4]

OpenAI moderation integration: url 'moderations'; payload {model, input}.

Parsing raises Error with the API error message when the body contains one, otherwise builds a RubyLLM::Moderation with the response id, the requested model, and results defaulting to [] when absent.

<a id="u-f8cc82a1b290"></a>
### `provider.rb-message-formatting-stubs`

`def format_messages(messages)` · [lib/ruby_llm/provider.rb:L120-L127][f5]

format_messages maps each message to {role (stringified), content}; format_tool_calls and parse_tool_calls are nil-returning stubs for providers without tool-call translation.

<a id="u-b6d1678c05e4"></a>
### `provider.rb-provider`

`class Provider` · [lib/ruby_llm/provider.rb:L5-L10][f5]

Abstract base class for LLM providers, mixing in Streaming and owning a config and a per-provider Connection.

initialize stores the config, raises ConfigurationError via ensure_configured! when requirements are unmet, then builds the Connection (which re-checks configuration). Subclasses must supply api_base and the render/parse methods used by the operation templates.

<a id="u-4cb33e7d984c"></a>
### `provider.rb-provider-class-registry`

`class << self` · [lib/ruby_llm/provider.rb:L137-L138][f5]

Class-level DSL and registry: name/slug derive from the class name (slug downcased); capabilities raises NotImplementedError; configuration_requirements defaults to []; local?

defaults false and remote? its negation; configured?(config) checks requirements against a config; register/resolve store and fetch provider classes by symbol in a memoized hash; providers exposes it; local_providers/remote_providers select by class flag; configured_providers/configured_remote_providers select classes whose requirements are met for a config, returning the class values. Provider.for resolves a model's provider class via Models.find.

<a id="u-bc45c5ded73c"></a>
### `provider.rb-provider-classification`

`def configured?` · [lib/ruby_llm/provider.rb:L92-L94][f5]

configured?

checks all configuration_requirements against config; local?/remote? delegate to class-level flags (local defaults false, so remote defaults true).

<a id="u-ac15d4802edc"></a>
### `provider.rb-provider-metadata-accessors`

`def api_base` · [lib/ruby_llm/provider.rb:L16-L18][f5]

Mostly delegate to class-level values: slug/name/capabilities/configuration_requirements read class attributes; headers returns {} by default; api_base raises NotImplementedError, forcing subclass definition.

<a id="u-84f0aab55f18"></a>
### `provider.rb-provider-operation-templates`

`def embed(text, model:, dimensions:)` · [lib/ruby_llm/provider.rb:L67-L71][f5]

Uniform request/parse templates: embed renders an embedding payload and posts to the embedding URL; moderate posts a moderation payload; paint posts an image-generation payload; transcribe builds a multipart file part from a local path (Marcel MIME detection) and posts a transcription payload with language and extra options.

Each parses the response via the provider's corresponding parse method; connection errors propagate.

<a id="u-bf8a1c014c82"></a>
### `provider.rb-provider-private-helpers`

`def build_audio_file_part(file_path)` · [lib/ruby_llm/provider.rb:L206-L215][f5]

build_audio_file_part expands a file path and builds a Faraday multipart FilePart with Marcel-detected MIME type.

try_parse_json parses JSON strings, returning the original on JSON::ParserError and passing non-strings through. ensure_configured! raises ConfigurationError naming the provider and missing config keys. maybe_normalize_temperature is an identity no-op for subclass override. sync_response posts the payload to completion_url (merging additional headers) and parses the completion response.

<a id="u-84f57dfa011e"></a>
### `RubyLLM.Connection.ensure_configured!`

`def ensure_configured!` · [lib/ruby_llm/connection.rb:L112-L124][f1]

Raises ConfigurationError when the provider is not configured, listing missing configuration keys and embedding a ready-to-paste RubyLLM.configure snippet mapping each key to an ENV placeholder.

<a id="u-bbd0d20d0d5b"></a>
### `RubyLLM.Connection.instance_variables`

`def instance_variables` · [lib/ruby_llm/connection.rb:L50-L52][f1]

Excludes @config and @connection from instance_variables (duplication support).

<a id="u-b390fa4f90b2"></a>
### `RubyLLM.Models.fetch_from_parsera`

`def fetch_from_parsera` · [lib/ruby_llm/models.rb:L94-L104][f3]

Fetches model specs from the Parsera API over a basic JSON connection, wraps each response entry in Model::Info, and drops entries lacking provider or id.

Network/HTTP errors propagate from Faraday's raise_error middleware.

<a id="u-3dcbba4582dc"></a>
### `RubyLLM.Models.resolve`

`def resolve(model_id, provider: nil, assume_exists: false, config: nil) # rubocop:dis…` · [lib/ruby_llm/models.rb:L49-L80][f3]

Resolves a model id to a [Model::Info, Provider instance] pair.

With an explicit provider, its class is looked up (unknown provider raises Error), assume_exists is forced true for local providers, and ArgumentError is raised if assume_exists is set without a provider; local providers try Models.find and fall back to Model::Info.default, while remote providers with assume_exists skip the registry and use Model::Info.default directly. Without assume_exists, Models.find must succeed (raising ModelNotFoundError) and the model's provider class must be registered (else Error). The provider instance is built with the given or global config.

<a id="u-abe6300b0c53"></a>
### `RubyLLM.Provider.complete`

`def complete(messages, tools:, temperature:, model:, params: {}, headers: {}, schema:…` · [lib/ruby_llm/provider.rb:L40-L60][f5]

Template for chat completion: normalizes temperature (no-op by default), merges the rendered payload (with tools, temperature, model, stream flag from block presence, schema) with user params via Utils.deep_merge, then either streams via stream_response with the block or performs a synchronous sync_response against the connection, merging additional headers.

Payload rendering and response parsing are subclass-provided.

<a id="u-1336dd69d787"></a>
### `RubyLLM.Provider.list_models`

`def list_models` · [lib/ruby_llm/provider.rb:L62-L65][f5]

Fetches the provider's model list over the connection and parses it with the provider's parse_list_models_response using the slug and capabilities.

<a id="u-e15ff4c4936a"></a>
### `RubyLLM.Provider.parse_error`

`def parse_error(response)` · [lib/ruby_llm/provider.rb:L104-L118][f5]

Extracts a human-readable error message from a response: empty bodies yield nil; JSON hashes dig 'error'.'message'; JSON arrays join each part's error message with '.

'; non-JSON or non-hash bodies are returned as-is.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/connection.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/error.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/models.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/moderation.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/provider.rb
