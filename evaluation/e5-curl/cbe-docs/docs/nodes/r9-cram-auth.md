# CRAM-MD5 (SASL)

**Capability.** Builds a CRAM-MD5 SASL response: username plus HMAC-MD5 of the challenge keyed by the password, emitted through the dynbuf formatter family.

Use this child for CRAM-MD5 message creation; the residuals are the license header and closing guard. The unit lib/vauth/cram.c::module_residual::::0 contains only the include/guard region and grp:auth-fallback-helpers covers libssh auth-method fallback helpers referenced from the SSH backend.

**Depends on.**

- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 1 edge(s)

Parent: [HTTP/SOCKS authentication](r9-http-auth.md)

## Units (4)

<a id="u-8d9492691923"></a>
### `auth-fallback-helpers`

`static int myssh_to_PASSWD_AUTH(struct Curl_easy *data, struct ssh_conn *sshc)` · [lib/vssh/libssh.c:L392-L400][f1]

Auth method fallback helpers.

myssh_to_PASSWD_AUTH enters password auth if the server advertises SSH_AUTH_METHOD_PASSWORD, otherwise fails with CURLE_LOGIN_DENIED. myssh_to_KEY_AUTH prefers keyboard-interactive (SSH_AUTH_METHOD_INTERACTIVE) by moving to SSH_AUTH_KEY_INIT, falling back to password. myssh_to_GSSAPI_AUTH prefers GSSAPI (SSH_AUTH_METHOD_GSSAPI_MIC) by moving to SSH_AUTH_GSSAPI, falling back to key auth. Each returns SSH_OK on a successful transition or the error result of the fallback.

<a id="u-800012103ffb"></a>
### `Curl_auth_create_cram_md5_message`

`CURLcode Curl_auth_create_cram_md5_message(const struct bufref *chlg, struct Curl_cre…` · [lib/vauth/cram.c:L49-L85][f2]

Builds a CRAM-MD5 SASL response: the username, a space, and the HMAC-MD5 of the challenge keyed by the password, stored in an output bufref.

**Notes.**

- condition: A zero-length challenge skips the HMAC update, so the digest is the HMAC of empty input rather than an error
- failure: Returns CURLE_OUT_OF_MEMORY if HMAC context allocation or curl_maprintf fails; the maprintf string is transferred to out with curl_free as releaser on success

calls: [Curl_HMAC_init](r3-hash-primitives.md#u-3496b0bc2abc), [Curl_HMAC_update](r3-hash-primitives.md#u-33eccf51f0ed), [Curl_HMAC_final](r3-hash-primitives.md#u-333e5a23ac24), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368), [bufref-c-accessors](r14-bufref-buffers.md#u-ac8cad6d65f5), [warnless.c-narrowing-conversions](r12-socket-and-buffer-utils.md#u-97fe403e2706)

**Uncertainties.**

- Curl_creds_user/Curl_creds_passwd semantics are outside this batch; a NULL user or passwd would change strlen/curl_maprintf behavior, which cannot be established here

<a id="u-383916a337a8"></a>
### `cram.c module code (L1–L48)`

`module_region` · [lib/vauth/cram.c:L1-L48][f2]

License header and includes for the CRAM-MD5 module; the file body is guarded by !CURL_DISABLE_DIGEST_AUTH.

**Notes.**

- condition: Everything after the guard, including Curl_auth_create_cram_md5_message, is compiled only when CURL_DISABLE_DIGEST_AUTH is not defined

<a id="u-45d87eec9d1b"></a>
### `cram.c module code (L85–L87)`

`module_region` · [lib/vauth/cram.c:L85-L87][f2]

Closing endif comment for the CURL_DISABLE_DIGEST_AUTH guard; non-behavioral.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vssh/libssh.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/cram.c
