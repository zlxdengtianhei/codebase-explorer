# Message Conversion

**Capability.** Converts a persisted message row into an in-memory RubyLLM::Message, backed by private content-extraction helpers.

Use MessageMethods#to_llm to hydrate message rows into value objects for modern (non-legacy) integrations.

**Depends on.**

- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 2 edge(s)

Parent: [ActiveRecord & Rails Integration](r1-active-record-integration.md)

## Units (2)

<a id="u-f8aea5d5092c"></a>
### `lib/ruby_llm/active_record/message_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/message_methods.rb:L13-L28][f1]

Converts a persisted message row into an in-memory RubyLLM::Message.

Token-cache values are read only when the underlying columns exist (has_attribute? guards for cached_tokens and cache_creation_tokens, otherwise nil). Content comes from extract_content, tool calls from extract_tool_calls, the parent tool call id from extract_tool_call_id; model_id is taken from the model association (nil when absent). Pure read with no side effects besides any tempfiles created by extract_content.

calls: [message_methods-content-extraction](r1-message-methods.md#u-92796b41699b)

<a id="u-92796b41699b"></a>
### `message_methods-content-extraction`

`def extract_tool_calls` · [lib/ruby_llm/active_record/message_methods.rb:L32-L43][f1]

Private helpers backing MessageMethods#to_llm.

extract_tool_calls builds a hash keyed by each tool_call row's tool_call_id with RubyLLM::ToolCall values carrying id, name and arguments, read from the tool_calls_association. extract_tool_call_id returns parent_tool_call&.tool_call_id, nil when there is no parent. extract_content prefers raw content: when the record has a content_raw attribute and it is present it returns RubyLLM::Content::Raw over it; otherwise it uses the content column, and only when the record also has attached ActiveStorage attachments wraps the text in a RubyLLM::Content, downloading each attachment into a tempfile and adding it with the original filename. download_attachment creates a binary Tempfile from the attachment's basename/extension, streams attachment.download chunks into it, flushes, rewinds, appends it to @_tempfiles to prevent garbage collection, and returns it; tempfiles accumulate in @_tempfiles and are not cleaned here.

uses: [Content](r2-content-value-objects.md#u-fb6f20b3ce1b)

**Uncertainties.**

- Whether content_raw takes precedence over attached attachments is resolved by the code: raw wins and attachments are ignored in that case.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/message_methods.rb