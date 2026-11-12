# Provider Connection And Errors

**Capability.** Wraps HTTP connections, provider base behavior, configuration validation, request dispatch, and error mapping.

Observed units cover provider connection setup, shared request helpers, and error classes or middleware. They also include model refresh and OpenAI moderation payload helpers.

**Depends on.**

- [Model Registry And Media](model-registry-and-media.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md) · graph-confirmed · 3 edge(s) · Chat payload and auxiliary APIs use provider connection and errors for request dispatch and error handling.
- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) · graph-confirmed · 2 edge(s)
- [Embedding And Provider Hooks](embedding-and-provider-hooks.md) · graph-only · 2 edge(s)
- [Media And Auxiliary Operations](media-and-auxiliary-operations.md) · graph-only · 2 edge(s)
- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-only · 1 edge(s)
- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 1 edge(s)
- [Model Registry And Media](model-registry-and-media.md) · graph-only · 1 edge(s)
- [Provider Integration Compositions](provider-integration-compositions.md) · graph-only · 1 edge(s)

Parent: [Provider Transport And Streaming](provider-transport-and-streaming.md)

## Units (22)

<a id="u-86e8cf2420ac"></a>
### `connection.rb-connection-class`

`class Connection` · [lib/ruby_llm/connection.rb:L5-L8][f1]

Wraps a Faraday HTTP connection for a provider and its configuration.

It ensures provider configuration, builds middleware, and exposes post/get. instance_variables hides @config and @connection from introspection. Setup details are in private helpers.

<a id="u-652b4a8fbe78"></a>
### `connection.rb-faraday-setup`

`def setup_timeout(faraday)` · [lib/ruby_llm/connection.rb:L56-L58][f1]

Configures timeout, logging, retry, middleware, proxy, and retry exception list for the Faraday connection.

- setup_timeout: sets options.timeout to config.request_timeout.
- setup_logging: adds a response logger with bodies, response, and errors enabled, headers disabled, debug level, and filters for long base64 and embeddings arrays.
- setup_retry: sets max, interval, randomness, backoff, exceptions from retry_exceptions, and retry statuses 429, 500, 502, 503, 504, 529.
- setup_middleware: adds multipart, JSON request, JSON response, net_http adapter, and llm_errors with the provider.
- setup_http_proxy: returns unless config.http_proxy is set, otherwise assigns the proxy.
- retry_exceptions: returns the listed timeout, connection, retriable-response, rate-limit, server, unavailable, and overloaded error classes.

<a id="u-74415f2cb06c"></a>
### `connection.rb-http-verbs`

`def post(url, payload, &)` · [lib/ruby_llm/connection.rb:L36-L41][f1]

Sends POST or GET requests through the underlying Faraday connection.

Both merge provider.headers when the provider responds to headers and yield the request if a block is given.

<a id="u-76aa3609dabf"></a>
### `error.rb-error`

`class Error < StandardError` · [lib/ruby_llm/error.rb:L6-L9][f2]

Wraps an API response and message into a RubyLLM error.

initialize stores response and calls super with the explicit message or response.body.

<a id="u-37109e5ec92a"></a>
### `error.rb-errormiddleware`

`class ErrorMiddleware < Faraday::Middleware` · [lib/ruby_llm/error.rb:L32-L33][f2]

Faraday middleware that maps HTTP responses to RubyLLM error classes.

initialize stores the provider. call invokes the app and on completion calls parse_error. parse_error asks provider.parse_error for a message, then returns the message for 200..399; raises BadRequestError for 400, UnauthorizedError for 401, PaymentRequiredError for 402, ForbiddenError for 403, RateLimitError for 429, ServerError for 500, ServiceUnavailableError for 502..503, OverloadedError for 529, and Error otherwise. Each raise uses the provider message or a default. The file also registers this middleware as llm_errors.

<a id="u-3cb1c6caba2c"></a>
### `error.rb-http-error-classes`

`class BadRequestError < Error; end` · [lib/ruby_llm/error.rb:L22-L22][f2]

Defines Error subclasses for specific HTTP status failures.

They add no custom behavior; status mapping is performed by ErrorMiddleware.

<a id="u-2cb879383e73"></a>
### `error.rb-non-http-errors`

`class ConfigurationError < StandardError; end` · [lib/ruby_llm/error.rb:L16-L16][f2]

Defines StandardError subclasses for configuration, invalid role, missing model, and unsupported attachment.

They add no custom behavior in this source.

<a id="u-67f61a0ae416"></a>
### `models.rb-model-refresh-and-merge`

`def refresh!(remote_only: false)` · [lib/ruby_llm/models.rb:L28-L33][f3]

Refreshes the registry by fetching provider and Parsera models, merging them, and replacing the singleton instance.

refresh! fetches providers with remote_only, fetches Parsera, merges, and assigns a new instance. fetch_from_providers chooses configured remote or all configured providers, instantiates them, logs, and flat_maps list_models. fetch_from_parsera uses a basic JSON connection to GET the Parsera URL, maps Model::Info, and rejects nil provider/id. merge_models indexes both sources by provider:id, unions keys, prefers Parsera plus provider metadata when both exist, otherwise the available model, and sorts by provider and id. find_parsera_model uses a direct key match or, for vertexai, looks up gemini:model_id and returns it with provider vertexai. index_by_key builds provider:id keys. add_provider_metadata merges provider metadata into Parsera data.

<a id="u-1dda3f22f55e"></a>
### `moderation.rb-moderation-payload-and-response`

`def render_moderation_payload(input, model:)` · [lib/ruby_llm/providers/openai/moderation.rb:L14-L19][f4]

Builds moderation request payloads and parses moderation responses.

The payload contains model and input. Parsing raises Error with the response and error message when the body has an error message; otherwise it constructs a Moderation with id, model, and results, defaulting results to an empty array.

<a id="u-efdfa71114ab"></a>
### `provider.rb-configuration-predicates`

`def configured?` · [lib/ruby_llm/provider.rb:L92-L94][f5]

Reports whether the provider is configured, local, or remote.

configured? checks all configuration_requirements against config; local? and remote? delegate to class.

<a id="u-0b0c845c5ce3"></a>
### `provider.rb-formatting-hooks`

`def format_messages(messages)` · [lib/ruby_llm/provider.rb:L120-L127][f5]

Provides default message formatting and no-op tool-call formatting hooks.

format_messages maps role to string and content; format_tool_calls and parse_tool_calls return nil.

<a id="u-528dbec87490"></a>
### `provider.rb-provider-class`

`class Provider` · [lib/ruby_llm/provider.rb:L5-L10][f5]

Base class for LLM providers, including streaming support, provider registry, and shared request/response helpers.

Subclasses supply api_base, capabilities, payload rendering, and response parsing. Class methods register and select providers; instance methods build connections and dispatch operations.

<a id="u-4cb33e7d984c"></a>
### `provider.rb-provider-class-registry`

`def name` · [lib/ruby_llm/provider.rb:L138-L140][f5]

Defines provider class defaults and the registry used to resolve providers.

name is the last class-name component; slug is downcased name; capabilities raises NotImplementedError; configuration_requirements is empty; local? is false; remote? is the negation of local?; configured?(config) checks all requirements. register stores by symbol; resolve returns by symbol; for(model) finds the model then resolves its provider. providers is a memoized hash; local_providers and remote_providers select by local?; configured_providers selects configured? values; configured_remote_providers selects remote? and configured? values.

<a id="u-06808b7cde4b"></a>
### `provider.rb-provider-metadata`

`def api_base` · [lib/ruby_llm/provider.rb:L16-L18][f5]

Exposes provider base URL, headers, slug, name, capabilities, and configuration requirements.

api_base raises NotImplementedError; headers returns {}; the rest delegate to class methods.

<a id="u-dcd510622364"></a>
### `provider.rb-provider-operations`

`def list_models` · [lib/ruby_llm/provider.rb:L62-L65][f5]

Dispatches model listing, embedding, moderation, image, and transcription requests through the connection.

list_models GETs models_url and parses with slug/capabilities. embed renders an embedding payload, POSTs embedding_url, and parses the response. moderate renders a moderation payload, POSTs moderation_url, and parses the response. paint renders an image payload, POSTs images_url, and parses the response. transcribe builds a multipart audio file part, renders a transcription payload, POSTs transcription_url, and parses the response.

<a id="u-bf8a1c014c82"></a>
### `provider.rb-provider-private-helpers`

`def build_audio_file_part(file_path)` · [lib/ruby_llm/provider.rb:L206-L215][f5]

Builds multipart audio parts, parses JSON defensively, validates configuration, normalizes temperature, and sends synchronous completions.

build_audio_file_part expands the path, detects MIME with Marcel, and returns a Faraday multipart file part. try_parse_json returns non-Strings unchanged, parses Strings, and returns the original on JSON::ParserError. ensure_configured! finds missing requirements, returns if none, and raises ConfigurationError with name and missing keys. maybe_normalize_temperature returns the temperature unchanged. sync_response POSTs completion_url with additional headers merged into request headers when non-empty and parses the completion response.

<a id="u-364835f9f96e"></a>
### `RubyLLM.Connection.basic`

`def self.basic(&)` · [lib/ruby_llm/connection.rb:L8-L20][f1]

Builds a basic Faraday connection with logging and raise_error middleware.

The logger disables bodies, response, and headers while enabling errors at debug level; raise_error is added; a block can customize the Faraday builder.

<a id="u-84f57dfa011e"></a>
### `RubyLLM.Connection.ensure_configured!`

`def ensure_configured!` · [lib/ruby_llm/connection.rb:L112-L124][f1]

Raises a configuration error when the provider is missing required settings.

It returns if provider.configured?. Otherwise it finds missing requirements by rejecting config values, builds a Ruby configuration snippet, and raises ConfigurationError with the provider name and snippet.

<a id="u-2a5d8e299bee"></a>
### `RubyLLM.Connection.initialize`

`def initialize(provider, config)` · [lib/ruby_llm/connection.rb:L22-L34][f1]

Creates a provider connection after validating configuration and installing Faraday middleware.

It stores provider/config, calls ensure_configured!, then builds Faraday.new(provider.api_base) with timeout, logging, retry, middleware, and optional HTTP proxy.

<a id="u-abe6300b0c53"></a>
### `RubyLLM.Provider.complete`

`def complete(messages, tools:, temperature:, model:, params: {}, headers: {}, schema:…` · [lib/ruby_llm/provider.rb:L40-L60][f5]

Builds and sends a completion request, streaming when a block is given.

It normalizes temperature, deep-merges render_payload with params, and passes messages, tools, temperature, model, stream flag, and schema. With a block it calls stream_response; otherwise it calls sync_response.

<a id="u-ef8030ec0a41"></a>
### `RubyLLM.Provider.initialize`

`def initialize(config)` · [lib/ruby_llm/provider.rb:L10-L14][f5]

Initializes a provider with configuration, validates required settings, and creates its connection.

It stores config, calls ensure_configured!, and creates Connection.new(self, config).

<a id="u-e15ff4c4936a"></a>
### `RubyLLM.Provider.parse_error`

`def parse_error(response)` · [lib/ruby_llm/provider.rb:L104-L118][f5]

Extracts a provider error message from a response body.

It returns nil for an empty body. It parses JSON when possible; a Hash uses error.message, an Array joins each error.message with '. ', and other values are returned as is.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/connection.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/error.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/models.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/moderation.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/provider.rb
