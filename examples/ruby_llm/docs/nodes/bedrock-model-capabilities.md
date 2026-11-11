# Bedrock model capabilities

**Capability.** Provides Bedrock-specific capability queries: family resolution from model IDs, default pricing, streaming and function-calling flags, and text-only modalities.

A small capability module for AWS Bedrock model ids. Families map to Claude variants; capabilities default conservatively with text-only modalities and default per-million prices when a family is unknown.

**Depends on.**

- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (6)

<a id="u-981fe2bd2c72"></a>
### `capabilities.rb-capability-predicates-and-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L10-L15][f1]

Module-level capability queries for Bedrock model IDs.

Chat, streaming, images, vision, functions, and JSON mode are all true only when the ID matches /anthropic\.claude/; audio and structured output are always false; model_type is always 'chat'. Context window is 100_000 for claude-2 IDs, else 200_000; max output tokens is a flat 4_096. Input/output prices look up PRICES by model family, falling back to defaults (0.1/0.2 per million). format_display_name humanizes the ID.

<a id="u-a71a9acad31e"></a>
### `capabilities.rb-default-prices-and-humanize`

`def default_input_price` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L95-L97][f1]

Default per-million prices (input 0.1, output 0.2) used when PRICES has no entry for a family.

humanize turns an ID like 'anthropic.claude-3-5-sonnet' into 'Claude 3 5 Sonnet' by replacing hyphens with spaces, taking the segment after the last dot, and capitalizing each word.

<a id="u-538234723903"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.capabilities_for`

`def capabilities_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L126-L141][f1]

Builds a capability string list for a model: 'streaming' when the ID matches /anthropic\.claude/; 'function_calling' via supports_functions?

(same regex); 'reasoning' for claude-3-7 IDs; and both 'batch' and 'citations' when the ID matches claude-3.5 or claude-3-7.

<a id="u-7a5c0066cc58"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L112-L124][f1]

Returns input/output modality hashes defaulting to text-only.

If the ID matches /anthropic\.claude/ and supports_vision? is true (same regex), 'image' and 'pdf' are appended to input modalities.

<a id="u-d616ea5c4986"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L81-L83][f1]

Maps a Bedrock model ID to a family symbol by matching against the frozen MODEL_FAMILIES regex table (claude-3 opus/sonnet/haiku variants, claude-2, claude-instant), returning :other when nothing matches.

<a id="u-b42ad68cc99e"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L143-L163][f1]

Returns pricing keyed by :text_tokens with :standard and :batch entries.

Family prices come from PRICES with a default hash fallback; batch prices are exactly half the standard per-million input/output rates.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/capabilities.rb
