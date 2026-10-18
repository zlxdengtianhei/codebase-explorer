# Windows portability headers

**Capability.** Windows-only header abstractions: a tchar layer minimizing #ifdef UNICODE, and OS version verification helpers.

Include these in Windows-specific code instead of raw tchar.h/version checks.

Parent: [Portable utilities](r12-portable-utils.md)

## Units (2)

<a id="u-f1dd56553f6b"></a>
### `multibyte-h-tchar-abstraction`

`union` · [lib/curlx/multibyte.h:L51-L56][f1]

Windows-only header providing a tchar abstraction to minimize #ifdef UNICODE in callers.

In Unicode builds, curlx_convert_UTF8_to_tchar/curlx_convert_tchar_to_UTF8 map to the wide conversion functions and xcharp_u is a union of unsigned short pointers. In non-Unicode builds, both macros are curlx_strdup, leaving the string encoding unchanged (assumed UTF-8 but not enforced), and xcharp_u is a union of char pointers. Outside _WIN32 the header contributes nothing.

**Uncertainties.**

- In non-Unicode builds the source encoding is assumed UTF-8 without verification, per the header comment

<a id="u-238bcdceb660"></a>
### `version-win32-h-version-check`

`enum` · [lib/curlx/version_win32.h:L31-L37][f2]

Windows-only header for OS version verification.

Defines VersionCondition (less-than, less-or-equal, equal, greater-or-equal, greater-than comparisons) and PlatformIdentifier (DONT_CARE, WINDOWS, WINNT) enums, and declares curlx_verify_windows_version taking major/minor/build numbers plus these enums. curlx_verify_windows_init is a no-op under CURL_WINDOWS_UWP, otherwise a real function declared for one-time initialization before version checks. Contributes nothing outside _WIN32.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curlx/multibyte.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/version_win32.h
