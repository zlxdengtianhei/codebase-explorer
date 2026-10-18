# curl Command-Line Tool Support

**Capability.** Tool-side behavior layered on libcurl: the write callback that routes body bytes to files, terminals, or header storage with clobber-safe naming and Windows console output, and command-line form/multipart parsing into tool_mime trees translated to curl_mime handles.

Use this branch when working on the curl executable itself. Output writing handles where transferred bytes land; form parsing turns -F style arguments into mime structures.

**Children.**

- [Transfer Output Writing](r3-output-writing.md) `r3-output-writing` · 4 unit(s)
- [Form/Multipart Argument Parsing](r3-form-parsing.md) `r3-form-parsing` · 28 unit(s)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
