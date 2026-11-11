# Embeddings and Mistral support

**Capability.** Implements embedding endpoints for Gemini, OpenAI, Mistral, and VertexAI, the Mistral provider adapter, and the shared Embedding value object.

Visit for anything embedding-related: the immutable Embedding result object, per-provider payload rendering and response parsing, and the Anthropic stub that uniformly raises. The Mistral provider (chat, models, capabilities, embeddings) also lives here, including its zero-price placeholder and release-date table.

**Depends on.**

- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)

Parent: [Model Metadata and Embeddings](model-metadata-and-embeddings.md)

## Units (18)

<a id="u-85284c7bc99d"></a>
### `capabilities.rb-mistral-display-names-and-families`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L26-L40][f1]

format_display_name maps known ID patterns to friendly names (Mistral Large/Medium/Small, Ministral 3B/8B, Codestral, Pixtral Large/12B, Mistral Embed/Moderation), defaulting to hyphen-split capitalization.

model_family similarly maps IDs to family strings (mistral-large/medium/small, ministral, codestral, pixtral, mistral-embed, mistral-moderation), defaulting to 'mistral'.

<a id="u-0e48385d5ea0"></a>
### `capabilities.rb-mistral-feature-predicates`

`def supports_streaming?(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L10-L12][f1]

Regex-based capability checks.

Streaming is supported unless the ID mentions embed, moderation, ocr, or transcriptions. Tools are supported unless the ID also matches voxtral or the old mistral-tiny/small 2312/2402 versions. Vision requires pixtral, mistral-small-2503/2506, or mistral-medium. JSON mode requires both streaming eligibility and tool support.

<a id="u-899a6b56ea10"></a>
### `capabilities.rb-mistral-fixed-limits`

`def context_window_for(_model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L56-L58][f1]

All Mistral models get a 32,768-token context window and an 8,192-token max output, regardless of model ID.

<a id="u-54734965c0ca"></a>
### `capabilities.rb-mistral-modalities-and-capabilities`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L64-L82][f1]

modalities_for gives pixtral models text+image input with text output, embed models text input with embeddings output, and everything else text in/out.

capabilities_for special-cases moderation IDs to ['moderation'], voxtral transcribe IDs to ['transcription'], and ocr IDs to ['vision']; otherwise it assembles streaming/function_calling/structured_output/vision from the predicates, then adds reasoning for magistral, batch unless the ID is voxtral/ocr/embed/moderation, fine_tuning for mistral small/medium/large or devstral, distillation for ministral, and predicted_outputs for codestral, deduplicating at the end.

<a id="u-84b146660507"></a>
### `chat.rb-mistral-chat-overrides`

`def format_role(role)` · [lib/ruby_llm/providers/mistral/chat.rb:L10-L12][f2]

Mistral chat formatting: roles are stringified via to_s, and render_payload calls the superclass payload builder with all arguments then deletes :stream_options from the result before returning it (Mistral rejects that option).

**Uncertainties.**

- The super target of render_payload is not visible in this batch; only the deletion of stream_options after it is proven.

<a id="u-7f061595137f"></a>
### `chat.rb-vertexai-url-builders`

`def completion_url` · [lib/ruby_llm/providers/vertexai/chat.rb:L8-L10][f3]

Builds VertexAI endpoint paths from config: completion_url and transcription_url target {model}:generateContent, stream_url targets {model}:streamGenerateContent?alt=sse, all under projects/{vertexai_project_id}/locations/{vertexai_location}/publishers/google/models/.

transcription_url takes the model as a parameter; the other two read @model. All depend on @config being set with project id and location.

<a id="u-f77a38cbc691"></a>
### `embedding.rb-embedding-interface`

`class Embedding` · [lib/ruby_llm/embedding.rb:L5-L8][f4]

Immutable value object for embedding results (vectors, model, input_tokens defaulting to 0).

The class-level embed resolves the model (defaulting to config.default_embedding_model) via Models.resolve with the given provider/assume_model_exists/context, then delegates to the provider instance's embed with the model id and optional dimensions.

<a id="u-65be8ad4d577"></a>
### `embeddings.rb-embeddings`

`def embedding_url(model:)` · [lib/ruby_llm/providers/gemini/embeddings.rb:L10-L12][f5]

Renders and parses Gemini batch embedding requests.

embedding_url is "models/{model}:batchEmbedContents". render_embedding_payload flattens the text input into one request per item, each with model, a single text part, and outputDimensionality (compacted out when nil). parse_embedding_response extracts the values arrays from body['embeddings']; when exactly one vector came back and the input was not an array it unwraps to the single vector, otherwise keeps the array. Returns an Embedding with input_tokens hardcoded to 0.

<a id="u-3adeaddaa61b"></a>
### `embeddings.rb-embeddings-2`

`def embedding_url(...)` · [lib/ruby_llm/providers/openai/embeddings.rb:L10-L12][f6]

OpenAI embeddings integration: url 'embeddings'; payload {model, input, dimensions} with nil dimensions compacted out; response parsing reads usage.prompt_tokens (defaulting to 0), maps data[].embedding into a vector list, and unwraps a single vector when only one came back and the input text was not an Array.

Returns an Embedding with vectors, model and input_tokens.

<a id="u-b690130df5d9"></a>
### `embeddings.rb-mistral-embeddings`

`def embedding_url(...)` · [lib/ruby_llm/providers/mistral/embeddings.rb:L10-L12][f7]

Mistral embeddings integration: endpoint 'embeddings', payload {model, input} (dimensions accepted but ignored), and response parsing into an Embedding.

parse_embedding_response reads usage.prompt_tokens (default 0), maps body['data'] entries to their 'embedding' vectors, unwraps a single vector to a scalar when the input text was not an Array, and constructs Embedding with vectors, model, and input_tokens.

calls: [Embedding.initialize](../../catalog.json)

<a id="u-51b10f45ede9"></a>
### `embeddings.rb-vertexai-embeddings`

`def embedding_url(model:)` · [lib/ruby_llm/providers/vertexai/embeddings.rb:L10-L12][f8]

VertexAI embeddings integration: per-model predict URL, instances-based payload, and prediction parsing into an Embedding.

embedding_url builds the {model}:predict path from config. render_embedding_payload flattens the text into instances of {content: t.to_s} and adds parameters.outputDimensionality only when dimensions is truthy. parse_embedding_response maps body['predictions''] embeddings.values to vectors, unwraps a single vector when the input text was not an Array, and constructs Embedding with input_tokens hardcoded to 0 (VertexAI does not report token usage here).

calls: [Embedding.initialize](../../catalog.json)

<a id="u-3f4cd3b8446c"></a>
### `mistral.rb-mistral-provider`

`class Mistral < OpenAI` · [lib/ruby_llm/providers/mistral.rb:L6-L11][f9]

OpenAI-compatible Mistral provider with fixed api_base https://api.mistral.ai/v1, Bearer auth from mistral_api_key, and Chat/Models/Embeddings modules.

Class capabilities returns Mistral::Capabilities; configuration requires :mistral_api_key.

<a id="u-e0646bfd131e"></a>
### `models.rb-mistral-models-listing`

`def models_url` · [lib/ruby_llm/providers/mistral/models.rb:L10-L12][f10]

Lists Mistral models: URL 'models', Authorization header built from config.mistral_api_key, and parse_list_models_response mapping body['data'] to Model::Info.

created_at comes from capabilities.release_date_for (Time.parse) and is nil when no release date; name from format_display_name; family, context window, max tokens, modalities, capabilities, and pricing from the capabilities object; metadata carries object and owned_by from the API entry.

calls: [release_date_for](../../catalog.json)

<a id="u-968d4388cf0e"></a>
### `models.rb-vertexai-model-builders`

`def build_known_models` · [lib/ruby_llm/providers/vertexai/models.rb:L65-L83][f11]

build_known_models turns each KNOWN_GOOGLE_MODELS constant entry into a Model::Info with streaming and function_calling capabilities, nil window/modalities/pricing, and metadata source 'known_models'.

build_model_from_api_data does the same shape but derives capabilities from the API payload (streaming always, function_calling when the model name contains 'gemini') and stores versionId, openSourceCategory, launchStage, supportedActions, and publisherModelTemplate in metadata. extract_model_id_from_path takes the last path segment; determine_model_family maps gemini-2.x to 'gemini-2', gemini-1.x to 'gemini-1.5', text-embedding* to 'text-embedding', bison to 'palm', else 'gemini'.

<a id="u-f3ed357903a2"></a>
### `RubyLLM.Providers.Anthropic.Embeddings.embed`

`def embed` · [lib/ruby_llm/providers/anthropic/embeddings.rb:L10-L12][f12]

Anthropic embeddings stub: `embed` raises an Error, and render_embedding_payload, embedding_url, and parse_embedding_response are aliased to it, so any embeddings call fails identically.

raises: [Error](../../catalog.json)

**Uncertainties.**

- `raise Error "Anthropic doesn't support embeddings"` parses as raise(Error("...")) — a method-style call — rather than raise(Error, "..."); the actual exception class raised depends on how Error resolves at runtime.

<a id="u-9bc5cb356a59"></a>
### `RubyLLM.Providers.Mistral.Capabilities.pricing_for`

`def pricing_for(_model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L106-L111][f1]

Returns zero input and output pricing for every model ID — a placeholder that reports all Mistral models as free.

<a id="u-93e77c84bd71"></a>
### `RubyLLM.Providers.Mistral.Capabilities.release_date_for`

`def release_date_for(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L113-L151][f1]

Maps exact Mistral model ID strings (including -latest aliases) to release date strings spanning 2023-09-27 through 2025-08-30 via a large case statement; any unmatched ID falls through the case and returns nil.

<a id="u-1a94dec536b0"></a>
### `RubyLLM.Providers.VertexAI.Models.list_models`

`def list_models` · [lib/ruby_llm/providers/vertexai/models.rb:L32-L61][f11]

Lists Vertex AI models by first appending built-from-constant known Google models, then paginating through the publishers/google/models endpoint (page size 100, x-goog-user-project header from config) until no nextPageToken, skipping API entries whose launchStage is 'DEPRECATED' and converting the rest via build_model_from_api_data.

Any StandardError during the whole process is caught, logged at debug level, and the method returns just the known models as a fallback — so failures degrade rather than raise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/embedding.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/embeddings.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/embeddings.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/embeddings.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/embeddings.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/models.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/models.rb
[f12]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/embeddings.rb
