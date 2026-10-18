# Connection identity

**Capability.** Refcounted, normalized description of a connection target: scheme, hostname (IDN-decoded or UDS path), IPv6 zone/scope, port, flags, and the original user spelling.

Use whenever code must compare or describe endpoints; constructors, comparison, and proxy helpers are declared alongside the struct.

Parent: [Multi-handle core](r12-multi-core.md)

## Units (3)

<a id="u-84982795ba49"></a>
### `peer.h module code (L1–L32)`

`module_region` · [lib/peer.h:L1-L32][f1]

Header preamble, guard, and API declarations for peer handling.

<a id="u-b2ad90c3acfc"></a>
### `Curl_peer`

`struct Curl_peer` · [lib/peer.h:L33-L44][f1]

Immutable-ish, refcounted description of a connection target: scheme, normalized hostname (IDN-decoded, brackets stripped, or a UDS path), optional IPv6 zoneid string and numeric scopeid, port, unix_socket/abstract_uds/ipv6 flags, and a trailing user_hostname[1] flex buffer holding the original user/url spelling.

refcount starts at 1 and frees the peer at zero. The header also declares the constructor/link/unlink/comparison API, a from-URL constructor, a connect-to parser, and, unless proxies are disabled, the proxy scheme/type mapper; CURL_PEER_UDS_PREFIX marks the 'localhost/' prefix that turns a hostname into a UDS path.

contract: [Curl_peer_create](r3-peer-identity.md#u-bfcb55ed9008)

<a id="u-1e437b5d50ce"></a>
### `peer.h module code (L44–L108)`

`module_region` · [lib/peer.h:L44-L108][f1]

Declarations of the peer constructors, comparison and proxy helpers after the struct definition.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/peer.h
