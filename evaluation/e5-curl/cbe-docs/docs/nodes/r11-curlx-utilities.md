# curlx shared utilities

**Capability.** Portable, dependency-free primitives for string scanning, number parsing, allocation/zeroing, character-set storage, and Windows text conversion shared by library and tool code.

Use this subtree when you need the low-level building blocks (word extraction, quoted-word and numeric parsing, strdup-style helpers, the u8 string set). Consumers across alt-svc, DNS, RTSP and the tool call into it, so changes here affect many modules.

**Children.**

- [string parsing primitives](r11-strparse-word-scanning.md) `r11-strparse-word-scanning` · 7 unit(s)
- [allocation and Windows text conversion](r11-buffer-alloc-convert.md) `r11-buffer-alloc-convert` · 4 unit(s)
- [u8 string set](r11-u8-strset.md) `r11-u8-strset` · 14 unit(s)

Parent: [curl codebase](r11-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
