# Value & Utility Formatters

**Capability.** Formats filesystem::path (with native-string bridging), std::complex via the element's numeric specs, std::bitset via nested_formatter, plus delegating formatters, ptr() overloads for smart pointers, bit-reference traits, and Clang bitint aliases.

A mixed bag of concrete std types; delegating-formatters covers thin wrappers over primitive formatters, and ptr-helpers gives uniform address formatting.

Parent: [std Type Formatters](std-h.md)

## Units (8)

<a id="u-3f673c46a2a7"></a>
### `std-h-bitset-formatter`

`template <size_t N, typename Char> struct formatter<std::bitset<N>, Char> : nested_fo…` · [include/fmt/std.h:L353-L357][f1]

Formats std::bitset<N> by inheriting nested_formatter so fill/align/width nesting applies.

format converts the bitset with bs.to_string<Char>(), wraps it in a basic_string_view, and returns this->write(ctx, this->nested(view)) so the nested machinery performs padding around the 0/1 digit string.

<a id="u-35ea9c44b622"></a>
### `std-h-complex-formatter`

`template <typename T> struct is_tuple_like<std::complex<T>> : std::false_type` · [include/fmt/std.h:L764-L765][f1]

Formats std::complex<T> using the numeric format specs of T (is_tuple_like is specialized to false so ranges/tuple formatting never applies).

parse delegates to parse_format_specs with T's type constant, so empty or '}' specs are accepted. format copies the specs, resolves dynamic width and precision when any are dynamic, then: with zero width writes directly via do_format; otherwise renders into a memory_buffer with width/fill/align cleared and wraps the result with outer_specs carrying the original width, fill, and align. do_format writes '(real+imagi)' when real() != 0, forcing a plus sign on the imaginary part after the first write, otherwise just 'imagi'; a space is inserted before 'i' when imag() is not finite.

**Notes.**

- condition: The '+' sign on the imaginary part is set via specs.set_sign(sign::plus) only on the real-nonzero branch; the pure-imaginary branch never shows an explicit plus.
- failure: Non-finite imaginary values get a separating space before 'i' in both branches.

<a id="u-257e050b8fe6"></a>
### `std-h-delegating-formatters`

`template <typename Char> struct formatter<std::thread::id, Char> : basic_ostream_form…` · [include/fmt/std.h:L366-L367][f1]

Thin formatters that delegate to an underlying primitive formatter.

formatter<std::thread::id, Char> is just basic_ostream_formatter<Char>, so ids print through their ostream operator<< unlocalized. formatter<bitint<N>> and <ubitint<N>> inherit from the long long / ullong formatters, static_assert N <= 64, convert via format_as, and format through the base. formatter<BitRef> (enabled only for bit-reference-like types) converts to bool and formats as bool, which makes libc++ bit_const_reference and vector<bool>/bitset references printable. formatter<std::byte> formats as unsigned via a static_cast to unsigned char. formatter<std::atomic<T>> loads (a synchronizing read) and formats T; formatter<std::atomic_flag> uses v.test() and formats as bool. formatter<std::reference_wrapper<T>> (enabled only when T is formattable and has neither format_as nor a formatter format_as member, guarding against implicit conversion to T&) formats ref.get() through formatter<remove_cvref_t<T>>.

**Notes.**

- side_effect: Formatting a std::atomic performs load(), which is an atomic read, and atomic_flag::test() is an atomic query.

<a id="u-1b3bea1f69dc"></a>
### `std-h-path-formatter`

`template <typename Char> struct formatter<std::filesystem::path, Char>` · [include/fmt/std.h:L302-L310][f1]

Formats std::filesystem::path with align, width, '?' escaping, and an optional 'g' generic-path modifier.

parse parses align, then width (digit or '{') into specs_ with width_ref_, then sets debug_ on '?', then records path_type_ = 'g'. format copies the specs, resolves dynamic width, and chooses the source string: p.native() when no type was given, otherwise the generic form via generic_string<value_type>(). Without debug_ it converts via get_path_string and writes with specs; with debug_ it builds the escaped/quoted representation via write_escaped_path (which can FMT_ASSERT on invalid wide UTF) and writes that. set_debug_format toggles debug_.

calls: [std-h-filesystem-helpers](std-values.md#u-52d32afb595d)

**Uncertainties.**

- Characters after 'g' are not consumed, so trailing spec characters are silently ignored by parse as written.

<a id="u-52d32afb595d"></a>
### `std-h-filesystem-helpers`

`template <typename Char, typename PathChar> auto get_path_string(const std::filesyste…` · [include/fmt/std.h:L104-L113][f1]

Bridges std::filesystem::path native strings to the formatter's character type.

get_path_string returns to_utf8<wchar_t>(native, to_utf8_error_policy::wtf) when the formatter Char is char and the native string is wchar_t, else p.string<Char>(). write_escaped_path fills a quoted buffer: for char-formatter/wchar-native it escapes into a wchar_t buffer then converts via to_utf8<wchar_t>::convert, asserting FMT_ASSERT(valid, "invalid utf16"); when Char equals PathChar it escapes using path::value_type; otherwise it escapes p.string<Char>(). Both are compiled only when FMT_CPP_LIB_FILESYSTEM is enabled.

**Notes.**

- failure: Invalid UTF-16 in a wide path triggers FMT_ASSERT in write_escaped_path, an abort-style failure on invalid input.

<a id="u-fb2f01028fb8"></a>
### `std-h-ptr-helpers`

`template <typename T, typename Deleter> auto ptr(const std::unique_ptr<T, Deleter>& p…` · [include/fmt/std.h:L292-L295][f1]

Overloads of ptr() returning the stored raw pointer as const void*: one for std::unique_ptr<T, Deleter> (p.get()) and one for std::shared_ptr<T> (p.get()), giving a uniform way to format smart-pointer addresses.

<a id="u-f06385afb486"></a>
### `std-h-bit-traits`

`template <typename T, typename Enable = void> struct has_flip : std::false_type` · [include/fmt/std.h:L261-L262][f1]

Traits identifying bit-reference-like types and format_as members.

has_flip is true when declval<T>().flip() is valid. is_bit_reference_like requires convertible-to-bool, nothrow-assignable-from-bool, and has_flip; a libc++ workaround (unless FMT_IMPORT_STD) unconditionally marks std::__bit_const_reference<C> as true because the standard returns bool from const bitset::operator[]. has_format_as_member is true when formatter<T>::format_as(const T&) is a valid expression.

<a id="u-8ec3439bea01"></a>
### `std-h-bitint`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/std.h:L80-L97][f1]

Defines detail aliases for Clang's extended integer types.

When FMT_USE_BITINT (Clang >= 1500 and not CUDA, or user-provided) bitint<N> is _BitInt(N) and ubitint<N> is unsigned _BitInt(N), with a Clang pragma suppressing the -Wbit-int-extension warning; otherwise both become empty struct templates so dependent formatters still compile.

**Uncertainties.**

- FMT_USE_BITINT's third state when only FMT_CLANG_VERSION is absent is resolved by macro order shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/std.h