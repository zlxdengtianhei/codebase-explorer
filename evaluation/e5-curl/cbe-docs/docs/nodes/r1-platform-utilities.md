# Platform and Auth Utilities

**Capability.** Owns small cross-platform infrastructure: the SASL state vocabulary shared with mail/news clients, dynamic loading of the Windows SSPI dispatch table with identity building/freeing, and the mutex/threading API mapping onto Win32 or POSIX.

Use this for library-level platform abstractions. curl_sspi functions manage the SSPI table and identities, curl_threads.h selects the threading backend, and curl_sasl.h defines the shared SASL contract.

**Depended on by.**

- [curl Command-Line Tool](r1-curl-tool.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r1-curl-codebase.md)

## Units (6)

<a id="u-bff7d9a8b550"></a>
### `curl-sasl.h-state-and-contract`

`enum` · [lib/curl_sasl.h:L66-L85][f1]

Header defining the SASL vocabulary shared by curl_sasl.c and the IMAP/POP3/SMTP clients.

Mechanism bit flags (SASL_MECH_*, 1<<0..1<<10), aggregate values SASL_AUTH_NONE/ANY/DEFAULT (DEFAULT excludes EXTERNAL), wire name strings, and the SASL_FLAG_BASE64 message-encoding flag. The saslstate enum lists all machine states from SASL_STOP through SASL_FINAL and fixes the order that sasl_state's debug name table relies on. saslprogress reports SASL_IDLE/INPROGRESS/DONE. struct SASLproto is the protocol adapter contract: service name, sendauth/contauth/cancelauth/getmessage callbacks, maxirlen (must be zero for non-base64 protocols per comment), contcode/finalcode reply codes, default mechanisms and flags. struct SASL is the per-connection machine: params pointer, state, current mechanism, offered/preferred/used mechanism sets, and resetprefs/mutual_auth/force_ir bits. sasl_mech_equal is a macro testing a line prefix for exact mechanism equality.

**Notes.**

- contract: Curl_sasl_continue compares reply codes against SASLproto::contcode/finalcode and sends via sendauth/contauth/cancelauth, so protocol modules must keep those callbacks consistent with maxirlen and flags.

<a id="u-0cb4f32d8a3a"></a>
### `Curl_create_sspi_identity`

`CURLcode Curl_create_sspi_identity(const char *userp, const char *passwdp, SEC_WINNT_…` · [lib/curl_sspi.c:L95-L187][f2]

Populates an SEC_WINNT_AUTH_IDENTITY_EX from a username (optionally 'Domain\User' or 'Domain/User') and password, converting both from UTF-8 to TCHAR.

It zeroes the identity, sets Version, Length and Flags, then splits the username at the first backslash or forward slash into domain and user parts. Each allocation failure returns CURLE_OUT_OF_MEMORY and frees everything allocated so far in strict reverse order; _tcsncpy_s failure is treated as OOM. On success it stores duplicated user, domain and password pointers and their lengths in the identity, transferring ownership. The temporary password buffer is zeroed with curlx_memzero before being freed to avoid leaving the plaintext password in freed memory.

uses: [curl_sspi.h module code (L46–L103)](r5-protocol-headers.md#u-858c1a5dfaef)

**Uncertainties.**

- Behavior when userp contains multiple separators (only the first split point is used) follows _tcschr semantics but exact TCHAR conversion of malformed UTF-8 is delegated to curlx_convert_UTF8_to_tchar, whose failure modes are not shown.

<a id="u-4f3ccd1b8582"></a>
### `Curl_sspi_free_identity`

`void Curl_sspi_free_identity(SEC_WINNT_AUTH_IDENTITY_EX *identity)` · [lib/curl_sspi.c:L198-L207][f2]

Releases the user, password and domain buffers owned by an SSPI identity structure.

It is a no-op on a NULL identity. The password buffer is first zeroed using its recorded PasswordLength, then all three pointers are freed via curlx_safefree, which also nulls them.

<a id="u-4798a560bfd4"></a>
### `Curl_sspi_global_cleanup`

`void Curl_sspi_global_cleanup(void)` · [lib/curl_sspi.c:L74-L79][f2]

Clears the global SSPI dispatch table pointer, resetting SSPI global state so a later Curl_sspi_global_init reloads it.

It nulls Curl_pSecFn only when non-NULL and frees no other resources.

<a id="u-04f713aba199"></a>
### `Curl_sspi_global_init`

`CURLcode Curl_sspi_global_init(void)` · [lib/curl_sspi.c:L52-L63][f2]

Lazily loads the Windows SSPI dispatch table so callers can invoke SSPI without build-time linking.

If the global Curl_pSecFn pointer is still NULL, it calls InitSecurityInterface(); if that also returns NULL, it returns CURLE_FAILED_INIT. If the pointer is already set (or acquisition succeeds), it returns CURLE_OK and leaves the existing pointer untouched.

uses: [curl_sspi.h module code (L46–L103)](r5-protocol-headers.md#u-858c1a5dfaef)

**Uncertainties.**

- Thread-safety of the lazy initialization is not visible in this file.

<a id="u-c5fd178b8811"></a>
### `curl_threads.h module code (L1–L83)`

`module_region` · [lib/curl_threads.h:L1-L83][f3]

Header that maps curl's threading and mutex API onto Win32 or POSIX, all inside USE_MUTEX / USE_THREADS guards, with a #error when neither platform backend is defined.

It typedefs CURL_THREAD_RETURN_T, CURL_STDCALL, curl_mutex_t, curl_thread_t (HANDLE on Windows, pthread_t* on POSIX), curl_thread_id_t, curl_thread_t_null, and the Curl_mutex_* and Curl_cond_init/destroy macros, and declares Curl_cond_signal, Curl_cond_wait, Curl_cond_timedwait (documented to return CURLE_OPERATION_TIMEDOUT on timeout), Curl_thread_get_current_id, Curl_thread_is_current, Curl_thread_create, Curl_thread_destroy, and Curl_thread_join.

contract: [Curl_thread_create](r5-thread-primitives.md#u-57c0d8d7919d)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/curl_sasl.h
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_sspi.c
[f3]: ../../../../../../eval/curl-2c04412/lib/curl_threads.h
