# Refcounted credential store

**Capability.** A shared, refcounted representation of a credential set (user, password, bearer, SASL fields) with create/merge/link/unlink reference management and equality comparison.

All consumers (easy handle, connection, proxy, netrc path) reference credential sets through these functions. Read Curl_creds_create and Curl_creds_unlink to understand the ownership model.

**Depended on by.**

- [Connection metadata and scheme descriptors](r7-connection-metadata.md) · graph-confirmed · 3 edge(s)
- [Connection pool: find, match, create](r7-connection-pool.md) · graph-confirmed · 9 edge(s)
- [Easy handle lifecycle](r7-easy-handle-lifecycle.md) · graph-confirmed · 1 edge(s)
- [Proxy resolution and NO\_PROXY](r7-proxy-resolution.md) · graph-confirmed · 3 edge(s)
- [Transfer URL and credential resolution](r7-url-and-credentials.md) · graph-confirmed · 8 edge(s)

Parent: [Connection and credential core](r7-conn-core.md)

## Units (8)

<a id="u-299deff85f99"></a>
### `creds-h-struct-and-macros`

`struct Curl_creds` · [lib/creds.h:L34-L44][f1]

Defines the shared, refcounted credential representation and its accessors.

struct Curl_creds embeds five non-NULL string pointers (possibly empty), a uint32_t refcount, a uint8_t source carrying a CREDS_* origin value (CREDS_NONE, CREDS_URL, CREDS_OPTION, CREDS_NETRC), a bufsize recording the extra bytes allocated past the struct, and a flexible trailing buf. Header macros provide non-allocating accessors: the has_* macros test the first character for truthiness only when the set is non-NULL, and the value macros return the field or the empty string for a NULL set. Curl_creds_trace is declared only under CURLVERBOSE.

**Notes.**

- field: buf is the anchor for the variable-size tail allocation laid out by Curl_creds_create; accessors never touch it directly.
- contract: Readers may rely on user/passwd/oauth_bearer/sasl_authzid/sasl_service never being NULL inside a live non-NULL set.

contract: [Curl_creds_create](r7-credential-store.md#u-ca1cf603180d)

<a id="u-ca1cf603180d"></a>
### `Curl_creds_create`

`CURLcode Curl_creds_create(const char *user, const char *passwd, const char *oauth_be…` · [lib/creds.c:L34-L102][f2]

Allocates a refcounted credential object holding user, passwd, oauth bearer, SASL authzid and SASL service in one trailing buffer.

It first unlinks *pcreds, then returns a NULL credential when all inputs are empty/NULL (leaving *pcreds NULL via the out path). Any input longer than CURL_MAX_INPUT_LENGTH yields CURLE_BAD_FUNCTION_ARGUMENT. Otherwise it callocs sizeof(struct Curl_creds) plus space for all five strings plus terminators, sets refcount=1 and source, and lays the strings back-to-back via offsetof(struct Curl_creds, buf); empty inputs are left as empty strings since buf was zeroed. On success *pcreds is set; on failure the partially built object is unlinked (freed when its refcount drops to zero) and the error propagates.

**Notes.**

- side_effect: On entry *pcreds is unlinked, so a pre-existing credential is dereferenced even when creation subsequently fails.
- contract: All five string pointers in a created object are non-NULL, empty strings included; the NULL credential is the all-NULL-pointer object with refcount 0.

calls: [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

**Uncertainties.**

- Exact behavior of curlx_calloc and curlx_free under failure is defined outside this file.

<a id="u-6b0883339660"></a>
### `Curl_creds_equal`

`bool Curl_creds_equal(struct Curl_creds *c1, struct Curl_creds *c2)` · [lib/creds.c:L169-L173][f2]

Like Curl_creds_same but also requires matching source.

It returns the result of Curl_creds_same and, unless both pointers are identical, additionally requires both to be non-NULL with equal source bytes. NULL versus non-NULL remains unequal.

calls: [Curl_creds_same](r7-credential-store.md#u-338fbc38108d)

<a id="u-ed4d022e2a5a"></a>
### `Curl_creds_link`

`void Curl_creds_link(struct Curl_creds **pdest, struct Curl_creds *src)` · [lib/creds.c:L130-L140][f2]

Assigns a credential reference to *pdest with reference counting.

If *pdest already equals src nothing happens; otherwise the old *pdest reference is dropped, *pdest is set to src (possibly NULL), and src's refcount is incremented when non-NULL, with a debug assertion that it has not reached UINT32_MAX.

calls: [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

<a id="u-8ead1548f1fe"></a>
### `Curl_creds_merge`

`CURLcode Curl_creds_merge(const char *user, const char *passwd, struct Curl_creds *cr…` · [lib/creds.c:L104-L128][f2]

Builds a new credential set by overriding user and/or passwd of an existing credential set.

When creds_in is NULL it creates a credential from only user/passwd; otherwise it falls back per field to the existing user, passwd, oauth bearer, SASL authzid and SASL service, so a NULL override keeps the old value. It then links the new object into *pcreds_out (releasing any prior value there) and unlinks its local reference, so ownership transfers entirely via the link; the creation result code is returned.

calls: [Curl_creds_create](r7-credential-store.md#u-ca1cf603180d), [Curl_creds_link](r7-credential-store.md#u-ed4d022e2a5a), [Curl_creds_unlink](r7-credential-store.md#u-34e2f9d00816)

<a id="u-338fbc38108d"></a>
### `Curl_creds_same`

`bool Curl_creds_same(struct Curl_creds *c1, struct Curl_creds *c2)` · [lib/creds.c:L158-L167][f2]

Reports whether two credential sets carry the same values, ignoring source.

Two identical pointers are equal; otherwise both must be non-NULL and all five string fields (user, passwd, oauth_bearer, sasl_authzid, sasl_service) must compare equal via Curl_timestrcmp, the constant-time string comparison. Two NULLs are equal; a NULL versus a non-NULL set is not.

uses: [Curl_timestrcmp](r3-string-error-utils.md#u-7ed1fd4e44dd)

<a id="u-0ce4ba7e5f51"></a>
### `Curl_creds_trace`

`void Curl_creds_trace(struct Curl_easy *data, struct Curl_creds *creds, const char *msg)` · [lib/creds.c:L176-L191][f2]

Logs a credential set for verbose builds only.

When creds is non-NULL it emits a trace line with the message prefix, user, SASL authzid and numeric source, masking passwd and oauth bearer as '***' whenever non-empty and printing empty strings otherwise; when creds is NULL it logs the message with '-'. Compiled out entirely unless CURLVERBOSE is defined.

uses: [Curl_trc_multi](r1-trace-logging.md#u-385de27aa970)

<a id="u-34e2f9d00816"></a>
### `Curl_creds_unlink`

`void Curl_creds_unlink(struct Curl_creds **pcreds)` · [lib/creds.c:L142-L156][f2]

Drops one reference from the credential in *pcreds and frees it when the last reference goes away.

If *pcreds is NULL it does nothing. Otherwise it asserts a nonzero refcount, clears *pcreds, decrements the refcount, and only when it reaches zero zeroes the whole allocation (struct plus bufsize bytes) and frees it. A credential with refcount 0 is treated as the NULL credential but the pointer is still freed once.

**Notes.**

- failure: Calling unlink twice on the same dangling pointer would double-free; the caller must rely on *pcreds being set to NULL.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/creds.h
[f2]: ../../../../../../eval/curl-2c04412/lib/creds.c
