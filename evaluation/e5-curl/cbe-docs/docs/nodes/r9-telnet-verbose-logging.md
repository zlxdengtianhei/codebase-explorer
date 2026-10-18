# Telnet verbose logging

**Capability.** Verbose-only logging of sent/received commands, options, and suboption payloads via printoption and printsub, compiled to no-ops without CURLVERBOSE.

Consult this child when debugging negotiation exchanges. The whole subtree is gated on data->set.verbose and CURLVERBOSE.

**Depends on.**

- [Trace and Debug Logging](r1-trace-logging.md) · graph-only · 29 edge(s)

**Depended on by.**

- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) · graph-confirmed · 10 edge(s)

Parent: [Telnet protocol backend](r9-telnet.md)

## Units (2)

<a id="u-26a6f9558fd0"></a>
### `printoption`

`static void printoption(struct Curl_easy *data, const char *direction, int cmd, int o…` · [lib/telnet.c:L134-L167][f1]

Logs a sent or received telnet command/option pair when verbose mode is on; compiled to a no-op without CURLVERBOSE.

For IAC commands it prints the mnemonic if recognized, else the numeric value. For WILL/WONT/DO/DONT it resolves the option name via CURL_TELOPT, special-cases EXOPL, and falls back to numbers for unrecognized values or commands.

<a id="u-7bc5831dc7d0"></a>
### `printsub`

`static void printsub(struct Curl_easy *data, int direction, /* '<' or '>' */ const un…` · [lib/telnet.c:L490-L601][f1]

Verbose logger for suboption payloads, gated on data->set.verbose.

With direction '<'/'>' it prefixes RCVD/SENT and, for received data of length>=3, detects a suboption not terminated by IAC SE and names the actual terminator. It then trims two trailing bytes (returning early on bad input shorter than 2) and, for payloads of length<=1, logs 'Empty suboption?'. Dispatch on the first byte: recognized options print by name, TTYPE/XDISPLOC/NEW_ENVIRON/NAWS are supported, others '(unsupported)', unknown bytes print numerically. NAWS prints width/height from 16-bit pairs when length>4; other options print TELQUAL keywords (IS/SEND/INFO/NAME), quoted strings for TTYPE/XDISPLOC, formatted var/value lists for NEW_ENVIRON IS, or hex bytes for anything else.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/telnet.c
