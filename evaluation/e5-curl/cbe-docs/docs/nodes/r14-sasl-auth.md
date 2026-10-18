# SASL / Web Auth Message Builders

**Capability.** Owns client-side authentication message construction: SASL PLAIN/LOGIN/EXTERNAL cleartext messages, GSASL mechanism stepping, and the NTLM type-1/type-3 message building and type-2 challenge decoding with its debug dumps.

Protocol handlers call into this subtree to produce or consume authentication handshake messages. Builders return owned buffers (via bufref) and the NTLM debug helpers compile only under DEBUG_ME builds.

**Depends on.**

- [Bufref Utility](r14-bufref-buffers.md) · graph-confirmed · 2 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (9)

<a id="u-eb2d42a29507"></a>
### `cleartext-c-plain-login-external-messages`

`CURLcode Curl_auth_create_plain_message(struct Curl_creds *creds, struct bufref *out)` · [lib/vauth/cleartext.c:L49-L73][f1]

Builds the SASL PLAIN, LOGIN, and EXTERNAL client messages for cleartext authentication.

PLAIN assembles authzid, NUL, user, NUL, password into one binary blob; LOGIN and EXTERNAL wrap a single string value without copying it.

**Notes.**

- side_effect: PLAIN allocates the message via curl_maprintf and hands ownership to the bufref with curl_free as releaser; LOGIN/EXTERNAL attach no releaser and take no ownership.

calls: [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368), [lib-mprintf-c-dynbuf-alloc-family](r9-mprintf-formatter-families.md#u-ce09737881fa); group: [cleartext-c-plain-login-external-messages](r14-sasl-auth.md#u-eb2d42a29507)

**Uncertainties.**

- The PLAIN length check bounds each component at CURL_MAX_INPUT_LENGTH but the computed len is used as the bufref size while the maprintf buffer length is not independently verified to equal len.
- Entire file compiles out unless IMAP/SMTP/POP3 or OpenLDAP is enabled; behavior exists only under those build conditions.

<a id="u-4cc9e31eb284"></a>
### `ntlm.c-debug-print-helpers`

`static void ntlm_print_flags(FILE *handle, unsigned long flags)` · [lib/vauth/ntlm.c:L162-L226][f2]

Compile-time debug helpers that dump NTLM flag bits and raw buffers for DEBUG_ME builds only.

ntlm_print_flags tests each documented or unknown NTLMFLAG bit in order and prints the matching flag name to the given FILE handle via curl_mfprintf, so unknown bits appear as NTLMFLAG_UNKNOWN_n. ntlm_print_hex ignores its handle argument and writes '0x' followed by each byte of the buffer as two hex digits to stderr. Both functions are compiled only when DEBUG_ME is 1; otherwise DEBUG_OUT(x) expands to Curl_nop_stmt and no printing occurs.

**Uncertainties.**

- The supplied source does not show which callers pass a non-stderr handle to ntlm_print_flags.

<a id="u-700c9bae1bf9"></a>
### `Curl_auth_gsasl_cleanup`

`void Curl_auth_gsasl_cleanup(struct gsasldata *gsasl)` · [lib/vauth/gsasl.c:L113-L120][f3]

Tears down the GSASL session: gsasl_finish on the client, then gsasl_done on the context; both struct fields are nulled afterward, making repeat calls safe on already-null members only insofar as the external library tolerates them.

**Uncertainties.**

- Behavior of gsasl_finish/gsasl_done on NULL members is a libgsasl contract not visible in this source.

<a id="u-77b1c8a6ca6b"></a>
### `Curl_auth_gsasl_is_supported`

`bool Curl_auth_gsasl_is_supported(struct Curl_easy *data, const char *mech, struct gs…` · [lib/vauth/gsasl.c:L39-L59][f3]

Initializes a libgsasl client for the given mechanism.

gsasl_init failure is logged with failf and returns FALSE without touching the context. gsasl_client_start failure releases the context with gsasl_done, nulls gsasl->ctx, and returns FALSE. Success returns TRUE with gsasl->ctx and gsasl->client populated for later token exchange.

uses: [gsasl.c module code (L59–L92)][f3]

**Uncertainties.**

- The libgsasl API functions are external; their exact contracts are not visible in the supplied source.

<a id="u-5af3cbaf385b"></a>
### `Curl_auth_gsasl_token`

`CURLcode Curl_auth_gsasl_token(struct Curl_easy *data, const struct bufref *chlg, str…` · [lib/vauth/gsasl.c:L93-L111][f3]

Advances the GSASL authentication by feeding the server challenge through gsasl_step.

Any result other than GSASL_OK or GSASL_NEEDS_MORE is logged with failf and returns CURLE_BAD_CONTENT_ENCODING; on success the produced response buffer is returned via Curl_bufref_set with gsasl_free as destructor, whether the exchange is complete or another step is needed.

calls: [bufref-c-accessors](r14-bufref-buffers.md#u-ac8cad6d65f5), [Curl_bufref_set](r14-bufref-buffers.md#u-214d3ce6e368)

**Uncertainties.**

- Whether GSASL_NEEDS_MORE is distinguishable to the caller after this function returns CURLE_OK is not visible here; the bufref carries the partial response either way.

<a id="u-5c59c7e61d37"></a>
### `Curl_auth_create_ntlm_type1_message`

`CURLcode Curl_auth_create_ntlm_type1_message(struct Curl_easy *data, struct Curl_cred…` · [lib/vauth/ntlm.c:L423-L526][f2]

Builds a minimal NTLM type-1 (negotiate) message with empty host and domain fields.

It first calls Curl_auth_cleanup_ntlm to reset prior state, then formats the fixed 32-byte header via curl_maprintf using the ASCII NTLMSSP signature, type 1, and flag bits NEGOTIATE_OEM, REQUEST_TARGET, NEGOTIATE_NTLM_KEY, NEGOTIATE_NTLM2_KEY and NEGOTIATE_ALWAYS_SIGN; host/domain lengths and offsets are all zero because the strings are empty. Allocation failure returns CURLE_OUT_OF_MEMORY without touching out. On success the resulting size is 32 plus the (zero) host and domain lengths and the buffer is handed to the caller through Curl_bufref_set with curl_free as the destructor. The service/host/creds parameters are currently unused (cast to void).

**Notes.**

- contract: The caller receives ownership of the returned buffer via the bufref, freed by curl_free.

calls: [Curl_auth_cleanup_ntlm][f2]

**Uncertainties.**

- The SASL service selection expression (Curl_creds_has_sasl_service/Curl_creds_sasl_service) is computed but its result is discarded, so its effect on the message is none in this source.

<a id="u-bbc784ec1ca3"></a>
### `Curl_auth_create_ntlm_type3_message`

`CURLcode Curl_auth_create_ntlm_type3_message(struct Curl_easy *data, struct Curl_cred…` · [lib/vauth/ntlm.c:L544-L839][f2]

Builds the NTLM type-3 (authenticate) response to the stored type-2 challenge.

The username is split at the first backslash or slash into domain and user; the fixed hostname 'WORKSTATION' is sent instead of the real host. If ntlm->flags has NTLMFLAG_NEGOTIATE_NTLM2_KEY the NTLMv2 path runs: 8 random bytes are obtained from Curl_rand, then Curl_ntlm_core_mk_nt_hash, mk_ntlmv2_hash, mk_lmv2_resp and mk_ntlmv2_resp produce the 24-byte LMv2 response in lmresp and a variable-length NTLMv2 response in a heap buffer; every step's error (including random failure) is returned immediately before the buffer is allocated. Otherwise the NTLMv1 path computes NT and LM hashes and 24-byte responses against the nonce and clears the NTLM2 flag. If the peer negotiated Unicode, domain/user/host lengths are doubled for transmission. The fixed 64-byte header is written with curl_msnprintf including offsets computed from lmrespoff=64, ntrespoff, and string offsets; the 24-byte LM response is appended when size leaves room (size < NTLM_BUFSIZE - 0x18). If ntresplen plus size exceeds the 1024-byte buffer, a failf and CURLE_TOO_LARGE are raised through a shared error path; likewise if the domain, user and host strings would not fit. The strings are appended, with unicodecpy inserting zero bytes for Unicode or plain memcpy otherwise. On success the blob is copied into a new bufref via Curl_bufref_memdup0. The error label always frees the NTLMv2 response buffer and calls Curl_auth_cleanup_ntlm, so the ntlm state is reset whether or not an error occurred.

**Notes.**

- failure: All crypto and random-generation failures return early before any buffer is produced; size-limit failures free ntlmv2resp and reset ntlm via the shared error label.
- side_effect: ntlm state (flags cleared of NTLM2_KEY in v1 mode, target info freed) is mutated during message creation.

calls: [Curl_auth_create_ntlm_type3_message](r14-sasl-auth.md#u-bbc784ec1ca3), [Curl_auth_cleanup_ntlm][f2]; uses: [Curl_auth_decode_ntlm_type2_message](r14-sasl-auth.md#u-46326567541d)

**Uncertainties.**

- Whether ntresplen returned by Curl_ntlm_core_mk_ntlmv2_resp can exceed the buffer before the header write is not checked until after msnprintf, so a truncated header could precede the CURLE_TOO_LARGE error.
- DEBUGASSERT conditions assume size==64 and exact offsets; behavior in non-debug builds with unexpected sizes is not established.

<a id="u-46326567541d"></a>
### `Curl_auth_decode_ntlm_type2_message`

`CURLcode Curl_auth_decode_ntlm_type2_message(struct Curl_easy *data, const struct buf…` · [lib/vauth/ntlm.c:L335-L392][f2]

Validates a peer-supplied NTLM type-2 challenge and copies the fields the client needs into ntlm.

It first clears ntlm->flags, then rejects the message with an info log and CURLE_BAD_CONTENT_ENCODING if it is shorter than 32 bytes, lacks the 8-byte NTLMSSP signature, or does not carry the type-2 marker 0x02,0,0,0 at offset 8. On acceptance it reads the little-endian flags at offset 20 and the 8-byte challenge into ntlm->nonce. If the peer set NTLMFLAG_NEGOTIATE_TARGET_INFO it delegates to ntlm_decode_type2_target; any error there is logged and propagated unchanged after the failure info message. In DEBUG_ME builds it additionally prints flags and nonce to stderr. Returns CURLE_OK when parsing succeeded.

calls: [ntlm_decode_type2_target](r14-sasl-auth.md#u-a7a5faf280b5); uses: [ntlm.c-debug-print-helpers](r14-sasl-auth.md#u-4cc9e31eb284)

**Uncertainties.**

- The DEBUG_OUT block references a variable 'header' that is not visible in the shown parameters; this block is only compiled when DEBUG_ME is 1.

<a id="u-a7a5faf280b5"></a>
### `ntlm_decode_type2_target`

`static CURLcode ntlm_decode_type2_target(struct Curl_easy *data, const struct bufref …` · [lib/vauth/ntlm.c:L256-L288][f2]

Extracts the Target Information security buffer from a decoded NTLM type-2 message into ntlm.

It reads the little-endian 16-bit length at offset 40 and 32-bit offset at 44 only when the message is at least 48 bytes long. If the length is nonzero, it validates that the data lies entirely after offset 48 and within the message: an out-of-range or too-low offset logs an info message and returns CURLE_BAD_CONTENT_ENCODING. Otherwise it frees any previous ntlm->target_info and replaces it with a curlx_memdup copy; allocation failure returns CURLE_OUT_OF_MEMORY leaving target_info NULL. When the message is short or the length is zero, target_info_len is stored as 0 and CURLE_OK is returned without allocating.

calls: [Curl_auth_decode_ntlm_type2_message](r14-sasl-auth.md#u-46326567541d)

**Uncertainties.**

- Behavior when target_info_offset plus target_info_len overflows unsigned arithmetic is not guarded in the visible code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vauth/cleartext.c
[f2]: ../../../../../../eval/curl-2c04412/lib/vauth/ntlm.c
[f3]: ../../../../../../eval/curl-2c04412/lib/vauth/gsasl.c
