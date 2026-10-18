# Command-line tool support

**Capability.** The curl tool's configuration lifecycle (alloc/free of OperationConfig and global init/free), config-file parsing, CURLOPT-style callbacks for read/seek/opensocket, and terminal password prompting.

Config parsing feeds OperationConfig which mirrors UserDefined; callbacks adapt tool file descriptors to libcurl; getpass_r provides per-platform no-echo password input.

**Children.**

- [Tool configuration](r15-cli-config.md) `r15-cli-config` · 14 unit(s)
- [Tool libcurl callbacks](r15-cli-callbacks.md) `r15-cli-callbacks` · 5 unit(s)
- [Terminal password input](r15-cli-terminal-input.md) `r15-cli-terminal-input` · 9 unit(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
