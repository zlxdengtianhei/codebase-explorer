# Chrono Spec Parsing

**Capability.** Parses strftime-like format strings and validates every conversion spec through CRTP handler/checker classes that reject specs unsupported by the target type.

tm and duration formatters both call parse_chrono_format with their own checker; the null handler supplies throwing defaults so checkers only override accepted specs.

**Depended on by.**

- [Duration Formatting](chrono-duration.md) · model-inferred · 0 edge(s)
- [std::tm Formatting](chrono-tm.md) · model-inferred · 0 edge(s)

Parent: [Chrono Formatting](chrono-h.md)

## Units (5)

<a id="u-6fd583aecf8f"></a>
### `chrono-null-chrono-spec-handler`

`template <typename Derived> struct null_chrono_spec_handler` · [include/fmt/chrono.h:L815-L816][f1]

CRTP base giving chrono-format handlers a default reaction for every conversion spec: each on_* forwards to unsupported(), which by default calls the derived class's unsupported() — typically a throw — so derived handlers only override the specs they accept.

The on_* list covers years, weekdays, months, week/day-of-year counters, day of month, time fields, locale datetime forms, duration value/unit, UTC offset and timezone name, mirroring parse_chrono_format's dispatch table.

<a id="u-7121bda37a95"></a>
### `tm_format_checker`

`class tm_format_checker : public null_chrono_spec_handler<tm_format_checker>` · [include/fmt/chrono.h:L864-L869][f1]

Validates at compile/format time that a chrono format string contains only specs meaningful for a std::tm.

It inherits the throwing defaults of null_chrono_spec_handler but overrides every tm-applicable on_* with an empty body, so such specs pass; the inherited unsupported() still throws for non-tm specs like %Q/%q. unsupported() throws format_error("no format"). Constructor state has_timezone_ gates timezone specs: on_utc_offset and on_tz_name throw format_error("no timezone") when the source std::tm lacks a timezone member (no tm_gmtoff), otherwise they pass.

inherits: [chrono-null-chrono-spec-handler](chrono-parse.md#u-6fd583aecf8f)

<a id="u-0d3f26ea6de0"></a>
### `chrono_format_checker`

`struct chrono_format_checker : null_chrono_spec_handler<chrono_format_checker>` · [include/fmt/chrono.h:L1515-L1518][f1]

Compile-time validator for duration format strings: inherits throwing defaults from null_chrono_spec_handler, throws format_error("no date") for any unsupported (date-related) spec, and accepts only text and time/duration specs via empty overrides.

on_duration_value additionally rejects precision: when has_precision_integral was set during parsing (precision given for an integral rep) it throws format_error("precision not allowed for this argument type").

inherits: [chrono-null-chrono-spec-handler](chrono-parse.md#u-6fd583aecf8f)

<a id="u-953b80d7c4a3"></a>
### `parse_chrono_format`

`template <typename Char, typename Handler> FMT_CONSTEXPR auto parse_chrono_format(con…` · [include/fmt/chrono.h:L670-L813][f1]

Parses a strftime-like format string, invoking handler callbacks for each spec.

It returns immediately for an empty range or a leading '}'. A leading character other than '%' throws format_error("invalid format"). The loop copies literal text (calling on_text at spec boundaries and once at the end), and after each '%' accepts '_' (space pad) or '-' (no pad) flags before the conversion character; a trailing '%' or flag throws. Each recognized conversion char maps to one handler call, with '%', 'n', 't' emitted as literal text. 'E' and 'O' introduce alternative-representation forms with their own sub-switches, and any unrecognized conversion, alternative form, or empty E/O sequence throws format_error("invalid format"). The handler determines validity beyond syntax (e.g. via unsupported()), and the returned pointer marks the end of consumed input.

uses: [chrono-null-chrono-spec-handler](chrono-parse.md#u-6fd583aecf8f), [write_padding](chrono-parse.md#u-a26a79a60def)

**Uncertainties.**

- Handlers such as tm_format_checker throw their own errors (e.g. "no format"), so the exception thrown for a syntactically valid but unsupported spec depends on the handler type.

<a id="u-a26a79a60def"></a>
### `write_padding`

`template <typename OutputIt> auto write_padding(OutputIt out, pad_type pad, int width…` · [include/fmt/chrono.h:L657-L661][f1]

Emits padding before a single-digit number.

The width-aware overload returns out unchanged for pad_type::none and otherwise fills width characters with spaces or zeros depending on the pad type. The no-width overload writes one pad character only when padding is not none.

uses: [function::detail.tm_writer::40480::s0][f1]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/fmtlib/fmt/blob/b4ffa39b9994c961418406f47358791d89a5aa48/include/fmt/chrono.h