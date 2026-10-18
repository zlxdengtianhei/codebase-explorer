# DNS resolution

**Capability.** Resolving hostnames to cached address entries: a shared DNS cache with keyed lookup, negative caching and stale pruning, plus an optional c-ares-backed getaddrinfo shim.

Read the dnscache subtree to understand entry storage, lookup and CURLOPT_RESOLVE population; read fake-resolver to see how the system getaddrinfo surface can be replaced by c-ares. Both feed connection setup with Curl_dns_entry references.

**Children.**

- [DNS cache](r11-dnscache.md) `r11-dnscache` · 13 unit(s)
- [c-ares getaddrinfo shim](r11-fake-resolver.md) `r11-fake-resolver` · 5 unit(s)

Parent: [curl codebase](r11-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
