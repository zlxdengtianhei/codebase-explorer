# fmt: code map

The repository is the fmt formatting library, with core internals providing low-level primitives, platform and Dragonbox support, and big-integer float formatting. A compiled formatting engine supplies argument and spec parsing, compile-time checking, buffers, and compiled format strings, while character/style, chrono, standard-library, range/tuple, printf, and dynamic-argument/C-API modules extend formatting to specialized types and interfaces. OS and stream integration connects formatting to C APIs, files, and std::ostream.

## Modules

- [**Core Formatting Internals**](nodes/core-formatting-internals.md) — Houses low-level formatting primitives, platform and Dragonbox support, and arbitrary-precision integer floating-point formatting. (125 units; `format.h`, `format-inl.h`, `core.h`)
  - [**Low-Level Formatting Primitives**](nodes/low-level-formatting-primitives.md) — Provides shared low-level formatting utilities, spec parsing, numeric and string writers, floating-point cores, and UTF conversion used by higher formatting layers. (87 units; `format.h`, `format-inl.h`, `core.h`)
    - [**Format Core Utilities**](nodes/format-core-utilities.md) — Provides low-level formatting utilities for allocation checks, byte order, log approximations, Dragonbox conversion, format_as dispatch, and named arguments. (26 units; `format.h`, `format-inl.h`)
    - [**Format Spec Parsing and Writing**](nodes/format-spec-parsing-and-writing.md) — Parses format specifications and writes builtin values with padding, signs, prefixes, escaping, and floating-point presentation. (24 units; `format.h`)
    - [**Integer and Pointer Formatting**](nodes/integer-and-pointer-formatting.md) — Formats integers, characters, pointers, exponents, and grouped digits using digit tables, locale grouping, and stack buffers. (13 units; `format.h`)
    - [**Buffer and Core Integer Writer**](nodes/buffer-and-core-integer-writer.md) — Implements dynamic memory buffers, 128-bit arithmetic, and core unsigned integer digit writing for formatting. (9 units; `format.h`, `core.h`)
    - [**Floating-Point Formatting Core**](nodes/floating-point-formatting-core.md) — Extracts floating-point components and writes fixed, exponential, and hexadecimal floating-point representations. (7 units; `format.h`)
    - [**UTF Encoding and Decoding**](nodes/utf-encoding-and-decoding.md) — Converts and decodes UTF-8, UTF-16, and UTF-32 views, appends UTF-8 code points, and provides branchless decoding. (5 units; `format.h`)
    - [**String and Locale Formatting**](nodes/string-and-locale-formatting.md) — Formats locale strings into buffers and constructs fixed compile-time strings from character arrays. (3 units; `format.h`)
  - [**Platform and Dragonbox Support**](nodes/platform-and-dragonbox-support.md) — Wraps platform FILE and locale internals and supplies Dragonbox caches, decimal helpers, and assertion support for formatting internals. (33 units; `format-inl.h`)
    - [**Platform File and Locale Internals**](nodes/platform-file-and-locale-internals.md) — Wraps FILE internals, platform locking, locale facets, system-error formatting, UTF conversion, and allocation helpers. (26 units; `format-inl.h`)
    - [**Dragonbox Cache and Assertions**](nodes/dragonbox-cache-and-assertions.md) — Provides Dragonbox power caches, decimal division helpers, trailing-zero removal, interval checks, and assertion abort reporting. (7 units; `format-inl.h`)
  - [**Big Integer Float Formatting**](nodes/big-integer-float-formatting.md) — Implements arbitrary-precision integer storage and Steele-White fixed-precision floating-point formatting with rounding thresholds. (5 units; `format.h`)
- [**Compiled Formatting Engine**](nodes/compiled-formatting-engine.md) — Compiles format strings and supplies the argument, spec, buffer, and output machinery for compiled formatting. (92 units; `core.h`, `compile.h`, `format-inl.h`)
  - [**Argument and Spec Pipeline**](nodes/argument-and-spec-pipeline.md) — Maps arguments, parses format specs, checks compile-time formats, and adapts output buffers for the compiled formatting engine. (65 units; `core.h`, `format-inl.h`)
    - [**Format Argument Type Mapping**](nodes/format-argument-type-mapping.md) — Defines string views, type-erased arguments, type mapping traits, argument encoding, and core format-to and print entry points. (28 units; `core.h`)
    - [**Format Spec Parser**](nodes/format-spec-parser.md) — Parses replacement fields, argument ids, widths, precisions, alignment, and standard format specs into packed specs. (14 units; `core.h`, `format-inl.h`)
    - [**Output Buffer Adapters**](nodes/output-buffer-adapters.md) — Maps output iterators and containers to buffers and implements bounded, counting, and fixed-buffer formatting paths. (8 units; `core.h`)
    - [**Compile-Time Format Checking**](nodes/compile-time-format-checking.md) — Validates format strings against argument packs during constant evaluation and tracks argument indexing and character specs. (7 units; `core.h`)
    - [**Type-Erased Argument Context**](nodes/type-erased-argument-context.md) — Holds type-erased formatting arguments, argument views, and char formatting contexts for the formatting pipeline. (5 units; `core.h`)
    - [**Argument Store Construction**](nodes/argument-store-construction.md) — Builds format argument stores and named-argument stores from references and metadata. (3 units; `core.h`)
  - [**Compiled Format String Engine**](nodes/compiled-format-string-engine.md) — Compiles format strings into fragments and formats, measures, or writes compiled output with fixed and named fields. (27 units; `compile.h`)
- [**Character and Style Formatting**](nodes/character-and-style-formatting.md) — Groups wide and exotic character formatting paths with ANSI color and styled-text formatting support. (54 units; `color.h`, `xchar.h`)
  - [**Wide and Exotic Character Paths**](nodes/wide-and-exotic-character-paths.md) — Provides wide-character and non-char formatting helpers, forwarding, and exotic-character format and print paths. (34 units; `xchar.h`)
    - [**Wide Character Format Helpers**](nodes/wide-character-format-helpers.md) — Provides wchar_t and exotic-character format-string wrappers, argument stores, named arguments, and bounded formatting helpers. (14 units; `xchar.h`)
    - [**Wide Format and Print Forwarding**](nodes/wide-format-and-print-forwarding.md) — Forwards wchar_t format, format_to, print, and vprint operations to buffered formatting and wide output streams. (10 units; `xchar.h`)
    - [**Exotic Character Formatting**](nodes/exotic-character-formatting.md) — Implements format, vformat, and format_to paths for character types other than char and wchar_t. (10 units; `xchar.h`)
  - [**ANSI Color Style Formatting**](nodes/ansi-color-style-formatting.md) — Builds ANSI color escapes and formats, prints, and wraps styled text with foreground, background, and emphasis. (20 units; `color.h`)
- [**OS and Stream Integration**](nodes/os-and-stream-integration.md) — Connects formatting to C APIs, OS file abstractions, and std::ostream output paths. (49 units; `os.cc`, `os.h`, `ostream.h`)
  - [**C API and OS File Layer**](nodes/c-api-and-os-file-layer.md) — Implements C formatting APIs, OS file operations, ownership wrappers, and low-level OS type wrappers. (40 units; `os.cc`, `os.h`, `fmt-c.cc`)
    - [**C API and OS File Operations**](nodes/c-api-and-os-file-operations.md) — Implements C formatting API, file read/write/duplication, pipes, Windows error categories, and ostream file handling. (22 units; `os.cc`, `fmt-c.cc`)
    - [**File Ownership Wrappers**](nodes/file-ownership-wrappers.md) — Owns and manages FILE handles and file descriptors, opening, closing, and associating streams with descriptors. (10 units; `os.cc`, `os.h`)
    - [**OS Type Wrappers**](nodes/os-type-wrappers.md) — Defines non-owning C-string views, file descriptor wrappers, buffered output streams, pipe holders, and output parameters. (8 units; `os.h`)
  - [**Ostream Formatting Bridge**](nodes/ostream-formatting-bridge.md) — Bridges fmt formatting to std::ostream, including streamed value views, buffer writes, and FILE detection. (9 units; `ostream.h`)
- [**Chrono Formatting Support**](nodes/chrono-formatting-support.md) — Formats and parses chrono durations, time points, calendar fallback types, and chrono format handlers. (47 units; `chrono.h`)
  - [**Chrono Duration and Time Formatting**](nodes/chrono-duration-and-time-formatting.md) — Formats and parses chrono durations and time points, converting clocks, units, fractional seconds, and UTC/local times. (27 units; `chrono.h`)
  - [**Chrono Calendar Fallback Types**](nodes/chrono-calendar-fallback-types.md) — Provides fallback day, month, weekday, year, and date types and their formatters for chrono calendar formatting. (10 units; `chrono.h`)
  - [**Chrono Format Handlers**](nodes/chrono-format-handlers.md) — Validates chrono specs and renders duration and std::tm fields, including localized time strings and subseconds. (10 units; `chrono.h`)
- [**Standard Library Formatters**](nodes/standard-library-formatters.md) — Provides formatters and traits for standard-library, chrono/value, atomic, and scalar-wrapper types. (34 units; `std.h`, `chrono.h`)
  - [**Standard Type Formatters and Traits**](nodes/standard-type-formatters-and-traits.md) — Provides formatters and compile-time traits for standard-library types such as exceptions, paths, variants, smart pointers, and demangled names. (17 units; `std.h`)
  - [**Chrono and Standard Value Formatters**](nodes/chrono-and-standard-value-formatters.md) — Formats std::tm and standard value types including complex, error_code, expected, optional, monostate, source_location, type_info, and unexpected. (9 units; `std.h`, `chrono.h`)
  - [**Atomic and Scalar Wrapper Formatters**](nodes/atomic-and-scalar-wrapper-formatters.md) — Formats atomic, bit-reference, bitset, byte, reference_wrapper, and small _BitInt values by delegating to underlying formatters. (8 units; `std.h`)
- [**Range and Tuple Formatting**](nodes/range-and-tuple-formatting.md) — Supports range and tuple detection, access traits, formatter selection, and range formatter specializations. (31 units; `ranges.h`)
  - [**Range and Tuple Formatting Infrastructure**](nodes/range-and-tuple-formatting-infrastructure.md) — Provides range/tuple detection, formatter selection, join views, and tuple formatting helpers used by fmt range formatting. (16 units; `ranges.h`)
  - [**Range Access and Detection Traits**](nodes/range-access-and-detection-traits.md) — Detects and accesses ranges through member or ADL begin/end, C arrays, const references, and value-like expressions. (9 units; `ranges.h`)
  - [**Range Formatter Specializations**](nodes/range-formatter-specializations.md) — Selects and provides range formatter specializations for disabled, map-like, string, debug-string, and sequence ranges. (6 units; `ranges.h`)
- [**Printf-Style Formatting Engine**](nodes/printf-style-formatting-engine.md) — Implements printf-style parsing, argument conversion, context storage, and output through vfprintf, vsprintf, or memory buffers. (23 units; `printf.h`)
- [**Dynamic Arguments, Enums, and C API**](nodes/dynamic-arguments-enums-and-c-api.md) — Provides dynamic argument storage, enum formatter support, and C-facing argument types and builders. (17 units; `args.h`, `fmt-c.h`, `enum.h`)

## Key flows

- **Chrono tm formatting**: Chrono tm format handlers delegate to core/private helpers and assertion reporting. — `chrono.h-tm-writer-format-handlers` → `chrono.h-tm-writer-core-and-private-helpers` → `assert_fail`
- **Localized chrono tm output**: Chrono tm handlers use core helpers, locale writer policy, and locale time formatting helpers. — `chrono.h-tm-writer-format-handlers` → `chrono.h-tm-writer-core-and-private-helpers` → `chrono.h-locale-writer-policy` → `chrono.h-locale-time-formatting-helpers`
- **Dragonbox decimal conversion**: Dragonbox to_decimal uses log approximations and assertion reporting. — `to_decimal` → `format.h-log-approximations` → `assert_fail`
- **Dragon float formatting**: format_dragon uses big-integer support and assertion reporting. — `FMT_BEGIN_EXPORT.size_padding.format_dragon` → `format.h-big-integer` → `assert_fail`
- **Float formatting with cached powers**: format_float obtains Dragonbox cached powers through the cache accessor and assertion reporting. — `FMT_BEGIN_EXPORT.size_padding.format_float` → `get_cached_power` → `format-inl.h-double-cache-accessor` → `assert_fail`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)
