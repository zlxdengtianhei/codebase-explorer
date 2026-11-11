# RubyLLM LLM Integration Gem

**Capability.** A Ruby gem providing unified chat, streaming, embeddings, tool calling, and model metadata across OpenAI, Anthropic, Gemini, and other LLM providers.

Readers should start here for the whole system: provider adapters and wire formats, persistence and orchestration, Rails generators, and supporting infrastructure like attachments and AWS signing. The subgroups divide work between provider integration, model metadata, streaming core, persistence, and setup tooling.

**Children.**

- [Provider Adapters and Tools](provider-adapters-and-tools.md) `provider-adapters-and-tools` · 71 unit(s)
- [Model Metadata and Embeddings](model-metadata-and-embeddings.md) `model-metadata-and-embeddings` · 70 unit(s)
- [Streaming and Provider Core](streaming-and-provider-core.md) `streaming-and-provider-core` · 66 unit(s)
- [Persistence and Conversation Layer](persistence-and-conversation-layer.md) `persistence-and-conversation-layer` · 51 unit(s)
- [Rails Generator Tooling](rails-generator-tooling.md) `rails-generator-tooling` · 35 unit(s)
- [AWS SigV4 Request Signing](aws-sigv4-request-signing.md) `aws-sigv4-request-signing` · 23 unit(s)
- [Model Registry Rake Tooling](model-registry-rake-tooling.md) `model-registry-rake-tooling` · 22 unit(s)
- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) `attachment-normalization-and-mime` · 14 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
