# HTTP/SOCKS authentication

**Capability.** Implements challenge parsing and response generation for Digest (HTTP and SASL), Negotiate/SPNEGO, CRAM-MD5, and SOCKS5 GSS-API, delegating the crypto/format heavy lifting to vauth and SSPI backends.

Use the digest children for header and SASL challenge handling; the negotiate, cram, and socks children each own one scheme's handshake. All build output strings through mprintf dynbuf/nsprintf families and compare tokens with caseless strings.

**Children.**

- [HTTP Digest](r9-digest-http.md) `r9-digest-http` · 4 unit(s)
- [Digest core \(vauth/digest\)](r9-digest-core.md) `r9-digest-core` · 13 unit(s)
- [Negotiate/SPNEGO \(HTTP\)](r9-negotiate-auth.md) `r9-negotiate-auth` · 4 unit(s)
- [CRAM-MD5 \(SASL\)](r9-cram-auth.md) `r9-cram-auth` · 4 unit(s)
- [SOCKS5 GSS-API/SSPI](r9-socks-sspi.md) `r9-socks-sspi` · 7 unit(s)

**Depended on by.**

- [SOCKS5 GSS-API/SSPI](r9-socks-sspi.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r9-socks-sspi ` → ` r9-http-auth `)

Parent: [curl codebase](r9-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
