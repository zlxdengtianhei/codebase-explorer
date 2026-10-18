# Legacy acts_as Support

**Capability.** Declaration macros plus chat/message legacy methods: wrappers persist settings as message rows, persistence plumbing syncs in-memory activity into rows, cleanup repairs post-failure state, and extraction helpers back MessageLegacyMethods#to_llm.

Use this for pre-modern chat models declared via acts_as macros storing configuration in instance variables. to_llm builds a memoized in-memory chat from persisted state and wires persistence callbacks; complete delegates to it. Message rows convert to RubyLLM::Message via to_llm and its extraction helpers.

**Depends on.**

- [Chat Session & Completion Loop](r1-chat-session.md) · graph-confirmed · 1 edge(s) · Legacy ChatLegacyMethods.to_llm builds an in-memory Chat from persisted rows and delegates complete to it.
- [Shared Utilities](r1-shared-utilities.md) · graph-confirmed · 1 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 2 edge(s)

Parent: [ActiveRecord & Rails Integration](r1-active-record-integration.md)

## Units (8)

<a id="u-49418c9ac7e7"></a>
### `acts_as_legacy-acts-as-declarations`

`def acts_as_chat(message_class: 'Message', tool_call_class: 'ToolCall')` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L10-L23][f1]

Legacy declaration macros storing configuration in instance variables on the declaring class rather than class attributes.

acts_as_chat includes ChatLegacyMethods, sets @message_class/@tool_call_class (defaults 'Message'/'ToolCall'), declares has_many :messages ordered by created_at asc with inverse_of :chat and dependent: :destroy, and delegates add_message to to_llm. acts_as_message includes MessageLegacyMethods, derives @chat_foreign_key and @tool_call_foreign_key via Inflector.foreign_key when omitted, declares belongs_to :chat (inverse_of :messages, optional touch), has_many :tool_calls with dependent: :destroy, optional belongs_to :parent_tool_call (inverse_of :result), has_many :tool_results through tool_calls sourced from :result with class_name @message_class, and delegates tool_call?/tool_result? to to_llm. acts_as_tool_call declares belongs_to :message (inverse_of :tool_calls) and has_one :result (class_name @message_class, inverse_of :parent_tool_call, dependent: :nullify), deriving foreign keys with Inflector.foreign_key when omitted. Exposed attr_readers: tool_call_class on chat classes; chat_class, tool_call_class, chat_foreign_key, tool_call_foreign_key on message classes.

**Uncertainties.**

- Hardcoded default class names ('Message', 'Chat', 'ToolCall') mean misnamed models silently bind to the wrong classes; schema mismatch behavior is not shown here.

<a id="u-f7a92d16b4ef"></a>
### `acts_as_legacy-chat-legacy-wrappers`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L105-L112][f1]

Configuration and callback wrappers on legacy chat models that persist settings as message rows and/or forward to the underlying in-memory chat.

with_instructions wraps in a transaction: if replace is true it destroys existing system-role messages, then creates a system message with the instructions, and finally applies with_instructions on to_llm, returning self. with_model additionally persists the change by updating model_id from to_llm.with_model(...).model.id. with_context rebuilds the memoized chat through to_llm(context: context) without persisting anything. with_tool/with_tools/with_temperature/with_params/with_headers/with_schema/on_tool_call/on_tool_result purely forward arguments (via ...) to to_llm and return self. on_new_message and on_end_message first force to_llm, read the chat's existing callback from the @on instance variable, and register a new callback that invokes the existing callback then the given block, so both run. create_user_message creates a user-role message row and persists attachments when with: is present; ask (aliased say) creates the user message then calls complete with the given block. Exceptions from destroy_all/create! inside with_instructions abort the transaction, leaving existing system messages intact; failures propagate to the caller.

**Uncertainties.**

- The @on hash structure and callback semantics of the underlying chat object are defined in lib/ruby_llm/chat.rb, not here.

<a id="u-0b7cbfbc22b5"></a>
### `acts_as_legacy-chat-legacy-persistence`

`def setup_persistence_callbacks` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L236-L244][f1]

Persistence plumbing that syncs in-memory chat activity into message and tool-call rows (private).

setup_persistence_callbacks registers persist_new_message on the chat's new-message callback and persist_message_completion on its end-message callback, guarded by the @_persistence_callbacks_setup instance variable so registration happens once; it returns the chat. persist_new_message creates an empty assistant-role message row and stores it in @message. persist_message_completion returns immediately if the message is nil; otherwise inside a transaction it resolves a database tool_call_id via find_tool_call_id when the message carries one, normalizes content (RubyLLM::Content becomes its text with attachments split out; Hash/Array become JSON), updates @message with role/content/model_id/token counts, writes the tool_call foreign key when resolved, saves, then persists attachments via persist_content and creates tool-call rows via persist_tool_calls. persist_tool_calls maps each tool call hash, renaming :id to :tool_call_id, into a child record of @message. find_tool_call_id looks up the tool_call_class by tool_call_id and returns its database id or nil. persist_content attaches prepared attachables only when the record responds to attachments. prepare_for_active_storage normalizes attachments: UploadedFile/Blob pass through, Attached::One/Many contribute their blobs, Hash values are recursed, anything else goes through convert_to_active_storage_format; results are flattened and compacted. convert_to_active_storage_format returns nil for blank sources, wraps RubyLLM::Attachment or constructs one from the source, and yields io/filename/content_type from a StringIO of the attachment content; any StandardError is logged as a warning and yields nil, so a bad attachment is skipped rather than aborting persistence.

**Notes.**

- side_effect: persist_message_completion writes the tool_call foreign key via write_attribute after update!, then saves again.

calls: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5)

**Uncertainties.**

- @message.class.tool_call_foreign_key is assumed to exist as a class method (from ActsAsLegacy attr_readers); behavior when absent is not shown.

<a id="u-90700e047487"></a>
### `acts_as_legacy-chat-legacy-cleanup`

`def cleanup_failed_messages` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L211-L214][f1]

Post-failure repair helpers (private).

cleanup_failed_messages logs a warning including the message id and destroys @message; it assumes @message is set and persisted, as guaranteed by the caller's guard. cleanup_orphaned_tool_results reloads the messages association and inspects the last message by id: it returns without changes unless that message is a tool call or tool result. If the last message is a tool call it is destroyed. If it is a tool result, it looks up the parent tool call's message, compares the sorted ids of that message's tool_calls against the sorted tool_call_ids of its tool_results, and only when the sets differ destroys all of that message's tool_results and then the tool-call message itself. Matching sets are left untouched.

**Notes.**

- condition: cleanup_orphaned_tool_results is a no-op when the last message is neither a tool call nor a tool result, and when tool_calls/tool_results sets already match.

**Uncertainties.**

- If the last message is a tool result whose parent_tool_call or its message is missing, the navigation last.parent_tool_call.message may raise; no guard is visible.

<a id="u-2dc6239d943b"></a>
### `acts_as_legacy-message-legacy-extraction`

`def extract_tool_calls` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L353-L364][f1]

Private helpers backing MessageLegacyMethods#to_llm.

extract_tool_calls builds a hash keyed by each tool_call row's tool_call_id with RubyLLM::ToolCall values carrying id, name and arguments. extract_tool_call_id returns parent_tool_call&.tool_call_id, so messages without a parent tool call yield nil. extract_content returns the plain content when the record has no attachments; when attachments exist it builds a RubyLLM::Content from the text, downloads each attachment into a tempfile and adds it with the original filename. download_attachment derives a basename/extension from the filename, creates a binary Tempfile, streams attachment.download chunks into it, flushes and rewinds, appends the tempfile to @_tempfiles to keep it alive, and returns it. @_tempfiles accumulates across calls and is never cleaned up here.

uses: [Content](r2-content-value-objects.md#u-fb6f20b3ce1b)

**Uncertainties.**

- Tempfile lifetime beyond @_tempfiles and download failure handling are not addressed in this code.

<a id="u-3266c2e8afe4"></a>
### `complete`

`def complete(...)` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L201-L207][f1]

Runs the LLM completion by delegating all arguments to to_llm.complete.

On a RubyLLM::Error, it performs recovery before re-raising: if @message is persisted and its content is blank, cleanup_failed_messages logs a warning and destroys the empty assistant message; then cleanup_orphaned_tool_results removes a trailing dangling tool call or an incomplete tool-call/result pair. The original error is always re-raised after cleanup.

**Notes.**

- failure: Cleanup only discards the blank assistant message; a partially filled @message is kept and the error propagates.

calls: [acts_as_legacy-chat-legacy-cleanup](r1-legacy-acts-as.md#u-90700e047487)

<a id="u-01549a902085"></a>
### `to_llm`

`def to_llm(context: nil) # model_id is a string that RubyLLM can resolve` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L89-L103][f1]

Builds an in-memory RubyLLM chat from persisted state and wires persistence callbacks, memoized in @chat.

When a context is passed it uses context.chat(model: model_id), otherwise RubyLLM.chat(model: model_id); it always calls reset_messages! so the transcript is rebuilt from scratch, replays each persisted message via @chat.add_message(msg.to_llm), then installs persistence callbacks via setup_persistence_callbacks and returns the chat. Repeated calls re-sync messages but reuse the memoized chat.

calls: [acts_as_legacy-chat-legacy-persistence](r1-legacy-acts-as.md#u-0b7cbfbc22b5); uses: [acts_as_legacy-message-legacy-extraction](r1-legacy-acts-as.md#u-2dc6239d943b)

**Uncertainties.**

- Whether RubyLLM.chat or Context#chat handles the model_id string is defined outside this file.

<a id="u-2466705eae52"></a>
### `lib/ruby_llm/active_record/acts_as_legacy.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/acts_as_legacy.rb:L339-L349][f1]

Converts a persisted message row into an in-memory RubyLLM::Message, mapping role to a symbol, content through extract_content, tool calls through extract_tool_calls, the parent tool call id through extract_tool_call_id, and passing input_tokens, output_tokens and model_id straight through.

Pure read; no persistence or side effects.

calls: [acts_as_legacy-message-legacy-extraction](r1-legacy-acts-as.md#u-2dc6239d943b)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/acts_as_legacy.rb