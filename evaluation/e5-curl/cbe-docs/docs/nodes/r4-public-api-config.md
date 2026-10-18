# Public API headers and build config

**Capability.** The externally visible surface and build-time configuration: generated version macros for the libcurl release, the public curl_easy_header API types and codes, and the handcrafted OS/400 platform configuration header.

Consult curlver.h for version comparison macros, header.h before using curl_easy_header (struct curl_header and CURLHcode), and config-os400.h when building for OS/400.

Parent: [curl source tree](r4-curl.md)

## Units (5)

<a id="u-45c8b7ea3c9c"></a>
### `curlver-h-version-macros`

`group` · [include/curl/curlver.h:L1-L77][f1]

Defines libcurl release-version constants and comparison macros in a script-generated header.

It exports LIBCURL_COPYRIGHT, LIBCURL_VERSION ("8.23.1-DEV"), MAJOR/MINOR/PATCH, LIBCURL_VERSION_NUM as a full 0xXXYYZZ hex literal (written inline, not via the macro, because configure greps the raw number), and LIBCURL_TIMESTAMP ("[unreleased]"). CURL_VERSION_BITS(x,y,z) packs three 8-bit values as x<<16|y<<8|z; CURL_AT_LEAST_VERSION(x,y,z) expands to LIBCURL_VERSION_NUM >= CURL_VERSION_BITS(x,y,z), giving compile-time minimum-version checks. All values are compile-time constants with no runtime behavior.

**Notes.**

- side_effect: None; the header only defines macros and include-guard state.

<a id="u-0324322af322"></a>
### `header-h-header-api`

`struct curl_header` · [include/curl/header.h:L31-L38][f2]

Declares the public header-extraction API: the curl_header struct and the two functions that fill it.

struct curl_header carries name and value (case of name may differ from the request), amount (count of headers sharing that name), index (instance number, 0-based), origin bit flags, and a private anchor. Origin bits distinguish CURLH_HEADER, CURLH_TRAILER, CURLH_CONNECT, CURLH_1XX, and CURLH_PSEUDO. curl_easy_header(curl, name, nameindex, origin, request, hout) returns a CURLHcode; curl_easy_nextheader(curl, origin, request, prev) iterates, taking the previous curl_header as a cursor. Declared CURLHcode values cover ok, bad index, missing header/name, no request, out of memory, bad argument, and API-not-built-in. Only declarations appear here; implementations live outside this header.

uses: [curl_header](r4-public-api-config.md#u-cc08f834a42a), [include/curl/header.h:<enum>](r4-public-api-config.md#u-03e4d23468d1), [header-h-header-api](r4-public-api-config.md#u-0324322af322)

**Uncertainties.**

- Exact semantics of the request parameter and origin filtering are defined by the libcurl implementation, not visible here.

<a id="u-03e4d23468d1"></a>
### `include/curl/header.h:<enum>`

`enum` · [include/curl/header.h:L47-L56][f2]

CURLHcode enum listing return codes for the header API: success plus bad index, missing header, no headers, no such request, out of memory, bad argument, and disabled build.

<a id="u-cc08f834a42a"></a>
### `curl_header`

`struct curl_header` · [include/curl/header.h:L31-L38][f2]

Struct type describing one extracted HTTP header instance for the curl_easy_header API: name, value, amount of same-named headers, 0-based instance index, origin bit flags, and a private libcurl anchor handle.

<a id="u-20a3ae389dc7"></a>
### `config-os400.h module code (L1–L292)`

`module_region` · [lib/config-os400.h:L1-L292][f3]

Handcrafted OS/400 build-configuration header: it defines feature-detection macros, type-size constants, and platform-specific switches instead of executable code.

All content is preprocessor macros guarded by HEADER_CURL_CONFIG_OS400_H. It sets CURL_CA_BUNDLE to the system keyring path, CURL_OS to "OS/400", and declares availability of standard POSIX functions/headers (alarm, fcntl, getaddrinfo marked thread-safe, sockets, stricmp, etc.). Some HAVE_ macros are defined without a value (HAVE_GSSAPI, HAVE_DIRENT_H, USE_IPV6, USE_UNIX_SOCKETS, USE_OS400CRYPTO), so consumers must test definedness, not truth. Size macros pin curl_off_t/off_t to 8 bytes (off_t per the _LARGE_FILES IFS64IO variant) and int/long/size_t/time_t/curl_socket_t to 4. recv/send argument types are declared as int/char*/int/int with a non-const second send argument, which functypes.h-style wrappers rely on. A #pragma enum(int) forces enum width; an #ifndef _ALL_SOURCE block undefines _ALL_SOURCE rather than defining it. OS/400-specific macros (__ptr128 disabling teraspace, qadrt_use_*_inline wrappers, __cplusplus__strings__) are marked as required before system headers are included, so include order matters: this header must precede system includes.

**Notes.**

- contract: Several feature macros are defined empty rather than to 1, so build logic must check #ifdef, not #if value.
- condition: _ALL_SOURCE is explicitly undefined when not already defined, contrary to what an AIX-style 'define if OS is AIX' comment suggests.
- side_effect: #pragma enum(int) and the qadrt/__ptr128 macros alter compilation of any translation unit including this header.

**Uncertainties.**

- Whether off_t is actually 8 bytes depends on the _LARGE_FILES/IFS64IO compile environment; the header only asserts it via a comment.
- Effects of qadrt_use_fputc/fread/fwrite_inline and __ptr128 depend on OS/400 runtime headers not present in this source.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/curlver.h
[f2]: ../../../../../../eval/curl-2c04412/include/curl/header.h
[f3]: ../../../../../../eval/curl-2c04412/lib/config-os400.h
