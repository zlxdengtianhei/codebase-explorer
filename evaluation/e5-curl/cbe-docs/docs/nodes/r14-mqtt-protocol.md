# MQTT Protocol Handler

**Capability.** Owns the MQTT protocol implementation: connection state setup, packet encoding/decoding (CONNECT, SUBSCRIBE, PUBLISH, DISCONNECT, PING), the DO/DOING state machine, receive buffering, and the protocol vtable wiring including the MQTTS TLS phase.

Use this subtree to follow an MQTT transfer from mqtt_do through mqtt_doing's receive state machine to mqtt_done. Packet builders share mqtt_encode_len and mqtt_send/flush, and incoming data flows through mqtt_recv_atleast/consume.

**Depends on.**

- [Easy Handle Lifecycle & Transfers](r14-core-easy-lifecycle.md) · graph-confirmed · 13 edge(s)
- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 28 edge(s)
- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) · graph-only · 27 edge(s)

Parent: [curl Codebase](r14-curl-codebase.md)

## Units (30)

<a id="u-2010b909753a"></a>
### `mqtt-c-header-and-types`

`enum mqttstate` · [lib/mqtt.c:L62-L74][f1]

This module region holds the license header, includes, MQTT packet-type and length macros, the meta-handle keys, the mqttstate enum, the per-connection struct mqtt_conn, and the per-transfer struct MQTT.

mqtt_conn tracks the receiver state machine (state plus nextstate to enter once the remaining-length field is decoded) and an incrementing packetid. struct MQTT carries the dynbuf send queue for unwritten packet tails, the receive accumulation buffer, byte counters npacket and remaining_length, a four-byte header scratch buffer pkt_hd, the last-activity timestamp, the first byte of the in-flight packet, and a pingsent flag. These types underpin every state-machine function in the file.

**Notes.**

- field: mqtt_conn.nextstate is consumed by the receiver after decoding the variable-length remaining-length field, deferring the packet-type state choice.
- contract: CURL_META_MQTT_EASY and CURL_META_MQTT_CONN are the meta keys under which struct MQTT and struct mqtt_conn attach to the easy handle and connection.

<a id="u-4795f1c80d15"></a>
### `mqtt-c-protocol-tables`

`group` · [lib/mqtt.c:L1010-L1013][f1]

The tail of mqtt.c defines the Curl_protocol vtables.

Curl_protocol_mqtt wires mqtt_setup_conn (setup_connection), mqtt_do (do_it), mqtt_done (done), mqtt_doing (doing), and mqtt_pollset (doing_pollset), leaving connecting, do_more, disconnect, write_resp, and all other slots ZERO_NULL. Curl_protocol_mqtts, compiled only under USE_SSL, is identical except that mqtts_connecting occupies the connecting slot to perform the TLS handshake; both tables share the same callbacks otherwise. These tables are how the multi interface reaches every state-machine function in this file.

uses: [mqtt_setup_conn](r14-mqtt-protocol.md#u-94b20d5fccff), [mqtt_do](r14-mqtt-protocol.md#u-9a2b7bb81dd7), [mqtt_done](r14-mqtt-protocol.md#u-4840bf1f968e), [mqtt_doing](r14-mqtt-protocol.md#u-a430c3e19a64), [mqtt_pollset](r14-mqtt-protocol.md#u-ff24a9fe7965), [mqtts_connecting](r14-mqtt-protocol.md#u-867983a0c13d)

<a id="u-30be02682352"></a>
### `add_client_id`

`static int add_client_id(const char *client_id, const size_t client_id_len, char *pkt…` · [lib/mqtt.c:L244-L253][f1]

Writes the client-ID field: returns 1 unless the length is exactly MQTT_CLIENTID_LEN (12); otherwise stores a 0x00,0x0C big-endian length prefix at pkt[start] and copies the 12 ID bytes after it, returning 0.

<a id="u-c6320e3ddf2e"></a>
### `add_passwd`

`static int add_passwd(const char *passwd, const size_t plen, char *pkt, const size_t …` · [lib/mqtt.c:L207-L223][f1]

Writes the password field of a CONNECT payload: returns 1 if plen exceeds 0xffff; otherwise ORs the password flag 0x40 into the connect-flags byte at remain_pos+8, stores the two-byte big-endian length at pkt[start], and copies the password after it, returning 0.

No bounds check of pkt beyond the copy; the caller sizes the packet.

<a id="u-549b2fdf97b6"></a>
### `add_user`

`static int add_user(const char *username, const size_t ulen, unsigned char *pkt, cons…` · [lib/mqtt.c:L226-L241][f1]

Writes the username field of a CONNECT payload: returns 1 if ulen exceeds 0xffff; otherwise sets the username flag 0x80 at remain_pos+8, stores the big-endian two-byte length at pkt[start], copies the username after it, and returns 0.

Same caller-side packet sizing dependency as add_passwd.

<a id="u-f51b26c1152f"></a>
### `init_connpack`

`static int init_connpack(char *packet, char *remain, int remain_pos)` · [lib/mqtt.c:L256-L283][f1]

Fills the fixed and variable header of a CONNECT packet: control byte MQTT_MSG_CONNECT, the pre-encoded remaining-length bytes copied from remain, then protocol name "MQTT" with a length prefix of 4, protocol level 0x04, CleanSession connect flag 0x02, and keep-alive bytes 0x00,0x3c (60 seconds).

Returns the offset just past the variable header (remain_pos + 10) for the caller to place the payload.

**Notes.**

- contract: The comment says 'keep-alive 0 = disabled' but the code writes 0x3c (60 seconds); follow the implementation.

<a id="u-76549549df16"></a>
### `mqstate`

`static void mqstate(struct Curl_easy *data, enum mqttstate state, enum mqttstate next…` · [lib/mqtt.c:L674-L692][f1]

The only state mutator: sets mqtt->state to the given state and, when the new state is MQTT_FIRST, also records nextstate for later use.

Fetches the connection mqtt_conn meta and returns silently if absent (DEBUGASSERT fires in debug builds). Under DEBUGBUILD it logs old state, new state, and next state using the statenames table (which exists only when DEBUGBUILD and CURLVERBOSE are both defined).

calls: [url.c-conn-meta-helpers](r7-connection-metadata.md#u-597937b418a7)

**Uncertainties.**

- statenames is guarded by DEBUGBUILD && CURLVERBOSE while the infof call is guarded only by DEBUGBUILD; in a DEBUGBUILD without CURLVERBOSE the logging would reference an undefined table, so the exact build flags that co-occur are not provable from this file alone.

<a id="u-20af1a526694"></a>
### `mqtt_conn_dtor`

`static void mqtt_conn_dtor(const void *key, size_t klen, void *entry)` · [lib/mqtt.c:L106-L111][f1]

Meta destructor for the connection's struct mqtt_conn: frees the entry and ignores the key arguments.

Registered by mqtt_setup_conn when attaching the connection meta.

<a id="u-b500baab33a3"></a>
### `mqtt_connect`

`static CURLcode mqtt_connect(struct Curl_easy *data)` · [lib/mqtt.c:L285-L374][f1]

Builds and sends the MQTT CONNECT packet, then unlinks the credentials from the easy handle regardless of outcome.

It computes the payload size from credentials (username, password) plus the fixed 12-byte client id, encodes the remaining length with mqtt_encode_len, allocates and zero-fills the packet, and fills the headers via init_connpack. It randomizes the client-id suffix via Curl_rand_alnum (its result overwrites any prior error), then appends client id, username (advance start_pwd by 2 for the length prefix), and password conditionally on presence. Failure conditions: packetlen above 0xFFFFFFF returns CURLE_WEIRD_SERVER_REPLY before allocating; allocation failure returns CURLE_OUT_OF_MEMORY; non-zero rc from add_client_id/add_user/add_passwd logs a failf and returns CURLE_WEIRD_SERVER_REPLY via the shared end path. On success it sends via mqtt_send. The packet is zeroed and freed at end, and Curl_creds_unlink always runs.

**Notes.**

- side_effect: Always clears data->state.creds with Curl_creds_unlink, success or failure.
- failure: Curl_rand_alnum's result is assigned over the previous result, so a random failure can mask an earlier error state.

calls: [mqtt_encode_len](r14-mqtt-protocol.md#u-d33fadf28e8c), [init_connpack](r14-mqtt-protocol.md#u-f51b26c1152f), [add_client_id](r14-mqtt-protocol.md#u-30be02682352), [add_user](r14-mqtt-protocol.md#u-549b2fdf97b6), [add_passwd](r14-mqtt-protocol.md#u-c6320e3ddf2e), [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

**Uncertainties.**

- The Curl_rand_alnum result overwriting the prior result looks unintended but its effect on success/failure reporting is a real boundary: a random-generation failure alone would not abort the connect since no check follows.

<a id="u-544e476f4ba1"></a>
### `mqtt_decode_len`

`static bool mqtt_decode_len(size_t *lenp, const unsigned char *buf, size_t buflen)` · [lib/mqtt.c:L634-L655][f1]

Decodes an MQTT variable-byte remaining length from buf.

Iterates up to buflen bytes while the continuation bit is set; returns TRUE (error) at a fifth byte (i == 4, bad size) and TRUE if the input ends with the continuation bit still set (truncated). On success stores the decoded value in *lenp and returns FALSE.

<a id="u-fc0bc589b390"></a>
### `mqtt_disconnect`

`static CURLcode mqtt_disconnect(struct Curl_easy *data)` · [lib/mqtt.c:L376-L379][f1]

Sends the two-byte DISCONNECT packet 0xe0 0x00 via mqtt_send, returning its result.

calls: [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

<a id="u-9a2b7bb81dd7"></a>
### `mqtt_do`

`static CURLcode mqtt_do(struct Curl_easy *data, bool *done)` · [lib/mqtt.c:L794-L812][f1]

DO-phase entry: resets per-transfer state and sends CONNECT.

Sets *done = FALSE unconditionally, returns CURLE_FAILED_INIT without mq, stamps lastTime, clears pingsent, and sends the CONNECT via mqtt_connect; a failure logs 'Error %d sending MQTT CONNECT request' and propagates. On success it moves the connection to MQTT_FIRST with nextstate MQTT_CONNACK and returns CURLE_OK.

calls: [mqtt_connect](r14-mqtt-protocol.md#u-b500baab33a3), [mqstate](r14-mqtt-protocol.md#u-76549549df16)

<a id="u-a430c3e19a64"></a>
### `mqtt_doing`

`static CURLcode mqtt_doing(struct Curl_easy *data, bool *done)` · [lib/mqtt.c:L859-L1010][f1]

The main receiving state machine, run while the connection is established.

Requires both metas or returns CURLE_FAILED_INIT; always clears *done first. It first flushes any queued sendbuf tail (returning early on error or while a short write leaves bytes queued, since CURLE_OK may still mean a short write), then runs mqtt_ping and likewise waits while sendbuf is non-empty. The state switch: MQTT_FIRST reads one byte into firstbyte (a recv error propagates; zero reads log 'Connection disconnected', set *done and return CURLE_RECV_ERROR), stamps lastTime, resets npacket, and falls through. MQTT_REMAINING_LENGTH reads continuation bytes into pkt_hd (up to 4); if the last byte still has the continuation bit set, or mqtt_decode_len rejects the encoding, it returns CURLE_WEIRD_SERVER_REPLY. For DISCONNECT and PINGRESP first bytes it rejects nonzero remaining_length or nonzero reserved low-nibble bits upfront as malformed. With a nonzero remaining length it transitions to mqtt->nextstate and waits; with zero length it returns to MQTT_FIRST, treating firstbyte DISCONNECT as *done = TRUE and PINGRESP as clearing pingsent and moving to MQTT_FIRST/MQTT_PUBWAIT. MQTT_CONNACK verifies the CONNACK; then a non-POST request subscribes and moves to MQTT_FIRST/MQTT_SUBACK, while a POST publishes and falls through to MQTT_POST_DRAIN, which waits for an empty sendbuf, then sends DISCONNECT via mqtt_disconnect and falls through to MQTT_DISCONNECT_DRAIN, completing (*done = TRUE) only once the DISCONNECT bytes are fully flushed. SUBACK/PUBWAIT/PUB_REMAIN delegate to mqtt_read_publish. The default state fails with 'State not handled yet' and *done = TRUE. CURLE_AGAIN is converted to CURLE_OK before returning.

**Notes.**

- failure: Reads of zero bytes, malformed headers, oversized length encodings, and unhandled states all terminate with *done = TRUE and an error code.
- condition: PUBLISH-then-DISCONNECT ordering is enforced by waiting for an empty sendbuf at each drain stage.

calls: [mqtt_flush](r14-mqtt-protocol.md#u-aad936b2c349), [mqtt_ping](r14-mqtt-protocol.md#u-e9bcf762a9cc), [mqtt_decode_len](r14-mqtt-protocol.md#u-544e476f4ba1), [mqstate](r14-mqtt-protocol.md#u-76549549df16), [mqtt_verify_connack](r14-mqtt-protocol.md#u-779251becf1e), [mqtt_subscribe](r14-mqtt-protocol.md#u-3c09a688aabd), [mqtt_publish](r14-mqtt-protocol.md#u-28ebf44e22dc), [mqtt_disconnect](r14-mqtt-protocol.md#u-fc0bc589b390), [mqtt_read_publish](r14-mqtt-protocol.md#u-f538c4cc54b5)

**Uncertainties.**

- In MQTT_REMAINING_LENGTH, recvbyte is compared after the loop even when the last recv returned an error or zero bytes; the guard !result && nread protects the continuation check, but the value of recvbyte in the nread==0 break path is a stale/indeterminate read whose exact behavior depends on Curl_xfer_recv contract not shown.

<a id="u-4840bf1f968e"></a>
### `mqtt_done`

`static CURLcode mqtt_done(struct Curl_easy *data, CURLcode status, bool premature)` · [lib/mqtt.c:L814-L825][f1]

Done-phase cleanup: ignores status and premature, and when the easy-handle MQTT state exists frees both dynbuf buffers.

Always returns CURLE_OK. The struct itself is freed later by the meta destructor mqtt_easy_dtor.

contract: [mqtt_easy_dtor](r14-mqtt-protocol.md#u-c79167c92109)

<a id="u-c79167c92109"></a>
### `mqtt_easy_dtor`

`static void mqtt_easy_dtor(const void *key, size_t klen, void *entry)` · [lib/mqtt.c:L96-L104][f1]

Meta destructor for the easy-handle struct MQTT: frees both dynbuf queues and the struct itself, ignoring the key arguments.

Returns nothing, so free errors cannot be reported.

calls: [curlx_dyn_free](r3-dynbuf.md#u-21f694d1bd8a)

<a id="u-d33fadf28e8c"></a>
### `mqtt_encode_len`

`static int mqtt_encode_len(char *buf, size_t len)` · [lib/mqtt.c:L190-L204][f1]

Encodes a size_t as the MQTT variable-byte remaining-length field into buf, up to four bytes: each iteration writes len % 0x80, sets the continuation bit 0x80 while more remains, and divides by 0x80.

Returns the number of bytes written; the loop caps i at 4, so lengths needing more than four bytes are silently truncated. buf must have room for four bytes.

**Uncertainties.**

- No error is signaled for a length too large for four bytes; callers must bound lengths themselves (mqtt_connect checks separately).

<a id="u-aad936b2c349"></a>
### `mqtt_flush`

`static CURLcode mqtt_flush(struct Curl_easy *data)` · [lib/mqtt.c:L158-L176][f1]

Drains the queued outgoing tail from sendbuf.

Returns CURLE_FAILED_INIT without mq and CURLE_OK when the queue is empty. Sends up to the whole queue via Curl_xfer_send; a send error propagates unchanged. On success it stamps lastTime, dumps the n sent bytes, and calls curlx_dyn_tail to keep only the unsent remainder (len - n), returning its result, so a partial write leaves the rest queued for later writability polling.

contract: [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

<a id="u-75f134d61e7e"></a>
### `mqtt_get_topic`

`static CURLcode mqtt_get_topic(struct Curl_easy *data, char **topic, size_t *topiclen)` · [lib/mqtt.c:L455-L471][f1]

Extracts the MQTT topic from the request URL path.

If the path is longer than one character it URL-decodes path+1 with Curl_urldecode (REJECT_CTRL) into topic/topiclen; if decoding succeeds but the topic exceeds 0xffff bytes it logs 'Too long MQTT topic' and returns CURLE_URL_MALFORMAT. A path of '/' or shorter logs 'No MQTT topic found' and returns CURLE_URL_MALFORMAT. The decode result is returned otherwise.

calls: [Curl_urldecode](r7-string-escape-utils.md#u-0db7582a0fb5)

<a id="u-e9bcf762a9cc"></a>
### `mqtt_ping`

`static CURLcode mqtt_ping(struct Curl_easy *data)` · [lib/mqtt.c:L828-L857][f1]

Sends a keep-alive PINGREQ when idle.

Requires both metas or returns CURLE_FAILED_INIT. Only when state is MQTT_FIRST, no ping is outstanding, and upkeep_interval_ms is positive: it measures the time since mq->lastTime, and when the elapsed diff exceeds upkeep_interval_ms it sends the two-byte 0xC0 0x00 packet via mqtt_send, sets pingsent = TRUE only on send success, and logs. Returns CURLE_OK unless mqtt_send failed.

calls: [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

<a id="u-ff24a9fe7965"></a>
### `mqtt_pollset`

`static CURLcode mqtt_pollset(struct Curl_easy *data, struct easy_pollset *ps)` · [lib/mqtt.c:L181-L188][f1]

Pollset callback for the DOING/PROTOCONNECT phases: if the easy-handle MQTT state exists and sendbuf is non-empty it registers the first socket for writability so queued packet bytes can drain; otherwise it registers the socket for readability to await replies.

A missing mq yields the read-side registration. Assumes data->conn is set.

contract: [mqtt_flush](r14-mqtt-protocol.md#u-aad936b2c349)

<a id="u-28ebf44e22dc"></a>
### `mqtt_publish`

`static CURLcode mqtt_publish(struct Curl_easy *data)` · [lib/mqtt.c:L565-L631][f1]

Builds and sends a PUBLISH packet from data->set.postfields.

Returns CURLE_BAD_FUNCTION_ARGUMENT when there is no payload; when postfieldsize does not fit size_t, a positive value is rejected and a non-positive value falls back to strlen(payload). Gets the topic (fail path frees pkt and topic), rejects sizes where (SIZE_MAX - topiclen - 2) < payloadlen with CURLE_TOO_LARGE, computes remaininglength = payloadlen + 2 + topiclen, rejects remaininglength above MAX_MQTT_MESSAGE_SIZE minus encoding overhead, and mallocs the packet (CURLE_OUT_OF_MEMORY on failure). It assembles control byte, encoded remaining length, big-endian topic length, topic, and payload, then sends via mqtt_send.

calls: [mqtt_get_topic](r14-mqtt-protocol.md#u-75f134d61e7e), [mqtt_encode_len](r14-mqtt-protocol.md#u-d33fadf28e8c), [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

<a id="u-f538c4cc54b5"></a>
### `mqtt_read_publish`

`static CURLcode mqtt_read_publish(struct Curl_easy *data, bool *done)` · [lib/mqtt.c:L694-L792][f1]

Handles the data phase after the packet header: SUBACK completion and PUBLISH body download.

Requires both metas or returns CURLE_FAILED_INIT. In MQTT_SUBACK_COMING it verifies the SUBACK and, on success, returns to MQTT_FIRST/MQTT_PUBWAIT. In MQTT_SUBACK/MQTT_PUBWAIT it dispatches on the buffered firstbyte: PUBLISH moves to MQTT_PUB_REMAIN, SUBACK moves to MQTT_SUBACK_COMING and falls into that label immediately, DISCONNECT sets *done = TRUE and ends, anything else is CURLE_WEIRD_SERVER_REPLY. For PUBLISH it enforces data->set.max_filesize against remaining_length (CURLE_FILESIZE_EXCEEDED), records the download size, resets bytecount, and sets mq->npacket = remaining_length, then falls through to MQTT_PUB_REMAIN: it reads up to min(npacket, 4KB) via Curl_xfer_recv — CURLE_AGAIN propagates to the caller (logged), zero reads report 'server disconnected' as CURLE_PARTIAL_FILE, and Curl_client_write failures propagate. After each chunk it decrements npacket and, at zero, returns to MQTT_FIRST/MQTT_PUBWAIT. Any other state is an illegal-state assert and CURLE_WEIRD_SERVER_REPLY.

**Notes.**

- side_effect: Updates mq->lastTime after each received chunk and sets data->req.size/bytecount and the progress download size.

calls: [mqtt_verify_suback](r14-mqtt-protocol.md#u-60c62c7410da), [mqstate](r14-mqtt-protocol.md#u-76549549df16)

**Uncertainties.**

- Curl_client_write is invoked with the raw stack buffer; any reassembly or per-message framing beyond byte counting is not visible here.

<a id="u-7726765abc25"></a>
### `mqtt_recv_atleast`

`static CURLcode mqtt_recv_atleast(struct Curl_easy *data, size_t nbytes)` · [lib/mqtt.c:L381-L406][f1]

Ensures at least nbytes are buffered in mq->recvbuf, reading more only when needed.

Returns CURLE_FAILED_INIT without mq. If fewer bytes are buffered, it reads the deficit (asserted to fit a 1024-byte stack buffer) via Curl_xfer_recv; a recv error propagates, zero bytes read is EOF returning CURLE_RECV_ERROR, and dynbuf append failure returns CURLE_OUT_OF_MEMORY. After possibly one read, it returns CURLE_OK if the buffer now holds nbytes, otherwise CURLE_AGAIN — so a single call performs at most one recv attempt.

contract: [mqtt_recv_consume](r14-mqtt-protocol.md#u-d691c54c029b)

<a id="u-d691c54c029b"></a>
### `mqtt_recv_consume`

`static void mqtt_recv_consume(struct Curl_easy *data, size_t nbytes)` · [lib/mqtt.c:L408-L419][f1]

Consumes nbytes from the front of mq->recvbuf: asserts mq exists (and returns without action if not), then either resets the buffer entirely when it holds nbytes or fewer, or trims it with curlx_dyn_tail to keep the unconsumed tail.

<a id="u-10eef5d77808"></a>
### `mqtt_send`

`static CURLcode mqtt_send(struct Curl_easy *data, const char *buf, size_t len)` · [lib/mqtt.c:L135-L155][f1]

Sends one MQTT packet over the transfer layer and queues any unwritten tail.

Fetches the easy-handle struct MQTT and returns CURLE_FAILED_INIT if absent. A DEBUGASSERT requires the send queue to be empty: a new packet must not clobber a queued tail. After a successful Curl_xfer_send it stamps lastTime, dumps the n sent bytes as CURLINFO_HEADER_OUT, and, if the write was short (len != n), appends buf[n..len) to sendbuf and returns the dynbuf result; otherwise the send result.

**Notes.**

- side_effect: Updates mq->lastTime on successful send and logs CURLINFO_HEADER_OUT.

contract: [mqtt_flush](r14-mqtt-protocol.md#u-aad936b2c349)

<a id="u-94b20d5fccff"></a>
### `mqtt_setup_conn`

`static CURLcode mqtt_setup_conn(struct Curl_easy *data, struct connectdata *conn)` · [lib/mqtt.c:L113-L133][f1]

Allocates and attaches the MQTT protocol state: a zeroed struct mqtt_conn at the connection under CURL_META_MQTT_CONN with mqtt_conn_dtor, then a zeroed struct MQTT at the easy handle under CURL_META_MQTT_EASY with mqtt_easy_dtor, after initializing recvbuf and sendbuf with the DYN_MQTT_RECV/DYN_MQTT_SEND limits.

Any allocation or meta-set failure is reported as CURLE_OUT_OF_MEMORY; on the first failure path the already-attached connection meta is expected to be cleaned by the meta layer, which this file does not show.

uses: [mqtt_conn_dtor](r14-mqtt-protocol.md#u-20af1a526694), [mqtt_easy_dtor](r14-mqtt-protocol.md#u-c79167c92109)

**Uncertainties.**

- Whether a failed mq allocation after successful conn meta set leaks depends on meta-layer behavior not visible here.

<a id="u-3c09a688aabd"></a>
### `mqtt_subscribe`

`static CURLcode mqtt_subscribe(struct Curl_easy *data)` · [lib/mqtt.c:L473-L520][f1]

Builds and sends a SUBSCRIBE packet for the URL topic.

Requires the connection mqtt_conn meta or returns CURLE_FAILED_INIT. Gets the topic via mqtt_get_topic (propagating failure to the shared fail path that frees topic and packet), increments mqtt->packetid, sizes the packet as topiclen + 5 payload bytes plus the encoded remaining-length bytes and the control byte, and mallocs it (CURLE_OUT_OF_MEMORY on failure). It writes the SUBSCRIBE control byte, the encoded length, the big-endian packetid, the big-endian topic length, the topic, and a trailing QoS-zero byte, then sends via mqtt_send. All allocations are freed on the fail path regardless of result.

calls: [mqtt_get_topic](r14-mqtt-protocol.md#u-75f134d61e7e), [mqtt_encode_len](r14-mqtt-protocol.md#u-d33fadf28e8c), [mqtt_send](r14-mqtt-protocol.md#u-10eef5d77808)

**Uncertainties.**

- packetlen overflow before mqtt_encode_len is not checked, though topiclen was already capped at 0xffff by mqtt_get_topic.

<a id="u-779251becf1e"></a>
### `mqtt_verify_connack`

`static CURLcode mqtt_verify_connack(struct Curl_easy *data)` · [lib/mqtt.c:L421-L453][f1]

Validates the server CONNACK after CONNECT.

Requires mq; fails with CURLE_WEIRD_SERVER_REPLY if mq->remaining_length is not 2. Ensures MQTT_CONNACK_LEN (2) bytes are buffered via mqtt_recv_atleast and propagates its result, including CURLE_AGAIN. Dumps the two bytes as CURLINFO_HEADER_IN; if they are not 0x00 0x00 it fails with CURLE_WEIRD_SERVER_REPLY and resets recvbuf (dropping buffered bytes). On success it consumes the two bytes and returns CURLE_OK.

calls: [mqtt_recv_atleast](r14-mqtt-protocol.md#u-7726765abc25), [mqtt_recv_consume](r14-mqtt-protocol.md#u-d691c54c029b)

<a id="u-60c62c7410da"></a>
### `mqtt_verify_suback`

`static CURLcode mqtt_verify_suback(struct Curl_easy *data)` · [lib/mqtt.c:L525-L561][f1]

Validates the SUBACK after SUBSCRIBE, assuming the first byte was already read.

Requires both metas or returns CURLE_FAILED_INIT; fails with CURLE_WEIRD_SERVER_REPLY if remaining_length is not 3. Ensures MQTT_SUBACK_LEN bytes are buffered and propagates the result to the shared fail return. Dumps three bytes as CURLINFO_HEADER_IN; if the first two do not match the big-endian packetid or the third byte is not 0x00, it resets recvbuf and returns CURLE_WEIRD_SERVER_REPLY. On success it consumes the three bytes and returns CURLE_OK.

calls: [mqtt_recv_atleast](r14-mqtt-protocol.md#u-7726765abc25), [mqtt_recv_consume](r14-mqtt-protocol.md#u-d691c54c029b)

<a id="u-867983a0c13d"></a>
### `mqtts_connecting`

`static CURLcode mqtts_connecting(struct Curl_easy *data, bool *done)` · [lib/mqtt.c:L1014-L1023][f1]

TLS-phase callback for MQTTS: drives the TLS handshake via Curl_conn_connect on the first socket with blocking=TRUE; a handshake error marks the connection for close via connclose and propagates the result.

*done is driven by Curl_conn_connect.

uses: [mqtt-c-protocol-tables](r14-mqtt-protocol.md#u-4795f1c80d15)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/mqtt.c
