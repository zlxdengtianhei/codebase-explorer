# SSH backend (libssh)

**Capability.** Implements SCP and SFTP over libssh via one non-blocking state machine: session startup, host-key verification, authentication phases, quote command execution, transfer modes (upload/download/readdir), teardown, and data callbacks wired into the protocol vtables.

Use the connection/auth child for startup and authentication states, the transfer child for SFTP/SCP do-phase and data callbacks, and the quote child for pre/post-quote execution. The statemachine driver and error-transition helpers tie all states together.

**Children.**

- [SSH connection, auth and lifecycle](r9-ssh-conn-auth.md) `r9-ssh-conn-auth` · 32 unit(s)
- [SFTP and SCP transfer states](r9-ssh-transfers.md) `r9-ssh-transfers` · 55 unit(s)
- [SFTP quote commands](r9-ssh-quotes.md) `r9-ssh-quotes` · 8 unit(s)

Parent: [curl codebase](r9-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
