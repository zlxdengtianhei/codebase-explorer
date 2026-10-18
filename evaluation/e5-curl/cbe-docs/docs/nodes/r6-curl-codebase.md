# curl Codebase

**Capability.** Root: URL-based transfer spanning the libcurl engine (HTTP, URL parsing, connection setup, sharing, FTP listing) and curl command-line tool frontends.

Start here to navigate the repository. Children separate the library engine from tool-side helpers, public interfaces and platform configuration. Cross-module flows run from the tool into the URL API, and from HTTP into connection control and shared state.

**Children.**

- [Public API Headers](r6-public-headers.md) `r6-public-headers` · 4 unit(s)
- [Build and Platform Configuration](r6-build-and-platform-config.md) `r6-build-and-platform-config` · 3 unit(s)
- [Connection Setup and Control](r6-connection-management.md) `r6-connection-management` · 14 unit(s)
- [Share API](r6-share-api.md) `r6-share-api` · 10 unit(s)
- [FTP Wildcard LIST Parsing](r6-ftp-list-parsing.md) `r6-ftp-list-parsing` · 18 unit(s)
- [HTTP Protocol Engine](r6-http-engine.md) `r6-http-engine` · 0 unit(s)
- [URL API \(urlapi\)](r6-url-api.md) `r6-url-api` · 0 unit(s)
- [Command-Line Tool Support](r6-tool-side.md) `r6-tool-side` · 0 unit(s)

Parent: [Protocols & Authentication](protocols-and-auth.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
