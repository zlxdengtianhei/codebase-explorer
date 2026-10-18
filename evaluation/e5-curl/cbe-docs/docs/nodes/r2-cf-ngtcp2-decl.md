# ngtcp2 QUIC Filter Declaration

**Capability.** Compile-time-guarded declaration of the ngtcp2/NGHTTP3 connection-filter factories.

A declarations-only header; use it to see under which build macros the ngtcp2 QUIC filter is available. No behavior is defined here.

Parent: [Connection Filter Protocol Stacks](r2-protocol-filters.md)

## Units (1)

<a id="u-5c0159624a1b"></a>
### `cf-ngtcp2-h`

`module_region` · [lib/vquic/cf-ngtcp2.h:L1-L64][f1]

Declares the ngtcp2 QUIC connection-filter factories, active when HTTP is enabled and both USE_NGTCP2 and USE_NGHTTP3 are defined.

It conditionally includes backend headers: ngtcp2 crypto (plus the OpenSSL QUIC-API2 variant when OPENSSL_QUIC_API2 is defined), nghttp3, and either OpenSSL or wolfSSL TLS headers depending on USE_OPENSSL vs USE_WOLFSSL. `Curl_cf_ngtcp2_create` builds the filter from origin/peer, connection, and sockaddr; `Curl_cf_ngtcp2_insert_after` inserts it after a given filter. Both return CURLcode. Declarations only.

**Uncertainties.**

- Whether the wolfSSL branch fully supports the OPENSSL_QUIC_API2 path cannot be determined from the includes alone.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/cf-ngtcp2.h
