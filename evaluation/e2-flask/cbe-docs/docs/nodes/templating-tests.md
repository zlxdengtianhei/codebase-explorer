# Templating Test Suite

**Capability.** Pins Jinja integration: rendering context and streaming, autoescaping, app and blueprint template filters/tests/globals, custom environments and loaders, iterable template loading, loader-explain logging, and auto_reload resolution versus debug mode.

Read these to confirm how filters and tests register, how TEMPLATES_AUTO_RELOAD interacts with debug, and what EXPLAIN_TEMPLATE_LOADING logs for blueprint template lookup.

Parent: [Flask Capabilities Region](flask-capabilities-region.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
