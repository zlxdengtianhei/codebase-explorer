# C ABI Implementation

**Capability.** Implements the declared C entry points: converts fmt_arg arrays into basic_format_arg entries, formats into caller buffers, and prints to FILE streams with C status codes.

Read alongside fmt-c-interface; each exported function is defined here and depends on the conversion helper.

**Depends on.**

- [C ABI Surface](fmt-c-interface.md) · model-inferred · 0 edge(s)

Parent: [C API](fmt-c.md)

## Units (3)

<a id="u-a6a4b5f8fb66"></a>
### `convert_c_format_args`

`static int convert_c_format_args( fmt::basic_format_arg<fmt::format_context>* format_…` · [src/fmt-c.cc:L14-L36][f1]

Converts a C-style fmt_arg array into fmt basic_format_arg entries for the C API.

It rejects num_args above 16 with fmt_error_invalid_arg before converting anything, then per element switches on args[i].type: int, uint, bool, char, float, double, long double, cstring, and pointer each copy the matching union member into format_args[i]; any other type returns fmt_error_invalid_arg immediately, leaving already-converted entries in place. On full success it returns 0. Elements beyond num_args in the caller's array are untouched.

**Notes.**

- failure: An unrecognized args[i].type aborts the loop with fmt_error_invalid_arg; earlier slots keep their converted values.

uses: [fmt_vformat](fmt-c-impl.md#u-3d1a243a5735), [fmt_vprint](fmt-c-impl.md#u-6bf2af6338c5)

<a id="u-3d1a243a5735"></a>
### `fmt_vformat`

`int fmt_vformat(char* buffer, size_t size, const char* fmt, const fmt_arg* args, size…` · [src/fmt-c.cc:L38-L49][f1]

C entry point that formats into a caller-supplied buffer and returns a C status code.

Conversion errors from convert_c_format_args are returned unchanged. Otherwise it formats to at most size bytes at buffer via fmt::vformat_to_n inside FMT_TRY, returning the untruncated result size cast to int on success (the untruncated size can exceed size, so it is not a pure byte-count). Any caught exception is swallowed and yields fmt_error.

**Notes.**

- contract: Return values are overloaded: fmt_error* constants signal failure; otherwise the return is the untruncated formatted size.

calls: [convert_c_format_args](fmt-c-impl.md#u-a6a4b5f8fb66)

<a id="u-6bf2af6338c5"></a>
### `fmt_vprint`

`int fmt_vprint(FILE* stream, const char* fmt, const fmt_arg* args, size_t num_args)` · [src/fmt-c.cc:L54-L64][f1]

C entry point that prints formatted output to a FILE stream, returning 0 on success or a C error code.

It first converts the fmt_arg array via convert_c_format_args and propagates a nonzero conversion error unchanged. Inside FMT_TRY it calls fmt::vprint on the stream; on success it returns 0, and any caught exception is swallowed and reported as fmt_error.

calls: [convert_c_format_args](fmt-c-impl.md#u-a6a4b5f8fb66)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/src/fmt-c.cc