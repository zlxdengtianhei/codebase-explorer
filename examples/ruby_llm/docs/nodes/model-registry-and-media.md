# Model Registry And Media

**Capability.** Maintains model metadata registry and formats provider media or capability data for model resolution.

Observed units mix model collection lookup, filtering, resolution, and provider media/capability helpers. Use this module for registry operations and related provider formatting support.

**Depends on.**

- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 1 edge(s)
- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 1 edge(s)

Parent: [Provider Composition And Registry](provider-composition-and-registry.md)

## Units (16)

<a id="u-4a950ea59368"></a>
### `capabilities.rb-bedrock-capability-and-pricing-helpers`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L10-L15][f1]

These module functions derive model metadata, capability flags, and pricing from a Bedrock model ID using regex families and fixed tables.

Context window is 100,000 for IDs matching anthropic.claude-2, otherwise 200,000; max tokens is always 4,096. Chat, streaming, images, vision, functions, and JSON mode are true only when the ID matches anthropic.claude; audio and structured output are always false; model type is always 'chat'. Display name humanizes the ID by replacing hyphens, taking the segment after the last dot, splitting, capitalizing, and joining with spaces. Model family matches the first MODEL_FAMILIES regex or :other. Input/output price uses PRICES for that family or defaults 0.1/0.2. Modalities start text/text and add image and pdf input only for anthropic.claude IDs that also pass supports_vision?. Capabilities include streaming for anthropic.claude, function_calling when supports_functions?, reasoning for claude-3-7, and batch plus citations for claude-3.5 or claude-3-7. Pricing returns standard and half-price batch per-million text token prices, using defaults when family is absent.

<a id="u-39735cffa5f9"></a>
### `capabilities.rb-bedrock-provider-class-reopenings`

`class Bedrock # Determines capabilities and pricing for AWS Bedrock models` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L5-L7][f1]

The Bedrock provider class is reopened across the supplied files; these reopenings only nest provider modules and add no methods or mixins themselves.

The nested modules are Capabilities, Chat, Media, Models, Signing, and Streaming; the supplied source shows no include/extend of those modules into Bedrock, so how they are attached is not established. Streaming includes Base from a required file, but that does not mix Streaming into Bedrock.

<a id="u-b043a8b5556f"></a>
### `media.rb-bedrock-media-formatting`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/bedrock/media.rb:L13-L35][f2]

These module functions convert RubyLLM content and attachments into Anthropic-style Bedrock content blocks.

format_content returns raw content value unchanged; for Hash or Array it returns one formatted text block of JSON; for non-Content it returns one formatted text block; for Content it starts with text if present, then maps each attachment: image to base64 image block, pdf to base64 document block, text to Anthropic text-file block, and any other type raises UnsupportedAttachmentError with the type. format_image and format_pdf build base64 source hashes using the attachment MIME type and encoded data. The module extends Anthropic::Media, so helper methods come from that module; no URL attachment branch is present.

<a id="u-8382d615d802"></a>
### `media.rb-incoming-media-parsing`

`def build_response_content(parts) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/media.rb:L54-L75][f3]

Builds response content and attachments from Gemini response parts.

It collects text, inlineData, and fileData parts by index, joins text and nils it when empty, returns plain text when there are no attachments, and otherwise returns Content with text and attachments. Inline data is Base64-decoded into a binary StringIO and wrapped as an Attachment; ArgumentError during decoding logs a warning and yields nil. File data uses fileUri and an explicit filename or a generated one. Generated filenames use the index, map jpeg to jpg and plain to txt, and replace plus signs with dots.

<a id="u-f52b28ca0dbb"></a>
### `media.rb-media-content-formatting`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/media.rb:L10-L34][f4]

Formats content and attachments into OpenAI media parts.

Raw content returns its value; Hash or Array returns JSON; non-Content returns unchanged. Content becomes an array with a text part when text exists, then one part per attachment: image -> image_url using source when url? is true else for_llm; pdf -> file with filename and for_llm data; audio -> input_audio with encoded data and format; text -> text part with for_llm; any other attachment type raises UnsupportedAttachmentError with the type. The helper parts use the fixed type strings image_url, file, input_audio, and text.

<a id="u-39ec8714976f"></a>
### `media.rb-media-formatting`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/anthropic/media.rb:L10-L32][f5]

Formats Anthropic content parts.

Raw content returns its value; hashes and arrays become one JSON text part; non-content values become one text part; content objects emit optional text plus one part per attachment. Image and PDF attachments use URL source when available, otherwise base64 with mime type and encoded data; text attachments use for_llm text. Any other attachment type raises UnsupportedAttachmentError with the mime type.

<a id="u-88aa23229186"></a>
### `media.rb-outgoing-media-formatting`

`def format_content(content)` · [lib/ruby_llm/providers/gemini/media.rb:L10-L30][f3]

Formats chat content and attachments into Gemini parts.

Raw content returns its value; hashes and arrays become JSON text parts; non-Content values become text parts; Content emits its text when present and then each attachment as text-file, inline attachment, or raises UnsupportedAttachmentError for unknown attachment types. Inline attachments use inline_data with mime type and encoded data; text files use for_llm.

<a id="u-b6eda00a57a4"></a>
### `models.rb-bedrock-model-listing-and-parsing`

`def list_models` · [lib/ruby_llm/providers/bedrock/models.rb:L8-L17][f6]

These methods list Bedrock foundation models and convert Claude entries into Model::Info records.

list_models builds a management URL from @config.bedrock_region, signs a GET, fetches it with signature headers, and parses the response with slug and capabilities. parse_list_models_response reads modelSummaries as an array, keeps only modelId containing 'claude', and maps each to Model::Info using modelName or formatted display name, provider slug, family, nil created_at, capability-derived context/max tokens/modalities/capabilities/pricing, and metadata defaults for provider name, inference types, streaming, and input/output modalities. create_model_info builds a fixed Claude info record with family 'claude', 200,000 context, 4,096 max tokens, text-only modalities, empty capabilities/pricing/metadata, and ignores its capabilities argument. model_id_with_region returns the ID unchanged unless inferenceTypesSupported includes 'INFERENCE_PROFILE'; it also returns unchanged when that list includes 'ON_DEMAND'. Otherwise it computes the desired region prefix, returns unchanged if the ID already starts with that prefix, strips any leading two-lowercase-letter dot prefix, and prepends the desired prefix. inference_profile_region_prefix uses the first two characters of @config.bedrock_region, or 'us' when the region string is empty.

<a id="u-35e506d76217"></a>
### `models.rb-class-delegation`

`def method_missing(method, ...)` · [lib/ruby_llm/models.rb:L82-L88][f7]

Delegates unknown class methods to the singleton registry instance.

method_missing forwards when the instance responds, otherwise calls super; respond_to_missing? mirrors that check.

<a id="u-5c2a8698b78c"></a>
### `models.rb-instance-delegation`

`def refresh!(remote_only: false)` · [lib/ruby_llm/models.rb:L208-L210][f7]

Delegates instance refresh and resolve calls to the class methods.

<a id="u-c1567f9aa37c"></a>
### `models.rb-instance-storage`

`def initialize(models = nil)` · [lib/ruby_llm/models.rb:L156-L158][f7]

Stores a model collection and supports loading, saving, and enumeration.

initialize uses provided models or class.load_models. load_from_json! replaces @models with read_from_json. save_to_json writes pretty JSON of all.map(&:to_h). all returns @models; each delegates to all.each.

<a id="u-00e7142325dd"></a>
### `models.rb-model-filters`

`def chat_models` · [lib/ruby_llm/models.rb:L184-L186][f7]

Returns new Models collections filtered by type, modality, family, or provider.

chat_models selects type chat. embedding_models selects type embedding or output modalities including embeddings. audio_models selects type audio or output including audio. image_models selects type image or output including image. by_family compares family to a string; by_provider compares provider to a string.

<a id="u-75a1d5d16f1d"></a>
### `models.rb-model-lookup`

`def find(model_id, provider = nil)` · [lib/ruby_llm/models.rb:L176-L182][f7]

Finds a model by id, optionally constrained by provider, raising when absent.

find chooses the provider or non-provider path. find_with_provider resolves an alias, finds exact id/provider or resolved id/provider, otherwise raises ModelNotFoundError. find_without_provider finds exact id or alias-resolved id, otherwise raises ModelNotFoundError.

<a id="u-aa74e50b3b3f"></a>
### `models.rb-models-class`

`class Models` · [lib/ruby_llm/models.rb:L5-L8][f7]

Registry of model metadata with Enumerable access and class-level singleton operations.

Class methods delegate to a memoized instance via method_missing; instance methods filter and look up Model::Info records. Refresh and resolution coordinate providers and Parsera data.

<a id="u-44a159cd965f"></a>
### `models.rb-registry-loading`

`def instance` · [lib/ruby_llm/models.rb:L9-L11][f7]

Provides the singleton registry instance and loads model metadata from JSON.

instance memoizes new. schema_file returns the models_schema.json path. load_models calls read_from_json with the default config.model_registry_file. read_from_json reads the file if it exists or uses [], parses symbolized JSON, maps Model::Info.new, and returns [] on JSON::ParserError.

<a id="u-3dcbba4582dc"></a>
### `RubyLLM.Models.resolve`

`def resolve(model_id, provider: nil, assume_exists: false, config: nil) # rubocop:dis…` · [lib/ruby_llm/models.rb:L49-L80][f7]

Resolves a model id and provider into a model info object and provider instance.

It defaults config to RubyLLM.config and looks up an explicit provider in Provider.providers. If that provider class exists, it instantiates a temporary provider and forces assume_exists when the provider is local. In the assume_exists branch it requires a provider, raises Error for an unknown provider, instantiates it, tries Models.find for local providers while rescuing ModelNotFoundError, and falls back to Model::Info.default. In the non-assume branch it calls Models.find, then resolves the model's provider or raises Error if unregistered. An unknown explicit provider does not raise at the initial providers lookup; it returns nil, and the later path raises ModelNotFoundError or an unregistered-provider Error.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/media.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/media.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/media.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/media.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/models.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/models.rb
