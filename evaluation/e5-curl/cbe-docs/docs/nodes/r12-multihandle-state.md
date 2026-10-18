# Multi handle state

**Capability.** Defines struct Curl_multi (transfer counters, per-mid sets, timeout list, DNS/TLS caches, callbacks, connection pool limits, wakeup socketpairs) and the CURLMstate machine states.

Use as the map of everything a multi handle owns. The fixed-buffer struct and wakeup/pipe constants are part of this data model.

**Depends on.**

- [Multi event assessment and notifications](r12-multi-event.md) · model-inferred · 0 edge(s)

Parent: [Multi-handle core](r12-multi-core.md)

## Units (7)

<a id="u-b9591b5aabaf"></a>
### `lib/multihandle.h:<enum>`

`enum` · [lib/multihandle.h:L47-L65][f1]

Defines CURLMstate, the multi state machine states from MSTATE_INIT through SETUP, CONNECT(ING), PROTOCONNECT(ING), DO/DOING/DOING_MORE/DID, PERFORMING, RATELIMITING, DONE, COMPLETED, MSGSENT, with MSTATE_LAST as sentinel; the comment requires adding new names to statenames[] in curl_trc.c.

<a id="u-afa305a43a80"></a>
### `multihandle.h module code (L1–L47)`

`module_region` · [lib/multihandle.h:L1-L47][f1]

Guard, license and the header's include block (api, llist, hash, conncache, cshutdn, multi_ev, multi_ntfy, psl, socketpair, splay, uint sets/table, dnscache) plus forward declarations.

<a id="u-424c8c64f51f"></a>
### `multihandle.h module code (L65–L80)`

`module_region` · [lib/multihandle.h:L65-L80][f1]

Definitions: CURLPIPE_ANY, and ENABLE_WAKEUP / ENABLE_INTERNAL_WAKEUP conditionally enabled when socketpair support exists and Winsock is not used (the latter additionally requires threaded resolving), plus INITIAL_MAX_CONCURRENT_STREAMS.

<a id="u-8dd427c9fd97"></a>
### `multihandle.h module code (L84–L86)`

`module_region` · [lib/multihandle.h:L84-L86][f1]

Comment identifying struct Curl_multi as the external CURLM handle.

<a id="u-16e2fe7ff674"></a>
### `multihandle.h module code (L199–L201)`

`module_region` · [lib/multihandle.h:L199-L201][f1]

Closing include guard.

<a id="u-8596feaeb2e1"></a>
### `Curl_fixed_buf`

`struct Curl_fixed_buf` · [lib/multihandle.h:L81-L84][f1]

Fixed-size buffer header: allocated length plus an inline data area following the struct.

<a id="u-2dadfe7ea0df"></a>
### `Curl_multi`

`struct Curl_multi` · [lib/multihandle.h:L87-L199][f1]

The CURLM multi handle: identity magic and transfer counters (alive, really alive, total ever, max concurrent streams); mid-indexed transfer sets process/dirty/pending/msgsent (a mid lives in at most one of process/pending/msgsent, dirty may overlap process); the multi API call stack, timeout list, internal admin easy handle (mid 0), socket and push callbacks with user pointers, DNS and TLS caches, lazy fixed transfer buffers, event (ev) and notification (ntfy) subsystems, a protocol-lifetime proto_hash (elements needing their own destructors via Curl_hash_add2), connection shutdown and pool state, timer callback, conditional wakeup socketpairs (ENABLE_WAKEUP / ENABLE_INTERNAL_WAKEUP, both disabled for Winsock), connection limits, and flag bits including dead (set when a callback returned error) and quick_exit.

**Notes.**

- field: dead=TRUE means a callback failed and processing should abort.
- field: xfer_buf/xfer_ulbuf/xfer_sockbuf are lazily allocated and each has a *_borrowed flag.

uses: [curl_multi_ev](r12-multi-event.md#u-800f55154f52), [Curl_hash](r8-container-types.md#u-691a9d9c68ec)

**Uncertainties.**

- Semantics of members such as last_pending_mid, last_resolv_id and recheckstate are only named by comments; their update logic lives outside this header.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multihandle.h
