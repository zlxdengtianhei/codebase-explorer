# Cookie jar

**Capability.** Persistent HTTP cookie state: parsing Set-Cookie and Netscape lines, domain/path policy enforcement, jar storage and lookup, and file load/save.

Use for any cookie policy or storage change. Parsing/matching is separated from jar core; the core entry points are Curl_cookie_add/getlist/loadfiles/flush_cookies.

**Children.**

- [Cookie line parsing and matching](r12-cookie-parsing.md) `r12-cookie-parsing` · 13 unit(s)
- [Cookie jar storage and lifecycle](r12-cookie-jar-core.md) `r12-cookie-jar-core` · 26 unit(s)

**Depended on by.**

- [HTTP protocol semantics](r12-http-protocol.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r12-http-protocol ` → ` r12-cookie-jar `)

Parent: [HTTP protocol semantics](r12-http-protocol.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
