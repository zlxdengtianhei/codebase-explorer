# curl Codebase

**Capability.** Root responsibility: implementing the curl library and command-line tool as a layered system of connection filters, protocol/tunnel implementations, authentication, credential and header management, name resolution, and user-facing tool output, all on a set of portable core utilities.

Use this tree to locate any responsibility in the codebase. Library-level concerns live under connection filtering, tunneling, QUIC, headers, auth, resolution and core utilities; the command-line tool's output behavior lives under tooling.

**Children.**

- [Connection Filter Core](r8-conn-filter-core.md) `r8-conn-filter-core` · 0 unit(s)
- [Asynchronous Connection Shutdown](r8-conn-shutdown.md) `r8-conn-shutdown` · 12 unit(s)
- [Proxy Tunneling](r8-proxy-tunneling.md) `r8-proxy-tunneling` · 0 unit(s)
- [QUIC via ngtcp2](r8-quic-ngtcp2.md) `r8-quic-ngtcp2` · 0 unit(s)
- [HTTP Datagram Capsules](r8-http-datagram-capsules.md) `r8-http-datagram-capsules` · 7 unit(s)
- [HTTP Headers Store and API](r8-http-headers-api.md) `r8-http-headers-api` · 12 unit(s)
- [Authentication \(vauth\)](r8-authentication.md) `r8-authentication` · 0 unit(s)
- [netrc Credentials](r8-netrc-credentials.md) `r8-netrc-credentials` · 2 unit(s)
- [Host Address Resolution](r8-host-resolution.md) `r8-host-resolution` · 5 unit(s)
- [Command-Line Tool Output](r8-tooling.md) `r8-tooling` · 0 unit(s)
- [Core Utilities and Portability](r8-core-utilities.md) `r8-core-utilities` · 0 unit(s)

Parent: [Connection Core & Filters](connection-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
