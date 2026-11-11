# Gem entry and configuration

**Capability.** Provides the RubyLLM module facade forwarding to services, global Configuration, per-call Contexts, Zeitwerk setup, and provider registration.

The gem's front door: thin class-method forwarding (chat, embed, moderate, paint, transcribe), memoized global configuration with a configure block, isolated Contexts, logger, and the post-definition registration of all eleven provider adapters.

**Depends on.**

- [Chat conversation orchestration](chat-conversation-orchestration.md) · graph-confirmed · 2 edge(s)

Parent: [Chat Orchestration and Gem Facade](chat-orchestration-and-gem-facade.md)

## Units (11)

<a id="u-72a26d4e9dc3"></a>
### `configuration.rb-global-configuration`

`class Configuration` · [lib/ruby_llm/configuration.rb:L5-L51][f1]

Holds all RubyLLM configuration as attr_accessors: provider API keys/bases, default model IDs, model registry settings, Rails integration flag, connection retry/timeout options, and logging options.

initialize sets defaults: 300s timeout, 3 retries with 0.1s interval, backoff factor 2, randomness 0.5, no proxy; default chat/embedding/moderation/image/transcription models; registry file models.json beside this file with registry class 'Model'; use_new_acts_as false; log_file $stdout, DEBUG level only when ENV['RUBYLLM_DEBUG'] is set, stream debug only when RUBYLLM_STREAM_DEBUG is 'true'. instance_variables overrides Object's to strip ivars whose names end in _id, _key, _secret, or _token, so secrets are excluded (note this also hides non-secret ids like default_model's model_id-style fields).

**Notes.**

- field: All provider credentials default to nil and are set by the user.

**Uncertainties.**

- Consumers of the filtered instance_variables list are outside this batch, so the exact serialization effect is unproven.

<a id="u-c042fa69bc6f"></a>
### `context.rb-per-call-context`

`class Context` · [lib/ruby_llm/context.rb:L5-L8][f2]

Bundles a Configuration with per-call provider connections.

initialize stores the config and an empty connections hash (the hash is written but never read in this file). chat, embed, and paint forward all args, kwargs, and the block to Chat.new, Embedding.embed, and Image.paint respectively, injecting context: self so downstream calls use this configuration. connection_for simply returns the provider instance's connection.

calls: [Chat](../../catalog.json.gz), [Embedding.embed](../../catalog.json.gz), [image.rb-generated-image](gemini-and-media-integrations.md#u-639ed55c69c8)

**Uncertainties.**

- The @connections hash is never populated or read in this source; its intended lifecycle is unclear.

<a id="u-b9da7a2940a4"></a>
### `ruby_llm.rb-delegating-module-entrypoints`

`def chat(...)` · [lib/ruby_llm.rb:L46-L48][f3]

Thin forwarding class-methods: chat, embed, moderate, paint, and transcribe each pass all arguments (including keywords and blocks, via Ruby's (...) forwarding) straight to the corresponding service class — Chat.new, Embedding.embed, Moderation.moderate, Image.paint, Transcription.transcribe.

They add no logic, so their behavior, errors, and return values are entirely those of the delegate; the exact target classes are resolved by Zeitwerk autoloading and are not visible in this file.

<a id="u-18a7f14d498f"></a>
### `ruby_llm.rb-registry-accessors`

`def models` · [lib/ruby_llm.rb:L66-L68][f3]

models returns the singleton Models instance and providers returns the values (registered provider objects) of the Provider.providers hash; both are read-only lookups with no side effects.

<a id="u-131f0f30b3a9"></a>
### `Error`

`class Error < StandardError; end` · [lib/ruby_llm.rb:L37-L37][f3]

Defines RubyLLM::Error as a bare subclass of StandardError, the namespace's base exception type; it adds no behavior of its own.

<a id="u-54d2bff01bd5"></a>
### `RubyLLM.config`

`def config` · [lib/ruby_llm.rb:L78-L80][f3]

Lazily memoizes the global Configuration in @config on first call; subsequent calls return the same object, which is what makes configure's mutations persistent.

<a id="u-c02b4f1d4ee8"></a>
### `RubyLLM.configure`

`def configure` · [lib/ruby_llm.rb:L74-L76][f3]

Yields the memoized global Configuration to a block so callers can mutate it (e.g., set API keys); the block's return value is discarded and configure itself returns the block's result.

<a id="u-3e888b57f7f6"></a>
### `RubyLLM.context`

`def context` · [lib/ruby_llm.rb:L40-L44][f3]

Builds an isolated Context bound to a copy of the global configuration.

It dups the current config so later changes to RubyLLM.config do not leak into the context, and if a block is given it yields the duplicated config for per-context overrides before constructing the Context. Without a block it simply wraps the current configuration.

<a id="u-2eb9049c5207"></a>
### `RubyLLM.logger`

`def logger` · [lib/ruby_llm.rb:L82-L88][f3]

Lazily memoizes the module logger in @logger.

On first call it prefers config.logger if the configuration supplies one; otherwise it builds a stdlib Logger writing to config.log_file with progname 'RubyLLM' and level config.log_level. Note the fallback Logger is constructed with config values captured at creation time, so later config changes to log_file/log_level do not affect an already-created fallback logger.

<a id="u-2a8ec4b9190d"></a>
### `ruby_llm.rb module code (L1–L35)`

`module_region` · [lib/ruby_llm.rb:L1-L35][f3]

Sets up the gem's dependencies and Zeitwerk autoloading.

Requires HTTP, JSON, logging, MIME (marcel), Base64, and streaming parser libraries, then configures a gem Zeitwerk loader with custom inflections mapping filenames like 'ruby_llm', 'openai', 'vertexai', and 'UI' to their camelized constants. The loader ignores tasks/, generators/, and railtie.rb so they are not eagerly autoloaded; loader.setup then activates eager/normal loading for the rest of the gem.

<a id="u-aee1697ab019"></a>
### `ruby_llm.rb module code (L90–L107)`

`module_region` · [lib/ruby_llm.rb:L90-L107][f3]

After the module is defined, registers eleven provider adapters (anthropic, bedrock, deepseek, gemini, gpustack, mistral, ollama, openai, openrouter, perplexity, vertexai) into RubyLLM::Provider, making them available to models/providers lookups.

If Rails::Railtie is defined (i.e., under Rails), it additionally requires the railtie and the ActiveRecord acts_as extension; otherwise those integrations are skipped.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/configuration.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/context.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm.rb
