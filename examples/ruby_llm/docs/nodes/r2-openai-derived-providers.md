# OpenAI-Derived Providers

**Capability.** Vendors that subclass the OpenAI adapter and override only what differs: model catalogs, content formatting, and endpoint URLs.

Use to see the small delta each OpenAI-compatible vendor contributes on top of the OpenAI mixins.

**Depends on.**

- [Provider Connection](r2-connection.md) · model-inferred · 0 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-openai-derived-providers ` → ` r2-provider-openai `) · GPUStack, Ollama, and OpenRouter subclass the OpenAI adapter and override only deltas.

Parent: [OpenAI Adapter](r2-provider-openai.md)

## Units (13)

<a id="u-154f857359b4"></a>
### `Ollama`

`class Ollama < OpenAI` · [lib/ruby_llm/providers/ollama.rb:L6-L11][f1]

Ollama subclasses OpenAI and includes Ollama::Chat, Media, and Models.

api_base returns @config.ollama_api_base with no fallback, so an unset configuration yields nil. headers always returns an empty hash — no authentication is sent. Singleton configuration_requirements lists only :ollama_api_base and local? always returns true.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

<a id="u-14254f862f5f"></a>
### `GPUStack`

`class GPUStack < OpenAI` · [lib/ruby_llm/providers/gpustack.rb:L6-L11][f2]

GPUStack subclasses OpenAI and includes GPUStack::Chat, Models, and Media.

api_base returns @config.gpustack_api_base with no fallback, so an unset configuration yields nil as the base. headers returns an empty hash unless @config.gpustack_api_key is set, in which case it sends an Authorization bearer header — auth is optional. Singleton local? always returns true; configuration_requirements lists only :gpustack_api_base.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

<a id="u-534df7b9b015"></a>
### `RubyLLM.Providers.GPUStack.Chat.format_messages`

`def format_messages(messages)` · [lib/ruby_llm/providers/gpustack/chat.rb:L10-L19][f3]

Converts messages to OpenAI-style hashes with keys role (format_role stringifies the role), content (delegated to GPUStack::Media.format_content), tool_calls (delegated to format_tool_calls), and tool_call_id; .compact drops nil entries, so messages without tool data omit those keys.

calls: [RubyLLM.Providers.GPUStack.Chat.format_messages](r2-openai-derived-providers.md#u-534df7b9b015)

**Uncertainties.**

- format_tool_calls and GPUStack::Media.format_content are not defined in this file; their behavior and failure modes cannot be read here.

<a id="u-d31eae75605f"></a>
### `RubyLLM.Providers.GPUStack.Media.format_content`

`def format_content(content)` · [lib/ruby_llm/providers/gpustack/media.rb:L12-L32][f4]

Serializes chat content into GPUStack's expected shape.

A RubyLLM::Content::Raw is passed through as its .value; Hash or Array input is returned as JSON; any non-Content value is returned unchanged. For Content objects it builds a parts list: the text (via format_text) when present, then each attachment — images via format_image, text attachments via format_text_file (inherited from OpenAI::Media), and any other attachment type raising UnsupportedAttachmentError with the attachment's mime type. format_image produces an OpenAI-style image_url hash using image.for_llm and detail 'auto'.

calls: [RubyLLM.Providers.GPUStack.Media.format_content](r2-openai-derived-providers.md#u-d31eae75605f)

**Uncertainties.**

- format_text, format_text_file, and OpenAI::Media's extend behavior come from outside this file; UnsupportedAttachmentError's semantics are not shown.

<a id="u-e0d853ee2b90"></a>
### `gpustack-models-rb-classification`

`def determine_model_type(model)` · [lib/ruby_llm/providers/gpustack/models.rb:L43-L48][f5]

Classifies a GPUStack model entry by its categories: 'embedding' yields 'embedding', 'llm' yields 'chat', anything else 'other'.

No caller of determine_model_type appears in this file.

**Uncertainties.**

- No call site for determine_model_type is visible in this file; its consumer is external.

<a id="u-2d8eb1f75c79"></a>
### `RubyLLM.Providers.GPUStack.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, _capabilities)` · [lib/ruby_llm/providers/gpustack/models.rb:L14-L39][f5]

Maps the GPUStack model listing to Model::Info records.

Reads response.body['items'] (defaulting to []) and for each item builds id and name from model['name'], created_at by Time.parse of 'created_at' or nil when absent, provider slug, family 'gpustack', a metadata hash of description/source/huggingface/ollama/backend/meta/categories fields, context_window and max_output_tokens both from meta.n_ctx, capabilities from build_capabilities, modalities from build_modalities, and empty pricing. A missing meta hash makes the dig calls return nil rather than raising.

calls: [RubyLLM.Providers.GPUStack.Models.build_capabilities](r2-openai-derived-providers.md#u-5e4f4037e091), [RubyLLM.Providers.GPUStack.Models.build_modalities](r2-openai-derived-providers.md#u-3e2e69cd6964)

**Uncertainties.**

- Time.parse raises on malformed timestamps; no rescue exists here.

<a id="u-5e4f4037e091"></a>
### `RubyLLM.Providers.GPUStack.Models.build_capabilities`

`def build_capabilities(model) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gpustack/models.rb:L50-L66][f5]

Derives capabilities from GPUStack metadata.

'streaming' is added when categories include 'llm'. 'function_calling', 'vision', and 'reasoning' are each added when meta.support_tool_calls / support_vision / support_reasoning are truthy. 'structured_output' and 'json_mode' are added for every 'llm' category model. Non-LLM models get only whatever meta flags apply; no deduplication is applied.

<a id="u-3e2e69cd6964"></a>
### `RubyLLM.Providers.GPUStack.Models.build_modalities`

`def build_modalities(model)` · [lib/ruby_llm/providers/gpustack/models.rb:L68-L86][f5]

Builds input/output modality lists from categories and meta flags.

'llm' models get text input, plus 'image' when meta.support_vision and 'audio' when meta.support_audio, and text output. 'embedding' models get text input and 'embeddings' output. Anything else yields two empty lists.

<a id="u-898006d9227c"></a>
### `OpenRouter`

`class OpenRouter < OpenAI` · [lib/ruby_llm/providers/openrouter.rb:L6-L9][f6]

OpenRouter subclasses OpenAI and additionally includes OpenRouter::Models (inheriting all other OpenAI mixins and behavior).

api_base is the constant 'https://openrouter.ai/api/v1'. headers returns a single Authorization bearer header from @config.openrouter_api_key. Singleton configuration_requirements lists only :openrouter_api_key; the class defines no capabilities override, so it inherits OpenAI::Capabilities.

**Notes.**

- contract: No capabilities override means OpenRouter models report OpenAI capabilities at the class level.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

<a id="u-bfd5976ed151"></a>
### `RubyLLM.Providers.OpenRouter.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, _capabilities)` · [lib/ruby_llm/providers/openrouter/models.rb:L14-L57][f7]

Maps the OpenRouter model list to Model::Info records.

For each entry in response.body['data'] (coerced via Array) it reads modalities from architecture.input_modalities/output_modalities (each Array-coerced), builds pricing under text_tokens.standard from the 'pricing' object: prompt, completion, input_cache_read, and internal_reasoning values are converted to_f and, when positive, stored times 1,000,000 under input_per_million, output_per_million, cached_input_per_million, and reasoning_output_per_million respectively. Capabilities come from supported_parameters_to_capabilities. The record gets id, name, provider slug, family from the id's first '/' segment, created_at via Time.at of 'created' or nil when absent, context_window from context_length, max_output_tokens from top_provider.max_completion_tokens, and a metadata hash of description/architecture/top_provider/per_request_limits/supported_parameters.

calls: [RubyLLM.Providers.OpenRouter.Models.supported_parameters_to_capabilities](r2-openai-derived-providers.md#u-be77ca5923e8)

<a id="u-be77ca5923e8"></a>
### `RubyLLM.Providers.OpenRouter.Models.supported_parameters_to_capabilities`

`def supported_parameters_to_capabilities(params)` · [lib/ruby_llm/providers/openrouter/models.rb:L59-L69][f7]

Translates OpenRouter's supported_parameters list into capabilities.

Returns [] when params is nil; note that params.include? on a non-Array non-nil value would raise, so non-list shapes are unhandled. Otherwise: always 'streaming'; 'function_calling' when 'tools' or 'tool_choice' is present; 'structured_output' for 'response_format'; 'batch' for 'batch'; 'predicted_outputs' only when both 'logit_bias' and 'top_k' are present.

<a id="u-d6e571868ba9"></a>
### `RubyLLM.Providers.Perplexity.Models.list_models`

`def list_models(**)` · [lib/ruby_llm/providers/perplexity/models.rb:L8-L12][f8]

Returns Perplexity's model catalog without an HTTP call.

It hardcodes the slug 'perplexity', uses Perplexity::Capabilities as the capabilities source, and calls parse_list_models_response with a nil response — so the response argument is unused and the catalog is fully static.

calls: [models.rb-perplexity-model-catalog](r2-openai-derived-providers.md#u-9d48eef0f834)

<a id="u-9d48eef0f834"></a>
### `models.rb-perplexity-model-catalog`

`def parse_list_models_response(_response, slug, capabilities)` · [lib/ruby_llm/providers/perplexity/models.rb:L14-L22][f8]

Static Perplexity catalog construction.

parse_list_models_response ignores its response argument and returns Model::Info records for exactly five ids: 'sonar', 'sonar-pro', 'sonar-reasoning', 'sonar-reasoning-pro', and 'sonar-deep-research'. create_model_info fills name, family (stringified model_family), context_window, max_output_tokens, modalities, capabilities, and pricing from Perplexity::Capabilities, sets created_at to Time.now at call time, and leaves metadata empty.

**Uncertainties.**

- The Perplexity::Capabilities methods are defined outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/media.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gpustack/models.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openrouter/models.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/models.rb