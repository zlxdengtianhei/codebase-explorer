# Connection Filter Framework

**Capability.** Owns the insertable connection-filter abstraction: header-level filter interfaces (HAProxy) and the concrete filters that manage address resolution and parallel connection attempts before handing a working sub-filter to the chain.

Use this subtree to understand how a connection's filter chain is built. The HAProxy header declares one filter's interface; the two children are concrete filters plugged in via insert-after entry points.

**Children.**

- [Happy Eyeballs IP Filter](r1-happy-eyeballs-filter.md) `r1-happy-eyeballs-filter` · 15 unit(s)
- [DNS Resolve Connection Filter](r1-dns-resolve-filter.md) `r1-dns-resolve-filter` · 22 unit(s)

**Depends on.**

- [Trace and Debug Logging](r1-trace-logging.md) · graph-confirmed · 34 edge(s)

**Depended on by.**

- [Happy Eyeballs IP Filter](r1-happy-eyeballs-filter.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r1-happy-eyeballs-filter ` → ` r1-connection-filters `)

Parent: [curl Codebase](r1-curl-codebase.md)

## Units (1)

<a id="u-a54d3b28220d"></a>
### `cf-haproxy-h`

`group` · [lib/cf-haproxy.h:L1-L39][f1]

Declares the HAProxy connection-filter interface: an insertion helper and the filter type.

Both declarations are guarded by !CURL_DISABLE_PROXY, so in builds with proxy support disabled the header exposes nothing beyond its includes.

imports: [cf-haproxy-h](r1-connection-filters.md#u-a54d3b28220d)

**Uncertainties.**

- Implementations live outside this header; their behavior cannot be read here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/cf-haproxy.h
