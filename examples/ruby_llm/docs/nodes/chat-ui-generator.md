# Chat UI Generator

**Capability.** Scaffolds Rails chat UI controllers, views, jobs, routes, and Turbo broadcasting from configured model names.

Observed units show template copying, route/model checks, namespacing, and post-install messaging. Use this module when generating a Rails chat UI.

**Depends on.**

- [Generator Naming Helpers](generator-naming-helpers.md) · graph-confirmed · 3 edge(s) · Chat UI generator uses generator naming helpers to derive model names, namespaces, and routes.

Parent: [Rails Generator Tooling](rails-generator-tooling.md)

## Units (8)

<a id="u-da5574848fe2"></a>
### `chat_ui_generator.rb-chat-ui-generator`

`class ChatUIGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L9-L21][f1]

Rails generator that scaffolds a chat UI for RubyLLM, using shared generator helpers and a template source root.

It exposes a model-mapping argument and delegates model existence, view/controller/job creation, routes, broadcasting, and post-install messaging to its steps.

<a id="u-293cccf7f2f9"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_broadcasting_to_message_model`

`def add_broadcasting_to_message_model` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L128-L169][f1]

Adds Turbo broadcasting code to the message model, with a namespaced partial option when the message model is namespaced.

It injects before the literal `end\n` string, not anchored to the model's final end; if the model file is missing, it rescues Errno::ENOENT and prints the code as guidance instead of writing. The injected code includes broadcasts_to using the chat association id and a broadcast_append_chunk method targeting the content partial.

<a id="u-965240d6cb96"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_routes`

`def add_routes # For namespaced models, use Rails convention with namespace blocks` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L89-L126][f1]

Adds Rails routes for models, chats, and messages, choosing namespaced or top-level route blocks from the chat model name.

If the chat model contains a namespace separator, it emits one namespace block using demodulized plural resources and a model refresh collection route; otherwise it adds separate model and chat/message route blocks using table names.

<a id="u-ac2c1ff31158"></a>
### `RubyLLM.Generators.ChatUIGenerator.check_model_exists`

`def check_model_exists` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L21-L42][f1]

Verifies the message model file exists before scaffolding and raises a Thor error with install/upgrade guidance when it does not.

It builds optional mapping arguments only for non-default chat, message, model, and tool-call names; if the file exists it returns without side effects.

<a id="u-106cce23795c"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_controllers`

`def create_controllers # For namespaced models, use the proper Rails convention path` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L74-L83][f1]

Copies chat, message, and model controller templates into Rails-convention controller paths derived from the configured model names.

Namespaced models use underscored pluralized directories, producing controller files under those paths.

<a id="u-709e966eea8b"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_jobs`

`def create_jobs` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L85-L87][f1]

Copies the chat response job template into a job file named from the configured chat model's variable name.

It has no branching and writes one generated job file.

<a id="u-9e8c61b00f39"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_views`

`def create_views # For namespaced models, use the proper Rails convention path` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L44-L72][f1]

Copies chat, message, and model view templates into Rails-convention view directories derived from the configured model names.

It writes index/new/show/partial/form/turbo-stream files; namespaced models use underscored pluralized directories and demodulized partial names.

<a id="u-8dcfac437ffb"></a>
### `RubyLLM.Generators.ChatUIGenerator.display_post_install_message`

`def display_post_install_message` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L171-L184][f1]

Prints the post-install chat UI message only when the generator is invoking, not revoking.

It chooses a URL path from the namespaced underscored plural chat name or the chat table name, then prints success and localhost URL lines.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb
