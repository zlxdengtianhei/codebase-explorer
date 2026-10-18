# Platform build configuration

**Capability.** Compile-time normalization of platform, compiler, and feature differences so the rest of the library compiles against one consistent environment.

Consult these headers first when porting or debugging platform-specific behavior. They patch missing constants, redirect standard APIs, and translate OS-native path formats. No runtime logic lives here.

Parent: [curl codebase](r7-curl-codebase.md)

## Units (6)

<a id="u-e259768b37df"></a>
### `curl_setup-h-platform-configuration`

`struct timeval` · [lib/curl_setup.h:L869-L872][f1]

Build-time configuration header that normalizes platform, compiler, and feature differences for the whole libcurl library before any code is compiled.

It first enforces minimum toolchains (#error for mingw-w64 <3.0, MSVC <1600, Windows <Vista, and DEBUGBUILD+NDEBUG coexistence), applies targeted workarounds (Apple availability attribute and TargetConditionals fixes, llvm/Xcode built-in macro gap), and selects the config include: HAVE_CONFIG_H pulls in curl_config.h, otherwise platform-specific config-win32/mac/os400 headers are used. It then derives feature macros: disabling CURL_DISABLE_HTTP cascades into a list of related disable macros; resolver selection is mutually exclusive (CURLRES_IPV6 when USE_IPV6+HAVE_GETADDRINFO, error on Windows IPv6 without getaddrinfo, else CURLRES_IPV4; CURLRES_ASYNCH for threaded or c-ares resolvers with libc addrinfo calls undefined, else CURLRES_SYNCH). SSL, SPNEGO, Kerberos5, NTLM (gated by CURL_ENABLE_NTLM plus DES-capable backends or SSPI), SSH, HTTP2 and HTTP3/QUIC flags are derived from backend macros, with error cases for libidn2+WinIDN/AppleIDN and QUIC+MultiSSL. Socket I/O is abstracted into macros: sread maps to read/recv (recv argument types must come from config, else #error), swrite to write/send (with SEND_4TH_ARG=MSG_NOSIGNAL when defined, else 0; Minix uses read/write); CURL_SCLOSE picks closesocket/CloseSocket/close_s/lwip_close/close. Memory allocation macros route through curl_dbg_* logging wrappers under CURL_MEMDEBUG, through Curl_cmalloc-family when BUILDING_LIBCURL, or plain libc otherwise; curlx_safefree frees and NULLs the pointer. bool/timeval/sockaddr_un fallback types are defined only when missing; SIZEOF_TIME_T defaults to 4 and socket-size/format macros vary by Winsock and 64-bit builds. curlx_memzero_low selects SecureZeroMemory/memset_s/explicit_bzero variants per platform, declaring a function fallback when none applies. Everything is purely preprocessor, typedefs, and extern declarations: no runtime code executes here, but every macro choice changes which implementations downstream sources compile.

**Notes.**

- contract: This header must be included first; it deliberately defines compiler-behavior macros before any system header is included.
- condition: Several configurations are compile-time errors: stale toolchains, IPv6 without getaddrinfo on Windows, conflicting IDN backends, QUIC with MultiSSL, and lwIP mixed with Winsock.
- side_effect: On Windows it redefines read/write/fileno/unlink/isatty to their _-prefixed CRT variants to silence deprecation warnings.

imports: [lib/curl_setup.h][f1], [lib/curlx/warnless.h][f2]

**Uncertainties.**

- The tree-sitter parse reported an ERROR node near line 1, so macro-level coverage was reconstructed from the full text; individual conditional outcomes were read directly but no preprocessor evaluation was performed.
- The CURL_INLINE branch checking defined(inline) assumes an 'inline' macro may be set externally; its actual effect depends on build flags not visible here.

<a id="u-3199745f5b5e"></a>
### `setup-os400.h module code (L1–L147)`

`module_region` · [lib/setup-os400.h:L1-L147][f3]

OS/400 platform configuration header that patches missing constants and redirects standard APIs to ASCII-aware wrappers.

It unconditionally defines NI_MAXHOST (1025) and NI_MAXSERV (32) because OS/400 netdb.h omits them, redefines isatty(fd) as constant 0 so tty detection always reports no terminal, and#undefs then redefines puts to fputs on stdout followed by an explicit newline, working around an IBM QADRT runtime bug where puts omits the trailing newline. After including socket, netdb, GSKSSL, QSOASYNC, and GSSAPI headers, it activates its macro-rename block only when BUILDING_LIBCURL is defined: getaddrinfo/getnameinfo become Curl_getaddrinfo_a/Curl_getnameinfo_a (declared with socklen_t since curl_socklen_t is not yet available), four gss_* calls become _a variants, LDAP calls become UTF8/_a wrappers with BerValue aliased to struct berval, six socket calls (connect, bind, sendto, recvfrom, getpeername, getsockname) become Curl_os400_* functions noted as needed to handle textual AF_UNIX addresses, and, when HAVE_LIBZ is defined, zlib functions become Curl_os400_zlib* wrappers. All renames are macro text substitutions valid only while this header is in scope; the wrapper bodies are extern and defined elsewhere.

**Notes.**

- side_effect: Every rename is a preprocessor macro affecting only translation units that include this header after the #define lines.
- condition: All wrapper redirections, including the zlib ones, are gated on BUILDING_LIBCURL; zlib redirects additionally require HAVE_LIBZ.

imports: [lib/setup-os400.h][f3]; uses: [lib/setup-os400.h][f3]

**Uncertainties.**

- The behavior of the Curl_* wrapper functions (ASCII conversion, AF_UNIX handling) is only declared here, not defined; their runtime semantics are not visible in this file.

<a id="u-19fcfb1829ef"></a>
### `CONF_modules_load_file`

`static int CONF_modules_load_file(const char *filename, const char *appname, unsigned…` · [lib/setup-vms.h:L213-L217][f4]

Stub replacing CONF_modules_load_file only on __VAX builds with VMS_OLD_SSL, where the ancient OpenSSL lacks both the function and the CONF_MFLAGS_IGNORE_MISSING_FILE constant (defined here as 0x10 just before).

It ignores filename, appname, and flags and always returns 1, i.e. reports success so configuration loading is treated as a no-op. Outside that macro combination the name is only re-spelled uppercase via macro and the real OpenSSL symbol is used.

**Uncertainties.**

- Whether returning 1 matches the real function's success convention for all callers is not establishable from this file.

<a id="u-8839e891e25d"></a>
### `vms_getenv`

`static char *vms_getenv(const char *envvar)` · [lib/setup-vms.h:L116-L137][f4]

Overrides getenv on VMS: fetches the variable via the DECC C RTL (decc$getenv) and, when the result exists, passes it through vms_translate_path so VMS-format paths become Unix format.

If decc$getenv returns NULL, NULL is returned immediately and no translation is attempted. On 64-bit-pointer builds vms_translate_path is a macro no-op, so this reduces to a plain pass-through of decc$getenv's result. Ownership follows the DECC RTL: the trailing comment explicitly warns against freeing the result for DEC C RTL builds (and notes VAX C RTL would need a free), so no free occurs here.

calls: [vms_translate_path](r7-platform-build-config.md#u-144f8c23667c)

**Uncertainties.**

- Whether callers own or must copy the returned string is not enforced by this function; it relies on the documented DECC RTL behavior noted in the comment.

<a id="u-769a047a81cd"></a>
### `vms_getpwuid`

`static struct passwd *vms_getpwuid(uid_t uid)` · [lib/setup-vms.h:L141-L183][f4]

Overrides getpwuid on VMS, wrapping the DECC lookup selected at preprocessing time (long-GID, 32-bit, or default variant) and post-processing pw_dir into Unix form.

If decc_getpwuid returns NULL, NULL is returned. Otherwise pw_dir is run through vms_translate_path; the result is examined with '(long)unix_path <= 0' to detect failure, in which case the DECC passwd structure is returned as-is. If translation returned the same pointer (no change needed), the DECC structure is also returned. Only when a genuinely different translated path exists is the static cache struct vms_passwd_cache filled from the DECC result — pw_name, pw_uid, pw_gid, pw_shell copied verbatim, pw_dir set to the translated path — and its address returned; note pw_gid is assigned from pw_uid, preserving (or duplicating) whatever the RTL produced. Because the cache is a single static struct, the previously returned result is invalidated by any subsequent call. The unix_path pointer is declared as __char_ptr32 on 64-bit DECC builds to interoperate with 32-bit RTL.

**Notes.**

- side_effect: Returns the address of the static vms_passwd_cache, so concurrent or successive calls overwrite the previously returned passwd data.
- field: pw_gid is assigned my_passwd->pw_uid, not pw_gid — visible in source; whether that is intentional is unstated.

calls: [vms_translate_path](r7-platform-build-config.md#u-144f8c23667c)

**Uncertainties.**

- The '(long)unix_path <= 0' failure test assumes translated pointers never legitimately have a negative/zero long representation; behavior for such values is unproven.

<a id="u-144f8c23667c"></a>
### `vms_translate_path`

`static char *vms_translate_path(const char *path)` · [lib/setup-vms.h:L83-L101][f4]

Translates a VMS-format path to Unix syntax, used as a shim on 32-bit-pointer DECC builds.

It treats the input as a path (not arbitrary data) and checks for VMS path markers by scanning for any of ':', '[', '<', '^' with strpbrk; if none appear, the original pointer is returned unchanged. If a marker is found, decc$translate_vms is invoked; when its cast-to-int result is <= 0 the translation failed and the original string is returned. On 64-bit-initial-pointer DECC builds this function is not compiled; a same-name macro makes calls a no-op returning the argument. NOTE: in the compiled branch, when translation succeeds the function body ends without returning unix_path — it falls off the end of a non-void function, so the returned value is undefined; callers' checks like '(long)unix_path <= 0' operate on that indeterminate value.

**Notes.**

- failure: A successful decc$translate_vms hit falls off the end of the function without a return statement, so the success-path result is undefined in the compiled 32-bit branch.

uses: [vms_getenv](r7-platform-build-config.md#u-8839e891e25d)

**Uncertainties.**

- Whether decc$translate_vms returns a pointer on success cannot be confirmed from this file; the int cast check is the only guard.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_setup.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curlx/warnless.h
[f3]: ../../../../../../eval/curl-2c04412/lib/setup-os400.h
[f4]: ../../../../../../eval/curl-2c04412/lib/setup-vms.h
