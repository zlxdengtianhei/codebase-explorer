# Tool Variable Store and Expansion

**Capability.** Linked-list variable store backing --variable definitions and {{name}}/{{name:func...}} expansion with a chain of content functions (trim, json, url, b64, 64dec).

Use for how the tool defines, stores and expands command-line variables. setvariable parses specifications; varexpand substitutes references and applies varfunc chains over the store.

**Depends on.**

- [Extended Attribute Metadata](r6-tool-xattr-metadata.md) · graph-confirmed · 9 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 26 edge(s)

Parent: [Command-Line Tool Support](r6-tool-side.md)

## Units (4)

<a id="u-bcc60386083a"></a>
### `setvariable`

`ParameterError setvariable(const char *input)` · [src/var.c:L370-L489][f1]

Parses a --variable specification and stores the resulting variable, returning PARAM_OK for recoverable syntax problems after a warning (they skip the assignment).

If the input starts with '%', the name names an environment import: the name is alphanumerics/underscore only, 1 to MAX_VAR_LEN-1 characters, else a warning and PARAM_OK. With a default after the name it is copied to a local buffer for getenv lookup; importing a variable that is unset with no default is an error returning PARAM_EXPAND_ERROR; when the environment value exists it becomes the content (blank values supported deliberately via getenv rather than curl_getenv). Next an optional byte-range suffix '[num]' or '[num-num]' is parsed with curlx_str_number/curlx_str_single; malformed ranges, or start greater than end, return PARAM_VAR_SYNTAX. Content source: '@' reads a file (or stdin for '-') via file2memory_range over the parsed range; failure to open reports the errno string and returns PARAM_READ_ERROR; non-empty content is caller-allocated (contalloc TRUE). '=' takes the rest of the line verbatim, applying the byte range by advancing the pointer and clamping the end offset to the last byte (a start beyond the length yields empty content). Any other syntax warns and returns PARAM_OK. Finally addvariable stores the name/content; if that fails and the content was file-allocated, it is freed before propagating PARAM_NO_MEM.

**Notes.**

- failure: Imported environment content is never copied here; it aliases the environment string.
- condition: Range syntax is validated even for '=' content, where startoffset beyond the length silently produces an empty variable.

calls: [var.c-variable-store](r6-tool-variable-store.md#u-8fe7ee3c3289), [tool-paramhlp-file2memory-range](r9-tool-paramhlp.md#u-60bd880c7bef), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- A byte range combined with '@' file content is passed to file2memory_range; how that function applies startoffset/endoffset (including failures on out-of-range values) is defined in tool_paramhlp.c, not here.
- Whether imported-then-ranged content ('%' with '[n-m]' and no default) is handled — the range branch does not touch an already-set env content — suggests ranges apply only to '=' and '@' forms, but this is inferred, not stated.

<a id="u-acc1e71177f3"></a>
### `varexpand`

`ParameterError varexpand(const char *line, struct dynbuf *out, bool *replaced)` · [src/var.c:L203-L333][f1]

Expands {{name}} and {{name:func...}} references in a line into an output dynbuf, setting *replaced when any variable was substituted.

The output dynbuf is initialized with a MAX_EXPAND_CONTENT (10 MB) limit. A '\{{' escape emits the literal '{{' verbatim and continues after it. An unterminated '{{' without '}}' warns 'missing close }}' and stops scanning, leaving the rest unprocessed. A name that is empty or at least MAX_VAR_LEN long, or containing characters other than alphanumerics and underscore, warns and inserts the original text verbatim. Valid names are looked up with varcontent; when the reference carries a ':functions' part, varfunc is applied to the stored value (and a varfunc error propagates as that error). A found variable containing a NUL byte within its content is rejected with 'variable contains NUL byte' and PARAM_EXPAND_ERROR, since NUL bytes cannot be represented. The value (possibly empty) is appended, the scratch buffer freed, and scanning resumes after the '}}'. When nothing was replaced the output dynbuf is freed and *replaced is FALSE; otherwise any remaining suffix after the last '}}' is appended and *replaced is TRUE. All allocation failures return PARAM_NO_MEM immediately, leaving the partially built dynbuf unfreed by this function.

**Notes.**

- condition: If no variable was replaced, the entire input is effectively discarded: the dynbuf is freed and *replaced reports FALSE.
- failure: PARAM_NO_MEM returns after dynbuf errors do not free the partially built output buffer.

calls: [var.c-variable-store](r6-tool-variable-store.md#u-8fe7ee3c3289), [varfunc](r6-tool-variable-store.md#u-b1c8c0248ffd)

**Uncertainties.**

- The unterminated '{{' branch breaks out of the loop after warning but the already-emitted prefix text stays in the dynbuf while *replaced may be FALSE; whether the caller then uses or frees that buffer is not visible here.
- Behavior when a function-modified value is empty but the variable existed (value pointer from dynbuf, vlen 0) is not explicitly handled beyond appending nothing.

<a id="u-b1c8c0248ffd"></a>
### `varfunc`

`static ParameterError varfunc(char *c, /* content */ size_t clen, /* content length *…` · [src/var.c:L75-L201][f1]

Applies a left-to-right chain of variable functions (trim, json, url, b64, 64dec) to a content buffer, accumulating the result in a dynbuf.

The loop skips the leading colon, matches function names with FUNCMATCH, and on each lap resets the output buffer. trim strips leading (including CR/LF) and trailing whitespace; json JSON-quotes via jsonquoted only when content is non-empty; url percent-encodes with curl_easy_escape; b64 base64-encodes; 64dec base64-decodes, writing the literal string '[64dec-fail]' into the output on decode failure instead of erroring out. Memory failures in any function set PARAM_NO_MEM and break. An unrecognized function reports an error naming the whole function string and returns PARAM_EXPAND_ERROR. After each successful lap the output is copied into a fresh NUL-terminated buffer that becomes the input for the next function, and the scratch buffer is freed before return; on error the output dynbuf is freed by this function.

**Notes.**

- condition: A '}' encountered as the function character ends the chain immediately, leaving the output as-is.
- failure: 64dec failure is not an error; only a failure to append the '[64dec-fail]' text produces PARAM_NO_MEM.

calls: [jsonquoted](r12-writeout-output.md#u-f48962618bda), [curlx_base64_encode](r4-base64-codec.md#u-6cff14e8366f), [curlx_base64_decode](r4-base64-codec.md#u-153cda566bc5), [curl_easy_escape](r7-string-escape-utils.md#u-dc93e6e10bfa)

**Uncertainties.**

- Whether the caller expects the output dynbuf to remain initialized on success is inferred from the on-error curlx_dyn_free only; the success-path buffer ownership depends on the caller.

<a id="u-8fe7ee3c3289"></a>
### `var.c-variable-store`

`void varcleanup(void)` · [src/var.c:L37-L46][f1]

Helpers implementing the linked-list variable store hanging off global->variables.

varcleanup walks the list, freeing each node's content (through CURL_UNCONST because content is stored const) and the node itself, without nulling global->variables. varcontent finds a stored variable by exact name match of the given length (length equality plus strncmp) and returns a const pointer, or NULL. addvariable first checks for an existing name and notes 'Overwriting variable' when found (the old entry is not removed; the new entry is prepended, so it shadows the old). It callocs a node sized for the name, copies the name bytes (the terminator already present), and stores the content either as given (contalloc TRUE, adopting caller-owned memory) or as a copy via curlx_memdup0; on any allocation failure it frees the partial node and returns PARAM_NO_MEM, otherwise PARAM_OK after prepending to the list.

**Notes.**

- side_effect: Prepending means later setvariable calls with the same name shadow earlier ones; varcleanup only frees the nodes reachable from the head, and the shadowed node leaks.

calls: [strdup.c-allocation-and-zeroing-helpers](r11-buffer-alloc-convert.md#u-c74b7ad5f6c4)

**Uncertainties.**

- Whether shadowed (overwritten) variable nodes are ever freed elsewhere is not visible in this file; from this source they appear to remain in the list.
- varcleanup does not reset global->variables to NULL after freeing.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/var.c
