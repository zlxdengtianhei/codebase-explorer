# Attachment Normalization and MIME

**Capability.** Wraps files from URLs, paths, IO objects, or ActiveStorage into a uniform attachment with derived filename, MIME type, and LLM-ready rendering.

Come here when user-supplied files must be prepared for LLM requests. It normalizes diverse sources, lazily loads bytes, classifies type via MIME helpers, and renders text or base64 data-URI payloads.

**Depends on.**

- [Streaming and Provider Core](streaming-and-provider-core.md) · graph-confirmed · 1 edge(s) · Attachment normalization prepares file content for rendering into provider requests.
- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Persistence and Conversation Layer](persistence-and-conversation-layer.md) · graph-confirmed · 1 edge(s)
- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 2 edge(s)
- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 2 edge(s)
- [ActiveRecord persistence bridge](activerecord-persistence-bridge.md) · graph-only · 1 edge(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Units (14)

<a id="u-f217f75f8a07"></a>
### `attachment.rb-attachment`

`class Attachment` · [lib/ruby_llm/attachment.rb:L5-L8][f1]

Wraps a file attachment from a URL, path, IO-like object, or ActiveStorage record, normalizing the source and deriving filename and MIME type at construction.

initialize casts the source via source_type_cast (URL strings become URI, path-like strings become Pathname, others pass through), sets filename from the explicit argument or source_filename, then calls determine_mime_type. Raises ArgumentError if assume_model_exists... (not applicable here); URI() may raise for malformed URL strings.

<a id="u-8ac152b8a4a4"></a>
### `attachment.rb-content-loading`

`def content` · [lib/ruby_llm/attachment.rb:L36-L53][f1]

Lazily loads and memoizes the attachment's bytes, dispatching on source type: URL sources are fetched via Connection.basic.get (network side effect, Faraday raise_error middleware may throw on HTTP errors); paths via File.read; ActiveStorage via download (Blob directly, Attached::One via blob, Attached::Many takes the first blob, nil-safe); IO-like sources are rewound when possible then read.

Unrecognized sources log a warning and yield nil content. Subsequent calls return the memoized @content.

<a id="u-928218d62a27"></a>
### `attachment.rb-filename-derivation`

`def source_filename` · [lib/ruby_llm/attachment.rb:L170-L180][f1]

source_filename derives a filename per source type: URL uses the URI path basename; Pathname its basename; IO-like objects use original_filename for Rails uploaded files, File.basename of #path when available, else 'attachment'; ActiveStorage uses the blob's filename (first blob for Attached::Many), falling back to 'attachment'.

Returns nil for unrecognized sources.

<a id="u-db0f151d594d"></a>
### `attachment.rb-source-type-predicates`

`def url?` · [lib/ruby_llm/attachment.rb:L16-L18][f1]

Classify @source: url?

is true for URI or http(s):// strings; path? for Pathname or any non-URL string; io_like? for objects responding to read that are neither path-like nor ActiveStorage; active_storage? checks Blob/Attached::One/Attached::Many only when ActiveStorage is defined, else false.

<a id="u-03d8dc9ae103"></a>
### `attachment.rb-type-classification`

`def type` · [lib/ruby_llm/attachment.rb:L76-L84][f1]

type maps the MIME type to a symbol in priority order image, video, audio, pdf, text, else :unknown, delegating each predicate to RubyLLM::MimeType.

The individual predicates simply ask MimeType for the current mime_type.

<a id="u-cdbd151dc55c"></a>
### `mime_type.rb-mime-type-helpers`

`def for(...)` · [lib/ruby_llm/mime_type.rb:L10-L12][f2]

Thin wrappers over Marcel plus category predicates.

for forwards everything to Marcel::MimeType.for. image?, video?, and audio? test the 'image/', 'video/', 'audio/' prefixes respectively; pdf? tests exact 'application/pdf'. text? is true for 'text/' prefixes, for types ending in one of the structured suffixes (+json, +xml, +html, +yaml, +csv, +plain, +javascript, +svg), or for an explicit allowlist of non-text-prefixed types (JSON, XML, JavaScript, shell, YAML, TOML, PGP, etc.). All predicates assume a String and would raise NoMethodError on nil.

calls: [MimeType.for](../../catalog.json)

<a id="u-ecbfe1c4291d"></a>
### `RubyLLM.Attachment.active_storage_content_type`

`def active_storage_content_type` · [lib/ruby_llm/attachment.rb:L207-L218][f1]

Extracts the ActiveStorage content_type: Blob directly, Attached::One via its blob, Attached::Many from the first blob; nil when ActiveStorage is undefined or the source is none of these.

<a id="u-d16eafe20099"></a>
### `RubyLLM.Attachment.determine_mime_type`

`def determine_mime_type` · [lib/ruby_llm/attachment.rb:L123-L129][f1]

Sets @mime_type: ActiveStorage sources use their stored content_type when present; otherwise MimeType.for is called with the source (nil for URLs) and filename, falling back to sniffing from content when the result is application/octet-stream; audio/x-wav is normalized to audio/wav.

The content-sniffing fallback triggers content loading (network or file read) as a side effect.

<a id="u-860d93fb86f6"></a>
### `RubyLLM.Attachment.encoded`

`def encoded` · [lib/ruby_llm/attachment.rb:L55-L57][f1]

Returns the content Base64-encoded (strict_encode64); nil content propagates through encode64 as an empty string.

<a id="u-31b7c203d852"></a>
### `RubyLLM.Attachment.for_llm`

`def for_llm` · [lib/ruby_llm/attachment.rb:L67-L74][f1]

Renders the attachment for an LLM: text type yields an XML-ish <file> tag with name and mime_type wrapping the raw content; all other types yield a data URI with base64 content.

<a id="u-aac340b939aa"></a>
### `RubyLLM.Attachment.format`

`def format` · [lib/ruby_llm/attachment.rb:L98-L107][f1]

Derives a file extension from mime_type: mpeg maps to mp3, the wav variants to wav, otherwise the subtype after the slash.

<a id="u-f3e4a8311466"></a>
### `RubyLLM.Attachment.save`

`def save(path)` · [lib/ruby_llm/attachment.rb:L59-L65][f1]

Writes the source's bytes to the given path via File.open, but only for IO-like sources; other source types silently do nothing.

<a id="u-f05f8d1d8618"></a>
### `RubyLLM.Attachment.source_type_cast`

`def source_type_cast` · [lib/ruby_llm/attachment.rb:L160-L168][f1]

Casts the raw source: URL strings to URI, path-like strings to Pathname, anything else unchanged.

Called before url?/path? see the cast value, since initialize reassigns @source with the result.

<a id="u-0be8d55f3553"></a>
### `RubyLLM.Attachment.to_h`

`def to_h` · [lib/ruby_llm/attachment.rb:L117-L119][f1]

Returns a hash of type symbol and the raw source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/attachment.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/mime_type.rb
