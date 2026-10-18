# Tool Messaging and Parameter Helpers

**Capability.** Prefix-wrapped, word-wrapped terminal output with error/warning/note/help severity, plus small option helpers that record or advise about HTTP request method settings and translate ParameterError values to text.

All tool components report through warnf/notef/errorf here, so changes to message formatting are localized in voutf. The helpers in tool_helpers.c never alter transfer behavior beyond recording a requested method.

**Depended on by.**

- [Tool Output Directories and SSL Sessions](r5-tool-output.md) · graph-confirmed · 8 edge(s)
- [flag dispatch and simple assignment](r11-arg-dispatch.md) · graph-only · 28 edge(s)

Parent: [curl Command-Line Tool](r5-command-line-tool.md)

## Units (9)

<a id="u-c59223ee2807"></a>
### `tool_msgs-c-module-regions`

`module_region` · [src/tool_msgs.c:L1-L36][f1]

Non-behavioral regions of tool_msgs.c: license header, includes, and the WARN_PREFIX/NOTE_PREFIX/ERROR_PREFIX macro definitions.

<a id="u-591e703bf785"></a>
### `errorf`

`void errorf(const char *fmt, ...)` · [src/tool_msgs.c:L129-L137][f1]

Prints a 'curl: ' error via voutf unless silenced, unless showerror overrides silence.

**Notes.**

- condition: Suppresses output when global->silent is set, except when global->showerror is also set; emits when global is NULL.

calls: [voutf](r5-tool-messaging.md#u-f442fbc177d9)

<a id="u-0be25ff8537d"></a>
### `helpf`

`void helpf(const char *fmt, ...)` · [src/tool_msgs.c:L107-L123][f1]

Prints a 'curl: ' prefixed argument-error message to tool_stderr, then always a 'try curl --help' hint.

**Notes.**

- condition: If fmt is NULL the formatted message is skipped and only the usage hint is printed; USE_MANUAL adds 'or curl --manual' to the hint.
- contract: DEBUGASSERT rejects newlines in fmt; unlike voutf users, output is not terminal-width wrapped.

uses: [lib-mprintf-c-buffer-stdio-family](r9-mprintf-formatter-families.md#u-780e9db0224b)

<a id="u-c1aad52b5dde"></a>
### `notef`

`void notef(const char *fmt, ...)` · [src/tool_msgs.c:L79-L87][f1]

Prints a 'Note: ' message via voutf only when tracing is enabled and --silent is not set.

calls: [voutf](r5-tool-messaging.md#u-f442fbc177d9)

<a id="u-f442fbc177d9"></a>
### `voutf`

`static void voutf(const char *prefix, const char *fmt, va_list ap)` · [src/tool_msgs.c:L37-L73][f1]

Formats a message and writes it prefix-wrapped and word-wrapped to the terminal width on tool_stderr.

**Notes.**

- contract: DEBUGASSERT rejects format strings containing newlines; messages are expected single-line.
- condition: Wraps at terminal width minus prefix width; when cutting, backs up to the last blank; if no blank is found it hard-cuts at width - 1. Content beyond a 1024-byte format buffer is truncated by curl_mvsnprintf.
- side_effect: Writes prefix, wrapped chunks, and newlines to tool_stderr; if the terminal is narrower than the prefix, width becomes SIZE_MAX (no wrapping).

uses: [notef](r5-tool-messaging.md#u-c1aad52b5dde), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7), [errorf](r5-tool-messaging.md#u-591e703bf785)

**Uncertainties.**

- Exact interaction between the 1024-byte buffer and the width computation for overlong messages is not fully derivable here

<a id="u-b1c19a3e5da7"></a>
### `warnf`

`void warnf(const char *fmt, ...)` · [src/tool_msgs.c:L93-L101][f1]

Prints a 'Warning: ' message via voutf unless global exists and --silent is set (warns by default when global is NULL).

calls: [voutf](r5-tool-messaging.md#u-f442fbc177d9)

<a id="u-f529e9f82097"></a>
### `SetHTTPrequest`

`int SetHTTPrequest(HttpReq req, HttpReq *store)` · [src/tool_helpers.c:L77-L99][f2]

Records a requested HTTP request method unless one is already set.

If *store is TOOL_HTTPREQ_UNSPEC or already equals req, it stores req and returns 0. Otherwise it warns naming both conflicting methods from a static name table mirroring the HttpReq enum and returns 1. No other state changes.

**Notes.**

- contract: The reqname table indexes 0..5 and assumes req/*store are within that range; out-of-range values would read past the table.

calls: [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

<a id="u-3b5d3cb6ab00"></a>
### `customrequest_helper`

`void customrequest_helper(HttpReq req, const char *method)` · [src/tool_helpers.c:L101-L123][f2]

Advises about redundant or risky -X/--request usage; never changes state.

With a NULL method it does nothing. If the method matches the default method implied by req (dflt table), it notes that -X is unnecessary. Otherwise, if the method equals 'head' case-insensitively, it warns that -X HEAD may not behave as intended and suggests -I/--head. All other methods pass silently.

**Notes.**

- contract: Indexing dflt[req] requires req to be within 0..5; that bound is assumed, not checked.

calls: [notef](r5-tool-messaging.md#u-c1aad52b5dde), [warnf](r5-tool-messaging.md#u-b1c19a3e5da7)

<a id="u-dcd8be2d7fbc"></a>
### `param2text`

`const char *param2text(ParameterError error)` · [src/tool_helpers.c:L35-L75][f2]

Maps a ParameterError enum to a fixed human-readable phrase for error messages, with a switch over the known values (extra parameter, unknown option, bad usage, numeric errors, libcurl limitations, memory, etc.) and a default of 'unknown error'.

Pure, no side effects or allocation.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_msgs.c
[f2]: ../../../../../../eval/curl-2c04412/src/tool_helpers.c
