# Embedding And Provider Hooks

**Capability.** Provides embedding value and request flow plus provider-specific embedding, chat, model, and capability hooks.

Observed units cover embedding request/response handling and provider modules that compose embedding support. They include rejection, Gemini/Mistral/OpenAI/VertexAI implementations, and related metadata.

**Depends on.**

- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 2 edge(s)

Parent: [Provider Model Abstractions](provider-model-abstractions.md)

## Units (17)

<a id="u-800c89cf849f"></a>
### `capabilities.rb-capabilities-and-modalities`

`def supports_streaming?(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L10-L12][f1]

Derives Mistral capability flags and modalities.

Streaming is false for embed, moderation, ocr, or transcriptions. Tools are false for those plus voxtral and mistral tiny/small 2312/2402. Vision is true for pixtral, mistral-small 2503/2506, or mistral-medium. JSON mode requires the streaming exclusion and tools support. Modalities are text/image to text for pixtral, text to embeddings for embed, otherwise text to text. Capabilities special-case moderation, voxtral transcription, and ocr; otherwise they add streaming, function_calling, structured_output, vision, reasoning for magistral, batch unless voxtral/ocr/embed/moderation, fine_tuning for selected families, distillation for ministral, and predicted_outputs for codestral, then deduplicate.

<a id="u-b570313b89c3"></a>
### `capabilities.rb-metadata-pricing-and-release-dates`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L26-L40][f1]

Provides Mistral display names, families, fixed limits, zero pricing, and release dates.

Display names map known families and otherwise title-case hyphen parts; family maps known regexes and otherwise mistral. Context is always 32,768 and max output always 8,192. Pricing is zero input and output. Release dates are exact-string cases and return nil when no case matches.

<a id="u-20b2d275b748"></a>
### `chat.rb-mistral-chat-formatting`

`class Mistral # Chat methods for Mistral API` · [lib/ruby_llm/providers/mistral/chat.rb:L5-L7][f2]

Provides Mistral chat formatting and payload adjustment.

Role formatting stringifies the role. Payload rendering calls the superclass implementation, removes the stream_options key, and returns the modified payload.

**Uncertainties.**

- The superclass payload shape is outside this source.

<a id="u-efbe27704c71"></a>
### `chat.rb-vertex-ai-chat-url`

`class VertexAI # Chat methods for the Vertex AI implementation` · [lib/ruby_llm/providers/vertexai/chat.rb:L5-L7][f3]

Builds the Vertex AI generateContent URL from the configured project and location plus the current model.

No request is sent here.

<a id="u-89069ab89995"></a>
### `embedding.rb-embedding-class`

`class Embedding` · [lib/ruby_llm/embedding.rb:L5-L8][f4]

Value object holding embedding vectors, model identifier, and input token count.

initialize assigns vectors, model, and input_tokens defaulting to 0. The class method embed resolves a model/provider and delegates embedding.

<a id="u-b7e0999971cc"></a>
### `embeddings.rb-anthropic-embeddings-unsupported`

`class Anthropic # Embeddings methods of the Anthropic API integration` · [lib/ruby_llm/providers/anthropic/embeddings.rb:L5-L7][f5]

Provides Anthropic embedding hooks that uniformly reject embedding requests.

The primary method raises Error with a fixed unsupported message, and the payload-rendering, URL, and response-parsing aliases all route to that same raising method. No embedding data is produced.

<a id="u-bfa37a508a42"></a>
### `embeddings.rb-embedding-payload-and-response`

`def render_embedding_payload(text, model:, dimensions:)` · [lib/ruby_llm/providers/openai/embeddings.rb:L14-L20][f6]

Builds embedding request payloads and parses embedding responses.

The payload contains model, input text, and dimensions, with nil dimensions removed. Parsing reads prompt_tokens or 0, maps each data item to its embedding vector, and unwraps a single vector only when the input text was not an array; it then constructs an Embedding with vectors, model, and input tokens.

<a id="u-5f3696794a3a"></a>
### `embeddings.rb-embedding-request-response`

`def embedding_url(model:)` · [lib/ruby_llm/providers/gemini/embeddings.rb:L10-L12][f7]

Builds Gemini batch embedding requests and parses embedding responses.

The URL targets batchEmbedContents. Rendering flattens the input text, maps each item to a request with model, text content, and optional output dimensionality, and compacts nil values. Parsing maps response embeddings to vectors, unwraps a single vector when the input was not an array, and returns an Embedding with zero input tokens; missing embeddings yield nil vectors.

<a id="u-b690130df5d9"></a>
### `embeddings.rb-mistral-embeddings`

`class Mistral # Embeddings methods for Mistral API` · [lib/ruby_llm/providers/mistral/embeddings.rb:L5-L7][f8]

Implements Mistral embedding URL, payload, and response parsing.

The URL is fixed. The payload contains model and input and ignores dimensions. Parsing reads prompt token usage or zero, maps each data entry's embedding, collapses a single vector to a scalar vector when the original text was not an array, and returns an Embedding with vectors, model, and input tokens.

<a id="u-f9c260b338ca"></a>
### `embeddings.rb-vertex-ai-embeddings`

`class VertexAI # Embeddings methods for the Vertex AI implementation` · [lib/ruby_llm/providers/vertexai/embeddings.rb:L5-L7][f9]

Implements Vertex AI embedding URL, payload, and response parsing.

The URL uses the configured project and location plus the requested model and predict action. The payload flattens the input into instances with string content and adds outputDimensionality only when dimensions is truthy. Parsing reads body predictions, maps each prediction's embeddings.values, collapses a single vector when the original text was not an array, and returns an Embedding with zero input tokens.

<a id="u-3f4cd3b8446c"></a>
### `mistral.rb-mistral-provider`

`class Mistral < OpenAI` · [lib/ruby_llm/providers/mistral.rb:L6-L11][f10]

Mistral is an OpenAI-derived provider integration composing chat, models, and embeddings modules.

Its API base is the fixed Mistral URL. Headers send the configured Mistral API key as a Bearer token. The class-level capabilities method returns the Mistral capabilities class, and configuration requires a Mistral API key.

<a id="u-59067821ae2b"></a>
### `models.rb-mistral-model-listing`

`class Mistral # Model information for Mistral` · [lib/ruby_llm/providers/mistral/models.rb:L5-L7][f11]

Lists Mistral models and builds model info from API data.

The URL is fixed and headers use a bearer token from the configured Mistral API key. Listing maps each body data entry, derives created_at from the capability release date when present (otherwise nil), and fills name, family, context window, max tokens, modalities, capabilities, pricing, and metadata object/owned_by from the entry and capability lookups.

<a id="u-03bd2d939187"></a>
### `models.rb-model-listing-4`

`def list_models` · [lib/ruby_llm/providers/vertexai/models.rb:L32-L61][f12]

Lists Vertex AI models, starting with known Google models and paging through publisher models.

Requests use the configured project header, page size 100, and page token; deprecated models are skipped; ids come from the last path segment; paging continues while nextPageToken exists. Any standard error logs at debug and returns only the known-model list. Known models have streaming and function_calling capabilities and source metadata. API models store snake_case metadata keys version_id, open_source_category, launch_stage, supported_actions, and publisher_model_template. Family is gemini-2, gemini-1.5, text-embedding, palm, or gemini by regex; capabilities are streaming plus function_calling when the name includes gemini.

<a id="u-00ed25ac6168"></a>
### `streaming.rb-vertex-ai-streaming-url`

`class VertexAI # Streaming methods for the Vertex AI implementation` · [lib/ruby_llm/providers/vertexai/streaming.rb:L5-L7][f13]

Builds the Vertex AI streamGenerateContent URL with SSE output from the configured project and location plus the current model.

<a id="u-7fce8b9e19ec"></a>
### `transcription.rb-vertex-ai-transcription-url`

`class VertexAI # Vertex AI specific helpers for audio transcription` · [lib/ruby_llm/providers/vertexai/transcription.rb:L5-L7][f14]

Builds the Vertex AI generateContent URL for transcription from the configured project and location plus the supplied model.

<a id="u-8007dcb1387d"></a>
### `vertexai.rb-vertexai-provider`

`class VertexAI < Gemini` · [lib/ruby_llm/providers/vertexai.rb:L6-L13][f15]

VertexAI is a Gemini-derived Google provider integration composing chat, streaming, embeddings, models, and transcription modules.

Initialization calls super and clears the authorizer. Its API base builds a URL from the configured location. Headers use a fixed test token when VCR is defined and not recording; otherwise they initialize the authorizer if absent and apply it. Authorization errors from Google Auth are re-raised as UnauthorizedError with a credential message. Authorizer initialization requires googleauth, requests application default credentials with cloud-platform and generative-language.retriever scopes, and raises a load error message when the gem is missing. Configuration requires project id and location.

<a id="u-2e72a7f7f76b"></a>
### `RubyLLM.Embedding.embed`

`def self.embed(text, # rubocop:disable Metrics/ParameterLists model: nil, provider: n…` · [lib/ruby_llm/embedding.rb:L14-L27][f4]

Resolves an embedding model and provider, then delegates the embedding request.

It uses context config or RubyLLM.config, defaults the model to default_embedding_model, calls Models.resolve with provider/assume_exists/config, and passes model.id and dimensions to provider_instance.embed.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/embedding.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/embeddings.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/embeddings.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/embeddings.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/embeddings.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/embeddings.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/models.rb
[f12]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/models.rb
[f13]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/streaming.rb
[f14]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai/transcription.rb
[f15]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai.rb
