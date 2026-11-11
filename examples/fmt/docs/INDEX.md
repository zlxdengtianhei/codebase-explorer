# fmt: code map

This repository is the {fmt} C++ formatting library: a complete system for type-safe text formatting spanning core format/argument machinery, float-to-decimal conversion, chrono/time formatting, wide-character and styled output, printf compatibility, ranges/tuples, std-type formatters, and OS file/C API layers. The format-argument infrastructure (core.h parsing, buffers, argument storage) underpins everything, while the core formatting implementation turns parsed specs into output via a value-writing engine and Dragonbox/bigint float conversion. Specialized modules—chrono, wide/styling, printf, ranges, std types, OS/C API—build on these shared foundations rather than reimplementing them.

## Modules

- [**Core formatting implementation**](nodes/core-formatting-implementation.md) — Implements the main format.h layer: value writing, integer and float conversion algorithms, and out-of-line stdio/locale definitions. (137 units; `format.h`, `format-inl.h`, `core.h`)
  - [**Value writing and drivers**](nodes/value-writing-and-drivers.md) — Shared low-level helpers, spec-aware writing routines for strings and integers, locale-aware specs, and the formatting driver connecting arguments to writers. (79 units; `format.h`, `core.h`)
    - [**Core formatting utilities**](nodes/core-formatting-utilities.md) — Provides the header's shared low-level helpers: allocators, compile-time strings, named-argument factories, bit/UTF-8 primitives, and string-like formatter specializations. (29 units; `format.h`)
    - [**Value writing engine**](nodes/value-writing-engine.md) — Implements the spec-aware write routines for strings, integers, and localized output, plus buffer-backed memory buffers and code-point iteration used by formatting. (18 units; `format.h`, `core.h`)
    - [**Integer decimal formatting**](nodes/integer-decimal-formatting.md) — Formats integers as decimal digits using digit tables, digit counting, and stack-buffered writers, including to_string-style conversion. (10 units; `format.h`)
    - [**Locale and dynamic specs**](nodes/locale-and-dynamic-specs.md) — Adds locale-aware formatting wrappers (bytes, group_digits), digit grouping models, and dynamic width/precision resolution from format arguments. (7 units; `format.h`)
    - [**String and stream output**](nodes/string-and-stream-output.md) — Converts buffers to std::string, transcodes UTF-16/32 to UTF-8, and prints to buffered streams or FILE*, with optimizer hints. (5 units; `format.h`)
    - [**Character and pointer writers**](nodes/character-and-pointer-writers.md) — Writes single characters (with debug escaping), integers with grouping or character presentation, and pointers as hex. (5 units; `format.h`)
    - [**Formatting driver and contexts**](nodes/formatting-driver-and-contexts.md) — Drives parse callbacks during formatting and provides the argument visitors and generic formatting contexts that connect args to writers. (5 units; `format.h`)
  - [**Inline implementation and stdio**](nodes/inline-implementation-and-stdio.md) — Holds out-of-line definitions: FILE wrappers for glibc/Apple/MSVC, locale facet implementations, error formatting, UTF conversion, and vprint strategies. (25 units; `format-inl.h`)
  - [**Float to decimal conversion**](nodes/float-to-decimal-conversion.md) — Converts floating-point numbers to shortest decimal representations using Dragonbox, with an arbitrary-precision bigint fallback and shared numeric utilities. (18 units; `format-inl.h`, `format.h`)
    - [**Numeric core and assertions**](nodes/numeric-core-and-assertions.md) — Supplies 128-bit arithmetic, pow10 caches, Dragonbox multiplication helpers, and the library-wide assertion failure handler. (9 units; `format-inl.h`, `format.h`)
    - [**Float conversion entry points**](nodes/float-conversion-entry-points.md) — Converts doubles to shortest decimal digits via Dragonbox, computes log-based exponents, and exposes locale-aware vformat/vformat_to entry points. (6 units; `format.h`, `format-inl.h`)
    - [**Bigint fallback algorithm**](nodes/bigint-fallback-algorithm.md) — Implements the (FPP)^2 arbitrary-precision fallback for exact float formatting using a bigit-based bigint and boundary computation. (3 units; `format.h`)
  - [**Float presentation rendering**](nodes/float-presentation-rendering.md) — Renders converted float digits per format specs in fixed, exponential, or shortest notation, supported by bit-level binary and hexfloat primitives. (15 units; `format.h`)
    - [**Binary and float primitives**](nodes/binary-and-float-primitives.md) — Provides bit-level primitives: leading-zero counting, endianness detection, float format traits, power-of-two digit formatting, and hexfloat rendering. (8 units; `format.h`)
    - [**Float presentation writers**](nodes/float-presentation-writers.md) — Renders floats per specs in fixed, exponential, or shortest form, choosing notation by exponent and handling signs and non-finite values. (7 units; `format.h`)
- [**Format argument infrastructure**](nodes/format-argument-infrastructure.md) — Defines formatting arguments, their storage and compile-time checking, spec parsing, buffer adapters, and compile-time format string compilation. (114 units; `core.h`, `compile.h`, `printf.h`)
  - [**Parsing and buffer foundations**](nodes/parsing-and-buffer-foundations.md) — Provides the core.h base: buffer classes, argument type encoding, format-string parsing, spec parsing, and iterator/pointer buffer adapters. (68 units; `core.h`, `printf.h`)
    - [**Core argument and buffer base**](nodes/core-argument-and-buffer-base.md) — Defines core.h foundations: the buffer base class, type mapping and formattability traits, argument type encoding, and format-string parsing entry points. (30 units; `core.h`)
    - [**Spec parsing and printf mapping**](nodes/spec-parsing-and-printf-mapping.md) — Parses the standard specifier grammar into dynamic specs, tracks argument indexing modes, and maps printf conversions to presentation types. (14 units; `core.h`, `printf.h`)
    - [**Iterator buffer adapters**](nodes/iterator-buffer-adapters.md) — Adapts output iterators and containers to the buffer interface, with optimized copy paths and detection traits for back-insert iterators. (9 units; `core.h`)
    - [**Truncated formatting**](nodes/truncated-formatting.md) — Implements format_to_n and deprecated fixed-buffer overloads using fixed_buffer_traits to count and truncate output. (5 units; `core.h`)
    - [**format\_as type mapping**](nodes/format-as-type-mapping.md) — Detects and applies format_as conversions, mapping user types to natively formattable ones for both parsing and storage. (4 units; `core.h`)
    - [**Packed format specs**](nodes/packed-format-specs.md) — Stores format specifier state compactly in one unsigned word with mask-based accessors for type, alignment, sign, and flags. (3 units; `core.h`)
    - [**Raw pointer buffers**](nodes/raw-pointer-buffers.md) — Provides buffer specializations writing directly to raw pointers, with optional hard limits or effectively unlimited capacity. (3 units; `core.h`)
  - [**fmt: Compile Format**](nodes/fmt-compile-format.md) — Units around compile, format, argument, end in fmt (program-made description). (31 units; `compile.h`)
    - [**Compile-time format compilation**](nodes/compile-time-format-compilation.md) — Compiles format strings into node trees at compile time and provides format/format_to/format_to_n entry points over compiled strings. (20 units; `compile.h`)
    - [**Compiled field nodes**](nodes/compiled-field-nodes.md) — Defines the replacement-field node types and the per-field compiler that produces them from parsed argument ids and specs. (7 units; `compile.h`)
    - [**Compiled text nodes**](nodes/compiled-text-nodes.md) — Implements literal text, code-unit, and concatenation nodes that execute compiled format strings by writing directly to the output iterator. (4 units; `compile.h`)
  - [**Argument storage and checking**](nodes/argument-storage-and-checking.md) — Defines formatting arguments, their type-erased storage, named-argument handling, and compile-time format string validation. (15 units; `core.h`)
- [**Chrono and time formatting**](nodes/chrono-and-time-formatting.md) — Formats chrono durations, time points, and std::tm values, with spec parsing, calendar math, locale-aware writing, and unit suffixes. (51 units; `chrono.h`, `format.h`)
  - [**Chrono formatting internals**](nodes/chrono-formatting-internals.md) — Low-level chrono machinery: duration/tm spec parsing, checked conversions, time-point conversion, and numeric field writing helpers. (29 units; `chrono.h`)
  - [**Chrono formatters and validation**](nodes/chrono-formatters-and-validation.md) — Public chrono formatter classes plus compile-time validation of duration and tm format strings and calendar math helpers. (10 units; `chrono.h`)
  - [**Localized tm writer**](nodes/localized-tm-writer.md) — Coordinates writing a formatted std::tm through chrono spec callbacks, honoring locale settings and transcoding output. (5 units; `chrono.h`)
  - [**Duration unit suffixes**](nodes/duration-unit-suffixes.md) — Maps chrono period types to SI unit suffix strings and copies them to output, including UTF-8 to UTF-16 conversion. (4 units; `chrono.h`, `format.h`)
  - [**Primitive tm emitters**](nodes/primitive-tm-emitters.md) — Emits individual digits, years, English weekday and month names, and the on_* callback output for tm formatting. (3 units; `chrono.h`)
- [**Wide text and styling**](nodes/wide-text-and-styling.md) — Extends formatting to wide and exotic character types and adds ANSI color and emphasis styling to formatted output. (44 units; `color.h`, `xchar.h`)
  - [**Wide character formatting**](nodes/wide-character-formatting.md) — Provides format, print, and format_to entry points for wchar_t and other exotic character types, including locale-aware variants. (31 units; `xchar.h`)
    - [**Wide-character formatting core**](nodes/wide-character-formatting-core.md) — Wide/exotic-character format, print, and vformat entry points plus locale-aware numeric output and compile-time format string wrappers. (16 units; `xchar.h`)
    - [**Wide convenience formatting API**](nodes/wide-convenience-formatting-api.md) — User-facing wide-string format, format_to, print, styled format, and to_string wrappers built on compile-checked wformat_string. (8 units; `xchar.h`)
    - [**Exotic character formatting**](nodes/exotic-character-formatting.md) — Format and format_to entry points for character types beyond char and wchar_t, including locale-aware variants. (7 units; `xchar.h`)
  - [**Text styling and colors**](nodes/text-styling-and-colors.md) — ANSI color/emphasis styling: text_style, RGB/terminal color types, escape sequence generation, and styled print/format functions. (13 units; `color.h`)
- [**Standard library type formatters**](nodes/standard-library-type-formatters.md) — Provides formatters for standard library and wrapper types: bitsets, complex, optional, expected, filesystem paths, atomics, and BitInt. (31 units; `std.h`, `chrono.h`)
  - [**Standard type formatters**](nodes/standard-type-formatters.md) — Formatters for standard library types: bitsets, complex, exceptions, variants, source_location, type_info, and path transcoding. (19 units; `std.h`)
  - [**Wrapper type formatters**](nodes/wrapper-type-formatters.md) — Formatters for error_code, expected, filesystem::path, optional, and unexpected with their specific format spec options. (5 units; `std.h`)
  - [**Miscellaneous small formatters**](nodes/miscellaneous-small-formatters.md) — Formatters for std::tm, atomics, atomic_flag, and std::byte, each delegating to simpler underlying formatters. (4 units; `chrono.h`, `std.h`)
  - [**BitInt support**](nodes/bitint-support.md) — Conditional Clang _BitInt type aliases and formatters casting values of at most 64 bits to standard integer formatters. (3 units; `std.h`)
- [**OS file and C API**](nodes/os-file-and-c-api.md) — File and stream abstractions: RAII file/descriptor wrappers, buffered output streams, pipes, Windows errors, and the C API. (27 units; `os.h`, `os.cc`, `fmt-c.cc`)
- [**Ranges and tuples formatting**](nodes/ranges-and-tuples-formatting.md) — Range detection and formatting: classification traits, map/set/sequence formatters, join views, and tuple formatting. (25 units; `ranges.h`, `xchar.h`)
- [**Printf implementation**](nodes/printf-implementation.md) — Legacy printf-style formatting: argument conversion visitors, spec parsing, the core engine, and print/sprintf entry points. (24 units; `printf.h`, `format-inl.h`)
- [**Dynamic args, enums, ostream**](nodes/dynamic-args-enums-ostream.md) — Dynamic argument stores, enum reflection formatters, the C API value model, and ostream-based formatting integration. (21 units; `args.h`, `enum.h`, `fmt-c.h`)

## Key flows

- **Dragonbox float conversion**: A double is converted to shortest decimal digits using Dragonbox with cached powers, 128-bit arithmetic, and assertion checks. — `FMT_BEGIN_EXPORT.size_padding.format_float` → `get_cached_power` → `format-inl.h-cache-accessor-double` → `format.h-uint128` → `assert_fail`
- **Bigint fallback formatting**: When the fast path is insufficient, the dragon fallback computes exact digits with the bigint algorithm and shared limits helpers. — `FMT_BEGIN_EXPORT.size_padding.format_dragon` → `format.h-bigint` → `format.h-limits-helpers`
- **Format spec parsing**: Replacement fields are parsed into dynamic specs using type predicates, alignment/name detection, and error reporting. — `core.h-parse-format-specs` → `core.h-parse-align-is-name-start` → (model-inferred) → `report_error`
- **Chrono tm writing**: The tm writer's spec handlers dispatch to low-level writers and name tables to emit localized time fields. — `chrono.h-tm-writer-spec-handlers` → `chrono.h-low-level-writers`
- **Duration formatting**: Duration formatter spec handlers drive the duration formatter core to render chrono durations. — `chrono.h-duration-formatter-spec-handlers` → `chrono.h-duration-formatter-core`
- **Dragonbox decimal computation**: The to_decimal routine uses float layout helpers and log approximations to produce decimal output with assertion safety. — `to_decimal` → `format.h-float-layout-helpers`
- **Printf presentation mapping**: Printf conversion characters are mapped onto fmt presentation types using core type predicates. — `parse_printf_presentation_type` → `core.h-type-predicates-and-bitset-helpers`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
