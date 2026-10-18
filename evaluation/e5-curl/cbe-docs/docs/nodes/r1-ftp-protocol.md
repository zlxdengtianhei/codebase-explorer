# FTP Protocol Implementation

**Capability.** Implements the FTP protocol end to end: connection setup and teardown, the login handshake, the transfer command sequence (TYPE/SIZE/REST/MDTM/PASV/PORT/RETR/STOR), URL-path splitting, data-socket management and wildcard matching, all on top of the pingpong state machine.

Enter here for anything FTP. The lifecycle child covers the do/done/disconnect phases, the two state-machine children cover command handling, and the remaining children cover path/data plumbing and wildcard transfers.

**Children.**

- [FTP Transfer Lifecycle](r1-ftp-lifecycle.md) `r1-ftp-lifecycle` · 24 unit(s)
- [FTP Login and Response States](r1-ftp-login-states.md) `r1-ftp-login-states` · 17 unit(s)
- [FTP Transfer Command States](r1-ftp-transfer-states.md) `r1-ftp-transfer-states` · 35 unit(s)
- [FTP Path and Data-Channel Helpers](r1-ftp-path-data-helpers.md) `r1-ftp-path-data-helpers` · 7 unit(s)
- [FTP Wildcard Transfer](r1-ftp-wildcard-transfer.md) `r1-ftp-wildcard-transfer` · 2 unit(s)

Parent: [curl Codebase](r1-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
