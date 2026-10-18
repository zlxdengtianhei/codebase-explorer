# Portable Platform & Time Helpers

**Capability.** Owns small platform-dependent utilities shared across the library and tool: Windows version verification, terminal width reporting, and a portable localtime replacement.

Callers use these helpers instead of platform APIs directly, keeping OS differences localized. hms_for_sec in the debug callback is a typical consumer of toolx_localtime.

**Depended on by.**

- [Tool Help, Version & Debug Output](r14-tool-help-debug.md) · graph-confirmed · 1 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (4)

<a id="u-8e8e479dbb90"></a>
### `curlx_verify_windows_init`

`void curlx_verify_windows_init(void)` · [lib/curlx/version_win32.c:L51-L62][f1]

Non-UWP Windows initialization resolving RtlVerifyVersionInfo from ntdll for later use by version checks.

uses: [curlx_verify_windows_version](r14-platform-helpers.md#u-dd2717366ced)

**Uncertainties.**

- Behavior when GetProcAddress fails (stores NULL) is handled by the caller's fallback, not here

<a id="u-dd2717366ced"></a>
### `curlx_verify_windows_version`

`bool curlx_verify_windows_version(const unsigned int majorVersion, const unsigned int…` · [lib/curlx/version_win32.c:L84-L236][f1]

Checks the running Windows version against a major/minor/build/platform target under a comparison condition, returning TRUE on match.

**Notes.**

- condition: UWP builds cannot query the real version, so the compile-time _WIN32_WINNT target is compared against MAKEWORD(minor, major) per the condition; PLATFORM_WINDOWS always fails.
- condition: Each condition maps to VER_* comparison masks; strict greater-than/less-than use VER_LESS/VER_GREATER for service packs while equality checks use VER_GREATER_EQUAL for service packs. An unrecognized condition returns FALSE.
- condition: When RtlVerifyVersionInfo is unavailable, VerifyVersionInfoW is used; the Rtl variant is preferred so manifested apps still see the real version.
- condition: Build numbers are compared in a second pass only when the first match held, buildVersion is nonzero, and the condition is VERSION_EQUAL, or a *_EQUAL_OR_* condition that also matches at equal major.minor; otherwise hierarchical major/minor results stand.

uses: [curlx_verify_windows_init](r14-platform-helpers.md#u-8e8e479dbb90)

**Uncertainties.**

- Whether the UWP branch can ever report PLATFORM_WINDOWS as matched: code comment says apps always run on PLATFORM_WINNT, and matched is cleared only when platform == PLATFORM_WINDOWS

<a id="u-3e970cc9541a"></a>
### `terminal.h module code (L1–L30)`

`module_region` · [src/terminal.h:L1-L30][f2]

Header declaring get_terminal_columns(), which reports the terminal width in columns for the curl tool; implementation lives elsewhere, so this unit covers only the public contract and its tool_setup.h dependency.

imports: [tool_setup.h module code (L1–L115)](r10-tool-support.md#u-d7a2b32243f5)

**Uncertainties.**

- The body of get_terminal_columns is not in this file; its behavior cannot be documented from this source.

<a id="u-aa9ac3fcca23"></a>
### `toolx_localtime`

`CURLcode toolx_localtime(time_t intime, struct tm *store)` · [src/toolx/tool_time.c:L40-L61][f3]

Portable localtime() replacement that fills a caller-supplied struct tm from a time_t.

On Windows it calls localtime_s(store, &intime); a nonzero result yields CURLE_BAD_FUNCTION_ARGUMENT. With HAVE_LOCALTIME_R, it calls localtime_r(&intime, store) and returns CURLE_BAD_FUNCTION_ARGUMENT if the returned pointer is null. Otherwise it uses non-thread-safe localtime(&intime) and copies the pointed struct into *store on success; a null return yields CURLE_BAD_FUNCTION_ARGUMENT. It returns CURLE_OK only when the conversion filled *store. MinGW with __MINGW64_VERSION_MAJOR <= 3 remaps localtime_s to _localtime32_s or _localtime64_s depending on _USE_32BIT_TIME_T.

**Notes.**

- side_effect: On non-Windows, non-localtime_r builds the static buffer behind localtime() is used, so callers must not rely on thread safety in that configuration.
- contract: On success *store holds the local-time breakdown; on failure *store's contents are unspecified, though localtime_r/localtime paths already write into it.

uses: [tool_time.h module code (L1–L30)][f4]

**Uncertainties.**

- Which platform branch compiles depends on build macros (_WIN32, HAVE_LOCALTIME_R) not resolvable from this file alone.
- Failure semantics of *store contents after a failed localtime_s/localtime_r call depend on those platform functions, not shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/version_win32.c
[f2]: ../../../../../../eval/curl-2c04412/src/terminal.h
[f3]: ../../../../../../eval/curl-2c04412/src/toolx/tool_time.c
[f4]: ../../../../../../eval/curl-2c04412/src/toolx/tool_time.h
