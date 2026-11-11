# Ranges and tuples formatting

**Capability.** Range detection and formatting: classification traits, map/set/sequence formatters, join views, and tuple formatting.

Everything for formatting containers and tuples: range-ness detection traits, kind classification, per-kind formatters, and join/tuple_join view factories. Exotic-character join overloads are also here.

**Depends on.**

- [Printf implementation](printf-implementation.md) · graph-confirmed · 5 edge(s) · Range and tuple formatting shares the printf module's error reporting helper.

Parent: [fmt formatting library](fmt-formatting-library.md)

## Units (25)

<a id="u-c39686bbda4c"></a>
### `ranges.h-conjunction`

`template <typename...> struct conjunction : std::true_type` · [include/fmt/ranges.h:L390-L390][f1]

Short-circuiting variadic type-level AND: empty pack is true, single predicate is itself, and a head that is false short-circuits to the head without instantiating the tail — used in formatter enable_if conditions to avoid instantiating is_formattable_delayed for non-ranges.

<a id="u-d56fdc31117e"></a>
### `ranges.h-container-adaptor-formatter`

`template <typename T, typename Char> struct formatter< T, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L826-L834][f1]

For container adaptors whose range_format_kind is disabled, this formatter inherits from the formatter of detail::all<T::container_type> so parsing and element formatting come from the sequence formatter.

Its format override extracts the protected member `c` through the classic derived-class `getter` trick (a struct inheriting T with a static get returning all{v.*(&getter::c)}), then delegates to the inherited formatter's format. This makes std::stack etc. print like their underlying container.

<a id="u-751d4d4dadf4"></a>
### `ranges.h-detail-all-wrapper`

`template <typename Container> struct all` · [include/fmt/ranges.h:L804-L806][f1]

A tiny adapter holding a const reference to a container and exposing begin()/end() returning const_iterators — used to give container adaptors (whose members are protected) a range-like interface the inherited formatter can consume.

<a id="u-0fe38e7e0605"></a>
### `ranges.h-index-sequence-machinery`

`template <typename T, T... N> using integer_sequence = std::integer_sequence<T, N...>;` · [include/fmt/ranges.h:L142-L143][f1]

Aliases std::integer_sequence/index_sequence/make_index_sequence when available (C++14 library or MSVC 2015+); otherwise provides a fallback: integer_sequence<T,N...> with a constexpr size() returning sizeof...(N), and make_integer_sequence recursing by prepending N-1 until the <T,0,Ns...> primary that aliases integer_sequence<T,Ns...>.

tuple_index_sequence<T> is make_index_sequence<tuple_size<T>::value>, the index set used for tuple element iteration.

<a id="u-8456e032cf90"></a>
### `ranges.h-join-overloads`

`auto join(It begin, Sentinel end, string_view sep) -> join_view<It, Sentinel>` · [include/fmt/ranges.h:L850-L852][f1]

Four factory functions returning formatting views: join(It,Sentinel,sep) builds a join_view over an iterator pair (begin is moved); join(Range&&,sep) is constexpr and, for non-tuple-like ranges, builds a join_view from detail::range_begin/end of the range (so member or ADL begin/end is used); join(const Tuple&,sep) is constexpr, marked lifetimebound because tuple_join_view stores a reference to the tuple, and returns tuple_join_view; the initializer_list overload is deprecated and forwards to the iterator-pair overload via std::begin/end.

All are pure view constructors — no formatting happens here.

<a id="u-4531374685aa"></a>
### `ranges.h-join-view-formatter`

`template <typename It, typename Sentinel, typename Char> struct formatter<join_view<I…` · [include/fmt/ranges.h:L681-L699][f1]

join_view is a lightweight non-owning view holding begin, end, and a separator string_view.

Its formatter parses by delegating entirely to a formatter for the iterator's value type (so specifiers apply to every element), and format iterates: it returns immediately for an empty range, formats the first element, then repeatedly copies the separator and formats each subsequent element, advancing the context between writes. The view is taken by const& when the iterator is copy-constructible, otherwise by value/mutable reference, since move-only iterators cannot be copied out.

<a id="u-d713dc2df609"></a>
### `ranges.h-map-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L569-L587][f1]

Formats map-kind ranges as `{k1: v1, k2: v2}`.

It stores a formatter pair (via the get_formatters tuple trick) for the map's value_type, a no_delimiters_ flag, and nested specs. parse: if input is non-empty, parses nested specs up to ':', then an optional 'n' sets no_delimiters_, then requires either '}' or ':' (anything else is "invalid format specifier"), advances the context, and finally parses empty specs into both element formatters with debug format forced. format delegates to specs_.write; write_body writes '{' unless no_delimiters_, then for each map entry writes ", " between entries and formats the key/value pair via for_each2 with format_tuple_element using ": " as separator, then '}' unless no_delimiters_.

<a id="u-8416bc73d6f9"></a>
### `ranges.h-map-set-detection-traits`

`class is_map` · [include/fmt/ranges.h:L35-L42][f1]

Two SFINAE probe classes: is_map<T> is true when T names a member type `mapped_type`; is_set<T> is true when T names `key_type` and is not a map.

Both use the classic check-overload idiom and yield compile-time constants, no runtime behavior.

<a id="u-c4b88b1996af"></a>
### `ranges.h-optional-like-detection`

`template <typename T, typename _ = void> struct is_optional_like_ : std::false_type` · [include/fmt/ranges.h:L133-L134][f1]

is_optional_like_ is a SFINAE trait true when T has both has_value() and value(); used only to exclude optional-like types from is_range so optionals format via their own formatter rather than as sequences.

<a id="u-c356f6c10f84"></a>
### `ranges.h-range-begin-range-end-overloads`

`template <typename T, size_t N> auto range_begin(const T (&arr)[N]) -> const T*` · [include/fmt/ranges.h:L54-L57][f1]

Three overload layers for obtaining iterators of a range: C arrays decay to pointers (begin=arr, end=arr+N); member-function overloads forward to rng.begin()/rng.end() with forwarding; ADL overloads call unqualified begin/end but are disabled via enable_if when member functions exist, so member functions always win.

All are constexpr where marked and simply return the obtained iterator/sentinel.

<a id="u-3ba3be85c61d"></a>
### `ranges.h-range-detection-traits`

`template <typename T, typename Enable = void> struct has_member_fn_begin_end_t : std:…` · [include/fmt/ranges.h:L62-L63][f1]

Compile-time detection of range-ness: has_member_fn_begin_end_t is true when *rng.begin() and rng.end() are valid; has_const_begin_end/has_mutable_begin_end probe the detail::range_begin/end free functions on const/non-const lvalues respectively (the mutable variant adds a dummy int for old-MSVC SFINAE); is_range_ is the disjunction of the two probes.

Pure type-level machinery, no runtime effect.

<a id="u-21602bbee644"></a>
### `ranges.h-range-format-kind`

`template <typename T> struct range_format_kind_ : std::integral_constant<range_format…` · [include/fmt/ranges.h:L252-L259][f1]

range_format_kind_ classifies a range: disabled if the uncvref'd element type equals the range type itself (self-referential guard, e.g. a range of itself), else map if is_map, set if is_set, otherwise sequence.

The public range_format_kind yields this constant for ranges and disabled for non-ranges, driving which formatter specialization is selected.

<a id="u-770daeac9f71"></a>
### `ranges.h-range-formatter`

`FMT_EXPORT template <typename T, typename Char, typename Enable = void> struct range_…` · [include/fmt/ranges.h:L396-L415][f1]

The core range formatter for a single element type T (enabled only when T is its own uncvref'd formattable type).

It holds an underlying element formatter, default `[`/`]` brackets and ", " separator, an is_debug flag, and nested_format_specs. parse: first forces debug format on the underlying formatter; if input is empty, delegates straight to underlying parse. Otherwise it parses nested specs up to ':', and if exhausted delegates to underlying parse. Then a switch on the next char: 'n' clears brackets; '?' sets is_debug, clears brackets, and requires a following 's' (else report_error), falling through to 's' which requires T==Char (else error), and unless debug, sets double-quote brackets, clears the separator, and turns debug format off; after the switch, a remaining ':' consumes the colon and turns debug format off before delegating to underlying parse — any other non-'}' char is an error. format delegates to specs_.write; write_body obtains begin/end via detail::range_begin/end, and if is_debug copies all elements into a memory buffer and writes them as a debug-escaped string (the non-Char overload of write_debug_string is a no-op returning out, unreachable when is_debug since 's' required T==Char). Otherwise it writes the opening bracket, then each element with the separator between successive items, formatting through the underlying formatter with the context advanced between writes, and finally the closing bracket. underlying() exposes the element formatter for customization; set_separator/set_brackets adjust punctuation.

<a id="u-5cf0cf48d79e"></a>
### `ranges.h-range-reference-type`

`template <typename R> struct range_reference_type_impl` · [include/fmt/ranges.h:L231-L233][f1]

Computes a range's element type: range_reference_type is decltype(*range_begin(lvalue)) normally, with a special-cased T[N] -> T& impl for old MSVC that misdeduces array reference types; uncvref_type strips cv and references from that.

This is the element type the range formatter instantiates its underlying formatter with.

<a id="u-f04fe7161bf2"></a>
### `ranges.h-range-support-traits`

`template <typename Char, typename Element> using range_formatter_type = formatter<rem…` · [include/fmt/ranges.h:L378-L379][f1]

is_range is is_range_ minus optional-like types and types convertible to string_view (so strings format as strings, not sequences).

range_formatter_type is the element formatter instantiation; maybe_const_range picks `const R` when const begin/end are valid so const ranges can be formatted; is_formattable_delayed defers element formattability checking to avoid hard errors during formatter selection.

<a id="u-0932942a9659"></a>
### `ranges.h-sequence-set-range-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<conjuncti…` · [include/fmt/ranges.h:L532-L549][f1]

The generic range formatter specialization for kinds other than disabled, map, string, and debug_string.

It wraps a range_formatter over the uncvref'd element type of maybe_const_range<R> (const R when const iteration is valid). The constructor switches brackets to '{'/'}' at compile time when the kind is set; parse and format are pure forwarding to the inner range_formatter. Declares `nonlocking` so the top-level format machinery knows it cannot be split into per-element locks.

<a id="u-ab163421d7c9"></a>
### `ranges.h-string-range-formatter`

`template <typename R, typename Char> struct formatter< R, Char, enable_if_t<range_for…` · [include/fmt/ranges.h:L636-L654][f1]

Formats ranges classified as string or debug_string by delegating to a formatter for a string-like type: std_string_view<Char> if the range's begin/end pair is constructible into it, otherwise std::basic_string<Char> (a copy).

parse forwards to the underlying string formatter and, for debug_string kind, additionally calls set_debug_format() so output is escaped/quoted. format constructs the string type from range_begin/range_end and formats it.

<a id="u-17326cb73f2b"></a>
### `ranges.h-tuple-element-parse-format-functors`

`template <typename Char> struct parse_empty_specs` · [include/fmt/ranges.h:L265-L266][f1]

Two small functor structs used with for_each over formatter tuples.

parse_empty_specs::operator() calls each element formatter's parse on the shared context and then forces debug format on (maybe_set_debug_format(f,true)). format_tuple_element::operator() writes the separator before every element except the first (i>0), formats the value through the element formatter, advances the context, and increments the counter — this is what produces the `a, b` and `k: v` spacing in tuple and map output.

<a id="u-07f38570e014"></a>
### `ranges.h-tuple-formatter`

`template <typename Tuple, typename Char> struct formatter< Tuple, Char, // format_as …` · [include/fmt/ranges.h:L300-L322][f1]

Formats tuple-like types (excluding those with format_as, which takes precedence to avoid infinite recursion for self-referential tuple-likes) as `(a, b, c)`.

It stores one formatter per element type (via the get_formatters decltype trick), default separator ", " and round brackets, and a nested_format_specs for the whole-tuple spec. parse consumes nested specs up to ':', then an optional 'n' that clears brackets and separator, and reports "invalid format specifier" for anything other than '}' — then parses empty specs into every element formatter with debug format forced on. format delegates to specs_.write with write_body as the body callback; write_body copies the opening bracket, runs for_each2 over formatters and value with format_tuple_element, and copies the closing bracket. set_separator/set_brackets let users (and derived formatters) customize punctuation.

<a id="u-a234fd8d6a74"></a>
### `ranges.h-tuple-get-formatters`

`namespace tuple` · [include/fmt/ranges.h:L218-L219][f1]

A helper namespace for MSVC 2019 workaround: result_t<Char,T...> is a std::tuple of formatter<remove_cvref_t<T>,Char>..., and get_formatters is an unevaluated decltype-only factory whose return type is used to declare the member `formatters_` in tuple, map, and tuple-join formatters — it is never actually called.

<a id="u-9d77c8564594"></a>
### `ranges.h-tuple-iteration-helpers`

`template <typename Tuple, typename F, size_t... Is> FMT_CONSTEXPR void for_each(index…` · [include/fmt/ranges.h:L190-L196][f1]

for_each applies f to each element of a tuple via pack expansion over an index sequence (the unused-array idiom guarantees left-to-right evaluation and C++11 compatibility); the no-sequence overload derives the sequence from tuple_size of the decayed tuple type.

for_each2 does the same over two tuples in parallel, pairing get<Is>(t1) with get<Is>(t2); both forward the callables and tuples.

<a id="u-fcda8e6b2252"></a>
### `ranges.h-tuple-join-view-formatter`

`template <typename Tuple, typename Char> struct formatter<tuple_join_view<Tuple, Char…` · [include/fmt/ranges.h:L739-L742][f1]

Formats tuple_join_view (a reference to a tuple plus a separator) as `a<sep>b<sep>c`.

parse dispatches on tuple_size via integral_constant: the size-0 overload returns ctx.begin() unchanged; for N>0 the body is compiled out unless FMT_TUPLE_JOIN_SPECIFIERS is enabled (default 0), in which case it parses each element formatter and reports "incompatible format specs for tuple elements" if the parsed ends disagree. format likewise recurses over do_format with integral_constant<N>: the size-0 base returns ctx.out(); each step formats element (tuple_size-N) through its stored formatter, and for N>1 copies the separator, advances the context, and recurses on N-1. Element formatters are stored per element type via the get_formatters trick.

<a id="u-9390ec06cc25"></a>
### `ranges.h-tuple-like-detection-and-formattability`

`class is_tuple_like_` · [include/fmt/ranges.h:L123-L131][f1]

is_tuple_like_ detects std::tuple_size via SFINAE; the public is_tuple_like additionally excludes ranges.

is_tuple_formattable_ is false for non-tuple-like types; for tuple-like ones it checks that every element type is formattable by building an integer_sequence<bool, is_formattable<tuple_element<Is,T>,C>::value...> and matching it against a non-negative index sequence via the all_true overload pair — any false collapses to the variatic false_type fallback. This is the gate the tuple formatter's specialization uses.

<a id="u-43e8dea7d21a"></a>
### `xchar.h-join-overloads`

`template <typename It, typename Sentinel, typename S, typename Char = typename declty…` · [include/fmt/xchar.h:L145-L151][f2]

Construct range/tuple join views for exotic character types: iterator-pair join, generic range join (disabled for tuple-like ranges), a FMT_DEPRECATED initializer_list overload for wchar_t, and a tuple-like join returning tuple_join_view.

Each converts the separator to a string view via detail::to_string_view and is enabled only when the deduced Char is not char.

<a id="u-18a8d33bed1d"></a>
### `is_container_adaptor`

`struct is_container_adaptor` · [include/fmt/ranges.h:L816-L824][f1]

SFINAE trait true when T names a member type `container_type` (e.g. std::stack, std::queue, std::priority_queue); used to route such types to the underlying-container formatter even though their range kind is disabled.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/xchar.h
