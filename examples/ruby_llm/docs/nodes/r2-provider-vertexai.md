# VertexAI Adapter

**Capability.** Subclasses Gemini for Vertex AI endpoints: predict-based embeddings, publisher-model catalog, streaming/transcription/chat URLs, reusing Gemini mixins for the rest.

Use to see the Vertex-specific payload/URL differences and how the model catalog merges known models with API data.

**Depends on.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 1 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-confirmed · 1 edge(s)
- [Error Hierarchy and Middleware](r2-error-handling.md) · graph-confirmed · 1 edge(s)
- [Gemini Adapter](r2-provider-gemini.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-provider-vertexai ` → ` r2-provider-gemini `) · VertexAI subclasses Gemini, reusing its mixins and changing URLs and embeddings.

Parent: [Gemini Adapter](r2-provider-gemini.md)

## Units (8)

<a id="u-06d560296bcd"></a>
### `VertexAI`

`class VertexAI < Gemini` · [lib/ruby_llm/providers/vertexai.rb:L6-L13][f1]

VertexAI subclasses Gemini, includes VertexAI::Chat, Streaming, Embeddings, Models, and Transcription, and inherits Gemini's remaining mixins.

initialize calls super then sets @authorizer to nil, deferring credential loading until first use. api_base interpolates @config.vertexai_location into https://<location>-aiplatform.googleapis.com/v1beta1. headers has two paths: under VCR with a non-recording cassette it returns a fixed Bearer test-token header (test determinism); otherwise it lazily calls private initialize_authorizer unless @authorizer exists and applies the authorizer to an empty hash to produce auth headers. Any Google::Auth::AuthorizationError is rescued and re-raised as UnauthorizedError with the underlying message. initialize_authorizer requires 'googleauth' and obtains application default credentials scoped to cloud-platform and generative-language.retriever; a LoadError (gem missing) raises a generic Error explaining googleauth ~> 1.15 must be added to the Gemfile. Singleton configuration_requirements lists :vertexai_project_id and :vertexai_location; no capabilities override, so Gemini's is inherited.

**Notes.**

- side_effect: The @authorizer is memoized after the first headers call; credentials are loaded at most once per instance.
- failure: Missing googleauth gem surfaces as Error at first headers call, not at initialization, due to lazy authorizer setup.

inherits: [Gemini](r1-gemini-adapter.md#u-0ee8ddba6d0e); raises: [lib/ruby_llm/error.rb:Error](r2-error-handling.md#u-39e787c00a73)

**Uncertainties.**

- headers' return value when @authorizer.apply({}) succeeds depends on the googleauth gem, not shown here.
- Whether VCR's current_cassette can be nil during recording checks is unproven in this source.

<a id="u-f7bfda2a50eb"></a>
### `vertexai-chat.rb-endpoint-urls`

`def completion_url` · [lib/ruby_llm/providers/vertexai/chat.rb:L8-L10][f2]

Endpoint URL builders that interpolate instance state.

Chat's completion_url and Streaming's stream_url both build 'projects/<project>/locations/<location>/publishers/google/models/<model>...' paths from @config.vertexai_project_id, @config.vertexai_location, and @model — completion_url appends :generateContent, stream_url appends :streamGenerateContent?alt=sse. Transcription's private transcription_url(model) takes the model as an argument and appends :generateContent.

**Uncertainties.**

- These methods read @config and @model instance state set by the including class; embedding_url additionally reads the same config keys from the Embeddings module context, which relies on module_function receiver semantics not shown here.

<a id="u-ec0768f8515d"></a>
### `RubyLLM.Providers.VertexAI.Embeddings.render_embedding_payload`

`def render_embedding_payload(text, model:, dimensions:) # rubocop:disable Lint/Unused…` · [lib/ruby_llm/providers/vertexai/embeddings.rb:L14-L20][f3]

Builds the Vertex AI :predict request body.

Each text (the input, flattened) becomes an instance {content: t.to_s}, so non-string inputs are stringified. When dimensions is provided, payload[:parameters] is set to {outputDimensionality: dimensions}; otherwise no :parameters key is present.

<a id="u-132da5e8dd44"></a>
### `RubyLLM.Providers.VertexAI.Embeddings.parse_embedding_response`

`def parse_embedding_response(response, model:, text:)` · [lib/ruby_llm/providers/vertexai/embeddings.rb:L22-L28][f3]

Converts a Vertex AI predict response into an Embedding.

It maps each entry of response.body['predictions'] to p.dig('embeddings', 'values'); when predictions is nil the safe-navigation yields nil vectors. A single-vector result is unwrapped to that vector only when the requested text was not an array. It constructs Embedding.new with vectors:, model:, and input_tokens: always 0 (Vertex embeddings responses carry no usage data here).

**Uncertainties.**

- Behavior when predictions entries lack 'embeddings.values' (nil elements) and Embedding's constructor contract are defined outside this file.

<a id="u-1a94dec536b0"></a>
### `RubyLLM.Providers.VertexAI.Models.list_models`

`def list_models` · [lib/ruby_llm/providers/vertexai/models.rb:L32-L61][f4]

Fetches the Vertex AI publisher model catalog.

It starts with build_known_models, then pages GET 'publishers/google/models' via @connection.get with pageSize 100, the x-goog-user-project header from @config.vertexai_project_id, and successive pageToken values until nextPageToken is absent. For each publisher model it skips launchStage 'DEPRECATED', extracts the model id from the name path, and appends build_model_from_api_data. On any StandardError it logs the message at debug level and returns only build_known_models, so partial results gathered before the failure are discarded.

calls: [RubyLLM.Providers.VertexAI.Models.build_known_models](r2-provider-vertexai.md#u-9099038cece0), [RubyLLM.Providers.VertexAI.Models.build_model_from_api_data](r2-provider-vertexai.md#u-bf580ae0c85c), [connection.rb-connection](r2-connection.md#u-53be52e4979e)

**Uncertainties.**

- @connection and @config.vertexai_project_id are instance state of the including class; their setup is outside this file.

<a id="u-9099038cece0"></a>
### `RubyLLM.Providers.VertexAI.Models.build_known_models`

`def build_known_models` · [lib/ruby_llm/providers/vertexai/models.rb:L65-L83][f4]

Maps the frozen KNOWN_GOOGLE_MODELS list to Model::Info records with nil created_at, context_window, max_output_tokens, modalities, and pricing, capabilities fixed to ['streaming', 'function_calling'], family from determine_model_family, and metadata {source: 'known_models'}.

<a id="u-bf580ae0c85c"></a>
### `RubyLLM.Providers.VertexAI.Models.build_model_from_api_data`

`def build_model_from_api_data(model_data, model_id)` · [lib/ruby_llm/providers/vertexai/models.rb:L85-L105][f4]

Builds a Model::Info from one publisher-model API entry: id and name from the extracted model id, family from determine_model_family, nil created_at/context_window/max_output_tokens/modalities/pricing, capabilities from extract_capabilities, and metadata capturing versionId, openSourceCategory, launchStage, supportedActions, and publisherModelTemplate.

<a id="u-b0d69a273650"></a>
### `vertexai-models-rb-helpers`

`def extract_model_id_from_path(path)` · [lib/ruby_llm/providers/vertexai/models.rb:L107-L109][f4]

Support helpers.

extract_model_id_from_path returns the last '/'-segment of a model path. determine_model_family maps ids by ordered prefixes: /^gemini-2\.\d+/ -> 'gemini-2', /^gemini-1\.\d+/ -> 'gemini-1.5', /^text-embedding/ -> 'text-embedding', /bison/ -> 'palm', else 'gemini'. extract_capabilities starts from ['streaming'], adds 'function_calling' when the model_data name includes 'gemini', and uniqs — model_data['name'] being nil would raise on include?.

**Uncertainties.**

- extract_capabilities assumes model_data['name'] is a String; nil names would raise NoMethodError.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/embeddings.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/models.rb