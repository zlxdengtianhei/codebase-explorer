# Platform adaptation

**Capability.** OS-specific behavior beyond general portability: AmigaOS bsdsocket library lifecycle, a select wrapper, and an IPv4 resolver override; VMS C-RTL feature setup, shell detection, and exit encoding.

Consult when a specific OS needs non-portable startup, teardown, or resolver behavior. Both platforms hook into generic curl paths.

**Children.**

- [AmigaOS support](r12-amigaos-support.md) `r12-amigaos-support` · 4 unit(s)
- [VMS support](r12-vms-support.md) `r12-vms-support` · 4 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
