# Multi-handle core

**Capability.** The CURLM engine: the multi handle's transfer/socket state and lifecycle, its event-assessment subsystem, notification queue, and the refcounted description of connection targets.

Read these nodes when changing multi-interface scheduling, socket event accounting, or connection identity. The multi state enum requires matching updates to statenames[] in curl_trc.c.

**Children.**

- [Multi handle state](r12-multihandle-state.md) `r12-multihandle-state` · 7 unit(s)
- [Multi event assessment and notifications](r12-multi-event.md) `r12-multi-event` · 4 unit(s)
- [Connection identity](r12-connection-identity.md) `r12-connection-identity` · 3 unit(s)

**Depended on by.**

- [SSH/SFTP/SCP shared client](r12-ssh-client.md) · model-inferred · 0 edge(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
