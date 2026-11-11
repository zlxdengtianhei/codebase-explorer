# Provider class composition

**Capability.** Defines each provider class (Anthropic, Gemini, OpenAI and its OpenAI-compatible derivatives) and composes their chat, media, and models modules.

This is the entry point for seeing how a provider is assembled from capability modules and how OpenAI-compatible services (GPUStack, Ollama, OpenRouter) inherit or override OpenAI behavior. It also contains per-provider media content formatting. VertexAI subclasses Gemini while Bedrock lives elsewhere.

**Depends on.**

- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)
- [OpenAI model capabilities](openai-model-capabilities.md) · graph-only · 1 edge(s)

Parent: [Provider Adapters and Tools](provider-adapters-and-tools.md)

## Units (18)

<a id="u-4b37ca26f437"></a>
### `anthropic.rb-anthropic-provider`

`class Anthropic < Provider` · [lib/ruby_llm/providers/anthropic.rb:L6-L14][f1]

Provider subclass for the Anthropic Claude API, composing Chat, Embeddings, Media, Models, Streaming, and Tools modules.

api_base is the fixed https://api.anthropic.com; headers send the configured API key under 'x-api-key' plus the pinned 'anthropic-version' date. Class-level capabilities returns Anthropic::Capabilities; configuration_requirements lists :anthropic_api_key.

<a id="u-1461306f318b"></a>
### `chat.rb-gpustack-message-formatting`

`def format_messages(messages)` · [lib/ruby_llm/providers/gpustack/chat.rb:L10-L19][f2]

format_messages maps each message to a hash with the role stringified via format_role (plain to_s), content formatted by GPUStack::Media.format_content, plus tool_calls and tool_call_id fields; nil entries are removed by compact, so messages without tool data omit those keys.

<a id="u-d2f10b469195"></a>
### `chat.rb-ollama-chat-message-formatting`

`def format_messages(messages)` · [lib/ruby_llm/providers/ollama/chat.rb:L10-L19][f3]

Formats chat messages for Ollama: each message becomes a hash with stringified role (format_role via to_s), content formatted through Ollama::Media.format_content, tool_calls via format_tool_calls, and tool_call_id, with nil entries removed by compact.

format_tool_calls is not visible in this batch.

calls: [media.rb-ollama-media-formatting](provider-class-composition.md#u-766e93c700d5)

**Uncertainties.**

- format_tool_calls is not visible; its output shape is unproven.

<a id="u-bb1976a49777"></a>
### `gemini.rb-gemini-provider`

`class Gemini < Provider` · [lib/ruby_llm/providers/gemini.rb:L6-L16][f4]

Native Google Gemini provider composing Chat, Embeddings, Images, Models, Transcription, Streaming, Tools, and Media modules.

api_base prefers a configured gemini_api_base, defaulting to the generativelanguage.googleapis.com v1beta endpoint; headers pass the API key as 'x-goog-api-key'. Class capabilities returns Gemini::Capabilities; configuration requires :gemini_api_key.

<a id="u-c2f49ed5d781"></a>
### `gpustack.rb-gpustack-provider`

`class GPUStack < OpenAI` · [lib/ruby_llm/providers/gpustack.rb:L6-L11][f5]

OpenAI-compatible provider for GPUStack, including its Chat, Models, and Media modules.

api_base comes solely from the configured gpustack_api_base (nil if unset). headers returns {} when no gpustack_api_key is configured, otherwise a Bearer header. Class-level local? is true; configuration requires :gpustack_api_base.

<a id="u-ec18eff734e3"></a>
### `media.rb-gpustack-media-formatting`

`def format_content(content)` · [lib/ruby_llm/providers/gpustack/media.rb:L12-L32][f6]

Formats chat content into GPUStack/OpenAI-style parts, delegating base helpers to OpenAI::Media.

format_content returns content.value for Raw content, to_json for Hash/Array, the content itself when not a Content, and otherwise builds a parts array: format_text of content.text when present, then per attachment an image_url part (format_image: url from for_llm, detail 'auto') for :image, format_text_file for :text, else raises UnsupportedAttachmentError with the attachment's mime_type.

inherits: [Media](../../catalog.json)

**Uncertainties.**

- format_text and format_text_file come from OpenAI::Media, not visible here; their output shape is unproven.

<a id="u-289f5b551a0e"></a>
### `media.rb-image-and-pdf-part-formatting`

`def format_image(image)` · [lib/ruby_llm/providers/bedrock/media.rb:L37-L46][f7]

Formats an attachment as a base64-encoded Anthropic content part: images use type 'image', PDFs use type 'document', both with source {type: 'base64', media_type, data} taken from the attachment's mime_type and encoded payload.

<a id="u-eec369a62887"></a>
### `media.rb-media-part-formatters`

`def format_image(image)` · [lib/ruby_llm/providers/openai/media.rb:L36-L43][f8]

Per-type attachment formatters producing OpenAI content parts.

Images become {type:'image_url', image_url:{url}} using the attachment's source directly when it has a URL, otherwise its for_llm representation. PDFs become {type:'file', file:{filename, file_data: for_llm}}. Text files and plain text both become {type:'text', text}. Audio becomes {type:'input_audio', input_audio:{data: encoded, format}} relying on the attachment's encoded payload and format.

<a id="u-766e93c700d5"></a>
### `media.rb-ollama-media-formatting`

`def format_content(content)` · [lib/ruby_llm/providers/ollama/media.rb:L12-L32][f9]

Formats chat content into Ollama/OpenAI-style parts, delegating base helpers to OpenAI::Media.

format_content returns content.value for Raw content, to_json for Hash/Array, the content itself when not a Content, and otherwise builds a parts array: format_text of content.text when present, then per attachment an image_url part (format_image: url from for_llm, detail 'auto') for :image, format_text_file for :text, else raises UnsupportedAttachmentError with the attachment's mime_type.

inherits: [Media](../../catalog.json)

**Uncertainties.**

- format_text and format_text_file come from OpenAI::Media, not visible here; their output shape is unproven.

<a id="u-5a368e6b82af"></a>
### `models.rb-gpustack-model-list-parsing`

`def parse_list_models_response(response, slug, _capabilities)` · [lib/ruby_llm/providers/gpustack/models.rb:L14-L39][f10]

parse_list_models_response converts a GPUStack API response's 'items' into Model::Info records: id and name from the item's 'name', created_at parsed with Time.parse when present, provider from the slug, family 'gpustack', context window and max output tokens both from meta.n_ctx, empty pricing, and metadata carrying description, source, repo ids, backend, meta, and categories.

build_capabilities starts empty and adds: streaming, structured_output, and json_mode for items categorized 'llm'; function_calling, vision, or reasoning when the corresponding meta support flags are set. build_modalities gives llm-categorized models text input (plus image or audio when supported) and text output; embedding-categorized models get text input and embeddings output; anything else gets empty modality arrays. determine_model_type classifies items as 'embedding', 'chat', or 'other' from categories, though it is not called by the parser in this file.

<a id="u-a5174e9527e3"></a>
### `models.rb-ollama-models-listing`

`def models_url` · [lib/ruby_llm/providers/ollama/models.rb:L8-L10][f11]

Lists Ollama models without using the capabilities argument: URL 'models'; parse_list_models_response maps body['data'] (default []) to Model::Info with id and name both from model['id'], family 'ollama', created_at from Time.at(model['created']) or nil, hardcoded text+image input / text output modalities, hardcoded streaming/function_calling/structured_output/vision capabilities, empty pricing, and owned_by metadata.

<a id="u-77a79f089e06"></a>
### `models.rb-openrouter-model-list-parsing`

`def parse_list_models_response(response, slug, _capabilities)` · [lib/ruby_llm/providers/openrouter/models.rb:L14-L57][f12]

parse_list_models_response converts the response's 'data' array into Model::Info records: id/name/provider from the payload, family from the ID's prefix before '/', created_at from the unix timestamp, context window from context_length, max output tokens from top_provider.max_completion_tokens, modalities from architecture input/output_modalities, and metadata carrying description, architecture, top_provider, per_request_limits, and supported_parameters.

Pricing is built under text_tokens.standard by reading prompt/completion/input_cache_read/internal_reasoning prices, scaling each by 1,000,000 and including only positive values. supported_parameters_to_capabilities returns [] when params is nil; otherwise it always includes 'streaming' and adds function_calling for tools or tool_choice, structured_output for response_format, batch for batch, and predicted_outputs only when both logit_bias and top_k are present.

<a id="u-c9594c889107"></a>
### `ollama.rb-ollama-provider`

`class Ollama < OpenAI` · [lib/ruby_llm/providers/ollama.rb:L6-L11][f13]

OpenAI-compatible local Ollama provider including Chat, Media, and Models modules.

api_base is the configured ollama_api_base; headers is always {} (no auth). Class-level configuration_requirements is [:ollama_api_base] and local? is true; no capabilities override, so it inherits OpenAI's.

<a id="u-9da6d221a66b"></a>
### `openai.rb-openai-provider`

`class OpenAI < Provider` · [lib/ruby_llm/providers/openai.rb:L6-L17][f14]

Base OpenAI provider composing Chat, Embeddings, Models, Moderation, Streaming, Tools, Images, Media, and Transcription modules.

api_base prefers configured openai_api_base, defaulting to https://api.openai.com/v1. headers builds Bearer auth plus OpenAI-Organization and OpenAI-Project entries, with compact removing any nil-valued optional headers. `maybe_normalize_temperature` delegates to OpenAI::Capabilities.normalize_temperature with the model id. Class capabilities returns OpenAI::Capabilities; configuration requires :openai_api_key.

<a id="u-3dcddd63cf52"></a>
### `openrouter.rb-openrouter-provider`

`class OpenRouter < OpenAI` · [lib/ruby_llm/providers/openrouter.rb:L6-L9][f15]

OpenAI-compatible OpenRouter provider including only its Models module, so chat behavior is inherited from OpenAI.

Fixed api_base https://openrouter.ai/api/v1; Bearer header from openrouter_api_key. Class configuration requires :openrouter_api_key; no capabilities or local? override.

<a id="u-8007dcb1387d"></a>
### `vertexai.rb-vertexai-provider`

`class VertexAI < Gemini` · [lib/ruby_llm/providers/vertexai.rb:L6-L13][f16]

Vertex AI provider subclassing Gemini and composing Chat, Streaming, Embeddings, Models, and Transcription modules.

`initialize` calls super then nils a cached authorizer. api_base interpolates the configured vertexai_location into the aiplatform v1beta1 endpoint. `headers` short-circuits with a static 'Bearer test-token' when VCR is defined and not recording (test replay); otherwise it lazily initializes the authorizer and applies it to an empty hash to obtain auth headers. A Google::Auth::AuthorizationError is rescued and re-raised as UnauthorizedError with a VertexAI-specific message. `initialize_authorizer` lazily requires the googleauth gem and fetches application-default credentials with cloud-platform and generative-language.retriever scopes; a LoadError is rescued and re-raised as a generic Error instructing the user to add googleauth ~> 1.15. Class configuration requires vertexai_project_id and vertexai_location; capabilities are inherited from Gemini.

<a id="u-15d22633b933"></a>
### `RubyLLM.Providers.Bedrock.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/bedrock/media.rb:L13-L35][f7]

Converts message content into Anthropic-style content parts, extending Anthropic::Media but overriding to reject URL-based attachments.

Raw content passes through as its value; Hash/Array content is JSON-serialized into a text part; non-Content objects become a single text part. For Content objects, text becomes a text part and each attachment is dispatched by type: image, pdf, text file (via Anthropic::Media.format_text_file), else raises UnsupportedAttachmentError with the attachment type.

<a id="u-c58a518d68d9"></a>
### `RubyLLM.Providers.OpenAI.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/media.rb:L10-L34][f8]

Converts message content into OpenAI-compatible parts.

Raw content returns its value verbatim; Hash/Array content is JSON-serialized; non-Content objects pass through unchanged. For Content objects it collects a text part (when text is present) plus one part per attachment, dispatched by type: image, pdf, audio, and text each have a dedicated formatter; any other attachment type raises UnsupportedAttachmentError with the type as the message.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/media.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/media.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/media.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/media.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/models.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/models.rb
[f12]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter/models.rb
[f13]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama.rb
[f14]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai.rb
[f15]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter.rb
[f16]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/vertexai.rb
