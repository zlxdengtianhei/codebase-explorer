# Error Hierarchy and Middleware

**Capability.** Maps completed HTTP responses to typed RubyLLM errors by status, exposed as Faraday middleware registered at load time as :llm_errors.

Use this to see which error class a given status raises and how provider-specific messages are extracted. Connection installs this middleware; streaming error paths also route through parse_error.

**Depends on.**

- [Provider Connection](r2-connection.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 4 edge(s) · Connection installs the error middleware that maps HTTP statuses to RubyLLM errors.
- [Provider Base and Registry](r2-provider-base.md) · model-inferred · 0 edge(s)
- [VertexAI Adapter](r2-provider-vertexai.md) · graph-confirmed · 1 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · model-inferred · 0 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · graph-only · 1 edge(s)

Parent: [Core Runtime](r2-core-runtime.md)

## Units (4)

<a id="u-39e787c00a73"></a>
### `lib/ruby_llm/error.rb:Error`

`class Error < StandardError` · [lib/ruby_llm/error.rb:L6-L9][f1]

Base error carrying the raw provider response; initialize stores response and passes message, defaulting to response&.body when no message is given.

The HTTP-status subclasses (BadRequestError, UnauthorizedError, PaymentRequiredError, ForbiddenError, RateLimitError, ServerError, ServiceUnavailableError, OverloadedError) inherit this behavior unchanged and exist only as status categories. ConfigurationError, InvalidRoleError, ModelNotFoundError, and UnsupportedAttachmentError derive directly from StandardError and carry no response.

<a id="u-622400cac239"></a>
### `RubyLLM.ErrorMiddleware.call`

`def call(env)` · [lib/ruby_llm/error.rb:L38-L42][f1]

Faraday middleware instance entry: runs the downstream app and, on completion, invokes the class-level parse_error with the stored provider and the finished response, which either passes 2xx/3xx responses through or raises the mapped RubyLLM error.

calls: [RubyLLM.ErrorMiddleware.parse_error](r2-error-handling.md#u-f775c1bd477e)

<a id="u-f775c1bd477e"></a>
### `RubyLLM.ErrorMiddleware.parse_error`

`def parse_error(provider:, response:) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/error.rb:L45-L71][f1]

Maps a completed HTTP response to a RubyLLM error by status, after asking the provider for a specific message.

For 200..399 it returns the provider message without raising. Otherwise it raises: BadRequestError on 400, UnauthorizedError on 401, PaymentRequiredError on 402, ForbiddenError on 403, RateLimitError on 429, ServerError on 500, ServiceUnavailableError on 502-503, OverloadedError on 529, and the generic Error for any other status; each message falls back to a fixed human-readable hint when the provider supplied none.

<a id="u-ed30cc5cb05f"></a>
### `error.rb module code (L74–L76)`

`module_region` · [lib/ruby_llm/error.rb:L74-L76][f1]

Registers RubyLLM::ErrorMiddleware with Faraday under the :llm_errors name at load time, making it available to Connection's middleware stack; this registration is a load-time side effect.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/error.rb