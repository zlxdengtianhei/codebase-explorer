# Provider Integration Compositions

**Capability.** Composes provider-specific chat, models, media, capabilities, and streaming modules for multiple LLM backends.

Observed units show provider classes assembled from provider-specific modules. Come here to see composition and small formatting or capability helpers; full runtime behavior is not shown.

**Depends on.**

- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 1 edge(s)

Parent: [Provider Composition And Registry](provider-composition-and-registry.md)

## Units (22)

<a id="u-4b37ca26f437"></a>
### `anthropic.rb-anthropic-provider`

`class Anthropic < Provider` · [lib/ruby_llm/providers/anthropic.rb:L6-L14][f1]

Anthropic is a provider integration that composes Anthropic chat, embeddings, media, models, streaming, and tools modules.

Its API base is the fixed Anthropic URL. Headers send the configured Anthropic API key as x-api-key and a fixed anthropic-version. The class-level capabilities method returns the Anthropic capabilities class, and configuration requires an Anthropic API key.

<a id="u-c73d285a37f3"></a>
### `bedrock.rb-bedrock-provider`

`class Bedrock < Provider` · [lib/ruby_llm/providers/bedrock.rb:L9-L17][f2]

Bedrock is an AWS provider integration that composes Bedrock chat, streaming, models, signing, media, and Anthropic tools modules.

Its API base builds a runtime URL from the configured region. Error parsing returns nil for an empty body, parses JSON, returns a hash message, joins array part messages with a period and space, or returns the parsed body otherwise. Request signing creates a signer, builds a request, and signs it. The signer uses configured access key, secret, session token, region, and the bedrock service. Request building returns connection, HTTP method, the given URL or completion URL, and a JSON body generated with ascii_only false or nil when no payload. Header building merges Content-Type application/json and Accept set to application/vnd.amazon.eventstream when streaming, otherwise application/json. Configuration requires access key, secret key, and region.

<a id="u-5db1ef3f7fa4"></a>
### `capabilities.rb-model-metadata-and-capabilities`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L10-L15][f3]

Derives DeepSeek model metadata and capabilities.

Context is 64,000 for chat or reasoner ids and 32,768 otherwise; max output is 8,192 for those ids and 4,096 otherwise. Vision and JSON mode are always false; function calling is true only for deepseek-chat. Display names special-case chat and reasoner, otherwise title-case hyphen parts. Type is always chat; family is reasoner for reasoner ids and chat otherwise. Modalities are text/text; capabilities are streaming plus function_calling for deepseek-chat.

<a id="u-6f818b3e5ab7"></a>
### `capabilities.rb-model-metadata-and-capabilities-2`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L10-L15][f4]

Derives Perplexity model metadata and capabilities.

Context is 200,000 for sonar-pro and 128,000 otherwise; max output is 8,192 for sonar-pro or sonar-reasoning-pro and 4,096 otherwise. Vision is true for sonar ids, functions are always false, and JSON mode is always true. Display names special-case known sonar names and otherwise title-case hyphen parts. Type is always chat; family maps exact sonar names to symbols and otherwise unknown. Modalities are text/text; capabilities are streaming and json_mode plus vision when supported.

<a id="u-fe5b31daff9e"></a>
### `capabilities.rb-pricing`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L24-L26][f3]

Computes DeepSeek pricing.

The family helper returns a symbol and the price table is symbol-keyed, so input, output, and cache-hit lookups hit known families and otherwise use defaults 0.27, 1.10, and 0.07. Aggregate pricing fetches the family with a default hash, reports standard input_miss and output, and adds cached input when input_hit exists.

<a id="u-741ea82cadd1"></a>
### `capabilities.rb-pricing-2`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L24-L26][f4]

Computes Perplexity pricing.

The family helper returns a symbol and the price table is symbol-keyed, so input and output lookups hit known families and otherwise default to 1.0. Aggregate pricing fetches the family with a 1.0/1.0 default, reports standard input and output, and adds citation, reasoning, or search-query prices when present.

<a id="u-478f39088514"></a>
### `chat.rb-deepseek-chat-role-formatting`

`class DeepSeek # Chat methods of the DeepSeek API integration` · [lib/ruby_llm/providers/deepseek/chat.rb:L5-L7][f5]

Provides DeepSeek chat formatting; the only visible behavior is converting a role to its string form.

No other chat transformation is defined here.

<a id="u-49a35ad4cc2b"></a>
### `chat.rb-message-formatting-2`

`def format_messages(messages)` · [lib/ruby_llm/providers/gpustack/chat.rb:L10-L19][f6]

Formats GPUStack chat messages.

Each message becomes a hash with string role, media-formatted content, tool calls, and tool-call id; nil values are removed. Role formatting is just string conversion.

<a id="u-e25698e909a5"></a>
### `chat.rb-ollama-chat-formatting`

`class Ollama # Chat methods of the Ollama API integration` · [lib/ruby_llm/providers/ollama/chat.rb:L5-L7][f7]

Formats Ollama chat messages and roles.

Each message becomes a compact hash with stringified role, media-formatted content, formatted tool calls, and tool-call id; nil fields are removed. Role formatting stringifies the role.

<a id="u-fbb3ea3dc359"></a>
### `chat.rb-perplexity-chat-role-formatting`

`class Perplexity # Chat formatting for Perplexity provider` · [lib/ruby_llm/providers/perplexity/chat.rb:L5-L7][f8]

Provides Perplexity chat formatting; the only visible behavior is converting a role to its string form.

<a id="u-4cd167fc4442"></a>
### `deepseek.rb-deepseek-provider`

`class DeepSeek < OpenAI` · [lib/ruby_llm/providers/deepseek.rb:L6-L9][f9]

DeepSeek is an OpenAI-derived provider that adds DeepSeek chat behavior.

Its API base is the fixed DeepSeek URL. Headers send the configured DeepSeek API key as a Bearer token. The class-level capabilities method returns the DeepSeek capabilities class, and configuration requires a DeepSeek API key.

<a id="u-bb1976a49777"></a>
### `gemini.rb-gemini-provider`

`class Gemini < Provider` · [lib/ruby_llm/providers/gemini.rb:L6-L16][f10]

Gemini is a native Google provider integration composing chat, embeddings, images, models, transcription, streaming, tools, and media modules.

Its API base uses the configured Gemini base when present, otherwise a fixed default. Headers send the configured Gemini API key as x-goog-api-key. The class-level capabilities method returns the Gemini capabilities class, and configuration requires a Gemini API key.

<a id="u-c2f49ed5d781"></a>
### `gpustack.rb-gpustack-provider`

`class GPUStack < OpenAI` · [lib/ruby_llm/providers/gpustack.rb:L6-L11][f11]

GPUStack is an OpenAI-derived local provider integration composing chat, models, and media modules.

Its API base comes from the configured GPUStack base. Headers are empty unless a GPUStack API key is configured, in which case they send a Bearer token. The class reports itself as local and configuration requires a GPUStack API base.

<a id="u-ec18eff734e3"></a>
### `media.rb-gpustack-media-formatting`

`class GPUStack # Handles formatting of media content (images, audio) for GPUStack APIs` · [lib/ruby_llm/providers/gpustack/media.rb:L5-L7][f12]

Formats GPUStack message content and images for chat payloads.

Raw content returns its value; hashes and arrays return JSON; non-Content values pass through unchanged. Content objects build a parts array with text when present, then each attachment: images become image_url objects with the attachment's LLM URL and auto detail, text attachments use the inherited text-file formatter, and any other attachment type raises UnsupportedAttachmentError with the MIME type.

**Uncertainties.**

- The inherited text and text-file formatters are outside this source.

<a id="u-766e93c700d5"></a>
### `media.rb-ollama-media-formatting`

`class Ollama # Handles formatting of media content (images, audio) for Ollama APIs` · [lib/ruby_llm/providers/ollama/media.rb:L5-L7][f13]

Formats Ollama message content and images for chat payloads.

Raw content returns its value; hashes and arrays return JSON; non-Content values pass through unchanged. Content objects build a parts array with text when present, then each attachment: images become image_url objects with the attachment's LLM URL and auto detail, text attachments use the inherited text-file formatter, and any other attachment type raises UnsupportedAttachmentError with the MIME type.

**Uncertainties.**

- The inherited text and text-file formatters are outside this source.

<a id="u-d4af1bd9d00e"></a>
### `models.rb-model-listing-2`

`def models_url` · [lib/ruby_llm/providers/gpustack/models.rb:L10-L12][f14]

Parses GPUStack model listings into model info.

The models URL is 'models'. It maps response items, using name for id and name, parsing created_at when present, provider slug, family gpustack, metadata fields, context and max output from meta.n_ctx, built capabilities and modalities, and empty pricing. Model type is embedding for embedding category, chat for llm, otherwise other. Capabilities add streaming, structured_output, and json_mode for llm; function_calling, vision, and reasoning follow meta flags. Modalities for llm are text input plus image/audio by meta flags and text output; embedding is text input and embeddings output; other categories get empty arrays.

<a id="u-aa6af10ca4e0"></a>
### `models.rb-model-listing-3`

`def models_url` · [lib/ruby_llm/providers/openrouter/models.rb:L10-L12][f15]

Parses OpenRouter model listings into model info.

The models URL is 'models'. It maps data entries, reads input/output modalities from architecture, converts positive prompt, completion, cache-read, and internal-reasoning prices to per-million values, derives capabilities from supported parameters, and fills id, name, provider, family from the id prefix, created time, context, max completion tokens, pricing, and metadata. Supported parameters always add streaming; tools or tool_choice add function_calling; response_format adds structured_output; batch adds batch; logit_bias with top_k adds predicted_outputs; nil parameters yield no capabilities.

<a id="u-fe12e3ec9242"></a>
### `models.rb-ollama-model-listing`

`class Ollama # Models methods for the Ollama API integration` · [lib/ruby_llm/providers/ollama/models.rb:L5-L7][f16]

Lists Ollama models and builds fixed-capability model info.

The URL is fixed. Listing uses body data or an empty array, maps each entry to Model::Info with id/name from the entry id, provider slug, family 'ollama', created_at from Time.at when created is present (otherwise nil), fixed text/image input and text output modalities, fixed streaming/function-calling/structured-output/vision capabilities, empty pricing, and owned_by metadata.

<a id="u-9aa2d0252831"></a>
### `models.rb-perplexity-model-listing`

`class Perplexity # Models methods of the Perplexity API integration` · [lib/ruby_llm/providers/perplexity/models.rb:L5-L7][f17]

Lists a fixed set of Perplexity models without calling the API.

The list entrypoint ignores its arguments, uses the perplexity slug and capability module, and parses a nil response. Parsing returns five hard-coded model infos. Each info uses the id, display name, provider slug, stringified family, current time as created_at, and capability lookups for context, max tokens, modalities, capabilities, and pricing; metadata is empty.

<a id="u-c9594c889107"></a>
### `ollama.rb-ollama-provider`

`class Ollama < OpenAI` · [lib/ruby_llm/providers/ollama.rb:L6-L11][f18]

Ollama is an OpenAI-derived local provider integration composing chat, media, and models modules.

Its API base comes from the configured Ollama base. Headers are always an empty hash. Configuration requires an Ollama API base, and the class reports itself as local.

<a id="u-3dcddd63cf52"></a>
### `openrouter.rb-openrouter-provider`

`class OpenRouter < OpenAI` · [lib/ruby_llm/providers/openrouter.rb:L6-L9][f19]

OpenRouter is an OpenAI-derived provider integration composing OpenRouter models.

Its API base is the fixed OpenRouter URL. Headers send the configured OpenRouter API key as a Bearer token. Configuration requires an OpenRouter API key.

<a id="u-9b2b17fcd7d9"></a>
### `perplexity.rb-perplexity-provider`

`class Perplexity < OpenAI` · [lib/ruby_llm/providers/perplexity.rb:L6-L10][f20]

Perplexity is an OpenAI-derived provider integration composing chat and models modules.

Its API base is the fixed Perplexity URL. Headers send a Bearer API key and Content-Type application/json. The class-level capabilities method returns the Perplexity capabilities class, and configuration requires a Perplexity API key. Error parsing returns nil for an empty body; when the body contains both html and title markers, it extracts the title, strips a leading number and space, and returns it; if no title match is found it falls through to the inherited parser, which also handles non-HTML bodies.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek/capabilities.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/capabilities.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek/chat.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/chat.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/chat.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/chat.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack.rb
[f12]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/media.rb
[f13]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/media.rb
[f14]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/models.rb
[f15]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter/models.rb
[f16]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/models.rb
[f17]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/models.rb
[f18]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama.rb
[f19]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter.rb
[f20]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity.rb
