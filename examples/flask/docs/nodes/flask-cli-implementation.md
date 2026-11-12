# Flask CLI Implementation

**Capability.** Implements the flask command line: parameter types, app loading and import discovery, the command groups, built-in commands and the development server command.

Read this to see how the flask command finds an app and runs commands. Option handling and ScriptInfo prepare the context, import discovery resolves the app, and the group and command modules define what the user runs.

**Children.**

- [CLI Options and App Loading Info](cli-options-and-app-loading-info.md) `cli-options-and-app-loading-info` · 17 unit(s)
- [CLI Groups and Built-in Commands](cli-groups-and-built-in-commands.md) `cli-groups-and-built-in-commands` · 10 unit(s)
- [CLI Run Command and Command Discovery](cli-run-command-and-command-discovery.md) `cli-run-command-and-command-discovery` · 7 unit(s)
- [CLI App Import and Discovery](cli-app-import-and-discovery.md) `cli-app-import-and-discovery` · 4 unit(s)

**Depends on.**

- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-confirmed · 3 edge(s) · 3 inferred relation(s) · The CLI implementation uses helpers such as debug-flag checks and the app run method.

**Depended on by.**

- [Helpers, Flask Blueprint and Run](helpers-flask-blueprint-and-run.md) · graph-confirmed · 2 edge(s)

Parent: [Command Line and Public Helpers](command-line-and-public-helpers.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.
