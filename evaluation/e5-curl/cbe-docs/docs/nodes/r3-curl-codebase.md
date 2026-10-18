# curl Codebase

**Capability.** Umbrella over the public libcurl API, the connection/protocol infrastructure that implements it, shared primitives (buffers, containers, hashing), name resolution, TLS certificate handling, version reporting, and the curl command-line tool.

Start here to navigate the codebase. Major branches separate the public header contract, transport/proxy plumbing, DNS, crypto and signing, certificate inspection, shared utilities, runtime version data, and the CLI tool layers.

**Children.**

- [Public libcurl API Header](r3-public-curl-api.md) `r3-public-curl-api` · 13 unit(s)
- [Connection & Proxy Infrastructure](r3-connection-infra.md) `r3-connection-infra` · 0 unit(s)
- [Asynchronous Name Resolution](r3-dns-resolution.md) `r3-dns-resolution` · 0 unit(s)
- [Crypto Primitives & HTTP Authentication](r3-crypto-auth.md) `r3-crypto-auth` · 0 unit(s)
- [TLS Certificate Handling](r3-tls-certificates.md) `r3-tls-certificates` · 0 unit(s)
- [Shared Core Utilities](r3-core-utilities.md) `r3-core-utilities` · 0 unit(s)
- [Version & Feature Reporting](r3-version-info.md) `r3-version-info` · 5 unit(s)
- [curl Command-Line Tool Support](r3-cli-tool.md) `r3-cli-tool` · 0 unit(s)

Parent: [Shared Infrastructure & Public API](shared-infra-and-api.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
