# ruby_llm: code map

RubyLLM is a Ruby gem offering a unified API for chat, streaming, embeddings, tool calling, and model metadata across OpenAI, Anthropic, Gemini, Bedrock, and other LLM providers. Provider adapters and tool definitions translate internal messages into provider-specific wire formats, while a shared streaming/provider core supplies connections, the model registry, and SSE handling. A persistence and conversation layer bridges ActiveRecord records to Chat objects and exposes the gem's entry facade, and Rails generator tooling installs and upgrades the gem in applications, with supporting infrastructure for attachments and AWS SigV4 signing.

## Modules

- [**Provider Adapters and Tools**](nodes/provider-adapters-and-tools.md) — Defines provider classes and their composition, plus the Tool DSL for declaring and executing function calls. (71 units)
  - [**Chat Wire and Media Formats**](nodes/chat-wire-and-media-formats.md) — Translates internal messages and content into provider-specific request payloads and back, covering chat, media, images, and transcription. (36 units)
  - [**Provider class composition**](nodes/provider-class-composition.md) — Defines each provider class (Anthropic, Gemini, OpenAI and its OpenAI-compatible derivatives) and composes their chat, media, and models modules. (18 units)
  - [**Tool definition and execution**](nodes/tool-definition-and-execution.md) — Provides the Tool base class with its parameter DSL, schema resolution, invocation logic, and OpenAI tool-call wire conversion. (17 units)
- [**Model Metadata and Embeddings**](nodes/model-metadata-and-embeddings.md) — Resolves model identity, capabilities, limits, and pricing across providers, and implements embedding endpoints and the Mistral adapter. (70 units)
  - [**Per-Provider Capability Lookups**](nodes/per-provider-capability-lookups.md) — Provides provider-specific resolution of model families, context limits, capabilities, pricing, and display names. (46 units)
  - [**Embeddings and Mistral support**](nodes/embeddings-and-mistral-support.md) — Implements embedding endpoints for Gemini, OpenAI, Mistral, and VertexAI, the Mistral provider adapter, and the shared Embedding value object. (18 units)
  - [**Model info value objects**](nodes/model-info-value-objects.md) — Defines immutable value objects describing a model's identity, type, modalities, and nested pricing structures with empty-data skipping. (6 units)
- [**Streaming and Provider Core**](nodes/streaming-and-provider-core.md) — Implements the abstract provider base, connections, errors, model registry, SSE streaming, and Bedrock AWS-specific plumbing. (66 units)
  - [**Streaming and result objects**](nodes/streaming-and-result-objects.md) — Implements SSE stream processing, chunk accumulation into final Messages, in-stream error handling, and the Chunk, ToolCall, and Transcription value objects. (28 units)
  - [**Core provider infrastructure**](nodes/core-provider-infrastructure.md) — Provides the abstract Provider base class, Faraday connection management, error hierarchy and middleware, and the model registry with lookup and refresh. (27 units)
  - [**Bedrock AWS integration**](nodes/bedrock-aws-integration.md) — Implements Bedrock model listing with signed management-API requests and the AWS event-stream binary framing parser for streaming chunks. (11 units)
- [**Persistence and Conversation Layer**](nodes/persistence-and-conversation-layer.md) — Bridges chat conversations to ActiveRecord persistence and orchestrates message history, configuration, and completion dispatch. (51 units)
  - [**ActiveRecord persistence bridge**](nodes/activerecord-persistence-bridge.md) — Bridges ActiveRecord chat, message, tool-call, and model records to RubyLLM objects, persisting streamed completions and syncing the model registry. (27 units)
  - [**Chat Orchestration and Gem Facade**](nodes/chat-orchestration-and-gem-facade.md) — Manages conversations with fluent tool and parameter configuration, and exposes the RubyLLM module entry point and global configuration. (24 units)
- [**Rails Generator Tooling**](nodes/rails-generator-tooling.md) — Generates migrations, models, initializers, and chat UI scaffolding to install and upgrade RubyLLM in Rails applications. (35 units)
  - [**Generator shared helpers**](nodes/generator-shared-helpers.md) — Provides helpers mixed into all RubyLLM Rails generators: model-mapping parsing, naming and table derivation, acts_as declaration builders, and namespace module creation. (10 units)
  - [**v1.7 upgrade generator**](nodes/v1-7-upgrade-generator.md) — Upgrades pre-1.7 apps to the Rails-like API by generating models migrations, the model class, rewriting acts_as declarations, and ensuring the initializer exists. (8 units)
  - [**Chat UI scaffolding generator**](nodes/chat-ui-scaffolding-generator.md) — Scaffolds a Turbo-streaming chat UI: controllers, views, a response job, routes, and Turbo broadcasting hooks injected into the message model. (8 units)
  - [**Install generator**](nodes/install-generator.md) — Generates the initial RubyLLM Rails setup: five ordered migrations, model files, an initializer, and optional ActiveStorage installation. (5 units)
  - [**Migration numbering and v1.9**](nodes/migration-numbering-and-v1-9.md) — Provides timestamped migration-number delegation for generators and the v1.9 upgrade generator adding cached-token and raw-content message columns. (4 units)
- [**AWS SigV4 Request Signing**](nodes/aws-sigv4-request-signing.md) — Implements AWS Signature Version 4 request signing for the Bedrock provider, from canonical request construction to credential handling and header assembly. (23 units)
- [**Model Registry Rake Tooling**](nodes/model-registry-rake-tooling.md) — Rake tasks and alias resolution that refresh, validate, and document the model registry, plus VCR cassette management for tests. (22 units)
- [**Attachment Normalization and MIME**](nodes/attachment-normalization-and-mime.md) — Wraps files from URLs, paths, IO objects, or ActiveStorage into a uniform attachment with derived filename, MIME type, and LLM-ready rendering. (14 units)

## Key flows

- **Streaming response accumulation**: A streamed provider response is parsed chunk by chunk and accumulated into a final Message with tool calls. — `stream_response` → `handle_stream` → `streaming.rb-stream-parser-setup` → `streaming.rb-stream-processor-callbacks` → `process_stream_chunk` → (model-inferred) → `RubyLLM.StreamAccumulator.add` → `RubyLLM.StreamAccumulator.accumulate_tool_calls`
- **Stream error handling**: Streamed chunks are inspected for error payloads and routed to error handling when detected. — `stream_response` → `handle_stream` → `streaming.rb-stream-parser-setup` → `streaming.rb-stream-processor-callbacks` → `process_stream_chunk` → `error_chunk?` → (model-inferred) → `handle_error_chunk`
- **ActiveRecord chat to LLM**: A persisted ActiveRecord chat is converted into a RubyLLM Chat, completing and persisting new messages and tool calls. — `chat_methods.rb-with-configurators` → `lib/ruby_llm/active_record/chat_methods.rb:to_llm` → `chat_methods.rb-persistence-callbacks-and-completion` → `chat_methods.rb-tool-call-persistence` → `chat_methods.rb-attachment-and-content-normalization` → `utils.rb-data-utilities`
- **Legacy chat delegation**: Legacy acts_as chat records delegate to the modern Chat API, adding messages through the current Chat object. — `acts_as_legacy.rb-legacy-with-delegators` → `acts_as_legacy.rb-legacy-chat-to-llm` → `RubyLLM.Chat.add_message` → `chat.rb-chat` → `chat.rb-chat-configuration-builders`
- **Model info and pricing assembly**: Model listings assemble identity, modalities, and nested pricing structures into Model::Info value objects. — `info.rb-info-type-and-to-h` → `info.rb-model-info` → `pricing.rb-model-pricing` → `pricing_category.rb-model-pricingcategory` → `pricing_tier.rb-model-pricingtier`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
