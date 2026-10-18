# Build and Platform Configuration

**Capability.** Handcrafted preprocessor configuration per platform plus a test-support fake resolver interface.

Use when porting or building on the covered platforms; these predefine feature macros instead of a generated config. fake_addrinfo.h is a c-ares test stub kept here for lack of a better home.

Parent: [curl Codebase](r6-curl-codebase.md)

## Units (3)

<a id="u-014b4d242fb9"></a>
### `config-win32-h-build-macros`

`module_region` · [lib/config-win32.h:L1-L123][f1]

Handcrafted configuration header that predefines curl build settings for Visual Studio IDE project builds instead of a generated config.

It hard-fails via #error when _MSC_VER is undefined or greater than 1800, restricting use to MSVC 2010-2013. It then defines header/function availability macros, recv/send argument and return types, and type sizes with three compile-time branches: _WIN64 selects SIZEOF_SIZE_T 8 and ssize_t __int64, otherwise 4 and int; _USE_32BIT_TIME_T selects SIZEOF_TIME_T 4, otherwise 8; and CURL_OS defaults to 'i386-pc-win32', 'x86_64-pc-win32', or 'unknown-pc-win32' based on _M_IX86/_M_X64, unless already defined. It defaults USE_RESOLV_THREADED to 1 only when neither USE_RESOLV_THREADED nor USE_SYNC_DNS is already defined, so a caller can override the DNS threading choice.

**Notes.**

- condition: Building with any MSVC outside 2010-2013 (or a non-MSVC compiler) triggers #error because _MSC_VER is absent or above 1800.
- contract: All HAVE_*/SIZEOF_*/USE_* values are fixed here; only _WIN64, _MSC_VER, _USE_32BIT_TIME_T, CURL_OS, USE_RESOLV_THREADED, and USE_SYNC_DNS alter the resulting configuration.

**Uncertainties.**

- Whether MSVC 2010 (not just 2013) truly works cannot be verified from this header; only the _MSC_VER <= 1800 guard is visible.
- ssize_t is mapped to __int64/int, but no check ensures the chosen type matches SIZEOF_SIZE_T on all toolchain variants.

<a id="u-1684dca038fc"></a>
### `config-mac.h module code (L1–L83)`

`module_region` · [lib/config-mac.h:L1-L83][f2]

Handcrafted preprocessor configuration for Mac OS 9 builds of curl.

The file is guarded by HEADER_CURL_CONFIG_MAC_H, defines CURL_OS as "mac", includes <ConditionalMacros.h>, and then unconditionally sets feature-detection macros (USE_MANUAL, HAVE_* headers and functions including socket, sigaction, and ioctl FIONBIO), disables LDAP via CURL_DISABLE_LDAP, fixes type sizes (int/long/size_t 4 bytes, curl_off_t 8), and supplies recv/send calling-convention macros with POSIX-like signatures (int socket, void* buffer, size_t length, int flags, ssize_t return). All definitions are #define constants with no logic; their effect is entirely conditional-compilation behavior in the including sources.

**Notes.**

- side_effect: Defines HAVE_RECV/RECV_TYPE_* and HAVE_SEND/SEND_TYPE_* macros that shape recv/send prototypes wherever curl_config.h-equivalent configuration is consumed.
- contract: The include of <ConditionalMacros.h> is external and its contents are not visible here.

imports: [ConditionalMacros.h](../../catalog.json)

**Uncertainties.**

- Whether this file is used by current build paths or is legacy Mac OS 9-only cannot be determined from the file itself.
- The role of <ConditionalMacros.h> in guarding or altering these definitions is not visible in the supplied source.

<a id="u-8a524deb5eb3"></a>
### `fake_addrinfo.h module code (L1–L53)`

`module_region` · [lib/fake_addrinfo.h:L1-L53][f3]

Header declaring the fake c-ares-backed getaddrinfo interface.

It defines USE_FAKE_GETADDRINFO only when CURL_MEMDEBUG, HAVE_GETADDRINFO, USE_ARES, and c-ares >= 1.26.0 all hold; under that macro it declares r_freeaddrinfo and r_getaddrinfo and pulls in netdb/arpa-inet headers. No behavior of its own.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/config-win32.h
[f2]: ../../../../../../eval/curl-2c04412/lib/config-mac.h
[f3]: ../../../../../../eval/curl-2c04412/lib/fake_addrinfo.h
