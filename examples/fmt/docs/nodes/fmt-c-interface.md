# C ABI Surface

**Capability.** Header-only C interface: the type-tag enum, tagged-union argument struct, error codes, exported entry-point declarations, C macros expanding to vformat/vprint calls, and per-type arg constructor helpers.

This is the entire API visible to C code; the macros build compound-literal arg arrays and delegate to the two declared entry points.

**Depended on by.**

- [C ABI Implementation](fmt-c-impl.md) · model-inferred · 0 edge(s)

Parent: [C API](fmt-c.md)

## Units (3)

<a id="u-8d41297c3c3a"></a>
### `fmt-c-h-exported-c-interface`

`enum` · [include/fmt/fmt-c.h:L36-L46][f1]

Defines the stable C ABI surface: a type-tag enum, a tagged-union argument struct, negative error codes, and declarations of two variadic-by-array entry points.

fmt_type gives explicit values where they matter (fmt_int=1 so fmt_uint=2; fmt_bool=7 so fmt_char..fmt_cstring are 8..13; fmt_pointer=14); intermediate values are implicit. fmt_arg pairs a fmt_type discriminator with an anonymous union of one int/uint/bool/char/float/double/long double, a const char*, or a const void*; the uint_value slot is commented as also used for pointers and custom data. Error codes are fmt_error=-1 and fmt_error_invalid_arg=-2. FMT_CAPI is chosen at preprocessing time: on Windows without FMT_HEADER_ONLY it is __declspec(dllexport) under FMT_LIB_EXPORT or __declspec(dllimport) under FMT_SHARED; elsewhere a default-visibility attribute on GCC/Clang under either macro, empty otherwise. The declarations fmt_vformat(buffer,size,fmt,args,num_args) and fmt_vprint(stream,fmt,args,num_args) are C-linkage when compiled as C++.

**Notes.**

- contract: Callers must keep the buffer/args alive across the call; this header only declares the functions and does not define them.

**Uncertainties.**

- Return-value and buffering semantics of fmt_vformat/fmt_vprint are declared here but implemented elsewhere, so truncation or error behavior cannot be established from this file.

<a id="u-1febe4f2d0e0"></a>
### `fmt-c-h-c-macros`

`enum` · [include/fmt/fmt-c.h:L117-L117][f1]

C-only macro layer that turns calls like fmt_format(buf, size, "...", a, b) into fmt_vformat/fmt_vprint with a heap-allocated (compound-literal) fmt_arg array and an argument count.

FMT_MAKE_ARG uses _Generic over every listed C integer, floating, character, bool, and pointer type to pick the matching fmt_from_* constructor; the default association calls fmt_unsupported_type (declared void FMT_CAPI, defined elsewhere), so unsupported operand types reach the library instead of failing to compile. fmt_signed_char is signed char, or an empty enum under MSVC without Clang; a #error requires MSVC 2019+ with /Zc:preprocessor. FMT_NARG counts up to 16 arguments (0 when empty); FMT_MAP dispatches to FMT_MAP_0..16 to apply FMT_MAKE_ARG to each argument, producing a comma-separated initializer list. FMT_VA_SELECT expands to FMT_MAKE_NULL (NULL) when no arguments are given, otherwise to the (fmt_arg[]){...} compound literal; FMT_FORMAT_ARGS assembles (fmt, args, N) and the fmt_format/fmt_print wrappers forward to the v-functions.

**Notes.**

- failure: More than 16 arguments break the FMT_NARG counting scheme and yield wrong behavior rather than a diagnostic visible here.

<a id="u-473c9d3bd3d2"></a>
### `fmt-c-h-arg-constructors`

`static inline fmt_arg fmt_from_int(long long x)` · [include/fmt/fmt-c.h:L76-L78][f1]

Nine static inline helpers, compiled only when the header is included as C, each returning an fmt_arg via a designated initializer that sets the matching fmt_type tag and the corresponding union member (fmt_from_int, fmt_from_uint, fmt_from_bool, fmt_from_char, fmt_from_float, fmt_from_double, fmt_from_long_double, fmt_from_str, fmt_from_ptr).

They perform no validation and copy the value or pointer as given.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/fmt-c.h