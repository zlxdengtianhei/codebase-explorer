# Chat UI scaffolding generator

**Capability.** Scaffolds a Turbo-streaming chat UI: controllers, views, a response job, routes, and Turbo broadcasting hooks injected into the message model.

A Rails generator producing a ready-to-visit chat interface. It templates controllers, ERB views, and a response job, injects routes and Turbo broadcast declarations, and guards on the message model file existing. Prints the URL to visit on success.

**Depends on.**

- [Generator shared helpers](generator-shared-helpers.md) · graph-confirmed · 3 edge(s) · The chat UI generator uses shared helpers for naming, model mappings, and acts_as declarations.

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (8)

<a id="u-76a8deef4fa6"></a>
### `ChatUIGenerator`

`class ChatUIGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L9-L21][f1]

Rails generator (namespace ruby_llm:chat_ui) that scaffolds a Turbo-streaming chat UI: views, controllers, a response job, routes, and broadcasting hooks, parameterized by chat/message/model/tool_call model-name mappings.

<a id="u-293cccf7f2f9"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_broadcasting_to_message_model`

`def add_broadcasting_to_message_model` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L128-L169][f1]

Injects Turbo broadcasting declarations and a broadcast_append_chunk method into the message model file before its final end.

For namespaced message models it emits broadcasts_to with an explicit partial path (pluralized underscored path plus demodulized name); otherwise a plain broadcasts_to lambda keyed on the chat association id. If the model file is absent (Errno::ENOENT from inject_into_file), it rescues and prints the intended code in yellow instead of failing.

<a id="u-965240d6cb96"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_routes`

`def add_routes # For namespaced models, use Rails convention with namespace blocks` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L89-L126][f1]

Injects REST routes via the Rails route method.

If the chat model is namespaced, it emits one namespace block containing model resources (index/show plus collection post :refresh) and nested chat resources with message creation. Otherwise it emits two separate route snippets: model resources with the refresh collection action, and chat resources nesting message creation, using table names.

<a id="u-ac2c1ff31158"></a>
### `RubyLLM.Generators.ChatUIGenerator.check_model_exists`

`def check_model_exists` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L21-L42][f1]

Guards the generator by verifying the message model file exists at app/models/<underscored name>.rb; if missing it raises Thor::Error with a tailored remediation message listing the install or upgrade_to_v1_7 command, appending only the non-default model mapping arguments (chat:/message:/model:/tool_call: when they differ from Chat/Message/Model/ToolCall).

<a id="u-106cce23795c"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_controllers`

`def create_controllers # For namespaced models, use the proper Rails convention path` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L74-L83][f1]

Templates the chats, messages, and models controllers into app/controllers using pluralized underscored model names as file paths (e.g. app/models-style namespacing maps to nested controller paths).

<a id="u-709e966eea8b"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_jobs`

`def create_jobs` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L85-L87][f1]

Templates the chat response job to app/jobs/<variable_name_for(chat)>_response_job.rb, converting namespaced names like LLM::Chat to llm_chat_response_job.

<a id="u-9e8c61b00f39"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_views`

`def create_views # For namespaced models, use the proper Rails convention path` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L44-L72][f1]

Copies ERB templates for chat, message, and model views into app/views, deriving directory paths from the pluralized underscored model names and partial file names from the demodulized underscored model names, so namespaced models land on Rails-convention paths.

<a id="u-8dcfac437ffb"></a>
### `RubyLLM.Generators.ChatUIGenerator.display_post_install_message`

`def display_post_install_message` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L171-L184][f1]

After invocation (skipped on revert since behavior != :invoke), prints a success message and the URL to visit, using the pluralized underscored chat name for namespaced models or the chat table name otherwise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb
