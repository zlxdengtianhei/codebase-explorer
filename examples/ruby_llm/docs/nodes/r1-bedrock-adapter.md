# Bedrock Adapter

**Capability.** The AWS Bedrock provider: SigV4 request signing, claude-filtered model catalog fetching with capability/pricing derivation, media content conversion, and low-level event-stream framing (prelude scanning) plus staged payload decoding.

Use this subtree for Bedrock-specific transport: signing is self-contained, streaming is byte-level, and models/capabilities mirror the AWS catalog. Media converts message content into Bedrock-compatible parts.

**Children.**

- [SigV4 Signing](r1-bedrock-signing.md) `r1-bedrock-signing` · 7 unit(s)
- [Bedrock Models & Capabilities](r1-bedrock-models-capabilities.md) `r1-bedrock-models-capabilities` · 8 unit(s)
- [Bedrock Event-Stream Streaming](r1-bedrock-streaming.md) `r1-bedrock-streaming` · 5 unit(s)

Parent: [Provider Framework](r1-provider-framework.md)

## Units (1)

<a id="u-15d22633b933"></a>
### `RubyLLM.Providers.Bedrock.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/bedrock/media.rb:L13-L35][f1]

Converts RubyLLM message content into Bedrock-compatible content parts, with a branch per input shape.

Raw content returns its .value untouched. Hashes/Arrays are serialized with to_json and wrapped as a single Anthropic text part. Plain strings become a single text part. A Content object yields a parts list: its text (when present) becomes a text part, then each attachment is formatted by type — :image via format_image, :pdf via format_pdf, :text via Anthropic::Media.format_text_file — and any other attachment type raises UnsupportedAttachmentError, aborting the whole conversion. The module extends Anthropic::Media so shared text helpers are available; URL-based attachments are not supported here (see the module comment).

**Notes.**

- failure: Any attachment whose type is not :image, :pdf, or :text raises UnsupportedAttachmentError before a response is attempted.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/media.rb