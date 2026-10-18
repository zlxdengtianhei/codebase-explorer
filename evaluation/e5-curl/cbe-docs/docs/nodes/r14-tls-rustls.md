# rustls TLS Backend

**Capability.** Owns the rustls TLS backend: its Curl_ssl backend table and per-connection state, the non-blocking handshake/recv/send/shutdown filter methods over the connection filter chain, and the client-config builder (ciphers, ALPN, client auth, verifiers, ECH, keylog).

Consumers reach this backend through the Curl_ssl table; inside, cr_connect drives the handshake using tls_recv_more/cr_flush_out, while cr_init_backend assembles the configuration from the init_config_builder_* helpers. Use the three children to separate transport behavior from configuration assembly and backend registration.

**Children.**

- [rustls Connection Transport](r14-tls-rustls-transport.md) `r14-tls-rustls-transport` · 17 unit(s)
- [rustls Client Config Builder](r14-tls-rustls-config.md) `r14-tls-rustls-config` · 15 unit(s)
- [rustls Backend Registration & Misc](r14-tls-rustls-backend.md) `r14-tls-rustls-backend` · 11 unit(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
