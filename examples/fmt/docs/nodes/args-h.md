# Dynamic Argument Stores

**Capability.** Builds named and positional format-argument collections at runtime, with stable linked-list storage for copied values and reference_wrapper normalization.

Use dynamic_format_arg_store to assemble arguments incrementally; named arguments are kept via a placeholder layout surfaced by size() and the basic_format_args conversion.

**Depends on.**

- [Error Reporting](core-errors.md) · graph-confirmed · 1 edge(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Units (12)

<a id="u-88deca88db84"></a>
### `args.h-dynamic-arg-list`

`FMT_BEGIN_NAMESPACE namespace detail` · [include/fmt/args.h:L30-L37][f1]

Linked list that owns copied argument values so their addresses stay stable while the store's vector of format args may reallocate.

node is a fake template (workarounds for an MSVC C2504 bug and clang -Wweak-vtables) with a virtual destructor and a unique_ptr next link; typed_node<T> adds a T value, copying from any Arg, with a string_view overload copying data/size into a string so the store never dangles on the caller's buffer. dynamic_arg_list::push<T> allocates a typed_node<T>, captures a reference to its value, splices the node onto the front of the head_ chain via std::move, and returns the value reference; the reference stays valid because nodes are never relocated or destroyed until the store is cleared. If allocation throws the list is unchanged because the node is not yet linked.

<a id="u-7bd7b224d743"></a>
### `args.h-dynamic-format-arg-store-storage`

`class dynamic_arg_list { template <typename T> struct typed_node : node<> { T value; …` · [include/fmt/args.h:L66-L78][f1]

Private storage and copy policy of dynamic_format_arg_store.

data_ holds the contiguous basic_format_arg entries handed to formatting; named_info_ holds named-argument metadata; dynamic_args_ owns copied values that data_ entries point into, so that backing storage must grow without relocation. need_copy<T>::value is true unless T is a reference wrapper, a basic/std string view, or a type whose mapped type is cstring, string, or custom — those are stored by reference. stored_t maps string-convertible non-wrapper types to std::basic_string for stable storage. The default constructor is trivial and the conversion operator builds basic_format_args from data(), size(), and whether named arguments exist.

uses: [args.h-reference-wrapper-unwrap](args-h.md#u-b5581b58fe02)

**Uncertainties.**

- The mapped_type_constant<T, char_type> values driving need_copy are defined in format.h, not supplied here.

<a id="u-b5581b58fe02"></a>
### `args.h-reference-wrapper-unwrap`

`template <typename T> struct is_reference_wrapper : std::false_type` · [include/fmt/args.h:L22-L22][f1]

Compile-time helpers that normalize std::reference_wrapper arguments to plain references before formatting.

is_reference_wrapper is false_type for arbitrary T and specializes to true_type for reference_wrapper<T>. unwrap returns a non-wrapper value unchanged by reference; the reference_wrapper overload static_casts to const T&, so formatting observes the wrapped object directly. Selection is by overload resolution; no failure paths.

uses: [args.h-dynamic-format-arg-store-storage](args-h.md#u-7bd7b224d743)

<a id="u-c2064958854c"></a>
### `basic_format_args`

`operator basic_format_args<Context>() const` · [include/fmt/args.h:L133-L136][f1]

Converts the store to basic_format_args for type-erased formatting calls.

It passes data() (skipping the placeholder slot when named arguments exist), the user-visible size(), and the flag !named_info_.empty() so consumers know a named-argument table is present.

calls: [data](args-h.md#u-fbc881ec390b), [size](args-h.md#u-d50936898274)

<a id="u-fbc881ec390b"></a>
### `data`

`auto data() const -> const basic_format_arg<Context>*` · [include/fmt/args.h:L108-L110][f1]

Returns the argument-array pointer passed to basic_format_args.

With no named arguments it is data_.data(); with named arguments the first slot holds the named-info placeholder, so the pointer is advanced by one to skip it.

uses: [args.h-dynamic-format-arg-store-storage](args-h.md#u-7bd7b224d743)

<a id="u-f3547aa7053c"></a>
### `include/fmt/args.h:emplace_arg`

`template <typename T> void emplace_arg(const named_arg<T, char_type>& arg)` · [include/fmt/args.h:L116-L128][f1]

Appends a named argument while maintaining the placeholder layout.

On the first named argument it inserts basic_format_arg(nullptr, 0) at the front of data_ as the slot that will carry the named-info table. It then appends unwrap(arg.value) and installs a pop_back guard: if named_info_.push_back or the data_[0] assignment throws, the appended value slot is popped so data_ stays consistent; on success the guard is released and data_[0] is set to {named_info_.data(), named_info_.size()}. The stored index is data_.size() - 2, assuming the placeholder occupies index 0. The single-line overload emplace_arg::3573 simply appends one unnamed argument.

calls: [args.h-reference-wrapper-unwrap](args-h.md#u-b5581b58fe02)

<a id="u-239cc3718c1b"></a>
### `push_back`

`template <typename T> void push_back(const T& arg)` · [include/fmt/args.h:L153-L158][f1]

Adds one positional argument.

At compile time need_copy<T> selects the path: copy-needing types are first stored via dynamic_args_.push<stored_t<T>>(arg), and the stable reference into the node list is emplaced; view, cstring, custom, and wrapper types are unwrapped and emplaced by reference, so the caller must keep the referenced data alive for the store's lifetime. The FMT_CONSTEXPR20 if makes the copy path constexpr-evaluable where supported.

calls: [args.h-dynamic-arg-list](args-h.md#u-88deca88db84); contract: [args.h-dynamic-format-arg-store-storage](args-h.md#u-7bd7b224d743)

<a id="u-daba28b8b4cd"></a>
### `include/fmt/args.h:push_back`

`template <typename T> void push_back(std::reference_wrapper<T> arg)` · [include/fmt/args.h:L173-L178][f1]

Adds an argument by reference to avoid copying.

A static_assert rejects wrappers of types for which need_copy<T> is false (built-in types and string views must always be copied), failing compilation otherwise. For allowed types it emplaces arg.get() directly, so later mutation of the referenced object is visible to formatting.

<a id="u-40dadd562e0d"></a>
### `include/fmt/args.h:push_back (2)`

`template <typename T> void push_back(const named_arg<T, char_type>& arg)` · [include/fmt/args.h:L185-L188][f1]

Adds a named argument.

The name is always copied into dynamic_args_ as a basic_string whose c_str() becomes arg_name, so the name outlives the call. need_copy on the value then selects between fmt::arg(arg_name, dynamic_args_.push<stored_t<T>>(arg.value)) (stored copy) and fmt::arg(arg_name, arg.value) (by reference); the resulting named_arg is inserted via the guarded emplace_arg that manages the placeholder slot.

calls: [include/fmt/args.h:emplace_arg](args-h.md#u-f3547aa7053c)

<a id="u-7bf7a2493f78"></a>
### `clear`

`void clear()` · [include/fmt/args.h:L197-L201][f1]

Erases everything from the store: clears data_ and named_info_, and replaces dynamic_args_ with a default-constructed list, freeing all copied values.

Any outstanding references returned earlier by push_back become invalid afterward.

uses: [args.h-dynamic-arg-list](args-h.md#u-88deca88db84)

<a id="u-6aa55220fcb7"></a>
### `reserve`

`void reserve(size_t new_cap, size_t new_cap_named)` · [include/fmt/args.h:L205-L210][f1]

Pre-allocates capacity for at least new_cap total arguments and new_cap_named named arguments.

FMT_ASSERT aborts (via assert_fail) when new_cap < new_cap_named, since named arguments also occupy data_ slots; otherwise both vectors are reserved.

raises: [assert_fail](core-errors.md#u-51c7265a0ebb)

<a id="u-d50936898274"></a>
### `size`

`auto size() const noexcept -> size_t` · [include/fmt/args.h:L213-L215][f1]

Returns the user-visible argument count: data_.size() minus one placeholder slot when named arguments exist, otherwise data_.size() unchanged.

Noexcept.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/args.h