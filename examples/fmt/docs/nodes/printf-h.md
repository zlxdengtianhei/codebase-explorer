# printf Compatibility

**Capability.** A printf-style engine on top of fmt: C printf semantics for flags, width, precision and length-modified conversions, exposed as printf/fprintf/sprintf APIs.

Use when C printf format strings must be honored. Support visitors convert and probe args; header parsing maps printf syntax; the engine formats and the wrappers dispatch.

**Children.**

- [printf Arg Visitors](printf-support.md) `printf-support` · 8 unit(s)
- [printf Spec Parsing](printf-spec.md) `printf-spec` · 5 unit(s)
- [printf Engine & API](printf-engine.md) `printf-engine` · 10 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
