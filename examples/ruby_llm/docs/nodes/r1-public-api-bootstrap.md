# Public API & Bootstrap

**Capability.** Bootstraps the gem (dependencies, Zeitwerk autoloading, provider registration) and exposes the RubyLLM module facade that delegates one-to-one to library components, plus an isolated-context entry point and the base Error type.

Read lib/ruby_llm.rb first to see how the library is assembled and which entry points exist. RubyLLM.context creates an isolated configuration copy; RubyLLM::Error is the base error type. The facade delegates to Chat, Image, Models, and other components.

**Depends on.**

- [Chat Session & Completion Loop](r1-chat-session.md) · graph-confirmed · 1 edge(s) · The RubyLLM facade delegates to Chat, constructing a chat session for callers.
- [Configuration and Context](r2-config-context.md) · graph-only · 2 edge(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Units (5)

<a id="u-fb85d6d61ce4"></a>
### `ruby_llm.rb-module-facade`

`def chat(...)` · [lib/ruby_llm.rb:L46-L48][f1]

Singleton-class facade methods that delegate one-to-one to library components.

chat forwards all arguments to Chat.new and returns a new Chat; embed, moderate, paint, and transcribe forward to Embedding.embed, Moderation.moderate, Image.paint, and Transcription.transcribe respectively. models returns the Models.instance singleton, and providers returns the values of the Provider.providers registry hash. configure yields the shared global config for mutation, while config lazily memoizes a single Configuration instance in @config. logger lazily memoizes @logger: it uses config.logger when one is configured, otherwise builds a standard Logger writing to config.log_file with progname 'RubyLLM' and config.log_level. Both config and logger are cached per-process, so later configure changes to log_file/log_level are not picked up once logger has been created.

calls: [RubyLLM.Chat.initialize](r1-chat-session.md#u-986c171f6698), [Configuration](r2-config-context.md#u-5df427d3c359); uses: [embedding.rb-embedding](r2-content-value-objects.md#u-0061f299adf1), [Moderation](r2-content-value-objects.md#u-665bdee2e65d), [Image](r1-content-media.md#u-5f36460b61e5)

**Uncertainties.**

- Whether embed/moderate/paint resolve to the class-level methods on Embedding/Moderation/Image shown in the graph or Context variants; only the constant-name call form is visible here.
- Exact behavior of the delegated methods is outside this file.

<a id="u-ddd15096bdcd"></a>
### `ruby_llm.rb-zeitwerk-bootstrap`

`group` · [lib/ruby_llm.rb:L1-L35][f1]

Bootstraps the gem: requires runtime dependencies, configures Zeitwerk autoloading with custom inflections, and registers all built-in providers after the module is defined.

The inflector maps snake_case files (ruby_llm, openai, api, bedrock, etc.) to their constant forms; the tasks, generators, and railtie directories are excluded from eager autoload. At the end, each provider class is registered under a symbol via RubyLLM::Provider.register, and when Rails::Railtie is defined the railtie and ActiveRecord acts_as extension are additionally required. Any missing provider constant or failed require surfaces as a NameError/LoadError at load time.

uses: [lib/ruby_llm.rb:RubyLLM](r1-public-api-bootstrap.md#u-ac1c19d9eaa3)

<a id="u-131f0f30b3a9"></a>
### `Error`

`class Error < StandardError; end` · [lib/ruby_llm.rb:L37-L37][f1]

Base error type for the library; an empty StandardError subclass with no added behavior.

<a id="u-3e888b57f7f6"></a>
### `RubyLLM.context`

`def context` · [lib/ruby_llm.rb:L40-L44][f1]

Creates an isolated Context whose configuration starts as a shallow copy of the global config; an optional block mutates only that copy before it is handed to Context.new.

The global configuration is therefore never affected by per-context overrides, but because the copy is shallow, mutated nested objects could leak back (boundary not established here). Without a block, the context shares the copied default settings.

**Notes.**

- side_effect: Global config is never mutated; only the dup'd context_config is passed to Context.

calls: [ruby_llm.rb-module-facade](r1-public-api-bootstrap.md#u-fb85d6d61ce4), [Context](r2-config-context.md#u-5801d9966ac3)

**Uncertainties.**

- Shallow copy semantics of config.dup depend on Configuration internals not in this file.

<a id="u-ac1c19d9eaa3"></a>
### `lib/ruby_llm.rb:RubyLLM`

`module RubyLLM` · [lib/ruby_llm.rb:L36-L37][f1]

Defines the RubyLLM namespace and its single Error class, then opens the singleton class to expose the module-level facade methods documented in their own units.

group: [Error](r1-public-api-bootstrap.md#u-131f0f30b3a9)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm.rb