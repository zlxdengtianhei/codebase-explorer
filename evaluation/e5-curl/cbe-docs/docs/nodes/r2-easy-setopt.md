# Easy Handle Option Setting

**Capability.** Validating, converting and storing CURLOPT_* values into an easy handle's configuration, dispatched by option type into protocol-domain sub-handlers.

Use this subtree for any CURLOPT handling: the type-dispatch core, typed storage helpers, and the per-domain long/cptr handlers covering HTTP, proxy, TLS, net, protocol and misc options.

**Children.**

- [Setopt Dispatch & Storage](r2-setopt-core.md) `r2-setopt-core` · 15 unit(s)
- [Setopt Domain Handlers](r2-setopt-domains.md) `r2-setopt-domains` · 29 unit(s)

Parent: [libcurl Transfer Runtime](r2-libcurl-runtime.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
