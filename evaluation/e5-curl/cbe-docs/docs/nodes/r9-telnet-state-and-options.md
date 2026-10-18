# Telnet state, options and negotiation

**Capability.** Compile-time state (Q-state constants, 256-slot us/him negotiation tables, suboption buffer) plus the RFC 1143 negotiation machinery: set_local/remote_option, telnet_negotiate across all 256 slots, and the rec_* handlers for received DO/DONT/WILL/WONT.

Read this child to understand how option enable/disable requests are queued and answered. The transfer FSM child dispatches into rec_* and suboption from the receive path.

**Depended on by.**

- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) · graph-confirmed · 8 edge(s)

Parent: [Telnet protocol backend](r9-telnet.md)

## Units (10)

<a id="u-64a7f9a32628"></a>
### `telnet-c-state-and-options`

`enum` · [lib/telnet.c:L96-L106][f1]

Groups the telnet module's compile-time state: suboption buffer macros, RFC 1143 Q-state constants (CURL_NO/CURL_YES/CURL_WANTYES/CURL_WANTNO and queue values CURL_EMPTY/CURL_OPPOSITE), the easy-handle meta key, the FSM state enum, and struct TELNET which holds per-transfer negotiation tables (us/usq/him/himq/preferred arrays of 256), suboption strings (TTYPE, XDISPLOC, NAWS sizes), the receiver FSM state, the environment-variable slist, an output dynbuf, and the 512-byte suboption accumulation buffer with subpointer/subend.

CURL_SB_ACCUM silently drops bytes once the buffer is full.

uses: [telnet-c-receive-fsm](../../catalog.json)

<a id="u-7f711f01132c"></a>
### `bad_option`

`static bool bad_option(const char *data)` · [lib/telnet.c:L960-L963][f1]

Returns TRUE when the string is NULL or contains an IAC (0xFF) byte, i.e. cannot be safely embedded in a telnet suboption.

<a id="u-5dcbf0f804bd"></a>
### `rec_do`

`static void rec_do(struct Curl_easy *data, struct TELNET *tn, int option)` · [lib/telnet.c:L720-L776][f1]

Handles a received DO for the 'us' table.

From NO: if locally preferred, enable (YES), send WILL, and send the subnegotiation payload when registered; otherwise, if only subnegotiation is requested (e.g. NAWS), enable and send suboption data anyway; otherwise refuse with WONT. From YES: no-op. From WANTNO: erroneous DO ends pending disable — EMPTY settles to NO, OPPOSITE settles to YES and clears the queue. From WANTYES: EMPTY enables and triggers subnegotiation; OPPOSITE flips to WANTNO and sends WONT.

<a id="u-43e24e438dc2"></a>
### `rec_dont`

`static void rec_dont(struct Curl_easy *data, struct TELNET *tn, int option)` · [lib/telnet.c:L778-L816][f1]

Handles a received DONT for the 'us' table.

From NO: no-op. From YES: disable and send WONT. From WANTNO: EMPTY settles to NO; OPPOSITE flips back to WANTYES and sends WILL. From WANTYES: EMPTY and OPPOSITE both settle to NO, the latter clearing the queue.

<a id="u-d56441fa4bf4"></a>
### `rec_will`

`static void rec_will(struct Curl_easy *data, struct TELNET *tn, int option)` · [lib/telnet.c:L404-L448][f1]

Handles a received WILL per the RFC 1143 Q-matrix for the 'him' table.

From NO: confirm with DO if him_preferred, otherwise refuse with DONT. From YES: no-op. From WANTNO: an erroneous WILL ends the pending disable — with EMPTY queue the option settles to NO, with OPPOSITE queue it settles to YES and the queue clears. From WANTYES: with EMPTY queue the option becomes YES; with OPPOSITE queue (a queued disable arrived during enable negotiation) it flips to WANTNO and sends DONT.

<a id="u-9619be511575"></a>
### `rec_wont`

`static void rec_wont(struct Curl_easy *data, struct TELNET *tn, int option)` · [lib/telnet.c:L450-L488][f1]

Handles a received WONT for the 'him' table.

From NO: no-op. From YES: move to NO and send DONT. From WANTNO: EMPTY queue settles to NO; OPPOSITE queue flips back to WANTYES and sends DO. From WANTYES: EMPTY settles to NO; OPPOSITE also settles to NO and clears the queue.

<a id="u-fa05419bd3f2"></a>
### `send_negotiation`

`static void send_negotiation(struct Curl_easy *data, int cmd, int option)` · [lib/telnet.c:L225-L240][f1]

Sends a 3-byte IAC/cmd/option negotiation message via Curl_xfer_send.

On send failure it logs the error via failf but does not propagate; always logs the command through printoption. Return value is void, so callers cannot detect send failure here.

**Uncertainties.**

- Send failure is only logged; whether the negotiation state stays consistent depends on later round trips, not visible here.

<a id="u-8d32f544446b"></a>
### `set_local_option`

`static void set_local_option(struct Curl_easy *data, struct TELNET *tn, int option, i…` · [lib/telnet.c:L315-L386][f1]

Mirror of set_remote_option for the local 'us' side, using us/usq tables and sending WILL to enable or WONT to disable.

The same Q-state transitions and queue corrections apply; no send-failure handling beyond send_negotiation's own logging.

<a id="u-d9028c620c1c"></a>
### `set_remote_option`

`static void set_remote_option(struct Curl_easy *data, struct TELNET *tn, int option, …` · [lib/telnet.c:L242-L313][f1]

Applies the Q-matrix for the 'him' side to request the peer enable or disable an option.

newstate==CURL_YES: from NO it enters WANTYES and sends DO; from YES nothing; from WANTNO it queues OPPOSITE (empty queue) or ignores (already opposite-queued); from WANTYES it clears an OPPOSITE queue. newstate==NO: from YES it enters WANTNO and sends DONT; from WANTYES it queues OPPOSITE; WANTNO with OPPOSITE queue clears it; NO is a no-op. State mutations are local to tn->him/himq.

<a id="u-1ed47d41b533"></a>
### `telnet_negotiate`

`static void telnet_negotiate(struct Curl_easy *data, struct TELNET *tn)` · [lib/telnet.c:L388-L402][f1]

Drives initial option negotiation across all 256 option slots (CURL_NTELOPTS iterations): skips ECHO entirely so the server may echo without being asked, and for each option preferred YES locally sends WILL via set_local_option and requests the peer enable it via set_remote_option.

calls: [set_local_option](r9-telnet-state-and-options.md#u-8d32f544446b), [set_remote_option](r9-telnet-state-and-options.md#u-d9028c620c1c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/telnet.c
