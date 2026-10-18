# Gemini Adapter

**Capability.** The Gemini provider: request building and response parsing for chat, embeddings, and images; message/content conversion into Gemini parts; JSON-schema-to-Gemini-schema conversion; and tool declaration/extraction in Gemini's functionDeclarations format.

Use this subtree for all Gemini wire-format behavior. Chat composes MessageFormatter output, structured output, and tool formatting; Media and Tools convert between RubyLLM objects and Gemini parts and declarations.

**Children.**

- [Gemini Chat & Schema](r1-gemini-chat.md) `r1-gemini-chat` · 8 unit(s)
- [Gemini Media](r1-gemini-media.md) `r1-gemini-media` · 6 unit(s)
- [Gemini Tools](r1-gemini-tools.md) `r1-gemini-tools` · 9 unit(s)
- [Gemini Embeddings & Images](r1-gemini-embeddings-images.md) `r1-gemini-embeddings-images` · 4 unit(s)

Parent: [Provider Framework](r1-provider-framework.md)

## Units (1)

<a id="u-0ee8ddba6d0e"></a>
### `Gemini`

`class Gemini < Provider` · [lib/ruby_llm/providers/gemini.rb:L6-L16][f1]

Gemini subclasses Provider and includes Gemini::Chat, Embeddings, Images, Models, Transcription, Streaming, Tools, and Media.

api_base prefers @config.gemini_api_base and falls back to 'https://generativelanguage.googleapis.com/v1beta'. headers returns a single 'x-goog-api-key' entry taken from @config.gemini_api_key. Singleton capabilities returns Gemini::Capabilities; configuration_requirements lists only :gemini_api_key (the api_base override is not required).

inherits: [provider.rb-provider-instance](r2-provider-base.md#u-961fc10a6a0f)

**Uncertainties.**

- Behavior of the included Gemini mixins lies outside this batch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini.rb