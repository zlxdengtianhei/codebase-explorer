# HTTP Protocol Engine

**Capability.** End-to-end HTTP handling in lib/http.c: request building and sending, incremental response parsing and reaction, authentication, redirects, Expect-100, and req/resp object lifecycle.

Enter via the request-construction or response-processing subtrees. Auth and Expect-100 helpers, header-value utilities and object lifecycle serve both directions. The engine consumes the URL API for targets and redirects and connection control for close/multiplex decisions.

**Children.**

- [Request Construction and Send](r6-http-request-build.md) `r6-http-request-build` · 18 unit(s)
- [Response Parsing and Reaction](r6-http-response-processing.md) `r6-http-response-processing` · 30 unit(s)
- [Auth Emission and Expect-100](r6-http-auth-and-expect.md) `r6-http-auth-and-expect` · 6 unit(s)
- [Shared HTTP Header Utilities](r6-http-shared-header-utils.md) `r6-http-shared-header-utils` · 2 unit(s)
- [HTTP Request/Response Objects](r6-http-req-resp-objects.md) `r6-http-req-resp-objects` · 3 unit(s)

Parent: [curl Codebase](r6-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
