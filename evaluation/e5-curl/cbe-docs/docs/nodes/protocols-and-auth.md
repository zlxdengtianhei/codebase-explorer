# Protocols & Authentication

**Capability.** Concrete transfer protocols (HTTP, IMAP, SMTP, FTP listing, WebSocket, MQTT, SSH, telnet, FILE, DICT/TFTP/LDAP) plus URL parsing and the SASL/NTLM/Digest authentication engines they share. They belong together because each protocol is a state machine over the same transfer machinery and reuses the same auth message builders.

Pick the protocol subtree matching your scheme; each owns its connect/do/doing/done flow. Authentication subtrees are protocol-shared and should be read when any handshake needs challenge/response handling.

**Children.**

- [curl Codebase](r6-curl-codebase.md) `r6-curl-codebase` · 0 unit(s)
- [curl codebase](r12-curl-codebase.md) `r12-curl-codebase` · 0 unit(s)
- [curl codebase](r15-curl-codebase.md) `r15-curl-codebase` · 0 unit(s)

**Depends on.**

- [Connection Core & Filters](connection-core.md) · graph-confirmed · 208 edge(s) · Protocol engines invoke connection control (close hooks, connection setup) via the connection core.
- [TLS Backends & Name Resolution](security-and-resolution.md) · graph-confirmed · 222 edge(s) · Protocol implementations resolve peer names and attach TLS through the security-and-resolution layer.
- [Shared Infrastructure & Public API](shared-infra-and-api.md) · graph-confirmed · 564 edge(s)
- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 125 edge(s) · Protocol engines (e.g. the HTTP engine) consume the transfer/xfer API to send requests and receive responses.

**Depended on by.**

- [TLS Backends & Name Resolution](security-and-resolution.md) · graph-confirmed · 105 edge(s)
- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 249 edge(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
