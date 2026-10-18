# Gemini Embeddings & Images

**Capability.** Builds batchEmbedContents and predict requests and parses their responses into Embedding and Image objects.

Use these methods for Gemini's non-chat surfaces; each pairs a request builder with a response parser.

**Depends on.**

- [Attachments & Images](r1-content-media.md) · graph-confirmed · 1 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 1 edge(s)

Parent: [Gemini Adapter](r1-gemini-adapter.md)

## Units (4)

<a id="u-223f7bd81ebf"></a>
### `embeddings-request`

`def embedding_url(model:)` · [lib/ruby_llm/providers/gemini/embeddings.rb:L10-L12][f1]

Groups embedding request construction.

embedding_url returns 'models/<model>:batchEmbedContents'. render_embedding_payload flattens the text argument into a list and builds one request per item. single_embedding_payload builds {model: 'models/<model>', content: {parts: [{text: <text.to_s>}]}, outputDimensionality: dimensions} with compact removing the dimensions key when nil, so omitting dimensions yields a payload without that field.

<a id="u-12c0d2f53008"></a>
### `RubyLLM.Providers.Gemini.Embeddings.parse_embedding_response`

`def parse_embedding_response(response, model:, text:)` · [lib/ruby_llm/providers/gemini/embeddings.rb:L18-L23][f1]

Converts a batchEmbedContents response into an Embedding.

It maps each entry of body['embeddings'] to its 'values' vector; when exactly one vector came back and the input text was not an Array, it unwraps to that single vector. Input tokens are always reported as 0. Missing 'embeddings' yields vectors nil, and a single-element input with an Array text keeps the nested form.

calls: [embedding.rb-embedding](r2-content-value-objects.md#u-0061f299adf1)

<a id="u-88fdf0636ce0"></a>
### `images-payload`

`def images_url` · [lib/ruby_llm/providers/gemini/images.rb:L8-L10][f2]

Groups image request construction.

images_url returns 'models/<model>:predict' using @model. render_image_payload logs a debug warning that the requested size is ignored because Gemini does not support image size customization, stores the model object in @model, and returns a payload with one prompt instance and sampleCount 1.

<a id="u-08690de76fa0"></a>
### `RubyLLM.Providers.Gemini.Images.parse_image_response`

`def parse_image_response(response, model:)` · [lib/ruby_llm/providers/gemini/images.rb:L27-L43][f2]

Converts a Gemini predict response into an Image.

It takes the first entry of body['predictions']; when it is missing or lacks 'bytesBase64Encoded' it raises Error with a message about an unexpected response format. Otherwise it builds an Image from the base64 data with mime_type defaulting to 'image/png' and the given model id.

**Notes.**

- failure: Raises RubyLLM::Error when predictions are absent or the first prediction has no base64 payload.

calls: [Image](r1-content-media.md#u-5f36460b61e5)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/embeddings.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/images.rb