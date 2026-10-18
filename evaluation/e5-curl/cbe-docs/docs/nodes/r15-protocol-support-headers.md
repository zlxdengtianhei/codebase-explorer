# Protocol support declarations

**Capability.** Small interface headers for optional protocol features: telnet option constants, GSS-API wrappers, the MD5 backend vtable types, range requests, HTTP proxy tunneling, and IDN handling.

These are declaration-only surfaces consumed elsewhere in libcurl. MD5_context/MD5_params define the pluggable hash backend contract; the rest declare hooks implemented in separate translation units.

Parent: [curl codebase](r15-curl-codebase.md)

## Units (7)

<a id="u-57e3287919ed"></a>
### `arpa_telnet.h module code (L1–L116)`

`module_region` · [lib/arpa_telnet.h:L1-L116][f1]

Header of Telnet protocol constants for curl's telnet support: option codes, command codes, negotiation qualifiers, range-check macros, and name lookup macros.

All content is guarded by both an include guard and CURL_DISABLE_TELNET, so the file expands to nothing when telnet is disabled. The check macros CURL_TELOPT_OK and CURL_TELCMD_OK are simple integer comparisons against the maximum defined option and command codes; CURL_TELCMD_OK casts its argument to unsigned int, so values below the minimum wrap to large numbers and fail the range test. Under CURLVERBOSE, CURL_TELOPT(x) and CURL_TELCMD(x) index static const string tables, with CURL_TELCMD offsetting by CURL_TELCMD_MINIMUM; no bounds check is performed by these macros themselves, so out-of-range indices read past the table unless the caller applies the OK macros first. Without CURLVERBOSE both lookup macros expand to an empty string, avoiding the tables entirely. Note the tables index by raw option code even though option numbers are sparse (e.g. 2 is absent), and telnetoptions has 40 entries covering codes 0-39, while CURL_TELOPT_MAXIMUM is NEW_ENVIRON (39), consistent with CURL_TELOPT_OK.

**Notes.**

- contract: CURL_TELOPT/CURL_TELCMD lookups are safe only for values passing the corresponding OK macros; the macros perform no bounds checking themselves.
- condition: CURLVERBOSE selects string-table lookups; without it both lookup macros yield "" and the tables are not compiled.
- failure: Out-of-range macro arguments index outside the static arrays, with undefined behavior; only the caller's use of CURL_TELOPT_OK/CURL_TELCMD_OK prevents this.

**Uncertainties.**

- Whether CURLVERBOSE is a standard curl build flag or a typo for CURL_VERBOSE is not determinable from this file; if it is a typo, the string tables and verbose lookups may never compile.
- The telnetoptions table has 40 entries but includes sparse codes; the mapping from code to table index for codes like 2 is positional and assumed correct only by table construction, not verified here.

<a id="u-fcb4afac4875"></a>
### `curl_gssapi.h module code (L1–L96)`

`module_region` · [lib/curl_gssapi.h:L1-L96][f2]

Header exposing curl's shared GSS-API wrappers and SOCKS5 GSS protection-level constants.

Guarded by HAVE_GSSAPI, it declares extern mechanism OIDs (SPNEGO and Kerberos) and prototypes for wrapped gss_* calls including Curl_gss_init_sec_context, context/credential lifecycle helpers, and, only when CURLVERBOSE is defined, a real Curl_gss_log_error; otherwise a variadic-argument-swallowing do/while macro. GSSAUTH_P_* macros define protection values 1/2/4 used by SOCKS5 GSS negotiation.

**Notes.**

- contract: Curl_gss_log_error is a no-op macro discarding all arguments when CURLVERBOSE is undefined, so non-verbose builds pay no logging cost.

uses: [socks5_gss_auth_loop](r3-socks-proxy.md#u-cd87d228bdcd), [socks5_gss_negotiate_enc](r3-socks-proxy.md#u-1b6d7016a6af)

**Uncertainties.**

- Implementations of the declared functions live outside this file; their behavior is not visible here.

<a id="u-498ab22762bb"></a>
### `MD5_params`

`struct MD5_params` · [lib/curl_md5.h:L40-L46][f3]

Function-pointer table describing an MD5 backend: init/update/final callbacks with CURLcode/void signatures, the backend context size, and the result length.

It parameterizes curl's MD5 digest API over the crypto library chosen at compile time.

uses: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

<a id="u-0473e7fd6415"></a>
### `MD5_context`

`struct MD5_context` · [lib/curl_md5.h:L48-L51][f3]

State holder for an incremental MD5 computation: the MD5_params backend table plus one opaque hash context (md5_hashctx) whose allocation size comes from the table's md5_ctxtsize.

The header also declares Curl_md5it and the Curl_MD5_init/update/final functions that operate on this context.

uses: [MD5_params](r15-protocol-support-headers.md#u-498ab22762bb)

<a id="u-53ae16e17c36"></a>
### `curl_range-h-header`

`group` · [lib/curl_range.h:L1-L31][f4]

Header declaring the single prototype CURLcode Curl_range(struct Curl_easy *data), with include guards; no behavior of its own.

<a id="u-1fd5c8ef9c70"></a>
### `http-proxy-h`

`enum Curl_proxy_use` · [lib/http_proxy.h:L32-L37][f5]

Declares the HTTP proxy tunnel interface.

Enum Curl_proxy_use classifies header context (direct server, proxy request, CONNECT, CONNECT-UDP). proxy_http_ver selects tunnel request HTTP version (v1/v2/v3), and proxy_inspect_result classifies tunnel response inspection as OK, FAILED, or AUTH_RETRY. Two functions create the CONNECT/CONNECT-UDP request and inspect its response for H2/H3 capsule-protocol and auth handling; insertion helper, transport mapper, PROXY_TIMEOUT of one hour, and the filter type complete the surface. Everything is guarded by !CURL_DISABLE_PROXY && !CURL_DISABLE_HTTP.

imports: [http-proxy-h](r15-protocol-support-headers.md#u-1fd5c8ef9c70)

**Uncertainties.**

- Function bodies are not in this header; response-inspection semantics beyond the enum comments are inferred from comments only.

<a id="u-6627b85ed551"></a>
### `idn.h module code (L1–L45)`

`module_region` · [lib/idn.h:L1-L45][f6]

Declarations for IDN (internationalized domain name) handling.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/arpa_telnet.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_gssapi.h
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_md5.h
[f4]: ../../../../../../eval/curl-2c04412/lib/curl_range.h
[f5]: ../../../../../../eval/curl-2c04412/lib/http_proxy.h
[f6]: ../../../../../../eval/curl-2c04412/lib/idn.h
