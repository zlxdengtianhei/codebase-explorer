# Provider Framework

**Capability.** Concrete provider adapters translating the provider-independent chat/message/tool model into each API's wire format: an OpenAI-descended family plus Gemini, Anthropic, Bedrock, and Ollama adapters.

Each provider subtree owns payload formatting, response parsing, capability metadata, and provider quirks. Providers depend on conversation-core value objects (Message, ToolCall, Image) and shared utilities.

**Children.**

- [OpenAI Family](r1-openai-family.md) `r1-openai-family` · 0 unit(s)
- [Anthropic Adapter](r1-anthropic-adapter.md) `r1-anthropic-adapter` · 18 unit(s)
- [Gemini Adapter](r1-gemini-adapter.md) `r1-gemini-adapter` · 1 unit(s)
- [Bedrock Adapter](r1-bedrock-adapter.md) `r1-bedrock-adapter` · 1 unit(s)
- [Ollama Adapter](r1-ollama-adapter.md) `r1-ollama-adapter` · 3 unit(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
