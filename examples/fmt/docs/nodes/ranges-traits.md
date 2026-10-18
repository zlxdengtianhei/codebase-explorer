# Range Detection Traits

**Capability.** Compile-time machinery classifying types (container, map, tuple-like, string, adaptor) and walking tuples/ranges; every formatter in this header gates on it.

Read when adding support for a new kind of range; classification here decides which formatter below is selected.

**Depended on by.**

- [Range Formatters](ranges-formatters.md) · model-inferred · 0 edge(s)

Parent: [Range Formatting](ranges-h.md)

## Units (1)

<a id="u-c4ccbfc94538"></a>
### `ranges-h-detection-traits`

`namespace detail` · [include/fmt/ranges.h:L33-L34][f1]

Compile-time machinery that classifies types and walks tuples/ranges.

is_map detects U::mapped_type and is_set detects U::key_type via SFINAE, with is_set additionally requiring !is_map. range_begin/range_end come in three overload sets: C arrays (arr / arr+N), member .begin()/.end(), and ADL begin/end that participate only when has_member_fn_begin_end_t is false. has_const_begin_end and has_mutable_begin_end probe begin/end on const and mutable references (an extra int template argument works around old MSVC SFINAE), and is_range_<T> is true if either holds. is_tuple_like_ requires std::tuple_size; is_optional_like_ requires has_value() and value(). integer_sequence/make_integer_sequence have a std fallback and a recursive C++11 fallback (make_integer_sequence<T,N> recurses down to 0). is_tuple_formattable_ uses an all_true overload trick over an integer_sequence<bool, is_formattable<tuple_element<Is,T>,C>::value...> to require every element formattable. for_each/for_each2 expand get<Is> over the index sequence to apply a functor to each element (or to paired elements of two tuples). tuple::get_formatters builds a std::tuple of per-element formatters. range_reference_type works around pre-1920 MSVC array reference deduction; uncvref_type strips cv/ref from the range's reference type. range_format_kind_ classifies: disabled when uncvref_type<T> is T itself, else map, set, or sequence. parse_empty_specs calls each element formatter's parse with the shared context and enables debug format; format_tuple_element copies the separator before every element after the first, formats the element, advances the context, and increments its counter. The public aliases refine these: is_tuple_like is tuple-like and not a range; is_range additionally excludes optional-like types and types with to_string_view; is_formattable_delayed checks formattability of the element type; conjunction short-circuits at the type level; the public range_format_kind yields disabled for anything not satisfying is_range.

imports: [include/fmt/format.h][f2]

**Uncertainties.**

- Behavior of has_to_string_view and is_formattable is defined in format.h, not in this batch; their exclusions in is_range/is_formattable_delayed cannot be verified here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/ranges.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h