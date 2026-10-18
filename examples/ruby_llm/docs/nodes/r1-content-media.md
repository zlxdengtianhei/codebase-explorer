# Attachments & Images

**Capability.** Loads and classifies user-supplied content (paths, URLs, IO objects, ActiveStorage) and represents generated images; MIME detection delegates to the Marcel gem.

Use Attachment to normalize any input into LLM-consumable form; Image models generated output as base64 data or URL. MimeType helpers centralize type detection.

**Depends on.**

- [Shared Utilities](r1-shared-utilities.md) · model-inferred · 0 edge(s)
- [Provider Connection](r2-connection.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Gemini Embeddings & Images](r1-gemini-embeddings-images.md) · graph-confirmed · 1 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · graph-only · 2 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 1 edge(s)
- [Gemini Adapter](r2-provider-gemini.md) · graph-only · 1 edge(s)

Parent: [Conversation Core](r1-conversation-core.md)

## Units (3)

<a id="u-f217f75f8a07"></a>
### `attachment.rb-attachment`

`def initialize(source, filename: nil)` · [lib/ruby_llm/attachment.rb:L8-L14][f1]

Loads and classifies a user-supplied file path, URL, IO-like object, or ActiveStorage attachment and renders it for LLM consumption.

initialize casts the source (URI for http(s) strings, Pathname for paths), derives a filename, and determines the MIME type. Type predicates delegate to RubyLLM::MimeType against the resolved mime_type; type returns :image/:video/:audio/:pdf/:text in that priority order, else :unknown. content lazily loads in this order: URL (via Connection.basic GET, response body), path (File.read), ActiveStorage, IO-like (rewind if possible then read); for an unrecognized source it logs a warning and returns nil. for_llm wraps text in a <file> XML tag, other types become data:...;base64 via encoded (Base64 of content). determine_mime_type prefers ActiveStorage content type when present, sniffs content when MimeType.for returns application/octet-stream, and normalizes audio/x-wav to audio/wav. format maps audio mpeg/wav variants to 'mp3'/'wav', otherwise the MIME subtype. ActiveStorage branches handle Blob, Attached::One, and Attached::Many (first blob only) and are no-ops guarded when ActiveStorage is not defined; filename extraction falls back to 'attachment'. save writes IO-like sources to a path with File.puts (adds a trailing newline).

**Notes.**

- side_effect: fetch_content performs an HTTP GET through Connection.basic, whose raise_error middleware turns failed responses into exceptions
- condition: Attachment::Many attachments only use the first blob's content, filename, and content type

uses: [connection.rb-connection](r2-connection.md#u-53be52e4979e); group: [attachment.rb-attachment](r1-content-media.md#u-f217f75f8a07)

**Uncertainties.**

- save uses f.puts, which appends a newline not present in the source bytes; whether callers compensate is not visible

<a id="u-5f36460b61e5"></a>
### `Image`

`class Image` · [lib/ruby_llm/image.rb:L5-L8][f2]

Represents a generated image delivered either as base64 data or a URL.

`base64?` is true only when `data` is non-nil. `to_blob` returns `Base64.decode64(data)` for base64 images; otherwise it GETs `url` through `Connection.basic` and returns the response body, so a missing or unreachable URL surfaces as a network error. `save(path)` expands the path, binwrites the blob, and returns the original path argument. Class method `paint(prompt, model:, provider:, assume_model_exists:, size:, context:)` picks the context config or global `RubyLLM.config`, defaults the model to `config.default_image_model`, resolves it via `Models.resolve(...)` (which also yields the provider instance), then calls `provider_instance.paint(prompt, model: model_id, size:)` and returns that result; resolve failures propagate uncaught.

<a id="u-5bc6e18ed033"></a>
### `mime_type-mime-type-helpers`

`def for(...)` · [lib/ruby_llm/mime_type.rb:L10-L12][f3]

Module-function helpers over MIME type strings, delegating detection to the Marcel gem where needed.

`for(...)` passes all arguments straight through to `Marcel::MimeType.for`, so its inputs, guessing behavior, and exceptions follow Marcel. The predicate helpers test a given type string: `image?`, `video?`, and `audio?` match their respective `type/` prefixes; `pdf?` matches exactly 'application/pdf'. `text?` is true when the type starts with 'text/', ends with one of the TEXT_SUFFIXES (+json, +xml, +html, +yaml, +csv, +plain, +javascript, +svg), or is listed in NON_TEXT_PREFIX_TEXT_MIME_TYPES (application/json, application/xml, JavaScript-family, script/config formats like yaml, toml, python, shell, and others) — so both suffixed structured types and these text-like application types count as text. All predicates assume the argument is a String and would raise NoMethodError on nil.

uses: [lib/ruby_llm/mime_type.rb:MimeType][f3]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/attachment.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/image.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/mime_type.rb