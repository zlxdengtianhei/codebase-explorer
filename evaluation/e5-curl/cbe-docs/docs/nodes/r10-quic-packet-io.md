# QUIC UDP Packet I/O

**Capability.** Owns sending and receiving QUIC datagrams: buffered send with flush and datagram-size splitting, GSO and non-GSO send paths, filter-tunneled sends, and batched receive via recvmmsg/recvmsg_x/recvmsg/recvfrom with ECN and UDP-GRO extraction.

Use this child for the UDP boundary of QUIC: compile-time syscall strategy selection, GSO fallback, and ancillary-data parsing from received messages.

Parent: [QUIC / HTTP-3 Transport](r10-quic-transport.md)

## Units (15)

<a id="u-c4d902c6d36d"></a>
### `Curl_vquic_flush`

`CURLcode Curl_vquic_flush(struct Curl_cfilter *cf, struct Curl_easy *data, struct cf_…` · [lib/vquic/vquic.c:L469-L514][f1]

Drains the context's sendbuf, sending buffered QUIC data either directly on the UDP socket or through a lower filter for tunneled QUIC.

Each iteration peeks the buffer; when a tail split is active (split_len set) it uses split_gsolen and caps the length at split_len. With a valid socket it calls vquic_send_packets; otherwise, if the buffer spans multiple datagrams it uses send_packet_no_gso_cf, else a plain Curl_conn_cf_send. On any result including CURLE_AGAIN it skips the sent bytes from the bufq and decreases split_len by the sent amount, then returns the error; success loops until the bufq is empty and returns CURLE_OK. Note that on CURLE_AGAIN the sent progress is retained before returning.

calls: [vquic_send_packets](r10-quic-packet-io.md#u-4e8ba842a00c), [send_packet_no_gso_cf](r10-quic-packet-io.md#u-cf9f2d80428c)

**Uncertainties.**

- Behavior when a lower-filter send reports sent > blen is not visible; skip could over-consume the bufq.

<a id="u-98014bd1c245"></a>
### `Curl_vquic_recv_packets`

`CURLcode Curl_vquic_recv_packets(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/vquic.c:L1008-L1035][f1]

Public entry that receives QUIC packets using the best available system call, chosen at compile time: recvmmsg, Apple recvmsg_x, recvmsg, or recvfrom.

On success (no error) it updates the context: if the first byte has not yet been seen and bytes were read, records got_first_byte with first_byte_at = last_op, and always refreshes last_io from last_op. Errors, including the CURLE_AGAIN returned by the receive helpers, propagate unchanged without touching last_io.

calls: [recvmmsg_packets](r10-quic-packet-io.md#u-759351dd1d9c), [recvmsg_x_packets](r10-quic-packet-io.md#u-4f1ed54a6fb9), [recvmsg_packets](r10-quic-packet-io.md#u-bca16e002968), [recvfrom_packets](r10-quic-packet-io.md#u-a73043765f06)

<a id="u-8c9f5003e82f"></a>
### `Curl_vquic_send`

`CURLcode Curl_vquic_send(struct Curl_cfilter *cf, struct Curl_easy *data, struct cf_q…` · [lib/vquic/vquic.c:L516-L521][f1]

Sets the datagram size (gsolen) used for the buffered data and triggers a flush of the sendbuf.

Returns whatever Curl_vquic_flush returns.

calls: [Curl_vquic_flush](r10-quic-packet-io.md#u-c4d902c6d36d)

<a id="u-409f61c7cc52"></a>
### `Curl_vquic_send_tail_split`

`CURLcode Curl_vquic_send_tail_split(struct Curl_cfilter *cf, struct Curl_easy *data, …` · [lib/vquic/vquic.c:L523-L535][f1]

Sends buffered data whose tail has a different datagram size than the head.

Marks the buffer prefix (total length minus tail_len) to be sent with gsolen, and sets the context gsolen to tail_gsolen so the flush uses the tail size for the remainder. Asserts in debug builds that the buffer exceeds tail_len, traces the split, and returns the flush result.

calls: [Curl_vquic_flush](r10-quic-packet-io.md#u-c4d902c6d36d)

<a id="u-fc5b262fdf26"></a>
### `do_sendmsg`

`static CURLcode do_sendmsg(struct Curl_cfilter *cf, struct Curl_easy *data, struct cf…` · [lib/vquic/vquic.c:L169-L255][f1]

Apple sendmsg_x variant that batches GSO-sized QUIC packets into up to 64 msghdr_x records and sends them with one SYS_sendmsg_x syscall per batch.

Empty input returns OK immediately; gsolen of 0 or exceeding pktlen is clamped to pktlen so the payload counts as one packet. The syscall retries only on EINTR. On EAGAIN it returns CURLE_AGAIN if nothing was sent yet, otherwise CURLE_OK with bytes sent so far. Other errnos except EMSGSIZE log a failure and return CURLE_SEND_ERROR; EMSGSIZE (e.g. PMTUD) treats the whole batch as sent, dropping the packets. A batch yielding zero sent packets ends the loop with CURLE_OK if prior progress was made, else CURLE_AGAIN. Partial batches stop the loop. *psent always receives the byte count.

**Notes.**

- side_effect: Packets rejected with EMSGSIZE are intentionally discarded and reported as sent.

uses: [msghdr_x][f1]

**Uncertainties.**

- Sent bytes are summed from msg_iov entries for pkts_sent packets, assuming the kernel fills iov entries in order; this is not verifiable here.

<a id="u-48033ece32cd"></a>
### `lib/vquic/vquic.c:do_sendmsg`

`static CURLcode do_sendmsg(struct Curl_cfilter *cf, struct Curl_easy *data, struct cf…` · [lib/vquic/vquic.c:L265-L368][f1]

Sends one QUIC datagram (possibly a GSO aggregate) on the UDP socket.

With HAVE_SENDMSG it builds a single-iov msghdr; on Linux with UDP_SEGMENT and pktlen > gsolen it attaches a UDP_SEGMENT cmsg carrying the segment size so the kernel fragments the GRO-style aggregate. sendmsg retries only on EINTR. If conversion of the return fails: EAGAIN returns CURLE_AGAIN with *psent 0; EMSGSIZE pretends the whole datagram was sent (PMTUD loss); EIO with a GSO aggregate logs, permanently sets qctx->no_gso = TRUE, and retries via send_packet_no_gso; any other errno (and EIO without GSO) fails with CURLE_SEND_ERROR. If fewer bytes than pktlen were reported sent, it returns CURLE_SEND_ERROR. Without HAVE_SENDMSG it falls back to swrite with the same EAGAIN/EMSGSIZE/SEND_ERROR handling. Traces via VQUIC_SEND_METHOD.

**Notes.**

- side_effect: A GSO EIO failure flips qctx->no_gso to TRUE for the remainder of the connection.

calls: [send_packet_no_gso](r10-quic-packet-io.md#u-6d96d3b16b49)

**Uncertainties.**

- The final trace label depends on the CURLVERBOSE-time VQUIC_SEND_METHOD macro, which differs per platform.

<a id="u-a73043765f06"></a>
### `recvfrom_packets`

`static CURLcode recvfrom_packets(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/vquic.c:L941-L1005][f1]

Fallback QUIC receive loop using recvfrom when no msg-based API exists, one 64 KiB buffer, one packet per call.

Retries on EINTR and EMSGSIZE; EAGAIN returns accumulated reads (traced); pre-connect ECONNREFUSED logs the peer and returns CURLE_COULDNT_CONNECT; other errors return CURLE_RECV_ERROR. Every datagram increments the packet count; zero-length datagrams contribute nothing to the byte total and no recv_cb invocation; non-empty datagrams call recv_cb with the peer address and ECN fixed at 0, propagating callback errors. *pnread receives the byte total.

**Uncertainties.**

- No GRO or ECN support is possible on this path, so multi-datagram aggregates are delivered as one packet with gso = length.

<a id="u-759351dd1d9c"></a>
### `recvmmsg_packets`

`static CURLcode recvmmsg_packets(struct Curl_cfilter *cf, struct Curl_easy *data, str…` · [lib/vquic/vquic.c:L630-L739][f1]

Receives up to max_pkts QUIC packets in batches with recvmmsg on Linux.

Borrows a transfer sockbuf of MMSG_NUM (16 with UDP_GRO, else 64) buffers of up to 1500 bytes each (64*1500 with GRO). The recvmmsg call retries on EINTR and EMSGSIZE only. On EAGAIN it returns with the bytes read so far (not an error); ECONNREFUSED before the filter is connected logs the refused remote via Curl_cf_socket_peek and returns CURLE_COULDNT_CONNECT; other errors log and return CURLE_RECV_ERROR. Per message: zero-length datagrams count as a packet but are skipped; otherwise ECN and GRO size are read from ancillary data (gso_size defaults to the message length), the recv_cb is invoked with buffer, length, gso, peer address, and ECN — its error aborts and propagates — and pkts advances by the number of contained datagrams. The loop continues until max_pkts is reached. Always releases the borrowed buffer and reports total bytes via *pnread.

calls: [vquic_msghdr_get_ecn](r10-quic-packet-io.md#u-55328ef61406), [vquic_msghdr_get_udp_gro](r10-quic-packet-io.md#u-5e65c031b908)

**Uncertainties.**

- recv_cb's semantics (which CURLcode values are fatal vs. ignored) are defined by its caller, not shown here.
- Datagrams larger than MSG_BUF_SIZE would be truncated by recvmsg semantics; that truncation is not handled explicitly.

<a id="u-bca16e002968"></a>
### `recvmsg_packets`

`static CURLcode recvmsg_packets(struct Curl_cfilter *cf, struct Curl_easy *data, stru…` · [lib/vquic/vquic.c:L853-L938][f1]

Single-datagram QUIC receive loop using recvmsg, one 64 KiB stack buffer.

The msghdr is fully re-initialized before every call because some platforms modify iov_len; ancillary space holds one int cmsg. recvmsg retries on EINTR and EMSGSIZE. EAGAIN returns accumulated reads as a non-error; pre-connect ECONNREFUSED logs the peer and returns CURLE_COULDNT_CONNECT; other errors return CURLE_RECV_ERROR. Zero-length datagrams count as packets but are skipped; otherwise ECN and UDP GRO size are extracted (gso_size defaults to nread), recv_cb is invoked and its error propagates, and pkts advances by datagrams contained. *pnread receives total bytes read.

calls: [vquic_msghdr_get_ecn](r10-quic-packet-io.md#u-55328ef61406), [vquic_msghdr_get_udp_gro](r10-quic-packet-io.md#u-5e65c031b908)

<a id="u-4f1ed54a6fb9"></a>
### `recvmsg_x_packets`

`static CURLcode recvmsg_x_packets(struct Curl_cfilter *cf, struct Curl_easy *data, st…` · [lib/vquic/vquic.c:L743-L850][f1]

Apple variant of batched QUIC receive using SYS_recvmsg_x with up to 64 msghdr_x records of 2048-byte buffers.

Mirrors recvmmsg_packets' error handling: retry on EINTR/EMSGSIZE, EAGAIN ends the loop with accumulated reads, pre-connect ECONNREFUSED yields CURLE_COULDNT_CONNECT after logging the peer, and other errors yield CURLE_RECV_ERROR. Zero-length datagrams (msg_datalen 0) count as packets but are skipped. ECN is read by casting the msghdr_x to struct msghdr; gso_size is always the datagram length, so each message counts as one packet. Buffers come from the multi-transfer sockbuf pool and are always released; *pnread gets the byte total.

calls: [vquic_msghdr_get_ecn](r10-quic-packet-io.md#u-55328ef61406)

**Uncertainties.**

- Casting struct msghdr_x to struct msghdr for ECN parsing assumes layout-compatible prefixes; the extra trailing field is ignored.

<a id="u-6d96d3b16b49"></a>
### `send_packet_no_gso`

`static CURLcode send_packet_no_gso(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/vquic.c:L372-L398][f1]

Sends a GSO aggregate as individual datagrams when kernel segmentation is unavailable.

Iterates the payload in gsolen-sized steps (last chunk may be shorter) and calls do_sendmsg for each with gsolen equal to the chunk length, accumulating bytes into *psent. The first error from do_sendmsg aborts the loop and is returned, leaving *psent at the bytes sent so far.

calls: [lib/vquic/vquic.c:do_sendmsg](r10-quic-packet-io.md#u-48033ece32cd)

<a id="u-cf9f2d80428c"></a>
### `send_packet_no_gso_cf`

`static CURLcode send_packet_no_gso_cf(struct Curl_cfilter *cf, struct Curl_easy *data…` · [lib/vquic/vquic.c:L402-L437][f1]

Sends QUIC datagrams through a non-UDP lower filter, such as a CONNECT-UDP proxy tunnel, preserving packet boundaries.

Splits the payload at gsolen boundaries and calls Curl_conn_cf_send on cf->next once per datagram. Any lower-filter result, including CURLE_AGAIN, is returned immediately with bytes sent so far in *psent; a partial datagram send (sent != len) cannot be resumed and yields CURLE_SEND_ERROR.

**Uncertainties.**

- Behavior when the lower filter sends more than requested is not guarded and would inflate *psent.

<a id="u-55328ef61406"></a>
### `vquic_msghdr_get_ecn`

`static uint8_t vquic_msghdr_get_ecn(struct msghdr *msg, int family)` · [lib/vquic/vquic.c:L574-L623][f1]

Extracts the ECN bits from a received message's ancillary data.

For AF_INET it scans cmsgs for IPPROTO_IP with type IP_RECVTOS (Apple) or IP_TOS (others) and returns the byte at CMSG_DATA masked with IPTOS_ECN_MASK. For AF_INET6 it looks for IPPROTO_IPV6/IPV6_TCLASS, copies an int-sized tos, and returns its ECN-masked low byte. Unknown families or missing cmsgs return 0. In builds without the required headers the macro expands to constant 0.

**Uncertainties.**

- For IPv6 it copies sizeof(int) bytes even though the value is later used as a byte; kernel padding beyond the ECN byte is assumed zero.

<a id="u-5e65c031b908"></a>
### `vquic_msghdr_get_udp_gro`

`static size_t vquic_msghdr_get_udp_gro(struct msghdr *msg)` · [lib/vquic/vquic.c:L539-L565][f1]

Extracts the UDP GRO segment size from a received message's ancillary data.

On Linux with UDP_GRO it scans the cmsg list for SOL_UDP/UDP_GRO and copies the int gso_size; otherwise (and when not found) returns 0. Compiled only when sendmmsg/sendmsg is available and Apple msg_x is not. Includes pragmas to suppress musl-related CMSG_NXTHDR warnings under clang.

**Uncertainties.**

- Whether the kernel returns a signed or unsigned gso_size is not constrained here; the value is cast to size_t.

<a id="u-4e8ba842a00c"></a>
### `vquic_send_packets`

`static CURLcode vquic_send_packets(struct Curl_cfilter *cf, struct Curl_easy *data, s…` · [lib/vquic/vquic.c:L439-L467][f1]

Dispatches one send of a QUIC packet buffer to the socket, choosing the strategy.

In DEBUGBUILD with a positive wblock_percent it draws a random byte via Curl_rand and, exceeding the threshold, simulates blocking by returning CURLE_AGAIN with *psent 0. If GSO is disabled and the payload spans multiple datagrams (pktlen > gsolen), it sends via send_packet_no_gso, otherwise via do_sendmsg. On success it stamps qctx->last_io with qctx->last_op; errors leave last_io untouched.

calls: [do_sendmsg](r10-quic-packet-io.md#u-fc5b262fdf26), [lib/vquic/vquic.c:do_sendmsg](r10-quic-packet-io.md#u-48033ece32cd), [send_packet_no_gso](r10-quic-packet-io.md#u-6d96d3b16b49)

**Uncertainties.**

- The random blocking simulation only affects DEBUGBUILD binaries.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/vquic/vquic.c
