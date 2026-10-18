# Ollama Adapter

**Capability.** Local-model adapter: message formatting into Ollama request hashes, content serialization into Ollama's expected shape, and models-list parsing without capability consultation.

Use this subtree when targeting local Ollama endpoints; its model metadata parsing skips capabilities entirely.

Parent: [Provider Framework](r1-provider-framework.md)

## Units (3)

<a id="u-a03d9fc91e34"></a>
### `RubyLLM.Providers.Ollama.Chat.format_messages`

`def format_messages(messages)` · [lib/ruby_llm/providers/ollama/chat.rb:L10-L19][f1]

Converts message objects into Ollama request hashes.

Each message becomes a hash with role (via format_role), content (via Ollama::Media.format_content), tool_calls (via format_tool_calls), and tool_call_id; compact removes any nil-valued keys, so absent tool fields vanish from the payload.

calls: [RubyLLM.Providers.Ollama.Chat.format_messages](r1-ollama-adapter.md#u-a03d9fc91e34)

**Uncertainties.**

- format_tool_calls and Ollama::Media.format_content behavior are defined elsewhere in or outside this batch.

<a id="u-c0df7b78d670"></a>
### `RubyLLM.Providers.Ollama.Media.format_content`

`def format_content(content)` · [lib/ruby_llm/providers/ollama/media.rb:L12-L32][f2]

Serializes chat content into Ollama's expected shape.

A RubyLLM::Content::Raw passes through as its .value; Hash or Array input becomes JSON; other non-Content values are returned unchanged. For Content objects it builds a parts list: text via format_text when present, then each attachment — images via format_image, text attachments via format_text_file (inherited from OpenAI::Media), and any other type raising UnsupportedAttachmentError with the attachment's mime type. format_image yields an OpenAI-style image_url hash from image.for_llm with detail 'auto'.

calls: [RubyLLM.Providers.Ollama.Media.format_content](r1-ollama-adapter.md#u-c0df7b78d670)

**Uncertainties.**

- format_text, format_text_file, and OpenAI::Media's surface come from outside this file; UnsupportedAttachmentError semantics are not shown.

<a id="u-fbcf52da3d80"></a>
### `RubyLLM.Providers.Ollama.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, _capabilities)` · [lib/ruby_llm/providers/ollama/models.rb:L12-L32][f3]

Maps the Ollama models-list response into Model::Info records without consulting capabilities.

It reads response.body['data'] (defaulting to [] when nil) and, for each entry, builds Model::Info with id and name both set to the model id, family 'ollama', created_at from Time.at(model['created']) only when 'created' is present (else nil), fixed modalities (input text/image, output text), fixed capabilities (streaming, function_calling, structured_output, vision), empty pricing, and metadata with 'owned_by'. The _capabilities argument is ignored.

**Uncertainties.**

- Time.at expects a numeric epoch; behavior for string timestamps or Model::Info validation is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/media.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/ollama/models.rb