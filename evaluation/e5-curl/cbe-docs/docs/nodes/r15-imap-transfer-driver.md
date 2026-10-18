# IMAP transfer driver

**Capability.** curl transfer-phase integration: connect/disconnect, do/doing/done callbacks, and the regular-transfer orchestration that parses the URL and runs the DO phase with its post hook.

These are the callbacks curl's multi interface invokes; they delegate into imap-commands and the response handlers. Use this node to trace how a transfer enters and exits the IMAP state machine.

**Depends on.**

- [IMAP commands and URL parsing](r15-imap-commands.md) · graph-confirmed · 5 edge(s)
- [IMAP core, types and framing](r15-imap-core.md) · graph-confirmed · 4 edge(s)
- [IMAP response handlers](r15-imap-resp-handlers.md) · graph-confirmed · 4 edge(s)

Parent: [IMAP protocol implementation](r15-imap-protocol.md)

## Units (6)

<a id="u-6866954b2f64"></a>
### `imap_connect`

`static CURLcode imap_connect(struct Curl_easy *data, bool *done)` · [lib/imap.c:L1947-L1971][f1]

Starts the protocol connect phase: parse URL options, then wait for the server greeting.

Missing per-connection IMAP data returns CURLE_FAILED_INIT; an options parse error propagates. Otherwise the state is set to IMAP_SERVERGREET, the response tag is primed to "*" so the greeting (untagged or tagged) is matched, and imap_multi_statemach runs non-blocking, setting *done when the machine reaches IMAP_STOP.

calls: [imap_parse_url_options](r15-imap-commands.md#u-ffce677c8d42), [imap.c-statemach-drivers](r15-imap-resp-handlers.md#u-80274aece5b5)

<a id="u-c4c8403699f7"></a>
### `imap_disconnect`

`static CURLcode imap_disconnect(struct Curl_easy *data, struct connectdata *conn, boo…` · [lib/imap.c:L2184-L2200][f1]

Disconnects an IMAP connection, attempting a graceful LOGOUT only under safe conditions.

The LOGOUT and the blocking statemach run only when per-connection data exists, the connection is not already dead, the protocol connect phase started (protoconnstart), and the pingpong channel has nothing pending to send (Curl_pp_needs_flush) - otherwise waiting for a reply on a stale connection would hang. Statemach errors during the LOGOUT drain are ignored; the function always returns CURLE_OK.

calls: [imap_perform_logout](r15-imap-commands.md#u-a003897ff7e4), [imap.c-statemach-drivers](r15-imap-resp-handlers.md#u-80274aece5b5)

<a id="u-9b54e67ac480"></a>
### `imap_do`

`static CURLcode imap_do(struct Curl_easy *data, bool *done)` · [lib/imap.c:L2154-L2175][f1]

Registered as the protocol do_it function; parses the URL into the request and runs the regular transfer.

Missing per-easy meta data returns CURLE_FAILED_INIT; *done defaults to FALSE. Failures from imap_parse_url_path or imap_parse_custom_request abort before any command is sent; otherwise imap_regular_transfer drives the DO phase and *done reflects a completed DO phase.

calls: [imap_parse_url_path](r15-imap-commands.md#u-8d6606ab08e5), [imap_parse_custom_request](r15-imap-commands.md#u-9ea5c240cbf3), [imap_regular_transfer](r15-imap-transfer-driver.md#u-9c85aebb7791)

<a id="u-6df26b24ca28"></a>
### `imap_doing`

`static CURLcode imap_doing(struct Curl_easy *data, bool *dophase_done)` · [lib/imap.c:L2203-L2221][f1]

Multi-interface callback that progresses the DO phase.

Missing per-easy data returns CURLE_FAILED_INIT. It runs the non-blocking statemachine; on failure it logs 'DO phase failed', and on a completed DO phase it runs imap_dophase_done (which only adjusts the transfer setup for no-body requests) and logs completion. The statemachine result propagates.

calls: [imap.c-statemach-drivers](r15-imap-resp-handlers.md#u-80274aece5b5)

<a id="u-b1c188f114f7"></a>
### `imap_done`

`static CURLcode imap_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/imap.c:L1982-L2024][f1]

Finalizes the transfer after the DO phase, deciding whether the server must confirm the transfer.

Missing per-connection data returns CURLE_FAILED_INIT; missing per-easy data is a silent CURLE_OK. On error or premature end it marks the connection for closure (connclose) and returns the original status. Otherwise, when not connect_only and the request actually transferred a body - a FETCH (uid or mindex, no custom), a custom command that set maxdownload > 0, an upload, or a MIME post - it either moves to IMAP_FETCH_FINAL for downloads or, for uploads, first sends an empty line to terminate the APPEND literal and moves to IMAP_APPEND_FINAL, then runs imap_block_statemach blocking until the final reply is consumed. In all paths imap_easy_reset clears the request state before returning; the reset result is not part of the return value.

calls: [imap.c-lifecycle](r15-imap-core.md#u-22d7e8df995e), [imap.c-statemach-drivers](r15-imap-resp-handlers.md#u-80274aece5b5)

**Uncertainties.**

- Whether Curl_pp_sendf failure on the APPEND terminator prevents running the statemachine is explicit here (yes: only when !result), but server-side effects of the truncated literal are not determinable from this file.

<a id="u-9c85aebb7791"></a>
### `imap_regular_transfer`

`static CURLcode imap_regular_transfer(struct Curl_easy *data, struct IMAP *imap, bool…` · [lib/imap.c:L2122-L2143][f1]

Runs the DO phase for a regular transfer and its immediate post-phase hook.

It resets data->req.size to unknown (-1) and clears progress state, then calls imap_perform; on success and a completed DO phase it calls imap_dophase_done, which only matters when no body is expected: it switches the transfer to a no-op receiver (Curl_xfer_setup_nop) when imap->transfer is not PPTRANSFER_BODY, otherwise doing nothing, and always returns CURLE_OK. The connected argument to imap_dophase_done is ignored by its body.

calls: [imap_perform](r15-imap-commands.md#u-d94c3119caaf), [progress-c-state-reset-and-counters](r9-progress-timing-and-policy.md#u-f8d97fbe4396)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/imap.c
