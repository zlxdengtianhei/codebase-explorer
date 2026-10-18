# TLS Session Serializer

**Capability.** Owns backend-independent (de)serialization of TLS sessions into tagged big-endian dynbuf form, built on byte-order packing primitives.

Use this child when touching how TLS sessions are stored in or read from the session cache. Backends such as wolfSSL feed their sessions through pack/unpack.

**Depended on by.**

- [wolfSSL Session Reuse](r10-wolfssl-session-cache.md) · model-inferred · 0 edge(s)

Parent: [wolfSSL TLS Backend](r10-tls-wolfssl.md)

## Units (3)

<a id="u-399646ccd2af"></a>
### `vtls_spack-width-helpers`

`static CURLcode spack_enc8(struct dynbuf *buf, uint8_t b)` · [lib/vtls/vtls_spack.c:L43-L46][f1]

Byte-order packing primitives used by the session serializer.

The enc functions append big-endian 8-, 16-, 32-, or 64-bit values (enc8 a raw byte) to a dynbuf, propagating the curlx_dyn_addn result. The dec functions require that many bytes remaining between *src and end, returning CURLE_READ_ERROR when short; otherwise they assemble the big-endian value and advance *src. str16/data16 variants first write/read a 16-bit length: encoding rejects lengths above UINT16_MAX with CURLE_BAD_FUNCTION_ARGUMENT; decoding checks remaining bytes, allocates a null-terminated copy with curlx_memdup0, advances *src, and returns CURLE_OUT_OF_MEMORY only if allocation fails (for decdata16, *val_len is set to the decoded length).

<a id="u-14a6cd92ae40"></a>
### `Curl_ssl_session_pack`

`CURLcode Curl_ssl_session_pack(struct Curl_easy *data, struct Curl_ssl_session *s, st…` · [lib/vtls/vtls_spack.c:L185-L234][f1]

Serializes a TLS session into a dynbuf as tagged big-endian fields, propagating the first failing helper result.

Mandatory fields are the version byte, the session ticket (sdata) as data16, the IETF TLS id as 16-bit, and valid_until as 64-bit; valid_until below 0 is rejected with CURLE_BAD_FUNCTION_ARGUMENT. Optional fields are emitted only when present: ALPN string (non-NULL), EARLYDATA as 32-bit (rejected with CURLE_BAD_FUNCTION_ARGUMENT when above UINT32_MAX), SECTRUST flag byte when sectrust_verified, and QUIC transport parameters as data16 when set. On any error it logs via CURL_TRC_SSLS and returns the error; the buffer may contain partial output in that case.

**Uncertainties.**

- Whether partial dynbuf contents are cleared by the caller on error is not visible here.

<a id="u-05625ca705ef"></a>
### `Curl_ssl_session_unpack`

`CURLcode Curl_ssl_session_unpack(struct Curl_easy *data, const void *bufv, size_t buf…` · [lib/vtls/vtls_spack.c:L236-L334][f1]

Parses a packed session buffer into a newly allocated Curl_ssl_session, or fails without setting *ps.

It first requires a version byte equal to CURL_SPACK_VERSION (mismatch → CURLE_READ_ERROR); allocation failure yields CURLE_OUT_OF_MEMORY. It then loops over tag bytes until the end: ALPN (string16, freeing a prior value), EARLYDATA (32-bit), IETF_ID (16-bit), QUICTP and TICKET (data16, freeing prior buffers before replacing), VALID_UNTIL (64-bit cast to curl_off_t), SECTRUST (sets the flag), and an unknown tag which aborts with CURLE_READ_ERROR. Any decode error logs via CURL_TRC_SSLS and destroys the partially built session with Curl_ssl_session_destroy; on success *ps receives the session.

**Uncertainties.**

- Duplicate tags are accepted with the later occurrence winning; whether this is intended is not stated in the source.
- Casting VALID_UNTIL from uint64_t to curl_off_t may overflow on platforms with narrower curl_off_t; this is not checked in the code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vtls/vtls_spack.c
