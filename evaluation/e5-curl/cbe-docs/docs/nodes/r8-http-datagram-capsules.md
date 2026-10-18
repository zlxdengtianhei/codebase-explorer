# HTTP Datagram Capsules

**Capability.** Encapsulates and decapsulates UDP datagrams as HTTP Datagram (CONNECT-UDP) capsules, with QUIC-style varint coding and non-consuming bufq peek/decode primitives.

Use this subtree when working with MASQUE/CONNECT-UDP datagram framing. The encap path appends complete capsules to a send bufq; the process path extracts one datagram payload from a receive bufq.

**Depends on.**

- [Poll/Select and Waiting](r8-poll-wait-api.md) · model-inferred · 0 edge(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Units (7)

<a id="u-3d10c43d5bf7"></a>
### `Curl_capsule_encap_udp_datagram`

`CURLcode Curl_capsule_encap_udp_datagram(struct bufq *q, const void *buf, size_t blen)` · [lib/vquic/capsule.c:L166-L189][f1]

Appends a complete UDP datagram capsule (header + payload) to a send bufq.

Builds the header via capsule_encap_udp_hdr; a zero length returns CURLE_FAILED_INIT. Writes header then payload with Curl_bufq_write; a short write yields CURLE_WRITE_ERROR, and CURLE_AGAIN maps to CURLE_WRITE_ERROR because a partially written capsule cannot be resumed here. Other errors propagate.

calls: [capsule_encap_udp_hdr](r8-http-datagram-capsules.md#u-5c2c073e0e30), [Curl_bufq_write](r15-bufq-stream-api.md#u-2bc159f60789)

**Uncertainties.**

- If the payload write fails after the header was buffered, the bufq holds a header without payload; recovery is the caller's concern

<a id="u-7cd3440e2d5a"></a>
### `Curl_capsule_process_udp_raw`

`size_t Curl_capsule_process_udp_raw(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/capsule.c:L191-L305][f1]

Extracts one UDP datagram from a receive bufq of HTTP Datagram capsules, copying the payload into buf (capacity len); returns the payload size with *err=CURLE_OK, or 0 with *err set.

Validation order: len==0 -> CURLE_BAD_FUNCTION_ARGUMENT; empty bufq or unpeekable first byte -> CURLE_AGAIN; nonzero capsule type -> log, skip 1 byte, CURLE_RECV_ERROR; varint decode -> CURLE_AGAIN or CURLE_RECV_ERROR propagated; nonzero context ID -> log, skip through that byte, CURLE_RECV_ERROR; capsule length 0 -> skip header, CURLE_RECV_ERROR; capsule_length-1 exceeding SIZE_MAX-offset -> CURLE_RECV_ERROR without consuming; payload larger than len -> skip whole capsule, CURLE_RECV_ERROR. When header+payload are not yet buffered: full bufq means the capsule can never complete -> CURLE_RECV_ERROR; else CURLE_AGAIN. On success skips the header; zero payload returns 0 with CURLE_OK; otherwise Curl_bufq_read copies the payload and a short read or error yields CURLE_RECV_ERROR.

calls: [capsule_decode_varint_at](r8-http-datagram-capsules.md#u-1d2a52746e51), [Curl_bufq_peek](r15-bufq-stream-api.md#u-029ea0a9d37a), [Curl_bufq_peek_at](r15-bufq-stream-api.md#u-4e4dc2e518ad), [Curl_bufq_skip](r15-bufq-stream-api.md#u-07cba12be06f), [Curl_bufq_read](r15-bufq-stream-api.md#u-aec66eaec7fc), [Curl_bufq_is_empty](r15-bufq-stream-api.md#u-972cf7343ce0), [Curl_bufq_len](r15-bufq-stream-api.md#u-976ebd055011), [Curl_bufq_is_full](r15-bufq-stream-api.md#u-d0e22f7ff218), [lib/curl_trc.c:Curl_infof](r1-trace-logging.md#u-b6145e5eb5c9)

**Uncertainties.**

- Whether skipping a capsule larger than the buffer capacity behaves correctly across a multi-chunk bufq is not shown in this file

<a id="u-1d2a52746e51"></a>
### `capsule_decode_varint_at`

`static CURLcode capsule_decode_varint_at(struct bufq *recvbufq, size_t offset, uint64…` · [lib/vquic/capsule.c:L112-L140][f1]

Decodes a QUIC-style variable-length integer at an offset in a bufq without consuming data.

The first byte's top two bits select length 1 << (first >> 6) (1, 2, 4 or 8 bytes); the low six bits seed the value. Each continuation byte is peeked at offset+i; CURLE_AGAIN from any peek propagates so callers can wait for more data; other errors propagate too. On success writes *pvalue and *pconsumed (the byte count).

calls: [capsule_peek_u8](r8-http-datagram-capsules.md#u-1542e5b9f1ae)

<a id="u-5c2c073e0e30"></a>
### `capsule_encap_udp_hdr`

`UNITTEST size_t capsule_encap_udp_hdr(uint8_t *hdr, size_t hdrlen, size_t payload_len)` · [lib/vquic/capsule.c:L153-L164][f1]

Writes an HTTP Datagram capsule header: type byte 0, a varint of payload_len + 1, and a zero context ID byte.

Requires hdrlen >= HTTP_CAPSULE_HEADER_MAX_SIZE (DEBUGASSERT and a runtime check returning 0 otherwise). Returns header bytes written, or 0 on error.

calls: [capsule_encode_varint_buf](r8-http-datagram-capsules.md#u-f5a4efcf1040)

**Uncertainties.**

- Length encodes payload_len + 1; a payload_len of SIZE_MAX would overflow, unchecked

<a id="u-f5a4efcf1040"></a>
### `capsule_encode_varint_buf`

`static size_t capsule_encode_varint_buf(uint8_t *buf, uint64_t value)` · [lib/vquic/capsule.c:L71-L97][f1]

Encodes a value as a QUIC-style variable-length integer into a buffer that must hold at least 8 bytes.

A DEBUGASSERT bounds the value to <= 0x3FFFFFFFFFFFFFFF. Selection: <= 0x3F -> 1 byte; <= 0x3FFF -> 2 bytes; <= 0x3FFFFFFF -> 4 bytes; else 8 bytes. Wider forms mask the value, OR the length marker (0x4000, 0x80000000, 0xC000000000000000) into the top bits, byte-swap via ntohs/ntohl/capsule_ntohll and memcpy into the buffer. Returns bytes written.

calls: [capsule_ntohll](r8-http-datagram-capsules.md#u-a5b57d21ea9b)

**Uncertainties.**

- Release builds have no runtime bound check; oversized values are silently masked

<a id="u-a5b57d21ea9b"></a>
### `capsule_ntohll`

`static uint64_t capsule_ntohll(uint64_t value)` · [lib/vquic/capsule.c:L45-L53][f1]

Converts a 64-bit value from network byte order to host byte order.

On big-endian it returns the value unchanged; with GCC/Clang on little-endian it uses __builtin_bswap64; otherwise a union-based ntohl swap of two 32-bit halves.

<a id="u-1542e5b9f1ae"></a>
### `capsule_peek_u8`

`static CURLcode capsule_peek_u8(struct bufq *recvbufq, size_t offset, uint8_t *pbyte)` · [lib/vquic/capsule.c:L99-L110][f1]

Peeks one byte at a given offset in a bufq without consuming it.

Returns CURLE_AGAIN if Curl_bufq_peek_at fails or yields zero length; otherwise stores peek[0] in *pbyte and returns CURLE_OK.

calls: [Curl_bufq_peek_at](r15-bufq-stream-api.md#u-4e4dc2e518ad)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/capsule.c
