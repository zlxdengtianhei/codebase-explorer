# Protocol module interfaces

**Capability.** Internal headers declaring per-protocol state and entry points that other libcurl modules consume, currently the FTP connection/easy state and wildcard parser interface and the WebSocket entry points.

Use this subtree to find the data structures and function contracts protocol implementations expose to the rest of the library; behavior lives in the corresponding implementation files, not here.

**Children.**

- [FTP state and wildcard interface](r4-ftp-protocol-state.md) `r4-ftp-protocol-state` · 7 unit(s)

Parent: [curl source tree](r4-curl.md)

## Units (1)

<a id="u-e3bd20a1b617"></a>
### `ws.h module code (L1–L44)`

`module_region` · [lib/ws.h:L1-L44][f1]

Declares the WebSocket protocol entry points for curl's HTTP stack.

When WebSockets and HTTP are both enabled, it exposes the global Curl_protocol_ws protocol dispatch table, the connection meta key used to store per-connection protocol state, and two functions: Curl_ws_request, which presumably mutates an outgoing request dynbuf during WebSocket handshake setup, and Curl_ws_accept, which consumes received bytes of a handshake response. When either feature is disabled, the macro block replaces these with inert stubs: Curl_ws_request expands to CURLE_OK so call sites compile away the handshake step, and Curl_ws_free expands to a no-op statement. The declarations themselves carry no implementation, so behavior such as error codes or buffer handling lives elsewhere.

**Uncertainties.**

- Curl_ws_free is macro-defined but has no corresponding declaration in the enabled branch; whether callers reference it in the enabled build cannot be confirmed from this header alone.
- The exact effects of Curl_ws_request on the dynbuf and Curl_ws_accept on input bytes are not visible; parameter semantics are inferred from names and types only.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/ws.h
