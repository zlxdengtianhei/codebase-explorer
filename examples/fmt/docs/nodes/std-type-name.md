# Type Name Formatting

**Capability.** Formats std::type_info via demangled names, normalizing libc++ inline namespaces and MSVC ABI keywords/spaces per platform under FMT_USE_RTTI.

Read when porting type-name output; write_demangled_name selects the platform path and both normalize helpers clean the demangler output.

Parent: [std Type Formatters](std-h.md)

## Units (4)

<a id="u-67e48241f0cd"></a>
### `std-h-type-info-formatter`

`template <> struct formatter<std::type_info>` · [include/fmt/std.h:L576-L578][f1]

Formats std::type_info by writing its demangled name; compiled only when FMT_USE_RTTI.

parse accepts no specs; format returns detail::write_demangled_name(ctx.out(), ti), whose platform branches determine the exact output (demangled and namespace-normalized where supported, raw name otherwise).

calls: [write_demangled_name](std-type-name.md#u-8b3040208410)

<a id="u-8b3040208410"></a>
### `write_demangled_name`

`template <typename OutputIt> auto write_demangled_name(OutputIt out, const std::type_…` · [include/fmt/std.h:L223-L257][f1]

Writes a human-readable type name for std::type_info, selected per platform at compile time under FMT_USE_RTTI.

With FMT_HAS_ABI_CXA_DEMANGLE it calls abi::__cxa_demangle wrapped in a unique_ptr with free deleter; on success it normalizes inline namespaces in place and writes the result, on demangler failure it writes ti.name() raw. Under MSVC with _MSVC_STL_UPDATE it applies normalize_msvc_abi_name; under MSVC ABI with libc++ it copies the name, applies both normalizers (keyword strip then inline-namespace strip, the latter operating on name_copy's data), and writes it. Otherwise it writes ti.name() unchanged.

calls: [normalize_libcxx_inline_namespaces](std-type-name.md#u-24dc39a7a34c), [normalize_msvc_abi_name](std-type-name.md#u-7b16b420448d)

**Uncertainties.**

- Whether __cxa_demangle failing on gabi++ (the __GABIXX_CXXAI note) is fully avoided is only encoded via the FMT_HAS_ABI_CXA_DEMANGLE macro definition elsewhere in the file.

<a id="u-24dc39a7a34c"></a>
### `normalize_libcxx_inline_namespaces`

`inline auto normalize_libcxx_inline_namespaces(string_view demangled_name_view, char*…` · [include/fmt/std.h:L170-L197][f1]

Strips libc++/libstdc++ ABI-versioning inline namespaces from a demangled name in place.

If the view starts with "std::", it scans from offset 5: when it sees a '__' prefix it searches ahead for '::'; if found, it skips the inline-namespace token entirely (removing std::__1::, std::__1::__fs::, std::__cxx11::, and std::filesystem::__cxx11:: collapses to std::filesystem::), otherwise it copies the character. Returns the shortened view {begin, to-begin} or the original view if no std:: prefix. Relies on the buffer being NUL-terminated, as noted for the demangled name.

**Uncertainties.**

- Safety of reading next[1] at the end of the buffer depends on the NUL-termination assumption stated in the comment, not verified here.

<a id="u-7b16b420448d"></a>
### `normalize_msvc_abi_name`

`class OutputIt> auto normalize_msvc_abi_name(string_view abi_name_view, OutputIt out)…` · [include/fmt/std.h:L199-L221][f1]

Removes MSVC's 'enum ', 'class ', 'union ', 'struct ' keywords and all spaces from an ABI type name while copying to out.

For each index it tests the remaining suffix with starts_with; on a keyword match it advances the index past the keyword (by 4, 5, or 6) and skips copying for those positions, otherwise it emits the current character only when it is not a space. Returns the advanced output iterator.

**Uncertainties.**

- Keyword removal uses index arithmetic (i += 4/5/6) that assumes the loop's ++i also runs; boundary indices at the string end rely on this interplay.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h