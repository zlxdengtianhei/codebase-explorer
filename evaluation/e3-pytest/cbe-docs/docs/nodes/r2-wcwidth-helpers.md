# Terminal Character Width

**Capability.** Computes terminal column widths for characters and strings (NFC-normalized, lru-cached), returning -1 for unprintable characters.

Use wcswidth for strings and wcwidth for single characters when aligning output containing wide/combining characters.

**Depended on by.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · model-inferred · 0 edge(s)

Parent: [Terminal I/O & CLI Integration Plugins](r2-io-cli-plugins.md)

## Units (2)

<a id="u-fc9075a0e801"></a>
### `wcwidth`

`def wcwidth(c: str) -> int:` · [src/_pytest/_io/wcwidth.py:L7-L43][f1]

Return the terminal column count for one character, cached with lru_cache(100).

ASCII 0x20–0x7E returns 1 via fast path; NUL and the zero-width ranges 200B–200F, 2028–202E, 2060–2063 return 0; Cc control characters return -1; combining Me/Mn categories return 0; east-asian F/W width characters return 2; everything else returns 1.

**Notes.**

- contract: -1 means non-printable; wcswidth turns any negative per-character result into -1 for the whole string.

<a id="u-437d5e6cbd0d"></a>
### `wcswidth`

`def wcswidth(s: str) -> int:` · [src/_pytest/_io/wcwidth.py:L46-L57][f1]

Sum wcwidth over the NFC-normalized characters of a string; if any character yields a negative width the whole string returns -1, otherwise the total width.

calls: [wcwidth](r2-wcwidth-helpers.md#u-fc9075a0e801)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/pytest-5989efe/src/_pytest/_io/wcwidth.py
