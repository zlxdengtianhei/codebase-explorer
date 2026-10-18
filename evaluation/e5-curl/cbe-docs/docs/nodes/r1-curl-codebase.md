# curl Codebase

**Capability.** Umbrella capability spanning the connection-establishment core of libcurl (connection filters, DNS, tracing, the FTP protocol and TLS configuration) and the curl command-line tool built on top of it.

Start here to orient between the library side (how connections are established, traced and secured) and the tool side (option handling, Windows support and code generation). Each child owns one cohesive subsystem.

**Children.**

- [Connection Filter Framework](r1-connection-filters.md) `r1-connection-filters` · 1 unit(s)
- [Trace and Debug Logging](r1-trace-logging.md) `r1-trace-logging` · 22 unit(s)
- [FTP Protocol Implementation](r1-ftp-protocol.md) `r1-ftp-protocol` · 0 unit(s)
- [TLS Configuration Management](r1-tls-configuration.md) `r1-tls-configuration` · 15 unit(s)
- [Platform and Auth Utilities](r1-platform-utilities.md) `r1-platform-utilities` · 6 unit(s)
- [curl Command-Line Tool](r1-curl-tool.md) `r1-curl-tool` · 4 unit(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
