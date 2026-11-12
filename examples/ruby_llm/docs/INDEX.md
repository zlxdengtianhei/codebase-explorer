# ruby_llm: code map

RubyLLM is a Ruby library for integrating multiple LLM providers with chat, embeddings, persistence, streaming, and Rails tooling. Its top-level modules separate provider/model abstractions, provider transport and streaming, chat payload and auxiliary APIs, chat persistence and orchestration, Rails generator tooling, Bedrock SigV4 signing, rake automation, and attachment/content handling. The provider side composes backends and metadata, transport handles connections/errors/streams, chat modules format and persist conversations, and generators scaffold Rails integration.

## Modules

- [**Provider Model Abstractions**](nodes/provider-model-abstractions.md) — Organizes provider integrations, model metadata, and embedding hooks so LLM backends share consistent model and capability abstractions. (85 units; `openai/capabilities.rb`)
  - [**Provider Composition And Registry**](nodes/provider-composition-and-registry.md) — Combines provider-specific integration modules with model registry and media formatting so backends expose chat, models, media, and capabilities. (38 units; `ruby_llm/models.rb`)
    - [**Provider Integration Compositions**](nodes/provider-integration-compositions.md) — Composes provider-specific chat, models, media, capabilities, and streaming modules for multiple LLM backends. (22 units; `deepseek/capabilities.rb`)
    - [**Model Registry And Media**](nodes/model-registry-and-media.md) — Maintains model metadata registry and formats provider media or capability data for model resolution. (16 units; `ruby_llm/models.rb`)
  - [**Capability And Model Metadata**](nodes/capability-and-model-metadata.md) — Defines model capability, pricing, modality, and display metadata plus value objects used to resolve and describe provider models. (30 units; `openai/capabilities.rb`)
    - [**Provider Capability Metadata**](nodes/provider-capability-metadata.md) — Derives model capabilities, limits, pricing, modalities, and display names for Anthropic, Gemini, and OpenAI. (23 units; `openai/capabilities.rb`)
    - [**Model Metadata Value Objects**](nodes/model-metadata-value-objects.md) — Stores model metadata, modalities, pricing categories, tiers, and capability predicates as mutable value objects. (7 units; `info.rb`)
  - [**Embedding And Provider Hooks**](nodes/embedding-and-provider-hooks.md) — Provides embedding value and request flow plus provider-specific embedding, chat, model, and capability hooks. (17 units; `mistral/capabilities.rb`)
- [**Provider Transport And Streaming**](nodes/provider-transport-and-streaming.md) — Handles provider connections, request/error behavior, and streaming chunk accumulation so responses are transported and assembled consistently. (80 units; `gemini/chat.rb`)
  - [**Chat Payload And Auxiliary APIs**](nodes/chat-payload-and-auxiliary-apis.md) — Formats chat messages, tools, schemas, and provider payloads while covering auxiliary operations such as aliases, images, moderation, transcription, and Rails entrypoints. (41 units; `gemini/chat.rb`)
    - [**Chat Message And Tool Formatting**](nodes/chat-message-and-tool-formatting.md) — Formats chat messages, tool calls, schemas, and provider payloads and parses completions into messages. (29 units; `gemini/chat.rb`)
    - [**Media And Auxiliary Operations**](nodes/media-and-auxiliary-operations.md) — Handles aliases, images, moderation, transcription, model listing, and Rails integration entrypoints. (12 units; `gemini/transcription.rb`)
  - [**Provider Connection And Errors**](nodes/provider-connection-and-errors.md) — Wraps HTTP connections, provider base behavior, configuration validation, request dispatch, and error mapping. (22 units; `provider.rb`)
  - [**Streaming Chunk Accumulation**](nodes/streaming-chunk-accumulation.md) — Streams provider responses, adapts provider events into chunks, and accumulates chunks into complete messages. (17 units; `ruby_llm/streaming.rb`)
- [**Chat Persistence And Orchestration**](nodes/chat-persistence-and-orchestration.md) — Connects ActiveRecord chat persistence with core configuration, context, callbacks, tool execution, and high-level chat API orchestration. (47 units; `acts_as_legacy.rb`)
  - [**ActiveRecord Chat Persistence**](nodes/activerecord-chat-persistence.md) — Wires chat, message, model, and tool-call records to persistence callbacks, associations, and conversion helpers. (27 units; `acts_as_legacy.rb`)
  - [**Core Chat Configuration**](nodes/core-chat-configuration.md) — Defines global configuration, per-call context, chat orchestration, callbacks, tool execution, and high-level API forwarding. (20 units; `ruby_llm/chat.rb`)
- [**Rails Generator Tooling**](nodes/rails-generator-tooling.md) — Provides Rails generators for chat UI scaffolding, installation, upgrades, migrations, and shared naming helpers. (33 units; `chat_ui_generator.rb`)
  - [**Chat UI Generator**](nodes/chat-ui-generator.md) — Scaffolds Rails chat UI controllers, views, jobs, routes, and Turbo broadcasting from configured model names. (8 units; `chat_ui_generator.rb`)
  - [**RubyLLM Install Generator**](nodes/rubyllm-install-generator.md) — Installs RubyLLM initializer, models, migrations, and optional ActiveStorage into a Rails app. (7 units; `install_generator.rb`)
  - [**V1.7 Upgrade Generator**](nodes/v1-7-upgrade-generator.md) — Upgrades existing Rails apps to the v1.7 acts_as API by updating models, initializer, and migrations. (7 units; `upgrade_to_v1_7_generator.rb`)
  - [**Generator Naming Helpers**](nodes/generator-naming-helpers.md) — Builds model-name mappings, acts_as declarations, namespace files, and Rails naming or table helpers for generators. (6 units; `generator_helpers.rb`)
  - [**Upgrade Migration Generators**](nodes/upgrade-migration-generators.md) — Creates v1.7 and v1.9 upgrade migrations and prints migration guidance for existing apps. (5 units; `upgrade_to_v1_9_generator.rb`)
- [**Bedrock SigV4 Signing**](nodes/bedrock-sigv4-signing.md) — Implements AWS SigV4 request signing components, credentials, canonicalization, signatures, and signer facade. (17 units; `signing.rb`)
- [**Rake Task Automation**](nodes/rake-task-automation.md) — Defines rake tasks for model refresh, docs, aliases, release prep, database loading, and VCR cassette recording. (17 units; `models.rake`)
- [**Attachment And Content Handling**](nodes/attachment-and-content-handling.md) — Normalizes attachments, content, MIME types, source loading, encoding, and request formatting for LLM inputs. (16 units; `attachment.rb`)

## Key flows

- **Provider request dispatch**: Provider operations delegate HTTP request execution to connection verbs. — `provider.rb-provider-operations` → `connection.rb-http-verbs`
- **Streaming response pipeline**: Stream entrypoints process provider events and route failures through stream error handling. — `streaming.rb-stream-entrypoints` → `streaming.rb-stream-processing-pipeline` → `streaming.rb-stream-error-handling`
- **Streamed tool-call assembly**: Streaming feeds accumulator add, which accumulates tool-call and token data into tool-call values. — `streaming.rb-stream-entrypoints` → `RubyLLM.StreamAccumulator.add` → `stream_accumulator.rb-tool-call-and-token-accumulation` → `tool_call.rb-tool-call-value`
- **ActiveRecord chat conversion**: Chat methods convert persisted records through to_llm into chat message mutation and chat objects. — `chat_methods.rb-chat-chainable-delegators` → `lib/ruby_llm/active_record/chat_methods.rb:to_llm` → `chat.rb-message-mutation` → `chat.rb-chat-class`
- **Legacy chat persistence**: Legacy chainable chat construction runs persistence callbacks and attachment persistence with data utilities. — `acts_as_legacy.rb-legacy-chainable-delegators` → `acts_as_legacy.rb-legacy-chat-construction-and-context` → `acts_as_legacy.rb-legacy-persistence-callbacks` → `acts_as_legacy.rb-legacy-attachment-persistence` → `utils.rb-data-utilities`
- **Model info pricing metadata**: Derived model attributes feed info construction and pricing collections, categories, and dynamic tier values. — `info.rb-derived-attributes` → `info.rb-info-construction-and-serialization` → `pricing.rb-pricing-collection` → `pricing_category.rb-pricingcategory-tiers` → `pricing_tier.rb-pricingtier-dynamic-values`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
