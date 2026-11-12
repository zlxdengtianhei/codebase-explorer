# Core Chat Configuration

**Capability.** Defines global configuration, per-call context, chat orchestration, callbacks, tool execution, and high-level API forwarding.

Observed units show RubyLLM core configuration, chat object, context, and top-level operation forwarding. They also show chat completion/tool handling and configuration/autoload setup.

**Depends on.**

- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 1 edge(s)

**Depended on by.**

- [ActiveRecord Chat Persistence](activerecord-chat-persistence.md) · graph-confirmed · 2 edge(s) · ActiveRecord chat persistence uses core chat configuration for chat setup and orchestration.

Parent: [Chat Persistence And Orchestration](chat-persistence-and-orchestration.md)

## Units (20)

<a id="u-197385b8fb91"></a>
### `chat.rb-ask-and-alias`

`def ask(message = nil, with: nil, &)` · [lib/ruby_llm/chat.rb:L33-L36][f1]

Sends a user message and completes the conversation.

ask builds content from the message and attachments, adds a user message, then calls complete. The alias say has the same behavior.

<a id="u-d05763fd2018"></a>
### `chat.rb-chat-callbacks`

`def on_new_message(&block)` · [lib/ruby_llm/chat.rb:L100-L103][f1]

Registers callbacks for new message, end message, tool call, and tool result events.

Each setter stores the block under its event key and returns self; no callback is invoked here.

<a id="u-4b3f925f7621"></a>
### `chat.rb-chat-class`

`class Chat` · [lib/ruby_llm/chat.rb:L5-L10][f1]

Represents a conversation with an AI model, including messages, tools, request options, callbacks, and provider connection.

It includes Enumerable; each delegates to messages.each. instance_variables hides @connection and @config from introspection. The class coordinates model resolution, completion, streaming callbacks, and tool execution; individual builders and completion behavior are documented separately.

<a id="u-7ad41d62d255"></a>
### `chat.rb-chat-configuration-builders`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/chat.rb:L40-L45][f1]

Configures chat state and returns self for chaining.

- with_instructions: removes existing system messages when replace is true, then adds a system message.
- with_tool: instantiates a class tool or uses an instance, storing it by name symbol.
- with_tools: clears tools when replace is true, compacts the list, and adds each tool.
- with_model: resolves model/provider through Models.resolve with config and sets the connection.
- with_temperature: stores the temperature.
- with_context: stores context/config and re-resolves the current model with provider slug and assume_exists true.
- with_params: replaces params with the keyword arguments.
- with_headers: replaces headers with the keyword arguments.
- with_schema: instantiates a class schema; if it responds to to_json_schema it stores [:schema], otherwise it stores the value as is.

<a id="u-4b1c6650ec29"></a>
### `chat.rb-message-mutation`

`def add_message(message_or_attributes)` · [lib/ruby_llm/chat.rb:L156-L160][f1]

Appends messages to the conversation and clears them.

add_message reuses a Message instance or constructs one from attributes, appends it, and returns it. reset_messages! clears the messages array.

<a id="u-ec43293fe398"></a>
### `chat.rb-tool-and-content-helpers`

`def execute_tool(tool_call)` · [lib/ruby_llm/chat.rb:L207-L211][f1]

Looks up and invokes tools, builds content objects, and recognizes content-like values.

execute_tool finds tools by symbolized tool-call name and calls the tool with its arguments; this source has no missing-tool guard. build_content returns the message when it is content-like, otherwise constructs Content with message and attachments. content_like? is true for Content or Content::Raw.

<a id="u-72a26d4e9dc3"></a>
### `configuration.rb-global-configuration`

`class Configuration` · [lib/ruby_llm/configuration.rb:L5-L51][f2]

Global mutable configuration object for provider credentials, defaults, retries, registry, Rails integration, and logging.

Initialization sets request timeout 300, max retries 3, retry interval 0.1, backoff factor 2, randomness 0.5, and no HTTP proxy; default models are gpt-4.1-nano, text-embedding-3-small, omni-moderation-latest, gpt-image-1, and whisper-1. The registry file is models.json beside the source, registry class is Model, new acts-as is false, log file is stdout, log level is DEBUG when RUBYLLM_DEBUG is truthy else INFO, and stream debug is true only when RUBYLLM_STREAM_DEBUG equals 'true'. API key fields are not assigned here. The instance-variable filter removes names containing _id, _key, or _secret anywhere, and names ending in _token; the first three are not anchored.

<a id="u-c042fa69bc6f"></a>
### `context.rb-per-call-context`

`class Context` · [lib/ruby_llm/context.rb:L5-L8][f3]

Holds per-call configuration and delegates chat, embedding, and image operations with that context.

Initialization stores the config and an empty connections hash; no shown method reads or writes that hash. Chat construction forwards arguments, keywords, and block with the context attached. Embedding and image painting delegate to their class entrypoints with the context attached. Connection lookup simply returns the provider instance's connection.

calls: [Chat#initialize](../../catalog.json.gz), [Embedding.embed](../../catalog.json.gz), [Image.paint](../../catalog.json.gz)

<a id="u-ee057edf6913"></a>
### `ruby_llm.rb-configuration-access`

`def configure` · [lib/ruby_llm.rb:L74-L76][f4]

Provides the shared configuration object and a block-based mutation hook.

config memoizes Configuration.new in @config; configure yields that same object and returns the block's result. Calling configure without a block raises LocalJumpError from yield, and block exceptions propagate.

<a id="u-2b1bbd1e8bdf"></a>
### `ruby_llm.rb-operation-entrypoints`

`def chat(...)` · [lib/ruby_llm.rb:L46-L48][f4]

Forwards high-level AI operations to their implementation classes without local validation or rescue.

chat constructs Chat; embed, moderate, paint, and transcribe call the corresponding class methods. All arguments and blocks pass through via forwarding, and target exceptions propagate.

<a id="u-18a7f14d498f"></a>
### `ruby_llm.rb-registry-accessors`

`def models` · [lib/ruby_llm.rb:L66-L68][f4]

Exposes the model registry and registered provider list.

models returns Models.instance; providers returns the values of Provider.providers. Neither method rescues, and the source does not establish whether Models.instance has side effects.

**Uncertainties.**

- Whether Models.instance has side effects is not shown by this source.

<a id="u-131f0f30b3a9"></a>
### `Error`

`class Error < StandardError; end` · [lib/ruby_llm.rb:L37-L37][f4]

Defines RubyLLM::Error as a StandardError subclass for library-specific exceptions.

It adds no methods or custom behavior.

<a id="u-3e888b57f7f6"></a>
### `RubyLLM.context`

`def context` · [lib/ruby_llm.rb:L40-L44][f4]

Builds a per-call Context from a duplicated global configuration, optionally mutated by a block.

The block receives the duplicate; without a block the duplicate is used unchanged. It returns the new Context and does not rescue block or construction errors.

<a id="u-2eb9049c5207"></a>
### `RubyLLM.logger`

`def logger` · [lib/ruby_llm.rb:L82-L88][f4]

Returns a memoized logger, preferring the configured logger and otherwise constructing one.

If config.logger is truthy it is used; otherwise a Logger is built with config.log_file, progname 'RubyLLM', and config.log_level. The result is stored in @logger, so later calls reuse it without re-evaluating configuration; construction errors propagate.

<a id="u-2a8ec4b9190d"></a>
### `ruby_llm.rb module code (L1–L35)`

`module_region` · [lib/ruby_llm.rb:L1-L35][f4]

Configures the gem's load path before RubyLLM is defined by requiring dependencies and installing a Zeitwerk autoloader.

It creates a gem loader, applies custom inflections, ignores tasks, generators, and the railtie file, then calls setup to install autoloading; it does not eager-load the gem. Require or loader errors propagate.

<a id="u-aee1697ab019"></a>
### `ruby_llm.rb module code (L90–L107)`

`module_region` · [lib/ruby_llm.rb:L90-L107][f4]

Registers built-in providers and conditionally loads Rails integration.

It registers anthropic, bedrock, deepseek, gemini, gpustack, mistral, ollama, openai, openrouter, perplexity, and vertexai; if Rails::Railtie is defined, it requires the railtie and active_record/acts_as files. Registration mutates the provider registry, and require errors propagate.

<a id="u-115f6c6ea65d"></a>
### `RubyLLM.Chat.complete`

`def complete(&) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L124-L154][f1]

Runs a completion through the provider and updates conversation state, callbacks, schema parsing, and tool handling.

It calls provider.complete with messages, tools, temperature, model, params, headers, schema, and a streaming wrapper. Without a block it calls the new-message callback. If a schema is set and response content is a String, it parses JSON and keeps the string on JSON::ParserError. It adds the response message, calls the end-message callback, then either handles tool calls or returns the response.

<a id="u-1b19f1a82466"></a>
### `RubyLLM.Chat.handle_tool_calls`

`def handle_tool_calls(response, &) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L188-L205][f1]

Executes every tool call in a response, appends tool messages, and either returns the last halt result or recurses into completion.

It iterates all response tool calls without breaking. For each it calls the new-message callback, tool-call callback, execute_tool, and tool-result callback; it uses Halt content as the payload when the result is a Halt, otherwise the result, converts non-content-like payloads to strings, adds a tool message with the tool_call_id, and calls the end-message callback. It records halt_result for each Halt, so a later Halt overwrites an earlier one. After the loop it returns halt_result if any Halt occurred, otherwise it calls complete. Remaining tool calls still execute; only the final recursion is skipped, and the last Halt result is returned.

<a id="u-986c171f6698"></a>
### `RubyLLM.Chat.initialize`

`def initialize(model: nil, provider: nil, assume_model_exists: false, context: nil)` · [lib/ruby_llm/chat.rb:L10-L31][f1]

Initializes a chat with model/provider resolution, empty conversation state, and callback slots.

If assume_model_exists is true without a provider, it raises ArgumentError. It uses context config or RubyLLM.config, resolves the model, then initializes temperature, messages, tools, params, headers, schema, and callbacks.

<a id="u-5429c02071a1"></a>
### `RubyLLM.Chat.wrap_streaming_block`

`def wrap_streaming_block(&block)` · [lib/ruby_llm/chat.rb:L172-L186][f1]

Wraps a streaming block so the new-message callback fires once on the first chunk.

It returns nil without a block; otherwise it returns a proc that sets first_chunk_received, calls the new-message callback once, then forwards each chunk to the original block.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/configuration.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/context.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm.rb
