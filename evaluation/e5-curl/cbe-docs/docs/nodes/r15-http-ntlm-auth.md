# HTTP NTLM authentication

**Capability.** Parses incoming WWW-/Proxy-Authenticate NTLM headers and produces outgoing Authorization headers, selecting host or proxy state and credentials by the proxy flag.

Use this for HTTP-specific NTLM handshake state. It is separate from the generic SASL engine; output generation depends on the state advanced by input parsing.

Parent: [curl codebase](r15-curl-codebase.md)

## Units (2)

<a id="u-d3ec333abb90"></a>
### `Curl_input_ntlm`

`CURLcode Curl_input_ntlm(struct Curl_easy *data, bool proxy, /* if proxy or not */ co…` · [lib/http_ntlm.c:L51-L111][f1]

Parses an incoming WWW-/Proxy-Authenticate: NTLM header and advances the per-connection NTLM state, choosing http or proxy state by the proxy flag.

If the header starts with 'NTLM': it obtains the ntlmdata (CURLE_OUT_OF_MEMORY if unavailable), skips past the token and blanks; when a payload follows, it base64-decodes it (propagating decode errors) and feeds it to Curl_auth_decode_ntlm_type2_message, then sets state to NTLMSTATE_TYPE2. With no payload: NTLMSTATE_LAST logs 'restarted' and removes the NTLM state; NTLMSTATE_TYPE3 logs 'handshake rejected', removes state, unlinks peer credentials, resets to NTLMSTATE_NONE, and returns CURLE_REMOTE_ACCESS_DENIED; any state >= NTLMSTATE_TYPE1 logs an internal-error failure and returns CURLE_REMOTE_ACCESS_DENIED; otherwise the state becomes NTLMSTATE_TYPE1. Headers not prefixed with NTLM are ignored and CURLE_OK returned.

uses: [curl_ntlm_core.h module code (L1–L73)][f2]

**Uncertainties.**

- Curl_auth_ntlm_get, Curl_auth_decode_ntlm_type2_message, Curl_auth_ntlm_remove, Curl_peer_unlink, Curl_creds_unlink are defined elsewhere; their failure semantics beyond returned CURLcode are not visible here

<a id="u-9599a49cec7a"></a>
### `Curl_output_ntlm`

`CURLcode Curl_output_ntlm(struct Curl_easy *data, bool proxy)` · [lib/http_ntlm.c:L116-L251][f1]

Produces the outgoing NTLM Authorization header for host or proxy, selected by the proxy flag, which determines the target header pointer, credentials, hostname, state variable, and auth struct.

Proxy support is compiled out with CURL_DISABLE_PROXY, returning CURLE_NOT_BUILT_IN in that case. It obtains ntlmdata (CURLE_OUT_OF_MEMORY on failure), clears authp->done, and on Windows SSPI lazily initializes the global security function table (returning the init result if still unavailable). If state is TYPE3 it moves to LAST, meaning no further header is needed. State TYPE1 (and the default/restart case): for non-proxy it verifies creds_origin matches the current origin and the connection creds match, returning CURLE_FAILED_INIT with a debug assert on mismatch; it links peer and creds, builds a type-1 message, base64-encodes it, replaces *allocuserpwd with an 'Authorization: NTLM <b64>\r\n' (Proxy- prefixed for proxies) via curl_maprintf, and maps allocation failure to CURLE_OUT_OF_MEMORY. State TYPE2: builds a type-3 message; when a message is produced it encodes, writes the header, advances state to TYPE3, and sets authp->done. State LAST: forces httpauthpicked/proxyauthpicked to CURLAUTH_NTLM, frees the header, and sets authp->done. The message bufref is freed before returning the accumulated result.

contract: [Curl_input_ntlm](r15-http-ntlm-auth.md#u-d3ec333abb90)

**Uncertainties.**

- Curl_auth_create_ntlm_type1_message and Curl_auth_create_ntlm_type3_message are external; their failure modes are handled only through the returned CURLcode here

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/lib/http_ntlm.c
[f2]: ../../../../../../eval/curl-2c04412/lib/curl_ntlm_core.h
