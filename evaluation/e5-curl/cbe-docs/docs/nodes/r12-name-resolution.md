# Name resolution

**Capability.** Resolves hostnames to addresses: synchronous IPv4 lookup, the asynchronous resolver contract and DNS cache model, and HTTPS RR (SvcParam) records with ALPN/ECH/address hints.

Use this subtree for anything between a hostname string and a Curl_addrinfo. Platform-specific IPv4 replacement lives under platform adaptation and interacts with the sync resolver.

**Children.**

- [Async DNS interface and caches](r12-async-dns-interface.md) `r12-async-dns-interface` · 4 unit(s)
- [Synchronous IPv4 resolver](r12-sync-ipv4-resolver.md) `r12-sync-ipv4-resolver` · 2 unit(s)
- [HTTPS RR records](r12-https-rr.md) `r12-https-rr` · 11 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
