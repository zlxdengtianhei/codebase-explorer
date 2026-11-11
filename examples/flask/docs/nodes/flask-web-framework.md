# Flask Web Framework

**Capability.** Implements the Flask WSGI micro-framework: application core, request handling, contexts, CLI, templating, sessions, JSON and configuration support, and testing tools.

Start here to understand how Flask is assembled end to end. The largest children cover the app core and sansio bases, the runtime request machinery with testing, and the CLI with public helpers, while smaller modules supply templating, JSON, sessions and configuration.

**Children.**

- [Sansio App and Scaffold Foundations](sansio-app-and-scaffold-foundations.md) `sansio-app-and-scaffold-foundations` · 74 unit(s)
- [Runtime App, Contexts and Testing](runtime-app-contexts-and-testing.md) `runtime-app-contexts-and-testing` · 64 unit(s)
- [Command Line and Public Helpers](command-line-and-public-helpers.md) `command-line-and-public-helpers` · 58 unit(s)
- [Templates, Views and Wrappers](templates-views-and-wrappers.md) `templates-views-and-wrappers` · 39 unit(s)
- [Tagged JSON Serialization](tagged-json-serialization.md) `tagged-json-serialization` · 16 unit(s)
- [JSON Providers and Helpers](json-providers-and-helpers.md) `json-providers-and-helpers` · 14 unit(s)
- [Session Interface and Cookies](session-interface-and-cookies.md) `session-interface-and-cookies` · 14 unit(s)
- [Configuration Loading](configuration-loading.md) `configuration-loading` · 14 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
