# printf engine (mprintf)

**Capability.** curl's own printf implementation: format-string parsing into output/argument segments and a streaming emitter with padding and conversion, exposed as stdio, bounded (snprintf), and dynbuf-append formatter families.

Use the format-engine child for how conversions are parsed and emitted; use the formatter-families child for the public entry points consumers call. The two children call each other.

**Children.**

- [Format parsing and emission](r9-mprintf-format-engine.md) `r9-mprintf-format-engine` · 13 unit(s)
- [Formatter API families](r9-mprintf-formatter-families.md) `r9-mprintf-formatter-families` · 3 unit(s)

**Depended on by.**

- [CRAM-MD5 \(SASL\)](r9-cram-auth.md) · graph-confirmed · 1 edge(s)
- [Digest core \(vauth/digest\)](r9-digest-core.md) · graph-confirmed · 13 edge(s)
- [HTTP Digest](r9-digest-http.md) · graph-confirmed · 1 edge(s)
- [Transfer progress](r9-progress.md) · graph-confirmed · 2 edge(s)
- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) · graph-confirmed · 7 edge(s)
- [Tool --libcurl source generation](r9-tool-easysrc.md) · graph-confirmed · 10 edge(s)
- [Tool parameter helpers](r9-tool-paramhlp.md) · graph-confirmed · 3 edge(s)

Parent: [Shared core infrastructure](r9-core-infra.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
