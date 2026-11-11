# Streaming and Provider Core

**Capability.** Implements the abstract provider base, connections, errors, model registry, SSE streaming, and Bedrock AWS-specific plumbing.

Come here for the runtime backbone shared by all providers. Core provider infrastructure supplies base classes and the registry; Streaming and result objects handles SSE parsing and chunk accumulation; Bedrock AWS integration adds signed requests and event-stream framing.

**Children.**

- [Streaming and result objects](streaming-and-result-objects.md) `streaming-and-result-objects` · 28 unit(s)
- [Core provider infrastructure](core-provider-infrastructure.md) `core-provider-infrastructure` · 27 unit(s)
- [Bedrock AWS integration](bedrock-aws-integration.md) `bedrock-aws-integration` · 11 unit(s)

**Depends on.**

- [Model Metadata and Embeddings](model-metadata-and-embeddings.md) · model-inferred · 1 inferred relation(s)
- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-confirmed · 1 edge(s) · Attachment normalization prepares file content for rendering into provider requests.
- [AWS SigV4 Request Signing](aws-sigv4-request-signing.md) · graph-confirmed · 1 edge(s) · SigV4 signing authenticates Bedrock requests issued through the provider core.
- [Model Metadata and Embeddings](model-metadata-and-embeddings.md) · graph-confirmed · 2 edge(s)
- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 9 edge(s) · Provider adapters rely on the shared provider base, connections, and streaming machinery to execute requests.

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
