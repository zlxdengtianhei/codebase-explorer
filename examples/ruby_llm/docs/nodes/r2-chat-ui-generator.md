# Chat UI Generator

**Capability.** Scaffolds a Turbo/ broadcasting chat UI: guards on the message model, copies views, injects broadcasting, adds routes, and prints post-install notes.

Read to see the ordered generation steps and their guards; revoke behavior skips the post-install message.

**Depends on.**

- [GeneratorHelpers](r2-generator-helpers.md) · graph-confirmed · 3 edge(s) · The chat UI generator derives names and adapter settings through GeneratorHelpers.

Parent: [Rails Generators](r2-generators.md)

## Units (6)

<a id="u-76a8deef4fa6"></a>
### `ChatUIGenerator`

`class ChatUIGenerator < Rails::Generators::Base` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L9-L21][f1]

Rails generator class that scaffolds a Turbo-streaming chat UI from templates.

It includes GeneratorHelpers, sets source_root to a local templates directory, namespace ruby_llm:chat_ui, and declares an array argument model_mappings (default [], banner 'chat:ChatName message:MessageName ...'). Parsed mappings drive all names. Public methods run as generator steps in definition order. The class body folds two trivial steps: create_controllers templates chats/messages/models controllers into app/controllers/<underscored plural>_controller.rb, and create_jobs templates chat_response_job.rb to app/jobs/<variable_name>_response_job.rb. Boundary: names come from model_mappings parsing, so namespaced names reshape paths.

uses: [parse_model_mappings](r2-generator-helpers.md#u-5c99c008abdc)

**Uncertainties.**

- Exact step execution order depends on Rails generator conventions, not visible here.

<a id="u-ac2c1ff31158"></a>
### `RubyLLM.Generators.ChatUIGenerator.check_model_exists`

`def check_model_exists` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L21-L42][f1]

Guard step that aborts the chat UI generation when the message model file is missing.

It builds app/models/<message_model_name.underscore>.rb and returns silently if the file exists. Otherwise it assembles install/upgrade command hints, appending each 'chat:/message:/model:/tool_call:' argument only when the name differs from the default (Chat/Message/Model/ToolCall), then raises Thor::Error with a message telling the user to run ruby_llm:install or, for apps upgrading from <= 1.6.x, ruby_llm:upgrade_to_v1_7 with those arguments. The raise propagates to Thor, which reports the message as a generator error.

**Notes.**

- failure: Raising Thor::Error with a heredoc is the only failure path; the check is filesystem-based and does not verify constants or tables.

<a id="u-9e8c61b00f39"></a>
### `RubyLLM.Generators.ChatUIGenerator.create_views`

`def create_views # For namespaced models, use the proper Rails convention path` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L44-L72][f1]

Copies ERB view templates for chats, messages, and models into app/views/<underscored plural name>/.

Chat views include index/new/show/_form plus a partial named after the demodulized model (e.g. _chat.html.erb); message views include a demodulized partial, _tool_calls, _content, _form, and create.turbo_stream.erb; model views include index/show and a demodulized partial. For namespaced models the underscored plural path (e.g. llm/chats) follows Rails convention, and partial file names use only the demodulized, underscored name. No conditional logic; every template is copied unconditionally, overwriting existing files per Rails template behavior.

<a id="u-965240d6cb96"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_routes`

`def add_routes # For namespaced models, use Rails convention with namespace blocks` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L89-L126][f1]

Appends resource routes, taking two shapes depending on whether the chat model is namespaced.

If chat_model_name contains '::', it emits one namespace :<namespace> block containing model resources (index/show plus a collection post :refresh) and nested chat resources with message create-only routes, added via a single route call. Otherwise it makes two separate route calls: model resources using chat/message/model table names (index/show + collection post :refresh), then chat resources nesting message create routes. The demodulized plural resource names are used inside the namespace variant; table names in the flat variant.

**Uncertainties.**

- Behavior if only chat but not message/model names are namespaced is unhandled: the namespace branch demodulizes message/model resources but does not namespace them.

<a id="u-293cccf7f2f9"></a>
### `RubyLLM.Generators.ChatUIGenerator.add_broadcasting_to_message_model`

`def add_broadcasting_to_message_model` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L128-L169][f1]

Injects Turbo broadcasting code into the message model file.

It computes variable names for message and chat, the singularized chat table name as the association, and the pluralized message path. Two shapes: when the message model is namespaced, broadcasts_to gets an explicit partial: '<plural_path>/<demodulized name>' option; otherwise a bare broadcasts_to lambda targeting "<chat_var>_<chat_association>_id" is injected. A broadcast_append_chunk(content) method is also injected, broadcasting append with target '<msg_var>_<id>_content' and partial '<partial_path>/content'. Injection inserts before the final 'end' of app/models/<message underscore>.rb via inject_into_file. On Errno::ENOENT (file missing) it does not fail: it prints the model-not-found warning in yellow plus the exact code to add manually.

**Notes.**

- failure: rescue Errno::ENOENT catches only missing-file errors; other IO errors propagate.
- side_effect: Repeated generator runs will re-inject the broadcasting code because there is no presence check.

**Uncertainties.**

- The comment notes Turbo passes the record with the demodulized name for namespaced models; this is asserted, not verifiable here.

<a id="u-8dcfac437ffb"></a>
### `RubyLLM.Generators.ChatUIGenerator.display_post_install_message`

`def display_post_install_message` · [lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb:L171-L184][f1]

Prints post-install instructions, only when generator behavior is :invoke (skipped during revoke).

The suggested URL path uses the underscored plural chat name when the chat model is namespaced, otherwise chat_table_name. It prints a green success line, a cyan localhost:3000/<url_path> URL, and a blank line. No file modifications.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/generators/ruby_llm/chat_ui/chat_ui_generator.rb