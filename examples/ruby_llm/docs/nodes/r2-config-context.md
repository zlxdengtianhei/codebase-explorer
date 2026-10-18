# Configuration and Context

**Capability.** Owns the mutable global settings object (credentials, endpoints, defaults, retries, logging) and the per-call Context that lets a call group override the global config.

Read Configuration to see every tunable; read Context to see how scoped overrides travel through chat, embedding, and image calls.

**Depends on.**

- [Provider Connection](r2-connection.md) · model-inferred · 0 edge(s)
- [Chat Session & Completion Loop](r1-chat-session.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Public API & Bootstrap](r1-public-api-bootstrap.md) · graph-only · 2 edge(s)

Parent: [Core Runtime](r2-core-runtime.md)

## Units (2)

<a id="u-5df427d3c359"></a>
### `Configuration`

`class Configuration` · [lib/ruby_llm/configuration.rb:L5-L51][f1]

Holds every provider credential/endpoint, default model, retry/timeout, registry, Rails-integration, and logging setting as attr_accessors, so values can be overridden after construction.

`initialize` sets defaults: timeout 300s, 3 retries, 0.1s interval, backoff factor 2, 0.5 interval randomness, nil proxy; OpenAI-hosted default models (gpt-4.1-nano, text-embedding-3-small, omni-moderation-latest, gpt-image-1, whisper-1); registry file at models.json beside this file with registry class 'Model'; legacy acts_as off. Logging defaults to $stdout, level DEBUG when ENV['RUBYLLM_DEBUG'] is set (otherwise INFO), and stream debug only when ENV['RUBYLLM_STREAM_DEBUG'] equals 'true'. The overridden `instance_variables` calls super and rejects any ivar whose name matches `_id`, `_key`, `_secret`, or a trailing `_token`, redacting credentials from reflective serialization.

**Uncertainties.**

- The filter regex is unanchored for `_id|_key|_secret` (only `_token$` is anchored), so names containing those substrings anywhere would be hidden; with the declared accessor names this only matches at the end.

<a id="u-5801d9966ac3"></a>
### `Context`

`class Context` · [lib/ruby_llm/context.rb:L5-L8][f2]

Carries a per-call Configuration through chat, embedding, and image calls so a group of calls shares one config instead of the global.

`initialize` stores the config and an empty `@connections` hash that is never read in this file. `chat` constructs `Chat.new(*args, **kwargs, context: self, &)` forwarding everything; `embed` delegates to `Embedding.embed(..., context: self)`; `paint` delegates to `Image.paint(..., context: self)`, letting those entry points pick up this config via `context&.config`. `connection_for(provider_instance)` returns that instance's `connection`; it does not consult `@connections`.

**Uncertainties.**

- `@connections` is initialized but unused within this file; whether it is populated elsewhere cannot be established from this source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/configuration.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/context.rb