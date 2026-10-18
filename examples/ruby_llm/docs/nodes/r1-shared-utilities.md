# Shared Utilities

**Capability.** Module-function data helpers (conversion, symbolization, time/date coercion) consumed across the whole library.

Treat this as a leaf dependency of most other subtrees. It owns no domain policy; it only normalizes data shapes. Consumers include tool schema building, Model::Info construction, Gemini schema conversion, and legacy persistence.

**Depended on by.**

- [Attachments & Images](r1-content-media.md) · model-inferred · 0 edge(s)
- [Gemini Chat & Schema](r1-gemini-chat.md) · graph-confirmed · 8 edge(s)
- [Legacy acts\_as Support](r1-legacy-acts-as.md) · graph-confirmed · 1 edge(s)
- [Model Metadata Objects](r1-model-metadata.md) · graph-confirmed · 2 edge(s)
- [OpenAI Tools](r1-openai-tools.md) · graph-confirmed · 1 edge(s)
- [Tool Definition DSL](r1-tool-dsl.md) · graph-confirmed · 3 edge(s)
- [Gemini Tools](r1-gemini-tools.md) · graph-only · 4 edge(s)
- [ChatMethods Persistence](r2-chat-persistence.md) · graph-only · 1 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 1 edge(s)
- [Anthropic Adapter](r2-provider-anthropic.md) · graph-only · 1 edge(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Units (1)

<a id="u-add7cf7f30e5"></a>
### `utils-utils-helpers`

`def hash_get(hash, key)` · [lib/ruby_llm/utils.rb:L8-L10][f1]

Module-function data helpers used across the library.

`hash_get(hash, key)` looks up `key.to_sym` then `key.to_s`, returning the first hit or nil. `to_safe_array` returns Arrays unchanged, wraps a Hash in a one-element array, and otherwise uses `Array(item)` (nil becomes []). `to_time`/`to_date` return nil for falsy values, pass through Time/Date instances, and otherwise parse `value.to_s` with `Time.parse`/`Date.parse`, so unparseable strings raise ArgumentError from stdlib. `deep_merge` merges overrides into original recursively: only when both sides are Hash does it recurse; otherwise the override wins (original is not mutated by `merge`). `deep_dup` recursively copies hashes (keys and values), arrays, and calls `.dup` on leaves, returning the value unchanged when dup raises TypeError (e.g. for Integers/symbols/frozen or non-dupable objects). `deep_stringify_keys` converts hash keys to strings recursively, maps arrays element-wise, converts Symbols to strings, and leaves other leaves alone; `deep_symbolize_keys` is the mirror, symbolizing keys only when they respond to `to_sym`, keeping them otherwise. All functions return new containers rather than mutating inputs; self-referential structures would recurse infinitely.

**Notes.**

- failure: deep_dup rescues only TypeError from .dup; other exceptions (e.g. NotImplementedError subclasses raised differently) propagate to the caller.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/utils.rb