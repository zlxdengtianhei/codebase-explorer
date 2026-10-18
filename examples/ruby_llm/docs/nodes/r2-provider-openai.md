# OpenAI Adapter

**Capability.** Implements all OpenAI endpoints: chat payloads and parsing, media encoding, embeddings, images, moderation, models, streaming chunks, and audio transcription.

Read as the reference adapter; most other providers subclass or copy these mixins. Shared SSE handling comes from streaming-shared.

**Children.**

- [OpenAI-Derived Providers](r2-openai-derived-providers.md) `r2-openai-derived-providers` · 13 unit(s)

**Depends on.**

- [Content and Result Value Objects](r2-content-value-objects.md) · graph-confirmed · 1 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · graph-confirmed · 1 edge(s)
- [Attachments & Images](r1-content-media.md) · graph-only · 2 edge(s)
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-only · 1 edge(s)
- [OpenAI Tools](r1-openai-tools.md) · graph-only · 1 edge(s)

**Depended on by.**

- [OpenAI-Derived Providers](r2-openai-derived-providers.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-openai-derived-providers ` → ` r2-provider-openai `) · GPUStack, Ollama, and OpenRouter subclass the OpenAI adapter and override only deltas.
- [Provider Base and Registry](r2-provider-base.md) · graph-only · 2 edge(s)

Parent: [Provider Adapters](r2-providers.md)

## Units (14)

<a id="u-dd4454ea38ce"></a>
### `RubyLLM.Providers.OpenAI.Chat.render_payload`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil…` · [lib/ruby_llm/providers/openai/chat.rb:L14-L39][f1]

Assembles the OpenAI chat completion request body.

Always includes model.id, formatted messages, and the stream flag. Temperature is omitted when nil. When tools are present each is converted via tool_for. When a schema is given, strict defaults to true unless schema[:strict] == false, and a response_format of type 'json_schema' embeds the whole schema hash under name 'response'. When streaming, adds stream_options {include_usage: true}. The payload hash is returned unchanged otherwise; no error handling here.

uses: [RubyLLM.Providers.OpenAI.Tools.tool_for](r1-openai-tools.md#u-6b22fb38aebb); calls: [chat-rb-message-formatting](r2-provider-openai.md#u-1426a9e6f258)

<a id="u-04c9213bd74e"></a>
### `RubyLLM.Providers.OpenAI.Chat.parse_completion_response`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/openai/chat.rb:L41-L64][f1]

Converts an OpenAI chat completion HTTP response into a Message.

Reads response.body; returns nil when the body is empty. If data.dig('error','message') is present it raises Error.new(response, that message), so API errors surface before any message parsing. Otherwise it reads choices[0].message and returns nil if absent. Usage tokens come from data['usage'] (empty hash default): input from prompt_tokens, output from completion_tokens, cached_tokens from prompt_tokens_details.cached_tokens; cache_creation_tokens is hardcoded 0. Builds Message.new with role :assistant, content, tool_calls from parse_tool_calls, model_id from data['model'], and the raw response attached.

calls: [Message](r1-messaging-primitives.md#u-cb349e033cb3); uses: [RubyLLM.Providers.OpenAI.Tools.parse_tool_calls](r1-openai-tools.md#u-1fd3512688a5); raises: [RubyLLM.Error](../../catalog.json)

**Uncertainties.**

- The Error class here resolves to an OpenAI-namespaced error subclass; the exact class (e.g. BadRequestError vs generic) is not visible in this file.

<a id="u-1426a9e6f258"></a>
### `chat-rb-message-formatting`

`def format_messages(messages)` · [lib/ruby_llm/providers/openai/chat.rb:L66-L75][f1]

Formats outgoing chat messages.

format_messages maps each message to a role/content/tool_calls/tool_call_id hash and calls .compact, so nil tool_calls and nil tool_call_id are dropped; content is converted by Media.format_content, which can return a string or a parts array. format_role maps :system either to 'system' or 'developer' depending on @config.openai_use_system_role, an instance-variable read that implies this module is mixed into a class providing @config; all other roles are stringified via to_s.

**Notes.**

- condition: The system/developer role switch is driven entirely by the @config.openai_use_system_role truthiness.

calls: [RubyLLM.Providers.OpenAI.Media.format_content](r2-provider-openai.md#u-c58a518d68d9)

**Uncertainties.**

- format_role reads @config, so calling it outside a host object with @config set will raise NameError/NoMethodError; the host wiring is not in this file.

<a id="u-c58a518d68d9"></a>
### `RubyLLM.Providers.OpenAI.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/media.rb:L10-L34][f2]

Converts message content into OpenAI API form.

Early returns: RubyLLM::Content::Raw passes through its .value untouched; Hash/Array content is JSON-encoded to a string; anything not a Content is returned as-is. For a Content object it builds a parts array: a text part via format_text when content.text is truthy, then one part per attachment dispatched by type — :image→format_image, :pdf→format_pdf, :audio→format_audio, :text→format_text_file; any other type raises UnsupportedAttachmentError. Returns the parts array (or a single string for the early-return paths), so callers receive mixed string/array shapes depending on input kind.

**Notes.**

- failure: Unknown attachment types abort formatting with UnsupportedAttachmentError; earlier parts are discarded.

raises: [UnsupportedAttachmentError](../../catalog.json)

<a id="u-3f0c7386f0f6"></a>
### `media-rb-formatters`

`def format_image(image)` · [lib/ruby_llm/providers/openai/media.rb:L36-L43][f2]

Per-type attachment encoders for the OpenAI wire format.

format_image emits {type: 'image_url', image_url: {url: ...}} where the url is the attachment's own source when it already has a URL (image.url?), otherwise its for_llm representation (typically base64 data). format_pdf emits {type: 'file', file: {filename:, file_data: pdf.for_llm}}. format_text_file emits a {type: 'text', text: for_llm} part. format_audio emits {type: 'input_audio', input_audio: {data: audio.encoded, format: audio.format}}, relying on Attachment to base64-encode. format_text wraps a plain string as {type: 'text', text:}. All are pure transformations; nil/for_llm behavior depends on the Attachment class, not shown here.

<a id="u-798939f89625"></a>
### `embeddings-rb-embeddings`

`def embedding_url(...)` · [lib/ruby_llm/providers/openai/embeddings.rb:L10-L12][f3]

OpenAI embeddings endpoint plumbing.

embedding_url returns the relative path 'embeddings'. render_embedding_payload builds {model:, input:, dimensions:}.compact, so nil dimensions are omitted from the request. parse_embedding_response reads response.body, takes input_tokens from usage.prompt_tokens defaulting to 0, maps data entries to their 'embedding' vectors, and collapses to the first vector only when exactly one vector was returned and the input text was not an Array; it then constructs Embedding.new(vectors:, model:, input_tokens:). No error handling: a missing 'data' key would raise NoMethodError on nil.

**Notes.**

- condition: A single input string yields a bare vector; an Array input always yields an array of vectors even if length 1.

calls: [embedding.rb-embedding](r2-content-value-objects.md#u-0061f299adf1)

<a id="u-a146b2d8a0a5"></a>
### `images-rb-images`

`def images_url` · [lib/ruby_llm/providers/openai/images.rb:L10-L12][f4]

OpenAI image-generation endpoint plumbing.

images_url returns 'images/generations'. render_image_payload builds {model:, prompt:, n: 1, size:} — exactly one image per request, size passed through unvalidated. parse_image_response takes response.body['data'].first and constructs Image.new with url, a hardcoded mime_type 'image/png' (commented as a DALL-E assumption, so non-PNG responses are mislabeled), revised_prompt, the requested model id, and b64_json payload data. No nil/empty-data guard: an empty data array raises on first.

**Notes.**

- failure: parse_image_response assumes data['data'] is a non-empty array; nil or [] produces an exception from .first[] access.

calls: [Image](r1-content-media.md#u-5f36460b61e5)

<a id="u-e6ce8720a4a8"></a>
### `moderation-rb-moderation`

`def moderation_url` · [lib/ruby_llm/providers/openai/moderation.rb:L10-L12][f5]

OpenAI moderation endpoint plumbing.

moderation_url returns 'moderations'. render_moderation_payload builds {model:, input:}. parse_moderation_response reads response.body and raises Error.new(response, data.dig('error','message')) when an error message is present; otherwise it constructs RubyLLM::Moderation.new with the response 'id', the requested model, and results defaulting to [] when 'results' is missing. No other validation is performed.

raises: [RubyLLM.Error](../../catalog.json)

<a id="u-67c313e936c1"></a>
### `RubyLLM.Providers.OpenAI.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/openai/models.rb:L14-L35][f6]

Converts an OpenAI 'models' listing response into Model::Info records.

Wraps response.body['data'] in Array (so nil yields no entries) and maps each entry by its 'id'. Each record is enriched through the injected capabilities module: display name, family, context window, max output tokens, modalities, capabilities list, and pricing. created_at is Time.at(model_data['created']) when a created timestamp exists, else nil. Metadata preserves the raw 'object' and 'owned_by' fields. slug is recorded as the provider. Failure behavior depends on the capabilities methods, not this method.

uses: [capabilities-rb-family-and-pricing](r1-openai-core.md#u-1b26134a08d8)

**Uncertainties.**

- The capabilities argument is duck-typed; the code requires it to respond to format_display_name, model_family, context_window_for, max_tokens_for, modalities_for, capabilities_for, and pricing_for, but its concrete class is not in this file.

<a id="u-e4f6dc6fb46b"></a>
### `streaming-rb-streaming`

`def stream_url` · [lib/ruby_llm/providers/openai/streaming.rb:L10-L12][f7]

stream_url returns completion_url, so streaming reuses the chat completions endpoint path rather than a dedicated URL.

build_chunk and parse_streaming_error have their own units.

calls: [RubyLLM.Providers.OpenAI.Chat.completion_url][f1]

<a id="u-3d64a1bd4ad3"></a>
### `RubyLLM.Providers.OpenAI.Streaming.build_chunk`

`def build_chunk(data)` · [lib/ruby_llm/providers/openai/streaming.rb:L14-L28][f7]

Builds a Chunk from one OpenAI streaming SSE data payload.

Reads usage (empty-hash default) with cached_tokens from prompt_tokens_details.cached_tokens and cache_creation_tokens hardcoded 0. Content comes from choices[0].delta.content; tool calls from choices[0].delta.tool_calls parsed with parse_arguments: false, so streamed tool arguments stay as raw JSON strings rather than being decoded mid-stream. Role is fixed :assistant and model_id from data['model']. Missing keys simply yield nil fields.

calls: [Chunk](r2-streaming-shared.md#u-ec2920a443c8); uses: [RubyLLM.Providers.OpenAI.Tools.parse_tool_calls](r1-openai-tools.md#u-1fd3512688a5)

<a id="u-a1d118df8cf3"></a>
### `RubyLLM.Providers.OpenAI.Streaming.parse_streaming_error`

`def parse_streaming_error(data)` · [lib/ruby_llm/providers/openai/streaming.rb:L30-L42][f7]

Maps a raw streaming error body to an HTTP-style status/message pair.

Parses the input as JSON — malformed JSON raises from JSON.parse and propagates. If no 'error' key exists it returns nil (not an error). Otherwise it switches on error.type: 'server_error' → [500, message]; 'rate_limit_exceeded' or 'insufficient_quota' → [429, message]; any other type → [400, message]. The message always comes from error_data['error']['message'].

**Notes.**

- failure: Non-JSON input raises a JSON::ParserError from JSON.parse; only structurally valid payloads produce a status pair or nil.

<a id="u-18da718d7f6c"></a>
### `transcription-rb-payload`

`def render_transcription_payload(file_part, model:, language:, **options)` · [lib/ruby_llm/providers/openai/transcription.rb:L14-L27][f8]

Builds the audio transcription request payload and its helpers.

render_transcription_payload always includes model and file; other keys are dropped when nil via .compact. chunking_strategy defaults to 'auto' but is only emitted when supports_chunking_strategy? says so: false for models starting with 'whisper', true when the caller explicitly passed :chunking_strategy, otherwise only for model ids containing 'diarize'. response_format comes from options[:response_format] when the key is present (even if nil), otherwise 'diarized_json' for diarize models. known_speaker_references pass through encode_speaker_references, which returns nil for nil input and otherwise wraps each reference in Attachment.new(ref).for_llm, so unreadable references surface as Attachment errors.

**Notes.**

- condition: An explicit nil options[:response_format] suppresses the diarize default because the check is options.key?(:response_format).

calls: [attachment.rb-attachment](r1-content-media.md#u-f217f75f8a07)

<a id="u-81d580a2f867"></a>
### `RubyLLM.Providers.OpenAI.Transcription.parse_transcription_response`

`def parse_transcription_response(response, model:)` · [lib/ruby_llm/providers/openai/transcription.rb:L50-L66][f8]

Converts a transcription response into a RubyLLM::Transcription.

If response.body is a plain String (e.g. a simple text format), it returns Transcription.new(text: data, model:) with no other fields. Otherwise it reads usage (empty-hash default) and builds a record with text, language, duration, and segments from the body, taking input_tokens from usage['input_tokens'] or falling back to usage['prompt_tokens'], and output_tokens from usage['output_tokens'] or 'completion_tokens' — accommodating different usage key conventions. No error handling: a nil body that is not a String would raise on data['usage'].

**Uncertainties.**

- The two usage-key fallbacks imply multiple API response shapes, but which endpoints produce which shape is not visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/media.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/embeddings.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/images.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/moderation.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/models.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/streaming.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/transcription.rb