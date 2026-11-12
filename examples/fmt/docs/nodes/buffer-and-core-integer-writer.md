# Buffer and Core Integer Writer

**Capability.** Implements dynamic memory buffers, 128-bit arithmetic, and core unsigned integer digit writing for formatting.

Come here for buffer storage and low-level integer digit emission. The units describe memory buffers, 128-bit operations, fill writing, and core base conversion.

**Depends on.**

- [Dragonbox Cache and Assertions](dragonbox-cache-and-assertions.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Floating-Point Formatting Core](floating-point-formatting-core.md) · graph-confirmed · 1 edge(s)
- [Format Spec Parsing and Writing](format-spec-parsing-and-writing.md) · graph-confirmed · 5 edge(s)
- [Integer and Pointer Formatting](integer-and-pointer-formatting.md) · graph-confirmed · 2 edge(s)
- [Format Argument Type Mapping](format-argument-type-mapping.md) · graph-only · 4 edge(s)
- [Compile-Time Format Checking](compile-time-format-checking.md) · graph-only · 2 edge(s)
- [Big Integer Float Formatting](big-integer-float-formatting.md) · graph-only · 1 edge(s)

Parent: [Low-Level Formatting Primitives](low-level-formatting-primitives.md)

## Units (9)

<a id="u-a5481c360af0"></a>
### `format.h-128-bit-operators`

`constexpr auto operator==(const uint128& lhs, const uint128& rhs) -> bool` · [include/fmt/format.h:L303-L306][f1]

These operators implement value semantics for a two-limb unsigned 128-bit type.

Equality compares both limbs; greater-than compares high then low; bitwise operators act per limb. Addition delegates to compound addition. Multiplication accepts only a 32-bit right operand and asserts the high limb is zero, then computes a 64-by-32 product with carry. Subtraction borrows from the high limb. Shifts special-case 64 and recurse for larger counts, otherwise combine both limbs.

<a id="u-8f4f44f8fe8d"></a>
### `format.h-decimal-formatting`

`template <typename Char, typename UInt> FMT_CONSTEXPR20 auto do_format_decimal(Char* …` · [include/fmt/format.h:L1431-L1478][f1]

The core writer formats an unsigned integer into a caller-sized buffer and returns a pointer to the first digit.

It asserts the size is sufficient, splits 128-bit values into 19-digit chunks, and writes pairs of digits from the end. The pointer wrapper returns the end of the requested width. The output-iterator wrapper tries direct pointer access, otherwise formats into a stack buffer and copies without inlining.

<a id="u-ab1dbcd36abc"></a>
### `format.h-fill-n-overloads`

`template <typename OutputIt, typename Size, typename T> FMT_CONSTEXPR auto fill_n(Out…` · [include/fmt/format.h:L533-L538][f1]

These overloads write a value repeatedly.

The generic version loops and returns the advanced iterator. The pointer/char version uses memset outside constant evaluation and asserts element size one. The appender version reserves in chunks, resizes, fills each chunk, and returns the appender.

<a id="u-8da28c117397"></a>
### `format.h-inline-memory-buffer`

`class basic_memory_buffer : public detail::buffer<T>` · [include/fmt/format.h:L965-L973][f1]

This class is a dynamically growing buffer with inline storage and an allocator.

Growth aborts fuzzing above 5000 bytes, computes one-and-a-half times capacity or the requested size, allocates, constructs or copies elements, installs the new storage, and frees old heap storage. The constructor installs inline storage and zero-fills it in constant evaluation. Move allocation either moves a propagating allocator or, for a non-propagating allocator, copies when allocators differ and the source is not inline. Move steals heap storage or copies inline storage, then resizes. Move assignment asserts no self-assignment, deallocates, and moves.

<a id="u-f1535f880d4f"></a>
### `format.h-power-of-two-formatting`

`template <typename Char, typename UInt> FMT_CONSTEXPR auto do_format_base2e(int base_…` · [include/fmt/format.h:L1502-L1513][f1]

The core writer emits digits for a power-of-two base by masking and shifting, writing backwards; it supports upper-case hex.

The pointer wrapper returns the end of the requested width. The output-iterator wrapper tries direct pointer access, otherwise formats into a stack buffer sized by the integer width and copies without inlining.

<a id="u-d7acc77837b5"></a>
### `format.h-uint128-operator`

`FMT_CONSTEXPR void operator+=(uint128 n)` · [include/fmt/format.h:L356-L362][f1]

operator+=(uint128) adds the low halves, propagates carry into the high halves, and asserts that the new high half did not overflow (new_hi >= hi_).

operator+=(uint64_t) is noexcept and adds a 64-bit value to the low half, propagating carry into the high half; it uses compiler carry intrinsics when available and otherwise performs the same carry check without asserting.

<a id="u-e233491117b6"></a>
### `is_constant_evaluated`

`constexpr auto is_constant_evaluated(bool default_value = false) noexcept -> bool` · [include/fmt/core.h:L378-L392][f2]

Returns whether evaluation is constant, choosing a compiler/library workaround, std::is_constant_evaluated, or the supplied default.

The clang/libstdc++ consteval workaround uses __builtin_is_constant_evaluated; otherwise if the library feature macro exists it uses std::is_constant_evaluated; otherwise it returns default_value. The default argument is ignored in the first two branches.

<a id="u-37727571a621"></a>
### `include/fmt/format.h:basic_memory_buffer (5)`

`class basic_memory_buffer : public detail::buffer<T>` · [include/fmt/format.h:L1058-L1066][f1]

Move-constructs a basic_memory_buffer by delegating to the private move routine, which transfers the allocator when it propagates, copies inline storage when the source used its inline array, and otherwise adopts the heap block while resetting the source to its empty inline store; the constructor is noexcept because move never allocates.

<a id="u-735209b14c7d"></a>
### `fill`

`template <typename Char, typename OutputIt> FMT_CONSTEXPR FMT_NOINLINE auto fill(Outp…` · [include/fmt/format.h:L1919-L1928][f1]

This function writes a fill pattern a requested number of times.

A single-unit fill uses the simple fill helper; a multi-unit fill copies the pattern repeatedly. It returns the advanced iterator.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/format.h
[f2]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/core.h
