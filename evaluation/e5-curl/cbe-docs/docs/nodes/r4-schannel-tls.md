# Schannel TLS backend

**Capability.** The Windows Schannel/SSPI TLS backend: its vtable wiring to the generic TLS layer, one-time and per-connection initialization, and teardown, with children covering handshake setup, record I/O, and certificate/cache support.

Start at this node to see the backend vtable and overall structure; descend into handshake, record I/O or certificate/cache children for specifics. All SSPI interaction is confined to this subtree.

**Children.**

- [Schannel handshake and credentials](r4-schannel-handshake.md) `r4-schannel-handshake` · 19 unit(s)
- [Schannel record I/O](r4-schannel-record-io.md) `r4-schannel-record-io` · 8 unit(s)
- [Schannel certificates and caching](r4-schannel-certs-cache.md) `r4-schannel-certs-cache` · 6 unit(s)

Parent: [TLS and QUIC connections](r4-tls-quic.md)

## Units (1)

<a id="u-284e1016f28e"></a>
### `schannel.c-backend-struct`

`group` · [lib/vtls/schannel.c:L2893-L2928][f1]

The trailing region defines Curl_ssl_schannel, the backend vtable wiring every function in this file to the generic TLS layer, advertising support for certinfo, CAINFO blob, pinned public key, CA caching, HTTPS proxy, and cipher lists, with NULL slots for engines, channel binding, and close_all.

Declarations only.

uses: [schannel_connect](r4-schannel-handshake.md#u-5f8743053a3d), [schannel_recv](r4-schannel-record-io.md#u-57aff20ea872), [schannel_send](r4-schannel-record-io.md#u-d0071ea7442e)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/schannel.c
