# Multi event assessment and notifications

**Capability.** Per-multi socket event bookkeeping (assign, assess transfers/connections, dirty/done tracking) and the notification queue headers.

Read to understand how socket readiness is attributed to transfers inside the multi handle; the API prototypes document each contract.

**Depended on by.**

- [Multi handle state](r12-multihandle-state.md) · model-inferred · 0 edge(s)

Parent: [Multi-handle core](r12-multi-core.md)

## Units (4)

<a id="u-6e607e07b91d"></a>
### `multi_ev.h module code (L1–L35)`

`module_region` · [lib/multi_ev.h:L1-L35][f1]

Guard, license, includes of hash.h and forward declarations of Curl_easy, Curl_multi, easy_pollset, uint32_bset, plus the CURL_META_MEV_POLLSET meta key definition.

<a id="u-800f55154f52"></a>
### `curl_multi_ev`

`struct curl_multi_ev` · [lib/multi_ev.h:L36-L38][f1]

Multi-handle event state: currently only the socket hash sh_entries holding one mev_sh_entry per announced socket, keyed by socket value.

uses: [Curl_hash](r8-container-types.md#u-691a9d9c68ec)

<a id="u-89054f52b718"></a>
### `multi_ev.h module code (L38–L80)`

`module_region` · [lib/multi_ev.h:L38-L80][f1]

Public multi-event API prototypes: init/cleanup, assign, assess_xfer/assess_xfer_bset/assess_conn, dirty_xfers, socket_done, xfer_done, conn_done, with behavioral contracts in comments.

uses: [curl_multi_ev](r12-multi-event.md#u-800f55154f52)

<a id="u-6827ba64c1ec"></a>
### `multi_ntfy.h-state-and-macros`

`struct curl_multi_ntfy` · [lib/multi_ntfy.h:L33-L40][f2]

Header for the multi-handle notification queue.

struct curl_multi_ntfy holds the registered callback and its data, the chunk list head/tail, a flags word whose high bit (CURL_MNTFY_FLAG_HAS_ENTRIES) marks queued entries, and a latched CURLMcode failure. The CURLM_NTFY macro is a guarded shorthand that calls Curl_mntfy_add only when the easy handle, its multi handle, and a callback all exist; CURL_MNTFY_HAS_ENTRIES tests the queued-entries flag. Function declarations correspond to the implementations documented in multi_ntfy.c.

**Uncertainties.**

- curl_notify_callback's exact signature is not shown in this header; only its use as ntfy_cb type is evidenced.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/multi_ev.h
[f2]: ../../../../../../eval/curl-2c04412/lib/multi_ntfy.h
