# ActiveRecord & Rails Integration

**Capability.** Persistence-facing mixins that bridge database rows and in-memory RubyLLM objects: legacy chat/message acts_as support, modern message conversion, registry-record syncing, and the Rails railtie hook.

Use this subtree when models backed by ActiveRecord must talk to LLMs or expose registry data. Legacy support (acts_as_legacy) rebuilds chats from persisted rows and re-persists activity; MessageMethods and ModelMethods convert rows to value objects. The railtie integrates with Rails only when Rails::Railtie is loaded.

**Children.**

- [Legacy acts\_as Support](r1-legacy-acts-as.md) `r1-legacy-acts-as` · 8 unit(s)
- [Message Conversion](r1-message-methods.md) `r1-message-methods` · 2 unit(s)
- [Registry Record Sync](r1-model-registry-sync.md) `r1-model-registry-sync` · 2 unit(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Units (1)

<a id="u-acb5d0270dbf"></a>
### `Railtie`

`class Railtie < Rails::Railtie` · [lib/ruby_llm/railtie.rb:L6-L33][f1]

Rails integration hook, defined only when `Rails::Railtie` is already loaded (the whole file body is guarded by `if defined?(Rails::Railtie)`).

It registers three integrations: the 'ruby_llm.inflections' initializer adds the 'RubyLLM' acronym to the English inflector; the 'ruby_llm.active_record' initializer runs on ActiveRecord load and branches on `RubyLLM.config.use_new_acts_as` — when true it requires and includes `RubyLLM::ActiveRecord::ActsAs`, otherwise it requires and includes `ActsAsLegacy` and logs a deprecation warning about removal in RubyLLM 2.0.0 through Rails.logger; a `rake_tasks` block loads 'tasks/ruby_llm.rake'. The config read happens at ActiveRecord load time, not at boot, and missing rake task file or logger would raise during those hooks.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/railtie.rb