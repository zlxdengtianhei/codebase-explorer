# Gemini and media integrations

**Capability.** Implements Gemini chat, images, models, transcription, and media conversion, plus OpenAI image/transcription/model endpoints and shared utility helpers.

Visit for Gemini-specific request/response shaping (contents, schemas, tool declarations, streaming-friendly state) and for OpenAI-style image generation, transcription, and model listing. Also holds the Image value object and small pure helpers used across the gem. Gemini's schema and tool formatting differ enough from OpenAI to warrant dedicated converters here.

**Depends on.**

- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-confirmed · 1 edge(s)
- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-only · 2 edge(s)
- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 2 edge(s)
- [Streaming and result objects](streaming-and-result-objects.md) · graph-only · 2 edge(s)

**Depended on by.**

- [ActiveRecord persistence bridge](activerecord-persistence-bridge.md) · graph-only · 3 edge(s)
- [Tool definition and execution](tool-definition-and-execution.md) · graph-only · 3 edge(s)
- [Model info value objects](model-info-value-objects.md) · graph-only · 2 edge(s)

Parent: [Chat Wire and Media Formats](chat-wire-and-media-formats.md)

## Units (18)

<a id="u-634af1536e69"></a>
### `chat.rb-chat-payload-rendering`

`def completion_url` · [lib/ruby_llm/providers/gemini/chat.rb:L13-L15][f1]

Builds the Gemini generateContent request.

completion_url returns "models/{@model}:generateContent" where @model is set from the model argument in render_payload. render_payload formats messages via MessageFormatter, starts an empty generationConfig, sets temperature only when non-nil, merges structured_output_config when a schema is given, and adds tools via format_tools when any are present. The stream parameter is accepted but unused.

<a id="u-eba733af3a2f"></a>
### `chat.rb-completion-response-parsing`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/gemini/chat.rb:L63-L76][f1]

Parses a Gemini generateContent response into a Message.

parse_content returns '' when there is no candidate, when any part is a functionCall (tool-call-only turn), or when parts are empty; otherwise it builds content via build_response_content. calculate_output_tokens sums candidatesTokenCount and thoughtsTokenCount, defaulting each to 0. model_id prefers body['modelVersion'], falling back to parsing the request URL path segment before the colon. input_tokens comes from usageMetadata.promptTokenCount.

<a id="u-e32292e71662"></a>
### `chat.rb-geminischema-converter`

`class GeminiSchema` · [lib/ruby_llm/providers/gemini/chat.rb:L250-L251][f1]

Converts a JSON schema into Gemini's native schema format.

to_h returns nil for a nil schema; otherwise it deep-dups the input, recursively symbolizes keys while extracting $defs/definitions into a merged definitions store, then converts. convert: non-Hash schemas become a bare STRING type; strict and additionalProperties keys are stripped; $ref is resolved from the definitions store (with cycle protection via a visited set that is cleaned up in ensure), merging non-ref keys as overrides; anyOf is normalized by picking the first non-null option and setting nullable when a null option existed (defaulting to string type if all options are null). Types map to OBJECT/ARRAY/NUMBER/INTEGER/BOOLEAN/STRING, with the else branch catching string and unknown types as STRING. Objects convert properties recursively, include required (stringified, uniq) when present, copy propertyOrdering and nullable; arrays convert items (defaulting to STRING when absent) and copy minItems/maxItems/nullable; scalars copy only their allowed keys (e.g. enum/format/nullable for strings, minimum/maximum/multipleOf for numbers). A description is copied to the result when present. lookup_definition walks the ref path (skipping a leading # and $defs/definitions segment) and returns a deep copy, or nil on a missing path.

<a id="u-9e7783c98221"></a>
### `chat.rb-message-and-part-formatting`

`def format_messages(messages)` · [lib/ruby_llm/providers/gemini/chat.rb:L34-L42][f1]

Converts the conversation into Gemini contents.

format_messages delegates to MessageFormatter with role/part/tool-result callables. format_role maps :assistant to 'model', :system to 'user', :tool to 'function', else the role as string. format_parts dispatches per message: tool_call messages go to format_tool_call, tool_result messages to format_tool_result, otherwise Media.format_content renders the content.

<a id="u-dda98d99e889"></a>
### `chat.rb-messageformatter`

`class MessageFormatter` · [lib/ruby_llm/providers/gemini/chat.rb:L175-L176][f1]

Stateful formatter that walks the message list, grouping consecutive :tool messages into single 'function'-role responses.

format loops: for a tool message it collects all consecutive tool messages, resolving each tool_call_id against names remembered from earlier assistant tool-call messages (deleted from the map on use, so a missing id yields a nil tool name passed to the format callback), and emits one {role:'function', parts:[...]} entry; otherwise it records tool-call id-to-name pairs when the message has tool calls and emits a standard {role, parts} entry via the injected callables. The injected format_role/format_parts/format_tool_result callables come from the Chat module, keeping this class provider-agnostic. Index advances by one for standard messages and past the tool run for grouped ones.

<a id="u-3bb5188e4571"></a>
### `chat.rb-structured-output-configuration`

`def convert_schema_to_gemini(schema)` · [lib/ruby_llm/providers/gemini/chat.rb:L78-L82][f1]

Decides how JSON schema constraints are sent.

structured_output_config always sets responseMimeType to application/json; if the model's extracted Gemini version is >= 2.5 it sends the raw JSON schema (deep-duplicated, strict keys removed, stringified keys) as responseJsonSchema, otherwise it converts via GeminiSchema into Gemini's native schema format under responseSchema. gemini_version tries the model id, family, metadata version (symbol and string keys), and description in order, extracting the first decimal or integer match into a Gem::Version; extract_version rescues ArgumentError and returns nil, so unparseable matches are skipped. response_json_schema_supported? is false when no version can be determined.

<a id="u-639ed55c69c8"></a>
### `image.rb-generated-image`

`class Image` · [lib/ruby_llm/image.rb:L5-L8][f2]

Represents an image produced by a model, holding url, base64 data, mime_type, revised_prompt, and model_id.

base64? is true when data is present. to_blob decodes Base64 data when present, otherwise performs an HTTP GET on the url via Connection.basic and returns the response body. save expands the path, binary-writes the blob, and returns the given path. The class method paint resolves configuration (context's config or the global one), defaults the model to config.default_image_model, resolves model and provider via Models.resolve, and delegates to provider_instance.paint with the model id and size (default '1024x1024'), returning its result.

calls: [Connection.basic](../../catalog.json.gz), [Models.resolve](../../catalog.json.gz)

**Uncertainties.**

- Connection.basic and provider_instance.paint behavior is outside this batch; network errors from to_blob propagate unhandled here.

<a id="u-5339e6e6cef7"></a>
### `images.rb-image-generation`

`def images_url` · [lib/ruby_llm/providers/gemini/images.rb:L8-L10][f3]

Gemini image generation via the predict endpoint.

images_url is "models/{@model}:predict"; render_image_payload sets @model from the model argument, logs a debug message that the size parameter is ignored, and returns one instance with the prompt and sampleCount 1. parse_image_response takes the first prediction and raises Error unless it contains bytesBase64Encoded; otherwise it returns an Image with the base64 data, mimeType (defaulting to image/png), and the model id.

<a id="u-71843b1d42a2"></a>
### `images.rb-image-generation-2`

`def images_url` · [lib/ruby_llm/providers/openai/images.rb:L10-L12][f4]

OpenAI image generation integration: url 'images/generations'; payload {model, prompt, n: 1, size}.

Parsing takes the first entry of data and builds an Image with its url, hardcoded mime_type 'image/png', optional revised_prompt, the requested model id, and b64_json data. Assumes data is non-empty; a missing first element would raise NoMethodError.

<a id="u-ed23d0614d5a"></a>
### `media.rb-inbound-response-content`

`def build_response_content(parts) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/media.rb:L54-L75][f5]

Rebuilds Content from Gemini response parts.

build_response_content collects text parts and inlineData/fileData attachments in order; joined text becomes nil when empty, and the method returns bare text when there are no attachments, otherwise a Content with text and attachments. build_inline_attachment decodes base64 data into a binary StringIO Attachment, returning nil when data is absent or decoding raises ArgumentError (logged as a warning). build_file_attachment wraps the fileUri in an Attachment, using the response filename or a mime-derived one. attachment_filename derives an extension from the mime subtype, mapping jpeg to jpg and plain to txt and turning '+' into '.', yielding e.g. gemini_attachment_1.png; without a mime type it omits the extension.

<a id="u-5ca5a4f3b2e7"></a>
### `media.rb-outbound-media-formatting`

`def format_content(content)` · [lib/ruby_llm/providers/gemini/media.rb:L10-L30][f5]

Converts message content into Gemini request parts.

Raw content passes through its value; Hash/Array content is serialized to JSON and sent as a text part; non-Content objects are sent as text. For Content objects, a text part is added when text is present, then each attachment: :text type becomes {text: for_llm}, :unknown raises UnsupportedAttachmentError with the mime type, and anything else becomes inline_data with mime_type and base64-encoded data.

<a id="u-e68aea834497"></a>
### `models.rb-model-listing`

`def models_url` · [lib/ruby_llm/providers/gemini/models.rb:L10-L12][f6]

Parses the Gemini list-models response into Model::Info records.

Each entry's name has the models/ prefix stripped to form the id; context window and max output tokens prefer the API's inputTokenLimit/outputTokenLimit and fall back to the capabilities module's pattern-based values. Family, modalities, capabilities, and pricing come from the passed capabilities module; created_at is always nil; metadata carries version, description, and supportedGenerationMethods.

<a id="u-d4af1bd9d00e"></a>
### `models.rb-model-listing-2`

`def models_url` · [lib/ruby_llm/providers/openai/models.rb:L10-L12][f7]

OpenAI models listing: url 'models'.

parse_list_models_response takes the response body's 'data' array (Array() tolerates nil by yielding nothing) plus a provider slug and a capabilities object, and maps each entry to a Model::Info with the API id, display name, family, context window, max output tokens, modalities, capabilities and pricing all computed by delegating to the passed capabilities module, created_at from the epoch 'created' field (nil when absent), and metadata carrying object/owned_by.

<a id="u-22d8bb1e49ac"></a>
### `tools.rb-tool-call-formatting-and-extraction`

`def format_tools(tools)` · [lib/ruby_llm/providers/gemini/tools.rb:L8-L14][f8]

Formats tool traffic for Gemini and parses tool calls from responses.

format_tools returns [] when empty, else one declaration group. format_tool_call emits content parts first (when content is present and non-empty), then one functionCall part per tool call with name and raw args. format_tool_result wraps content in a functionResponse, defaulting the function name to the tool_call_id when none is given. extract_tool_calls scans the first candidate's parts for functionCall entries, assigning a SecureRandom uuid id to each and defaulting args to {}; returns nil when there is no candidate, parts isn't an array, or no function calls were found.

<a id="u-6a75b341b6a8"></a>
### `tools.rb-tool-schema-conversion`

`def function_declaration_for(tool)` · [lib/ruby_llm/providers/gemini/tools.rb:L77-L91][f8]

Converts tool parameter schemas into Gemini's declaration format.

function_declaration_for builds {name, description} plus converted parameters, falling back to deriving a schema from the tool's parameters; provider_params are deep-merged over the declaration when present. convert_tool_schema_to_gemini stringifies keys and raises ArgumentError unless the top-level type is 'object'; it emits OBJECT with converted properties and stringified required. convert_property normalizes anyOf (single non-null option wins, nullable set when a null option existed, all-null becomes nullable string), maps types to Gemini's uppercase forms (integer/number/boolean/array/object, else STRING), copies description/enum/format/nullable/maximum/minimum/multipleOf from both the normalized and original schemas, recurses for ARRAY items (defaulting to string) and OBJECT properties with minItems/maxItems copied for arrays. schema_value tolerates string, symbol, and snake_case key variants for multipleOf and the item-count attributes.

<a id="u-80a0118903cd"></a>
### `transcription.rb-audio-transcription`

`def transcription_url` · [lib/ruby_llm/providers/openai/transcription.rb:L10-L12][f9]

OpenAI transcription integration against 'audio/transcriptions'.

render_transcription_payload builds {model, file, language, chunking_strategy, response_format, prompt, temperature, timestamp_granularities, known_speaker_names, known_speaker_references} with nils compacted. chunking_strategy defaults to 'auto' but only when supports_chunking_strategy? holds: whisper models never get it, an explicitly passed option always allows it, and otherwise only diarize models do. response_format_for honors an explicit :response_format option, else returns 'diarized_json' for diarize models, else nil. encode_speaker_references returns nil without references, otherwise maps each to an Attachment and takes its for_llm form. parse_transcription_response handles plain-string bodies (some formats return raw text) by wrapping them in a Transcription with just text and model; object bodies populate language, duration, segments, and token counts reading usage.input_tokens/prompt_tokens and output_tokens/completion_tokens with fallbacks between the two key styles.

<a id="u-64ecaa05ac6c"></a>
### `transcription.rb-transcription`

`def transcribe(audio_file, model:, language:, **options)` · [lib/ruby_llm/providers/gemini/transcription.rb:L10-L15][f10]

Transcribes audio through Gemini's generateContent endpoint.

transcribe wraps the file in an Attachment, renders the payload, POSTs via @connection, and parses the response into a RubyLLM::Transcription. render_transcription_payload builds a user message with the prompt and an inline_data audio part, raising UnsupportedAttachmentError when the attachment is not audio; it adds generationConfig (responseMimeType defaulting to text/plain, optional temperature and maxOutputTokens) only when non-empty, and passes safety_settings through when given. build_prompt starts from the constant default, appends a language instruction when a language is given, then any custom prompt. Parsing extracts joined text parts from the first candidate (nil when none) and usage from promptTokenCount plus candidates+thoughts token counts, defaulting to nils when usageMetadata is absent.

<a id="u-907fb557c5e2"></a>
### `utils.rb-data-utilities`

`def hash_get(hash, key)` · [lib/ruby_llm/utils.rb:L8-L10][f11]

Small pure helpers.

hash_get reads a key trying symbol then string form, returning nil/first falsy value otherwise. to_safe_array returns Arrays as-is, wraps a Hash in a one-element array, and otherwise uses Array(item) (so nil becomes []). to_time/to_date return nil for nil input, pass through Time/Date instances, and otherwise parse the stringified value (raising on unparseable input). deep_merge recursively merges hashes, with override values winning on conflicts and non-hash conflicts taking the override wholesale; it does not mutate the original. deep_dup recursively duplicates Hash keys and values and Array items, falling back to value.dup and rescuing TypeError to return the value itself (so immediates like nil/Integer/symbols survive). deep_stringify_keys recursively converts hash keys and standalone symbols to strings, mapping arrays; deep_symbolize_keys symmetrically converts keys via to_sym when the key responds to it, leaving other keys and arrays' contents otherwise intact. Neither stringify/symbolize mutates input.

**Notes.**

- contract: deep_merge assumes the first argument is a Hash; a non-Hash would raise NoMethodError.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/image.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/images.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/images.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/media.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/models.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/models.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/tools.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/transcription.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/transcription.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/utils.rb
