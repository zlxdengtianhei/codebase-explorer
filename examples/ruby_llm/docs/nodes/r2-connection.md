# Provider Connection

**Capability.** Wraps Faraday for one provider API: enforces configuration, applies logging, retries, and the error middleware.

Read to see request/response plumbing shared by all providers. It raises RubyLLM errors via the error-handling subtree.

**Depends on.**

- [Error Hierarchy and Middleware](r2-error-handling.md) · graph-confirmed · 4 edge(s) · Connection installs the error middleware that maps HTTP statuses to RubyLLM errors.

**Depended on by.**

- [Configuration and Context](r2-config-context.md) · model-inferred · 0 edge(s)
- [Error Hierarchy and Middleware](r2-error-handling.md) · model-inferred · 0 edge(s)
- [OpenAI-Derived Providers](r2-openai-derived-providers.md) · model-inferred · 0 edge(s)
- [Provider Base and Registry](r2-provider-base.md) · graph-confirmed · 7 edge(s) · The provider base class issues every request through its per-provider Connection.
- [Bedrock Adapter](r2-provider-bedrock.md) · graph-confirmed · 2 edge(s)
- [Gemini Adapter](r2-provider-gemini.md) · graph-confirmed · 2 edge(s)
- [VertexAI Adapter](r2-provider-vertexai.md) · graph-confirmed · 1 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · graph-confirmed · 1 edge(s)
- [Attachments & Images](r1-content-media.md) · graph-only · 2 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · graph-only · 2 edge(s)
- [Bedrock Models & Capabilities](r1-bedrock-models-capabilities.md) · graph-only · 1 edge(s)

Parent: [HTTP Transport and Provider Base](r2-transport.md)

## Units (1)

<a id="u-53be52e4979e"></a>
### `connection.rb-connection`

`class Connection` · [lib/ruby_llm/connection.rb:L5-L8][f1]

Wraps Faraday setup for one provider's API, enforcing configuration and applying logging, retries, and error mapping.

The class method basic builds an ad-hoc Faraday stack with debug logging (no bodies/headers) and raise_error, optionally extended by a block. initialize validates the provider via ensure_configured!, which raises ConfigurationError containing a ready-to-paste RubyLLM.configure snippet (env-var based) for each missing requirement when provider.configured? fails; it then builds a Faraday connection at provider.api_base with: timeout from config.request_timeout; response logging that masks runs of 100+ base64 characters as '[BASE64 DATA]' and long numeric runs as '[EMBEDDINGS ARRAY]'; retry middleware using config retry knobs, the retry_exceptions list (timeouts, connection failures, and the RubyLLM rate-limit/server/unavailable/overloaded errors), and retry statuses 429, 500, 502, 503, 504, 529; multipart/json request and json response middleware; the :llm_errors middleware bound to the provider; and config.http_proxy when set. post and get issue requests through that connection, merging provider.headers into the request when the provider responds to headers, and yield the request for caller customization. instance_variables hides @config/@connection.

uses: [RubyLLM.ErrorMiddleware.call](r2-error-handling.md#u-622400cac239)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/connection.rb