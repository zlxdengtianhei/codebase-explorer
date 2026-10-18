# Model Aliases

**Capability.** Class-level mapping of generic model aliases to provider-specific model ids loaded from a bundled JSON file.

Use Aliases to translate a friendly name into concrete provider ids. It is purely lookup data with no documented runtime behavior beyond lookup.

**Depended on by.**

- [Model Maintenance Rake Tasks](r1-model-maintenance-tasks.md) · model-inferred · 0 edge(s)

Parent: [Model Registry](r1-model-registry.md)

## Units (1)

<a id="u-53bd7c18c313"></a>
### `Aliases`

`class Aliases` · [lib/ruby_llm/aliases.rb:L5-L6][f1]

Maps generic model aliases to provider-specific model ids loaded from a bundled JSON file, all as class-level singleton methods.

`resolve(model_id, provider)` returns the id unchanged when it is not a known alias; when a provider is given it returns `aliases[model_id][provider.to_s]` or falls back to the original id; without a provider it returns the first mapped value (`values.first`) or the original id. `aliases` memoizes `load_aliases` in `@aliases`. `load_aliases` JSON-parses `aliases.json` (path expanded from `__dir__` by `aliases_file`) if the file exists, otherwise returns `{}`; JSON parse or read errors propagate. `reload!` overwrites the memo with a fresh read, so later `resolve` calls see the reloaded data.

**Uncertainties.**

- The nesting alias -> {provider_string => id} is inferred from `aliases[model_id][provider.to_s]`; the JSON file itself is not in the supplied source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/aliases.rb