# Attachment And Content Handling

**Capability.** Normalizes attachments, content, MIME types, source loading, encoding, and request formatting for LLM inputs.

Observed units show attachment and content value objects plus MIME classification. They include source normalization, lazy loading, base64/data URI formatting, and content wrappers.

**Depends on.**

- [Provider Transport And Streaming](provider-transport-and-streaming.md) · graph-confirmed · 2 edge(s) · Attachment and content handling uses provider transport and streaming for provider-facing content handling.
- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 1 edge(s)
- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Chat Persistence And Orchestration](chat-persistence-and-orchestration.md) · graph-confirmed · 4 edge(s) · Chat persistence and orchestration uses attachment and content handling to normalize chat content and attachments.
- [Provider Transport And Streaming](provider-transport-and-streaming.md) · graph-confirmed · 2 edge(s) · 1 inferred relation(s)
- [ActiveRecord Chat Persistence](activerecord-chat-persistence.md) · graph-only · 4 edge(s)
- [Media And Auxiliary Operations](media-and-auxiliary-operations.md) · graph-only · 2 edge(s)

Parent: [RubyLLM Multi-Provider Library](rubyllm-multi-provider-library.md)

## Units (16)

<a id="u-e43bf0509d6f"></a>
### `attachment.rb-attachment-class`

`class Attachment` · [lib/ruby_llm/attachment.rb:L5-L8][f1]

Represents a file attachment and normalizes its source, filename, and MIME type for later content access.

It distinguishes URL, path, IO-like, and ActiveStorage sources; content loading and MIME detection are delegated to private helpers and RubyLLM::MimeType. It exposes type predicates, LLM formatting, and a hash view. The class does not itself validate unsupported sources; content returns nil with a warning when no source branch matches.

<a id="u-2c145ce8f764"></a>
### `attachment.rb-content-loaders`

`def fetch_content` · [lib/ruby_llm/attachment.rb:L131-L134][f1]

Loads attachment bytes from URL, filesystem path, IO, or ActiveStorage.

URL loading uses Connection.basic.get and stores the response body; path loading uses File.read; IO loading rewinds when possible and reads; ActiveStorage loading downloads a Blob, an Attached::One blob, or the first Attached::Many blob, returning early unless ActiveStorage is defined.

<a id="u-19713985a4d5"></a>
### `attachment.rb-source-classification`

`def url?` · [lib/ruby_llm/attachment.rb:L16-L18][f1]

Classifies the normalized source as URL, path, IO-like, or ActiveStorage.

- url?: true for a URI or a String matching ^https?://.
- path?: true for a Pathname or a String that is not a URL.
- io_like?: true when the source responds to read and is neither a path nor ActiveStorage.
- active_storage?: false unless ActiveStorage is defined; true for Blob, Attached::One, or Attached::Many.

<a id="u-97786192c4ac"></a>
### `attachment.rb-source-normalization-and-filenames`

`def source_type_cast` · [lib/ruby_llm/attachment.rb:L160-L168][f1]

Casts sources to URI/Pathname and derives filenames and ActiveStorage content types.

source_type_cast uses URI for URLs, Pathname for paths, and leaves other sources unchanged. source_filename branches by URL, path, IO-like, or ActiveStorage. IO filenames use UploadedFile original_filename, a path basename, or attachment. ActiveStorage filenames use blob filenames or attachment fallbacks; active_storage_content_type reads Blob, Attached::One, or first Attached::Many content types.

<a id="u-03d8dc9ae103"></a>
### `attachment.rb-type-classification`

`def type` · [lib/ruby_llm/attachment.rb:L76-L84][f1]

Classifies MIME type into image, video, audio, pdf, text, or unknown and exposes matching predicates.

type checks image, video, audio, pdf, then text; the first true wins, otherwise :unknown. Each predicate delegates to RubyLLM::MimeType with the stored mime_type.

<a id="u-515477396b7a"></a>
### `content.rb-content-container`

`class Content` · [lib/ruby_llm/content.rb:L5-L8][f2]

Holds text and attachments for LLM content and normalizes attachment inputs.

Initialization stores text, starts with an empty attachment list, processes attachments, and raises ArgumentError only when text is nil and no attachments were added; an empty string with no attachments is accepted. Attachment processing treats a Hash by processing each value, otherwise processes the value directly; each value is coerced to a safe array and each item becomes an attachment. Adding an attachment appends a new attachment and returns self. Formatting returns the text only when text is truthy and there are no attachments, otherwise returns self. Serialization returns text plus each attachment's hash form.

calls: [Attachment#initialize](../../catalog.json.gz)

**Uncertainties.**

- Attachment construction and attachment hash behavior are outside this file.

<a id="u-df2ef9762db0"></a>
### `content.rb-raw-content-payload`

`class Raw` · [lib/ruby_llm/content.rb:L55-L58][f2]

Wraps a non-nil provider-specific payload that bypasses normal content formatting.

Initialization raises ArgumentError when the value is nil; formatting and serialization both return the stored value unchanged.

<a id="u-cdbd151dc55c"></a>
### `mime_type.rb-mime-type-helpers`

`def for(...)` · [lib/ruby_llm/mime_type.rb:L10-L12][f3]

Module functions that classify MIME type strings and delegate detection to Marcel.

Detection delegates to Marcel. Image, video, and audio predicates test the corresponding prefix. PDF tests exact equality with application/pdf, so nil returns false. Text is true when the type starts with text/, ends with a configured text suffix, or is in the configured non-text-prefix text MIME list. The prefix predicates call start_with? and therefore raise NoMethodError on nil.

calls: [MimeType.for](../../catalog.json.gz)

**Uncertainties.**

- Marcel::MimeType.for behavior is outside this file.

<a id="u-7e68832e7169"></a>
### `RubyLLM.Attachment.content`

`def content` · [lib/ruby_llm/attachment.rb:L36-L53][f1]

Returns attachment bytes, caching a non-nil @content and loading lazily by source kind.

It returns cached content first; otherwise it fetches URLs, reads paths, downloads ActiveStorage blobs, or reads IO-like sources. If no branch matches, it logs a warning and returns nil.

<a id="u-d16eafe20099"></a>
### `RubyLLM.Attachment.determine_mime_type`

`def determine_mime_type` · [lib/ruby_llm/attachment.rb:L123-L129][f1]

Determines and normalizes the attachment MIME type.

If ActiveStorage content type is present, it uses that; otherwise it asks RubyLLM::MimeType.for with nil for URLs or the source plus filename. If the result is application/octet-stream, it retries with content; audio/x-wav is normalized to audio/wav.

<a id="u-860d93fb86f6"></a>
### `RubyLLM.Attachment.encoded`

`def encoded` · [lib/ruby_llm/attachment.rb:L55-L57][f1]

Base64-encodes the attachment content with strict encoding.

It calls Base64.strict_encode64(content) directly; if content is nil, the supplied source provides no empty-string fallback and the encoder is expected to error.

<a id="u-31b7c203d852"></a>
### `RubyLLM.Attachment.for_llm`

`def for_llm` · [lib/ruby_llm/attachment.rb:L67-L74][f1]

Formats the attachment for an LLM request as inline text or a base64 data URI.

For type :text it emits a file tag containing filename, MIME type, and content; otherwise it emits data:mime;base64,encoded.

<a id="u-aac340b939aa"></a>
### `RubyLLM.Attachment.format`

`def format` · [lib/ruby_llm/attachment.rb:L98-L107][f1]

Maps MIME type to a short format name.

audio/mpeg becomes mp3; audio/wav, audio/wave, and audio/x-wav become wav; any other MIME type uses the segment after the slash.

<a id="u-939f637ad6f0"></a>
### `RubyLLM.Attachment.initialize`

`def initialize(source, filename: nil)` · [lib/ruby_llm/attachment.rb:L8-L14][f1]

Builds an attachment by storing the source, casting it to URI/Pathname when applicable, choosing a filename, and determining the MIME type.

The filename argument wins; otherwise source_filename is used. This constructor has no assume_model_exists parameter and raises no ArgumentError.

<a id="u-f3e4a8311466"></a>
### `RubyLLM.Attachment.save`

`def save(path)` · [lib/ruby_llm/attachment.rb:L59-L65][f1]

Copies an IO-like source to a destination path.

It returns nil unless io_like?. It opens the destination in write mode and calls puts on @source.read, so a newline is appended and the source IO is not rewound before reading.

<a id="u-0be8d55f3553"></a>
### `RubyLLM.Attachment.to_h`

`def to_h` · [lib/ruby_llm/attachment.rb:L117-L119][f1]

Returns a hash with the attachment type and source.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/attachment.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/content.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/mime_type.rb
