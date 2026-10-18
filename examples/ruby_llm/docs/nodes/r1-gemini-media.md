# Gemini Media

**Capability.** Converts message content into Gemini parts, builds inline/file attachments with deterministic filenames, and reassembles response parts into content.

Use Media for all attachment serialization and response-content reassembly; leaf part builders feed format_content.

**Depended on by.**

- [Gemini Chat & Schema](r1-gemini-chat.md) · graph-confirmed · 1 edge(s)
- [Gemini Tools](r1-gemini-tools.md) · model-inferred · 0 edge(s)

Parent: [Gemini Adapter](r1-gemini-adapter.md)

## Units (6)

<a id="u-f090cebf0dbd"></a>
### `RubyLLM.Providers.Gemini.Media.format_content`

`def format_content(content)` · [lib/ruby_llm/providers/gemini/media.rb:L10-L30][f1]

Converts message content into Gemini parts.

A RubyLLM::Content::Raw is returned as its value directly; a Hash or Array is JSON-serialized into a single text part; any non-Content scalar becomes one text part. For a Content object it emits a text part when content.text is present, then iterates attachments: :text attachments become {text: for_llm} parts, :unknown attachments raise UnsupportedAttachmentError carrying the mime type, and all other types become inline_data parts with the attachment's mime type and encoded data.

**Notes.**

- failure: UnsupportedAttachmentError is raised for attachments whose type cannot be determined.

<a id="u-9c9ffce70342"></a>
### `media-format-parts`

`def format_attachment(attachment)` · [lib/ruby_llm/providers/gemini/media.rb:L32-L39][f1]

Groups the leaf part builders of Media.

format_attachment returns {inline_data: {mime_type:, data: encoded}}. format_text_file returns {text: text_file.for_llm}, relying on the attachment's LLM-safe rendering. format_text wraps any value as {text: value}.

<a id="u-5654c1bfb92e"></a>
### `RubyLLM.Providers.Gemini.attachment_filename`

`def attachment_filename(mime_type, index)` · [lib/ruby_llm/providers/gemini/media.rb:L101-L109][f1]

Generates a deterministic attachment filename from a mime type and part index: without a mime type it returns 'gemini_attachment_<index+1>'; otherwise it derives an extension from the text after '/', maps 'jpeg' to 'jpg' and 'plain' to 'txt', converts '+' to '.', and appends it to the same prefix.

<a id="u-02130c9065db"></a>
### `RubyLLM.Providers.Gemini.build_file_attachment`

`def build_file_attachment(file_data, index)` · [lib/ruby_llm/providers/gemini/media.rb:L93-L99][f1]

Builds an Attachment from a file reference.

It returns nil when 'fileUri' is absent; otherwise it uses the provided 'filename' or falls back to attachment_filename derived from the mime type and part index, and constructs RubyLLM::Attachment from the URI. No fetch happens here; the URI is handed to Attachment as-is.

<a id="u-a5924e4a5462"></a>
### `RubyLLM.Providers.Gemini.build_inline_attachment`

`def build_inline_attachment(inline_data, index)` · [lib/ruby_llm/providers/gemini/media.rb:L77-L91][f1]

Builds an Attachment from inline base64 data.

It returns nil when the 'data' field is absent; otherwise decodes the base64, wraps the bytes in a binary StringIO, and constructs RubyLLM::Attachment with a generated filename. A decoding ArgumentError is caught, logged as a warning, and converted to nil, so the caller drops the attachment silently.

**Notes.**

- failure: Base64 decode failures downgrade to a logged warning and nil instead of propagating.

uses: [lib/ruby_llm/media.rb](../../catalog.json)

<a id="u-3ab8e9936746"></a>
### `RubyLLM.Providers.Gemini.build_response_content`

`def build_response_content(parts) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/media.rb:L54-L75][f1]

Reassembles response parts into content.

It walks parts with index: parts with 'text' accumulate into a joined text; parts with 'inlineData' or 'fileData' become attachments via the respective builders, skipped when the builder returns nil. Empty joined text becomes nil. With no attachments the text (or nil) is returned alone; with attachments a Content bundling text and attachments is returned, so a response can carry both.

**Notes.**

- side_effect: Parts matching none of text/inlineData/fileData are silently ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/media.rb