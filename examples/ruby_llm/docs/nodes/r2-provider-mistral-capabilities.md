# Mistral Capabilities

**Capability.** Static, model-id-pattern-driven capability profiles for Mistral: predicates, modality/capability profiles, fixed limits, zero pricing, display names, families, and release dates.

Consult when mapping a Mistral model id to its marketing name, family, limits, or release date; ordering of pattern cases determines precedence.

**Depended on by.**

- [Mistral Adapter](r1-mistral-adapter.md) · graph-only · 1 edge(s)

Parent: [Provider Adapters](r2-providers.md)

## Units (6)

<a id="u-a7db4c902b7f"></a>
### `mistral-capabilities-rb-predicates`

`def supports_streaming?(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L10-L12][f1]

Capability predicates on model-id patterns.

supports_streaming? is false for ids matching /embed|moderation|ocr|transcriptions/ and true otherwise. supports_tools? excludes a wider set: embed, moderation, ocr, voxtral, transcriptions, and mistral-(tiny|small)-(2312|2402). supports_vision? is true only for pixtral, mistral-small-(2503|2506), or mistral-medium ids. supports_json_mode? requires both not matching the embed/moderation/ocr/voxtral/transcriptions pattern and supports_tools? being true.

<a id="u-03721cad5d5d"></a>
### `mistral-capabilities-rb-model-profile`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L64-L82][f1]

Modality and capability profiles.

modalities_for: pixtral ids get text+image input and text output; embed ids get text input and 'embeddings' output; all others text in/text out. capabilities_for has special-case returns first: moderation ids -> ['moderation'], voxtral.*transcribe -> ['transcription'], ocr -> ['vision']. Otherwise it accumulates: 'streaming' if supports_streaming?, 'function_calling' if supports_tools?, 'structured_output' if supports_json_mode?, 'vision' if supports_vision?, then 'reasoning' for /magistral/, 'batch' unless the id matches /voxtral|ocr|embed|moderation/, 'fine_tuning' for /mistral-(small|medium|large)|devstral/, 'distillation' for /ministral/, 'predicted_outputs' for /codestral/, and uniqs the result.

calls: [mistral-capabilities-rb-predicates](r2-provider-mistral-capabilities.md#u-a7db4c902b7f)

<a id="u-a344cb9420f6"></a>
### `mistral-capabilities-rb-limits-pricing`

`def context_window_for(_model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L56-L58][f1]

Fixed limits and zero pricing.

context_window_for returns 32,768 and max_tokens_for returns 8192 for every id. pricing_for ignores the id and returns {input: 0.0, output: 0.0}, a flat shape unlike the text_tokens nesting used by other providers.

<a id="u-2a4ba27c2498"></a>
### `RubyLLM.Providers.Mistral.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L26-L40][f1]

Maps id patterns to marketing names via ordered cases (mistral-large/medium/small, ministral-3b/8b, codestral, pixtral-large/12b, mistral-embed, mistral-moderation); first matching pattern wins.

Unrecognized ids are split on '-', capitalized per part, and joined with spaces.

<a id="u-06865e267a16"></a>
### `RubyLLM.Providers.Mistral.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L42-L54][f1]

Ordered pattern cases map ids to family strings: mistral-large, mistral-medium, mistral-small, ministral, codestral, pixtral, mistral-embed, mistral-moderation; anything else becomes 'mistral'.

<a id="u-93e77c84bd71"></a>
### `RubyLLM.Providers.Mistral.Capabilities.release_date_for`

`def release_date_for(model_id)` · [lib/ruby_llm/providers/mistral/capabilities.rb:L113-L151][f1]

Exact-match case table from model id to a 'YYYY-MM-DD' release date string, covering entries from 2023-09-27 ('open-mistral-7b'/'mistral-tiny') through 2025-08-30 ('codestral-2508'/'codestral-latest').

Ids not listed return nil; matches are on the whole id string, not patterns.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/capabilities.rb