# HTTP/2 Connection Filter (nghttp2)

**Capability.** Full HTTP/2 client support over a connection filter: session and stream lifecycle, nghttp2 event processing, per-transfer stream I/O, and switching/upgrading connections to HTTP/2.

Read this subtree to understand how libcurl drives nghttp2 sessions, converts frames into transfer results, and installs or upgrades to the HTTP/2 filter. Children separate session/window management, frame callbacks, per-stream data flow, and the filter vtable plus upgrade/switch/push logic.

**Children.**

- [H2 Session & Window Management](r2-h2-session-lifecycle.md) `r2-h2-session-lifecycle` · 20 unit(s)
- [H2 Frame Event Handling](r2-h2-frame-processing.md) `r2-h2-frame-processing` · 17 unit(s)
- [H2 Per-Stream Data Flow](r2-h2-stream-xfer.md) `r2-h2-stream-xfer` · 13 unit(s)
- [H2 Filter Vtable, Upgrade & Push](r2-h2-filter-upgrade.md) `r2-h2-filter-upgrade` · 24 unit(s)

**Depends on.**

- [Buffer Queue Model](r2-bufq-buffer-queues.md) · model-inferred · 0 edge(s)

Parent: [Connection Filter Protocol Stacks](r2-protocol-filters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
