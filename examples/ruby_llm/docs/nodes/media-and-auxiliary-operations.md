# Media And Auxiliary Operations

**Capability.** Handles aliases, images, moderation, transcription, model listing, and Rails integration entrypoints.

Observed units show non-chat operations such as image generation, moderation, transcription, aliases, and model listing. They include value objects and provider-specific request/response helpers.

**Depends on.**

- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-only · 2 edge(s)
- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 2 edge(s)

Parent: [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md)

## Units (12)

<a id="u-2dffedbe942e"></a>
### `aliases.rb-model-alias-resolution`

`class Aliases` · [lib/ruby_llm/aliases.rb:L5-L6][f1]

Class-level model alias resolver backed by a JSON file and memoized hash.

Resolution returns the input model id when no alias entry exists; with a provider it returns that provider's alias or the input, and without a provider it returns the first alias value or the input. The alias map is loaded once and memoized; the file path is aliases.json beside the source, and a missing file yields an empty hash. Reloading replaces the memoized map with a fresh load.

calls: [aliases.rb-model-alias-resolution](media-and-auxiliary-operations.md#u-2dffedbe942e)

**Uncertainties.**

- JSON parse and file read errors are not rescued; the alias file shape is inferred from resolve.

<a id="u-639ed55c69c8"></a>
### `image.rb-generated-image`

`class Image` · [lib/ruby_llm/image.rb:L5-L8][f2]

Represents a generated image and provides blob retrieval, saving, and class-level paint entrypoint.

Initialization stores url, data, MIME type, revised prompt, and model id. Base64 detection is true whenever data is non-nil. Blob retrieval decodes data when base64, otherwise fetches the URL through the basic connection and returns the response body. Saving writes the blob to the expanded path and returns the original path. Painting uses the context config or global config, defaults the model to the configured image model, resolves the model and provider, then calls the provider's paint with the resolved model id and size.

calls: [Connection.basic.get](../../catalog.json.gz), [Models.resolve](../../catalog.json.gz), [provider paint](../../catalog.json.gz)

**Uncertainties.**

- Connection.basic and provider paint behavior are outside this file.

<a id="u-5339e6e6cef7"></a>
### `images.rb-image-generation`

`def images_url` · [lib/ruby_llm/providers/gemini/images.rb:L8-L10][f3]

Builds Gemini image-generation requests and parses image responses.

The URL targets predict. Rendering logs that size is ignored, stores the model, and sends one prompt instance with sampleCount 1. Parsing takes the first prediction, raises an Error when bytesBase64Encoded is absent, defaults mime type to image/png, and returns an Image with data, mime type, and model id.

<a id="u-7a75bb88a70e"></a>
### `images.rb-image-payload-and-response`

`def render_image_payload(prompt, model:, size:)` · [lib/ruby_llm/providers/openai/images.rb:L14-L21][f4]

Builds image-generation payloads and parses image responses.

The payload contains model, prompt, n fixed at 1, and size. Parsing takes the first data element and constructs an Image with its url, mime type image/png, revised_prompt, model id, and b64_json data; it does not guard against a missing data element.

<a id="u-e68aea834497"></a>
### `models.rb-model-listing`

`def models_url` · [lib/ruby_llm/providers/gemini/models.rb:L10-L12][f5]

Builds the Gemini models URL and maps listed models to Model::Info records.

The URL is models. Parsing maps the response models array, strips models/ from each id, and fills name, provider, family, nil creation time, context window and max output tokens from API limits or capability fallbacks, modalities, capabilities, pricing, and metadata for version, description, and supported generation methods.

<a id="u-0f295539dd8a"></a>
### `moderation.rb-moderation-result-and-entrypoint`

`class Moderation` · [lib/ruby_llm/moderation.rb:L6-L9][f6]

Stores moderation results and provides a class-level moderation entrypoint.

Initialization stores id, model, and results. Moderation uses the context config or global config, defaults the model to the configured moderation model or omni-moderation-latest, resolves the model and provider, then calls the provider's moderate with the resolved model id. Content returns the results. Flagged detection is true when any result's flagged value is truthy. Flagged categories collect truthy category keys from each result, treating missing categories as empty, and remove duplicates. Category scores and categories return the first result's value or an empty hash.

calls: [Models.resolve](../../catalog.json.gz), [provider moderate](../../catalog.json.gz)

**Uncertainties.**

- Provider moderate and model resolution behavior are outside this file.

<a id="u-80a0118903cd"></a>
### `transcription.rb-audio-transcription`

`def transcribe(audio_file, model:, language:, **options)` · [lib/ruby_llm/providers/gemini/transcription.rb:L10-L15][f7]

Sends audio to Gemini for transcription and parses transcript text and usage.

It wraps the audio, renders a payload, posts to generateContent, and parses the response. Payload rendering raises UnsupportedAttachmentError unless the attachment is audio, builds a prompt plus inline audio part, adds generation config when non-empty, and adds safety settings when provided. The prompt starts with the default transcription prompt, appends a language sentence when language is given, and appends a custom prompt when present. Response parsing joins text parts when any exist and returns input/output token counts, with output summing candidate and thought tokens.

<a id="u-481d5e64d0a5"></a>
### `transcription.rb-transcription-payload-construction`

`def render_transcription_payload(file_part, model:, language:, **options)` · [lib/ruby_llm/providers/openai/transcription.rb:L14-L27][f8]

Builds the transcription request payload and its option helpers.

The payload includes model, file, language, response_format, prompt, temperature, timestamp_granularities, known_speaker_names from speaker_names, and known_speaker_references from encoded speaker references, with nil values removed. Chunking strategy is included only when supported: whisper models return false before checking options, so an explicitly passed chunking_strategy is not allowed for whisper; otherwise an explicit option allows it, and diarize models default to auto. Response format uses an explicit option when present, otherwise diarized_json for diarize models. Speaker references map each reference through Attachment.for_llm, or nil when absent.

<a id="u-5b9674473133"></a>
### `transcription.rb-transcription-result-and-entrypoint`

`class Transcription` · [lib/ruby_llm/transcription.rb:L5-L8][f9]

Stores transcription output and provides a class-level transcription entrypoint.

Initialization stores text and model, plus optional language, duration, segments, input tokens, and output tokens; unknown attributes are ignored. Transcription extracts model, language, provider, assume-model-exists defaulting to false, and context from keywords, leaving the rest as options. It uses the context config or global config, defaults the model to the configured transcription model, resolves the model and provider, then calls the provider's transcribe with the resolved model id, language, and remaining options.

calls: [Models.resolve](../../catalog.json.gz), [provider transcribe](../../catalog.json.gz)

**Uncertainties.**

- Provider transcribe and model resolution behavior are outside this file.

<a id="u-67c313e936c1"></a>
### `RubyLLM.Providers.OpenAI.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/openai/models.rb:L14-L35][f10]

Maps the response data array into Model::Info records.

For each model it uses the id, display name, provider slug, family, created_at from Time.at when created is present, context window, max output tokens, modalities, capabilities, pricing, and metadata object/owned_by. A missing data value becomes an empty array through Array(), so no records are produced.

<a id="u-81d580a2f867"></a>
### `RubyLLM.Providers.OpenAI.Transcription.parse_transcription_response`

`def parse_transcription_response(response, model:)` · [lib/ruby_llm/providers/openai/transcription.rb:L50-L66][f8]

Parses a transcription response into a Transcription.

A string body is treated as plain text and returned with the model. Otherwise it reads text, language, duration, segments, and usage token counts, preferring input_tokens/output_tokens and falling back to prompt_tokens/completion_tokens.

<a id="u-acb5d0270dbf"></a>
### `Railtie`

`class Railtie < Rails::Railtie` · [lib/ruby_llm/railtie.rb:L6-L33][f11]

Rails integration class defined only when Rails::Railtie is available.

It registers an inflections initializer that adds the RubyLLM acronym. Its active-record initializer runs on the active_record load hook: when new acts-as is enabled it requires the new implementation and includes it; otherwise it requires the legacy implementation, includes it, and logs a deprecation warning. It also registers a rake task that loads tasks/ruby_llm.rake.

**Uncertainties.**

- Initializer execution order and Rails load-hook behavior are outside this file.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/aliases.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/image.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/images.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/images.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/models.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/moderation.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/transcription.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/transcription.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/transcription.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/models.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/railtie.rb
