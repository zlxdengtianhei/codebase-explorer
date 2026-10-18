# Format parsing and emission

**Capability.** Parses conversion specs (flags, width, precision, %N$ positional args) into segment arrays, then renders numbers, doubles, pointers, and strings through a byte-sink abstraction with pad/run primitives.

Read this child to trace a format spec from parsefmt through parse_flags/parse_conversion to the out_* renderers and stream_* emitters. Parse errors yield zero output from formatf.

Parent: [printf engine \(mprintf\)](r9-mprintf.md)

## Units (13)

<a id="u-46012175d62f"></a>
### `lib-mprintf-c-format-data-structures`

`enum` · [lib/mprintf.c:L50-L64][f1]

Defines the type and flag vocabulary shared by the format parser and formatters.

FormatType enumerates what each argument is; the flags bitfield records conversion modifiers; the DOLLAR enum tracks positional (%N$) usage state; struct va_input stores one argument's type plus a union of its value; struct outsegment describes one output piece (literal substring or conversion) with width, precision, flags, argument index, source pointer, and length; struct nsprintf carries the bounded-buffer sink state for snprintf-style calls; struct asprintf carries the dynbuf sink with a 512-byte staging buffer and an merr error code; struct ioprintf carries a FILE* plus an error flag; struct mproperty is the per-conversion width/precision/flags bundle passed to the out_* emitters.

<a id="u-28d66dada51d"></a>
### `dollarstring`

`static int dollarstring(const char *p, const char **end)` · [lib/mprintf.c:L151-L159][f1]

Parses a positional '%N$' argument number, returning it 0-based.

It reads a number via curlx_str_number with MAX_PARAMETERS as the upper bound, then requires an immediately following '$' via curlx_str_single; if the number parse fails, the '$' is missing, or the number is zero, it returns -1 and does not advance *end. On success it stores the post-'$' position in *end and returns num-1.

**Notes.**

- failure: Returns -1 for a zero argument number as well as for malformed input, so '%0$' is treated as no positional specifier.

calls: [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- Whether curlx_str_number accepts surrounding whitespace or signs is defined in strparse.c, not visible here.

<a id="u-7022ea537fbf"></a>
### `formatf`

`static int formatf(void *userp, /* untouched by format(), sent to the stream() functi…` · [lib/mprintf.c:L1089-L1217][f1]

Core engine: parses the format with parsefmt (returning 0 written on any parse error) and then emits each output segment in order.

Literal portions go through stream_zrun. Per conversion it builds an mproperty from the segment: a width from the WIDTHPARAM argument is negated when negative (INT_MIN clamped to INT_MAX) with LEFT set and PAD_NIL cleared; precision comes from the PRECPARAM argument (negative treated as omitted), the literal precision, or -1. The argument's parsed type selects an emitter: unsigned/signed integers to out_number, strings to out_string, pointers to out_pointer, doubles to out_double. %n (MTYPE_INTPTR) first commits pending sink output via the flush callback and aborts if that fails, then stores the running count as int64_t/long/int/short per size flags. Any emitter returning TRUE stops and returns the count so far. Stack arrays size MAX_SEGMENTS/MAX_PARAMETERS/BUFFSIZE bound all work.

calls: [parsefmt](r9-mprintf-format-engine.md#u-8e0d657f8c8d), [stream_zrun](r9-mprintf-format-engine.md#u-f1916838efd6), [out_number](r9-mprintf-format-engine.md#u-4273e4a6b56a), [out_string](r9-mprintf-format-engine.md#u-6a592c0bff9a), [out_double](r9-mprintf-format-engine.md#u-75ac76097632); uses: [function::out_pointer::27106][f1]

**Uncertainties.**

- On parse failure formatf returns 0 with no partial output; whether callers distinguish that from an empty format is decided at call sites.
- The flush callback is invoked only before %n; sinks that buffer otherwise rely on their own final flush.

<a id="u-75ac76097632"></a>
### `out_double`

`static bool out_double(void *userp, int (*stream)(unsigned char, void *), mp_streamn …` · [lib/mprintf.c:L737-L824][f1]

Formats one double by building a snprintf format string in a 32-byte fmt buffer and letting the platform snprintf do the conversion into work (BUFFSIZE bytes), then streaming the result via stream_run.

Left-justify, '+', space, and '#' flags are copied as '-', '+', ' ', '#'. Width >= 0 is clamped to BUFFSIZE-1 and appended via curl_msnprintf. Precision >= 0 is computed defensively: prec above BUFFSIZE-1 is clamped; if width > 0 and prec <= width the precision budget shrinks by the width; each integer digit of the value reduces the allowed precision, and prec is clamped again and floored at 0 before being appended as '.<prec>'. 'l' is appended for FLAGS_LONG (matching 'L' handled at parse time via LONGDOUBLE type), then the conversion character e/E, g/G, or f/F chosen by flags and case. On _WIN32 curlx_win32_snprintf performs the conversion, otherwise snprintf. Returns stream_run's abort status for the rendered bytes.

calls: [stream_run](r9-mprintf-format-engine.md#u-270a839426ce); uses: [lib-mprintf-c-nsprintf-family](r9-mprintf-formatter-families.md#u-e17299de2a1f)

**Uncertainties.**

- long double values arrive already narrowed to double by the parser, so long-double precision beyond double is not preserved here.
- The 'l' flag for a double conversion is unusual; platform snprintf behavior with '%lf' style formats is assumed correct.

<a id="u-4273e4a6b56a"></a>
### `out_number`

`static bool out_number(void *userp, int (*stream)(unsigned char, void *), mp_streamn …` · [lib/mprintf.c:L826-L967][f1]

Renders one integer (or with FLAGS_CHAR, a single character) into work and streams it with padding/sign handling.

Character mode emits the byte as (char)num with space padding before or after depending on LEFT, setting width to 1 after left-padding. Otherwise base is 8 for OCTAL, 16 for HEX (digit case chosen by UPPER), 10 for UNSIGNED; signed decimal conversion negates safely by adding/subtracting 1 around the negation so INT64_MIN does not overflow. Digits are written backwards from workend. Default precision of 1 applies when prec is -1; precision zero-fills to the given count. ALT adds a leading '0' for octal when precision would not already supply one, and reserves width for the '0x'/'0X' prefix on hex. Sign or space consumes one width unit. Right-aligned space padding, sign ('-', '+' or ' '), hex prefix, zero padding for PAD_NIL, the digits themselves, and finally left-aligned space padding are emitted in that order; every emission may abort via its helper's TRUE return, which propagates immediately.

calls: [stream_pad](r9-mprintf-format-engine.md#u-5b62971138af), [stream_run](r9-mprintf-format-engine.md#u-270a839426ce)

**Uncertainties.**

- Zero-padding plus LEFT: PAD_NIL is only applied when LEFT is unset, matching the parse-time clearing of PAD_NIL by '-'; other flag combinations inherit C-printf conventions but some corner cases (e.g. zero pad with precision) follow this ordering rather than a documented standard.

<a id="u-2a416fb5f826"></a>
### `out_pointer`

`static bool out_pointer(void *userp, int (*stream)(unsigned char, void *), mp_streamn…` · [lib/mprintf.c:L1035-L1072][f1]

Renders a %p argument.

A non-NULL pointer is reformatted as a hex-with-alt number: FLAGS_HEX and FLAGS_ALT are added to p->flags and out_number is invoked with the pointer value cast to size_t. A NULL pointer emits the literal "(nil)", reducing width by its length and applying left or right space padding around the text. Propagates TRUE from the helpers to abort formatting.

calls: [out_number](r9-mprintf-format-engine.md#u-4273e4a6b56a), [stream_pad](r9-mprintf-format-engine.md#u-5b62971138af), [stream_run](r9-mprintf-format-engine.md#u-270a839426ce)

**Uncertainties.**

- The pointer is printed as a plain hex number, not the platform's %p notation; leading '0x' comes from out_number's ALT hex handling.

<a id="u-6a592c0bff9a"></a>
### `out_string`

`static bool out_string(void *userp, int (*stream)(unsigned char, void *), mp_streamn …` · [lib/mprintf.c:L971-L1033][f1]

Renders one string argument with optional ALT quoting, width padding, and precision truncation.

A NULL string becomes "(nil)" when precision permits (prec == -1 or at least its length), clearing ALT so it is not quoted; otherwise it becomes an empty string. With a real string and prec != -1, len is set to prec without reading the string; prec == -1 gives len = strlen(str) or 0 for an empty string. Width is reduced by the (INT_MAX-clamped) length. An opening '"' is emitted for ALT, then for non-left alignment space padding, then the bytes: without precision via stream_run for exactly len bytes; with precision via stream_zrun, which stops at a NUL since the buffer may be shorter than prec or not null-terminated. Left-alignment padding and a closing ALT quote follow. Any helper returning TRUE aborts and propagates.

calls: [stream_run](r9-mprintf-format-engine.md#u-270a839426ce), [stream_zrun](r9-mprintf-format-engine.md#u-f1916838efd6), [stream_pad](r9-mprintf-format-engine.md#u-5b62971138af)

<a id="u-3317c78c7df3"></a>
### `parse_conversion`

`static bool parse_conversion(const char f, unsigned int *flagp, FormatType *typep)` · [lib/mprintf.c:L342-L441][f1]

Maps one conversion character to a FormatType and additional flags, returning TRUE (invalid, conversion disregarded) only for unrecognized characters.

'S' is string with ALT; 's' string; 'n' INTPTR; 'p' PTR. Integer conversions choose LONGLONG/LONG/INT types from the size flags: 'd'/'i' signed; 'u' unsigned; 'o' unsigned plus OCTAL; 'x' unsigned plus HEX; 'X' unsigned plus HEX and UPPER. 'c' sets FLAGS_CHAR with type INT. Floating conversions pick LONGDOUBLE over DOUBLE when FLAGS_LONGDOUBLE is set: 'f' plain, 'F' plus UPPER, 'e'/'E' plus FLOATE (and UPPER for 'E'), 'g'/'G' plus FLOATG (and UPPER for 'G'). Valid conversions write the merged flags and type through the out pointers and return FALSE.

<a id="u-79aca4bd080b"></a>
### `parse_flags`

`static int parse_flags(const char **fmtp, unsigned int *flagsp, int use_dollar, int *…` · [lib/mprintf.c:L185-L340][f1]

Scans the flag/width/precision portion of one conversion spec, accumulating flags until a character that is not part of the spec.

Recognized flag characters set SPACE, SHOWSIGN ('+' also clears PAD_NIL), ALT, SHORT (h), LONG (l, doubling to LONGLONG), LONGDOUBLE (L), LONGLONG (q), and size_t/curl_off_t width via 'z'/'O'/'I' mapped to LONG or LONGLONG depending on SIZEOF_* macros (the 'I32'/'I64' forms only under _WIN32). A leading '0' sets PAD_NIL unless LEFT is set, then falls through to digit handling. Digits set FLAGS_WIDTH and parse the width with curlx_str_number capped at INT_MAX, returning PFMT_WIDTH on overflow. '.' sets precision: with '*' it sets FLAGS_PRECPARAM, reading 'N$' via dollarstring when use_dollar is DOLLAR_USE (PFMT_DOLLARPREC if invalid) else marking width/precision as -1 to come from the next argument; with literal digits it sets FLAGS_PREC, allows a leading '-' to negate, and returns PFMT_PREC on overflow; specifying both precision forms returns PFMT_PRECMIX. '*' sets FLAGS_WIDTHPARAM and likewise reads 'N$' or defers to the next argument (PFMT_DOLLARWIDTH if invalid). Any other character ends the loop and is stepped back. On success writes flags, precision, width, and the advanced cursor to the outputs and returns PFMT_OK.

calls: [dollarstring](r9-mprintf-format-engine.md#u-28d66dada51d), [strparse.c-wrappers](r11-strparse-word-scanning.md#u-04060759ad16)

**Uncertainties.**

- The exact acceptance rules of curlx_str_number (signs, overflow handling) live in strparse.c.

<a id="u-8e0d657f8c8d"></a>
### `parsefmt`

`static int parsefmt(const char *format, struct outsegment *out, struct va_input *in, …` · [lib/mprintf.c:L443-L651][f1]

Pre-parses the whole format string into an output-segment array and an input-argument array, returning a PFMT_* code (zero on success).

It walks the format: at each '%' it closes the pending literal run as an outsegment; '%%' emits just a literal '%' segment and continues. Otherwise it optionally parses an 'N$' positional via dollarstring, switching use_dollar: a failed positional after a prior successful one is PFMT_DOLLAR, while the first failure means arguments are consumed sequentially (DOLLAR_NOPE). It then calls parse_flags (propagating its error codes) and parse_conversion, skipping the segment entirely for an invalid conversion character. FLAGS_WIDTHPARAM and FLAGS_PRECPARAM bind width or precision to an argument index: negative means take the next sequential parameter; an index already marked used is rejected as PFMT_WIDTHARG or PFMT_PRECARG; an index at or beyond MAX_PARAMETERS is PFMT_MANYARGS; the index is typed MTYPE_WIDTH/MTYPE_PRECISION and marked used. The main argument index likewise comes from the positional or param_num++, with PFMT_MANYARGS past the cap, and a trailing literal run becomes a final FLAGS_SUBSTR segment; exceeding MAX_SEGMENTS segments returns PFMT_MANYSEGS. Finally it consumes va_arg for each slot 0..max_param according to its type, returning PFMT_INPUTGAP if any slot in that range was never referenced, and reports the piece counts through opieces/ipieces.

**Notes.**

- failure: va_arg is consumed only after all structural errors are detected, so an error return leaves the caller's va_list untouched by this pass.

calls: [dollarstring](r9-mprintf-format-engine.md#u-28d66dada51d), [parse_flags](r9-mprintf-format-engine.md#u-79aca4bd080b), [parse_conversion](r9-mprintf-format-engine.md#u-3317c78c7df3)

**Uncertainties.**

- max_param bounds the va_arg loop, so referenced slots beyond the highest index used are not validated beyond the INPUTGAP check over 0..max_param.
- DEBUGASSERT in the default va_arg case suggests unreachable types, but behavior in release builds is unspecified here.

<a id="u-5b62971138af"></a>
### `stream_pad`

`static bool stream_pad(void *userp, int (*stream)(unsigned char, void *), mp_streamn …` · [lib/mprintf.c:L699-L717][f1]

Emits 'num' copies of a pad byte, returning TRUE to abort.

num <= 0 emits nothing. The pad byte selects a 16-byte constant source (pad_zeros or pad_spaces); the request is emitted in PAD_RUN chunks via stream_run until fewer than 16 remain, then one final run. Propagates stream_run's abort status.

calls: [stream_run](r9-mprintf-format-engine.md#u-270a839426ce)

<a id="u-270a839426ce"></a>
### `stream_run`

`static bool stream_run(void *userp, int (*stream)(unsigned char, void *), mp_streamn …` · [lib/mprintf.c:L671-L689][f1]

Emits a run of bytes through the sink, returning TRUE to abort formatting.

With no block callback it loops the byte callback (stream) over the buffer, and any nonzero stream return aborts. With a block callback (streamn) it hands the whole run over; the callback's return value counts accepted bytes into *donep, and accepting fewer than len aborts formatting. Zero-length runs are a no-op returning FALSE.

<a id="u-f1916838efd6"></a>
### `stream_zrun`

`static bool stream_zrun(void *userp, int (*stream)(unsigned char, void *), mp_streamn…` · [lib/mprintf.c:L725-L735][f1]

Emits at most 'len' bytes of a null-terminated string, stopping early at a NUL, then delegates to stream_run.

It scans with an explicit byte loop instead of memchr because callers (out_string with a precision, formatf for literal segments) pass unclamped lengths that may exceed the object, and memchr would read past the buffer's end. Returns TRUE to abort formatting.

calls: [stream_run](r9-mprintf-format-engine.md#u-270a839426ce)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mprintf.c
