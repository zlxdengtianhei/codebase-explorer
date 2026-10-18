# acts_as Declarations

**Capability.** Declares ActiveRecord classes as chat, message, model-registry, or tool-call records: includes behavior modules, records association/class-name attributes, and rebinds RubyLLM::Models to the ActiveRecord registry.

Read to see exactly what each acts_as_* call sets up on the including class and its defaults.

**Depends on.**

- [Gemini Adapter](r2-provider-gemini.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [ChatMethods Persistence](r2-chat-persistence.md) · model-inferred · 0 edge(s)
- [Rake Tasks](r2-rake-tasks.md) · model-inferred · 0 edge(s)
- [v1.7 Upgrade Generator](r2-upgrade-generator.md) · model-inferred · 0 edge(s)

Parent: [ActiveRecord Integration](r2-active-record-integration.md)

## Units (5)

<a id="u-ce86173f9605"></a>
### `acts_as_chat`

`def acts_as_chat(messages: :messages, message_class: nil, messages_foreign_key: nil, …` · [lib/ruby_llm/active_record/acts_as.rb:L34-L69][f1]

Declares the calling class a chat model: includes ChatMethods, records messages_association_name and model_association_name as class attributes, and derives message_class/model_class by classifying the association names when not given.

Declares a has_many messages ordered by created_at asc with dependent: :destroy and an optional belongs_to model. Delegates add_message to to_llm and defines messages_association, model_association and a model_association= writer that forward to the configured association names.

imports: [ChatMethods][f2]

<a id="u-d64e895db97c"></a>
### `acts_as_message`

`def acts_as_message(chat: :chat, chat_class: nil, chat_foreign_key: nil, touch_chat: …` · [lib/ruby_llm/active_record/acts_as.rb:L90-L143][f1]

Declares the calling class a message record: includes MessageMethods and records chat/tool_calls/model association names plus derived chat_class, tool_call_class and model_class as class attributes.

Declares belongs_to chat (optional touch), has_many tool_calls with dependent: :destroy, an optional belongs_to parent_tool_call whose foreign key is derived by singularizing the tool_calls association name, has_many :tool_results through tool_calls sourced from :result with class_name equal to the message class itself, and an optional belongs_to model. Delegates tool_call? and tool_result? to to_llm and defines chat_association, tool_calls_association and model_association forwarding methods.

**Notes.**

- contract: tool_results rows are instances of the declaring message class (class_name: name).

imports: [MessageMethods][f3]

<a id="u-f9481ae33026"></a>
### `acts_as_model`

`def acts_as_model(chats: :chats, chat_class: nil, chats_foreign_key: nil)` · [lib/ruby_llm/active_record/acts_as.rb:L71-L88][f1]

Declares the calling class a model-registry record: includes ModelMethods, stores chats_association_name and chat_class (default chats.to_s.classify) as class attributes, validates presence of model_id (unique scoped to provider), provider and name, declares has_many chats, and defines chats_association forwarding to the configured association.

imports: [ModelMethods][f4]

<a id="u-f3a66ef4538f"></a>
### `acts_as_tool_call`

`def acts_as_tool_call(message: :message, message_class: nil, message_foreign_key: nil…` · [lib/ruby_llm/active_record/acts_as.rb:L145-L170][f1]

Declares the calling class a tool-call record: records message/result association names and classes as class attributes, with result_class defaulting to the resolved message_class.

Declares a required belongs_to message and a has_one result with dependent: :nullify, plus message_association and result_association forwarding methods. Unlike the other acts_as_* macros it includes no behavior module.

<a id="u-8ba574a3b696"></a>
### `acts_as-rubyllm-models-monkey-patch`

`def self.included(base)` · [lib/ruby_llm/active_record/acts_as.rb:L10-L14][f1]

Rebinds RubyLLM::Models model loading to the ActiveRecord registry when ActsAs is included.

The included hook class_evals RubyLLM::Models so the class method load_models calls read_from_database, which constantizes RubyLLM.config.model_registry_class (a String is constantized) and maps all records through to_llm; any StandardError from that path is logged at debug level and load_models falls back to read_from_json. Instance method load_from_database! replaces the in-memory @models cache with the database snapshot.

**Uncertainties.**

- Behavior of read_from_json and of the configured model_registry_class is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/chat_methods.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/message_methods.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/model_methods.rb