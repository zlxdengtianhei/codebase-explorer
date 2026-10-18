# curl Codebase

**Capability.** Umbrella responsibility for performing network transfers: connection setup, transport (QUIC/TLS), request/transfer driving, HTTP domain policy, parsing, shared utilities, public API surface, and the command-line tool.

Read this subtree top-down to locate a responsibility. Each child owns one cohesive capability; leaves hold the primary homes of individual units. Dependencies between subtrees are listed in depends_on.

**Children.**

- [Connection Filter Setup](r10-connection-filters.md) `r10-connection-filters` · 14 unit(s)
- [QUIC / HTTP-3 Transport](r10-quic-transport.md) `r10-quic-transport` · 0 unit(s)
- [wolfSSL TLS Backend](r10-tls-wolfssl.md) `r10-tls-wolfssl` · 1 unit(s)
- [Request and Transfer Engine](r10-transfer-engine.md) `r10-transfer-engine` · 0 unit(s)
- [HTTP Domain Policy Caches](r10-url-policy.md) `r10-url-policy` · 0 unit(s)
- [Dynamic Header Array \(dynhds\)](r10-dynamic-headers.md) `r10-dynamic-headers` · 17 unit(s)
- [Date Parsing](r10-parsedate.md) `r10-parsedate` · 29 unit(s)
- [NTLM Core Crypto](r10-ntlm-crypto.md) `r10-ntlm-crypto` · 15 unit(s)
- [Small Shared Utilities](r10-misc-utilities.md) `r10-misc-utilities` · 11 unit(s)
- [Public WebSocket API](r10-websockets-api.md) `r10-websockets-api` · 2 unit(s)
- [curl Tool](r10-curl-tool.md) `r10-curl-tool` · 0 unit(s)

Parent: [Transfer & Multi Engine](transfer-engine.md)

## Units (1)

<a id="u-8f03428f39fb"></a>
### `tool_sdecls.h-structs-and-enums`

`struct OutStruct` · [src/tool_sdecls.h:L65-L78][f1]

Header defining the tool's shared value types, all data declarations without behavior.

OutStruct tracks one output destination: filename (NULL for a standard stream), stream, bytes written, init offset for truncation/append, a Windows-only incomplete UTF-8 sequence buffer, and flags alloc_filename, is_cd_filename, regular_file (implies seekable/appendable output with filename set), fopened (file must later be closed), and out_null. struct getout is one URL node in config->url_list holding url, outfile, infile, its URL ordinal, and flags outset/urlset/uploadset/useremote/noupload/noglob/out_null governing how the entry is treated. The trace enum selects trace/verbose output style (NONE, BIN, ASCII, PLAIN); HttpReq selects the tool's HTTP request kind starting with UNSPEC; SANITIZEcode enumerates sanitize results OK, INVALID_PATH, BAD_ARGUMENT, OUT_OF_MEMORY, with SANITIZE_ERR_LAST reserved.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: ../../../../../../eval/curl-2c04412/src/tool_sdecls.h
