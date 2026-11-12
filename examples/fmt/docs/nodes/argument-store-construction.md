# Argument Store Construction

**Capability.** Builds format argument stores and named-argument stores from references and metadata.

Come here for constructing argument stores. The units describe named-argument metadata, lvalue-reference stores, and named-argument slot initialization.

Parent: [Argument and Spec Pipeline](argument-and-spec-pipeline.md)

## Units (3)

<a id="u-e6ff4cb1e43f"></a>
### `core.h-named-argument-initialization`

`template <bool B1, bool B2, bool... Tail> constexpr auto count() -> int` · [include/fmt/core.h:L1075-L1077][f1]

Counts true boolean template values and initializes named-argument metadata.

count returns the number of true flags recursively. The non-named init overload only increments the positional argument index. The named init overload checks for a duplicate name, records the name and current positional id, and increments both indices; the static variant uses T::name instead of a stored name. Duplicate detection compares names by string-view content, not pointer identity.

<a id="u-16a5f8afa20c"></a>
### `make_format_args`

`template <typename Context = context, typename... T, int NUM_ARGS = int(sizeof...(T))…` · [include/fmt/core.h:L2773-L2780][f1]

Builds a format_arg_store from lvalue references to the arguments.

The store's descriptor and named-argument count are computed from the types; the returned store holds references rather than copies.

<a id="u-b4fccfd5d917"></a>
### `include/fmt/core.h:named_arg_store`

`template <typename Context, int NUM_ARGS, int NUM_NAMED_ARGS, ullong DESC> struct nam…` · [include/fmt/core.h:L2339-L2347][f1]

named_arg_store constructor initializes the first argument slot with the named-argument metadata pointer and count, then stores the values.

It walks the values to fill named-argument entries and positional indices. The move constructor resets the first slot to the new metadata, copies argument slots and named metadata; copy construction and assignment are deleted.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
