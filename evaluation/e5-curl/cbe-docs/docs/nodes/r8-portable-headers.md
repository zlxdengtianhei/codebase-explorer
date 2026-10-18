# Public Header Portability

**Capability.** Makes the public ABI portable: preprocessor-dispatched curl_off_t/curl_socklen_t typedefs, GCC-only compile-time type checking macros for setopt/getinfo, platform recv/send signature macro types, SIGPIPE suppression around internals, and the socket-layer filter interface declarations.

Use this subtree when touching ABI-visible types or platform compatibility. typecheck-gcc.h affects compilation only on GCC; sigpipe.h is a runtime guard used around blocking calls.

Parent: [Core Utilities and Portability](r8-core-utilities.md)

## Units (6)

<a id="u-b93e4a8c778e"></a>
### `system-h`

`group` · [include/curl/system.h:L1-L399][f1]

Fixes the platform-dependent typedefs curl_off_t and curl_socklen_t purely via preprocessor dispatch.

A long #elif chain, keyed only on compiler built-in symbols, selects per platform/compiler (DJGPP, Borland, POCC, LCC/MCST, classic Macintosh, Tandem, Windows CE, MinGW, VMS/VAX, OS400, MVS, z/OS IBM C, TPF, tcc, Solaris Studio, xlc, HP-UX, MSVC, GCC) CURL_TYPEOF_CURL_OFF_T plus matching printf format macros and integer literal suffixes. Ordering constraints are stated in comments: MSVC must stay penultimate and generic GCC last. The GCC branch picks long long on 32-bit targets (via ILP32/i386/hppa/ppc/arm/sparc/mips/sh/xtensa or __SIZEOF_LONG__==4 or __LONG_MAX__==2^31-1) versus long on LP64/64-bit targets, and defines CURL_POPCOUNT64/CURL_CTZ64 to __builtin_popcountll/ctzll (or the 32-bit-long variants) when GCC >= 3.4. A matched-but-unknown platform or an unmatched platform falls back to a generic long long 'safe guess'; within GCC the 32/64 sub-chains have no internal #else. socklen_t type varies per branch (int, unsigned int, or socklen_t); branches choosing socklen_t define CURL_PULL_SYS_TYPES_H/CURL_PULL_SYS_SOCKET_H, _AIX defines CURL_PULL_SYS_POLL_H, and MinGW/MSVC>=1800 include inttypes.h for PRId64/PRIu64. The conditional includes then pull sys/types.h, sys/socket.h, sys/poll.h as flagged, and conditional typedefs define curl_socklen_t and curl_off_t from the chosen CURL_TYPEOF_* types. Stated design requirement: curl_off_t must be a 64-bit signed type whose width is independent of large-file settings.

**Uncertainties.**

- Within the Solaris Studio and GCC branches the width sub-conditions have no #else; if neither ILP32 nor LP64 conditions match, CURL_TYPEOF_CURL_OFF_T (and for GCC, the popcount macros) remain undefined, and the resulting curl_off_t typedef is skipped.
- CURL_POPCOUNT64/CURL_CTZ64 are defined only in the GCC branch; consumers on other compilers must supply their own definitions elsewhere (not visible in this file).

<a id="u-35b66e97c11a"></a>
### `typecheck-gcc-h-wrapper-macros`

`group` · [include/curl/typecheck-gcc.h:L1-L519][f2]

Provides GCC-only compile-time type checking that wraps curl_easy_setopt, curl_easy_getinfo, and curl_multi_setopt with identically named macros.

Each wrapper expands to a GCC statement expression guarded by __builtin_constant_p(option): if the option/info is a compile-time constant, a cascade of per-type checks runs; otherwise no checks execute and only the parenthesized real function call remains, preserving the original behavior. Checks are nested double ifs (a workaround for gcc 4.3/4.4 -Wlogical-op bug #32061): an option-classifier macro selects the expected value type, and a type predicate on the value triggers a Wcurl_*_err warning function if incompatible. The predicates use __typeof__/__builtin_types_compatible_p and deliberately never evaluate value expressions. CURLOPT_PRIVATE is explicitly exempt from checking; CURL_IGNORE_DEPRECATION wraps the check block. The wrapper yields the result of the parenthesized real call (curl_easy_setopt)(handle, option, value), so runtime behavior is unchanged even when warnings fire (warnings are compile-time only). curl_share_setopt is simply forwarded with three arguments, no checking. Warning functions are defined via the CURLWARNING macro: static noinline unused functions carrying __attribute__((__warning__(message))), which GCC reports when it can prove a call path reaches them.

**Notes.**

- condition: All checks are skipped when __builtin_constant_p(option/info) is false, e.g. non-constant option variables.
- contract: Type predicates must not evaluate their arguments; only sizeof and __typeof__ are applied, so passing expressions with side effects is safe for checking but they still execute once in the real call.

calls: [typecheck-gcc-h-type-predicates](r8-portable-headers.md#u-d6566ba71b29); raises: [typecheck-gcc-h-warning-functions](r1-curl-tool.md#u-a9378c7134a8)

**Uncertainties.**

- Exact warning emission depends on GCC's __attribute__((warning__)) machinery and optimization/reachability analysis, not on this file's code alone.

<a id="u-d6566ba71b29"></a>
### `typecheck-gcc-h-type-predicates`

`group` · [include/curl/typecheck-gcc.h:L519-L964][f2]

Defines the classifier and value-type predicate macros used by the wrapper macros, plus companion typedefs.

Option classifiers group options by expected argument type: curlcheck_long_option (range below CURLOPTTYPE_OBJECTPOINT), curlcheck_off_t_option (between CURLOPTTYPE_OFF_T and CURLOPTTYPE_BLOB), and exact-match lists for string, write-callback, conv-callback, callback-data, postfields, and slist options; analogous info classifiers use CURLINFO_* ranges, excluding CURLINFO_PRIVATE from string info. Value predicates never evaluate expr: curlcheck_NULL compares the expr type against typeof(NULL); curlcheck_ptr/curlcheck_ptrptr/curlcheck_arr use __builtin_types_compatible_p over pointer, array, and const variants; curlcheck_string accepts char/signed char/unsigned char arrays and pointers. curlcheck_long is platform-dependent: when sizeof(long) != sizeof(int) only long variants pass; when equal, int/short/char and signedness variants also pass (documented XXX: int accepted due to variadic promotion). curlcheck_off_t requires exact curl_off_t compatibility. curlcheck_cb_data is deliberately permissive via curlcheck_any_ptr (sizeof == sizeof(void*) or char[]), the #if 0 branch showing an earlier stricter void*/FILE* check. Callback predicates accept NULL or compatibility with the canonical callback type or 'similar' typedefs (Wcurl_*_callback1..N) that vary const-qualification of pointer parameters; curlcheck_read_cb additionally accepts fread-like signatures and curlcheck_write_cb adds fwrite-like ones. The ssl-ctx predicate's typedefs 5-8 use SSL_CTX only when HEADER_SSL_H is defined, otherwise aliasing callback1 - a fragile include-order dependency acknowledged in its comment.

**Notes.**

- condition: curlcheck_ssl_ctx_cb strictness changes with HEADER_SSL_H: OpenSSL's ssl.h included beforehand enables real SSL_CTX typedefs, otherwise non-SSL_CTX aliases are checked.
- contract: curlcheck_long accepts differently signed integer types only on platforms where long and int have equal size.

uses: [typecheck-gcc-h-wrapper-macros](r8-portable-headers.md#u-35b66e97c11a)

**Uncertainties.**

- __builtin_types_compatible_p treatment of typedefs and enum types may cause false negatives not derivable from this file alone.

<a id="u-6d9ac7ebd621"></a>
### `lib-functypes-h-macro-type-defaults`

`group` · [lib/functypes.h:L1-L108][f3]

Defines platform-specific macro types for recv/send signatures, with portable defaults.

When USE_WINSOCK is defined, RECV/SEND_TYPE_ARG1..3 and return types map to SOCKET/char*/int/int; the AmigaOS branch additionally defines RECV_TYPE_ARG4 as long and SEND_NONCONST_ARG2, with int/char*/int argument types. Otherwise the fallback #ifndef blocks supply defaults: int socket, void*/char* buffer, size_t count, int flags, ssize_t return, matching the documented ssize_t prototypes. config-*.h systems can override via earlier defines.

**Uncertainties.**

- No source here shows how SEND_NONCONST_ARG2 is consumed, so its effect on call sites is inferred from its name and comment only

<a id="u-13846c4e2756"></a>
### `sigpipe.h-guard`

`struct Curl_sigpipe_ctx` · [lib/sigpipe.h:L31-L34][f4]

Temporarily ignore SIGPIPE around libcurl internals.

On systems with sigaction and without SO_NOSIGPIPE, struct Curl_sigpipe_ctx saves the previous SIGPIPE disposition and a no_signal flag. sigpipe_init zeroes the context and sets no_signal TRUE. sigpipe_ignore copies data->set.no_signal into the context; when the user did not disable the ignore (no_signal false), it saves the current SIGPIPE handler, installs SIG_IGN (clearing SA_SIGINFO under that flag so sa_handler is valid), and keeps the saved action for restoration. sigpipe_restore reinstates the saved handler only when no_signal is false. sigpipe_apply re-applies when the current handle's no_signal differs from the context's, restoring then re-ignoring, so the suppression follows the active easy handle. On platforms without sigaction or with SO_NOSIGPIPE, all four names become no-op macros and the context is a dummy bool, relying on the socket option or the absence of the signal.

**Notes.**

- contract: sigpipe_restore must only follow a corresponding sigpipe_ignore, as the header states.

**Uncertainties.**

- The parse reported a syntax error near line 1 of this header; coverage is per the program's chunking.

<a id="u-fcee65507f4a"></a>
### `cf-socket-h`

`group` · [lib/cf-socket.h:L1-L154][f5]

Declares the socket-layer interface: interface-option parsing, socket address/open/close helpers, per-transport connection-filter constructors (TCP, UDP, UNIX, TCP accept/listen), and a peek accessor.

The tcp/udp/unix create functions are documented as touching no connection or data flags so they can be used in happy-eyeballs racing, requiring an explicit _active() call once selected. Curl_cf_socket_peek returns the filter-owned socket, address reference, and IP quadruple, and is WARN_UNUSED_RESULT; its doc says it errors when the filter type is invalid. Curl_sock_nosigpipe exists only under USE_SO_NOSIGPIPE. Macros curl_sa_addr/curl_sa_addrbuf abstract sockaddr union access.

imports: [cf-socket-h](r8-portable-headers.md#u-fcee65507f4a)

**Uncertainties.**

- Only signatures and doc comments are visible; actual filter and socket behavior is implemented elsewhere.
- The header produced a parser syntax-error diagnostic near line 1, though full chunk coverage is reported.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/include/curl/system.h
[f2]: ../../../../../../eval/curl-2c04412/include/curl/typecheck-gcc.h
[f3]: ../../../../../../eval/curl-2c04412/lib/functypes.h
[f4]: ../../../../../../eval/curl-2c04412/lib/sigpipe.h
[f5]: ../../../../../../eval/curl-2c04412/lib/cf-socket.h
