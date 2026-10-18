# Core transfer data model

**Capability.** curl's central handle structures: connectdata with per-connection flags, the easy handle tying together all transfer state, the static UserDefined settings versus dynamic UrlState, and Digest auth state.

Every subsystem reads or writes through these structures. The UserDefined/UrlState split (static settings vs operational state) is the key distinction when tracing where a value lives.

**Depended on by.**

- [Tool configuration](r15-cli-config.md) · model-inferred · 0 edge(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Units (6)

<a id="u-2ade944005ca"></a>
### `urldata-h-connectdata`

`struct connectdata` · [lib/urldata.h:L259-L308][f1]

Groups the struct connectdata declaration: the per-connection state record holding identity, peers, sockets, filters, and per-connection flags.

The declaration is split into several source regions plus a closing tag, all describing one struct. Fields are grouped: identity (connection_id, attached_multi), peer/credential pointers (origin, via_peer, origin2, via_peer2, creds, creds_origin, scheme), a meta_hash key-value store whose elements carry their own destructors, proxy info (compiled out when CURL_DISABLE_PROXY), two filter/socket/send/recv slots indexed by FIRSTSOCKET(0)/SECONDARYSOCKET(1), shutdown timing, SSL configs, NTLM/SPNEGO/GSSAPI state under feature guards, and pool bookkeeping (attached_xfers counted by CONN_INUSE, cpid). CURL_CONN_HOST_DISPNAME picks the display hostname preferring SOCKS proxy peer, then HTTP proxy peer, then via_peer, then origin; the proxy branch is absent when CURL_DISABLE_PROXY is set. transport_wanted may differ from the actual transport (Alt-Svc, happy eyeballs); readers must use Curl_conn_get_transport() once connected.

uses: [ConnectBits](r15-core-data-model.md#u-25e72c79ebba), [ip_quadruple][f1], [hostname][f1]

**Uncertainties.**

- Struct is declared here only; initialization and lifetime rules live in other files not supplied.

<a id="u-25e72c79ebba"></a>
### `ConnectBits`

`struct ConnectBits` · [lib/urldata.h:L181-L222][f1]

Declares struct ConnectBits, the per-connection boolean flag set inside struct connectdata.

Each BIT member records one connection-state condition: connect_only mode; proxy origin and SOCKS5 authentication (guard CURL_DISABLE_PROXY); close-after-request versus reuse, where the comment mandates changes only via the connclose()/connkeep() macros; alt-svc use, IPv6, do_more protocol callback scheduling, retry-before-reclose, FTP EPSV/EPRT/SSL-data toggles (guard CURL_DISABLE_FTP), bind-done, protocol upgrade in progress, multiplexing, TCP fast open, ALPN, accepted secondary socket, happy-eyeballs parallel connect, abort, no_reuse, two shutdown-progress flags, and DNS-resolved status. Members disappear per their guards, changing struct layout by build configuration.

**Uncertainties.**

- Semantics of each flag come from inline comments; the code that sets them is not in this file.

<a id="u-d40218cbe050"></a>
### `Curl_easy`

`struct Curl_easy` · [lib/urldata.h:L1164-L1230][f1]

Declares struct Curl_easy, the easy handle tying together all transfer state: a magic identifier to detect handle mix-ups, multi-interface identity (mid, mstate, result, multi, multi_easy), connection pointer, share handle, a callstack of ongoing easy-API calls, one posted message slot, a non-unique log-tracking id, master handle linkage with a sub-transfer completion callback, a meta_hash key-value store with per-element destructors, and embedded sub-structures: SingleRequest req, UserDefined set, CookieInfo cookies, hsts, altsvc cache, Progress progress, UrlState state, WildcardData, PureInfo info, and TLS session info.

The comment restates the split: connection-oriented data lives in connectdata; user-set data in UserDefined; internal calculated values in UrlState.

**Uncertainties.**

- Whether msg is a queue slot reused per multi notification cannot be determined from the declaration alone.

<a id="u-13b53b75f2ec"></a>
### `UrlState`

`struct UrlState` · [lib/urldata.h:L525-L682][f1]

Declares struct UrlState, the dynamic per-transfer state that changes during operation, in contrast to UserDefined which holds static user settings.

It carries origin peer pointers for the initial and current request (credentials from CURLOPT_* apply only to the initial origin), errno capture, request/redirect counters, Digest auth state for host and proxy (guard CURL_DISABLE_DIGEST_AUTH), expire timers (splay-backed per-reason offsets sized by EXPIRE_LAST), async resolver data (USE_CURL_ASYNC), OpenSSL provider/engine pointers type-erased to void* (USE_OPENSSL), URL/redirect/range working strings, received-header list and curl_easy_nextheader() cache fields (HTTP guards), netrc, cookies/HSTS lists, RTSP session and CSeq state surviving requests and connections, and a large block of BIT flags governing follow, retry, errorbuf reuse, Expect-disabled after 417, done-once multi_done protection, upload/ASCII mode, and HTTP header-addition bookkeeping.

**Uncertainties.**

- Exact reset/cleanup points for these fields (Curl_init_transfer, multi_done) are referenced by comments but implemented elsewhere.

<a id="u-3f328a9245d9"></a>
### `UserDefined`

`struct UserDefined` · [lib/urldata.h:L829-L1139][f1]

Declares struct UserDefined, the static per-easy-handle settings set once by the application and unchanged during transfers; internally generated values belong in UrlState instead.

It aggregates all user callbacks (write, read, header, progress, debug, ioctl, socket open/close/sockopt, seek, prereq, HSTS, SSH host/key checks, trailer, resolver-start, SSL ctx) with their client pointers, authentication bitmasks, POST data variants (pointer, copied, MIME), timeout/speed-limit/buffer-size scalars, proxy settings (guards CURL_DISABLE_PROXY), SSL easy configs, header/resolve/connect_to/quote lists, protocol allow and redirect-allow masks, redirect limits and post-301/302/303 behaviors, FTP/TFTP/RTSP/SSH/SMTP/DoH/websocket options under feature guards, and roughly eighty BIT flags for behaviors like verbose, reuse forbid/fresh, no_signal, TCP keepalive/fastopen, HTTP version allowances, and fail-on-error. Enumerations dupstring and dupblob index its u8_strset strings and blobs[BLOB_LAST] array; CURL_EASY_STR* macros wrap that string store.

**Notes.**

- contract: Character pointer fields point to dynamic storage unless otherwise stated, per the preceding comment.

**Uncertainties.**

- Value ranges and validation for numeric fields (e.g. buffer_size clamping against UPLOADBUFFER_MIN/MAX) are enforced elsewhere, not here.

<a id="u-5336caf85d3b"></a>
### `digestdata`

`struct digestdata` · [lib/urldata.h:L142-L161][f1]

Declares struct digestdata, the Digest challenge-response authentication state.

Members depend on build: with USE_WINDOWS_SSPI it holds an SSPI input token, its length, and an HTTP context handle; otherwise it holds plain char* Digest parameters (nonce, cnonce, realm, opaque, qop, algorithm), a nonce count, an algorithm selector, and stale/userhash bit flags where stale marks renegotiation. The whole struct is compiled out when CURL_DISABLE_DIGEST_AUTH is defined. It references credential and peer structures for the bound credentials and origin.

**Uncertainties.**

- Interpretation of fields rests on their comments; no consuming code is visible here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/urldata.h
