# Miscellaneous small formatters

**Capability.** Formatters for std::tm, atomics, atomic_flag, and std::byte, each delegating to simpler underlying formatters.

A grab-bag of small formatters: the default tm formatter, atomic and atomic_flag wrappers, and std::byte. Each is a thin delegation to an existing formatter.

Parent: [Standard library type formatters](standard-library-type-formatters.md)

## Units (4)

<a id="u-62b3e028d0a0"></a>
### `chrono.h-formatter-std-tm`

`template <typename Char> struct formatter<std::tm, Char>` · [include/fmt/chrono.h:L2115-L2123][f1]

Standard formatter for std::tm with default format "%F %T".

do_parse handles alignment, width, an 'L' localized flag, and validates the spec body with tm_format_checker (timezone allowed iff std::tm has tm_gmtoff), replacing the stored format only for a non-empty spec. do_format drives a tm_writer (with optional subsecond duration) over the format into a memory buffer and writes it with the specs; the public parse passes has_tm_gmtoff<std::tm>, and format formats with second precision and no subseconds. set_format lets derived calendar formatters override the default spec.

<a id="u-ea826370cbab"></a>
### `std.h-atomic-flag-formatter`

`template <typename Char> struct formatter<std::atomic_flag, Char> : formatter<bool, C…` · [include/fmt/std.h:L752-L754][f2]

Formats std::atomic_flag as a bool via its test() member; only compiled when __cpp_lib_atomic_flag_test is available.

<a id="u-5618b86d4fdf"></a>
### `std.h-atomic-formatter`

`template <typename T, typename Char> struct formatter<std::atomic<T>, Char, enable_if…` · [include/fmt/std.h:L740-L744][f2]

Formats std::atomic<T> by loading the value and delegating to the formatter of T; enabled only when T itself is formattable.

<a id="u-10bbd1b2df7b"></a>
### `std.h-std-byte-formatter`

`template <typename Char> struct formatter<std::byte, Char> : formatter<unsigned, Char>` · [include/fmt/std.h:L727-L729][f2]

Formats std::byte as its unsigned char value via the unsigned formatter's format_as mechanism; only compiled with __cpp_lib_byte.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h
