# Shared infrastructure utilities

**Capability.** Self-contained utilities consumed across the library: string escaping and encoding, pattern matching, hashing, IDN, memory tracing, buffered connection filters, and the legacy HTTP form API.

These children have no knowledge of transfers or protocols; consumers call into them. Each can be read and reasoned about in isolation.

**Children.**

- [String escaping and encoding](r7-string-escape-utils.md) `r7-string-escape-utils` · 9 unit(s)
- [Filename pattern matching](r7-fnmatch-pattern.md) `r7-fnmatch-pattern` · 9 unit(s)
- [SHA-512/256 hashing](r7-sha512-256.md) `r7-sha512-256` · 14 unit(s)
- [Internationalized domain names](r7-idn-hostnames.md) `r7-idn-hostnames` · 13 unit(s)
- [Memory and socket debug tracing](r7-memdebug-tracing.md) `r7-memdebug-tracing` · 28 unit(s)
- [Buffered receive connection filter](r7-recvbuf-filter.md) `r7-recvbuf-filter` · 6 unit(s)
- [Legacy HTTP form \(multipart\) API](r7-httppost-form.md) `r7-httppost-form` · 16 unit(s)

Parent: [curl codebase](r7-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
