# Connection Name Resolution

**Capability.** Turns hostnames and literal addresses into usable Curl_addrinfo lists: address-string parsing/list management plus the asynchronous, cached DNS resolver that drives it.

Use this subtree when tracing how a connection obtains its target address. The addrinfo subtree is the pure data-conversion layer; the DNS resolver subtree orchestrates caching, async state, and timeouts on top of it.

**Children.**

- [Addrinfo Conversion Helpers](r5-addrinfo-core.md) `r5-addrinfo-core` · 14 unit(s)
- [Async DNS Resolver](r5-dns-resolver.md) `r5-dns-resolver` · 31 unit(s)

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
